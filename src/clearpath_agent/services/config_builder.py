"""Configuration Builder Service.

The core assembly engine that transforms Structured Intent JSON
into complete StatusActionFlow configurations.
"""

import logging
from typing import Optional

from ..models.entities import ActionButton, Status, StatusActionFlow, Widget
from ..models.enums import ActionButtonType, StatusCategory, UserRole, WidgetType
from ..models.intent_schemas import (
    ExtractedPhrase,
    ExtractedStep,
    ResolutionResult,
    StructuredIntent,
)
from .config_defaults import DefaultsProvider
from .entity_resolver import EntityResolver

logger = logging.getLogger(__name__)


class ConfigBuilder:
    """Builds StatusActionFlow configurations from structured intent.

    This is the main assembly engine that:
    1. Takes structured intent from LLM extraction
    2. Resolves phrases to canonical entities
    3. Applies intelligent defaults
    4. Produces complete, validated configurations
    """

    def __init__(
        self,
        resolver: Optional[EntityResolver] = None,
        defaults_provider: Optional[DefaultsProvider] = None,
        vector_store=None,
        graph_store=None,
    ):
        """Initialize the config builder.

        Args:
            resolver: EntityResolver instance (created if not provided)
            defaults_provider: DefaultsProvider instance (created if not provided)
            vector_store: Optional VectorStore for knowledge base lookups
            graph_store: Optional GraphStore for relationship lookups
        """
        self.resolver = resolver or EntityResolver(vector_store=vector_store)
        self.defaults_provider = defaults_provider or DefaultsProvider(
            vector_store=vector_store,
            graph_store=graph_store,
        )
        self.vector_store = vector_store
        self.graph_store = graph_store

        # Track applied defaults for transparency
        self._applied_defaults: list[str] = []
        # Track items needing review
        self._review_items: list[dict] = []

    def build_config(
        self,
        intent: StructuredIntent,
        apply_defaults: bool = True,
        apply_best_practices: bool = True,
    ) -> StatusActionFlow:
        """Build a complete StatusActionFlow from structured intent.

        Args:
            intent: The structured intent from LLM extraction
            apply_defaults: Whether to apply default widgets/toggles
            apply_best_practices: Whether to enforce best practices

        Returns:
            Complete StatusActionFlow ready for validation/export
        """
        logger.info(f"Building config for workflow: {intent.workflow_name}")

        # Reset tracking
        self._applied_defaults = []
        self._review_items = []

        # Resolve all phrases first
        resolution_result = self._resolve_all_phrases(intent)

        # Build statuses
        statuses = []
        for step in intent.steps:
            status = self._build_status(
                step=step,
                resolution_result=resolution_result,
                total_steps=len(intent.steps),
                apply_defaults=apply_defaults,
            )
            statuses.append(status)

        # Link statuses with next/previous
        self._link_statuses(statuses)

        # Apply best practices if enabled
        if apply_best_practices:
            for status in statuses:
                self._apply_best_practices(status)

        # Create the complete flow
        flow = StatusActionFlow(
            name=intent.workflow_name,
            description=intent.workflow_description,
            statuses=statuses,
            is_default=False,
            job_types=intent.metadata.job_types,
        )

        logger.info(
            f"Built config with {len(statuses)} statuses, "
            f"{sum(len(s.action_buttons) for s in statuses)} action buttons"
        )

        return flow

    def _resolve_all_phrases(
        self,
        intent: StructuredIntent,
    ) -> ResolutionResult:
        """Resolve all action and widget phrases in the intent.

        Args:
            intent: The structured intent

        Returns:
            ResolutionResult with all resolved entities
        """
        all_action_phrases = []
        all_widget_phrases = []

        for step in intent.steps:
            all_action_phrases.extend(step.action_phrases)
            all_widget_phrases.extend(step.information_needs)

        result = self.resolver.resolve_all(all_action_phrases, all_widget_phrases)

        # Track items needing review (low confidence)
        for phrase in result.review_required:
            self._review_items.append({
                "type": "low_confidence",
                "phrase": phrase.phrase,
                "confidence": phrase.confidence,
                "suggested_type": phrase.suggested_type,
                "alternatives": phrase.alternatives,
            })

        # Track unresolved phrases so users know they were dropped
        for phrase in result.unresolved_phrases:
            self._review_items.append({
                "type": "unresolved",
                "phrase": phrase.phrase,
                "context": phrase.context,
                "suggested_type": phrase.suggested_type,
                "confidence": phrase.confidence,
                "message": "Could not resolve to a known action/widget type",
            })

        return result

    def _build_status(
        self,
        step: ExtractedStep,
        resolution_result: ResolutionResult,
        total_steps: int,
        apply_defaults: bool = True,
    ) -> Status:
        """Build a Status from an extracted step.

        Args:
            step: The extracted step from intent
            resolution_result: Resolution results for all phrases
            total_steps: Total number of steps in workflow
            apply_defaults: Whether to apply defaults

        Returns:
            Complete Status object
        """
        # Determine category
        category = self._determine_category(step, total_steps)

        # Determine role
        role = self._determine_role(step, category)

        # Build action buttons
        action_buttons = self._build_action_buttons(
            step.action_phrases,
            resolution_result,
        )

        # Get action types for widget suggestions
        action_types = [
            ActionButtonType(ab.action.value)
            for ab in action_buttons
            if ab.action
        ]

        # Build widgets
        widgets = self._build_widgets(
            step.information_needs,
            resolution_result,
            action_types,
            apply_defaults,
        )

        # Format instructions
        instructions = self.defaults_provider.format_status_instructions(
            actions=action_types,
            raw_instructions=step.instructions_raw,
            include_action_list=not step.instructions_raw,
        )

        # Get default toggles
        toggles = self.defaults_provider.get_default_toggles(category)

        # Get color
        color = self.defaults_provider.get_color_for_category(category)

        return Status(
            name=step.step_name,
            category=category,
            color=color,
            sequence=step.sequence,
            user_role=role,
            action_buttons=action_buttons,
            widgets=widgets,
            status_instructions=instructions,
            display_action_menu=toggles["display_action_menu"],
            ability_to_change_status=toggles["ability_to_change_status"],
            focus_view_enabled=toggles["focus_view_enabled"],
            restrict_to_focus_view=toggles["restrict_to_focus_view"],
        )

    def _determine_category(
        self,
        step: ExtractedStep,
        total_steps: int,
    ) -> StatusCategory:
        """Determine the status category for a step.

        Args:
            step: The extracted step
            total_steps: Total number of steps

        Returns:
            Appropriate StatusCategory
        """
        # Use hint if provided
        if step.category_hint:
            try:
                return StatusCategory(step.category_hint)
            except ValueError:
                pass

        # Use defaults provider to infer
        return self.defaults_provider.infer_status_category(
            status_name=step.step_name,
            sequence=step.sequence,
            total_statuses=total_steps,
        )

    def _determine_role(
        self,
        step: ExtractedStep,
        category: StatusCategory,
    ) -> UserRole:
        """Determine the user role for a step.

        Args:
            step: The extracted step
            category: The status category

        Returns:
            Appropriate UserRole
        """
        # Use hint if provided
        if step.role_hint:
            try:
                return UserRole(step.role_hint)
            except ValueError:
                pass

        # Use defaults provider
        return self.defaults_provider.get_role_defaults(
            status_name=step.step_name,
            status_category=category,
        )

    def _build_action_buttons(
        self,
        phrases: list[ExtractedPhrase],
        resolution_result: ResolutionResult,
    ) -> list[ActionButton]:
        """Build ActionButton objects from resolved phrases.

        Args:
            phrases: List of action phrases
            resolution_result: Resolution results

        Returns:
            List of ActionButton objects
        """
        buttons = []

        for i, phrase in enumerate(phrases):
            resolved = resolution_result.resolved_actions.get(phrase.phrase)
            if not resolved:
                logger.warning(f"Skipping unresolved action: {phrase.phrase}")
                self._review_items.append({
                    "type": "unresolved_action",
                    "phrase": phrase.phrase,
                    "suggested_type": phrase.suggested_type,
                    "message": "Action phrase could not be resolved - skipped",
                })
                continue

            try:
                action_type = ActionButtonType(resolved.resolved_type)
            except ValueError:
                logger.warning(f"Invalid action type: {resolved.resolved_type}")
                continue

            # Create label from phrase or use default
            label = self._create_button_label(phrase, action_type)

            # Check template requirements
            template_reqs = self.resolver.check_template_requirements(action_type)

            button = ActionButton(
                action=action_type,
                label=label,
                order=i,
                required=phrase.requires_template,
                form_id=None,  # To be filled by user if required
                template_id=None,  # To be filled by user if required
            )
            buttons.append(button)

            # Track if template is needed
            if template_reqs["requires_template"] or template_reqs["requires_form"]:
                self._review_items.append({
                    "type": "template_required",
                    "action": action_type.value,
                    "label": label,
                    "requires_template": template_reqs["requires_template"],
                    "requires_form": template_reqs["requires_form"],
                })

        return buttons

    def _create_button_label(
        self,
        phrase: ExtractedPhrase,
        action_type: ActionButtonType,
    ) -> str:
        """Create a button label from phrase or action type.

        Args:
            phrase: The original phrase
            action_type: The resolved action type

        Returns:
            Formatted button label
        """
        # If phrase is short enough, use it
        if len(phrase.phrase) <= 50:
            # Capitalize first letter of each word
            return phrase.phrase.title()

        # Otherwise use action type value
        return action_type.value

    def _build_widgets(
        self,
        phrases: list[ExtractedPhrase],
        resolution_result: ResolutionResult,
        action_types: list[ActionButtonType],
        apply_defaults: bool = True,
    ) -> list[Widget]:
        """Build Widget objects from resolved phrases and defaults.

        Args:
            phrases: List of widget phrases
            resolution_result: Resolution results
            action_types: List of action types in this status
            apply_defaults: Whether to apply default widgets

        Returns:
            List of Widget objects
        """
        widget_types = set()

        # Add widgets from resolved phrases
        for phrase in phrases:
            resolved = resolution_result.resolved_widgets.get(phrase.phrase)
            if resolved:
                try:
                    widget_type = WidgetType(resolved.resolved_type)
                    widget_types.add(widget_type)
                except ValueError:
                    logger.warning(f"Invalid widget type: {resolved.resolved_type}")
                    self._review_items.append({
                        "type": "invalid_widget",
                        "phrase": phrase.phrase,
                        "resolved_type": resolved.resolved_type,
                        "message": f"Invalid widget type '{resolved.resolved_type}' - skipped",
                    })
            else:
                # Track unresolved widget phrases
                self._review_items.append({
                    "type": "unresolved_widget",
                    "phrase": phrase.phrase,
                    "suggested_type": phrase.suggested_type,
                    "message": "Widget phrase could not be resolved - skipped",
                })

        # Apply defaults if enabled
        if apply_defaults:
            default_widgets = self.defaults_provider.get_default_widgets(
                status_name="",  # Not used for now
                actions=action_types,
                include_core=True,
            )
            for widget_type in default_widgets:
                if widget_type not in widget_types:
                    widget_types.add(widget_type)
                    self._applied_defaults.append(f"Added default widget: {widget_type.value}")

        # Convert to ordered Widget objects
        widgets = self._order_widgets(list(widget_types))

        return widgets

    def _order_widgets(
        self,
        widget_types: list[WidgetType],
    ) -> list[Widget]:
        """Order widgets according to best practices.

        Ensures:
        - Job Title first
        - Job Status second
        - Status Instructions third
        - Action Buttons last

        Args:
            widget_types: Unordered list of widget types

        Returns:
            Ordered list of Widget objects
        """
        from .config_defaults import WIDGET_ORDER_PRIORITY

        # Sort by priority
        sorted_types = sorted(
            widget_types,
            key=lambda w: WIDGET_ORDER_PRIORITY.get(w, 50)
        )

        # Create Widget objects with proper ordering
        widgets = []
        for i, widget_type in enumerate(sorted_types):
            widgets.append(Widget(
                widget_type=widget_type,
                order=i,
                collapsed=False,
            ))

        return widgets

    def _link_statuses(
        self,
        statuses: list[Status],
    ) -> None:
        """Link statuses with next_status and previous_status.

        Args:
            statuses: List of Status objects to link
        """
        # Sort by sequence
        sorted_statuses = sorted(statuses, key=lambda s: s.sequence)

        for i, status in enumerate(sorted_statuses):
            # Set previous status
            if i > 0:
                status.previous_status = sorted_statuses[i - 1].name

            # Set next status
            if i < len(sorted_statuses) - 1:
                status.next_status = sorted_statuses[i + 1].name

    def _apply_best_practices(
        self,
        status: Status,
    ) -> None:
        """Apply ClearPath Tier 1 best practices to a status.

        Best practices:
        - Action Buttons widget should be last
        - Status Instructions should be numbered
        - Focus View should be enabled for field statuses

        Args:
            status: The Status to modify
        """
        # Ensure Action Buttons is last
        action_buttons_widget = None
        other_widgets = []

        for widget in status.widgets:
            if widget.widget_type == WidgetType.ACTION_BUTTONS:
                action_buttons_widget = widget
            else:
                other_widgets.append(widget)

        if action_buttons_widget:
            # Reorder
            for i, widget in enumerate(other_widgets):
                widget.order = i
            action_buttons_widget.order = len(other_widgets)
            status.widgets = other_widgets + [action_buttons_widget]
            self._applied_defaults.append("Moved Action Buttons to last position")

        # Ensure Focus View is enabled for field statuses
        if status.category == StatusCategory.IN_PROGRESS:
            if not status.focus_view_enabled:
                status.focus_view_enabled = True
                self._applied_defaults.append(
                    f"Enabled Focus View for '{status.name}' (in-progress status)"
                )

    def get_applied_defaults(self) -> list[str]:
        """Get list of defaults that were applied.

        Returns:
            List of strings describing applied defaults
        """
        return self._applied_defaults.copy()

    def get_review_items(self) -> list[dict]:
        """Get items that need user review.

        Returns:
            List of dicts describing items needing review
        """
        return self._review_items.copy()

    def build_from_template(
        self,
        template_name: str,
        customizations: Optional[dict] = None,
    ) -> StatusActionFlow:
        """Build a config from a predefined template.

        Args:
            template_name: Name of the template to use
            customizations: Optional customizations to apply

        Returns:
            StatusActionFlow built from template
        """
        # Import here to avoid circular dependency
        from .default_templates import get_template

        template = get_template(template_name)
        if not template:
            raise ValueError(f"Unknown template: {template_name}")

        # Apply customizations if provided
        if customizations:
            template = self._apply_customizations(template, customizations)

        return template

    def _apply_customizations(
        self,
        template: StatusActionFlow,
        customizations: dict,
    ) -> StatusActionFlow:
        """Apply customizations to a template.

        Args:
            template: The base template
            customizations: Customizations to apply

        Returns:
            Customized StatusActionFlow
        """
        # Create a copy to avoid modifying original
        template_dict = template.model_dump()

        # Apply name customization
        if "name" in customizations:
            template_dict["name"] = customizations["name"]

        # Apply description customization
        if "description" in customizations:
            template_dict["description"] = customizations["description"]

        # Apply job types customization
        if "job_types" in customizations:
            template_dict["job_types"] = customizations["job_types"]

        # Apply status customizations
        if "status_customizations" in customizations:
            for status_name, status_custom in customizations["status_customizations"].items():
                for status_dict in template_dict["statuses"]:
                    if status_dict["name"].lower() == status_name.lower():
                        status_dict.update(status_custom)
                        break

        return StatusActionFlow(**template_dict)

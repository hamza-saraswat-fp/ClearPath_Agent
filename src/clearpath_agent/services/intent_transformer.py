"""Simple transformer from StructuredIntent to StatusActionFlow.

Pass through Relational Agent output + add missing fields. No validation. No filtering.
"""

from typing import Optional

from ..models.entities import ActionButton, Status, StatusActionFlow, Widget
from ..models.enums import StatusCategory, UserRole
from ..models.intent_schemas import ExtractedPhrase, ExtractedStep, StructuredIntent


class IntentTransformer:
    """Transforms StructuredIntent from Relational Agent to StatusActionFlow.

    This transformer does ONE thing: add missing fields.
    - Pass through all actions and widgets (no filtering)
    - Add defaults for category, color, order, focus view settings
    """

    # Default colors by category
    DEFAULT_COLORS: dict[StatusCategory, str] = {
        StatusCategory.PENDING: "#6B7280",
        StatusCategory.IN_PROGRESS: "#3B82F6",
        StatusCategory.ON_HOLD: "#F59E0B",
        StatusCategory.COMPLETED: "#059669",
        StatusCategory.CANCELLED: "#EF4444",
    }

    # FieldPulse status types (maps to Status Type column)
    STATUS_TYPES: dict[StatusCategory, str] = {
        StatusCategory.PENDING: "New",
        StatusCategory.IN_PROGRESS: "In Progress",
        StatusCategory.ON_HOLD: "In Progress",
        StatusCategory.COMPLETED: "completed",  # lowercase per FieldPulse format
        StatusCategory.CANCELLED: "completed",
    }

    # Default icons by category
    DEFAULT_ICONS: dict[StatusCategory, str] = {
        StatusCategory.PENDING: "clipboard",
        StatusCategory.IN_PROGRESS: "sparkles",
        StatusCategory.ON_HOLD: "pause",
        StatusCategory.COMPLETED: "check",
        StatusCategory.CANCELLED: "x",
    }

    # Role name mappings
    ROLE_MAPPINGS: dict[str, UserRole] = {
        "tech": UserRole.TECHNICIAN,
        "technician": UserRole.TECHNICIAN,
        "dispatcher": UserRole.DISPATCHER,
        "office": UserRole.OFFICE_STAFF,
        "office staff": UserRole.OFFICE_STAFF,
        "manager": UserRole.MANAGER,
        "admin": UserRole.ADMIN,
        "sales": UserRole.SALES,
        "service agent": UserRole.SERVICE_AGENT,
    }

    def transform(self, intent: StructuredIntent) -> StatusActionFlow:
        """Transform StructuredIntent to StatusActionFlow.

        Args:
            intent: The structured intent from Relational Agent

        Returns:
            StatusActionFlow ready for Excel generation
        """
        total_steps = len(intent.steps)
        statuses = []

        for step in intent.steps:
            status = self._build_status(step, total_steps)
            statuses.append(status)

        # Link statuses (next/previous)
        self._link_statuses(statuses)

        return StatusActionFlow(
            workflow_name=intent.workflow_name,  # Custom Job Status Workflow Name
            name=intent.workflow_name,  # Status Action Flow Name (same for now)
            description=intent.workflow_description,
            job_types=intent.job_types or intent.metadata.job_types,
            statuses=statuses,
        )

    def _build_status(self, step: ExtractedStep, total_steps: int) -> Status:
        """Build a Status from an ExtractedStep."""
        # Infer category from sequence position
        category = self._infer_category(step.sequence, total_steps, step.category_hint)

        return Status(
            name=step.step_name,
            sequence=step.sequence,
            # ADD MISSING:
            category=category,
            color=self.DEFAULT_COLORS[category],
            icon=self.DEFAULT_ICONS[category],
            status_type=self.STATUS_TYPES[category],
            user_role=self._map_role(step.role_mentioned or step.role_hint),
            # PASS THROUGH (just format convert):
            action_buttons=self._build_actions(step.action_phrases),
            widgets=self._build_widgets(step.information_needs),
            status_instructions=step.instructions_raw or "",
            # ADD DEFAULTS:
            display_action_menu=True,
            ability_to_change_status=(category != StatusCategory.COMPLETED),
            focus_view_enabled=True,
            restrict_to_focus_view=(step.sequence > 1),
        )

    def _build_actions(self, phrases: list[ExtractedPhrase]) -> list[ActionButton]:
        """Build action buttons. NO VALIDATION. Just format convert."""
        actions = []
        for i, phrase in enumerate(phrases):
            if not phrase.suggested_type:
                continue

            # action:take_photo → "Take Photo"
            action_str = self._format_type(phrase.suggested_type)

            # Create label from phrase (title case, max 50 chars)
            label = phrase.phrase.strip().title()
            if len(label) > 50:
                label = label[:47] + "..."

            actions.append(ActionButton(
                action=action_str,
                label=label,
                order=i,
                required=phrase.requires_template,
                template_id=phrase.template_hint if phrase.requires_template else None,
            ))

        return actions

    def _build_widgets(self, phrases: list[ExtractedPhrase]) -> list[Widget]:
        """Build widgets. NO VALIDATION. Just format convert + add core widgets."""
        widgets = []

        # Add core widgets first
        core_widgets = ["Job Title", "Job Status", "Status Instructions"]
        for i, wt in enumerate(core_widgets):
            widgets.append(Widget(widget_type=wt, order=i, collapsed=False))

        # Add widgets from information_needs
        for phrase in phrases:
            if not phrase.suggested_type:
                continue

            # widget:job_notes → "Job Notes"
            widget_str = self._format_type(phrase.suggested_type)

            # Skip if already added (core widgets)
            if any(w.widget_type == widget_str for w in widgets):
                continue

            widgets.append(Widget(
                widget_type=widget_str,
                order=len(widgets),
                collapsed=False,
            ))

        # Add Action Buttons widget at the end
        widgets.append(Widget(
            widget_type="Action Buttons",
            order=len(widgets),
            collapsed=False,
        ))

        return widgets

    def _format_type(self, suggested_type: str) -> str:
        """Format suggested_type to display string.

        action:take_photo → "Take Photo"
        widget:job_notes → "Job Notes"
        """
        if ":" in suggested_type:
            _, type_part = suggested_type.split(":", 1)
        else:
            type_part = suggested_type

        # Replace underscores with spaces and title case
        return type_part.replace("_", " ").title()

    def _infer_category(
        self,
        sequence: int,
        total_steps: int,
        category_hint: Optional[str],
    ) -> StatusCategory:
        """Infer status category from sequence position or hint."""
        # Use hint if provided
        if category_hint:
            hint_lower = category_hint.lower()
            for cat in StatusCategory:
                if cat.value.lower() == hint_lower or cat.name.lower() == hint_lower:
                    return cat

        # Infer from position
        if sequence == 1:
            return StatusCategory.PENDING
        elif sequence == total_steps:
            return StatusCategory.COMPLETED
        else:
            return StatusCategory.IN_PROGRESS

    def _map_role(self, role_str: Optional[str]) -> UserRole:
        """Map role string to UserRole enum."""
        if not role_str:
            return UserRole.SERVICE_AGENT

        role_lower = role_str.lower().strip()

        # Check mappings
        if role_lower in self.ROLE_MAPPINGS:
            return self.ROLE_MAPPINGS[role_lower]

        # Check enum values directly
        for role in UserRole:
            if role.value.lower() == role_lower or role.name.lower() == role_lower:
                return role

        return UserRole.SERVICE_AGENT

    def _link_statuses(self, statuses: list[Status]) -> None:
        """Link statuses with next/previous pointers."""
        for i, status in enumerate(statuses):
            if i > 0:
                status.previous_status = statuses[i - 1].name
            if i < len(statuses) - 1:
                status.next_status = statuses[i + 1].name

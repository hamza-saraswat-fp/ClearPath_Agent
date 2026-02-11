"""Transformer from StructuredIntent to StatusActionFlow.

Pass through Relational Agent output + add missing fields + apply safety-net
fixes for common LLM output issues (duplicate actions, misplaced Change Status
buttons, descriptive button names, missing instructions).
"""

import logging
from typing import Optional

from ..models.entities import ActionButton, Status, StatusActionFlow, Widget
from ..models.enums import StatusCategory, UserRole
from ..models.intent_schemas import ExtractedPhrase, ExtractedStep, StructuredIntent

logger = logging.getLogger(__name__)


class IntentTransformer:
    """Transforms StructuredIntent from Relational Agent to StatusActionFlow.

    Responsibilities:
    - Pass through all actions and widgets
    - Add defaults for category, color, order, focus view settings
    - Deduplicate action buttons per status
    - Clean button labels using canonical names
    - Fix misplaced Change Status buttons
    - Generate fallback status instructions when missing
    """

    # Canonical button labels keyed by normalized action type.
    # These provide clean, imperative labels when the LLM produces
    # descriptive or verbose button names.
    CANONICAL_LABELS: dict[str, str] = {
        "job timesheet clock in / out": "Clock In/Out",
        "job timesheet clock": "Clock In/Out",
        "general timesheet clock in / out": "Clock In/Out",
        "general timesheet clock": "Clock In/Out",
        "send trip tracking sms to customer": "Send On-The-Way Text",
        "send trip tracking sms": "Send On-The-Way Text",
        "send customer communication": "Send Customer Text",
        "take photo": "Take Photos",
        "upload photo": "Upload Photos",
        "fill form": "Fill Out Form",
        "fill out form": "Fill Out Form",
        "create estimate": "Create Estimate",
        "create invoice": "Create Invoice",
        "create project": "Create Project",
        "create purchase order": "Create Purchase Order",
        "create maintenance agreement": "Create Maintenance Agreement",
        "create asset": "Create Asset",
        "create pdf form": "Create PDF Form",
        "create next occurrence": "Schedule Next Visit",
        "create site visit": "Create Site Visit",
        "create subtask": "Create Subtask",
        "create subtask series": "Create Subtask Series",
        "create material list": "Create Material List",
        "add comment": "Add Comment",
        "set a reminder": "Set Reminder",
        "attach file/photo": "Attach File",
        "attach photo/file": "Attach Photo",
        "generate job report": "Generate Job Report",
        "generate asset report": "Generate Asset Report",
        "duplicate": "Duplicate Job",
        "archive": "Archive Job",
        "change status": "Change Status",
    }

    # Filler phrases to strip from button labels
    LABEL_FILLER = [
        " to the customer",
        " for the customer",
        " to the homeowner",
        " for the job",
        " in the system",
        " on the job",
        " to the office",
        " for the tech",
    ]

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

        # Post-processing: fix misplaced Change Status buttons
        self._fix_change_status_placement(statuses)

        # Post-processing: generate fallback instructions for statuses missing them
        for status in statuses:
            if not status.status_instructions:
                status.status_instructions = self._generate_fallback_instructions(status)

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
        """Build action buttons with dedup and clean labels."""
        actions = []
        seen_actions: set[str] = set()

        for phrase in phrases:
            if not phrase.suggested_type:
                continue

            # action:take_photo → "Take Photo"
            action_str = self._format_type(phrase.suggested_type)

            # Deduplicate by normalized action type
            action_key = action_str.lower().strip()
            if action_key in seen_actions:
                logger.warning(
                    "Skipping duplicate action '%s' (phrase: '%s')",
                    action_str, phrase.phrase,
                )
                continue
            seen_actions.add(action_key)

            # Change Status buttons need special handling: always capture
            # the target status in template_id and format label with target
            is_change_status = "change status" in action_key
            if is_change_status:
                target = self._extract_status_target_from_phrase(phrase.phrase)
                template_id = phrase.template_hint or target
                label = f"Change Status to {template_id}" if template_id else "Change Status"
            else:
                template_id = phrase.template_hint if phrase.requires_template else None
                label = self._clean_button_label(phrase.phrase, action_str)

            actions.append(ActionButton(
                action=action_str,
                label=label,
                order=len(actions),
                required=phrase.requires_template,
                template_id=template_id,
            ))

        return actions

    @staticmethod
    def _extract_status_target_from_phrase(phrase: str) -> Optional[str]:
        """Extract the target status name from a 'change status to X' phrase."""
        phrase_lower = phrase.lower().strip()
        for prefix in ["change status to ", "change status: ", "move to "]:
            if phrase_lower.startswith(prefix):
                return phrase[len(prefix):].strip().title()
        return None

    def _clean_button_label(self, raw_phrase: str, action_type: str) -> str:
        """Produce a clean, imperative button label.

        Prefers the canonical label for known action types. Falls back to
        cleaning the raw phrase by stripping filler and title-casing.
        """
        # Check canonical labels by normalized action type
        action_key = action_type.lower().strip()
        if action_key in self.CANONICAL_LABELS:
            return self.CANONICAL_LABELS[action_key]

        # Fallback: clean the raw phrase
        label = raw_phrase.strip()

        # Strip common filler phrases
        label_lower = label.lower()
        for filler in self.LABEL_FILLER:
            if label_lower.endswith(filler):
                label = label[: len(label) - len(filler)]
                label_lower = label.lower()

        # Title case and cap at 50 chars
        label = label.strip().title()
        if len(label) > 50:
            label = label[:47] + "..."

        return label

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

    def _is_change_status_action(self, button: ActionButton) -> bool:
        """Check if an action button is a Change Status action."""
        return "change status" in button.action.lower()

    def _parse_change_status_target(self, button: ActionButton) -> Optional[str]:
        """Extract the target status name from a Change Status button.

        Checks template_id first, then parses from the label.
        """
        if button.template_id:
            return button.template_id

        # Parse from label: "Change Status to Heading to the Job" → "Heading to the Job"
        label_lower = button.label.lower()
        for prefix in ["change status to ", "change status: "]:
            if label_lower.startswith(prefix):
                return button.label[len(prefix):].strip()

        return None

    def _fix_change_status_placement(self, statuses: list[Status]) -> None:
        """Fix misplaced Change Status buttons.

        Detects Change Status buttons whose target matches the status they're
        on (meaning they were placed on the target instead of the source) and
        moves them to the previous status.

        Also ensures every non-terminal status has at least one Change Status
        button pointing to next_status as a fallback.
        """
        status_by_name: dict[str, Status] = {s.name.lower(): s for s in statuses}

        # Pass 1: Move misplaced Change Status buttons to previous status
        for i, status in enumerate(statuses):
            buttons_to_move = []
            buttons_to_keep = []

            for button in status.action_buttons:
                if not self._is_change_status_action(button):
                    buttons_to_keep.append(button)
                    continue

                target = self._parse_change_status_target(button)
                if target and target.lower() == status.name.lower() and i > 0:
                    # Misplaced: target matches current status → move to previous
                    logger.info(
                        "Moving misplaced 'Change Status to %s' from '%s' to '%s'",
                        target, status.name, statuses[i - 1].name,
                    )
                    buttons_to_move.append(button)
                else:
                    buttons_to_keep.append(button)

            # Update current status buttons
            status.action_buttons = buttons_to_keep

            # Add moved buttons to previous status
            if buttons_to_move and i > 0:
                prev_status = statuses[i - 1]
                for button in buttons_to_move:
                    button.order = len(prev_status.action_buttons)
                    prev_status.action_buttons.append(button)

        # Pass 2: Ensure non-terminal statuses have a Change Status button
        for status in statuses:
            if not status.next_status:
                continue  # Terminal status, no need for Change Status

            has_change_status = any(
                self._is_change_status_action(b) for b in status.action_buttons
            )
            if not has_change_status:
                label = f"Change Status to {status.next_status}"
                status.action_buttons.append(ActionButton(
                    action="Change Status",
                    label=label,
                    order=len(status.action_buttons),
                    required=False,
                    template_id=status.next_status,
                ))

    def _generate_fallback_instructions(self, status: Status) -> str:
        """Generate status instructions from the status's action buttons.

        Builds a numbered list from button labels, providing a basic
        step-by-step checklist when the LLM didn't produce instructions.
        """
        if not status.action_buttons:
            return ""

        steps = []
        for button in sorted(status.action_buttons, key=lambda b: b.order):
            steps.append(button.label)

        return "\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1))

"""Configuration Validator Service.

Validates complete StatusActionFlow configurations before Excel export.
Checks for ClearPath constraints, best practices, and logical consistency.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..models.entities import ActionButton, Status, StatusActionFlow, Widget
from ..models.enums import ActionButtonType, StatusCategory, WidgetType

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""

    ERROR = "error"  # Blocking - prevents Excel generation
    WARNING = "warning"  # Non-blocking - user should review
    INFO = "info"  # Informational - suggestions


@dataclass
class ValidationIssue:
    """A single validation issue."""

    severity: ValidationSeverity
    code: str
    message: str
    location: Optional[str] = None  # e.g., "Status: On Site", "Action: Clock In"
    suggestion: Optional[str] = None

    def __str__(self) -> str:
        loc = f" [{self.location}]" if self.location else ""
        return f"[{self.severity.value.upper()}]{loc} {self.message}"


@dataclass
class ValidationResult:
    """Result of validating a configuration."""

    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def info(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.INFO]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    @property
    def info_count(self) -> int:
        return len(self.info)

    def add_error(
        self,
        code: str,
        message: str,
        location: Optional[str] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.ERROR,
            code=code,
            message=message,
            location=location,
            suggestion=suggestion,
        ))
        self.is_valid = False

    def add_warning(
        self,
        code: str,
        message: str,
        location: Optional[str] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.WARNING,
            code=code,
            message=message,
            location=location,
            suggestion=suggestion,
        ))

    def add_info(
        self,
        code: str,
        message: str,
        location: Optional[str] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        self.issues.append(ValidationIssue(
            severity=ValidationSeverity.INFO,
            code=code,
            message=message,
            location=location,
            suggestion=suggestion,
        ))


# ClearPath constraints
MAX_ACTION_BUTTONS_PER_STATUS = 10
MAX_STATUSES_PER_WORKFLOW = 50
MAX_STATUS_NAME_LENGTH = 100
MAX_INSTRUCTION_LENGTH = 2000

# Actions that require templates
TEMPLATE_REQUIRED_ACTIONS = {
    ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
    ActionButtonType.CREATE_ESTIMATE,
    ActionButtonType.CREATE_INVOICE,
    ActionButtonType.SEND_ESTIMATE,
    ActionButtonType.SEND_INVOICE,
}

# Actions that require forms
FORM_REQUIRED_ACTIONS = {
    ActionButtonType.FILL_FORM,
}

# Action to Widget compatibility rules
# Maps action types to widgets that should be present to display action results
ACTION_WIDGET_COMPATIBILITY = {
    ActionButtonType.CREATE_INVOICE: WidgetType.INVOICES,
    ActionButtonType.CREATE_ESTIMATE: WidgetType.ESTIMATES,
    ActionButtonType.COLLECT_PAYMENT: WidgetType.PAYMENTS,
    ActionButtonType.COLLECT_SIGNATURE: WidgetType.SIGNATURES,
    ActionButtonType.FILL_FORM: WidgetType.FORMS,
    ActionButtonType.TAKE_PHOTO: WidgetType.FILES_PHOTOS,
    ActionButtonType.ADD_MATERIAL: WidgetType.MATERIALS,
    ActionButtonType.CREATE_ASSET: WidgetType.ASSETS,
    ActionButtonType.UPDATE_ASSET: WidgetType.ASSETS,
    ActionButtonType.CLOCK_IN_OUT: WidgetType.TIMESHEETS,
}


class ConfigValidator:
    """Validates StatusActionFlow configurations.

    Checks for:
    - ClearPath hard constraints (max buttons, required fields)
    - Logical consistency (status flow, sequences)
    - Best practices (widget ordering, instructions format)
    """

    def __init__(self):
        """Initialize the config validator."""
        pass

    def validate_config(
        self,
        config: StatusActionFlow,
        check_best_practices: bool = True,
    ) -> ValidationResult:
        """Validate a complete StatusActionFlow configuration.

        Args:
            config: The configuration to validate
            check_best_practices: Whether to check best practices

        Returns:
            ValidationResult with all issues found
        """
        result = ValidationResult(is_valid=True)

        # Validate workflow level
        self._validate_workflow(config, result)

        # Validate each status
        for status in config.statuses:
            self._validate_status(status, result)

            # Validate action buttons
            self._validate_action_buttons(status, result)

            # Validate widgets
            self._validate_widgets(status, result)

            # Validate widget compatibility with actions
            self._validate_widget_compatibility(status, result)

        # Validate status flow
        self._validate_status_flow(config, result)

        # Check best practices if enabled
        if check_best_practices:
            self._check_best_practices(config, result)

        logger.info(
            f"Validation complete: {result.error_count} errors, "
            f"{result.warning_count} warnings"
        )

        return result

    def _validate_workflow(
        self,
        config: StatusActionFlow,
        result: ValidationResult,
    ) -> None:
        """Validate workflow-level constraints.

        Args:
            config: The configuration
            result: ValidationResult to add issues to
        """
        # Check workflow name
        if not config.name or not config.name.strip():
            result.add_error(
                code="WORKFLOW_NAME_REQUIRED",
                message="Workflow name is required",
                suggestion="Provide a name for the workflow",
            )

        # Check status count
        if len(config.statuses) > MAX_STATUSES_PER_WORKFLOW:
            result.add_error(
                code="TOO_MANY_STATUSES",
                message=f"Workflow has {len(config.statuses)} statuses, "
                        f"maximum is {MAX_STATUSES_PER_WORKFLOW}",
                suggestion="Reduce the number of statuses or split into multiple workflows",
            )

        if len(config.statuses) == 0:
            result.add_error(
                code="NO_STATUSES",
                message="Workflow must have at least one status",
                suggestion="Add at least one status to the workflow",
            )

    def _validate_status(
        self,
        status: Status,
        result: ValidationResult,
    ) -> None:
        """Validate a single status.

        Args:
            status: The status to validate
            result: ValidationResult to add issues to
        """
        location = f"Status: {status.name}"

        # Check status name
        if not status.name or not status.name.strip():
            result.add_error(
                code="STATUS_NAME_REQUIRED",
                message="Status name is required",
                location=location,
            )

        if len(status.name) > MAX_STATUS_NAME_LENGTH:
            result.add_error(
                code="STATUS_NAME_TOO_LONG",
                message=f"Status name exceeds {MAX_STATUS_NAME_LENGTH} characters",
                location=location,
                suggestion="Shorten the status name",
            )

        # Check sequence
        if status.sequence < 1:
            result.add_error(
                code="INVALID_SEQUENCE",
                message=f"Status sequence must be >= 1, got {status.sequence}",
                location=location,
            )

        # Check instructions length
        if len(status.status_instructions) > MAX_INSTRUCTION_LENGTH:
            result.add_error(
                code="INSTRUCTIONS_TOO_LONG",
                message=f"Status instructions exceed {MAX_INSTRUCTION_LENGTH} characters",
                location=location,
                suggestion="Shorten the instructions",
            )

        # Check color format
        if status.color and not status.color.startswith("#"):
            result.add_warning(
                code="INVALID_COLOR_FORMAT",
                message=f"Color '{status.color}' should be in hex format (#RRGGBB)",
                location=location,
            )

    def _validate_action_buttons(
        self,
        status: Status,
        result: ValidationResult,
    ) -> None:
        """Validate action buttons for a status.

        Args:
            status: The status containing the buttons
            result: ValidationResult to add issues to
        """
        location = f"Status: {status.name}"

        # Check button count
        if len(status.action_buttons) > MAX_ACTION_BUTTONS_PER_STATUS:
            result.add_error(
                code="TOO_MANY_BUTTONS",
                message=f"Status has {len(status.action_buttons)} action buttons, "
                        f"maximum is {MAX_ACTION_BUTTONS_PER_STATUS}",
                location=location,
                suggestion="Remove some action buttons or split into multiple statuses",
            )

        # Check each button
        seen_labels = set()
        for button in status.action_buttons:
            btn_location = f"Status: {status.name}, Button: {button.label}"

            # Check for duplicate labels
            if button.label.lower() in seen_labels:
                result.add_warning(
                    code="DUPLICATE_BUTTON_LABEL",
                    message=f"Duplicate button label '{button.label}'",
                    location=btn_location,
                    suggestion="Use unique labels for each button",
                )
            seen_labels.add(button.label.lower())

            # Check template requirements
            if button.action in TEMPLATE_REQUIRED_ACTIONS:
                if not button.template_id:
                    result.add_error(
                        code="TEMPLATE_REQUIRED",
                        message=f"Action '{button.action.value}' requires a template_id",
                        location=btn_location,
                        suggestion="Assign a template to this action button",
                    )

            # Check form requirements
            if button.action in FORM_REQUIRED_ACTIONS:
                if not button.form_id:
                    result.add_error(
                        code="FORM_REQUIRED",
                        message=f"Action '{button.action.value}' requires a form_id",
                        location=btn_location,
                        suggestion="Assign a form to this action button",
                    )

            # Check label length
            if len(button.label) > 50:
                result.add_warning(
                    code="BUTTON_LABEL_TOO_LONG",
                    message=f"Button label exceeds 50 characters",
                    location=btn_location,
                    suggestion="Shorten the button label",
                )

    def _validate_widgets(
        self,
        status: Status,
        result: ValidationResult,
    ) -> None:
        """Validate widgets for a status.

        Args:
            status: The status containing the widgets
            result: ValidationResult to add issues to
        """
        location = f"Status: {status.name}"

        # Check for duplicate widgets
        widget_types = [w.widget_type for w in status.widgets]
        seen_types = set()
        for widget_type in widget_types:
            if widget_type in seen_types:
                result.add_warning(
                    code="DUPLICATE_WIDGET",
                    message=f"Duplicate widget '{widget_type.value}'",
                    location=location,
                    suggestion="Remove duplicate widgets",
                )
            seen_types.add(widget_type)

        # Check for action buttons widget if actions defined
        if status.action_buttons:
            has_action_buttons_widget = any(
                w.widget_type == WidgetType.ACTION_BUTTONS
                for w in status.widgets
            )
            if not has_action_buttons_widget:
                result.add_warning(
                    code="MISSING_ACTION_BUTTONS_WIDGET",
                    message="Status has action buttons but no Action Buttons widget",
                    location=location,
                    suggestion="Add the Action Buttons widget to display the buttons",
                )

    def _validate_widget_compatibility(
        self,
        status: Status,
        result: ValidationResult,
    ) -> None:
        """Check that action buttons have corresponding widgets.

        Args:
            status: The status containing the buttons and widgets
            result: ValidationResult to add issues to
        """
        location = f"Status: {status.name}"
        widget_types = {w.widget_type for w in status.widgets}

        for button in status.action_buttons:
            expected_widget = ACTION_WIDGET_COMPATIBILITY.get(button.action)
            if expected_widget and expected_widget not in widget_types:
                result.add_info(
                    code="MISSING_COMPATIBLE_WIDGET",
                    message=f"Action '{button.label}' should have '{expected_widget.value}' widget",
                    location=location,
                    suggestion=f"Add {expected_widget.value} widget to display action results",
                )

    def _validate_status_flow(
        self,
        config: StatusActionFlow,
        result: ValidationResult,
    ) -> None:
        """Validate status flow logic.

        Args:
            config: The configuration
            result: ValidationResult to add issues to
        """
        # Early return if no statuses - already flagged in _validate_workflow
        if not config.statuses:
            return

        # Check for duplicate status names
        seen_names: set[str] = set()
        for status in config.statuses:
            name_lower = status.name.lower()
            if name_lower in seen_names:
                result.add_error(
                    code="DUPLICATE_STATUS_NAME",
                    message=f"Duplicate status name '{status.name}'",
                    suggestion="Each status must have a unique name",
                )
            seen_names.add(name_lower)

        status_names = {s.name.lower() for s in config.statuses}
        sequences = [s.sequence for s in config.statuses]

        # Check for unique sequences
        if len(sequences) != len(set(sequences)):
            result.add_error(
                code="DUPLICATE_SEQUENCES",
                message="Status sequences must be unique",
                suggestion="Ensure each status has a unique sequence number",
            )

        # Check for gaps in sequences
        sorted_seqs = sorted(sequences)
        expected = list(range(sorted_seqs[0], sorted_seqs[-1] + 1))
        if sorted_seqs != expected:
            result.add_warning(
                code="SEQUENCE_GAPS",
                message="Status sequences have gaps",
                suggestion="Use consecutive sequence numbers (1, 2, 3, ...)",
            )

        # Validate next_status/previous_status references
        for status in config.statuses:
            if status.next_status:
                if status.next_status.lower() not in status_names:
                    result.add_error(
                        code="INVALID_NEXT_STATUS",
                        message=f"next_status '{status.next_status}' does not exist",
                        location=f"Status: {status.name}",
                    )

            if status.previous_status:
                if status.previous_status.lower() not in status_names:
                    result.add_error(
                        code="INVALID_PREVIOUS_STATUS",
                        message=f"previous_status '{status.previous_status}' does not exist",
                        location=f"Status: {status.name}",
                    )

    def _check_best_practices(
        self,
        config: StatusActionFlow,
        result: ValidationResult,
    ) -> None:
        """Check ClearPath Tier 1 best practices.

        Args:
            config: The configuration
            result: ValidationResult to add issues to
        """
        for status in config.statuses:
            location = f"Status: {status.name}"

            # Check: Action Buttons should be last widget
            if status.widgets:
                last_widget = status.widgets[-1]
                action_buttons_widgets = [
                    w for w in status.widgets
                    if w.widget_type == WidgetType.ACTION_BUTTONS
                ]
                if action_buttons_widgets:
                    if last_widget.widget_type != WidgetType.ACTION_BUTTONS:
                        result.add_info(
                            code="ACTION_BUTTONS_NOT_LAST",
                            message="Action Buttons widget should be last for thumb accessibility",
                            location=location,
                            suggestion="Move Action Buttons to the last position",
                        )

            # Check: Instructions should be numbered
            if status.status_instructions:
                lines = status.status_instructions.strip().split("\n")
                if len(lines) > 1:
                    numbered = all(
                        line.strip().startswith(str(i))
                        for i, line in enumerate(lines, 1)
                        if line.strip()
                    )
                    if not numbered:
                        result.add_info(
                            code="INSTRUCTIONS_NOT_NUMBERED",
                            message="Instructions should be numbered (1., 2., 3., ...)",
                            location=location,
                            suggestion="Format instructions as a numbered list",
                        )

            # Check: Focus View should be enabled for field statuses
            if status.category == StatusCategory.IN_PROGRESS:
                if not status.focus_view_enabled:
                    result.add_info(
                        code="FOCUS_VIEW_DISABLED",
                        message="Focus View should be enabled for in-progress statuses",
                        location=location,
                        suggestion="Enable Focus View for better field technician experience",
                    )

            # Check: Core widgets should be present
            widget_types = {w.widget_type for w in status.widgets}
            core_widgets = {
                WidgetType.JOB_TITLE,
                WidgetType.JOB_STATUS,
                WidgetType.STATUS_INSTRUCTIONS,
            }
            missing_core = core_widgets - widget_types
            if missing_core:
                missing_names = ", ".join(w.value for w in missing_core)
                result.add_info(
                    code="MISSING_CORE_WIDGETS",
                    message=f"Missing core widgets: {missing_names}",
                    location=location,
                    suggestion="Add core widgets for better user experience",
                )


def validate_action_button_count(buttons: list[ActionButton]) -> bool:
    """Quick check if button count is within limits.

    Args:
        buttons: List of action buttons

    Returns:
        True if within limits
    """
    return len(buttons) <= MAX_ACTION_BUTTONS_PER_STATUS


def validate_template_requirements(button: ActionButton) -> list[str]:
    """Check template/form requirements for a button.

    Args:
        button: The action button to check

    Returns:
        List of missing requirements
    """
    missing = []

    if button.action in TEMPLATE_REQUIRED_ACTIONS and not button.template_id:
        missing.append("template_id")

    if button.action in FORM_REQUIRED_ACTIONS and not button.form_id:
        missing.append("form_id")

    return missing

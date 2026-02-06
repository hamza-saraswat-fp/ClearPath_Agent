"""Config to Excel Schema Converter.

Transforms StatusActionFlow configurations into ExcelImportTemplate
format matching FieldPulse ClearPath Import Template exactly.
"""

import logging
from pathlib import Path
from typing import Optional

from ..models.entities import Status, StatusActionFlow
from ..models.excel_schemas import (
    ActionButtonRow,
    ExcelImportTemplate,
    FocusViewRow,
    JobCustomStatusRow,
    StatusDefinition,
)

logger = logging.getLogger(__name__)


class ConfigToExcelConverter:
    """Converts StatusActionFlow to ExcelImportTemplate (FieldPulse format).

    The ClearPath import template has 3 tabs:
    1. Job Custom Status - HORIZONTAL layout (one row per workflow)
    2. Action Buttons - One row per button per status per role
    3. Focus View + Status Instruction - One row per status per role
    """

    # FieldPulse role name mappings
    ROLE_DISPLAY_NAMES = {
        "Technician": "Service Agent",
        "Service Agent": "Service Agent",
        "Dispatcher": "Admin",
        "Manager": "Team Manager",
        "Admin": "Admin",
        "Office Staff": "Admin",
        "Sales": "Service Agent",
    }

    def convert(
        self,
        config: StatusActionFlow,
    ) -> ExcelImportTemplate:
        """Convert a StatusActionFlow to ExcelImportTemplate.

        Args:
            config: The StatusActionFlow configuration

        Returns:
            ExcelImportTemplate ready for Excel generation (FieldPulse format)
        """
        logger.info(f"Converting config '{config.name}' to Excel template")

        # Tab 1: Job Custom Status (HORIZONTAL - one row with all statuses)
        status_row = self._generate_status_row(config)

        # Tab 2: Action Buttons
        button_rows = self._generate_button_rows(config)

        # Tab 3: Focus View + Status Instruction
        focus_rows = self._generate_focus_rows(config)

        template = ExcelImportTemplate(
            job_custom_statuses=[status_row],
            action_buttons=button_rows,
            focus_view=focus_rows,
        )

        logger.info(
            f"Generated Excel template: 1 workflow row, "
            f"{len(button_rows)} button rows, {len(focus_rows)} focus view rows"
        )

        return template

    def _generate_status_row(
        self,
        config: StatusActionFlow,
    ) -> JobCustomStatusRow:
        """Generate the Job Custom Status row (HORIZONTAL format).

        One row contains ALL statuses for the workflow.

        Args:
            config: The StatusActionFlow configuration

        Returns:
            JobCustomStatusRow with all statuses
        """
        statuses = []
        for status in config.statuses:
            statuses.append(StatusDefinition(
                name=status.name,
                status_type=status.status_type,
                color=status.color,
                icon=status.icon,
            ))

        return JobCustomStatusRow(
            workflow_name=config.workflow_name,
            statuses=statuses,
        )

    def _generate_button_rows(
        self,
        config: StatusActionFlow,
    ) -> list[ActionButtonRow]:
        """Generate rows for the Action Buttons tab.

        One row per button per status.

        Args:
            config: The StatusActionFlow configuration

        Returns:
            List of ActionButtonRow objects
        """
        rows = []

        for status in config.statuses:
            role_display = self._get_role_display(status.user_role.value)

            for button in status.action_buttons:
                # Combine form_id and template_id into action_option
                action_option = button.template_id or button.form_id or None

                row = ActionButtonRow(
                    workflow_name=config.workflow_name,
                    action_flow_name=config.name,
                    job_status_name=status.name,
                    user_role=role_display,
                    button_action=button.action,
                    action_option=action_option,
                    action_button_name=button.label,
                )
                rows.append(row)

        return rows

    def _generate_focus_rows(
        self,
        config: StatusActionFlow,
    ) -> list[FocusViewRow]:
        """Generate rows for the Focus View + Status Instruction tab.

        One row per status.

        Args:
            config: The StatusActionFlow configuration

        Returns:
            List of FocusViewRow objects
        """
        rows = []

        for status in config.statuses:
            role_display = self._get_role_display(status.user_role.value)

            # Build comma-separated widget list (Focus View Layout)
            widget_list = ", ".join(
                w.widget_type for w in sorted(status.widgets, key=lambda x: x.order)
            )

            row = FocusViewRow(
                workflow_name=config.workflow_name,
                action_flow_name=config.name,
                job_status_name=status.name,
                user_role=role_display,
                status_instructions=status.status_instructions or "",
                display_action_menu=self._format_boolean(status.display_action_menu),
                ability_to_change_status=self._format_boolean(status.ability_to_change_status),
                focus_view_enabled=self._format_boolean(status.focus_view_enabled),
                focus_view_layout=widget_list,
                restrict_to_focus_view=self._format_boolean(status.restrict_to_focus_view),
            )
            rows.append(row)

        return rows

    def _get_role_display(self, role: str) -> str:
        """Convert internal role to FieldPulse display name.

        Args:
            role: Internal role name

        Returns:
            FieldPulse role display name
        """
        return self.ROLE_DISPLAY_NAMES.get(role, "Service Agent")

    def _format_boolean(self, value: bool) -> str:
        """Format boolean as FieldPulse T/F string.

        Args:
            value: Boolean value

        Returns:
            "T" or "F"
        """
        return "T" if value else "F"

    def convert_and_generate(
        self,
        config: StatusActionFlow,
        output_path: Optional[Path] = None,
        overwrite: bool = False,
    ) -> Path:
        """Convert config to Excel template and generate the Excel file.

        This is a convenience method that chains the full pipeline:
        convert → generate Excel file.

        Args:
            config: The StatusActionFlow configuration to convert
            output_path: Optional path for the output Excel file
            overwrite: Whether to overwrite existing files

        Returns:
            Path to the generated Excel file

        Raises:
            ValueError: If conversion fails
            IOError: If file cannot be written
        """
        # Import here to avoid circular dependency
        from .excel_generator import ExcelGenerator

        # Convert to Excel template
        template = self.convert(config)

        # Generate Excel file
        generator = ExcelGenerator()
        return generator.generate(
            template,
            output_path=output_path,
            overwrite=overwrite,
            validate_first=True,
        )

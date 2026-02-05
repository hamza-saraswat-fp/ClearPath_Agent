"""Config to Excel Schema Converter.

Transforms StatusActionFlow configurations into ExcelImportTemplate
format ready for Phase 4 (Excel Generation).
"""

import logging
from pathlib import Path
from typing import Optional

from ..models.entities import Status, StatusActionFlow
from ..models.enums import UserRole
from ..models.excel_schemas import (
    ActionButtonRow,
    ExcelImportTemplate,
    FocusViewRow,
    JobCustomStatusRow,
)

logger = logging.getLogger(__name__)


class ConfigToExcelConverter:
    """Converts StatusActionFlow to ExcelImportTemplate.

    The ClearPath import template has 3 tabs:
    1. Job Custom Status - Basic status definitions
    2. Action Buttons - Action buttons per status per role
    3. Focus View - Widgets and settings per status per role
    """

    def __init__(
        self,
        default_roles: Optional[list[UserRole]] = None,
        expand_to_all_roles: bool = False,
    ):
        """Initialize the converter.

        Args:
            default_roles: Default roles to expand to if expand_to_all_roles is True
            expand_to_all_roles: Whether to create rows for all roles
        """
        self.default_roles = default_roles or [
            UserRole.SERVICE_AGENT,
            UserRole.MANAGER,
            UserRole.ADMIN,
        ]
        self.expand_to_all_roles = expand_to_all_roles

    def convert(
        self,
        config: StatusActionFlow,
    ) -> ExcelImportTemplate:
        """Convert a StatusActionFlow to ExcelImportTemplate.

        Args:
            config: The StatusActionFlow configuration

        Returns:
            ExcelImportTemplate ready for Excel generation
        """
        logger.info(f"Converting config '{config.name}' to Excel template")

        # Tab 1: Job Custom Status
        status_rows = self._generate_status_rows(config)

        # Tab 2: Action Buttons
        button_rows = self._generate_button_rows(config)

        # Tab 3: Focus View
        focus_rows = self._generate_focus_rows(config)

        template = ExcelImportTemplate(
            job_custom_statuses=status_rows,
            action_buttons=button_rows,
            focus_view=focus_rows,
        )

        logger.info(
            f"Generated Excel template: {len(status_rows)} statuses, "
            f"{len(button_rows)} button rows, {len(focus_rows)} focus view rows"
        )

        return template

    def _generate_status_rows(
        self,
        config: StatusActionFlow,
    ) -> list[JobCustomStatusRow]:
        """Generate rows for the Job Custom Status tab.

        One row per status in the workflow.

        Args:
            config: The StatusActionFlow configuration

        Returns:
            List of JobCustomStatusRow objects
        """
        rows = []

        for status in config.statuses:
            row = JobCustomStatusRow(
                status_action_flow_name=config.name,
                status_name=status.name,
                status_category=status.category,
                status_color=status.color,
                sequence=status.sequence,
                is_active=True,
            )
            rows.append(row)

        return rows

    def _generate_button_rows(
        self,
        config: StatusActionFlow,
    ) -> list[ActionButtonRow]:
        """Generate rows for the Action Buttons tab.

        One row per button per status per role.

        Args:
            config: The StatusActionFlow configuration

        Returns:
            List of ActionButtonRow objects
        """
        rows = []

        for status in config.statuses:
            roles = self._get_roles_for_status(status)

            for role in roles:
                for button in status.action_buttons:
                    row = ActionButtonRow(
                        status_action_flow_name=config.name,
                        status_name=status.name,
                        user_role=role,
                        action_type=button.action,
                        button_label=button.label,
                        button_order=button.order,
                        is_required=button.required,
                        form_id=button.form_id,
                        template_id=button.template_id,
                    )
                    rows.append(row)

        return rows

    def _generate_focus_rows(
        self,
        config: StatusActionFlow,
    ) -> list[FocusViewRow]:
        """Generate rows for the Focus View tab.

        One row per status per role.

        Args:
            config: The StatusActionFlow configuration

        Returns:
            List of FocusViewRow objects
        """
        rows = []

        for status in config.statuses:
            roles = self._get_roles_for_status(status)

            for role in roles:
                # Get widget types in order
                widget_types = [w.widget_type for w in sorted(
                    status.widgets,
                    key=lambda x: x.order
                )]

                row = FocusViewRow(
                    status_action_flow_name=config.name,
                    status_name=status.name,
                    user_role=role,
                    widgets=widget_types,
                    status_instructions=status.status_instructions,
                    display_action_menu=status.display_action_menu,
                    ability_to_change_status=status.ability_to_change_status,
                    focus_view_enabled=status.focus_view_enabled,
                    restrict_to_focus_view=status.restrict_to_focus_view,
                )
                rows.append(row)

        return rows

    def _get_roles_for_status(
        self,
        status: Status,
    ) -> list[UserRole]:
        """Get the roles to generate rows for.

        Args:
            status: The status

        Returns:
            List of UserRole values
        """
        if self.expand_to_all_roles:
            return self.default_roles
        else:
            return [status.user_role]

    def convert_with_multi_role(
        self,
        config: StatusActionFlow,
        role_configurations: dict[str, dict[str, list[UserRole]]],
    ) -> ExcelImportTemplate:
        """Convert with specific role configurations per status.

        Allows different statuses to have different role assignments.

        Args:
            config: The StatusActionFlow configuration
            role_configurations: Dict mapping status name to role config
                Example: {"On Site": {"roles": [UserRole.SERVICE_AGENT, UserRole.TECHNICIAN]}}

        Returns:
            ExcelImportTemplate with role-specific configurations
        """
        logger.info(f"Converting config '{config.name}' with multi-role support")

        status_rows = self._generate_status_rows(config)
        button_rows = []
        focus_rows = []

        for status in config.statuses:
            # Get role config for this status
            role_config = role_configurations.get(status.name, {})
            roles = role_config.get("roles", [status.user_role])

            for role in roles:
                # Generate button rows for this role
                for button in status.action_buttons:
                    row = ActionButtonRow(
                        status_action_flow_name=config.name,
                        status_name=status.name,
                        user_role=role,
                        action_type=button.action,
                        button_label=button.label,
                        button_order=button.order,
                        is_required=button.required,
                        form_id=button.form_id,
                        template_id=button.template_id,
                    )
                    button_rows.append(row)

                # Generate focus view row for this role
                widget_types = [w.widget_type for w in sorted(
                    status.widgets,
                    key=lambda x: x.order
                )]

                focus_row = FocusViewRow(
                    status_action_flow_name=config.name,
                    status_name=status.name,
                    user_role=role,
                    widgets=widget_types,
                    status_instructions=status.status_instructions,
                    display_action_menu=status.display_action_menu,
                    ability_to_change_status=status.ability_to_change_status,
                    focus_view_enabled=status.focus_view_enabled,
                    restrict_to_focus_view=status.restrict_to_focus_view,
                )
                focus_rows.append(focus_row)

        return ExcelImportTemplate(
            job_custom_statuses=status_rows,
            action_buttons=button_rows,
            focus_view=focus_rows,
        )

    def validate_excel_template(
        self,
        template: ExcelImportTemplate,
    ) -> list[str]:
        """Validate the generated Excel template.

        Args:
            template: The ExcelImportTemplate to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check status consistency
        status_names = {
            row.status_name for row in template.job_custom_statuses
        }

        # Check button rows reference valid statuses
        for row in template.action_buttons:
            if row.status_name not in status_names:
                errors.append(
                    f"Action button references unknown status: {row.status_name}"
                )

        # Check focus view rows reference valid statuses
        for row in template.focus_view:
            if row.status_name not in status_names:
                errors.append(
                    f"Focus view references unknown status: {row.status_name}"
                )

        # Check for orphan statuses (in status list but no focus view)
        focus_view_statuses = {row.status_name for row in template.focus_view}
        orphan_statuses = status_names - focus_view_statuses
        for status_name in orphan_statuses:
            errors.append(
                f"Status '{status_name}' has no Focus View configuration"
            )

        return errors

    def get_excel_summary(
        self,
        template: ExcelImportTemplate,
    ) -> dict:
        """Get a summary of the Excel template contents.

        Args:
            template: The ExcelImportTemplate

        Returns:
            Dict with summary statistics
        """
        # Count unique statuses
        status_names = {row.status_name for row in template.job_custom_statuses}

        # Count buttons per status
        buttons_by_status = {}
        for row in template.action_buttons:
            if row.status_name not in buttons_by_status:
                buttons_by_status[row.status_name] = set()
            buttons_by_status[row.status_name].add(row.button_label)

        # Count widgets per status
        widgets_by_status = {}
        for row in template.focus_view:
            if row.status_name not in widgets_by_status:
                widgets_by_status[row.status_name] = set()
            widgets_by_status[row.status_name].update(w.value for w in row.widgets)

        # Count roles used
        roles_used = set()
        for row in template.action_buttons:
            roles_used.add(row.user_role)
        for row in template.focus_view:
            roles_used.add(row.user_role)

        return {
            "total_statuses": len(status_names),
            "total_button_rows": len(template.action_buttons),
            "total_focus_rows": len(template.focus_view),
            "unique_buttons_per_status": {
                name: len(buttons) for name, buttons in buttons_by_status.items()
            },
            "unique_widgets_per_status": {
                name: len(widgets) for name, widgets in widgets_by_status.items()
            },
            "roles_used": [r.value for r in roles_used],
            "status_names": list(status_names),
        }

    def convert_and_generate(
        self,
        config: StatusActionFlow,
        output_path: Optional[Path] = None,
        overwrite: bool = False,
    ) -> Path:
        """Convert config to Excel template and generate the Excel file.

        This is a convenience method that chains the full pipeline:
        convert → validate → generate Excel file.

        Args:
            config: The StatusActionFlow configuration to convert
            output_path: Optional path for the output Excel file
            overwrite: Whether to overwrite existing files

        Returns:
            Path to the generated Excel file

        Raises:
            ValueError: If conversion or validation fails
            IOError: If file cannot be written
        """
        # Import here to avoid circular dependency
        from .excel_generator import ExcelGenerator

        # Convert to Excel template
        template = self.convert(config)

        # Validate the template
        errors = self.validate_excel_template(template)
        if errors:
            raise ValueError(
                f"Template validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )

        # Generate Excel file
        generator = ExcelGenerator()
        return generator.generate(
            template,
            output_path=output_path,
            overwrite=overwrite,
            validate_first=False,  # Already validated above
        )

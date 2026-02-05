"""Excel Generator Service.

Generates physical .xlsx files from ExcelImportTemplate schemas
using openpyxl. This is the final stage of the configuration pipeline.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.worksheet import Worksheet

from ..models.enums import ActionButtonType, StatusCategory, UserRole, WidgetType
from ..models.excel_schemas import ExcelImportTemplate

logger = logging.getLogger(__name__)


class ExcelGenerator:
    """Generates Excel files from ExcelImportTemplate schemas.

    Creates properly formatted .xlsx files with 3 tabs matching
    FieldPulse's ClearPath import template structure.

    Example usage:
        ```python
        from clearpath_agent.services.excel_generator import ExcelGenerator
        from clearpath_agent.services.config_to_excel import ConfigToExcelConverter

        # Convert config to template
        converter = ConfigToExcelConverter()
        template = converter.convert(status_action_flow)

        # Generate Excel file
        generator = ExcelGenerator()
        output_path = generator.generate(template, "my_workflow.xlsx")
        print(f"Generated: {output_path}")
        ```
    """

    # Sheet names matching FieldPulse import format
    SHEET_JOB_CUSTOM_STATUS = "Job Custom Status"
    SHEET_ACTION_BUTTONS = "Action Buttons"
    SHEET_FOCUS_VIEW = "Focus View + Status Instruction"

    # Column headers for each tab
    HEADERS_JOB_CUSTOM_STATUS = [
        "Status Action Flow Name",
        "Status Name",
        "Status Category",
        "Status Color",
        "Sequence",
        "Is Active",
    ]

    HEADERS_ACTION_BUTTONS = [
        "Status Action Flow Name",
        "Status Name",
        "User Role",
        "Action Type",
        "Button Label",
        "Button Order",
        "Is Required",
        "Form ID",
        "Template ID",
    ]

    HEADERS_FOCUS_VIEW = [
        "Status Action Flow Name",
        "Status Name",
        "User Role",
        "Widgets",
        "Status Instructions",
        "Display Action Menu",
        "Ability to Change Status",
        "Focus View Enabled",
        "Restrict to Focus View",
    ]

    # Column widths for each tab
    WIDTHS_JOB_CUSTOM_STATUS = [30, 25, 15, 12, 10, 10]
    WIDTHS_ACTION_BUTTONS = [30, 20, 15, 25, 20, 12, 12, 20, 20]
    WIDTHS_FOCUS_VIEW = [30, 20, 15, 50, 40, 18, 22, 18, 20]

    # Styling constants
    HEADER_FONT = Font(bold=True, size=11)
    HEADER_FILL = PatternFill(
        start_color="D3D3D3", end_color="D3D3D3", fill_type="solid"
    )
    DATA_ALIGNMENT = Alignment(horizontal="left", vertical="top")
    WRAP_ALIGNMENT = Alignment(horizontal="left", vertical="top", wrap_text=True)
    THIN_BORDER = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    def __init__(
        self,
        default_output_dir: Optional[Path] = None,
    ):
        """Initialize the Excel generator.

        Args:
            default_output_dir: Default directory for output files.
                Defaults to 'reports/' in the project root.
        """
        self.default_output_dir = default_output_dir or Path("reports")

    def generate(
        self,
        template: ExcelImportTemplate,
        output_path: Optional[Path] = None,
        overwrite: bool = False,
        validate_first: bool = True,
    ) -> Path:
        """Generate an Excel file from the template.

        Args:
            template: The ExcelImportTemplate to convert to Excel
            output_path: Optional path for the output file.
                If not provided, generates a timestamped filename.
            overwrite: Whether to overwrite existing files.
                Raises error if False and file exists.
            validate_first: Whether to validate the template before generation.

        Returns:
            Path to the generated Excel file.

        Raises:
            ValueError: If template is invalid or file exists and overwrite=False.
            IOError: If file cannot be written.
        """
        # Validate template if requested
        if validate_first:
            errors = self._validate_template(template)
            if errors:
                raise ValueError(
                    f"Template validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
                )

        # Determine output path
        output_path = self._resolve_output_path(template, output_path, overwrite)

        logger.info(f"Generating Excel file: {output_path}")

        # Create workbook and sheets
        workbook = Workbook()

        # Remove default sheet
        default_sheet = workbook.active
        if default_sheet is not None:
            workbook.remove(default_sheet)

        # Generate all three tabs
        self._generate_job_custom_status_sheet(workbook, template)
        self._generate_action_buttons_sheet(workbook, template)
        self._generate_focus_view_sheet(workbook, template)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save workbook
        try:
            workbook.save(output_path)
        except Exception as e:
            raise IOError(f"Failed to save Excel file: {e}") from e

        logger.info(
            f"Excel file generated successfully: {output_path} "
            f"({len(template.job_custom_statuses)} statuses, "
            f"{len(template.action_buttons)} button rows, "
            f"{len(template.focus_view)} focus view rows)"
        )

        return output_path.absolute()

    def _validate_template(self, template: ExcelImportTemplate) -> list[str]:
        """Validate the template before generation.

        Args:
            template: The template to validate

        Returns:
            List of validation error messages
        """
        errors = []

        # Check for empty template
        if not template.job_custom_statuses:
            errors.append("Template has no statuses defined")

        # Check status consistency
        status_names = {row.status_name for row in template.job_custom_statuses}

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

        # Warn about long status instructions
        for row in template.focus_view:
            if len(row.status_instructions) > 2000:
                errors.append(
                    f"Status instructions for '{row.status_name}' exceeds 2000 chars "
                    f"({len(row.status_instructions)} chars) - will be truncated"
                )

        return errors

    def _resolve_output_path(
        self,
        template: ExcelImportTemplate,
        output_path: Optional[Path],
        overwrite: bool,
    ) -> Path:
        """Resolve the output file path.

        Args:
            template: The template (used for default filename)
            output_path: Optional explicit output path
            overwrite: Whether to allow overwriting

        Returns:
            Resolved Path object

        Raises:
            ValueError: If file exists and overwrite=False
        """
        if output_path is None:
            # Generate default filename
            flow_name = template.job_custom_statuses[0].status_action_flow_name
            # Sanitize flow name for filename
            safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in flow_name)
            safe_name = safe_name.replace(" ", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ClearPath_Import_{safe_name}_{timestamp}.xlsx"
            output_path = self.default_output_dir / filename
        else:
            output_path = Path(output_path)

        # Check for existing file
        if output_path.exists() and not overwrite:
            raise ValueError(
                f"Output file already exists: {output_path}. "
                "Set overwrite=True to replace."
            )

        return output_path

    def _generate_job_custom_status_sheet(
        self,
        workbook: Workbook,
        template: ExcelImportTemplate,
    ) -> None:
        """Generate the Job Custom Status tab.

        Args:
            workbook: The workbook to add the sheet to
            template: The template containing status data
        """
        sheet = workbook.create_sheet(self.SHEET_JOB_CUSTOM_STATUS)

        # Write header row
        self._write_header_row(sheet, self.HEADERS_JOB_CUSTOM_STATUS)

        # Write data rows
        for row_idx, status_row in enumerate(template.job_custom_statuses, start=2):
            data = [
                status_row.status_action_flow_name,
                status_row.status_name,
                self._format_status_category(status_row.status_category),
                status_row.status_color,
                status_row.sequence,
                self._format_boolean(status_row.is_active),
            ]
            self._write_data_row(sheet, row_idx, data)

        # Set column widths
        self._set_column_widths(sheet, self.WIDTHS_JOB_CUSTOM_STATUS)

        # Freeze header row
        sheet.freeze_panes = "A2"

        logger.debug(
            f"Generated {self.SHEET_JOB_CUSTOM_STATUS} sheet "
            f"with {len(template.job_custom_statuses)} rows"
        )

    def _generate_action_buttons_sheet(
        self,
        workbook: Workbook,
        template: ExcelImportTemplate,
    ) -> None:
        """Generate the Action Buttons tab.

        Args:
            workbook: The workbook to add the sheet to
            template: The template containing action button data
        """
        sheet = workbook.create_sheet(self.SHEET_ACTION_BUTTONS)

        # Write header row
        self._write_header_row(sheet, self.HEADERS_ACTION_BUTTONS)

        # Write data rows
        for row_idx, button_row in enumerate(template.action_buttons, start=2):
            data = [
                button_row.status_action_flow_name,
                button_row.status_name,
                self._format_user_role(button_row.user_role),
                self._format_action_type(button_row.action_type),
                button_row.button_label,
                button_row.button_order,
                self._format_boolean(button_row.is_required),
                button_row.form_id or "",
                button_row.template_id or "",
            ]
            self._write_data_row(sheet, row_idx, data)

        # Set column widths
        self._set_column_widths(sheet, self.WIDTHS_ACTION_BUTTONS)

        # Freeze header row
        sheet.freeze_panes = "A2"

        logger.debug(
            f"Generated {self.SHEET_ACTION_BUTTONS} sheet "
            f"with {len(template.action_buttons)} rows"
        )

    def _generate_focus_view_sheet(
        self,
        workbook: Workbook,
        template: ExcelImportTemplate,
    ) -> None:
        """Generate the Focus View tab.

        Args:
            workbook: The workbook to add the sheet to
            template: The template containing focus view data
        """
        sheet = workbook.create_sheet(self.SHEET_FOCUS_VIEW)

        # Write header row
        self._write_header_row(sheet, self.HEADERS_FOCUS_VIEW)

        # Write data rows
        for row_idx, focus_row in enumerate(template.focus_view, start=2):
            data = [
                focus_row.status_action_flow_name,
                focus_row.status_name,
                self._format_user_role(focus_row.user_role),
                self._format_widget_list(focus_row.widgets),
                focus_row.status_instructions,
                self._format_boolean(focus_row.display_action_menu),
                self._format_boolean(focus_row.ability_to_change_status),
                self._format_boolean(focus_row.focus_view_enabled),
                self._format_boolean(focus_row.restrict_to_focus_view),
            ]
            self._write_data_row(sheet, row_idx, data, wrap_column=5)

        # Set column widths
        self._set_column_widths(sheet, self.WIDTHS_FOCUS_VIEW)

        # Freeze header row
        sheet.freeze_panes = "A2"

        logger.debug(
            f"Generated {self.SHEET_FOCUS_VIEW} sheet "
            f"with {len(template.focus_view)} rows"
        )

    def _write_header_row(
        self,
        sheet: Worksheet,
        headers: list[str],
    ) -> None:
        """Write and format the header row.

        Args:
            sheet: The worksheet to write to
            headers: List of header strings
        """
        for col_idx, header in enumerate(headers, start=1):
            cell = sheet.cell(row=1, column=col_idx, value=header)
            cell.font = self.HEADER_FONT
            cell.fill = self.HEADER_FILL
            cell.alignment = self.DATA_ALIGNMENT
            cell.border = self.THIN_BORDER

    def _write_data_row(
        self,
        sheet: Worksheet,
        row_idx: int,
        data: list,
        wrap_column: Optional[int] = None,
    ) -> None:
        """Write and format a data row.

        Args:
            sheet: The worksheet to write to
            row_idx: The row number (1-indexed)
            data: List of values to write
            wrap_column: Optional column index (1-indexed) to apply text wrapping
        """
        for col_idx, value in enumerate(data, start=1):
            cell = sheet.cell(row=row_idx, column=col_idx, value=value)
            if wrap_column and col_idx == wrap_column:
                cell.alignment = self.WRAP_ALIGNMENT
            else:
                cell.alignment = self.DATA_ALIGNMENT
            cell.border = self.THIN_BORDER

    def _set_column_widths(
        self,
        sheet: Worksheet,
        widths: list[int],
    ) -> None:
        """Set column widths for a sheet.

        Args:
            sheet: The worksheet to modify
            widths: List of column widths
        """
        for col_idx, width in enumerate(widths, start=1):
            col_letter = chr(ord("A") + col_idx - 1)
            if col_idx > 26:
                # Handle columns beyond Z (AA, AB, etc.)
                col_letter = chr(ord("A") + (col_idx - 1) // 26 - 1) + chr(
                    ord("A") + (col_idx - 1) % 26
                )
            sheet.column_dimensions[col_letter].width = width

    # --- Enum Conversion Helper Methods ---

    def _format_status_category(self, category: StatusCategory) -> str:
        """Convert StatusCategory enum to display string.

        Args:
            category: The StatusCategory enum value

        Returns:
            Display string for the category
        """
        return category.value

    def _format_user_role(self, role: UserRole) -> str:
        """Convert UserRole enum to display string.

        Args:
            role: The UserRole enum value

        Returns:
            Display string for the role
        """
        return role.value

    def _format_action_type(self, action: ActionButtonType) -> str:
        """Convert ActionButtonType enum to display string.

        Args:
            action: The ActionButtonType enum value

        Returns:
            Display string for the action type
        """
        return action.value

    def _format_widget_list(self, widgets: list[WidgetType]) -> str:
        """Convert widget list to comma-separated string.

        Args:
            widgets: List of WidgetType enum values

        Returns:
            Comma-separated string of widget names
        """
        return ", ".join(w.value for w in widgets)

    def _format_boolean(self, value: bool) -> str:
        """Convert Python bool to Excel-compatible string.

        Args:
            value: Boolean value

        Returns:
            "TRUE" or "FALSE" string
        """
        return "TRUE" if value else "FALSE"

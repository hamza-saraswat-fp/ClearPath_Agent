"""Production Data Parser Module.

Parses production Excel files to extract structured workflow data including
statuses, action buttons, and focus view configurations.
"""

import logging
from pathlib import Path
from typing import Optional

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from pydantic import BaseModel, Field

from ..models.enums import StatusCategory, UserRole

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models for Parsed Data
# ============================================================================


class StatusConfig(BaseModel):
    """Parsed status configuration from production Excel."""

    name: str = Field(..., description="Status name")
    category: StatusCategory = Field(
        default=StatusCategory.IN_PROGRESS, description="Status category"
    )
    sequence: int = Field(default=0, description="Order in workflow")
    color: str = Field(default="#3B82F6", description="Hex color code")
    flow_name: str = Field(default="", description="Parent workflow name")
    is_active: bool = Field(default=True, description="Whether status is active")


class ActionButtonConfig(BaseModel):
    """Parsed action button configuration from production Excel."""

    action_type: str = Field(..., description="Type of action button")
    label: str = Field(..., description="Button display label")
    status_name: str = Field(..., description="Parent status name")
    flow_name: str = Field(default="", description="Parent workflow name")
    user_role: UserRole = Field(
        default=UserRole.SERVICE_AGENT, description="Role this button is for"
    )
    order: int = Field(default=0, description="Display order")
    is_required: bool = Field(default=False, description="Whether action is required")
    form_id: Optional[str] = Field(default=None, description="Associated form ID")
    template_id: Optional[str] = Field(
        default=None, description="Associated template ID"
    )


class FocusViewConfig(BaseModel):
    """Parsed Focus View configuration from production Excel."""

    status_name: str = Field(..., description="Parent status name")
    flow_name: str = Field(default="", description="Parent workflow name")
    user_role: UserRole = Field(
        default=UserRole.SERVICE_AGENT, description="Role this config is for"
    )
    widgets: list[str] = Field(default_factory=list, description="Widget list in order")
    status_instructions: str = Field(default="", description="Instructions text")
    display_action_menu: bool = Field(default=True, description="Show action menu")
    ability_to_change_status: bool = Field(default=True, description="Can change status")
    focus_view_enabled: bool = Field(default=True, description="Focus View enabled")
    restrict_to_focus_view: bool = Field(
        default=False, description="Restrict to Focus View"
    )


class ParsedWorkflow(BaseModel):
    """Container for all parsed data from one Excel file."""

    source_file: str = Field(..., description="Source Excel filename")
    flow_name: str = Field(default="", description="Workflow name if detected")
    statuses: list[StatusConfig] = Field(
        default_factory=list, description="Parsed statuses"
    )
    action_buttons: list[ActionButtonConfig] = Field(
        default_factory=list, description="Parsed action buttons"
    )
    focus_views: list[FocusViewConfig] = Field(
        default_factory=list, description="Parsed focus view configs"
    )

    @property
    def status_count(self) -> int:
        """Number of statuses parsed."""
        return len(self.statuses)

    @property
    def action_count(self) -> int:
        """Number of action buttons parsed."""
        return len(self.action_buttons)

    @property
    def widget_count(self) -> int:
        """Number of unique widgets across all focus views."""
        all_widgets = set()
        for fv in self.focus_views:
            all_widgets.update(fv.widgets)
        return len(all_widgets)


# ============================================================================
# Sheet Type Detection
# ============================================================================


class SheetType:
    """Enum-like class for sheet types."""

    JOB_CUSTOM_STATUS = "job_custom_status"
    ACTION_BUTTONS = "action_buttons"
    FOCUS_VIEW = "focus_view"
    UNKNOWN = "unknown"


# Header patterns for auto-detection (case-insensitive)
HEADER_PATTERNS = {
    SheetType.JOB_CUSTOM_STATUS: [
        "status name",
        "status_name",
        "status category",
        "sequence",
        "status color",
    ],
    SheetType.ACTION_BUTTONS: [
        "action type",
        "action_type",
        "button label",
        "button_label",
        "button order",
    ],
    SheetType.FOCUS_VIEW: [
        "widgets",
        "widget",
        "status instructions",
        "focus view enabled",
        "restrict to focus view",
    ],
}


# ============================================================================
# Production Data Parser
# ============================================================================


class ProductionDataParser:
    """Parser for production Excel workflow files."""

    def __init__(self):
        """Initialize the parser."""
        self._header_cache: dict[str, list[str]] = {}

    def parse_excel_file(self, filepath: Path) -> ParsedWorkflow:
        """Parse a production Excel file and extract structured data.

        Args:
            filepath: Path to the Excel file

        Returns:
            ParsedWorkflow containing all extracted data

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a valid Excel file
        """
        if not filepath.exists():
            raise FileNotFoundError(f"Excel file not found: {filepath}")

        if not filepath.suffix.lower() in (".xlsx", ".xls"):
            raise ValueError(f"Not an Excel file: {filepath}")

        logger.info(f"Parsing Excel file: {filepath.name}")

        try:
            workbook = load_workbook(filepath, read_only=True, data_only=True)
        except Exception as e:
            logger.error(f"Failed to load workbook {filepath}: {e}")
            raise ValueError(f"Invalid Excel file: {e}")

        parsed = ParsedWorkflow(source_file=filepath.name)

        # Process each sheet
        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            sheet_type = self._detect_sheet_structure(sheet)

            logger.debug(f"Sheet '{sheet_name}' detected as: {sheet_type}")

            if sheet_type == SheetType.JOB_CUSTOM_STATUS:
                statuses = self._parse_job_custom_status_tab(sheet)
                parsed.statuses.extend(statuses)
                # Try to extract flow name
                if statuses and not parsed.flow_name:
                    parsed.flow_name = statuses[0].flow_name

            elif sheet_type == SheetType.ACTION_BUTTONS:
                buttons = self._parse_action_buttons_tab(sheet)
                parsed.action_buttons.extend(buttons)

            elif sheet_type == SheetType.FOCUS_VIEW:
                focus_views = self._parse_focus_view_tab(sheet)
                parsed.focus_views.extend(focus_views)

            else:
                logger.warning(f"Skipping unrecognized sheet: {sheet_name}")

        workbook.close()

        logger.info(
            f"Parsed {filepath.name}: "
            f"{parsed.status_count} statuses, "
            f"{parsed.action_count} actions, "
            f"{parsed.widget_count} unique widgets"
        )

        return parsed

    def _detect_sheet_structure(self, sheet: Worksheet) -> str:
        """Auto-detect which tab type based on headers.

        Args:
            sheet: Excel worksheet to analyze

        Returns:
            SheetType constant indicating the detected type
        """
        # Get first row headers
        headers = []
        for cell in sheet[1]:
            if cell.value:
                headers.append(str(cell.value).lower().strip())

        if not headers:
            return SheetType.UNKNOWN

        # Check against patterns
        for sheet_type, patterns in HEADER_PATTERNS.items():
            matches = sum(1 for p in patterns if any(p in h for h in headers))
            if matches >= 2:  # Need at least 2 pattern matches
                return sheet_type

        return SheetType.UNKNOWN

    def _get_header_index(
        self, headers: list[str], *possible_names: str
    ) -> Optional[int]:
        """Get column index for a header, trying multiple possible names.

        Args:
            headers: List of header strings (lowercase)
            *possible_names: Possible column names to look for

        Returns:
            Column index if found, None otherwise
        """
        for name in possible_names:
            name_lower = name.lower()
            for i, header in enumerate(headers):
                if name_lower in header or header in name_lower:
                    return i
        return None

    def _parse_job_custom_status_tab(self, sheet: Worksheet) -> list[StatusConfig]:
        """Parse the Job Custom Status tab.

        Args:
            sheet: Excel worksheet

        Returns:
            List of StatusConfig objects
        """
        statuses = []
        rows = list(sheet.iter_rows(values_only=True))

        if len(rows) < 2:
            return statuses

        # Get headers
        headers = [str(h).lower().strip() if h else "" for h in rows[0]]

        # Find column indices
        idx_flow = self._get_header_index(
            headers, "status action flow", "flow name", "workflow"
        )
        idx_name = self._get_header_index(headers, "status name", "name", "status")
        idx_category = self._get_header_index(
            headers, "status category", "category", "type"
        )
        idx_color = self._get_header_index(headers, "status color", "color", "hex")
        idx_sequence = self._get_header_index(
            headers, "sequence", "order", "sort order"
        )
        idx_active = self._get_header_index(headers, "is active", "active", "enabled")

        # Parse data rows
        for row_num, row in enumerate(rows[1:], start=2):
            try:
                # Skip empty rows
                if not any(row):
                    continue

                # Extract values with defaults
                name = str(row[idx_name]).strip() if idx_name is not None and row[idx_name] else None
                if not name:
                    continue  # Skip rows without status name

                flow_name = (
                    str(row[idx_flow]).strip()
                    if idx_flow is not None and row[idx_flow]
                    else ""
                )

                # Parse category
                category = StatusCategory.IN_PROGRESS
                if idx_category is not None and row[idx_category]:
                    cat_str = str(row[idx_category]).strip().lower()
                    category = self._parse_status_category(cat_str)

                # Parse color
                color = "#3B82F6"
                if idx_color is not None and row[idx_color]:
                    color_val = str(row[idx_color]).strip()
                    if color_val.startswith("#"):
                        color = color_val

                # Parse sequence
                sequence = row_num - 1  # Default to row order
                if idx_sequence is not None and row[idx_sequence]:
                    try:
                        sequence = int(row[idx_sequence])
                    except (ValueError, TypeError):
                        pass

                # Parse active
                is_active = True
                if idx_active is not None and row[idx_active] is not None:
                    is_active = str(row[idx_active]).lower() in (
                        "true",
                        "yes",
                        "1",
                        "y",
                    )

                status = StatusConfig(
                    name=name,
                    category=category,
                    sequence=sequence,
                    color=color,
                    flow_name=flow_name,
                    is_active=is_active,
                )
                statuses.append(status)

            except Exception as e:
                logger.warning(f"Error parsing status row {row_num}: {e}")
                continue

        return statuses

    def _parse_action_buttons_tab(self, sheet: Worksheet) -> list[ActionButtonConfig]:
        """Parse the Action Buttons tab.

        Args:
            sheet: Excel worksheet

        Returns:
            List of ActionButtonConfig objects
        """
        buttons = []
        rows = list(sheet.iter_rows(values_only=True))

        if len(rows) < 2:
            return buttons

        # Get headers
        headers = [str(h).lower().strip() if h else "" for h in rows[0]]

        # Find column indices
        idx_flow = self._get_header_index(
            headers, "status action flow", "flow name", "workflow"
        )
        idx_status = self._get_header_index(
            headers, "status name", "status", "parent status"
        )
        idx_role = self._get_header_index(headers, "user role", "role", "user type")
        idx_action = self._get_header_index(
            headers, "action type", "action", "button type"
        )
        idx_label = self._get_header_index(
            headers, "button label", "label", "display name"
        )
        idx_order = self._get_header_index(
            headers, "button order", "order", "sort order"
        )
        idx_required = self._get_header_index(
            headers, "is required", "required", "mandatory"
        )
        idx_form = self._get_header_index(headers, "form id", "form", "form_id")
        idx_template = self._get_header_index(
            headers, "template id", "template", "template_id"
        )

        # Parse data rows
        for row_num, row in enumerate(rows[1:], start=2):
            try:
                # Skip empty rows
                if not any(row):
                    continue

                # Extract required values
                action_type = (
                    str(row[idx_action]).strip()
                    if idx_action is not None and row[idx_action]
                    else None
                )
                if not action_type:
                    continue

                label = (
                    str(row[idx_label]).strip()
                    if idx_label is not None and row[idx_label]
                    else action_type
                )

                status_name = (
                    str(row[idx_status]).strip()
                    if idx_status is not None and row[idx_status]
                    else ""
                )

                flow_name = (
                    str(row[idx_flow]).strip()
                    if idx_flow is not None and row[idx_flow]
                    else ""
                )

                # Parse role
                user_role = UserRole.SERVICE_AGENT
                if idx_role is not None and row[idx_role]:
                    user_role = self._parse_user_role(str(row[idx_role]).strip())

                # Parse order
                order = 0
                if idx_order is not None and row[idx_order]:
                    try:
                        order = int(row[idx_order])
                    except (ValueError, TypeError):
                        pass

                # Parse required
                is_required = False
                if idx_required is not None and row[idx_required] is not None:
                    is_required = str(row[idx_required]).lower() in (
                        "true",
                        "yes",
                        "1",
                        "y",
                    )

                # Parse form/template IDs
                form_id = (
                    str(row[idx_form]).strip()
                    if idx_form is not None and row[idx_form]
                    else None
                )
                template_id = (
                    str(row[idx_template]).strip()
                    if idx_template is not None and row[idx_template]
                    else None
                )

                button = ActionButtonConfig(
                    action_type=action_type,
                    label=label,
                    status_name=status_name,
                    flow_name=flow_name,
                    user_role=user_role,
                    order=order,
                    is_required=is_required,
                    form_id=form_id,
                    template_id=template_id,
                )
                buttons.append(button)

            except Exception as e:
                logger.warning(f"Error parsing action button row {row_num}: {e}")
                continue

        return buttons

    def _parse_focus_view_tab(self, sheet: Worksheet) -> list[FocusViewConfig]:
        """Parse the Focus View tab.

        Args:
            sheet: Excel worksheet

        Returns:
            List of FocusViewConfig objects
        """
        focus_views = []
        rows = list(sheet.iter_rows(values_only=True))

        if len(rows) < 2:
            return focus_views

        # Get headers
        headers = [str(h).lower().strip() if h else "" for h in rows[0]]

        # Find column indices
        idx_flow = self._get_header_index(
            headers, "status action flow", "flow name", "workflow"
        )
        idx_status = self._get_header_index(
            headers, "status name", "status", "parent status"
        )
        idx_role = self._get_header_index(headers, "user role", "role", "user type")
        idx_widgets = self._get_header_index(headers, "widgets", "widget list")
        idx_instructions = self._get_header_index(
            headers, "status instructions", "instructions"
        )
        idx_action_menu = self._get_header_index(
            headers, "display action menu", "action menu", "show action"
        )
        idx_change_status = self._get_header_index(
            headers, "ability to change status", "change status", "can change"
        )
        idx_fv_enabled = self._get_header_index(
            headers, "focus view enabled", "enabled", "fv enabled"
        )
        idx_restrict = self._get_header_index(
            headers, "restrict to focus view", "restrict", "fv only"
        )

        # Parse data rows
        for row_num, row in enumerate(rows[1:], start=2):
            try:
                # Skip empty rows
                if not any(row):
                    continue

                status_name = (
                    str(row[idx_status]).strip()
                    if idx_status is not None and row[idx_status]
                    else None
                )
                if not status_name:
                    continue

                flow_name = (
                    str(row[idx_flow]).strip()
                    if idx_flow is not None and row[idx_flow]
                    else ""
                )

                # Parse role
                user_role = UserRole.SERVICE_AGENT
                if idx_role is not None and row[idx_role]:
                    user_role = self._parse_user_role(str(row[idx_role]).strip())

                # Parse widgets (comma or semicolon separated)
                widgets = []
                if idx_widgets is not None and row[idx_widgets]:
                    widget_str = str(row[idx_widgets])
                    # Handle both comma and semicolon separators
                    for sep in [";", ","]:
                        if sep in widget_str:
                            widgets = [w.strip() for w in widget_str.split(sep) if w.strip()]
                            break
                    if not widgets:
                        widgets = [widget_str.strip()] if widget_str.strip() else []

                # Parse instructions
                instructions = (
                    str(row[idx_instructions]).strip()
                    if idx_instructions is not None and row[idx_instructions]
                    else ""
                )

                # Parse boolean fields
                display_action_menu = self._parse_bool(
                    row[idx_action_menu] if idx_action_menu is not None else None, True
                )
                ability_to_change = self._parse_bool(
                    row[idx_change_status] if idx_change_status is not None else None,
                    True,
                )
                fv_enabled = self._parse_bool(
                    row[idx_fv_enabled] if idx_fv_enabled is not None else None, True
                )
                restrict = self._parse_bool(
                    row[idx_restrict] if idx_restrict is not None else None, False
                )

                focus_view = FocusViewConfig(
                    status_name=status_name,
                    flow_name=flow_name,
                    user_role=user_role,
                    widgets=widgets,
                    status_instructions=instructions,
                    display_action_menu=display_action_menu,
                    ability_to_change_status=ability_to_change,
                    focus_view_enabled=fv_enabled,
                    restrict_to_focus_view=restrict,
                )
                focus_views.append(focus_view)

            except Exception as e:
                logger.warning(f"Error parsing focus view row {row_num}: {e}")
                continue

        return focus_views

    def _parse_status_category(self, cat_str: str) -> StatusCategory:
        """Parse status category string to enum.

        Args:
            cat_str: Category string (lowercase)

        Returns:
            StatusCategory enum value
        """
        mapping = {
            "pending": StatusCategory.PENDING,
            "in progress": StatusCategory.IN_PROGRESS,
            "in_progress": StatusCategory.IN_PROGRESS,
            "inprogress": StatusCategory.IN_PROGRESS,
            "on hold": StatusCategory.ON_HOLD,
            "on_hold": StatusCategory.ON_HOLD,
            "onhold": StatusCategory.ON_HOLD,
            "completed": StatusCategory.COMPLETED,
            "complete": StatusCategory.COMPLETED,
            "done": StatusCategory.COMPLETED,
            "cancelled": StatusCategory.CANCELLED,
            "canceled": StatusCategory.CANCELLED,
        }
        return mapping.get(cat_str.lower(), StatusCategory.IN_PROGRESS)

    def _parse_user_role(self, role_str: str) -> UserRole:
        """Parse user role string to enum.

        Args:
            role_str: Role string

        Returns:
            UserRole enum value
        """
        mapping = {
            "service agent": UserRole.SERVICE_AGENT,
            "service_agent": UserRole.SERVICE_AGENT,
            "serviceagent": UserRole.SERVICE_AGENT,
            "technician": UserRole.TECHNICIAN,
            "tech": UserRole.TECHNICIAN,
            "office staff": UserRole.OFFICE_STAFF,
            "office_staff": UserRole.OFFICE_STAFF,
            "office": UserRole.OFFICE_STAFF,
            "manager": UserRole.MANAGER,
            "admin": UserRole.ADMIN,
            "administrator": UserRole.ADMIN,
            "dispatcher": UserRole.DISPATCHER,
            "dispatch": UserRole.DISPATCHER,
            "sales": UserRole.SALES,
        }
        return mapping.get(role_str.lower(), UserRole.SERVICE_AGENT)

    def _parse_bool(self, value: any, default: bool = False) -> bool:
        """Parse a value to boolean.

        Args:
            value: Value to parse
            default: Default if value is None

        Returns:
            Boolean value
        """
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "yes", "1", "y")

    def parse_csv_file(self, filepath: Path) -> list[ParsedWorkflow]:
        """Parse a production CSV file and extract structured data.

        The CSV format contains one row per status per company/workflow.
        Expected columns:
        - company_id, company_name, industry
        - status_workflow_id, status_workflow_name
        - status_action_flow_id, status_action_flow_name
        - status_id, status_name, status_sequence
        - object_type, user_role
        - action_buttons (comma-separated list)
        - widgets (comma-separated list)
        - status_instructions
        - display_action_menu, ability_to_change_status
        - focus_view_enabled, is_forced_focused_view

        Args:
            filepath: Path to the CSV file

        Returns:
            List of ParsedWorkflow objects (one per company/workflow combination)
        """
        import csv

        if not filepath.exists():
            raise FileNotFoundError(f"CSV file not found: {filepath}")

        logger.info(f"Parsing CSV file: {filepath.name}")

        # Group rows by (company_id, status_workflow_id) to form workflows
        workflow_data: dict[tuple, dict] = {}

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Create workflow key
                        company_id = row.get("company_id", "unknown")
                        workflow_id = row.get("status_workflow_id", "unknown")
                        key = (company_id, workflow_id)

                        # Initialize workflow data if new
                        if key not in workflow_data:
                            workflow_data[key] = {
                                "company_name": row.get("company_name", ""),
                                "industry": row.get("industry", ""),
                                "flow_name": row.get("status_workflow_name", "")
                                    or row.get("status_action_flow_name", ""),
                                "statuses": {},  # keyed by status_name to avoid duplicates
                                "action_buttons": [],
                                "focus_views": [],
                            }

                        wf = workflow_data[key]
                        status_name = row.get("status_name", "").strip()

                        if not status_name:
                            continue

                        # Parse status (avoid duplicates)
                        if status_name not in wf["statuses"]:
                            # Determine category from object_type or default
                            object_type = row.get("object_type", "job").lower()
                            category = StatusCategory.IN_PROGRESS  # Default

                            # Parse sequence
                            sequence = 0
                            seq_val = row.get("status_sequence", "0")
                            try:
                                sequence = int(seq_val) if seq_val else 0
                            except (ValueError, TypeError):
                                pass

                            wf["statuses"][status_name] = StatusConfig(
                                name=status_name,
                                category=category,
                                sequence=sequence,
                                flow_name=wf["flow_name"],
                            )

                        # Parse user role
                        user_role = self._parse_user_role(row.get("user_role", "Service agent"))

                        # Parse action buttons (comma-separated)
                        action_buttons_str = row.get("action_buttons", "").strip()
                        if action_buttons_str and action_buttons_str not in (", ", ",", ""):
                            # Split by comma and clean up
                            actions = [a.strip() for a in action_buttons_str.split(",") if a.strip()]
                            for order, action_type in enumerate(actions):
                                if action_type:  # Skip empty strings
                                    wf["action_buttons"].append(ActionButtonConfig(
                                        action_type=action_type,
                                        label=action_type,  # Use action type as label
                                        status_name=status_name,
                                        flow_name=wf["flow_name"],
                                        user_role=user_role,
                                        order=order,
                                    ))

                        # Parse widgets (comma-separated)
                        widgets_str = row.get("widgets", "").strip()
                        widgets_list = []
                        if widgets_str and widgets_str not in (", ", ",", ""):
                            widgets_list = [w.strip() for w in widgets_str.split(",") if w.strip()]

                        # Create FocusViewConfig if we have widgets or instructions
                        status_instructions = row.get("status_instructions", "").strip()
                        if widgets_list or status_instructions:
                            wf["focus_views"].append(FocusViewConfig(
                                status_name=status_name,
                                flow_name=wf["flow_name"],
                                user_role=user_role,
                                widgets=widgets_list,
                                status_instructions=status_instructions,
                                display_action_menu=self._parse_bool(
                                    row.get("display_action_menu"), True
                                ),
                                ability_to_change_status=self._parse_bool(
                                    row.get("ability_to_change_status"), True
                                ),
                                focus_view_enabled=self._parse_bool(
                                    row.get("focus_view_enabled"), False
                                ),
                                restrict_to_focus_view=self._parse_bool(
                                    row.get("is_forced_focused_view"), False
                                ),
                            ))

                    except Exception as e:
                        logger.warning(f"Error parsing CSV row {row_num}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Failed to read CSV file {filepath}: {e}")
            raise ValueError(f"Invalid CSV file: {e}")

        # Convert to ParsedWorkflow objects
        workflows = []
        for (company_id, workflow_id), data in workflow_data.items():
            source_name = f"{data['company_name']}_{data['flow_name']}_{company_id}"
            workflow = ParsedWorkflow(
                source_file=source_name,
                flow_name=data["flow_name"],
                statuses=list(data["statuses"].values()),
                action_buttons=data["action_buttons"],
                focus_views=data["focus_views"],
            )
            workflows.append(workflow)

        logger.info(
            f"Parsed CSV {filepath.name}: "
            f"{len(workflows)} workflows, "
            f"{sum(w.status_count for w in workflows)} total statuses, "
            f"{sum(w.action_count for w in workflows)} action buttons, "
            f"{sum(w.widget_count for w in workflows)} unique widgets"
        )

        return workflows

    def parse_directory(self, directory: Path) -> list[ParsedWorkflow]:
        """Parse all Excel and CSV files in a directory.

        Args:
            directory: Directory containing Excel/CSV files

        Returns:
            List of ParsedWorkflow objects
        """
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        workflows = []

        # Find Excel files
        excel_files = list(directory.glob("*.xlsx")) + list(directory.glob("*.xls"))
        excel_files = [f for f in excel_files if not f.name.startswith("~$")]

        # Find CSV files
        csv_files = list(directory.glob("*.csv"))

        total_files = len(excel_files) + len(csv_files)
        logger.info(f"Found {len(excel_files)} Excel files and {len(csv_files)} CSV files in {directory}")

        # Parse Excel files
        for filepath in excel_files:
            try:
                workflow = self.parse_excel_file(filepath)
                workflows.append(workflow)
            except Exception as e:
                logger.error(f"Failed to parse {filepath.name}: {e}")
                continue

        # Parse CSV files
        for filepath in csv_files:
            try:
                csv_workflows = self.parse_csv_file(filepath)
                workflows.extend(csv_workflows)
            except Exception as e:
                logger.error(f"Failed to parse {filepath.name}: {e}")
                continue

        logger.info(f"Successfully parsed {len(workflows)} workflows from {total_files} files")
        return workflows

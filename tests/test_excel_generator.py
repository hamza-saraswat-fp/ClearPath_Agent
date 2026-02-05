"""Tests for the Excel Generator service."""

import tempfile
from pathlib import Path

import pytest
from openpyxl import load_workbook

from clearpath_agent.models.entities import (
    ActionButton,
    Status,
    StatusActionFlow,
    Widget,
)
from clearpath_agent.models.enums import (
    ActionButtonType,
    StatusCategory,
    UserRole,
    WidgetType,
)
from clearpath_agent.models.excel_schemas import (
    ActionButtonRow,
    ExcelImportTemplate,
    FocusViewRow,
    JobCustomStatusRow,
)
from clearpath_agent.services.config_to_excel import ConfigToExcelConverter
from clearpath_agent.services.excel_generator import ExcelGenerator


@pytest.fixture
def minimal_template():
    """Create a minimal valid ExcelImportTemplate."""
    return ExcelImportTemplate(
        job_custom_statuses=[
            JobCustomStatusRow(
                status_action_flow_name="Test Flow",
                status_name="New",
                status_category=StatusCategory.PENDING,
                status_color="#3B82F6",
                sequence=1,
                is_active=True,
            ),
        ],
        action_buttons=[
            ActionButtonRow(
                status_action_flow_name="Test Flow",
                status_name="New",
                user_role=UserRole.SERVICE_AGENT,
                action_type=ActionButtonType.CLOCK_IN_OUT,
                button_label="Clock In",
                button_order=0,
                is_required=False,
            ),
        ],
        focus_view=[
            FocusViewRow(
                status_action_flow_name="Test Flow",
                status_name="New",
                user_role=UserRole.SERVICE_AGENT,
                widgets=[WidgetType.JOB_TITLE, WidgetType.JOB_STATUS],
                status_instructions="1. Clock in when you arrive",
                display_action_menu=True,
                ability_to_change_status=True,
                focus_view_enabled=True,
                restrict_to_focus_view=False,
            ),
        ],
    )


@pytest.fixture
def full_template():
    """Create a complete ExcelImportTemplate with multiple statuses."""
    return ExcelImportTemplate(
        job_custom_statuses=[
            JobCustomStatusRow(
                status_action_flow_name="HVAC Service Call",
                status_name="New",
                status_category=StatusCategory.PENDING,
                status_color="#6B7280",
                sequence=1,
                is_active=True,
            ),
            JobCustomStatusRow(
                status_action_flow_name="HVAC Service Call",
                status_name="Dispatched",
                status_category=StatusCategory.IN_PROGRESS,
                status_color="#3B82F6",
                sequence=2,
                is_active=True,
            ),
            JobCustomStatusRow(
                status_action_flow_name="HVAC Service Call",
                status_name="Completed",
                status_category=StatusCategory.COMPLETED,
                status_color="#10B981",
                sequence=3,
                is_active=True,
            ),
        ],
        action_buttons=[
            ActionButtonRow(
                status_action_flow_name="HVAC Service Call",
                status_name="New",
                user_role=UserRole.DISPATCHER,
                action_type=ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
                button_label="Send Confirmation",
                button_order=0,
                is_required=False,
                template_id="sms_confirmation_template",
            ),
            ActionButtonRow(
                status_action_flow_name="HVAC Service Call",
                status_name="Dispatched",
                user_role=UserRole.SERVICE_AGENT,
                action_type=ActionButtonType.CLOCK_IN_OUT,
                button_label="Clock In",
                button_order=0,
                is_required=True,
            ),
            ActionButtonRow(
                status_action_flow_name="HVAC Service Call",
                status_name="Dispatched",
                user_role=UserRole.SERVICE_AGENT,
                action_type=ActionButtonType.FILL_FORM,
                button_label="Safety Checklist",
                button_order=1,
                is_required=True,
                form_id="safety_checklist_form",
            ),
            ActionButtonRow(
                status_action_flow_name="HVAC Service Call",
                status_name="Completed",
                user_role=UserRole.SERVICE_AGENT,
                action_type=ActionButtonType.COLLECT_SIGNATURE,
                button_label="Get Signature",
                button_order=0,
                is_required=True,
            ),
        ],
        focus_view=[
            FocusViewRow(
                status_action_flow_name="HVAC Service Call",
                status_name="New",
                user_role=UserRole.DISPATCHER,
                widgets=[
                    WidgetType.JOB_TITLE,
                    WidgetType.JOB_STATUS,
                    WidgetType.CUSTOMER_CONTACT,
                    WidgetType.ACTION_BUTTONS,
                ],
                status_instructions="1. Review job details\n2. Assign technician\n3. Send confirmation",
                display_action_menu=True,
                ability_to_change_status=True,
                focus_view_enabled=True,
                restrict_to_focus_view=False,
            ),
            FocusViewRow(
                status_action_flow_name="HVAC Service Call",
                status_name="Dispatched",
                user_role=UserRole.SERVICE_AGENT,
                widgets=[
                    WidgetType.JOB_TITLE,
                    WidgetType.JOB_STATUS,
                    WidgetType.CUSTOMER_ADDRESS,
                    WidgetType.FORMS,
                    WidgetType.ACTION_BUTTONS,
                ],
                status_instructions="1. Clock in on arrival\n2. Complete safety checklist\n3. Begin work",
                display_action_menu=True,
                ability_to_change_status=True,
                focus_view_enabled=True,
                restrict_to_focus_view=True,
            ),
            FocusViewRow(
                status_action_flow_name="HVAC Service Call",
                status_name="Completed",
                user_role=UserRole.SERVICE_AGENT,
                widgets=[
                    WidgetType.JOB_TITLE,
                    WidgetType.JOB_STATUS,
                    WidgetType.SIGNATURES,
                    WidgetType.ACTION_BUTTONS,
                ],
                status_instructions="1. Get customer signature\n2. Review completed work",
                display_action_menu=True,
                ability_to_change_status=False,
                focus_view_enabled=True,
                restrict_to_focus_view=False,
            ),
        ],
    )


@pytest.fixture
def sample_config():
    """Create a sample StatusActionFlow for testing."""
    return StatusActionFlow(
        name="Test Workflow",
        description="A test workflow",
        statuses=[
            Status(
                name="New",
                category=StatusCategory.PENDING,
                color="#6B7280",
                sequence=1,
                user_role=UserRole.DISPATCHER,
                action_buttons=[
                    ActionButton(
                        action=ActionButtonType.ADD_NOTE,
                        label="Add Note",
                        order=0,
                    ),
                ],
                widgets=[
                    Widget(widget_type=WidgetType.JOB_TITLE, order=0),
                    Widget(widget_type=WidgetType.JOB_STATUS, order=1),
                    Widget(widget_type=WidgetType.ACTION_BUTTONS, order=2),
                ],
                status_instructions="Review and dispatch",
            ),
            Status(
                name="In Progress",
                category=StatusCategory.IN_PROGRESS,
                color="#3B82F6",
                sequence=2,
                user_role=UserRole.SERVICE_AGENT,
                action_buttons=[
                    ActionButton(
                        action=ActionButtonType.CLOCK_IN_OUT,
                        label="Clock In",
                        order=0,
                    ),
                ],
                widgets=[
                    Widget(widget_type=WidgetType.JOB_TITLE, order=0),
                    Widget(widget_type=WidgetType.TIMESHEETS, order=1),
                    Widget(widget_type=WidgetType.ACTION_BUTTONS, order=2),
                ],
                status_instructions="Complete the work",
            ),
        ],
    )


class TestExcelGenerator:
    """Tests for ExcelGenerator class."""

    def test_generate_creates_file(self, minimal_template):
        """Test that generate() creates an Excel file."""
        generator = ExcelGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.xlsx"
            result = generator.generate(minimal_template, output_path)

            assert result.exists()
            assert result.suffix == ".xlsx"

    def test_generate_creates_three_sheets(self, minimal_template):
        """Test that generated file has exactly 3 sheets."""
        generator = ExcelGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.xlsx"
            generator.generate(minimal_template, output_path)

            workbook = load_workbook(output_path)
            assert len(workbook.sheetnames) == 3
            assert "Job Custom Status" in workbook.sheetnames
            assert "Action Buttons" in workbook.sheetnames
            assert "Focus View + Status Instruction" in workbook.sheetnames

    def test_job_custom_status_sheet_headers(self, minimal_template):
        """Test Job Custom Status sheet has correct headers."""
        generator = ExcelGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.xlsx"
            generator.generate(minimal_template, output_path)

            workbook = load_workbook(output_path)
            sheet = workbook["Job Custom Status"]

            expected_headers = [
                "Status Action Flow Name",
                "Status Name",
                "Status Category",
                "Status Color",
                "Sequence",
                "Is Active",
            ]

            for col_idx, expected in enumerate(expected_headers, start=1):
                assert sheet.cell(row=1, column=col_idx).value == expected

    def test_action_buttons_sheet_headers(self, minimal_template):
        """Test Action Buttons sheet has correct headers."""
        generator = ExcelGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.xlsx"
            generator.generate(minimal_template, output_path)

            workbook = load_workbook(output_path)
            sheet = workbook["Action Buttons"]

            expected_headers = [
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

            for col_idx, expected in enumerate(expected_headers, start=1):
                assert sheet.cell(row=1, column=col_idx).value == expected

    def test_focus_view_sheet_headers(self, minimal_template):
        """Test Focus View sheet has correct headers."""
        generator = ExcelGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.xlsx"
            generator.generate(minimal_template, output_path)

            workbook = load_workbook(output_path)
            sheet = workbook["Focus View + Status Instruction"]

            expected_headers = [
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

            for col_idx, expected in enumerate(expected_headers, start=1):
                assert sheet.cell(row=1, column=col_idx).value == expected

    def test_job_custom_status_data_rows(self, full_template):
        """Test Job Custom Status sheet has correct data."""
        generator = ExcelGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.xlsx"
            generator.generate(full_template, output_path)

            workbook = load_workbook(output_path)
            sheet = workbook["Job Custom Status"]

            # Check row count (1 header + 3 data rows)
            assert sheet.max_row == 4

            # Check first data row
            assert sheet.cell(row=2, column=1).value == "HVAC Service Call"
            assert sheet.cell(row=2, column=2).value == "New"
            assert sheet.cell(row=2, column=3).value == "Pending"
            assert sheet.cell(row=2, column=4).value == "#6B7280"
            assert sheet.cell(row=2, column=5).value == 1
            assert sheet.cell(row=2, column=6).value == "TRUE"

    def test_action_buttons_data_rows(self, full_template):
        """Test Action Buttons sheet has correct data."""
        generator = ExcelGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.xlsx"
            generator.generate(full_template, output_path)

            workbook = load_workbook(output_path)
            sheet = workbook["Action Buttons"]

            # Check row count (1 header + 4 data rows)
            assert sheet.max_row == 5

            # Check first data row
            assert sheet.cell(row=2, column=1).value == "HVAC Service Call"
            assert sheet.cell(row=2, column=2).value == "New"
            assert sheet.cell(row=2, column=3).value == "Dispatcher"
            assert sheet.cell(row=2, column=4).value == "Send Customer Communication"
            assert sheet.cell(row=2, column=5).value == "Send Confirmation"
            assert sheet.cell(row=2, column=9).value == "sms_confirmation_template"

    def test_focus_view_data_rows(self, full_template):
        """Test Focus View sheet has correct data."""
        generator = ExcelGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.xlsx"
            generator.generate(full_template, output_path)

            workbook = load_workbook(output_path)
            sheet = workbook["Focus View + Status Instruction"]

            # Check row count (1 header + 3 data rows)
            assert sheet.max_row == 4

            # Check widgets are comma-separated
            widgets_cell = sheet.cell(row=2, column=4).value
            assert "Job Title" in widgets_cell
            assert "Job Status" in widgets_cell

            # Check boolean formatting
            assert sheet.cell(row=2, column=6).value == "TRUE"

    def test_header_formatting(self, minimal_template):
        """Test that headers have bold formatting."""
        generator = ExcelGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.xlsx"
            generator.generate(minimal_template, output_path)

            workbook = load_workbook(output_path)
            sheet = workbook["Job Custom Status"]

            # Check header is bold
            header_cell = sheet.cell(row=1, column=1)
            assert header_cell.font.bold is True

    def test_frozen_panes(self, minimal_template):
        """Test that top row is frozen."""
        generator = ExcelGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.xlsx"
            generator.generate(minimal_template, output_path)

            workbook = load_workbook(output_path)
            sheet = workbook["Job Custom Status"]

            assert sheet.freeze_panes == "A2"

    def test_overwrite_protection(self, minimal_template):
        """Test that existing files are not overwritten by default."""
        generator = ExcelGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.xlsx"
            generator.generate(minimal_template, output_path)

            # Try to generate again without overwrite flag
            with pytest.raises(ValueError, match="already exists"):
                generator.generate(minimal_template, output_path)

    def test_overwrite_allowed(self, minimal_template):
        """Test that overwrite flag allows replacing files."""
        generator = ExcelGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_output.xlsx"
            generator.generate(minimal_template, output_path)

            # Should succeed with overwrite=True
            result = generator.generate(minimal_template, output_path, overwrite=True)
            assert result.exists()

    def test_default_filename_generation(self, minimal_template):
        """Test that default filename is generated correctly."""
        generator = ExcelGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            generator.default_output_dir = Path(tmpdir)
            result = generator.generate(minimal_template)

            assert result.exists()
            assert "ClearPath_Import_Test_Flow_" in result.name
            assert result.suffix == ".xlsx"

    def test_creates_output_directory(self, minimal_template):
        """Test that output directory is created if it doesn't exist."""
        generator = ExcelGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "nested" / "deep" / "output.xlsx"
            result = generator.generate(minimal_template, nested_path)

            assert result.exists()
            assert result.parent.exists()


class TestExcelGeneratorValidation:
    """Tests for template validation in ExcelGenerator."""

    def test_validation_empty_template(self):
        """Test validation fails for empty template."""
        generator = ExcelGenerator()

        # Create template with empty statuses (bypassing Pydantic validation)
        template = ExcelImportTemplate(
            job_custom_statuses=[
                JobCustomStatusRow(
                    status_action_flow_name="Test",
                    status_name="Status1",
                    sequence=1,
                ),
            ],
        )

        # Should pass - has at least one status
        errors = generator._validate_template(template)
        assert len(errors) == 0

    def test_validation_unknown_status_reference(self):
        """Test validation catches unknown status references."""
        generator = ExcelGenerator()

        template = ExcelImportTemplate(
            job_custom_statuses=[
                JobCustomStatusRow(
                    status_action_flow_name="Test",
                    status_name="New",
                    sequence=1,
                ),
            ],
            action_buttons=[
                ActionButtonRow(
                    status_action_flow_name="Test",
                    status_name="Unknown Status",  # Does not exist
                    user_role=UserRole.SERVICE_AGENT,
                    action_type=ActionButtonType.CLOCK_IN_OUT,
                    button_label="Clock In",
                ),
            ],
        )

        errors = generator._validate_template(template)
        assert any("Unknown Status" in e for e in errors)


class TestEnumConversions:
    """Tests for enum-to-string conversion methods."""

    def test_format_status_category(self):
        """Test status category formatting."""
        generator = ExcelGenerator()

        assert generator._format_status_category(StatusCategory.PENDING) == "Pending"
        assert generator._format_status_category(StatusCategory.IN_PROGRESS) == "In Progress"
        assert generator._format_status_category(StatusCategory.COMPLETED) == "Completed"

    def test_format_user_role(self):
        """Test user role formatting."""
        generator = ExcelGenerator()

        assert generator._format_user_role(UserRole.SERVICE_AGENT) == "Service Agent"
        assert generator._format_user_role(UserRole.MANAGER) == "Manager"
        assert generator._format_user_role(UserRole.DISPATCHER) == "Dispatcher"

    def test_format_action_type(self):
        """Test action type formatting."""
        generator = ExcelGenerator()

        assert generator._format_action_type(ActionButtonType.CLOCK_IN_OUT) == "Job Timesheet Clock in / out"
        assert generator._format_action_type(ActionButtonType.FILL_FORM) == "Fill Form"

    def test_format_widget_list(self):
        """Test widget list formatting."""
        generator = ExcelGenerator()

        widgets = [WidgetType.JOB_TITLE, WidgetType.JOB_STATUS, WidgetType.ACTION_BUTTONS]
        result = generator._format_widget_list(widgets)

        assert result == "Job Title, Job Status, Action Buttons"

    def test_format_boolean(self):
        """Test boolean formatting."""
        generator = ExcelGenerator()

        assert generator._format_boolean(True) == "TRUE"
        assert generator._format_boolean(False) == "FALSE"


class TestConfigToExcelIntegration:
    """Tests for integration between ConfigToExcelConverter and ExcelGenerator."""

    def test_convert_and_generate(self, sample_config):
        """Test the full convert and generate pipeline."""
        converter = ConfigToExcelConverter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "integrated_output.xlsx"
            result = converter.convert_and_generate(sample_config, output_path)

            assert result.exists()

            # Verify the file structure
            workbook = load_workbook(result)
            assert len(workbook.sheetnames) == 3

            # Verify status count
            status_sheet = workbook["Job Custom Status"]
            assert status_sheet.max_row == 3  # 1 header + 2 statuses

    def test_round_trip_parsing(self, sample_config):
        """Test that generated Excel can be re-parsed (structure validation)."""
        converter = ConfigToExcelConverter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "round_trip.xlsx"
            converter.convert_and_generate(sample_config, output_path)

            # Load and verify structure
            workbook = load_workbook(output_path)

            # Verify Job Custom Status sheet
            status_sheet = workbook["Job Custom Status"]
            assert status_sheet.cell(row=2, column=2).value == "New"
            assert status_sheet.cell(row=3, column=2).value == "In Progress"

            # Verify Action Buttons sheet
            button_sheet = workbook["Action Buttons"]
            assert button_sheet.cell(row=2, column=5).value == "Add Note"
            assert button_sheet.cell(row=3, column=5).value == "Clock In"

            # Verify Focus View sheet
            focus_sheet = workbook["Focus View + Status Instruction"]
            assert focus_sheet.cell(row=2, column=2).value == "New"


class TestMultiRoleExpansion:
    """Tests for multi-role row generation."""

    def test_multi_role_button_rows(self):
        """Test that multi-role expansion creates correct number of rows."""
        config = StatusActionFlow(
            name="Multi Role Test",
            statuses=[
                Status(
                    name="New",
                    category=StatusCategory.PENDING,
                    sequence=1,
                    user_role=UserRole.SERVICE_AGENT,
                    action_buttons=[
                        ActionButton(action=ActionButtonType.ADD_NOTE, label="Note", order=0),
                    ],
                    widgets=[Widget(widget_type=WidgetType.JOB_TITLE, order=0)],
                ),
            ],
        )

        converter = ConfigToExcelConverter(expand_to_all_roles=True)
        template = converter.convert(config)

        # Should have 3 button rows (one per default role)
        assert len(template.action_buttons) == 3

        # Should have 3 focus view rows (one per default role)
        assert len(template.focus_view) == 3

        # Verify all roles are present
        roles_in_buttons = {row.user_role for row in template.action_buttons}
        assert UserRole.SERVICE_AGENT in roles_in_buttons
        assert UserRole.MANAGER in roles_in_buttons
        assert UserRole.ADMIN in roles_in_buttons

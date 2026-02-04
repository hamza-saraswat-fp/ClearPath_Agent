"""Tests for ClearPath data models."""

import pytest
from pydantic import ValidationError

from clearpath_agent.models import (
    ActionButton,
    ActionButtonRow,
    ActionButtonType,
    ExcelImportTemplate,
    FocusViewRow,
    JobCustomStatusRow,
    Status,
    StatusActionFlow,
    StatusCategory,
    UserRole,
    Widget,
    WidgetType,
)


class TestActionButton:
    """Tests for ActionButton model."""

    def test_create_action_button(self):
        """Test creating a valid action button."""
        button = ActionButton(
            action=ActionButtonType.CLOCK_IN_OUT,
            label="Clock In",
            order=0,
        )
        assert button.action == ActionButtonType.CLOCK_IN_OUT
        assert button.label == "Clock In"
        assert button.required is False

    def test_action_button_with_form(self):
        """Test action button with form ID."""
        button = ActionButton(
            action=ActionButtonType.FILL_FORM,
            label="Safety Inspection",
            form_id="form_123",
        )
        assert button.form_id == "form_123"

    def test_action_button_label_validation(self):
        """Test that label is stripped of whitespace."""
        button = ActionButton(
            action=ActionButtonType.TAKE_PHOTO,
            label="  Before Photos  ",
        )
        assert button.label == "Before Photos"


class TestWidget:
    """Tests for Widget model."""

    def test_create_widget(self):
        """Test creating a valid widget."""
        widget = Widget(
            widget_type=WidgetType.JOB_TITLE,
            order=0,
        )
        assert widget.widget_type == WidgetType.JOB_TITLE
        assert widget.collapsed is False


class TestStatus:
    """Tests for Status model."""

    def test_create_status(self):
        """Test creating a valid status."""
        status = Status(
            name="On Site",
            sequence=1,
            category=StatusCategory.IN_PROGRESS,
        )
        assert status.name == "On Site"
        assert status.sequence == 1
        assert status.focus_view_enabled is True

    def test_status_with_buttons_and_widgets(self):
        """Test status with action buttons and widgets."""
        status = Status(
            name="On Site",
            sequence=1,
            action_buttons=[
                ActionButton(
                    action=ActionButtonType.CLOCK_IN_OUT,
                    label="Clock In",
                ),
            ],
            widgets=[
                Widget(widget_type=WidgetType.JOB_TITLE),
                Widget(widget_type=WidgetType.ACTION_BUTTONS, order=1),
            ],
        )
        assert len(status.action_buttons) == 1
        assert len(status.widgets) == 2


class TestStatusActionFlow:
    """Tests for StatusActionFlow model."""

    def test_create_flow(self):
        """Test creating a valid status action flow."""
        flow = StatusActionFlow(
            name="Service Call Flow",
            statuses=[
                Status(name="Dispatched", sequence=1),
                Status(name="On Site", sequence=2),
                Status(name="Completed", sequence=3),
            ],
        )
        assert flow.name == "Service Call Flow"
        assert len(flow.statuses) == 3

    def test_flow_statuses_sorted_by_sequence(self):
        """Test that statuses are sorted by sequence."""
        flow = StatusActionFlow(
            name="Test Flow",
            statuses=[
                Status(name="Third", sequence=3),
                Status(name="First", sequence=1),
                Status(name="Second", sequence=2),
            ],
        )
        assert flow.statuses[0].name == "First"
        assert flow.statuses[1].name == "Second"
        assert flow.statuses[2].name == "Third"

    def test_flow_duplicate_sequences_rejected(self):
        """Test that duplicate sequences are rejected."""
        with pytest.raises(ValidationError):
            StatusActionFlow(
                name="Test Flow",
                statuses=[
                    Status(name="First", sequence=1),
                    Status(name="Also First", sequence=1),
                ],
            )

    def test_get_status_by_name(self):
        """Test getting status by name."""
        flow = StatusActionFlow(
            name="Test Flow",
            statuses=[
                Status(name="On Site", sequence=1),
            ],
        )
        status = flow.get_status_by_name("on site")
        assert status is not None
        assert status.name == "On Site"


class TestExcelSchemas:
    """Tests for Excel import template schemas."""

    def test_job_custom_status_row(self):
        """Test JobCustomStatusRow validation."""
        row = JobCustomStatusRow(
            status_action_flow_name="Service Call",
            status_name="On Site",
            sequence=1,
        )
        assert row.status_action_flow_name == "Service Call"
        assert row.is_active is True

    def test_action_button_row(self):
        """Test ActionButtonRow validation."""
        row = ActionButtonRow(
            status_action_flow_name="Service Call",
            status_name="On Site",
            action_type=ActionButtonType.CLOCK_IN_OUT,
            button_label="Clock In",
        )
        assert row.user_role == UserRole.SERVICE_AGENT
        assert row.is_required is False

    def test_focus_view_row(self):
        """Test FocusViewRow validation."""
        row = FocusViewRow(
            status_action_flow_name="Service Call",
            status_name="On Site",
            widgets=[WidgetType.JOB_TITLE, WidgetType.ACTION_BUTTONS],
            status_instructions="1. Clock in\n2. Take photos",
        )
        assert len(row.widgets) == 2
        assert row.focus_view_enabled is True

    def test_excel_import_template(self):
        """Test complete ExcelImportTemplate validation."""
        template = ExcelImportTemplate(
            job_custom_statuses=[
                JobCustomStatusRow(
                    status_action_flow_name="Service Call",
                    status_name="On Site",
                    sequence=1,
                ),
                JobCustomStatusRow(
                    status_action_flow_name="Service Call",
                    status_name="Completed",
                    sequence=2,
                ),
            ],
            action_buttons=[
                ActionButtonRow(
                    status_action_flow_name="Service Call",
                    status_name="On Site",
                    action_type=ActionButtonType.CLOCK_IN_OUT,
                    button_label="Clock In",
                ),
            ],
            focus_view=[
                FocusViewRow(
                    status_action_flow_name="Service Call",
                    status_name="On Site",
                    widgets=[WidgetType.JOB_TITLE],
                ),
            ],
        )
        assert len(template.job_custom_statuses) == 2
        assert len(template.action_buttons) == 1

    def test_duplicate_status_names_rejected(self):
        """Test that duplicate status names in same flow are rejected."""
        with pytest.raises(ValidationError):
            ExcelImportTemplate(
                job_custom_statuses=[
                    JobCustomStatusRow(
                        status_action_flow_name="Service Call",
                        status_name="On Site",
                        sequence=1,
                    ),
                    JobCustomStatusRow(
                        status_action_flow_name="Service Call",
                        status_name="On Site",
                        sequence=2,
                    ),
                ],
            )

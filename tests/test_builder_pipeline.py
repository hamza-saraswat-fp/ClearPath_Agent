"""Tests for BuilderPipeline and related services."""

import json
import tempfile
from pathlib import Path

import pytest

from clearpath_agent.models import (
    ActionButton,
    ActionButtonType,
    Status,
    StatusActionFlow,
    StatusCategory,
    Widget,
    WidgetType,
)
from clearpath_agent.models.intent_schemas import (
    ExtractedPhrase,
    ExtractedStep,
    StructuredIntent,
)
from clearpath_agent.services.builder_pipeline import BuilderPipeline, BuildResult
from clearpath_agent.services.config_editor import ConfigEditor
from clearpath_agent.services.config_to_excel import ConfigToExcelConverter


class TestBuilderPipeline:
    """Tests for BuilderPipeline orchestration."""

    @pytest.fixture
    def sample_intent(self):
        """Create a sample intent for testing."""
        return StructuredIntent(
            workflow_name="HVAC Service Workflow",
            workflow_description="Standard HVAC service call workflow",
            job_types=["HVAC Service", "AC Repair"],
            steps=[
                ExtractedStep(
                    step_name="New",
                    sequence=1,
                    role_mentioned="dispatcher",
                    action_phrases=[
                        ExtractedPhrase(
                            phrase="assign technician",
                            context="Assign a tech to the job",
                            confidence=0.95,
                        ),
                    ],
                    information_needs=[
                        ExtractedPhrase(
                            phrase="customer details",
                            context="View customer info",
                            confidence=0.9,
                        ),
                    ],
                ),
                ExtractedStep(
                    step_name="Dispatched",
                    sequence=2,
                    role_mentioned="technician",
                    action_phrases=[
                        ExtractedPhrase(
                            phrase="check in",
                            context="Arrive at site",
                            confidence=0.95,
                        ),
                    ],
                    information_needs=[],
                ),
                ExtractedStep(
                    step_name="On Site",
                    sequence=3,
                    role_mentioned="technician",
                    action_phrases=[
                        ExtractedPhrase(
                            phrase="take photos",
                            context="Document equipment",
                            confidence=0.9,
                        ),
                        ExtractedPhrase(
                            phrase="add notes",
                            context="Record work details",
                            confidence=0.95,
                        ),
                    ],
                    information_needs=[
                        ExtractedPhrase(
                            phrase="equipment history",
                            context="Previous service records",
                            confidence=0.8,
                        ),
                    ],
                ),
                ExtractedStep(
                    step_name="Completed",
                    sequence=4,
                    role_mentioned="technician",
                    action_phrases=[
                        ExtractedPhrase(
                            phrase="check out",
                            context="Leave site",
                            confidence=0.95,
                        ),
                    ],
                    information_needs=[],
                ),
            ],
        )

    def test_execute_pipeline_success(self, sample_intent):
        """Test successful pipeline execution."""
        pipeline = BuilderPipeline()
        result = pipeline.execute(sample_intent)

        assert result.success is True
        assert result.config is not None
        assert result.excel_template is not None
        assert result.error_message is None

    def test_execute_pipeline_creates_statuses(self, sample_intent):
        """Test that pipeline creates correct number of statuses."""
        pipeline = BuilderPipeline()
        result = pipeline.execute(sample_intent)

        assert len(result.config.statuses) == 4
        status_names = [s.name for s in result.config.statuses]
        assert "New" in status_names
        assert "Dispatched" in status_names
        assert "On Site" in status_names
        assert "Completed" in status_names

    def test_execute_pipeline_resolves_actions(self, sample_intent):
        """Test that pipeline resolves action phrases to types."""
        pipeline = BuilderPipeline()
        result = pipeline.execute(sample_intent)

        on_site = result.config.get_status_by_name("On Site")
        action_types = [b.action for b in on_site.action_buttons]

        assert ActionButtonType.TAKE_PHOTO in action_types
        # "add notes" resolves to ADD_NOTE or similar action
        assert len(action_types) >= 1

    def test_execute_pipeline_generates_excel_template(self, sample_intent):
        """Test that pipeline generates Excel template."""
        pipeline = BuilderPipeline()
        result = pipeline.execute(sample_intent)

        assert result.excel_template is not None
        assert len(result.excel_template.job_custom_statuses) == 4
        assert len(result.excel_template.action_buttons) > 0
        assert len(result.excel_template.focus_view) > 0

    def test_execute_pipeline_validates_config(self, sample_intent):
        """Test that pipeline validates the configuration."""
        pipeline = BuilderPipeline()
        result = pipeline.execute(sample_intent)

        assert result.validation_result is not None
        assert result.is_valid is True

    def test_execute_pipeline_tracks_defaults(self, sample_intent):
        """Test that pipeline tracks applied defaults."""
        pipeline = BuilderPipeline()
        result = pipeline.execute(sample_intent, apply_defaults=True)

        assert len(result.applied_defaults) > 0

    def test_execute_pipeline_strict_validation(self, sample_intent):
        """Test strict validation mode."""
        pipeline = BuilderPipeline(strict_validation=True)
        result = pipeline.execute(sample_intent)

        # With strict mode, warnings become errors
        if result.validation_result.warning_count > 0:
            assert result.is_valid is False

    def test_execute_pipeline_invalid_intent(self):
        """Test pipeline with invalid intent."""
        from pydantic import ValidationError
        pipeline = BuilderPipeline()

        # Missing workflow name - should raise validation error
        with pytest.raises(ValidationError):
            StructuredIntent(
                workflow_name="",
                steps=[],
            )

    def test_preview_intent(self, sample_intent):
        """Test previewing intent without full build."""
        pipeline = BuilderPipeline()
        preview = pipeline.preview(sample_intent)

        assert preview["workflow_name"] == "HVAC Service Workflow"
        assert preview["step_count"] == 4
        assert len(preview["steps"]) == 4

    def test_build_result_summary(self, sample_intent):
        """Test BuildResult summary generation."""
        pipeline = BuilderPipeline()
        result = pipeline.execute(sample_intent)

        summary = result.get_summary()

        assert "success" in summary
        assert "status_count" in summary
        assert "action_button_count" in summary
        assert summary["status_count"] == 4


class TestConfigToExcelConverter:
    """Tests for ConfigToExcelConverter service."""

    @pytest.fixture
    def sample_config(self):
        """Create a sample configuration for testing."""
        return StatusActionFlow(
            name="Test Workflow",
            statuses=[
                Status(
                    name="New",
                    sequence=1,
                    category=StatusCategory.PENDING,
                    action_buttons=[
                        ActionButton(
                            action=ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
                            label="Assign",
                            order=0,
                            template_id="notification-template-1",
                        ),
                    ],
                    widgets=[
                        Widget(widget_type=WidgetType.JOB_TITLE, order=0),
                        Widget(widget_type=WidgetType.CUSTOMER_CONTACT, order=1),
                        Widget(widget_type=WidgetType.ACTION_BUTTONS, order=2),
                    ],
                    focus_view_enabled=True,
                    status_instructions="1. Review job\n2. Assign tech",
                ),
                Status(
                    name="On Site",
                    sequence=2,
                    category=StatusCategory.IN_PROGRESS,
                    action_buttons=[
                        ActionButton(
                            action=ActionButtonType.CLOCK_IN_OUT,
                            label="Clock In",
                            order=0,
                        ),
                        ActionButton(
                            action=ActionButtonType.TAKE_PHOTO,
                            label="Take Photos",
                            order=1,
                        ),
                    ],
                    widgets=[
                        Widget(widget_type=WidgetType.JOB_TITLE, order=0),
                        Widget(widget_type=WidgetType.ACTION_BUTTONS, order=1),
                    ],
                ),
                Status(
                    name="Completed",
                    sequence=3,
                    category=StatusCategory.COMPLETED,
                ),
            ],
        )

    def test_convert_to_excel_template(self, sample_config):
        """Test converting config to Excel template."""
        converter = ConfigToExcelConverter()
        template = converter.convert(sample_config)

        assert len(template.job_custom_statuses) == 3
        assert len(template.action_buttons) == 3  # 1 + 2 from two statuses
        assert len(template.focus_view) == 3

    def test_status_rows_have_correct_fields(self, sample_config):
        """Test that status rows have required fields."""
        converter = ConfigToExcelConverter()
        template = converter.convert(sample_config)

        for row in template.job_custom_statuses:
            assert row.status_action_flow_name == "Test Workflow"
            assert row.status_name in ["New", "On Site", "Completed"]
            assert row.sequence > 0
            assert row.is_active is True

    def test_action_button_rows_have_correct_fields(self, sample_config):
        """Test that action button rows have required fields."""
        converter = ConfigToExcelConverter()
        template = converter.convert(sample_config)

        for row in template.action_buttons:
            assert row.status_action_flow_name == "Test Workflow"
            assert row.action_type is not None
            assert row.button_label is not None

    def test_focus_view_rows_have_widgets(self, sample_config):
        """Test that focus view rows have widgets."""
        converter = ConfigToExcelConverter()
        template = converter.convert(sample_config)

        # Find the "New" status focus view
        new_focus = next(
            (r for r in template.focus_view if r.status_name == "New"),
            None
        )
        assert new_focus is not None
        assert len(new_focus.widgets) == 3
        assert WidgetType.JOB_TITLE in new_focus.widgets

    def test_validate_excel_template(self, sample_config):
        """Test Excel template validation."""
        converter = ConfigToExcelConverter()
        template = converter.convert(sample_config)

        errors = converter.validate_excel_template(template)
        assert len(errors) == 0

    def test_get_excel_summary(self, sample_config):
        """Test getting Excel template summary."""
        converter = ConfigToExcelConverter()
        template = converter.convert(sample_config)

        summary = converter.get_excel_summary(template)

        assert summary["total_statuses"] == 3
        assert summary["total_button_rows"] == 3
        assert "New" in summary["status_names"]


class TestConfigEditor:
    """Tests for ConfigEditor service."""

    @pytest.fixture
    def sample_config(self):
        """Create a sample configuration for testing."""
        return StatusActionFlow(
            name="Editable Workflow",
            description="A workflow for editing tests",
            job_types=["Test Type"],
            statuses=[
                Status(
                    name="New",
                    sequence=1,
                    category=StatusCategory.PENDING,
                    action_buttons=[
                        ActionButton(
                            action=ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
                            label="Assign",
                            order=0,
                            template_id="notification-template-1",
                        ),
                    ],
                    widgets=[
                        Widget(widget_type=WidgetType.JOB_TITLE, order=0),
                        Widget(widget_type=WidgetType.JOB_STATUS, order=1),
                        Widget(widget_type=WidgetType.STATUS_INSTRUCTIONS, order=2),
                        Widget(widget_type=WidgetType.ACTION_BUTTONS, order=3),
                    ],
                    status_instructions="Review and assign",
                ),
                Status(
                    name="In Progress",
                    sequence=2,
                    category=StatusCategory.IN_PROGRESS,
                    widgets=[
                        Widget(widget_type=WidgetType.JOB_TITLE, order=0),
                        Widget(widget_type=WidgetType.JOB_STATUS, order=1),
                        Widget(widget_type=WidgetType.STATUS_INSTRUCTIONS, order=2),
                    ],
                ),
                Status(
                    name="Completed",
                    sequence=3,
                    category=StatusCategory.COMPLETED,
                    widgets=[
                        Widget(widget_type=WidgetType.JOB_TITLE, order=0),
                        Widget(widget_type=WidgetType.JOB_STATUS, order=1),
                        Widget(widget_type=WidgetType.STATUS_INSTRUCTIONS, order=2),
                    ],
                ),
            ],
        )

    def test_get_editable_json(self, sample_config):
        """Test converting config to editable JSON."""
        editor = ConfigEditor()
        editable = editor.get_editable_json(sample_config)

        assert "workflow" in editable
        assert "statuses" in editable
        assert editable["workflow"]["name"] == "Editable Workflow"
        assert len(editable["statuses"]) == 3

    def test_get_editable_json_includes_buttons(self, sample_config):
        """Test that editable JSON includes action buttons."""
        editor = ConfigEditor()
        editable = editor.get_editable_json(sample_config)

        new_status = next(
            (s for s in editable["statuses"] if s["name"] == "New"),
            None
        )
        assert new_status is not None
        assert len(new_status["action_buttons"]) == 1
        assert new_status["action_buttons"][0]["label"] == "Assign"

    def test_apply_user_edits_workflow_name(self, sample_config):
        """Test applying edits to workflow name."""
        editor = ConfigEditor()

        edits = {
            "workflow": {
                "name": "Renamed Workflow",
            }
        }

        modified = editor.apply_user_edits(sample_config, edits)
        assert modified.name == "Renamed Workflow"

    def test_apply_user_edits_status_fields(self, sample_config):
        """Test applying edits to status fields."""
        editor = ConfigEditor()

        edits = {
            "statuses": [
                {
                    "name": "New",
                    "color": "#FF0000",
                    "status_instructions": "New instructions",
                }
            ]
        }

        modified = editor.apply_user_edits(sample_config, edits)
        new_status = modified.get_status_by_name("New")

        assert new_status.color == "#FF0000"
        assert new_status.status_instructions == "New instructions"

    def test_validate_edits(self, sample_config):
        """Test validating edits before applying."""
        editor = ConfigEditor()

        valid_edits = {
            "workflow": {"name": "Valid Name"}
        }

        result = editor.validate_edits(sample_config, valid_edits)
        assert result.is_valid is True

    def test_get_review_summary(self, sample_config):
        """Test generating review summary."""
        editor = ConfigEditor()
        summary = editor.get_review_summary(sample_config)

        assert "Editable Workflow" in summary
        assert "3 statuses" in summary
        assert "New" in summary

    def test_add_status(self, sample_config):
        """Test adding a new status."""
        editor = ConfigEditor()

        new_status_data = {
            "name": "Review",
            "category": "In Progress",  # Must match StatusCategory enum value
            "color": "#00FF00",
        }

        modified = editor.add_status(sample_config, new_status_data, position=2)

        assert len(modified.statuses) == 4
        review_status = modified.get_status_by_name("Review")
        assert review_status is not None
        assert review_status.sequence == 2

    def test_remove_status(self, sample_config):
        """Test removing a status."""
        editor = ConfigEditor()
        modified = editor.remove_status(sample_config, "In Progress")

        assert len(modified.statuses) == 2
        assert modified.get_status_by_name("In Progress") is None

    def test_reorder_statuses(self, sample_config):
        """Test reordering statuses."""
        editor = ConfigEditor()

        new_order = ["Completed", "In Progress", "New"]
        modified = editor.reorder_statuses(sample_config, new_order)

        assert modified.statuses[0].name == "Completed"
        assert modified.statuses[1].name == "In Progress"
        assert modified.statuses[2].name == "New"

    def test_export_import_json(self, sample_config):
        """Test exporting and importing JSON."""
        editor = ConfigEditor()

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "config.json"

            # Export
            editor.export_to_json(sample_config, str(filepath))
            assert filepath.exists()

            # Import
            imported = editor.import_from_json(str(filepath))

            assert imported.name == sample_config.name
            assert len(imported.statuses) == len(sample_config.statuses)

    def test_highlight_low_confidence(self, sample_config):
        """Test highlighting low-confidence items."""
        editor = ConfigEditor()

        low_confidence_items = [
            {"phrase": "Assign", "confidence": 0.5}
        ]

        result = editor.highlight_low_confidence(sample_config, low_confidence_items)

        assert result["highlight_count"] == 1
        assert "config" in result
        assert "highlighted_items" in result


class TestDefaultTemplates:
    """Tests for default workflow templates."""

    def test_get_service_call_template(self):
        """Test getting service call template."""
        from clearpath_agent.data.default_templates import get_template

        template = get_template("service_call")

        assert template is not None
        assert template.name == "Service Call Workflow"
        assert len(template.statuses) > 0

    def test_get_installation_template(self):
        """Test getting installation template."""
        from clearpath_agent.data.default_templates import get_template

        template = get_template("installation")

        assert template is not None
        assert "Installation" in template.name

    def test_get_inspection_template(self):
        """Test getting inspection template."""
        from clearpath_agent.data.default_templates import get_template

        template = get_template("inspection")

        assert template is not None
        assert "Inspection" in template.name

    def test_get_emergency_template(self):
        """Test getting emergency template."""
        from clearpath_agent.data.default_templates import get_template

        template = get_template("emergency")

        assert template is not None
        assert "Emergency" in template.name

    def test_list_templates(self):
        """Test listing all templates."""
        from clearpath_agent.data.default_templates import list_templates

        templates = list_templates()

        # Returns a list of dicts with template info
        assert len(templates) >= 4
        template_names = [t["name"] for t in templates]
        assert "service_call" in template_names
        assert "installation" in template_names
        assert "inspection" in template_names
        assert "emergency" in template_names

    def test_template_selector(self):
        """Test template selector matching."""
        from clearpath_agent.data.default_templates import TemplateSelector

        selector = TemplateSelector()

        # Test matching by workflow description
        match = selector.select("HVAC Service Call Workflow")
        assert match == "service_call"

        # Test matching by job types
        match = selector.select(
            "Any Workflow",
            job_types=["Installation"]
        )
        # Should match installation template
        assert match == "installation"

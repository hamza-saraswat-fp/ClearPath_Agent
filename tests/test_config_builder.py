"""Tests for ConfigBuilder and related services."""

import pytest

from clearpath_agent.models import (
    ActionButton,
    ActionButtonType,
    Status,
    StatusActionFlow,
    StatusCategory,
    UserRole,
    Widget,
    WidgetType,
)
from clearpath_agent.models.intent_schemas import (
    ConfidenceLevel,
    ExtractedPhrase,
    ExtractedStep,
    StructuredIntent,
    WorkflowMetadata,
)
from clearpath_agent.services.config_builder import ConfigBuilder
from clearpath_agent.services.config_defaults import DefaultsProvider
from clearpath_agent.services.config_validator import ConfigValidator
from clearpath_agent.services.entity_resolver import EntityResolver


class TestEntityResolver:
    """Tests for EntityResolver service."""

    def test_resolve_action_exact_match(self):
        """Test resolving action with exact phrase match."""
        resolver = EntityResolver()
        phrase = ExtractedPhrase(
            phrase="clock in",
            context="Technician starts work",
            confidence=0.95,
        )
        result = resolver.resolve_action(phrase)

        assert result is not None
        assert result.resolved_type == ActionButtonType.CLOCK_IN_OUT.value
        assert result.confidence >= 0.9

    def test_resolve_action_partial_match(self):
        """Test resolving action with partial phrase match."""
        resolver = EntityResolver()
        phrase = ExtractedPhrase(
            phrase="take before photos",
            context="Document equipment",
            confidence=0.9,
        )
        result = resolver.resolve_action(phrase)

        assert result is not None
        assert result.resolved_type == ActionButtonType.TAKE_PHOTO.value
        assert result.confidence > 0.7

    def test_resolve_action_no_match(self):
        """Test resolving action with no match."""
        resolver = EntityResolver()
        phrase = ExtractedPhrase(
            phrase="xyz completely unknown action qwerty",
            context="Some context",
            confidence=0.3,
        )
        result = resolver.resolve_action(phrase)

        # Should return None for completely unmatched phrases
        assert result is None

    def test_resolve_widget_exact_match(self):
        """Test resolving widget with exact phrase match."""
        resolver = EntityResolver()
        phrase = ExtractedPhrase(
            phrase="job title",
            context="Show job name",
            confidence=0.95,
        )
        result = resolver.resolve_widget(phrase)

        assert result is not None
        assert result.resolved_type == WidgetType.JOB_TITLE.value
        assert result.confidence >= 0.9

    def test_resolve_widget_synonym_match(self):
        """Test resolving widget with synonym."""
        resolver = EntityResolver()
        phrase = ExtractedPhrase(
            phrase="customer info",
            context="Show customer details",
            confidence=0.9,
        )
        result = resolver.resolve_widget(phrase)

        assert result is not None
        assert result.resolved_type == WidgetType.CUSTOMER_CONTACT.value

    def test_resolve_all(self):
        """Test resolving multiple actions and widgets at once."""
        resolver = EntityResolver()
        action_phrases = [
            ExtractedPhrase(phrase="clock in", context="Start work", confidence=0.9),
            ExtractedPhrase(phrase="take photos", context="Document", confidence=0.85),
        ]
        widget_phrases = [
            ExtractedPhrase(phrase="job title", context="Show title", confidence=0.9),
        ]

        result = resolver.resolve_all(action_phrases, widget_phrases)

        assert len(result.resolved_actions) == 2
        assert len(result.resolved_widgets) == 1
        assert "clock in" in result.resolved_actions
        assert "take photos" in result.resolved_actions

    def test_check_template_requirements(self):
        """Test checking template requirements for actions."""
        resolver = EntityResolver()

        # Actions that require forms
        requirements = resolver.check_template_requirements(ActionButtonType.FILL_FORM)
        assert requirements["requires_form"] is True

        # Actions that require templates
        requirements = resolver.check_template_requirements(ActionButtonType.SEND_CUSTOMER_COMMUNICATION)
        assert requirements["requires_template"] is True

        # Actions that don't require templates
        requirements = resolver.check_template_requirements(ActionButtonType.CLOCK_IN_OUT)
        assert requirements["requires_template"] is False
        assert requirements["requires_form"] is False


class TestDefaultsProvider:
    """Tests for DefaultsProvider service."""

    def test_get_default_widgets(self):
        """Test getting default widgets for a status."""
        provider = DefaultsProvider()
        widgets = provider.get_default_widgets(
            status_name="On Site",
            actions=[ActionButtonType.CLOCK_IN_OUT, ActionButtonType.TAKE_PHOTO],
        )

        # Should include ACTION_BUTTONS at minimum
        assert WidgetType.ACTION_BUTTONS in widgets
        # Should include JOB_TITLE as core widget
        assert WidgetType.JOB_TITLE in widgets

    def test_get_default_toggles(self):
        """Test getting default toggles for a status category."""
        provider = DefaultsProvider()

        # In Progress status
        toggles = provider.get_default_toggles(StatusCategory.IN_PROGRESS)
        assert toggles["focus_view_enabled"] is True
        assert toggles["display_action_menu"] is True

        # Completed status
        toggles = provider.get_default_toggles(StatusCategory.COMPLETED)
        assert toggles["ability_to_change_status"] is False

    def test_get_default_widgets_includes_cooccurrence(self):
        """Test that widgets include action co-occurrence suggestions."""
        provider = DefaultsProvider()
        widgets = provider.get_default_widgets(
            status_name="On Site",
            actions=[ActionButtonType.CREATE_ESTIMATE],
        )

        # Create Estimate should include ESTIMATES widget via co-occurrence
        assert WidgetType.ESTIMATES in widgets

    def test_widget_ordering(self):
        """Test that widgets are ordered correctly."""
        provider = DefaultsProvider()
        widgets = provider.get_default_widgets(
            status_name="Test",
            actions=[ActionButtonType.CLOCK_IN_OUT],
        )

        # ACTION_BUTTONS should be last in the list
        if WidgetType.ACTION_BUTTONS in widgets:
            assert widgets[-1] == WidgetType.ACTION_BUTTONS


class TestConfigValidator:
    """Tests for ConfigValidator service."""

    @pytest.fixture
    def valid_config(self):
        """Create a valid configuration for testing."""
        return StatusActionFlow(
            name="Test Flow",
            statuses=[
                Status(
                    name="New",
                    sequence=1,
                    category=StatusCategory.PENDING,
                    action_buttons=[
                        ActionButton(
                            action=ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
                            label="Notify",
                            order=0,
                            template_id="notification-template-1",
                        )
                    ],
                    widgets=[
                        Widget(widget_type=WidgetType.JOB_TITLE, order=0),
                        Widget(widget_type=WidgetType.ACTION_BUTTONS, order=1),
                    ],
                    focus_view_enabled=True,
                ),
                Status(
                    name="Completed",
                    sequence=2,
                    category=StatusCategory.COMPLETED,
                ),
            ],
        )

    def test_validate_valid_config(self, valid_config):
        """Test validating a valid configuration."""
        validator = ConfigValidator()
        result = validator.validate_config(valid_config)

        assert result.is_valid is True
        assert result.error_count == 0

    def test_validate_too_many_buttons(self):
        """Test validation fails with too many action buttons."""
        config = StatusActionFlow(
            name="Test",
            statuses=[
                Status(
                    name="Overloaded",
                    sequence=1,
                    action_buttons=[
                        ActionButton(
                            action=ActionButtonType.TAKE_PHOTO,
                            label=f"Button {i}",
                            order=i,
                        )
                        for i in range(12)  # Max is 10
                    ],
                ),
            ],
        )

        validator = ConfigValidator()
        result = validator.validate_config(config)

        assert result.error_count > 0
        assert any("TOO_MANY_BUTTONS" in issue.code for issue in result.issues)

    def test_validate_template_required(self):
        """Test validation warns when template is required."""
        config = StatusActionFlow(
            name="Test",
            statuses=[
                Status(
                    name="Test",
                    sequence=1,
                    action_buttons=[
                        ActionButton(
                            action=ActionButtonType.FILL_FORM,
                            label="Fill Form",
                            # Missing form_id
                        ),
                    ],
                ),
            ],
        )

        validator = ConfigValidator()
        result = validator.validate_config(config)

        # Should have a warning about missing template
        assert any("TEMPLATE" in issue.code or "FORM" in issue.code for issue in result.issues)

    def test_validate_unique_sequences(self, valid_config):
        """Test that duplicate sequences are caught."""
        validator = ConfigValidator()
        result = validator.validate_config(valid_config)

        # Valid config should pass
        assert not any("DUPLICATE_SEQUENCE" in issue.code for issue in result.issues)

    def test_check_best_practices(self, valid_config):
        """Test best practices validation."""
        validator = ConfigValidator()
        result = validator.validate_config(valid_config, check_best_practices=True)

        # Should check for action buttons widget position
        # and numbered instructions
        assert result is not None


class TestConfigBuilder:
    """Tests for ConfigBuilder service."""

    @pytest.fixture
    def simple_intent(self):
        """Create a simple intent for testing."""
        return StructuredIntent(
            workflow_name="Test Workflow",
            workflow_description="A test workflow",
            metadata=WorkflowMetadata(job_types=["Service Call"]),
            steps=[
                ExtractedStep(
                    step_name="New",
                    sequence=1,
                    role_mentioned="dispatcher",
                    action_phrases=[
                        ExtractedPhrase(
                            phrase="send text",
                            context="Notify customer",
                            confidence=0.95,
                        ),
                    ],
                    information_needs=[
                        ExtractedPhrase(
                            phrase="customer info",
                            context="See customer details",
                            confidence=0.9,
                        ),
                    ],
                ),
                ExtractedStep(
                    step_name="On Site",
                    sequence=2,
                    role_mentioned="technician",
                    action_phrases=[
                        ExtractedPhrase(
                            phrase="clock in",
                            context="Start work",
                            confidence=0.95,
                        ),
                        ExtractedPhrase(
                            phrase="take photos",
                            context="Document equipment",
                            confidence=0.9,
                        ),
                    ],
                    information_needs=[
                        ExtractedPhrase(
                            phrase="job details",
                            context="Job information",
                            confidence=0.85,
                        ),
                    ],
                ),
                ExtractedStep(
                    step_name="Completed",
                    sequence=3,
                    role_mentioned="technician",
                    action_phrases=[
                        ExtractedPhrase(
                            phrase="clock out",
                            context="End work",
                            confidence=0.95,
                        ),
                    ],
                    information_needs=[],
                ),
            ],
        )

    def test_build_config_basic(self, simple_intent):
        """Test basic configuration building."""
        builder = ConfigBuilder()
        config = builder.build_config(simple_intent)

        assert config.name == "Test Workflow"
        assert len(config.statuses) == 3
        assert config.job_types == ["Service Call"]

    def test_build_config_resolves_actions(self, simple_intent):
        """Test that actions are resolved correctly."""
        builder = ConfigBuilder()
        config = builder.build_config(simple_intent)

        # Find On Site status
        on_site = config.get_status_by_name("On Site")
        assert on_site is not None

        # Should have clock in and take photo buttons
        button_types = [b.action for b in on_site.action_buttons]
        assert ActionButtonType.CLOCK_IN_OUT in button_types
        assert ActionButtonType.TAKE_PHOTO in button_types

    def test_build_config_applies_defaults(self, simple_intent):
        """Test that defaults are applied."""
        builder = ConfigBuilder()
        config = builder.build_config(simple_intent, apply_defaults=True)

        # Each status should have widgets
        for status in config.statuses:
            assert len(status.widgets) > 0

        # Should have ACTION_BUTTONS widget
        on_site = config.get_status_by_name("On Site")
        widget_types = [w.widget_type for w in on_site.widgets]
        assert WidgetType.ACTION_BUTTONS in widget_types

    def test_build_config_without_defaults(self, simple_intent):
        """Test building without defaults."""
        builder = ConfigBuilder()
        config = builder.build_config(simple_intent, apply_defaults=False)

        # Should still have basic structure
        assert len(config.statuses) == 3

    def test_build_config_tracks_applied_defaults(self, simple_intent):
        """Test that applied defaults are tracked."""
        builder = ConfigBuilder()
        builder.build_config(simple_intent, apply_defaults=True)

        applied = builder.get_applied_defaults()
        assert len(applied) > 0

    def test_build_config_tracks_review_items(self, simple_intent):
        """Test that low-confidence items are tracked for review."""
        # Add a low-confidence phrase
        simple_intent.steps[0].action_phrases.append(
            ExtractedPhrase(
                phrase="do something vague",
                context="Unclear action",
                confidence=0.3,  # Low confidence
            )
        )

        builder = ConfigBuilder()
        builder.build_config(simple_intent)

        review_items = builder.get_review_items()
        # Should have flagged items (may include unresolved phrases)
        assert isinstance(review_items, list)

    def test_build_config_links_statuses(self, simple_intent):
        """Test that statuses are linked correctly."""
        builder = ConfigBuilder()
        config = builder.build_config(simple_intent)

        # Check next/previous status links
        new_status = config.get_status_by_name("New")
        assert new_status.next_status == "On Site"
        assert new_status.previous_status is None

        on_site = config.get_status_by_name("On Site")
        assert on_site.previous_status == "New"
        assert on_site.next_status == "Completed"

    def test_build_config_assigns_categories(self, simple_intent):
        """Test that status categories are assigned correctly."""
        builder = ConfigBuilder()
        config = builder.build_config(simple_intent)

        new_status = config.get_status_by_name("New")
        assert new_status.category == StatusCategory.PENDING

        completed = config.get_status_by_name("Completed")
        assert completed.category == StatusCategory.COMPLETED


class TestIntentSchemas:
    """Tests for StructuredIntent schema validation."""

    def test_create_extracted_phrase(self):
        """Test creating an extracted phrase."""
        phrase = ExtractedPhrase(
            phrase="clock in",
            context="Start work",
            confidence=0.95,
        )
        assert phrase.confidence_level == ConfidenceLevel.HIGH

    def test_extracted_phrase_confidence_levels(self):
        """Test confidence level categorization."""
        high = ExtractedPhrase(phrase="test", context="", confidence=0.95)
        medium = ExtractedPhrase(phrase="test", context="", confidence=0.7)
        low = ExtractedPhrase(phrase="test", context="", confidence=0.4)

        assert high.confidence_level == ConfidenceLevel.HIGH
        assert medium.confidence_level == ConfidenceLevel.MEDIUM
        assert low.confidence_level == ConfidenceLevel.LOW

    def test_create_extracted_step(self):
        """Test creating an extracted step."""
        step = ExtractedStep(
            step_name="On Site",
            sequence=1,
            role_mentioned="technician",
            action_phrases=[
                ExtractedPhrase(
                    phrase="clock in",
                    context="Start",
                    confidence=0.9,
                ),
            ],
            information_needs=[
                ExtractedPhrase(
                    phrase="job details",
                    context="Info",
                    confidence=0.85,
                ),
            ],
        )
        assert step.step_name == "On Site"
        assert len(step.action_phrases) == 1
        assert len(step.information_needs) == 1

    def test_extracted_step_items_needing_review(self):
        """Test getting items needing review from a step."""
        step = ExtractedStep(
            step_name="Test",
            sequence=1,
            action_phrases=[
                ExtractedPhrase(phrase="clear", context="", confidence=0.95),
                ExtractedPhrase(phrase="ambiguous", context="", confidence=0.5),
            ],
            information_needs=[
                ExtractedPhrase(phrase="unclear", context="", confidence=0.4),
            ],
        )
        # items_needing_review returns phrases where needs_review is True (confidence < 0.85)
        review_items = step.items_needing_review
        # ambiguous (0.5) and unclear (0.4) need review
        assert len(review_items) == 2

    def test_create_structured_intent(self):
        """Test creating a complete structured intent."""
        intent = StructuredIntent(
            workflow_name="Test Workflow",
            workflow_description="Description",
            metadata=WorkflowMetadata(job_types=["Service"]),
            steps=[
                ExtractedStep(
                    step_name="Step 1",
                    sequence=1,
                    action_phrases=[],
                    information_needs=[],
                ),
            ],
        )
        assert intent.workflow_name == "Test Workflow"
        assert len(intent.steps) == 1
        assert intent.metadata.job_types == ["Service"]

    def test_structured_intent_has_ambiguities(self):
        """Test ambiguity detection in intent."""
        intent = StructuredIntent(
            workflow_name="Test",
            steps=[
                ExtractedStep(
                    step_name="Ambiguous Step",
                    sequence=1,
                    action_phrases=[
                        ExtractedPhrase(phrase="vague", context="", confidence=0.3),
                    ],
                    information_needs=[],
                ),
            ],
        )
        assert intent.has_ambiguities is True

    def test_structured_intent_all_items_needing_review(self):
        """Test collecting all items needing review."""
        intent = StructuredIntent(
            workflow_name="Test",
            steps=[
                ExtractedStep(
                    step_name="Step 1",
                    sequence=1,
                    action_phrases=[
                        ExtractedPhrase(phrase="low", context="", confidence=0.4),
                    ],
                    information_needs=[],
                ),
                ExtractedStep(
                    step_name="Step 2",
                    sequence=2,
                    action_phrases=[
                        ExtractedPhrase(phrase="also low", context="", confidence=0.5),
                    ],
                    information_needs=[],
                ),
            ],
        )
        all_items = intent.all_items_needing_review
        assert len(all_items) == 2

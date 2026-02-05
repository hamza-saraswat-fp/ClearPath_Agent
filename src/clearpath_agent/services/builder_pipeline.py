"""Builder Pipeline Orchestrator.

Chains all ConfigBuilder components together to execute the complete
build process from Structured Intent to ExcelImportTemplate.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from ..models.entities import StatusActionFlow
from ..models.excel_schemas import ExcelImportTemplate
from ..models.intent_schemas import StructuredIntent
from .config_builder import ConfigBuilder
from .config_defaults import DefaultsProvider
from .config_to_excel import ConfigToExcelConverter
from .config_validator import ConfigValidator, ValidationResult
from .entity_resolver import EntityResolver

logger = logging.getLogger(__name__)


@dataclass
class BuildResult:
    """Result of the complete build pipeline."""

    # Main outputs
    config: Optional[StatusActionFlow] = None
    excel_template: Optional[ExcelImportTemplate] = None

    # Validation
    validation_result: Optional[ValidationResult] = None
    is_valid: bool = False

    # Review items
    low_confidence_items: list[dict] = field(default_factory=list)
    template_required_items: list[dict] = field(default_factory=list)

    # Transparency
    applied_defaults: list[str] = field(default_factory=list)
    build_warnings: list[str] = field(default_factory=list)

    # Status
    success: bool = False
    error_message: Optional[str] = None

    def get_summary(self) -> dict:
        """Get a summary of the build result."""
        return {
            "success": self.success,
            "is_valid": self.is_valid,
            "status_count": len(self.config.statuses) if self.config else 0,
            "action_button_count": sum(
                len(s.action_buttons) for s in self.config.statuses
            ) if self.config else 0,
            "validation_errors": self.validation_result.error_count if self.validation_result else 0,
            "validation_warnings": self.validation_result.warning_count if self.validation_result else 0,
            "low_confidence_items": len(self.low_confidence_items),
            "template_required_items": len(self.template_required_items),
            "defaults_applied": len(self.applied_defaults),
            "error_message": self.error_message,
        }


class BuilderPipeline:
    """Orchestrates the complete build process.

    Pipeline steps:
    1. Validate input intent schema
    2. Resolve all phrases to canonical entities
    3. Build configuration using ConfigBuilder
    4. Validate configuration using ConfigValidator
    5. Convert to Excel schema using ConfigToExcelConverter
    6. Final validation of Excel schema
    """

    def __init__(
        self,
        vector_store=None,
        graph_store=None,
        strict_validation: bool = False,
    ):
        """Initialize the builder pipeline.

        Args:
            vector_store: Optional VectorStore for knowledge base lookups
            graph_store: Optional GraphStore for relationship lookups
            strict_validation: If True, warnings are treated as errors
        """
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.strict_validation = strict_validation

        # Initialize components
        self.resolver = EntityResolver(vector_store=vector_store)
        self.defaults_provider = DefaultsProvider(
            vector_store=vector_store,
            graph_store=graph_store,
        )
        self.builder = ConfigBuilder(
            resolver=self.resolver,
            defaults_provider=self.defaults_provider,
            vector_store=vector_store,
            graph_store=graph_store,
        )
        self.validator = ConfigValidator()
        self.converter = ConfigToExcelConverter()

    def execute(
        self,
        intent: StructuredIntent,
        apply_defaults: bool = True,
        apply_best_practices: bool = True,
        validate_excel: bool = True,
    ) -> BuildResult:
        """Execute the complete build pipeline.

        Args:
            intent: The structured intent from LLM extraction
            apply_defaults: Whether to apply default widgets/toggles
            apply_best_practices: Whether to enforce best practices
            validate_excel: Whether to validate the Excel template

        Returns:
            BuildResult with all outputs and status
        """
        result = BuildResult()

        try:
            logger.info(f"Starting build pipeline for: {intent.workflow_name}")

            # Step 1: Validate input intent
            self._validate_intent(intent, result)
            if result.error_message:
                return result

            # Step 2 & 3: Build configuration (includes resolution)
            config = self.builder.build_config(
                intent=intent,
                apply_defaults=apply_defaults,
                apply_best_practices=apply_best_practices,
            )
            result.config = config
            result.applied_defaults = self.builder.get_applied_defaults()
            result.low_confidence_items = [
                item for item in self.builder.get_review_items()
                if item.get("confidence", 1.0) < 0.85
            ]
            result.template_required_items = [
                item for item in self.builder.get_review_items()
                if item.get("type") == "template_required"
            ]

            logger.info(f"Built config with {len(config.statuses)} statuses")

            # Step 4: Validate configuration
            validation_result = self.validator.validate_config(
                config=config,
                check_best_practices=apply_best_practices,
            )
            result.validation_result = validation_result
            result.is_valid = validation_result.is_valid

            # Check if we should stop on warnings
            if self.strict_validation and validation_result.warning_count > 0:
                result.is_valid = False
                result.build_warnings.append(
                    f"Strict validation: {validation_result.warning_count} warnings treated as errors"
                )

            # Log validation issues
            for issue in validation_result.issues:
                if issue.severity.value == "error":
                    logger.error(str(issue))
                elif issue.severity.value == "warning":
                    logger.warning(str(issue))
                else:
                    logger.info(str(issue))

            # Step 5: Convert to Excel schema
            excel_template = self.converter.convert(config)
            result.excel_template = excel_template

            logger.info(
                f"Generated Excel template: "
                f"{len(excel_template.job_custom_statuses)} statuses, "
                f"{len(excel_template.action_buttons)} button rows"
            )

            # Step 6: Validate Excel schema
            if validate_excel:
                excel_errors = self.converter.validate_excel_template(excel_template)
                if excel_errors:
                    for error in excel_errors:
                        result.build_warnings.append(f"Excel validation: {error}")
                    logger.warning(f"Excel validation found {len(excel_errors)} issues")

            # Mark success if we got this far without errors
            result.success = result.is_valid
            if not result.success and result.validation_result:
                result.error_message = f"Validation failed with {result.validation_result.error_count} errors"

            logger.info(f"Build pipeline complete: success={result.success}")

        except Exception as e:
            logger.exception("Build pipeline failed")
            result.success = False
            result.error_message = str(e)

        return result

    def _validate_intent(
        self,
        intent: StructuredIntent,
        result: BuildResult,
    ) -> None:
        """Validate the input structured intent.

        Args:
            intent: The intent to validate
            result: BuildResult to update with errors
        """
        # Check workflow name
        if not intent.workflow_name or not intent.workflow_name.strip():
            result.error_message = "Workflow name is required"
            result.success = False
            return

        # Check steps
        if not intent.steps or len(intent.steps) == 0:
            result.error_message = "At least one workflow step is required"
            result.success = False
            return

        # Check for ambiguities
        if intent.has_ambiguities:
            items = intent.all_items_needing_review
            result.build_warnings.append(
                f"Intent has {len(items)} items needing review"
            )

    def execute_with_review(
        self,
        intent: StructuredIntent,
        user_resolutions: Optional[dict] = None,
    ) -> BuildResult:
        """Execute the pipeline with user review support.

        Allows users to provide resolutions for ambiguous items
        before building the final configuration.

        Args:
            intent: The structured intent
            user_resolutions: Dict mapping phrases to resolved types
                Example: {"send text to customer": "Send Customer Communication"}

        Returns:
            BuildResult with all outputs
        """
        # Apply user resolutions to intent
        if user_resolutions:
            intent = self._apply_user_resolutions(intent, user_resolutions)

        return self.execute(intent)

    def _apply_user_resolutions(
        self,
        intent: StructuredIntent,
        resolutions: dict,
    ) -> StructuredIntent:
        """Apply user-provided resolutions to ambiguous phrases.

        Args:
            intent: The original intent
            resolutions: Dict mapping phrases to resolved types

        Returns:
            Modified StructuredIntent with resolutions applied
        """
        # Create a copy of the intent
        intent_dict = intent.model_dump()

        for step_dict in intent_dict["steps"]:
            # Apply to action phrases
            for phrase_dict in step_dict["action_phrases"]:
                phrase = phrase_dict["phrase"]
                if phrase in resolutions:
                    phrase_dict["suggested_type"] = resolutions[phrase]
                    phrase_dict["confidence"] = 1.0  # User confirmed

            # Apply to information needs
            for phrase_dict in step_dict["information_needs"]:
                phrase = phrase_dict["phrase"]
                if phrase in resolutions:
                    phrase_dict["suggested_type"] = resolutions[phrase]
                    phrase_dict["confidence"] = 1.0  # User confirmed

        return StructuredIntent(**intent_dict)

    def preview(
        self,
        intent: StructuredIntent,
    ) -> dict:
        """Preview the build without generating full output.

        Useful for showing users what will be built before confirming.

        Args:
            intent: The structured intent

        Returns:
            Dict with preview information
        """
        preview = {
            "workflow_name": intent.workflow_name,
            "description": intent.workflow_description,
            "step_count": len(intent.steps),
            "steps": [],
            "ambiguities": intent.all_items_needing_review,
            "warnings": [],
        }

        for step in intent.steps:
            step_preview = {
                "name": step.step_name,
                "sequence": step.sequence,
                "action_count": len(step.action_phrases),
                "widget_count": len(step.information_needs),
                "actions": [p.phrase for p in step.action_phrases],
                "widgets": [p.phrase for p in step.information_needs],
            }
            preview["steps"].append(step_preview)

        # Add warnings for common issues
        total_actions = sum(len(s.action_phrases) for s in intent.steps)
        if total_actions == 0:
            preview["warnings"].append("No action buttons defined")

        if intent.has_ambiguities:
            preview["warnings"].append(
                f"{len(preview['ambiguities'])} items need clarification"
            )

        return preview

    def build_from_template(
        self,
        template_name: str,
        customizations: Optional[dict] = None,
    ) -> BuildResult:
        """Build a configuration from a predefined template.

        Args:
            template_name: Name of the template to use
            customizations: Optional customizations to apply

        Returns:
            BuildResult with the template-based configuration
        """
        result = BuildResult()

        try:
            # Get template
            config = self.builder.build_from_template(
                template_name=template_name,
                customizations=customizations,
            )
            result.config = config

            # Validate
            validation_result = self.validator.validate_config(config)
            result.validation_result = validation_result
            result.is_valid = validation_result.is_valid

            # Convert to Excel
            excel_template = self.converter.convert(config)
            result.excel_template = excel_template

            result.success = result.is_valid

        except Exception as e:
            logger.exception(f"Failed to build from template '{template_name}'")
            result.success = False
            result.error_message = str(e)

        return result


def create_pipeline(
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
    neo4j_uri: Optional[str] = None,
    neo4j_user: Optional[str] = None,
    neo4j_password: Optional[str] = None,
) -> BuilderPipeline:
    """Create a BuilderPipeline with optional knowledge base connections.

    Args:
        supabase_url: Supabase project URL
        supabase_key: Supabase API key
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password

    Returns:
        Configured BuilderPipeline
    """
    vector_store = None
    graph_store = None

    # Initialize vector store if credentials provided
    if supabase_url and supabase_key:
        try:
            from .vector_store import VectorStore
            vector_store = VectorStore(
                supabase_url=supabase_url,
                supabase_key=supabase_key,
            )
            logger.info("Connected to Supabase vector store")
        except Exception as e:
            logger.warning(f"Could not connect to Supabase: {e}")

    # Initialize graph store if credentials provided
    if neo4j_uri and neo4j_password:
        try:
            from .graph_store import GraphStore
            graph_store = GraphStore(
                uri=neo4j_uri,
                user=neo4j_user or "neo4j",
                password=neo4j_password,
            )
            logger.info("Connected to Neo4j graph store")
        except Exception as e:
            logger.warning(f"Could not connect to Neo4j: {e}")

    return BuilderPipeline(
        vector_store=vector_store,
        graph_store=graph_store,
    )

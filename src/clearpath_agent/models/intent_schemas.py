"""Pydantic schemas for Structured Intent JSON from LLM extraction.

These schemas define the input format for the ConfigBuilder, representing
the output from Phase 2 (LLM Semantic Extraction).
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ConfidenceLevel(str, Enum):
    """Confidence levels for phrase matching."""

    HIGH = "high"  # > 0.85 - auto-accept
    MEDIUM = "medium"  # 0.6-0.85 - flag for review
    LOW = "low"  # < 0.6 - reject or require clarification


class ExtractedPhrase(BaseModel):
    """A phrase extracted from user input with confidence scoring.

    Represents an action or widget phrase identified by the LLM
    that needs to be resolved to a canonical entity.
    """

    phrase: str = Field(
        ...,
        min_length=1,
        description="The original phrase from user input",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for this phrase (0-1)",
    )
    suggested_type: Optional[str] = Field(
        default=None,
        description="LLM's suggested canonical type (action or widget name)",
    )
    alternatives: list[str] = Field(
        default_factory=list,
        description="Alternative interpretations for ambiguous phrases",
    )
    requires_template: bool = Field(
        default=False,
        description="Whether this action requires a template_id or form_id",
    )
    template_hint: Optional[str] = Field(
        default=None,
        description="Hint about which template to use (e.g., 'arrival SMS')",
    )
    context: str = Field(
        default="",
        description="Context about where/how this phrase was used",
    )

    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Get the confidence level category."""
        if self.confidence >= 0.85:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 0.6:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    @property
    def needs_review(self) -> bool:
        """Check if this phrase needs user review."""
        return self.confidence_level != ConfidenceLevel.HIGH

    @field_validator("phrase")
    @classmethod
    def strip_phrase(cls, v: str) -> str:
        """Strip whitespace from phrase."""
        return v.strip()


class ExtractedStep(BaseModel):
    """A workflow step extracted from user description.

    Represents a single status in the workflow with its associated
    actions and information needs.
    """

    step_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of this workflow step/status",
    )
    step_description: str = Field(
        default="",
        description="Description of what happens in this step",
    )
    sequence: int = Field(
        ...,
        ge=1,
        description="Order in the workflow (1-indexed)",
    )
    action_phrases: list[ExtractedPhrase] = Field(
        default_factory=list,
        description="Action button phrases for this step",
    )
    information_needs: list[ExtractedPhrase] = Field(
        default_factory=list,
        description="Information/widget phrases needed in this step",
    )
    instructions_raw: str = Field(
        default="",
        description="Raw instructions text from user (to be formatted)",
    )
    category_hint: Optional[str] = Field(
        default=None,
        description="Hint about status category (pending, in_progress, etc.)",
    )
    role_hint: Optional[str] = Field(
        default=None,
        description="Hint about primary user role for this status",
    )
    role_mentioned: Optional[str] = Field(
        default=None,
        description="Role mentioned in the step description",
    )

    @property
    def has_low_confidence_items(self) -> bool:
        """Check if this step has any low-confidence phrases."""
        all_phrases = self.action_phrases + self.information_needs
        return any(p.confidence_level == ConfidenceLevel.LOW for p in all_phrases)

    @property
    def items_needing_review(self) -> list[ExtractedPhrase]:
        """Get all phrases that need user review."""
        all_phrases = self.action_phrases + self.information_needs
        return [p for p in all_phrases if p.needs_review]

    @field_validator("step_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        """Strip whitespace from step name."""
        return v.strip()


class WorkflowMetadata(BaseModel):
    """Metadata about the workflow being configured."""

    industry: Optional[str] = Field(
        default=None,
        description="Industry type (e.g., HVAC, Plumbing, Electrical)",
    )
    company_size: Optional[str] = Field(
        default=None,
        description="Company size hint (small, medium, large)",
    )
    job_types: list[str] = Field(
        default_factory=list,
        description="Job types this workflow applies to",
    )
    source_template: Optional[str] = Field(
        default=None,
        description="Template this workflow is based on (if any)",
    )
    complexity: Optional[str] = Field(
        default=None,
        description="Workflow complexity (simple, standard, complex)",
    )


class StructuredIntent(BaseModel):
    """Top-level schema for structured intent from LLM extraction.

    This is the primary input to the ConfigBuilder, containing
    all extracted workflow information from the user's description.
    """

    workflow_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the workflow being created",
    )
    workflow_description: str = Field(
        default="",
        max_length=500,
        description="Description of the workflow's purpose",
    )
    steps: list[ExtractedStep] = Field(
        ...,
        min_length=1,
        description="Extracted workflow steps in sequence",
    )
    job_types: list[str] = Field(
        default_factory=list,
        description="Job types this workflow applies to (convenience field)",
    )
    metadata: WorkflowMetadata = Field(
        default_factory=WorkflowMetadata,
        description="Additional workflow metadata",
    )
    extraction_notes: list[str] = Field(
        default_factory=list,
        description="Notes from the LLM about extraction decisions",
    )
    ambiguity_flags: list[str] = Field(
        default_factory=list,
        description="Flags for areas needing clarification",
    )

    @property
    def total_steps(self) -> int:
        """Get total number of steps."""
        return len(self.steps)

    @property
    def total_actions(self) -> int:
        """Get total number of action phrases across all steps."""
        return sum(len(step.action_phrases) for step in self.steps)

    @property
    def total_widgets(self) -> int:
        """Get total number of widget phrases across all steps."""
        return sum(len(step.information_needs) for step in self.steps)

    @property
    def has_ambiguities(self) -> bool:
        """Check if there are any ambiguities to resolve."""
        if self.ambiguity_flags:
            return True
        return any(step.has_low_confidence_items for step in self.steps)

    @property
    def all_items_needing_review(self) -> list[dict]:
        """Get all items across all steps that need review."""
        items = []
        for step in self.steps:
            for phrase in step.items_needing_review:
                items.append({
                    "step": step.step_name,
                    "phrase": phrase.phrase,
                    "confidence": phrase.confidence,
                    "suggested_type": phrase.suggested_type,
                    "alternatives": phrase.alternatives,
                })
        return items

    @field_validator("workflow_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        """Strip whitespace from workflow name."""
        return v.strip()

    @field_validator("steps")
    @classmethod
    def validate_step_sequence(cls, v: list[ExtractedStep]) -> list[ExtractedStep]:
        """Ensure steps have proper sequence ordering."""
        sequences = [s.sequence for s in v]
        if len(sequences) != len(set(sequences)):
            raise ValueError("Step sequences must be unique")
        return sorted(v, key=lambda s: s.sequence)


class ResolvedEntity(BaseModel):
    """An entity resolved from an extracted phrase.

    Represents the mapping from a user phrase to a canonical
    action or widget type.
    """

    original_phrase: str = Field(
        ...,
        description="The original phrase from extraction",
    )
    resolved_type: str = Field(
        ...,
        description="The canonical type (ActionButtonType or WidgetType value)",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in the resolution",
    )
    was_auto_resolved: bool = Field(
        default=False,
        description="Whether this was auto-resolved (high confidence) or user-confirmed",
    )
    user_override: bool = Field(
        default=False,
        description="Whether user manually selected this resolution",
    )


class ResolutionResult(BaseModel):
    """Result of resolving all phrases in a StructuredIntent."""

    resolved_actions: dict[str, ResolvedEntity] = Field(
        default_factory=dict,
        description="Map of phrase -> resolved action entity",
    )
    resolved_widgets: dict[str, ResolvedEntity] = Field(
        default_factory=dict,
        description="Map of phrase -> resolved widget entity",
    )
    unresolved_phrases: list[ExtractedPhrase] = Field(
        default_factory=list,
        description="Phrases that could not be resolved",
    )
    review_required: list[ExtractedPhrase] = Field(
        default_factory=list,
        description="Phrases requiring user review",
    )

    @property
    def all_resolved(self) -> bool:
        """Check if all phrases were resolved."""
        return len(self.unresolved_phrases) == 0 and len(self.review_required) == 0

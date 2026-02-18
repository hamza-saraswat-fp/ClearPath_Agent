"""API-specific response schemas.

The main input schema is StructuredIntent from models/intent_schemas.py.
These schemas are for error responses only.
"""

from pydantic import BaseModel, Field


class PipelineError(BaseModel):
    """Error response from the generation pipeline."""

    error: str = Field(..., description="Error type identifier")
    message: str = Field(..., description="Human-readable error message")
    stage: str = Field(
        default="unknown",
        description="Pipeline stage where error occurred",
    )

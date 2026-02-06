"""Pydantic models for ClearPath entities."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .enums import StatusCategory, UserRole


class ActionButton(BaseModel):
    """Represents an action button configuration for a status."""

    action: str = Field(
        ...,
        min_length=1,
        description="The type of action this button performs (pass through from Relational Agent)",
    )
    label: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Display label for the button",
    )
    order: int = Field(
        default=0,
        ge=0,
        description="Display order of the button (0-indexed)",
    )
    required: bool = Field(
        default=False,
        description="Whether this action must be completed before status change",
    )
    form_id: Optional[str] = Field(
        default=None,
        description="Associated form ID (for Fill Form action)",
    )
    template_id: Optional[str] = Field(
        default=None,
        description="Associated template ID (for communication actions)",
    )

    @field_validator("label")
    @classmethod
    def validate_label(cls, v: str) -> str:
        """Ensure label is properly formatted."""
        return v.strip()


class Widget(BaseModel):
    """Represents a widget in the Focus View."""

    widget_type: str = Field(
        ...,
        min_length=1,
        description="The type of widget to display (pass through from Relational Agent)",
    )
    order: int = Field(
        default=0,
        ge=0,
        description="Display order of the widget (0-indexed)",
    )
    collapsed: bool = Field(
        default=False,
        description="Whether the widget should be collapsed by default",
    )


class Status(BaseModel):
    """Represents a job custom status in ClearPath."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the status",
    )
    category: StatusCategory = Field(
        default=StatusCategory.IN_PROGRESS,
        description="Category this status belongs to",
    )
    color: str = Field(
        default="#3B82F6",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Hex color code for the status",
    )
    icon: str = Field(
        default="clipboard",
        description="Icon name for the status (FieldPulse icon)",
    )
    status_type: str = Field(
        default="In Progress",
        description="Status type for FieldPulse (New, In Progress, completed)",
    )
    sequence: int = Field(
        ...,
        ge=1,
        description="Order in the workflow (1-indexed)",
    )
    user_role: UserRole = Field(
        default=UserRole.SERVICE_AGENT,
        description="Primary user role for this status",
    )
    action_buttons: list[ActionButton] = Field(
        default_factory=list,
        description="Action buttons available in this status",
    )
    widgets: list[Widget] = Field(
        default_factory=list,
        description="Widgets displayed in Focus View for this status",
    )
    status_instructions: str = Field(
        default="",
        max_length=2000,
        description="Instructions displayed to the user in this status",
    )
    display_action_menu: bool = Field(
        default=True,
        description="Whether to show the action menu",
    )
    ability_to_change_status: bool = Field(
        default=True,
        description="Whether user can manually change status",
    )
    focus_view_enabled: bool = Field(
        default=True,
        description="Whether Focus View is enabled for this status",
    )
    restrict_to_focus_view: bool = Field(
        default=False,
        description="Whether to restrict user to Focus View only",
    )
    next_status: Optional[str] = Field(
        default=None,
        description="Name of the next status in the workflow",
    )
    previous_status: Optional[str] = Field(
        default=None,
        description="Name of the previous status in the workflow",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is properly formatted."""
        return v.strip()


class StatusActionFlow(BaseModel):
    """Represents a complete ClearPath Status Action Flow configuration."""

    workflow_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Custom Job Status Workflow Name (Tab 1 in FieldPulse)",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Status Action Flow Name (can differ from workflow_name)",
    )
    description: str = Field(
        default="",
        max_length=500,
        description="Description of the workflow",
    )
    statuses: list[Status] = Field(
        ...,
        min_length=1,
        description="List of statuses in this workflow",
    )
    is_default: bool = Field(
        default=False,
        description="Whether this is the default workflow",
    )
    job_types: list[str] = Field(
        default_factory=list,
        description="Job types this workflow applies to",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is properly formatted."""
        return v.strip()

    @field_validator("statuses")
    @classmethod
    def validate_statuses_sequence(cls, v: list[Status]) -> list[Status]:
        """Ensure statuses have proper sequence ordering."""
        sequences = [s.sequence for s in v]
        if len(sequences) != len(set(sequences)):
            raise ValueError("Status sequences must be unique")
        return sorted(v, key=lambda s: s.sequence)

    def get_status_by_name(self, name: str) -> Optional[Status]:
        """Get a status by its name."""
        for status in self.statuses:
            if status.name.lower() == name.lower():
                return status
        return None

    def get_status_by_sequence(self, sequence: int) -> Optional[Status]:
        """Get a status by its sequence number."""
        for status in self.statuses:
            if status.sequence == sequence:
                return status
        return None

"""Pydantic schemas for Excel import template validation.

The ClearPath import template has 3 tabs matching FieldPulse format:
1. Job Custom Status - HORIZONTAL layout (all statuses in one row per workflow)
2. Action Buttons - One row per button per status per role
3. Focus View + Status Instruction - One row per status per role
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class StatusDefinition(BaseModel):
    """A single status definition for the horizontal Job Custom Status layout."""

    name: str = Field(..., description="Status Name")
    status_type: str = Field(..., description="Status Type (New, In Progress, completed)")
    color: str = Field(default="#3B82F6", description="Status Color (hex)")
    icon: str = Field(default="clipboard", description="Status Icon name")


class JobCustomStatusRow(BaseModel):
    """Schema for a row in the 'Job Custom Status' tab.

    FieldPulse uses HORIZONTAL layout: one row per workflow with all statuses
    in columns: Status Name 1, Type 1, Color 1, Icon 1, Name 2, Type 2, etc.
    """

    workflow_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Custom Job Status Workflow Name",
    )
    statuses: list[StatusDefinition] = Field(
        ...,
        min_length=1,
        description="List of statuses (will be flattened to horizontal columns)",
    )

    @field_validator("workflow_name")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip whitespace from string fields."""
        return v.strip()


class ActionButtonRow(BaseModel):
    """Schema for a row in the 'Action Buttons' tab.

    Matches FieldPulse column names exactly.
    """

    workflow_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Custom Job Status Workflow Name",
    )
    action_flow_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Status Action Flow Name",
    )
    job_status_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Job Status Name (must match a status in the workflow)",
    )
    user_role: str = Field(
        default="Service Agent",
        description="User Role (Admin, Team Manager, Service Agent)",
    )
    button_action: str = Field(
        ...,
        min_length=1,
        description="Button Action (e.g., Create Invoice, Take Photo)",
    )
    action_option: Optional[str] = Field(
        default=None,
        description="Action Option (template name, form name, custom status, etc.)",
    )
    action_button_name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Action Button Name (display label)",
    )

    @field_validator("workflow_name", "action_flow_name", "job_status_name", "action_button_name")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip whitespace from string fields."""
        return v.strip()


class FocusViewRow(BaseModel):
    """Schema for a row in the 'Focus View + Status Instruction' tab.

    Matches FieldPulse column names exactly.
    """

    workflow_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Custom Job Status Workflow Name",
    )
    action_flow_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Status Action Flow Name",
    )
    job_status_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Job Status Name",
    )
    user_role: str = Field(
        default="Service Agent",
        description="User Role (Admin, Team Manager, Service Agent)",
    )
    status_instructions: str = Field(
        default="",
        max_length=2000,
        description="Status Instructions",
    )
    display_action_menu: str = Field(
        default="T",
        description="Display Action Menu (T/F)",
    )
    ability_to_change_status: str = Field(
        default="T",
        description="Ability to Change Status (T/F)",
    )
    focus_view_enabled: str = Field(
        default="T",
        description="Focus View Enabled (T/F)",
    )
    focus_view_layout: str = Field(
        default="",
        description="Focus View Layout (comma-separated widget names)",
    )
    restrict_to_focus_view: str = Field(
        default="F",
        description="Restrict user access to Focus View only (T/F)",
    )

    @field_validator("workflow_name", "action_flow_name", "job_status_name")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip whitespace from string fields."""
        return v.strip()


class ExcelImportTemplate(BaseModel):
    """Complete Excel import template structure with all 3 tabs.

    Matches FieldPulse ClearPath Import Template format exactly.
    """

    job_custom_statuses: list[JobCustomStatusRow] = Field(
        ...,
        min_length=1,
        description="Rows for the Job Custom Status tab (one row per workflow)",
    )
    action_buttons: list[ActionButtonRow] = Field(
        default_factory=list,
        description="Rows for the Action Buttons tab",
    )
    focus_view: list[FocusViewRow] = Field(
        default_factory=list,
        description="Rows for the Focus View + Status Instruction tab",
    )

    @field_validator("job_custom_statuses")
    @classmethod
    def validate_unique_workflows(
        cls, v: list[JobCustomStatusRow]
    ) -> list[JobCustomStatusRow]:
        """Ensure workflow names are unique."""
        seen: set[str] = set()
        for row in v:
            if row.workflow_name in seen:
                raise ValueError(
                    f"Duplicate workflow name: '{row.workflow_name}'"
                )
            seen.add(row.workflow_name)
        return v

    def get_max_statuses(self) -> int:
        """Get the maximum number of statuses across all workflows."""
        if not self.job_custom_statuses:
            return 0
        return max(len(row.statuses) for row in self.job_custom_statuses)

"""Pydantic schemas for Excel import template validation.

The ClearPath import template has 3 tabs:
1. Job Custom Status - Defines the statuses in a workflow
2. Action Buttons - Defines action buttons per status per role
3. Focus View - Defines widgets and settings per status per role
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .enums import ActionButtonType, StatusCategory, UserRole, WidgetType


class JobCustomStatusRow(BaseModel):
    """Schema for a row in the 'Job Custom Status' tab.

    This tab defines the basic status information for a workflow.
    """

    status_action_flow_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the Status Action Flow this status belongs to",
    )
    status_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the status",
    )
    status_category: StatusCategory = Field(
        default=StatusCategory.IN_PROGRESS,
        description="Category of the status",
    )
    status_color: str = Field(
        default="#3B82F6",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Hex color code for the status",
    )
    sequence: int = Field(
        ...,
        ge=1,
        description="Order of the status in the workflow (1-indexed)",
    )
    is_active: bool = Field(
        default=True,
        description="Whether this status is active",
    )

    @field_validator("status_name", "status_action_flow_name")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip whitespace from string fields."""
        return v.strip()


class ActionButtonRow(BaseModel):
    """Schema for a row in the 'Action Buttons' tab.

    This tab defines action buttons available for each status/role combination.
    One row per button per status per role.
    """

    status_action_flow_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the Status Action Flow",
    )
    status_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the status this button belongs to",
    )
    user_role: UserRole = Field(
        default=UserRole.SERVICE_AGENT,
        description="User role this button is visible to",
    )
    action_type: ActionButtonType = Field(
        ...,
        description="Type of action this button performs",
    )
    button_label: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Display label for the button",
    )
    button_order: int = Field(
        default=0,
        ge=0,
        description="Display order of the button",
    )
    is_required: bool = Field(
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

    @field_validator("status_name", "status_action_flow_name", "button_label")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip whitespace from string fields."""
        return v.strip()


class FocusViewRow(BaseModel):
    """Schema for a row in the 'Focus View' tab.

    This tab defines Focus View widgets and status settings per status/role.
    One row per status per role.
    """

    status_action_flow_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the Status Action Flow",
    )
    status_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the status",
    )
    user_role: UserRole = Field(
        default=UserRole.SERVICE_AGENT,
        description="User role these settings apply to",
    )
    widgets: list[WidgetType] = Field(
        default_factory=list,
        description="List of widgets to display in Focus View (in order)",
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

    @field_validator("status_name", "status_action_flow_name")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip whitespace from string fields."""
        return v.strip()


class ExcelImportTemplate(BaseModel):
    """Complete Excel import template structure with all 3 tabs."""

    job_custom_statuses: list[JobCustomStatusRow] = Field(
        ...,
        min_length=1,
        description="Rows for the Job Custom Status tab",
    )
    action_buttons: list[ActionButtonRow] = Field(
        default_factory=list,
        description="Rows for the Action Buttons tab",
    )
    focus_view: list[FocusViewRow] = Field(
        default_factory=list,
        description="Rows for the Focus View tab",
    )

    @field_validator("job_custom_statuses")
    @classmethod
    def validate_unique_statuses(
        cls, v: list[JobCustomStatusRow]
    ) -> list[JobCustomStatusRow]:
        """Ensure status names are unique within each workflow."""
        seen: dict[str, set[str]] = {}
        for row in v:
            flow_name = row.status_action_flow_name
            if flow_name not in seen:
                seen[flow_name] = set()
            if row.status_name in seen[flow_name]:
                raise ValueError(
                    f"Duplicate status name '{row.status_name}' in flow '{flow_name}'"
                )
            seen[flow_name].add(row.status_name)
        return v

    def get_statuses_for_flow(self, flow_name: str) -> list[JobCustomStatusRow]:
        """Get all statuses for a specific workflow."""
        return [
            row
            for row in self.job_custom_statuses
            if row.status_action_flow_name == flow_name
        ]

    def get_buttons_for_status(
        self, flow_name: str, status_name: str, role: Optional[UserRole] = None
    ) -> list[ActionButtonRow]:
        """Get action buttons for a specific status."""
        buttons = [
            row
            for row in self.action_buttons
            if row.status_action_flow_name == flow_name
            and row.status_name == status_name
        ]
        if role:
            buttons = [b for b in buttons if b.user_role == role]
        return sorted(buttons, key=lambda x: x.button_order)

    def get_focus_view_for_status(
        self, flow_name: str, status_name: str, role: Optional[UserRole] = None
    ) -> list[FocusViewRow]:
        """Get Focus View configuration for a specific status."""
        views = [
            row
            for row in self.focus_view
            if row.status_action_flow_name == flow_name
            and row.status_name == status_name
        ]
        if role:
            views = [v for v in views if v.user_role == role]
        return views

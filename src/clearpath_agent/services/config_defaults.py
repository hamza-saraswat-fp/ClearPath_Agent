"""Configuration Defaults Service.

Provides intelligent defaults based on ClearPath best practices
and production patterns from the knowledge base.
"""

import logging
from typing import Optional

from ..models.enums import ActionButtonType, StatusCategory, UserRole, WidgetType

logger = logging.getLogger(__name__)


# Widget ordering based on Tier 1 best practices
# Job Title → Job Status → Status Instructions → context widgets → Action Buttons
WIDGET_ORDER_PRIORITY = {
    WidgetType.JOB_TITLE: 1,
    WidgetType.JOB_STATUS: 2,
    WidgetType.STATUS_INSTRUCTIONS: 3,
    WidgetType.CUSTOMER_CONTACT: 10,
    WidgetType.CUSTOMER_ADDRESS: 11,
    WidgetType.CUSTOMER_NOTES: 12,
    WidgetType.SCHEDULED_TIME: 15,
    WidgetType.ASSIGNED_TEAM: 16,
    WidgetType.JOB_DETAILS: 20,
    WidgetType.JOB_DESCRIPTION: 21,
    WidgetType.JOB_NOTES: 22,
    WidgetType.JOB_TAGS: 23,
    WidgetType.JOB_CUSTOM_FIELDS: 24,
    WidgetType.FORMS: 30,
    WidgetType.CHECKLIST: 31,
    WidgetType.FILES_PHOTOS: 35,
    WidgetType.SIGNATURES: 36,
    WidgetType.TIMESHEETS: 40,
    WidgetType.MATERIALS: 45,
    WidgetType.LABOR: 46,
    WidgetType.EXPENSES: 47,
    WidgetType.LINE_ITEMS: 48,
    WidgetType.ESTIMATES: 50,
    WidgetType.INVOICES: 51,
    WidgetType.PAYMENTS: 52,
    WidgetType.ASSETS: 55,
    WidgetType.ASSET_DETAILS: 56,
    WidgetType.CUSTOMER_HISTORY: 60,
    WidgetType.JOB_HISTORY: 61,
    WidgetType.RELATED_JOBS: 62,
    WidgetType.ACTION_BUTTONS: 100,  # Always last for thumb accessibility
}

# Action to Widget mappings - which widgets commonly appear with which actions
ACTION_WIDGET_COOCCURRENCE = {
    ActionButtonType.CLOCK_IN_OUT: [WidgetType.TIMESHEETS],
    ActionButtonType.SEND_CUSTOMER_COMMUNICATION: [WidgetType.CUSTOMER_CONTACT],
    ActionButtonType.FILL_FORM: [WidgetType.FORMS],
    ActionButtonType.TAKE_PHOTO: [WidgetType.FILES_PHOTOS],
    ActionButtonType.COLLECT_SIGNATURE: [WidgetType.SIGNATURES],
    ActionButtonType.COLLECT_PAYMENT: [WidgetType.PAYMENTS, WidgetType.INVOICES],
    ActionButtonType.ADD_LINE_ITEM: [WidgetType.LINE_ITEMS],
    ActionButtonType.ADD_MATERIAL: [WidgetType.MATERIALS],
    ActionButtonType.ADD_LABOR: [WidgetType.LABOR],
    ActionButtonType.ADD_EXPENSE: [WidgetType.EXPENSES],
    ActionButtonType.CREATE_ESTIMATE: [WidgetType.ESTIMATES],
    ActionButtonType.CREATE_INVOICE: [WidgetType.INVOICES],
    ActionButtonType.SEND_ESTIMATE: [WidgetType.ESTIMATES],
    ActionButtonType.SEND_INVOICE: [WidgetType.INVOICES],
    ActionButtonType.VIEW_ESTIMATE: [WidgetType.ESTIMATES],
    ActionButtonType.VIEW_INVOICE: [WidgetType.INVOICES],
    ActionButtonType.ADD_NOTE: [WidgetType.JOB_NOTES],
    ActionButtonType.ADD_ATTACHMENT: [WidgetType.FILES_PHOTOS],
    ActionButtonType.VIEW_CUSTOMER_HISTORY: [WidgetType.CUSTOMER_HISTORY],
    ActionButtonType.VIEW_ASSET_HISTORY: [WidgetType.ASSETS, WidgetType.ASSET_DETAILS],
    ActionButtonType.VIEW_JOB_HISTORY: [WidgetType.JOB_HISTORY],
    ActionButtonType.UPDATE_ASSET: [WidgetType.ASSETS, WidgetType.ASSET_DETAILS],
    ActionButtonType.CREATE_ASSET: [WidgetType.ASSETS],
    ActionButtonType.SCHEDULE_FOLLOW_UP: [WidgetType.SCHEDULED_TIME],
    ActionButtonType.REQUEST_REVIEW: [],
    ActionButtonType.MARK_COMPLETE: [],
    ActionButtonType.CUSTOM_ACTION: [],
}

# Default toggles by status category
DEFAULT_TOGGLES_BY_CATEGORY = {
    StatusCategory.PENDING: {
        "display_action_menu": True,
        "ability_to_change_status": True,
        "focus_view_enabled": True,
        "restrict_to_focus_view": False,
    },
    StatusCategory.IN_PROGRESS: {
        "display_action_menu": True,
        "ability_to_change_status": True,
        "focus_view_enabled": True,
        "restrict_to_focus_view": True,  # Field work - restrict to focus view
    },
    StatusCategory.ON_HOLD: {
        "display_action_menu": True,
        "ability_to_change_status": True,
        "focus_view_enabled": True,
        "restrict_to_focus_view": False,
    },
    StatusCategory.COMPLETED: {
        "display_action_menu": True,
        "ability_to_change_status": False,  # Completed jobs shouldn't change status
        "focus_view_enabled": True,
        "restrict_to_focus_view": False,
    },
    StatusCategory.CANCELLED: {
        "display_action_menu": False,
        "ability_to_change_status": False,
        "focus_view_enabled": False,
        "restrict_to_focus_view": False,
    },
}

# Default role assignments based on status keywords
STATUS_ROLE_KEYWORDS = {
    UserRole.SERVICE_AGENT: [
        "on site", "in progress", "working", "en route", "traveling",
        "arrived", "service", "repair", "installation", "inspection",
    ],
    UserRole.OFFICE_STAFF: [
        "new", "scheduled", "pending", "waiting", "review",
        "billing", "invoice", "estimate", "quote",
    ],
    UserRole.MANAGER: [
        "approval", "review", "quality", "escalated", "exception",
    ],
    UserRole.DISPATCHER: [
        "dispatch", "assign", "schedule", "route",
    ],
}


class DefaultsProvider:
    """Provides intelligent defaults for workflow configuration.

    Uses ClearPath Tier 1 best practices and production patterns
    to suggest defaults for widgets, toggles, and instructions.
    """

    def __init__(
        self,
        vector_store=None,
        graph_store=None,
    ):
        """Initialize the defaults provider.

        Args:
            vector_store: Optional VectorStore for knowledge base lookups
            graph_store: Optional GraphStore for relationship lookups
        """
        self.vector_store = vector_store
        self.graph_store = graph_store
        self._pattern_cache = {}

    def get_default_widgets(
        self,
        status_name: str,
        actions: list[ActionButtonType],
        include_core: bool = True,
    ) -> list[WidgetType]:
        """Get ordered widget list following Tier 1 best practices.

        Widget ordering:
        1. Job Title (always first)
        2. Job Status (always second)
        3. Status Instructions (always third)
        4. Context-specific widgets (based on actions)
        5. Action Buttons (always last for thumb accessibility)

        Args:
            status_name: Name of the status
            actions: List of action button types in this status
            include_core: Whether to include core widgets (title, status, instructions)

        Returns:
            Ordered list of WidgetType values
        """
        widgets = set()

        # Core widgets (always included if include_core=True)
        if include_core:
            widgets.add(WidgetType.JOB_TITLE)
            widgets.add(WidgetType.JOB_STATUS)
            widgets.add(WidgetType.STATUS_INSTRUCTIONS)
            widgets.add(WidgetType.ACTION_BUTTONS)

        # Add context-specific widgets based on actions
        for action in actions:
            related_widgets = ACTION_WIDGET_COOCCURRENCE.get(action, [])
            widgets.update(related_widgets)

        # Add customer contact if communication actions present
        communication_actions = {
            ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
        }
        if any(a in communication_actions for a in actions):
            widgets.add(WidgetType.CUSTOMER_CONTACT)
            widgets.add(WidgetType.CUSTOMER_ADDRESS)

        # Add job notes if note-related actions present
        if ActionButtonType.ADD_NOTE in actions:
            widgets.add(WidgetType.JOB_NOTES)

        # Sort widgets by priority
        sorted_widgets = sorted(
            widgets,
            key=lambda w: WIDGET_ORDER_PRIORITY.get(w, 50)
        )

        logger.debug(f"Generated {len(sorted_widgets)} default widgets for status '{status_name}'")
        return sorted_widgets

    def get_default_toggles(
        self,
        status_category: StatusCategory,
    ) -> dict[str, bool]:
        """Get default toggle values based on status category.

        Args:
            status_category: Category of the status

        Returns:
            Dict with toggle names and values
        """
        return DEFAULT_TOGGLES_BY_CATEGORY.get(
            status_category,
            DEFAULT_TOGGLES_BY_CATEGORY[StatusCategory.IN_PROGRESS]
        ).copy()

    def format_status_instructions(
        self,
        actions: list[ActionButtonType],
        raw_instructions: str = "",
        include_action_list: bool = True,
    ) -> str:
        """Format actions into numbered status instructions.

        Per Tier 1 doc, instructions should be numbered (1., 2., 3., etc.)

        Args:
            actions: List of action button types
            raw_instructions: Optional raw instructions from user
            include_action_list: Whether to include action list in instructions

        Returns:
            Formatted numbered instructions string
        """
        lines = []

        # If raw instructions provided, parse and number them
        if raw_instructions:
            raw_lines = [
                line.strip()
                for line in raw_instructions.split("\n")
                if line.strip()
            ]
            for i, line in enumerate(raw_lines, 1):
                # Remove existing numbering if present
                cleaned = line.lstrip("0123456789.-) ")
                lines.append(f"{i}. {cleaned}")
        elif include_action_list and actions:
            # Generate instructions from actions
            for i, action in enumerate(actions, 1):
                instruction = self._action_to_instruction(action)
                lines.append(f"{i}. {instruction}")

        return "\n".join(lines)

    def _action_to_instruction(self, action: ActionButtonType) -> str:
        """Convert an action type to an instruction line.

        Args:
            action: The action button type

        Returns:
            Human-readable instruction for this action
        """
        action_instructions = {
            ActionButtonType.CLOCK_IN_OUT: "Clock in/out for time tracking",
            ActionButtonType.SEND_CUSTOMER_COMMUNICATION: "Send communication to customer",
            ActionButtonType.FILL_FORM: "Complete required form(s)",
            ActionButtonType.TAKE_PHOTO: "Take photos of work area/equipment",
            ActionButtonType.COLLECT_SIGNATURE: "Collect customer signature",
            ActionButtonType.COLLECT_PAYMENT: "Collect payment from customer",
            ActionButtonType.ADD_LINE_ITEM: "Add line items to job",
            ActionButtonType.ADD_MATERIAL: "Record materials used",
            ActionButtonType.ADD_LABOR: "Record labor time",
            ActionButtonType.ADD_EXPENSE: "Record expenses",
            ActionButtonType.CREATE_ESTIMATE: "Create estimate for customer",
            ActionButtonType.CREATE_INVOICE: "Create invoice for customer",
            ActionButtonType.SEND_ESTIMATE: "Send estimate to customer",
            ActionButtonType.SEND_INVOICE: "Send invoice to customer",
            ActionButtonType.VIEW_ESTIMATE: "Review estimate details",
            ActionButtonType.VIEW_INVOICE: "Review invoice details",
            ActionButtonType.ADD_NOTE: "Add notes to job record",
            ActionButtonType.ADD_ATTACHMENT: "Attach files or documents",
            ActionButtonType.VIEW_CUSTOMER_HISTORY: "Review customer history",
            ActionButtonType.VIEW_ASSET_HISTORY: "Review asset/equipment history",
            ActionButtonType.VIEW_JOB_HISTORY: "Review job history",
            ActionButtonType.UPDATE_ASSET: "Update asset information",
            ActionButtonType.CREATE_ASSET: "Create new asset record",
            ActionButtonType.SCHEDULE_FOLLOW_UP: "Schedule follow-up appointment",
            ActionButtonType.REQUEST_REVIEW: "Request review/approval",
            ActionButtonType.MARK_COMPLETE: "Mark task as complete",
            ActionButtonType.CUSTOM_ACTION: "Complete custom action",
        }
        return action_instructions.get(action, action.value)

    def suggest_related_widgets(
        self,
        actions: list[ActionButtonType],
    ) -> list[WidgetType]:
        """Suggest widgets based on action co-occurrence patterns.

        Uses production data patterns to suggest widgets that commonly
        appear with the given actions.

        Args:
            actions: List of action button types

        Returns:
            List of suggested widget types
        """
        suggested = set()

        for action in actions:
            related = ACTION_WIDGET_COOCCURRENCE.get(action, [])
            suggested.update(related)

        # If we have access to graph store, use production patterns
        if self.graph_store:
            try:
                # Query production co-occurrence patterns
                # This would query: MATCH (a:Action)-[:CO_OCCURS_WITH]-(w:Widget)
                # For now, use static mappings
                pass
            except Exception as e:
                logger.warning(f"Failed to query graph store for patterns: {e}")

        return list(suggested)

    def get_role_defaults(
        self,
        status_name: str,
        status_category: Optional[StatusCategory] = None,
    ) -> UserRole:
        """Get default user role for a status.

        Args:
            status_name: Name of the status
            status_category: Optional category hint

        Returns:
            Suggested UserRole for this status
        """
        status_lower = status_name.lower()

        # Check keywords for role assignment
        for role, keywords in STATUS_ROLE_KEYWORDS.items():
            if any(kw in status_lower for kw in keywords):
                return role

        # Default based on category
        if status_category == StatusCategory.PENDING:
            return UserRole.OFFICE_STAFF
        elif status_category == StatusCategory.IN_PROGRESS:
            return UserRole.SERVICE_AGENT
        elif status_category == StatusCategory.COMPLETED:
            return UserRole.SERVICE_AGENT
        else:
            return UserRole.SERVICE_AGENT

    def infer_status_category(
        self,
        status_name: str,
        sequence: int,
        total_statuses: int,
    ) -> StatusCategory:
        """Infer status category from name and position in workflow.

        Args:
            status_name: Name of the status
            sequence: Position in workflow (1-indexed)
            total_statuses: Total number of statuses in workflow

        Returns:
            Inferred StatusCategory
        """
        name_lower = status_name.lower()

        # Check for explicit category keywords
        category_keywords = {
            StatusCategory.PENDING: ["new", "pending", "scheduled", "assigned", "waiting"],
            StatusCategory.IN_PROGRESS: ["progress", "working", "active", "on site", "en route", "started"],
            StatusCategory.ON_HOLD: ["hold", "paused", "blocked", "waiting for"],
            StatusCategory.COMPLETED: ["complete", "done", "finished", "closed"],
            StatusCategory.CANCELLED: ["cancel", "void", "rejected"],
        }

        for category, keywords in category_keywords.items():
            if any(kw in name_lower for kw in keywords):
                return category

        # Infer from position
        if sequence == 1:
            return StatusCategory.PENDING
        elif sequence == total_statuses:
            return StatusCategory.COMPLETED
        else:
            return StatusCategory.IN_PROGRESS

    def get_standard_colors(self) -> dict[StatusCategory, str]:
        """Get standard color codes for status categories.

        Returns:
            Dict mapping StatusCategory to hex color codes
        """
        return {
            StatusCategory.PENDING: "#FCD34D",  # Yellow
            StatusCategory.IN_PROGRESS: "#3B82F6",  # Blue
            StatusCategory.ON_HOLD: "#F97316",  # Orange
            StatusCategory.COMPLETED: "#22C55E",  # Green
            StatusCategory.CANCELLED: "#EF4444",  # Red
        }

    def get_color_for_category(self, category: StatusCategory) -> str:
        """Get default color for a status category.

        Args:
            category: The status category

        Returns:
            Hex color code
        """
        colors = self.get_standard_colors()
        return colors.get(category, "#3B82F6")

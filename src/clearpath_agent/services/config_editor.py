"""Configuration Editor Service.

Provides utilities for users to review and modify generated
configurations before Excel export.
"""

import json
import logging
from typing import Optional

from ..models.entities import ActionButton, Status, StatusActionFlow, Widget
from ..models.enums import ActionButtonType, StatusCategory, UserRole, WidgetType
from .config_validator import ConfigValidator, ValidationResult

logger = logging.getLogger(__name__)


class ConfigEditor:
    """Editor for reviewing and modifying StatusActionFlow configurations.

    Supports:
    - Converting configs to user-friendly JSON for review
    - Applying user edits back to configurations
    - Validating edits before applying
    - Generating human-readable summaries
    """

    def __init__(self):
        """Initialize the config editor."""
        self.validator = ConfigValidator()

    def get_editable_json(
        self,
        config: StatusActionFlow,
        include_all_fields: bool = False,
    ) -> dict:
        """Convert StatusActionFlow to user-friendly JSON format.

        The output format is designed for easy review and editing.

        Args:
            config: The configuration to convert
            include_all_fields: Whether to include all fields or just editable ones

        Returns:
            Dict in user-friendly format
        """
        result = {
            "workflow": {
                "name": config.name,
                "description": config.description,
                "job_types": config.job_types,
            },
            "statuses": [],
        }

        for status in config.statuses:
            status_dict = {
                "name": status.name,
                "sequence": status.sequence,
                "category": status.category.value,
                "color": status.color,
                "role": status.user_role.value,
                "instructions": status.status_instructions,
                "action_buttons": [],
                "widgets": [],
                "settings": {
                    "display_action_menu": status.display_action_menu,
                    "ability_to_change_status": status.ability_to_change_status,
                    "focus_view_enabled": status.focus_view_enabled,
                    "restrict_to_focus_view": status.restrict_to_focus_view,
                },
            }

            # Add action buttons
            for button in status.action_buttons:
                button_dict = {
                    "label": button.label,
                    "action": button.action.value,
                    "order": button.order,
                    "required": button.required,
                }
                if button.form_id:
                    button_dict["form_id"] = button.form_id
                if button.template_id:
                    button_dict["template_id"] = button.template_id
                status_dict["action_buttons"].append(button_dict)

            # Add widgets
            for widget in status.widgets:
                widget_dict = {
                    "type": widget.widget_type.value,
                    "order": widget.order,
                }
                if include_all_fields:
                    widget_dict["collapsed"] = widget.collapsed
                status_dict["widgets"].append(widget_dict)

            if include_all_fields:
                status_dict["next_status"] = status.next_status
                status_dict["previous_status"] = status.previous_status

            result["statuses"].append(status_dict)

        return result

    def apply_user_edits(
        self,
        config: StatusActionFlow,
        edits: dict,
    ) -> StatusActionFlow:
        """Apply user modifications to a configuration.

        Args:
            config: The original configuration
            edits: Dict with edits to apply

        Returns:
            Modified StatusActionFlow
        """
        # Start with a copy
        config_dict = config.model_dump()

        # Apply workflow-level edits
        if "workflow" in edits:
            workflow_edits = edits["workflow"]
            if "name" in workflow_edits:
                config_dict["name"] = workflow_edits["name"]
            if "description" in workflow_edits:
                config_dict["description"] = workflow_edits["description"]
            if "job_types" in workflow_edits:
                config_dict["job_types"] = workflow_edits["job_types"]

        # Apply status edits
        if "statuses" in edits:
            for status_edit in edits["statuses"]:
                status_name = status_edit.get("name")
                if not status_name:
                    continue

                # Find matching status
                for status_dict in config_dict["statuses"]:
                    if status_dict["name"].lower() == status_name.lower():
                        self._apply_status_edit(status_dict, status_edit)
                        break

        return StatusActionFlow(**config_dict)

    def _apply_status_edit(
        self,
        status_dict: dict,
        edit: dict,
    ) -> None:
        """Apply edits to a single status.

        Args:
            status_dict: The status dict to modify (in place)
            edit: The edits to apply
        """
        # Simple field edits
        simple_fields = [
            "name", "sequence", "color", "status_instructions",
        ]
        for field in simple_fields:
            if field in edit:
                status_dict[field] = edit[field]

        # Category edit (needs enum conversion)
        if "category" in edit:
            status_dict["category"] = edit["category"]

        # Role edit (needs enum conversion)
        if "role" in edit:
            status_dict["user_role"] = edit["role"]

        # Settings edits
        if "settings" in edit:
            for key, value in edit["settings"].items():
                if key in status_dict:
                    status_dict[key] = value

        # Action button edits
        if "action_buttons" in edit:
            status_dict["action_buttons"] = self._parse_action_buttons(
                edit["action_buttons"]
            )

        # Widget edits
        if "widgets" in edit:
            status_dict["widgets"] = self._parse_widgets(edit["widgets"])

    def _parse_action_buttons(
        self,
        buttons_data: list[dict],
    ) -> list[dict]:
        """Parse action button data into internal format.

        Args:
            buttons_data: List of button dicts from user

        Returns:
            List of button dicts in internal format
        """
        result = []
        for i, button in enumerate(buttons_data):
            result.append({
                "action": button.get("action"),
                "label": button.get("label", button.get("action", "")),
                "order": button.get("order", i),
                "required": button.get("required", False),
                "form_id": button.get("form_id"),
                "template_id": button.get("template_id"),
            })
        return result

    def _parse_widgets(
        self,
        widgets_data: list[dict],
    ) -> list[dict]:
        """Parse widget data into internal format.

        Args:
            widgets_data: List of widget dicts from user

        Returns:
            List of widget dicts in internal format
        """
        result = []
        for i, widget in enumerate(widgets_data):
            result.append({
                "widget_type": widget.get("type"),
                "order": widget.get("order", i),
                "collapsed": widget.get("collapsed", False),
            })
        return result

    def validate_edits(
        self,
        config: StatusActionFlow,
        edits: dict,
    ) -> ValidationResult:
        """Validate user edits before applying.

        Args:
            config: The original configuration
            edits: The edits to validate

        Returns:
            ValidationResult with any issues
        """
        # Apply edits to a copy
        try:
            modified = self.apply_user_edits(config, edits)
        except Exception as e:
            result = ValidationResult(is_valid=False)
            result.add_error(
                code="EDIT_PARSE_ERROR",
                message=f"Failed to parse edits: {e}",
            )
            return result

        # Validate the modified config
        return self.validator.validate_config(modified)

    def get_review_summary(
        self,
        config: StatusActionFlow,
    ) -> str:
        """Generate a human-readable summary of the configuration.

        Args:
            config: The configuration to summarize

        Returns:
            Formatted summary string
        """
        lines = [
            f"# {config.name}",
            "",
            f"**Description:** {config.description or 'No description'}",
            f"**Job Types:** {', '.join(config.job_types) or 'None specified'}",
            "",
            f"## Workflow ({len(config.statuses)} statuses)",
            "",
        ]

        for i, status in enumerate(config.statuses, 1):
            lines.append(f"### {i}. {status.name}")
            lines.append(f"   - Category: {status.category.value}")
            lines.append(f"   - Role: {status.user_role.value}")
            lines.append(f"   - Action Buttons: {len(status.action_buttons)}")

            if status.action_buttons:
                button_names = [b.label for b in status.action_buttons]
                lines.append(f"     - {', '.join(button_names)}")

            lines.append(f"   - Widgets: {len(status.widgets)}")
            lines.append(f"   - Focus View: {'Enabled' if status.focus_view_enabled else 'Disabled'}")

            if status.status_instructions:
                lines.append("   - Instructions:")
                for line in status.status_instructions.split("\n")[:3]:
                    lines.append(f"     {line}")
                if len(status.status_instructions.split("\n")) > 3:
                    lines.append("     ...")

            lines.append("")

        return "\n".join(lines)

    def highlight_low_confidence(
        self,
        config: StatusActionFlow,
        low_confidence_items: list[dict],
    ) -> dict:
        """Mark items needing attention in the configuration.

        Args:
            config: The configuration
            low_confidence_items: List of low-confidence items

        Returns:
            Dict with config and highlighted items
        """
        # Create a set of phrases to highlight
        highlight_phrases = {
            item["phrase"].lower()
            for item in low_confidence_items
            if "phrase" in item
        }

        editable = self.get_editable_json(config)

        # Mark highlighted items
        for status in editable["statuses"]:
            for button in status["action_buttons"]:
                if button["label"].lower() in highlight_phrases:
                    button["_needs_review"] = True

        return {
            "config": editable,
            "highlighted_items": low_confidence_items,
            "highlight_count": len(low_confidence_items),
        }

    def add_status(
        self,
        config: StatusActionFlow,
        status_data: dict,
        position: Optional[int] = None,
    ) -> StatusActionFlow:
        """Add a new status to the configuration.

        Args:
            config: The configuration to modify
            status_data: Data for the new status
            position: Position to insert (None = end)

        Returns:
            Modified StatusActionFlow
        """
        config_dict = config.model_dump()

        # Determine sequence number
        if position is None:
            sequence = max(s["sequence"] for s in config_dict["statuses"]) + 1
        else:
            sequence = position
            # Shift existing sequences
            for status in config_dict["statuses"]:
                if status["sequence"] >= position:
                    status["sequence"] += 1

        # Create new status
        new_status = {
            "name": status_data.get("name", "New Status"),
            "category": status_data.get("category", StatusCategory.IN_PROGRESS.value),
            "color": status_data.get("color", "#3B82F6"),
            "sequence": sequence,
            "user_role": status_data.get("role", UserRole.SERVICE_AGENT.value),
            "action_buttons": status_data.get("action_buttons", []),
            "widgets": status_data.get("widgets", []),
            "status_instructions": status_data.get("instructions", ""),
            "display_action_menu": status_data.get("display_action_menu", True),
            "ability_to_change_status": status_data.get("ability_to_change_status", True),
            "focus_view_enabled": status_data.get("focus_view_enabled", True),
            "restrict_to_focus_view": status_data.get("restrict_to_focus_view", False),
            "next_status": None,
            "previous_status": None,
        }

        config_dict["statuses"].append(new_status)
        config_dict["statuses"].sort(key=lambda s: s["sequence"])

        return StatusActionFlow(**config_dict)

    def remove_status(
        self,
        config: StatusActionFlow,
        status_name: str,
    ) -> StatusActionFlow:
        """Remove a status from the configuration.

        Args:
            config: The configuration to modify
            status_name: Name of the status to remove

        Returns:
            Modified StatusActionFlow
        """
        config_dict = config.model_dump()

        # Find and remove the status
        config_dict["statuses"] = [
            s for s in config_dict["statuses"]
            if s["name"].lower() != status_name.lower()
        ]

        # Re-sequence
        for i, status in enumerate(
            sorted(config_dict["statuses"], key=lambda s: s["sequence"]),
            start=1
        ):
            status["sequence"] = i

        return StatusActionFlow(**config_dict)

    def reorder_statuses(
        self,
        config: StatusActionFlow,
        new_order: list[str],
    ) -> StatusActionFlow:
        """Reorder statuses in the configuration.

        Args:
            config: The configuration to modify
            new_order: List of status names in desired order

        Returns:
            Modified StatusActionFlow
        """
        config_dict = config.model_dump()

        # Create name-to-status mapping
        status_map = {
            s["name"].lower(): s for s in config_dict["statuses"]
        }

        # Reorder
        reordered = []
        for i, name in enumerate(new_order, start=1):
            status = status_map.get(name.lower())
            if status:
                status["sequence"] = i
                reordered.append(status)

        config_dict["statuses"] = reordered

        return StatusActionFlow(**config_dict)

    def export_to_json(
        self,
        config: StatusActionFlow,
        filepath: str,
    ) -> None:
        """Export configuration to a JSON file.

        Args:
            config: The configuration to export
            filepath: Path to write the JSON file
        """
        editable = self.get_editable_json(config, include_all_fields=True)
        with open(filepath, "w") as f:
            json.dump(editable, f, indent=2)
        logger.info(f"Exported configuration to {filepath}")

    def import_from_json(
        self,
        filepath: str,
    ) -> StatusActionFlow:
        """Import configuration from a JSON file.

        Args:
            filepath: Path to the JSON file

        Returns:
            StatusActionFlow from the file
        """
        with open(filepath) as f:
            data = json.load(f)

        # Convert from editable format to internal format
        config_dict = {
            "name": data["workflow"]["name"],
            "description": data["workflow"].get("description", ""),
            "job_types": data["workflow"].get("job_types", []),
            "is_default": False,
            "statuses": [],
        }

        for status_data in data["statuses"]:
            status = {
                "name": status_data["name"],
                "category": status_data["category"],
                "color": status_data.get("color", "#3B82F6"),
                "sequence": status_data["sequence"],
                "user_role": status_data["role"],
                "action_buttons": self._parse_action_buttons(
                    status_data.get("action_buttons", [])
                ),
                "widgets": self._parse_widgets(
                    status_data.get("widgets", [])
                ),
                "status_instructions": status_data.get("instructions", ""),
                "display_action_menu": status_data.get("settings", {}).get(
                    "display_action_menu", True
                ),
                "ability_to_change_status": status_data.get("settings", {}).get(
                    "ability_to_change_status", True
                ),
                "focus_view_enabled": status_data.get("settings", {}).get(
                    "focus_view_enabled", True
                ),
                "restrict_to_focus_view": status_data.get("settings", {}).get(
                    "restrict_to_focus_view", False
                ),
                "next_status": status_data.get("next_status"),
                "previous_status": status_data.get("previous_status"),
            }
            config_dict["statuses"].append(status)

        return StatusActionFlow(**config_dict)

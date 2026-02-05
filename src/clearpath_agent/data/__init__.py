"""Data module for ClearPath Agent."""

from .default_templates import (
    EMERGENCY_TEMPLATE,
    INSPECTION_TEMPLATE,
    INSTALLATION_TEMPLATE,
    SERVICE_CALL_TEMPLATE,
    TemplateSelector,
    get_template,
    list_templates,
)

__all__ = [
    "SERVICE_CALL_TEMPLATE",
    "INSTALLATION_TEMPLATE",
    "INSPECTION_TEMPLATE",
    "EMERGENCY_TEMPLATE",
    "get_template",
    "list_templates",
    "TemplateSelector",
]

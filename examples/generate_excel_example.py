#!/usr/bin/env python3
"""Example script demonstrating Excel generation from StatusActionFlow.

This script shows the complete workflow for generating a ClearPath
import template Excel file from a StatusActionFlow configuration.

Usage:
    python examples/generate_excel_example.py
"""

import json
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from clearpath_agent.models.entities import (
    ActionButton,
    Status,
    StatusActionFlow,
    Widget,
)
from clearpath_agent.models.enums import (
    ActionButtonType,
    StatusCategory,
    UserRole,
    WidgetType,
)
from clearpath_agent.services.config_to_excel import ConfigToExcelConverter
from clearpath_agent.services.config_validator import ConfigValidator
from clearpath_agent.services.excel_generator import ExcelGenerator


def create_sample_workflow() -> StatusActionFlow:
    """Create a sample HVAC service call workflow."""
    return StatusActionFlow(
        name="HVAC Service Call",
        description="Standard workflow for HVAC service appointments",
        job_types=["Service Call", "Maintenance", "Repair"],
        statuses=[
            # Status 1: New
            Status(
                name="New",
                category=StatusCategory.PENDING,
                color="#6B7280",
                sequence=1,
                user_role=UserRole.DISPATCHER,
                action_buttons=[
                    ActionButton(
                        action=ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
                        label="Send Confirmation",
                        order=0,
                        template_id="sms_confirmation",
                    ),
                    ActionButton(
                        action=ActionButtonType.ADD_NOTE,
                        label="Add Note",
                        order=1,
                    ),
                ],
                widgets=[
                    Widget(widget_type=WidgetType.JOB_TITLE, order=0),
                    Widget(widget_type=WidgetType.JOB_STATUS, order=1),
                    Widget(widget_type=WidgetType.STATUS_INSTRUCTIONS, order=2),
                    Widget(widget_type=WidgetType.CUSTOMER_CONTACT, order=3),
                    Widget(widget_type=WidgetType.CUSTOMER_ADDRESS, order=4),
                    Widget(widget_type=WidgetType.SCHEDULED_TIME, order=5),
                    Widget(widget_type=WidgetType.ACTION_BUTTONS, order=6),
                ],
                status_instructions="1. Review job details\n2. Assign technician\n3. Send confirmation to customer",
                display_action_menu=True,
                ability_to_change_status=True,
                focus_view_enabled=True,
                restrict_to_focus_view=False,
            ),
            # Status 2: Dispatched
            Status(
                name="Dispatched",
                category=StatusCategory.IN_PROGRESS,
                color="#3B82F6",
                sequence=2,
                user_role=UserRole.SERVICE_AGENT,
                action_buttons=[
                    ActionButton(
                        action=ActionButtonType.CLOCK_IN_OUT,
                        label="Clock In",
                        order=0,
                        required=True,
                    ),
                    ActionButton(
                        action=ActionButtonType.SEND_CUSTOMER_COMMUNICATION,
                        label="Notify On Way",
                        order=1,
                        template_id="sms_on_way",
                    ),
                ],
                widgets=[
                    Widget(widget_type=WidgetType.JOB_TITLE, order=0),
                    Widget(widget_type=WidgetType.JOB_STATUS, order=1),
                    Widget(widget_type=WidgetType.STATUS_INSTRUCTIONS, order=2),
                    Widget(widget_type=WidgetType.CUSTOMER_ADDRESS, order=3),
                    Widget(widget_type=WidgetType.CUSTOMER_CONTACT, order=4),
                    Widget(widget_type=WidgetType.TIMESHEETS, order=5),
                    Widget(widget_type=WidgetType.ACTION_BUTTONS, order=6),
                ],
                status_instructions="1. Clock in when arriving\n2. Notify customer you're on the way",
                display_action_menu=True,
                ability_to_change_status=True,
                focus_view_enabled=True,
                restrict_to_focus_view=True,
            ),
            # Status 3: On Site
            Status(
                name="On Site",
                category=StatusCategory.IN_PROGRESS,
                color="#8B5CF6",
                sequence=3,
                user_role=UserRole.SERVICE_AGENT,
                action_buttons=[
                    ActionButton(
                        action=ActionButtonType.FILL_FORM,
                        label="Safety Checklist",
                        order=0,
                        required=True,
                        form_id="safety_checklist",
                    ),
                    ActionButton(
                        action=ActionButtonType.TAKE_PHOTO,
                        label="Take Before Photo",
                        order=1,
                    ),
                    ActionButton(
                        action=ActionButtonType.ADD_NOTE,
                        label="Add Note",
                        order=2,
                    ),
                ],
                widgets=[
                    Widget(widget_type=WidgetType.JOB_TITLE, order=0),
                    Widget(widget_type=WidgetType.JOB_STATUS, order=1),
                    Widget(widget_type=WidgetType.STATUS_INSTRUCTIONS, order=2),
                    Widget(widget_type=WidgetType.JOB_DESCRIPTION, order=3),
                    Widget(widget_type=WidgetType.FORMS, order=4),
                    Widget(widget_type=WidgetType.FILES_PHOTOS, order=5),
                    Widget(widget_type=WidgetType.ACTION_BUTTONS, order=6),
                ],
                status_instructions="1. Complete safety checklist\n2. Take before photos\n3. Diagnose the issue",
                display_action_menu=True,
                ability_to_change_status=True,
                focus_view_enabled=True,
                restrict_to_focus_view=True,
            ),
            # Status 4: Work In Progress
            Status(
                name="Work In Progress",
                category=StatusCategory.IN_PROGRESS,
                color="#F59E0B",
                sequence=4,
                user_role=UserRole.SERVICE_AGENT,
                action_buttons=[
                    ActionButton(
                        action=ActionButtonType.ADD_MATERIAL,
                        label="Add Parts",
                        order=0,
                    ),
                    ActionButton(
                        action=ActionButtonType.ADD_LABOR,
                        label="Add Labor",
                        order=1,
                    ),
                    ActionButton(
                        action=ActionButtonType.TAKE_PHOTO,
                        label="Take Photo",
                        order=2,
                    ),
                    ActionButton(
                        action=ActionButtonType.ADD_NOTE,
                        label="Add Note",
                        order=3,
                    ),
                ],
                widgets=[
                    Widget(widget_type=WidgetType.JOB_TITLE, order=0),
                    Widget(widget_type=WidgetType.JOB_STATUS, order=1),
                    Widget(widget_type=WidgetType.STATUS_INSTRUCTIONS, order=2),
                    Widget(widget_type=WidgetType.MATERIALS, order=3),
                    Widget(widget_type=WidgetType.LABOR, order=4),
                    Widget(widget_type=WidgetType.FILES_PHOTOS, order=5),
                    Widget(widget_type=WidgetType.ACTION_BUTTONS, order=6),
                ],
                status_instructions="1. Complete the repair\n2. Add parts used\n3. Log labor time\n4. Document with photos",
                display_action_menu=True,
                ability_to_change_status=True,
                focus_view_enabled=True,
                restrict_to_focus_view=True,
            ),
            # Status 5: Ready for Invoice
            Status(
                name="Ready for Invoice",
                category=StatusCategory.IN_PROGRESS,
                color="#10B981",
                sequence=5,
                user_role=UserRole.SERVICE_AGENT,
                action_buttons=[
                    ActionButton(
                        action=ActionButtonType.CREATE_INVOICE,
                        label="Create Invoice",
                        order=0,
                        required=True,
                    ),
                    ActionButton(
                        action=ActionButtonType.COLLECT_SIGNATURE,
                        label="Get Signature",
                        order=1,
                        required=True,
                    ),
                    ActionButton(
                        action=ActionButtonType.COLLECT_PAYMENT,
                        label="Collect Payment",
                        order=2,
                    ),
                ],
                widgets=[
                    Widget(widget_type=WidgetType.JOB_TITLE, order=0),
                    Widget(widget_type=WidgetType.JOB_STATUS, order=1),
                    Widget(widget_type=WidgetType.STATUS_INSTRUCTIONS, order=2),
                    Widget(widget_type=WidgetType.LINE_ITEMS, order=3),
                    Widget(widget_type=WidgetType.INVOICES, order=4),
                    Widget(widget_type=WidgetType.SIGNATURES, order=5),
                    Widget(widget_type=WidgetType.PAYMENTS, order=6),
                    Widget(widget_type=WidgetType.ACTION_BUTTONS, order=7),
                ],
                status_instructions="1. Create invoice\n2. Review with customer\n3. Collect signature\n4. Collect payment",
                display_action_menu=True,
                ability_to_change_status=True,
                focus_view_enabled=True,
                restrict_to_focus_view=True,
            ),
            # Status 6: Completed
            Status(
                name="Completed",
                category=StatusCategory.COMPLETED,
                color="#059669",
                sequence=6,
                user_role=UserRole.SERVICE_AGENT,
                action_buttons=[
                    ActionButton(
                        action=ActionButtonType.CLOCK_IN_OUT,
                        label="Clock Out",
                        order=0,
                        required=True,
                    ),
                    ActionButton(
                        action=ActionButtonType.REQUEST_REVIEW,
                        label="Request Review",
                        order=1,
                    ),
                ],
                widgets=[
                    Widget(widget_type=WidgetType.JOB_TITLE, order=0),
                    Widget(widget_type=WidgetType.JOB_STATUS, order=1),
                    Widget(widget_type=WidgetType.STATUS_INSTRUCTIONS, order=2),
                    Widget(widget_type=WidgetType.JOB_HISTORY, order=3),
                    Widget(widget_type=WidgetType.ACTION_BUTTONS, order=4),
                ],
                status_instructions="1. Clock out\n2. Request customer review",
                display_action_menu=True,
                ability_to_change_status=False,
                focus_view_enabled=True,
                restrict_to_focus_view=False,
            ),
        ],
    )


def main():
    """Run the Excel generation example."""
    print("=" * 60)
    print("ClearPath Excel Generator Example")
    print("=" * 60)
    print()

    # Step 1: Create or load a StatusActionFlow
    print("Step 1: Creating sample HVAC Service Call workflow...")
    config = create_sample_workflow()
    print(f"  Workflow: {config.name}")
    print(f"  Statuses: {len(config.statuses)}")
    print(f"  Total Actions: {sum(len(s.action_buttons) for s in config.statuses)}")
    print()

    # Step 2: Validate the configuration
    print("Step 2: Validating configuration...")
    validator = ConfigValidator()
    validation_result = validator.validate_config(config, check_best_practices=True)
    print(f"  Valid: {validation_result.is_valid}")
    print(f"  Errors: {validation_result.error_count}")
    print(f"  Warnings: {validation_result.warning_count}")
    if validation_result.issues:
        for issue in validation_result.issues[:3]:
            print(f"    - [{issue.severity.value}] {issue.message}")
    print()

    # Step 3: Convert to Excel template schema
    print("Step 3: Converting to Excel template schema...")
    converter = ConfigToExcelConverter()
    template = converter.convert(config)
    print(f"  Job Custom Status rows: {len(template.job_custom_statuses)}")
    print(f"  Action Button rows: {len(template.action_buttons)}")
    print(f"  Focus View rows: {len(template.focus_view)}")
    print()

    # Step 4: Validate the Excel template
    print("Step 4: Validating Excel template...")
    template_errors = converter.validate_excel_template(template)
    if template_errors:
        print("  Warnings:")
        for error in template_errors:
            print(f"    - {error}")
    else:
        print("  No validation errors!")
    print()

    # Step 5: Generate the Excel file
    print("Step 5: Generating Excel file...")
    generator = ExcelGenerator()

    # Use reports directory
    output_dir = Path(__file__).parent.parent / "reports"
    output_dir.mkdir(exist_ok=True)

    output_path = generator.generate(
        template,
        output_path=None,  # Auto-generate filename
        overwrite=True,
    )
    print(f"  Output: {output_path}")
    print()

    # Step 6: Show summary
    print("Step 6: Excel file structure summary")
    summary = converter.get_excel_summary(template)
    print(f"  Total statuses: {summary['total_statuses']}")
    print(f"  Roles used: {', '.join(summary['roles_used'])}")
    print("  Buttons per status:")
    for status, count in summary['unique_buttons_per_status'].items():
        print(f"    - {status}: {count} buttons")
    print()

    # Also save the config as JSON for reference
    json_output = output_dir / "sample_config.json"
    with open(json_output, "w") as f:
        json.dump(config.model_dump(mode="json"), f, indent=2)
    print(f"Config JSON saved to: {json_output}")
    print()

    print("=" * 60)
    print("Generation complete!")
    print("=" * 60)
    print()
    print("The generated Excel file has 3 tabs:")
    print("  1. Job Custom Status - Status definitions")
    print("  2. Action Buttons - Action buttons per status/role")
    print("  3. Focus View + Status Instruction - Widgets and settings")
    print()
    print("Import this file into FieldPulse ClearPath to create the workflow.")


if __name__ == "__main__":
    main()

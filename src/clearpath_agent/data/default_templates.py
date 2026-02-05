"""Default Workflow Templates.

Pre-configured workflow templates based on common industry patterns
extracted from production data.
"""

from typing import Optional

from ..models.entities import ActionButton, Status, StatusActionFlow, Widget
from ..models.enums import ActionButtonType, StatusCategory, UserRole, WidgetType


def _create_widget(widget_type: WidgetType, order: int) -> Widget:
    """Helper to create a Widget."""
    return Widget(widget_type=widget_type, order=order, collapsed=False)


def _create_action(
    action_type: ActionButtonType,
    label: str,
    order: int,
    required: bool = False,
    template_id: Optional[str] = None,
    form_id: Optional[str] = None,
) -> ActionButton:
    """Helper to create an ActionButton."""
    return ActionButton(
        action=action_type,
        label=label,
        order=order,
        required=required,
        template_id=template_id,
        form_id=form_id,
    )


# =============================================================================
# SERVICE CALL TEMPLATE
# Standard service call workflow: Scheduled → En Route → On Site → In Progress → Complete
# =============================================================================

SERVICE_CALL_TEMPLATE = StatusActionFlow(
    name="Service Call Workflow",
    description="Standard service call workflow for field service technicians",
    is_default=False,
    job_types=["Service Call", "Repair", "Maintenance"],
    statuses=[
        Status(
            name="Scheduled",
            category=StatusCategory.PENDING,
            color="#FCD34D",
            sequence=1,
            user_role=UserRole.SERVICE_AGENT,
            action_buttons=[
                _create_action(ActionButtonType.SEND_CUSTOMER_COMMUNICATION, "Confirm Appointment", 0, template_id="template:confirm-appointment"),
                _create_action(ActionButtonType.ADD_NOTE, "Add Note", 1),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.SCHEDULED_TIME, 3),
                _create_widget(WidgetType.CUSTOMER_CONTACT, 4),
                _create_widget(WidgetType.CUSTOMER_ADDRESS, 5),
                _create_widget(WidgetType.JOB_NOTES, 6),
                _create_widget(WidgetType.ACTION_BUTTONS, 7),
            ],
            status_instructions="1. Review job details\n2. Confirm appointment with customer\n3. Prepare for dispatch",
            display_action_menu=True,
            ability_to_change_status=True,
            focus_view_enabled=True,
            restrict_to_focus_view=False,
        ),
        Status(
            name="En Route",
            category=StatusCategory.IN_PROGRESS,
            color="#3B82F6",
            sequence=2,
            user_role=UserRole.SERVICE_AGENT,
            action_buttons=[
                _create_action(ActionButtonType.CLOCK_IN_OUT, "Clock In", 0),
                _create_action(ActionButtonType.SEND_CUSTOMER_COMMUNICATION, "On My Way Text", 1, template_id="template:on-my-way"),
                _create_action(ActionButtonType.ADD_NOTE, "Add Note", 2),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.CUSTOMER_ADDRESS, 3),
                _create_widget(WidgetType.CUSTOMER_CONTACT, 4),
                _create_widget(WidgetType.TIMESHEETS, 5),
                _create_widget(WidgetType.ACTION_BUTTONS, 6),
            ],
            status_instructions="1. Clock in for the job\n2. Send on-the-way text to customer\n3. Navigate to job site",
            display_action_menu=True,
            ability_to_change_status=True,
            focus_view_enabled=True,
            restrict_to_focus_view=True,
        ),
        Status(
            name="On Site",
            category=StatusCategory.IN_PROGRESS,
            color="#3B82F6",
            sequence=3,
            user_role=UserRole.SERVICE_AGENT,
            action_buttons=[
                _create_action(ActionButtonType.SEND_CUSTOMER_COMMUNICATION, "Arrival Text", 0, template_id="template:arrival-notification"),
                _create_action(ActionButtonType.TAKE_PHOTO, "Before Photos", 1),
                _create_action(ActionButtonType.FILL_FORM, "Safety Check", 2, form_id="form:safety-check"),
                _create_action(ActionButtonType.ADD_NOTE, "Add Note", 3),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.CUSTOMER_CONTACT, 3),
                _create_widget(WidgetType.JOB_NOTES, 4),
                _create_widget(WidgetType.FORMS, 5),
                _create_widget(WidgetType.FILES_PHOTOS, 6),
                _create_widget(WidgetType.ACTION_BUTTONS, 7),
            ],
            status_instructions="1. Send arrival notification\n2. Take before photos\n3. Complete safety inspection\n4. Review job scope with customer",
            display_action_menu=True,
            ability_to_change_status=True,
            focus_view_enabled=True,
            restrict_to_focus_view=True,
        ),
        Status(
            name="In Progress",
            category=StatusCategory.IN_PROGRESS,
            color="#3B82F6",
            sequence=4,
            user_role=UserRole.SERVICE_AGENT,
            action_buttons=[
                _create_action(ActionButtonType.TAKE_PHOTO, "Progress Photos", 0),
                _create_action(ActionButtonType.FILL_FORM, "Work Form", 1, form_id="form:work-form"),
                _create_action(ActionButtonType.ADD_MATERIAL, "Add Materials", 2),
                _create_action(ActionButtonType.ADD_NOTE, "Add Note", 3),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.JOB_NOTES, 3),
                _create_widget(WidgetType.FORMS, 4),
                _create_widget(WidgetType.MATERIALS, 5),
                _create_widget(WidgetType.FILES_PHOTOS, 6),
                _create_widget(WidgetType.ACTION_BUTTONS, 7),
            ],
            status_instructions="1. Perform service work\n2. Document progress with photos\n3. Record materials used\n4. Complete required forms",
            display_action_menu=True,
            ability_to_change_status=True,
            focus_view_enabled=True,
            restrict_to_focus_view=True,
        ),
        Status(
            name="Complete",
            category=StatusCategory.COMPLETED,
            color="#22C55E",
            sequence=5,
            user_role=UserRole.SERVICE_AGENT,
            action_buttons=[
                _create_action(ActionButtonType.TAKE_PHOTO, "After Photos", 0),
                _create_action(ActionButtonType.CREATE_INVOICE, "Create Invoice", 1, template_id="template:invoice"),
                _create_action(ActionButtonType.COLLECT_SIGNATURE, "Get Signature", 2),
                _create_action(ActionButtonType.COLLECT_PAYMENT, "Collect Payment", 3),
                _create_action(ActionButtonType.CLOCK_IN_OUT, "Clock Out", 4),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.FILES_PHOTOS, 3),
                _create_widget(WidgetType.INVOICES, 4),
                _create_widget(WidgetType.SIGNATURES, 5),
                _create_widget(WidgetType.PAYMENTS, 6),
                _create_widget(WidgetType.TIMESHEETS, 7),
                _create_widget(WidgetType.ACTION_BUTTONS, 8),
            ],
            status_instructions="1. Take after photos\n2. Create and present invoice\n3. Collect customer signature\n4. Collect payment\n5. Clock out",
            display_action_menu=True,
            ability_to_change_status=False,
            focus_view_enabled=True,
            restrict_to_focus_view=False,
        ),
    ],
)


# =============================================================================
# INSTALLATION TEMPLATE
# Installation workflow with pre-work, installation, testing phases
# =============================================================================

INSTALLATION_TEMPLATE = StatusActionFlow(
    name="Installation Workflow",
    description="Installation workflow with pre-work, installation, and testing phases",
    is_default=False,
    job_types=["Installation", "New Install", "Equipment Install"],
    statuses=[
        Status(
            name="Scheduled",
            category=StatusCategory.PENDING,
            color="#FCD34D",
            sequence=1,
            user_role=UserRole.OFFICE_STAFF,
            action_buttons=[
                _create_action(ActionButtonType.SEND_CUSTOMER_COMMUNICATION, "Confirm Install Date", 0, template_id="template:confirm-installation"),
                _create_action(ActionButtonType.ADD_NOTE, "Add Note", 1),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.SCHEDULED_TIME, 3),
                _create_widget(WidgetType.CUSTOMER_CONTACT, 4),
                _create_widget(WidgetType.ESTIMATES, 5),
                _create_widget(WidgetType.ACTION_BUTTONS, 6),
            ],
            status_instructions="1. Review installation requirements\n2. Confirm install date with customer\n3. Verify equipment availability",
            display_action_menu=True,
            ability_to_change_status=True,
            focus_view_enabled=True,
            restrict_to_focus_view=False,
        ),
        Status(
            name="Pre-Work",
            category=StatusCategory.IN_PROGRESS,
            color="#3B82F6",
            sequence=2,
            user_role=UserRole.SERVICE_AGENT,
            action_buttons=[
                _create_action(ActionButtonType.CLOCK_IN_OUT, "Clock In", 0),
                _create_action(ActionButtonType.TAKE_PHOTO, "Site Photos", 1),
                _create_action(ActionButtonType.FILL_FORM, "Pre-Install Checklist", 2, form_id="form:pre-install-checklist"),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.JOB_NOTES, 3),
                _create_widget(WidgetType.FORMS, 4),
                _create_widget(WidgetType.FILES_PHOTOS, 5),
                _create_widget(WidgetType.ACTION_BUTTONS, 6),
            ],
            status_instructions="1. Clock in\n2. Take site photos\n3. Complete pre-installation checklist\n4. Verify measurements and clearances",
            display_action_menu=True,
            ability_to_change_status=True,
            focus_view_enabled=True,
            restrict_to_focus_view=True,
        ),
        Status(
            name="Installation",
            category=StatusCategory.IN_PROGRESS,
            color="#3B82F6",
            sequence=3,
            user_role=UserRole.SERVICE_AGENT,
            action_buttons=[
                _create_action(ActionButtonType.TAKE_PHOTO, "Progress Photos", 0),
                _create_action(ActionButtonType.ADD_MATERIAL, "Add Materials", 1),
                _create_action(ActionButtonType.CREATE_ASSET, "Create Asset", 2),
                _create_action(ActionButtonType.ADD_NOTE, "Add Note", 3),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.MATERIALS, 3),
                _create_widget(WidgetType.ASSETS, 4),
                _create_widget(WidgetType.FILES_PHOTOS, 5),
                _create_widget(WidgetType.ACTION_BUTTONS, 6),
            ],
            status_instructions="1. Install equipment per specifications\n2. Document progress with photos\n3. Record materials used\n4. Create asset record for new equipment",
            display_action_menu=True,
            ability_to_change_status=True,
            focus_view_enabled=True,
            restrict_to_focus_view=True,
        ),
        Status(
            name="Testing",
            category=StatusCategory.IN_PROGRESS,
            color="#3B82F6",
            sequence=4,
            user_role=UserRole.SERVICE_AGENT,
            action_buttons=[
                _create_action(ActionButtonType.FILL_FORM, "Test Form", 0, form_id="form:test-form"),
                _create_action(ActionButtonType.TAKE_PHOTO, "Test Photos", 1),
                _create_action(ActionButtonType.UPDATE_ASSET, "Update Asset", 2),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.FORMS, 3),
                _create_widget(WidgetType.ASSETS, 4),
                _create_widget(WidgetType.FILES_PHOTOS, 5),
                _create_widget(WidgetType.ACTION_BUTTONS, 6),
            ],
            status_instructions="1. Complete testing procedures\n2. Document test results with form\n3. Take photos of completed installation\n4. Update asset record with serial numbers",
            display_action_menu=True,
            ability_to_change_status=True,
            focus_view_enabled=True,
            restrict_to_focus_view=True,
        ),
        Status(
            name="Customer Walkthrough",
            category=StatusCategory.IN_PROGRESS,
            color="#3B82F6",
            sequence=5,
            user_role=UserRole.SERVICE_AGENT,
            action_buttons=[
                _create_action(ActionButtonType.SEND_CUSTOMER_COMMUNICATION, "Training Complete", 0, template_id="template:training-complete"),
                _create_action(ActionButtonType.COLLECT_SIGNATURE, "Get Approval", 1),
                _create_action(ActionButtonType.TAKE_PHOTO, "Final Photos", 2),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.CUSTOMER_CONTACT, 3),
                _create_widget(WidgetType.SIGNATURES, 4),
                _create_widget(WidgetType.FILES_PHOTOS, 5),
                _create_widget(WidgetType.ACTION_BUTTONS, 6),
            ],
            status_instructions="1. Walk customer through operation\n2. Answer questions\n3. Collect customer approval signature\n4. Take final installation photos",
            display_action_menu=True,
            ability_to_change_status=True,
            focus_view_enabled=True,
            restrict_to_focus_view=True,
        ),
        Status(
            name="Complete",
            category=StatusCategory.COMPLETED,
            color="#22C55E",
            sequence=6,
            user_role=UserRole.SERVICE_AGENT,
            action_buttons=[
                _create_action(ActionButtonType.CREATE_INVOICE, "Create Invoice", 0, template_id="template:invoice"),
                _create_action(ActionButtonType.COLLECT_PAYMENT, "Collect Payment", 1),
                _create_action(ActionButtonType.CLOCK_IN_OUT, "Clock Out", 2),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.INVOICES, 3),
                _create_widget(WidgetType.PAYMENTS, 4),
                _create_widget(WidgetType.TIMESHEETS, 5),
                _create_widget(WidgetType.ACTION_BUTTONS, 6),
            ],
            status_instructions="1. Create invoice\n2. Collect payment\n3. Clock out",
            display_action_menu=True,
            ability_to_change_status=False,
            focus_view_enabled=True,
            restrict_to_focus_view=False,
        ),
    ],
)


# =============================================================================
# INSPECTION TEMPLATE
# Inspection workflow with arrival, inspection, reporting phases
# =============================================================================

INSPECTION_TEMPLATE = StatusActionFlow(
    name="Inspection Workflow",
    description="Inspection workflow with arrival, inspection, and reporting phases",
    is_default=False,
    job_types=["Inspection", "Assessment", "Evaluation"],
    statuses=[
        Status(
            name="Scheduled",
            category=StatusCategory.PENDING,
            color="#FCD34D",
            sequence=1,
            user_role=UserRole.OFFICE_STAFF,
            action_buttons=[
                _create_action(ActionButtonType.SEND_CUSTOMER_COMMUNICATION, "Confirm Inspection", 0, template_id="template:confirm-inspection"),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.SCHEDULED_TIME, 3),
                _create_widget(WidgetType.CUSTOMER_CONTACT, 4),
                _create_widget(WidgetType.ACTION_BUTTONS, 5),
            ],
            status_instructions="1. Confirm inspection time with customer",
            display_action_menu=True,
            ability_to_change_status=True,
            focus_view_enabled=True,
            restrict_to_focus_view=False,
        ),
        Status(
            name="On Site",
            category=StatusCategory.IN_PROGRESS,
            color="#3B82F6",
            sequence=2,
            user_role=UserRole.SERVICE_AGENT,
            action_buttons=[
                _create_action(ActionButtonType.CLOCK_IN_OUT, "Clock In", 0),
                _create_action(ActionButtonType.SEND_CUSTOMER_COMMUNICATION, "Arrived", 1, template_id="template:arrival-notification"),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.CUSTOMER_CONTACT, 3),
                _create_widget(WidgetType.TIMESHEETS, 4),
                _create_widget(WidgetType.ACTION_BUTTONS, 5),
            ],
            status_instructions="1. Clock in\n2. Notify customer of arrival",
            display_action_menu=True,
            ability_to_change_status=True,
            focus_view_enabled=True,
            restrict_to_focus_view=True,
        ),
        Status(
            name="Inspecting",
            category=StatusCategory.IN_PROGRESS,
            color="#3B82F6",
            sequence=3,
            user_role=UserRole.SERVICE_AGENT,
            action_buttons=[
                _create_action(ActionButtonType.FILL_FORM, "Inspection Form", 0, required=True, form_id="form:inspection-form"),
                _create_action(ActionButtonType.TAKE_PHOTO, "Inspection Photos", 1),
                _create_action(ActionButtonType.ADD_NOTE, "Add Note", 2),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.FORMS, 3),
                _create_widget(WidgetType.FILES_PHOTOS, 4),
                _create_widget(WidgetType.JOB_NOTES, 5),
                _create_widget(WidgetType.ACTION_BUTTONS, 6),
            ],
            status_instructions="1. Complete inspection form (required)\n2. Take photos of all findings\n3. Document any issues in notes",
            display_action_menu=True,
            ability_to_change_status=True,
            focus_view_enabled=True,
            restrict_to_focus_view=True,
        ),
        Status(
            name="Reporting",
            category=StatusCategory.IN_PROGRESS,
            color="#3B82F6",
            sequence=4,
            user_role=UserRole.SERVICE_AGENT,
            action_buttons=[
                _create_action(ActionButtonType.CREATE_ESTIMATE, "Create Quote", 0, template_id="template:estimate"),
                _create_action(ActionButtonType.COLLECT_SIGNATURE, "Customer Acknowledgment", 1),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.FORMS, 3),
                _create_widget(WidgetType.ESTIMATES, 4),
                _create_widget(WidgetType.SIGNATURES, 5),
                _create_widget(WidgetType.ACTION_BUTTONS, 6),
            ],
            status_instructions="1. Review findings with customer\n2. Create quote for recommended repairs\n3. Get customer acknowledgment",
            display_action_menu=True,
            ability_to_change_status=True,
            focus_view_enabled=True,
            restrict_to_focus_view=True,
        ),
        Status(
            name="Complete",
            category=StatusCategory.COMPLETED,
            color="#22C55E",
            sequence=5,
            user_role=UserRole.SERVICE_AGENT,
            action_buttons=[
                _create_action(ActionButtonType.CLOCK_IN_OUT, "Clock Out", 0),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.FORMS, 3),
                _create_widget(WidgetType.FILES_PHOTOS, 4),
                _create_widget(WidgetType.TIMESHEETS, 5),
                _create_widget(WidgetType.ACTION_BUTTONS, 6),
            ],
            status_instructions="1. Clock out",
            display_action_menu=True,
            ability_to_change_status=False,
            focus_view_enabled=True,
            restrict_to_focus_view=False,
        ),
    ],
)


# =============================================================================
# EMERGENCY TEMPLATE
# Emergency service workflow with rapid response steps
# =============================================================================

EMERGENCY_TEMPLATE = StatusActionFlow(
    name="Emergency Service Workflow",
    description="Emergency/urgent service workflow with rapid response steps",
    is_default=False,
    job_types=["Emergency", "Urgent", "Priority Call"],
    statuses=[
        Status(
            name="Dispatched",
            category=StatusCategory.PENDING,
            color="#EF4444",
            sequence=1,
            user_role=UserRole.SERVICE_AGENT,
            action_buttons=[
                _create_action(ActionButtonType.CLOCK_IN_OUT, "Clock In", 0),
                _create_action(ActionButtonType.SEND_CUSTOMER_COMMUNICATION, "On My Way", 1, template_id="template:on-my-way"),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.CUSTOMER_ADDRESS, 3),
                _create_widget(WidgetType.CUSTOMER_CONTACT, 4),
                _create_widget(WidgetType.JOB_NOTES, 5),
                _create_widget(WidgetType.ACTION_BUTTONS, 6),
            ],
            status_instructions="1. Clock in immediately\n2. Send on-my-way notification\n3. Proceed directly to customer",
            display_action_menu=True,
            ability_to_change_status=True,
            focus_view_enabled=True,
            restrict_to_focus_view=True,
        ),
        Status(
            name="On Site",
            category=StatusCategory.IN_PROGRESS,
            color="#EF4444",
            sequence=2,
            user_role=UserRole.SERVICE_AGENT,
            action_buttons=[
                _create_action(ActionButtonType.SEND_CUSTOMER_COMMUNICATION, "Arrived", 0, template_id="template:arrival-notification"),
                _create_action(ActionButtonType.TAKE_PHOTO, "Document Issue", 1),
                _create_action(ActionButtonType.FILL_FORM, "Safety Assessment", 2, form_id="form:safety-assessment"),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.CUSTOMER_CONTACT, 3),
                _create_widget(WidgetType.FORMS, 4),
                _create_widget(WidgetType.FILES_PHOTOS, 5),
                _create_widget(WidgetType.ACTION_BUTTONS, 6),
            ],
            status_instructions="1. Notify arrival\n2. Assess situation and document\n3. Complete safety assessment if needed",
            display_action_menu=True,
            ability_to_change_status=True,
            focus_view_enabled=True,
            restrict_to_focus_view=True,
        ),
        Status(
            name="Working",
            category=StatusCategory.IN_PROGRESS,
            color="#EF4444",
            sequence=3,
            user_role=UserRole.SERVICE_AGENT,
            action_buttons=[
                _create_action(ActionButtonType.TAKE_PHOTO, "Progress Photos", 0),
                _create_action(ActionButtonType.ADD_MATERIAL, "Add Materials", 1),
                _create_action(ActionButtonType.ADD_NOTE, "Add Note", 2),
                _create_action(ActionButtonType.CREATE_ESTIMATE, "Create Estimate", 3, template_id="template:estimate"),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.MATERIALS, 3),
                _create_widget(WidgetType.ESTIMATES, 4),
                _create_widget(WidgetType.FILES_PHOTOS, 5),
                _create_widget(WidgetType.ACTION_BUTTONS, 6),
            ],
            status_instructions="1. Resolve emergency situation\n2. Document work performed\n3. Record materials used\n4. Create estimate if additional work needed",
            display_action_menu=True,
            ability_to_change_status=True,
            focus_view_enabled=True,
            restrict_to_focus_view=True,
        ),
        Status(
            name="Complete",
            category=StatusCategory.COMPLETED,
            color="#22C55E",
            sequence=4,
            user_role=UserRole.SERVICE_AGENT,
            action_buttons=[
                _create_action(ActionButtonType.TAKE_PHOTO, "After Photos", 0),
                _create_action(ActionButtonType.CREATE_INVOICE, "Create Invoice", 1, template_id="template:invoice"),
                _create_action(ActionButtonType.COLLECT_SIGNATURE, "Get Signature", 2),
                _create_action(ActionButtonType.COLLECT_PAYMENT, "Collect Payment", 3),
                _create_action(ActionButtonType.CLOCK_IN_OUT, "Clock Out", 4),
            ],
            widgets=[
                _create_widget(WidgetType.JOB_TITLE, 0),
                _create_widget(WidgetType.JOB_STATUS, 1),
                _create_widget(WidgetType.STATUS_INSTRUCTIONS, 2),
                _create_widget(WidgetType.FILES_PHOTOS, 3),
                _create_widget(WidgetType.INVOICES, 4),
                _create_widget(WidgetType.SIGNATURES, 5),
                _create_widget(WidgetType.PAYMENTS, 6),
                _create_widget(WidgetType.TIMESHEETS, 7),
                _create_widget(WidgetType.ACTION_BUTTONS, 8),
            ],
            status_instructions="1. Take after photos\n2. Create invoice\n3. Collect signature\n4. Collect payment\n5. Clock out",
            display_action_menu=True,
            ability_to_change_status=False,
            focus_view_enabled=True,
            restrict_to_focus_view=False,
        ),
    ],
)


# =============================================================================
# TEMPLATE REGISTRY
# =============================================================================

TEMPLATES = {
    "service_call": SERVICE_CALL_TEMPLATE,
    "installation": INSTALLATION_TEMPLATE,
    "inspection": INSPECTION_TEMPLATE,
    "emergency": EMERGENCY_TEMPLATE,
}


def get_template(name: str) -> Optional[StatusActionFlow]:
    """Get a template by name.

    Args:
        name: Template name (case-insensitive)

    Returns:
        StatusActionFlow template or None if not found
    """
    return TEMPLATES.get(name.lower())


def list_templates() -> list[dict]:
    """List all available templates.

    Returns:
        List of dicts with template info
    """
    return [
        {
            "name": key,
            "display_name": template.name,
            "description": template.description,
            "status_count": len(template.statuses),
            "job_types": template.job_types,
        }
        for key, template in TEMPLATES.items()
    ]


class TemplateSelector:
    """Selects the best template based on user intent."""

    # Keywords for template matching
    TEMPLATE_KEYWORDS = {
        "service_call": [
            "service", "repair", "maintenance", "fix", "call",
            "service call", "routine", "standard",
        ],
        "installation": [
            "install", "installation", "new", "setup", "equipment",
            "new install", "equipment install",
        ],
        "inspection": [
            "inspect", "inspection", "assessment", "evaluate", "check",
            "survey", "audit",
        ],
        "emergency": [
            "emergency", "urgent", "priority", "asap", "critical",
            "rush", "same day",
        ],
    }

    def select(
        self,
        intent_description: str,
        job_types: Optional[list[str]] = None,
    ) -> Optional[str]:
        """Select the best template based on intent.

        Args:
            intent_description: Description of the workflow intent
            job_types: Optional list of job types

        Returns:
            Template name or None if no match
        """
        description_lower = intent_description.lower()

        # Check job types first
        if job_types:
            for job_type in job_types:
                job_type_lower = job_type.lower()
                for template_name, template in TEMPLATES.items():
                    if any(
                        jt.lower() == job_type_lower
                        for jt in template.job_types
                    ):
                        return template_name

        # Check keywords in description
        scores = {}
        for template_name, keywords in self.TEMPLATE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in description_lower)
            if score > 0:
                scores[template_name] = score

        if scores:
            return max(scores, key=scores.get)

        return None

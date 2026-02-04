"""Enumerations for ClearPath entities."""

from enum import Enum


class ActionButtonType(str, Enum):
    """Available action button types in ClearPath (27 total)."""

    CLOCK_IN_OUT = "Job Timesheet Clock in / out"
    SEND_CUSTOMER_COMMUNICATION = "Send Customer Communication"
    FILL_FORM = "Fill Form"
    TAKE_PHOTO = "Take Photo"
    COLLECT_SIGNATURE = "Collect Signature"
    COLLECT_PAYMENT = "Collect Payment"
    ADD_LINE_ITEM = "Add Line Item"
    ADD_MATERIAL = "Add Material"
    ADD_LABOR = "Add Labor"
    ADD_EXPENSE = "Add Expense"
    CREATE_ESTIMATE = "Create Estimate"
    CREATE_INVOICE = "Create Invoice"
    SEND_ESTIMATE = "Send Estimate"
    SEND_INVOICE = "Send Invoice"
    VIEW_ESTIMATE = "View Estimate"
    VIEW_INVOICE = "View Invoice"
    ADD_NOTE = "Add Note"
    ADD_ATTACHMENT = "Add Attachment"
    VIEW_CUSTOMER_HISTORY = "View Customer History"
    VIEW_ASSET_HISTORY = "View Asset History"
    VIEW_JOB_HISTORY = "View Job History"
    UPDATE_ASSET = "Update Asset"
    CREATE_ASSET = "Create Asset"
    SCHEDULE_FOLLOW_UP = "Schedule Follow Up"
    REQUEST_REVIEW = "Request Review"
    MARK_COMPLETE = "Mark Complete"
    CUSTOM_ACTION = "Custom Action"


class WidgetType(str, Enum):
    """Available widget types for Focus View in ClearPath (31 total)."""

    JOB_TITLE = "Job Title"
    JOB_STATUS = "Job Status"
    STATUS_INSTRUCTIONS = "Status Instructions"
    CUSTOMER_CONTACT = "Customer Contact"
    CUSTOMER_ADDRESS = "Customer Address"
    CUSTOMER_NOTES = "Customer Notes"
    JOB_DETAILS = "Job Details"
    JOB_DESCRIPTION = "Job Description"
    JOB_NOTES = "Job Notes"
    JOB_TAGS = "Job Tags"
    JOB_CUSTOM_FIELDS = "Job Custom Fields"
    ASSIGNED_TEAM = "Assigned Team"
    SCHEDULED_TIME = "Scheduled Time"
    ACTION_BUTTONS = "Action Buttons"
    FORMS = "Forms"
    FILES_PHOTOS = "Files/Photos"
    SIGNATURES = "Signatures"
    ESTIMATES = "Estimates"
    INVOICES = "Invoices"
    PAYMENTS = "Payments"
    LINE_ITEMS = "Line Items"
    MATERIALS = "Materials"
    LABOR = "Labor"
    EXPENSES = "Expenses"
    TIMESHEETS = "Timesheets"
    ASSETS = "Assets"
    ASSET_DETAILS = "Asset Details"
    CUSTOMER_HISTORY = "Customer History"
    JOB_HISTORY = "Job History"
    RELATED_JOBS = "Related Jobs"
    CHECKLIST = "Checklist"


class UserRole(str, Enum):
    """User roles that can be assigned to statuses."""

    SERVICE_AGENT = "Service Agent"
    OFFICE_STAFF = "Office Staff"
    MANAGER = "Manager"
    ADMIN = "Admin"
    TECHNICIAN = "Technician"
    DISPATCHER = "Dispatcher"
    SALES = "Sales"


class StatusCategory(str, Enum):
    """Categories for job statuses."""

    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    ON_HOLD = "On Hold"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"

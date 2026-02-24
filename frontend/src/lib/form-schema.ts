import type { BusinessContext } from "@/types/discovery";

// ============================================================
// Form Schema: Defines the structured form that drives
// discovery prompts, form UI rendering, and completion tracking.
// Change fields here — the rest of the system adapts automatically.
// ============================================================

// --- Types ---

export type FieldType =
  | "text"
  | "textarea"
  | "dropdown"
  | "multi-select"
  | "toggle"
  | "checkboxes";

export interface FieldOption {
  value: string;
  label: string;
}

export interface FormFieldDefinition {
  id: string;
  label: string;
  type: FieldType;
  options?: FieldOption[];
  placeholder?: string;
  helpText?: string;
  required: boolean;
  llmHint?: string; // shown ONLY to the LLM in the prompt, not in the UI
}

export interface FormSectionDefinition {
  id: string;
  label: string;
  description: string;
  fields: FormFieldDefinition[];
}

// Form state is a flat map — not nested by section.
// Flat makes LLM extraction + merge trivial: Object.assign(state, extraction)
export type FormFieldValue = string | string[] | boolean | null;
export type FormState = Record<string, FormFieldValue>;

// --- Schema Definition (DRAFT — team will iterate) ---

export const FORM_SCHEMA: FormSectionDefinition[] = [
  {
    id: "intake",
    label: "Job Intake",
    description: "How jobs come in, who creates them, scheduling",
    fields: [
      {
        id: "job_source",
        label: "Where do jobs come from?",
        type: "multi-select",
        options: [
          { value: "phone", label: "Phone calls" },
          { value: "online_booking", label: "Online booking" },
          { value: "referral", label: "Referrals" },
          { value: "office_dispatch", label: "Office dispatch" },
          { value: "text", label: "Text/SMS" },
          { value: "portal", label: "Customer portal" },
        ],
        required: true,
        llmHint: "Common sources: phone, online booking, referral, office dispatch, text",
      },
      {
        id: "job_creator",
        label: "Who creates the job in the system?",
        type: "dropdown",
        options: [
          { value: "office", label: "Office / dispatcher" },
          { value: "tech", label: "Technician in field" },
          { value: "both", label: "Both" },
          { value: "auto", label: "Auto-created from booking" },
        ],
        required: true,
      },
      {
        id: "scheduling_step",
        label: "Is there a scheduling step before dispatch?",
        type: "toggle",
        required: false,
        llmHint: "Some companies schedule first, others dispatch immediately",
      },
    ],
  },
  {
    id: "en_route",
    label: "En Route",
    description: "Between dispatch and arrival at the job site",
    fields: [
      {
        id: "customer_notification",
        label: "Notify the customer when the tech is on the way?",
        type: "toggle",
        required: true,
        llmHint: "Most companies text the customer when en route",
      },
      {
        id: "clock_in_timing",
        label: "When does the tech clock in?",
        type: "dropdown",
        options: [
          { value: "before_driving", label: "Before driving to job" },
          { value: "on_arrival", label: "When they arrive on site" },
          { value: "no_clock", label: "No clock-in required" },
        ],
        required: true,
      },
      {
        id: "gps_tracking",
        label: "GPS tracking needed for drive time?",
        type: "toggle",
        required: false,
      },
      {
        id: "appointment_confirmation",
        label: "Do you confirm the appointment with the customer?",
        type: "toggle",
        required: false,
      },
    ],
  },
  {
    id: "arrival",
    label: "Arrival",
    description: "First actions when the tech arrives on site",
    fields: [
      {
        id: "first_action",
        label: "What's the first thing the tech does on site?",
        type: "dropdown",
        options: [
          { value: "meet_customer", label: "Meet the customer" },
          { value: "before_photos", label: "Take before photos" },
          { value: "safety_check", label: "Safety check / site assessment" },
          { value: "confirm_scope", label: "Confirm scope of work" },
          { value: "check_in", label: "Check in / announce arrival" },
        ],
        required: true,
        llmHint: "What happens first when they walk up to the door or job site?",
      },
      {
        id: "pre_work_requirements",
        label: "Pre-work requirements before starting",
        type: "checkboxes",
        options: [
          { value: "before_photos", label: "Before photos" },
          { value: "safety_check", label: "Safety check" },
          { value: "customer_signature", label: "Customer signature / authorization" },
          { value: "site_assessment", label: "Site assessment form" },
        ],
        required: false,
        helpText: "Select all that apply",
      },
    ],
  },
  {
    id: "during_work",
    label: "During Work",
    description: "What happens while the tech is working on the job",
    fields: [
      {
        id: "forms_checklists",
        label: "Are forms or checklists required during the job?",
        type: "toggle",
        required: true,
        llmHint: "Inspection forms, safety checklists, service reports, etc.",
      },
      {
        id: "photo_requirements",
        label: "Photo requirements during the job",
        type: "dropdown",
        options: [
          { value: "before_and_after", label: "Before & after photos" },
          { value: "before_only", label: "Before photos only" },
          { value: "after_only", label: "After photos only" },
          { value: "progress", label: "Progress photos throughout" },
          { value: "none", label: "No photos required" },
        ],
        required: true,
      },
      {
        id: "estimates_or_invoices_onsite",
        label: "Do techs create estimates or invoices on site?",
        type: "dropdown",
        options: [
          { value: "estimates", label: "Estimates on site" },
          { value: "invoices", label: "Invoices on site" },
          { value: "both", label: "Both estimates and invoices" },
          { value: "neither", label: "Office handles these" },
        ],
        required: false,
      },
      {
        id: "info_needed_on_screen",
        label: "What info does the tech need to see during the job?",
        type: "multi-select",
        options: [
          { value: "job_details", label: "Job details / description" },
          { value: "customer_info", label: "Customer contact info" },
          { value: "job_history", label: "Job / equipment history" },
          { value: "parts_list", label: "Parts / materials list" },
          { value: "notes", label: "Job notes" },
          { value: "forms", label: "Forms / checklists" },
          { value: "photos", label: "Photos / files" },
        ],
        required: false,
        helpText: "Select all that the tech should see in their mobile view",
      },
      {
        id: "estimate_during_service",
        label: "Can techs create estimates for new work while on site?",
        type: "toggle",
        required: false,
        llmHint: "Common: tech is on-site for service and customer asks for a quote on something else",
      },
      {
        id: "asset_logging",
        label: "Where do assets get logged?",
        type: "dropdown",
        options: [
          { value: "new_equipment", label: "Installing new equipment" },
          { value: "existing_assets", label: "Connecting existing assets" },
          { value: "both", label: "Both" },
          { value: "none", label: "No assets" },
        ],
        required: false,
      },
      {
        id: "can_tech_exit_focus_view",
        label: "Can the tech swipe out of Focus View?",
        type: "toggle",
        required: false,
        llmHint: "Almost all customers want techs locked into focus view",
      },
      {
        id: "can_tech_change_status",
        label: "Can the tech change status from the action button?",
        type: "toggle",
        required: false,
      },
    ],
  },
  {
    id: "completion",
    label: "Completion",
    description: "Wrapping up the job — signatures, invoicing, payment",
    fields: [
      {
        id: "completion_requirements",
        label: "What must happen before the job can be marked complete?",
        type: "checkboxes",
        options: [
          { value: "after_photos", label: "After photos" },
          { value: "customer_signature", label: "Customer signature" },
          { value: "completion_notes", label: "Completion notes" },
          { value: "form_submitted", label: "Form / checklist submitted" },
          { value: "invoice_created", label: "Invoice created" },
        ],
        required: true,
        helpText: "Select all that apply",
      },
      {
        id: "invoice_process",
        label: "Who handles invoicing?",
        type: "dropdown",
        options: [
          { value: "tech_on_site", label: "Tech creates invoice on site" },
          { value: "office_after", label: "Office creates invoice after" },
          { value: "auto_from_estimate", label: "Auto-generated from estimate" },
        ],
        required: true,
      },
      {
        id: "payment_collection",
        label: "Is payment collected on site?",
        type: "toggle",
        required: false,
        llmHint: "Some companies collect payment at the door, others invoice later",
      },
      {
        id: "signature_required",
        label: "Customer signature required at completion?",
        type: "toggle",
        required: false,
      },
      {
        id: "invoice_separation",
        label: "Should invoicing be a separate status stage?",
        type: "dropdown",
        options: [
          { value: "same_as_completion", label: "Same status as work completion" },
          { value: "separate_status", label: "Separate invoicing status" },
          { value: "office_handles", label: "Office handles invoicing separately" },
        ],
        required: false,
        llmHint: "About 50/50 — some customers want a dedicated invoicing status, others fold it into completion",
      },
    ],
  },
  {
    id: "edge_cases",
    label: "Edge Cases & Pain Points",
    description: "What goes wrong, what frustrates your team",
    fields: [
      {
        id: "forgotten_steps",
        label: "What steps do techs commonly forget?",
        type: "textarea",
        required: false,
        placeholder: "e.g. Taking photos, filling out forms, updating job status...",
        helpText: "These become status instructions, not new statuses.",
        llmHint: "Common: forgetting photos, not filling out paperwork, skipping steps. These become reminders in status instructions, not new statuses.",
      },
      {
        id: "parts_not_available",
        label: "What happens when parts aren't available?",
        type: "dropdown",
        options: [
          { value: "supply_house", label: "Go to supply house" },
          { value: "order_reschedule", label: "Order parts, reschedule" },
          { value: "swap_truck", label: "Swap from another truck" },
          { value: "other", label: "Other" },
        ],
        required: false,
        llmHint: "What's the protocol when the tech doesn't have the right parts?",
      },
      {
        id: "customer_absent",
        label: "What happens when the customer isn't there?",
        type: "dropdown",
        options: [
          { value: "call_wait", label: "Call and wait" },
          { value: "leave_note", label: "Leave a note, move on" },
          { value: "reschedule", label: "Reschedule the job" },
          { value: "start_anyway", label: "Start work anyway" },
        ],
        required: false,
      },
    ],
  },
  {
    id: "preferences",
    label: "Workflow Preferences",
    description: "General preferences and existing setup",
    fields: [
      {
        id: "existing_forms",
        label: "Existing forms or checklists in FieldPulse",
        type: "text",
        required: false,
        placeholder: "e.g. Safety checklist, Inspection form",
        helpText: "Separate multiple forms with commas",
      },
      {
        id: "spanish_speaking_techs",
        label: "Are your technicians Spanish-speaking?",
        type: "toggle",
        required: false,
      },
    ],
  },
];

// --- Helper Functions ---

/**
 * Create an empty FormState from the schema with all fields set to null.
 */
export function initializeFormState(schema: FormSectionDefinition[]): FormState {
  const state: FormState = {};
  for (const section of schema) {
    for (const field of section.fields) {
      state[field.id] = null;
    }
  }
  return state;
}

/**
 * Count filled/total fields and required filled/required total.
 */
export function getFormProgress(
  schema: FormSectionDefinition[],
  state: FormState
): { filled: number; total: number; requiredFilled: number; requiredTotal: number } {
  let filled = 0;
  let total = 0;
  let requiredFilled = 0;
  let requiredTotal = 0;

  for (const section of schema) {
    for (const field of section.fields) {
      total++;
      if (field.required) requiredTotal++;

      if (isFieldFilled(state[field.id])) {
        filled++;
        if (field.required) requiredFilled++;
      }
    }
  }

  return { filled, total, requiredFilled, requiredTotal };
}

/**
 * Get progress for a single section.
 */
export function getSectionProgress(
  section: FormSectionDefinition,
  state: FormState
): { filled: number; total: number } {
  let filled = 0;
  const total = section.fields.length;

  for (const field of section.fields) {
    if (isFieldFilled(state[field.id])) filled++;
  }

  return { filled, total };
}

/**
 * Get unfilled required fields (for fallback question generation).
 */
export function getUnfilledRequiredFields(
  schema: FormSectionDefinition[],
  state: FormState
): FormFieldDefinition[] {
  const unfilled: FormFieldDefinition[] = [];
  for (const section of schema) {
    for (const field of section.fields) {
      if (field.required && !isFieldFilled(state[field.id])) {
        unfilled.push(field);
      }
    }
  }
  return unfilled;
}

/**
 * Get a Set of all valid field IDs (for whitelist validation in message route).
 */
export function getAllFieldIds(schema: FormSectionDefinition[]): Set<string> {
  const ids = new Set<string>();
  for (const section of schema) {
    for (const field of section.fields) {
      ids.add(field.id);
    }
  }
  return ids;
}

/**
 * Build a formatted string for LLM prompt injection.
 * Shows each field with its type, options, current value, and unfilled summary.
 */
export function buildFormStatusForPrompt(
  schema: FormSectionDefinition[],
  state: FormState
): string {
  const lines: string[] = [];
  const unfilledRequired: string[] = [];

  for (const section of schema) {
    // Skip preferences section — LLM doesn't fill those during chat
    if (section.id === "preferences") continue;

    lines.push(`\nSection: ${section.label}`);
    for (const field of section.fields) {
      const value = state[field.id];
      const filled = isFieldFilled(value);
      const requiredTag = field.required ? ", REQUIRED" : "";
      const typeTag = formatFieldTypeForPrompt(field);

      if (filled) {
        const displayValue = formatValueForPrompt(value);
        lines.push(`  - ${field.id} [${typeTag}${requiredTag}]: ${displayValue} ✓`);
      } else {
        lines.push(`  - ${field.id} [${typeTag}${requiredTag}]: (empty)`);
        if (field.required) {
          unfilledRequired.push(field.id);
        }
      }

      // Add LLM hint if present
      if (field.llmHint) {
        lines.push(`    hint: ${field.llmHint}`);
      }
    }
  }

  if (unfilledRequired.length > 0) {
    lines.push(`\nUNFILLED REQUIRED FIELDS: ${unfilledRequired.join(", ")}`);
  } else {
    lines.push("\nAll required fields are filled.");
  }

  return lines.join("\n");
}

/**
 * Validate and coerce a value from the LLM to match the field's expected type.
 * Returns the coerced value, or undefined if the value is invalid/empty.
 */
export function validateFieldValue(
  fieldId: string,
  value: unknown,
  schema: FormSectionDefinition[]
): FormFieldValue | undefined {
  const field = findField(schema, fieldId);
  if (!field) return undefined;

  // Null/undefined means no data
  if (value === null || value === undefined || value === "") return undefined;

  switch (field.type) {
    case "toggle": {
      if (typeof value === "boolean") return value;
      if (typeof value === "string") {
        const lower = value.toLowerCase().trim();
        if (["yes", "true", "y", "1"].includes(lower)) return true;
        if (["no", "false", "n", "0"].includes(lower)) return false;
      }
      return undefined;
    }

    case "dropdown": {
      if (typeof value === "string" && value.trim()) return value.trim();
      return undefined;
    }

    case "multi-select":
    case "checkboxes": {
      if (Array.isArray(value)) {
        const filtered = value.filter((v) => typeof v === "string" && v.trim());
        return filtered.length > 0 ? filtered : undefined;
      }
      // If LLM returns a single string, wrap in array
      if (typeof value === "string" && value.trim()) return [value.trim()];
      return undefined;
    }

    case "text":
    case "textarea": {
      if (typeof value === "string" && value.trim()) return value.trim();
      return undefined;
    }

    default:
      return undefined;
  }
}

// --- Private Helpers ---

export function isFieldFilled(value: FormFieldValue): boolean {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim() !== "";
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "boolean") return true; // false is a valid filled value
  return false;
}

function findField(
  schema: FormSectionDefinition[],
  fieldId: string
): FormFieldDefinition | undefined {
  for (const section of schema) {
    for (const field of section.fields) {
      if (field.id === fieldId) return field;
    }
  }
  return undefined;
}

function formatFieldTypeForPrompt(field: FormFieldDefinition): string {
  if (field.options && (field.type === "dropdown" || field.type === "multi-select" || field.type === "checkboxes")) {
    const optionValues = field.options.map((o) => o.value).join(", ");
    return `${field.type}: ${optionValues}`;
  }
  return field.type;
}

function formatValueForPrompt(value: FormFieldValue): string {
  if (value === null || value === undefined) return "(empty)";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return JSON.stringify(value);
  return String(value);
}

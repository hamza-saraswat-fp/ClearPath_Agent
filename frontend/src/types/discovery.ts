// ============================================================
// ClearPath Discovery Chat — Core TypeScript Types
// ============================================================

// --- Coverage Areas (behind-the-scenes tracking) ---

export type CoverageAreaId =
  | "intake"
  | "en_route"
  | "arrival"
  | "during_work"
  | "completion"
  | "edge_cases";

export type CoverageStatus = "uncovered" | "partial" | "covered";

export interface CoverageDataPoints {
  intake?: {
    job_source?: string;
    job_creator?: string;
    info_captured_at_intake?: string;
    scheduling_model?: string;
  };
  en_route?: {
    customer_notification?: string;
    clock_in_timing?: string;
    travel_tracking?: string;
  };
  arrival?: {
    first_action?: string;
    pre_work_requirements?: string[];
  };
  during_work?: {
    work_description?: string;
    forms_checklists?: string;
    photo_requirements?: string;
    parts_materials?: string;
    time_tracking?: string;
    estimates_or_invoices_onsite?: string;
    info_needed_on_screen?: string[];
  };
  completion?: {
    completion_requirements?: string[];
    signature?: string;
    handoff_to_office?: string;
    invoice_process?: string;
    payment_collection?: string;
  };
  edge_cases?: {
    common_mistakes?: string;
    management_frustrations?: string;
    parts_not_available?: string;
    customer_absent?: string;
    multi_day_jobs?: string;
    multiple_job_types?: string;
  };
  additional_context?: {
    compliance_requirements?: string;
    asset_equipment_tracking?: string;
    special_processes?: string;
    additional_details?: string;
  };
}

export interface CoverageState {
  areas: Record<CoverageAreaId, CoverageStatus>;
  dataPoints: CoverageDataPoints;
  inferred: Record<string, string>;
  specificGaps: string[];
  customerLanguage: Record<string, string>;
}

// --- Conversation ---

export interface ConversationMessage {
  id: string;
  role: "assistant" | "user";
  content: string;
  timestamp: string;
  quickSelectOptions?: QuickSelectOption[];
}

export interface QuickSelectOption {
  label: string;
  value: string;
}

// --- Session ---

export type SessionPhase = "business_context" | "discovery" | "preferences" | "confirmation";

export interface BusinessContext {
  companyName: string;
  industry: string;
  companySize: string;
  jobType: string;
}

export interface Preferences {
  restrictionPreference: "guided" | "flexible";
  customerTextOnTheWay: boolean | null;
  existingForms: string[];
}

export interface DiscoverySession {
  id: string;
  phase: SessionPhase;
  businessContext: BusinessContext;
  coverage: CoverageState;
  messages: ConversationMessage[];
  preferences?: Preferences;
  report?: DiscoveryReport;
  createdAt: string;
  updatedAt: string;
}

// --- AI Discovery Response (single Sonnet call: extraction + follow-up) ---

export interface DiscoveryLLMResponse {
  extraction: {
    data_points: Partial<CoverageDataPoints>;
    inferred: Record<string, string>;
    specific_gaps: string[];
    customer_language: Record<string, string>;
  };
  follow_up: string;
  model_thinks_complete: boolean;
  suggested_quick_selects?: QuickSelectOption[];
}

// --- API Request/Response Types ---

export interface StartSessionRequest {
  businessContext: BusinessContext;
}

export interface StartSessionResponse {
  sessionId: string;
  firstMessage: ConversationMessage;
}

export interface SendMessageRequest {
  sessionId: string;
  message: string;
  quickSelectValue?: string;
}

export interface SendMessageResponse {
  coverageUpdate: CoverageState;
  assistantMessage: ConversationMessage;
  isComplete: boolean;
}

export interface AssembleReportRequest {
  sessionId: string;
  preferences: Preferences;
}

export interface AssembleReportResponse {
  report: DiscoveryReport;
  summary: string;
}

export interface SubmitReportRequest {
  sessionId: string;
  report: DiscoveryReport;
}

export interface SubmitReportResponse {
  success: boolean;
  webhookResponse?: unknown;
}

// --- Discovery Report (the final output sent to n8n) ---

export interface DiscoveryReportStatus {
  name: string;
  order: number;
  instructions: string;
  actions: string[];
  widgets: string[];
  edge_cases: string[];
  transitions_to: string[];
  notes: string;
}

export interface DiscoveryReport {
  workflow_name: string;
  job_types_covered: string[];
  problems_to_solve: string[];
  restriction_preference: string;
  statuses: DiscoveryReportStatus[];
  existing_templates_mentioned: string[];
  forms_mentioned: string[];
  confidence_notes: {
    high_confidence: string[];
    medium_confidence: string[];
    gaps_or_unknowns: string[];
  };
  customer_language: Record<string, string>;
}

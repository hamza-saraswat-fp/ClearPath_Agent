// ============================================================
// ClearPath Discovery Chat — Core TypeScript Types
// ============================================================

import type { FormFieldValue, FormState } from "@/lib/form-schema";

// --- Form-Driven State (replaces CoverageState) ---

export interface FormDrivenState {
  formState: FormState;
  inferred: Record<string, string>;
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

export type SessionPhase = "business_context" | "choice" | "discovery" | "form_review" | "confirmation";

export interface BusinessContext {
  companyName: string;
  industry: string;
  companySize: string;
  jobType: string;
}

export interface DiscoverySession {
  id: string;
  phase: SessionPhase;
  businessContext: BusinessContext;
  coverage: FormDrivenState;
  messages: ConversationMessage[];
  report?: DiscoveryReport;
  createdAt: string;
  updatedAt: string;
}

// --- AI Discovery Response (single Sonnet call: extraction + follow-up) ---

export interface DiscoveryLLMResponse {
  extraction: {
    fields: Record<string, FormFieldValue>;
    inferred: Record<string, string>;
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
  formStateUpdate: FormDrivenState;
  assistantMessage: ConversationMessage;
  isComplete: boolean;
}

export interface AssembleReportRequest {
  sessionId: string;
  formState: FormState;
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
  can_tech_exit_focus_view: boolean;
  can_tech_change_status: boolean;
  spanish_speaking_techs: boolean;
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

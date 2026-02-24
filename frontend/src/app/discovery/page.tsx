"use client";

import { useReducer, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import type {
  ConversationMessage,
  SessionPhase,
  BusinessContext,
  FormDrivenState,
  DiscoveryReport,
} from "@/types/discovery";
import { FORM_SCHEMA, initializeFormState } from "@/lib/form-schema";
import type { FormState } from "@/lib/form-schema";

import { ChatInterface } from "@/components/discovery/ChatInterface";
import { FormReview } from "@/components/phases/FormReview";
import { ChoiceMenu } from "@/components/phases/ChoiceMenu";
import { ConfirmationView } from "@/components/phases/ConfirmationView";
import { ClearPathLogo } from "@/components/shared/ClearPathLogo";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

interface DiscoveryState {
  sessionId: string | null;
  businessContext: BusinessContext | null;
  phase: SessionPhase;
  messages: ConversationMessage[];
  formState: FormState;
  isLoading: boolean;
  isAssembling: boolean;
  isSubmitting: boolean;
  report: DiscoveryReport | null;
  reportSummary: string;
  error: string | null;
  flowChoice: "chat" | "form_direct" | null;
}

type DiscoveryAction =
  | { type: "INIT_SESSION"; sessionId: string; businessContext: BusinessContext; firstMessage: ConversationMessage }
  | { type: "ADD_USER_MESSAGE"; message: ConversationMessage }
  | { type: "REMOVE_LAST_USER_MESSAGE" }
  | { type: "ADD_ASSISTANT_MESSAGE"; message: ConversationMessage; formStateUpdate: FormDrivenState; isComplete: boolean }
  | { type: "SET_LOADING"; loading: boolean }
  | { type: "SET_PHASE"; phase: SessionPhase }
  | { type: "SET_ASSEMBLING"; assembling: boolean }
  | { type: "SET_SUBMITTING"; submitting: boolean }
  | { type: "SET_REPORT"; report: DiscoveryReport; summary: string }
  | { type: "SET_FLOW_CHOICE"; choice: "chat" | "form_direct" }
  | { type: "SET_ERROR"; error: string | null };

const initialState: DiscoveryState = {
  sessionId: null,
  businessContext: null,
  phase: "discovery",
  messages: [],
  formState: initializeFormState(FORM_SCHEMA),
  isLoading: false,
  isAssembling: false,
  isSubmitting: false,
  report: null,
  reportSummary: "",
  error: null,
  flowChoice: null,
};

function discoveryReducer(
  state: DiscoveryState,
  action: DiscoveryAction
): DiscoveryState {
  switch (action.type) {
    case "INIT_SESSION":
      return {
        ...state,
        sessionId: action.sessionId,
        businessContext: action.businessContext,
        messages: [action.firstMessage],
        phase: "choice",
        flowChoice: null,
      };
    case "ADD_USER_MESSAGE":
      return {
        ...state,
        messages: [...state.messages, action.message],
      };
    case "REMOVE_LAST_USER_MESSAGE": {
      const idx = state.messages.findLastIndex((m) => m.role === "user");
      if (idx === -1) return state;
      return {
        ...state,
        messages: [...state.messages.slice(0, idx), ...state.messages.slice(idx + 1)],
      };
    }
    case "ADD_ASSISTANT_MESSAGE":
      return {
        ...state,
        messages: [...state.messages, action.message],
        formState: { ...state.formState, ...action.formStateUpdate.formState },
        phase: action.isComplete ? "form_review" : state.phase,
        isLoading: false,
      };
    case "SET_FLOW_CHOICE":
      return {
        ...state,
        flowChoice: action.choice,
        phase: action.choice === "chat" ? "discovery" : "form_review",
      };
    case "SET_LOADING":
      return { ...state, isLoading: action.loading };
    case "SET_PHASE":
      return { ...state, phase: action.phase };
    case "SET_ASSEMBLING":
      return { ...state, isAssembling: action.assembling };
    case "SET_SUBMITTING":
      return { ...state, isSubmitting: action.submitting };
    case "SET_REPORT":
      return {
        ...state,
        report: action.report,
        reportSummary: action.summary,
        phase: "confirmation",
        isAssembling: false,
      };
    case "SET_ERROR":
      return { ...state, error: action.error, isLoading: false, isAssembling: false, isSubmitting: false };
    default:
      return state;
  }
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DiscoveryPage() {
  const router = useRouter();
  const [state, dispatch] = useReducer(discoveryReducer, initialState);

  // Load session from sessionStorage
  useEffect(() => {
    const stored = sessionStorage.getItem("clearpath_session");
    if (!stored) {
      router.push("/");
      return;
    }
    try {
      const data = JSON.parse(stored);
      dispatch({
        type: "INIT_SESSION",
        sessionId: data.sessionId,
        businessContext: data.businessContext,
        firstMessage: data.firstMessage,
      });
    } catch {
      router.push("/");
    }
  }, [router]);

  // Send message
  const handleSendMessage = useCallback(
    async (message: string) => {
      if (!state.sessionId || state.isLoading) return;

      const userMsg: ConversationMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: message,
        timestamp: new Date().toISOString(),
      };

      dispatch({ type: "ADD_USER_MESSAGE", message: userMsg });
      dispatch({ type: "SET_LOADING", loading: true });

      try {
        const res = await fetch("/api/discovery/message", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sessionId: state.sessionId,
            message,
          }),
        });

        if (!res.ok) throw new Error("Failed to send message");

        const data = await res.json();
        dispatch({
          type: "ADD_ASSISTANT_MESSAGE",
          message: data.assistantMessage,
          formStateUpdate: data.formStateUpdate,
          isComplete: data.isComplete,
        });
      } catch (err) {
        console.error("Message error:", err);
        dispatch({ type: "REMOVE_LAST_USER_MESSAGE" });
        dispatch({ type: "SET_ERROR", error: "Failed to send message. Please try again." });
      }
    },
    [state.sessionId, state.isLoading]
  );

  // Quick select
  const handleQuickSelect = useCallback(
    (value: string) => {
      handleSendMessage(value);
    },
    [handleSendMessage]
  );

  // Form review submit
  const handleFormReviewSubmit = useCallback(
    async (formState: FormState) => {
      if (!state.sessionId) return;
      dispatch({ type: "SET_ASSEMBLING", assembling: true });

      try {
        const res = await fetch("/api/discovery/assemble", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sessionId: state.sessionId,
            formState,
          }),
        });

        if (!res.ok) throw new Error("Failed to assemble report");

        const data = await res.json();
        dispatch({
          type: "SET_REPORT",
          report: data.report,
          summary: data.summary,
        });
      } catch (err) {
        console.error("Assembly error:", err);
        dispatch({ type: "SET_ASSEMBLING", assembling: false });
        dispatch({ type: "SET_ERROR", error: "Failed to generate report. Please try again." });
      }
    },
    [state.sessionId]
  );

  // Confirm and submit
  const handleConfirm = useCallback(async () => {
    if (!state.sessionId || !state.report) return;
    dispatch({ type: "SET_SUBMITTING", submitting: true });

    try {
      const res = await fetch("/api/discovery/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sessionId: state.sessionId,
          report: state.report,
        }),
      });

      if (!res.ok) throw new Error("Failed to submit report");

      // Clear session and redirect to success or home
      sessionStorage.removeItem("clearpath_session");
      router.push("/?submitted=true");
    } catch (err) {
      console.error("Submit error:", err);
      dispatch({ type: "SET_SUBMITTING", submitting: false });
      dispatch({ type: "SET_ERROR", error: "Failed to submit. Please try again." });
    }
  }, [state.sessionId, state.report, router]);

  // Edit — go back to chat
  const handleEdit = useCallback(() => {
    dispatch({ type: "SET_PHASE", phase: state.flowChoice === "form_direct" ? "form_review" : "discovery" });
  }, [state.flowChoice]);

  // Guard: no session loaded yet
  if (!state.sessionId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <ClearPathLogo size={48} />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-white">
      {/* Header */}
      <header className="shrink-0 border-b border-border-light bg-white">
        <div className="flex items-center justify-between px-6 py-2.5">
          <div className="flex items-center gap-3">
            <ClearPathLogo size={32} />
            <span className="text-sm font-semibold text-foreground tracking-tight">
              ClearPath
            </span>
          </div>
          {state.businessContext && (
            <div className="text-xs text-muted">
              {state.businessContext.companyName} &middot;{" "}
              {state.businessContext.jobType}
            </div>
          )}
        </div>
      </header>

      {/* Error toast */}
      <AnimatePresence>
        {state.error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mx-auto mt-3 px-4 py-2 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg max-w-md text-center"
          >
            {state.error}
            <button
              onClick={() => dispatch({ type: "SET_ERROR", error: null })}
              className="ml-3 text-red-500 hover:text-red-700 font-medium"
            >
              Dismiss
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main content — phase-dependent */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <AnimatePresence mode="wait">
          {state.phase === "choice" && state.businessContext && (
            <motion.div
              key="choice"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="flex-1 flex items-center justify-center overflow-hidden"
            >
              <ChoiceMenu
                businessContext={state.businessContext}
                onChoice={(choice) => dispatch({ type: "SET_FLOW_CHOICE", choice })}
              />
            </motion.div>
          )}

          {state.phase === "discovery" && (
            <motion.div
              key="discovery"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.25 }}
              className="flex-1 flex flex-col overflow-hidden"
            >
              <ChatInterface
                messages={state.messages}
                onSendMessage={handleSendMessage}
                onQuickSelect={handleQuickSelect}
                isLoading={state.isLoading}
              />
            </motion.div>
          )}

          {state.phase === "form_review" && (
            <motion.div
              key="form_review"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
              className="flex-1 overflow-y-auto"
            >
              <FormReview
                formState={state.formState}
                onSubmit={handleFormReviewSubmit}
                isSubmitting={state.isAssembling}
                isFormDirect={state.flowChoice === "form_direct"}
                businessContext={state.businessContext}
              />
            </motion.div>
          )}

          {state.phase === "confirmation" && state.report && (
            <motion.div
              key="confirmation"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
              className="flex-1 overflow-y-auto"
            >
              <ConfirmationView
                report={state.report}
                summary={state.reportSummary}
                onConfirm={handleConfirm}
                onEdit={handleEdit}
                isSubmitting={state.isSubmitting}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}

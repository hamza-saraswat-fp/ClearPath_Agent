import { NextResponse } from "next/server";
import { chatCompletion, MODELS } from "@/lib/openrouter";
import { getSession, updateSessionAfterMessage } from "@/lib/supabase";
import { buildDiscoveryPrompt, formatConversationHistory } from "@/lib/prompts";
import { FORM_SCHEMA, getUnfilledRequiredFields, validateFieldValue, getAllFieldIds } from "@/lib/form-schema";
import logger from "@/lib/logger";
import type {
  SendMessageRequest,
  SendMessageResponse,
  ConversationMessage,
  DiscoveryLLMResponse,
  FormDrivenState,
} from "@/types/discovery";
import type { FormState, FormFieldValue } from "@/lib/form-schema";

/**
 * Runtime validation for the LLM response shape.
 */
function isValidDiscoveryResponse(raw: unknown): raw is DiscoveryLLMResponse {
  if (typeof raw !== "object" || raw === null) return false;
  const obj = raw as Record<string, unknown>;
  if (typeof obj.follow_up !== "string") return false;
  if (typeof obj.model_thinks_complete !== "boolean") return false;
  if (typeof obj.extraction !== "object" || obj.extraction === null) return false;
  const ext = obj.extraction as Record<string, unknown>;
  if (typeof ext.fields !== "object" || ext.fields === null) return false;
  return true;
}

/**
 * Parse the LLM response with 3-tier fallback.
 */
function parseDiscoveryResponse(text: string, currentFormState: FormState): DiscoveryLLMResponse {
  // Tier 1: Direct JSON parse
  try {
    const parsed = JSON.parse(text);
    if (isValidDiscoveryResponse(parsed)) return parsed;
  } catch {
    // fall through
  }

  // Tier 2: Extract JSON from markdown wrapping
  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (jsonMatch) {
    try {
      const parsed = JSON.parse(jsonMatch[0]);
      if (isValidDiscoveryResponse(parsed)) return parsed;
    } catch {
      // fall through
    }
  }

  // Tier 3: Form-aware fallback — no LLM data, use form state to guide next question
  // Never signals completion — only the LLM (via valid JSON) can mark a session complete
  logger.warn("Discovery LLM response parsing failed, using form-aware fallback");

  const emptyExtraction = {
    fields: {} as Record<string, FormFieldValue>,
    inferred: {},
    customer_language: {},
  };

  const unfilledRequired = getUnfilledRequiredFields(FORM_SCHEMA, currentFormState);

  if (unfilledRequired.length === 0) {
    // All required fields have data — ask a general follow-up, let next LLM turn handle completion
    return {
      extraction: emptyExtraction,
      follow_up: "Is there anything else about your workflow I should know — any edge cases or things that don't go as planned?",
      model_thinks_complete: false,
      suggested_quick_selects: [],
    };
  }

  const fieldLabel = unfilledRequired[0].label;
  return {
    extraction: emptyExtraction,
    follow_up: `${fieldLabel}`,
    model_thinks_complete: false,
    suggested_quick_selects: [],
  };
}

export async function POST(request: Request) {
  try {
    const body: SendMessageRequest = await request.json();
    const { sessionId, message, quickSelectValue } = body;

    if (!sessionId || !message) {
      return NextResponse.json(
        { error: "Missing sessionId or message" },
        { status: 400 }
      );
    }

    // Get session from Supabase
    const session = await getSession(sessionId);
    if (!session) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 });
    }

    const userContent = quickSelectValue || message;

    // Build the user message object
    const userMessage: ConversationMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: userContent,
      timestamp: new Date().toISOString(),
    };

    // --- Single Discovery Call (extraction + follow-up) ---

    const allMessages = [...session.messages, userMessage];
    const userTurnCount = allMessages.filter((m) => m.role === "user").length;

    logger.info({ sessionId, userTurnCount }, "Processing discovery message");

    // --- Scripted Q2: fires on the first user reply, but still extracts data ---
    const priorUserCount = session.messages.filter((m) => m.role === "user").length;
    if (userTurnCount === 1 && priorUserCount === 0) {
      // Run extraction on the first message (often the most data-rich)
      const extractionHistory = formatConversationHistory(
        allMessages.map((m) => ({ role: m.role, content: m.content }))
      );
      const extractionPrompt = buildDiscoveryPrompt(
        session.businessContext,
        extractionHistory,
        userTurnCount,
        session.coverage.formState
      );
      let extractedCoverage = session.coverage;
      try {
        const extractionText = await chatCompletion(MODELS.discovery, extractionPrompt, 2048);
        const extractionResponse = parseDiscoveryResponse(extractionText, session.coverage.formState);
        const extractedFormState: FormState = { ...session.coverage.formState };
        const validIds = getAllFieldIds(FORM_SCHEMA);
        for (const [fieldId, value] of Object.entries(extractionResponse.extraction.fields)) {
          if (!validIds.has(fieldId)) continue;
          const validated = validateFieldValue(fieldId, value, FORM_SCHEMA);
          if (validated !== undefined) extractedFormState[fieldId] = validated;
        }
        extractedCoverage = {
          formState: extractedFormState,
          inferred: { ...session.coverage.inferred, ...extractionResponse.extraction.inferred },
          customerLanguage: { ...session.coverage.customerLanguage, ...extractionResponse.extraction.customer_language },
        };
        logger.debug({ sessionId, fields: extractionResponse.extraction.fields }, "Q2 extraction result");
      } catch (err) {
        logger.warn({ sessionId, err }, "Q2 extraction failed, continuing with scripted response");
      }

      const q2Message: ConversationMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "Now walk me through the details — what does your tech actually do at each stage? Think about the paperwork, photos, customer interactions, and how the job gets closed out.",
        timestamp: new Date().toISOString(),
      };
      await updateSessionAfterMessage(sessionId, [userMessage, q2Message], extractedCoverage);
      const q2Response: SendMessageResponse = {
        formStateUpdate: extractedCoverage,
        assistantMessage: q2Message,
        isComplete: false,
      };
      return NextResponse.json(q2Response);
    }

    const conversationHistory = formatConversationHistory(
      allMessages.map((m) => ({ role: m.role, content: m.content }))
    );

    const discoveryPrompt = buildDiscoveryPrompt(
      session.businessContext,
      conversationHistory,
      userTurnCount,
      session.coverage.formState
    );

    const discoveryText = await chatCompletion(
      MODELS.discovery,
      discoveryPrompt,
      2048
    );

    const response = parseDiscoveryResponse(discoveryText, session.coverage.formState);

    logger.debug({ sessionId, fields: response.extraction.fields }, "LLM extraction result");

    // --- Merge extracted fields into form state ---

    const updatedFormState: FormState = { ...session.coverage.formState };
    const validFieldIds = getAllFieldIds(FORM_SCHEMA);

    for (const [fieldId, value] of Object.entries(response.extraction.fields)) {
      if (!validFieldIds.has(fieldId)) {
        logger.warn({ sessionId, fieldId }, "Unknown field ID from LLM, skipping");
        continue;
      }
      const validated = validateFieldValue(fieldId, value, FORM_SCHEMA);
      if (validated !== undefined) {
        updatedFormState[fieldId] = validated;
      }
    }

    // Merge inferred and customer language
    const updatedInferred = {
      ...session.coverage.inferred,
      ...response.extraction.inferred,
    };
    const updatedCustomerLanguage = {
      ...session.coverage.customerLanguage,
      ...response.extraction.customer_language,
    };

    const updatedCoverage: FormDrivenState = {
      formState: updatedFormState,
      inferred: updatedInferred,
      customerLanguage: updatedCustomerLanguage,
    };

    // --- Completion check (LLM-driven, backend coverage is advisory only) ---

    const modelComplete = response.model_thinks_complete && userTurnCount >= 3;
    const complete = modelComplete;

    logger.info({ sessionId, modelComplete, userTurnCount }, "Completion check");

    // --- Build assistant message ---

    let assistantMessage: ConversationMessage;

    if (complete) {
      assistantMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content:
          "I think I have a good picture of your workflow now. Let me put together a summary for you — just a couple more quick questions about your preferences and we'll be all set.",
        timestamp: new Date().toISOString(),
      };
    } else {
      // Use LLM-suggested chips if available, otherwise empty
      const quickSelectOptions = response.suggested_quick_selects?.length
        ? response.suggested_quick_selects
        : [];
      assistantMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.follow_up,
        timestamp: new Date().toISOString(),
        quickSelectOptions: quickSelectOptions.length > 0 ? quickSelectOptions : undefined,
      };
    }

    // --- Persist messages + coverage to Supabase ---

    await updateSessionAfterMessage(
      sessionId,
      [userMessage, assistantMessage],
      updatedCoverage
    );

    const apiResponse: SendMessageResponse = {
      formStateUpdate: updatedCoverage,
      assistantMessage,
      isComplete: complete,
    };

    return NextResponse.json(apiResponse);
  } catch (error) {
    logger.error({ err: error }, "Failed to process message");
    return NextResponse.json(
      { error: "Failed to process message" },
      { status: 500 }
    );
  }
}

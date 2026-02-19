import { NextResponse } from "next/server";
import { chatCompletion, MODELS } from "@/lib/openrouter";
import { getSession, updateSessionAfterMessage } from "@/lib/supabase";
import { buildDiscoveryPrompt, formatConversationHistory } from "@/lib/prompts";
import { getAreaCoverageStatus, isDiscoveryComplete, getQuickSelectsForNextArea, COVERAGE_AREAS } from "@/lib/coverage-areas";
import type {
  SendMessageRequest,
  SendMessageResponse,
  ConversationMessage,
  DiscoveryLLMResponse,
  CoverageState,
  CoverageAreaId,
  CoverageDataPoints,
} from "@/types/discovery";

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
  if (typeof ext.inferred !== "object" || ext.inferred === null) return false;
  return true;
}

/**
 * Parse the LLM response with 3-tier fallback.
 */
function parseDiscoveryResponse(text: string): DiscoveryLLMResponse {
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

  // Tier 3: Use raw text as follow-up, empty extraction
  console.warn("Discovery LLM response parsing failed, using fallback");
  return {
    extraction: {
      data_points: {},
      inferred: {},
      specific_gaps: [],
      customer_language: {},
    },
    follow_up: text.length > 0 && text.length < 1000
      ? text
      : "Tell me more about your workflow.",
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
    const conversationHistory = formatConversationHistory(
      allMessages.map((m) => ({ role: m.role, content: m.content }))
    );

    const discoveryPrompt = buildDiscoveryPrompt(
      session.businessContext,
      conversationHistory,
      userTurnCount
    );

    const discoveryText = await chatCompletion(
      MODELS.discovery,
      discoveryPrompt,
      2048
    );

    const response = parseDiscoveryResponse(discoveryText);

    // --- Merge extracted data points into coverage state ---

    const updatedDataPoints: CoverageDataPoints = { ...session.coverage.dataPoints };

    for (const [areaId, points] of Object.entries(response.extraction.data_points)) {
      const key = areaId as CoverageAreaId | "additional_context";
      updatedDataPoints[key] = {
        ...(updatedDataPoints[key] || {}),
        ...points,
      } as CoverageDataPoints[typeof key];
    }

    // Recalculate area statuses (only tracked areas, not additional_context)
    const updatedAreas = { ...session.coverage.areas };
    for (const area of COVERAGE_AREAS) {
      updatedAreas[area.id] = getAreaCoverageStatus(area.id, updatedDataPoints);
    }

    // Merge inferred, specific gaps, and customer language
    const updatedInferred = {
      ...session.coverage.inferred,
      ...response.extraction.inferred,
    };
    const updatedGaps = [
      ...new Set([...session.coverage.specificGaps, ...response.extraction.specific_gaps]),
    ];
    const updatedCustomerLanguage = {
      ...session.coverage.customerLanguage,
      ...response.extraction.customer_language,
    };

    const updatedCoverage: CoverageState = {
      areas: updatedAreas,
      dataPoints: updatedDataPoints,
      inferred: updatedInferred,
      specificGaps: updatedGaps,
      customerLanguage: updatedCustomerLanguage,
    };

    // --- Completion check ---

    const backendComplete = isDiscoveryComplete(updatedDataPoints);
    const modelComplete = response.model_thinks_complete && userTurnCount >= 3;
    const complete = backendComplete || modelComplete;

    if (modelComplete && !backendComplete) {
      console.warn("Model marked complete but backend disagrees", {
        sessionId,
        coverageStatuses: updatedAreas,
        turnCount: userTurnCount,
      });
    }

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
      // Use LLM-suggested chips, fall back to coverage-based chips
      const quickSelectOptions = response.suggested_quick_selects?.length
        ? response.suggested_quick_selects
        : getQuickSelectsForNextArea(updatedDataPoints);
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
      coverageUpdate: updatedCoverage,
      assistantMessage,
      isComplete: complete,
    };

    return NextResponse.json(apiResponse);
  } catch (error) {
    console.error("Failed to process message:", error);
    return NextResponse.json(
      { error: "Failed to process message" },
      { status: 500 }
    );
  }
}

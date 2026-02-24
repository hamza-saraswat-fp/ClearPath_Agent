import { NextResponse } from "next/server";
import { chatCompletion, MODELS } from "@/lib/openrouter";
import { getSession, saveFormState, saveReport } from "@/lib/supabase";
import { buildReportAssemblyPrompt, formatConversationHistory } from "@/lib/prompts";
import logger from "@/lib/logger";
import type { AssembleReportRequest, AssembleReportResponse, DiscoveryReport } from "@/types/discovery";

export async function POST(request: Request) {
  try {
    const body: AssembleReportRequest = await request.json();
    const { sessionId, formState } = body;

    if (!sessionId || !formState) {
      return NextResponse.json(
        { error: "Missing sessionId or formState" },
        { status: 400 }
      );
    }

    // Get session from Supabase
    const session = await getSession(sessionId);
    if (!session) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 });
    }

    logger.info({ sessionId }, "Starting report assembly");

    // Extract narrative context from form-direct path (not schema fields)
    const narrativeStages = (formState._narrative_stages as string) || "";
    const narrativeDetails = (formState._narrative_details as string) || "";
    delete formState._narrative_stages;
    delete formState._narrative_details;

    // Save form state (user may have edited fields in the review form)
    await saveFormState(sessionId, formState);

    // Build transcript — use narrative fields if present, otherwise session messages
    let fullTranscript: string;
    if (narrativeStages || narrativeDetails) {
      const parts: string[] = [];
      if (narrativeStages) parts.push(`Customer: ${narrativeStages}`);
      if (narrativeDetails) parts.push(`Customer: ${narrativeDetails}`);
      fullTranscript = parts.join("\n\n");
    } else {
      fullTranscript = formatConversationHistory(
        session.messages.map((m) => ({ role: m.role, content: m.content }))
      );
    }

    // Build assembly prompt — use formState from request (user-edited), inferred from session
    const assemblyPrompt = buildReportAssemblyPrompt(
      session.businessContext,
      fullTranscript,
      formState,
      session.coverage.inferred || {}
    );

    // Call Claude Sonnet via OpenRouter to assemble the report
    const assemblyText = await chatCompletion(
      MODELS.assembly,
      assemblyPrompt,
      4096
    );

    // Parse the report JSON
    let report: DiscoveryReport;
    try {
      report = JSON.parse(assemblyText);
    } catch {
      // Try to extract JSON from the response if it has surrounding text
      const jsonMatch = assemblyText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        try {
          report = JSON.parse(jsonMatch[0]);
        } catch {
          return NextResponse.json(
            { error: "Failed to parse discovery report from AI response" },
            { status: 500 }
          );
        }
      } else {
        return NextResponse.json(
          { error: "Failed to parse discovery report from AI response" },
          { status: 500 }
        );
      }
    }

    // Validate required fields
    if (!report.workflow_name || !Array.isArray(report.statuses) || report.statuses.length === 0) {
      return NextResponse.json(
        { error: "Invalid report structure: missing workflow_name or statuses" },
        { status: 500 }
      );
    }

    logger.info({ sessionId, statusCount: report.statuses.length }, "Report assembled");

    // Save report to Supabase
    await saveReport(sessionId, report);

    // Build a human-readable summary for Phase 4
    const summary = buildSummary(report);

    const response: AssembleReportResponse = {
      report,
      summary,
    };

    return NextResponse.json(response);
  } catch (error) {
    logger.error({ err: error }, "Failed to assemble report");
    return NextResponse.json(
      { error: "Failed to assemble discovery report" },
      { status: 500 }
    );
  }
}

function buildSummary(report: DiscoveryReport): string {
  const lines: string[] = [];

  lines.push(report.workflow_name);
  lines.push(`Job types: ${report.job_types_covered?.join(", ") ?? "—"}`);
  lines.push(`Tech can exit Focus View: ${report.can_tech_exit_focus_view ? "Yes" : "No"}`);
  lines.push(`Tech can change status: ${report.can_tech_change_status ? "Yes" : "No"}`);
  lines.push("");
  lines.push("Workflow Statuses:");

  for (const status of report.statuses) {
    lines.push(`${status.order}. ${status.name}`);
    if (status.actions?.length > 0) {
      lines.push(`   Actions: ${status.actions.join(", ")}`);
    }
    if (status.transitions_to?.length > 0) {
      lines.push(`   → ${status.transitions_to.join(", ")}`);
    }
  }

  if (report.confidence_notes?.gaps_or_unknowns?.length > 0) {
    lines.push("");
    lines.push("Gaps/Unknowns:");
    for (const gap of report.confidence_notes.gaps_or_unknowns) {
      lines.push(`- ${gap}`);
    }
  }

  return lines.join("\n");
}

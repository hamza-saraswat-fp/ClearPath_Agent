import { NextResponse } from "next/server";
import { chatCompletion, MODELS } from "@/lib/openrouter";
import { getSession, savePreferences, saveReport } from "@/lib/supabase";
import { buildReportAssemblyPrompt, formatConversationHistory } from "@/lib/prompts";
import type { AssembleReportRequest, AssembleReportResponse, DiscoveryReport } from "@/types/discovery";

export async function POST(request: Request) {
  try {
    const body: AssembleReportRequest = await request.json();
    const { sessionId, preferences } = body;

    if (!sessionId || !preferences) {
      return NextResponse.json(
        { error: "Missing sessionId or preferences" },
        { status: 400 }
      );
    }

    // Get session from Supabase
    const session = await getSession(sessionId);
    if (!session) {
      return NextResponse.json({ error: "Session not found" }, { status: 404 });
    }

    // Save preferences
    await savePreferences(sessionId, preferences);

    // Build the full transcript
    const fullTranscript = formatConversationHistory(
      session.messages.map((m) => ({ role: m.role, content: m.content }))
    );

    // Build assembly prompt
    const assemblyPrompt = buildReportAssemblyPrompt(
      session.businessContext,
      fullTranscript,
      session.coverage.dataPoints,
      session.coverage.inferred || {},
      preferences
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
        report = JSON.parse(jsonMatch[0]);
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
    console.error("Failed to assemble report:", error);
    return NextResponse.json(
      { error: "Failed to assemble discovery report" },
      { status: 500 }
    );
  }
}

function buildSummary(report: DiscoveryReport): string {
  const lines: string[] = [];

  lines.push(`**${report.workflow_name}**`);
  lines.push(`Job types: ${report.job_types_covered.join(", ")}`);
  lines.push(`Restriction: ${report.restriction_preference}`);
  lines.push("");
  lines.push("**Workflow Statuses:**");

  for (const status of report.statuses) {
    lines.push(`${status.order}. **${status.name}**`);
    if (status.actions.length > 0) {
      lines.push(`   Actions: ${status.actions.join(", ")}`);
    }
    if (status.transitions_to.length > 0) {
      lines.push(`   → ${status.transitions_to.join(", ")}`);
    }
  }

  if (report.confidence_notes.gaps_or_unknowns.length > 0) {
    lines.push("");
    lines.push("**Gaps/Unknowns:**");
    for (const gap of report.confidence_notes.gaps_or_unknowns) {
      lines.push(`- ${gap}`);
    }
  }

  return lines.join("\n");
}

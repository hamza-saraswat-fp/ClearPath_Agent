import { NextResponse } from "next/server";
import logger from "@/lib/logger";
import type { SubmitReportRequest, SubmitReportResponse } from "@/types/discovery";

export async function POST(request: Request) {
  try {
    const body: SubmitReportRequest = await request.json();
    const { sessionId, report } = body;

    if (!sessionId || !report) {
      return NextResponse.json(
        { error: "Missing sessionId or report" },
        { status: 400 }
      );
    }

    const webhookUrl = process.env.N8N_WEBHOOK_URL;
    if (!webhookUrl) {
      return NextResponse.json(
        { error: "N8N_WEBHOOK_URL not configured" },
        { status: 500 }
      );
    }

    logger.info({ sessionId }, "Submitting report to webhook");

    // POST the discovery report to the n8n webhook
    const webhookResponse = await fetch(webhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sessionId,
        report,
      }),
    });

    if (!webhookResponse.ok) {
      const errorText = await webhookResponse.text();
      logger.error({ sessionId, status: webhookResponse.status, errorText }, "Webhook error");
      return NextResponse.json(
        { error: `Webhook returned ${webhookResponse.status}` },
        { status: 502 }
      );
    }

    const responseText = await webhookResponse.text();
    let webhookData: unknown;
    try {
      webhookData = JSON.parse(responseText);
    } catch {
      webhookData = responseText;
    }

    logger.info({ sessionId }, "Report submitted to webhook");

    const response: SubmitReportResponse = {
      success: true,
      webhookResponse: webhookData,
    };

    return NextResponse.json(response);
  } catch (error) {
    logger.error({ err: error }, "Failed to submit report");
    return NextResponse.json(
      { error: "Failed to submit discovery report" },
      { status: 500 }
    );
  }
}

import { NextResponse } from "next/server";
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
      console.error("Webhook error:", webhookResponse.status, errorText);
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

    const response: SubmitReportResponse = {
      success: true,
      webhookResponse: webhookData,
    };

    return NextResponse.json(response);
  } catch (error) {
    console.error("Failed to submit report:", error);
    return NextResponse.json(
      { error: "Failed to submit discovery report" },
      { status: 500 }
    );
  }
}

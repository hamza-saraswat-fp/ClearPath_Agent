import { NextResponse } from "next/server";
import { createSession, updateSessionAfterMessage } from "@/lib/supabase";
import { buildOpeningMessage } from "@/lib/prompts";
import type { StartSessionRequest, StartSessionResponse, ConversationMessage } from "@/types/discovery";

export async function POST(request: Request) {
  try {
    const body: StartSessionRequest = await request.json();
    const { businessContext } = body;

    if (
      !businessContext?.companyName ||
      !businessContext?.industry ||
      !businessContext?.companySize ||
      !businessContext?.jobType
    ) {
      return NextResponse.json(
        { error: "Missing required business context fields" },
        { status: 400 }
      );
    }

    // Create session in Supabase
    const session = await createSession(businessContext);

    // Generate the opening message
    const openingText = buildOpeningMessage(businessContext);
    const firstMessage: ConversationMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: openingText,
      timestamp: new Date().toISOString(),
    };

    // Persist the opening message
    await updateSessionAfterMessage(session.id, [firstMessage], session.coverage);

    const response: StartSessionResponse = {
      sessionId: session.id,
      firstMessage,
    };

    return NextResponse.json(response);
  } catch (error) {
    console.error("Failed to start session:", error);
    return NextResponse.json(
      { error: "Failed to start discovery session" },
      { status: 500 }
    );
  }
}

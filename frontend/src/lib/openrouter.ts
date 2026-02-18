// ============================================================
// OpenRouter API Client
// OpenAI-compatible API for Claude model access
// ============================================================

const OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions";

export const MODELS = {
  /** Discovery: extraction + follow-up in one pass — Sonnet */
  discovery: "anthropic/claude-sonnet-4.5",
  /** Report assembly — Sonnet */
  assembly: "anthropic/claude-sonnet-4.5",
} as const;

interface ChatCompletionResponse {
  choices: {
    message: {
      content: string;
    };
  }[];
}

/**
 * Call OpenRouter's chat completions API.
 */
export async function chatCompletion(
  model: string,
  prompt: string,
  maxTokens: number = 1024
): Promise<string> {
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) {
    throw new Error("OPENROUTER_API_KEY is not set");
  }

  const response = await fetch(OPENROUTER_API_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://clearpath.fieldpulse.com",
      "X-Title": "ClearPath Discovery Chat",
    },
    body: JSON.stringify({
      model,
      max_tokens: maxTokens,
      messages: [{ role: "user", content: prompt }],
    }),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`OpenRouter API error (${response.status}): ${errorBody}`);
  }

  const data: ChatCompletionResponse = await response.json();
  return data.choices[0]?.message?.content || "";
}

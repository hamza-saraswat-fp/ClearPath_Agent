import { createClient } from "@supabase/supabase-js";
import type { DiscoverySession, CoverageState, ConversationMessage, BusinessContext, Preferences, DiscoveryReport } from "@/types/discovery";

// ============================================================
// Supabase Client + Session CRUD
// ============================================================

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// --- Session table schema (create in Supabase dashboard or migration):
// CREATE TABLE discovery_sessions (
//   id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
//   phase TEXT NOT NULL DEFAULT 'business_context',
//   business_context JSONB NOT NULL,
//   coverage JSONB NOT NULL DEFAULT '{"areas":{},"dataPoints":{},"specificGaps":[],"customerLanguage":{}}',
//   messages JSONB NOT NULL DEFAULT '[]',
//   preferences JSONB,
//   report JSONB,
//   created_at TIMESTAMPTZ DEFAULT NOW(),
//   updated_at TIMESTAMPTZ DEFAULT NOW()
// );

const TABLE = "discovery_sessions";

/**
 * Create a new discovery session.
 */
export async function createSession(businessContext: BusinessContext): Promise<DiscoverySession> {
  const initialCoverage: CoverageState = {
    areas: {
      intake: "uncovered",
      en_route: "uncovered",
      arrival: "uncovered",
      during_work: "uncovered",
      completion: "uncovered",
      edge_cases: "uncovered",
    },
    dataPoints: {},
    inferred: {},
    specificGaps: [],
    customerLanguage: {},
  };

  const { data, error } = await supabase
    .from(TABLE)
    .insert({
      phase: "discovery",
      business_context: businessContext,
      coverage: initialCoverage,
      messages: [],
    })
    .select()
    .single();

  if (error) throw new Error(`Failed to create session: ${error.message}`);

  return mapRowToSession(data);
}

/**
 * Get a session by ID.
 */
export async function getSession(sessionId: string): Promise<DiscoverySession | null> {
  const { data, error } = await supabase
    .from(TABLE)
    .select()
    .eq("id", sessionId)
    .single();

  if (error) return null;
  return mapRowToSession(data);
}

/**
 * Append a message and update coverage state.
 */
export async function updateSessionAfterMessage(
  sessionId: string,
  newMessages: ConversationMessage[],
  coverage: CoverageState
): Promise<void> {
  // Get current messages first
  const session = await getSession(sessionId);
  if (!session) throw new Error("Session not found");

  const allMessages = [...session.messages, ...newMessages];

  const { error } = await supabase
    .from(TABLE)
    .update({
      messages: allMessages,
      coverage,
      updated_at: new Date().toISOString(),
    })
    .eq("id", sessionId);

  if (error) throw new Error(`Failed to update session: ${error.message}`);
}

/**
 * Save preferences (Phase 3).
 */
export async function savePreferences(
  sessionId: string,
  preferences: Preferences
): Promise<void> {
  const { error } = await supabase
    .from(TABLE)
    .update({
      phase: "confirmation",
      preferences,
      updated_at: new Date().toISOString(),
    })
    .eq("id", sessionId);

  if (error) throw new Error(`Failed to save preferences: ${error.message}`);
}

/**
 * Save the assembled report (Phase 4).
 */
export async function saveReport(
  sessionId: string,
  report: DiscoveryReport
): Promise<void> {
  const { error } = await supabase
    .from(TABLE)
    .update({
      report,
      updated_at: new Date().toISOString(),
    })
    .eq("id", sessionId);

  if (error) throw new Error(`Failed to save report: ${error.message}`);
}

// --- Helpers ---

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapRowToSession(row: any): DiscoverySession {
  return {
    id: row.id,
    phase: row.phase,
    businessContext: row.business_context,
    coverage: row.coverage,
    messages: row.messages,
    preferences: row.preferences || undefined,
    report: row.report || undefined,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

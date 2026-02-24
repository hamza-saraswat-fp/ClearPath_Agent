# ClearPath Discovery Chat — System Documentation

## 1. System Overview

The Discovery Chat is a guided conversational interview that extracts a field service company's workflow and produces a structured JSON report. That report is then sent to an n8n pipeline which translates it into actual FieldPulse software configuration.

```
 React Client (Browser)                    Next.js API Routes                  External Services
 ─────────────────────                     ──────────────────                  ─────────────────
 ┌───────────────────┐   POST /start       ┌─────────────────────┐
 │ Business Context   │──────────────────→  │ /api/discovery/     │ ──→  Supabase (create session)
 │ Form               │                     │        start        │
 └────────┬──────────┘                     └─────────────────────┘
          ↓
 ┌───────────────────┐   POST /message     ┌─────────────────────┐
 │ Discovery Chat     │──────────────────→  │ /api/discovery/     │ ──→  Supabase (read/write)
 │ (N turns)          │  (per message)      │       message       │ ──→  OpenRouter / Sonnet
 └────────┬──────────┘                     └─────────────────────┘
          ↓
 ┌───────────────────┐   POST /assemble    ┌─────────────────────┐
 │ Preferences Form   │──────────────────→  │ /api/discovery/     │ ──→  Supabase (read/write)
 │                     │                     │      assemble       │ ──→  OpenRouter / Sonnet
 └────────┬──────────┘                     └─────────────────────┘
          ↓
 ┌───────────────────┐   POST /submit      ┌─────────────────────┐
 │ Confirmation &     │──────────────────→  │ /api/discovery/     │ ──→  n8n Webhook
 │ Submit             │                     │       submit        │
 └───────────────────┘                     └─────────────────────┘
```

**Four phases, in order:**

| Phase | UI Component | API Route | What happens |
|-------|-------------|-----------|-------------|
| 1. Business Context | Landing page form | `/api/discovery/start` | User enters company name, industry, size, job type. Session created in Supabase. Scripted Q1 returned. |
| 2. Discovery Chat | `ChatInterface` | `/api/discovery/message` | Multi-turn conversation. One Sonnet call per message extracts data + generates follow-up. Coverage tracked server-side. |
| 3. Preferences | `PreferencesForm` | `/api/discovery/assemble` | User picks guided/flexible, customer text preference, existing forms. Triggers assembly Sonnet call. |
| 4. Confirmation | `ConfirmationView` | `/api/discovery/submit` | User reviews assembled report. On confirm, JSON POSTed to n8n webhook. |

---

## 2. Architecture

```
 Browser                                         Next.js Server (API Routes)
 ───────                                         ──────────────────────────
 ┌─────────────────────────────┐                 ┌──────────────────────────────────────────────┐
 │  page.tsx (useReducer)      │                 │  /api/discovery/start                        │
 │  ─────────────────────      │    fetch()      │    └─ supabase.ts ──→ Supabase DB            │
 │                             │ ──────────────→ │                                              │
 │  Renders by phase:          │                 │  /api/discovery/message                      │
 │    discovery → ChatInterface│    fetch()      │    ├─ prompts.ts (build discovery prompt)    │
 │    preferences → PrefsForm  │ ──────────────→ │    ├─ openrouter.ts ──→ Sonnet 4.5           │
 │    confirmation → ConfView  │                 │    ├─ coverage-areas.ts (score 6 areas)      │
 │                             │    fetch()      │    ├─ supabase.ts ──→ Supabase DB            │
 │  State:                     │ ──────────────→ │    └─ logger.ts (Pino)                       │
 │    sessionId                │                 │                                              │
 │    messages[]               │                 │  /api/discovery/assemble                     │
 │    coverageStatuses         │    fetch()      │    ├─ prompts.ts (build assembly prompt)     │
 │    phase                    │ ──────────────→ │    ├─ openrouter.ts ──→ Sonnet 4.5           │
 │    report                   │                 │    └─ supabase.ts ──→ Supabase DB            │
 │                             │                 │                                              │
 │                             │                 │  /api/discovery/submit                       │
 │                             │                 │    └─ fetch() ──→ n8n Webhook                │
 └─────────────────────────────┘                 └──────────────────────────────────────────────┘
```

**Key design decisions:**
- **Single LLM call per message** — extraction + follow-up + completion signal all in one Sonnet call (2048 max tokens)
- **Server-side state** — all session data (messages, coverage, report) lives in Supabase JSONB columns, not client state
- **Client is thin** — `page.tsx` is a `useReducer` orchestrator that calls API routes and renders phase-appropriate components
- **OpenRouter as proxy** — all Sonnet calls go through OpenRouter's OpenAI-compatible API, not Anthropic directly

---

## 3. Discovery Chat Loop (Per-Message Flow)

This is the core loop. Every time the user sends a message, this sequence runs:

```
 User (Browser)          /api/discovery/message           Supabase          OpenRouter (Sonnet)
 ──────────────          ─────────────────────            ────────          ───────────────────
      │
      │  POST { sessionId, message }
      │─────────────────→│
      │                  │  getSession(sessionId)
      │                  │──────────────────────→│
      │                  │←──────────────────────│ session (messages, coverage, ctx)
      │                  │
      │                  │  allMessages = [...session.messages, userMessage]
      │                  │  userTurnCount = count user messages
      │                  │
      │                  ├── IF Turn 1 (Scripted Q2 Guard) ──────────────────────────────┐
      │                  │   userTurnCount === 1 && priorUserCount === 0                 │
      │                  │   Save [userMsg, q2Msg] to Supabase                           │
      │                  │   Return scripted Q2, isComplete: false                       │
      │←─────────────────│                                                               │
      │                  │                                                               │
      │                  ├── ELSE Turn 2+ (LLM Takes Over) ─────────────────────────────┐│
      │                  │                                                              ││
      │                  │   buildDiscoveryPrompt(ctx, history, turnCount, dataPoints)   ││
      │                  │                                                              ││
      │                  │   chatCompletion(sonnet, prompt, 2048)                        ││
      │                  │──────────────────────────────────────────────→│               ││
      │                  │←──────────────────────────────────────────────│ raw JSON text ││
      │                  │                                                              ││
      │                  │   parseDiscoveryResponse (3-tier fallback)                    ││
      │                  │   Merge extraction.data_points into coverage                  ││
      │                  │   Recalculate area statuses (6 areas)                         ││
      │                  │   Check: model_thinks_complete && turnCount >= 3              ││
      │                  │                                                              ││
      │                  │   updateSessionAfterMessage(...)                              ││
      │                  │──────────────────────→│                                      ││
      │                  │                                                              ││
      │←─────────────────│   { assistantMessage, coverageUpdate, isComplete }            ││
      │                  └──────────────────────────────────────────────────────────────┘┘
```

### 3.1 Scripted Questions (Turns 1-2)

The first two turns are deterministic — no LLM involved:

| Turn | Who generates it | Content |
|------|-----------------|---------|
| Q1 (assistant) | `buildOpeningMessage()` in `/api/discovery/start` | "What are the main stages of a typical {jobType} job — from when your team first gets the call to when everything's wrapped up?" |
| A1 (user) | User's first reply | Their narrative description of the workflow |
| Q2 (assistant) | Hardcoded in `/api/discovery/message` | "Now walk me through the details — what does your tech actually do at each stage? Think about the paperwork, photos, customer interactions, and how the job gets closed out." |

**Why?** Q1 gets the broad strokes. Q2 pushes for operational detail. This gives the LLM a rich foundation before it takes over at Turn 3.

The guard condition: `userTurnCount === 1 && priorUserCount === 0` — fires exactly once on the user's first reply.

### 3.2 The 3-Tier JSON Parse Fallback

The LLM is instructed to return raw JSON (no markdown), but it doesn't always comply:

```
Tier 1: JSON.parse(text)           → Direct parse
        ↓ fails
Tier 2: text.match(/\{[\s\S]*\}/) → Extract JSON from markdown wrapping (```json ... ```)
        ↓ fails
Tier 3: Coverage-aware fallback    → No extraction, generic follow-up targeting first uncovered area
```

**Tier 3 is a safety net.** It:
- Extracts nothing (empty `data_points`)
- Generates a follow-up like "Tell me about the {uncovered area} stage"
- **Never signals completion** (`model_thinks_complete: false`) — only valid LLM JSON can end the conversation

### 3.3 Extraction Merge

After parsing, extracted `data_points` are merged into the session's accumulated `CoverageDataPoints`:

```
For each area in extraction.data_points:
  1. Lowercase the key (handles LLM returning "INTAKE" or "Intake")
  2. Check against validAreaKeys whitelist (6 areas + "additional_context")
  3. Shallow-merge: { ...existing[area], ...new[area] }
```

Also merged: `inferred` (implied data with reasoning), `specificGaps`, `customerLanguage`.

### 3.4 Completion Logic

```typescript
const modelComplete = response.model_thinks_complete && userTurnCount >= 3;
const complete = modelComplete;
```

**The LLM is the sole completion authority.** Backend coverage scoring is advisory only — it feeds into the prompt as a guide, but never gates completion.

The `turnCount >= 3` floor prevents premature completion if the LLM signals `true` too early.

When `complete === true`, the client transitions from the "discovery" phase to the "preferences" phase.

---

## 4. The Discovery Prompt

`buildDiscoveryPrompt()` in `prompts.ts` constructs the full prompt sent to Sonnet each turn. Here's its structure, annotated:

```
┌─────────────────────────────────────────────────────┐
│ PERSONA                                             │
│ "You are ClearPath, a workflow discovery agent..."  │
│                                                     │
│ WHAT YOU'RE BUILDING FOR                            │
│ Explains FieldPulse concepts: statuses, actions,    │
│ widgets, Focus View. Gives the LLM context on       │
│ WHY it's asking these questions.                    │
│                                                     │
│ BUSINESS CONTEXT                                    │
│ Company: {companyName}                              │
│ Industry: {industry}                                │
│ Size: {companySize}                                 │
│ Job type: {jobType}                                 │
│                                                     │
│ CONVERSATION SO FAR                                 │
│ ClearPath: ...                                      │
│ Customer: ...                                       │
│ (full history, every turn)                          │
│                                                     │
│ Turn count: {N}                                     │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ COVERAGE STATUS (injected by buildCoverage      │ │
│ │ Summary)                                        │ │
│ │ - intake: COVERED                               │ │
│ │ - en_route: PARTIAL — still need: travel_track  │ │
│ │ - arrival: UNCOVERED — still need: first_action │ │
│ │ - during_work: PARTIAL — still need: ...        │ │
│ │ - completion: COVERED                           │ │
│ │ - edge_cases: UNCOVERED — still need: ...       │ │
│ │                                                 │ │
│ │ "Use this as a guide — not every field is       │ │
│ │ relevant for every business."                   │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ═══════════════════════════════════════════          │
│ TASK 1 — EXTRACT                                    │
│ Parse latest message, extract NEW data into         │
│ structured fields. Lists all field names by area.   │
│ ═══════════════════════════════════════════          │
│                                                     │
│ ═══════════════════════════════════════════          │
│ TASK 2 — RESPOND                                    │
│ 7 rules for follow-up generation.                   │
│ COMPLETION rules (signal at 5+ turns, hard          │
│ ceiling at 8).                                      │
│ ═══════════════════════════════════════════          │
│                                                     │
│ ═══════════════════════════════════════════          │
│ OUTPUT — JSON schema for DiscoveryLLMResponse       │
│ ═══════════════════════════════════════════          │
└─────────────────────────────────────────────────────┘
```

**Key rules in the prompt:**
1. Never re-ask something already covered
2. After a big first message, confirm briefly then ask about ONE gap
3. Prioritize edge cases and pain points over happy-path details
4. ONE question per turn
5. Discover, don't consult (no advice or feature suggestions)
6. Suggest 2-3 quick-select chips
7. Coverage status is a guide, not a checklist

**Completion rules in the prompt:**
- Signal `model_thinks_complete: true` when core flow is covered + some edge case awareness + turn count 5+
- Hard ceiling: if turn count reaches 8 and core flow is covered, mark complete
- "The assembly step flags unknowns" — the LLM doesn't need to chase every detail

---

## 5. Coverage System

### 5.1 The Six Coverage Areas

Defined in `coverage-areas.ts`. Each area has required and optional data points:

| Area | Required Fields | Optional Fields |
|------|----------------|-----------------|
| **intake** | `job_source`, `job_creator` | `info_captured_at_intake`, `scheduling_model` |
| **en_route** | `customer_notification`, `clock_in_timing` | `travel_tracking` |
| **arrival** | `first_action` | `pre_work_requirements` |
| **during_work** | `work_description`, `photo_requirements` | `forms_checklists`, `parts_materials`, `time_tracking`, `estimates_or_invoices_onsite`, `info_needed_on_screen` |
| **completion** | `completion_requirements`, `invoice_process` | `signature`, `handoff_to_office`, `payment_collection` |
| **edge_cases** | `common_mistakes`, `management_frustrations` | `parts_not_available`, `customer_absent`, `multi_day_jobs`, `multiple_job_types` |

Plus a 7th non-tracked area: **additional_context** (`compliance_requirements`, `asset_equipment_tracking`, `special_processes`, `additional_details`).

### 5.2 Scoring Rules

`getAreaCoverageStatus(areaId, dataPoints)`:

```
No fields filled at all          → "uncovered"
Any field (required or optional) → "partial"
ALL required fields filled       → "covered"
```

### 5.3 How Coverage Feeds the Prompt

`buildCoverageSummary()` iterates the 6 areas and formats each as:

```
- intake: COVERED
- en_route: PARTIAL — still need: travel_tracking
- arrival: UNCOVERED — still need: first_action
```

This block is injected into the discovery prompt between the conversation history and TASK 1. The instruction below it says: *"Use this as a guide — not every field is relevant for every business. Focus on gaps that would change what gets built."*

### 5.4 The Coverage System's Two Roles

1. **Prompt anchor** — the COVERAGE STATUS block guides (but does not force) the LLM's question selection
2. **Structured extraction accumulator** — data extracted each turn builds up organized `CoverageDataPoints` that feed the assembly call

The coverage system does NOT gate completion. The LLM decides when the conversation is done.

---

## 6. Assembly (End of Conversation)

When the user submits preferences, the `/api/discovery/assemble` route runs a second Sonnet call to produce the final report.

```
 User (Browser)         /api/discovery/assemble          Supabase          OpenRouter (Sonnet)
 ──────────────         ──────────────────────           ────────          ───────────────────
      │
      │  POST { sessionId, preferences }
      │─────────────────→│
      │                  │  getSession(sessionId)
      │                  │──────────────────────→│
      │                  │←──────────────────────│ session (messages, coverage, ctx)
      │                  │
      │                  │  savePreferences(sessionId, preferences)
      │                  │──────────────────────→│
      │                  │
      │                  │  Build full transcript from all messages
      │                  │  buildReportAssemblyPrompt(ctx, transcript,
      │                  │      dataPoints, inferred, preferences)
      │                  │
      │                  │  chatCompletion(sonnet, assemblyPrompt, 4096)
      │                  │──────────────────────────────────────────────→│
      │                  │←──────────────────────────────────────────────│ DiscoveryReport JSON
      │                  │
      │                  │  Parse JSON (with regex fallback)
      │                  │  Validate: workflow_name + statuses[] required
      │                  │
      │                  │  saveReport(sessionId, report)
      │                  │──────────────────────→│
      │                  │
      │←─────────────────│  { report, summary }
```

### 6.1 What Gets Passed to Assembly

The assembly prompt receives everything accumulated during the conversation:

| Input | Source | Description |
|-------|--------|-------------|
| `businessContext` | Session row | Company name, industry, size, job type |
| `fullTranscript` | All session messages | Formatted as "ClearPath: ... / Customer: ..." |
| `allDataPoints` | `session.coverage.dataPoints` | The structured extraction from every turn, merged |
| `inferred` | `session.coverage.inferred` | Data the LLM marked as implied-but-not-confirmed |
| `preferences` | User's form submission | `restrictionPreference` (guided/flexible), `customerTextOnTheWay`, `existingForms` |

### 6.2 Assembly Prompt Structure

```
You are assembling a workflow discovery report from a conversation.

Business context: {company}, {industry}, {size}, {jobType}

Full conversation transcript:
{entire chat history}

Extracted data points:
{JSON of all accumulated CoverageDataPoints}

Inferred data:
{JSON of inferred entries}

User preferences:
- Restriction: guided/flexible
- Customer text on the way: true/false
- Existing forms: [...]

Produce the discovery report as JSON matching this exact schema:
{ ... DiscoveryReport schema ... }

Rules:
- Use customer's OWN language
- Number instructions in each status
- Every status has transitions_to
- Inferred data → medium_confidence
- Unknowns → gaps_or_unknowns
- 4-8 statuses typical
```

**Model:** `anthropic/claude-sonnet-4.5` via OpenRouter, 4096 max tokens.

---

## 7. Final JSON Report Schema

The `DiscoveryReport` — this is what the assembly produces and what gets sent to n8n:

```typescript
interface DiscoveryReport {
  workflow_name: string;           // e.g. "HVAC Service Call Workflow"
  job_types_covered: string[];     // e.g. ["Service Calls"]
  problems_to_solve: string[];     // Pain points from the conversation
  restriction_preference: string;  // "guided" or "flexible"

  statuses: DiscoveryReportStatus[];  // The workflow stages (4-8 typically)

  existing_templates_mentioned: string[];
  forms_mentioned: string[];

  confidence_notes: {
    high_confidence: string[];     // Explicitly confirmed by customer
    medium_confidence: string[];   // Inferred from context
    gaps_or_unknowns: string[];    // Not covered or unclear
  };

  customer_language: Record<string, string>;  // Their terms → meanings
}

interface DiscoveryReportStatus {
  name: string;            // e.g. "New Job Created"
  order: number;           // 1, 2, 3...
  instructions: string;    // "1. Do X\n2. Do Y\n3. Change status to Next"
  actions: string[];       // Plain language actions (e.g. "Clock in")
  widgets: string[];       // Info blocks (e.g. "Customer contact info")
  edge_cases: string[];    // What-if scenarios for this stage
  transitions_to: string[];// Next status name(s)
  notes: string;           // Additional context
}
```

**Important:** This report describes what the customer *wants* in plain language. It is NOT FieldPulse configuration. The n8n Relational Agent downstream translates this report into actual FieldPulse status/action/widget configuration using a knowledge base of patterns.

---

## 8. Submit to n8n

```
 User (Browser)        /api/discovery/submit             n8n Workflow (Clearpath Agent MVP)
 ──────────────        ─────────────────────             ────────────────────────────────
      │
      │  POST { sessionId, report }
      │────────────────→│
      │                 │  POST { sessionId, report }
      │                 │───────────────────────────→  ┌──────────────────────────────────┐
      │                 │                              │  Webhook (POST)                  │
      │                 │                              │    │                              │
      │                 │                              │    ↓                              │
      │                 │                              │  Prep Webhook Input (Code node)  │
      │                 │                              │    Extract body.report            │
      │                 │                              │    Stringify as output            │
      │                 │                              │    │                              │
      │                 │                              │    ↓                              │
      │                 │                              │  Relational Agent (Opus 4.5)     │
      │                 │                              │    Tools: PGVector, Neo4j,        │
      │                 │                              │           Structured Output       │
      │                 │                              │    Translates report →            │
      │                 │                              │      FieldPulse config            │
      │                 │                              │    │                              │
      │                 │                              │    ↓                              │
      │                 │                              │  Generate XLSX                   │
      │                 │                              └──────────────────────────────────┘
      │                 │←───────────────────────────  200 OK
      │←────────────────│  { success: true }
```

### 8.1 Webhook Payload

The exact JSON sent to the n8n webhook:

```json
{
  "sessionId": "uuid",
  "report": { /* full DiscoveryReport object */ }
}
```

### 8.2 n8n Workflow (Clearpath Agent MVP)

**Webhook** (POST) → **Prep Webhook Input** (Code node) → **Relational Agent** → **Generate XLSX**

The Prep Webhook Input code node extracts the report:
```javascript
const body = $input.all()[0].json.body;
const report = body.report;
return [{ json: { output: JSON.stringify(report), sessionId: body.sessionId } }];
```

The Relational Agent uses `anthropic/claude-opus-4.5` with tools:
- **PGVector Store** — searches `clearpath_status_patterns` for similar workflow configurations
- **Neo4j** — Cypher queries against a graph of FieldPulse entities and relationships
- **Structured Output Parser** — ensures output matches the expected Excel schema

---

## 9. Data Flow Summary

```
 Phase 1: Start
 ──────────────
 Business Context Form ──POST /start──→ Create Session in Supabase ──→ Return Scripted Q1

                                              │
                                              ↓
 Phase 2: Discovery Chat (N turns)
 ────────────────────────────────
                          ┌──────────────────────────────────────────────────────────┐
                          │                                                          │
  User Message ──POST /message──→ Turn 1? ──YES──→ Return Scripted Q2               │
                                    │                                                │
                                   NO                                                │
                                    ↓                                                │
                            Build Discovery Prompt                                   │
                            (includes COVERAGE STATUS)                               │
                                    ↓                                                │
                            Sonnet Call (2048 tokens)                                │
                                    ↓                                                │
                            3-Tier JSON Parse                                        │
                                    ↓                                                │
                            Merge Extraction → CoverageDataPoints                    │
                                    ↓                                                │
                            Score 6 Areas                                            │
                                    ↓                                                │
                    model_thinks_complete && turnCount >= 3?                          │
                          │                        │                                 │
                         NO                       YES                                │
                          ↓                        ↓                                 │
                   Return follow_up       Return isComplete: true                    │
                   + chips                         │                                 │
                          │                        │                                 │
                          └────── next turn ────→──┘                                 │
                          └──────────────────────────────────────────────────────────┘

                                              │
                                              ↓
 Phase 3: Preferences + Assembly
 ───────────────────────────────
 Preferences Form ──POST /assemble──→ Assembly Sonnet Call (4096 tokens)
                                      Input: full transcript + dataPoints + inferred + prefs
                                          ↓
                                      DiscoveryReport JSON

                                              │
                                              ↓
 Phase 4: Submit
 ───────────────
 User Reviews Report ──POST /submit──→ n8n Webhook ──→ Relational Agent ──→ XLSX
```

---

## 10. Supabase Session Schema

Table: `discovery_sessions`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Session identifier |
| `phase` | TEXT | Current phase: `business_context`, `discovery`, `preferences`, `confirmation` |
| `business_context` | JSONB | `{ companyName, industry, companySize, jobType }` |
| `coverage` | JSONB | Full `CoverageState`: areas, dataPoints, inferred, specificGaps, customerLanguage |
| `messages` | JSONB | Array of `ConversationMessage` objects (full chat history) |
| `preferences` | JSONB | `{ restrictionPreference, customerTextOnTheWay, existingForms }` |
| `report` | JSONB | The assembled `DiscoveryReport` (null until Phase 3) |
| `created_at` | TIMESTAMPTZ | Session creation time |
| `updated_at` | TIMESTAMPTZ | Last modification time |

Every API route reads/writes this single row. The `coverage.dataPoints` field grows incrementally as the LLM extracts data each turn.

---

## 11. Key Files Reference

| File | Purpose |
|------|---------|
| `src/app/discovery/page.tsx` | Client orchestrator — `useReducer` state machine, fetches API routes, renders phase components |
| `src/app/api/discovery/start/route.ts` | Creates Supabase session, returns scripted Q1 |
| `src/app/api/discovery/message/route.ts` | Core chat loop — scripted Q2 guard, Sonnet call, extraction merge, coverage scoring, completion check |
| `src/app/api/discovery/assemble/route.ts` | End-of-conversation assembly — second Sonnet call produces `DiscoveryReport` |
| `src/app/api/discovery/submit/route.ts` | POSTs `{ sessionId, report }` to n8n webhook |
| `src/lib/prompts.ts` | All AI prompt templates — `buildDiscoveryPrompt`, `buildReportAssemblyPrompt`, `buildOpeningMessage`, `buildCoverageSummary` |
| `src/lib/coverage-areas.ts` | 6 coverage area definitions, scoring functions, quick-select chip generation |
| `src/lib/openrouter.ts` | OpenRouter API client — `chatCompletion()`, model constants |
| `src/lib/supabase.ts` | Supabase client + CRUD: `createSession`, `getSession`, `updateSessionAfterMessage`, `savePreferences`, `saveReport` |
| `src/lib/logger.ts` | Pino logger — multistream to stdout (pretty) + `logs/discovery.log` (JSON lines) |
| `src/types/discovery.ts` | All TypeScript interfaces: `CoverageDataPoints`, `DiscoveryLLMResponse`, `DiscoveryReport`, API request/response types |
| `src/components/discovery/ChatInterface.tsx` | Chat UI — message bubbles, input, quick-select chips |
| `src/components/phases/PreferencesForm.tsx` | Preferences form UI (guided/flexible, text on the way, existing forms) |
| `src/components/phases/ConfirmationView.tsx` | Report review + submit/edit buttons |

---

## 12. LLM Response Shape

The single Sonnet call per message returns this JSON:

```json
{
  "extraction": {
    "data_points": {
      "intake": { "job_source": "Customer calls tech directly" },
      "during_work": { "photo_requirements": "Before and after photos" }
    },
    "inferred": {
      "en_route.customer_notification": "Likely none since customer calls tech directly"
    },
    "specific_gaps": ["No info on multi-day job handling"],
    "customer_language": {
      "completion report": "end-of-job form with work details, materials, hours"
    }
  },
  "follow_up": "What happens when a tech needs parts they don't have on the truck?",
  "model_thinks_complete": false,
  "suggested_quick_selects": [
    { "label": "Run to supply house", "value": "They run to the supply house and come back" },
    { "label": "Order and reschedule", "value": "We order the parts and reschedule for another day" }
  ]
}
```

This is validated by `isValidDiscoveryResponse()` which checks:
- `follow_up` is a string
- `model_thinks_complete` is a boolean
- `extraction` is an object with `inferred` sub-object

---

## 13. Logging

Pino structured logger (`src/lib/logger.ts`) writes to two streams:

| Stream | Format | Level |
|--------|--------|-------|
| `stdout` | Human-readable (pino-pretty in dev) | `debug` (dev) / `info` (prod) |
| `logs/discovery.log` | JSON lines | `debug` (dev) / `info` (prod) |

Every API route logs key events with `sessionId` for tracing:

```
Session started          → start/route.ts
Processing discovery message → message/route.ts (+ userTurnCount)
LLM extraction result    → message/route.ts (debug level, includes data_points)
Completion check         → message/route.ts (includes coverageAreas, modelComplete, userTurnCount)
Starting report assembly → assemble/route.ts
Report assembled         → assemble/route.ts (+ statusCount)
Submitting to webhook    → submit/route.ts
Report submitted         → submit/route.ts
```

View logs: `tail -f frontend/logs/discovery.log | npx pino-pretty`

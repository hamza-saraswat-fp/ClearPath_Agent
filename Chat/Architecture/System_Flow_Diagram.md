# ClearPath Guided Chat — System Flow Diagram (v2)

## Architecture Overview

**2 LLM Roles:**
- **Role 1: Discovery (Sonnet)** — Runs every message. Single call that extracts structured data AND generates the follow-up question. The model that decides what to ask is the same one that understood what was said.
- **Role 2: Assembly (Sonnet)** — Runs once at end. Synthesizes full conversation + extracted data + inferred data + preferences into the Discovery Report JSON.

```
                        ClearPath Guided Chat — Full System Flow (v2)
═══════════════════════════════════════════════════════════════════════════════

USER BROWSER                          NEXT.JS API ROUTES                    EXTERNAL
(React Frontend)                      (Server-Side)                         SERVICES
─────────────────                     ──────────────────                    ─────────

┌─────────────────────┐
│  LANDING PAGE       │
│  (app/page.tsx)     │
│                     │
│  ┌───────────────┐  │
│  │ Company Name  │  │
│  │ Industry  [v] │  │
│  │ Team Size [v] │  │
│  │ Job Type      │  │
│  │               │  │
│  │  [Start →]    │  │
│  └───────────────┘  │
└─────────┬───────────┘
          │
          │ POST /api/discovery/start
          │ { businessContext }
          │──────────────────────────────►┌──────────────────┐
          │                               │ start/route.ts   │
          │                               │                  │──────────►┌──────────┐
          │                               │ Create session   │           │ SUPABASE │
          │                               │ Generate opening │◄──────────│          │
          │◄──────────────────────────────│ message (static) │  session  │ sessions │
          │ { sessionId, firstMessage }   └──────────────────┘  row     │ table    │
          │                                                             └──────────┘
          ▼
┌─────────────────────────────────────────┐
│  DISCOVERY CHAT (app/discovery/page.tsx)│
│                                         │
│  ClearPath    [●● ●● ○○ ○○ ○○ ○○] 2/6 │   ◄── Progress bar (6 segments)
│  ─────────────────────────────────────  │
│                                         │
│  🤖 "Walk me through a typical AC      │
│     repair job from start to finish..." │
│                                         │
│  👤 "Customer calls in, office books   │
│     it, tech drives over, clocks in,   │
│     takes before photos, diagnoses,    │
│     fixes it, fills out completion     │
│     form, customer signs, office       │
│     invoices after..."                 │
│                                         │
│  🤖 "Got it — office schedules, tech   │
│     handles repair and paperwork,      │
│     office invoices. What about when   │
│     things don't go to plan — like     │
│     needing parts from the supply      │
│     house?"                            │
│                                         │
│  [Techs forget stuff] [Parts not      │   ◄── Quick-select chips
│   on truck]                            │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │ Type your answer...          [→]  │ │
│  └───────────────────────────────────┘ │
└─────────┬───────────────────────────────┘
          │
          │ ◄── Loop repeats ~3-6 turns until complete ──►
          │
          │ POST /api/discovery/message
          │ { sessionId, message }
          │──────────────────────────────►┌──────────────────────────────┐
          │                               │ message/route.ts             │
          │                               │                              │
          │                               │ 1. Get session from Supabase │
          │                               │                              │
          │                               │ 2. DISCOVERY (Sonnet)        │
          │                               │    Single LLM call ─────────────────►┌────────────┐
          │                               │    ┌────────────────────┐    │       │ OPENROUTER │
          │                               │    │                    │    │       │            │
          │                               │    │ Full conversation  │    │       │ Claude     │
          │                               │    │ + coverage state   │    │       │ Sonnet 4.5 │
          │                               │    │ + turn count       │◄──────────│            │
          │                               │    │                    │    │       └────────────┘
          │                               │    │ Returns BOTH:      │    │
          │                               │    │  extraction: {     │    │
          │                               │    │    data_points     │    │
          │                               │    │    inferred        │    │
          │                               │    │    specific_gaps   │    │
          │                               │    │    customer_lang   │    │
          │                               │    │  }                 │    │
          │                               │    │  follow_up: "..."  │    │
          │                               │    │  model_complete    │    │
          │                               │    └────────────────────┘    │
          │                               │                              │
          │                               │ 3. Merge into coverage state │
          │                               │    Recalculate area statuses │
          │                               │    Accumulate inferred data  │
          │                               │                              │
          │                               │ 4. Completion check:         │
          │                               │    backend_complete (all 6   │
          │                               │    areas covered) OR         │
          │                               │    model_complete (turn >= 3)│
          │                               │    Hard ceiling at turn 8    │
          │                               │                              │
          │                               │ 5. Build assistant message   │
          │                               │    + quick-select chips      │
          │                               │                              │
          │                               │ 6. Persist to Supabase       │──────►┌──────────┐
          │◄──────────────────────────────│                              │       │ SUPABASE │
          │ { coverageUpdate,             └──────────────────────────────┘       └──────────┘
          │   assistantMessage,
          │   isComplete }
          │
          │ ◄── When isComplete = true ──►
          ▼
┌─────────────────────────────────────────┐
│  PREFERENCES FORM (Phase 3)             │
│                                         │
│  How much freedom for techs?            │
│  ┌─────────────┐  ┌──────────────┐     │
│  │  ● Guided   │  │  ○ Flexible  │     │
│  └─────────────┘  └──────────────┘     │
│                                         │
│  Text customer when on the way?         │
│  [Yes]  [No]  [Decide later]           │
│                                         │
│  Existing forms in FieldPulse?          │
│  [Yes → ________]  [No]  [Not sure]   │
│                                         │
│  [Continue →]                           │
└─────────┬───────────────────────────────┘
          │
          │ POST /api/discovery/assemble
          │ { sessionId, preferences }
          │──────────────────────────────►┌──────────────────────────────┐
          │                               │ assemble/route.ts            │
          │                               │                              │
          │                               │ 1. Save preferences          │
          │                               │                              │
          │                               │ 2. ASSEMBLY (Sonnet)         │
          │                               │    ┌────────────────────┐    │
          │                               │    │ Full conversation + │    │
          │                               │    │ all data points +   │───────────►┌────────────┐
          │                               │    │ inferred data +     │    │        │ OPENROUTER │
          │                               │    │ preferences         │    │        │            │
          │                               │    │         ↓           │◄───────────│ Claude     │
          │                               │    │ Discovery Report    │    │        │ Sonnet 4.5 │
          │                               │    │ JSON                │    │        └────────────┘
          │                               │    └────────────────────┘    │
          │                               │                              │
          │                               │ 3. Validate & save report    │──────►┌──────────┐
          │◄──────────────────────────────│                              │       │ SUPABASE │
          │ { report, summary }           └──────────────────────────────┘       └──────────┘
          │
          ▼
┌─────────────────────────────────────────┐
│  CONFIRMATION VIEW (Phase 4)            │
│                                         │
│  AC Repair Workflow                     │
│  ──────────────────                     │
│  1. New             → Scheduled         │
│     Actions: assign tech                │
│  2. Scheduled       → On The Way        │
│     Actions: schedule date              │
│  3. On The Way      → On Site           │
│     Actions: send text, clock in        │
│  4. On Site         → In Progress       │
│     Actions: before photos, safety check│
│  5. In Progress     → Wrapping Up       │
│     Actions: fill form, take photos     │
│  6. Wrapping Up     → Complete          │
│     Actions: signature, invoice         │
│                                         │
│  ⚠ Inferred: signature is on the form  │
│  ⚠ Unknown: payment collection method  │
│                                         │
│  [← Edit]              [Confirm & Send] │
└─────────┬───────────────────────────────┘
          │
          │ POST /api/discovery/submit
          │ { sessionId, report }
          │──────────────────────────────►┌──────────────────────────────┐
          │                               │ submit/route.ts              │
          │                               │                              │
          │                               │ POST report JSON ───────────────────►┌──────────┐
          │                               │ to n8n webhook               │       │   N8N    │
          │◄──────────────────────────────│                              │       │          │
          │ { success: true }             └──────────────────────────────┘       │ Webhook  │
          │                                                                      │    ↓     │
          ▼                                                                      │ Agent 2  │
┌─────────────────────┐                                                          │ (Rela-   │
│  SUCCESS!            │                                                          │ tional)  │
│                      │                                                          │    ↓     │
│  Your workflow has   │                                                          │ Excel    │
│  been submitted.     │                                                          │ Pipeline │
│                      │                                                          │    ↓     │
│  [Start Another]     │                                                          │ .xlsx    │
└──────────────────────┘                                                          └──────────┘
```

---

## LLM Role Architecture

```
                    ┌──────────────────────────────────────────────────────┐
                    │              PER-MESSAGE (runs every turn)           │
                    │                                                      │
  User message ───► │  ROLE 1: DISCOVERY (Sonnet 4.5)                     │
                    │                                                      │
                    │  Input:                                              │
                    │    - Full conversation history                       │
                    │    - Current coverage state + data points            │
                    │    - Turn count                                      │
                    │    - Known gaps from previous turns                  │
                    │                                                      │
                    │  Does TWO things in ONE call:                        │
                    │    1. EXTRACT — parse new data into structured       │
                    │       fields across 6 coverage areas + catch-all    │
                    │       Separates confirmed vs inferred data          │
                    │    2. RESPOND — generate natural follow-up          │
                    │       targeting genuine config-relevant gaps        │
                    │                                                      │
                    │  Output:                                             │
                    │    { extraction, follow_up, model_thinks_complete }  │
                    └──────────────────────────────────────────────────────┘

                    ┌──────────────────────────────────────────────────────┐
                    │              ONCE (runs after preferences)           │
                    │                                                      │
  Preferences ────► │  ROLE 2: ASSEMBLY (Sonnet 4.5)                      │
                    │                                                      │
                    │  Input:                                              │
                    │    - Full conversation transcript                    │
                    │    - All accumulated data points                     │
                    │    - Inferred data with reasoning                    │
                    │    - User preferences                                │
                    │                                                      │
                    │  Does:                                               │
                    │    Synthesizes into Discovery Report JSON            │
                    │    - Ordered statuses with instructions              │
                    │    - Actions and widgets per status                  │
                    │    - Confidence notes (confirmed / inferred / gaps)  │
                    │    - Customer language mapping                       │
                    │                                                      │
                    │  Output:                                             │
                    │    Discovery Report JSON → n8n webhook               │
                    └──────────────────────────────────────────────────────┘
```

---

## Coverage State (tracked behind the scenes)

After each user message, the Discovery role extracts data across ALL 6 areas simultaneously.
The backend merges and recalculates coverage status per area.

```
  Comprehensive first message: "Customer calls in, office books it, tech drives over,
  clocks in, takes photos, diagnoses, fixes it, fills out form, customer signs,
  office invoices..."
                    │
                    ▼  Single Sonnet call extracts across ALL areas at once
  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
  │ INTAKE  │ │EN ROUTE │ │ ARRIVAL │ │  WORK   │ │COMPLETE │ │  EDGE   │
  │    ●    │ │    ◐    │ │    ●    │ │    ●    │ │    ●    │ │    ◐    │
  │ covered │ │ partial │ │ covered │ │ covered │ │ covered │ │ partial │
  │         │ │         │ │         │ │         │ │         │ │         │
  │ source: │ │ clock:  │ │ first:  │ │ work:   │ │ reqs:   │ │ parts:  │
  │  phone  │ │ arrival │ │ photos  │ │ diag +  │ │ photos, │ │ supply  │
  │ creator:│ │ notif:  │ │ pre:    │ │ repair  │ │ form,   │ │ house   │
  │  office │ │ inferred│ │ photos  │ │ forms:  │ │ sign    │ │ common: │
  │ sched:  │ │         │ │         │ │ complet │ │ handoff:│ │  ???    │
  │ advance │ │         │ │         │ │ photos: │ │ office  │ │ mgmt:   │
  │         │ │         │ │         │ │ b&a     │ │ invoice:│ │  ???    │
  │         │ │         │ │         │ │ parts:  │ │ office  │ │         │
  │         │ │         │ │         │ │ supply  │ │         │ │         │
  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘

  Progress bar: [●● ◐◐ ●● ●● ●● ◐◐]  4/6 covered  (after just 1 message!)

  Inferred: { "en_route.customer_notification": "customer initiated call, likely expecting visit" }
  Gaps: ["what do techs keep forgetting?", "how are multi-day jobs handled?"]

  → Sonnet follow-up targets edge cases: "What about when things don't go to plan?"
```

---

## Coverage Data Points (v2 expanded schema)

```
INTAKE                    EN ROUTE                ARRIVAL
├─ job_source             ├─ customer_notification ├─ first_action
├─ job_creator            ├─ clock_in_timing      └─ pre_work_requirements
├─ info_captured_at_intake└─ travel_tracking
└─ scheduling_model

DURING WORK               COMPLETION              EDGE CASES
├─ work_description       ├─ completion_reqs      ├─ common_mistakes
├─ forms_checklists       ├─ signature            ├─ management_frustrations
├─ photo_requirements     ├─ handoff_to_office    ├─ parts_not_available
├─ parts_materials        ├─ invoice_process      ├─ customer_absent
├─ time_tracking          └─ payment_collection   ├─ multi_day_jobs
├─ estimates_or_invoices                          └─ multiple_job_types
└─ info_needed_on_screen

ADDITIONAL CONTEXT (not tracked — extraction only, feeds into assembly)
├─ compliance_requirements
├─ asset_equipment_tracking
├─ special_processes
└─ additional_details
```

---

## Discovery Report JSON (what gets sent to n8n webhook)

```json
{
  "workflow_name": "AC Repair Workflow",
  "job_types_covered": ["AC repair", "service calls"],
  "problems_to_solve": ["techs forget before photos", "no consistent process"],
  "restriction_preference": "guided",
  "statuses": [
    {
      "name": "On The Way",
      "order": 3,
      "instructions": "1. Send on-the-way text\n2. Clock in\n3. Change status to On Site",
      "actions": ["send on-the-way text", "clock in"],
      "widgets": ["customer contact", "customer address"],
      "edge_cases": [],
      "transitions_to": ["On Site"],
      "notes": ""
    }
  ],
  "existing_templates_mentioned": [],
  "forms_mentioned": [],
  "confidence_notes": {
    "high_confidence": ["office creates jobs", "before/after photos required"],
    "medium_confidence": ["signature is on the completion form (inferred)"],
    "gaps_or_unknowns": ["payment collection method not discussed"]
  },
  "customer_language": {
    "the girls up front": "front desk/office staff",
    "supply house": "parts supplier",
    "turn in the paperwork": "submit the completion form"
  }
}
```

---

## Key Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| **1 LLM call per message (not 2)** | The model that decides what to ask must be the same one that understood what was said. Splitting extraction and follow-up created handoff loss — Haiku missed nuance, Sonnet re-asked covered topics. |
| **Confirmed vs Inferred extraction** | Captures "strongly implied" information without burning a follow-up turn to confirm it. Inferred data flows to assembly as `medium_confidence`. |
| **Turn count ceiling (8 max)** | Prevents drawn-out conversations. A focused 4-6 turn chat beats a 12-turn micro-question interview. |
| **additional_context not tracked** | Compliance, assets, special processes are bonus extraction — they feed assembly but don't block completion or show in progress bar. |
| **Backend OR model completion** | `isDiscoveryComplete()` checks all required fields filled. Model can also signal completion if core flow + pain points are covered (min 3 turns). Either path triggers transition to preferences. |

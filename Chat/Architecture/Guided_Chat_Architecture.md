# ClearPath Guided Chat — Architecture Plan (v2)

## Context

ClearPath needs a guided chat frontend that discovers a field service company's job workflow through conversation, then produces a structured discovery report JSON. This report gets sent via webhook to an n8n Relational Agent that handles all the FieldPulse-specific mapping (widgets, action buttons, relationships).

**The problem:** Having AI run the entire conversation from a single prompt is too non-deterministic — it skips topics, rushes, combines questions, misses data. We need the app to provide guardrails while keeping the experience conversational.

**The output** is a discovery report — NOT the `StructuredIntent` Python schema. The guided chat's only job is capturing the workflow in plain language. The n8n agent downstream does all the heavy lifting.

---

## Output Schema: Discovery Report

```json
{
  "workflow_name": "string",
  "job_types_covered": ["string"],
  "problems_to_solve": ["string"],
  "restriction_preference": "string",
  "statuses": [
    {
      "name": "string",
      "order": 1,
      "instructions": "1. First thing to do\n2. Second thing\n3. Change status to Next Status",
      "actions": ["clock in", "send on-the-way text"],
      "widgets": ["job details", "customer contact info"],
      "edge_cases": [],
      "transitions_to": ["Next Status Name"],
      "notes": "Any additional context"
    }
  ],
  "existing_templates_mentioned": [],
  "forms_mentioned": [],
  "confidence_notes": {
    "high_confidence": [],
    "medium_confidence": [],
    "gaps_or_unknowns": []
  },
  "customer_language": {}
}
```

This is what gets POST'd to the n8n webhook. Plain language, no ClearPath-specific terminology.

---

## Phase 2: Conversational Discovery with Guardrails

### How it works

Instead of walking through 6 topics one-by-one, the conversation starts open-ended and the app tracks coverage behind the scenes.

```
1. Open with: "Walk me through a typical {jobType} job from start to finish --
   from when you first get the call to when the job is completely done."

2. User gives their narrative (often covers multiple areas at once)

3. AI extracts coverage across ALL 6 topic areas from every response
   (not just the "current" topic -- cross-topic extraction)

4. App updates coverage tracker:
   [x] Intake  [x] En Route  [ ] Arrival  [ ] Work  [ ] Completion  [ ] Edge Cases

5. AI generates a natural follow-up targeting the FIRST uncovered area
   "You covered how the job comes in and the drive over.
    What happens when your tech actually arrives on site?"

6. Repeat until all areas have sufficient coverage

7. Targeted probes for specific gaps:
   "You mentioned photos -- is that before AND after, or just after?"

8. Edge case questions (always asked, even if user didn't mention):
   "What's the one thing you're always reminding your team about?"
   "What do they keep forgetting to do?"
   "What happens if they need parts they don't have?"
```

### The 6 Coverage Areas (behind-the-scenes checklist)

These are NOT shown as rigid topics to the user. They're internal tracking for what the conversation needs to cover.

| Area | What We Need | Key Data Points |
|------|-------------|-----------------|
| **Intake** | How jobs come in, who creates them, scheduling | job source, job creator, scheduling step |
| **En Route** | Between dispatch and arrival | customer notification, clock-in timing |
| **Arrival** | First actions on site | first thing at site, pre-work requirements |
| **During Work** | The actual work | forms, photos, estimates/invoices, info needed |
| **Completion** | Wrapping up | signature, final docs, invoicing, payment |
| **Edge Cases** | The unexpected | reminders, forgotten tasks, parts, absent customer, multi-day |

### Where AI is Used (3 layers)

| Layer | What | When | Model |
|-------|------|------|-------|
| **Coverage Extraction** | Reads user message, marks which areas were addressed, extracts key data points | Every user message | Haiku (fast, cheap) |
| **Follow-Up Generation** | Generates natural conversational follow-up targeting uncovered areas or gaps | When areas remain uncovered | Sonnet (natural language) |
| **Report Assembly** | Synthesizes full conversation into the discovery report JSON | Once, at end of Phase 2 | Sonnet (structured output) |

### Coverage Extraction Prompt
```
You are tracking a workflow discovery conversation for a {industry} company ({companySize}).
They are describing their {jobType} workflow.

Coverage areas to track:
1. Intake: how jobs come in, who creates, scheduling
2. En Route: customer notification, clock-in timing, between dispatch and arrival
3. Arrival: first action on site, pre-work requirements
4. During Work: what they do, forms, photos, estimates/invoices, info needed
5. Completion: what's required before done, signature, invoice handling, payment
6. Edge Cases: constant reminders, forgotten tasks, parts needed, customer absent, multi-day

User's message: "{userMessage}"

Previously covered: {coveredAreas}

Output JSON:
{
  "newly_covered": ["intake", "en_route"],
  "data_points": {
    "intake": { "job_source": "phone call", "job_creator": "tech", "scheduling": false },
    "en_route": { "customer_notification": false }
  },
  "still_uncovered": ["arrival", "during_work", "completion", "edge_cases"],
  "specific_gaps": ["clock_in_timing not mentioned"],
  "customer_language": { "phone call": "they just call the tech directly" }
}
```

### Follow-Up Generation Prompt
```
You are having a natural conversation discovering a {industry} company's {jobType} workflow.
Company: {companyName}, Size: {companySize}

Conversation so far:
{conversationHistory}

We've covered: {coveredAreas}
Still need to learn about: {uncoveredAreas}
Specific gaps: {specificGaps}

Generate a natural follow-up (2-3 sentences max) that:
- Briefly acknowledges what they just said
- Transitions naturally to the next uncovered area
- Uses language appropriate for a {industry} business owner
- Does NOT sound like a form or checklist

If all main areas are covered but specific gaps remain, ask a targeted clarifier.
If only edge cases remain, ask: "A few quick questions about the unexpected stuff..."
```

### Report Assembly Prompt
```
You are assembling a workflow discovery report from a conversation.
Business context: {companyName}, {industry}, {companySize}, {jobType}

Full conversation transcript:
{fullTranscript}

Extracted data points:
{allDataPoints}

User preferences:
{phase3Preferences}

Produce the discovery report JSON matching this exact schema:
{discoveryReportSchema}

Rules:
- Use the customer's own language in actions/widgets (don't translate to technical terms)
- Number instructions in each status as "1. ... 2. ... 3. Change status to [Next]"
- Every status must have transitions_to pointing to the next logical status
- Capture anything you're uncertain about in confidence_notes.gaps_or_unknowns
- Include customer_language mapping their words to what they likely mean
```

---

## The 4-Phase Flow

### Phase 1: Business Context (Structured Form)
Separate page. Fields:
- Company name (text)
- Industry (dropdown: HVAC, Plumbing, Electrical, Garage Door, General Contracting, Other)
- Company size (dropdown: 1-5 techs, 6-15, 16-50, 50+)
- Job type for this workflow (text: "AC installation", "service calls", etc.)

### Phase 2: Guided Discovery (Conversational + Coverage Tracking)
See detailed section above. Open-ended conversation with behind-the-scenes coverage tracking. Quick-select chips for common answers. Minimal progress bar at top (6 dots) shows coverage progress.

### Phase 3: Preferences (Structured Form)
Fields:
- How much freedom should techs have? (Guided / Flexible) -> restriction_preference
- Should the system text the customer when the tech is on the way? (Yes / No / Decide later)
- Any existing forms or checklists in FieldPulse? (Yes -> which ones / No / Not sure)

### Phase 4: Confirmation & Handoff
- AI assembles the discovery report JSON from conversation + preferences
- User sees a human-readable summary of statuses/actions
- User confirms or requests edits (can chat to modify)
- On confirm: POST discovery report JSON to n8n webhook

---

## Frontend Architecture

### Decisions
- **Same repo** -- Next.js app in `frontend/` directory
- **Server-side sessions** -- Supabase for session persistence (JSONB for conversation + coverage state)
- **Chips + free text** -- Quick-select chips for common answers, free text always available
- **Minimal progress** -- Top progress bar with 6 dots, no sidebar

### UI Layout

Full-width chat with a minimal progress bar at the top. No sidebar -- keeps the experience feeling like a natural conversation, not a form.

```
+---------------------------------------------+
|  ClearPath     [** ** .. .. .. ..]  3/6     |
+---------------------------------------------+
|                                              |
|  Bot: "Walk me through a typical AC repair   |
|   job from start to finish..."               |
|                                              |
|  User: "Tech gets a call, drives over,       |
|   clocks in when they get there..."          |
|                                              |
|  Bot: "Got it. What happens when they        |
|   arrive on site?"                           |
|                                              |
|  [Take photos] [Safety check] [Meet cust.]  |
|                                              |
|  +----------------------------------------+ |
|  | Type your answer...               [->] | |
|  +----------------------------------------+ |
+---------------------------------------------+
```

### Tech Stack
- **Next.js 14+ (App Router)** -- React, Tailwind CSS
- **Framer Motion** -- Animations
- **lucide-react** -- Icons
- **Supabase** -- Session storage (sessions table, JSONB columns)
- **Anthropic SDK** (`@anthropic-ai/sdk`) -- Claude API calls server-side
- Client state: `useReducer` synced to server sessions via API

### Key Files
```
frontend/
  src/
    app/
      page.tsx                              -- Landing / Phase 1 business context form
      discovery/page.tsx                    -- Phase 2-4 (chat, preferences, confirmation)
    app/api/
      discovery/start/route.ts              -- Create session
      discovery/message/route.ts            -- Core chat endpoint
      discovery/session/[id]/route.ts       -- Get session (reconnection)
      discovery/assemble/route.ts           -- Assemble discovery report
      discovery/submit/route.ts             -- POST to n8n webhook
    components/
      discovery/ChatInterface.tsx           -- Main chat area
      discovery/ProgressBar.tsx             -- Top progress bar (6 segments)
      discovery/QuickSelectChips.tsx        -- Clickable answer chips
      discovery/MessageBubble.tsx           -- Chat message component
      discovery/TypingIndicator.tsx         -- Loading state
    components/phases/
      BusinessContextForm.tsx               -- Phase 1 form
      PreferencesForm.tsx                   -- Phase 3 form
      ConfirmationView.tsx                  -- Phase 4 summary + confirm
    lib/
      coverage-areas.ts                     -- 6 area definitions + helpers
      prompts.ts                            -- All 3 AI prompt templates
      supabase.ts                           -- Supabase client + session CRUD
    types/
      discovery.ts                          -- All TypeScript interfaces
```

---

## Verification

1. **Conversation flow:** Walk through CSS Mechanical scenario -- verify coverage tracking works
2. **Coverage completeness:** All 6 areas covered before assembly allowed
3. **Report quality:** Compare discovery report against expected output for test scenarios
4. **Webhook integration:** Report POSTs correctly to n8n
5. **Session persistence:** Browser refresh loads full state from Supabase
6. **Edge cases:** One-word answer user vs. dump-everything-at-once user

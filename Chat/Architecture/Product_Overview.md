# ClearPath Discovery Chat — Product Overview

## What It Is

ClearPath is a guided conversational tool that discovers how a field service company runs their jobs — from the first customer call to the final invoice — and produces a structured workflow configuration. The output is a JSON report sent to an n8n automation that configures FieldPulse (the field service management platform) to match how the business actually works.

The whole experience takes about 5 minutes.

---

## The Four Phases

### Phase 1: Business Context Form

Before the chat starts, the user fills out a short form with four fields:

| Field | Input Type | Purpose |
|-------|-----------|---------|
| **Company Name** | Text | Personalizes the conversation and report |
| **Industry** | Dropdown (10 options: HVAC, Plumbing, Electrical, Garage Door, General Contracting, Roofing, Landscaping, Pest Control, Cleaning, Other) | Gives the AI context for industry-specific defaults and terminology |
| **Team Size** | Button group (1-5, 6-15, 16-50, 50+ techs) | Affects complexity assumptions — a 3-person shop works differently than a 50-tech operation |
| **Job Type** | Text (e.g., "AC installation," "service calls") | Scopes the conversation to ONE workflow type |

**Why these four?** They're the minimum context the AI needs to have a productive first conversation. Industry tells it what kind of work to expect. Team size tells it whether there's an office staff or if the owner IS the tech. Job type scopes the conversation — a plumbing company might run installs and service calls completely differently, so we discover one at a time.

After submitting, a session is created and the chat begins.

---

### Phase 2: Discovery Conversation

This is the core of ClearPath. The AI (Claude Sonnet via OpenRouter) has a natural conversation with the business owner to understand their workflow.

#### The Opening Question

> "What are the main stages of a typical {job type} job — from when your team first gets the call to when everything's wrapped up? For example, stages like 'Dispatched,' 'On Site,' 'Work Complete.' Walk me through how yours usually goes."

This is deliberately open-ended and framed around **named stages/milestones**. Most business owners will respond with a comprehensive narrative covering 60-80% of what we need in one message.

#### What the AI Does on Every Turn

Each time the user sends a message, the AI performs two tasks in a single pass:

**Task 1 — Extract:** Parse the message and pull out structured data into specific fields across 6 coverage areas (see below). The AI distinguishes between:
- **Confirmed** — the customer explicitly said it
- **Inferred** — strongly implied but not stated (e.g., "tech fills out the form and gets a signature" implies the signature is ON the form). These get flagged as medium-confidence in the final report.
- **Unknown** — not mentioned or implied. The AI doesn't guess.

**Task 2 — Respond:** Generate a natural follow-up question targeting the most important gap that hasn't been covered yet. The AI follows strict conversational rules (see "Conversation Behavior" below).

#### The 6 Coverage Areas

Behind the scenes, the conversation is tracking progress across six areas. These aren't shown to the user as a checklist — they drive the AI's question selection and the progress bar at the top of the chat.

**1. Job Intake** — How jobs originate
| Data Point | What We're Capturing | Example |
|-----------|---------------------|---------|
| `job_source` | How jobs come in | "Customer calls the office" |
| `job_creator` | Who creates the job in the system | "Office staff enters it" |
| `info_captured_at_intake` | What's recorded upfront | "Customer name, address, job type" |
| `scheduling_model` | How scheduling works | "Same-day reactive, mostly" |

**2. En Route** — Between dispatch and arrival
| Data Point | What We're Capturing | Example |
|-----------|---------------------|---------|
| `customer_notification` | Whether/how customer is notified | "Tech sends a text when leaving" |
| `clock_in_timing` | When time tracking starts | "When they create the job" |
| `travel_tracking` | Whether drive time is tracked separately | "No, just total hours" |

**3. Arrival** — First actions on site
| Data Point | What We're Capturing | Example |
|-----------|---------------------|---------|
| `first_action` | What happens first | "Meet customer, confirm scope" |
| `pre_work_requirements` | Anything required before starting | "Take before photos" |

**4. During Work** — The actual job
| Data Point | What We're Capturing | Example |
|-----------|---------------------|---------|
| `work_description` | What the tech physically does | "Installs the unit, runs linesets" |
| `forms_checklists` | Structured data capture | "Startup form with readings" |
| `photo_requirements` | What photos, when, visibility rules | "Before/after, receipt photos internal only" |
| `parts_materials` | How parts are handled | "PO from supply house, receipt photo" |
| `time_tracking` | How hours are recorded | "Total hours, regular vs overtime" |
| `estimates_or_invoices_onsite` | Whether estimates/invoices happen on site | "Tech creates estimate on site" |
| `info_needed_on_screen` | What info tech needs visible | "Equipment model, customer notes" |

**5. Completion** — Wrapping up
| Data Point | What We're Capturing | Example |
|-----------|---------------------|---------|
| `completion_requirements` | What must happen before marking done | "Form submitted, signature, photos" |
| `signature` | Where it lives, what it authorizes | "On the form, authorizes invoicing" |
| `handoff_to_office` | What happens after tech marks complete | "Office reviews and builds invoice" |
| `invoice_process` | Who creates invoices, approval steps | "Office creates from the job" |
| `payment_collection` | On-site or billed later | "Billed later, net 30" |

**6. Edge Cases** — The real-world messiness
| Data Point | What We're Capturing | Example |
|-----------|---------------------|---------|
| `common_mistakes` | What techs frequently get wrong | "Forget to take before photos" |
| `management_frustrations` | What the owner constantly reminds about | "Fill out the form BEFORE leaving" |
| `parts_not_available` | What happens when parts aren't on the truck | "Go to supply house, come back" |
| `customer_absent` | What happens when customer isn't there | "Call them, wait 15 min" |
| `multi_day_jobs` | How return visits are handled | "Create a follow-up job" |
| `multiple_job_types` | Whether different work follows different flows | "Install and service are different" |

There's also an **Additional Context** bucket for things like compliance requirements, asset tracking, and special processes. This doesn't appear in the progress bar — it's just extra data that flows into the report.

#### Coverage Status Logic

Each area has **required** and **optional** data points:
- **Uncovered** — no data points extracted yet
- **Partial** — at least one data point (required or optional) has been extracted
- **Covered** — all required data points for that area are filled

The progress bar at the top of the chat shows 6 segments that fill based on these statuses.

#### Conversation Behavior Rules

The AI follows strict rules to keep the conversation productive:

1. **Never re-ask** something the customer already told you — even if the data field isn't perfectly filled
2. **After a big first message** — don't walk through it step by step. Briefly confirm the flow, then ask about ONE genuine gap
3. **Genuine gaps only** — a gap is genuine if the answer would change what gets built. "What happens when a tech needs parts they don't have?" is genuine. "Tell me more about the form" when they already described it is not.
4. **Prioritize edge cases and pain points** — these drive the most important config decisions (required fields, restrictions, guardrails)
5. **One question per turn** — no lists, no multi-part questions
6. **Match their energy** — brief user gets brief AI, detailed user gets slightly more conversational AI
7. **Natural transitions** — "Makes sense. So once the tech wraps up — what needs to happen before that job is officially done?" not "Now let's talk about completion."
8. **Discover, don't consult** — no advice, no opinions, no feature suggestions
9. **Mirror their language** — if they say "turn in the paperwork," don't say "submit the completion form"

#### Quick Select Chips

After each AI question, 2-3 quick-select chips appear below the message. These are **contextual** — the AI generates them based on the specific question it just asked, offering realistic shortcut answers the user can tap instead of typing.

Example: If the AI asks "What happens when a tech needs parts they don't have?", chips might show:
- "Supply house run" → "They go to the supply house and come back the same day"
- "Order and reschedule" → "We order the parts and schedule a return visit"
- "Always stocked" → "We make sure techs are stocked with common parts"

#### Completion Logic

The conversation ends when either:
- **Backend complete:** All 6 areas have all required data points filled (all segments "covered")
- **Model complete:** The AI signals it has enough to build the config AND the user has sent at least 3 messages (prevents premature completion)
- **Hard ceiling:** If turn count hits 8 and the core flow is covered, the AI wraps up regardless. The assembly step flags unknowns.

Target: **4-6 turns** for a typical conversation. The first message usually covers 60-80% of the workflow, and the remaining turns fill genuine gaps.

---

### Phase 3: Preferences Form

After the chat completes, the user sees a short form with three preference questions:

| Question | Options | Why It Matters |
|----------|---------|---------------|
| **How much freedom should techs have?** | Guided (follow steps in order, status changes enforced) vs. Flexible (skip steps, change status freely) | Determines whether the workflow has strict status restrictions or loose ones |
| **Text customer when tech is on the way?** | Yes / No / Decide later | Configures automated customer notification |
| **Existing forms or checklists in FieldPulse?** | Yes (with text input for names) / No / Not sure | Tells the config builder whether to reference existing templates or create new ones |

These are asked separately from the chat because they're **preference decisions**, not discovery questions. The business owner needs to decide how they WANT it to work, not describe how it currently works.

---

### Phase 4: Confirmation & Submit

The system assembles the full Discovery Report by running a second AI pass (Claude Sonnet) that synthesizes the entire conversation, extracted data, inferred data, and preferences into a structured JSON report.

The user sees a visual summary showing:
- Workflow name and job types
- All statuses in order, with actions, instructions, and transitions
- Expandable detail for each status
- Confidence notes (high confidence, medium confidence, gaps/unknowns)

The user can:
- **Edit** — go back to the chat to add more information
- **Confirm & Submit** — sends the report to the n8n webhook for FieldPulse configuration

---

## The Discovery Report (What Gets Sent to n8n)

The final output is a structured JSON payload:

```json
{
  "workflow_name": "HVAC Service Call",
  "job_types_covered": ["Service call", "Repair"],
  "problems_to_solve": ["Techs forget before photos", "Invoices delayed because office doesn't know job is done"],
  "restriction_preference": "guided",
  "statuses": [
    {
      "name": "New Job",
      "order": 1,
      "instructions": "1. Verify customer info and job details\n2. Assign tech\n3. Change status to Dispatched",
      "actions": ["Assign technician", "Confirm schedule"],
      "widgets": ["Customer info", "Job details"],
      "edge_cases": ["Customer calls to reschedule — update date before dispatching"],
      "transitions_to": ["Dispatched"],
      "notes": "Office handles this step"
    },
    {
      "name": "Dispatched",
      "order": 2,
      "instructions": "1. Review job details\n2. Text customer you're on the way\n3. Change status to On Site when you arrive",
      "actions": ["Send customer notification", "Start travel time"],
      "widgets": ["Navigation", "Customer phone"],
      "edge_cases": ["Running late — text customer with updated ETA"],
      "transitions_to": ["On Site"],
      "notes": ""
    }
  ],
  "existing_templates_mentioned": ["Safety checklist"],
  "forms_mentioned": ["Startup form"],
  "confidence_notes": {
    "high_confidence": ["Job intake process", "Photo requirements", "Completion flow"],
    "medium_confidence": ["Signature is on the form (inferred from 'fill out form and get signature')"],
    "gaps_or_unknowns": ["Multi-day job handling not discussed", "Payment terms unclear"]
  },
  "customer_language": {
    "turn in the paperwork": "submit completion form",
    "startup form": "post-installation checklist with system readings"
  }
}
```

Key design decisions in the report:
- **Uses the customer's own language** in actions and instructions, not FieldPulse technical terms
- **Numbered instructions** in each status ("1. Do this. 2. Do that. 3. Change status to X")
- **Every status has transitions_to** pointing to the next logical status
- **Confidence notes** separate confirmed facts from inferred ones, and flag anything unknown
- **Customer language map** helps the config builder translate colloquial terms

---

## Architecture Summary

| Component | Technology | Role |
|-----------|-----------|------|
| Frontend | Next.js + React + Tailwind | Chat UI, forms, progress tracking |
| AI (Discovery) | Claude Sonnet via OpenRouter | Extraction + follow-up per message |
| AI (Assembly) | Claude Sonnet via OpenRouter | Synthesizes conversation into report |
| Database | Supabase (PostgreSQL + JSONB) | Session persistence, messages, coverage state |
| Automation | n8n webhook | Receives report, configures FieldPulse |

The conversation state (messages, coverage data, inferred data) is persisted to Supabase after every message, so sessions survive page refreshes.

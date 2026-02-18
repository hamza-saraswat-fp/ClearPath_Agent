# ClearPath Guided Chat — Strategy & Direction

## Part 1: Architecture — Custom Next.js/React App

### Why n8n Isn't Working for the Guided Chat

The n8n chat trigger gives you a basic back-and-forth conversation window, but it has critical limitations for what we're building:

- **No conversation pacing control** — can't enforce "ask these 3 questions before generating." The agent rushes through in 2 exchanges and tries to generate the report.
- **No UI control** — can't add buttons, progress indicators, dropdowns, or structured input fields alongside the chat. It's pure text in, text out.
- **No state visibility** — the user can't see what's been captured so far or what's still missing.
- **No conditional branching in the UI** — can't say "if they mention multiple workflows, show a selector."
- **No embeddability** — can't drop this into a FieldPulse-branded experience.

n8n remains great for the backend orchestration (Agent 2 → knowledge graph → Excel generation). But the front-end discovery conversation needs a custom-built solution.

### The Approach: Custom React/Next.js Guided Chat App

We're building a custom Next.js/React application for the guided chat front end. This gives us:

- **Total control over UX** — progress bars, status previews, phase transitions, multi-workflow detection
- **Hybrid form + chat experience** — structured form fields for bounded questions (Phase 1), AI-powered conversational interface for open-ended discovery (Phase 2), structured inputs again for preferences (Phase 3)
- **Direct API integration** — calls the Claude API for the Discovery Agent conversation, then hits the n8n webhook to trigger Agent 2 + Excel generation downstream
- **Deployable as standalone or embeddable** — can run as an internal tool now, and eventually be embedded into FieldPulse
- **Conversation state management** — React state tracks what's been captured, what phases are complete, and what gaps remain
- **No platform limitations or vendor lock-in** — we own the full stack

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  NEXT.JS / REACT APP (Guided Chat Front End)                │
│                                                              │
│  Phase 1: Business Context Form                              │
│    → Structured form fields (company, industry, size, job)   │
│    → Collected as state, passed to Phase 2 as context        │
│                                                              │
│  Phase 2: AI-Guided Discovery Conversation                   │
│    → Chat UI powered by Claude API                           │
│    → Discovery Agent system prompt with Phase 1 context      │
│    → Controlled pacing: agent must cover all discovery areas  │
│    → Conversation history maintained in React state           │
│                                                              │
│  Phase 3: Preferences & Guardrails                           │
│    → Structured form fields (Focus View, notifications, etc) │
│                                                              │
│  Phase 4: Confirmation & Report Generation                   │
│    → Agent summarizes captured workflow                       │
│    → User confirms or requests edits                         │
│    → Structured JSON report generated                        │
│                                                              │
└──────────────────────┬──────────────────────────────────────┘
                       │ POST structured report (JSON)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  N8N (Backend Orchestration)                                 │
│                                                              │
│  Webhook receives Discovery Report                           │
│    → Agent 2: Semantic Mapping (Neo4j graph + Supabase       │
│      pgvector) maps customer language to ClearPath            │
│      terminology, action buttons, widgets                    │
│    → Excel Transformer API: deterministic code generates      │
│      3-tab .xlsx import template                             │
│    → Output: ClearPath_Import.xlsx                           │
│                                                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  HUMAN REVIEW + IMPORT                                       │
│                                                              │
│  FieldPulse rep reviews generated template, makes final      │
│  adjustments, imports into customer account via Master tool.  │
│  Nothing goes live without human eyes.                        │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack

- **Frontend:** Next.js (React), Tailwind CSS for styling
- **AI:** Claude API (Anthropic) for the Discovery Agent conversation in Phase 2
- **State Management:** React state (useState/useReducer) for conversation history, form data, and phase tracking
- **Backend API:** Next.js API routes for Claude API calls (keeps API key server-side)
- **Downstream:** n8n webhook for Agent 2 pipeline (existing infrastructure)
- **Deployment:** Vercel (simplest for Next.js) or internal hosting

---

## Part 2: Building the Right Question Framework

### What We Know from the Transcripts & Jaden's Review

Having gone through the CSS Mechanical, Barnett, Wayside, 1st Choice, and AK Doors transcripts — plus Jaden's detailed review of what the agent produced versus what the real accounts look like — here's what actually matters in a discovery conversation:

#### What the Implementation Reps Actually Ask (from the Gong transcripts)

The best reps (Keaton, Kristian, Fatima) follow a pattern:

1. **Start with business context** — "What kind of work do you do?" / "How many techs?" / "How does a job typically come in?"
2. **Walk the job lifecycle** — "Okay so the tech gets the call, then what?" / "After they arrive, what's the first thing they do?" / "What happens before they leave?"
3. **Probe on accountability** — "What's the one thing you want them to do every single time?" / "What do they keep forgetting?"
4. **Ask about documentation** — "Do they need to take photos?" / "Any forms or checklists?" / "Do they create the invoice in the field or does the office handle it?"
5. **Clarify roles** — "Who dispatches?" / "Does the tech create the job or does the office?"
6. **Edge cases** — "What if they need parts they don't have?" / "What about multi-day jobs?"

#### What Jaden's Review Revealed About Missing Information

These are the gaps that caused problems in the agent's output:

- **When does clock-in happen?** On the way? At arrival? The agent guessed wrong.
- **Should there be a customer notification text?** Not mentioned, but arguably best practice.
- **How many statuses is too many instructions?** The agent crammed 12 steps into one status.
- **Focus View preference** — defaulted to ON, should be OFF unless specified.
- **Multiple workflows** — customer talks about service AND install but agent can't separate them.
- **Form attachment** — customer mentions forms but agent can't attach specific ones.

---

### The Guided Chat Flow — Recommended Structure

Based on everything above, here's how the guided chat is structured. The Next.js app handles structured form phases (1 and 3) natively, and the AI-guided conversation (Phase 2) is powered by Claude API calls with the Discovery Agent system prompt.

#### Phase 1: Business Context (Structured — form fields, not conversation)

These are bounded questions with predictable answers. Don't waste conversation turns on them.

```
Fields:
- Company name (text)
- Industry (dropdown: HVAC, Plumbing, Electrical, Garage Door, General Contracting, Other)
- Company size (dropdown: 1-5 techs, 6-15, 16-50, 50+)
- What type of work is this workflow for? (text: "AC installation", "service calls", "drain cleaning", etc.)
```

These bounded fields collect the essential business context without burning conversation turns or tokens. The data is passed to Phase 2 as context for the Discovery Agent prompt, allowing the AI to tailor its questions to the customer's industry and scale.

#### Phase 2: Job Lifecycle Walk-Through (AI-guided conversation)

This is where the Discovery Agent prompt takes over, but within a structured flow that ensures coverage.

**Opening prompt (from the agent):**
> "Tell me how a typical [job type] goes from start to finish. Start from when your team first gets the job — how does it come in? Then walk me through what happens at each step until the job is completely done."

**The agent listens, then probes on these areas (in order):**

**2a. Job Intake & Dispatch**
- How does a job come in? (Phone call, text, customer portal, office creates it)
- Who creates the job? (Tech in the field vs. office/dispatch)
- Is there a scheduling step or does the tech go immediately?

**2b. On The Way / En Route**
- Should the customer be notified when the tech is heading out?
- Does anything need to happen between dispatch and arrival? (GPS tracking, send text, etc.)

**2c. Arrival & Start of Work**
- What's the first thing the tech does when they arrive?
- Do they clock in? If so, when exactly — on the way or at arrival?
- Any pre-work requirements? (Safety check, customer signature, before photos)

**2d. During the Work**
- What does the tech actually do? (Free text — let them describe)
- Any forms or checklists they need to fill out?
- Do they need to take photos? Before/after? Of what specifically?
- Do they create estimates or invoices on-site, or does the office handle it?
- What information do they need to see while working? (Customer info, job notes, equipment history, etc.)

**2e. Completion & Wrap-Up**
- What has to happen before the tech can mark the job complete?
- Customer signature required?
- Any cleanup, final photos, or documentation?
- Who handles the invoice — tech in the field or office?
- Payment collection on-site?

**2f. Edge Cases (the four core discovery questions)**
- "What's the one thing you're always reminding your team about?"
- "What do they keep forgetting to do?"
- "What if the tech needs parts they don't have on the truck?"
- "What if the customer isn't home?"
- "What if the job takes more than one day?"

#### Phase 3: Preferences & Guardrails (Structured)

```
Fields:
- How much freedom should your techs have? 
  (Guided: they only see buttons we create / Flexible: buttons + full app access)
  → This directly maps to Focus View restrict toggle. Default: Flexible (OFF).

- Should the system send a text to the customer when the tech is on the way?
  (Yes / No / Let me decide later)

- Do you have any existing forms or checklists in FieldPulse already?
  (Yes → which ones? / No / Not sure)
```

#### Phase 4: Confirmation & Handoff

The agent summarizes what it captured:

> "Here's what I've got for your [job type] workflow:
> 
> **Stages:** New → Scheduled → On The Way → In Progress → Complete → Invoice
> 
> **On The Way:** Send customer text, clock in
> **In Progress:** Take before photos, fill out [form name], do the work, take after photos
> **Complete:** Get customer signature, submit job notes
> **Invoice:** Office reviews and creates invoice
> 
> **Your preferences:** Guided mode (techs see only ClearPath buttons), customer text enabled
> 
> Does this look right? Anything I'm missing or that should be different?"

Then the structured report gets generated and sent to Agent 2.

---

### Question Framework — Quick Reference

For easy reference when building the Next.js app or refining the Discovery Agent prompt:

| Category | Key Questions | Maps To |
|----------|--------------|---------|
| **Business Context** | Industry, size, job type | Filtering for knowledge graph queries, complexity calibration |
| **Job Intake** | How does the job come in? Who creates it? | First status configuration, dispatch model |
| **En Route** | Customer notification? Clock in timing? | "On The Way" status buttons and instructions |
| **Arrival** | First thing at site? Pre-work requirements? | Arrival status, required actions before proceeding |
| **During Work** | What do they do? Forms? Photos? Estimates? | In Progress status, action buttons, widgets |
| **Completion** | What must happen before done? Signature? | Complete status, required actions |
| **Invoicing** | Tech or office? Payment on-site? | Invoice status, action buttons |
| **Edge Cases** | Parts needed? Multi-day? Customer absent? | Additional statuses, branching logic, instructions |
| **Preferences** | Guided vs. flexible? Auto-text? | Focus View toggle, default buttons |

---

### What to Pull from Implementation Reps (Jaden's Action Item)

When Jaden reviews implementation calls, she should look for:

1. **Questions that consistently uncover important details** — these go in the guided flow
2. **Questions that customers struggle to answer** — these need better framing or examples
3. **Things reps always add that customers don't mention** — these become suggested defaults
4. **Common misunderstandings** — these need clarification in the chat UI (tooltips, examples)
5. **The exact language reps use** — natural phrasing that customers respond well to

---

## Part 3: Implementation Plan

### Week 1: Build the Next.js Guided Chat App
1. Scaffold Next.js project with Tailwind CSS
2. Build Phase 1 UI (structured business context form)
3. Build Phase 2 UI (chat interface) + Claude API integration with Discovery Agent system prompt
4. Build Phase 3 UI (preferences form)
5. Build Phase 4 UI (confirmation/summary view) + webhook call to n8n

### Week 2: Test with Real Scenarios
1. Run CSS Mechanical narrative through the guided chat
2. Run Barnett narrative through it
3. Compare outputs to what the old n8n pipeline produced
4. Identify where the guided flow improved things vs. where gaps remain

### Week 3: Incorporate Jaden's Feedback
1. Integrate questions from implementation rep review
2. Refine pacing and probing behavior in the Discovery Agent prompt
3. Add suggested defaults (customer text, photo reminders)
4. Test with Wayside and 1st Choice scenarios

### Week 4: Present to Gabe + T
1. Side-by-side comparison: old pipeline output vs. guided chat output
2. Demo the guided chat experience
3. Discuss the "existing statuses → ClearPath" path as a future parallel track
4. Get alignment on next steps

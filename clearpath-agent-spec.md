# ClearPath AI Agent: Technical Specification

## Document Information
- **Project Name:** ClearPath AI Agent
- **Version:** 1.0
- **Date:** January 2026
- **Author:** Hamza / FieldPulse AI Automation Team

---

## 1. Executive Summary

### What We're Building
An AI-powered agent that converts natural language workflow descriptions into FieldPulse ClearPath import templates. The agent helps customers—especially smaller accounts unfamiliar with ClearPath—get a "starter" configuration instead of facing a blank canvas.

### Key Design Principle
> "The main use of AI here is to understand the natural language the user is using."

The LLM's job is **semantic understanding only**. Once the system understands what the user means, everything else (mapping to buttons, widgets, toggles, Excel generation) is **deterministic processing**.

### Success Criteria
- Customer provides workflow narrative → System outputs usable import template
- Output doesn't need to be 100% perfect—goal is "better than blank"
- Customer can refine the generated configuration in FieldPulse

---

## 2. Problem Statement

### The Customer Pain Point
New or smaller FieldPulse accounts struggle to set up ClearPath because:
1. They don't understand ClearPath terminology (status action flows, widgets, focus view)
2. They don't know what the 27 action buttons or 31 widgets do
3. The import template is intimidating (3 tabs, many columns)
4. They **do** know their workflow—they just can't translate it to FieldPulse's structure

### Current State
Customer knows: *"When my tech arrives, they clock in, text the customer, fill out the safety checklist, then start the work..."*

But they don't know how to turn that into:
- Status: "On Site"
- Action Buttons: Clock In, Send Customer Communication, Fill Form
- Widgets: Job Title, Customer Contact, Status Instructions, Action Buttons
- Toggles: Display Action Menu = True, Ability to Change Status = False

### Desired State
Customer describes their workflow in plain language → System generates a starter ClearPath import template they can refine.

---

## 3. Solution Overview

### Architecture Pattern: Semantic Core with RAG-Enhanced Knowledge

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLEARPATH AI AGENT                            │
│                                                                  │
│   [Natural Language Input]                                      │
│              │                                                   │
│              ▼                                                   │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │         SEMANTIC EXTRACTION            │   │
│   │                                                          │   │
│   │   • Extracts workflow steps                             │   │
│   │   • Identifies action phrases                           │   │
│   │   • Identifies information needs                        │   │
│   │   • Flags ambiguities                                   │   │
│   │                                                          │   │
│   │   Enhanced by: RAG retrieval from Knowledge Base        │   │
│   └─────────────────────────────────────────────────────────┘   │
│              │                                                   │
│              ▼                                                   │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │         KNOWLEDGE LOOKUP (Deterministic)                 │   │
│   │                                                          │   │
│   │   • Vector search: phrase → canonical action/widget     │   │
│   │   • Graph traversal: find related suggestions           │   │
│   └─────────────────────────────────────────────────────────┘   │
│              │                                                   │
│              ▼                                                   │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │         CONFIGURATION BUILDER (Deterministic)            │   │
│   │                                                          │   │
│   │   • Assembles complete ClearPath config                 │   │
│   │   • Applies defaults and best practices                 │   │
│   │   • Validates structure                                 │   │
│   └─────────────────────────────────────────────────────────┘   │
│              │                                                   │
│              ▼                                                   │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │         EXCEL GENERATOR (Deterministic)                  │   │
│   │                                                          │   │
│   │   • Outputs 3-tab Excel import template                 │   │
│   └─────────────────────────────────────────────────────────┘   │
│              │                                                   │
│              ▼                                                   │
│   [ClearPath Import Template (.xlsx)]                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Why This Architecture?

| Decision | Rationale |
|----------|-----------|
| RAG for domain knowledge | Keep prompt light, make knowledge maintainable |
| Knowledge graph for relationships | Enable inference ("if X, usually also Y") |
| Deterministic downstream processing | Predictable, testable, no LLM randomness |

---
```

### 4.2 Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| LLM | Claude API (Sonnet 4) | Cost-effective, good at structured extraction |
| Vector Store | Supabase + pgvector | Already used in Juju, familiar stack |
| Graph Store | Node4js |
| Excel Generation | openpyxl | Standard Python library for .xlsx |
| Schema Validation | Pydantic v2 | Type safety, JSON schema generation |
| API Framework | FastAPI (optional) | If exposing as service |

### 4.3 Data Flow

```
Step 1: INPUT
─────────────────────────────────────────────────────────────────
User provides natural language workflow description:
"When the tech gets to the job site, they need to clock in first,
then send the customer a text that they've arrived. They fill out
the safety inspection form, take before photos, then start work..."

Step 2: RAG RETRIEVAL
─────────────────────────────────────────────────────────────────
Query knowledge base with user's narrative.
Retrieve relevant context:
- Action button definitions
- Widget definitions
- Similar workflow patterns
- Best practices

Step 3: SEMANTIC EXTRACTION (LLM)
─────────────────────────────────────────────────────────────────
LLM receives: User narrative + Retrieved context
LLM outputs: Structured JSON with extracted intent

{
  "workflow_name": "Service Call",
  "steps": [
    {
      "name": "On Site",
      "sequence": 1,
      "actions_mentioned": [
        {"phrase": "clock in", "confidence": 0.95},
        {"phrase": "send the customer a text", "confidence": 0.90},
        {"phrase": "fill out the safety inspection form", "confidence": 0.92},
        {"phrase": "take before photos", "confidence": 0.88}
      ],
      "information_needs": [
        {"phrase": "customer contact", "inferred": true}
      ]
    }
  ]
}

Step 4: KNOWLEDGE LOOKUP (RAG LLM)
─────────────────────────────────────────────────────────────────
For each extracted phrase, find canonical match:
- "clock in" → vector search → "action:clock_in_job" (0.94 similarity)
- "send the customer a text" → "action:send_customer_communication" (0.91)
- "safety inspection form" → "action:fill_form" (0.89)
- "take before photos" → "action:take_photo" (0.93)

Graph traversal for suggestions:
- "send_customer_communication" → suggests → "widget:customer_contact"
- "fill_form" → typically_paired → "action:take_photo"

Step 5: CONFIGURATION BUILD (Deterministic)
─────────────────────────────────────────────────────────────────
Assemble complete config with defaults:

{
  "workflow_name": "Service Call",
  "status_action_flow_name": "Service Call Flow",
  "statuses": [
    {
      "name": "On Site",
      "user_role": "Service Agent",
      "action_buttons": [
        {"action": "Job Timesheet Clock in / out", "label": "Clock In"},
        {"action": "Send Customer Communication", "label": "Send Arrival Text"},
        {"action": "Fill Form", "label": "Safety Inspection"},
        {"action": "Take Photo", "label": "Take Before Photos"}
      ],
      "widgets": ["Job Title", "Job Status", "Status Instructions", 
                  "Customer Contact", "Forms", "Files/Photos", "Action Buttons"],
      "status_instructions": "1. Clock in\n2. Send arrival text\n3. Complete safety inspection\n4. Take before photos",
      "display_action_menu": true,
      "ability_to_change_status": false,
      "focus_view_enabled": true,
      "restrict_to_focus_view": false
    }
  ]
}

Step 6: EXCEL GENERATION (Deterministic)
─────────────────────────────────────────────────────────────────
Transform config → 3-tab Excel import template

Tab 1: Job Custom Status (if creating new workflow)
Tab 2: Action Buttons (one row per button per status per role)
Tab 3: Focus View + Status Instructions (one row per status per role)
```
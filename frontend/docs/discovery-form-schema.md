# ClearPath Discovery — Form Schema Review

> **For PM review.** This document lists every field in the discovery form schema. The schema drives two things:
> 1. **During chat** — the LLM sees these fields (with types and options) and extracts answers from the conversation
> 2. **After chat (or instead of chat)** — the customer reviews a pre-filled form with these fields and can edit anything before report generation
>
> To change what gets asked or how it's answered, update this schema. The rest of the system adapts automatically.
>
> **New:** Users can now choose to skip the chat and fill the form directly.

---

## 1. Job Intake

*How jobs come in, who creates them, scheduling*

| # | Question | Type | Required | Options |
|---|----------|------|----------|---------|
| 1 | Where do jobs come from? | Multi-select | Yes | Phone calls, Online booking, Referrals, Office dispatch, Text/SMS, Customer portal |
| 2 | Who creates the job in the system? | Dropdown | Yes | Office / dispatcher, Technician in field, Both, Auto-created from booking |
| 3 | Is there a scheduling step before dispatch? | Yes / No | No | — |

---

## 2. En Route

*Between dispatch and arrival at the job site*

| # | Question | Type | Required | Options |
|---|----------|------|----------|---------|
| 4 | Notify the customer when the tech is on the way? | Yes / No | Yes | — |
| 5 | When does the tech clock in? | Dropdown | Yes | Before driving to job, When they arrive on site, No clock-in required |
| 6 | GPS tracking needed for drive time? | Yes / No | No | — |
| 7 | Do you confirm the appointment with the customer? | Yes / No | No | — |

---

## 3. Arrival

*First actions when the tech arrives on site*

| # | Question | Type | Required | Options |
|---|----------|------|----------|---------|
| 8 | What's the first thing the tech does on site? | Dropdown | Yes | Meet the customer, Take before photos, Safety check / site assessment, Confirm scope of work, Check in / announce arrival |
| 9 | Pre-work requirements before starting | Checkboxes | No | Before photos, Safety check, Customer signature / authorization, Site assessment form |

---

## 4. During Work

*What happens while the tech is working on the job*

| # | Question | Type | Required | Options |
|---|----------|------|----------|---------|
| 10 | Are forms or checklists required during the job? | Yes / No | Yes | — |
| 11 | Photo requirements during the job | Dropdown | Yes | Before & after photos, Before photos only, After photos only, Progress photos throughout, No photos required |
| 12 | Do techs create estimates or invoices on site? | Dropdown | No | Estimates on site, Invoices on site, Both estimates and invoices, Office handles these |
| 13 | What info does the tech need to see during the job? | Multi-select | No | Job details / description, Customer contact info, Job / equipment history, Parts / materials list, Job notes, Forms / checklists, Photos / files |
| 14 | Can techs create estimates for new work while on site? | Yes / No | No | — |
| 15 | Where do assets get logged? | Dropdown | No | Installing new equipment, Connecting existing assets, Both, No assets |
| 16 | Can the tech swipe out of Focus View? | Yes / No | No | — |
| 17 | Can the tech change status from the action button? | Yes / No | No | — |

---

## 5. Completion

*Wrapping up the job — signatures, invoicing, payment*

| # | Question | Type | Required | Options |
|---|----------|------|----------|---------|
| 18 | What must happen before the job can be marked complete? | Checkboxes | Yes | After photos, Customer signature, Completion notes, Form / checklist submitted, Invoice created |
| 19 | Who handles invoicing? | Dropdown | Yes | Tech creates invoice on site, Office creates invoice after, Auto-generated from estimate |
| 20 | Is payment collected on site? | Yes / No | No | — |
| 21 | Customer signature required at completion? | Yes / No | No | — |
| 22 | Should invoicing be a separate status stage? | Dropdown | No | Same status as work completion, Separate invoicing status, Office handles invoicing separately |

---

## 6. Edge Cases & Pain Points

*What goes wrong, what frustrates your team*

| # | Question | Type | Required | Options |
|---|----------|------|----------|---------|
| 23 | What steps do techs commonly forget? | Free text | No | — |
| 24 | What happens when parts aren't available? | Dropdown | No | Go to supply house, Order parts / reschedule, Swap from another truck, Other |
| 25 | What happens when the customer isn't there? | Dropdown | No | Call and wait, Leave a note / move on, Reschedule the job, Start work anyway |

> **Note:** "Forgotten steps" answers translate to **status instructions** (e.g., "Don't forget to upload the photo"), not new statuses.

---

## 7. Workflow Preferences

*General preferences and existing setup — only shown in form review, not during chat*

| # | Question | Type | Required | Options |
|---|----------|------|----------|---------|
| 26 | Existing forms or checklists in FieldPulse | Free text | No | — |
| 27 | Are your technicians Spanish-speaking? | Yes / No | No | — |

---

## Changes from Previous Version

**Added (from Keaton's feedback):**
- #7: Appointment confirmation (en route)
- #14: Estimate creation during service (during work)
- #15: Asset logging (during work)
- #16-17: Focus View / status change toggles — split from old "How much freedom should techs have?" (moved from Preferences to During Work so the AI can discover them)
- #22: Invoice separation (completion)
- #28: Spanish-speaking techs (preferences)

**Removed:**
- "How much freedom should techs have?" — replaced by two specific toggles (#16, #17)
- "Text customer when tech is on the way?" — redundant with #4 (customer notification)
- "What do techs keep forgetting to do?" — merged into "What steps do techs commonly forget?" (same intent, one field)

**Renamed:**
- "Common mistakes or recurring issues" → "What steps do techs commonly forget?" — clarifies these become instructions, not statuses

---

## Summary

- **Total fields:** 27
- **Required fields:** 10 (filled by the LLM during chat)
- **Optional fields:** 17 (filled if mentioned, otherwise left for form review)
- **Sections 1–6** are targeted by the LLM during the discovery conversation
- **Section 7 (Preferences)** is only shown in the form review — the LLM doesn't fill these

### Field type guide

| Type | What the customer sees |
|------|----------------------|
| **Dropdown** | Pick one option from a list |
| **Multi-select** | Pick one or more options (toggle buttons) |
| **Checkboxes** | Select all that apply (vertical list) |
| **Yes / No** | Two-button toggle |
| **Free text** | Open text input or textarea |

# ClearPath Discovery Agent
**Actionable Updates from Stakeholder Feedback**
February 24, 2026

---

## 1. Keaton's Form Feedback

Keaton validated that the current discovery form covers the majority of what an implementation specialist would expect on a first pass. He gave specific additions and refinements across several areas. Below is every piece of feedback and the context behind it.

### 1.1 New Questions to Add

| Feedback Item | Details / Context |
|---|---|
| **Appointment Confirmation** | "Do you confirm the appointment with the customer?" If yes, this typically results in an extra workflow step or an automation (e.g., a customer communication or text notification). |
| **Invoice Separation** | Does the "in progress" status contain all billing (invoice creation, payment collection), or should invoicing be a separate status stage? Keaton says this is roughly 50/50 among customers. Some want a dedicated "Invoicing" or "Bill from Office" or "No Payment Collected" status for office follow-up. |
| **Estimate Creation During Service** | Very common scenario: tech is on-site doing service work and the customer says "while you're here, can you quote me on something else?" This means the tech needs to create an invoice for the current work AND create an estimate for the new request. Usually results in two buttons in the in-progress status. |
| **Assets** | Where do assets get logged? Always during in-progress. Two scenarios: (1) installing new equipment (e.g., water heater) that needs to be added as an asset, or (2) tech arrives and discovers an existing asset in the system that needs to be connected to the job. |

### 1.2 Existing Questions to Revise

| Feedback Item | Details / Context |
|---|---|
| **Technician Freedom / Focus View** | The current single question about "how much freedom should the tech have" is confusing. It actually covers two separate FieldPulse toggles: (1) Can the tech swipe out of focus mode? (2) Can the tech change status from the action button? These are independent settings. Keaton says almost all customers want techs locked into focus view. |
| **Common Mistakes / Forgetting Steps** | The question "What are the techs' most common mistakes?" is vague. Keaton says this translates primarily to status instructions (e.g., "Don't forget to upload the photo before moving to the next step"). It does NOT translate to subtasks or new statuses. |

### 1.3 Agent Logic Updates

| Feedback Item | Details / Context |
|---|---|
| **Status vs. Instruction Distinction** | The agent sometimes turns every detail a customer mentions into a new status step, when many things should just be instructions within an existing status. Keaton's example: a customer wanted "boot covers" as part of their workflow. That's an instruction ("Put on boot covers before entering the home"), not a workflow stage. This was echoed later in Meeting 2 as a top concern from Addie and Ti. |
| **Status Count Control** | Some outputs had 15+ statuses which is unusable. Others were too broad with only 3. Typical workflows should land in the 5–10 status range. |
| **Module Dependency Awareness** | The agent doesn't account for whether features like purchase orders or materialist are actually turned on in the customer's FieldPulse account. Example: a customer said purchase orders are critical, but the generated workflow didn't include PO actions because the module wasn't enabled. Keaton suggested testing: turn on the module, re-run the same transcript, and compare outputs. |

---

## 2. ClearPath Template Context

Ti and Jaden have been building standardized ClearPath workflow templates by industry. Understanding what they've built and how the agent can leverage these templates is critical for improving output quality.

### 2.1 What the Templates Are

The team has created pre-built ClearPath workflow configurations for common industry use cases (HVAC, plumbing, electrical, etc.). These templates represent what the team considers best-practice workflows based on patterns they've seen across many customer implementations. They are importable via the existing ClearPath import into master, which is the same import mechanism the agent's output uses.

### 2.2 How They're Being Used Today

- Ti has been selectively importing templates into customer accounts, but not blindly. She imports only what makes sense for each customer because you cannot delete workflows once imported (only deactivate). Importing irrelevant workflows frustrates customers.
- Jaden is incorporating templates into the onboarding app (details TBD from a separate meeting).
- Marketing is using the same workflows for content creation, so there's an effort to standardize the language and structure across teams.
- Sales (Zach) wants these same templates available in demo accounts so prospects see consistent examples. Currently demo accounts are messy with test data from multiple reps.

### 2.3 How to Integrate Templates with the Agent

There are several ways the agent could leverage these templates:

- **Use templates as training data:** You've already trained the agent on high-usage customer ClearPath configurations and Ashley's training materials. Adding Ti/Jaden's curated templates as additional reference models would give the agent a clearer picture of what "good" looks like for each industry.
- **Template suggestion mode:** Based on the customer's industry and answers, the agent could suggest a specific template as a starting point, then customize from there. This could significantly reduce hallucinated status steps since the agent would be working from a vetted baseline.
- **Template-driven form branching:** If a template is selected, the form could surface additional questions specific to that template's configuration options rather than asking everything from scratch.

### 2.4 What to Get from Ti/Jaden

To move forward on template integration, you need the following from their project:

- The actual template files (ClearPath Excel imports) for each industry they've built
- The rationale behind key decisions in each template (why certain statuses exist, why certain actions are in certain stages) so the agent can explain its suggestions
- Which templates they consider most stable/validated vs. still in progress
- Any template variations within the same industry (e.g., residential vs. commercial HVAC)

---

## 3. Customer Language Extraction

This was one of Keaton's strongest pieces of feedback and was reinforced in Meeting 2. The agent currently generates output in FieldPulse's internal terminology, but customers and their technicians use their own language. The agent needs to capture and use the customer's actual words.

### 3.1 The Problem

FieldPulse has its own vocabulary for statuses, actions, and buttons (e.g., "En Route", "In Progress", "Complete Job"). Customers describe the same concepts in completely different terms. When the agent generates a ClearPath config using FieldPulse's default terminology, the technicians who actually use the mobile app don't recognize what the buttons mean. Implementation specialists currently spend significant time manually translating.

Examples Keaton gave:

- "Clock in" → the customer says this, but FieldPulse calls it "Start"
- "Complete job" → the customer might say "Finish" or "Done"
- "En Route" → the customer might say "On the way" or "Heading out"
- Status instructions are often needed in Spanish because many technicians are Spanish-speaking

### 3.2 What Needs to Happen in the Agent

**Language Detection During Transcript Processing:** When the agent processes a gong transcript, it should actively identify and extract the customer's own terminology for workflow concepts. Build a terminology mapping as part of the transcript analysis phase, before generating any ClearPath configuration. This mapping should capture: what the customer calls each phase of work, what words they use for actions their techs take, any industry-specific jargon, and whether they reference their techs using Spanish terms or indicate Spanish is their techs' primary language.

**Apply Customer Language to Output:** Once the terminology mapping exists, use it when generating: button labels (rename default FieldPulse button names to the customer's terms), status names, status instructions (write these in the customer's voice, not FieldPulse's documentation voice), and action flow descriptions.

**Spanish Language Support:** Add a question to the form: "Are your technicians Spanish-speaking?" If yes, generate bilingual button labels using the single-button-with-slash format that's already standard practice (e.g., "Start / Iniciar", "Finish / Terminar"). Status instructions should also be written in Spanish or bilingual depending on the customer's preference. Keaton confirmed this is very common — he gave the example of doing an entire implementation in English and then having to hand off to a Spanish-speaking trainer (Fatima) because none of the techs spoke English.

### 3.3 Testing This

When you run your next batch of transcript tests, evaluate each output for language alignment. For each transcript, check: Does the output use the customer's words or FieldPulse defaults? Are button labels recognizable to someone who only heard the customer's description? If the customer mentioned Spanish-speaking techs, did the output generate bilingual labels? Create a simple scorecard column for "language alignment" in your test tracking.

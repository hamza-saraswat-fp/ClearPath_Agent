# ClearPath Test Scenario: 101 Technologies

## Scenario Brief

| Field | Detail |
|-------|--------|
| **Company** | 101 Technologies |
| **Industry** | Technology Installation — Hospitality (hotel systems) and Lottery (terminal/equipment deployment) |
| **Location** | Multi-state operations — currently active in Illinois, with upcoming projects in Texas, Minnesota, Missouri, Colorado, Indiana (Dallas and Indianapolis for service starting April 1) |
| **Company Size** | ~50 users. Core admin team: Mikel (owner), Jennifer (office manager/operations backbone), Dan Taylor (lottery project manager), Caleb/Jonathan (hospitality project manager). Field workforce is primarily 1099 contractors, not W-2 employees. |
| **Job Types** | Two completely distinct workflows: (1) Hospitality — hotel technology installations (long-duration, travel-based, multi-day projects with formal SOW and closeout). (2) Lottery — high-volume terminal/equipment deployments (5-6,000 sites in ~50 days, fast-moving, data-heavy with QA process). Also launching a service division in April (Dallas and Indianapolis). |
| **Current Tools** | Fuse (two versions — Fuse Lottery with dashboard, Fuse Hotel without dashboard), Monday.com (used as dashboard replacement for hospitality), QuickBooks Online (invoicing — no sync with Fuse). Fuse has major pain points: developer dependency for all setup/changes/imports (sent request Monday, crickets for weeks), buggy mobile app (iOS requires backdoor install, newest Android versions incompatible — Mikel bought cheap Amazon phones as workarounds). |
| **Key Pain Points** | Three separate systems to track work — wants everything under one hood. Developer bottleneck with Fuse (can't self-manage templates, imports, or project setup). Mobile app compatibility issues forcing hardware workarounds. Photo export limitations (currently must download all photos, put in OneDrive, send to customer). Need for real-time data collection and daily reporting from techs. Efficiency is the #1 goal. |
| **Dispatch Model** | Varies by division. Hospitality: office creates project → assigns tech → books travel → tech flies to site for multi-day install. Lottery: import site list → assign techs by geography using mapping software → techs self-sequence their jobs (1 through 250) → Dan builds weekly schedules for customer → techs schedule day-of from their sequence. |
| **Contractors** | Field techs are 1099 contractors, not employees. Need to track contractor payments per job separately from customer invoicing. |
| **Source Transcript** | 101Technologies<>FieldPulse \| Kick-off Call!!! — Feb 11, 2026, 51 min. Keaton Crume & Matt Eldredge (Internal) with Mikel Longe (President), Jonathan Rader, Dan Taylor, Jennifer Williams (External). |

---

## Customer Narrative — Hospitality Division

> For our hospitality work, we do hotel technology installations. Here's how a project flows from start to finish.
>
> We receive a job — usually a project scope or plan from the customer. We bid on it. If we win the bid, we mark it accordingly. If we lose it, we track that too. Once we win a project, we put it on the schedule.
>
> All the documentation for that job gets uploaded — everything we've received via email goes into that job record. Then we create a Statement of Work for the technician. This is a new process we started this year — Jennifer sends out the SOW to the tech, and I require them to sign it acknowledging that they accept the current terms and conditions. They sign it and send it back to us. So everything lives in the job at that point.
>
> Then we book travel for the tech — they're flying to the hotel site. The tech arrives on day one and does inventory. If anything's missing, they let us know and we either order the parts or get with the customer about what we need.
>
> Sometimes we have to do what's called a golden room sign-off. That's where we set up one room completely — do speed tests and some extra verification items to make sure everything's working for that particular room. We have the hotel manager or our point of contact sign off on that golden room. That requires a signature and can be done hopefully through the system.
>
> Then the tech goes about the daily install work. Every day, we require a daily report to be sent in by the technicians. Right now that's an email form, and we hound them constantly — "don't forget, don't forget" — because our tech has to send the dailies to our customer, and then the customer often forwards them to whoever their point of contact is, hotel ownership, whatever.
>
> The install goes through however many days it takes. At the end of the install, we do a review with the tech before they leave site. We verify: do you have X, Y, and Z paperwork done? Yes. We verify all the installation numbers with them. Did you have anything out of the ordinary that we don't know about that wasn't on your SOW? Yes, no, maybe. We mark that down. And if there was anything extra, we should have a list in real time of any extras that weren't on the SOW.
>
> Once everything's signed off, we release the technician. We book travel for the tech to fly out. Then Jennifer takes the closeout notes from that job and invoices — bill X, Y, and Z. She bills it, we mark it as completed, and it's done.
>
> One thing that's important — sometimes documentation needs to be shared with the customer during the project. Right now I have to download all the photos, put them into a OneDrive, and send them to the customer. I need a better way to share that.

---

## Customer Narrative — Lottery Division

> For lottery, it's a completely different animal. It's fast-moving and project-oriented. Communication is key and data is really key with our daily reports and the data we have to collect on certain jobs.
>
> Right now we've got Texas, Minnesota, and Missouri to kick off. Between the three states, we have probably five to six thousand sites that we'll do in about 50 days. That's how fast-moving lottery is.
>
> Here's how it works. We get a site list from the customer. We import that into our system. Then I go through and map everything out with our mapping software — I assign techs to geographic areas. Once techs are assigned their jobs, they give me a sequence number for each one. So if a tech has 250 jobs, they list them in order, one through 250, how they're going to do them.
>
> Dan then looks at that and says okay, you're going to do an average of 20 a week. He builds a weekly schedule and sends it to our customer so the lottery service representatives can let their retailers know — "hey, your store is going to be visited this week by a technician, be on the lookout."
>
> Once we have a date for it, the tech goes in and schedules their jobs day-of from their sequence. They might have five jobs scheduled for that day. They go to job one, complete the tasks that are in that job.
>
> For a normal lottery install, we have term packs associated with each job. A T1 could be a terminal and a printer and a cradle point. A T2 could be a terminal, a printer, a cradle point, and a ticket checker. A T3 could add a digital signage screen. A T4 could add more. So the term packs define what equipment is at each site. That doesn't always mean that's exactly what happens, but we list out the parts.
>
> There's also information the techs need for each job that we upload ahead of time — like a unique number for programming the cradle point, a unique number for programming the terminal. All this data is pre-loaded when we import the jobs.
>
> The tech completes the job and changes the status to complete. That same evening, my QA person Val comes in and reviews the job. She checks — "hey Art, you're missing a serial number for this, you're missing a serial number for that, did you do this?" If no QA is needed, she marks it as QA'd and that job is done.
>
> The following Monday, I come in and grab everything that was completed the previous week. I put in my invoice number for that job, the date it was invoiced, and send it off to the customer. I track the invoice number and date so I don't double-bill. Then later that week, I go through the contractors — they're all 1099s — and I do the same thing for their pay. They get paid this amount for this job, I mark it as paid, and upload that. Then the job is truly done.
>
> We use QuickBooks Online for the actual invoicing — the tracking in our system is so we don't double-bill or double-pay. The two systems don't talk to each other at all right now.

---

## Customer Narrative — Service Division (Upcoming)

> Starting April first, I'm also launching a service division in Dallas and Indianapolis. So on top of the project-based install work for hospitality and lottery, we'll also need to handle ongoing service calls. I haven't gotten deep into that workflow yet, but it needs to be part of the same system — everything under one hood.

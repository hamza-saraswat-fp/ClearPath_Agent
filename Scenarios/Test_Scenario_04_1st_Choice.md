# ClearPath Test Scenario: 1st Choice Heating & Cooling

## Scenario Brief

| Field | Detail |
|-------|--------|
| **Company** | 1st Choice (Heating & Cooling — implied from furnace tune-ups, HVAC maintenance agreements) |
| **Industry** | Residential HVAC |
| **Company Size** | Medium — Phil (owner/manager), Dan (sales), Brenda and Julia (dispatch/admin), plus field technicians. Migrating from ServiceTitan. |
| **Job Types** | Service calls, furnace tune-ups, maintenance agreements (semi-annual, seasonal — furnace in spring, A/C in summer). Different job types need different workflows. |
| **Current Tools** | Migrating from ServiceTitan. Cleaning up ServiceTitan PriceBook for Excel import into FieldPulse. |
| **Key Pain Points** | Need to establish an internal SOP around the new system. Dispatchers (Brenda, Julia) need to figure out how to work with tags, scheduling, and the dispatch board. Different job types (furnace tune-up vs. service call) need different workflow statuses. Need to track estimate follow-ups — know when a customer has declined an estimate so they can reference it when they call back. Maintenance agreements need custom seasonal scheduling (not just fixed intervals) because Wisconsin weather doesn't follow 6-month cycles. |
| **Dispatch Model** | Office-dispatched. Jobs created → put on schedule unassigned → dispatchers assign to techs. Use both calendar view and horizontal dispatch view. Dispatchers can drag jobs onto technician schedules, use "find availability" tool, and filter unassigned jobs by status (e.g., "needs to be scheduled"). |
| **Workflow Design** | Multiple workflows needed — furnace tune-up has different steps than a service call. Statuses map to time tracking categories: travel time (on the way), in progress (contributes to job duration), pending (pauses the clock — e.g., waiting on parts). Want statuses like "needs to be scheduled" in the pending bucket so unscheduled jobs are easy to filter and track. |
| **Estimate Process** | Sales team creates estimates. Customers can accept or decline. Team needs visibility into which estimates are outstanding, which are sold (have the invoice indicator icon), and which were affirmatively declined. Previously in ServiceTitan, customers could formally reject/decline estimates. |
| **Maintenance Agreements** | Recurring service plans with seasonal scheduling. In Wisconsin, furnace tune-up might be in March/April, A/C tune-up in June — not exactly 6 months apart. Need custom frequency per customer with automated reminders (email to customer and/or office) X days before service is due. Monthly membership billing handled separately through recurring billing. |
| **Source Transcript** | FieldPulse \| 1st Choice - Check In/Refresher for Dispatch & Admin — Jan 23, 2025, 51 min. Keaton Crume (Internal) with Phil Lorum, Julia Grennell, Brenda Paulus, Jessica Grennell (External). Call ID: 6142501124148491255 |

---

## Customer Narrative

> We're 1st Choice. We're an HVAC company out of Wisconsin, coming over from ServiceTitan. We've got a dispatch team — Brenda and Julia handle scheduling and dispatch — plus sales guys and field technicians.
>
> What we need to figure out is our internal workflow around this system. How should we be working with tags, scheduling, the dispatch board, and getting jobs assigned to technicians? We need an SOP that everyone follows.
>
> The basic flow is: a call comes in, we create a work order, and it goes on the schedule. Sometimes we create it and leave it unassigned — like we queue up 10 jobs and come back later to figure out who's available. We use a mix of the calendar view and the dispatch view. Some of us like the calendar, some like seeing things horizontally on the dispatch board.
>
> The key thing is we need different workflows for different job types. A furnace tune-up has different steps than a service call. So we'd want separate workflow statuses for each type. When we create a work order, we pick which workflow applies to that job.
>
> For the statuses themselves, we're thinking about things like "needs to be scheduled" — that way we can filter and see all the jobs sitting in that status that still need to get on someone's calendar. We also want something like "waiting on parts" which would pause any time tracking. And the usual on the way, in progress, completed.
>
> The dispatch notes are important — that's the scope of work that goes to the technician. It's read-only for them. Then the field notes are what the tech fills in while they're at the job. Those are separate.
>
> On estimates — our sales team creates them and sends them to customers. We need to know when a customer has affirmatively declined an estimate, not just ignored it. In our old system, they could formally reject it. That way when they call back months later, we can say "well, you had an estimate out there and didn't go along with it." We need to be able to filter our estimate list by status — show me the sold ones, the pending ones, the declined ones.
>
> We also do maintenance agreements. The tricky thing in Wisconsin is that seasonal timing doesn't always line up with neat 6-month intervals. A customer might want their A/C tune-up in June but their furnace tune-up in March or April. So we need custom scheduling per customer — pick the specific months, not just "every 6 months." And we want automated reminders going out to the customer and to us, like 30 days before service is due, so we can proactively schedule it.
>
> Phil's going to take Dan through the sales side separately. For now, the priority is getting Brenda and Julia comfortable with dispatching and building out our workflows so we have a consistent process for everyone to follow.

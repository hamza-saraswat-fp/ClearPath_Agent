import type { CoverageAreaId, CoverageStatus, CoverageDataPoints } from "@/types/discovery";

// ============================================================
// Coverage Area Definitions
// Behind-the-scenes checklist for what the conversation must cover
// ============================================================

export interface CoverageAreaDefinition {
  id: CoverageAreaId;
  label: string;
  description: string;
  requiredDataPoints: string[];
  optionalDataPoints: string[];
}

export const COVERAGE_AREAS: CoverageAreaDefinition[] = [
  {
    id: "intake",
    label: "Job Intake",
    description: "How jobs come in, who creates them, scheduling",
    requiredDataPoints: ["job_source", "job_creator"],
    optionalDataPoints: ["info_captured_at_intake", "scheduling_model"],
  },
  {
    id: "en_route",
    label: "En Route",
    description: "Between dispatch and arrival",
    requiredDataPoints: ["customer_notification", "clock_in_timing"],
    optionalDataPoints: ["travel_tracking"],
  },
  {
    id: "arrival",
    label: "Arrival",
    description: "First actions on site",
    requiredDataPoints: ["first_action"],
    optionalDataPoints: ["pre_work_requirements"],
  },
  {
    id: "during_work",
    label: "During Work",
    description: "The actual work — forms, photos, parts, time",
    requiredDataPoints: ["work_description", "photo_requirements"],
    optionalDataPoints: ["forms_checklists", "parts_materials", "time_tracking", "estimates_or_invoices_onsite", "info_needed_on_screen"],
  },
  {
    id: "completion",
    label: "Completion",
    description: "Wrapping up — signature, handoff, invoice, payment",
    requiredDataPoints: ["completion_requirements", "invoice_process"],
    optionalDataPoints: ["signature", "handoff_to_office", "payment_collection"],
  },
  {
    id: "edge_cases",
    label: "Edge Cases",
    description: "Pain points — mistakes, frustrations, the unexpected",
    requiredDataPoints: ["common_mistakes", "management_frustrations"],
    optionalDataPoints: ["parts_not_available", "customer_absent", "multi_day_jobs", "multiple_job_types"],
  },
];

/**
 * Determine coverage status for a single area based on its filled data points.
 */
export function getAreaCoverageStatus(
  areaId: CoverageAreaId,
  dataPoints: CoverageDataPoints
): CoverageStatus {
  const areaDef = COVERAGE_AREAS.find((a) => a.id === areaId);
  if (!areaDef) return "uncovered";

  const areaData = dataPoints[areaId];
  if (!areaData) return "uncovered";

  // Check if ANY field (required or optional) has data
  const allFields = [...areaDef.requiredDataPoints, ...areaDef.optionalDataPoints];
  const filledAny = allFields.some((key) => {
    const val = (areaData as Record<string, unknown>)[key];
    return val !== undefined && val !== null && val !== "";
  });

  if (!filledAny) return "uncovered";

  // Check if ALL required fields are filled for "covered"
  const filledRequired = areaDef.requiredDataPoints.filter((key) => {
    const val = (areaData as Record<string, unknown>)[key];
    return val !== undefined && val !== null && val !== "";
  });

  if (filledRequired.length >= areaDef.requiredDataPoints.length) return "covered";
  return "partial";
}

/**
 * Get the count of covered areas (for progress bar).
 */
export function getCoveredCount(dataPoints: CoverageDataPoints): number {
  return COVERAGE_AREAS.filter(
    (area) => getAreaCoverageStatus(area.id, dataPoints) === "covered"
  ).length;
}

/**
 * Get all uncovered or partially covered areas (for follow-up targeting).
 */
export function getUncoveredAreas(dataPoints: CoverageDataPoints): CoverageAreaDefinition[] {
  return COVERAGE_AREAS.filter(
    (area) => getAreaCoverageStatus(area.id, dataPoints) !== "covered"
  );
}

/**
 * Check if all areas are sufficiently covered to proceed to assembly.
 */
export function isDiscoveryComplete(dataPoints: CoverageDataPoints): boolean {
  return COVERAGE_AREAS.every(
    (area) => getAreaCoverageStatus(area.id, dataPoints) === "covered"
  );
}

/**
 * Get quick-select options relevant to the first uncovered area.
 */
export function getQuickSelectsForNextArea(
  dataPoints: CoverageDataPoints
): { label: string; value: string }[] {
  const uncovered = getUncoveredAreas(dataPoints);
  if (uncovered.length === 0) return [];

  const nextArea = uncovered[0];

  const quickSelectMap: Record<CoverageAreaId, { label: string; value: string }[]> = {
    intake: [
      { label: "Phone/text from customer", value: "Customer calls or texts us directly" },
      { label: "Office dispatches", value: "Office creates the job and dispatches the tech" },
      { label: "Tech creates in field", value: "Tech creates it themselves on their phone" },
    ],
    en_route: [
      { label: "Text the customer", value: "We send the customer a text when the tech is on the way" },
      { label: "No notification", value: "No notification — customer already knows they're coming" },
    ],
    arrival: [
      { label: "Take before photos", value: "First thing is take before photos" },
      { label: "Meet the customer", value: "Meet the customer and confirm the scope" },
      { label: "Safety check", value: "Do a safety check or site assessment" },
    ],
    during_work: [
      { label: "Before & after photos", value: "They take before and after photos" },
      { label: "Fill out forms", value: "They fill out forms or checklists during the job" },
      { label: "Create estimate on site", value: "Tech creates the estimate on site" },
    ],
    completion: [
      { label: "Customer signature", value: "Customer has to sign off before we're done" },
      { label: "Office handles invoicing", value: "Office reviews the work and creates the invoice" },
      { label: "Tech collects payment", value: "Tech collects payment on site" },
    ],
    edge_cases: [
      { label: "Techs forget stuff", value: "Techs keep forgetting to fill out paperwork or take photos" },
      { label: "Parts not on truck", value: "If they need parts they don't have, they go to the supply house and come back" },
    ],
  };

  return quickSelectMap[nextArea.id] || [];
}

"use client";

import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import {
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
} from "lucide-react";
import {
  FORM_SCHEMA,
  getSectionProgress,
  getFormProgress,
  isFieldFilled,
} from "@/lib/form-schema";
import type { FormState, FormFieldValue } from "@/lib/form-schema";
import type { BusinessContext } from "@/types/discovery";
import { buildOpeningMessage } from "@/lib/prompts";
import { FormField } from "./FormField";

interface FormReviewProps {
  formState: FormState;
  onSubmit: (formState: FormState) => void;
  isSubmitting: boolean;
  isFormDirect?: boolean;
  businessContext?: BusinessContext | null;
}

export function FormReview({
  formState,
  onSubmit,
  isSubmitting,
  isFormDirect = false,
  businessContext,
}: FormReviewProps) {
  const [localState, setLocalState] = useState<FormState>(() => ({
    ...formState,
  }));
  const [narrativeStages, setNarrativeStages] = useState("");
  const [narrativeDetails, setNarrativeDetails] = useState("");

  const allSectionIds = useMemo(
    () => FORM_SCHEMA.map((s) => s.id),
    []
  );
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    () => new Set(allSectionIds)
  );

  const progress = getFormProgress(FORM_SCHEMA, localState);

  const handleFieldChange = (fieldId: string, value: FormFieldValue) => {
    setLocalState((prev) => ({ ...prev, [fieldId]: value }));
  };

  const toggleSection = (sectionId: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(sectionId)) {
        next.delete(sectionId);
      } else {
        next.add(sectionId);
      }
      return next;
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;
    const submitState: FormState = { ...localState };
    if (narrativeStages.trim()) submitState._narrative_stages = narrativeStages.trim();
    if (narrativeDetails.trim()) submitState._narrative_details = narrativeDetails.trim();
    onSubmit(submitState);
  };

  const sectionVariants = {
    hidden: { opacity: 0, y: 16 },
    visible: (i: number) => ({
      opacity: 1,
      y: 0,
      transition: { duration: 0.35, delay: i * 0.08, ease: "easeOut" as const },
    }),
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="w-full max-w-2xl mx-auto py-8 px-4"
    >
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-foreground mb-2">
          Review Your Workflow
        </h2>
        <p className="text-muted text-[15px]">
          Review the details we captured and fill in anything we missed.
        </p>
      </div>

      {/* Progress bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="text-muted">
            {progress.requiredFilled}/{progress.requiredTotal} required fields
            captured
          </span>
          {progress.requiredFilled === progress.requiredTotal ? (
            <span className="flex items-center gap-1 text-green-600 text-xs font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" />
              All required filled
            </span>
          ) : (
            <span className="flex items-center gap-1 text-amber-600 text-xs font-medium">
              <AlertCircle className="w-3.5 h-3.5" />
              {progress.requiredTotal - progress.requiredFilled} remaining
            </span>
          )}
        </div>
        <div className="w-full h-2 bg-border-light rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-accent rounded-full"
            initial={{ width: 0 }}
            animate={{
              width: `${progress.requiredTotal > 0 ? (progress.requiredFilled / progress.requiredTotal) * 100 : 0}%`,
            }}
            transition={{ duration: 0.5, ease: "easeOut" }}
          />
        </div>
      </div>

      {/* Sections */}
      <form onSubmit={handleSubmit} className="space-y-3">
        {/* Narrative context — form-direct path only */}
        {isFormDirect && (
          <motion.div
            custom={0}
            variants={sectionVariants}
            initial="hidden"
            animate="visible"
            className="border border-border-light rounded-xl overflow-hidden bg-white"
          >
            <div className="px-5 py-4">
              <div className="text-sm font-semibold text-foreground mb-0.5">
                Tell us about your workflow
              </div>
              <div className="text-xs text-muted mb-4">
                Optional — helps generate better status instructions and edge cases
              </div>
              <div className="space-y-5">
                <div className="space-y-1.5">
                  <label className="block text-sm font-medium text-foreground">
                    {businessContext ? buildOpeningMessage(businessContext) : "What are the main stages of a typical job?"}
                  </label>
                  <textarea
                    rows={4}
                    value={narrativeStages}
                    onChange={(e) => setNarrativeStages(e.target.value)}
                    placeholder="e.g. We get a call, dispatch the tech, they drive out, do the work, get a signature, and invoice later..."
                    className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-foreground placeholder:text-muted/50 focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="block text-sm font-medium text-foreground">
                    Walk me through the details — what does your tech actually do at each stage?
                  </label>
                  <textarea
                    rows={4}
                    value={narrativeDetails}
                    onChange={(e) => setNarrativeDetails(e.target.value)}
                    placeholder="e.g. Tech calls the customer on the way, takes before photos, fills out the inspection form, gets a signature..."
                    className="w-full rounded-lg border border-border bg-white px-3 py-2 text-sm text-foreground placeholder:text-muted/50 focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent"
                  />
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {FORM_SCHEMA.map((section, i) => {
          const sectionProg = getSectionProgress(section, localState);
          const isExpanded = expandedSections.has(section.id);
          const animIndex = isFormDirect ? i + 1 : i;

          return (
            <motion.div
              key={section.id}
              custom={animIndex}
              variants={sectionVariants}
              initial="hidden"
              animate="visible"
              className="border border-border-light rounded-xl overflow-hidden bg-white"
            >
              {/* Section header */}
              <button
                type="button"
                onClick={() => toggleSection(section.id)}
                className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-surface/50 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-foreground">
                    {section.label}
                  </div>
                  <div className="text-xs text-muted mt-0.5">
                    {section.description}
                  </div>
                </div>
                <span
                  className={`text-xs font-medium px-2.5 py-1 rounded-full shrink-0 ${
                    sectionProg.filled === sectionProg.total
                      ? "bg-green-50 text-green-600"
                      : "bg-accent-light text-accent"
                  }`}
                >
                  {sectionProg.filled}/{sectionProg.total} filled
                </span>
                {isExpanded ? (
                  <ChevronUp className="w-4 h-4 text-muted shrink-0" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-muted shrink-0" />
                )}
              </button>

              {/* Section body */}
              {isExpanded && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="border-t border-border-light px-5 py-4 space-y-5"
                >
                  {section.fields.map((field) => (
                    <FormField
                      key={field.id}
                      field={field}
                      value={localState[field.id]}
                      onChange={handleFieldChange}
                      highlighted={
                        field.required && !isFieldFilled(localState[field.id])
                      }
                    />
                  ))}
                </motion.div>
              )}
            </motion.div>
          );
        })}

        {/* Submit button */}
        <motion.div
          custom={FORM_SCHEMA.length}
          variants={sectionVariants}
          initial="hidden"
          animate="visible"
          className="pt-4"
        >
          <motion.button
            type="submit"
            disabled={isSubmitting}
            whileHover={!isSubmitting ? { scale: 1.01 } : {}}
            whileTap={!isSubmitting ? { scale: 0.99 } : {}}
            className={`
              w-full flex items-center justify-center gap-2
              py-3.5 rounded-xl text-[15px] font-semibold
              transition-all duration-200
              ${
                !isSubmitting
                  ? "bg-accent text-white hover:bg-accent-dark shadow-sm shadow-accent/25"
                  : "bg-accent/70 text-white cursor-wait"
              }
            `}
          >
            {isSubmitting ? (
              <>
                <motion.div
                  className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full"
                  animate={{ rotate: 360 }}
                  transition={{
                    duration: 0.8,
                    repeat: Infinity,
                    ease: "linear",
                  }}
                />
                Assembling report...
              </>
            ) : (
              <>
                Generate Report
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </motion.button>
        </motion.div>
      </form>
    </motion.div>
  );
}

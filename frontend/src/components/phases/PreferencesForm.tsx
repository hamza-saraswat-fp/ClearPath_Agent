"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Shield, MessageSquare, FileText } from "lucide-react";
import type { Preferences } from "@/types/discovery";

interface PreferencesFormProps {
  onSubmit: (preferences: Preferences) => void;
  isSubmitting?: boolean;
}

export function PreferencesForm({
  onSubmit,
  isSubmitting = false,
}: PreferencesFormProps) {
  const [restrictionPreference, setRestrictionPreference] = useState<
    "guided" | "flexible" | null
  >(null);
  const [customerText, setCustomerText] = useState<boolean | null>(null);
  const [hasExistingForms, setHasExistingForms] = useState<
    "yes" | "no" | "not_sure" | null
  >(null);
  const [formsText, setFormsText] = useState("");

  const isValid =
    restrictionPreference !== null &&
    customerText !== null &&
    hasExistingForms !== null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid || isSubmitting) return;

    const existingForms: string[] =
      hasExistingForms === "yes" && formsText.trim()
        ? formsText
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean)
        : [];

    onSubmit({
      restrictionPreference: restrictionPreference!,
      customerTextOnTheWay: customerText,
      existingForms,
    });
  };

  const sectionVariants = {
    hidden: { opacity: 0, y: 16 },
    visible: (i: number) => ({
      opacity: 1,
      y: 0,
      transition: { duration: 0.35, delay: i * 0.12, ease: "easeOut" as const },
    }),
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="w-full max-w-lg mx-auto py-8 px-4"
    >
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-foreground mb-2">
          Almost there
        </h2>
        <p className="text-muted text-[15px]">
          A few quick preferences to finalize your workflow.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Restriction Preference */}
        <motion.div
          custom={0}
          variants={sectionVariants}
          initial="hidden"
          animate="visible"
        >
          <label className="flex items-center gap-2 text-sm font-semibold text-foreground mb-3">
            <Shield className="w-4 h-4 text-accent" />
            How much freedom should techs have?
          </label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setRestrictionPreference("guided")}
              className={`
                p-4 rounded-xl border text-left transition-all duration-150
                ${
                  restrictionPreference === "guided"
                    ? "border-accent bg-accent-light ring-1 ring-accent/20"
                    : "border-border bg-white hover:border-muted-light"
                }
              `}
            >
              <div className="text-sm font-semibold text-foreground mb-1">
                Guided
              </div>
              <div className="text-xs text-muted leading-relaxed">
                Techs follow steps in order. Status changes are enforced.
              </div>
            </button>
            <button
              type="button"
              onClick={() => setRestrictionPreference("flexible")}
              className={`
                p-4 rounded-xl border text-left transition-all duration-150
                ${
                  restrictionPreference === "flexible"
                    ? "border-accent bg-accent-light ring-1 ring-accent/20"
                    : "border-border bg-white hover:border-muted-light"
                }
              `}
            >
              <div className="text-sm font-semibold text-foreground mb-1">
                Flexible
              </div>
              <div className="text-xs text-muted leading-relaxed">
                Techs can skip steps or change status freely.
              </div>
            </button>
          </div>
        </motion.div>

        {/* Customer Text */}
        <motion.div
          custom={1}
          variants={sectionVariants}
          initial="hidden"
          animate="visible"
        >
          <label className="flex items-center gap-2 text-sm font-semibold text-foreground mb-3">
            <MessageSquare className="w-4 h-4 text-accent" />
            Text customer when tech is on the way?
          </label>
          <div className="flex gap-2">
            {[
              { label: "Yes", value: true },
              { label: "No", value: false },
              { label: "Decide later", value: null },
            ].map((option) => (
              <button
                key={option.label}
                type="button"
                onClick={() => setCustomerText(option.value)}
                className={`
                  flex-1 py-2.5 rounded-xl border text-sm font-medium
                  transition-all duration-150
                  ${
                    customerText === option.value
                      ? "border-accent bg-accent-light text-accent"
                      : "border-border bg-white text-foreground hover:border-muted-light"
                  }
                `}
              >
                {option.label}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Existing Forms */}
        <motion.div
          custom={2}
          variants={sectionVariants}
          initial="hidden"
          animate="visible"
        >
          <label className="flex items-center gap-2 text-sm font-semibold text-foreground mb-3">
            <FileText className="w-4 h-4 text-accent" />
            Any existing forms or checklists in FieldPulse?
          </label>
          <div className="flex gap-2 mb-3">
            {(["yes", "no", "not_sure"] as const).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setHasExistingForms(value)}
                className={`
                  flex-1 py-2.5 rounded-xl border text-sm font-medium
                  transition-all duration-150
                  ${
                    hasExistingForms === value
                      ? "border-accent bg-accent-light text-accent"
                      : "border-border bg-white text-foreground hover:border-muted-light"
                  }
                `}
              >
                {value === "yes"
                  ? "Yes"
                  : value === "no"
                    ? "No"
                    : "Not sure"}
              </button>
            ))}
          </div>

          {hasExistingForms === "yes" && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
            >
              <input
                type="text"
                value={formsText}
                onChange={(e) => setFormsText(e.target.value)}
                placeholder="e.g. Safety checklist, Inspection form"
                className="w-full px-4 py-3 rounded-xl border border-border bg-white text-[15px]
                  placeholder:text-muted-light outline-none
                  focus:border-accent focus:ring-1 focus:ring-accent/20 transition-all"
              />
              <p className="text-xs text-muted mt-1.5">
                Separate multiple forms with commas
              </p>
            </motion.div>
          )}
        </motion.div>

        {/* Submit */}
        <motion.div
          custom={3}
          variants={sectionVariants}
          initial="hidden"
          animate="visible"
          className="pt-2"
        >
          <motion.button
            type="submit"
            disabled={!isValid || isSubmitting}
            whileHover={isValid && !isSubmitting ? { scale: 1.01 } : {}}
            whileTap={isValid && !isSubmitting ? { scale: 0.99 } : {}}
            className={`
              w-full flex items-center justify-center gap-2
              py-3.5 rounded-xl text-[15px] font-semibold
              transition-all duration-200
              ${
                isValid && !isSubmitting
                  ? "bg-accent text-white hover:bg-accent-dark shadow-sm shadow-accent/25"
                  : "bg-border-light text-muted-light cursor-not-allowed"
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

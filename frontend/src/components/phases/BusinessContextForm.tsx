"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Building2, Users, Wrench, Briefcase } from "lucide-react";
import type { BusinessContext } from "@/types/discovery";

interface BusinessContextFormProps {
  onSubmit: (context: BusinessContext) => void;
  isSubmitting?: boolean;
}

const INDUSTRIES = [
  "HVAC",
  "Plumbing",
  "Electrical",
  "Garage Door",
  "General Contracting",
  "Roofing",
  "Landscaping",
  "Pest Control",
  "Cleaning",
  "Other",
];

const COMPANY_SIZES = [
  "1-5 techs",
  "6-15 techs",
  "16-50 techs",
  "50+ techs",
];

export function BusinessContextForm({
  onSubmit,
  isSubmitting = false,
}: BusinessContextFormProps) {
  const [form, setForm] = useState<BusinessContext>({
    companyName: "",
    industry: "",
    companySize: "",
    jobType: "",
  });

  const [focusedField, setFocusedField] = useState<string | null>(null);

  const isValid =
    form.companyName.trim() &&
    form.industry &&
    form.companySize &&
    form.jobType.trim();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isValid && !isSubmitting) {
      onSubmit(form);
    }
  };

  const inputVariants = {
    hidden: { opacity: 0, y: 16 },
    visible: (i: number) => ({
      opacity: 1,
      y: 0,
      transition: { duration: 0.35, delay: i * 0.1, ease: "easeOut" as const },
    }),
  };

  return (
    <motion.form
      onSubmit={handleSubmit}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="w-full max-w-md space-y-5"
    >
      {/* Company Name */}
      <motion.div
        custom={0}
        variants={inputVariants}
        initial="hidden"
        animate="visible"
      >
        <label className="flex items-center gap-2 text-sm font-medium text-foreground mb-1.5">
          <Building2 className="w-4 h-4 text-muted" />
          Company Name
        </label>
        <input
          type="text"
          value={form.companyName}
          onChange={(e) =>
            setForm((prev) => ({ ...prev, companyName: e.target.value }))
          }
          onFocus={() => setFocusedField("companyName")}
          onBlur={() => setFocusedField(null)}
          placeholder="e.g. CSS Mechanical"
          className={`
            w-full px-4 py-3 rounded-xl border bg-white text-[15px]
            placeholder:text-muted-light outline-none transition-all duration-150
            ${
              focusedField === "companyName"
                ? "border-accent ring-1 ring-accent/20"
                : "border-border hover:border-muted-light"
            }
          `}
        />
      </motion.div>

      {/* Industry */}
      <motion.div
        custom={1}
        variants={inputVariants}
        initial="hidden"
        animate="visible"
      >
        <label className="flex items-center gap-2 text-sm font-medium text-foreground mb-1.5">
          <Briefcase className="w-4 h-4 text-muted" />
          Industry
        </label>
        <select
          value={form.industry}
          onChange={(e) =>
            setForm((prev) => ({ ...prev, industry: e.target.value }))
          }
          onFocus={() => setFocusedField("industry")}
          onBlur={() => setFocusedField(null)}
          className={`
            w-full px-4 py-3 rounded-xl border bg-white text-[15px]
            outline-none transition-all duration-150 appearance-none
            bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2212%22%20height%3D%2212%22%20fill%3D%22none%22%20stroke%3D%22%236b7280%22%20stroke-width%3D%222%22%3E%3Cpath%20d%3D%22m2%204%204%204%204-4%22%2F%3E%3C%2Fsvg%3E')]
            bg-[length:12px] bg-[right_16px_center] bg-no-repeat
            ${!form.industry ? "text-muted-light" : "text-foreground"}
            ${
              focusedField === "industry"
                ? "border-accent ring-1 ring-accent/20"
                : "border-border hover:border-muted-light"
            }
          `}
        >
          <option value="" disabled>
            Select your industry
          </option>
          {INDUSTRIES.map((industry) => (
            <option key={industry} value={industry}>
              {industry}
            </option>
          ))}
        </select>
      </motion.div>

      {/* Company Size */}
      <motion.div
        custom={2}
        variants={inputVariants}
        initial="hidden"
        animate="visible"
      >
        <label className="flex items-center gap-2 text-sm font-medium text-foreground mb-1.5">
          <Users className="w-4 h-4 text-muted" />
          Team Size
        </label>
        <div className="grid grid-cols-2 gap-2">
          {COMPANY_SIZES.map((size) => (
            <button
              key={size}
              type="button"
              onClick={() => setForm((prev) => ({ ...prev, companySize: size }))}
              className={`
                px-4 py-2.5 rounded-xl border text-sm font-medium
                transition-all duration-150
                ${
                  form.companySize === size
                    ? "border-accent bg-accent-light text-accent"
                    : "border-border bg-white text-foreground hover:border-muted-light"
                }
              `}
            >
              {size}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Job Type */}
      <motion.div
        custom={3}
        variants={inputVariants}
        initial="hidden"
        animate="visible"
      >
        <label className="flex items-center gap-2 text-sm font-medium text-foreground mb-1.5">
          <Wrench className="w-4 h-4 text-muted" />
          Job Type for This Workflow
        </label>
        <input
          type="text"
          value={form.jobType}
          onChange={(e) =>
            setForm((prev) => ({ ...prev, jobType: e.target.value }))
          }
          onFocus={() => setFocusedField("jobType")}
          onBlur={() => setFocusedField(null)}
          placeholder="e.g. AC installation, service calls"
          className={`
            w-full px-4 py-3 rounded-xl border bg-white text-[15px]
            placeholder:text-muted-light outline-none transition-all duration-150
            ${
              focusedField === "jobType"
                ? "border-accent ring-1 ring-accent/20"
                : "border-border hover:border-muted-light"
            }
          `}
        />
      </motion.div>

      {/* Submit */}
      <motion.div
        custom={4}
        variants={inputVariants}
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
                transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
              />
              Starting...
            </>
          ) : (
            <>
              Start Discovery
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </motion.button>
      </motion.div>
    </motion.form>
  );
}

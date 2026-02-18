"use client";

import { motion } from "framer-motion";
import {
  CheckCircle2,
  ArrowRight,
  Pencil,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { useState } from "react";
import type { DiscoveryReport } from "@/types/discovery";

interface ConfirmationViewProps {
  report: DiscoveryReport;
  summary: string;
  onConfirm: () => void;
  onEdit: () => void;
  isSubmitting?: boolean;
}

export function ConfirmationView({
  report,
  summary,
  onConfirm,
  onEdit,
  isSubmitting = false,
}: ConfirmationViewProps) {
  const [expandedStatus, setExpandedStatus] = useState<number | null>(null);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="w-full max-w-2xl mx-auto py-8 px-4"
    >
      {/* Header */}
      <div className="text-center mb-8">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-green-50 mb-4"
        >
          <CheckCircle2 className="w-6 h-6 text-green-600" />
        </motion.div>
        <h2 className="text-2xl font-bold text-foreground mb-2">
          Your Workflow Summary
        </h2>
        <p className="text-muted text-[15px] max-w-md mx-auto">{summary}</p>
      </div>

      {/* Workflow name + metadata */}
      <div className="bg-surface rounded-xl border border-border-light p-5 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-foreground">
            {report.workflow_name}
          </h3>
          <span className="text-xs font-medium text-accent bg-accent-light px-2.5 py-1 rounded-full">
            {report.statuses.length} statuses
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {report.job_types_covered.map((type) => (
            <span
              key={type}
              className="text-xs bg-white border border-border rounded-full px-3 py-1 text-muted"
            >
              {type}
            </span>
          ))}
        </div>
      </div>

      {/* Statuses list */}
      <div className="space-y-2 mb-8">
        {report.statuses.map((status, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: index * 0.06 }}
            className="border border-border-light rounded-xl overflow-hidden bg-white"
          >
            <button
              type="button"
              onClick={() =>
                setExpandedStatus(expandedStatus === index ? null : index)
              }
              className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-surface/50 transition-colors"
            >
              {/* Order indicator */}
              <div className="w-7 h-7 rounded-full bg-accent-light text-accent text-xs font-bold flex items-center justify-center shrink-0">
                {status.order}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-foreground truncate">
                  {status.name}
                </div>
                <div className="text-xs text-muted truncate">
                  {status.actions.length} action{status.actions.length !== 1 && "s"}
                  {status.transitions_to.length > 0 && (
                    <span>
                      {" "}
                      &rarr; {status.transitions_to[0]}
                    </span>
                  )}
                </div>
              </div>
              {expandedStatus === index ? (
                <ChevronUp className="w-4 h-4 text-muted shrink-0" />
              ) : (
                <ChevronDown className="w-4 h-4 text-muted shrink-0" />
              )}
            </button>

            {expandedStatus === index && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
                className="border-t border-border-light px-5 py-4 space-y-3"
              >
                {/* Instructions */}
                <div>
                  <div className="text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">
                    Instructions
                  </div>
                  <div className="text-sm text-foreground whitespace-pre-line leading-relaxed">
                    {status.instructions}
                  </div>
                </div>

                {/* Actions */}
                {status.actions.length > 0 && (
                  <div>
                    <div className="text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">
                      Actions
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {status.actions.map((action, i) => (
                        <span
                          key={i}
                          className="text-xs bg-accent-light text-accent px-2.5 py-1 rounded-full font-medium"
                        >
                          {action}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Edge Cases */}
                {status.edge_cases.length > 0 && (
                  <div>
                    <div className="text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">
                      Edge Cases
                    </div>
                    <ul className="text-sm text-muted space-y-1">
                      {status.edge_cases.map((ec, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-accent mt-0.5">&#8226;</span>
                          {ec}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Notes */}
                {status.notes && (
                  <div>
                    <div className="text-xs font-semibold text-muted uppercase tracking-wider mb-1.5">
                      Notes
                    </div>
                    <p className="text-sm text-muted">{status.notes}</p>
                  </div>
                )}
              </motion.div>
            )}
          </motion.div>
        ))}
      </div>

      {/* Confidence Notes */}
      {(report.confidence_notes.gaps_or_unknowns.length > 0 ||
        report.confidence_notes.medium_confidence.length > 0) && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 mb-8">
          <h4 className="text-sm font-semibold text-amber-800 mb-2">
            Items to review
          </h4>
          <ul className="text-sm text-amber-700 space-y-1">
            {report.confidence_notes.gaps_or_unknowns.map((gap, i) => (
              <li key={`gap-${i}`} className="flex items-start gap-2">
                <span className="mt-0.5">&#9679;</span>
                {gap}
              </li>
            ))}
            {report.confidence_notes.medium_confidence.map((item, i) => (
              <li key={`med-${i}`} className="flex items-start gap-2">
                <span className="mt-0.5">&#9675;</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-3">
        <motion.button
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          onClick={onEdit}
          disabled={isSubmitting}
          className="flex-1 flex items-center justify-center gap-2 py-3.5 rounded-xl
            border border-border text-[15px] font-semibold text-foreground
            hover:bg-surface transition-colors"
        >
          <Pencil className="w-4 h-4" />
          Edit
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          onClick={onConfirm}
          disabled={isSubmitting}
          className={`
            flex-[2] flex items-center justify-center gap-2 py-3.5 rounded-xl
            text-[15px] font-semibold transition-all duration-200
            ${
              isSubmitting
                ? "bg-accent/70 text-white cursor-wait"
                : "bg-accent text-white hover:bg-accent-dark shadow-sm shadow-accent/25"
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
              Submitting...
            </>
          ) : (
            <>
              Confirm & Submit
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </motion.button>
      </div>
    </motion.div>
  );
}

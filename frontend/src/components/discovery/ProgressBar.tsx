"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import type { CoverageAreaId, CoverageStatus } from "@/types/discovery";
import { COVERAGE_AREAS } from "@/lib/coverage-areas";

interface ProgressBarProps {
  coverageStatuses: Record<CoverageAreaId, CoverageStatus>;
}

export function ProgressBar({ coverageStatuses }: ProgressBarProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  const coveredCount = COVERAGE_AREAS.filter(
    (a) => coverageStatuses[a.id] === "covered"
  ).length;

  return (
    <div className="w-full px-6 py-3">
      <div className="max-w-2xl mx-auto">
        {/* Label */}
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-muted tracking-wide uppercase">
            Discovery Progress
          </span>
          <span className="text-xs font-medium text-muted">
            {coveredCount}/{COVERAGE_AREAS.length}
          </span>
        </div>

        {/* Segments */}
        <div className="flex gap-1.5 relative">
          {COVERAGE_AREAS.map((area, index) => {
            const status = coverageStatuses[area.id];
            const isCovered = status === "covered";
            const isPartial = status === "partial";

            return (
              <div
                key={area.id}
                className="relative flex-1"
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(null)}
              >
                {/* Segment bar */}
                <div className="h-1.5 rounded-full bg-border-light overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{
                      width: isCovered ? "100%" : isPartial ? "50%" : "0%",
                    }}
                    transition={{ duration: 0.5, ease: "easeOut" }}
                    className={`h-full rounded-full ${
                      isCovered
                        ? "bg-accent"
                        : isPartial
                          ? "bg-accent/40"
                          : "bg-transparent"
                    }`}
                  />
                </div>

                {/* Tooltip */}
                {hoveredIndex === index && (
                  <motion.div
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.15 }}
                    className="absolute top-full left-1/2 -translate-x-1/2 mt-2 z-50"
                  >
                    <div className="bg-foreground text-white text-xs font-medium px-3 py-1.5 rounded-lg whitespace-nowrap shadow-lg">
                      {area.label}
                      <span className="ml-1.5 opacity-70">
                        {isCovered
                          ? "Covered"
                          : isPartial
                            ? "Partial"
                            : "Not covered"}
                      </span>
                      {/* Arrow */}
                      <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-foreground rotate-45" />
                    </div>
                  </motion.div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

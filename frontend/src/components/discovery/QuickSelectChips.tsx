"use client";

import { motion } from "framer-motion";
import type { QuickSelectOption } from "@/types/discovery";

interface QuickSelectChipsProps {
  options: QuickSelectOption[];
  onSelect: (value: string) => void;
  disabled?: boolean;
}

export function QuickSelectChips({
  options,
  onSelect,
  disabled = false,
}: QuickSelectChipsProps) {
  if (options.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 pl-11">
      {options.map((option, index) => (
        <motion.button
          key={option.value}
          initial={{ opacity: 0, y: 8, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{
            duration: 0.25,
            delay: index * 0.06,
            ease: "easeOut",
          }}
          whileHover={disabled ? {} : { scale: 1.03 }}
          whileTap={disabled ? {} : { scale: 0.97 }}
          onClick={() => !disabled && onSelect(option.value)}
          disabled={disabled}
          className={`
            px-4 py-2 rounded-full text-sm font-medium
            border transition-colors duration-150
            ${
              disabled
                ? "bg-surface border-border-light text-muted-light cursor-default"
                : "bg-white border-border text-foreground hover:border-accent hover:bg-accent-light hover:text-accent cursor-pointer"
            }
          `}
        >
          {option.label}
        </motion.button>
      ))}
    </div>
  );
}

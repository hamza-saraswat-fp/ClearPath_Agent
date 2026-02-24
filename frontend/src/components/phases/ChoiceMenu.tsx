"use client";

import { motion } from "framer-motion";
import { MessageCircle, ClipboardList } from "lucide-react";
import type { BusinessContext } from "@/types/discovery";

interface ChoiceMenuProps {
  businessContext: BusinessContext;
  onChoice: (choice: "chat" | "form_direct") => void;
}

const cardVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, delay: i * 0.1, ease: "easeOut" as const },
  }),
};

const CHOICES = [
  {
    id: "chat" as const,
    icon: MessageCircle,
    title: "Chat with AI",
    description: "Answer questions to build your workflow",
  },
  {
    id: "form_direct" as const,
    icon: ClipboardList,
    title: "Fill form directly",
    description: "I know what I need",
  },
];

export function ChoiceMenu({ businessContext, onChoice }: ChoiceMenuProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="w-full max-w-md mx-auto py-12 px-6"
    >
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-foreground mb-2">
          How would you like to proceed?
        </h2>
        <p className="text-muted text-[15px]">
          Build the {businessContext.jobType} workflow for{" "}
          {businessContext.companyName}
        </p>
      </div>

      <div className="space-y-3">
        {CHOICES.map((choice, i) => (
          <motion.button
            key={choice.id}
            custom={i}
            variants={cardVariants}
            initial="hidden"
            animate="visible"
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            onClick={() => onChoice(choice.id)}
            className="w-full flex items-center gap-4 p-5 rounded-xl border border-border bg-white
              text-left transition-all duration-150
              hover:border-accent hover:bg-accent-light"
          >
            <div className="w-10 h-10 rounded-xl bg-accent-light flex items-center justify-center shrink-0">
              <choice.icon className="w-5 h-5 text-accent" />
            </div>
            <div>
              <div className="text-sm font-semibold text-foreground">
                {choice.title}
              </div>
              <div className="text-xs text-muted mt-0.5">
                {choice.description}
              </div>
            </div>
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
}

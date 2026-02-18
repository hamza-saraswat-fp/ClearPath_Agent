"use client";

import { motion } from "framer-motion";
import type { ConversationMessage } from "@/types/discovery";
import { QuickSelectChips } from "./QuickSelectChips";

interface MessageBubbleProps {
  message: ConversationMessage;
  onQuickSelect?: (value: string) => void;
  isLatest?: boolean;
  chipsDisabled?: boolean;
}

export function MessageBubble({
  message,
  onQuickSelect,
  isLatest = false,
  chipsDisabled = false,
}: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={`flex flex-col gap-2 ${isUser ? "items-end" : "items-start"}`}
    >
      <div
        className={`flex items-start gap-3 max-w-[85%] ${
          isUser ? "flex-row-reverse" : "flex-row"
        }`}
      >
        {/* Avatar */}
        {!isUser && (
          <div className="w-8 h-8 rounded-full bg-accent-light flex items-center justify-center shrink-0 mt-0.5">
            <svg width="14" height="14" viewBox="0 0 200 200" fill="none">
              <path
                fillRule="evenodd"
                clipRule="evenodd"
                d="M100 150c27.614 0 50-22.386 50-50s-22.386-50-50-50-50 22.386-50 50 22.386 50 50 50zm0 50c55.228 0 100-44.772 100-100S155.228 0 100 0 0 44.772 0 100s44.772 100 100 100z"
                fill="#0066FF"
              />
            </svg>
          </div>
        )}

        {/* Bubble */}
        <div
          className={`
            px-4 py-3 text-[15px] leading-relaxed
            ${
              isUser
                ? "bg-accent text-white rounded-2xl rounded-tr-sm"
                : "bg-surface text-foreground rounded-2xl rounded-tl-sm"
            }
          `}
        >
          {message.content}
        </div>
      </div>

      {/* Quick select chips below bot messages */}
      {!isUser &&
        message.quickSelectOptions &&
        message.quickSelectOptions.length > 0 &&
        onQuickSelect && (
          <QuickSelectChips
            options={message.quickSelectOptions}
            onSelect={onQuickSelect}
            disabled={chipsDisabled || !isLatest}
          />
        )}
    </motion.div>
  );
}

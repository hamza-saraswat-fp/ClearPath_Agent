"use client";

import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { ArrowUp } from "lucide-react";
import type { ConversationMessage } from "@/types/discovery";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";

interface ChatInterfaceProps {
  messages: ConversationMessage[];
  onSendMessage: (message: string) => void;
  onQuickSelect: (value: string) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export function ChatInterface({
  messages,
  onSendMessage,
  onQuickSelect,
  isLoading,
  disabled = false,
}: ChatInterfaceProps) {
  const [inputValue, setInputValue] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 120)}px`;
    }
  }, [inputValue]);

  const handleSend = () => {
    const trimmed = inputValue.trim();
    if (!trimmed || isLoading || disabled) return;
    onSendMessage(trimmed);
    setInputValue("");
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const lastAssistantIndex = messages.reduce(
    (acc, msg, i) => (msg.role === "assistant" ? i : acc),
    -1
  );

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto chat-scrollbar px-4 py-6">
        <div className="max-w-2xl mx-auto space-y-4">
          {messages.map((msg, index) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              onQuickSelect={onQuickSelect}
              isLatest={index === lastAssistantIndex}
              chipsDisabled={isLoading}
            />
          ))}
          {isLoading && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="border-t border-border-light bg-white px-4 py-3">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-end gap-3 bg-surface rounded-xl border border-border px-4 py-3 focus-within:border-accent focus-within:ring-1 focus-within:ring-accent/20 transition-all">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe your workflow..."
              disabled={isLoading || disabled}
              rows={1}
              className="flex-1 bg-transparent text-[15px] text-foreground placeholder:text-muted-light outline-none resize-none leading-relaxed"
            />
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleSend}
              disabled={!inputValue.trim() || isLoading || disabled}
              className={`
                w-8 h-8 rounded-full flex items-center justify-center shrink-0
                transition-colors duration-150
                ${
                  inputValue.trim() && !isLoading && !disabled
                    ? "bg-accent text-white hover:bg-accent-dark"
                    : "bg-border-light text-muted-light cursor-not-allowed"
                }
              `}
            >
              <ArrowUp className="w-4 h-4" />
            </motion.button>
          </div>
          <p className="text-center text-xs text-muted-light mt-2">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  );
}

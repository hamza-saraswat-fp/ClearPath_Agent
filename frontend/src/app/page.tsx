"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ClearPathLogo } from "@/components/shared/ClearPathLogo";
import { BusinessContextForm } from "@/components/phases/BusinessContextForm";
import type { BusinessContext } from "@/types/discovery";

export default function HomePage() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (context: BusinessContext) => {
    setIsSubmitting(true);
    try {
      const res = await fetch("/api/discovery/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ businessContext: context }),
      });

      if (!res.ok) throw new Error("Failed to start session");

      const data = await res.json();
      // Store session data for the discovery page
      sessionStorage.setItem(
        "clearpath_session",
        JSON.stringify({
          sessionId: data.sessionId,
          businessContext: context,
          firstMessage: data.firstMessage,
        })
      );
      router.push("/discovery");
    } catch (err) {
      console.error("Failed to start discovery:", err);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-white px-6 py-12">
      <div className="w-full max-w-md flex flex-col items-center">
        {/* Logo */}
        <ClearPathLogo size={72} className="mb-6" />

        {/* Title */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15 }}
          className="text-center mb-10"
        >
          <h1 className="text-3xl font-bold text-foreground mb-2 tracking-tight">
            ClearPath
          </h1>
          <p className="text-muted text-[15px] max-w-sm">
            Let&apos;s map your field service workflow. Tell us about your business to
            get started.
          </p>
        </motion.div>

        {/* Form */}
        <BusinessContextForm
          onSubmit={handleSubmit}
          isSubmitting={isSubmitting}
        />
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

export interface ReasoningStep {
  step: string;
  status: string;
  detail: string;
  duration_ms?: number;
}

interface DecisionTraceProps {
  steps?: ReasoningStep[];
  label?: string;
}

const statusStyles: Record<
  string,
  { bg: string; border: string; text: string; dot: string }
> = {
  success: {
    bg: "rgba(16,185,129,0.08)",
    border: "rgba(16,185,129,0.20)",
    text: "#065F46",
    dot: "#10B981",
  },
  warning: {
    bg: "rgba(245,158,11,0.08)",
    border: "rgba(245,158,11,0.20)",
    text: "#92400E",
    dot: "#F59E0B",
  },
  error: {
    bg: "rgba(239,68,68,0.08)",
    border: "rgba(239,68,68,0.20)",
    text: "#991B1B",
    dot: "#EF4444",
  },
};

function prettyStepName(step: string): string {
  return step
    .toLowerCase()
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export default function DecisionTrace({
  steps = [],
  label = "Decision Trace",
}: DecisionTraceProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!steps.length) return null;

  return (
    <div className="mt-4">
      <button
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          setIsOpen((prev) => !prev);
        }}
        className="group inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.18em] transition-all"
        style={{
          background: isOpen ? "#1A1A1A" : "#F8F8F8",
          color: isOpen ? "#FFFFFF" : "#525252",
          border: isOpen
            ? "1px solid #1A1A1A"
            : "1px solid rgba(0,0,0,0.08)",
        }}
      >
        <span
          className={`inline-flex h-4 w-4 items-center justify-center rounded-full transition-transform duration-200 ${
            isOpen ? "rotate-90" : "rotate-0"
          }`}
          style={{
            background: isOpen ? "rgba(255,255,255,0.14)" : "#FFFFFF",
            border: isOpen
              ? "1px solid rgba(255,255,255,0.16)"
              : "1px solid rgba(0,0,0,0.06)",
          }}
        >
          <svg
            width="10"
            height="10"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </span>
        <span>{isOpen ? `Hide ${label}` : `Open ${label}`}</span>
      </button>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0, y: -6 }}
            animate={{ opacity: 1, height: "auto", y: 0 }}
            exit={{ opacity: 0, height: 0, y: -6 }}
            transition={{ duration: 0.22, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div
              className="mt-3 rounded-2xl p-4"
              style={{
                background: "linear-gradient(180deg, #FFFFFF 0%, #FCFCFC 100%)",
                border: "1px solid rgba(0,0,0,0.06)",
                boxShadow: "0 8px 28px rgba(0,0,0,0.05)",
              }}
            >
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-[#1A1A1A]">
                    {label}
                  </p>
                  <p className="mt-1 text-[12px] text-[#737373]">
                    Structured trace of routing, retrieval, SQL, and response steps.
                  </p>
                </div>
                <div className="text-[11px] font-medium text-[#8A8A8A]">
                  {steps.length} steps
                </div>
              </div>

              <div className="space-y-3">
                {steps.map((step, index) => {
                  const style =
                    statusStyles[step.status?.toLowerCase()] ||
                    statusStyles.success;

                  return (
                    <div
                      key={`${step.step}-${index}`}
                      className="rounded-xl px-3 py-3"
                      style={{
                        background: "#FFFFFF",
                        border: "1px solid rgba(0,0,0,0.05)",
                      }}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span
                              className="inline-block h-2 w-2 rounded-full"
                              style={{ background: style.dot }}
                            />
                            <span className="text-[12px] font-semibold text-[#1A1A1A]">
                              {prettyStepName(step.step)}
                            </span>
                            <span
                              className="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.14em]"
                              style={{
                                background: style.bg,
                                border: `1px solid ${style.border}`,
                                color: style.text,
                              }}
                            >
                              {step.status || "success"}
                            </span>
                          </div>
                          <p className="mt-2 text-[13px] leading-[1.65] text-[#4B5563]">
                            {step.detail}
                          </p>
                        </div>
                        {typeof step.duration_ms === "number" && (
                          <span className="shrink-0 text-[11px] font-medium text-[#9CA3AF]">
                            {step.duration_ms} ms
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

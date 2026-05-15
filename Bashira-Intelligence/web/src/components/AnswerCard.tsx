"use client";
import { motion } from "framer-motion";
import DecisionTrace, { type ReasoningStep } from "@/components/DecisionTrace";

// ── Types ───────────────────────────────────────────────────────────────
interface PredictiveSummary {
  forecast_line?: string;
  risk_line?: string;
  causal_line?: string;
  intervention_line?: string;
  scan_status?: string;
}

interface AnswerCardProps {
  answerText: string;
  riskLabel: string; // ON_TRACK | WATCH | AT_RISK | CRITICAL
  predictiveSummary: PredictiveSummary;
  reasoningSteps?: ReasoningStep[];
  sqlColumns?: string[];
  sqlRows?: unknown[][];
  onShowChart: () => void;
  onDismissChart: () => void;
  onDeepDive?: (wellId?: string) => void;
  onSimulate?: (wellId?: string) => void;
}

const riskConfig: Record<
  string,
  { label: string; bg: string; border: string; dot: string; text: string }
> = {
  ON_TRACK: {
    label: "ON TRACK",
    bg: "rgba(16,185,129,0.08)",
    border: "rgba(16,185,129,0.25)",
    dot: "#10B981",
    text: "#065F46",
  },
  WATCH: {
    label: "WATCH",
    bg: "rgba(245,158,11,0.08)",
    border: "rgba(245,158,11,0.25)",
    dot: "#F59E0B",
    text: "#92400E",
  },
  AT_RISK: {
    label: "AT RISK",
    bg: "rgba(239,68,68,0.08)",
    border: "rgba(239,68,68,0.25)",
    dot: "#EF4444",
    text: "#991B1B",
  },
  CRITICAL: {
    label: "CRITICAL",
    bg: "rgba(220,38,38,0.12)",
    border: "rgba(220,38,38,0.35)",
    dot: "#DC2626",
    text: "#7F1D1D",
  },
};

// Strip markdown bold markers from LLM output
function cleanMarkdown(text: string): string {
  return text
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/#{1,3}\s/g, "")
    .trim();
}

// ── Icons ───────────────────────────────────────────────────────────────
const ScanIcon = () => (
  <svg
    width="14"
    height="14"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
  >
    <circle cx="12" cy="12" r="9" strokeDasharray="2 2" />
    <circle cx="12" cy="12" r="5" />
    <circle cx="12" cy="12" r="1.5" fill="currentColor" />
    <path d="M12 3V5" strokeLinecap="round" />
    <path d="M12 19V21" strokeLinecap="round" />
    <path d="M3 12H5" strokeLinecap="round" />
    <path d="M19 12H21" strokeLinecap="round" />
  </svg>
);

const ChartIcon = () => (
  <svg
    width="14"
    height="14"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
  >
    <path d="M18 20V10M12 20V4M6 20V14" strokeLinecap="round" />
  </svg>
);

const DeepDiveIcon = () => (
  <svg
    width="14"
    height="14"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
  >
    <path
      d="M4 18L9 13L13 16L20 7"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path d="M17 7H21V11" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const SimulateIcon = () => (
  <svg
    width="14"
    height="14"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
  >
    <path d="M6 6H10V10H6V6Z" />
    <path d="M14 4H18V8H14V4Z" />
    <path d="M14 16H18V20H14V16Z" />
    <path d="M10 8H14" strokeLinecap="round" />
    <path d="M16 8V16" strokeLinecap="round" />
  </svg>
);

// ── Component ───────────────────────────────────────────────────────────
export default function AnswerCard({
  answerText,
  riskLabel,
  predictiveSummary,
  reasoningSteps,
  sqlColumns,
  sqlRows,
  onShowChart,
  onDismissChart,
  onDeepDive,
  onSimulate,
}: AnswerCardProps) {
  const risk = riskConfig[riskLabel] || riskConfig.WATCH;
  const hasScan =
    predictiveSummary?.scan_status &&
    predictiveSummary.scan_status !== "unavailable";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="w-full rounded-2xl overflow-hidden"
      style={{
        background: "#FFFFFF",
        border: `1.5px solid ${risk.border}`,
        boxShadow: "0 4px 24px rgba(0,0,0,0.06)",
      }}
    >
      {/* ── Header ── */}
      <div
        className="flex items-center justify-between px-5 py-3"
        style={{
          background: risk.bg,
          borderBottom: `1px solid ${risk.border}`,
        }}
      >
        <div className="flex items-center gap-2">
          <ScanIcon />
          <span
            className="text-[11px] font-bold uppercase tracking-widest"
            style={{ color: risk.text }}
          >
            Predictive Intelligence
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span
            className="w-2 h-2 rounded-full animate-pulse"
            style={{ background: risk.dot }}
          />
          <span
            className="text-[10px] font-bold uppercase tracking-wider"
            style={{ color: risk.text }}
          >
            {risk.label}
          </span>
        </div>
      </div>

      {/* ── Answer Text ── */}
      <div className="px-5 py-4">
        <p
          className="text-[14px] leading-[1.7] text-[#1A1A1A]"
          style={{ fontFamily: '"Figtree", sans-serif' }}
        >
          {cleanMarkdown(answerText)}
        </p>
      </div>

      {/* ── Predictive Scan Panel ── */}
      {hasScan && (
        <div
          className="mx-4 mb-4 rounded-xl p-4"
          style={{
            background: "#FAFAFA",
            border: "1px solid rgba(0,0,0,0.06)",
          }}
        >
          <div className="flex items-center gap-2 mb-3">
            <ScanIcon />
            <span className="text-[10px] font-bold uppercase tracking-widest text-[#525252]">
              Predictive Scan
            </span>
            {predictiveSummary.scan_status === "partial" && (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#FEF3C7] text-[#92400E] font-semibold">
                PARTIAL
              </span>
            )}
          </div>

          <div className="grid gap-2.5">
            {predictiveSummary.forecast_line && (
              <div className="flex items-start gap-2.5">
                <span
                  className="w-2 h-2 rounded-full mt-1.5 shrink-0"
                  style={{ background: "#E87722" }}
                />
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#737373]">
                    Forecast
                  </span>
                  <p className="text-[13px] text-[#374151] leading-snug">
                    {predictiveSummary.forecast_line}
                  </p>
                </div>
              </div>
            )}
            {predictiveSummary.risk_line && (
              <div className="flex items-start gap-2.5">
                <span
                  className="w-2 h-2 rounded-full mt-1.5 shrink-0"
                  style={{ background: "#EF4444" }}
                />
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#737373]">
                    Risk
                  </span>
                  <p className="text-[13px] text-[#374151] leading-snug">
                    {predictiveSummary.risk_line}
                  </p>
                </div>
              </div>
            )}
            {predictiveSummary.causal_line && (
              <div className="flex items-start gap-2.5">
                <span
                  className="w-2 h-2 rounded-full mt-1.5 shrink-0"
                  style={{ background: "#8B5CF6" }}
                />
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#737373]">
                    Root Cause
                  </span>
                  <p className="text-[13px] text-[#374151] leading-snug">
                    {predictiveSummary.causal_line}
                  </p>
                </div>
              </div>
            )}
            {predictiveSummary.intervention_line && (
              <div className="flex items-start gap-2.5">
                <span
                  className="w-2 h-2 rounded-full mt-1.5 shrink-0"
                  style={{ background: "#10B981" }}
                />
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#737373]">
                    Best Fix
                  </span>
                  <p className="text-[13px] text-[#374151] leading-snug">
                    {predictiveSummary.intervention_line}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Chart Decision: Yes / No ── */}
      <div
        className="mx-4 mb-4 rounded-xl p-4 text-center"
        style={{
          background: "linear-gradient(135deg, #FAFAFA 0%, #F5F5F5 100%)",
          border: "1px solid rgba(0,0,0,0.06)",
        }}
      >
        <p className="text-[13px] text-[#525252] mb-3 font-medium">
          Want to see the visualization?
        </p>
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={onShowChart}
            className="flex items-center gap-2 px-5 py-2 rounded-lg text-[12px] font-semibold transition-all hover:shadow-md"
            style={{
              background: "#1A1A1A",
              color: "#FFFFFF",
            }}
          >
            <ChartIcon /> Yes, show chart
          </button>
          <button
            onClick={onDismissChart}
            className="flex items-center gap-2 px-5 py-2 rounded-lg text-[12px] font-semibold transition-all hover:bg-[#EEEEEE]"
            style={{
              background: "#F5F5F5",
              color: "#525252",
              border: "1px solid rgba(0,0,0,0.08)",
            }}
          >
            No thanks
          </button>
        </div>
      </div>

      {/* ── Action Pills ── */}
      <div className="px-5 pb-4 flex items-center gap-2 flex-wrap">
        {onDeepDive && (
          <button
            onClick={() => onDeepDive?.()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold transition-all hover:bg-[#F0F0F0]"
            style={{
              border: "1px solid rgba(0,0,0,0.1)",
              color: "#525252",
            }}
          >
            <DeepDiveIcon /> Deep Dive
          </button>
        )}
        {onSimulate && (
          <button
            onClick={() => onSimulate?.()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-semibold transition-all hover:bg-[#F0F0F0]"
            style={{
              border: "1px solid rgba(0,0,0,0.1)",
              color: "#525252",
            }}
          >
            <SimulateIcon /> Simulate
          </button>
        )}
      </div>

      <div className="px-4 pb-4">
        <DecisionTrace steps={reasoningSteps} />
      </div>
    </motion.div>
  );
}

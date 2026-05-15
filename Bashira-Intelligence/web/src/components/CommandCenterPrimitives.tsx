"use client";

import type { ReactNode } from "react";

/* ── Formatters ────────────────────────────────────────────────────────── */

export function formatCompactNumber(value: number | string | null | undefined) {
  const numeric = Number(value ?? 0);
  if (!Number.isFinite(numeric)) return "0";
  return new Intl.NumberFormat("en-US", {
    notation: Math.abs(numeric) >= 1000 ? "compact" : "standard",
    maximumFractionDigits: 1,
  }).format(numeric);
}

export function formatPct(value: number | string | null | undefined) {
  const numeric = Number(value ?? 0);
  if (!Number.isFinite(numeric)) return "0.0%";
  return `${numeric.toFixed(1)}%`;
}

/* ── Surface Panel — Solid White Component ────────────────────────────────── */

export function SurfacePanel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-[12px] border border-[#E5E5E5] bg-[#FFFFFF] shadow-sm transition-all duration-300 hover:border-[#D4D4D4] ${className}`}
    >
      {children}
    </div>
  );
}

/* ── Metric Tile — Clean data cell ───────────────────────────────────── */

export function MetricTile({
  label,
  value,
  detail,
  accent = "#E87722",
}: {
  label: string;
  value: string;
  detail?: string;
  accent?: string;
}) {
  return (
    <div className="group rounded-[10px] border border-[#E5E5E5] bg-[#FFFFFF] px-5 py-4 shadow-sm transition-all duration-300 hover:border-[#D4D4D4] hover:shadow-md">
      <div className="flex items-center justify-between gap-4">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-[0.24em] text-[#737373]">
            {label}
          </div>
          <div className="text-data mt-2 text-[28px] font-bold tracking-[-0.03em] text-[#1A1A1A]">
            {value}
          </div>
          {detail ? (
            <div className="mt-1 text-[11px] leading-4 text-[#A3A3A3]">{detail}</div>
          ) : null}
        </div>
        <div
          className="h-10 w-[3px] rounded-full opacity-60 transition-opacity duration-300 group-hover:opacity-100"
          style={{ backgroundColor: accent }}
        />
      </div>
    </div>
  );
}

/* ── Section Header — Clean Layout ─────────────────────────────────── */

export function SectionHeader({
  kicker,
  title,
  subtitle,
  aside,
}: {
  kicker: string;
  title: string;
  subtitle: string;
  aside?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.28em] text-[#737373]">
          {kicker}
        </div>
        <h1 className="mt-2 text-[26px] font-bold tracking-[-0.03em] text-[#1A1A1A]">
          {title}
        </h1>
        <p className="mt-1.5 max-w-[880px] text-[13px] leading-5 text-[#525252]">
          {subtitle}
        </p>
      </div>
      {aside ? <div className="shrink-0">{aside}</div> : null}
    </div>
  );
}

/* ── Tone Pill — Refined badge ─────────────────────────────────────────── */

export function TonePill({
  label,
  tone = "neutral",
}: {
  label: string;
  tone?: "critical" | "warning" | "positive" | "neutral";
}) {
  const palette =
    tone === "critical"
      ? { bg: "#FEF2F2", border: "#FCA5A5", text: "#DC2626" }
      : tone === "warning"
        ? { bg: "#FFFBEB", border: "#FDE68A", text: "#D97706" }
        : tone === "positive"
          ? { bg: "#F0FDF4", border: "#86EFAC", text: "#16A34A" }
          : { bg: "#F5F5F5", border: "#E5E5E5", text: "#525252" };

  return (
    <span
      className="inline-flex items-center rounded-[6px] border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.16em]"
      style={{
        backgroundColor: palette.bg,
        borderColor: palette.border,
        color: palette.text,
      }}
    >
      {label}
    </span>
  );
}

/* ── Loading State ─────────────────────────────────────────────────────── */

export function LoadingState({ label }: { label: string }) {
  return (
    <SurfacePanel className="p-6">
      <div className="flex items-center gap-3 text-[#525252]">
        <span className="inline-flex h-2 w-2 animate-pulse rounded-full bg-[#E87722]" />
        <span className="text-[13px] font-medium">{label}</span>
      </div>
    </SurfacePanel>
  );
}

/* ── Error State ───────────────────────────────────────────────────────── */

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-[12px] border border-[#FCA5A5] bg-[#FEF2F2] p-6 shadow-sm">
      <div className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#DC2626]">
        Integration Error
      </div>
      <div className="mt-2 text-[13px] leading-5 text-[#991B1B]">{message}</div>
    </div>
  );
}

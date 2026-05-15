"use client";

import { useState, type ReactNode } from "react";

/** ─────────────────────────────────────────────────────────────────────────────
 *  ChartViewToggle
 *  A premium 2D / 3D toggle wrapper for any paired chart.
 *  ── Usage ──
 *    <ChartViewToggle view2d={<PlotlyChart />} view3d={<ThreeChart />} />
 * ────────────────────────────────────────────────────────────────────────── */

interface ChartViewToggleProps {
  view2d: ReactNode;
  view3d?: ReactNode;
  defaultView?: "2d" | "3d";
  label?: string;
}

export default function ChartViewToggle({
  view2d,
  view3d,
  defaultView = "2d",
  label,
}: ChartViewToggleProps) {
  const [mode, setMode] = useState<"2d" | "3d">(defaultView);
  const has3d = !!view3d;

  return (
    <div className="relative border-2 border-black bg-white overflow-hidden">
      {/* Toggle pill — solid angular top right */}
      {has3d ? (
        <div className="absolute right-0 top-0 z-30 flex border-b-2 border-l-2 border-black bg-white">
          <button
            onClick={() => setMode("2d")}
            className={`px-4 py-1.5 text-[9px] font-bold uppercase tracking-[0.18em] transition-none border-r border-[#333] ${
              mode === "2d"
                ? "bg-black text-white"
                : "text-black hover:bg-[#E5E5E5]"
            }`}
          >
            2D FLAT
          </button>
          <button
            onClick={() => setMode("3d")}
            className={`px-4 py-1.5 text-[9px] font-bold uppercase tracking-[0.18em] transition-none ${
              mode === "3d"
                ? "bg-[#0f62fe] text-white"
                : "text-black hover:bg-[#E5E5E5]"
            }`}
          >
            3D VOLUMETRIC
          </button>
        </div>
      ) : null}

      {/* Optional label badge */}
      {label ? (
        <div className="absolute left-0 top-0 z-30 bg-black px-3 py-1.5 text-[8px] font-bold uppercase tracking-[0.22em] text-white border-b-2 border-r-2 border-black">
          {label}
        </div>
      ) : null}

      {/* Active view */}
      <div className="bg-white">
        {mode === "3d" && view3d ? view3d : view2d}
      </div>
    </div>
  );
}

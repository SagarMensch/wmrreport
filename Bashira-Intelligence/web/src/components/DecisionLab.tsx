"use client";

import { useEffect, useState } from "react";

import CausalCommand from "@/components/CausalCommand";
import DecisionStudio from "@/components/DecisionStudio";
import PredictiveStudio from "@/components/PredictiveStudio";

export type DecisionLabView = "studio" | "forecast" | "causal";

export default function DecisionLab({
  initialView = "studio",
}: {
  initialView?: DecisionLabView;
}) {
  const [view, setView] = useState<DecisionLabView>(initialView);

  useEffect(() => {
    setView(initialView);
  }, [initialView]);

  return (
    <div className="h-full overflow-hidden bg-[#0F0C0A]">
      <div className="border-b border-[rgba(185,150,100,0.08)] bg-[rgba(26,21,16,0.60)] px-6 py-4 backdrop-blur-[20px]">
        <div className="mx-auto flex max-w-[1540px] flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-[0.28em] text-[#C9A96E]">
              Decision Lab
            </div>
            <div className="mt-2 text-[22px] font-semibold tracking-[-0.03em] text-[#EDE8DF]">
              Forecast, explain, simulate
            </div>
          </div>
          <div className="flex flex-wrap gap-1 rounded-[8px] border border-[rgba(185,150,100,0.10)] bg-[rgba(26,21,16,0.50)] p-1 backdrop-blur-[16px]">
            {([
              ["studio", "Decision Studio"],
              ["forecast", "Predictive Forecast"],
              ["causal", "Causal Why"],
            ] as const).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setView(key)}
                className={`rounded-[6px] px-3.5 py-2 text-[10px] font-semibold uppercase tracking-[0.14em] transition-all duration-300 ${
                  view === key
                    ? "bg-[rgba(201,169,110,0.15)] text-[#C9A96E] border border-[rgba(201,169,110,0.30)]"
                    : "text-[#6B6259] hover:text-[#9A8B78] border border-transparent"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="h-[calc(100%-80px)]">
        {view === "studio" ? <DecisionStudio /> : null}
        {view === "forecast" ? <PredictiveStudio /> : null}
        {view === "causal" ? <CausalCommand /> : null}
      </div>
    </div>
  );
}

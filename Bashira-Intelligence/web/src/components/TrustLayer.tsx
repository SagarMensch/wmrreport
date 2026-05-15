"use client";

import { useEffect, useState } from "react";

import DataDictionary from "@/components/DataDictionary";
import DataIntegrity from "@/components/DataIntegrity";
import IntelligenceMatrix from "@/components/IntelligenceMatrix";

export type TrustLayerView = "integrity" | "dictionary" | "lineage";

export default function TrustLayer({
  initialView = "integrity",
}: {
  initialView?: TrustLayerView;
}) {
  const [view, setView] = useState<TrustLayerView>(initialView);

  useEffect(() => {
    setView(initialView);
  }, [initialView]);

  return (
    <div className="h-full overflow-hidden bg-[#0F0C0A]">
      <div className="border-b border-[rgba(185,150,100,0.08)] bg-[rgba(26,21,16,0.60)] px-6 py-4 backdrop-blur-[20px]">
        <div className="mx-auto flex max-w-[1540px] flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="text-[10px] font-semibold uppercase tracking-[0.28em] text-[#C9A96E]">
              Trust Layer
            </div>
            <div className="mt-2 text-[22px] font-semibold tracking-[-0.03em] text-[#EDE8DF]">
              Governance & auditability
            </div>
          </div>
          <div className="flex flex-wrap gap-1 rounded-[8px] border border-[rgba(185,150,100,0.10)] bg-[rgba(26,21,16,0.50)] p-1 backdrop-blur-[16px]">
            {([
              ["integrity", "Integrity"],
              ["dictionary", "Dictionary"],
              ["lineage", "Lineage Graph"],
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
        {view === "integrity" ? <DataIntegrity /> : null}
        {view === "dictionary" ? <DataDictionary /> : null}
        {view === "lineage" ? <IntelligenceMatrix /> : null}
      </div>
    </div>
  );
}

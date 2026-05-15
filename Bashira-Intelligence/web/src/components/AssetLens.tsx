"use client";

import { useEffect, useState } from "react";

import DelayHeatmap from "@/components/DelayHeatmap";
import EngineeringTimeline from "@/components/EngineeringTimeline";
import FieldAtlas from "@/components/FieldAtlas";
import LocationPreparation from "@/components/LocationPreparation";
import PortfolioCommand from "@/components/PortfolioCommand";
import RigOperations from "@/components/RigOperations";

export type AssetLensView =
  | "atlas"
  | "portfolio"
  | "rigs"
  | "readiness"
  | "engineering"
  | "heatmap";

export default function AssetLens({
  initialView = "atlas",
}: {
  initialView?: AssetLensView;
}) {
  const [view, setView] = useState<AssetLensView>(initialView);

  useEffect(() => {
    setView(initialView);
  }, [initialView]);

  return (
    <div className="min-h-full bg-[#FAFAFA]">
      <div className="border-b border-[#E5E5E5] bg-[#FFFFFF] px-6 py-4">
        <div className="mx-auto flex max-w-[1540px] flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="text-[10px] font-bold uppercase tracking-[0.28em] text-[#737373]">
              Asset Lens
            </div>
            <div className="mt-2 text-[22px] font-bold tracking-[-0.03em] text-[#1A1A1A]">
              Operational drilldown
            </div>
          </div>
          <div className="flex flex-wrap gap-1 rounded-[8px] border border-[#E5E5E5] bg-[#F5F5F5] p-1">
            {(
              [
                ["atlas", "Field Atlas"],
                ["portfolio", "Portfolio"],
                ["rigs", "Rig Control"],
                ["readiness", "Readiness"],
                ["engineering", "Engineering"],
                ["heatmap", "Variance"],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setView(key)}
                className={`rounded-[6px] px-3.5 py-2 text-[10px] font-bold uppercase tracking-[0.14em] transition-all duration-300 ${
                  view === key
                    ? "bg-[#FFFFFF] text-[#1A1A1A] shadow-sm ring-1 ring-black/5"
                    : "text-[#737373] hover:text-[#1A1A1A] hover:bg-black/5"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="min-h-0 pb-8">
        {view === "atlas" ? <FieldAtlas /> : null}
        {view === "portfolio" ? <PortfolioCommand /> : null}
        {view === "rigs" ? <RigOperations /> : null}
        {view === "readiness" ? <LocationPreparation /> : null}
        {view === "engineering" ? <EngineeringTimeline /> : null}
        {view === "heatmap" ? <DelayHeatmap /> : null}
      </div>
    </div>
  );
}

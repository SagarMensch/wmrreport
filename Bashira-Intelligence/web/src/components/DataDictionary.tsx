"use client";

import { useMemo, useState } from "react";

import {
  ErrorState,
  formatCompactNumber,
  formatPct,
  LoadingState,
  SectionHeader,
  SurfacePanel,
  TonePill,
} from "@/components/CommandCenterPrimitives";
import { useCommandCenterData } from "@/components/useCommandCenterData";

interface DictionaryColumn {
  table_name: string;
  column_name: string;
  data_type: string;
  description: string;
}

interface DictionaryTable {
  table_name: string;
  column_count: number;
  documented_columns: number;
  coverage_pct: number;
  columns: {
    column_name: string;
    data_type: string;
    description: string;
  }[];
}

interface DimensionRow {
  [key: string]: string | number;
  count: number;
}

interface DictionaryPayload {
  generated_at?: string;
  summary: {
    total_tables?: number;
    total_columns?: number;
    documented_columns?: number;
    coverage_pct?: number;
  };
  tables: DictionaryTable[];
  columns: DictionaryColumn[];
  dimensions: {
    projects: DimensionRow[];
    locations: DimensionRow[];
    well_types: DimensionRow[];
  };
}

const EMPTY_DATA: DictionaryPayload = {
  summary: {},
  tables: [],
  columns: [],
  dimensions: {
    projects: [],
    locations: [],
    well_types: [],
  },
};

type ViewMode = "tables" | "columns" | "dimensions";

function dimensionLabel(row: DimensionRow, primaryKey: string) {
  const value = row[primaryKey];
  return typeof value === "string" && value.trim() ? value : "Unknown";
}

export default function DataDictionary() {
  const { data, loading, error, refresh } = useCommandCenterData<DictionaryPayload>(
    "data_dictionary",
    EMPTY_DATA,
  );
  const [view, setView] = useState<ViewMode>("tables");
  const [query, setQuery] = useState("");
  const [selectedTable, setSelectedTable] = useState("");

  const normalizedQuery = query.trim().toLowerCase();

  const filteredTables = useMemo(() => {
    if (!normalizedQuery) return data.tables;
    return data.tables.filter((table) =>
      table.table_name.toLowerCase().includes(normalizedQuery),
    );
  }, [data.tables, normalizedQuery]);

  const activeTable =
    filteredTables.find((table) => table.table_name === selectedTable) ||
    filteredTables[0] ||
    null;

  const filteredColumns = useMemo(() => {
    return data.columns.filter((column) => {
      const matchesTable =
        !selectedTable || column.table_name === selectedTable || view !== "columns";
      const matchesQuery =
        !normalizedQuery ||
        column.table_name.toLowerCase().includes(normalizedQuery) ||
        column.column_name.toLowerCase().includes(normalizedQuery) ||
        column.description.toLowerCase().includes(normalizedQuery);
      return matchesTable && matchesQuery;
    });
  }, [data.columns, normalizedQuery, selectedTable, view]);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto flex w-full max-w-[1540px] flex-col gap-4 px-5 py-5">
        <SectionHeader
          kicker="Data Dictionary"
          title="Schema governance & coverage"
          subtitle={`${formatCompactNumber(data.summary.total_tables)} tables · ${formatCompactNumber(data.summary.total_columns)} columns · ${formatPct(data.summary.coverage_pct)} documented`}
          aside={
            <div className="flex items-center gap-3">
              <button
                onClick={() => void refresh()}
                className="rounded-[8px] border border-[rgba(185,150,100,0.14)] bg-[rgba(26,21,16,0.6)] px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#C9A96E] backdrop-blur-[16px] transition-all duration-300 hover:border-[rgba(185,150,100,0.28)] hover:text-[#EDE8DF]"
              >
                Refresh
              </button>
              <div className="flex gap-1 rounded-[8px] border border-[rgba(185,150,100,0.10)] bg-[rgba(26,21,16,0.50)] p-1 backdrop-blur-[16px]">
                {(["tables", "columns", "dimensions"] as const).map((item) => (
                  <button
                    key={item}
                    onClick={() => setView(item)}
                    className={`rounded-[6px] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] transition-all duration-300 ${
                      view === item
                        ? "bg-[rgba(201,169,110,0.15)] text-[#C9A96E] border border-[rgba(201,169,110,0.30)]"
                        : "text-[#6B6259] hover:text-[#9A8B78] border border-transparent"
                    }`}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
          }
        />

        {loading ? <LoadingState label="Indexing schema surfaces…" /> : null}
        {error ? <ErrorState message={error} /> : null}

        {!loading && !error ? (
          <>
            {/* KPI Strip */}
            <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
              {[
                { label: "Tables", value: formatCompactNumber(data.summary.total_tables), accent: "#C9A96E" },
                { label: "Columns", value: formatCompactNumber(data.summary.total_columns), accent: "#9A8B78" },
                { label: "Documented", value: formatCompactNumber(data.summary.documented_columns), accent: "#5BA88C" },
                { label: "Coverage", value: formatPct(data.summary.coverage_pct), accent: "#D4A04A" },
              ].map((m) => (
                <div
                  key={m.label}
                  className="group rounded-[10px] border border-[rgba(185,150,100,0.08)] bg-[rgba(26,21,16,0.65)] px-4 py-3 backdrop-blur-[16px] transition-all duration-300 hover:border-[rgba(185,150,100,0.18)]"
                >
                  <div className="text-[9px] font-semibold uppercase tracking-[0.22em] text-[#6B6259]">
                    {m.label}
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="text-data mt-1 text-[22px] font-semibold tracking-[-0.02em] text-[#EDE8DF]">
                      {m.value}
                    </div>
                    <div
                      className="h-5 w-[2px] rounded-full opacity-40 transition-opacity group-hover:opacity-80"
                      style={{ backgroundColor: m.accent }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Search bar */}
            <SurfacePanel className="px-5 py-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#C9A96E]">
                    Explorer
                  </div>
                </div>
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search table, column, or description"
                  className="w-full rounded-[10px] border border-[rgba(185,150,100,0.12)] bg-[rgba(35,28,21,0.50)] px-4 py-2.5 text-[13px] text-[#EDE8DF] outline-none transition-all placeholder:text-[#6B6259] focus:border-[rgba(201,169,110,0.35)] lg:max-w-[420px]"
                />
              </div>
            </SurfacePanel>

            {view === "tables" ? (
              <div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
                <SurfacePanel className="p-5">
                  <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#C9A96E]">
                    Tables
                  </div>
                  <div className="mt-1 text-[14px] font-semibold text-[#EDE8DF]">
                    Coverage-ranked inventory
                  </div>
                  <div className="mt-4 space-y-2">
                    {filteredTables.map((table) => (
                      <button
                        key={table.table_name}
                        onClick={() => setSelectedTable(table.table_name)}
                        className={`w-full rounded-[10px] border p-3.5 text-left transition-all duration-300 ${
                          activeTable?.table_name === table.table_name
                            ? "border-[rgba(201,169,110,0.30)] bg-[rgba(201,169,110,0.10)]"
                            : "border-[rgba(185,150,100,0.08)] bg-[rgba(35,28,21,0.40)] hover:border-[rgba(185,150,100,0.16)]"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <div className="text-[12px] font-semibold text-[#EDE8DF]">{table.table_name}</div>
                            <div className="mt-0.5 text-[10px] text-[#6B6259]">
                              {table.documented_columns} of {table.column_count} documented
                            </div>
                          </div>
                          <TonePill
                            label={formatPct(table.coverage_pct)}
                            tone={table.coverage_pct >= 80 ? "positive" : "warning"}
                          />
                        </div>
                      </button>
                    ))}
                  </div>
                </SurfacePanel>

                <SurfacePanel className="overflow-hidden">
                  <div className="border-b border-[rgba(185,150,100,0.08)] px-5 py-4">
                    <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#C9A96E]">
                      Selected Table
                    </div>
                    <div className="mt-1.5 flex flex-wrap items-center gap-2">
                      <div className="text-[18px] font-semibold text-[#EDE8DF]">
                        {activeTable?.table_name || "No match"}
                      </div>
                      {activeTable ? (
                        <>
                          <TonePill label={`${activeTable.column_count} cols`} tone="neutral" />
                          <TonePill label={`${activeTable.documented_columns} doc`} tone="positive" />
                        </>
                      ) : null}
                    </div>
                  </div>

                  <div className="divide-y divide-[rgba(185,150,100,0.06)]">
                    {(activeTable?.columns || []).map((column) => (
                      <div
                        key={`${activeTable?.table_name}-${column.column_name}`}
                        className="grid grid-cols-1 gap-3 px-5 py-3 lg:grid-cols-[220px_120px_minmax(0,1fr)]"
                      >
                        <div className="text-[12px] font-semibold text-[#EDE8DF]">
                          {column.column_name}
                        </div>
                        <div>
                          <span className="rounded-[6px] bg-[rgba(185,150,100,0.10)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#9A8B78]">
                            {column.data_type || "Unknown"}
                          </span>
                        </div>
                        <div className="text-[12px] leading-5 text-[#7A6E62]">
                          {column.description}
                        </div>
                      </div>
                    ))}
                  </div>
                </SurfacePanel>
              </div>
            ) : null}

            {view === "columns" ? (
              <SurfacePanel className="overflow-hidden">
                <div className="flex flex-col gap-3 border-b border-[rgba(185,150,100,0.08)] px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#C9A96E]">
                      Column Explorer
                    </div>
                    <div className="mt-1 text-[14px] font-semibold text-[#EDE8DF]">
                      Full field inventory
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <button
                      onClick={() => setSelectedTable("")}
                      className={`rounded-[6px] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] transition-all duration-300 ${
                        !selectedTable
                          ? "bg-[rgba(201,169,110,0.15)] text-[#C9A96E] border border-[rgba(201,169,110,0.30)]"
                          : "text-[#6B6259] hover:text-[#9A8B78] border border-[rgba(185,150,100,0.08)]"
                      }`}
                    >
                      All Tables
                    </button>
                    {data.tables.slice(0, 10).map((table) => (
                      <button
                        key={table.table_name}
                        onClick={() => setSelectedTable(table.table_name)}
                        className={`rounded-[6px] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] transition-all duration-300 ${
                          selectedTable === table.table_name
                            ? "bg-[rgba(201,169,110,0.15)] text-[#C9A96E] border border-[rgba(201,169,110,0.30)]"
                            : "text-[#6B6259] hover:text-[#9A8B78] border border-[rgba(185,150,100,0.08)]"
                        }`}
                      >
                        {table.table_name}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-[200px_180px_minmax(0,1fr)] gap-0 border-b border-[rgba(185,150,100,0.06)] bg-[rgba(35,28,21,0.30)] px-5 py-2.5 text-[9px] font-semibold uppercase tracking-[0.18em] text-[#6B6259]">
                  <div>Table / Column</div>
                  <div>Type</div>
                  <div>Description</div>
                </div>

                <div className="divide-y divide-[rgba(185,150,100,0.06)]">
                  {filteredColumns.slice(0, 180).map((column) => (
                    <div
                      key={`${column.table_name}-${column.column_name}`}
                      className="grid grid-cols-1 gap-3 px-5 py-3 lg:grid-cols-[200px_180px_minmax(0,1fr)]"
                    >
                      <div>
                        <div className="text-[9px] font-semibold uppercase tracking-[0.14em] text-[#6B6259]">
                          {column.table_name}
                        </div>
                        <div className="mt-1 text-[12px] font-semibold text-[#EDE8DF]">
                          {column.column_name}
                        </div>
                      </div>
                      <div>
                        <span className="inline-flex rounded-[6px] bg-[rgba(185,150,100,0.10)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#9A8B78]">
                          {column.data_type || "Unknown"}
                        </span>
                      </div>
                      <div className="text-[12px] leading-5 text-[#7A6E62]">
                        {column.description}
                      </div>
                    </div>
                  ))}
                </div>
              </SurfacePanel>
            ) : null}

            {view === "dimensions" ? (
              <div className="grid gap-4 xl:grid-cols-3">
                {[
                  { title: "Project Slice", sub: "Wells by project", data: data.dimensions.projects, key: "project" },
                  { title: "Location Slice", sub: "Wells by cluster", data: data.dimensions.locations, key: "cluster" },
                  { title: "Well Type Slice", sub: "Wells by type", data: data.dimensions.well_types, key: "well_type" },
                ].map((section) => (
                  <SurfacePanel key={section.title} className="p-5">
                    <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#C9A96E]">
                      {section.title}
                    </div>
                    <div className="mt-1 text-[14px] font-semibold text-[#EDE8DF]">
                      {section.sub}
                    </div>
                    <div className="mt-4 space-y-2">
                      {section.data.map((row) => (
                        <div
                          key={`${section.key}-${dimensionLabel(row, section.key)}`}
                          className="flex items-center justify-between rounded-[8px] border border-[rgba(185,150,100,0.06)] bg-[rgba(35,28,21,0.40)] px-3.5 py-2.5"
                        >
                          <span className="text-[12px] font-medium text-[#EDE8DF]">
                            {dimensionLabel(row, section.key)}
                          </span>
                          <TonePill label={String(row.count)} tone="neutral" />
                        </div>
                      ))}
                    </div>
                  </SurfacePanel>
                ))}
              </div>
            ) : null}
          </>
        ) : null}
      </div>
    </div>
  );
}

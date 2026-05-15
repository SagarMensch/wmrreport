"use client";

import { useEffect, useMemo, useState } from "react";

type Summary = {
  open_exceptions: number;
  critical: number;
  missing_data: number;
  logic_violations: number;
  task_daily_rows: number;
  activity_task_plan_rows: number;
};

type SourceCard = {
  id: string;
  label: string;
  exception_count: number;
  row_count: number;
};

type RuleCard = {
  id: string;
  rule_code: string;
  title: string;
  source: string;
  source_label: string;
  severity: string;
  category: string;
  summary: string;
  exception_count: number;
  status_label: string;
  evaluation_basis: string;
};

type RuleViewRow = {
  values: Record<string, string | number | null>;
  failed_fields: string[];
};

type RuleView = {
  id: string;
  rule_code: string;
  title: string;
  source: string;
  source_label: string;
  severity: string;
  client_rule: string;
  technical_logic: string;
  evaluation_basis?: string;
  expected: string;
  recommendation: string;
  base_total_violations: number;
  total_violations: number;
  showing_rows: number;
  page: number;
  page_size: number;
  page_start: number;
  page_end: number;
  has_prev_page: boolean;
  has_next_page: boolean;
  date_field?: string | null;
  available_date_range?: {
    min: string | null;
    max: string | null;
  };
  date_from?: string | null;
  date_to?: string | null;
  sql: string;
  columns: string[];
  rows: RuleViewRow[];
  note: string;
};

type PrimaryFocus = {
  rule: string;
  title: string;
  source_label: string;
  severity: string;
  exception_count: number;
  message: string;
};

type ExceptionItem = {
  id: string;
  rule_id: string;
  rule_code: string;
  rule_title: string;
  source: string;
  source_label: string;
  severity: string;
  category: string;
  key: string;
  record_id: string;
  record_date: string | null;
  title: string;
  summary: string;
  failed_fields: string[];
  expected: string;
  recommendation: string;
  values: Record<string, string | number | null>;
  action_url?: string | null;
};

type TableScope = {
  source: string;
  label: string;
  row_count: number;
};

type TaskDailyActivation = {
  mode: string;
  label: string;
  note: string;
  basis_label: string;
  basis_detail: string;
  total_rows: number;
  applicable_rows: number;
  url_linked_rows: number;
  operational_rows: number;
  fallback_active: boolean;
};

type DataIntegrityResponse = {
  generated_at: string;
  workspace_name: string;
  objective: string;
  summary: Summary;
  source_cards: SourceCard[];
  rule_cards: RuleCard[];
  rule_views: Record<string, RuleView>;
  exceptions: ExceptionItem[];
  primary_focus: PrimaryFocus;
  table_scope: {
    task_daily: TableScope;
    ActivityTaskPlan: TableScope;
  };
  activation_context: {
    task_daily: TaskDailyActivation;
  };
  cache_age_seconds: number;
};

type SourceFilter = "all" | "task_daily" | "ActivityTaskPlan";
type SeverityFilter = "all" | "critical" | "high" | "medium" | "clear";
type EvidenceTab = "rows" | "sql" | "logic";
type InspectorPane = "overview" | "logic" | "values";
type SurfacePane = "rules" | "queue" | "detail";

const numberFormatter = new Intl.NumberFormat("en-US");
const RULE_VIEW_PAGE_SIZE = 60;
const dateFormatter = new Intl.DateTimeFormat("en-GB", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

const severityTokens: Record<
  string,
  { chipBg: string; chipText: string; border: string; accent: string }
> = {
  critical: {
    chipBg: "rgba(212,99,111,0.15)",
    chipText: "#D4636F",
    border: "rgba(212,99,111,0.28)",
    accent: "#D4636F",
  },
  high: {
    chipBg: "rgba(232,119,34,0.15)",
    chipText: "#E87722",
    border: "rgba(232,119,34,0.28)",
    accent: "#E87722",
  },
  medium: {
    chipBg: "rgba(212,160,74,0.15)",
    chipText: "#D4A04A",
    border: "rgba(212,160,74,0.28)",
    accent: "#D4A04A",
  },
  clear: {
    chipBg: "rgba(91,168,140,0.15)",
    chipText: "#5BA88C",
    border: "rgba(91,168,140,0.28)",
    accent: "#5BA88C",
  },
};

function getDataIntegrityEndpoint(): string {
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      return "http://127.0.0.1:8005/api/data-integrity";
    }
  }
  return "/api/data-integrity";
}

function getDataIntegrityRuleViewEndpoint(): string {
  const base = getDataIntegrityEndpoint();
  return `${base}/rule-view`;
}

async function fetchWithTimeout(url: string, timeoutMs: number) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      method: "GET",
      cache: "no-store",
      signal: controller.signal,
    });
    return response;
  } finally {
    window.clearTimeout(timeout);
  }
}

function formatDate(value?: string | null) {
  if (!value) return "Not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return dateFormatter.format(date);
}

function formatValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "NULL";
  }
  if (typeof value === "number") {
    return Number.isInteger(value)
      ? numberFormatter.format(value)
      : value.toLocaleString("en-US", { maximumFractionDigits: 2 });
  }
  return String(value);
}

function severityRank(value: string) {
  if (value === "critical") return 0;
  if (value === "high") return 1;
  if (value === "medium") return 2;
  return 3;
}

export default function DataIntegrity() {
  const [workspace, setWorkspace] = useState<DataIntegrityResponse | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>("all");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [selectedRule, setSelectedRule] = useState<string>("ALL");
  const [selectedExceptionId, setSelectedExceptionId] = useState<string>("");
  const [searchInput, setSearchInput] = useState("");
  const [activeRuleViewId, setActiveRuleViewId] = useState<string>("");
  const [activeRuleViewData, setActiveRuleViewData] = useState<RuleView | null>(
    null,
  );
  const [ruleViewLoading, setRuleViewLoading] = useState(false);
  const [ruleViewError, setRuleViewError] = useState("");
  const [ruleViewPage, setRuleViewPage] = useState(1);
  const [ruleViewDateFromInput, setRuleViewDateFromInput] = useState("");
  const [ruleViewDateToInput, setRuleViewDateToInput] = useState("");
  const [ruleViewDateFromApplied, setRuleViewDateFromApplied] = useState("");
  const [ruleViewDateToApplied, setRuleViewDateToApplied] = useState("");
  const [ruleViewExporting, setRuleViewExporting] = useState(false);
  const [evidenceTab, setEvidenceTab] = useState<EvidenceTab>("rows");
  const [inspectorPane, setInspectorPane] = useState<InspectorPane>("overview");
  const [surfacePane, setSurfacePane] = useState<SurfacePane | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const response = await fetchWithTimeout(
          getDataIntegrityEndpoint(),
          120000,
        );
        if (!response.ok) {
          const detail = await response.text();
          throw new Error(detail || `Request failed with ${response.status}`);
        }
        const data = (await response.json()) as DataIntegrityResponse;
        if (!cancelled) {
          setWorkspace(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load data integrity workspace",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!activeRuleViewId) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [activeRuleViewId]);

  useEffect(() => {
    if (!surfacePane || activeRuleViewId) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [surfacePane, activeRuleViewId]);

  useEffect(() => {
    if (!activeRuleViewId) {
      setActiveRuleViewData(null);
      setRuleViewError("");
      return;
    }

    let cancelled = false;

    async function loadRuleView() {
      setRuleViewLoading(true);
      setRuleViewError("");
      setActiveRuleViewData(null);
      try {
        const params = new URLSearchParams({
          rule_id: activeRuleViewId,
          page: String(ruleViewPage),
          page_size: String(RULE_VIEW_PAGE_SIZE),
        });
        if (ruleViewDateFromApplied) {
          params.set("date_from", ruleViewDateFromApplied);
        }
        if (ruleViewDateToApplied) {
          params.set("date_to", ruleViewDateToApplied);
        }
        const response = await fetchWithTimeout(
          `${getDataIntegrityRuleViewEndpoint()}?${params.toString()}`,
          120000,
        );
        if (!response.ok) {
          const detail = await response.text();
          throw new Error(detail || `Request failed with ${response.status}`);
        }
        const data = (await response.json()) as RuleView;
        if (!cancelled) {
          setActiveRuleViewData(data);
          setRuleViewDateFromInput(data.date_from ?? ruleViewDateFromApplied);
          setRuleViewDateToInput(data.date_to ?? ruleViewDateToApplied);
        }
      } catch (err) {
        if (!cancelled) {
          setRuleViewError(
            err instanceof Error ? err.message : "Failed to load SSMS view",
          );
        }
      } finally {
        if (!cancelled) {
          setRuleViewLoading(false);
        }
      }
    }

    void loadRuleView();
    return () => {
      cancelled = true;
    };
  }, [
    activeRuleViewId,
    ruleViewDateFromApplied,
    ruleViewDateToApplied,
    ruleViewPage,
  ]);

  const searchNeedle = searchInput.trim().toLowerCase();

  const filteredRuleCards = useMemo(() => {
    if (!workspace) return [];
    return [...workspace.rule_cards]
      .filter((rule) => {
        const sourceMatch =
          sourceFilter === "all" || rule.source === sourceFilter;
        const severityMatch =
          severityFilter === "all" || rule.severity === severityFilter;
        const searchMatch =
          !searchNeedle ||
          [
            rule.rule_code,
            rule.title,
            rule.source_label,
            rule.category,
            rule.summary,
          ]
            .join(" ")
            .toLowerCase()
            .includes(searchNeedle);
        return sourceMatch && severityMatch && searchMatch;
      })
      .sort((left, right) => {
        const severityDiff =
          severityRank(left.severity) - severityRank(right.severity);
        if (severityDiff !== 0) return severityDiff;
        return right.exception_count - left.exception_count;
      });
  }, [workspace, searchNeedle, severityFilter, sourceFilter]);

  const ruleNavigatorCards = useMemo(() => {
    if (!workspace) return [];
    return [...workspace.rule_cards].sort((left, right) => {
      const severityDiff =
        severityRank(left.severity) - severityRank(right.severity);
      if (severityDiff !== 0) return severityDiff;
      return right.exception_count - left.exception_count;
    });
  }, [workspace]);

  const filteredExceptions = useMemo(() => {
    if (!workspace) return [];
    return workspace.exceptions.filter((item) => {
      const sourceMatch =
        sourceFilter === "all" || item.source === sourceFilter;
      const ruleMatch = selectedRule === "ALL" || item.rule_id === selectedRule;
      const severityMatch =
        severityFilter === "all" || item.severity === severityFilter;
      const searchMatch =
        !searchNeedle ||
        [
          item.rule_code,
          item.rule_title,
          item.source_label,
          item.key,
          item.record_id,
          item.summary,
          item.title,
          item.failed_fields.join(" "),
        ]
          .join(" ")
          .toLowerCase()
          .includes(searchNeedle);
      return sourceMatch && ruleMatch && severityMatch && searchMatch;
    });
  }, [workspace, searchNeedle, selectedRule, severityFilter, sourceFilter]);

  const visibleExceptions = useMemo(
    () => filteredExceptions.slice(0, 36),
    [filteredExceptions],
  );

  const selectedException = useMemo(() => {
    if (!visibleExceptions.length) return null;
    return (
      visibleExceptions.find((item) => item.id === selectedExceptionId) ??
      visibleExceptions[0]
    );
  }, [selectedExceptionId, visibleExceptions]);

  const selectedRuleMeta = useMemo(() => {
    if (!workspace || selectedRule === "ALL") return null;
    return (
      workspace.rule_cards.find((item) => item.id === selectedRule) ?? null
    );
  }, [selectedRule, workspace]);

  const severityDistribution = useMemo(() => {
    const distribution = {
      critical: 0,
      high: 0,
      medium: 0,
      clear: 0,
    };
    if (!workspace) return distribution;
    for (const rule of workspace.rule_cards) {
      const key = rule.severity as keyof typeof distribution;
      if (key in distribution) {
        distribution[key] += rule.exception_count;
      }
    }
    return distribution;
  }, [workspace]);

  const activeRuleView = activeRuleViewData;

  useEffect(() => {
    if (!visibleExceptions.length) {
      setSelectedExceptionId("");
      return;
    }
    if (!visibleExceptions.some((item) => item.id === selectedExceptionId)) {
      setSelectedExceptionId(visibleExceptions[0].id);
    }
  }, [selectedExceptionId, visibleExceptions]);

  useEffect(() => {
    setInspectorPane("overview");
  }, [selectedExceptionId]);

  function resetFilters() {
    setSearchInput("");
    setSourceFilter("all");
    setSeverityFilter("all");
    setSelectedRule("ALL");
    setSurfacePane(null);
  }

  function focusRule(ruleId: string, source: SourceFilter) {
    setSelectedRule(ruleId);
    setSourceFilter(source);
    setSurfacePane(null);
  }

  function openRuleView(ruleId: string) {
    setActiveRuleViewId(ruleId);
    setActiveRuleViewData(null);
    setRuleViewError("");
    setRuleViewPage(1);
    setRuleViewDateFromInput("");
    setRuleViewDateToInput("");
    setRuleViewDateFromApplied("");
    setRuleViewDateToApplied("");
    setEvidenceTab("rows");
  }

  function closeRuleView() {
    setActiveRuleViewId("");
    setActiveRuleViewData(null);
    setRuleViewError("");
    setRuleViewLoading(false);
    setRuleViewPage(1);
    setRuleViewDateFromInput("");
    setRuleViewDateToInput("");
    setRuleViewDateFromApplied("");
    setRuleViewDateToApplied("");
    setRuleViewExporting(false);
  }

  function applyRuleViewFilters() {
    setRuleViewPage(1);
    setRuleViewDateFromApplied(ruleViewDateFromInput);
    setRuleViewDateToApplied(ruleViewDateToInput);
  }

  function clearRuleViewFilters() {
    setRuleViewPage(1);
    setRuleViewDateFromInput("");
    setRuleViewDateToInput("");
    setRuleViewDateFromApplied("");
    setRuleViewDateToApplied("");
  }

  async function exportRuleViewCsv() {
    if (!activeRuleViewId) return;
    setRuleViewExporting(true);
    try {
      const params = new URLSearchParams({
        rule_id: activeRuleViewId,
        format: "csv",
      });
      if (ruleViewDateFromApplied) {
        params.set("date_from", ruleViewDateFromApplied);
      }
      if (ruleViewDateToApplied) {
        params.set("date_to", ruleViewDateToApplied);
      }
      const response = await fetchWithTimeout(
        `${getDataIntegrityRuleViewEndpoint()}?${params.toString()}`,
        120000,
      );
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || `CSV export failed with ${response.status}`);
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const ruleCode = activeRuleView?.rule_code || activeRuleViewId;
      const suffix =
        ruleViewDateFromApplied || ruleViewDateToApplied
          ? `_${ruleViewDateFromApplied || "start"}_${ruleViewDateToApplied || "end"}`
          : "";
      const link = document.createElement("a");
      link.href = url;
      link.download = `${ruleCode.replace(/[^A-Za-z0-9]+/g, "_").toLowerCase()}${suffix}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setRuleViewError(
        err instanceof Error ? err.message : "Failed to export CSV",
      );
    } finally {
      setRuleViewExporting(false);
    }
  }

  function runQuickCommand(command: string) {
    const normalized = command.toLowerCase();
    setSearchInput(command);
    setSurfacePane(null);

    if (normalized.includes("task daily")) {
      setSourceFilter("task_daily");
    } else if (normalized.includes("task plan")) {
      setSourceFilter("ActivityTaskPlan");
    } else {
      setSourceFilter("all");
    }

    if (normalized.includes("critical")) {
      setSeverityFilter("critical");
    } else if (normalized.includes("high")) {
      setSeverityFilter("high");
    } else if (normalized.includes("medium")) {
      setSeverityFilter("medium");
    }

    if (!workspace) return;
    const matchedRule = workspace.rule_cards.find((rule) =>
      `${rule.rule_code} ${rule.title}`.toLowerCase().includes(normalized),
    );
    setSelectedRule(matchedRule?.id ?? "ALL");
  }

  if (loading) {
    return (
      <div
        className="w-full min-h-full flex items-center justify-center bg-white p-8"
        style={{ fontFamily: '"Figtree", sans-serif' }}
      >
        <div
          className="flex flex-col items-center gap-4 rounded-[24px] border bg-white px-9 py-8 shadow-[0_24px_80px_rgba(15,23,42,0.06)]"
          style={{ borderColor: "rgba(15,23,42,0.08)" }}
        >
          <div
            className="w-11 h-11 rounded-full animate-spin"
            style={{
              border: "3px solid rgba(15,23,42,0.10)",
              borderTopColor: "#0F62FE",
            }}
          />
          <div className="text-center">
            <div className="text-[11px] tracking-[0.28em] uppercase text-[#667085]">
              Data Integrity
            </div>
            <div className="mt-2 text-[18px] font-medium text-[#111827]">
              Loading control surface
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !workspace) {
    return (
      <div
        className="w-full min-h-full flex items-center justify-center bg-white p-8"
        style={{ fontFamily: '"Figtree", sans-serif' }}
      >
        <div
          className="max-w-[560px] w-full rounded-[24px] border bg-white p-7 shadow-[0_24px_80px_rgba(15,23,42,0.06)]"
          style={{ borderColor: "rgba(15,23,42,0.08)" }}
        >
          <div className="text-[11px] uppercase tracking-[0.28em] text-[#667085]">
            Data Integrity
          </div>
          <div className="mt-3 text-[22px] font-medium text-[#111827]">
            Integrity control unavailable
          </div>
          <div className="mt-2 text-[13px] leading-6 text-[#667085]">
            {error || "The integrity workspace could not be loaded."}
          </div>
        </div>
      </div>
    );
  }

  const taskDailyContext = workspace.activation_context.task_daily;
  const focusRuleCard =
    selectedRuleMeta ??
    workspace.rule_cards.find(
      (card) => card.rule_code === workspace.primary_focus.rule,
    ) ??
    workspace.rule_cards[0];
  const inspectorRuleMeta =
    (selectedException
      ? workspace.rule_cards.find((rule) => rule.id === selectedException.rule_id)
      : null) ??
    selectedRuleMeta ??
    focusRuleCard;
  const inspectorRuleView = workspace.rule_views[inspectorRuleMeta.id] ?? null;
  const compactMetrics = [
    { label: "Open", value: workspace.summary.open_exceptions, accent: "#111827" },
    { label: "Critical", value: workspace.summary.critical, accent: "#B42318" },
    { label: "Task Daily", value: workspace.summary.task_daily_rows, accent: "#0F62FE" },
    {
      label: "Task Plan",
      value: workspace.summary.activity_task_plan_rows,
      accent: "#00A36C",
    },
  ];

  return (
    <div
      className="w-full h-full overflow-y-auto lg:overflow-hidden bg-white text-[#111827]"
      style={{ fontFamily: '"Figtree", sans-serif', fontSize: "80%" }}
    >
      <div className="mx-auto flex h-full max-w-[1680px] flex-col gap-4 px-6 py-5">
        <section
          className="shrink-0 rounded-[24px] bg-[#FFFFFF] px-5 py-4"
          style={{
            border: "1px solid rgba(15,23,42,0.08)",
            boxShadow: "0 24px 80px rgba(15,23,42,0.05)",
          }}
        >
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-3 2xl:flex-row 2xl:items-center 2xl:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2.5">
                  <div className="text-[10px] uppercase tracking-[0.30em] text-[#98A2B3]">
                    {workspace.workspace_name}
                  </div>
                  <div
                    className="rounded-full border bg-[#F8FAFC] px-2.5 py-1 text-[10px] font-medium text-[#111827]"
                    style={{ borderColor: "rgba(15,23,42,0.08)" }}
                  >
                    {taskDailyContext.label}
                  </div>
                  <div className="text-[11px] text-[#667085]">
                    Activation {taskDailyContext.basis_label}
                  </div>
                </div>
                <div className="mt-2 flex flex-wrap items-end gap-3">
                  <div className="text-[24px] leading-none font-medium text-[#111827]">
                    Integrity Control
                  </div>
                  <div className="text-[11px] text-[#667085]">
                    Rule governance | queue triage | SSMS evidence
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {compactMetrics.map((chip) => (
                  <div
                    key={chip.label}
                    className="inline-flex items-center gap-2 rounded-full border bg-[#FCFCFD] px-3 py-1.5"
                    style={{ borderColor: "rgba(15,23,42,0.08)" }}
                  >
                    <span className="text-[10px] uppercase tracking-[0.20em] text-[#667085]">
                      {chip.label}
                    </span>
                    <span className="text-[13px] font-semibold" style={{ color: chip.accent }}>
                      {typeof chip.value === "number" ? numberFormatter.format(chip.value) : chip.value}
                    </span>
                  </div>
                ))}
                <div
                  className="inline-flex items-center gap-2 rounded-full border bg-[#FCFCFD] px-3 py-1.5"
                  style={{ borderColor: "rgba(15,23,42,0.08)" }}
                >
                  <span className="text-[10px] uppercase tracking-[0.20em] text-[#667085]">
                    Cache
                  </span>
                  <span className="text-[13px] font-semibold text-[#667085]">
                    {workspace.cache_age_seconds}s
                  </span>
                </div>
              </div>
            </div>

            <div className="grid gap-2 lg:grid-cols-12">
              <select
                value={selectedRule}
                onChange={(event) => {
                  const value = event.target.value;
                  if (value === "ALL") {
                    setSelectedRule("ALL");
                    setSurfacePane(null);
                    return;
                  }
                  const rule = workspace.rule_cards.find((item) => item.id === value);
                  if (rule) {
                    focusRule(rule.id, rule.source as SourceFilter);
                  }
                }}
                className="h-10 w-full rounded-[14px] bg-[#FFFFFF] px-4 text-[12px] text-[#111827] outline-none lg:col-span-3"
                style={{ border: "1px solid rgba(15,23,42,0.08)" }}
              >
                <option value="ALL">Rule Focus | All rules</option>
                {ruleNavigatorCards.map((rule) => (
                  <option key={rule.id} value={rule.id}>
                    {rule.rule_code} | {rule.title} | {numberFormatter.format(rule.exception_count)} hits
                  </option>
                ))}
              </select>
              <input
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="Search rule, task code, well, record, or summary"
                className="h-10 w-full rounded-[14px] px-4 text-[12px] text-[#111827] bg-[#FFFFFF] outline-none lg:col-span-5"
                style={{ border: "1px solid rgba(15,23,42,0.08)" }}
              />
              <button
                type="button"
                onClick={() => openRuleView(selectedRuleMeta?.id || focusRuleCard.id)}
                className="h-10 px-4 rounded-[14px] text-[11px] font-medium bg-[#111827] text-[#FFFFFF] lg:col-span-2"
              >
                SSMS View
              </button>
              <button
                type="button"
                onClick={resetFilters}
                className="h-10 px-4 rounded-[14px] text-[11px] font-medium text-[#111827] bg-[#FFFFFF] lg:col-span-2"
                style={{ border: "1px solid rgba(15,23,42,0.08)" }}
              >
                Reset
              </button>
            </div>

            <div className="flex flex-col gap-2 xl:flex-row xl:items-center xl:justify-between">
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="text-[9px] uppercase tracking-[0.24em] text-[#667085]">
                    Source
                  </div>
                  {workspace.source_cards.map((card) => {
                    const active = sourceFilter === card.id;
                    return (
                      <button
                        key={card.id}
                        type="button"
                        onClick={() => {
                          setSourceFilter(card.id as SourceFilter);
                          setSelectedRule("ALL");
                        }}
                        className="px-3 py-1.5 rounded-full text-[10px] font-medium transition-all"
                        style={{
                          background: active ? "#111827" : "#FFFFFF",
                          color: active ? "#FFFFFF" : "#111827",
                          border: active
                            ? "1px solid rgba(17,24,39,0.96)"
                            : "1px solid rgba(15,23,42,0.08)",
                        }}
                      >
                        {card.label} | {numberFormatter.format(card.exception_count)}
                      </button>
                    );
                  })}
                </div>

                <div className="h-4 w-px bg-[rgba(15,23,42,0.08)]" />

                <div className="flex flex-wrap items-center gap-2">
                  <div className="text-[9px] uppercase tracking-[0.24em] text-[#667085]">
                    Severity
                  </div>
                  {(
                    ["all", "critical", "high", "medium", "clear"] as SeverityFilter[]
                  ).map((severity) => {
                    const active = severityFilter === severity;
                    return (
                      <button
                        key={severity}
                        type="button"
                        onClick={() => setSeverityFilter(severity)}
                        className="px-3 py-1.5 rounded-full text-[10px] font-medium transition-all"
                        style={{
                          background: active ? "#111827" : "#FFFFFF",
                          color: active ? "#FFFFFF" : "#111827",
                          border: active
                            ? "1px solid rgba(17,24,39,0.96)"
                            : "1px solid rgba(15,23,42,0.08)",
                        }}
                      >
                        {severity === "all"
                          ? "All"
                          : severity.charAt(0).toUpperCase() + severity.slice(1)}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div
                className="inline-flex max-w-full items-center gap-2 rounded-full border bg-[#FCFCFD] px-3 py-1.5 text-[11px] text-[#667085]"
                style={{ borderColor: "rgba(15,23,42,0.08)" }}
              >
                <span className="uppercase tracking-[0.22em] text-[#98A2B3]">
                  Active
                </span>
                <span className="truncate text-[#111827]">
                  {focusRuleCard.rule_code} | {numberFormatter.format(focusRuleCard.exception_count)} hits | {taskDailyContext.basis_detail}
                </span>
              </div>
            </div>
          </div>
        </section>

        <section className="shrink-0">
          <div className="grid gap-3 lg:grid-cols-3">
            {[
              {
                id: "rules" as SurfacePane,
                eyebrow: "Rule Stack",
                title: "Five-rule registry",
                accent: "#FACC15",
                accentText: "#111827",
                border: "rgba(202,138,4,0.22)",
                summary: "Open the rule registry and inspect all five rule outcomes in one focused surface.",
                badge: numberFormatter.format(ruleNavigatorCards.length),
              },
              {
                id: "queue" as SurfacePane,
                eyebrow: "Exception Queue",
                title: `${numberFormatter.format(filteredExceptions.length)} open hits`,
                accent: "#B42318",
                accentText: "#FFFFFF",
                border: "rgba(180,35,24,0.18)",
                summary: "Open the queue in a dedicated red work surface and move row by row without crowding the page.",
                badge: focusRuleCard.rule_code,
              },
              {
                id: "detail" as SurfacePane,
                eyebrow: "Record Detail",
                title: selectedException ? selectedException.key : "No row selected",
                accent: "#0F62FE",
                accentText: "#FFFFFF",
                border: "rgba(15,98,254,0.18)",
                summary: "Open a compact record dossier where the selected row is readable in one controlled frame.",
                badge: selectedException ? "Live" : "Empty",
              },
            ].map((card) => (
              <button
                key={card.id}
                type="button"
                onClick={() => setSurfacePane(card.id)}
                disabled={card.id === "detail" && !selectedException}
                className="rounded-[24px] bg-[#FFFFFF] p-4 text-left transition-all hover:translate-y-[-1px] disabled:cursor-not-allowed disabled:opacity-50"
                style={{
                  border: `1px solid ${card.border}`,
                  boxShadow: "0 18px 56px rgba(15,23,42,0.04)",
                }}
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-[10px] uppercase tracking-[0.28em]" style={{ color: card.id === "rules" ? "#CA8A04" : card.id === "queue" ? "#B42318" : "#0F62FE" }}>
                      {card.eyebrow}
                    </div>
                    <div className="mt-1 text-[20px] font-medium text-[#111827]">
                      {card.title}
                    </div>
                  </div>
                  <div
                    className="rounded-full px-3 py-1 text-[11px] font-medium"
                    style={{ background: card.accent, color: card.accentText }}
                  >
                    {card.badge}
                  </div>
                </div>
                <div className="mt-3 text-[12px] leading-6 text-[#667085]">
                  {card.summary}
                </div>
                <div
                  className="mt-4 inline-flex rounded-full border bg-[#FFFFFF] px-3 py-1.5 text-[11px] font-medium"
                  style={{ borderColor: card.border, color: card.id === "rules" ? "#A16207" : card.id === "queue" ? "#B42318" : "#0F62FE" }}
                >
                  Open {card.eyebrow}
                </div>
              </button>
            ))}
          </div>
        </section>

        <section
          id="integrity-queue"
          className="hidden"
        >
          <div className="flex h-full min-h-0 flex-col gap-3">
            <div
              className="shrink-0 rounded-[20px] border bg-[#FFFFFF] p-3"
              style={{
                borderColor: "rgba(15,23,42,0.08)",
                boxShadow: "0 18px 56px rgba(15,23,42,0.04)",
              }}
            >
              <div className="flex flex-wrap items-center gap-2">
                {(
                  [
                    {
                      id: "rules",
                      label: "Rule Stack",
                      count: numberFormatter.format(ruleNavigatorCards.length),
                      activeBg: "#FACC15",
                      activeText: "#111827",
                      activeBorder: "rgba(202,138,4,0.34)",
                    },
                    {
                      id: "queue",
                      label: "Exception Queue",
                      count: numberFormatter.format(filteredExceptions.length),
                      activeBg: "#B42318",
                      activeText: "#FFFFFF",
                      activeBorder: "rgba(180,35,24,0.32)",
                    },
                    {
                      id: "detail",
                      label: "Record Detail",
                      count: selectedException ? "Live" : "Empty",
                      activeBg: "#0F62FE",
                      activeText: "#FFFFFF",
                      activeBorder: "rgba(15,98,254,0.24)",
                    },
                  ] as {
                    id: SurfacePane;
                    label: string;
                    count: string;
                    activeBg: string;
                    activeText: string;
                    activeBorder: string;
                  }[]
                ).map((pane) => {
                  const active = surfacePane === pane.id;
                  return (
                    <button
                      key={pane.id}
                      type="button"
                      onClick={() => setSurfacePane(pane.id)}
                      className="inline-flex items-center gap-2 rounded-full px-3.5 py-2 text-[11px] font-medium transition-all"
                      style={{
                        background: active ? pane.activeBg : "#FFFFFF",
                        color: active ? pane.activeText : "#111827",
                        border: active
                          ? `1px solid ${pane.activeBorder}`
                          : "1px solid rgba(15,23,42,0.08)",
                      }}
                    >
                      <span>{pane.label}</span>
                      <span
                        className="rounded-full px-2 py-0.5 text-[10px]"
                        style={{
                          background: active ? "rgba(255,255,255,0.18)" : "#F8FAFC",
                          color: active ? pane.activeText : "#667085",
                        }}
                      >
                        {pane.count}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid flex-1 min-h-0">
            <aside
              className={`${surfacePane === "rules" ? "flex" : "hidden"} rounded-[24px] bg-[#FFFFFF] p-4 min-h-0 flex-col`}
              style={{
                border: "1px solid rgba(15,23,42,0.08)",
                boxShadow: "0 24px 80px rgba(15,23,42,0.05)",
              }}
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-[10px] uppercase tracking-[0.28em] text-[#98A2B3]">
                    Rule Stack
                  </div>
                  <div className="mt-1 text-[16px] font-medium text-[#111827]">
                    Five-rule registry
                  </div>
                </div>
                <div className="text-[11px] text-[#667085]">
                  {numberFormatter.format(ruleNavigatorCards.length)} rules
                </div>
              </div>

              <div className="mt-4 overflow-hidden rounded-[16px]" style={{ border: "1px solid rgba(15,23,42,0.08)" }}>
                <div
                  className="grid grid-cols-[minmax(0,1fr)_56px] gap-3 px-4 py-2.5 text-[10px] uppercase tracking-[0.24em]"
                  style={{ background: "#F8FAFC", color: "#667085" }}
                >
                  <div>Rule</div>
                  <div>Hits</div>
                </div>

                <div>
                  {ruleNavigatorCards.map((rule) => {
                    const token =
                      severityTokens[rule.severity] ?? severityTokens.medium;
                    const active =
                      selectedRule === rule.id ||
                      (!selectedRuleMeta && focusRuleCard.id === rule.id);
                    return (
                      <button
                        key={rule.id}
                        type="button"
                        onClick={() => focusRule(rule.id, rule.source as SourceFilter)}
                        className="grid w-full grid-cols-[minmax(0,1fr)_56px] gap-3 px-4 py-3 text-left"
                        style={{
                          borderTop: "1px solid rgba(15,23,42,0.06)",
                          background: active ? "#F8FAFC" : "#FFFFFF",
                          boxShadow: active ? `inset 2px 0 0 ${token.accent}` : "none",
                        }}
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                              {rule.rule_code}
                            </span>
                            <span
                              className="rounded-full px-2 py-0.5 text-[9px] font-semibold"
                              style={{
                                background: token.chipBg,
                                color: token.chipText,
                                border: `1px solid ${token.border}`,
                              }}
                            >
                              {rule.status_label}
                            </span>
                          </div>
                          <div className="mt-1 truncate text-[13px] font-medium text-[#111827]">
                            {rule.title}
                          </div>
                          <div className="mt-1 truncate text-[10px] text-[#667085]">
                            {rule.source_label} | {rule.category}
                          </div>
                        </div>

                        <div className="flex flex-col items-end justify-between">
                          <div className="text-[18px] font-semibold text-[#111827]">
                            {numberFormatter.format(rule.exception_count)}
                          </div>
                          <div className="text-[9px] uppercase tracking-[0.18em] text-[#98A2B3]">
                            hits
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div
                className="mt-4 rounded-[16px] border bg-[#FCFCFD] px-4 py-3"
                style={{ borderColor: "rgba(15,23,42,0.08)" }}
              >
                <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                  Focus Rule
                </div>
                <div className="mt-1 text-[14px] font-medium text-[#111827]">
                  {focusRuleCard.rule_code} | {focusRuleCard.title}
                </div>
                <div className="mt-1 text-[11px] leading-5 text-[#667085] line-clamp-3">
                  {focusRuleCard.evaluation_basis}
                </div>
              </div>

              <div className="mt-4 grid gap-2">
                <button
                  type="button"
                  onClick={() => openRuleView(focusRuleCard.id)}
                  className="rounded-[14px] bg-[#111827] px-4 py-2.5 text-[11px] font-medium text-[#FFFFFF]"
                >
                  Open SSMS View
                </button>
                <button
                  type="button"
                  onClick={() => runQuickCommand(focusRuleCard.rule_code)}
                  className="rounded-[14px] bg-[#FFFFFF] px-4 py-2.5 text-[11px] font-medium text-[#111827]"
                  style={{ border: "1px solid rgba(15,23,42,0.08)" }}
                >
                  Filter to {focusRuleCard.rule_code}
                </button>
              </div>
            </aside>

            <section
              className={`${surfacePane === "queue" ? "flex" : "hidden"} rounded-[24px] bg-[#FFFFFF] p-4 min-h-0 flex-col`}
              style={{
                border: "1px solid rgba(15,23,42,0.08)",
                boxShadow: "0 24px 80px rgba(15,23,42,0.05)",
              }}
            >
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="text-[10px] uppercase tracking-[0.28em] text-[#98A2B3]">
                    Exception Queue
                  </div>
                  <div className="mt-1 text-[16px] font-medium text-[#111827]">
                    {selectedRuleMeta ? `${selectedRuleMeta.rule_code} open hits` : "All open hits"}
                  </div>
                  <div className="mt-1 text-[11px] text-[#667085] line-clamp-1">
                    {selectedRuleMeta?.summary || "Selected row controls the audit detail panel on the right."}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-[11px] text-[#667085]">
                    Showing {numberFormatter.format(visibleExceptions.length)} of {numberFormatter.format(filteredExceptions.length)}
                  </div>
                  <button
                    type="button"
                    onClick={() => openRuleView(selectedRuleMeta?.id || focusRuleCard.id)}
                    className="rounded-[12px] border bg-[#FFFFFF] px-3 py-2 text-[10px] font-medium text-[#111827]"
                    style={{ borderColor: "rgba(15,23,42,0.08)" }}
                  >
                    SSMS View
                  </button>
                </div>
              </div>

              <div className="mt-4 min-h-0 flex-1 overflow-hidden rounded-[16px]" style={{ border: "1px solid rgba(15,23,42,0.08)" }}>
                <div
                  className="grid grid-cols-[72px_minmax(0,0.95fr)_minmax(0,1.15fr)_88px_46px] gap-3 px-4 py-2.5 text-[10px] uppercase tracking-[0.24em]"
                  style={{ background: "#F8FAFC", color: "#667085" }}
                >
                  <div>Rule</div>
                  <div>Record</div>
                  <div>Summary</div>
                  <div>Date</div>
                  <div>Fail</div>
                </div>
                <div className="max-h-full overflow-y-auto">
                  {!visibleExceptions.length && (
                    <div className="px-4 py-6 text-[12px] text-[#667085]">
                      No open exceptions in this slice. Change the filters or open another rule queue.
                    </div>
                  )}

                  {visibleExceptions.map((item) => {
                    const token =
                      severityTokens[item.severity] ?? severityTokens.medium;
                    const selected = selectedException?.id === item.id;
                    return (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => {
                          setSelectedExceptionId(item.id);
                          setSurfacePane("detail");
                        }}
                        className="grid w-full grid-cols-[72px_minmax(0,0.95fr)_minmax(0,1.15fr)_88px_46px] gap-3 px-4 py-3 text-left transition-all"
                        style={{
                          borderTop: "1px solid rgba(15,23,42,0.06)",
                          background: selected ? "#F8FAFC" : "#FFFFFF",
                          boxShadow: selected ? `inset 2px 0 0 ${token.accent}` : "none",
                        }}
                      >
                        <div className="min-w-0">
                          <div className="text-[10px] uppercase tracking-[0.20em] text-[#98A2B3]">
                            {item.rule_code}
                          </div>
                          <span
                            className="mt-2 inline-flex rounded-full px-2 py-0.5 text-[9px] font-semibold"
                            style={{
                              background: token.chipBg,
                              color: token.chipText,
                              border: `1px solid ${token.border}`,
                            }}
                          >
                            {item.severity}
                          </span>
                        </div>

                        <div className="min-w-0">
                          <div className="truncate text-[13px] font-medium text-[#111827]">
                            {item.key}
                          </div>
                          <div className="mt-1 truncate text-[10px] text-[#98A2B3]">
                            {item.record_id}
                          </div>
                        </div>

                        <div className="min-w-0">
                          <div className="truncate text-[12px] text-[#111827]">
                            {item.title}
                          </div>
                          <div className="mt-1 truncate text-[10px] text-[#667085]">
                            {item.summary}
                          </div>
                        </div>

                        <div className="text-[10px] text-[#667085]">
                          {formatDate(item.record_date)}
                        </div>

                        <div className="text-right">
                          <div className="text-[12px] font-semibold text-[#111827]">
                            {item.failed_fields.length}
                          </div>
                          <div className="text-[9px] uppercase tracking-[0.18em] text-[#98A2B3]">
                            fail
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </section>

            <aside
              className={`${surfacePane === "detail" ? "flex" : "hidden"} rounded-[24px] bg-[#FFFFFF] p-4 min-h-0 flex-col`}
              style={{
                border: "1px solid rgba(15,23,42,0.08)",
                boxShadow: "0 24px 80px rgba(15,23,42,0.05)",
              }}
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-[10px] uppercase tracking-[0.28em] text-[#98A2B3]">
                    Record Detail
                  </div>
                  <div className="mt-1 text-[16px] font-medium text-[#111827]">
                    {selectedException ? selectedException.key : "Select a queue row"}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {selectedException && (
                    <div
                      className="px-2 py-1 rounded-full text-[9px] font-semibold"
                      style={{
                        background: (severityTokens[selectedException.severity] ?? severityTokens.medium).chipBg,
                        color: (severityTokens[selectedException.severity] ?? severityTokens.medium).chipText,
                        border: `1px solid ${(severityTokens[selectedException.severity] ?? severityTokens.medium).border}`,
                      }}
                    >
                      {selectedException.severity}
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={() => openRuleView(selectedException?.rule_id || focusRuleCard.id)}
                    className="rounded-[12px] bg-[#111827] px-3.5 py-2 text-[10px] font-medium text-[#FFFFFF]"
                  >
                    SSMS View
                  </button>
                </div>
              </div>

              {!selectedException && (
                <div className="mt-4 text-[12px] text-[#667085]">
                  Select a queue row to inspect the failing values, rule basis, and evidence path.
                </div>
              )}

              {selectedException && (
                <>
                  <div className="mt-4 flex flex-wrap items-center gap-2">
                    {(
                      [
                        { id: "overview", label: "Overview" },
                        { id: "logic", label: "Rule Logic" },
                        { id: "values", label: "Failing Values" },
                      ] as { id: InspectorPane; label: string }[]
                    ).map((pane) => {
                      const active = inspectorPane === pane.id;
                      return (
                        <button
                          key={pane.id}
                          type="button"
                          onClick={() => setInspectorPane(pane.id)}
                          className="rounded-full px-3 py-1.5 text-[10px] font-medium transition-all"
                          style={{
                            background: active ? "#111827" : "#FFFFFF",
                            color: active ? "#FFFFFF" : "#111827",
                            border: active
                              ? "1px solid rgba(17,24,39,0.96)"
                              : "1px solid rgba(15,23,42,0.08)",
                          }}
                        >
                          {pane.label}
                        </button>
                      );
                    })}
                  </div>

                  <div className="mt-4 min-h-0 flex-1 overflow-y-auto pr-1">
                    {inspectorPane === "overview" && (
                      <>
                        <div className="grid gap-3 xl:grid-cols-2 2xl:grid-cols-4">
                          {[
                            { label: "Rule", value: selectedException.rule_code },
                            { label: "Source", value: selectedException.source_label },
                            { label: "Record", value: selectedException.record_id },
                            { label: "Date", value: formatDate(selectedException.record_date) },
                          ].map((item) => (
                            <div
                              key={item.label}
                              className="rounded-[16px] border bg-[#FCFCFD] px-4 py-3"
                              style={{ borderColor: "rgba(15,23,42,0.08)" }}
                            >
                              <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                                {item.label}
                              </div>
                              <div className="mt-1.5 text-[12px] font-medium text-[#111827] break-all">
                                {item.value}
                              </div>
                            </div>
                          ))}
                        </div>

                        <div className="mt-3 rounded-[18px] border bg-[#FFFFFF] px-4 py-4" style={{ borderColor: "rgba(15,23,42,0.08)" }}>
                          <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                            Exception Summary
                          </div>
                          <div className="mt-2 text-[13px] leading-6 text-[#111827]">
                            {selectedException.summary}
                          </div>
                        </div>

                        <div className="mt-3 grid gap-3 xl:grid-cols-2">
                          <div className="rounded-[18px] border bg-[#F8FAFC] p-4" style={{ borderColor: "rgba(15,23,42,0.08)" }}>
                            <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                              Expected
                            </div>
                            <div className="mt-2 text-[12px] leading-6 text-[#111827]">
                              {selectedException.expected}
                            </div>
                          </div>
                          <div className="rounded-[18px] border bg-[#F8FAFC] p-4" style={{ borderColor: "rgba(15,23,42,0.08)" }}>
                            <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                              Fix Path
                            </div>
                            <div className="mt-2 text-[12px] leading-6 text-[#111827]">
                              {selectedException.recommendation}
                            </div>
                          </div>
                        </div>

                        <div
                          className="mt-3 rounded-[18px] border bg-[#FCFCFD] px-4 py-3"
                          style={{ borderColor: "rgba(15,23,42,0.08)" }}
                        >
                          <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                            Failing Fields
                          </div>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {selectedException.failed_fields.map((field) => (
                              <span
                                key={field}
                                className="rounded-full border bg-[#FFF7F6] px-2.5 py-1 text-[10px] font-medium text-[#B42318]"
                                style={{ borderColor: "rgba(180,35,24,0.18)" }}
                              >
                                {field}
                              </span>
                            ))}
                          </div>
                        </div>
                      </>
                    )}

                    {inspectorPane === "logic" && (
                      <div className="grid gap-3">
                        <div className="rounded-[18px] border bg-[#FFFFFF] p-4" style={{ borderColor: "rgba(15,23,42,0.08)" }}>
                          <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                            Evaluation Basis
                          </div>
                          <div className="mt-2 text-[12px] leading-6 text-[#111827]">
                            {inspectorRuleMeta.evaluation_basis}
                          </div>
                        </div>
                        <div className="rounded-[18px] border bg-[#FFFFFF] p-4" style={{ borderColor: "rgba(15,23,42,0.08)" }}>
                          <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                            Client Rule
                          </div>
                          <div className="mt-2 text-[12px] leading-6 text-[#111827]">
                            {inspectorRuleView?.client_rule || "Not available"}
                          </div>
                        </div>
                        <div className="rounded-[18px] border bg-[#FFFFFF] p-4" style={{ borderColor: "rgba(15,23,42,0.08)" }}>
                          <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                            Technical Logic
                          </div>
                          <div className="mt-2 text-[12px] leading-6 text-[#111827]">
                            {inspectorRuleView?.technical_logic || "Not available"}
                          </div>
                        </div>
                        {inspectorRuleView?.note && (
                          <div className="rounded-[18px] border bg-[#FCFCFD] p-4" style={{ borderColor: "rgba(15,23,42,0.08)" }}>
                            <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                              Evidence Note
                            </div>
                            <div className="mt-2 text-[12px] leading-6 text-[#111827]">
                              {inspectorRuleView.note}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {inspectorPane === "values" && (
                      <div>
                        <div className="flex flex-wrap gap-2.5">
                          {selectedException.action_url && (
                            <button
                              type="button"
                              onClick={() =>
                                window.open(
                                  selectedException.action_url || "",
                                  "_blank",
                                  "noopener,noreferrer",
                                )
                              }
                              className="px-3.5 py-2 rounded-[12px] text-[11px] font-medium text-[#111827] bg-[#FFFFFF]"
                              style={{ border: "1px solid rgba(15,23,42,0.08)" }}
                            >
                              Source Link
                            </button>
                          )}

                          <button
                            type="button"
                            onClick={() =>
                              void navigator.clipboard.writeText(
                                selectedException.record_id,
                              )
                            }
                            className="px-3.5 py-2 rounded-[12px] text-[11px] font-medium text-[#111827] bg-[#FFFFFF]"
                            style={{ border: "1px solid rgba(15,23,42,0.08)" }}
                          >
                            Copy Record Key
                          </button>
                        </div>

                        <div className="mt-3 text-[10px] uppercase tracking-[0.28em] text-[#98A2B3]">
                          Failing Values
                        </div>
                        <div className="mt-3 grid grid-cols-1 gap-2.5 xl:grid-cols-2">
                          {Object.entries(selectedException.values).map(
                            ([field, value]) => {
                              const failed =
                                selectedException.failed_fields.includes(field);
                              return (
                                <div
                                  key={field}
                                  className="rounded-[14px] px-3.5 py-3 bg-[#FFFFFF]"
                                  style={{
                                    border: failed
                                      ? "1px solid rgba(217,45,32,0.28)"
                                      : "1px solid rgba(15,23,42,0.08)",
                                    background: failed ? "#FFF7F6" : "#FFFFFF",
                                  }}
                                >
                                  <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                                    {field}
                                  </div>
                                  <div className="mt-1.5 text-[11px] text-[#111827] break-all">
                                    {formatValue(value)}
                                  </div>
                                </div>
                              );
                            },
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </>
              )}
            </aside>
          </div>
          </div>
        </section>
      </div>

      {surfacePane && (
        <div className="fixed inset-0 z-40 bg-[rgba(15,23,42,0.34)] px-5 py-5">
          <div
            className="mx-auto flex h-full max-w-[1500px] flex-col overflow-hidden rounded-[30px] bg-[#FFFFFF]"
            style={{ boxShadow: "0 40px 140px rgba(15,23,42,0.18)" }}
          >
            <div
              className="flex shrink-0 items-start justify-between gap-4 border-b px-6 py-5"
              style={{ borderColor: "rgba(15,23,42,0.08)" }}
            >
              <div className="min-w-0">
                <div
                  className="text-[10px] uppercase tracking-[0.28em]"
                  style={{
                    color:
                      surfacePane === "rules"
                        ? "#CA8A04"
                        : surfacePane === "queue"
                          ? "#B42318"
                          : "#0F62FE",
                  }}
                >
                  {surfacePane === "rules"
                    ? "Rule Stack"
                    : surfacePane === "queue"
                      ? "Exception Queue"
                      : "Record Detail"}
                </div>
                <div className="mt-2 text-[26px] font-medium text-[#111827]">
                  {surfacePane === "rules"
                    ? "Five-rule registry"
                    : surfacePane === "queue"
                      ? `${numberFormatter.format(filteredExceptions.length)} open hits`
                      : selectedException?.key || "Select a queue row"}
                </div>
                <div className="mt-2 text-[12px] text-[#667085]">
                  {surfacePane === "rules"
                    ? "All rules in one focused control surface."
                    : surfacePane === "queue"
                      ? "Scan the queue, then open a row into the record detail surface."
                      : "One selected row, one controlled reading frame."}
                </div>
              </div>

              <div className="flex items-center gap-2">
                {surfacePane !== "rules" && (
                  <button
                    type="button"
                    onClick={() =>
                      openRuleView(
                        surfacePane === "detail"
                          ? selectedException?.rule_id || focusRuleCard.id
                          : selectedRuleMeta?.id || focusRuleCard.id,
                      )
                    }
                    className="rounded-full border bg-[#FFFFFF] px-4 py-2 text-[11px] font-medium text-[#111827]"
                    style={{ borderColor: "rgba(15,23,42,0.08)" }}
                  >
                    SSMS View
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setSurfacePane(null)}
                  className="rounded-full bg-[#111827] px-4 py-2 text-[11px] font-medium text-[#FFFFFF]"
                >
                  Close
                </button>
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto bg-[#FCFCFD] px-6 py-5">
              {surfacePane === "rules" && (
                <div className="grid gap-3 lg:grid-cols-2">
                  {ruleNavigatorCards.map((rule) => {
                    const token =
                      severityTokens[rule.severity] ?? severityTokens.medium;
                    const active =
                      selectedRule === rule.id ||
                      (!selectedRuleMeta && focusRuleCard.id === rule.id);
                    return (
                      <button
                        key={rule.id}
                        type="button"
                        onClick={() => {
                          focusRule(rule.id, rule.source as SourceFilter);
                          setSurfacePane("queue");
                        }}
                        className="rounded-[20px] bg-[#FFFFFF] px-4 py-4 text-left"
                        style={{
                          border: active
                            ? `1px solid ${token.border}`
                            : "1px solid rgba(15,23,42,0.08)",
                          boxShadow: active
                            ? `inset 3px 0 0 ${token.accent}`
                            : "0 10px 30px rgba(15,23,42,0.03)",
                        }}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] uppercase tracking-[0.24em] text-[#98A2B3]">
                              {rule.rule_code}
                            </span>
                            <span
                              className="rounded-full px-2 py-0.5 text-[9px] font-semibold"
                              style={{
                                background: token.chipBg,
                                color: token.chipText,
                                border: `1px solid ${token.border}`,
                              }}
                            >
                              {rule.status_label}
                            </span>
                          </div>
                          <div className="text-[18px] font-semibold text-[#111827]">
                            {numberFormatter.format(rule.exception_count)}
                          </div>
                        </div>
                        <div className="mt-2 text-[16px] font-medium text-[#111827]">
                          {rule.title}
                        </div>
                        <div className="mt-2 text-[12px] leading-6 text-[#667085]">
                          {rule.evaluation_basis}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}

              {surfacePane === "queue" && (
                <div
                  className="overflow-hidden rounded-[22px] bg-[#FFFFFF]"
                  style={{ border: "1px solid rgba(180,35,24,0.18)" }}
                >
                  <div
                    className="grid grid-cols-[96px_minmax(0,1fr)_150px_84px] gap-3 px-4 py-3 text-[10px] uppercase tracking-[0.24em] text-[#B42318]"
                    style={{ background: "#FFF7F6" }}
                  >
                    <div>Rule</div>
                    <div>Record</div>
                    <div>Missing Fields</div>
                    <div>Date</div>
                  </div>
                  <div className="max-h-[calc(100vh-260px)] overflow-y-auto">
                    {visibleExceptions.map((item) => {
                      const selected = selectedException?.id === item.id;
                      return (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => {
                            setSelectedExceptionId(item.id);
                            setSurfacePane("detail");
                          }}
                          className="grid w-full grid-cols-[96px_minmax(0,1fr)_150px_84px] gap-3 px-4 py-3 text-left"
                          style={{
                            borderTop: "1px solid rgba(15,23,42,0.06)",
                            background: selected ? "#FFF7F6" : "#FFFFFF",
                          }}
                        >
                          <div>
                            <div className="text-[10px] uppercase tracking-[0.20em] text-[#98A2B3]">
                              {item.rule_code}
                            </div>
                            <div className="mt-1 inline-flex rounded-full bg-[#FFF7F6] px-2 py-0.5 text-[9px] font-semibold text-[#B42318]">
                              {item.severity}
                            </div>
                          </div>
                          <div className="min-w-0">
                            <div className="truncate text-[13px] font-medium text-[#111827]">
                              {item.key}
                            </div>
                            <div className="mt-1 truncate text-[11px] text-[#667085]">
                              {item.failed_fields.join(", ")}
                            </div>
                          </div>
                          <div className="text-[11px] text-[#111827]">
                            {item.failed_fields.length} fields
                          </div>
                          <div className="text-[11px] text-[#667085]">
                            {formatDate(item.record_date)}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {surfacePane === "detail" && (
                <div className="grid gap-4">
                  {!selectedException && (
                    <div className="rounded-[22px] border bg-[#FFFFFF] px-5 py-6 text-[13px] text-[#667085]" style={{ borderColor: "rgba(15,23,42,0.08)" }}>
                      Select a row from Exception Queue first.
                    </div>
                  )}

                  {selectedException && (
                    <>
                      <div className="flex flex-wrap items-center gap-2">
                        {(
                          [
                            { id: "overview", label: "Overview" },
                            { id: "logic", label: "Rule Logic" },
                            { id: "values", label: "Failing Values" },
                          ] as { id: InspectorPane; label: string }[]
                        ).map((pane) => {
                          const active = inspectorPane === pane.id;
                          return (
                            <button
                              key={pane.id}
                              type="button"
                              onClick={() => setInspectorPane(pane.id)}
                              className="rounded-full px-3 py-1.5 text-[10px] font-medium"
                              style={{
                                background: active ? "#0F62FE" : "#FFFFFF",
                                color: active ? "#FFFFFF" : "#111827",
                                border: active
                                  ? "1px solid rgba(15,98,254,0.24)"
                                  : "1px solid rgba(15,23,42,0.08)",
                              }}
                            >
                              {pane.label}
                            </button>
                          );
                        })}
                      </div>

                      {inspectorPane === "overview" && (
                        <div className="grid gap-4 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
                          <div className="grid gap-3">
                            {[
                              { label: "Rule", value: selectedException.rule_code },
                              { label: "Source", value: selectedException.source_label },
                              { label: "Record", value: selectedException.record_id },
                              { label: "Date", value: formatDate(selectedException.record_date) },
                            ].map((item) => (
                              <div key={item.label} className="rounded-[18px] border bg-[#FFFFFF] px-4 py-3" style={{ borderColor: "rgba(15,23,42,0.08)" }}>
                                <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                                  {item.label}
                                </div>
                                <div className="mt-1.5 text-[13px] font-medium text-[#111827] break-all">
                                  {item.value}
                                </div>
                              </div>
                            ))}
                          </div>
                          <div className="grid gap-3">
                            <div className="rounded-[18px] border bg-[#FFFFFF] px-4 py-4" style={{ borderColor: "rgba(15,23,42,0.08)" }}>
                              <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                                Exception Summary
                              </div>
                              <div className="mt-2 text-[13px] leading-6 text-[#111827]">
                                {selectedException.summary}
                              </div>
                            </div>
                            <div className="grid gap-3 lg:grid-cols-2">
                              <div className="rounded-[18px] border bg-[#F8FAFC] p-4" style={{ borderColor: "rgba(15,23,42,0.08)" }}>
                                <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                                  Expected
                                </div>
                                <div className="mt-2 text-[12px] leading-6 text-[#111827]">
                                  {selectedException.expected}
                                </div>
                              </div>
                              <div className="rounded-[18px] border bg-[#F8FAFC] p-4" style={{ borderColor: "rgba(15,23,42,0.08)" }}>
                                <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                                  Fix Path
                                </div>
                                <div className="mt-2 text-[12px] leading-6 text-[#111827]">
                                  {selectedException.recommendation}
                                </div>
                              </div>
                            </div>
                            <div className="rounded-[18px] border bg-[#FFF7F6] px-4 py-3" style={{ borderColor: "rgba(180,35,24,0.16)" }}>
                              <div className="text-[10px] uppercase tracking-[0.22em] text-[#B42318]">
                                Failing Fields
                              </div>
                              <div className="mt-2 flex flex-wrap gap-2">
                                {selectedException.failed_fields.map((field) => (
                                  <span key={field} className="rounded-full border bg-[#FFFFFF] px-2.5 py-1 text-[10px] font-medium text-[#B42318]" style={{ borderColor: "rgba(180,35,24,0.18)" }}>
                                    {field}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </div>
                        </div>
                      )}

                      {inspectorPane === "logic" && (
                        <div className="grid gap-3 lg:grid-cols-3">
                          <div className="rounded-[18px] border bg-[#FFFFFF] p-4" style={{ borderColor: "rgba(15,23,42,0.08)" }}>
                            <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                              Evaluation Basis
                            </div>
                            <div className="mt-2 text-[12px] leading-6 text-[#111827]">
                              {inspectorRuleMeta.evaluation_basis}
                            </div>
                          </div>
                          <div className="rounded-[18px] border bg-[#FFFFFF] p-4" style={{ borderColor: "rgba(15,23,42,0.08)" }}>
                            <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                              Client Rule
                            </div>
                            <div className="mt-2 text-[12px] leading-6 text-[#111827]">
                              {inspectorRuleView?.client_rule || "Not available"}
                            </div>
                          </div>
                          <div className="rounded-[18px] border bg-[#FFFFFF] p-4" style={{ borderColor: "rgba(15,23,42,0.08)" }}>
                            <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                              Technical Logic
                            </div>
                            <div className="mt-2 text-[12px] leading-6 text-[#111827]">
                              {inspectorRuleView?.technical_logic || "Not available"}
                            </div>
                          </div>
                        </div>
                      )}

                      {inspectorPane === "values" && (
                        <div className="grid gap-3 lg:grid-cols-2">
                          {Object.entries(selectedException.values).map(([field, value]) => {
                            const failed = selectedException.failed_fields.includes(field);
                            return (
                              <div
                                key={field}
                                className="rounded-[16px] bg-[#FFFFFF] px-4 py-3"
                                style={{
                                  border: failed
                                    ? "1px solid rgba(180,35,24,0.24)"
                                    : "1px solid rgba(15,23,42,0.08)",
                                  background: failed ? "#FFF7F6" : "#FFFFFF",
                                }}
                              >
                                <div className="text-[10px] uppercase tracking-[0.22em] text-[#98A2B3]">
                                  {field}
                                </div>
                                <div className="mt-1.5 text-[12px] text-[#111827] break-all">
                                  {formatValue(value)}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeRuleViewId && (
        <div className="fixed inset-0 z-50 bg-[rgba(15,23,42,0.56)] px-6 py-6">
          <div className="w-full h-full max-w-[1600px] mx-auto rounded-[28px] bg-[#FFFFFF] overflow-hidden flex flex-col shadow-[0_40px_140px_rgba(15,23,42,0.35)]">
            <div
              className="px-6 py-5 border-b"
              style={{ borderColor: "rgba(15,23,42,0.08)" }}
            >
              <div className="flex items-start justify-between gap-5">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[10px] uppercase tracking-[0.26em] text-[#98A2B3]">
                      SSMS View
                    </span>
                    <span className="text-[10px] text-[#667085]">
                      {activeRuleView?.rule_code || activeRuleViewId} |{" "}
                      {activeRuleView?.source_label || "Loading"}
                    </span>
                  </div>
                  <div className="mt-2 text-[24px] leading-[1.08] font-medium text-[#111827]">
                    {activeRuleView?.title || "Loading evidence view"}
                  </div>
                  <div className="mt-2 text-[12px] leading-6 text-[#667085]">
                    {activeRuleView
                      ? `Showing ${numberFormatter.format(activeRuleView.page_start)}-${numberFormatter.format(activeRuleView.page_end)} of ${numberFormatter.format(activeRuleView.total_violations)} violating rows${activeRuleView.base_total_violations !== activeRuleView.total_violations ? ` | ${numberFormatter.format(activeRuleView.base_total_violations)} total across all dates` : ""}.`
                      : ruleViewLoading
                        ? "Loading current SSMS slice."
                        : "Preparing evidence view."}
                  </div>
                  {activeRuleView?.evaluation_basis && (
                    <div className="mt-2 text-[11px] text-[#475467]">
                      Evaluation basis: {activeRuleView.evaluation_basis}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={!activeRuleView}
                    onClick={() =>
                      activeRuleView
                        ? void navigator.clipboard.writeText(activeRuleView.sql)
                        : undefined
                    }
                    className="px-3.5 py-2 rounded-full text-[11px] font-medium text-[#344054] bg-[#FFFFFF]"
                    style={{ border: "1px solid rgba(15,23,42,0.08)" }}
                  >
                    Copy SQL
                  </button>
                  <button
                    type="button"
                    disabled={ruleViewExporting}
                    onClick={() => void exportRuleViewCsv()}
                    className="px-3.5 py-2 rounded-full text-[11px] font-medium text-[#344054] bg-[#FFFFFF]"
                    style={{ border: "1px solid rgba(15,23,42,0.08)" }}
                  >
                    {ruleViewExporting ? "Exporting..." : "Export CSV"}
                  </button>
                  <button
                    type="button"
                    onClick={closeRuleView}
                    className="px-3.5 py-2 rounded-full text-[11px] font-medium bg-[#111827] text-[#FFFFFF]"
                  >
                    Close
                  </button>
                </div>
              </div>

              <div className="mt-4 flex flex-wrap items-center gap-2">
                {(
                  [
                    { id: "rows", label: "Rows" },
                    { id: "sql", label: "SQL" },
                    { id: "logic", label: "Rule Logic" },
                  ] as { id: EvidenceTab; label: string }[]
                ).map((tab) => {
                  const active = evidenceTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setEvidenceTab(tab.id)}
                      className="px-3 py-1.5 rounded-full text-[10px] font-medium"
                      style={{
                        background: active ? "#111827" : "#FFFFFF",
                        color: active ? "#FFFFFF" : "#344054",
                        border: active
                          ? "1px solid rgba(17,24,39,0.95)"
                          : "1px solid rgba(15,23,42,0.08)",
                      }}
                    >
                      {tab.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex-1 min-h-0 overflow-hidden">
              {ruleViewError && (
                <div className="px-6 py-3 text-[11px] text-[#B42318] border-b bg-[#FFF7F6]">
                  {ruleViewError}
                </div>
              )}

              {evidenceTab === "rows" && (
                <div className="h-full flex flex-col">
                  <div
                    className="px-6 py-3 border-b bg-[#FFFFFF]"
                    style={{ borderColor: "rgba(15,23,42,0.08)" }}
                  >
                    <div className="flex flex-col 2xl:flex-row 2xl:items-end 2xl:justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="text-[11px] text-[#667085]">
                          {activeRuleView?.note ||
                            "Preparing the rule-specific SSMS evidence slice."}
                        </div>
                      </div>

                      <div className="flex flex-wrap items-end gap-2">
                        {activeRuleView?.date_field ? (
                          <>
                            <div className="text-[10px] text-[#667085] pb-1">
                              Date field: {activeRuleView.date_field}
                            </div>
                            <input
                              type="date"
                              value={ruleViewDateFromInput}
                              min={
                                activeRuleView.available_date_range?.min ||
                                undefined
                              }
                              max={
                                activeRuleView.available_date_range?.max ||
                                undefined
                              }
                              onChange={(event) =>
                                setRuleViewDateFromInput(event.target.value)
                              }
                              className="rounded-[12px] px-3 py-2 text-[11px] text-[#111827] bg-[#FFFFFF] outline-none"
                              style={{
                                border: "1px solid rgba(15,23,42,0.12)",
                              }}
                            />
                            <input
                              type="date"
                              value={ruleViewDateToInput}
                              min={
                                activeRuleView.available_date_range?.min ||
                                undefined
                              }
                              max={
                                activeRuleView.available_date_range?.max ||
                                undefined
                              }
                              onChange={(event) =>
                                setRuleViewDateToInput(event.target.value)
                              }
                              className="rounded-[12px] px-3 py-2 text-[11px] text-[#111827] bg-[#FFFFFF] outline-none"
                              style={{
                                border: "1px solid rgba(15,23,42,0.12)",
                              }}
                            />
                            <button
                              type="button"
                              onClick={applyRuleViewFilters}
                              className="px-3 py-2 rounded-[12px] text-[10px] font-medium bg-[#111827] text-[#FFFFFF]"
                            >
                              Apply
                            </button>
                            <button
                              type="button"
                              onClick={clearRuleViewFilters}
                              className="px-3 py-2 rounded-[12px] text-[10px] font-medium text-[#344054] bg-[#FFFFFF]"
                              style={{
                                border: "1px solid rgba(15,23,42,0.08)",
                              }}
                            >
                              Clear
                            </button>
                          </>
                        ) : (
                          <div className="text-[10px] text-[#98A2B3] pb-1">
                            No date filter on this rule
                          </div>
                        )}

                        <div className="flex items-center gap-2 ml-2">
                          <button
                            type="button"
                            disabled={
                              !activeRuleView?.has_prev_page || ruleViewLoading
                            }
                            onClick={() =>
                              setRuleViewPage((current) =>
                                Math.max(1, current - 1),
                              )
                            }
                            className="w-9 h-9 rounded-full text-[14px] font-medium text-[#344054] bg-[#FFFFFF]"
                            style={{
                              border: "1px solid rgba(15,23,42,0.08)",
                              opacity:
                                !activeRuleView?.has_prev_page ||
                                ruleViewLoading
                                  ? 0.4
                                  : 1,
                            }}
                          >
                            ←
                          </button>
                          <div className="min-w-[150px] text-center text-[10px] text-[#667085]">
                            {activeRuleView
                              ? `${numberFormatter.format(activeRuleView.page_start)}-${numberFormatter.format(activeRuleView.page_end)}`
                              : "Loading"}
                          </div>
                          <button
                            type="button"
                            disabled={
                              !activeRuleView?.has_next_page || ruleViewLoading
                            }
                            onClick={() =>
                              setRuleViewPage((current) => current + 1)
                            }
                            className="w-9 h-9 rounded-full text-[14px] font-medium text-[#344054] bg-[#FFFFFF]"
                            style={{
                              border: "1px solid rgba(15,23,42,0.08)",
                              opacity:
                                !activeRuleView?.has_next_page ||
                                ruleViewLoading
                                  ? 0.4
                                  : 1,
                            }}
                          >
                            →
                          </button>
                        </div>
                      </div>
                    </div>
                    {activeRuleView?.date_field && (
                      <div className="mt-2 text-[10px] text-[#98A2B3]">
                        Available range:{" "}
                        {activeRuleView.available_date_range?.min || "N/A"} to{" "}
                        {activeRuleView.available_date_range?.max || "N/A"}
                      </div>
                    )}
                  </div>
                  <div className="flex-1 overflow-auto bg-[#F8FAFC]">
                    {ruleViewLoading && !activeRuleView ? (
                      <div className="h-full flex items-center justify-center">
                        <div className="flex flex-col items-center gap-3">
                          <div
                            className="w-10 h-10 rounded-full animate-spin"
                            style={{
                              border: "3px solid rgba(0,0,0,0.10)",
                              borderTopColor: "#0F62FE",
                            }}
                          />
                          <div className="text-[12px] text-[#667085]">
                            Loading SSMS slice
                          </div>
                        </div>
                      </div>
                    ) : activeRuleView && activeRuleView.rows.length ? (
                      <table className="min-w-full text-[11px] border-separate border-spacing-0">
                        <thead className="sticky top-0 z-10">
                          <tr style={{ background: "#EEF2F6" }}>
                            {activeRuleView.columns.map((column) => (
                              <th
                                key={column}
                                className="px-3 py-3 text-left font-semibold text-[#344054]"
                                style={{
                                  borderBottom: "1px solid rgba(15,23,42,0.08)",
                                  whiteSpace: "nowrap",
                                }}
                              >
                                {column}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {activeRuleView.rows.map((row, rowIndex) => (
                            <tr
                              key={`${activeRuleView.id}:${rowIndex}`}
                              style={{
                                background:
                                  rowIndex % 2 === 0 ? "#FFFFFF" : "#FAFAFB",
                              }}
                            >
                              {activeRuleView.columns.map((column) => {
                                const failed =
                                  row.failed_fields.includes(column);
                                return (
                                  <td
                                    key={`${rowIndex}:${column}`}
                                    className="px-3 py-2.5 align-top text-[#111827]"
                                    style={{
                                      borderBottom:
                                        "1px solid rgba(15,23,42,0.06)",
                                      background: failed
                                        ? "#FFF3F2"
                                        : undefined,
                                      boxShadow: failed
                                        ? "inset 0 0 0 1px rgba(217,45,32,0.18)"
                                        : undefined,
                                      whiteSpace: "nowrap",
                                    }}
                                  >
                                    {formatValue(row.values[column])}
                                  </td>
                                );
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <div className="h-full flex items-center justify-center">
                        <div className="text-center">
                          <div className="text-[16px] font-medium text-[#111827]">
                            No violating rows in this date slice
                          </div>
                          <div className="mt-2 text-[12px] text-[#667085]">
                            Adjust the date filters or clear them to return to
                            the full rule result set.
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {evidenceTab === "sql" && (
                <div className="h-full overflow-auto bg-[#0B1220] px-6 py-6">
                  <pre className="text-[12px] leading-7 text-[#E2E8F0] whitespace-pre-wrap">
                    {activeRuleView?.sql || "Loading SQL..."}
                  </pre>
                </div>
              )}

              {evidenceTab === "logic" && (
                <div className="h-full overflow-auto px-6 py-6 bg-[#FAFAFA]">
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                    {[
                      {
                        label: "Client Rule",
                        value: activeRuleView?.client_rule || "Loading...",
                      },
                      {
                        label: "Technical Logic",
                        value: activeRuleView?.technical_logic || "Loading...",
                      },
                      {
                        label: "Expected",
                        value: activeRuleView?.expected || "Loading...",
                      },
                      {
                        label: "Recommended Fix",
                        value: activeRuleView?.recommendation || "Loading...",
                      },
                    ].map((card) => (
                      <div
                        key={card.label}
                        className="rounded-[18px] bg-[#FFFFFF] p-4"
                        style={{
                          border: "1px solid rgba(15,23,42,0.08)",
                          boxShadow: "0 10px 24px rgba(15,23,42,0.04)",
                        }}
                      >
                        <div className="text-[10px] uppercase tracking-[0.24em] text-[#98A2B3]">
                          {card.label}
                        </div>
                        <div className="mt-2 text-[13px] leading-6 text-[#111827]">
                          {card.value}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div
                    className="mt-4 rounded-[18px] bg-[#FFFFFF] p-4"
                    style={{
                      border: "1px solid rgba(15,23,42,0.08)",
                      boxShadow: "0 10px 24px rgba(15,23,42,0.04)",
                    }}
                  >
                    <div className="text-[10px] uppercase tracking-[0.24em] text-[#98A2B3]">
                      Evidence Note
                    </div>
                    <div className="mt-2 text-[13px] leading-6 text-[#111827]">
                      {activeRuleView?.note || "Loading evidence note..."}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

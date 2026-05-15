"""
SQL Agent — Anti-hallucination SQL generation via DSPy
======================================================
Uses DSPy ChainOfThought with strict schema constraints.
The prompt explicitly forbids inventing column names and
requires INSUFFICIENT_SCHEMA response when columns are missing.

Compiled with BootstrapFewShot using domain-specific training examples.
"""

import re
import dspy
import logging
from dataclasses import dataclass

log = logging.getLogger("bashira.sql_agent")


# ── Data Classes ─────────────────────────────────────────────────────────

@dataclass
class SQLResult:
    """Output from SQL generation."""
    sql_query: str
    confidence: float
    reasoning: str
    is_insufficient: bool = False


def _normalize_question(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _is_portfolio_status_question(question: str) -> bool:
    q = _normalize_question(question)
    portfolio_markers = [
        "overall project portfolio status",
        "overall portfolio status",
        "portfolio status",
        "project portfolio",
    ]
    status_markers = ["today", "current", "latest", "right now", "overall"]
    return any(marker in q for marker in portfolio_markers) and any(
        marker in q for marker in status_markers
    )


def _portfolio_status_sql() -> str:
    return """
WITH latest_snapshot AS (
    SELECT MAX(Week_Number) AS snapshot_date
    FROM WellMonitoringReport
),
portfolio_base AS (
    SELECT
        w.pdo_well_id,
        w.Cluster,
        TRY_CAST(w.over_all_progress_percentages AS FLOAT) AS progress_ratio,
        TRY_CAST(w.[exp.rig_off_location_sap_data] AS DATE) AS expected_rig_off,
        w.actual_rig_off_date
    FROM WellMonitoringReport w
    INNER JOIN latest_snapshot s
        ON w.Week_Number = s.snapshot_date
)
SELECT
    (SELECT snapshot_date FROM latest_snapshot) AS snapshot_date,
    COUNT(DISTINCT pdo_well_id) AS total_wells,
    CAST(AVG(progress_ratio) * 100 AS DECIMAL(10,2)) AS avg_progress_pct,
    SUM(CASE WHEN progress_ratio >= 1 THEN 1 ELSE 0 END) AS complete_wells,
    SUM(CASE WHEN progress_ratio = 0 THEN 1 ELSE 0 END) AS not_started_wells,
    SUM(CASE WHEN progress_ratio > 0 AND progress_ratio < 1 THEN 1 ELSE 0 END) AS active_wells,
    SUM(CASE WHEN expected_rig_off < CAST(GETDATE() AS DATE) AND actual_rig_off_date IS NULL THEN 1 ELSE 0 END) AS overdue_rig_off_no_actual
FROM portfolio_base;
""".strip()


def _is_current_quarter_revenue_forecast_question(question: str) -> bool:
    q = _normalize_question(question)
    revenue_markers = [
        "forecasted revenue",
        "forecast revenue",
        "revenue forecast",
        "projected revenue",
    ]
    quarter_markers = [
        "this quarter",
        "current quarter",
        "for this quarter",
        "for the current quarter",
    ]
    return any(marker in q for marker in revenue_markers) and any(
        marker in q for marker in quarter_markers
    )


def _is_annual_target_status_question(question: str) -> bool:
    q = _normalize_question(question)
    direct_markers = [
        "are we on track to meet annual targets",
        "are we on track to meet yearly targets",
        "on track to meet annual targets",
        "on track to meet yearly targets",
        "annual target status",
        "yearly target status",
    ]
    return any(marker in q for marker in direct_markers)


def _current_quarter_revenue_forecast_sql() -> str:
    return """
WITH quarter_bounds AS (
    SELECT
        DATEADD(QUARTER, DATEDIFF(QUARTER, 0, GETDATE()), 0) AS quarter_start,
        DATEADD(DAY, -1, DATEADD(QUARTER, DATEDIFF(QUARTER, 0, GETDATE()) + 1, 0)) AS quarter_end
),
actual_to_date AS (
    SELECT
        MAX(qb.quarter_start) AS quarter_start,
        MAX(qb.quarter_end) AS quarter_end,
        MAX(CAST(r.[created_at] AS DATE)) AS as_of_date,
        SUM(TRY_CAST(r.[actual_purpose_value] AS DECIMAL(18,2))) AS actual_revenue_to_date
    FROM [Revenue] r
    CROSS JOIN quarter_bounds qb
    WHERE CAST(r.[created_at] AS DATE) >= qb.quarter_start
      AND CAST(r.[created_at] AS DATE) <= CAST(GETDATE() AS DATE)
),
planned_full_quarter AS (
    SELECT
        SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) AS planned_revenue_full_quarter
    FROM [Revenue] r
    CROSS JOIN quarter_bounds qb
    WHERE CAST(r.[created_at] AS DATE) >= qb.quarter_start
      AND CAST(r.[created_at] AS DATE) <= qb.quarter_end
),
projection AS (
    SELECT
        a.quarter_start,
        a.quarter_end,
        a.as_of_date,
        a.actual_revenue_to_date,
        p.planned_revenue_full_quarter,
        DATEDIFF(DAY, a.quarter_start, a.as_of_date) + 1 AS elapsed_days,
        DATEDIFF(DAY, a.quarter_start, a.quarter_end) + 1 AS total_days
    FROM actual_to_date a
    CROSS JOIN planned_full_quarter p
)
SELECT
    quarter_start,
    quarter_end,
    as_of_date,
    actual_revenue_to_date,
    planned_revenue_full_quarter,
    CASE
        WHEN elapsed_days <= 0 OR actual_revenue_to_date IS NULL THEN NULL
        ELSE (actual_revenue_to_date / elapsed_days) * total_days
    END AS forecasted_quarter_revenue,
    CASE
        WHEN planned_revenue_full_quarter IS NULL OR planned_revenue_full_quarter = 0 OR elapsed_days <= 0 OR actual_revenue_to_date IS NULL THEN NULL
        ELSE (((actual_revenue_to_date / elapsed_days) * total_days) - planned_revenue_full_quarter) * 100.0 / planned_revenue_full_quarter
    END AS forecast_vs_plan_pct
FROM projection;
""".strip()


# ── DSPy Signatures ─────────────────────────────────────────────────────

def _annual_target_status_sql() -> str:
    return """
WITH year_bounds AS (
    SELECT
        DATEFROMPARTS(YEAR(GETDATE()), 1, 1) AS year_start,
        DATEFROMPARTS(YEAR(GETDATE()), 12, 31) AS year_end
),
actual_ytd AS (
    SELECT
        MAX(CAST(r.[created_at] AS DATE)) AS as_of_date,
        SUM(TRY_CAST(r.[actual_purpose_value] AS DECIMAL(18,2))) AS actual_revenue_ytd
    FROM [Revenue] r
    CROSS JOIN year_bounds y
    WHERE CAST(r.[created_at] AS DATE) >= y.year_start
      AND CAST(r.[created_at] AS DATE) <= CAST(GETDATE() AS DATE)
),
plan_ytd AS (
    SELECT
        SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) AS planned_revenue_ytd
    FROM [Revenue] r
    CROSS JOIN year_bounds y
    WHERE CAST(r.[created_at] AS DATE) >= y.year_start
      AND CAST(r.[created_at] AS DATE) <= CAST(GETDATE() AS DATE)
),
plan_full_year AS (
    SELECT
        SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) AS planned_revenue_full_year
    FROM [Revenue] r
    CROSS JOIN year_bounds y
    WHERE CAST(r.[created_at] AS DATE) >= y.year_start
      AND CAST(r.[created_at] AS DATE) <= y.year_end
),
projection AS (
    SELECT
        y.year_start,
        y.year_end,
        a.as_of_date,
        a.actual_revenue_ytd,
        py.planned_revenue_ytd,
        pf.planned_revenue_full_year,
        DATEDIFF(DAY, y.year_start, a.as_of_date) + 1 AS elapsed_days,
        DATEDIFF(DAY, y.year_start, y.year_end) + 1 AS total_days
    FROM year_bounds y
    CROSS JOIN actual_ytd a
    CROSS JOIN plan_ytd py
    CROSS JOIN plan_full_year pf
)
SELECT
    year_start,
    year_end,
    as_of_date,
    actual_revenue_ytd,
    planned_revenue_ytd,
    planned_revenue_full_year,
    CASE
        WHEN elapsed_days <= 0 OR actual_revenue_ytd IS NULL THEN NULL
        ELSE (actual_revenue_ytd / elapsed_days) * total_days
    END AS projected_full_year_actual,
    CASE
        WHEN planned_revenue_ytd IS NULL OR planned_revenue_ytd = 0 THEN NULL
        ELSE actual_revenue_ytd * 100.0 / planned_revenue_ytd
    END AS ytd_achievement_pct,
    CASE
        WHEN planned_revenue_full_year IS NULL OR planned_revenue_full_year = 0 OR elapsed_days <= 0 OR actual_revenue_ytd IS NULL THEN NULL
        ELSE ((actual_revenue_ytd / elapsed_days) * total_days) * 100.0 / planned_revenue_full_year
    END AS projected_achievement_pct,
    CASE
        WHEN planned_revenue_full_year IS NULL OR planned_revenue_full_year = 0 OR elapsed_days <= 0 OR actual_revenue_ytd IS NULL THEN 'INSUFFICIENT_DATA'
        WHEN (actual_revenue_ytd / elapsed_days) * total_days >= planned_revenue_full_year THEN 'ON_TRACK'
        ELSE 'BEHIND_PLAN'
    END AS annual_target_status
FROM projection;
""".strip()


def _is_major_constraints_progress_question(question: str) -> bool:
    q = _normalize_question(question)
    markers = [
        "major constraints affecting progress",
        "major constraints",
        "constraints affecting progress",
        "what are the major constraints",
    ]
    return any(marker in q for marker in markers) and "progress" in q


def _is_labor_productivity_trend_question(question: str) -> bool:
    q = _normalize_question(question)
    return ("productivity trend" in q or "trend of productivity" in q) and any(
        token in q for token in ["labor", "labour", "workforce", "crew"]
    )


def _labor_productivity_trend_sql() -> str:
    return """
WITH recent_months AS (
    SELECT TOP 12
        [MonthStart],
        AVG(TRY_CAST([Average Productivity (%)] AS FLOAT)) AS [avg_productivity_pct],
        COUNT(*) AS [crew_records]
    FROM [PH_PRODUCTIVITY_WEEKLY_REPORT]
    WHERE TRY_CAST([Average Productivity (%)] AS FLOAT) BETWEEN 0 AND 200
    GROUP BY [MonthStart]
    ORDER BY [MonthStart] DESC
)
SELECT
    [MonthStart],
    CAST([avg_productivity_pct] AS DECIMAL(10,2)) AS [Average Productivity %],
    [crew_records] AS [Crew Records]
FROM recent_months
ORDER BY [MonthStart];
""".strip()


def _is_most_efficient_crews_question(question: str) -> bool:
    q = _normalize_question(question)
    return ("crew" in q or "crews" in q) and any(
        token in q for token in ["most efficient", "highest productivity", "best productivity", "most productive"]
    )


def _most_efficient_crews_sql() -> str:
    return """
WITH latest_month AS (
    SELECT MAX([MonthStart]) AS [month_start]
    FROM [PH_PRODUCTIVITY_WEEKLY_REPORT]
    WHERE TRY_CAST([Average Productivity (%)] AS FLOAT) BETWEEN 0 AND 200
)
SELECT TOP 15
    p.[MonthStart],
    p.[Crew Name],
    p.[Crew Type],
    CAST(AVG(TRY_CAST(p.[Average Productivity (%)] AS FLOAT)) AS DECIMAL(10,2)) AS [Average Productivity %],
    COUNT(*) AS [Observation Rows]
FROM [PH_PRODUCTIVITY_WEEKLY_REPORT] p
INNER JOIN latest_month lm
    ON p.[MonthStart] = lm.[month_start]
WHERE TRY_CAST(p.[Average Productivity (%)] AS FLOAT) BETWEEN 0 AND 200
  AND LEN(ISNULL(p.[Crew Name], '')) < 120
GROUP BY
    p.[MonthStart],
    p.[Crew Name],
    p.[Crew Type]
HAVING COUNT(*) >= 2
ORDER BY [Average Productivity %] DESC, [Observation Rows] DESC, p.[Crew Name];
""".strip()


def _is_workforce_allocation_question(question: str) -> bool:
    q = _normalize_question(question)
    return "workforce allocation" in q and "project" in q


def _workforce_allocation_sql() -> str:
    return """
WITH active_task_manhours AS (
    SELECT
        p.[column2] AS [Project Category],
        COUNT(*) AS [Active Task Rows],
        SUM(COALESCE(TRY_CAST(a.[manhoursactual] AS FLOAT), 0)) AS [Actual Manhours],
        SUM(COALESCE(TRY_CAST(a.[manhourforacst] AS FLOAT), 0)) AS [Forecast Manhours],
        AVG(COALESCE(TRY_CAST(a.[progress] AS FLOAT), 0)) * 100 AS [Avg Progress %]
    FROM [ActivityTaskPlan] a
    INNER JOIN [ProjectIDs] p
        ON LOWER(CONVERT(nvarchar(36), p.[ID])) = LOWER(CONVERT(nvarchar(36), a.[project_id]))
    WHERE TRY_CAST(a.[progress] AS FLOAT) < 1
    GROUP BY p.[column2]
)
SELECT
    [Project Category],
    [Active Task Rows],
    CAST([Actual Manhours] AS DECIMAL(18,2)) AS [Actual Manhours],
    CAST([Forecast Manhours] AS DECIMAL(18,2)) AS [Forecast Manhours],
    CAST([Avg Progress %] AS DECIMAL(10,2)) AS [Avg Progress %]
FROM active_task_manhours
WHERE [Actual Manhours] > 0 OR [Forecast Manhours] > 0
ORDER BY [Forecast Manhours] DESC, [Project Category];
""".strip()


def _major_constraints_progress_sql() -> str:
    return """
WITH latest_snapshot AS (
    SELECT MAX([Week_Number]) AS snapshot_date
    FROM [WellMonitoringReport]
),
phase_metrics AS (
    SELECT
        'Construction' AS [Constraint Area],
        AVG(TRY_CAST([overall_const._10_100] AS FLOAT)) * 100 AS [Avg Progress %],
        SUM(CASE WHEN TRY_CAST([overall_const._10_100] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Lagging Wells],
        COUNT(DISTINCT [pdo_well_id]) AS [Total Wells]
    FROM [WellMonitoringReport] w
    INNER JOIN latest_snapshot s
        ON w.[Week_Number] = s.snapshot_date

    UNION ALL

    SELECT
        'Engineering' AS [Constraint Area],
        AVG(TRY_CAST([overall_engg._10_100] AS FLOAT)) * 100 AS [Avg Progress %],
        SUM(CASE WHEN TRY_CAST([overall_engg._10_100] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Lagging Wells],
        COUNT(DISTINCT [pdo_well_id]) AS [Total Wells]
    FROM [WellMonitoringReport] w
    INNER JOIN latest_snapshot s
        ON w.[Week_Number] = s.snapshot_date

    UNION ALL

    SELECT
        'Flowline Construction' AS [Constraint Area],
        AVG(TRY_CAST([flowline_construction_progress] AS FLOAT)) * 100 AS [Avg Progress %],
        SUM(CASE WHEN TRY_CAST([flowline_construction_progress] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Lagging Wells],
        COUNT(DISTINCT [pdo_well_id]) AS [Total Wells]
    FROM [WellMonitoringReport] w
    INNER JOIN latest_snapshot s
        ON w.[Week_Number] = s.snapshot_date

    UNION ALL

    SELECT
        'Pipe Welding / NDT' AS [Constraint Area],
        AVG(TRY_CAST([cs_pipe_welding_ndt_10_rt_for_op_100_for_60] AS FLOAT)) * 100 AS [Avg Progress %],
        SUM(CASE WHEN TRY_CAST([cs_pipe_welding_ndt_10_rt_for_op_100_for_60] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Lagging Wells],
        COUNT(DISTINCT [pdo_well_id]) AS [Total Wells]
    FROM [WellMonitoringReport] w
    INNER JOIN latest_snapshot s
        ON w.[Week_Number] = s.snapshot_date

    UNION ALL

    SELECT
        'OHL' AS [Constraint Area],
        AVG(TRY_CAST([overall_ohl_progr_100] AS FLOAT)) * 100 AS [Avg Progress %],
        SUM(CASE WHEN TRY_CAST([overall_ohl_progr_100] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Lagging Wells],
        COUNT(DISTINCT [pdo_well_id]) AS [Total Wells]
    FROM [WellMonitoringReport] w
    INNER JOIN latest_snapshot s
        ON w.[Week_Number] = s.snapshot_date

    UNION ALL

    SELECT
        'Material Readiness' AS [Constraint Area],
        AVG(TRY_CAST([overall_material_10_100] AS FLOAT)) * 100 AS [Avg Progress %],
        SUM(CASE WHEN TRY_CAST([overall_material_10_100] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Lagging Wells],
        COUNT(DISTINCT [pdo_well_id]) AS [Total Wells]
    FROM [WellMonitoringReport] w
    INNER JOIN latest_snapshot s
        ON w.[Week_Number] = s.snapshot_date
)
SELECT
    [Constraint Area],
    CAST([Avg Progress %] AS DECIMAL(10,2)) AS [Avg Progress %],
    [Lagging Wells],
    CAST(([Lagging Wells] * 100.0) / NULLIF([Total Wells], 0) AS DECIMAL(10,2)) AS [Lagging Wells %]
FROM phase_metrics
WHERE [Avg Progress %] IS NOT NULL
ORDER BY [Lagging Wells %] DESC, [Avg Progress %] ASC;
""".strip()


def _is_cost_budget_question(question: str) -> bool:
    q = _normalize_question(question)
    return (
        "cost overrun" in q
        or "cost overruns" in q
        or "cost vs budget" in q
        or "budget vs actual" in q
        or "over budget" in q
    )


def _is_performance_kpi_trend_question(question: str) -> bool:
    q = _normalize_question(question)
    return any(token in q for token in [
        "trend analysis of performance kpis",
        "performance kpi trend",
        "kpi trend analysis",
        "trend analysis of kpis",
    ])


def _performance_kpi_trend_sql() -> str:
    return """
WITH latest_weeks AS (
    SELECT TOP 12 CAST([Week_Number] AS DATE) AS [Snapshot Date]
    FROM [WMR_Full]
    WHERE [Week_Number] IS NOT NULL
    GROUP BY CAST([Week_Number] AS DATE)
    ORDER BY [Snapshot Date] DESC
),
weekly_trend AS (
    SELECT
        CAST(f.[Week_Number] AS DATE) AS [Snapshot Date],
        AVG(TRY_CAST(f.[over_all_progress_percentages] AS FLOAT)) * 100 AS [Overall Progress %],
        AVG(TRY_CAST(f.[overall_engg._10_100] AS FLOAT)) * 100 AS [Engineering %],
        AVG(TRY_CAST(f.[overall_const._10_100] AS FLOAT)) * 100 AS [Construction %],
        AVG(TRY_CAST(f.[overall_material_10_100] AS FLOAT)) * 100 AS [Material %],
        AVG(TRY_CAST(f.[flowline_construction_progress] AS FLOAT)) * 100 AS [Flowline %],
        AVG(TRY_CAST(f.[overall_ohl_progr_100] AS FLOAT)) * 100 AS [OHL %],
        AVG(TRY_CAST(f.[overall_comm_progress_100] AS FLOAT)) * 100 AS [Commissioning %]
    FROM [WMR_Full] f
    INNER JOIN latest_weeks w
        ON CAST(f.[Week_Number] AS DATE) = w.[Snapshot Date]
    GROUP BY CAST(f.[Week_Number] AS DATE)
)
SELECT
    [Snapshot Date],
    CAST([Overall Progress %] AS DECIMAL(10,2)) AS [Overall Progress %],
    CAST([Engineering %] AS DECIMAL(10,2)) AS [Engineering %],
    CAST([Construction %] AS DECIMAL(10,2)) AS [Construction %],
    CAST([Material %] AS DECIMAL(10,2)) AS [Material %],
    CAST([Flowline %] AS DECIMAL(10,2)) AS [Flowline %],
    CAST([OHL %] AS DECIMAL(10,2)) AS [OHL %],
    CAST([Commissioning %] AS DECIMAL(10,2)) AS [Commissioning %]
FROM weekly_trend
ORDER BY [Snapshot Date];
""".strip()


def _is_kpi_threshold_deviation_question(question: str) -> bool:
    q = _normalize_question(question)
    return any(token in q for token in [
        "which kpis are deviating from thresholds today",
        "kpis are deviating from thresholds",
    ])


def _uses_kpi_threshold_proxy(question: str) -> bool:
    q = _normalize_question(question)
    return any(token in q for token in [
        "latest operational snapshot",
        "below 50% progress",
        "proxy thresholds",
        "major phase kpis below 50% progress",
    ])


def _kpi_threshold_deviation_proxy_sql() -> str:
    return """
WITH latest_snapshot AS (
    SELECT MAX([Week_Number]) AS snapshot_date
    FROM [WellMonitoringReport]
),
kpi_metrics AS (
    SELECT
        'Overall Progress' AS [KPI],
        AVG(TRY_CAST(w.[over_all_progress_percentages] AS FLOAT)) * 100 AS [Avg Value %],
        SUM(CASE WHEN TRY_CAST(w.[over_all_progress_percentages] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Violating Wells],
        COUNT(DISTINCT w.[pdo_well_id]) AS [Total Wells]
    FROM [WellMonitoringReport] w
    INNER JOIN latest_snapshot s
        ON w.[Week_Number] = s.snapshot_date

    UNION ALL

    SELECT
        'Engineering' AS [KPI],
        AVG(TRY_CAST(w.[overall_engg._10_100] AS FLOAT)) * 100 AS [Avg Value %],
        SUM(CASE WHEN TRY_CAST(w.[overall_engg._10_100] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Violating Wells],
        COUNT(DISTINCT w.[pdo_well_id]) AS [Total Wells]
    FROM [WellMonitoringReport] w
    INNER JOIN latest_snapshot s
        ON w.[Week_Number] = s.snapshot_date

    UNION ALL

    SELECT
        'Construction' AS [KPI],
        AVG(TRY_CAST(w.[overall_const._10_100] AS FLOAT)) * 100 AS [Avg Value %],
        SUM(CASE WHEN TRY_CAST(w.[overall_const._10_100] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Violating Wells],
        COUNT(DISTINCT w.[pdo_well_id]) AS [Total Wells]
    FROM [WellMonitoringReport] w
    INNER JOIN latest_snapshot s
        ON w.[Week_Number] = s.snapshot_date

    UNION ALL

    SELECT
        'Material Readiness' AS [KPI],
        AVG(TRY_CAST(w.[overall_material_10_100] AS FLOAT)) * 100 AS [Avg Value %],
        SUM(CASE WHEN TRY_CAST(w.[overall_material_10_100] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Violating Wells],
        COUNT(DISTINCT w.[pdo_well_id]) AS [Total Wells]
    FROM [WellMonitoringReport] w
    INNER JOIN latest_snapshot s
        ON w.[Week_Number] = s.snapshot_date

    UNION ALL

    SELECT
        'Flowline Construction' AS [KPI],
        AVG(TRY_CAST(w.[flowline_construction_progress] AS FLOAT)) * 100 AS [Avg Value %],
        SUM(CASE WHEN TRY_CAST(w.[flowline_construction_progress] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Violating Wells],
        COUNT(DISTINCT w.[pdo_well_id]) AS [Total Wells]
    FROM [WellMonitoringReport] w
    INNER JOIN latest_snapshot s
        ON w.[Week_Number] = s.snapshot_date

    UNION ALL

    SELECT
        'OHL' AS [KPI],
        AVG(TRY_CAST(w.[overall_ohl_progr_100] AS FLOAT)) * 100 AS [Avg Value %],
        SUM(CASE WHEN TRY_CAST(w.[overall_ohl_progr_100] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Violating Wells],
        COUNT(DISTINCT w.[pdo_well_id]) AS [Total Wells]
    FROM [WellMonitoringReport] w
    INNER JOIN latest_snapshot s
        ON w.[Week_Number] = s.snapshot_date

    UNION ALL

    SELECT
        'Commissioning' AS [KPI],
        AVG(TRY_CAST(w.[overall_comm_progress_100] AS FLOAT)) * 100 AS [Avg Value %],
        SUM(CASE WHEN TRY_CAST(w.[overall_comm_progress_100] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Violating Wells],
        COUNT(DISTINCT w.[pdo_well_id]) AS [Total Wells]
    FROM [WellMonitoringReport] w
    INNER JOIN latest_snapshot s
        ON w.[Week_Number] = s.snapshot_date
)
SELECT
    [KPI],
    CAST([Avg Value %] AS DECIMAL(10,2)) AS [Avg Value %],
    [Violating Wells],
    CAST(([Violating Wells] * 100.0) / NULLIF([Total Wells], 0) AS DECIMAL(10,2)) AS [Violating Wells %]
FROM kpi_metrics
WHERE [Avg Value %] IS NOT NULL
ORDER BY [Violating Wells %] DESC, [Avg Value %] ASC;
""".strip()


def _is_delivery_risk_question(question: str) -> bool:
    q = _normalize_question(question)
    return "risks impacting delivery" in q or "top 10 risks impacting delivery" in q


def _uses_operational_delivery_risk_proxy(question: str) -> bool:
    q = _normalize_question(question)
    return any(token in q for token in [
        "operational delivery risk proxy",
        "latest wellmonitoringreport snapshot",
        "at-risk project categories",
        "use operational proxy",
    ])


def _delivery_risk_proxy_category_sql() -> str:
    return """
WITH latest_snapshot AS (
    SELECT MAX([Week_Number]) AS snapshot_date
    FROM [WellMonitoringReport]
),
latest_wmr AS (
    SELECT
        TRY_CONVERT(nvarchar(50), w.[pdo_well_id]) AS [well_id],
        TRY_CAST(w.[over_all_progress_percentages] AS FLOAT) AS [overall_progress],
        TRY_CAST(w.[overall_engg._10_100] AS FLOAT) AS [engg_progress],
        TRY_CAST(w.[overall_const._10_100] AS FLOAT) AS [const_progress],
        TRY_CAST(w.[overall_material_10_100] AS FLOAT) AS [material_progress],
        TRY_CAST(w.[flowline_construction_progress] AS FLOAT) AS [flowline_progress],
        TRY_CAST(w.[overall_ohl_progr_100] AS FLOAT) AS [ohl_progress],
        TRY_CAST(w.[exp.rig_off_location_sap_data] AS DATE) AS [expected_rig_off],
        w.[actual_rig_off_date],
        w.[buffer_status]
    FROM [WellMonitoringReport] w
    INNER JOIN latest_snapshot s
        ON w.[Week_Number] = s.snapshot_date
),
category_by_well AS (
    SELECT
        TRY_CONVERT(nvarchar(50), j.[Well ID]) AS [well_id],
        MAX(j.[Category]) AS [Category]
    FROM [Job_Progress_Report_GB] j
    WHERE j.[Category] IS NOT NULL
    GROUP BY TRY_CONVERT(nvarchar(50), j.[Well ID])
),
scored_wells AS (
    SELECT
        c.[Category],
        w.[well_id],
        w.[overall_progress],
        CASE WHEN w.[expected_rig_off] < CAST(GETDATE() AS DATE) AND w.[actual_rig_off_date] IS NULL THEN 4 ELSE 0 END
        + CASE WHEN w.[overall_progress] < 0.30 THEN 3 WHEN w.[overall_progress] < 0.60 THEN 1 ELSE 0 END
        + CASE WHEN w.[engg_progress] < 0.50 THEN 1 ELSE 0 END
        + CASE WHEN w.[const_progress] < 0.50 THEN 1 ELSE 0 END
        + CASE WHEN w.[material_progress] < 0.50 THEN 1 ELSE 0 END
        + CASE WHEN w.[flowline_progress] < 0.50 THEN 1 ELSE 0 END
        + CASE WHEN w.[ohl_progress] < 0.50 THEN 1 ELSE 0 END
        + CASE WHEN w.[buffer_status] = 'ROL' AND w.[overall_progress] < 0.60 THEN 1 ELSE 0 END AS [risk_score],
        CASE WHEN w.[expected_rig_off] < CAST(GETDATE() AS DATE) AND w.[actual_rig_off_date] IS NULL THEN 1 ELSE 0 END AS [overdue_rig_off_flag]
    FROM latest_wmr w
    INNER JOIN category_by_well c
        ON c.[well_id] = w.[well_id]
)
SELECT TOP 10
    [Category] AS [Project],
    COUNT(DISTINCT [well_id]) AS [Wells],
    CAST(AVG([overall_progress]) * 100 AS DECIMAL(10,2)) AS [Avg Progress %],
    CAST(AVG(CAST([risk_score] AS FLOAT)) AS DECIMAL(10,2)) AS [Avg Delivery Risk Score],
    SUM(CASE WHEN [risk_score] >= 6 THEN 1 ELSE 0 END) AS [High-Risk Wells],
    SUM([overdue_rig_off_flag]) AS [Overdue Rig-Off Wells]
FROM scored_wells
GROUP BY [Category]
ORDER BY [Avg Delivery Risk Score] DESC, [High-Risk Wells] DESC, [Project];
""".strip()


def _is_top_cost_overrun_question(question: str) -> bool:
    q = _normalize_question(question)
    return _is_cost_budget_question(question) and any(token in q for token in ["top", "highest", "largest", "major"])


def _extract_cost_budget_grain(question: str) -> str | None:
    q = _normalize_question(question)
    if "project code" in q or "rig code" in q or "rigcode" in q:
        return "project_code"
    if "category" in q:
        return "category"
    if "well level" in q or "by well" in q or "well-wise" in q or "well wise" in q:
        return "well"
    return None


def _extract_cost_budget_window(question: str) -> str | None:
    q = _normalize_question(question)
    if "this month" in q or "current month" in q or "month-to-date" in q or "month to date" in q:
        return "current_month"
    if "this quarter" in q or "current quarter" in q or "quarter-to-date" in q or "quarter to date" in q:
        return "current_quarter"
    if "this year" in q or "current year" in q or "year-to-date" in q or "year to date" in q or "ytd" in q:
        return "current_year"
    if "cumulative" in q or "to-date" in q or "to date" in q or "overall" in q or "all time" in q:
        return "cumulative_to_date"
    return None


def _uses_revenue_budget_proxy(question: str) -> bool:
    q = _normalize_question(question)
    return any(token in q for token in [
        "planned vs actual",
        "purpose value",
        "use proxy",
        "use revenue",
        "budget proxy",
        "cost proxy",
    ])


def _uses_operational_context_proxy(question: str) -> bool:
    q = _normalize_question(question)
    return any(token in q for token in [
        "operational context",
        "why proxy",
        "use issue text",
        "reason_if_kpi_not_met",
        "remark_status_area_of_attention_issues_",
    ])


def _cost_budget_window_filter(window: str | None) -> str:
    if window == "current_month":
        return "CAST(r.[created_at] AS DATE) >= DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1) AND CAST(r.[created_at] AS DATE) <= CAST(GETDATE() AS DATE)"
    if window == "current_quarter":
        return "CAST(r.[created_at] AS DATE) >= DATEADD(QUARTER, DATEDIFF(QUARTER, 0, GETDATE()), 0) AND CAST(r.[created_at] AS DATE) <= CAST(GETDATE() AS DATE)"
    if window == "current_year":
        return "CAST(r.[created_at] AS DATE) >= DATEFROMPARTS(YEAR(GETDATE()), 1, 1) AND CAST(r.[created_at] AS DATE) <= CAST(GETDATE() AS DATE)"
    return "CAST(r.[created_at] AS DATE) <= CAST(GETDATE() AS DATE)"


def _cost_budget_common_ctes(window: str | None) -> str:
    where_clause = _cost_budget_window_filter(window)
    return f"""
WITH revenue_by_well AS (
    SELECT
        TRY_CONVERT(nvarchar(50), r.[well_id]) AS [well_id],
        MAX(r.[rigcode]) AS [project_code],
        SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) AS [planned_value],
        SUM(TRY_CAST(r.[actual_purpose_value] AS DECIMAL(18,2))) AS [actual_value]
    FROM [Revenue] r
    WHERE {where_clause}
      AND TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2)) IS NOT NULL
      AND TRY_CAST(r.[actual_purpose_value] AS DECIMAL(18,2)) IS NOT NULL
    GROUP BY TRY_CONVERT(nvarchar(50), r.[well_id])
),
wmr_latest AS (
    SELECT
        w.*,
        ROW_NUMBER() OVER (
            PARTITION BY w.[pdo_well_id]
            ORDER BY w.[Week_Number] DESC
        ) AS rn
    FROM [WellMonitoringReport] w
),
well_context AS (
    SELECT
        TRY_CONVERT(nvarchar(50), w.[pdo_well_id]) AS [well_id],
        w.[well_name_after_spud],
        w.[Cluster],
        COALESCE(
            NULLIF(LTRIM(RTRIM(w.[reason_if_kpi_not_met])), ''),
            NULLIF(LTRIM(RTRIM(w.[remark_status_area_of_attention_issues_])), '')
        ) AS [operational_context]
    FROM wmr_latest w
    WHERE w.rn = 1
),
category_by_well AS (
    SELECT
        TRY_CONVERT(nvarchar(50), j.[Well ID]) AS [well_id],
        MAX(j.[Category]) AS [Category]
    FROM [Job_Progress_Report_GB] j
    WHERE j.[Category] IS NOT NULL
    GROUP BY TRY_CONVERT(nvarchar(50), j.[Well ID])
)
""".strip()


def _cost_vs_budget_well_sql(window: str | None, include_context: bool = False) -> str:
    ctes = _cost_budget_common_ctes(window)
    context_cols = ""
    if include_context:
        context_cols = """,
    wc.[operational_context] AS [Operational Context],
    CASE
        WHEN wc.[operational_context] IS NULL THEN 'No direct cost-cause field available in current schema'
        ELSE 'Operational issue text only; not a validated cost-cause'
    END AS [Why Note]"""
    return f"""
{ctes}
SELECT TOP 10
    wc.[well_name_after_spud] AS [Well Name],
    r.[project_code] AS [Project Code],
    wc.[Cluster],
    r.[planned_value] AS [Planned Value],
    r.[actual_value] AS [Actual Value],
    r.[actual_value] - r.[planned_value] AS [Overrun Amount],
    CASE
        WHEN r.[planned_value] = 0 THEN NULL
        ELSE ((r.[actual_value] - r.[planned_value]) * 100.0) / r.[planned_value]
    END AS [Overrun Pct]{context_cols}
FROM revenue_by_well r
LEFT JOIN well_context wc
    ON wc.[well_id] = r.[well_id]
WHERE r.[actual_value] > r.[planned_value]
  AND r.[planned_value] > 0
ORDER BY [Overrun Amount] DESC, [Well Name];
""".strip()


def _cost_vs_budget_project_code_sql(window: str | None, top_only: bool = False, include_context: bool = False) -> str:
    ctes = _cost_budget_common_ctes(window)
    top_clause = "TOP 10 " if top_only else ""
    context_cte = ""
    context_join = ""
    context_cols = ""
    if include_context:
        context_cte = """
, ranked_context AS (
    SELECT
        r.[project_code],
        wc.[operational_context],
        COUNT(DISTINCT r.[well_id]) AS [context_wells],
        ROW_NUMBER() OVER (
            PARTITION BY r.[project_code]
            ORDER BY COUNT(DISTINCT r.[well_id]) DESC, wc.[operational_context]
        ) AS rn
    FROM revenue_by_well r
    INNER JOIN well_context wc
        ON wc.[well_id] = r.[well_id]
    WHERE r.[actual_value] > r.[planned_value]
      AND r.[planned_value] > 0
      AND wc.[operational_context] IS NOT NULL
    GROUP BY r.[project_code], wc.[operational_context]
)
"""
        context_join = """
LEFT JOIN ranked_context rc
    ON rc.[project_code] = a.[Project Code]
   AND rc.rn = 1"""
        context_cols = """,
    rc.[operational_context] AS [Operational Context],
    rc.[context_wells] AS [Wells With Same Context]"""
    return f"""
{ctes}{context_cte}
, aggregated AS (
    SELECT
        r.[project_code] AS [Project Code],
        SUM(r.[planned_value]) AS [Planned Value],
        SUM(r.[actual_value]) AS [Actual Value]
    FROM revenue_by_well r
    GROUP BY r.[project_code]
)
SELECT {top_clause}
    a.[Project Code],
    a.[Planned Value],
    a.[Actual Value],
    a.[Actual Value] - a.[Planned Value] AS [Overrun Amount],
    CASE
        WHEN a.[Planned Value] = 0 THEN NULL
        ELSE ((a.[Actual Value] - a.[Planned Value]) * 100.0) / a.[Planned Value]
    END AS [Overrun Pct]{context_cols}
FROM aggregated a
{context_join}
WHERE a.[Actual Value] > a.[Planned Value]
  AND a.[Planned Value] > 0
ORDER BY [Overrun Amount] DESC, a.[Project Code];
""".strip()


def _cost_vs_budget_category_sql(window: str | None, top_only: bool = False, include_context: bool = False) -> str:
    ctes = _cost_budget_common_ctes(window)
    top_clause = "TOP 10 " if top_only else ""
    context_cte = ""
    context_join = ""
    context_cols = ""
    if include_context:
        context_cte = """
, ranked_context AS (
    SELECT
        c.[Category],
        wc.[operational_context],
        COUNT(DISTINCT r.[well_id]) AS [context_wells],
        ROW_NUMBER() OVER (
            PARTITION BY c.[Category]
            ORDER BY COUNT(DISTINCT r.[well_id]) DESC, wc.[operational_context]
        ) AS rn
    FROM revenue_by_well r
    INNER JOIN category_by_well c
        ON c.[well_id] = r.[well_id]
    INNER JOIN well_context wc
        ON wc.[well_id] = r.[well_id]
    WHERE r.[actual_value] > r.[planned_value]
      AND r.[planned_value] > 0
      AND wc.[operational_context] IS NOT NULL
    GROUP BY c.[Category], wc.[operational_context]
)
"""
        context_join = """
LEFT JOIN ranked_context rc
    ON rc.[Category] = a.[Category]
   AND rc.rn = 1"""
        context_cols = """,
    rc.[operational_context] AS [Operational Context],
    rc.[context_wells] AS [Wells With Same Context]"""
    return f"""
{ctes}{context_cte}
, aggregated AS (
    SELECT
        c.[Category],
        SUM(r.[planned_value]) AS [Planned Value],
        SUM(r.[actual_value]) AS [Actual Value]
    FROM revenue_by_well r
    INNER JOIN category_by_well c
        ON c.[well_id] = r.[well_id]
    GROUP BY c.[Category]
)
SELECT {top_clause}
    a.[Category],
    a.[Planned Value],
    a.[Actual Value],
    a.[Actual Value] - a.[Planned Value] AS [Overrun Amount],
    CASE
        WHEN a.[Planned Value] = 0 THEN NULL
        ELSE ((a.[Actual Value] - a.[Planned Value]) * 100.0) / a.[Planned Value]
    END AS [Overrun Pct]{context_cols}
FROM aggregated a
{context_join}
WHERE a.[Actual Value] > a.[Planned Value]
  AND a.[Planned Value] > 0
ORDER BY [Overrun Amount] DESC, a.[Category];
""".strip()


def _is_forecast_manpower_requirement_question(question: str) -> bool:
    q = _normalize_question(question)
    return "forecast manpower requirement" in q or "forecasted manpower requirement" in q


def _extract_manpower_requirement_grain(question: str) -> str | None:
    q = _normalize_question(question)
    if "by well" in q or "per well" in q or ("well" in q and "project" not in q and "category" not in q):
        return "well"
    if "category" in q or "project" in q or "across projects" in q:
        return "category"
    return None


def _uses_manhour_forecast_proxy(question: str) -> bool:
    q = _normalize_question(question)
    return any(token in q for token in [
        "manhourforacst",
        "forecast manhours",
        "activitytaskplan",
        "use proxy",
        "current open workload",
        "open workload",
    ])


def _forecast_manpower_requirement_category_sql() -> str:
    return """
SELECT
    p.[column2] AS [Project Category],
    COUNT(*) AS [Open Task Rows],
    CAST(SUM(COALESCE(TRY_CAST(a.[manhourforacst] AS FLOAT), 0)) AS DECIMAL(18,2)) AS [Forecast Manhours Required],
    CAST(AVG(COALESCE(TRY_CAST(a.[progress] AS FLOAT), 0)) * 100 AS DECIMAL(10,2)) AS [Avg Open-Task Progress %]
FROM [ActivityTaskPlan] a
INNER JOIN [ProjectIDs] p
    ON LOWER(CONVERT(nvarchar(36), p.[ID])) = LOWER(CONVERT(nvarchar(36), a.[project_id]))
WHERE TRY_CAST(a.[progress] AS FLOAT) < 1
GROUP BY p.[column2]
HAVING SUM(COALESCE(TRY_CAST(a.[manhourforacst] AS FLOAT), 0)) > 0
ORDER BY [Forecast Manhours Required] DESC, [Project Category];
""".strip()


def _forecast_manpower_requirement_well_sql() -> str:
    return """
WITH well_lookup AS (
    SELECT
        TRY_CONVERT(nvarchar(50), [pdo_well_id]) AS [well_id],
        MAX([well_name_after_spud]) AS [well_name_after_spud]
    FROM [WellMonitoringReport]
    GROUP BY TRY_CONVERT(nvarchar(50), [pdo_well_id])
)
SELECT TOP 25
    a.[Well_ID] AS [Well ID],
    wl.[well_name_after_spud] AS [Well Name],
    COUNT(*) AS [Open Task Rows],
    CAST(SUM(COALESCE(TRY_CAST(a.[manhourforacst] AS FLOAT), 0)) AS DECIMAL(18,2)) AS [Forecast Manhours Required],
    CAST(AVG(COALESCE(TRY_CAST(a.[progress] AS FLOAT), 0)) * 100 AS DECIMAL(10,2)) AS [Avg Open-Task Progress %]
FROM [ActivityTaskPlan] a
LEFT JOIN well_lookup wl
    ON wl.[well_id] = TRY_CONVERT(nvarchar(50), a.[Well_ID])
WHERE TRY_CAST(a.[progress] AS FLOAT) < 1
GROUP BY a.[Well_ID], wl.[well_name_after_spud]
HAVING SUM(COALESCE(TRY_CAST(a.[manhourforacst] AS FLOAT), 0)) > 0
ORDER BY [Forecast Manhours Required] DESC, [Well ID];
""".strip()


def _is_skills_shortage_question(question: str) -> bool:
    q = _normalize_question(question)
    return "skills are in shortage" in q or "skills in shortage" in q


def _uses_skills_shortage_proxy(question: str) -> bool:
    q = _normalize_question(question)
    return any(token in q for token in [
        "crew_type demand",
        "crew type demand",
        "activitytaskplan",
        "forecast manhours",
        "use proxy",
        "open tasks",
    ])


def _skills_shortage_proxy_sql() -> str:
    return """
SELECT TOP 15
    a.[crew_type] AS [Crew Type / Skill Proxy],
    COUNT(*) AS [Open Task Rows],
    CAST(SUM(COALESCE(TRY_CAST(a.[manhourforacst] AS FLOAT), 0)) AS DECIMAL(18,2)) AS [Forecast Manhours Required],
    CAST(AVG(COALESCE(TRY_CAST(a.[progress] AS FLOAT), 0)) * 100 AS DECIMAL(10,2)) AS [Avg Progress %]
FROM [ActivityTaskPlan] a
WHERE NULLIF(LTRIM(RTRIM(a.[crew_type])), '') IS NOT NULL
  AND TRY_CAST(a.[progress] AS FLOAT) < 1
GROUP BY a.[crew_type]
HAVING SUM(COALESCE(TRY_CAST(a.[manhourforacst] AS FLOAT), 0)) > 0
ORDER BY [Forecast Manhours Required] DESC, [Open Task Rows] DESC, a.[crew_type];
""".strip()


def _is_subcontractor_manpower_status_question(question: str) -> bool:
    q = _normalize_question(question)
    return "subcontractor manpower status" in q


def _uses_subcontractor_manpower_proxy(question: str) -> bool:
    q = _normalize_question(question)
    return any(token in q for token in [
        "crew-count",
        "crew count",
        "productivity proxy",
        "ph_productivity",
        "latest month",
        "use proxy",
    ])


def _subcontractor_manpower_status_proxy_sql() -> str:
    return """
WITH latest_month AS (
    SELECT MAX([MonthStart]) AS [month_start]
    FROM [PH_PRODUCTIVITY_WEEKLY_REPORT]
    WHERE TRY_CAST([Average Productivity (%)] AS FLOAT) BETWEEN 0 AND 200
)
SELECT
    p.[MonthStart],
    p.[ATNM/Sub Contractor] AS [Workforce Type],
    COUNT(DISTINCT CONCAT(ISNULL(p.[Crew Name], ''), '|', ISNULL(p.[Crew Type], ''))) AS [Distinct Crew Groups],
    COUNT(DISTINCT p.[Crew Discipline]) AS [Crew Disciplines],
    CAST(AVG(TRY_CAST(p.[Average Productivity (%)] AS FLOAT)) AS DECIMAL(10,2)) AS [Average Productivity %]
FROM [PH_PRODUCTIVITY_WEEKLY_REPORT] p
INNER JOIN latest_month lm
    ON p.[MonthStart] = lm.[month_start]
WHERE TRY_CAST(p.[Average Productivity (%)] AS FLOAT) BETWEEN 0 AND 200
GROUP BY p.[MonthStart], p.[ATNM/Sub Contractor]
ORDER BY [Distinct Crew Groups] DESC, [Average Productivity %] DESC;
""".strip()


def _is_weekly_overdue_milestones_question(question: str) -> bool:
    q = _normalize_question(question)
    return "milestone" in q and "overdue" in q and ("this week" in q or "current week" in q)


def _uses_activity_taskplan_scope(question: str) -> bool:
    q = _normalize_question(question)
    scope_markers = [
        "activitytaskplan",
        "schedule milestones/tasks",
        "schedule milestones",
        "schedule tasks",
        "task milestones",
        "task milestone",
    ]
    return any(marker in q for marker in scope_markers)


def _weekly_overdue_activity_tasks_sql() -> str:
    return """
WITH week_bounds AS (
    SELECT
        CAST(DATEADD(DAY, -(DATEDIFF(DAY, '19000101', CAST(GETDATE() AS DATE)) % 7), CAST(GETDATE() AS DATE)) AS DATE) AS week_start,
        CAST(DATEADD(DAY, 6 - (DATEDIFF(DAY, '19000101', CAST(GETDATE() AS DATE)) % 7), CAST(GETDATE() AS DATE)) AS DATE) AS week_end
),
well_lookup AS (
    SELECT
        TRY_CONVERT(nvarchar(50), w.[pdo_well_id]) AS [well_id],
        MAX(w.[well_name_after_spud]) AS [well_name_after_spud]
    FROM [WellMonitoringReport] w
    GROUP BY TRY_CONVERT(nvarchar(50), w.[pdo_well_id])
)
SELECT
    a.[Well_ID],
    wl.[well_name_after_spud] AS [Well Name],
    a.[project_id],
    a.[text] AS [Milestone],
    CAST(a.[target_end] AS DATE) AS [Due Date],
    CAST(a.[actual_end] AS DATE) AS [Actual End Date],
    TRY_CAST(a.[progress] AS DECIMAL(10,4)) AS [Progress]
FROM [ActivityTaskPlan] a
CROSS JOIN week_bounds wb
LEFT JOIN well_lookup wl
    ON wl.[well_id] = TRY_CONVERT(nvarchar(50), a.[Well_ID])
WHERE
    a.[target_end] IS NOT NULL
    AND CAST(a.[target_end] AS DATE) >= wb.[week_start]
    AND CAST(a.[target_end] AS DATE) <= wb.[week_end]
    AND CAST(a.[target_end] AS DATE) < CAST(GETDATE() AS DATE)
    AND (a.[actual_end] IS NULL OR CAST(a.[actual_end] AS DATE) > CAST(a.[target_end] AS DATE))
    AND NULLIF(LTRIM(RTRIM(a.[text])), '') IS NOT NULL
ORDER BY
    CAST(a.[target_end] AS DATE),
    wl.[well_name_after_spud],
    a.[text];
""".strip()


def _is_critical_path_question(question: str) -> bool:
    q = _normalize_question(question)
    return "critical path" in q and ("activity" in q or "activities" in q)


def _uses_critical_path_proxy(question: str) -> bool:
    q = _normalize_question(question)
    return "proxy" in q or "currently critical open activities" in q or "critical activities" in q


def _uses_portfolio_scope(question: str) -> bool:
    q = _normalize_question(question)
    scope_markers = [
        "portfolio",
        "across the portfolio",
        "all wells",
        "all projects",
        "overall",
    ]
    return any(marker in q for marker in scope_markers)


def _critical_path_proxy_portfolio_sql() -> str:
    return """
WITH well_lookup AS (
    SELECT
        TRY_CONVERT(nvarchar(50), w.[pdo_well_id]) AS [well_id],
        MAX(w.[well_name_after_spud]) AS [well_name_after_spud],
        MAX(w.[rig_no]) AS [rig_no],
        MAX(w.[Cluster]) AS [Cluster]
    FROM [WellMonitoringReport] w
    GROUP BY TRY_CONVERT(nvarchar(50), w.[pdo_well_id])
),
open_activities AS (
    SELECT
        a.[Well_ID],
        wl.[well_name_after_spud],
        wl.[rig_no],
        wl.[Cluster],
        a.[project_id],
        a.[source_id] AS [task_id],
        a.[text] AS [activity_name],
        a.[type] AS [activity_type],
        CAST(a.[target_end] AS DATE) AS [target_end],
        CAST(a.[actual_end] AS DATE) AS [actual_end],
        TRY_CAST(a.[remaining_duration] AS FLOAT) AS [remaining_duration],
        TRY_CAST(a.[progress] AS FLOAT) AS [progress_ratio],
        a.[ancestor],
        a.[parent]
    FROM [ActivityTaskPlan] a
    LEFT JOIN well_lookup wl
        ON wl.[well_id] = TRY_CONVERT(nvarchar(50), a.[Well_ID])
    WHERE
        a.[target_end] IS NOT NULL
        AND NULLIF(LTRIM(RTRIM(a.[text])), '') IS NOT NULL
        AND (a.[actual_end] IS NULL OR CAST(a.[actual_end] AS DATE) > CAST(a.[target_end] AS DATE))
        AND (TRY_CAST(a.[progress] AS FLOAT) IS NULL OR TRY_CAST(a.[progress] AS FLOAT) < 1)
        AND (TRY_CAST(a.[remaining_duration] AS FLOAT) IS NULL OR TRY_CAST(a.[remaining_duration] AS FLOAT) > 0)
)
SELECT TOP 25
    [Well_ID] AS [Well ID],
    [well_name_after_spud] AS [Well Name],
    [rig_no] AS [Rig No],
    [Cluster],
    [project_id] AS [Project ID],
    [task_id] AS [Task ID],
    [activity_name] AS [Activity],
    [activity_type] AS [Activity Type],
    [target_end] AS [Target End],
    [actual_end] AS [Actual End],
    [remaining_duration] AS [Remaining Duration],
    [progress_ratio] * 100 AS [Progress %],
    CASE
        WHEN [target_end] < CAST(GETDATE() AS DATE) THEN DATEDIFF(DAY, [target_end], CAST(GETDATE() AS DATE))
        ELSE 0
    END AS [Overdue Days],
    [ancestor] AS [Ancestor Task],
    [parent] AS [Parent Task]
FROM open_activities
ORDER BY
    CASE WHEN [target_end] < CAST(GETDATE() AS DATE) THEN 0 ELSE 1 END,
    CASE
        WHEN [target_end] < CAST(GETDATE() AS DATE) THEN DATEDIFF(DAY, [target_end], CAST(GETDATE() AS DATE))
        ELSE 0
    END DESC,
    COALESCE([remaining_duration], 0) DESC,
    COALESCE([progress_ratio], 0) ASC,
    [target_end];
""".strip()


class SQLSignature(dspy.Signature):
    """You are a Microsoft SQL Server expert. Generate precise SELECT queries
    using ONLY the tables and columns provided in the schema context.

    RULES (CRITICAL — NEVER violate these):
    1. ONLY use table names and column names that appear in the schema context.
    2. If a required column is NOT in the schema context, respond with INSUFFICIENT_SCHEMA.
    3. NEVER invent, guess, or hallucinate column names.
    4. Use exact column names as shown (preserve case, underscores).
    5. ALWAYS wrap table and column names in [square brackets] if they contain spaces, dots, or special characters. (e.g., [PO No], [Job_Progress_Report_GB]).
    6. Always specify table aliases for clarity in JOINs.
    7. Use IS NOT NULL to find rows where a value is recorded.
    8. First keyword must be SELECT or WITH.
    9. Do NOT use markdown formatting. No ```sql blocks.
    10. When comparing numeric columns (like days, counts, KPIs) with values, ALWAYS wrap the column in TRY_CAST or CAST to ensure proper type conversion: WHERE TRY_CAST([column_name] AS FLOAT) > 2
    11. IMPORTANT: Use 'WellMonitoringReport' (NOT _Latest) for queries about clusters, fields, or historical data. WellMonitoringReport_Latest only contains Marmul cluster data - use it ONLY when explicitly asking for "latest" or "current" status of specific wells.
    12. If the user filters by specific entities, names, locations, or IDs that are NOT explicitly found as column names in the schema context, DO NOT ABORT! These are search values inside the database. Assume they reside in descriptive categorical columns and dynamically apply a filter using `LIKE '%[Entity]%'`.
    13. COUNTING WELLS: ALWAYS use COUNT(DISTINCT pdo_well_id) for counting unique wells. NEVER count well_name_after_spud - it can have duplicates. Use well_name_after_spud only for display names, not for counting.
    14. When asking "how many wells" or "number of wells", ALWAYS use pdo_well_id as the unique identifier - this is the PDO-assigned unique ID for each well.
    15. "SHOW ME WELLS" QUERIES: When user asks to show/display/list wells, ALWAYS return MULTIPLE useful columns: pdo_well_id, well_name_after_spud, relevant metric columns, and any filter columns used. NEVER return only well_name_after_spud - that's useless for analysis.
    16. CRITICAL COLUMN MAPPINGS - NEVER use wrong column names:
       - For WELL PROGRESS: Use 'over_all_progress_percentages' (NOT 'progress', NOT 'acutal_progress')
       - For WELL NAME: Use 'well_name_after_spud' (NOT 'well_name', NOT 'ssfd_wells')
       - For LOCATION: Use 'well_location' (NOT 'location')
       - For RIG: Use 'rig_no' (NOT 'rig_id')
       - For CLUSTER: Use 'Cluster' (exact case)
       - For FIELD (SAP): Use 'Field' column in SAP_DRILLING_SEQUENCE table
       - For RIG ARRIVAL/SPUD DATE: Use 'actual_rig_on_date' (NOT 'actual_start_date' - that is different!)
       - For DATE DIFFERENCE (spud, rig on, tie-in): Use actual_rig_on_date not actual_start_date
    17. JOIN KEYS:
       - WellMonitoringReport.pdo_well_id = Job_Progress_Report_GB.Well_ID
       - WellMonitoringReport.pdo_well_id = Revenue.Well_ID
       - WellMonitoringReport.rig_no = crews.rig_code
       - WellMonitoringReport.well_name_after_spud = SAP_DRILLING_SEQUENCE.Well_Name
       - WMR_Full.pdo_well_id = WellMonitoringReport.pdo_well_id
    18. CRITICAL - AGGREGATION WITH MIXED TYPES: When summing columns where some are nvarchar (text) type, you MUST wrap them in TRY_CAST([column] AS DECIMAL(18,2)) BEFORE the SUM. Example: SUM(TRY_CAST(planned_purpose_value AS DECIMAL(18,2))) - never try to SUM nvarchar directly!
    19. ACHIEVEMENT RATE CALCULATION: For "achievement rate" or "actual vs planned" queries, calculate AFTER aggregation: SUM(actual) / SUM(planned) - NOT ratio of individual rows.
    20. CRITICAL - RIG CODE vs LOCATION: When user mentions rig identifiers like NL0010, NF0010, ML0010, etc., ALWAYS use Revenue.rigcode column for filtering, NOT well_location! Rig codes are in the 'rigcode' column, not in location columns.
    21. COLUMN NAME WITH SPACES: When column name has spaces like "Well ID", wrap in brackets: [Well ID]
    22. WELL ID JOIN NOTE: Job_Progress_Report_GB uses [Well ID] (with brackets due to space), not "Well_ID"
    23. WEEK NUMBER FILTER: Only filter by Week_Number if user specifies EXACT date (e.g., "on March 19, 2026"). For "this week" or general progress, DO NOT filter by Week_Number - just get all wells for the cluster.
    24. USE REVENUE TABLE FOR PROGRESS: For "actual vs planned progress" or "overperformed" queries, ALWAYS use the Revenue table with rigcode filter. Do NOT invent tables like "PerformanceData" - use Revenue!
    26. REVENUE JOIN WITH WELLMONITORINGREPORT: When joining Revenue with WellMonitoringReport, ALWAYS use: "INNER JOIN WellMonitoringReport w ON w.pdo_well_id = r.Well_ID" - do NOT use subqueries or complex ON conditions!
    27. APPMASTERDB VIEW LOGIC - EXACT COLUMN NAMES:
        # Job_Progress_Report_GB columns (USE THESE EXACT NAMES):
        - [Well ID] - with brackets! (NOT Well_ID)
        - [Well Name / Project Name]
        - [Category] - from ProjectIDs.column2
        - [Week-1 Plan %], [Week-1 Actual %], [Week-2 Plan %], [Week-2 Actual %], etc
        - [Current Month Plan %], [Current Month Actual %]
        - [Purpose Value] - monetary value
        - [Target End] - date

        # Week bucket definitions (for calculations):
        - W1 = days 1-7, W2 = 8-14, W3 = 15-21, W4 = 22-28, W5 = 29+

        # VMB LOGIC FORMULAS (from VMB_Logics.xlsx):
        # 1. Project Tie in port readiness = actual_rig_on_date - date_of_tie_in_port_readiness (Target: >140 days = green)
        # 2. Location Pegged to Spud = actual_rig_on_date - actual_pegged_date (Target: >140 days = green)
        # 3. Stable Rig Sequence = actual_rig_on_date - scr_date (Target: >90 days = green)
        # 4. FLAF to Spud = actual_rig_on_date - flaf_issue_date (Target: >90 days = green)
        # 5. Survey Report from FLAF = date_of_site_survey_report_issuance - flaf_issue_date (Target: <15 days = green)
        # 6. Commissioning Duration = actual_comm_finish_date - actual_rig_off_date (Target: <5 days with Rig/FBU/RSR, <15 days with Hoist)

        # PH_Productivity columns (USE THESE EXACT NAMES):
        - [Date] - action date
        - [PA Name] - Permit Applicant (from task_assignee email before '.')
        - [PH Emp ID] - PH Employee ID
        - [PH Name] - QHSE Supervisor (from Employee.Email = supervisor_email)
        - [ATNM/Sub Contractor] - 'ATNM' if 6-digit ID starting with 9, else 'Sub contractor'
        - [Crew Type] - crew type code
        - [Crew Name] - crew description
        - [Average Productivity (%)] - (data_qty/data_hours)/Norms*100
        - [PI (CMR)] - PI bucket P0-P8 by CMR slab
        - [PI (T-Wise)] - PI bucket P0-P8 by T-Wise slab

        # vw_JOB_COST columns:
        - [Plant/ Location] - 'MML' or 'NIM'
        - [Project] = Revenue.rigcode
        - [Well ID] - well identifier
        - [Activity ID] = LEFT(task_code, 8)
        - [Activity Code] - from ActivityMasterMapping
        - [Plan Employee Name/ Equipment Name], [Actual Employee / Equipment Name]
        - [Plan PG / EG Code], [Actual PG/EG Code]
        - [Effective Work Hours]

        # Daily_Plan_Report columns:
        - [Well ID], [PA Name], [PH Name], [PH Emp ID]
        - [Well Category], [Location], [Job Title / Project Name]
        - [Activities], [Manpower], [Eqpt], [Vehicle]

        # Always wrap columns with spaces in brackets: [Week-1 Plan %]
    28. TABLE ROUTING INTELLIGENCE - CHOOSE THE RIGHT TABLE:
        # WellMonitoringReport / WellMonitoringReport_Latest:
        #   - SINGLE SNAPSHOT: 1 row per well (latest week)
        #   - Use for: current status, progress, location, rig assignments, KPIs, dates, buffer status, construction progress
        #   - Has: cum_progress_for_this_week, last_week_cum_progress (ONLY 2 weeks of data)
        #   - LIMITATION: Can only compare THIS week vs LAST week. CANNOT detect 3+ week stalls.

        # Job_Progress_Report_GB:
        #   - WEEKLY BREAKDOWN: Has Week-1 through Week-5 Plan/Actual per well per project
        #   - Use for: weekly progress trends, plan vs actual by week, multi-week analysis, stall detection
        #   - Has: [Cum-Prior Month Actual %], [Week-1 Plan %], [Week-1 Actual %], ..., [Week-5 Plan %], [Week-5 Actual %]
        #   - Has: [Current Month Plan %], [Current Month Actual %], [Cum-Current Month Plan %], [Cum-Current Month Actual %]
        #   - Has: [Purpose Value] (monetary), [Target End] (date), [PO No], [WBS No], [Category]
        #   - STALL DETECTION: If [Week-1 Actual %] = 0 AND [Week-2 Actual %] = 0 AND [Week-3 Actual %] = 0 → stuck for 3+ weeks

        # PH_Productivity:
        #   - CREW PERFORMANCE: Daily productivity per PH/PA/Crew
        #   - Use for: productivity ranking, crew efficiency, PI index analysis

        # vw_JOB_COST:
        #   - RESOURCE COST TRACKING: Planned vs actual employees/equipment per task per day
        #   - Use for: job costing, resource utilization, manpower analysis

        # vw_JobProgress:
        #   - SIMILAR to Job_Progress_Report_GB but from a different source table (ActivityTaskPlan)
        #   - Use for: alternative weekly breakdown, Feb-only data

        # Daily_Plan_Report:
        #   - TODAY'S PLAN ONLY: No historical data
        #   - Use for: current day work plan, crew assignments
    29. STALL/STUCK WELL DETECTION: To find wells stuck at same progress:
        - For 1-week stall: Use WellMonitoringReport WHERE cum_progress_for_this_week = last_week_cum_progress
        - For multi-week stall: Use Job_Progress_Report_GB WHERE [Week-1 Actual %] = 0 AND [Week-2 Actual %] = 0 AND [Week-3 Actual %] = 0
        - NEVER use [last_week_exp.rig_on_location_sap_data] for stall detection - those are SAP scheduling dates!
    30. PROGRESS COLUMN SEMANTICS:
        - WellMonitoringReport.cum_progress_for_this_week = location preparation progress (0-1 decimal)
        - WellMonitoringReport.over_all_progress_percentages = overall well progress (0-1, multiply by 100 for %)
        - Job_Progress_Report_GB.[Week-N Actual %] = weekly actual progress as percentage (already 0-100)
        - Job_Progress_Report_GB.[Current Month Actual %] = total month actual (already 0-100)
    31. COST AND PRODUCTIVITY QUERIES:
        - For job costing: Use vw_JOB_COST
        - For crew productivity: Use PH_Productivity
        - For daily work plan: Use Daily_Plan_Report
        - NEVER use WellMonitoringReport for cost or productivity questions
    32. WEEKLY TREND QUERIES: When user asks about "weekly trends", "week-by-week", or "Week 1 vs Week 2":
        - ALWAYS use Job_Progress_Report_GB with column names [Week-1 Plan %], [Week-1 Actual %], etc.
        - Join with WellMonitoringReport for well names: ON w.pdo_well_id = j.[Well ID]
    33. CATEGORY/PROJECT TYPE QUERIES: The [Category] column in Job_Progress_Report_GB comes from ProjectIDs.column2.
        - Values include: 'Nimr Location', 'Marmul Location', 'Nimr Flowline', 'Marmul Flowline', etc.
        - For filtering by category type, use LIKE: WHERE [Category] LIKE '%Location%' or LIKE '%Flowline%'
    34. "DONE" STATUS (DOUBLE-CHECK): A phase is considered DONE if its Milestone Date is NOT NULL OR its respective overall progress is >= 100.
        - Engineering: [actual_eng._completion_date] IS NOT NULL OR [overall_engg._10_100] >= 100.
        - Construction: [const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date] IS NOT NULL OR [overall_const._10_100] >= 100.
        - Commissioning: [actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date] IS NOT NULL OR [overall_comm_progress_100] >= 100.
        - Ratio Calculation: For ratios of "Done" items, use COUNT(DISTINCT CASE WHEN [Double-Check Logic] THEN pdo_well_id END).
    35. CTE NAMING & BRACKETS: When using Common Table Expressions (WITH clause):
        - Define every alias clearly: WITH CTE_NAME AS (...)
        - If using multiple CTEs: WITH CTE1 AS (...), CTE2 AS (...)
        - NEVER name a CTE the same as an existing table.
    36. CRITICAL RISK DEFINITION: When user asks about "CRITICAL risk wells":
        - Use buffer_status = 'ROL' (actively drilling = highest risk)
        - Do NOT use MOC columns (not related to risk tier)
        - Filter: buffer_status = 'ROL' AND (ohl_progress = 0 OR ohl_progress IS NULL)
        - If user specifically mentions MOC, then use: moc_raised IN ('YES') AND moc_approved NOT IN ('YES')
    37. EXECUTIVE PORTFOLIO STATUS: For questions like "What is our overall project portfolio status today/current/latest?":
        - Use WellMonitoringReport, not WellMonitoringReport_Latest.
        - First derive the latest portfolio snapshot with MAX(Week_Number).
        - Count wells with COUNT(DISTINCT pdo_well_id), never project_id.
        - Return executive KPI fields only: snapshot_date, total_wells, avg_progress_pct, complete_wells, not_started_wells, active_wells, overdue_rig_off_no_actual.
        - Do NOT add engineering/construction/material aggregates unless the user explicitly asks for phase-level status.
    38. SAFETY DATA LIMITATION:
        - Do NOT infer safety risk from PH productivity, reason_if_kpi_not_met, or generic text fields unless the user explicitly asks for a proxy.
        - If the user asks for cost/schedule/safety risk together and no direct safety incident/hazard table is present in the schema context, return safety_risk as NULL plus a safety_note explaining that direct safety data is unavailable.
    39. PROFIT MARGIN / PROJECT AMBIGUITY:
        - If the user says "project" without further qualification, default project grain to Job_Progress_Report_GB.[Category]. Category values include Nimr Location, Nimr Flowline, Marmul Location, and Marmul Flowline.
        - If the user has already clarified project grain as rig code, use Revenue.rigcode.
        - If the user has already clarified project grain as category, aggregate through Job_Progress_Report_GB.[Category] joined via WellMonitoringReport.pdo_well_id = Job_Progress_Report_GB.[Well ID].
        - If the user has already clarified project grain as individual project name, aggregate at well/project-name grain using WellMonitoringReport.well_name_after_spud.
        - True profit margin requires confirmed cost data. If the resolved user request says to use planned vs actual purpose value as a proxy, return revenue variance / achievement-rate SQL instead of inventing a cost table.
        - Never claim planned_purpose_value is a true cost field unless the user explicitly accepts it as a proxy.
    40. FORECASTED REVENUE / CURRENT QUARTER:
        - Do NOT treat "forecasted revenue" as simply SUM(planned_purpose_value) from the latest snapshot.
        - For SQL-only questions like "What is the forecasted revenue for this quarter?", default to a run-rate projection using Revenue.actual_purpose_value quarter-to-date, projected to quarter end from Revenue.created_at.
        - For the same query, compare the projected full-quarter actual against full-quarter planned revenue using SUM(TRY_CAST(planned_purpose_value AS DECIMAL(18,2))) across the full quarter window.
        - Use the full current quarter date range, not only rows where created_at = MAX(created_at).
        - Label the metric as a projection/forecast proxy, not a booked actual.
    41. ANNUAL TARGET STATUS:
        - For questions like "Are we on track to meet annual targets?", default to annual revenue targets from Revenue for the current year.
        - Use current-year actual revenue year-to-date from Revenue.actual_purpose_value.
        - Use current-year planned revenue year-to-date and full-year planned revenue from Revenue.planned_purpose_value cast to DECIMAL(18,2).
        - Determine "on track" using a run-rate projection to year end, not just SUM(actual) / SUM(planned) over all rows.
        - Return: year_start, year_end, as_of_date, actual_revenue_ytd, planned_revenue_ytd, planned_revenue_full_year, projected_full_year_actual, ytd_achievement_pct, projected_achievement_pct, annual_target_status.
    42. OVERDUE MILESTONES / THIS WEEK:
        - "Which milestones are overdue this week?" is ambiguous by default and should be clarified before SQL unless the user explicitly chooses ActivityTaskPlan schedule milestones/tasks or WellMonitoringReport high-level rig milestones.
        - If the user chooses ActivityTaskPlan schedule milestones/tasks, use ActivityTaskPlan.target_end, ActivityTaskPlan.actual_end, ActivityTaskPlan.text, ActivityTaskPlan.progress, and ActivityTaskPlan.Well_ID.
        - For overdue-this-week schedule milestones, filter target_end to the current Monday-Sunday week window, require target_end < today, and require actual_end IS NULL or actual_end > target_end.
        - Do NOT collapse this question to a single WellMonitoringReport field like [last_week_exp.rig_on_location_sap_data] unless the user explicitly asks for rig-on-location milestones only.
    43. CRITICAL PATH / ACTIVITIES:
        - "Which activities are on the critical path?" is ambiguous by default because the current schema has no explicit critical_path flag or predecessor/successor table.
        - Do NOT claim a true CPM critical path from ActivityTaskPlan.ancestor / parent alone.
        - If the user explicitly accepts a SQL proxy, use ActivityTaskPlan open activities with target_end, actual_end, remaining_duration, progress, text, ancestor, and parent.
        - For the proxy, rank incomplete activities by overdue target_end first, then remaining_duration descending, then lowest progress.
        - Label the result as critical-path proxy / currently critical open activities, not a true critical path.
    44. COST / BUDGET QUESTIONS:
        - The current schema does not expose a confirmed enterprise cost/budget fact table. Revenue.planned_purpose_value vs Revenue.actual_purpose_value may only be used as a proxy if the user explicitly accepts that proxy.
        - For "cost vs budget" or "cost overrun" questions, aggregate Revenue by the requested grain before ranking or calculating variance. Never rank raw Revenue rows directly.
        - Exclude or separately flag cases where aggregated planned_value = 0; do not silently treat zero-plan rows as valid budget overruns.
        - If the user asks "why", use only the latest WellMonitoringReport operational context as a proxy explanation and label it as operational context, not a validated cost-cause.
    45. MAJOR CONSTRAINTS AFFECTING PROGRESS:
        - Do not default to WellMonitoringReport.reasons_for_year_2018 for current operational constraints.
        - If the latest snapshot has no populated issue-text fields, answer from measurable bottlenecks using latest-snapshot phase progress fields such as overall_const._10_100, overall_engg._10_100, flowline_construction_progress, overall_ohl_progr_100, and overall_material_10_100.
        - Rank major constraints by highest share of lagging wells and lowest average progress.
    46. LABOR PRODUCTIVITY AND CREW EFFICIENCY:
        - For labor productivity trend and crew efficiency questions, use PH_PRODUCTIVITY_WEEKLY_REPORT.
        - Filter [Average Productivity (%)] to a defensible range such as 0 to 200 before ranking or trending, because the raw table contains extreme outliers and negatives.
        - For "most efficient crews", default to the latest reporting month with valid productivity and include observation counts.
    47. WORKFORCE ALLOCATION / MANPOWER PROXIES:
        - The current schema does not expose a clean live headcount-allocation fact by project.
        - For workforce allocation questions, use ActivityTaskPlan manhoursactual and manhourforacst on incomplete tasks, grouped through ProjectIDs.column2 as a manhours-allocation proxy.
        - Label the result as actual/forecast manhours allocation, not audited deployed headcount.
    48. SKILLS SHORTAGE PROXY:
        - The current schema has no normalized skill-demand vs skill-supply model.
        - Only if the user explicitly accepts a proxy, rank ActivityTaskPlan.crew_type on incomplete tasks by forecast manhours (manhourforacst) and open-task volume.
        - Label the output as a crew-type demand proxy, not a validated skill shortage.
    49. SUBCONTRACTOR MANPOWER STATUS PROXY:
        - The current schema has PH_PRODUCTIVITY_WEEKLY_REPORT.[ATNM/Sub Contractor], crew names, crew types, and productivity, but no direct subcontractor manpower headcount.
        - Only if the user explicitly accepts a proxy, summarize the latest valid month by [ATNM/Sub Contractor] using distinct crew-group counts, crew-discipline counts, and average productivity.
    50. PROCUREMENT / VENDOR DATA LIMITATION:
        - Do not invent overtime cost, absenteeism, inventory, shipment, expediting, vendor rating, vendor quality, or overdue PO metrics if the schema context does not contain the required fact fields.
        - If direct promised-date, inventory-balance, shipment-tracking, or vendor-quality facts are absent or unpopulated, return INSUFFICIENT_SCHEMA or ask for a proxy instead of hallucinating.
    51. PERFORMANCE KPI TREND ANALYSIS:
        - For "trend analysis of performance KPIs", use WMR_Full rather than the latest-only WellMonitoringReport snapshot.
        - Default to weekly portfolio trends for overall progress, engineering, construction, material, flowline, OHL, and commissioning over the latest 12 weekly snapshots.
        - Return one row per snapshot date with KPI percentages.
    52. KPI THRESHOLD DEVIATIONS:
        - The current schema does not contain a formal KPI-threshold registry.
        - Only if the user explicitly accepts a proxy, use the latest WellMonitoringReport snapshot and flag major phase KPIs below 50% progress as threshold deviations.
        - Summarize deviations by KPI name with average value, violating wells, and violating-well percentage.
    53. DELIVERY-RISK PROXY:
        - The current schema does not contain a formal enterprise risk register.
        - Only if the user explicitly accepts an operational delivery-risk proxy, use the latest WellMonitoringReport snapshot plus Job_Progress_Report_GB category mapping.
        - Rank project categories by aggregated delivery-risk score using overdue rig-off, low overall progress, and low engineering/construction/material/flowline/OHL progress signals.
    """

    neo4j_schema_context = dspy.InputField(
        desc="The ONLY available tables and columns. Do NOT use any table/column not listed here."
    )
    user_question = dspy.InputField(
        desc="The user's natural language question."
    )
    query_type = dspy.InputField(
        desc="Query classification: single_table, multi_table_join, aggregation, trend, ranking, comparison"
    )

    sql_query = dspy.OutputField(
        desc="Exact MS SQL Server SELECT query using ONLY columns from neo4j_schema_context. "
             "If required columns are missing, output exactly 'INSUFFICIENT_SCHEMA'. "
             "DO NOT wrap in markdown. First word must be SELECT or WITH."
    )
    confidence = dspy.OutputField(
        desc="Float between 0.0 and 1.0 indicating confidence that the query is correct. "
             "0.9+ if all columns are clearly in schema. 0.5-0.8 if inferred. Below 0.5 if uncertain."
    )


# ── Training Examples ────────────────────────────────────────────────────

TRAINING_EXAMPLES = [
    dspy.Example(
        user_question="Which Nimr wells are below 50% progress?",
        query_type="single_table",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'well_name_after_spud' (nvarchar): The official name of the well after spudding.
  - Column 'over_all_progress_percentages' (float): Total completion decimal (0.0 to 1.0).
  - Column 'Cluster' (nvarchar): The operational cluster the well belongs to.""",
        sql_query="SELECT well_name_after_spud, (over_all_progress_percentages * 100) AS progress_pct FROM WellMonitoringReport WHERE Cluster = 'Nimr' AND over_all_progress_percentages < 0.50 ORDER BY over_all_progress_percentages;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Example: Average progress for cluster - NO date filter needed!
    dspy.Example(
        user_question="What is the average overall progress for all Nimr wells this week?",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'over_all_progress_percentages' (decimal): Overall completion (0-1 decimal scale). Multiply by 100 for percentage.
  - Column 'Cluster' (nvarchar): Operational cluster - use 'Nimr' or 'Marmul'.
  - Column 'Week_Number' (date): Week date - DO NOT filter by this unless user specifies exact week date!""",
        sql_query="SELECT AVG(over_all_progress_percentages) * 100 AS average_overall_progress FROM WellMonitoringReport WHERE Cluster = 'Nimr';",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Example: Wells in NL0010 with actual > planned - CORRECT JOIN
    dspy.Example(
        user_question="list me wells in NL0010 which has actual progress more than planned progress",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: Revenue
  - Column 'rigcode' (nvarchar): The RIG identifier (NL0010, NF0010). Use for filtering by rig.
  - Column 'well_id' (nvarchar): The well identifier - join with WellMonitoringReport.pdo_well_id.
  - Column 'acutal_progress' (decimal): Actual progress achieved (note: misspelled as 'acutal').
  - Column 'planned_progress' (nvarchar): Planned progress - MUST CAST to DECIMAL before comparison!

TABLE: WellMonitoringReport
  - Column 'pdo_well_id' (nvarchar): The unique PDO well identifier - join with Revenue.Well_ID.
  - Column 'well_name_after_spud' (nvarchar): The official well name.""",
        sql_query="SELECT w.pdo_well_id, w.well_name_after_spud, r.acutal_progress, TRY_CAST(r.planned_progress AS DECIMAL(10,2)) AS planned_progress FROM Revenue r INNER JOIN WellMonitoringReport w ON w.pdo_well_id = r.Well_ID WHERE r.rigcode = 'NL0010' AND r.acutal_progress > TRY_CAST(r.planned_progress AS DECIMAL(10,2));",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Example: Wells that overperformed - use Revenue table with rigcode filter
    dspy.Example(
        user_question="show me which well has over performed than the plan in month of Feb 2026 in rig code NL0010 and NF0010",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: Revenue
  - Column 'rigcode' (nvarchar): The RIG identifier (NL0010, NF0010, ML0010 etc). Use for filtering by rig.
  - Column 'well_id' (nvarchar): The well identifier - join with WellMonitoringReport.pdo_well_id.
  - Column 'acutal_progress' (decimal): Actual progress achieved (note: misspelled as 'acutal').
  - Column 'planned_progress' (nvarchar): Planned progress - MUST CAST to DECIMAL before comparison!
  - Column 'created_at' (datetime2): Record creation date - filter by month using this.""",
        sql_query="SELECT r.rigcode, r.well_id, r.acutal_progress, TRY_CAST(r.planned_progress AS DECIMAL(10,2)) AS planned_progress FROM Revenue r WHERE r.rigcode IN ('NL0010', 'NF0010') AND r.created_at >= '2026-02-01' AND r.created_at < '2026-03-01' AND r.acutal_progress > TRY_CAST(r.planned_progress AS DECIMAL(10,2));",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Example: MOC approved wells
    dspy.Example(
        user_question="Which wells have MOC approved?",
        query_type="single_table",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'pdo_well_id' (nvarchar): The unique PDO well identifier.
  - Column 'well_name_after_spud' (nvarchar): The official name of the well.
  - Column 'moc_raised' (nvarchar): MOC raised status - values: 'YES', 'Yes', 'yes'.
  - Column 'moc_approved' (nvarchar): MOC approved status - values: 'YES', 'Yes', 'yes'.""",
        sql_query="SELECT pdo_well_id, well_name_after_spud, moc_raised, moc_approved FROM WellMonitoringReport WHERE moc_approved IN ('YES', 'Yes', 'yes');",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Example: MOC raised but not approved
    # MOC Status (only use when user specifically asks about MOC)
    dspy.Example(
        user_question="Which wells have a MOC raised but not yet approved?",
        query_type="single_table",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'pdo_well_id' (nvarchar): The unique PDO well identifier.
  - Column 'well_name_after_spud' (nvarchar): The official name of the well.
  - Column 'moc_raised' (nvarchar): MOC raised status - values: 'YES', 'Yes', 'yes'.
  - Column 'moc_approved' (nvarchar): MOC approved status - values: 'YES', 'Yes', 'yes'. Filter for NOT approved.
  NOTE: Only use this query when user explicitly mentions "MOC" or "Management of Change".""",
        sql_query="SELECT pdo_well_id, well_name_after_spud, moc_raised, moc_approved FROM WellMonitoringReport WHERE moc_raised IN ('YES', 'Yes', 'yes') AND moc_approved NOT IN ('YES', 'Yes', 'yes');",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="What is the actual revenue earned per rig for the current month?",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: Job_Progress_Report_GB
  - Column 'Revenue Current Month Actual' (float): Actual revenue earned this month.
  - Column 'Well ID' (nvarchar): The PDO well ID.

TABLE: WellMonitoringReport
  - Column 'rig_no' (nvarchar): The identifier for the rig.
  - Column 'pdo_well_id' (int): The PDO well ID.

JOIN RELATIONSHIPS:
  - Job_Progress_Report_GB.[Well ID] JOINS_ON WellMonitoringReport.pdo_well_id""",
        sql_query="SELECT w.rig_no, SUM(j.[Revenue Current Month Actual]) AS actual_revenue FROM Job_Progress_Report_GB j JOIN WellMonitoringReport w ON j.[Well ID] = CAST(w.pdo_well_id AS VARCHAR) GROUP BY w.rig_no ORDER BY actual_revenue DESC;",
        confidence="0.90",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="Show me the weekly progress trend for well RKDS_2026_OP_LOC3.",
        query_type="trend",
        neo4j_schema_context="""TABLE: Job_Progress_Report_GB
  - Column 'Well Name / Project Name' (nvarchar): The name of the well or project.
  - Column 'Week-1 Actual %' (float): Actual progress percentage for week 1.
  - Column 'Week-2 Actual %' (float): Actual progress percentage for week 2.
  - Column 'Week-3 Actual %' (float): Actual progress percentage for week 3.""",
        sql_query="SELECT [Well Name / Project Name], [Week-1 Actual %], [Week-2 Actual %], [Week-3 Actual %] FROM Job_Progress_Report_GB WHERE [Well Name / Project Name] = 'RKDS_2026_OP_LOC3';",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="Rank all project holders by average productivity.",
        query_type="ranking",
        neo4j_schema_context="""TABLE: PH_PRODUCTIVITY_WEEKLY_REPORT
  - Column 'PH Name' (nvarchar): The name of the project holder.
  - Column 'Average Productivity (%)' (float): The average productivity percentage.""",
        sql_query="SELECT [PH Name], [Average Productivity (%)] FROM PH_PRODUCTIVITY_WEEKLY_REPORT ORDER BY [Average Productivity (%)] DESC;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Example showing proper type casting for numeric comparisons
    dspy.Example(
        user_question="How many wells have an Engg KPI after Rig-Off of more than 2 days?",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'well_name_after_spud' (nvarchar): The official name of the well.
  - Column 'engg_kpi_after_rig_off_days' (float): Days taken for engineering completion after rig moved off.
  - Column 'Cluster' (nvarchar): The operational cluster.""",
        sql_query="SELECT [Cluster], COUNT(*) AS well_count FROM WellMonitoringReport WHERE TRY_CAST([engg_kpi_after_rig_off_days] AS FLOAT) > 2 GROUP BY [Cluster];",
        confidence="0.90",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Example for counting wells - ALWAYS use pdo_well_id for unique count
    dspy.Example(
        user_question="How many wells are in each cluster?",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: WellMonitoringReport_Latest
  - Column 'pdo_well_id' (int): The PDO unique well ID - USE THIS for counting wells.
  - Column 'well_name_after_spud' (nvarchar): The official name of the well - use for display only.
  - Column 'Cluster' (nvarchar): The operational cluster.""",
        sql_query="SELECT [Cluster], COUNT(DISTINCT [pdo_well_id]) AS well_count FROM WellMonitoringReport_Latest GROUP BY [Cluster] ORDER BY well_count DESC;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Example for counting wells with filter
    dspy.Example(
        user_question="How many wells have an Engg KPI after Rig-Off of more than 2 days?",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: WellMonitoringReport_Latest
  - Column 'pdo_well_id' (int): The PDO unique well ID - USE THIS for counting wells.
  - Column 'well_name_after_spud' (nvarchar): The official name of the well.
  - Column 'engg_kpi_after_rig_off_days' (float): Days taken for engineering after rig off.""",
        sql_query="SELECT COUNT(DISTINCT [pdo_well_id]) AS well_count FROM WellMonitoringReport_Latest WHERE TRY_CAST([engg_kpi_after_rig_off_days] AS FLOAT) > 2;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Example for "show me all wells" - return MULTIPLE useful columns, not just name
    dspy.Example(
        user_question="Show me all wells in Nimr cluster with rig SWER102 where location preparation progress is 1",
        query_type="single_table",
        neo4j_schema_context="""TABLE: WellMonitoringReport_Latest
  - Column 'pdo_well_id' (int): The PDO unique well ID.
  - Column 'well_name_after_spud' (nvarchar): The official name of the well.
  - Column 'rig_no' (nvarchar): The rig identifier.
  - Column 'Cluster' (nvarchar): The operational cluster.
  - Column 'overall_loc_preparation_10_100' (float): Location preparation progress (0-100 scale).""",
        sql_query="SELECT [pdo_well_id] AS Well_ID, [well_name_after_spud] AS Well_Name, [rig_no] AS Rig, [Cluster] AS Cluster, [overall_loc_preparation_10_100] AS Loc_Prep_Pct FROM WellMonitoringReport_Latest WHERE [Cluster] = 'Nimr' AND [rig_no] = 'SWER102' AND [overall_loc_preparation_10_100] = 1;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Example for rig-based ranking queries - CRITICAL: use WellMonitoringReport_Latest with rig_no
    dspy.Example(
        user_question="Which rig has the highest average well progress in Nimr?",
        query_type="ranking",
        neo4j_schema_context="""TABLE: WellMonitoringReport_Latest
  - Column 'rig_no' (nvarchar): The rig identifier (e.g., SWER102, SWER103).
  - Column 'Cluster' (nvarchar): The operational cluster (Nimr or Marmul).
  - Column 'over_all_progress_percentages' (float): Overall well progress (0-1 scale, multiply by 100 for percentage).
  - Column 'pdo_well_id' (int): The unique well identifier.""",
        sql_query="SELECT rig_no, AVG(TRY_CAST(over_all_progress_percentages AS FLOAT)) * 100 AS avg_progress_pct, COUNT(DISTINCT pdo_well_id) AS well_count FROM WellMonitoringReport_Latest WHERE Cluster = 'Nimr' GROUP BY rig_no ORDER BY avg_progress_pct DESC;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Example for joining with Job_Progress_Report_GB - ALWAYS use WellMonitoringReport_Latest
    dspy.Example(
        user_question="Which wells overachieved their Week 1 plan by more than 10 percentage points?",
        query_type="comparison",
        neo4j_schema_context="""TABLE: WellMonitoringReport_Latest
  - Column 'well_name_after_spud' (nvarchar): The official name of the well.
  - Column 'pdo_well_id' (int): The PDO well ID.

TABLE: Job_Progress_Report_GB
  - Column 'Well_ID' (smallint): The PDO well ID (join key).
  - Column 'Week_1_Actual' (float): Actual progress percentage.
  - Column 'Week_1_Plan' (float): Planned progress percentage.""",
        sql_query="SELECT WM.[well_name_after_spud] AS Well_Name, JPR.[Week_1_Actual], JPR.[Week_1_Plan], JPR.[Week_1_Actual] - JPR.[Week_1_Plan] AS Variance FROM WellMonitoringReport_Latest WM JOIN Job_Progress_Report_GB JPR ON WM.[pdo_well_id] = JPR.[Well_ID] WHERE (JPR.[Week_1_Actual] - JPR.[Week_1_Plan]) > 10;",
        confidence="0.90",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # New: SCR-specific example to teach the model about SCR columns
    dspy.Example(
        user_question="Which wells have a SCR number recorded and what is their current progress?",
        query_type="single_table",
        neo4j_schema_context="""TABLE: WellMonitoringReport_Latest
  - Column 'well_name_after_spud' (nvarchar): The official name of the well after spudding.
  - Column 'scr_no' (nvarchar): The Site Change Request / Survey Completion Report number.
  - Column 'over_all_progress_percentages' (float): Total completion decimal.
  - Column 'cum_progress_for_this_week' (float): Cumulative progress for the current week.""",
        sql_query="SELECT well_name_after_spud, scr_no, (over_all_progress_percentages * 100) AS progress_pct FROM WellMonitoringReport_Latest WHERE scr_no IS NOT NULL ORDER BY progress_pct DESC;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="Which wells have no PO number recorded in the Job Progress report?",
        query_type="single_table",
        neo4j_schema_context="""TABLE: Job_Progress_Report_GB
  - Column [Well Name / Project Name] (nvarchar): The human-readable name of the well or project.
  - Column [PO No] (nvarchar): The Purchase Order number associated with this well.
  - Column [Well ID] (nvarchar): Unique identifier for the well.""",
        sql_query="SELECT [Well Name / Project Name], [Well ID] FROM Job_Progress_Report_GB WHERE [PO No] IS NULL;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # CRITICAL: For tie-in port readiness queries, use actual_rig_on_date NOT actual_start_date
    dspy.Example(
        user_question="Which wells across Nimr and Marmul have not achieved tie-in port readiness within the 140-day target ahead of spud?",
        query_type="single_table",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'Cluster' (nvarchar): Operational cluster - 'Nimr' or 'Marmul'.
  - Column 'rig_no' (nvarchar): The drilling rig identifier (e.g., NL0010, NF0010).
  - Column 'well_location' (nvarchar): Geographic location code - NOT for rig codes!
  - Column 'well_name_after_spud' (nvarchar): Official well name after drilling begins.
  - Column 'pdo_well_id' (nvarchar): Unique PDO well identifier.
  - Column 'date_of_tie_in_port_readiness' (date): Date tie-in port became ready.
  - Column 'actual_rig_on_date' (date): Date rig arrived at well location - USE THIS for spud-related queries, NOT actual_start_date.
  - Column 'actual_start_date' (date): Actual work start date - different from rig on date.""",
        sql_query="SELECT Cluster, rig_no, well_location, well_name_after_spud, pdo_well_id, date_of_tie_in_port_readiness, actual_rig_on_date, DATEDIFF(DAY, date_of_tie_in_port_readiness, actual_rig_on_date) AS tie_in_port_readiness_days FROM WellMonitoringReport WHERE Cluster IN ('Nimr', 'Marmul') AND date_of_tie_in_port_readiness IS NOT NULL AND actual_rig_on_date IS NOT NULL AND DATEDIFF(DAY, date_of_tie_in_port_readiness, actual_rig_on_date) > 140 ORDER BY Cluster, rig_no, well_location, pdo_well_id;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # VMB Logic: Location Pegged to SPUD - Target 140 days
    dspy.Example(
        user_question="Which wells have Location Pegged to Spud target below 140 days (red status)?",
        query_type="single_table",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'well_name_after_spud' (nvarchar): Official well name.
  - Column 'rig_no' (nvarchar): The drilling rig identifier.
  - Column 'actual_rig_on_date' (date): Date rig arrived (Spud date).
  - Column 'location_pegged_date' (date): Date location was pegged.""",
        sql_query="SELECT well_name_after_spud, rig_no, location_pegged_date, actual_rig_on_date, DATEDIFF(DAY, location_pegged_date, actual_rig_on_date) AS days_from_pegged_to_spud FROM WellMonitoringReport WHERE location_pegged_date IS NOT NULL AND actual_rig_on_date IS NOT NULL AND DATEDIFF(DAY, location_pegged_date, actual_rig_on_date) < 140;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # VMB Logic: Stable Rig Sequence - Target 90 days (SCR Date to Rig On)
    dspy.Example(
        user_question="Which wells have Stable Rig Sequence below 90 days (below target)?",
        query_type="single_table",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'well_name_after_spud' (nvarchar): Official well name.
  - Column 'rig_no' (nvarchar): The drilling rig identifier.
  - Column 'actual_rig_on_date' (date): Date rig arrived at well.
  - Column 'scr_date' (date): Site Change Request date.""",
        sql_query="SELECT well_name_after_spud, rig_no, scr_date, actual_rig_on_date, DATEDIFF(DAY, scr_date, actual_rig_on_date) AS stable_rig_sequence_days FROM WellMonitoringReport WHERE scr_date IS NOT NULL AND actual_rig_on_date IS NOT NULL AND DATEDIFF(DAY, scr_date, actual_rig_on_date) < 90;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # VMB Logic: FLAF issued to Spud - Target 90 days
    dspy.Example(
        user_question="Show wells where FLAF to Spud is below 90 days target",
        query_type="single_table",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'well_name_after_spud' (nvarchar): Official well name.
  - Column 'rig_no' (nvarchar): The drilling rig identifier.
  - Column 'actual_rig_on_date' (date): Date rig arrived (Spud).
  - Column 'flaf_issue_date' (date): Date FLAF was issued.""",
        sql_query="SELECT well_name_after_spud, rig_no, flaf_issue_date, actual_rig_on_date, DATEDIFF(DAY, flaf_issue_date, actual_rig_on_date) AS flaf_to_spud_days FROM WellMonitoringReport WHERE flaf_issue_date IS NOT NULL AND actual_rig_on_date IS NOT NULL AND DATEDIFF(DAY, flaf_issue_date, actual_rig_on_date) < 90;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # VMB Logic: Survey Report within 15 days from FLAF (green = below 15)
    dspy.Example(
        user_question="Show wells where Survey Report took more than 15 days from FLAF (red status)",
        query_type="single_table",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'well_name_after_spud' (nvarchar): Official well name.
  - Column 'flaf_issue_date' (date): Date FLAF was issued.
  - Column 'date_of_site_survey_report_issuance' (date): Date site survey report was issued.""",
        sql_query="SELECT well_name_after_spud, flaf_issue_date, date_of_site_survey_report_issuance, DATEDIFF(DAY, flaf_issue_date, date_of_site_survey_report_issuance) AS survey_report_days FROM WellMonitoringReport WHERE flaf_issue_date IS NOT NULL AND date_of_site_survey_report_issuance IS NOT NULL AND DATEDIFF(DAY, flaf_issue_date, date_of_site_survey_report_issuance) > 15;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # VMB Logic: Overall Commissioning Duration after Rig Off - Target 5 days (with Rig/FBU/RSR) or 15 days (with Hoist)
    dspy.Example(
        user_question="Show wells where commissioning duration after rig off exceeded target (more than 5 days for Rig/FBU/RSR or 15 days for Hoist)",
        query_type="single_table",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'well_name_after_spud' (nvarchar): Official well name.
  - Column 'rig_no' (nvarchar): The drilling rig identifier.
  - Column 'actual_rig_off_date' (date): Date rig departed.
  - Column 'actual_comm_finish_date_with_in_2_days_from_actual_engg_completion_date' (date): Commissioning finish date.""",
        sql_query="SELECT well_name_after_spud, rig_no, actual_rig_off_date, actual_comm_finish_date_with_in_2_days_from_actual_engg_completion_date, DATEDIFF(DAY, actual_rig_off_date, actual_comm_finish_date_with_in_2_days_from_actual_engg_completion_date) AS commissioning_duration_days FROM WellMonitoringReport WHERE actual_rig_off_date IS NOT NULL AND actual_comm_finish_date_with_in_2_days_from_actual_engg_completion_date IS NOT NULL;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # VMB Logic: Flowline Completion - Target 50% at 45 days before Rig On
    dspy.Example(
        user_question="Which wells are below 50% flowline completion with fewer than 45 days to the rig-on date?",
        query_type="single_table",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'pdo_well_id' (nvarchar): Unique well ID.
  - Column 'well_name_after_spud' (nvarchar): Official well name.
  - Column 'flowline_construction_progress' (decimal): Flowline completion - 0-1 SCALE (0.5 = 50%, NOT 50!).
  - Column 'actual_rig_on_date' (date): Date rig arrives (Spud date).""",
        sql_query="SELECT pdo_well_id, well_name_after_spud, flowline_construction_progress, actual_rig_on_date, DATEDIFF(DAY, GETDATE(), actual_rig_on_date) AS days_until_rig_on FROM WellMonitoringReport WHERE TRY_CAST(flowline_construction_progress AS FLOAT) < 0.50 AND DATEDIFF(DAY, GETDATE(), actual_rig_on_date) < 45 AND actual_rig_on_date IS NOT NULL AND flowline_construction_progress IS NOT NULL;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # ========== REVENUE ACHIEVEMENT RATE EXAMPLES ==========

    # Example: Calculate achievement rate - MUST cast nvarchar to DECIMAL before SUM
    dspy.Example(
        user_question="What is the revenue achievement rate (actual / planned) by rigcode?",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: Revenue
  - Column 'rigcode' (nvarchar): The rig identifier.
  - Column 'actual_purpose_value' (decimal): Actual revenue achieved.
  - Column 'planned_purpose_value' (nvarchar): Planned revenue - MUST CAST TO DECIMAL before SUM!""",
        sql_query="SELECT rigcode, SUM(actual_purpose_value) AS total_actual, SUM(TRY_CAST(planned_purpose_value AS DECIMAL(18,2))) AS total_planned, CASE WHEN SUM(TRY_CAST(planned_purpose_value AS DECIMAL(18,2))) = 0 THEN NULL ELSE SUM(actual_purpose_value) / SUM(TRY_CAST(planned_purpose_value AS DECIMAL(18,2))) END AS achievement_rate FROM Revenue GROUP BY rigcode;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Example: Achievement rate with percentage
    dspy.Example(
        user_question="Show achievement percentage by well for planned vs actual",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: Revenue
  - Column 'well_id' (nvarchar): The unique well identifier.
  - Column 'actual_purpose_value' (decimal): Actual purpose value achieved.
  - Column 'planned_purpose_value' (nvarchar): Planned purpose value - MUST CAST TO DECIMAL!""",
        sql_query="SELECT well_id, SUM(actual_purpose_value) AS actual, SUM(TRY_CAST(planned_purpose_value AS DECIMAL(18,2))) AS planned, CASE WHEN SUM(TRY_CAST(planned_purpose_value AS DECIMAL(18,2))) = 0 THEN 0 ELSE (SUM(actual_purpose_value) / SUM(TRY_CAST(planned_purpose_value AS DECIMAL(18,2)))) * 100 END AS achievement_pct FROM Revenue GROUP BY well_id;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Example: Revenue by rig with type casting
    dspy.Example(
        user_question="Show total revenue by rigcode",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: Revenue
  - Column 'rigcode' (nvarchar): The rig identifier.
  - Column 'actual_purpose_value' (decimal): Actual revenue.
  - Column 'planned_purpose_value' (nvarchar): Planned revenue - MUST CAST!""",
        sql_query="SELECT rigcode, SUM(actual_purpose_value) AS actual_revenue, SUM(TRY_CAST(planned_purpose_value AS DECIMAL(18,2))) AS planned_revenue FROM Revenue GROUP BY rigcode;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Example: Filter by RIGCODE (NOT well_location) - CRITICAL!
    dspy.Example(
        user_question="Show wells in NL0010 which has actual progress more than planned progress",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'pdo_well_id' (int): The unique well identifier (join key).
  - Column 'well_name_after_spud' (nvarchar): The official well name.
  - Column 'well_location' (nvarchar): The well location.

TABLE: Revenue
  - Column 'well_id' (nvarchar): The well identifier (join key).
  - Column 'rigcode' (nvarchar): The rig identifier - use THIS for filtering by rig (NL0010, NF0010, etc). NEVER use well_location for rig names!
  - Column 'acutal_progress' (decimal): Actual progress (note: misspelled as 'acutal').
  - Column 'planned_progress' (nvarchar): Planned progress - CAST to DECIMAL!""",
        sql_query="SELECT w.pdo_well_id, w.well_name_after_spud, w.well_location, r.acutal_progress AS actual_progress, TRY_CAST(r.planned_progress AS DECIMAL(10,2)) AS planned_progress FROM WellMonitoringReport w INNER JOIN Revenue r ON w.pdo_well_id = r.Well_ID WHERE r.rigcode = 'NL0010' AND TRY_CAST(r.acutal_progress AS DECIMAL(10,2)) > TRY_CAST(r.planned_progress AS DECIMAL(10,2));",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Example: Filter Revenue by rigcode (NOT well_location)
    dspy.Example(
        user_question="Show wells in NL0010 which has actual progress more than planned progress",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: Revenue
  - Column 'rigcode' (nvarchar): The rig identifier - use THIS for filtering by rig (NL0010, etc).
  - Column 'well_id' (nvarchar): The unique well identifier.
  - Column 'actual_purpose_value' (decimal): Actual purpose value achieved.
  - Column 'planned_purpose_value' (nvarchar): Planned purpose value - MUST CAST!""",
        sql_query="SELECT well_id, SUM(actual_purpose_value) AS total_actual, SUM(TRY_CAST(planned_purpose_value AS DECIMAL(18,2))) AS total_planned FROM Revenue WHERE rigcode = 'NL0010' GROUP BY well_id HAVING SUM(actual_purpose_value) > SUM(TRY_CAST(planned_purpose_value AS DECIMAL(18,2)));",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Example: Revenue achievement by rig
    dspy.Example(
        user_question="What is the achievement rate by rigcode in Revenue?",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: Revenue
  - Column 'rigcode' (nvarchar): The rig identifier - use for grouping.
  - Column 'actual_purpose_value' (decimal): Actual revenue achieved.
  - Column 'planned_purpose_value' (nvarchar): Planned revenue - MUST CAST to DECIMAL before SUM!""",
        sql_query="SELECT rigcode, SUM(actual_purpose_value) AS actual, SUM(TRY_CAST(planned_purpose_value AS DECIMAL(18,2))) AS planned, CASE WHEN SUM(TRY_CAST(planned_purpose_value AS DECIMAL(18,2))) = 0 THEN NULL ELSE SUM(actual_purpose_value) / SUM(TRY_CAST(planned_purpose_value AS DECIMAL(18,2))) END AS achievement_rate FROM Revenue GROUP BY rigcode;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # ========== COMPLEX JOIN EXAMPLES ==========

    # Join WellMonitoringReport with SAP_DRILLING_SEQUENCE
    dspy.Example(
        user_question="Show me wells from Nimr cluster along with their SAP drilling status",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'pdo_well_id' (int): The unique well ID.
  - Column 'well_name_after_spud' (nvarchar): The official well name.
  - Column 'Cluster' (nvarchar): The operational cluster (Nimr or Marmul).

TABLE: SAP_DRILLING_SEQUENCE
  - Column 'Well_Name' (nvarchar): The well name in SAP system.
  - Column 'Field' (nvarchar): The field name (e.g., NIMR, FAHUD).
  - Column 'Well_Function' (nvarchar): Function type of the well.
  - Column 'Opr_System_status' (nvarchar): Operational status.""",
        sql_query="SELECT w.pdo_well_id, w.well_name_after_spud, w.Cluster, s.Well_Function, s.Opr_System_status FROM WellMonitoringReport w LEFT JOIN SAP_DRILLING_SEQUENCE s ON w.well_name_after_spud = s.Well_Name WHERE w.Cluster = 'Nimr';",
        confidence="0.90",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Join with Revenue table
    dspy.Example(
        user_question="Show revenue per well for all wells with their progress",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'pdo_well_id' (int): The unique well ID.
  - Column 'well_name_after_spud' (nvarchar): The official well name.
  - Column 'over_all_progress_percentages' (float): Overall progress (0-1 scale).

TABLE: Revenue
  - Column 'Well_ID' (int): The well identifier.
  - Column 'Revenue_Current_Month_Actual' (float): Actual revenue this month.
  - Column 'Well_Name' (nvarchar): The well name.""",
        sql_query="SELECT w.pdo_well_id, w.well_name_after_spud, w.over_all_progress_percentages * 100 AS progress_pct, r.Revenue_Current_Month_Actual FROM WellMonitoringReport w LEFT JOIN Revenue r ON w.pdo_well_id = r.Well_ID WHERE r.Revenue_Current_Month_Actual IS NOT NULL ORDER BY r.Revenue_Current_Month_Actual DESC;",
        confidence="0.85",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Join with Job_Progress_Report_GB
    dspy.Example(
        user_question="Show wells with their weekly progress variance",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'pdo_well_id' (int): The unique well ID.
  - Column 'well_name_after_spud' (nvarchar): The official well name.
  - Column 'rig_no' (nvarchar): The rig identifier.

TABLE: Job_Progress_Report_GB
  - Column 'Well_ID' (smallint): The PDO well ID.
  - Column 'Well Name / Project Name' (nvarchar): The well name.
  - Column 'Week_1_Plan' (float): Week 1 planned progress.
  - Column 'Week_1_Actual' (float): Week 1 actual progress.
  - Column 'Week_2_Plan' (float): Week 2 planned progress.
  - Column 'Week_2_Actual' (float): Week 2 actual progress.""",
        sql_query="SELECT w.pdo_well_id, w.well_name_after_spud, w.rig_no, j.[Week_1_Actual] - j.[Week_1_Plan] AS Week1_Variance, j.[Week_2_Actual] - j.[Week_2_Plan] AS Week2_Variance FROM WellMonitoringReport w INNER JOIN Job_Progress_Report_GB j ON w.pdo_well_id = j.[Well_ID];",
        confidence="0.90",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Join with crews table
    dspy.Example(
        user_question="Show which crew is assigned to each well in Nimr",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'pdo_well_id' (int): The unique well ID.
  - Column 'well_name_after_spud' (nvarchar): The official well name.
  - Column 'Cluster' (nvarchar): The operational cluster.
  - Column 'rig_no' (nvarchar): The rig identifier.

TABLE: crews
  - Column 'rig_code' (nvarchar): The rig code (join key).
  - Column 'crew_uid' (nvarchar): The crew unique identifier.
  - Column 'crew_type' (nvarchar): Type of crew.""",
        sql_query="SELECT w.pdo_well_id, w.well_name_after_spud, w.rig_no, c.crew_uid, c.crew_type FROM WellMonitoringReport w LEFT JOIN crews c ON w.rig_no = c.rig_code WHERE w.Cluster = 'Nimr';",
        confidence="0.90",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Multi-table join with aggregation
    dspy.Example(
        user_question="Show total revenue by cluster",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'pdo_well_id' (int): The unique well ID.
  - Column 'Cluster' (nvarchar): The operational cluster.

TABLE: Revenue
  - Column 'Well_ID' (int): The well identifier.
  - Column 'Revenue_Current_Month_Actual' (float): Actual revenue.""",
        sql_query="SELECT w.Cluster, SUM(r.Revenue_Current_Month_Actual) AS total_revenue FROM WellMonitoringReport w INNER JOIN Revenue r ON w.pdo_well_id = r.Well_ID GROUP BY w.Cluster ORDER BY total_revenue DESC;",
        confidence="0.90",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Join WMR_Full with SAP
    dspy.Example(
        user_question="Show WMR data combined with SAP drilling sequence",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: WMR_Full
  - Column 'pdo_well_id' (int): The unique well ID.
  - Column 'well_name_after_spud' (nvarchar): The official well name.
  - Column 'well_location' (nvarchar): The location of the well.
  - Column 'over_all_progress_percentages' (float): Overall progress.

TABLE: SAP_DRILLING_SEQUENCE
  - Column 'Well_Name' (nvarchar): The well name in SAP.
  - Column 'Field' (nvarchar): The field name.
  - Column 'Opr_System_status' (nvarchar): Operational status.""",
        sql_query="SELECT w.pdo_well_id, w.well_name_after_spud, w.well_location, w.over_all_progress_percentages * 100 AS progress_pct, s.Opr_System_status FROM WMR_Full w LEFT JOIN SAP_DRILLING_SEQUENCE s ON w.well_name_after_spud = s.Well_Name;",
        confidence="0.85",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Complex: Well + Job Progress + Revenue
    dspy.Example(
        user_question="Show wells with their progress, variance, and revenue all together",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'pdo_well_id' (int): The unique well ID.
  - Column 'well_name_after_spud' (nvarchar): The official well name.
  - Column 'Cluster' (nvarchar): The operational cluster.

TABLE: Job_Progress_Report_GB
  - Column 'Well_ID' (smallint): The PDO well ID.
  - Column 'Week_1_Actual' (float): Week 1 actual.
  - Column 'Week_1_Plan' (float): Week 1 plan.

TABLE: Revenue
  - Column 'Well_ID' (int): The well ID.
  - Column 'Revenue_Current_Month_Actual' (float): Revenue this month.""",
        sql_query="SELECT w.pdo_well_id, w.well_name_after_spud, w.Cluster, w.over_all_progress_percentages * 100 AS progress_pct, j.[Week_1_Actual] - j.[Week_1_Plan] AS Week1_Variance, r.Revenue_Current_Month_Actual FROM WellMonitoringReport w LEFT JOIN Job_Progress_Report_GB j ON w.pdo_well_id = j.[Well_ID] LEFT JOIN Revenue r ON w.pdo_well_id = r.Well_ID;",
        confidence="0.85",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Field-based queries (SAP)
    dspy.Example(
        user_question="How many wells are in FAHUD field and show their status",
        query_type="single_table",
        neo4j_schema_context="""TABLE: SAP_DRILLING_SEQUENCE
  - Column 'Well_Name' (nvarchar): The well name.
  - Column 'Field' (nvarchar): The field name (e.g., FAHUD, NIMR, LEKHWAIR).
  - Column 'Opr_System_status' (nvarchar): Operational status.
  - Column 'Well_Function' (nvarchar): Well function type.""",
        sql_query="SELECT Field, COUNT(DISTINCT Well_Name) AS well_count, Opr_System_status FROM SAP_DRILLING_SEQUENCE WHERE Field = 'FAHUD' GROUP BY Field, Opr_System_status;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Employee/crew productivity
    dspy.Example(
        user_question="Show wells with their assigned crew and progress",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'pdo_well_id' (int): The unique well ID.
  - Column 'well_name_after_spud' (nvarchar): The official well name.
  - Column 'rig_no' (nvarchar): The rig identifier.

TABLE: crews
  - Column 'rig_code' (nvarchar): The rig code.
  - Column 'crew_uid' (nvarchar): Crew identifier.
  - Column 'crew_type' (nvarchar): Type of crew.
  - Column 'code' (nvarchar): Crew code.""",
        sql_query="SELECT w.pdo_well_id, w.well_name_after_spud, w.rig_no, c.crew_uid, c.crew_type, c.code AS crew_code FROM WellMonitoringReport w LEFT JOIN crews c ON w.rig_no = c.rig_code;",
        confidence="0.90",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Subquery example
    dspy.Example(
        user_question="Show wells that are above average progress in their cluster",
        query_type="subquery",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column 'pdo_well_id' (int): The unique well ID.
  - Column 'well_name_after_spud' (nvarchar): The official well name.
  - Column 'Cluster' (nvarchar): The operational cluster.
  - Column 'over_all_progress_percentages' (float): Overall progress (0-1 scale).""",
        sql_query="SELECT pdo_well_id, well_name_after_spud, Cluster, over_all_progress_percentages * 100 AS progress_pct FROM WellMonitoringReport WHERE Cluster = 'Nimr' AND TRY_CAST(over_all_progress_percentages AS FLOAT) > (SELECT AVG(TRY_CAST(over_all_progress_percentages AS FLOAT)) FROM WellMonitoringReport WHERE Cluster = 'Nimr');",
        confidence="0.90",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # ========== APPMASTERDB VIEW EXAMPLES - COMPLETE ==========

    # Job_Progress_Report_GB: Weekly progress with exact column names (BRACKETS REQUIRED!)
    dspy.Example(
        user_question="Show week 1 actual progress for all wells",
        query_type="single_table",
        neo4j_schema_context="""TABLE: Job_Progress_Report_GB
  - Column [Well ID] (nvarchar): Unique well identifier - USE BRACKETS due to space!
  - Column [Well Name / Project Name] (nvarchar): Human readable well name
  - Column [Week-1 Actual %] (decimal): Week 1 actual progress percentage
  - Column [Week-1 Plan %] (decimal): Week 1 planned progress
  - Column [Category] (nvarchar): Project category from ProjectIDs""",
        sql_query="SELECT [Well ID], [Well Name / Project Name], [Week-1 Actual %], [Week-1 Plan %] FROM Job_Progress_Report_GB;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Job_Progress_Report_GB: Current month totals
    dspy.Example(
        user_question="What is the current month actual progress vs plan for each well?",
        query_type="single_table",
        neo4j_schema_context="""TABLE: Job_Progress_Report_GB
  - Column [Well ID] (nvarchar): Well identifier with brackets!
  - Column [Well Name / Project Name] (nvarchar): Well name
  - Column [Current Month Plan %] (decimal): Total month planned progress
  - Column [Current Month Actual %] (decimal): Total month actual progress""",
        sql_query="SELECT [Well Name / Project Name], [Current Month Plan %], [Current Month Actual %] FROM Job_Progress_Report_GB;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Job_Progress_Report_GB: Purpose Value (monetary)
    dspy.Example(
        user_question="Show purpose value and actual achievement for each well",
        query_type="single_table",
        neo4j_schema_context="""TABLE: Job_Progress_Report_GB
  - Column [Well Name / Project Name] (nvarchar): Well identifier
  - Column [Purpose Value] (decimal): Monetary purpose value
  - Column [Current Month Actual] (decimal): Actual value achieved
  - Column [Category] (nvarchar): Project category""",
        sql_query="SELECT [Well Name / Project Name], [Purpose Value], [Current Month Actual], [Category] FROM Job_Progress_Report_GB;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # PH_Productivity: Productivity calculations
    dspy.Example(
        user_question="Show productivity by PH (QHSE Supervisor)",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: PH_Productivity
  - Column [PH Name] (nvarchar): QHSE Supervisor name
  - Column [Average Productivity (%)] (decimal): Average productivity percentage = (QtyPerHour/Norms)*100
  - Column [Date] (date): Activity date""",
        sql_query="SELECT [PH Name], AVG([Average Productivity (%)]) AS avg_productivity FROM PH_Productivity GROUP BY [PH Name];",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # PH_Productivity: Crew productivity
    dspy.Example(
        user_question="Show crew productivity this month",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: PH_Productivity
  - Column [Crew Name] (nvarchar): Crew type description
  - Column [Crew Type] (nvarchar): Crew type code
  - Column [Average Productivity (%)] (decimal): Productivity percentage
  - Column [Date] (date): Activity date""",
        sql_query="SELECT [Crew Name], [Crew Type], AVG([Average Productivity (%)]) AS productivity FROM PH_Productivity WHERE MONTH([Date]) = MONTH(GETDATE()) AND YEAR([Date]) = YEAR(GETDATE()) GROUP BY [Crew Name], [Crew Type];",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # vw_JOB_COST: Resource tracking
    dspy.Example(
        user_question="Show planned vs actual employees for each well",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: vw_JOB_COST
  - Column [Well ID] (nvarchar): Well identifier
  - Column [Project] (nvarchar): Project/rigcode from Revenue
  - Column [crew code] (nvarchar): Crew identifier
  - Column [Plan Employee Name/ Equipment Name] (nvarchar): Planned resource
  - Column [Actual Employee / Equipment Name] (nvarchar): Actual resource""",
        sql_query="SELECT [Well ID], [Project], [crew code], [Plan Employee Name/ Equipment Name], [Actual Employee / Equipment Name] FROM vw_JOB_COST;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # vw_JOB_COST: Project/rig cost
    dspy.Example(
        user_question="Show total cost by rig (project)",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: vw_JOB_COST
  - Column [Project] (nvarchar): Rig code from Revenue.rigcode (NL0010, NF0010 etc)
  - Column [Effective Work Hours] (decimal): Actual hours worked""",
        sql_query="SELECT [Project], SUM([Effective Work Hours]) AS total_hours FROM vw_JOB_COST GROUP BY [Project];",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # CRITICAL Risk = ROL (actively drilling) + Zero OHL
    dspy.Example(
        user_question="Which CRITICAL risk wells also have zero OHL progress?",
        query_type="single_table",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column [pdo_well_id] (nvarchar): Unique ID.
  - Column [well_name_after_spud] (nvarchar): Well name.
  - Column [ohl_progress] (decimal): OHL completion (0-100).
  - Column [buffer_status] (nvarchar): Status values: 'drilled', 'ROL', 'Buffer1', 'Buffer2', 'Error', NULL.
    * 'ROL' = Rig On Location - well is actively being drilled (CRITICAL risk)
  - Column [over_all_progress_percentages] (decimal): Overall progress.
  - Column [rig_no] (nvarchar): Rig identifier.
  NOTE: 'risk_tier' is NOT in database. CRITICAL risk = buffer_status='ROL' (active on rig).""",
        sql_query="SELECT pdo_well_id, well_name_after_spud, ohl_progress, buffer_status, over_all_progress_percentages, rig_no FROM WellMonitoringReport WHERE buffer_status = 'ROL' AND (ohl_progress = 0 OR ohl_progress IS NULL);",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),
    # IFC within 75 days of spud - CORRECT LOGIC
    dspy.Example(
        user_question="Which wells have not had IFC issued within 75 days of spud, and by how many days are they overdue?",
        query_type="single_table",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column [pdo_well_id] (nvarchar): Unique well ID
  - Column [well_name_after_spud] (nvarchar): Official well name
  - Column [actual_rig_on_date] (date): Spud date - when rig arrived (USE THIS for spud!)
  - Column [actual_comm._start_date] (date): IFC date - Initial For Construction / commissioning start
  NOTE: IFC is commissioning, NOT FLAF! Use [actual_comm._start_date] for IFC.""",
        sql_query="SELECT pdo_well_id, well_name_after_spud, actual_rig_on_date AS spud_date, [actual_comm._start_date] AS ifc_date, DATEDIFF(day, actual_rig_on_date, [actual_comm._start_date]) AS days_to_ifc, CASE WHEN DATEDIFF(day, actual_rig_on_date, [actual_comm._start_date]) > 75 THEN DATEDIFF(day, actual_rig_on_date, [actual_comm._start_date]) - 75 ELSE 0 END AS overdue_days FROM WellMonitoringReport WHERE actual_rig_on_date IS NOT NULL AND [actual_comm._start_date] IS NOT NULL AND DATEDIFF(day, actual_rig_on_date, [actual_comm._start_date]) > 75 ORDER BY overdue_days DESC;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),
    # Flowline completion with days to rig-on - CORRECT COLUMN NAMES
    dspy.Example(
        user_question="Which wells are below 50% flowline completion with fewer than 45 days to the tentative rig-on date?",
        query_type="single_table",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column [pdo_well_id] (nvarchar): Unique well ID
  - Column [well_name_after_spud] (nvarchar): Official well name
  - Column [flowline_construction_progress] (decimal): Flowline completion (0-1 scale)
  - Column [latest_exp.rig_on_location_sap_data] (date): TENTATIVE rig-on date from SAP
  NOTE: Column names with dots MUST use brackets like [latest_exp.rig_on_location_sap_data]""",
        sql_query="SELECT pdo_well_id, well_name_after_spud, (flowline_construction_progress * 100) AS flowline_pct, [latest_exp.rig_on_location_sap_data] AS tentative_rig_on_date, DATEDIFF(day, GETDATE(), [latest_exp.rig_on_location_sap_data]) AS days_to_rig_on FROM WellMonitoringReport WHERE (flowline_construction_progress * 100) < 50 AND [latest_exp.rig_on_location_sap_data] IS NOT NULL AND DATEDIFF(day, GETDATE(), [latest_exp.rig_on_location_sap_data]) < 45 ORDER BY days_to_rig_on ASC;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),
    # WellMonitoringReport: MOC with exact values
    dspy.Example(
        user_question="Which wells have MOC approved in Nimr cluster?",
        query_type="single_table",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column [pdo_well_id] (nvarchar): Unique well ID
  - Column [well_name_after_spud] (nvarchar): Official well name
  - Column [Cluster] (nvarchar): nimr or marmul
  - Column [moc_raised] (nvarchar): Values: YES or Yes (NOT 'Raised')
  - Column [moc_approved] (nvarchar): Values: YES or Yes (NOT 'Approved')""",
        sql_query="SELECT pdo_well_id, well_name_after_spud, Cluster, moc_raised, moc_approved FROM WellMonitoringReport WHERE Cluster = 'Nimr' AND moc_approved IN ('YES', 'Yes', 'yes');",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Category filtering from ProjectIDs
    dspy.Example(
        user_question="Show wells in Marmul SNLP category",
        query_type="single_table",
        neo4j_schema_context="""TABLE: Job_Progress_Report_GB
  - Column [Well Name / Project Name] (nvarchar): Well name
  - Column [Category] (nvarchar): Project category (Marmul SNLP, Conversion, Flowline etc)""",
        sql_query="SELECT [Well Name / Project Name], [Category] FROM Job_Progress_Report_GB WHERE [Category] LIKE '%Marmul%' OR [Category] LIKE '%SNLP%';",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # CRITICAL: Multi-week stall detection (solving user's main issue)
    dspy.Example(
        user_question="How many wells per rig have been stuck at the same progress for 3+ weeks?",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: Job_Progress_Report_GB
  - Column [Well ID] (nvarchar): Well identifier.
  - Column [Week-1 Actual %] (decimal): Progress in week 1.
  - Column [Week-2 Actual %] (decimal): Progress in week 2.
  - Column [Week-3 Actual %] (decimal): Progress in week 3.
  - Note: zero progress across W1-W3 indicates a 3-week stall.

TABLE: WellMonitoringReport
  - Column [pdo_well_id] (nvarchar): Well identifier (join key).
  - Column [rig_no] (nvarchar): Rig identifier.""",
        sql_query="SELECT w.rig_no AS Rig, COUNT(DISTINCT j.[Well ID]) AS Stuck_Wells_3Plus_Weeks FROM Job_Progress_Report_GB j JOIN WellMonitoringReport w ON j.[Well ID] = w.pdo_well_id WHERE TRY_CAST(j.[Week-1 Actual %] AS FLOAT) = 0 AND TRY_CAST(j.[Week-2 Actual %] AS FLOAT) = 0 AND TRY_CAST(j.[Week-3 Actual %] AS FLOAT) = 0 GROUP BY w.rig_no ORDER BY Stuck_Wells_3Plus_Weeks DESC;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # PH Productivity Ranking
    dspy.Example(
        user_question="Rank the top 10 Project Holders (PH) by their average productivity this month",
        query_type="ranking",
        neo4j_schema_context="""TABLE: PH_Productivity
  - Column [PH Name] (nvarchar): The supervisor name.
  - Column [Average Productivity (%)] (decimal): Productivity percentage.
  - Column [Date] (date): Date of activity.""",
        sql_query="SELECT TOP 10 [PH Name], AVG([Average Productivity (%)]) AS Overall_Avg_Productivity FROM PH_Productivity WHERE [Date] >= DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1) GROUP BY [PH Name] ORDER BY Overall_Avg_Productivity DESC;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # PI Bucket Analysis
    dspy.Example(
        user_question="How many crews fall into each PI (CMR) bucket?",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: PH_Productivity
  - Column [Crew Name] (nvarchar): Crew description.
  - Column [PI (CMR)] (nvarchar): Productivity index bucket (P0-P8).""",
        sql_query="SELECT [PI (CMR)], COUNT(DISTINCT [Crew Name]) AS Crew_Count FROM PH_Productivity GROUP BY [PI (CMR)] ORDER BY [PI (CMR)];",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Job Cost Resource Comparison
    dspy.Example(
        user_question="Show me tasks where the actual employee assigned was different from the planned employee",
        query_type="comparison",
        neo4j_schema_context="""TABLE: vw_JOB_COST
  - Column [Well ID] (nvarchar): Well identifier.
  - Column [Activity Code] (nvarchar): Task identifier.
  - Column [Plan Employee Name/ Equipment Name] (nvarchar): Planned resource.
  - Column [Actual Employee / Equipment Name] (nvarchar): Actual resource.""",
        sql_query="SELECT [Well ID], [Activity Code], [Plan Employee Name/ Equipment Name] AS Planned, [Actual Employee / Equipment Name] AS Actual FROM vw_JOB_COST WHERE [Plan Employee Name/ Equipment Name] <> [Actual Employee / Equipment Name] AND [Plan Employee Name/ Equipment Name] IS NOT NULL AND [Actual Employee / Equipment Name] IS NOT NULL;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Multi-week Trend Routing
    dspy.Example(
        user_question="What is the weekly progress variance for all Nimr Location projects?",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: Job_Progress_Report_GB
  - Column [Category] (nvarchar): Project category (e.g. Nimr Location).
  - Column [Week-1 Actual %], [Week-1 Plan %], [Week-2 Actual %], [Week-2 Plan %] (decimal).

TABLE: WellMonitoringReport
  - Column [pdo_well_id] (nvarchar): Well ID.
  - Column [well_name_after_spud] (nvarchar): Well name.""",
        sql_query="SELECT w.well_name_after_spud, j.[Week-1 Actual %] - j.[Week-1 Plan %] AS W1_Variance, j.[Week-2 Actual %] - j.[Week-2 Plan %] AS W2_Variance FROM Job_Progress_Report_GB j JOIN WellMonitoringReport w ON j.[Well ID] = w.pdo_well_id WHERE j.[Category] LIKE '%Nimr Location%';",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Ratio of Engineering vs Construction Done (Double-Check Logic)
    dspy.Example(
        user_question="What is the ratio of wells with engineering done vs wells with construction done?",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column [pdo_well_id] (nvarchar): Unique well ID.
  - Column [actual_eng._completion_date] (date): Engineering milestone.
  - Column [overall_engg._10_100] (decimal): Engineering progress.
  - Column [const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date] (date): Construction milestone.
  - Column [overall_const._10_100] (decimal): Construction progress.""",
        sql_query="SELECT COUNT(DISTINCT CASE WHEN [actual_eng._completion_date] IS NOT NULL OR [overall_engg._10_100] >= 100 THEN pdo_well_id END) * 1.0 / NULLIF(COUNT(DISTINCT CASE WHEN [const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date] IS NOT NULL OR [overall_const._10_100] >= 100 THEN pdo_well_id END), 0) AS engineering_to_construction_ratio FROM WellMonitoringReport;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Fastest vs Slowest well per rig (User's Gold Standard ROW_NUMBER pattern)
    dspy.Example(
        user_question="For each rig, show the fastest and slowest well completion time",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column [rig_no] (nvarchar): Rig identifier.
  - Column [pdo_well_id] (nvarchar): Unique well ID.
  - Column [well_name_after_spud] (nvarchar): Well name.
  - Column [actual_rig_on_date] (date): Start date.
  - Column [actual_rig_off_date] (date): End date.""",
        sql_query="WITH WellCompletionTimes AS (SELECT w.rig_no, w.well_name_after_spud, w.pdo_well_id, DATEDIFF(day, w.actual_rig_on_date, w.actual_rig_off_date) AS completion_days FROM WellMonitoringReport w WHERE w.actual_rig_on_date IS NOT NULL AND w.actual_rig_off_date IS NOT NULL), RankedWells AS (SELECT rig_no, well_name_after_spud, pdo_well_id, completion_days, ROW_NUMBER() OVER (PARTITION BY rig_no ORDER BY completion_days ASC) AS fastest_rank, ROW_NUMBER() OVER (PARTITION BY rig_no ORDER BY completion_days DESC) AS slowest_rank FROM WellCompletionTimes) SELECT r.rig_no, f.well_name_after_spud AS fastest_well_name, f.completion_days AS fastest_completion_days, s.well_name_after_spud AS slowest_well_name, s.completion_days AS slowest_completion_days FROM (SELECT DISTINCT rig_no FROM RankedWells) r LEFT JOIN RankedWells f ON r.rig_no = f.rig_no AND f.fastest_rank = 1 LEFT JOIN RankedWells s ON r.rig_no = s.rig_no AND s.slowest_rank = 1 ORDER BY r.rig_no;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="What is our overall project portfolio status today?",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column [Week_Number] (date): Snapshot date for the portfolio.
  - Column [pdo_well_id] (nvarchar): Unique well identifier; use this for counting wells.
  - Column [Cluster] (nvarchar): Portfolio cluster.
  - Column [over_all_progress_percentages] (decimal): Overall progress on a 0-1 scale.
  - Column [exp.rig_off_location_sap_data] (date): Expected rig-off date from SAP.
  - Column [actual_rig_off_date] (date): Actual rig-off date.""",
        sql_query="WITH latest_snapshot AS (SELECT MAX(Week_Number) AS snapshot_date FROM WellMonitoringReport), portfolio_base AS (SELECT w.pdo_well_id, w.Cluster, TRY_CAST(w.over_all_progress_percentages AS FLOAT) AS progress_ratio, TRY_CAST(w.[exp.rig_off_location_sap_data] AS DATE) AS expected_rig_off, w.actual_rig_off_date FROM WellMonitoringReport w INNER JOIN latest_snapshot s ON w.Week_Number = s.snapshot_date) SELECT (SELECT snapshot_date FROM latest_snapshot) AS snapshot_date, COUNT(DISTINCT pdo_well_id) AS total_wells, CAST(AVG(progress_ratio) * 100 AS DECIMAL(10,2)) AS avg_progress_pct, SUM(CASE WHEN progress_ratio >= 1 THEN 1 ELSE 0 END) AS complete_wells, SUM(CASE WHEN progress_ratio = 0 THEN 1 ELSE 0 END) AS not_started_wells, SUM(CASE WHEN progress_ratio > 0 AND progress_ratio < 1 THEN 1 ELSE 0 END) AS active_wells, SUM(CASE WHEN expected_rig_off < CAST(GETDATE() AS DATE) AND actual_rig_off_date IS NULL THEN 1 ELSE 0 END) AS overdue_rig_off_no_actual FROM portfolio_base;",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="Which projects are at risk (cost, schedule, safety)?",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column [Week_Number] (date): Snapshot date.
  - Column [pdo_well_id] (nvarchar): Unique well identifier.
  - Column [well_name_after_spud] (nvarchar): Official well/project display name.
  - Column [Cluster] (nvarchar): Operational cluster.
  - Column [rig_no] (nvarchar): Rig identifier.
  - Column [over_all_progress_percentages] (decimal): Overall progress on a 0-1 scale.
  - Column [exp.rig_off_location_sap_data] (date): Expected rig-off date from SAP.
  - Column [actual_rig_off_date] (date): Actual rig-off date.

TABLE: Revenue
  - Column [well_id] (nvarchar): Join key to WellMonitoringReport.pdo_well_id.
  - Column [rigcode] (nvarchar): Project/rig code.
  - Column [planned_purpose_value] (nvarchar): Planned value - MUST CAST to DECIMAL before SUM.
  - Column [actual_purpose_value] (decimal): Actual value achieved.

NOTE:
  - Direct safety incident or hazard data is not available in this schema context.
  - Return safety_risk as NULL with a note instead of inventing a proxy.""",
        sql_query="WITH latest_snapshot AS (SELECT MAX([Week_Number]) AS snapshot_date FROM [WellMonitoringReport]), latest_wmr AS (SELECT w.[pdo_well_id], w.[well_name_after_spud], w.[Cluster], w.[rig_no], TRY_CAST(w.[over_all_progress_percentages] AS FLOAT) AS progress_ratio, TRY_CAST(w.[exp.rig_off_location_sap_data] AS DATE) AS expected_rig_off, w.[actual_rig_off_date] FROM [WellMonitoringReport] w INNER JOIN latest_snapshot s ON w.[Week_Number] = s.snapshot_date), cost_by_well AS (SELECT TRY_CONVERT(nvarchar(50), r.[well_id]) AS well_id, MAX(r.[rigcode]) AS project_code, SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) AS planned_value, SUM(TRY_CAST(r.[actual_purpose_value] AS DECIMAL(18,2))) AS actual_value FROM [Revenue] r GROUP BY TRY_CONVERT(nvarchar(50), r.[well_id])) SELECT w.[pdo_well_id], w.[well_name_after_spud], w.[Cluster], w.[rig_no], c.project_code, CAST(w.progress_ratio * 100 AS DECIMAL(10,2)) AS progress_pct, w.expected_rig_off, w.[actual_rig_off_date], c.planned_value, c.actual_value, c.actual_value - c.planned_value AS cost_gap, CASE WHEN c.planned_value > 0 THEN ((c.actual_value - c.planned_value) * 100.0) / c.planned_value ELSE NULL END AS cost_gap_pct, CASE WHEN c.planned_value > 0 AND c.actual_value < c.planned_value THEN 'AT_RISK' ELSE 'OK' END AS cost_risk, CASE WHEN w.expected_rig_off < CAST(GETDATE() AS DATE) AND w.[actual_rig_off_date] IS NULL THEN 'OVERDUE' WHEN w.expected_rig_off <= DATEADD(DAY, 14, CAST(GETDATE() AS DATE)) AND w.progress_ratio < 0.60 AND w.[actual_rig_off_date] IS NULL THEN 'AT_RISK_NEXT_14_DAYS' ELSE 'OK' END AS schedule_risk, CAST(NULL AS NVARCHAR(50)) AS safety_risk, 'No direct safety incident or hazard data in current schema' AS safety_note FROM latest_wmr w LEFT JOIN cost_by_well c ON c.well_id = w.[pdo_well_id] WHERE (c.planned_value > 0 AND c.actual_value < c.planned_value) OR ((w.expected_rig_off < CAST(GETDATE() AS DATE) AND w.[actual_rig_off_date] IS NULL) OR (w.expected_rig_off <= DATEADD(DAY, 14, CAST(GETDATE() AS DATE)) AND w.progress_ratio < 0.60 AND w.[actual_rig_off_date] IS NULL)) ORDER BY w.expected_rig_off, cost_gap_pct, progress_pct;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="Generate a chart for projects at risk across cost and schedule",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column [Week_Number] (date): Snapshot date.
  - Column [pdo_well_id] (nvarchar): Unique well identifier.
  - Column [over_all_progress_percentages] (decimal): Overall progress on a 0-1 scale.
  - Column [exp.rig_off_location_sap_data] (date): Expected rig-off date from SAP.
  - Column [actual_rig_off_date] (date): Actual rig-off date.

TABLE: Revenue
  - Column [well_id] (nvarchar): Join key to WellMonitoringReport.pdo_well_id.
  - Column [rigcode] (nvarchar): Project/rig code.
  - Column [planned_purpose_value] (nvarchar): Planned value - MUST CAST to DECIMAL before SUM.
  - Column [actual_purpose_value] (decimal): Actual value achieved.

NOTE:
  - For charting, aggregate by project_code/rigcode.
  - Return numeric risk counts per project so the frontend can render grouped bars.""",
        sql_query="WITH latest_snapshot AS (SELECT MAX([Week_Number]) AS snapshot_date FROM [WellMonitoringReport]), latest_wmr AS (SELECT w.[pdo_well_id], TRY_CAST(w.[over_all_progress_percentages] AS FLOAT) AS progress_ratio, TRY_CAST(w.[exp.rig_off_location_sap_data] AS DATE) AS expected_rig_off, w.[actual_rig_off_date] FROM [WellMonitoringReport] w INNER JOIN latest_snapshot s ON w.[Week_Number] = s.snapshot_date), cost_by_well AS (SELECT TRY_CONVERT(nvarchar(50), r.[well_id]) AS well_id, MAX(r.[rigcode]) AS project_code, SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) AS planned_value, SUM(TRY_CAST(r.[actual_purpose_value] AS DECIMAL(18,2))) AS actual_value FROM [Revenue] r GROUP BY TRY_CONVERT(nvarchar(50), r.[well_id])) SELECT c.project_code, COUNT(DISTINCT CASE WHEN c.planned_value > 0 AND c.actual_value < c.planned_value THEN w.[pdo_well_id] END) AS cost_risk_wells, COUNT(DISTINCT CASE WHEN w.expected_rig_off < CAST(GETDATE() AS DATE) AND w.[actual_rig_off_date] IS NULL THEN w.[pdo_well_id] WHEN w.expected_rig_off <= DATEADD(DAY, 14, CAST(GETDATE() AS DATE)) AND w.progress_ratio < 0.60 AND w.[actual_rig_off_date] IS NULL THEN w.[pdo_well_id] END) AS schedule_risk_wells, COUNT(DISTINCT CASE WHEN (c.planned_value > 0 AND c.actual_value < c.planned_value) OR (w.expected_rig_off < CAST(GETDATE() AS DATE) AND w.[actual_rig_off_date] IS NULL) OR (w.expected_rig_off <= DATEADD(DAY, 14, CAST(GETDATE() AS DATE)) AND w.progress_ratio < 0.60 AND w.[actual_rig_off_date] IS NULL) THEN w.[pdo_well_id] END) AS total_at_risk_wells FROM latest_wmr w LEFT JOIN cost_by_well c ON c.well_id = w.[pdo_well_id] WHERE c.project_code IS NOT NULL GROUP BY c.project_code HAVING COUNT(DISTINCT CASE WHEN (c.planned_value > 0 AND c.actual_value < c.planned_value) OR (w.expected_rig_off < CAST(GETDATE() AS DATE) AND w.[actual_rig_off_date] IS NULL) OR (w.expected_rig_off <= DATEADD(DAY, 14, CAST(GETDATE() AS DATE)) AND w.progress_ratio < 0.60 AND w.[actual_rig_off_date] IS NULL) THEN w.[pdo_well_id] END) > 0 ORDER BY total_at_risk_wells DESC, c.project_code;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="What is the current profit margin per project? Use planned vs actual purpose value as a proxy.",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: Revenue
  - Column [well_id] (nvarchar): Join key to WellMonitoringReport.pdo_well_id.
  - Column [actual_purpose_value] (decimal): Actual value achieved.
  - Column [planned_purpose_value] (nvarchar): Planned value - MUST CAST to DECIMAL before aggregation.

TABLE: Job_Progress_Report_GB
  - Column [Well ID] (nvarchar): Well identifier.
  - Column [Category] (nvarchar): Project category values such as Nimr Location, Nimr Flowline, Marmul Location.

NOTE:
  - In client/business language, "project" defaults to category unless the user explicitly asks for rig code or well name.
  - User has accepted planned vs actual purpose value as a proxy instead of true cost.
  - Aggregate at category grain.""",
        sql_query="WITH revenue_by_well AS (SELECT TRY_CONVERT(nvarchar(50), r.[well_id]) AS [well_id], SUM(r.[actual_purpose_value]) AS [actual_revenue], SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) AS [planned_revenue] FROM [Revenue] r WHERE r.[created_at] >= DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1) AND TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2)) IS NOT NULL GROUP BY TRY_CONVERT(nvarchar(50), r.[well_id])), category_by_well AS (SELECT TRY_CONVERT(nvarchar(50), j.[Well ID]) AS [well_id], MAX(j.[Category]) AS [Category] FROM [Job_Progress_Report_GB] j WHERE j.[Category] IS NOT NULL GROUP BY TRY_CONVERT(nvarchar(50), j.[Well ID])) SELECT c.[Category] AS [Project], SUM(r.[actual_revenue]) AS [Actual_Revenue], SUM(r.[planned_revenue]) AS [Planned_Revenue], CASE WHEN SUM(r.[planned_revenue]) = 0 THEN NULL ELSE ((SUM(r.[actual_revenue]) - SUM(r.[planned_revenue])) * 100.0) / SUM(r.[planned_revenue]) END AS [Revenue_Variance_Pct], CASE WHEN SUM(r.[planned_revenue]) = 0 THEN NULL ELSE SUM(r.[actual_revenue]) / SUM(r.[planned_revenue]) END AS [Achievement_Rate] FROM revenue_by_well r INNER JOIN category_by_well c ON c.[well_id] = r.[well_id] GROUP BY c.[Category] ORDER BY [Revenue_Variance_Pct] DESC;",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="What is the forecasted revenue for this quarter?",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: Revenue
  - Column [created_at] (datetime2): Revenue record timestamp.
  - Column [actual_purpose_value] (decimal): Actual revenue booked.
  - Column [planned_purpose_value] (nvarchar): Planned revenue - MUST CAST to DECIMAL before aggregation.
  NOTE:
  - For SQL-only forecasting, use quarter-to-date actual revenue run rate projected to quarter end.
  - Do NOT restrict to created_at = MAX(created_at) only.
  - Do NOT return only planned value and call it forecasted revenue.
  - Compare the forecast against full-quarter planned revenue, not planned-to-date.""",
        sql_query="WITH quarter_bounds AS (SELECT DATEADD(QUARTER, DATEDIFF(QUARTER, 0, GETDATE()), 0) AS quarter_start, DATEADD(DAY, -1, DATEADD(QUARTER, DATEDIFF(QUARTER, 0, GETDATE()) + 1, 0)) AS quarter_end), actual_to_date AS (SELECT MAX(qb.quarter_start) AS quarter_start, MAX(qb.quarter_end) AS quarter_end, MAX(CAST(r.[created_at] AS DATE)) AS as_of_date, SUM(TRY_CAST(r.[actual_purpose_value] AS DECIMAL(18,2))) AS actual_revenue_to_date FROM [Revenue] r CROSS JOIN quarter_bounds qb WHERE CAST(r.[created_at] AS DATE) >= qb.quarter_start AND CAST(r.[created_at] AS DATE) <= CAST(GETDATE() AS DATE)), planned_full_quarter AS (SELECT SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) AS planned_revenue_full_quarter FROM [Revenue] r CROSS JOIN quarter_bounds qb WHERE CAST(r.[created_at] AS DATE) >= qb.quarter_start AND CAST(r.[created_at] AS DATE) <= qb.quarter_end), projection AS (SELECT a.quarter_start, a.quarter_end, a.as_of_date, a.actual_revenue_to_date, p.planned_revenue_full_quarter, DATEDIFF(DAY, a.quarter_start, a.as_of_date) + 1 AS elapsed_days, DATEDIFF(DAY, a.quarter_start, a.quarter_end) + 1 AS total_days FROM actual_to_date a CROSS JOIN planned_full_quarter p) SELECT quarter_start, quarter_end, as_of_date, actual_revenue_to_date, planned_revenue_full_quarter, CASE WHEN elapsed_days <= 0 OR actual_revenue_to_date IS NULL THEN NULL ELSE (actual_revenue_to_date / elapsed_days) * total_days END AS forecasted_quarter_revenue, CASE WHEN planned_revenue_full_quarter IS NULL OR planned_revenue_full_quarter = 0 OR elapsed_days <= 0 OR actual_revenue_to_date IS NULL THEN NULL ELSE (((actual_revenue_to_date / elapsed_days) * total_days) - planned_revenue_full_quarter) * 100.0 / planned_revenue_full_quarter END AS forecast_vs_plan_pct FROM projection;",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="Are we on track to meet annual targets?",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: Revenue
  - Column [created_at] (datetime2): Revenue record timestamp.
  - Column [actual_purpose_value] (decimal): Actual revenue booked.
  - Column [planned_purpose_value] (nvarchar): Planned revenue - MUST CAST to DECIMAL before aggregation.
  NOTE:
  - Treat annual targets as annual revenue targets for the current year.
  - Use current-year actual revenue year-to-date projected to year end using run rate.
  - Compare projected full-year actual against full-year planned revenue.
  - Do NOT answer with a lifetime SUM(actual) / SUM(planned) ratio across all rows.""",
        sql_query="WITH year_bounds AS (SELECT DATEFROMPARTS(YEAR(GETDATE()), 1, 1) AS year_start, DATEFROMPARTS(YEAR(GETDATE()), 12, 31) AS year_end), actual_ytd AS (SELECT MAX(CAST(r.[created_at] AS DATE)) AS as_of_date, SUM(TRY_CAST(r.[actual_purpose_value] AS DECIMAL(18,2))) AS actual_revenue_ytd FROM [Revenue] r CROSS JOIN year_bounds y WHERE CAST(r.[created_at] AS DATE) >= y.year_start AND CAST(r.[created_at] AS DATE) <= CAST(GETDATE() AS DATE)), plan_ytd AS (SELECT SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) AS planned_revenue_ytd FROM [Revenue] r CROSS JOIN year_bounds y WHERE CAST(r.[created_at] AS DATE) >= y.year_start AND CAST(r.[created_at] AS DATE) <= CAST(GETDATE() AS DATE)), plan_full_year AS (SELECT SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) AS planned_revenue_full_year FROM [Revenue] r CROSS JOIN year_bounds y WHERE CAST(r.[created_at] AS DATE) >= y.year_start AND CAST(r.[created_at] AS DATE) <= y.year_end), projection AS (SELECT y.year_start, y.year_end, a.as_of_date, a.actual_revenue_ytd, py.planned_revenue_ytd, pf.planned_revenue_full_year, DATEDIFF(DAY, y.year_start, a.as_of_date) + 1 AS elapsed_days, DATEDIFF(DAY, y.year_start, y.year_end) + 1 AS total_days FROM year_bounds y CROSS JOIN actual_ytd a CROSS JOIN plan_ytd py CROSS JOIN plan_full_year pf) SELECT year_start, year_end, as_of_date, actual_revenue_ytd, planned_revenue_ytd, planned_revenue_full_year, CASE WHEN elapsed_days <= 0 OR actual_revenue_ytd IS NULL THEN NULL ELSE (actual_revenue_ytd / elapsed_days) * total_days END AS projected_full_year_actual, CASE WHEN planned_revenue_ytd IS NULL OR planned_revenue_ytd = 0 THEN NULL ELSE actual_revenue_ytd * 100.0 / planned_revenue_ytd END AS ytd_achievement_pct, CASE WHEN planned_revenue_full_year IS NULL OR planned_revenue_full_year = 0 OR elapsed_days <= 0 OR actual_revenue_ytd IS NULL THEN NULL ELSE ((actual_revenue_ytd / elapsed_days) * total_days) * 100.0 / planned_revenue_full_year END AS projected_achievement_pct, CASE WHEN planned_revenue_full_year IS NULL OR planned_revenue_full_year = 0 OR elapsed_days <= 0 OR actual_revenue_ytd IS NULL THEN 'INSUFFICIENT_DATA' WHEN (actual_revenue_ytd / elapsed_days) * total_days >= planned_revenue_full_year THEN 'ON_TRACK' ELSE 'BEHIND_PLAN' END AS annual_target_status FROM projection;",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="What are the major constraints affecting progress?",
        query_type="ranking",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column [Week_Number] (date): Snapshot date.
  - Column [pdo_well_id] (nvarchar): Unique well identifier.
  - Column [overall_const._10_100] (decimal): Construction progress on 0-1 scale.
  - Column [overall_engg._10_100] (decimal): Engineering progress on 0-1 scale.
  - Column [flowline_construction_progress] (decimal): Flowline construction progress on 0-1 scale.
  - Column [overall_ohl_progr_100] (decimal): OHL progress on 0-1 or percentage scale per schema usage.
  - Column [overall_material_10_100] (decimal): Material readiness progress.
  NOTE:
  - Do not use reasons_for_year_2018 by default.
  - Use the latest snapshot and rank measurable bottlenecks by lagging-well share and lowest average progress.""",
        sql_query="WITH latest_snapshot AS (SELECT MAX([Week_Number]) AS snapshot_date FROM [WellMonitoringReport]), phase_metrics AS (SELECT 'Construction' AS [Constraint Area], AVG(TRY_CAST([overall_const._10_100] AS FLOAT)) * 100 AS [Avg Progress %], SUM(CASE WHEN TRY_CAST([overall_const._10_100] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Lagging Wells], COUNT(DISTINCT [pdo_well_id]) AS [Total Wells] FROM [WellMonitoringReport] w INNER JOIN latest_snapshot s ON w.[Week_Number] = s.snapshot_date UNION ALL SELECT 'Engineering' AS [Constraint Area], AVG(TRY_CAST([overall_engg._10_100] AS FLOAT)) * 100 AS [Avg Progress %], SUM(CASE WHEN TRY_CAST([overall_engg._10_100] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Lagging Wells], COUNT(DISTINCT [pdo_well_id]) AS [Total Wells] FROM [WellMonitoringReport] w INNER JOIN latest_snapshot s ON w.[Week_Number] = s.snapshot_date UNION ALL SELECT 'Flowline Construction' AS [Constraint Area], AVG(TRY_CAST([flowline_construction_progress] AS FLOAT)) * 100 AS [Avg Progress %], SUM(CASE WHEN TRY_CAST([flowline_construction_progress] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Lagging Wells], COUNT(DISTINCT [pdo_well_id]) AS [Total Wells] FROM [WellMonitoringReport] w INNER JOIN latest_snapshot s ON w.[Week_Number] = s.snapshot_date UNION ALL SELECT 'Pipe Welding / NDT' AS [Constraint Area], AVG(TRY_CAST([cs_pipe_welding_ndt_10_rt_for_op_100_for_60] AS FLOAT)) * 100 AS [Avg Progress %], SUM(CASE WHEN TRY_CAST([cs_pipe_welding_ndt_10_rt_for_op_100_for_60] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Lagging Wells], COUNT(DISTINCT [pdo_well_id]) AS [Total Wells] FROM [WellMonitoringReport] w INNER JOIN latest_snapshot s ON w.[Week_Number] = s.snapshot_date UNION ALL SELECT 'OHL' AS [Constraint Area], AVG(TRY_CAST([overall_ohl_progr_100] AS FLOAT)) * 100 AS [Avg Progress %], SUM(CASE WHEN TRY_CAST([overall_ohl_progr_100] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Lagging Wells], COUNT(DISTINCT [pdo_well_id]) AS [Total Wells] FROM [WellMonitoringReport] w INNER JOIN latest_snapshot s ON w.[Week_Number] = s.snapshot_date UNION ALL SELECT 'Material Readiness' AS [Constraint Area], AVG(TRY_CAST([overall_material_10_100] AS FLOAT)) * 100 AS [Avg Progress %], SUM(CASE WHEN TRY_CAST([overall_material_10_100] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Lagging Wells], COUNT(DISTINCT [pdo_well_id]) AS [Total Wells] FROM [WellMonitoringReport] w INNER JOIN latest_snapshot s ON w.[Week_Number] = s.snapshot_date) SELECT [Constraint Area], CAST([Avg Progress %] AS DECIMAL(10,2)) AS [Avg Progress %], [Lagging Wells], CAST(([Lagging Wells] * 100.0) / NULLIF([Total Wells], 0) AS DECIMAL(10,2)) AS [Lagging Wells %] FROM phase_metrics WHERE [Avg Progress %] IS NOT NULL ORDER BY [Lagging Wells %] DESC, [Avg Progress %] ASC;",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="What are the top cost overruns and why? Use Revenue planned vs actual purpose value as a proxy. Show cumulative-to-date by well and attach latest operational context for why.",
        query_type="ranking",
        neo4j_schema_context="""TABLE: Revenue
  - Column [well_id] (nvarchar): Join key to WellMonitoringReport.pdo_well_id.
  - Column [rigcode] (nvarchar): Project/rig code.
  - Column [planned_purpose_value] (nvarchar): Planned value - MUST CAST to DECIMAL.
  - Column [actual_purpose_value] (decimal): Actual value.
  - Column [created_at] (datetime2): Time window filter.

TABLE: WellMonitoringReport
  - Column [pdo_well_id] (nvarchar): Well identifier.
  - Column [Week_Number] (date): Snapshot date.
  - Column [well_name_after_spud] (nvarchar): Well display name.
  - Column [Cluster] (nvarchar): Cluster.
  - Column [reason_if_kpi_not_met] (nvarchar): Operational issue text proxy.
  - Column [remark_status_area_of_attention_issues_] (nvarchar): Operational issue text proxy.

NOTE:
  - Aggregate Revenue by well before ranking.
  - Exclude planned_value = 0 from validated overrun ranking.
  - Use latest operational context only as a proxy for why.""",
        sql_query="WITH revenue_by_well AS (SELECT TRY_CONVERT(nvarchar(50), r.[well_id]) AS [well_id], MAX(r.[rigcode]) AS [project_code], SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) AS [planned_value], SUM(TRY_CAST(r.[actual_purpose_value] AS DECIMAL(18,2))) AS [actual_value] FROM [Revenue] r WHERE CAST(r.[created_at] AS DATE) <= CAST(GETDATE() AS DATE) AND TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2)) IS NOT NULL AND TRY_CAST(r.[actual_purpose_value] AS DECIMAL(18,2)) IS NOT NULL GROUP BY TRY_CONVERT(nvarchar(50), r.[well_id])), wmr_latest AS (SELECT w.*, ROW_NUMBER() OVER (PARTITION BY w.[pdo_well_id] ORDER BY w.[Week_Number] DESC) AS rn FROM [WellMonitoringReport] w), well_context AS (SELECT TRY_CONVERT(nvarchar(50), w.[pdo_well_id]) AS [well_id], w.[well_name_after_spud], w.[Cluster], COALESCE(NULLIF(LTRIM(RTRIM(w.[reason_if_kpi_not_met])), ''), NULLIF(LTRIM(RTRIM(w.[remark_status_area_of_attention_issues_])), '')) AS [operational_context] FROM wmr_latest w WHERE w.rn = 1) SELECT TOP 10 wc.[well_name_after_spud] AS [Well Name], r.[project_code] AS [Project Code], wc.[Cluster], r.[planned_value] AS [Planned Value], r.[actual_value] AS [Actual Value], r.[actual_value] - r.[planned_value] AS [Overrun Amount], CASE WHEN r.[planned_value] = 0 THEN NULL ELSE ((r.[actual_value] - r.[planned_value]) * 100.0) / r.[planned_value] END AS [Overrun Pct], wc.[operational_context] AS [Operational Context], CASE WHEN wc.[operational_context] IS NULL THEN 'No direct cost-cause field available in current schema' ELSE 'Operational issue text only; not a validated cost-cause' END AS [Why Note] FROM revenue_by_well r LEFT JOIN well_context wc ON wc.[well_id] = r.[well_id] WHERE r.[actual_value] > r.[planned_value] AND r.[planned_value] > 0 ORDER BY [Overrun Amount] DESC, [Well Name];",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="What is the current cost vs budget for each project? Use Revenue planned vs actual purpose value as a proxy. Use category and current year.",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: Revenue
  - Column [well_id] (nvarchar): Join key to Job_Progress_Report_GB.[Well ID].
  - Column [planned_purpose_value] (nvarchar): Planned value proxy for budget.
  - Column [actual_purpose_value] (decimal): Actual value.
  - Column [created_at] (datetime2): Time filter.

TABLE: Job_Progress_Report_GB
  - Column [Well ID] (nvarchar): Well identifier.
  - Column [Category] (nvarchar): Project category.

NOTE:
  - User accepted Revenue planned vs actual as proxy for budget vs actual.
  - Aggregate by category for current year.""",
        sql_query="WITH revenue_by_well AS (SELECT TRY_CONVERT(nvarchar(50), r.[well_id]) AS [well_id], SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) AS [planned_value], SUM(TRY_CAST(r.[actual_purpose_value] AS DECIMAL(18,2))) AS [actual_value] FROM [Revenue] r WHERE CAST(r.[created_at] AS DATE) >= DATEFROMPARTS(YEAR(GETDATE()), 1, 1) AND CAST(r.[created_at] AS DATE) <= CAST(GETDATE() AS DATE) AND TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2)) IS NOT NULL AND TRY_CAST(r.[actual_purpose_value] AS DECIMAL(18,2)) IS NOT NULL GROUP BY TRY_CONVERT(nvarchar(50), r.[well_id])), category_by_well AS (SELECT TRY_CONVERT(nvarchar(50), j.[Well ID]) AS [well_id], MAX(j.[Category]) AS [Category] FROM [Job_Progress_Report_GB] j WHERE j.[Category] IS NOT NULL GROUP BY TRY_CONVERT(nvarchar(50), j.[Well ID])) SELECT c.[Category], SUM(r.[planned_value]) AS [Planned Value], SUM(r.[actual_value]) AS [Actual Value], SUM(r.[actual_value]) - SUM(r.[planned_value]) AS [Variance Amount], CASE WHEN SUM(r.[planned_value]) = 0 THEN NULL ELSE ((SUM(r.[actual_value]) - SUM(r.[planned_value])) * 100.0) / SUM(r.[planned_value]) END AS [Variance Pct] FROM revenue_by_well r INNER JOIN category_by_well c ON c.[well_id] = r.[well_id] GROUP BY c.[Category] ORDER BY [Variance Amount] DESC, c.[Category];",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="What is the trend analysis of performance KPIs?",
        query_type="trend",
        neo4j_schema_context="""TABLE: WMR_Full
  - Column [Week_Number] (date): Historical weekly snapshot date.
  - Column [over_all_progress_percentages] (decimal): Overall progress ratio.
  - Column [overall_engg._10_100] (decimal): Engineering progress ratio.
  - Column [overall_const._10_100] (decimal): Construction progress ratio.
  - Column [overall_material_10_100] (decimal): Material progress ratio.
  - Column [flowline_construction_progress] (decimal): Flowline progress ratio.
  - Column [overall_ohl_progr_100] (decimal): OHL progress ratio.
  - Column [overall_comm_progress_100] (decimal): Commissioning progress ratio.
  NOTE:
  - Use WMR_Full history, not the latest-only WellMonitoringReport snapshot.
  - Default to weekly portfolio trends over the latest 12 snapshot weeks.""",
        sql_query="WITH latest_weeks AS (SELECT TOP 12 CAST([Week_Number] AS DATE) AS [Snapshot Date] FROM [WMR_Full] WHERE [Week_Number] IS NOT NULL GROUP BY CAST([Week_Number] AS DATE) ORDER BY [Snapshot Date] DESC), weekly_trend AS (SELECT CAST(f.[Week_Number] AS DATE) AS [Snapshot Date], AVG(TRY_CAST(f.[over_all_progress_percentages] AS FLOAT)) * 100 AS [Overall Progress %], AVG(TRY_CAST(f.[overall_engg._10_100] AS FLOAT)) * 100 AS [Engineering %], AVG(TRY_CAST(f.[overall_const._10_100] AS FLOAT)) * 100 AS [Construction %], AVG(TRY_CAST(f.[overall_material_10_100] AS FLOAT)) * 100 AS [Material %], AVG(TRY_CAST(f.[flowline_construction_progress] AS FLOAT)) * 100 AS [Flowline %], AVG(TRY_CAST(f.[overall_ohl_progr_100] AS FLOAT)) * 100 AS [OHL %], AVG(TRY_CAST(f.[overall_comm_progress_100] AS FLOAT)) * 100 AS [Commissioning %] FROM [WMR_Full] f INNER JOIN latest_weeks w ON CAST(f.[Week_Number] AS DATE) = w.[Snapshot Date] GROUP BY CAST(f.[Week_Number] AS DATE)) SELECT [Snapshot Date], CAST([Overall Progress %] AS DECIMAL(10,2)) AS [Overall Progress %], CAST([Engineering %] AS DECIMAL(10,2)) AS [Engineering %], CAST([Construction %] AS DECIMAL(10,2)) AS [Construction %], CAST([Material %] AS DECIMAL(10,2)) AS [Material %], CAST([Flowline %] AS DECIMAL(10,2)) AS [Flowline %], CAST([OHL %] AS DECIMAL(10,2)) AS [OHL %], CAST([Commissioning %] AS DECIMAL(10,2)) AS [Commissioning %] FROM weekly_trend ORDER BY [Snapshot Date];",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="Which KPIs are deviating from thresholds today? Use the latest operational snapshot and flag major phase KPIs below 50% progress as threshold deviations.",
        query_type="ranking",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column [Week_Number] (date): Latest snapshot date.
  - Column [pdo_well_id] (nvarchar): Unique well identifier.
  - Column [over_all_progress_percentages] (decimal): Overall progress ratio.
  - Column [overall_engg._10_100] (decimal): Engineering progress ratio.
  - Column [overall_const._10_100] (decimal): Construction progress ratio.
  - Column [overall_material_10_100] (decimal): Material progress ratio.
  - Column [flowline_construction_progress] (decimal): Flowline progress ratio.
  - Column [overall_ohl_progr_100] (decimal): OHL progress ratio.
  - Column [overall_comm_progress_100] (decimal): Commissioning progress ratio.
  NOTE:
  - User explicitly accepted the proxy threshold definition: major phase KPIs below 50% progress on the latest snapshot.""",
        sql_query="WITH latest_snapshot AS (SELECT MAX([Week_Number]) AS snapshot_date FROM [WellMonitoringReport]), kpi_metrics AS (SELECT 'Overall Progress' AS [KPI], AVG(TRY_CAST(w.[over_all_progress_percentages] AS FLOAT)) * 100 AS [Avg Value %], SUM(CASE WHEN TRY_CAST(w.[over_all_progress_percentages] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Violating Wells], COUNT(DISTINCT w.[pdo_well_id]) AS [Total Wells] FROM [WellMonitoringReport] w INNER JOIN latest_snapshot s ON w.[Week_Number] = s.snapshot_date UNION ALL SELECT 'Engineering' AS [KPI], AVG(TRY_CAST(w.[overall_engg._10_100] AS FLOAT)) * 100 AS [Avg Value %], SUM(CASE WHEN TRY_CAST(w.[overall_engg._10_100] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Violating Wells], COUNT(DISTINCT w.[pdo_well_id]) AS [Total Wells] FROM [WellMonitoringReport] w INNER JOIN latest_snapshot s ON w.[Week_Number] = s.snapshot_date UNION ALL SELECT 'Construction' AS [KPI], AVG(TRY_CAST(w.[overall_const._10_100] AS FLOAT)) * 100 AS [Avg Value %], SUM(CASE WHEN TRY_CAST(w.[overall_const._10_100] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Violating Wells], COUNT(DISTINCT w.[pdo_well_id]) AS [Total Wells] FROM [WellMonitoringReport] w INNER JOIN latest_snapshot s ON w.[Week_Number] = s.snapshot_date UNION ALL SELECT 'Material Readiness' AS [KPI], AVG(TRY_CAST(w.[overall_material_10_100] AS FLOAT)) * 100 AS [Avg Value %], SUM(CASE WHEN TRY_CAST(w.[overall_material_10_100] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Violating Wells], COUNT(DISTINCT w.[pdo_well_id]) AS [Total Wells] FROM [WellMonitoringReport] w INNER JOIN latest_snapshot s ON w.[Week_Number] = s.snapshot_date UNION ALL SELECT 'Flowline Construction' AS [KPI], AVG(TRY_CAST(w.[flowline_construction_progress] AS FLOAT)) * 100 AS [Avg Value %], SUM(CASE WHEN TRY_CAST(w.[flowline_construction_progress] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Violating Wells], COUNT(DISTINCT w.[pdo_well_id]) AS [Total Wells] FROM [WellMonitoringReport] w INNER JOIN latest_snapshot s ON w.[Week_Number] = s.snapshot_date UNION ALL SELECT 'OHL' AS [KPI], AVG(TRY_CAST(w.[overall_ohl_progr_100] AS FLOAT)) * 100 AS [Avg Value %], SUM(CASE WHEN TRY_CAST(w.[overall_ohl_progr_100] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Violating Wells], COUNT(DISTINCT w.[pdo_well_id]) AS [Total Wells] FROM [WellMonitoringReport] w INNER JOIN latest_snapshot s ON w.[Week_Number] = s.snapshot_date UNION ALL SELECT 'Commissioning' AS [KPI], AVG(TRY_CAST(w.[overall_comm_progress_100] AS FLOAT)) * 100 AS [Avg Value %], SUM(CASE WHEN TRY_CAST(w.[overall_comm_progress_100] AS FLOAT) < 0.50 THEN 1 ELSE 0 END) AS [Violating Wells], COUNT(DISTINCT w.[pdo_well_id]) AS [Total Wells] FROM [WellMonitoringReport] w INNER JOIN latest_snapshot s ON w.[Week_Number] = s.snapshot_date) SELECT [KPI], CAST([Avg Value %] AS DECIMAL(10,2)) AS [Avg Value %], [Violating Wells], CAST(([Violating Wells] * 100.0) / NULLIF([Total Wells], 0) AS DECIMAL(10,2)) AS [Violating Wells %] FROM kpi_metrics WHERE [Avg Value %] IS NOT NULL ORDER BY [Violating Wells %] DESC, [Avg Value %] ASC;",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="What are the top 10 risks impacting delivery? Use operational delivery risk proxy by project category.",
        query_type="ranking",
        neo4j_schema_context="""TABLE: WellMonitoringReport
  - Column [Week_Number] (date): Latest snapshot date.
  - Column [pdo_well_id] (nvarchar): Well identifier.
  - Column [over_all_progress_percentages] (decimal): Overall progress ratio.
  - Column [overall_engg._10_100] (decimal): Engineering progress ratio.
  - Column [overall_const._10_100] (decimal): Construction progress ratio.
  - Column [overall_material_10_100] (decimal): Material progress ratio.
  - Column [flowline_construction_progress] (decimal): Flowline progress ratio.
  - Column [overall_ohl_progr_100] (decimal): OHL progress ratio.
  - Column [exp.rig_off_location_sap_data] (date): Expected rig-off date.
  - Column [actual_rig_off_date] (date): Actual rig-off date.
  - Column [buffer_status] (nvarchar): Operational status.

TABLE: Job_Progress_Report_GB
  - Column [Well ID] (nvarchar): Well identifier.
  - Column [Category] (nvarchar): Project category.

NOTE:
  - User explicitly accepted an operational delivery-risk proxy.
  - Rank project categories by aggregated delivery-risk score from the latest snapshot.""",
        sql_query="WITH latest_snapshot AS (SELECT MAX([Week_Number]) AS snapshot_date FROM [WellMonitoringReport]), latest_wmr AS (SELECT TRY_CONVERT(nvarchar(50), w.[pdo_well_id]) AS [well_id], TRY_CAST(w.[over_all_progress_percentages] AS FLOAT) AS [overall_progress], TRY_CAST(w.[overall_engg._10_100] AS FLOAT) AS [engg_progress], TRY_CAST(w.[overall_const._10_100] AS FLOAT) AS [const_progress], TRY_CAST(w.[overall_material_10_100] AS FLOAT) AS [material_progress], TRY_CAST(w.[flowline_construction_progress] AS FLOAT) AS [flowline_progress], TRY_CAST(w.[overall_ohl_progr_100] AS FLOAT) AS [ohl_progress], TRY_CAST(w.[exp.rig_off_location_sap_data] AS DATE) AS [expected_rig_off], w.[actual_rig_off_date], w.[buffer_status] FROM [WellMonitoringReport] w INNER JOIN latest_snapshot s ON w.[Week_Number] = s.snapshot_date), category_by_well AS (SELECT TRY_CONVERT(nvarchar(50), j.[Well ID]) AS [well_id], MAX(j.[Category]) AS [Category] FROM [Job_Progress_Report_GB] j WHERE j.[Category] IS NOT NULL GROUP BY TRY_CONVERT(nvarchar(50), j.[Well ID])), scored_wells AS (SELECT c.[Category], w.[well_id], w.[overall_progress], CASE WHEN w.[expected_rig_off] < CAST(GETDATE() AS DATE) AND w.[actual_rig_off_date] IS NULL THEN 4 ELSE 0 END + CASE WHEN w.[overall_progress] < 0.30 THEN 3 WHEN w.[overall_progress] < 0.60 THEN 1 ELSE 0 END + CASE WHEN w.[engg_progress] < 0.50 THEN 1 ELSE 0 END + CASE WHEN w.[const_progress] < 0.50 THEN 1 ELSE 0 END + CASE WHEN w.[material_progress] < 0.50 THEN 1 ELSE 0 END + CASE WHEN w.[flowline_progress] < 0.50 THEN 1 ELSE 0 END + CASE WHEN w.[ohl_progress] < 0.50 THEN 1 ELSE 0 END + CASE WHEN w.[buffer_status] = 'ROL' AND w.[overall_progress] < 0.60 THEN 1 ELSE 0 END AS [risk_score], CASE WHEN w.[expected_rig_off] < CAST(GETDATE() AS DATE) AND w.[actual_rig_off_date] IS NULL THEN 1 ELSE 0 END AS [overdue_rig_off_flag] FROM latest_wmr w INNER JOIN category_by_well c ON c.[well_id] = w.[well_id]) SELECT TOP 10 [Category] AS [Project], COUNT(DISTINCT [well_id]) AS [Wells], CAST(AVG([overall_progress]) * 100 AS DECIMAL(10,2)) AS [Avg Progress %], CAST(AVG(CAST([risk_score] AS FLOAT)) AS DECIMAL(10,2)) AS [Avg Delivery Risk Score], SUM(CASE WHEN [risk_score] >= 6 THEN 1 ELSE 0 END) AS [High-Risk Wells], SUM([overdue_rig_off_flag]) AS [Overdue Rig-Off Wells] FROM scored_wells GROUP BY [Category] ORDER BY [Avg Delivery Risk Score] DESC, [High-Risk Wells] DESC, [Project];",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="Which milestones are overdue this week? Use schedule milestones/tasks from ActivityTaskPlan.",
        query_type="ranking",
        neo4j_schema_context="""TABLE: ActivityTaskPlan
  - Column [Well_ID] (nvarchar): Well identifier.
  - Column [project_id] (nvarchar): Project identifier.
  - Column [text] (nvarchar): Task or milestone name.
  - Column [target_end] (datetime2): Planned finish date.
  - Column [actual_end] (datetime2): Actual finish date.
  - Column [progress] (nvarchar): Task progress - cast when needed.

TABLE: WellMonitoringReport
  - Column [pdo_well_id] (nvarchar): Well identifier for join.
  - Column [well_name_after_spud] (nvarchar): Display well name.

NOTE:
  - User has clarified they want schedule milestones/tasks, not high-level rig milestones.
  - Use the current Monday-Sunday week window.
  - "Overdue this week" means target_end falls within this week, target_end is before today, and actual_end is missing or later than target_end.""",
        sql_query="WITH week_bounds AS (SELECT CAST(DATEADD(DAY, -(DATEDIFF(DAY, '19000101', CAST(GETDATE() AS DATE)) % 7), CAST(GETDATE() AS DATE)) AS DATE) AS week_start, CAST(DATEADD(DAY, 6 - (DATEDIFF(DAY, '19000101', CAST(GETDATE() AS DATE)) % 7), CAST(GETDATE() AS DATE)) AS DATE) AS week_end), well_lookup AS (SELECT TRY_CONVERT(nvarchar(50), w.[pdo_well_id]) AS [well_id], MAX(w.[well_name_after_spud]) AS [well_name_after_spud] FROM [WellMonitoringReport] w GROUP BY TRY_CONVERT(nvarchar(50), w.[pdo_well_id])) SELECT a.[Well_ID], wl.[well_name_after_spud] AS [Well Name], a.[project_id], a.[text] AS [Milestone], CAST(a.[target_end] AS DATE) AS [Due Date], CAST(a.[actual_end] AS DATE) AS [Actual End Date], TRY_CAST(a.[progress] AS DECIMAL(10,4)) AS [Progress] FROM [ActivityTaskPlan] a CROSS JOIN week_bounds wb LEFT JOIN well_lookup wl ON wl.[well_id] = TRY_CONVERT(nvarchar(50), a.[Well_ID]) WHERE a.[target_end] IS NOT NULL AND CAST(a.[target_end] AS DATE) >= wb.[week_start] AND CAST(a.[target_end] AS DATE) <= wb.[week_end] AND CAST(a.[target_end] AS DATE) < CAST(GETDATE() AS DATE) AND (a.[actual_end] IS NULL OR CAST(a.[actual_end] AS DATE) > CAST(a.[target_end] AS DATE)) AND NULLIF(LTRIM(RTRIM(a.[text])), '') IS NOT NULL ORDER BY CAST(a.[target_end] AS DATE), wl.[well_name_after_spud], a.[text];",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="What is the current profit margin per project? Use rig code and use planned vs actual purpose value as a proxy.",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: Revenue
  - Column [rigcode] (nvarchar): Project/rig code.
  - Column [actual_purpose_value] (decimal): Actual value achieved.
  - Column [planned_purpose_value] (nvarchar): Planned value - MUST CAST to DECIMAL before aggregation.
  NOTE:
  - User has accepted planned vs actual purpose value as a proxy instead of true cost.
  - Return revenue variance / achievement-rate logic grouped by rigcode.""",
        sql_query="SELECT r.[rigcode] AS [Project], SUM(r.[actual_purpose_value]) AS [Actual_Revenue], SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) AS [Planned_Revenue], CASE WHEN SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) = 0 THEN NULL ELSE ((SUM(r.[actual_purpose_value]) - SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2)))) * 100.0) / SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) END AS [Revenue_Variance_Pct], CASE WHEN SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) = 0 THEN NULL ELSE SUM(r.[actual_purpose_value]) / SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) END AS [Achievement_Rate] FROM [Revenue] r WHERE r.[created_at] >= DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1) AND TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2)) IS NOT NULL GROUP BY r.[rigcode] ORDER BY [Revenue_Variance_Pct] DESC;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="What is the current profit margin per project? Use category and use planned vs actual purpose value as a proxy.",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: Revenue
  - Column [well_id] (nvarchar): Join key to WellMonitoringReport.pdo_well_id.
  - Column [actual_purpose_value] (decimal): Actual value achieved.
  - Column [planned_purpose_value] (nvarchar): Planned value - MUST CAST to DECIMAL before aggregation.

TABLE: Job_Progress_Report_GB
  - Column [Well ID] (nvarchar): Well identifier.
  - Column [Category] (nvarchar): Project category.

NOTE:
  - User has accepted planned vs actual purpose value as a proxy instead of true cost.
  - Aggregate at category grain.""",
        sql_query="WITH revenue_by_well AS (SELECT TRY_CONVERT(nvarchar(50), r.[well_id]) AS [well_id], SUM(r.[actual_purpose_value]) AS [actual_revenue], SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) AS [planned_revenue] FROM [Revenue] r WHERE r.[created_at] >= DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1) AND TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2)) IS NOT NULL GROUP BY TRY_CONVERT(nvarchar(50), r.[well_id])), category_by_well AS (SELECT TRY_CONVERT(nvarchar(50), j.[Well ID]) AS [well_id], MAX(j.[Category]) AS [Category] FROM [Job_Progress_Report_GB] j WHERE j.[Category] IS NOT NULL GROUP BY TRY_CONVERT(nvarchar(50), j.[Well ID])) SELECT c.[Category], SUM(r.[actual_revenue]) AS [Actual_Revenue], SUM(r.[planned_revenue]) AS [Planned_Revenue], CASE WHEN SUM(r.[planned_revenue]) = 0 THEN NULL ELSE ((SUM(r.[actual_revenue]) - SUM(r.[planned_revenue])) * 100.0) / SUM(r.[planned_revenue]) END AS [Revenue_Variance_Pct], CASE WHEN SUM(r.[planned_revenue]) = 0 THEN NULL ELSE SUM(r.[actual_revenue]) / SUM(r.[planned_revenue]) END AS [Achievement_Rate] FROM revenue_by_well r INNER JOIN category_by_well c ON c.[well_id] = r.[well_id] GROUP BY c.[Category] ORDER BY [Revenue_Variance_Pct] DESC;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="What is the current profit margin per project? Use individual project name and use planned vs actual purpose value as a proxy.",
        query_type="multi_table_join",
        neo4j_schema_context="""TABLE: Revenue
  - Column [well_id] (nvarchar): Join key to WellMonitoringReport.pdo_well_id.
  - Column [actual_purpose_value] (decimal): Actual value achieved.
  - Column [planned_purpose_value] (nvarchar): Planned value - MUST CAST to DECIMAL before aggregation.

TABLE: WellMonitoringReport
  - Column [pdo_well_id] (nvarchar): Well identifier.
  - Column [well_name_after_spud] (nvarchar): Individual well / project display name.

NOTE:
  - User has accepted planned vs actual purpose value as a proxy instead of true cost.
  - Aggregate at well/project-name grain.""",
        sql_query="WITH revenue_by_well AS (SELECT TRY_CONVERT(nvarchar(50), r.[well_id]) AS [well_id], SUM(r.[actual_purpose_value]) AS [actual_revenue], SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) AS [planned_revenue] FROM [Revenue] r WHERE r.[created_at] >= DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1) AND TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2)) IS NOT NULL GROUP BY TRY_CONVERT(nvarchar(50), r.[well_id])) SELECT w.[pdo_well_id], w.[well_name_after_spud] AS [Project_Name], SUM(r.[actual_revenue]) AS [Actual_Revenue], SUM(r.[planned_revenue]) AS [Planned_Revenue], CASE WHEN SUM(r.[planned_revenue]) = 0 THEN NULL ELSE ((SUM(r.[actual_revenue]) - SUM(r.[planned_revenue])) * 100.0) / SUM(r.[planned_revenue]) END AS [Revenue_Variance_Pct], CASE WHEN SUM(r.[planned_revenue]) = 0 THEN NULL ELSE SUM(r.[actual_revenue]) / SUM(r.[planned_revenue]) END AS [Achievement_Rate] FROM revenue_by_well r INNER JOIN [WellMonitoringReport] w ON w.[pdo_well_id] = r.[well_id] GROUP BY w.[pdo_well_id], w.[well_name_after_spud] ORDER BY [Revenue_Variance_Pct] DESC;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="What is labor productivity trend?",
        query_type="trend",
        neo4j_schema_context="""TABLE: PH_PRODUCTIVITY_WEEKLY_REPORT
  - Column [MonthStart] (date): Reporting month.
  - Column [Average Productivity (%)] (decimal): Productivity percentage.
  NOTE:
  - Filter extreme outliers and negatives by keeping only values between 0 and 200 for trend reporting.""",
        sql_query="WITH recent_months AS (SELECT TOP 12 [MonthStart], AVG(TRY_CAST([Average Productivity (%)] AS FLOAT)) AS [avg_productivity_pct], COUNT(*) AS [crew_records] FROM [PH_PRODUCTIVITY_WEEKLY_REPORT] WHERE TRY_CAST([Average Productivity (%)] AS FLOAT) BETWEEN 0 AND 200 GROUP BY [MonthStart] ORDER BY [MonthStart] DESC) SELECT [MonthStart], CAST([avg_productivity_pct] AS DECIMAL(10,2)) AS [Average Productivity %], [crew_records] AS [Crew Records] FROM recent_months ORDER BY [MonthStart];",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="Which crews are most efficient?",
        query_type="ranking",
        neo4j_schema_context="""TABLE: PH_PRODUCTIVITY_WEEKLY_REPORT
  - Column [MonthStart] (date): Reporting month.
  - Column [Crew Name] (nvarchar): Crew name.
  - Column [Crew Type] (nvarchar): Crew type.
  - Column [Average Productivity (%)] (decimal): Productivity percentage.
  NOTE:
  - Use the latest reporting month with valid productivity and filter to 0-200 to avoid outliers.""",
        sql_query="WITH latest_month AS (SELECT MAX([MonthStart]) AS [month_start] FROM [PH_PRODUCTIVITY_WEEKLY_REPORT] WHERE TRY_CAST([Average Productivity (%)] AS FLOAT) BETWEEN 0 AND 200) SELECT TOP 15 p.[MonthStart], p.[Crew Name], p.[Crew Type], CAST(AVG(TRY_CAST(p.[Average Productivity (%)] AS FLOAT)) AS DECIMAL(10,2)) AS [Average Productivity %], COUNT(*) AS [Observation Rows] FROM [PH_PRODUCTIVITY_WEEKLY_REPORT] p INNER JOIN latest_month lm ON p.[MonthStart] = lm.[month_start] WHERE TRY_CAST(p.[Average Productivity (%)] AS FLOAT) BETWEEN 0 AND 200 AND LEN(ISNULL(p.[Crew Name], '')) < 120 GROUP BY p.[MonthStart], p.[Crew Name], p.[Crew Type] HAVING COUNT(*) >= 2 ORDER BY [Average Productivity %] DESC, [Observation Rows] DESC, p.[Crew Name];",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="What is workforce allocation across projects?",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: ActivityTaskPlan
  - Column [project_id] (nvarchar): Project identifier.
  - Column [progress] (nvarchar): Task progress ratio.
  - Column [manhoursactual] (nvarchar): Actual manhours booked.
  - Column [manhourforacst] (nvarchar): Forecast manhours.

TABLE: ProjectIDs
  - Column [ID] (nvarchar): Project ID join key.
  - Column [column2] (nvarchar): Project category / business project name.

NOTE:
  - Use incomplete tasks and return actual vs forecast manhours allocation as the workforce proxy.""",
        sql_query="WITH active_task_manhours AS (SELECT p.[column2] AS [Project Category], COUNT(*) AS [Active Task Rows], SUM(COALESCE(TRY_CAST(a.[manhoursactual] AS FLOAT), 0)) AS [Actual Manhours], SUM(COALESCE(TRY_CAST(a.[manhourforacst] AS FLOAT), 0)) AS [Forecast Manhours], AVG(COALESCE(TRY_CAST(a.[progress] AS FLOAT), 0)) * 100 AS [Avg Progress %] FROM [ActivityTaskPlan] a INNER JOIN [ProjectIDs] p ON LOWER(CONVERT(nvarchar(36), p.[ID])) = LOWER(CONVERT(nvarchar(36), a.[project_id])) WHERE TRY_CAST(a.[progress] AS FLOAT) < 1 GROUP BY p.[column2]) SELECT [Project Category], [Active Task Rows], CAST([Actual Manhours] AS DECIMAL(18,2)) AS [Actual Manhours], CAST([Forecast Manhours] AS DECIMAL(18,2)) AS [Forecast Manhours], CAST([Avg Progress %] AS DECIMAL(10,2)) AS [Avg Progress %] FROM active_task_manhours WHERE [Actual Manhours] > 0 OR [Forecast Manhours] > 0 ORDER BY [Forecast Manhours] DESC, [Project Category];",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="What is the forecast manpower requirement? Use ActivityTaskPlan manhourforacst as a proxy. Use category for the current open workload.",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: ActivityTaskPlan
  - Column [project_id] (nvarchar): Project identifier.
  - Column [progress] (nvarchar): Task progress ratio.
  - Column [manhourforacst] (nvarchar): Forecast manhours.

TABLE: ProjectIDs
  - Column [ID] (nvarchar): Project ID join key.
  - Column [column2] (nvarchar): Project category / business project name.

NOTE:
  - User has accepted manhourforacst as the forecast manpower proxy for the current open workload.""",
        sql_query="SELECT p.[column2] AS [Project Category], COUNT(*) AS [Open Task Rows], CAST(SUM(COALESCE(TRY_CAST(a.[manhourforacst] AS FLOAT), 0)) AS DECIMAL(18,2)) AS [Forecast Manhours Required], CAST(AVG(COALESCE(TRY_CAST(a.[progress] AS FLOAT), 0)) * 100 AS DECIMAL(10,2)) AS [Avg Open-Task Progress %] FROM [ActivityTaskPlan] a INNER JOIN [ProjectIDs] p ON LOWER(CONVERT(nvarchar(36), p.[ID])) = LOWER(CONVERT(nvarchar(36), a.[project_id])) WHERE TRY_CAST(a.[progress] AS FLOAT) < 1 GROUP BY p.[column2] HAVING SUM(COALESCE(TRY_CAST(a.[manhourforacst] AS FLOAT), 0)) > 0 ORDER BY [Forecast Manhours Required] DESC, [Project Category];",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="Which skills are in shortage? Use incomplete ActivityTaskPlan crew_type demand as a proxy for shortage.",
        query_type="ranking",
        neo4j_schema_context="""TABLE: ActivityTaskPlan
  - Column [crew_type] (nvarchar): Crew type / skill proxy.
  - Column [progress] (nvarchar): Task progress ratio.
  - Column [manhourforacst] (nvarchar): Forecast manhours.

NOTE:
  - The user has accepted crew_type demand on incomplete tasks as a proxy for skill shortage.""",
        sql_query="SELECT TOP 15 a.[crew_type] AS [Crew Type / Skill Proxy], COUNT(*) AS [Open Task Rows], CAST(SUM(COALESCE(TRY_CAST(a.[manhourforacst] AS FLOAT), 0)) AS DECIMAL(18,2)) AS [Forecast Manhours Required], CAST(AVG(COALESCE(TRY_CAST(a.[progress] AS FLOAT), 0)) * 100 AS DECIMAL(10,2)) AS [Avg Progress %] FROM [ActivityTaskPlan] a WHERE NULLIF(LTRIM(RTRIM(a.[crew_type])), '') IS NOT NULL AND TRY_CAST(a.[progress] AS FLOAT) < 1 GROUP BY a.[crew_type] HAVING SUM(COALESCE(TRY_CAST(a.[manhourforacst] AS FLOAT), 0)) > 0 ORDER BY [Forecast Manhours Required] DESC, [Open Task Rows] DESC, a.[crew_type];",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    dspy.Example(
        user_question="What is subcontractor manpower status? Use the latest PH productivity month as a crew-count and productivity proxy.",
        query_type="aggregation",
        neo4j_schema_context="""TABLE: PH_PRODUCTIVITY_WEEKLY_REPORT
  - Column [MonthStart] (date): Reporting month.
  - Column [ATNM/Sub Contractor] (varchar): Workforce ownership bucket.
  - Column [Crew Name] (nvarchar): Crew name.
  - Column [Crew Type] (nvarchar): Crew type.
  - Column [Crew Discipline] (nvarchar): Crew discipline.
  - Column [Average Productivity (%)] (decimal): Productivity percentage.

NOTE:
  - The user has accepted latest-month crew-count and productivity as a proxy for subcontractor manpower status.""",
        sql_query="WITH latest_month AS (SELECT MAX([MonthStart]) AS [month_start] FROM [PH_PRODUCTIVITY_WEEKLY_REPORT] WHERE TRY_CAST([Average Productivity (%)] AS FLOAT) BETWEEN 0 AND 200) SELECT p.[MonthStart], p.[ATNM/Sub Contractor] AS [Workforce Type], COUNT(DISTINCT CONCAT(ISNULL(p.[Crew Name], ''), '|', ISNULL(p.[Crew Type], ''))) AS [Distinct Crew Groups], COUNT(DISTINCT p.[Crew Discipline]) AS [Crew Disciplines], CAST(AVG(TRY_CAST(p.[Average Productivity (%)] AS FLOAT)) AS DECIMAL(10,2)) AS [Average Productivity %] FROM [PH_PRODUCTIVITY_WEEKLY_REPORT] p INNER JOIN latest_month lm ON p.[MonthStart] = lm.[month_start] WHERE TRY_CAST(p.[Average Productivity (%)] AS FLOAT) BETWEEN 0 AND 200 GROUP BY p.[MonthStart], p.[ATNM/Sub Contractor] ORDER BY [Distinct Crew Groups] DESC, [Average Productivity %] DESC;",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),
]

# Merge client 100-question training set
try:
    from agents.client_100_questions import CLIENT_100_EXAMPLES
    TRAINING_EXAMPLES.extend(CLIENT_100_EXAMPLES)
    log.info(f"✓ Loaded {len(CLIENT_100_EXAMPLES)} client training examples (total: {len(TRAINING_EXAMPLES)})")
except ImportError:
    pass  # client_100_questions.py not deployed: ignore gracefully


# ── Security Metric ─────────────────────────────────────────────────────

FORBIDDEN_KEYWORDS = [
    'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'TRUNCATE',
    'EXEC', 'EXECUTE', 'CREATE', 'GRANT', 'REVOKE', 'DENY',
    'MERGE', 'BULK', 'OPENROWSET', 'xp_', 'sp_',
]

FORBIDDEN_PATTERNS = []


def security_metric(example, pred, trace=None) -> bool:
    """Reject unsafe queries during DSPy compilation."""
    sql = pred.sql_query.strip()

    # Allow INSUFFICIENT_SCHEMA
    if sql == "INSUFFICIENT_SCHEMA":
        return True

    sql_upper = sql.upper()

    # Must start with SELECT or WITH
    if not (sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')):
        return False

    # Forbidden keywords
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf'\b{kw}\b', sql_upper):
            return False

    # Forbidden patterns
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in sql:
            return False

    return True


# ── SQL Agent ────────────────────────────────────────────────────────────

class SQLAgent(dspy.Module):
    """DSPy-based SQL generation with anti-hallucination constraints."""

    def __init__(self, compile_on_init: bool = True):
        super().__init__()
        self.generate = dspy.ChainOfThought(SQLSignature)

        if compile_on_init:
            self._compile()

    def _compile(self) -> None:
        """Manually inject training examples to avoid compilation rate limits."""
        log.info("Injecting %d training examples into SQL Agent (Manual Few-Shot)",
                 len(TRAINING_EXAMPLES))
        # Zero-shot default, but we can pre-load demos to the module
        self.generate.demos = TRAINING_EXAMPLES
        log.info("   ✓ Demos injected")

    def forward(self, neo4j_schema_context: str, user_question: str,
                query_type: str = "single_table") -> SQLResult:
        """Generate SQL from schema context and user question."""
        if _is_portfolio_status_question(user_question):
            return SQLResult(
                sql_query=_portfolio_status_sql(),
                confidence=0.99,
                reasoning=(
                    "Detected executive portfolio-status intent. "
                    "Using the latest portfolio-wide WellMonitoringReport snapshot, "
                    "counting wells by pdo_well_id and returning KPI summary fields only."
                ),
                is_insufficient=False,
            )

        if _is_current_quarter_revenue_forecast_question(user_question):
            return SQLResult(
                sql_query=_current_quarter_revenue_forecast_sql(),
                confidence=0.99,
                reasoning=(
                    "Detected current-quarter revenue forecast intent. "
                    "Using Revenue quarter-to-date actual_purpose_value with a run-rate projection "
                    "to quarter end, and comparing it against full-quarter planned_purpose_value."
                ),
                is_insufficient=False,
            )

        if _is_annual_target_status_question(user_question):
            return SQLResult(
                sql_query=_annual_target_status_sql(),
                confidence=0.99,
                reasoning=(
                    "Detected annual-target status intent. "
                    "Using current-year Revenue actual_purpose_value year-to-date, projecting to year end by run rate, "
                    "and comparing the projection against current-year planned_purpose_value."
                ),
                is_insufficient=False,
            )

        if _is_major_constraints_progress_question(user_question):
            return SQLResult(
                sql_query=_major_constraints_progress_sql(),
                confidence=0.99,
                reasoning=(
                    "Detected major-constraints-affecting-progress intent. "
                    "Using latest-snapshot measurable bottlenecks from WellMonitoringReport phase progress fields "
                    "instead of weak historical reason-text columns."
                ),
                is_insufficient=False,
            )

        if _is_performance_kpi_trend_question(user_question):
            return SQLResult(
                sql_query=_performance_kpi_trend_sql(),
                confidence=0.99,
                reasoning=(
                    "Detected performance-KPI trend-analysis intent. "
                    "Using WMR_Full historical weekly snapshots to return portfolio KPI trends over the latest 12 weeks."
                ),
                is_insufficient=False,
            )

        if _is_kpi_threshold_deviation_question(user_question) and _uses_kpi_threshold_proxy(user_question):
            return SQLResult(
                sql_query=_kpi_threshold_deviation_proxy_sql(),
                confidence=0.99,
                reasoning=(
                    "Detected clarified KPI-threshold deviation intent. "
                    "Using the latest operational snapshot and flagging major phase KPIs below 50% progress "
                    "as proxy threshold deviations."
                ),
                is_insufficient=False,
            )

        if _is_delivery_risk_question(user_question) and _uses_operational_delivery_risk_proxy(user_question):
            return SQLResult(
                sql_query=_delivery_risk_proxy_category_sql(),
                confidence=0.99,
                reasoning=(
                    "Detected clarified delivery-risk intent. "
                    "Using the latest WellMonitoringReport snapshot and Job_Progress_Report_GB category mapping "
                    "to rank project categories by an operational delivery-risk proxy."
                ),
                is_insufficient=False,
            )

        if _is_labor_productivity_trend_question(user_question):
            return SQLResult(
                sql_query=_labor_productivity_trend_sql(),
                confidence=0.99,
                reasoning=(
                    "Detected labor-productivity trend intent. "
                    "Using PH_PRODUCTIVITY_WEEKLY_REPORT monthly averages with defensible outlier filtering "
                    "to return the trend of reported productivity over time."
                ),
                is_insufficient=False,
            )

        if _is_most_efficient_crews_question(user_question):
            return SQLResult(
                sql_query=_most_efficient_crews_sql(),
                confidence=0.99,
                reasoning=(
                    "Detected crew-efficiency ranking intent. "
                    "Using the latest valid PH productivity month, filtering extreme outliers, "
                    "and ranking crew groups by average productivity with observation counts."
                ),
                is_insufficient=False,
            )

        if _is_workforce_allocation_question(user_question):
            return SQLResult(
                sql_query=_workforce_allocation_sql(),
                confidence=0.99,
                reasoning=(
                    "Detected workforce-allocation intent. "
                    "The current schema lacks a clean live headcount allocation fact, so this uses incomplete "
                    "ActivityTaskPlan tasks to return actual vs forecast manhours allocation by project category."
                ),
                is_insufficient=False,
            )

        if _is_cost_budget_question(user_question) and _uses_revenue_budget_proxy(user_question):
            grain = _extract_cost_budget_grain(user_question)
            window = _extract_cost_budget_window(user_question)
            include_context = ("why" in _normalize_question(user_question)) or _uses_operational_context_proxy(user_question)
            top_only = _is_top_cost_overrun_question(user_question)

            if grain == "well" and window:
                return SQLResult(
                    sql_query=_cost_vs_budget_well_sql(window, include_context=include_context),
                    confidence=0.99,
                    reasoning=(
                        "Detected clarified cost/budget proxy intent at well grain. "
                        "Aggregating Revenue by well within the requested time window before ranking, "
                        "and attaching latest operational context only as a proxy explanation when requested."
                    ),
                    is_insufficient=False,
                )

            if grain == "project_code" and window:
                return SQLResult(
                    sql_query=_cost_vs_budget_project_code_sql(window, top_only=top_only, include_context=include_context),
                    confidence=0.99,
                    reasoning=(
                        "Detected clarified cost/budget proxy intent at project-code grain. "
                        "Aggregating Revenue by project code within the requested time window and excluding zero-plan groups from validated overrun ranking."
                    ),
                    is_insufficient=False,
                )

            if grain == "category" and window:
                return SQLResult(
                    sql_query=_cost_vs_budget_category_sql(window, top_only=top_only, include_context=include_context),
                    confidence=0.99,
                    reasoning=(
                        "Detected clarified cost/budget proxy intent at category grain. "
                        "Aggregating Revenue by well first, mapping wells to Job_Progress_Report_GB category, and then calculating proxy budget variance by category."
                    ),
                    is_insufficient=False,
                )

        if _is_forecast_manpower_requirement_question(user_question) and _uses_manhour_forecast_proxy(user_question):
            grain = _extract_manpower_requirement_grain(user_question)
            if grain == "category":
                return SQLResult(
                    sql_query=_forecast_manpower_requirement_category_sql(),
                    confidence=0.99,
                    reasoning=(
                        "Detected clarified manpower-forecast intent at project-category grain. "
                        "Using ActivityTaskPlan manhourforacst on incomplete tasks as the forecast manpower proxy "
                        "for the current open workload."
                    ),
                    is_insufficient=False,
                )
            if grain == "well":
                return SQLResult(
                    sql_query=_forecast_manpower_requirement_well_sql(),
                    confidence=0.99,
                    reasoning=(
                        "Detected clarified manpower-forecast intent at well grain. "
                        "Using ActivityTaskPlan manhourforacst on incomplete tasks as the forecast manpower proxy "
                        "for the current open workload."
                    ),
                    is_insufficient=False,
                )

        if _is_skills_shortage_question(user_question) and _uses_skills_shortage_proxy(user_question):
            return SQLResult(
                sql_query=_skills_shortage_proxy_sql(),
                confidence=0.99,
                reasoning=(
                    "Detected clarified skills-shortage proxy intent. "
                    "Using incomplete ActivityTaskPlan crew_type demand ranked by forecast manhours as a proxy "
                    "for where skill demand is heaviest."
                ),
                is_insufficient=False,
            )

        if _is_subcontractor_manpower_status_question(user_question) and _uses_subcontractor_manpower_proxy(user_question):
            return SQLResult(
                sql_query=_subcontractor_manpower_status_proxy_sql(),
                confidence=0.99,
                reasoning=(
                    "Detected clarified subcontractor-manpower proxy intent. "
                    "Using the latest valid PH productivity month to summarize ATNM vs Sub contractor workforce coverage "
                    "through crew-group counts, discipline counts, and average productivity."
                ),
                is_insufficient=False,
            )

        if _is_weekly_overdue_milestones_question(user_question) and _uses_activity_taskplan_scope(user_question):
            return SQLResult(
                sql_query=_weekly_overdue_activity_tasks_sql(),
                confidence=0.99,
                reasoning=(
                    "Detected overdue-this-week milestones intent with ActivityTaskPlan scope. "
                    "Using ActivityTaskPlan target_end and actual_end within the current Monday-Sunday week window, "
                    "and returning overdue schedule milestones/tasks rather than inferring a single rig milestone from WellMonitoringReport."
                ),
                is_insufficient=False,
            )

        try:
            pred = self.generate(
                neo4j_schema_context=neo4j_schema_context,
                user_question=user_question,
                query_type=query_type,
            )
        except Exception as e:
            log.error(f"   ! SQL Generation Engine Failure: {e}")
            return SQLResult(
                sql_query="",
                confidence=0.0,
                reasoning=f"Critical Generator Error: {str(e)}",
                is_insufficient=True
            )

        sql = pred.sql_query.strip()

        # Parse confidence
        try:
            confidence = float(pred.confidence)
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 0.5

        # Check for insufficient schema
        is_insufficient = "INSUFFICIENT_SCHEMA" in sql.upper()

        # Clean up any accidental markdown wrapping
        if sql.startswith("```"):
            lines = sql.split("\n")
            sql = "\n".join(
                l for l in lines if not l.startswith("```")
            ).strip()

        reasoning = getattr(pred, 'rationale',
                           getattr(pred, 'reasoning', ''))

        return SQLResult(
            sql_query=sql,
            confidence=confidence,
            reasoning=reasoning,
            is_insufficient=is_insufficient,
        )

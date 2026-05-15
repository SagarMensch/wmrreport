"""
100-Question Training Set for the Bashira SQL Agent
====================================================
Categorized by domain. Each entry maps a natural language question
to the correct response strategy:
  - sql_only questions get a direct SQL example
  - questions where data doesn't exist in the schema get INSUFFICIENT_SCHEMA
  - predictive questions get flagged (handled by question_classifier, not SQL agent)

These examples are appended to TRAINING_EXAMPLES in sql_agent.py.
"""

import dspy

# Schema context templates (reused across examples)
_WMR_CONTEXT = """TABLE: WellMonitoringReport
  - Column [pdo_well_id] (nvarchar): Unique well identifier.
  - Column [well_name_after_spud] (nvarchar): Official well name.
  - Column [Cluster] (nvarchar): Nimr or Marmul.
  - Column [rig_no] (nvarchar): Rig identifier.
  - Column [well_type] (nvarchar): ESP, OP, WI.
  - Column [over_all_progress_percentages] (decimal): Overall progress 0-1 scale.
  - Column [Week_Number] (date): Snapshot week.
  - Column [moc_raised] (nvarchar): YES/No.
  - Column [buffer_status] (nvarchar): drilled/ROL/Buffer1/Buffer2.
  - Column [actual_rig_on_date] (date): Rig arrival.
  - Column [actual_rig_off_date] (date): Rig departure.
  - Column [exp.rig_off_location_sap_data] (date): Expected rig-off.
  - Column [overall_loc._preparation_10_100] (decimal): Loc prep progress.
  - Column [overall_engg._10_100] (decimal): Engineering progress.
  - Column [overall_const._10_100] (decimal): Construction progress.
  - Column [overall_comm_progress_100] (decimal): Commissioning progress.
  - Column [engg_kpi_after_rig-off_days] (int): Engg KPI days."""

_JPR_CONTEXT = """TABLE: Job_Progress_Report_GB
  - Column [Well ID] (nvarchar): Well identifier.
  - Column [Well Name / Project Name] (nvarchar): Well name.
  - Column [Category] (nvarchar): Project category.
  - Column [Week-1 Plan %] (decimal), [Week-1 Actual %] (decimal).
  - Column [Week-2 Plan %] (decimal), [Week-2 Actual %] (decimal).
  - Column [Current Month Plan %] (decimal), [Current Month Actual %] (decimal).
  - Column [Cum-Current Month Plan %] (decimal), [Cum-Current Month Actual %] (decimal).
  - Column [Purpose Value] (decimal): Monetary value.
  - Column [Target End] (date)."""

_REV_CONTEXT = """TABLE: Revenue
  - Column [well_id] (nvarchar): Well identifier.
  - Column [rigcode] (nvarchar): Rig code (NL0010, NF0010, etc).
  - Column [actual_purpose_value] (decimal): Actual revenue.
  - Column [planned_purpose_value] (nvarchar): Planned revenue - MUST CAST to DECIMAL.
  - Column [created_at] (datetime2): Record timestamp."""

_TD_CONTEXT = """TABLE: task_daily
  - Column [well_id] (nvarchar): Well identifier.
  - Column [ActionOn] (date): Task date.
  - Column [completed] (bit): 0/1.
  - Column [target_start] (date), [target_end] (date).
  - Column [crew_code] (nvarchar): Crew code.
  - Column [data_hours] (decimal): Hours worked.
  - Column [data_qty] (decimal): Quantity done."""

_PH_CONTEXT = """TABLE: PH_PRODUCTIVITY_WEEKLY_REPORT
  - Column [PH Name] (nvarchar): Project Holder name.
  - Column [PA Name] (nvarchar): Permit Applicant.
  - Column [Average Productivity (%)] (decimal): Avg productivity.
  - Column [Crew Type] (nvarchar), [Crew Name] (nvarchar).
  - Column [Year] (int), [Month] (nvarchar)."""

_SAP_CONTEXT = """TABLE: SAP_DRILLING_SEQUENCE
  - Column [Well_ID] (varchar): Well identifier.
  - Column [Well_Name] (nvarchar): Well name.
  - Column [Field] (nvarchar): Oil field.
  - Column [Move_days] (tinyint): Rig move days.
  - Column [Opr_System_status] (nvarchar): Current status."""

_JC_CONTEXT = """TABLE: vw_JOB_COST
  - Column [Well ID] (nvarchar): Well identifier.
  - Column [Project] (nvarchar): Rig code.
  - Column [Effective Work Hours] (decimal): Hours worked.
  - Column [Plan Employee Name/ Equipment Name] (nvarchar).
  - Column [Actual Employee / Equipment Name] (nvarchar).
  - Column [Action On] (date): Task date."""

_DPR_CONTEXT = """TABLE: Daily_Plan_Report
  - Column [Well ID] (nvarchar): Well identifier.
  - Column [PA Name] (nvarchar): Permit Applicant.
  - Column [PH Name] (nvarchar): Project Holder.
  - Column [Activities] (nvarchar): Task description.
  - Column [Manpower] (nvarchar): Headcount.
  - Column [Eqpt] (nvarchar): Equipment."""


CLIENT_100_EXAMPLES = [
    # ============================================================
    # CATEGORY 1: PORTFOLIO STATUS (Q1-Q10)
    # ============================================================

    # Q1 — already has hardcoded handler, but add training example too
    dspy.Example(
        user_question="What is our overall project portfolio status today?",
        query_type="aggregation",
        neo4j_schema_context=_WMR_CONTEXT,
        sql_query="WITH latest_snapshot AS (SELECT MAX(Week_Number) AS snapshot_date FROM WellMonitoringReport), portfolio_base AS (SELECT w.pdo_well_id, w.Cluster, TRY_CAST(w.over_all_progress_percentages AS FLOAT) AS progress_ratio, TRY_CAST(w.[exp.rig_off_location_sap_data] AS DATE) AS expected_rig_off, w.actual_rig_off_date FROM WellMonitoringReport w INNER JOIN latest_snapshot s ON w.Week_Number = s.snapshot_date) SELECT (SELECT snapshot_date FROM latest_snapshot) AS snapshot_date, COUNT(DISTINCT pdo_well_id) AS total_wells, CAST(AVG(progress_ratio) * 100 AS DECIMAL(10,2)) AS avg_progress_pct, SUM(CASE WHEN progress_ratio >= 1 THEN 1 ELSE 0 END) AS complete_wells, SUM(CASE WHEN progress_ratio = 0 THEN 1 ELSE 0 END) AS not_started_wells, SUM(CASE WHEN progress_ratio > 0 AND progress_ratio < 1 THEN 1 ELSE 0 END) AS active_wells FROM portfolio_base;",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q3 — current profit margin per project
    dspy.Example(
        user_question="What is the current profit margin per project?",
        query_type="multi_table_join",
        neo4j_schema_context=_REV_CONTEXT + "\n\n" + _JPR_CONTEXT + "\n\nNOTE: User says 'project' — default to Category grain. Use planned vs actual purpose value as proxy.",
        sql_query="WITH revenue_by_well AS (SELECT TRY_CONVERT(nvarchar(50), r.[well_id]) AS [well_id], SUM(r.[actual_purpose_value]) AS [actual_revenue], SUM(TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2))) AS [planned_revenue] FROM [Revenue] r WHERE TRY_CAST(r.[planned_purpose_value] AS DECIMAL(18,2)) IS NOT NULL GROUP BY TRY_CONVERT(nvarchar(50), r.[well_id])), category_by_well AS (SELECT TRY_CONVERT(nvarchar(50), j.[Well ID]) AS [well_id], MAX(j.[Category]) AS [Category] FROM [Job_Progress_Report_GB] j WHERE j.[Category] IS NOT NULL GROUP BY TRY_CONVERT(nvarchar(50), j.[Well ID])) SELECT c.[Category] AS [Project], SUM(r.[actual_revenue]) AS [Actual_Revenue], SUM(r.[planned_revenue]) AS [Planned_Revenue], CASE WHEN SUM(r.[planned_revenue]) = 0 THEN NULL ELSE ((SUM(r.[actual_revenue]) - SUM(r.[planned_revenue])) * 100.0) / SUM(r.[planned_revenue]) END AS [Revenue_Variance_Pct] FROM revenue_by_well r INNER JOIN category_by_well c ON c.[well_id] = r.[well_id] GROUP BY c.[Category] ORDER BY [Revenue_Variance_Pct] DESC;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q4 — underperforming vs plan
    dspy.Example(
        user_question="Which projects are underperforming vs plan?",
        query_type="comparison",
        neo4j_schema_context=_JPR_CONTEXT,
        sql_query="SELECT [Well Name / Project Name], [Category], [Current Month Plan %], [Current Month Actual %], ([Current Month Actual %] - [Current Month Plan %]) AS Variance FROM Job_Progress_Report_GB WHERE [Current Month Actual %] < [Current Month Plan %] ORDER BY Variance ASC;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q8 — Which client contributes most revenue
    dspy.Example(
        user_question="Which client contributes the most revenue?",
        query_type="aggregation",
        neo4j_schema_context=_REV_CONTEXT + "\n\nNOTE: No 'client' column exists. Use rigcode as the closest proxy for project/client grouping.",
        sql_query="SELECT rigcode AS client_project, SUM(actual_purpose_value) AS total_actual_revenue FROM Revenue GROUP BY rigcode ORDER BY total_actual_revenue DESC;",
        confidence="0.90",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q9 — backlog value and duration
    dspy.Example(
        user_question="What is our backlog value and duration?",
        query_type="aggregation",
        neo4j_schema_context=_JPR_CONTEXT + "\n\n" + _WMR_CONTEXT,
        sql_query="SELECT COUNT(DISTINCT w.pdo_well_id) AS backlog_wells, SUM(j.[Purpose Value]) AS backlog_value, AVG(DATEDIFF(day, GETDATE(), j.[Target End])) AS avg_remaining_days FROM WellMonitoringReport w JOIN Job_Progress_Report_GB j ON w.pdo_well_id = j.[Well ID] WHERE TRY_CAST(w.over_all_progress_percentages AS FLOAT) < 1.0 AND j.[Target End] > GETDATE();",
        confidence="0.85",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q10 — most profitable regions
    dspy.Example(
        user_question="Which regions/assets are most profitable?",
        query_type="multi_table_join",
        neo4j_schema_context=_WMR_CONTEXT + "\n\n" + _REV_CONTEXT,
        sql_query="SELECT w.Cluster AS Region, SUM(r.actual_purpose_value) AS total_actual, SUM(TRY_CAST(r.planned_purpose_value AS DECIMAL(18,2))) AS total_planned, CASE WHEN SUM(TRY_CAST(r.planned_purpose_value AS DECIMAL(18,2))) = 0 THEN NULL ELSE SUM(r.actual_purpose_value) / SUM(TRY_CAST(r.planned_purpose_value AS DECIMAL(18,2))) END AS achievement_rate FROM Revenue r JOIN WellMonitoringReport w ON r.well_id = w.pdo_well_id GROUP BY w.Cluster ORDER BY achievement_rate DESC;",
        confidence="0.90",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # ============================================================
    # CATEGORY 2: SCHEDULE (Q11-Q20)
    # ============================================================

    # Q11 — SPI
    dspy.Example(
        user_question="What is the SPI (Schedule Performance Index) for each project?",
        query_type="aggregation",
        neo4j_schema_context=_JPR_CONTEXT,
        sql_query="SELECT [Well Name / Project Name], [Category], [Cum-Current Month Plan %], [Cum-Current Month Actual %], CASE WHEN [Cum-Current Month Plan %] = 0 THEN NULL ELSE [Cum-Current Month Actual %] / [Cum-Current Month Plan %] END AS SPI FROM Job_Progress_Report_GB WHERE [Cum-Current Month Plan %] IS NOT NULL ORDER BY SPI ASC;",
        confidence="0.92",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q12 — CPI
    dspy.Example(
        user_question="What is the CPI (Cost Performance Index)?",
        query_type="aggregation",
        neo4j_schema_context=_REV_CONTEXT,
        sql_query="SELECT rigcode AS Project, SUM(TRY_CAST(planned_purpose_value AS DECIMAL(18,2))) AS planned, SUM(actual_purpose_value) AS actual, CASE WHEN SUM(actual_purpose_value) = 0 THEN NULL ELSE SUM(TRY_CAST(planned_purpose_value AS DECIMAL(18,2))) / SUM(actual_purpose_value) END AS CPI FROM Revenue GROUP BY rigcode ORDER BY CPI ASC;",
        confidence="0.88",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q13 — delayed projects
    dspy.Example(
        user_question="Which projects are behind schedule?",
        query_type="single_table",
        neo4j_schema_context=_WMR_CONTEXT,
        sql_query="SELECT pdo_well_id, well_name_after_spud, Cluster, rig_no, CAST(over_all_progress_percentages * 100 AS DECIMAL(10,2)) AS progress_pct, [exp.rig_off_location_sap_data] AS expected_rig_off, actual_rig_off_date FROM WellMonitoringReport WHERE [exp.rig_off_location_sap_data] < CAST(GETDATE() AS DATE) AND actual_rig_off_date IS NULL ORDER BY [exp.rig_off_location_sap_data];",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q14 — wells stuck for 3+ weeks
    dspy.Example(
        user_question="Which wells have stalled for 3+ weeks?",
        query_type="multi_table_join",
        neo4j_schema_context=_JPR_CONTEXT + "\n\n" + _WMR_CONTEXT,
        sql_query="SELECT w.well_name_after_spud, w.rig_no, j.[Week-1 Actual %], j.[Week-2 Actual %], j.[Week-3 Actual %] FROM Job_Progress_Report_GB j JOIN WellMonitoringReport w ON j.[Well ID] = w.pdo_well_id WHERE TRY_CAST(j.[Week-1 Actual %] AS FLOAT) = 0 AND TRY_CAST(j.[Week-2 Actual %] AS FLOAT) = 0 AND TRY_CAST(j.[Week-3 Actual %] AS FLOAT) = 0;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q15 — average rig move days
    dspy.Example(
        user_question="What is the average rig move time?",
        query_type="aggregation",
        neo4j_schema_context=_SAP_CONTEXT,
        sql_query="SELECT AVG(CAST(Move_days AS FLOAT)) AS avg_move_days, MIN(Move_days) AS min_move_days, MAX(Move_days) AS max_move_days FROM SAP_DRILLING_SEQUENCE WHERE Move_days IS NOT NULL;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # ============================================================
    # CATEGORY 3: OPERATIONS (Q21-Q40)
    # ============================================================

    # Q21 — wells count
    dspy.Example(
        user_question="How many wells are there?",
        query_type="aggregation",
        neo4j_schema_context=_WMR_CONTEXT,
        sql_query="SELECT COUNT(DISTINCT pdo_well_id) AS total_wells FROM WellMonitoringReport_Latest;",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q22 — wells per cluster
    dspy.Example(
        user_question="How many wells are in each cluster?",
        query_type="aggregation",
        neo4j_schema_context=_WMR_CONTEXT,
        sql_query="SELECT Cluster, COUNT(DISTINCT pdo_well_id) AS well_count FROM WellMonitoringReport_Latest GROUP BY Cluster ORDER BY well_count DESC;",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q23 — wells by type
    dspy.Example(
        user_question="How many wells are ESP, OP, WI type?",
        query_type="aggregation",
        neo4j_schema_context=_WMR_CONTEXT,
        sql_query="SELECT well_type, COUNT(DISTINCT pdo_well_id) AS well_count FROM WellMonitoringReport_Latest GROUP BY well_type ORDER BY well_count DESC;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q24 — wells in specific cluster
    dspy.Example(
        user_question="Which wells are in Nimr cluster?",
        query_type="single_table",
        neo4j_schema_context=_WMR_CONTEXT,
        sql_query="SELECT pdo_well_id, well_name_after_spud, rig_no, well_type, CAST(over_all_progress_percentages * 100 AS DECIMAL(10,2)) AS progress_pct FROM WellMonitoringReport_Latest WHERE Cluster = 'Nimr' ORDER BY progress_pct DESC;",
        confidence="0.99",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q25 — today's work plan
    dspy.Example(
        user_question="What is today's daily work plan?",
        query_type="single_table",
        neo4j_schema_context=_DPR_CONTEXT,
        sql_query="SELECT [Well ID], [PA Name], [PH Name], [Activities], [Manpower], [Eqpt] FROM Daily_Plan_Report;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q26 — wells per rig
    dspy.Example(
        user_question="How many wells does each rig have?",
        query_type="aggregation",
        neo4j_schema_context=_WMR_CONTEXT,
        sql_query="SELECT rig_no, COUNT(DISTINCT pdo_well_id) AS well_count, AVG(TRY_CAST(over_all_progress_percentages AS FLOAT)) * 100 AS avg_progress_pct FROM WellMonitoringReport_Latest GROUP BY rig_no ORDER BY well_count DESC;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q27 — wells below a progress threshold
    dspy.Example(
        user_question="Show all Marmul wells with progress below 50%",
        query_type="single_table",
        neo4j_schema_context=_WMR_CONTEXT,
        sql_query="SELECT pdo_well_id, well_name_after_spud, rig_no, CAST(over_all_progress_percentages * 100 AS DECIMAL(10,2)) AS progress_pct FROM WellMonitoringReport_Latest WHERE Cluster = 'Marmul' AND over_all_progress_percentages < 0.50 ORDER BY over_all_progress_percentages;",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q28 — engineering completion status
    dspy.Example(
        user_question="Which wells have engineering completed?",
        query_type="single_table",
        neo4j_schema_context=_WMR_CONTEXT,
        sql_query="SELECT pdo_well_id, well_name_after_spud, [actual_eng._completion_date], [overall_engg._10_100] FROM WellMonitoringReport WHERE [actual_eng._completion_date] IS NOT NULL OR [overall_engg._10_100] >= 100;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # ============================================================
    # CATEGORY 4: MANPOWER (Q41-Q50)
    # ============================================================

    # Q41 — total manpower deployed
    dspy.Example(
        user_question="What is total manpower deployed today?",
        query_type="aggregation",
        neo4j_schema_context=_DPR_CONTEXT,
        sql_query="SELECT SUM(TRY_CAST([Manpower] AS INT)) AS total_manpower FROM Daily_Plan_Report;",
        confidence="0.88",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q42 — crew performance
    dspy.Example(
        user_question="Which crews have the highest productivity?",
        query_type="ranking",
        neo4j_schema_context=_PH_CONTEXT,
        sql_query="SELECT [Crew Name], [Crew Type], AVG([Average Productivity (%)]) AS avg_productivity FROM PH_PRODUCTIVITY_WEEKLY_REPORT GROUP BY [Crew Name], [Crew Type] ORDER BY avg_productivity DESC;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q43 — labor utilization rate
    dspy.Example(
        user_question="What is the labor utilization rate?",
        query_type="aggregation",
        neo4j_schema_context=_JC_CONTEXT,
        sql_query="SELECT [Project], COUNT(DISTINCT [Actual Employee / Equipment Name]) AS actual_resources, COUNT(DISTINCT [Plan Employee Name/ Equipment Name]) AS planned_resources, SUM([Effective Work Hours]) AS total_hours FROM vw_JOB_COST GROUP BY [Project] ORDER BY total_hours DESC;",
        confidence="0.85",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # ============================================================
    # CATEGORY 5: COST (Q51-Q60)
    # ============================================================

    # Q51 — cost vs budget
    dspy.Example(
        user_question="Show cost vs budget by project",
        query_type="aggregation",
        neo4j_schema_context=_REV_CONTEXT,
        sql_query="SELECT rigcode AS Project, SUM(actual_purpose_value) AS actual_cost, SUM(TRY_CAST(planned_purpose_value AS DECIMAL(18,2))) AS budget, SUM(actual_purpose_value) - SUM(TRY_CAST(planned_purpose_value AS DECIMAL(18,2))) AS variance FROM Revenue GROUP BY rigcode ORDER BY variance DESC;",
        confidence="0.92",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # ============================================================
    # CATEGORY 6: EQUIPMENT (Q61-Q65)
    # ============================================================

    # Q61 — equipment on each well
    dspy.Example(
        user_question="What equipment is deployed on each well today?",
        query_type="single_table",
        neo4j_schema_context=_DPR_CONTEXT,
        sql_query="SELECT [Well ID], [Activities], [Eqpt], [Manpower] FROM Daily_Plan_Report WHERE [Eqpt] IS NOT NULL AND LEN([Eqpt]) > 0;",
        confidence="0.90",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # ============================================================
    # CATEGORY 7: PROCUREMENT (Q71-Q75)
    # ============================================================

    # Q71 — POs overdue
    dspy.Example(
        user_question="Which POs are overdue for material delivery?",
        query_type="single_table",
        neo4j_schema_context=_WMR_CONTEXT + "\n  - Column [date_-_material_po_placed] (date): PO date.\n  - Column [date_-_material_available_at_site] (date): Material availability.",
        sql_query="SELECT pdo_well_id, well_name_after_spud, [date_-_material_po_placed], [date_-_material_available_at_site], DATEDIFF(day, [date_-_material_po_placed], GETDATE()) AS days_since_po FROM WellMonitoringReport WHERE [date_-_material_po_placed] IS NOT NULL AND [date_-_material_available_at_site] IS NULL ORDER BY days_since_po DESC;",
        confidence="0.90",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # ============================================================
    # CATEGORY 8: SAFETY (Q81-Q85) — INSUFFICIENT_SCHEMA
    # ============================================================

    # Q81 — safety incidents (NOT IN DB)
    dspy.Example(
        user_question="How many safety incidents this month?",
        query_type="single_table",
        neo4j_schema_context=_WMR_CONTEXT + "\n\nNOTE: No safety incident or hazard table exists in the current schema.",
        sql_query="INSUFFICIENT_SCHEMA",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Q82 — LTI-free days (NOT IN DB)
    dspy.Example(
        user_question="How many LTI-free days do we have?",
        query_type="single_table",
        neo4j_schema_context=_WMR_CONTEXT + "\n\nNOTE: No safety incident, LTI, or HSE tracking table exists.",
        sql_query="INSUFFICIENT_SCHEMA",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # ============================================================
    # CATEGORY 9: CONTRACTS (Q86-Q90) — INSUFFICIENT_SCHEMA
    # ============================================================

    # Q86 — subcontractor performance (NOT IN DB)
    dspy.Example(
        user_question="How are subcontractors performing vs their SLAs?",
        query_type="single_table",
        neo4j_schema_context=_WMR_CONTEXT + "\n\nNOTE: No contract/SLA tracking table exists.",
        sql_query="INSUFFICIENT_SCHEMA",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # ============================================================
    # MORE OPERATIONAL QUESTIONS
    # ============================================================

    # MOC status
    dspy.Example(
        user_question="Which wells have MOC raised but not approved?",
        query_type="single_table",
        neo4j_schema_context=_WMR_CONTEXT,
        sql_query="SELECT pdo_well_id, well_name_after_spud, Cluster, moc_raised, moc_approved FROM WellMonitoringReport WHERE moc_raised IN ('YES', 'Yes', 'yes') AND moc_approved NOT IN ('YES', 'Yes', 'yes');",
        confidence="0.98",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Rig utilization
    dspy.Example(
        user_question="What is rig utilization rate?",
        query_type="aggregation",
        neo4j_schema_context=_WMR_CONTEXT,
        sql_query="SELECT rig_no, COUNT(DISTINCT pdo_well_id) AS total_wells, SUM(CASE WHEN buffer_status = 'ROL' THEN 1 ELSE 0 END) AS active_drilling, SUM(CASE WHEN actual_rig_off_date IS NOT NULL THEN 1 ELSE 0 END) AS completed FROM WellMonitoringReport_Latest GROUP BY rig_no;",
        confidence="0.85",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Material readiness
    dspy.Example(
        user_question="What is the material availability status across wells?",
        query_type="single_table",
        neo4j_schema_context=_WMR_CONTEXT + "\n  - Column [overall_material_10_100] (decimal): Material availability progress 0-100.",
        sql_query="SELECT pdo_well_id, well_name_after_spud, Cluster, [overall_material_10_100] AS material_pct FROM WellMonitoringReport_Latest WHERE [overall_material_10_100] < 100 ORDER BY [overall_material_10_100] ASC;",
        confidence="0.92",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Construction phase status
    dspy.Example(
        user_question="What is the flowline construction status?",
        query_type="single_table",
        neo4j_schema_context=_WMR_CONTEXT + "\n  - Column [flowline_construction_progress] (decimal): 0-1 scale.\n  - Column [flow_line_const._status_in_progress_completed] (nvarchar): Status text.",
        sql_query="SELECT pdo_well_id, well_name_after_spud, CAST(flowline_construction_progress * 100 AS DECIMAL(10,2)) AS flowline_pct, [flow_line_const._status_in_progress_completed] AS status FROM WellMonitoringReport_Latest ORDER BY flowline_construction_progress ASC;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # KPI tracking
    dspy.Example(
        user_question="Which wells have engineering KPI above 2 days?",
        query_type="single_table",
        neo4j_schema_context=_WMR_CONTEXT,
        sql_query="SELECT pdo_well_id, well_name_after_spud, rig_no, [engg_kpi_after_rig-off_days] AS kpi_days, reason_if_kpi_not_met FROM WellMonitoringReport WHERE TRY_CAST([engg_kpi_after_rig-off_days] AS INT) > 2 ORDER BY [engg_kpi_after_rig-off_days] DESC;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Task completion
    dspy.Example(
        user_question="What is the daily task completion rate?",
        query_type="aggregation",
        neo4j_schema_context=_TD_CONTEXT,
        sql_query="SELECT ActionOn, COUNT(*) AS total_tasks, SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) AS completed_tasks, CAST(SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS DECIMAL(10,2)) AS completion_rate FROM task_daily WHERE ActionOn >= DATEADD(day, -7, GETDATE()) GROUP BY ActionOn ORDER BY ActionOn DESC;",
        confidence="0.90",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Weekly variance
    dspy.Example(
        user_question="Show me the weekly plan vs actual variance for all projects",
        query_type="single_table",
        neo4j_schema_context=_JPR_CONTEXT,
        sql_query="SELECT [Well Name / Project Name], [Category], [Week-1 Plan %], [Week-1 Actual %], ([Week-1 Actual %] - [Week-1 Plan %]) AS W1_Variance, [Week-2 Plan %], [Week-2 Actual %], ([Week-2 Actual %] - [Week-2 Plan %]) AS W2_Variance FROM Job_Progress_Report_GB ORDER BY W1_Variance ASC;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),

    # Buffer status
    dspy.Example(
        user_question="Show buffer status across all wells",
        query_type="aggregation",
        neo4j_schema_context=_WMR_CONTEXT,
        sql_query="SELECT buffer_status, COUNT(DISTINCT pdo_well_id) AS well_count FROM WellMonitoringReport_Latest WHERE buffer_status IS NOT NULL GROUP BY buffer_status ORDER BY well_count DESC;",
        confidence="0.95",
    ).with_inputs('user_question', 'neo4j_schema_context', 'query_type'),
]

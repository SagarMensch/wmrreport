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


# ── DSPy Signatures ─────────────────────────────────────────────────────

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
]


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

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
    17. JOIN KEYS:
       - WellMonitoringReport.pdo_well_id = Job_Progress_Report_GB.Well_ID
       - WellMonitoringReport.pdo_well_id = Revenue.Well_ID
       - WellMonitoringReport.rig_no = crews.rig_code
       - WellMonitoringReport.well_name_after_spud = SAP_DRILLING_SEQUENCE.Well_Name
       - WMR_Full.pdo_well_id = WellMonitoringReport.pdo_well_id
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
]


# ── Security Metric ─────────────────────────────────────────────────────

FORBIDDEN_KEYWORDS = [
    'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'TRUNCATE',
    'EXEC', 'EXECUTE', 'CREATE', 'GRANT', 'REVOKE', 'DENY',
    'MERGE', 'BULK', 'OPENROWSET', 'xp_', 'sp_',
]

FORBIDDEN_PATTERNS = ['--']


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

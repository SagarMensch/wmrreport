"""
=============================================================================
AppMasterDB KNOWLEDGE BASE - PALANTIR LEVEL
=============================================================================
Comprehensive knowledge extracted from ALL view creation scripts.
This is the SINGLE SOURCE OF TRUTH for AI to generate correct SQL.

Views Parsed:
1. Job_Progress_Report_GB (707 lines) - COMPLETE
2. vw_JobProgress (214 lines)
3. vw_JOB_COST (350 lines)
4. WellMonitoringReport (758 lines)
5. PH_Productivity (214 lines)
6. Daily_Plan_Report (49 lines)
7. New_Daily_Plan (18 lines)

Each view includes:
- Business logic in detail
- SQL transformation patterns
- Column derivations
- Join relationships
- Date handling
- Data type conversions
=============================================================================
"""

import json
import re

# ============================================================================
# VIEW 1: Job_Progress_Report_GB (MAIN PROGRESS VIEW)
# ============================================================================

VIEW_Job_Progress_Report_GB = {
    "name": "Job_Progress_Report_GB",
    "database": "AppMasterDB",
    "purpose": "Main job progress tracking - most comprehensive view with weekly buckets, purpose values, WBS",
    "source_tables": [
        "dbo.WMR", "dbo.WMR_TaskPlan_csv_imported", "dbo.Job_Progress_PlanSnapshot",
        "dbo.task_daily", "dbo.ProjectIDs", "dbo.data_table_sched_jsons", 
        "dbo.WBS_Master_Tracker_"
    ],
    
    "key_columns": {
        # Identity
        "Well ID": {"type": "nvarchar", "derived_from": "WMR_TaskPlan_csv_imported.New_Well_ID", "logic": "LTRIM(RTRIM(TRY_CONVERT(nvarchar(50), tp.New_Well_ID)))"},
        "Well Name / Project Name": {"type": "nvarchar", "derived_from": "WMR.well_name_after_spud", "logic": "MAX(well_name_after_spud) GROUP BY pdo_well_id"},
        "Category": {"type": "nvarchar", "derived_from": "ProjectIDs.column2", "logic": "JOIN on project_id"},
        
        # PO/WBS
        "PO No": {"type": "nvarchar", "logic": "IF category contains flowline/cwf/rwf THEN flow_line_po_no ELSE location_po_no"},
        "WBS No": {"type": "nvarchar", "logic": "OUTER APPLY WBS_Master_Tracker_ with category matching"},
        
        # Progress Buckets (PERCENTAGES - multiply fraction by 100)
        "Cum-Prior Month Actual %": {"type": "decimal(18,2)", "logic": "prior actual fraction * 100"},
        "Week-1 Plan %": {"type": "decimal(18,2)", "logic": "W1_Plan_frac * 100, NULL if no plan"},
        "Week-1 Actual %": {"type": "decimal(18,2)", "logic": "W1_Act_frac * 100"},
        "Week-2 Plan %": {"type": "decimal(18,2)", "logic": "W2_Plan_frac * 100"},
        "Week-2 Actual %": {"type": "decimal(18,2)", "logic": "W2_Act_frac * 100"},
        "Week-3 Plan %": {"type": "decimal(18,2)", "logic": "W3_Plan_frac * 100"},
        "Week-3 Actual %": {"type": "decimal(18,2)", "logic": "W3_Act_frac * 100"},
        "Week-4 Plan %": {"type": "decimal(18,2)", "logic": "W4_Plan_frac * 100"},
        "Week-4 Actual %": {"type": "decimal(18,2)", "logic": "W4_Act_frac * 100"},
        "Week-5 Plan %": {"type": "decimal(18,2)", "logic": "W5_Plan_frac * 100"},
        "Week-5 Actual %": {"type": "decimal(18,2)", "logic": "W5_Act_frac * 100"},
        
        # Month Totals
        "Current Month Plan %": {"type": "decimal(18,2)", "logic": "SUM(W1-W5_Plan_frac) * 100, capped at 1.0"},
        "Current Month Actual %": {"type": "decimal(18,2)", "logic": "SUM(W1-W5_Act_frac) * 100, capped at 1.0"},
        "Cum-Current Month Plan %": {"type": "decimal(18,2)", "logic": "CumCurrentMonthPlanFrac * 100"},
        "Cum-Current Month Actual %": {"type": "decimal(18,2)", "logic": "SUM(CumPrior + W1-W5) * 100, capped at 1.0"},
        
        # Purpose Values (MONETARY)
        "Purpose Value": {"type": "decimal(28,2)", "logic": "SUM(schedule purpose_value) from SchedAgg"},
        "Cum-Prior Month Plan": {"type": "decimal(28,2)", "logic": "PurposeValue * Cum_Prior_Plan_frac"},
        "Cum-Prior Month Actual": {"type": "decimal(28,2)", "logic": "PurposeValue * Cum_Prior_Act_frac"},
        "Current month Plan": {"type": "decimal(28,2)", "logic": "PurposeValue * CurrentMonthPlanFrac"},
        "Current Month Actual": {"type": "decimal(28,2)", "logic": "PurposeValue * SUM(W1-W5_Act_frac)"},
        
        # Dates
        "Target End": {"type": "date", "logic": "COALESCE(snapshot, max from Base)"}
    },
    
    "business_logic": {
        "weightage_normalization": "If contains '%', remove and divide by 100. If > 1.0, divide by 100. If <= 1.0, use as-is",
        "progress_normalization": "Same as weightage - normalize to 0-1 fraction",
        "week_buckets": "W1=day1-7, W2=day8-14, W3=day15-21, W4=day22-28, W5=day29+",
        "actual_calculation_part1": "If actual_start AND actual_end exist AND valid: daily_frac = (progress_frac * weight_frac) / days",
        "actual_calculation_part2": "Fallback to task_daily when no valid date range: qty/qty_total * weight_frac",
        "plan_source": "From Job_Progress_PlanSnapshot table - weekly fractions",
        "cluster_derivation": "Source='NC-WD'→nimr, Source='MC-WD'→marmul from data_table_sched_jsons",
        "project_code_parsing": "Extract from filename: SCHED-XXXX-RIG → XXXX"
    },
    
    "joins": {
        "ProjectIDs": "pid.ID = a.project_id",
        "WMR": "wmr1.WellID = a.Well_ID",
        "WBS_Master_Tracker_": "WBS_Code where Category matches column2",
        "SchedAgg": "Well_ID_norm, Cluster, ProjCodeClean matching"
    },
    
    "sql_patterns": {
        "weight_frac": "CASE WHEN weightage LIKE '%' THEN REPLACE/100 WHEN weightage > 1 THEN weightage/100 ELSE weightage END",
        "week_bucket": "CASE WHEN day BETWEEN 1 AND 7 THEN 'W1' WHEN 8-14 THEN 'W2' etc",
        "cap_at_1": "CASE WHEN sum > 1 THEN 1.0 ELSE sum END",
        "well_id_extract": "LTRIM(RTRIM(TRY_CONVERT(nvarchar(50), New_Well_ID)))"
    }
}


# ============================================================================
# VIEW 2: vw_JobProgress (ALTERNATIVE PROGRESS VIEW)
# ============================================================================

VIEW_vw_JobProgress = {
    "name": "vw_JobProgress",
    "database": "AppMasterDB",
    "purpose": "Alternative job progress - simpler, monthly focus with category from ProjectIDs",
    "source_tables": ["dbo.ActivityTaskPlan", "dbo.ProjectIDs", "dbo.WMR"],
    
    "key_columns": {
        "Category": {"type": "nvarchar", "logic": "ProjectIDs.column2"},
        "Well ID / Project ID": {"type": "int", "logic": "Extract from code after '-'"},
        "Week-1 Plan %": {"type": "decimal(10,2)", "logic": "SUM(weightage) WHERE target_start day 1-7"},
        "Week-1 Actual %": {"type": "decimal(10,2)", "logic": "SUM(weightage * progress_ratio) WHERE actual_start day 1-7"},
    },
    
    "business_logic": {
        "well_id_from_code": "RIGHT(code, LEN(code) - CHARINDEX('-', code))",
        "week_definition": "Week1=1-7, Week2=8-14, Week3=15-21, Week4=22-28, Week5=29+",
        "progress_ratio": "1 or 100→1.0, 0.10→0.10, 10→0.10"
    }
}


# ============================================================================
# VIEW 3: vw_JOB_COST (RESOURCE COST TRACKING)
# ============================================================================

VIEW_vw_JOB_COST = {
    "name": "vw_JOB_COST",
    "database": "AppMasterDB", 
    "purpose": "Job cost - planned vs actual resources (employees, equipment)",
    "source_tables": [
        "dbo.task_daily", "dbo.Revenue", "dbo.crews", "dbo.Employee", 
        "dbo.company_employees", "dbo.EmployeeType", "dbo.Equipment", 
        "dbo.EquipmentType", "dbo.ActivityMasterMapping"
    ],
    
    "key_columns": {
        "Project": {"type": "nvarchar", "logic": "Revenue.rigcode - the rig identifier"},
        "Well ID": {"type": "nvarchar", "logic": "task_daily.well_id"},
        "Activity ID": {"type": "nvarchar", "logic": "LEFT(task_code, 8) - first 8 characters"},
        "crew code": {"type": "nvarchar", "logic": "task_daily.crew_code → crews.Code"},
        "Plan Employee Name": {"type": "nvarchar", "logic": "FROM crews.Employees JSON → Employee table"},
        "Actual Employee Name": {"type": "nvarchar", "logic": "FROM task_daily.employee_ids_text JSON → Employee"},
        "Effective Work Hours": {"type": "decimal", "logic": "JSON_VALUE(daily_data, '$.actual_hours')"}
    },
    
    "business_logic": {
        "activity_extraction": "LEFT(LTRIM(RTRIM(task_code)), 8)",
        "crew_json_explode": "OPENJSON(c.Employees) to get employee IDs",
        "resource_pairing": "Full outer join Planned vs Actual on: well_id + ActionOn + ActivityID + resource_type + PGCode + rn",
        "project_prefix": "M→MML, N→NIM from first letter of rigcode"
    },
    
    "joins": {
        "Revenue": "task_daily.well_id = Revenue.well_id AND Revenue.ActivityID = task_daily.ActivityID",
        "crews": "crews.Code = task_daily.crew_code",
        "Employee": "Employee.id = company_employees.id"
    }
}


# ============================================================================
# VIEW 4: PH_Productivity (EFFICIENCY METRICS)
# ============================================================================

VIEW_PH_Productivity = {
    "name": "PH_Productivity",
    "database": "AppMasterDB",
    "purpose": "Productivity tracking - QHSE Supervisor and Crew performance",
    "source_tables": ["dbo.task_daily", "dbo.Employee", "dbo.ActivityCodesNorms", "dbo.CrewType"],
    
    "key_columns": {
        "Year": {"type": "int", "logic": "YEAR from ActionOn"},
        "Month": {"type": "int", "logic": "MONTH from ActionOn"},
        "PA Name": {"type": "nvarchar", "logic": "LEFT(task_assignee, CHARINDEX('.', task_assignee)-1)"},
        "PH Name": {"type": "nvarchar", "logic": "Employee.Email = supervisor_email → Employee.Name"},
        "PH Emp ID": {"type": "nvarchar", "logic": "Employee.UId"},
        "Crew Name": {"type": "nvarchar", "logic": "CrewType.Description WHERE Code = REPLACE(crew_type, '-', '')"},
        "Avg_Productivity_Pct": {"type": "decimal", "logic": "(SUM(data_qty)/SUM(data_hours)) / Norms * 100"},
        "W1_PI_T_Wise": {"type": "decimal", "logic": "Week 1 Productivity Index T-Wise"},
        "W1_PI_CMR": {"type": "decimal", "logic": "Week 1 Productivity Index CMR"}
    },
    
    "business_logic": {
        "productivity_formula": "Productivity% = (QtyPerHour / Norms) * 100",
        "ph_lookup": "supervisor_email → Employee.Email → Employee.Name",
        "pa_lookup": "task_assignee email before @",
        "crew_lookup": "crew_type compared with CrewType.Code"
    }
}


# ============================================================================
# VIEW 5: WellMonitoringReport (COMPREHENSIVE WELL TRACKING)
# ============================================================================

VIEW_WellMonitoringReport = {
    "name": "WellMonitoringReport",
    "database": "AppMasterDB",
    "purpose": "Complete well monitoring - MOC, dates, progress, SAP data",
    "source_tables": [
        "dbo.WMR", "dbo.WMR_TaskPlan_csv_imported", "dbo.DesignTrackerCSVImport",
        "dbo.SAP_DRILLING_SEQUENCE", "dbo.Revenue", "dbo.crews"
    ],
    
    "key_columns": {
        "pdo_well_id": {"type": "nvarchar", "logic": "PRIMARY KEY - unique well identifier"},
        "Cluster": {"type": "nvarchar", "logic": "nimr or marmul"},
        "rig_no": {"type": "nvarchar", "logic": "Drilling rig → crews.Code"},
        "moc_raised": {"type": "nvarchar", "logic": "YES or Yes"},
        "moc_approved": {"type": "nvarchar", "logic": "YES or Yes"},
        "over_all_progress_percentages": {"type": "decimal", "logic": "0-1 scale, multiply by 100 for %"}
    },
    
    "business_logic": {
        "target_week": "Latest week minus 1 (second most recent)",
        "taskplan_parsing": "fn_WMR_ParseProgress, fn_WMR_ParseDate",
        "moc_values": "Use IN ('YES', 'Yes', 'yes') - NOT 'Raised'"
    }
}


# ============================================================================
# VIEW 6 & 7: Daily Planning Views
# ============================================================================

VIEW_Daily_Plan_Report = {
    "name": "Daily_Plan_Report",
    "database": "AppMasterDB",
    "purpose": "Daily work planning - well, PA, PH, PO, activities",
    "key_columns": {
        "Well ID": "Well identifier",
        "PA Name": "Permit Applicant name",
        "PH Name": "QHSE Supervisor name",
        "PO No": "Purchase Order",
        "Activities": "Activity Description (fixed from original ACTIVITIES bug)"
    }
}


# ============================================================================
# CENTRAL KNOWLEDGE BASE - FOR AI REFERENCE
# ============================================================================

KNOWLEDGE_BASE = {
    "views": {
        "Job_Progress_Report_GB": VIEW_Job_Progress_Report_GB,
        "vw_JobProgress": VIEW_vw_JobProgress,
        "vw_JOB_COST": VIEW_vw_JOB_COST,
        "PH_Productivity": VIEW_PH_Productivity,
        "WellMonitoringReport": VIEW_WellMonitoringReport,
        "Daily_Plan_Report": VIEW_Daily_Plan_Report
    },
    
    # Critical SQL patterns the AI must use
    "sql_patterns": {
        "week_bucket_plan": "CASE WHEN DATEPART(DAY, target_start) BETWEEN 1 AND 7 THEN 'W1' WHEN 8-14 THEN 'W2' WHEN 15-21 THEN 'W3' WHEN 22-28 THEN 'W4' ELSE 'W5' END",
        "week_bucket_actual": "Same as plan but using actual_start",
        "weightage_normalize": "CASE WHEN weightage LIKE '%%' THEN REPLACE(weightage,'%','')/100.0 WHEN weightage > 1.0 THEN weightage/100.0 ELSE weightage END",
        "cap_at_one": "CASE WHEN SUM > 1.0 THEN 1.0 ELSE SUM END",
        "well_id_extract": "TRY_CONVERT(int, LTRIM(RTRIM(RIGHT(code, LEN(code) - CHARINDEX('-', code)))))",
        "rigcode_filter": "Revenue.rigcode IN ('NL0010','NF0010','ML0010','MS0010','MF0010','MCOF10','MCWF10','MROP10','MRWF10','NCOF10','NNSW10','NS0010')",
        "moc_filter": "moc_raised IN ('YES','Yes','yes') AND moc_approved NOT IN ('YES','Yes','yes')"
    },
    
    # Column name mappings (user term → database column)
    "semantic_mappings": {
        "progress": "over_all_progress_percentages or Week-1 Actual %",
        "plan": "Week-1 Plan % or Current Month Plan %",
        "actual": "Week-1 Actual % or Current Month Actual %",
        "well": "Well ID or pdo_well_id",
        "rig": "rig_no or Revenue.rigcode",
        "cluster": "Cluster = 'Nimr' or 'Marmul'",
        "moc": "moc_raised, moc_approved",
        "productivity": "Avg_Productivity_Pct",
        "category": "ProjectIDs.column2 or Category",
        "purpose_value": "Purpose Value or actual_purpose_value",
        "week": "Week-1, Week-2, Week-3, Week-4, Week-5"
    }
}


# ============================================================================
# BM25 DOCUMENTS - For Semantic Search
# ============================================================================

def generate_bm25_documents():
    """Generate comprehensive BM25 documents from knowledge base."""
    
    documents = []
    
    # View-level documents
    for view_name, view_info in KNOWLEDGE_BASE["views"].items():
        doc = {
            "table": f"AppMasterDB.dbo.{view_name}",
            "column": "*",
            "document": f"""
                VIEW: AppMasterDB.dbo.{view_name}
                PURPOSE: {view_info['purpose']}
                SOURCE TABLES: {', '.join(view_info.get('source_tables', []))}
                
                KEY COLUMNS:
                {json.dumps(view_info.get('key_columns', {}), indent=2)}
                
                BUSINESS LOGIC:
                {json.dumps(view_info.get('business_logic', {}), indent=2)}
                
                SQL PATTERNS:
                {json.dumps(view_info.get('sql_patterns', {}), indent=2)}
            """.strip(),
            "type": "VIEW"
        }
        documents.append(doc)
        
        # Column-level documents
        for col_name, col_info in view_info.get("key_columns", {}).items():
            # Handle both dict and string formats
            if isinstance(col_info, dict):
                col_type = col_info.get('type', 'unknown')
                col_logic = col_info.get('logic', '')
                col_derived = col_info.get('derived_from', '')
            else:
                col_type = 'nvarchar'
                col_logic = col_info
                col_derived = 'direct'
            
            doc = {
                "table": f"AppMasterDB.dbo.{view_name}",
                "column": col_name,
                "document": f"""
                    VIEW COLUMN: AppMasterDB.dbo.{view_name}.{col_name}
                    DATA TYPE: {col_type}
                    DERIVED FROM: {col_derived}
                    LOGIC: {col_logic}
                    
                    VIEW PURPOSE: {view_info['purpose']}
                """.strip(),
                "type": "VIEW_COLUMN",
                "semantic": col_logic,
                "view_purpose": view_info["purpose"]
            }
            documents.append(doc)
    
    return documents


# ============================================================================
# DSPY TRAINING RULES
# ============================================================================

DSPY_RULES = """
DSPY SQL GENERATION RULES FROM APPMASTERDB:

1. WELL ID FROM CODE: RIGHT(code, LEN(code) - CHARINDEX('-', code))

2. PROGRESS COLUMNS (Job_Progress_Report_GB):
   - Use Week-1 Plan %, Week-1 Actual % etc
   - Multiply fractions by 100 for percentage
   - Use: CAST(ROUND(100.0 * fraction, 2) AS decimal(18,2))

3. PURPOSE VALUES:
   - Purpose Value in currency
   - Calculate: PurposeValue * progress_fraction
   - Use: CAST(ISNULL(pv.PurposeValue,0) * fraction AS decimal(28,2))

4. WEEK BUCKETS:
   - W1: day 1-7, W2: 8-14, W3: 15-21, W4: 22-28, W5: 29+
   - Plan from Job_Progress_PlanSnapshot
   - Actual from task_daily or TaskPlan

5. RIG CODE FILTER: Revenue.rigcode IN ('NL0010','NF0010',...)
   - NEVER use well_location for rig codes!

6. MOC STATUS: moc_raised IN ('YES','Yes','yes')

7. CLUSTER: Cluster = 'Nimr' or 'Marmul'

8. PRODUCTIVITY: (data_qty / data_hours) / Norms * 100

9. DATE FORMATS:
   - target_start, actual_start are DATE type
   - Use: TRY_CONVERT(date, column)

10. JOIN KEYS:
    - ActivityTaskPlan.New_Well_ID → WMR.pdo_well_id
    - task_daily.well_id → Revenue.Well_ID
    - crews.Code = task_daily.crew_code
"""


if __name__ == "__main__":
    # Save knowledge base
    with open("appmasterdb_complete_knowledge.json", "w", encoding="utf-8") as f:
        json.dump(KNOWLEDGE_BASE, f, indent=2)
    
    # Generate BM25 documents
    docs = generate_bm25_documents()
    with open("appmasterdb_bm25_documents.json", "w", encoding="utf-8") as f:
        json.dump(docs, f, indent=2)
    
    # Save DSPY rules
    with open("appmasterdb_dspy_rules.txt", "w", encoding="utf-8") as f:
        f.write(DSPY_RULES)
    
    print("="*70)
    print("APPMASTERDB KNOWLEDGE BASE - PALANTIR LEVEL")
    print("="*70)
    print(f"\nViews parsed: {len(KNOWLEDGE_BASE['views'])}")
    print(f"BM25 documents: {len(docs)}")
    print("\nViews:")
    for name, info in KNOWLEDGE_BASE["views"].items():
        print(f"  - {name}")
        print(f"    Purpose: {info['purpose'][:60]}...")
        print(f"    Columns: {len(info.get('key_columns', {}))}")
    
    print("\n" + "="*70)
    print("FILES CREATED:")
    print("="*70)
    print("1. appmasterdb_complete_knowledge.json - Full knowledge base")
    print("2. appmasterdb_bm25_documents.json - BM25 search documents")
    print("3. appmasterdb_dspy_rules.txt - DSPy training rules")

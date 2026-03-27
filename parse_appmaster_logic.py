"""
AppMasterDB Logic Parser
=======================
Parses CREATE VIEW scripts to extract:
- Business logic
- Table joins
- Column transformations
- Data flow

This becomes the KNOWLEDGE BASE for AI to write correct SQL.
"""

import re
import json

# ============================================================================
# PARSED VIEW LOGIC - This is the GOLD MINE
# ============================================================================

VIEW_LOGIC = {
    
    "vw_JobProgress": {
        "source": "AppMasterDB.dbo.vw_JobProgress",
        "purpose": "Weekly job progress tracking with plan vs actual bucketed by week",
        "business_logic": """
        KEY LOGIC:
        - Derives Well_ID from code: everything AFTER '-' (e.g., 'ABC-12345' → 12345)
        - Category comes from ProjectIDs.column2 (joined via project_id)
        - Week buckets: Week1 (1-7), Week2 (8-14), Week3 (15-21), Week4 (22-28), Week5 (29+)
        - Plan = SUM(weightage) normalized to %
        - Actual = SUM(weightage * progress_ratio)
        - progress_ratio: 1 or 100 → 1.0, 0.10 → 0.10, 10 → 0.10
        - Joins: ActivityTaskPlan → ProjectIDs → WMR
        """,
        "tables_used": ["ActivityTaskPlan", "ProjectIDs", "WMR"],
        "key_columns": {
            "Well_ID": "Extracted from code - everything AFTER first '-'",
            "Category": "ProjectIDs.column2 - project category (Marmul SNLP, Conversion etc)",
            "Week-1 Plan %": "SUM(weightage) where target_start between day 1-7",
            "Week-1 Actual %": "SUM(weightage * progress_ratio) where actual_start between day 1-7"
        },
        "sql_patterns": {
            "extract_well_id": "TRY_CONVERT(int, LTRIM(RTRIM(RIGHT(LTRIM(RTRIM(l.code)), LEN(LTRIM(RTRIM(l.code))) - CHARINDEX('-', LTRIM(RTRIM(l.code)) + '-')))))",
            "normalize_weightage": "CASE WHEN weightage < 1 THEN weightage * 100 ELSE weightage END",
            "progress_ratio": "CASE WHEN progress = 1 OR progress = 100 THEN 1.0 WHEN progress > 1 AND progress >= 100 THEN 1.0 WHEN progress > 1 THEN progress / 100.0 ELSE progress END"
        }
    },

    "vw_JOB_COST": {
        "source": "AppMasterDB.dbo.vw_JOB_COST", 
        "purpose": "Job cost tracking - compares planned vs actual resources",
        "business_logic": """
        KEY LOGIC:
        - LEFT JOINs Revenue to get rigcode (project)
        - Extracts ActivityID: first 8 chars of task_code
        - Crews JSON parsing: OPENJSON to explode employees and equipment
        - Planned: from crews table (Employees JSON, Equipments JSON)
        - Actual: from task_daily employee_ids_text and equipment_ids_text
        - Full outer join Planned vs Actual on: well_id + ActionOn + ActivityID + resource_type + PGCode + rn
        - Project derived: first letter of rigcode: M→MML, N→NIM
        """,
        "tables_used": ["task_daily", "Revenue", "crews", "Employee", "company_employees", "EmployeeType", "Equipment", "EquipmentType", "ActivityMasterMapping"],
        "key_columns": {
            "Project": "Revenue.rigcode - the rig identifier (NL0010, NF0010 etc)",
            "ActivityID": "LEFT(task_code, 8) - first 8 characters",
            "crew_code": "Links to crews.Code",
            "PlanName": "Employee.Name or Equipment.Description",
            "Effective Work Hours": "JSON_VALUE(daily_data, '$.actual_hours')"
        },
        "joins": {
            "Revenue": "task_daily.well_id = Revenue.well_id AND Revenue.ActivityID = task_daily.ActivityID",
            "crews": "crews.Code = task_daily.crew_code",
            "Employee": "Employee.id = company_employees.id (via company_employees)"
        }
    },

    "PH_Productivity": {
        "source": "AppMasterDB.dbo.PH_Productivity",
        "purpose": "Productivity tracking per PH (QHSE Supervisor) and Crew",
        "business_logic": """
        KEY LOGIC:
        - PH Name: supervisor_email → Employee.Email → Employee.Name
        - PA Name: task_assignee trimmed at '.' (basil.971144@ → basil)
        - Crew Name: crew_type compared with CrewType.Code after removing '-'
        - Productivity = QtyPerHour / Norms * 100
        - PI buckets: As per CMR & T-Wise slabs
        """,
        "tables_used": ["task_daily", "Employee", "ActivityCodesNorms", "CrewType", "company_employees"],
        "key_columns": {
            "PH Name": "Employee.Name WHERE Employee.Email = task_daily.supervisor_email",
            "PA Name": "LEFT(task_assignee, CHARINDEX('.', task_assignee) - 1)",
            "Crew Name": "CrewType.Description WHERE CrewType.Code = REPLACE(crew_type, '-', '')",
            "Productivity %": "(data_qty / data_hours) / ActivityCodesNorms.Norms * 100"
        }
    },

    "WellMonitoringReport": {
        "source": "AppMasterDB.dbo.WellMonitoringReport",
        "purpose": "Comprehensive well monitoring with all progress, MOC, dates",
        "business_logic": """
        KEY LOGIC:
        - Target week: Latest week minus 1 (second most recent)
        - TaskPlan parsing: dbo.fn_WMR_ParseProgress, dbo.fn_WMR_ParseDate
        - DesignTracker: E_I_AFC_Completion_Date parsed (multiple dates in one cell, pick latest)
        - MOC: moc_raised, moc_approved columns
        - Links to: SAP_DRILLING_SEQUENCE, Revenue, crews
        """,
        "tables_used": ["WMR", "WMR_TaskPlan_csv_imported", "DesignTrackerCSVImport", "SAP_DRILLING_SEQUENCE", "Revenue", "crews"],
        "key_columns": {
            "pdo_well_id": "Primary key - unique well identifier",
            "Cluster": "Nimr or Marmul",
            "moc_raised": "YES/Yes means MOC raised",
            "moc_approved": "YES/Yes means MOC approved"
        },
        "joins": {
            "SAP_DRILLING_SEQUENCE": "WMR.pdo_well_id = SAP_DRILLING_SEQUENCE.Well_ID",
            "Revenue": "WMR.pdo_well_id = Revenue.Well_ID",
            "crews": "WMR.rig_no = crews.Code"
        }
    },

    "Daily_Plan_Report": {
        "source": "AppMasterDB.dbo.Daily_Plan_Report",
        "purpose": "Daily work plan with well, PA, PH, PO, location, activities",
        "business_logic": """
        KEY LOGIC:
        - ROW_NUMBER() over Order by Location, Crew Code, Linking_code
        - Fixed column mapping: Activity Description → Activities (not ACTIVITIES)
        - Many CAST(NULL AS ...) columns for future expansion
        """,
        "tables_used": ["vw_DailyWorkPlanC_TodayReport"]
    }
}

# ============================================================================
# KNOWLEDGE BASE FOR AI - COLUMN MAPPINGS
# ============================================================================

COLUMN_MAPPINGS = {
    # Well identification
    "Well_ID extraction": "Use RIGHT(code, LEN(code) - CHARINDEX('-', code)) to extract well ID from codes like 'ABC-12345'",
    
    # Progress calculations
    "progress_ratio": "1 or 100 → 1.0, 0.10 → 0.10, 10 → 0.10",
    
    # Productivity
    "productivity_formula": "(data_qty / data_hours) / Norms * 100",
    
    # Names from emails
    "PH from email": "Employee.Email = task_daily.supervisor_email → Employee.Name",
    "PA from email": "LEFT(task_assignee, CHARINDEX('.', task_assignee) - 1)",
    
    # Project codes
    "MML": "Project starting with M → MML (Marmul)",
    "NIM": "Project starting with N → NIM (Nimr)",
    
    # Rig codes
    "rigcode values": "NL0010, NF0010, ML0010, MS0010, MF0010, MCOF10, MCWF10, MROP10, MRWF10, NCOF10, NNSW10, NS0010",
    
    # MOC status
    "MOC values": "Use IN ('YES', 'Yes', 'yes') - not 'Raised' or 'Approved'"
}

# ============================================================================
# DSPY TRAINING EXAMPLES - From AppMasterDB Logic
# ============================================================================

TRAINING_HINTS = """
DSPY should use these rules when generating SQL:

1. WELL ID FROM CODE: When user asks about wells in a code like 'ABC-12345', extract: RIGHT(code, LEN(code) - CHARINDEX('-', code))

2. JOB PROGRESS WEEK BUCKETS: 
   - Week1: target_start/actual_start BETWEEN day 1-7
   - Week2: day 8-14, Week3: day 15-21, Week4: day 22-28

3. PRODUCTIVITY: data_qty / data_hours / Norms * 100

4. RIGCODE FILTER: Always use Revenue.rigcode for NL0010, NF0010 etc - NOT well_location

5. PROJECT CLUSTER: LEFT(Project, 1) = 'M' → 'MML', 'N' → 'NIM'

6. MOC STATUS: moc_raised IN ('YES', 'Yes', 'yes')
"""


def get_view_logic(view_name: str) -> dict:
    """Get parsed logic for a view."""
    return VIEW_LOGIC.get(view_name, {})


def get_column_hint(column_name: str) -> str:
    """Get hint for column usage."""
    for key, hint in COLUMN_MAPPINGS.items():
        if key.lower() in column_name.lower():
            return hint
    return ""


if __name__ == "__main__":
    # Save as JSON for DSPy
    with open("appmaster_knowledge_base.json", "w", encoding="utf-8") as f:
        json.dump({
            "view_logic": VIEW_LOGIC,
            "column_mappings": COLUMN_MAPPINGS,
            "training_hints": TRAINING_HINTS
        }, f, indent=2)
    
    print("="*70)
    print("APPMASTERDB KNOWLEDGE BASE CREATED")
    print("="*70)
    print(f"\nViews parsed: {len(VIEW_LOGIC)}")
    for name, info in VIEW_LOGIC.items():
        print(f"  - {name}: {info['purpose'][:50]}...")
    print(f"\nColumn mappings: {len(COLUMN_MAPPINGS)}")
    print("\nThis knowledge base can be used to:")
    print("  1. Train DSPy with correct SQL patterns")
    print("  2. Validate generated SQL against business logic")
    print("  3. Explain query results to users")

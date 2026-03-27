"""
Build Knowledge Base from Client's AppMasterDB Views
====================================================
Extracts schema, relationships, and business logic from SQL view definitions.
"""

import re
import csv
import os
from pathlib import Path

# ============================================================================
# APPMASTERDB VIEW DEFINITIONS
# ============================================================================

VIEWS = {
    "New_Daily_Plan": {
        "database": "AppMasterDB",
        "source": "dbo.vw_New_Daily_Plan",
        "description": "Daily planning view - retrieves daily work plan data",
        "tables_used": ["dbo.vw_New_Daily_Plan"],
        "columns": [
            ("Sl.No", "int", "Row number"),
            ("ATNM/SC", "nvarchar", "ATNM/SC identifier"),
            ("Discipline", "nvarchar", "Discipline (nullable)"),
            ("Well ID", "nvarchar", "Well identifier"),
            ("PA Name", "nvarchar", "Permit Applicant Name"),
            ("PA Mob No", "nvarchar", "PA Mobile Number"),
            ("PH Emp ID", "nvarchar", "PH Employee ID"),
            ("PH Name", "nvarchar", "PH Name"),
            ("PH Mob No", "nvarchar", "PH Mobile Number"),
            ("PO No", "nvarchar", "PO/WBS Number"),
            ("WBS", "nvarchar", "Work Breakdown Structure"),
            ("Well Category", "nvarchar", "Category of well"),
            ("Location", "nvarchar", "Location"),
            ("Job Title / Project Name", "nvarchar", "Job or project name"),
            ("Activities", "nvarchar", "Activity description"),
            ("Manpower", "nvarchar", "Manpower count"),
            ("Eqpt", "nvarchar", "Equipment"),
            ("Vehicle", "nvarchar", "Vehicle"),
            ("Remarks", "nvarchar", "Additional remarks")
        ]
    },

    "Daily_Plan_Report": {
        "database": "AppMasterDB",
        "source": "dbo.vw_DailyWorkPlanC_TodayReport",
        "description": "Daily plan report with crew and location details",
        "tables_used": ["dbo.vw_DailyWorkPlanC_TodayReport"],
        "columns": [
            ("Sl.No", "int", "Serial number"),
            ("ATNM/SC", "nvarchar", "ATNM/SC"),
            ("Discipline", "nvarchar", "Discipline"),
            ("Well ID", "nvarchar", "Well ID"),
            ("PA Name", "nvarchar", "Permit Applicant Name"),
            ("PH Emp ID", "nvarchar", "PH Employee ID"),
            ("PH Name", "nvarchar", "PH Name"),
            ("PO No", "nvarchar", "PO Number"),
            ("Well Category", "nvarchar", "Well category"),
            ("Location", "nvarchar", "Location"),
            ("Job Title / Project Name", "nvarchar", "Project name"),
            ("Activities", "nvarchar", "Activities/Task description"),
            ("Manpower", "nvarchar", "Manpower required"),
            ("Eqpt", "nvarchar", "Equipment"),
            ("Vehicle", "nvarchar", "Vehicles")
        ]
    },

    "vw_JOB_COST": {
        "database": "AppMasterDB",
        "source": "Complex view joining task_daily, Revenue, crews, Employee, Equipment",
        "description": "Job cost tracking - compares planned vs actual for employees and equipment",
        "tables_used": [
            "dbo.task_daily",
            "dbo.Revenue", 
            "dbo.crews",
            "dbo.Employee",
            "dbo.company_employees",
            "dbo.EmployeeType",
            "dbo.Equipment",
            "dbo.EquipmentType",
            "dbo.ActivityMasterMapping"
        ],
        "columns": [
            ("sr.no", "int", "Serial number"),
            ("Plant/ Location", "nvarchar", "Plant or location (MML/NIM derived from Project)"),
            ("Project", "nvarchar", "Project - links to Revenue.rigcode"),
            ("Well ID", "nvarchar", "Well identifier"),
            ("Activity ID", "nvarchar", "Activity code (first 8 chars)"),
            ("Activity Code", "nvarchar", "Mapped activity code from ActivityMasterMapping"),
            ("Action On", "date", "Action date"),
            ("start_date", "date", "Planned start date"),
            ("end_date", "date", "Planned end date"),
            ("target_start", "datetime", "Target start"),
            ("target_end", "datetime", "Target end"),
            ("actual_start", "datetime", "Actual start"),
            ("actual_end", "datetime", "Actual end"),
            ("crew type", "nvarchar", "Crew type"),
            ("crew code", "nvarchar", "Crew code"),
            ("Plan Employee Name/ Equipment Name", "nvarchar", "Planned resource name"),
            ("Plan Employee ID/ Equipment ID/Plate No", "nvarchar", "Planned resource ID"),
            ("Plan PG / EG Code", "nvarchar", "Planned payment group code"),
            ("Plan PG / EG Text", "nvarchar", "Planned payment group description"),
            ("Actual Employee / Equipment Name", "nvarchar", "Actual resource name"),
            ("Actual Employee ID/ Equipment ID/Plate No", "nvarchar", "Actual resource ID"),
            ("Actual PG/EG Code", "nvarchar", "Actual PG code"),
            ("Actual PG/EG Text", "nvarchar", "Actual PG description"),
            ("Effective Work Hours", "decimal", "Effective work hours from JSON")
        ],
        "joins": [
            ("task_daily.well_id", "Revenue.well_id", "LEFT JOIN - get rigcode"),
            ("crews.Code", "task_daily.crew_code", "LEFT JOIN - crew details"),
            ("Employee.id", "company_employees.id", "LEFT JOIN - employee details"),
            ("EmployeeType.Code", "company_employees.code", "LEFT JOIN - employee type"),
            ("Equipment.LicensePlate", "equipment_ids", "LEFT JOIN - equipment"),
            ("ActivityMasterMapping.ActivityID", "left 8 chars of task_code", "Activity mapping")
        ]
    },

    "WellMonitoringReport": {
        "database": "AppMasterDB",
        "source": "Complex view - multiple CTEs joining WMR, TaskPlan, DesignTracker, SAP, Revenue, Crews",
        "description": "Comprehensive well monitoring with progress, MOC, dates, SAP data",
        "tables_used": [
            "dbo.WMR",
            "dbo.WMR_TaskPlan_csv_imported",
            "dbo.DesignTrackerCSVImport",
            "dbo.SAP_DRILLING_SEQUENCE", 
            "dbo.Revenue",
            "dbo.crews"
        ],
        "key_columns": [
            ("pdo_well_id", "nvarchar", "PDO well identifier - PRIMARY KEY"),
            ("well_name_after_spud", "nvarchar", "Official well name"),
            ("well_location", "nvarchar", "Location"),
            ("Cluster", "nvarchar", "Nimr or Marmul"),
            ("rig_no", "nvarchar", "Rig number"),
            ("well_type", "nvarchar", "ESP, OP, WI"),
            ("over_all_progress_percentages", "decimal", "Overall progress 0-1"),
            ("moc_raised", "nvarchar", "MOC raised YES/No"),
            ("moc_approved", "nvarchar", "MOC approved YES/No"),
            ("actual_rig_on_date", "date", "Rig arrival"),
            ("actual_rig_off_date", "date", "Rig departure")
        ]
    },

    "vw_JobProgress": {
        "database": "AppMasterDB",
        "source": "ActivityTaskPlan, ProjectIDs, WMR",
        "description": "Weekly job progress with plan vs actual bucketed by week",
        "tables_used": [
            "dbo.ActivityTaskPlan",
            "dbo.ProjectIDs",
            "dbo.WMR"
        ],
        "columns": [
            ("Sl.No", "int", "Serial number"),
            ("Category", "nvarchar", "Project category from ProjectIDs.column2"),
            ("Well ID / Project ID", "int", "Well ID"),
            ("Well Name / Project Name", "nvarchar", "Well name"),
            ("PO No - Location", "nvarchar", "Location PO"),
            ("PO No - FlowLine", "nvarchar", "Flowline PO"),
            ("WBS No - Location", "nvarchar", "Location WBS"),
            ("WBS No - FlowLine", "nvarchar", "Flowline WBS"),
            ("Cum-Prior Month Plan %", "decimal", "Cumulative prior month plan"),
            ("Cum-Prior Month Actual %", "decimal", "Cumulative prior month actual"),
            ("Week-1 Plan %", "decimal", "Week 1 plan"),
            ("Week-1 Actual %", "decimal", "Week 1 actual"),
            ("Week-2 Plan %", "decimal", "Week 2 plan"),
            ("Week-2 Actual %", "decimal", "Week 2 actual"),
            ("Week-3 Plan %", "decimal", "Week 3 plan"),
            ("Week-3 Actual %", "decimal", "Week 3 actual"),
            ("Week-4 Plan %", "decimal", "Week 4 plan"),
            ("Week-4 Actual %", "decimal", "Week 4 actual"),
            ("Current Month Plan %", "decimal", "Current month total plan"),
            ("Current Month Actual %", "decimal", "Current month total actual")
        ]
    },

    "PH_Productivity": {
        "database": "AppMasterDB",
        "source": "task_daily, Employee, ActivityCodesNorms, CrewType",
        "description": "Productivity tracking per PH (QHSE Supervisor) and Crew",
        "tables_used": [
            "dbo.task_daily",
            "dbo.Employee",
            "dbo.ActivityCodesNorms",
            "dbo.CrewType"
        ],
        "columns": [
            ("Year", "int", "Year"),
            ("Month", "int", "Month"),
            ("PA Name", "nvarchar", "Permit Applicant name (from task_assignee email)"),
            ("PH Name", "nvarchar", "QHSE Supervisor name (from supervisor_email)"),
            ("Crew Name", "nvarchar", "Crew type description"),
            ("Crew Type", "nvarchar", "Crew type code"),
            ("Category", "nvarchar", "Category from ProjectIDs"),
            ("Sub_Contractor", "nvarchar", "Subcontractor"),
            ("Avg_Productivity_Pct", "decimal", "Average productivity percentage"),
            ("W1_PI_T_Wise", "decimal", "Week 1 Productivity Index T-Wise"),
            ("W1_PI_CMR", "decimal", "Week 1 Productivity Index CMR"),
            ("W2_PI_T_Wise", "decimal", "Week 2 Productivity Index T-Wise"),
            ("W2_PI_CMR", "decimal", "Week 2 Productivity Index CMR"),
            ("Month_PI_T_Wise", "decimal", "Month Productivity Index T-Wise"),
            ("Month_PI_CMR", "decimal", "Month Productivity Index CMR")
        ]
    }
}

# ============================================================================
# RELATIONSHIPS BETWEEN VIEWS AND TABLES
# ============================================================================

VIEW_RELATIONSHIPS = """
KEY RELATIONSHIPS:

1. WellMonitoringReport (AppMasterDB) → ATNM_Dev
   - pdo_well_id (WMR) = pdo_well_id (WellMonitoringReport)
   - Links to: Revenue.Well_ID, SAP_DRILLING_SEQUENCE.Well_ID

2. task_daily (AppMasterDB) → ATNM_Dev
   - well_id (task_daily) = Revenue.Well_ID (for rigcode/project)
   - Links to: crews (crew_code), Employee (via company_employees)

3. Job Progress Flow:
   ActivityTaskPlan → ProjectIDs (category) → WMR (well details)
   
4. Productivity Flow:
   task_daily → Employee (supervisor_email → Name) → company_employees → EmployeeType

5. Job Cost Flow:
   task_daily → Revenue (well_id + activity) → crews → Employee/Equipment
"""


def generate_csv_entries():
    """Generate CSV entries for BM25 index."""
    entries = []
    
    for view_name, view_info in VIEWS.items():
        # Add view entry
        entries.append({
            "tableName": f"AppMasterDB.dbo.{view_name}",
            "columnName": "*",
            "dataType": "VIEW",
            "description": f"VIEW in {view_info['database']}: {view_info['description']}. Source: {view_info['source']}"
        })
        
        # Add columns
        for col in view_info.get("columns", []):
            entries.append({
                "tableName": f"AppMasterDB.dbo.{view_name}",
                "columnName": col[0],
                "dataType": col[1],
                "description": f"VIEW column: {col[2]}"
            })
        
        # Add key columns for WellMonitoringReport
        if view_name == "WellMonitoringReport":
            for col in view_info.get("key_columns", []):
                entries.append({
                    "tableName": "AppMasterDB.dbo.WellMonitoringReport",
                    "columnName": col[0],
                    "dataType": col[1],
                    "description": f"KEY COLUMN: {col[2]}"
                })
    
    return entries


def save_to_csv(output_path: str):
    """Save AppMasterDB schema to CSV."""
    entries = generate_csv_entries()
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["tableName", "columnName", "dataType", "description"])
        writer.writeheader()
        writer.writerows(entries)
    
    print(f"Created {len(entries)} entries in {output_path}")
    return entries


def generate_neo4j_queries():
    """Generate Neo4j queries to add AppMasterDB schema."""
    
    queries = []
    
    for view_name, view_info in VIEWS.items():
        # Create view node
        queries.append(f"""
        MERGE (v:View {{name: 'AppMasterDB.dbo.{view_name}', database: '{view_info['database']}', description: '{view_info['description']}'}})
        """)
        
        # Add source relationship
        for table in view_info.get("tables_used", []):
            table_clean = table.replace("dbo.", "")
            queries.append(f"""
            MATCH (v:View {{name: 'AppMasterDB.dbo.{view_name}'}})
            MATCH (t:Table {{name: '{table}'}})
            MERGE (v)-[:DERIVED_FROM]->(t)
            """)
    
    return queries


if __name__ == "__main__":
    # Save CSV for BM25
    entries = save_to_csv("appmasterdb_schema.csv")
    
    # Print summary
    print("\n" + "="*70)
    print("APPMASTERDB SCHEMA SUMMARY")
    print("="*70)
    
    for view_name, view_info in VIEWS.items():
        print(f"\n{view_name}:")
        print(f"  Description: {view_info['description']}")
        print(f"  Tables used: {', '.join(view_info.get('tables_used', []))}")
        if "columns" in view_info:
            print(f"  Columns: {len(view_info['columns'])}")
        if "key_columns" in view_info:
            print(f"  Key columns: {len(view_info['key_columns'])}")
    
    print("\n" + "="*70)
    print("RELATIONSHIPS")
    print("="*70)
    print(VIEW_RELATIONSHIPS)

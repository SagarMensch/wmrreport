"""
Enhanced Schema Knowledge Base Builder
========================================
Creates deeply semantic, business-context-rich descriptions for every column.
This enables accurate BM25 and Vector search for SQL generation.
"""

import csv
import json
import os
from datetime import datetime

# ============================================================================
# COMPREHENSIVE COLUMN SEMANTIC DEFINITIONS
# ============================================================================

COLUMN_SEMANTICS = {
    # =========================================================================
    # WELL MONITORING TABLES - Core Well Data
    # =========================================================================
    
    "WellMonitoringReport": {
        "pdo_well_id": {
            "semantic_name": "PDO Well Identifier",
            "business_meaning": "The unique Petroleum Development Oman assigned identifier for each well. This is the PRIMARY JOIN KEY for linking well data across Revenue, SAP_DRILLING_SEQUENCE, Job_Progress tables.",
            "usage": "Use for counting unique wells (COUNT DISTINCT), joining tables, identifying specific wells.",
            "example": "34422, 31339, 37797",
            "common_queries": ["count wells", "well details", "join with revenue", "well id"],
            "critical": True
        },
        "well_name_after_spud": {
            "semantic_name": "Official Well Name",
            "business_meaning": "The formal name assigned to the well after spudding (drilling begins). Used for display and SAP linking.",
            "usage": "Display well names, join with SAP_DRILLING_SEQUENCE.Well_Name",
            "example": "AL BURJ-280, AMIN-580, NIMR-1693",
            "common_queries": ["show wells", "well name", "display well"]
        },
        "well_location": {
            "semantic_name": "Physical Well Location",
            "business_meaning": "The geographic location identifier where the well is located. Contains detailed location codes like AL BURJ_26_MC_OP2. NOT for rig codes!",
            "usage": "Filter by specific locations, show location details. NOT for rig filtering.",
            "example": "AL BURJ_26_MC_OP2, NIMRG_2205240004_AP2, AMIN_3946610_OP23",
            "warning": "Do NOT use for rig codes like NL0010 - those are in Revenue.rigcode",
            "common_queries": ["location", "where is well"]
        },
        "rig_no": {
            "semantic_name": "Rig Number",
            "business_meaning": "The identifier of the drilling rig assigned to this well. Links to crews table via rig_code.",
            "usage": "Filter by rig, track rig performance, join with crews",
            "example": "SWER101, SWER149, SWERIG99",
            "common_queries": ["rig performance", "which rig", "rig assignment"]
        },
        "Cluster": {
            "semantic_name": "Operational Cluster",
            "business_meaning": "The operational area/cluster the well belongs to. Major clusters are Nimr and Marmul.",
            "usage": "Filter by cluster for regional analysis",
            "example": "Nimr, Marmul",
            "common_queries": ["cluster", "Nimr wells", "Marmul wells", "area"]
        },
        "well_type": {
            "semantic_name": "Well Type",
            "business_meaning": "The classification of well based on its purpose and equipment.",
            "usage": "Categorize wells by type for analysis",
            "example": "ESP (Electric Submersible Pump), PCP (Progressive Cavity Pump), OP (Oil Producer), WI (Water Injector)",
            "common_queries": ["well type", "ESP wells", "producer"]
        },
        "over_all_progress_percentages": {
            "semantic_name": "Overall Well Progress",
            "business_meaning": "The cumulative completion percentage of the well project (0-1 decimal scale). Multiply by 100 for percentage.",
            "usage": "Track overall project completion, calculate completion rates",
            "example": "0.63 = 63% complete, 1.0 = 100% complete",
            "common_queries": ["progress", "completion", "how far along"]
        },
        "cum_progress_for_this_week": {
            "semantic_name": "Weekly Cumulative Progress",
            "business_meaning": "The cumulative drilling progress achieved this week (decimal 0-1).",
            "usage": "Weekly progress tracking",
            "example": "0.58, 0.35, 1.0"
        },
        "actual_rig_on_date": {
            "semantic_name": "Rig Arrival Date",
            "business_meaning": "The actual date when the drilling rig was moved onto the well location.",
            "usage": "Track rig schedule, calculate rig days",
            "common_queries": ["rig on", "when did rig arrive"]
        },
        "actual_rig_off_date": {
            "semantic_name": "Rig Departure Date",
            "business_meaning": "The actual date when the drilling rig moved off the well location.",
            "usage": "Track rig completion, calculate rig duration",
            "common_queries": ["rig off", "when did rig leave"]
        },
        "actual_start_date": {
            "semantic_name": "Actual Start Date",
            "business_meaning": "The actual date when work began on the well.",
            "usage": "Schedule tracking, duration calculation",
            "common_queries": ["start date", "when started"]
        },
        "actual_finish_date": {
            "semantic_name": "Completion Date",
            "business_meaning": "The actual date when well work was completed.",
            "usage": "Completion tracking, deadline analysis",
            "common_queries": ["finish date", "completion", "when done"]
        },
        "scr_no": {
            "semantic_name": "Sequence Change Request Number",
            "business_meaning": "Document number for Sequence Change Request (SCR) - tracks schedule changes.",
            "usage": "Track schedule changes, SCR management",
            "common_queries": ["SCR", "schedule change", "sequence"]
        },
        "flaf_issue_date": {
            "semantic_name": "FLAF Issue Date",
            "business_meaning": "Date when the First Line Acceptable Form (FLAF) was issued - key milestone.",
            "usage": "Track key milestone, readiness dates",
            "common_queries": ["FLAF", "milestone", "ready"]
        }
    },

    # =========================================================================
    # REVENUE TABLE - Progress Tracking
    # =========================================================================
    
    "Revenue": {
        "well_id": {
            "semantic_name": "Revenue Well ID",
            "business_meaning": "The well identifier linking to WellMonitoringReport.pdo_well_id. This is the JOIN KEY for Revenue data.",
            "usage": "Join with WellMonitoringReport, identify wells in revenue data",
            "critical_join": "WellMonitoringReport.pdo_well_id = Revenue.Well_ID",
            "example": "37230, 31339"
        },
        "rigcode": {
            "semantic_name": "Rig Code",
            "business_meaning": "CRITICAL: The identifier for the drilling rig. NOT a location! Use for filtering by rig names like NL0010, NF0010. This is NOT in well_location!",
            "usage": "Filter by rig identifier, analyze rig performance. NEVER use well_location for this!",
            "example": "NL0010, NF0010, ML0010, MS0010, MF0010, MCOF10, MCWF10, MROP10, MRWF10, NCOF10, NNSW10, NS0010",
            "critical": True,
            "warning": "This is RIG CODE, not location. Do NOT search in well_location for NL0010!",
            "common_queries": ["rig NL0010", "wells by rig", "rig performance", "NF0010"]
        },
        "acutal_progress": {
            "semantic_name": "Actual Progress",
            "business_meaning": "The actual progress achieved (note: column name is misspelled as 'acutal'). Decimal value representing completion.",
            "usage": "Compare actual vs planned, track achievement",
            "data_type_note": "This column is correctly spelled as decimal",
            "example": "1.0000, 0.5"
        },
        "planned_progress": {
            "semantic_name": "Planned Progress",
            "business_meaning": "The planned progress target. CRITICAL: This is NVARCHAR (text) type - must CAST to DECIMAL before comparison or SUM!",
            "usage": "Compare with actual, calculate variance. MUST CAST to DECIMAL!",
            "data_type_warning": "NVARCHAR - requires TRY_CAST(planned_progress AS DECIMAL(10,2)) before use",
            "critical": True,
            "example": "'1', '0.93' (stored as text)"
        },
        "actual_purpose_value": {
            "semantic_name": "Actual Revenue/Purpose Value",
            "business_meaning": "The actual monetary value or purpose value achieved. Decimal type.",
            "usage": "Calculate actual revenue, achievement rates",
            "example": "5000.00, 0.00"
        },
        "planned_purpose_value": {
            "semantic_name": "Planned Revenue/Purpose Value",
            "business_meaning": "CRITICAL: The planned monetary target. This is NVARCHAR (text) - must CAST to DECIMAL before SUM!",
            "usage": "Calculate planned revenue, achievement rates. MUST CAST before SUM!",
            "data_type_warning": "NVARCHAR - requires TRY_CAST(planned_purpose_value AS DECIMAL(18,2)) before SUM",
            "critical": True,
            "example": "'5000', '0' (stored as text)"
        },
        "Title": {
            "semantic_name": "Task/Activity Title",
            "business_meaning": "The description/title of the revenue-generating activity or task.",
            "usage": "Understand what activities generate revenue",
            "example": "RDX, Wadi Crossing, Welding Jo"
        }
    },

    # =========================================================================
    # SAP DRILLING SEQUENCE - SAP Integration
    # =========================================================================
    
    "SAP_DRILLING_SEQUENCE": {
        "Well_ID": {
            "semantic_name": "SAP Well ID",
            "business_meaning": "The well identifier in SAP system. Links to WellMonitoringReport.pdo_well_id.",
            "usage": "Join with WellMonitoringReport, SAP integration",
            "critical_join": "WellMonitoringReport.pdo_well_id = SAP_DRILLING_SEQUENCE.Well_ID",
            "example": "10207, 10239"
        },
        "Well_Name": {
            "semantic_name": "SAP Well Name",
            "business_meaning": "The well name as recorded in SAP system.",
            "usage": "SAP integration, join with WellMonitoringReport.well_name_after_spud",
            "critical_join": "WellMonitoringReport.well_name_after_spud = SAP_DRILLING_SEQUENCE.Well_Name",
            "example": "RKDS_2026_OP_LOC18, DMB-LSB-OP-3"
        },
        "Well_Location": {
            "semantic_name": "SAP Well Location",
            "business_meaning": "The location of the well in SAP system.",
            "usage": "SAP location tracking",
            "example": "RKDS_2026_OP_LOC18"
        },
        "Field": {
            "semantic_name": "Oil Field Name",
            "business_meaning": "The name of the oil field where the well is located.",
            "usage": "Filter by field, regional analysis",
            "example": "RAKID SOUTH, NIMR, FAHUD, DHULAIMA",
            "common_queries": ["field", "which field", "RAKID", "NIMR"]
        },
        "Well_Function": {
            "semantic_name": "Well Function",
            "business_meaning": "The purpose/type of well in terms of its function.",
            "usage": "Categorize wells by function",
            "example": "Oil Producer, Water Injector, Gas Producer",
            "common_queries": ["producer", "injector", "well purpose"]
        },
        "Well_Category": {
            "semantic_name": "Well Category",
            "business_meaning": "Classification category of the well.",
            "usage": "Well classification",
            "example": "Development, Exploration, Appraisal"
        },
        "Opr_System_status": {
            "semantic_name": "Operational Status",
            "business_meaning": "The operational status in SAP system.",
            "usage": "Track operational status",
            "example": "REL (Released), CNF (Confirmed)"
        },
        "PDO_Well_Type": {
            "semantic_name": "PDO Well Type Code",
            "business_meaning": "The PDO classification code for well type.",
            "usage": "Well type identification",
            "example": "NPS9723PCVH, NP9724WIVABH"
        }
    },

    # =========================================================================
    # JOB PROGRESS TABLES - Weekly Tracking
    # =========================================================================
    
    "Job_Progress_Report_GB": {
        "Well ID": {
            "semantic_name": "Job Progress Well ID",
            "business_meaning": "The well identifier in Job Progress report. Links to WellMonitoringReport.pdo_well_id.",
            "usage": "Join with WellMonitoringReport",
            "critical_join": "WellMonitoringReport.pdo_well_id = Job_Progress_Report_GB.[Well ID]",
            "note": "Use brackets due to space in column name",
            "example": "628, 729"
        },
        "Well Name / Project Name": {
            "semantic_name": "Well or Project Name",
            "business_meaning": "Human-readable name of the well or project (often NULL).",
            "usage": "Display names (when available)",
            "note": "Frequently NULL in data"
        },
        "Week-1 Actual %": {
            "semantic_name": "Week 1 Actual Progress",
            "business_meaning": "Actual progress achieved in week 1 (percentage).",
            "usage": "Weekly tracking, variance analysis",
            "example": "0.00, 14.17"
        },
        "Week-1 Plan %": {
            "semantic_name": "Week 1 Planned Progress",
            "business_meaning": "Planned progress target for week 1 (percentage).",
            "usage": "Weekly planning, variance analysis",
            "example": "0.33, 13.70"
        },
        "Current Month Plan %": {
            "semantic_name": "Monthly Planned Progress",
            "business_meaning": "Planned progress for the current month (percentage).",
            "usage": "Monthly tracking",
            "example": "74.69"
        },
        "Current Month Actual %": {
            "semantic_name": "Monthly Actual Progress",
            "business_meaning": "Actual progress achieved this month (percentage).",
            "usage": "Monthly tracking",
            "example": "0.00, 17.79"
        },
        "Purpose Value": {
            "semantic_name": "Purpose/Monetary Value",
            "business_meaning": "The monetary value or purpose value associated with the job.",
            "usage": "Financial tracking, value analysis",
            "example": "5000.00, 17059.40"
        },
        "Category": {
            "semantic_name": "Job Category",
            "business_meaning": "Category of the job/work.",
            "usage": "Categorize jobs",
            "example": "Marmul SNLP, Marmul Conversion with Flowlin"
        }
    },

    "Job_Progress_PlanSnapshot": {
        "Well_ID": {
            "semantic_name": "Plan Snapshot Well ID",
            "business_meaning": "The well identifier for planning snapshot. Links to WellMonitoringReport.pdo_well_id.",
            "usage": "Join with WellMonitoringReport, planning data",
            "critical_join": "WellMonitoringReport.pdo_well_id = Job_Progress_PlanSnapshot.Well_ID",
            "example": "10207, 10239"
        },
        "W1_Plan_frac": {
            "semantic_name": "Week 1 Plan Fraction",
            "business_meaning": "Planned progress as fraction (decimal) for week 1.",
            "usage": "Weekly planning fraction",
            "example": "0.01177941"
        },
        "CurrentMonthPlanFrac": {
            "semantic_name": "Monthly Plan Fraction",
            "business_meaning": "Current month planned progress as fraction.",
            "usage": "Monthly planning",
            "example": "0.73209502"
        },
        "Latest_Target_End": {
            "semantic_name": "Target End Date",
            "business_meaning": "The latest target end date for the well.",
            "usage": "Deadline tracking",
            "example": "2026-05-11"
        }
    },

    # =========================================================================
    # CREWS TABLE - Resource Management
    # =========================================================================
    
    "crews": {
        "Code": {
            "semantic_name": "Crew Code",
            "business_meaning": "Unique identifier for the crew/team.",
            "usage": "Identify crews",
            "critical_join": "WellMonitoringReport.rig_no = crews.rig_code"
        },
        "CrewType": {
            "semantic_name": "Crew Type",
            "business_meaning": "Type/classification of the crew.",
            "usage": "Categorize crews"
        },
        "Supervisor": {
            "semantic_name": "Crew Supervisor",
            "business_meaning": "Name or ID of the crew supervisor.",
            "usage": "Contact, reporting"
        }
    },

    # =========================================================================
    # ACTIVITY & TASK TABLES
    # =========================================================================
    
    "ActivityTaskPlan": {
        "Well_ID": {
            "semantic_name": "Activity Well ID",
            "business_meaning": "The well identifier for this activity/task.",
            "usage": "Link activities to wells"
        },
        "project_id": {
            "semantic_name": "Project Identifier",
            "business_meaning": "The project this activity belongs to.",
            "usage": "Project filtering"
        },
        "progress": {
            "semantic_name": "Activity Progress",
            "business_meaning": "Progress percentage of this specific activity.",
            "usage": "Activity tracking"
        },
        "actual_start": {
            "semantic_name": "Actual Start",
            "business_meaning": "Actual start date/time of the activity.",
            "usage": "Schedule tracking"
        },
        "actual_end": {
            "semantic_name": "Actual End",
            "business_meaning": "Actual end date/time of the activity.",
            "usage": "Completion tracking"
        }
    },

    "task_daily": {
        "well_id": {
            "semantic_name": "Daily Task Well ID",
            "business_meaning": "The well identifier for daily task tracking.",
            "usage": "Link daily tasks to wells"
        },
        "project_id": {
            "semantic_name": "Project Identifier",
            "business_meaning": "Project this task belongs to.",
            "usage": "Project filtering"
        },
        "progress": {
            "semantic_name": "Task Progress",
            "business_meaning": "Completion progress of the task (decimal).",
            "usage": "Progress tracking"
        },
        "crew_code": {
            "semantic_name": "Crew Code",
            "business_meaning": "Code of the crew assigned to this task.",
            "usage": "Crew assignment tracking"
        }
    },

    # =========================================================================
    # WBS MASTER TRACKER
    # =========================================================================
    
    "WBS_Master_Tracker_": {
        "Cluster": {
            "semantic_name": "WBS Cluster",
            "business_meaning": "Operational cluster in WBS tracking.",
            "usage": "Cluster filtering"
        },
        "Well_ID_Project_PO": {
            "semantic_name": "WBS Well/Project ID",
            "business_meaning": "Well or project identifier in WBS.",
            "usage": "WBS linking"
        },
        "WBS_Code": {
            "semantic_name": "WBS Code",
            "business_meaning": "Work Breakdown Structure code.",
            "usage": "WBS identification"
        }
    }
}


# ============================================================================
# JOIN KEYS REFERENCE
# ============================================================================

JOIN_KEYS = {
    "WellMonitoringReport.pdo_well_id": [
        "Revenue.Well_ID",
        "SAP_DRILLING_SEQUENCE.Well_ID",
        "Job_Progress_Report_GB.[Well ID]",
        "Job_Progress_PlanSnapshot.Well_ID",
        "ActivityTaskPlan.Well_ID",
        "task_daily.well_id"
    ],
    "WellMonitoringReport.rig_no": [
        "crews.rig_code"
    ],
    "WellMonitoringReport.well_name_after_spud": [
        "SAP_DRILLING_SEQUENCE.Well_Name"
    ]
}


# ============================================================================
# CRITICAL RULES
# ============================================================================

CRITICAL_RULES = """
CRITICAL RULES FOR SQL GENERATION:

1. RIG CODE vs LOCATION:
   - NL0010, NF0010, ML0010, MS0010 are RIG CODES - use Revenue.rigcode
   - NEVER search for rig codes in well_location - returns ZERO results
   - CORRECT: WHERE r.rigcode = 'NL0010'
   - WRONG: WHERE w.well_location LIKE '%NL0010%'

2. JOIN KEYS:
   - WellMonitoringReport.pdo_well_id = Revenue.Well_ID
   - WellMonitoringReport.pdo_well_id = SAP_DRILLING_SEQUENCE.Well_ID
   - WellMonitoringReport.pdo_well_id = Job_Progress_Report_GB.[Well ID]
   - WellMonitoringReport.well_name_after_spud = SAP_DRILLING_SEQUENCE.Well_Name

3. TYPE CASTING:
   - Revenue.planned_progress is NVARCHAR - MUST CAST before comparison
   - Revenue.planned_purpose_value is NVARCHAR - MUST CAST before SUM
   - Use: TRY_CAST(column AS DECIMAL(10,2))

4. CLUSTER:
   - Use WellMonitoringReport.Cluster for Nimr/Marmul filtering
   - Example: WHERE Cluster = 'Nimr'

5. COUNTING WELLS:
   - ALWAYS use COUNT(DISTINCT pdo_well_id)
   - NEVER count well_name_after_spud (can have duplicates)
"""


def build_enhanced_documents(csv_path: str, output_path: str):
    """Build enhanced BM25 documents with rich semantic descriptions."""
    
    documents = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    for row in rows:
        table = row.get('tableName', '')
        column = row.get('columnName', '')
        data_type = row.get('dataType', '')
        
        # Get semantic info if available
        semantic = COLUMN_SEMANTICS.get(table, {}).get(column, {})
        
        # Build rich document text
        doc_parts = [
            f"Table: {table}",
            f"Column: {column}",
            f"Data Type: {data_type}",
        ]
        
        if semantic:
            doc_parts.extend([
                f"Semantic Name: {semantic.get('semantic_name', '')}",
                f"Business Meaning: {semantic.get('business_meaning', '')}",
                f"Usage: {semantic.get('usage', '')}",
            ])
            
            if semantic.get('example'):
                doc_parts.append(f"Example: {semantic['example']}")
            
            if semantic.get('critical'):
                doc_parts.append("CRITICAL: This is a key column!")
                
            if semantic.get('warning'):
                doc_parts.append(f"WARNING: {semantic['warning']}")
                
            if semantic.get('critical_join'):
                doc_parts.append(f"JOIN: {semantic['critical_join']}")
        
        # Add common query terms
        if semantic and semantic.get('common_queries'):
            doc_parts.append(f"Search Terms: {', '.join(semantic['common_queries'])}")
        
        document = {
            "table": table,
            "column": column,
            "data_type": data_type,
            "document": " | ".join(doc_parts),
            "semantic": semantic
        }
        
        documents.append(document)
    
    # Save enhanced documents
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(documents, f, indent=2)
    
    print(f"Created {len(documents)} enhanced documents")
    return documents


def get_column_hints():
    """Generate column hints for DSPy prompt."""
    hints = []
    
    for table, cols in COLUMN_SEMANTICS.items():
        for col, sem in cols.items():
            if sem.get('critical') or sem.get('warning'):
                hints.append({
                    "table": table,
                    "column": col,
                    "hint": sem.get('warning') or sem.get('business_meaning', '')[:100]
                })
    
    return hints


if __name__ == "__main__":
    # Build enhanced documents
    docs = build_enhanced_documents(
        "columns_atnm_dev.csv",
        "enhanced_schema_documents.json"
    )
    
    # Save hints
    hints = get_column_hints()
    with open("column_hints.json", 'w') as f:
        json.dump(hints, f, indent=2)
    
    print(f"\nCritical hints: {len(hints)}")
    for h in hints[:5]:
        print(f"  {h['table']}.{h['column']}: {h['hint'][:60]}...")
    
    print("\nDone!")

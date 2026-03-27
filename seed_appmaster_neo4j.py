"""
Comprehensive Neo4j Seeder for AppMasterDB + ATNM_Dev
=====================================================
Creates complete graph with:
- All views from AppMasterDB
- All tables from ATNM_Dev  
- Rich relationships between them
- Semantic descriptions for MiniLM embeddings
- BM25-ready descriptions
"""

import json
import csv
from neo4j import GraphDatabase

URI = "neo4j+s://4ba6a45a.databases.neo4j.io"
AUTH = ("4ba6a45a", "M_191EiDn_UIQBWy1RN24A2yJSWnzyhJogUoiRqV69s")

# ============================================================================
# COMPREHENSIVE VIEW DEFINITIONS WITH SEMANTICS
# ============================================================================

VIEWS = {
    # View 1: WellMonitoringReport - Main well tracking
    "AppMasterDB.dbo.WellMonitoringReport": {
        "type": "VIEW",
        "database": "AppMasterDB",
        "description": "Comprehensive well monitoring with progress, MOC, dates, SAP data. Links to ATNM_Dev tables via pdo_well_id.",
        "semantic_search": "well progress monitoring MOC management change rig schedule timeline",
        "columns": {
            "pdo_well_id": {"type": "nvarchar", "semantic": "PRIMARY KEY - unique PDO well identifier. Join with ATNM_Dev.WellMonitoringReport.pdo_well_id, Revenue.Well_ID, SAP_DRILLING_SEQUENCE.Well_ID"},
            "well_name_after_spud": {"type": "nvarchar", "semantic": "Official well name after drilling begins"},
            "well_location": {"type": "nvarchar", "semantic": "Geographic location - NOT for rig codes"},
            "Cluster": {"type": "nvarchar", "semantic": "Operational cluster: Nimr or Marmul"},
            "rig_no": {"type": "nvarchar", "semantic": "Drilling rig identifier - links to crews.Code"},
            "well_type": {"type": "nvarchar", "semantic": "Well type: ESP (Electric Submersible Pump), OP (Oil Producer), WI (Water Injector)"},
            "over_all_progress_percentages": {"type": "decimal", "semantic": "Overall completion 0-1 scale, multiply by 100 for percentage"},
            "moc_raised": {"type": "nvarchar", "semantic": "Management of Change raised status: YES or Yes"},
            "moc_approved": {"type": "nvarchar", "semantic": "Management of Change approved status: YES or Yes"},
            "actual_rig_on_date": {"type": "date", "semantic": "Date rig arrived at well location"},
            "actual_rig_off_date": {"type": "date", "semantic": "Date rig departed from well location"},
            "actual_start_date": {"type": "date", "semantic": "Actual work start date"},
            "actual_finish_date": {"type": "date", "semantic": "Actual completion date"}
        }
    },

    # View 2: vw_JobProgress - Weekly progress tracking
    "AppMasterDB.dbo.vw_JobProgress": {
        "type": "VIEW",
        "database": "AppMasterDB", 
        "description": "Weekly job progress with plan vs actual bucketed by week. Shows Category, Well details, PO numbers, and weekly plan/actual percentages.",
        "semantic_search": "job progress weekly plan actual target achievement productivity tracking",
        "columns": {
            "Category": {"type": "nvarchar", "semantic": "Project category from ProjectIDs - Marmul SNLP, Conversion etc"},
            "Well ID / Project ID": {"type": "int", "semantic": "PDO well identifier"},
            "Well Name / Project Name": {"type": "nvarchar", "semantic": "Human readable well name"},
            "PO No - Location": {"type": "nvarchar", "semantic": "Purchase Order number for location"},
            "PO No - FlowLine": {"type": "nvarchar", "semantic": "Purchase Order number for flowline"},
            "Week-1 Plan %": {"type": "decimal", "semantic": "Week 1 planned progress percentage"},
            "Week-1 Actual %": {"type": "decimal", "semantic": "Week 1 actual progress percentage"},
            "Week-2 Plan %": {"type": "decimal", "semantic": "Week 2 planned progress"},
            "Week-2 Actual %": {"type": "decimal", "semantic": "Week 2 actual progress"},
            "Week-3 Plan %": {"type": "decimal", "semantic": "Week 3 planned progress"},
            "Week-3 Actual %": {"type": "decimal", "semantic": "Week 3 actual progress"},
            "Week-4 Plan %": {"type": "decimal", "semantic": "Week 4 planned progress"},
            "Week-4 Actual %": {"type": "decimal", "semantic": "Week 4 actual progress"},
            "Current Month Plan %": {"type": "decimal", "semantic": "Total month planned progress"},
            "Current Month Actual %": {"type": "decimal", "semantic": "Total month actual progress achieved"}
        },
        "joins_to": ["ATNM_Dev.dbo.Job_Progress_Report_GB", "ATNM_Dev.dbo.Job_Progress_PlanSnapshot"]
    },

    # View 3: PH_Productivity - Productivity metrics
    "AppMasterDB.dbo.PH_Productivity": {
        "type": "VIEW",
        "database": "AppMasterDB",
        "description": "Productivity tracking per PH (QHSE Supervisor) and Crew. Calculates Productivity% = QtyPerHour / Norms * 100",
        "semantic_search": "productivity efficiency performance PH supervisor crew QHSE employee norms output",
        "columns": {
            "Year": {"type": "int", "semantic": "Year of productivity data"},
            "Month": {"type": "int", "semantic": "Month of productivity data"},
            "PA Name": {"type": "nvarchar", "semantic": "Permit Applicant name - extracted from task_assignee email before @"},
            "PH Name": {"type": "nvarchar", "semantic": "QHSE Supervisor name - from Employee.Email = supervisor_email"},
            "PH Emp ID": {"type": "nvarchar", "semantic": "Employee UID from Employee table"},
            "Crew Name": {"type": "nvarchar", "semantic": "Crew type description from CrewType"},
            "Crew Type": {"type": "nvarchar", "semantic": "Crew type code"},
            "Category": {"type": "nvarchar", "semantic": "Project category"},
            "Sub_Contractor": {"type": "nvarchar", "semantic": "Subcontractor name"},
            "Avg_Productivity_Pct": {"type": "decimal", "semantic": "Average productivity percentage - QtyPerHour / Norms * 100"},
            "W1_PI_T_Wise": {"type": "decimal", "semantic": "Week 1 Productivity Index T-Wise"},
            "W1_PI_CMR": {"type": "decimal", "semantic": "Week 1 Productivity Index CMR"},
            "Month_PI_T_Wise": {"type": "decimal", "semantic": "Month Productivity Index T-Wise"},
            "Month_PI_CMR": {"type": "decimal", "semantic": "Month Productivity Index CMR"}
        },
        "joins_to": ["AppMasterDB.dbo.Employee", "AppMasterDB.dbo.CrewType", "AppMasterDB.dbo.ActivityCodesNorms"]
    },

    # View 4: vw_JOB_COST - Cost tracking
    "AppMasterDB.dbo.vw_JOB_COST": {
        "type": "VIEW",
        "database": "AppMasterDB",
        "description": "Job cost tracking - compares planned vs actual resources (employees and equipment) per well per activity",
        "semantic_search": "job cost resource planning actual employee equipment hours rate budget",
        "columns": {
            "Project": {"type": "nvarchar", "semantic": "Project/rigcode from Revenue - links to NL0010, NF0010 etc"},
            "Well ID": {"type": "nvarchar", "semantic": "PDO well identifier"},
            "Activity ID": {"type": "nvarchar", "semantic": "Activity code (first 8 characters of task_code)"},
            "Activity Code": {"type": "nvarchar", "semantic": "Mapped activity code from ActivityMasterMapping"},
            "crew type": {"type": "nvarchar", "semantic": "Type of crew"},
            "crew code": {"type": "nvarchar", "semantic": "Crew identifier - links to crews.Code"},
            "Plan Employee Name": {"type": "nvarchar", "semantic": "Planned employee name from Employee table"},
            "Actual Employee Name": {"type": "nvarchar", "semantic": "Actual employee who worked"},
            "Plan PG / EG Code": {"type": "nvarchar", "semantic": "Planned Payment Group code"},
            "Actual PG/EG Code": {"type": "nvarchar", "semantic": "Actual Payment Group code"},
            "Effective Work Hours": {"type": "decimal", "semantic": "Hours extracted from JSON: employee_ids, equipment_ids"}
        },
        "joins_to": ["ATNM_Dev.dbo.Revenue", "ATNM_Dev.dbo.task_daily", "AppMasterDB.dbo.crews", "AppMasterDB.dbo.Employee"]
    },

    # View 5: Daily_Plan_Report
    "AppMasterDB.dbo.Daily_Plan_Report": {
        "type": "VIEW",
        "database": "AppMasterDB",
        "description": "Daily plan report with well, PA, PH, PO, location, activities",
        "semantic_search": "daily plan schedule activities manpower equipment vehicle location PO well",
        "columns": {
            "Well ID": {"type": "nvarchar", "semantic": "Well identifier"},
            "PA Name": {"type": "nvarchar", "semantic": "Permit Applicant name"},
            "PH Name": {"type": "nvarchar", "semantic": "QHSE Supervisor name"},
            "PO No": {"type": "nvarchar", "semantic": "Purchase Order number"},
            "Location": {"type": "nvarchar", "semantic": "Geographic location"},
            "Activities": {"type": "nvarchar", "semantic": "Activity/task description"},
            "Manpower": {"type": "nvarchar", "semantic": "Number of workers needed"},
            "Eqpt": {"type": "nvarchar", "semantic": "Equipment required"},
            "Vehicle": {"type": "nvarchar", "semantic": "Vehicles required"}
        }
    },

    # View 6: New_Daily_Plan
    "AppMasterDB.dbo.New_Daily_Plan": {
        "type": "VIEW",
        "database": "AppMasterDB",
        "description": "Daily planning view from vw_New_Daily_Plan",
        "semantic_search": "new daily plan schedule well permit applicant"
    }
}

# ============================================================================
# CROSS-DATABASE RELATIONSHIPS (AppMasterDB <-> ATNM_Dev)
# ============================================================================

RELATIONSHIPS = [
    # WellMonitoringReport links
    {
        "from_view": "AppMasterDB.dbo.WellMonitoringReport",
        "from_column": "pdo_well_id",
        "to_table": "ATNM_Dev.dbo.WellMonitoringReport", 
        "to_column": "pdo_well_id",
        "type": "MIRRORS",
        "description": "AppMasterDB view mirrors ATNM_Dev table"
    },
    {
        "from_view": "AppMasterDB.dbo.WellMonitoringReport",
        "from_column": "pdo_well_id",
        "to_table": "ATNM_Dev.dbo.Revenue",
        "to_column": "Well_ID",
        "type": "HAS_REVENUE",
        "description": "Well links to Revenue for progress tracking"
    },
    {
        "from_view": "AppMasterDB.dbo.WellMonitoringReport",
        "from_column": "rig_no",
        "to_table": "ATNM_Dev.dbo.crews",
        "to_column": "Code",
        "type": "ASSIGNED_RIG",
        "description": "Well assigned to rig/crew"
    },

    # vw_JobProgress links
    {
        "from_view": "AppMasterDB.dbo.vw_JobProgress",
        "from_column": "Well ID / Project ID",
        "to_table": "ATNM_Dev.dbo.WellMonitoringReport",
        "to_column": "pdo_well_id",
        "type": "HAS_JOB_PROGRESS",
        "description": "Well has weekly job progress data"
    },
    {
        "from_view": "AppMasterDB.dbo.vw_JobProgress",
        "from_column": "Category",
        "to_table": "ATNM_Dev.dbo.ProjectIDs",
        "to_column": "column2",
        "type": "IN_CATEGORY",
        "description": "Project category from ProjectIDs"
    },

    # vw_JOB_COST links
    {
        "from_view": "AppMasterDB.dbo.vw_JOB_COST",
        "from_column": "Project",
        "to_table": "ATNM_Dev.dbo.Revenue",
        "to_column": "rigcode",
        "type": "COSTS_FOR_RIG",
        "description": "Job cost linked to rig via Revenue.rigcode"
    },
    {
        "from_view": "AppMasterDB.dbo.vw_JOB_COST",
        "from_column": "Well ID",
        "to_table": "ATNM_Dev.dbo.Revenue",
        "to_column": "Well_ID",
        "type": "HAS_COST",
        "description": "Well has cost data"
    },
    {
        "from_view": "AppMasterDB.dbo.vw_JOB_COST",
        "from_column": "crew code",
        "to_table": "ATNM_Dev.dbo.crews",
        "to_column": "Code",
        "type": "HAS_CREW",
        "description": "Job has assigned crew"
    },

    # PH_Productivity links
    {
        "from_view": "AppMasterDB.dbo.PH_Productivity",
        "from_column": "PH Name",
        "to_table": "AppMasterDB.dbo.Employee",
        "to_column": "Name",
        "type": "SUPERVISOR",
        "description": "PH is QHSE Supervisor from Employee table"
    }
]


def seed_neo4j():
    """Seed Neo4j with comprehensive AppMasterDB + ATNM_Dev schema."""
    
    driver = GraphDatabase.driver(URI, auth=AUTH)
    
    with driver.session() as session:
        print("Seeding Neo4j with AppMasterDB views...")
        
        # Create View nodes
        for view_name, view_info in VIEWS.items():
            # Build column properties
            cols = []
            for col_name, col_info in view_info.get("columns", {}).items():
                cols.append({
                    "name": col_name,
                    "type": col_info["type"],
                    "semantic": col_info["semantic"],
                    "search_text": f"{view_name}.{col_name} {col_info['semantic']} {view_info.get('semantic_search', '')}"
                })
            
            props = {
                "name": view_name,
                "type": "VIEW",
                "database": view_info["database"],
                "description": view_info["description"],
                "semantic_search": view_info.get("semantic_search", ""),
                "columns": json.dumps(cols),
                "search_content": f"{view_name} {view_info['description']} {view_info.get('semantic_search', '')}"
            }
            
            # Build SET clause dynamically
            set_parts = [f"v.{k} = ${k}" for k in props.keys()]
            
            session.run(f"""
                MERGE (v:View {{name: $name}})
                SET {', '.join(set_parts)}
            """, props)
            
            print(f"  Created view: {view_name}")
        
        # Create relationships
        print("\nCreating cross-database relationships...")
        for rel in RELATIONSHIPS:
            session.run("""
                MATCH (v:View {name: $from_view})
                MATCH (t:Table {name: $to_table})
                MERGE (v)-[r:RELATES_TO {
                    from_column: $from_col,
                    to_column: $to_col,
                    type: $rel_type,
                    description: $desc
                }]->(t)
            """, 
                from_view=rel["from_view"],
                to_table=rel["to_table"],
                from_col=rel["from_column"],
                to_col=rel["to_column"],
                rel_type=rel["type"],
                desc=rel["description"]
            )
            print(f"  {rel['from_view']}.{rel['from_column']} -> {rel['to_table']}.{rel['to_column']}")
        
        # Create indexes for search
        print("\nCreating search indexes...")
        session.run("CREATE INDEX view_search IF NOT EXISTS FOR (v:View) ON (v.search_content)")
        session.run("CREATE INDEX column_search IF NOT EXISTS FOR (c:Column) ON (c.search_text)")
        
        # Create vector similarity readiness
        print("Adding embedding readiness...")
        session.run("""
            MATCH (v:View)
            SET v.embedding_ready = true
        """)
        
        print("\n" + "="*60)
        print("NEO4J SEEDING COMPLETE")
        print("="*60)
        
        # Count results
        result = session.run("MATCH (v:View) RETURN count(v) as view_count")
        print(f"Views created: {result.single()['view_count']}")
        
        result = session.run("MATCH ()-[r:RELATES_TO]->() RETURN count(r) as rel_count")
        print(f"Relationships created: {result.single()['rel_count']}")
    
    driver.close()


def generate_bm25_documents():
    """Generate BM25-ready documents for all views and columns."""
    
    documents = []
    
    # Add view-level documents
    for view_name, view_info in VIEWS.items():
        doc = {
            "table": view_name,
            "column": "*",
            "document": f"""
                VIEW: {view_name}
                Database: {view_info['database']}
                Description: {view_info['description']}
                Semantic Search Terms: {view_info.get('semantic_search', '')}
                Used For: {view_info.get('usage', '')}
            """.strip(),
            "type": "VIEW"
        }
        documents.append(doc)
        
        # Add column-level documents
        for col_name, col_info in view_info.get("columns", {}).items():
            doc = {
                "table": view_name,
                "column": col_name,
                "document": f"""
                    VIEW COLUMN: {view_name}.{col_name}
                    Data Type: {col_info['type']}
                    Meaning: {col_info['semantic']}
                    View Purpose: {view_info['description']}
                    Search Terms: {view_info.get('semantic_search', '')}
                """.strip(),
                "type": "VIEW_COLUMN",
                "semantic": col_info["semantic"]
            }
            documents.append(doc)
    
    # Save to JSON
    with open("appmaster_bm25_documents.json", "w", encoding="utf-8") as f:
        json.dump(documents, f, indent=2)
    
    print(f"Generated {len(documents)} BM25 documents")
    return documents


if __name__ == "__main__":
    # Seed Neo4j
    seed_neo4j()
    
    # Generate BM25 documents
    generate_bm25_documents()
    
    print("\nDone! AppMasterDB views are now in Neo4j and BM25 is ready.")

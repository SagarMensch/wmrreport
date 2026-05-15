"""
Comprehensive Neo4j Schema Seeder
================================
Seeds Neo4j with accurate relationships and rich semantic data.
"""

import json
import os
from neo4j import GraphDatabase
import sys

# ============================================================================
# CONFIGURATION
# ============================================================================

# Try different connection options
NEO4J_URI = os.getenv('NEO4J_URI', 'neo4j+s://4ba6a45a.databases.neo4j.io')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'bashira123')

# Fallback to local
LOCAL_URI = 'bolt://localhost:7687'
LOCAL_USER = 'neo4j'
LOCAL_PASSWORD = 'bashira123'


# ============================================================================
# COMPREHENSIVE SCHEMA DEFINITION
# ============================================================================

TABLES = {
    "WellMonitoringReport": {
        "description": "Main well monitoring and tracking table with all well data, progress, dates",
        "row_count_estimate": "~7000 wells",
        "key_columns": ["pdo_well_id", "well_name_after_spud", "well_location", "rig_no", "Cluster", "well_type"]
    },
    "WellMonitoringReport_Latest": {
        "description": "Latest snapshot of well monitoring - contains only Marmul cluster data",
        "key_columns": ["pdo_well_id", "Cluster"]
    },
    "WMR_Full": {
        "description": "Full well monitoring historical data",
        "key_columns": ["pdo_well_id", "well_name_after_spud"]
    },
    "Revenue": {
        "description": "Revenue tracking by well and rig with actual vs planned progress",
        "key_columns": ["well_id", "rigcode", "acutal_progress", "planned_progress", "actual_purpose_value", "planned_purpose_value"]
    },
    "SAP_DRILLING_SEQUENCE": {
        "description": "SAP drilling sequence and status data",
        "key_columns": ["Well_ID", "Well_Name", "Field", "Well_Function", "Opr_System_status"]
    },
    "Job_Progress_Report_GB": {
        "description": "Weekly job progress tracking with planned vs actual percentages",
        "key_columns": ["Well ID", "Week-1 Plan %", "Week-1 Actual %", "Current Month Plan %", "Current Month Actual %"]
    },
    "Job_Progress_PlanSnapshot": {
        "description": "Planning snapshot with weekly fractions",
        "key_columns": ["Well_ID", "W1_Plan_frac", "CurrentMonthPlanFrac", "Latest_Target_End"]
    },
    "crews": {
        "description": "Crew/team information and assignments",
        "key_columns": ["Code", "CrewType", "Supervisor"]
    },
    "ActivityTaskPlan": {
        "description": "Activity and task planning with progress",
        "key_columns": ["Well_ID", "progress", "actual_start", "actual_end", "crew_uid"]
    },
    "task_daily": {
        "description": "Daily task tracking with progress",
        "key_columns": ["well_id", "progress", "crew_code", "project_id"]
    },
    "WBS_Master_Tracker_": {
        "description": "Work Breakdown Structure master tracking",
        "key_columns": ["Cluster", "Well_ID_Project_PO", "WBS_Code"]
    }
}


# ============================================================================
# ACCURATE RELATIONSHIPS
# ============================================================================

RELATIONSHIPS = [
    # Primary Well ID relationships
    {
        "from_table": "WellMonitoringReport",
        "from_column": "pdo_well_id",
        "to_table": "Revenue",
        "to_column": "well_id",
        "relationship": "HAS_REVENUE",
        "description": "Links well to its revenue/progress tracking data"
    },
    {
        "from_table": "WellMonitoringReport",
        "from_column": "pdo_well_id",
        "to_table": "SAP_DRILLING_SEQUENCE",
        "to_column": "Well_ID",
        "relationship": "HAS_SAP_RECORD",
        "description": "Links well to its SAP drilling sequence"
    },
    {
        "from_table": "WellMonitoringReport",
        "from_column": "pdo_well_id",
        "to_table": "Job_Progress_Report_GB",
        "to_column": "Well ID",
        "relationship": "HAS_JOB_PROGRESS",
        "description": "Links well to weekly job progress"
    },
    {
        "from_table": "WellMonitoringReport",
        "from_column": "pdo_well_id",
        "to_table": "Job_Progress_PlanSnapshot",
        "to_column": "Well_ID",
        "relationship": "HAS_PLAN_SNAPSHOT",
        "description": "Links well to planning snapshot"
    },
    {
        "from_table": "WellMonitoringReport",
        "from_column": "pdo_well_id",
        "to_table": "ActivityTaskPlan",
        "to_column": "Well_ID",
        "relationship": "HAS_ACTIVITY",
        "description": "Links well to planned activities"
    },
    {
        "from_table": "WellMonitoringReport",
        "from_column": "pdo_well_id",
        "to_table": "task_daily",
        "to_column": "well_id",
        "relationship": "HAS_DAILY_TASK",
        "description": "Links well to daily tasks"
    },
    # Well Name relationship
    {
        "from_table": "WellMonitoringReport",
        "from_column": "well_name_after_spud",
        "to_table": "SAP_DRILLING_SEQUENCE",
        "to_column": "Well_Name",
        "relationship": "MIRRORS",
        "description": "Well name mirrors SAP well name"
    },
    # Rig relationships
    {
        "from_table": "WellMonitoringReport",
        "from_column": "rig_no",
        "to_table": "crews",
        "to_column": "Code",
        "relationship": "ASSIGNED_RIG",
        "description": "Well is assigned to this rig"
    },
    # Cluster relationships
    {
        "from_table": "WellMonitoringReport",
        "from_column": "Cluster",
        "to_table": "WBS_Master_Tracker_",
        "to_column": "Cluster",
        "relationship": "IN_CLUSTER",
        "description": "Well belongs to operational cluster"
    }
]


# ============================================================================
# CRITICAL COLUMN ANNOTATIONS
# ============================================================================

CRITICAL_COLUMNS = {
    ("WellMonitoringReport", "pdo_well_id"): {
        "is_primary_key": True,
        "is_join_key": True,
        "description": "PDO unique well identifier - PRIMARY KEY for joining all well tables",
        "usage": "COUNT DISTINCT for counting wells, JOIN with Revenue/SAP/Job_Progress"
    },
    ("Revenue", "rigcode"): {
        "is_critical": True,
        "description": "RIG CODE - NOT location! Use for NL0010, NF0010 filtering",
        "warning": "This is rig identifier, NOT geographic location. Do NOT use well_location for rig codes!",
        "values": ["NL0010", "NF0010", "ML0010", "MS0010", "MF0010", "MCOF10", "MCWF10", "MROP10", "MRWF10", "NCOF10", "NNSW10", "NS0010"]
    },
    ("Revenue", "well_id"): {
        "is_join_key": True,
        "description": "Links to WellMonitoringReport.pdo_well_id"
    },
    ("Revenue", "planned_progress"): {
        "data_type_issue": True,
        "description": "Planned progress - NVARCHAR requires CAST to DECIMAL",
        "warning": "MUST use TRY_CAST(planned_progress AS DECIMAL(10,2)) before comparison"
    },
    ("Revenue", "planned_purpose_value"): {
        "data_type_issue": True,
        "description": "Planned revenue - NVARCHAR requires CAST before SUM",
        "warning": "MUST use TRY_CAST(planned_purpose_value AS DECIMAL(18,2)) before SUM"
    },
    ("WellMonitoringReport", "well_location"): {
        "description": "Geographic location - NOT for rig codes!",
        "warning": "Do NOT use for NL0010/NF0010 - those are in Revenue.rigcode"
    },
    ("WellMonitoringReport", "Cluster"): {
        "description": "Operational cluster - Nimr or Marmul",
        "values": ["Nimr", "Marmul"]
    },
    ("SAP_DRILLING_SEQUENCE", "Well_ID"): {
        "is_join_key": True,
        "description": "SAP well ID - links to WellMonitoringReport.pdo_well_id"
    },
    ("Job_Progress_Report_GB", "Well ID"): {
        "is_join_key": True,
        "description": "Job progress well ID with space in column name - use [Well ID]"
    }
}


def seed_neo4j(uri, user, password):
    """Seed Neo4j with comprehensive schema."""
    
    print(f"Connecting to Neo4j: {uri}")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session() as session:
        # Clear existing data
        print("Clearing existing schema...")
        session.run("MATCH (n) DETACH DELETE n")
        
        # Create tables
        print("Creating table nodes...")
        for table_name, table_info in TABLES.items():
            session.run("""
                CREATE (t:Table {
                    name: $name,
                    description: $description,
                    key_columns: $keys
                })
            """, name=table_name, description=table_info["description"], keys=table_info["key_columns"])
        
        print(f"Created {len(TABLES)} tables")
        
        # Create columns with annotations
        print("Creating column nodes...")
        
        # Load from CSV for complete column list
        import csv
        columns_created = set()
        
        try:
            with open('columns_atnm_dev.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    table = row['tableName']
                    column = row['columnName']
                    data_type = row['dataType']
                    description = row.get('description', '')
                    
                    # Skip if already created
                    if (table, column) in columns_created:
                        continue
                    columns_created.add((table, column))
                    
                    # Check for critical annotations
                    crit = CRITICAL_COLUMNS.get((table, column), {})
                    
                    props = {
                        "name": column,
                        "table_name": table,
                        "data_type": data_type,
                        "description": description,
                        "is_join_key": crit.get("is_join_key", False),
                        "is_primary_key": crit.get("is_primary_key", False),
                        "is_critical": crit.get("is_critical", False),
                        "warning": crit.get("warning", ""),
                        "usage_hint": crit.get("description", "")
                    }
                    
                    # Add values if specified
                    if crit.get("values"):
                        props["valid_values"] = crit["values"]
                    
                    session.run("""
                        CREATE (c:Column $props)
                        WITH c
                        MATCH (t:Table {name: $table})
                        CREATE (c)-[:FROM_TABLE]->(t)
                    """, props=props, table=table)
        except Exception as e:
            print(f"Warning: Could not load columns CSV: {e}")
        
        print(f"Created {len(columns_created)} columns")
        
        # Create relationships
        print("Creating relationships...")
        for rel in RELATIONSHIPS:
            session.run("""
                MATCH (t1:Table {name: $from_table})
                MATCH (t2:Table {name: $to_table})
                CREATE (t1)-[r:RELATES_TO {
                    from_column: $from_col,
                    to_column: $to_col,
                    type: $rel_type,
                    description: $desc
                }]->(t2)
            """, 
                from_table=rel["from_table"],
                to_table=rel["to_table"],
                from_col=rel["from_column"],
                to_col=rel["to_column"],
                rel_type=rel["relationship"],
                desc=rel["description"]
            )
        
        print(f"Created {len(RELATIONSHIPS)} relationships")
        
        # Create join key indexes
        print("Creating indexes...")
        session.run("CREATE INDEX IF NOT EXISTS FOR (c:Column) ON (c.name, c.table_name)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (t:Table) ON (t.name)")
        
        # Add critical column relationships
        print("Marking critical columns...")
        for (table, column), crit in CRITICAL_COLUMNS.items():
            session.run("""
                MATCH (c:Column {table_name: $table, name: $column})
                SET c.is_join_key = true
            """, table=table, column=column)
        
        # Verify
        result = session.run("""
            MATCH (t:Table) RETURN t.name as table, size((t)--()) as connections
        """)
        print("\nTables and connections:")
        for r in result:
            print(f"  {r['table']}: {r['connections']} connections")
    
    driver.close()
    print("\nNeo4j seeding complete!")


def main():
    # Try Aura first, then local
    for uri, user, pw in [
        (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD),
        (LOCAL_URI, LOCAL_USER, LOCAL_PASSWORD)
    ]:
        try:
            seed_neo4j(uri, user, pw)
            return
        except Exception as e:
            print(f"Failed to connect to {uri}: {e}")
            print("Trying next option...")
    
    print("\nCould not connect to any Neo4j instance.")
    print("Please ensure Neo4j is running and credentials are correct.")


if __name__ == "__main__":
    main()

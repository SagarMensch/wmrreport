"""
Quick Neo4j Seeding - Just Tables and Key Relationships
"""
import csv
from neo4j import GraphDatabase

URI = "neo4j+s://4ba6a45a.databases.neo4j.io"
USERNAME = "4ba6a45a"
PASSWORD = "M_191EiDn_UIQBWy1RN24A2yJSWnzyhJogUoiRqV69s"
DATABASE = "4ba6a45a"

TABLE_DESCRIPTIONS = {
    "WellMonitoringReport": "Main well progress tracking - 268 wells",
    "WellMonitoringReport_Latest": "Latest well snapshot - 169 wells",
    "WMR_Full": "Full well monitoring - 18969 rows",
    "SAP_DRILLING_SEQUENCE": "Rig drilling schedule - 6159 rows",
    "Revenue": "Financial data - 21566 rows",
    "Job_Progress_Report_GB": "Weekly job progress - 439 rows",
    "Job_Progress_PlanSnapshot": "Weekly plan snapshot",
    "task_daily": "Daily tasks - 35394 rows",
    "ActivityTaskPlan": "Task execution - 100000 rows",
    "crews": "Crew assignments",
    "Employee": "Personnel directory - 5554 rows",
    "company_employees": "Company employees",
    "PH_PRODUCTIVITY_WEEKLY_REPORT": "Weekly productivity - 510 rows",
    "WBS_Master_Tracker_": "WBS tracking - 81846 rows",
    "ProjectIDs": "Project lookup",
    "schema_knowledge_base": "System metadata",
}

# Join relationships between tables
JOIN_RELATIONSHIPS = [
    # WellMonitoringReport connects to other tables via pdo_well_id
    ("WellMonitoringReport", "pdo_well_id", "WMR_Full", "pdo_well_id", "MIRRORS", "Same well data in both tables"),
    ("WellMonitoringReport", "pdo_well_id", "WellMonitoringReport_Latest", "pdo_well_id", "MIRRORS", "Latest is subset of main"),
    
    # SAP links via Well_Name
    ("WellMonitoringReport", "well_name_after_spud", "SAP_DRILLING_SEQUENCE", "Well_Name", "HAS_SAP_RECORD", "SAP drilling sequence for this well"),
    
    # Job Progress links
    ("WellMonitoringReport", "pdo_well_id", "Job_Progress_Report_GB", "Well ID", "HAS_JOB_PROGRESS", "Weekly progress records"),
    
    # Revenue links
    ("WellMonitoringReport", "pdo_well_id", "Revenue", "well_id", "HAS_REVENUE", "Revenue records"),
    
    # Crew links via rig
    ("WellMonitoringReport", "rig_no", "crews", "Code", "ASSIGNED_CREW", "Crew assigned to rig"),
    
    # Task links
    ("WellMonitoringReport", "pdo_well_id", "task_daily", "well_id", "HAS_DAILY_TASKS", "Daily task records"),
    ("WellMonitoringReport", "pdo_well_id", "ActivityTaskPlan", "Well_ID", "HAS_TASKS", "Task execution records"),
]

def main():
    print("Connecting to Neo4j...")
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print("Connected!")

    with driver.session(database=DATABASE) as session:
        # Clear existing
        print("Clearing existing data...")
        session.run("MATCH (n) DETACH DELETE n")
        
        # Create Table nodes
        print("Creating Table nodes...")
        for table, desc in TABLE_DESCRIPTIONS.items():
            session.run("""
                MERGE (t:Table {name: $name})
                SET t.description = $desc
            """, name=table, desc=desc)
        print(f"  Created {len(TABLE_DESCRIPTIONS)} tables")
        
        # Create Well hub
        print("Creating Well hub...")
        session.run("""
            MERGE (w:Well {wellId: '__MASTER__'})
            SET w.label = 'Master Well Hub'
        """)
        
        # Link well tables to Well hub
        print("Linking well tables to Well hub...")
        well_tables = ["WellMonitoringReport", "WellMonitoringReport_Latest", "WMR_Full"]
        for table in well_tables:
            session.run("""
                MATCH (t:Table {name: $table})
                MATCH (w:Well {wellId: '__MASTER__'})
                MERGE (t)-[:REFERENCES_WELL {via: 'pdo_well_id'}]->(w)
            """, table=table)
        
        # Create JOIN relationships
        print("Creating JOIN relationships...")
        for src_table, src_col, tgt_table, tgt_col, rel_type, desc in JOIN_RELATIONSHIPS:
            session.run(f"""
                MATCH (a:Table {{name: $src}})
                MATCH (b:Table {{name: $tgt}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r.srcColumn = $src_col, r.tgtColumn = $tgt_col, r.description = $desc
            """, src=src_table, tgt=tgt_table, src_col=src_col, tgt_col=tgt_col, desc=desc)
        print(f"  Created {len(JOIN_RELATIONSHIPS)} relationships")

        # Verify
        result = session.run("MATCH (a)-[r]->(b) RETURN labels(a)[0] as from, type(r) as rel, labels(b)[0] as to, count(*) as cnt")
        print("\nRelationships created:")
        for record in result:
            print(f"  {record['from']} --[{record['rel']}]--> {record['to']}: {record['cnt']}")

    driver.close()
    print("\nDone!")

if __name__ == "__main__":
    main()

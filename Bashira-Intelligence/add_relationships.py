"""
Add detailed relationships to Neo4j on top of the full_seed.
Adds: REFERENCES_WELL, MIRRORS, JOINS_ON, isWellKey flags, constraints.
"""
from neo4j import GraphDatabase

URI = "neo4j+s://89f767c1.databases.neo4j.io"
USERNAME = "neo4j"
PASSWORD = "CR4vk-VCs2FnukUfp8-oRvSh-yHeuW_mUgst8m18wK0"
DATABASE = "neo4j"

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
driver.verify_connectivity()
print("Connected to Neo4j")


def run(session, cypher, **params):
    result = session.run(cypher, **params)
    return result.consume().counters


with driver.session(database=DATABASE) as session:
    # 1. REFERENCES_WELL
    print("\n[1] Adding REFERENCES_WELL links...")
    well_links = [
        ("ActivityTaskPlan", "Well_ID", "Links each task to its well"),
        ("WBS_Master_Tracker_", "Well_ID_Project_PO", "Links each WBS code to its well/project/PO"),
        ("Revenue", "well_id", "Links each revenue record to its well"),
        ("SAP_DRILLING_SEQUENCE", "Well_ID", "Links each SAP rig sequence entry to its well"),
        ("task_daily", "well_id", "Links each daily task execution record to its well"),
        ("WellMonitoringReport", "pdo_well_id", "Primary weekly progress snapshot keyed on PDO Well ID"),
        ("WellMonitoringReport_Latest", "pdo_well_id", "Latest-week snapshot of well progress"),
        ("WMR_Full", "pdo_well_id", "Full denormalized WMR view keyed on PDO Well ID"),
        ("Job_Progress_Report_GB", "Well_ID", "Links each weekly job progress row to its well"),
        ("Employee", "Location", "Employees are deployed to well locations"),
        ("PH_PRODUCTIVITY_WEEKLY_REPORT", "PH_Emp_ID", "Supervisor productivity measured against well-level task execution"),
        ("ProjectIDs", "ID", "Master project lookup; wells grouped under project IDs"),
    ]
    for tbl, col, desc in well_links:
        run(session, """
            MATCH (t:Table {name: $tbl})
            MATCH (w:Well {wellId: '__MASTER__'})
            MERGE (t)-[r:REFERENCES_WELL]->(w)
              ON CREATE SET r.viaColumn = $col, r.description = $desc
        """, tbl=tbl, col=col, desc=desc)
        print(f"   OK: {tbl} -> Well (via {col})")

    # 2. MIRRORS
    print("\n[2] Adding MIRRORS relationships...")
    mirrors = [
        ("WellMonitoringReport", "WellMonitoringReport_Latest", "Latest table is a filtered single-week view"),
        ("WMR_Full", "WellMonitoringReport", "WMR_Full is a denormalized view combining WellMonitoringReport"),
    ]
    for t1, t2, desc in mirrors:
        run(session, """
            MATCH (t1:Table {name: $t1}), (t2:Table {name: $t2})
            MERGE (t1)-[:MIRRORS {description: $desc}]->(t2)
        """, t1=t1, t2=t2, desc=desc)
        print(f"   OK: {t1} <MIRRORS> {t2}")

    # 3. JOINS_ON
    print("\n[3] Adding JOINS_ON relationships...")
    joins = [
        ("UId", "Employee", "task_assignee", "task_daily", "Employee UID maps to the task assignee"),
        ("UId", "Employee", "PH_Emp_ID", "PH_PRODUCTIVITY_WEEKLY_REPORT", "Employee UID links to supervisor PH_Emp_ID"),
        ("task_assignee", "task_daily", "PH_Emp_ID", "PH_PRODUCTIVITY_WEEKLY_REPORT", "Task assignee maps to PH_Emp_ID"),
        ("pdo_well_id", "WellMonitoringReport", "Well_ID", "Job_Progress_Report_GB", "PDO Well ID joins WMR to Job Progress"),
        ("pdo_well_id", "WellMonitoringReport", "well_id", "Revenue", "Well ID links monitoring to revenue"),
        ("pdo_well_id", "WellMonitoringReport", "pdo_well_id", "WMR_Full", "WMR_Full shares same PDO Well ID key"),
        ("pdo_well_id", "WellMonitoringReport_Latest", "pdo_well_id", "WellMonitoringReport", "Latest snapshot shares PDO Well ID"),
        ("WBS_Code", "WBS_Master_Tracker_", "WBS_No", "Job_Progress_Report_GB", "WBS Code links tracker to job progress"),
        ("Well_ID_Project_PO", "WBS_Master_Tracker_", "pdo_well_id", "WellMonitoringReport", "WBS well/project ID correlates to PDO Well ID"),
        ("Well_ID", "SAP_DRILLING_SEQUENCE", "pdo_well_id", "WellMonitoringReport", "SAP Well ID cross-referenced against PDO Well ID"),
        ("code", "ActivityTaskPlan", "code", "Revenue", "Activity task code links to revenue records"),
        ("crew_uid", "ActivityTaskPlan", "crew_code", "task_daily", "Crew UID in master plan resolves to crew code"),
        ("ID", "ProjectIDs", "project_id", "ActivityTaskPlan", "Project ID lookup links to ActivityTaskPlan"),
        ("ID", "ProjectIDs", "project_id", "task_daily", "Project ID lookup links to task_daily"),
        ("ID", "ProjectIDs", "project_id", "WellMonitoringReport", "Project ID lookup links to WMR"),
    ]
    for c1_name, c1_table, c2_name, c2_table, desc in joins:
        run(session, """
            MATCH (c1:Column {name: $c1Name, tableName: $c1Table})
            MATCH (c2:Column {name: $c2Name, tableName: $c2Table})
            MERGE (c1)-[:JOINS_ON {description: $desc}]->(c2)
        """, c1Name=c1_name, c1Table=c1_table, c2Name=c2_name, c2Table=c2_table, desc=desc)
        print(f"   OK: {c1_table}.{c1_name} <JOINS_ON> {c2_table}.{c2_name}")

    # 4. Well-key flags
    print("\n[4] Setting isWellKey flags...")
    session.run("""
        MATCH (c:Column)
        WHERE (c.name = 'Well_ID' AND c.tableName IN ['ActivityTaskPlan','SAP_DRILLING_SEQUENCE','Job_Progress_Report_GB'])
           OR (c.name = 'Well_ID_Project_PO' AND c.tableName = 'WBS_Master_Tracker_')
           OR (c.name = 'well_id' AND c.tableName IN ['Revenue','task_daily'])
           OR (c.name = 'pdo_well_id' AND c.tableName IN ['WellMonitoringReport','WellMonitoringReport_Latest','WMR_Full'])
        SET c.isWellKey = true
    """)
    print("   OK: Well-key columns flagged")

    # 5. Constraints
    print("\n[5] Creating indexes...")
    for c in [
        "CREATE CONSTRAINT well_id_unique IF NOT EXISTS FOR (w:Well) REQUIRE w.wellId IS UNIQUE",
        "CREATE CONSTRAINT table_name_unique IF NOT EXISTS FOR (t:Table) REQUIRE t.name IS UNIQUE",
    ]:
        try:
            session.run(c)
            print(f"   OK: {c[:50]}...")
        except Exception:
            pass

    # 6. Verify
    print("\n[6] Final verification...")
    result = session.run("MATCH (n) RETURN labels(n) AS label, count(n) AS total ORDER BY total DESC")
    print("   Node counts:")
    for r in result:
        print(f"     {r['label']}: {r['total']}")
    result = session.run("MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS total ORDER BY total DESC")
    print("   Relationship counts:")
    for r in result:
        print(f"     {r['rel']}: {r['total']}")

driver.close()
print("\nDONE! Knowledge graph fully seeded with all relationships.")

"""
Neo4j Aura Seeding Script — ATNM_Dev Schema v4
===================================================
Reads tables_updated.csv and columns_updated.csv locally, then executes all Cypher statements
via the Neo4j Python driver against Neo4j Aura.

v4 changes:
  - Updated for ATNM_Dev database (10.100.137.11)
  - Uses tables_updated.csv and columns_updated.csv
  - 12 core tables for Neo4j graph
  - Includes Well hub with pdo_well_id as primary key
"""

import csv
import os
from neo4j import GraphDatabase

# ── Credentials ──────────────────────────────────────────────────────────────
URI      = "neo4j+s://89f767c1.databases.neo4j.io"
USERNAME = "neo4j"
PASSWORD = "CR4vk-VCs2FnukUfp8-oRvSh-yHeuW_mUgst8m18wK0"
DATABASE = "neo4j"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Helper ───────────────────────────────────────────────────────────────────
def run(session, cypher, **params):
    result = session.run(cypher, **params)
    return result.consume().counters

def run_cypher(session, cypher):
    result = session.run(cypher)
    return result.consume()


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    print("OK: Connected to Neo4j Aura")

    with driver.session(database=DATABASE) as session:

        # ── 0. CLEAN SLATE ───────────────────────────────────────────────
        print("\n[0] Cleaning existing data ...")
        run_cypher(session, "MATCH (n) DETACH DELETE n")
        print("   OK: All nodes deleted")

        # ── 1. CONSTRAINTS & INDEXES ─────────────────────────────────────
        print("\n[1] Creating constraints & indexes ...")
        constraints = [
            "CREATE CONSTRAINT well_id_unique IF NOT EXISTS FOR (w:Well) REQUIRE w.wellId IS UNIQUE",
            "CREATE CONSTRAINT table_name_unique IF NOT EXISTS FOR (t:Table) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT column_key_unique IF NOT EXISTS FOR (c:Column) REQUIRE (c.name, c.tableName) IS UNIQUE",
            "CREATE FULLTEXT INDEX column_description_ft IF NOT EXISTS FOR (c:Column) ON EACH [c.name, c.description]",
            "CREATE FULLTEXT INDEX table_description_ft IF NOT EXISTS FOR (t:Table) ON EACH [t.description]",
        ]
        for c in constraints:
            try:
                run_cypher(session, c)
                print(f"   OK: {c[:60]}...")
            except Exception as e:
                print(f"   WARN: {c[:60]}... -> {e}")

        # ── 2. SEED WELL HUB NODE ───────────────────────────────────────
        print("\n[2] Creating central Well hub node ...")
        run(session, """
            MERGE (w:Well {wellId: '__SCHEMA_HUB__'})
              ON CREATE SET
                w.label       = 'Well (Schema Hub)',
                w.description = 'Central Well node representing all wells tracked across AppMasterDB. '
                              + 'Every table that references a well identifier is linked here. '
                              + 'Replace / extend with real pdo_well_id values when loading live data.',
                w.createdAt   = datetime()
        """)
        print("   OK: Well hub created")

        # ── 3. SEED TABLE NODES (from tables.csv) ───────────────────────
        print("\n[3] Seeding Table nodes from tables_clean.csv ...")
        tables_path = os.path.join(BASE_DIR, "tables_updated.csv")
        with open(tables_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                table_name = row["tableName"].strip()
                description = row["description"].strip()
                run(session, """
                    MERGE (t:Table {name: $name})
                      ON CREATE SET t.description = $desc, t.createdAt = datetime()
                      ON MATCH  SET t.description = $desc
                """, name=table_name, desc=description)
                count += 1
                print(f"   OK: Table: {table_name}")
        print(f"   -> {count} tables seeded")

        # ── 4. SEED COLUMN NODES & ATTACH TO TABLES (from columns.csv) ──
        print("\n[4] Seeding Column nodes from columns_clean.csv ...")
        cols_path = os.path.join(BASE_DIR, "columns_atnm_dev.csv")
        with open(cols_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                col_name   = row["columnName"].strip()
                table_name = row["tableName"].strip()
                description = row["description"].strip()
                data_type  = row.get("dataType", "").strip()
                run(session, """
                    MATCH (t:Table {name: $tableName})
                    MERGE (c:Column {name: $colName, tableName: $tableName})
                      ON CREATE SET c.description = $desc, c.dataType = $dtype, c.createdAt = datetime()
                      ON MATCH  SET c.description = $desc, c.dataType = $dtype
                    MERGE (c)-[:BELONGS_TO]->(t)
                    MERGE (t)-[:HAS_COLUMN]->(c)
                """, colName=col_name, tableName=table_name, desc=description, dtype=data_type)
                count += 1
            print(f"   -> {count} columns seeded")

        # ── 5. REFERENCES_WELL — link tables to Well hub ─────────────────
        print("\n[5] Linking well-referencing tables to Well hub ...")
        well_links = [
            ("ActivityTaskPlan",               "Well_ID",           "Links each task to its well"),
            ("WBS_Master_Tracker_",            "Well_ID_Project_PO","Links each WBS code to its well/project/PO"),
            ("Revenue",                        "well_id",           "Links each revenue record to its well"),
            ("SAP_DRILLING_SEQUENCE",          "Well_ID",           "Links each SAP rig sequence entry to its well"),
            ("task_daily",                     "well_id",           "Links each daily task execution record to its well"),
            ("WellMonitoringReport",           "pdo_well_id",       "Primary weekly progress snapshot keyed on PDO Well ID"),
            ("WellMonitoringReport_Latest",    "pdo_well_id",       "Latest-week snapshot of well progress keyed on PDO Well ID"),
            ("WMR_Full",                       "pdo_well_id",       "Full denormalized WMR view keyed on PDO Well ID"),
            ("Job_Progress_Report_GB",         "Well_ID",           "Links each weekly job progress row to its well"),
        ]
        for tbl, col, desc in well_links:
            run(session, """
                MATCH (t:Table {name: $tbl})
                MATCH (w:Well  {wellId: '__SCHEMA_HUB__'})
                MERGE (t)-[r:REFERENCES_WELL]->(w)
                  ON CREATE SET r.viaColumn = $col, r.description = $desc
            """, tbl=tbl, col=col, desc=desc)
            print(f"   OK: {tbl} -> Well (via {col})")

        # Indirect well references
        indirect_links = [
            ("Employee",                      "Location",   "Employees are deployed to well locations"),
            ("PH_PRODUCTIVITY_WEEKLY_REPORT", "PH_Emp_ID",  "Supervisor productivity measured against well-level task execution"),
            ("ProjectIDs",                    "ID",         "Master project lookup; wells grouped under project IDs defined here"),
            ("schema_metadata",               "table_name", "System schema table that describes all tables including well-referencing ones"),
        ]
        for tbl, col, desc in indirect_links:
            run(session, """
                MATCH (t:Table {name: $tbl})
                MATCH (w:Well  {wellId: '__SCHEMA_HUB__'})
                MERGE (t)-[r:REFERENCES_WELL]->(w)
                  ON CREATE SET r.viaColumn = $col, r.description = $desc
            """, tbl=tbl, col=col, desc=desc)
            print(f"   OK: {tbl} -> Well (indirect via {col})")

        # ── 6. WELL-KEY COLUMN FLAGS ─────────────────────────────────────
        print("\n[6] Setting isWellKey flags ...")
        run_cypher(session, """
            MATCH (c:Column)
            WHERE (c.name = 'Well_ID'           AND c.tableName IN ['ActivityTaskPlan','SAP_DRILLING_SEQUENCE','Job_Progress_Report_GB'])
               OR (c.name = 'Well_ID_Project_PO' AND c.tableName = 'WBS_Master_Tracker_')
               OR (c.name = 'well_id'            AND c.tableName IN ['Revenue','task_daily'])
               OR (c.name = 'pdo_well_id'        AND c.tableName IN ['WellMonitoringReport','WellMonitoringReport_Latest','WMR_Full'])
            SET c.isWellKey = true
        """)
        print("   OK: Well-key columns flagged")

        # ── 7. MIRRORS — same-schema sibling relationships ───────────────
        print("\n[7] Creating MIRRORS relationships ...")
        mirrors = [
            ("WellMonitoringReport",        "WellMonitoringReport_Latest",  "Latest table is a filtered single-week view of WellMonitoringReport"),
            ("WMR_Full",                     "WellMonitoringReport",         "WMR_Full is a denormalized view combining WellMonitoringReport with extended operational columns"),
        ]
        for t1, t2, desc in mirrors:
            run(session, """
                MATCH (t1:Table {name: $t1}), (t2:Table {name: $t2})
                MERGE (t1)-[:MIRRORS {description: $desc}]->(t2)
            """, t1=t1, t2=t2, desc=desc)
            print(f"   OK: {t1} <MIRRORS> {t2}")

        # ── 8. JOINS_ON — cross-table FK/join hint relationships ─────────
        print("\n[8] Creating JOINS_ON relationships ...")
        joins = [
            ("UId",              "Employee",                      "task_assignee",   "task_daily",                     "Employee UID maps to the task assignee in daily execution"),
            ("UId",              "Employee",                      "PH_Emp_ID",       "PH_PRODUCTIVITY_WEEKLY_REPORT",  "Employee UID links to supervisor PH_Emp_ID in weekly productivity report"),
            ("task_assignee",    "task_daily",                    "PH_Emp_ID",       "PH_PRODUCTIVITY_WEEKLY_REPORT",  "Task assignee maps to PH_Emp_ID for productivity scoring"),
            ("pdo_well_id",      "WellMonitoringReport",          "Well_ID",         "Job_Progress_Report_GB",         "PDO Well ID is the primary join between WellMonitoringReport and Job Progress Report"),
            ("pdo_well_id",      "WellMonitoringReport",          "well_id",         "Revenue",                        "Well ID links monitoring progress to revenue records"),
            ("pdo_well_id",      "WellMonitoringReport",          "pdo_well_id",     "WMR_Full",                       "WMR_Full shares the same PDO Well ID key as WellMonitoringReport"),
            ("pdo_well_id",      "WellMonitoringReport_Latest",   "pdo_well_id",     "WellMonitoringReport",           "Latest snapshot shares PDO Well ID key as full historical WellMonitoringReport"),
            ("WBS_Code",         "WBS_Master_Tracker_",           "WBS_No",          "Job_Progress_Report_GB",         "WBS Code links the tracker to job progress records for cluster and plant context"),
            ("Well_ID_Project_PO","WBS_Master_Tracker_",          "pdo_well_id",     "WellMonitoringReport",           "WBS well/project identifier correlates to PDO Well ID in monitoring report"),
            ("Well_ID",          "SAP_DRILLING_SEQUENCE",         "pdo_well_id",     "WellMonitoringReport",           "SAP Well ID cross-referenced against PDO Well ID for rig schedule vs actual comparison"),
            ("code",             "ActivityTaskPlan",              "code",            "Revenue",                        "Activity task code links planned tasks to revenue/purpose value records"),
            ("crew_uid",         "ActivityTaskPlan",              "crew_code",       "task_daily",                     "Crew UID in master plan resolves to crew code in daily execution"),
            ("ID",               "ProjectIDs",                   "project_id",      "ActivityTaskPlan",               "Project ID lookup links to project_id in ActivityTaskPlan"),
            ("ID",               "ProjectIDs",                   "project_id",      "task_daily",                     "Project ID lookup links to project_id in daily task execution table"),
            ("ID",               "ProjectIDs",                   "project_id",      "WellMonitoringReport",           "Project ID lookup resolves project_id in the well monitoring report"),
        ]
        for c1_name, c1_table, c2_name, c2_table, desc in joins:
            run(session, """
                MATCH (c1:Column {name: $c1Name, tableName: $c1Table})
                MATCH (c2:Column {name: $c2Name, tableName: $c2Table})
                MERGE (c1)-[:JOINS_ON {description: $desc}]->(c2)
            """, c1Name=c1_name, c1Table=c1_table, c2Name=c2_name, c2Table=c2_table, desc=desc)
            print(f"   OK: {c1_table}.{c1_name} <JOINS_ON> {c2_table}.{c2_name}")

        # ── 9. VERIFICATION ─────────────────────────────────────────────
        print("\n[9] Verification ...")
        result = session.run("MATCH (n) RETURN labels(n) AS label, count(n) AS total ORDER BY total DESC")
        print("   Node counts:")
        for record in result:
            print(f"     {record['label']}: {record['total']}")

        result = session.run("MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS total ORDER BY total DESC")
        print("   Relationship counts:")
        for record in result:
            print(f"     {record['rel']}: {record['total']}")

    driver.close()
    print("\nSeeding complete!")


if __name__ == "__main__":
    main()

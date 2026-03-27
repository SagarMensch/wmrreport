// =============================================================================
// Neo4j Seeding Script — AppMasterDB Schema
// Well is the center node of the graph.
//
// Graph Model:
//
//   (:Well)
//     <-[:REFERENCES_WELL]-  (:Table)
//                                 ^
//                                 |  :BELONGS_TO
//                                 |
//                            (:Column)
//
// Node Labels   : Well, Table, Column
// Relationships : REFERENCES_WELL   (Table  -> Well)
//                 BELONGS_TO        (Column -> Table)
//                 HAS_COLUMN        (Table  -> Column)  [convenience reverse]
//
// Prerequisites:
//   Place tables.csv and columns.csv in Neo4j's import directory
//   (typically $NEO4J_HOME/import/) before running this script.
//
// Run with:
//   cypher-shell -u neo4j -p <password> -f seed.cypher
//   — or paste into Neo4j Browser in order, statement by statement.
// =============================================================================


// -----------------------------------------------------------------------------
// 0. CLEAN SLATE  (remove if you want an incremental load)
// -----------------------------------------------------------------------------
MATCH (n)
DETACH DELETE n;


// -----------------------------------------------------------------------------
// 1. CONSTRAINTS & INDEXES
//    Create these first so MERGE is fast and duplicates are impossible.
// -----------------------------------------------------------------------------

// Well
CREATE CONSTRAINT well_id_unique IF NOT EXISTS
  FOR (w:Well) REQUIRE w.wellId IS UNIQUE;

// Table
CREATE CONSTRAINT table_name_unique IF NOT EXISTS
  FOR (t:Table) REQUIRE t.name IS UNIQUE;

// Column — uniqueness is (columnName + tableName) composite
CREATE CONSTRAINT column_key_unique IF NOT EXISTS
  FOR (c:Column) REQUIRE (c.name, c.tableName) IS UNIQUE;

// Full-text search index on Column descriptions (useful for RAG / LLM queries)
CREATE FULLTEXT INDEX column_description_ft IF NOT EXISTS
  FOR (c:Column) ON EACH [c.description];

CREATE FULLTEXT INDEX table_description_ft IF NOT EXISTS
  FOR (t:Table) ON EACH [t.description];


// -----------------------------------------------------------------------------
// 2. SEED THE CENTRAL Well NODE
//    A single representative Well node acts as the schema-level hub.
//    In production, replace / extend this with real PDO well IDs loaded
//    from WellMonitoringReport or SAP_DRILLING_SEQUENCE rows.
// -----------------------------------------------------------------------------
MERGE (w:Well {wellId: '__SCHEMA_HUB__'})
  ON CREATE SET
    w.label       = 'Well (Schema Hub)',
    w.description = 'Central Well node representing all wells tracked across AppMasterDB. '
                  + 'Every table that references a Well ID is linked here. '
                  + 'Replace with real pdo_well_id values when loading live data.',
    w.createdAt   = datetime();


// -----------------------------------------------------------------------------
// 3. SEED TABLE NODES  (from tables.csv)
// -----------------------------------------------------------------------------
LOAD CSV WITH HEADERS FROM 'file:///tables.csv' AS row
MERGE (t:Table {name: trim(row.tableName)})
  ON CREATE SET
    t.description = trim(row.description),
    t.createdAt   = datetime()
  ON MATCH SET
    t.description = trim(row.description);


// -----------------------------------------------------------------------------
// 4. SEED COLUMN NODES & ATTACH TO TABLES  (from columns.csv)
// -----------------------------------------------------------------------------
LOAD CSV WITH HEADERS FROM 'file:///columns.csv' AS row

// Resolve the parent Table
MATCH (t:Table {name: trim(row.tableName)})

// Create or update the Column
MERGE (c:Column {name: trim(row.columnName), tableName: trim(row.tableName)})
  ON CREATE SET
    c.description = trim(row.description),
    c.createdAt   = datetime()
  ON MATCH SET
    c.description = trim(row.description)

// Attach Column -> Table (BELONGS_TO)
MERGE (c)-[:BELONGS_TO]->(t)

// Attach Table -> Column (HAS_COLUMN) — convenience for "give me all columns of a table"
MERGE (t)-[:HAS_COLUMN]->(c);


// -----------------------------------------------------------------------------
// 5. LINK WELL-REFERENCING TABLES TO THE CENTRAL Well NODE
//
//    Each table that contains a well identifier column gets a
//    REFERENCES_WELL relationship to the Well hub node.
//    The relationship carries the name of the linking column.
// -----------------------------------------------------------------------------

// --- ActivityTaskPlan  (Well_ID) ---
MATCH (t:Table {name: 'ActivityTaskPlan'})
MATCH (w:Well   {wellId: '__SCHEMA_HUB__'})
MATCH (c:Column {name: 'Well_ID', tableName: 'ActivityTaskPlan'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn = c.name, r.description = 'Links each task to its well';

// --- WBS_Master_Tracker_  (Well_ID_Project_PO) ---
MATCH (t:Table {name: 'WBS_Master_Tracker_'})
MATCH (w:Well   {wellId: '__SCHEMA_HUB__'})
MATCH (c:Column {name: 'Well_ID_Project_PO', tableName: 'WBS_Master_Tracker_'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn = c.name, r.description = 'Links each WBS code to its well / project / PO';

// --- Revenue  (well_id) ---
MATCH (t:Table {name: 'Revenue'})
MATCH (w:Well   {wellId: '__SCHEMA_HUB__'})
MATCH (c:Column {name: 'well_id', tableName: 'Revenue'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn = c.name, r.description = 'Links each revenue record to its well';

// --- DailyWorkPlan(C)  (Well ID) ---
MATCH (t:Table {name: 'DailyWorkPlan(C)'})
MATCH (w:Well   {wellId: '__SCHEMA_HUB__'})
MATCH (c:Column {name: 'Well ID', tableName: 'DailyWorkPlan(C)'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn = c.name, r.description = 'Links each daily work plan record to its well';

// --- SAP_DRILLING_SEQUENCE  (Well_ID) ---
MATCH (t:Table {name: 'SAP_DRILLING_SEQUENCE'})
MATCH (w:Well   {wellId: '__SCHEMA_HUB__'})
MATCH (c:Column {name: 'Well_ID', tableName: 'SAP_DRILLING_SEQUENCE'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn = c.name, r.description = 'Links each SAP rig sequence entry to its well';

// --- task_daily  (well_id) ---
MATCH (t:Table {name: 'task_daily'})
MATCH (w:Well   {wellId: '__SCHEMA_HUB__'})
MATCH (c:Column {name: 'well_id', tableName: 'task_daily'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn = c.name, r.description = 'Links each daily task execution record to its well';

// --- WellMonitoringReport  (pdo_well_id) ---
MATCH (t:Table {name: 'WellMonitoringReport'})
MATCH (w:Well   {wellId: '__SCHEMA_HUB__'})
MATCH (c:Column {name: 'pdo_well_id', tableName: 'WellMonitoringReport'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn = c.name, r.description = 'Primary weekly progress snapshot keyed on PDO Well ID';

// --- dbo.Job_Progress_Report_GB  (Well ID) ---
MATCH (t:Table {name: 'dbo.Job_Progress_Report_GB'})
MATCH (w:Well   {wellId: '__SCHEMA_HUB__'})
MATCH (c:Column {name: 'Well ID', tableName: 'dbo.Job_Progress_Report_GB'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn = c.name, r.description = 'Links each weekly job progress row to its well';

// --- Employee  (Location — indirect well association via deployment) ---
MATCH (t:Table {name: 'Employee'})
MATCH (w:Well   {wellId: '__SCHEMA_HUB__'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn = 'Location', r.description = 'Employees are deployed to well locations';

// --- PH_PRODUCTIVITY_WEEKLY_REPORT  (indirect via PH Emp ID -> task_daily -> well_id) ---
MATCH (t:Table {name: 'PH_PRODUCTIVITY_WEEKLY_REPORT'})
MATCH (w:Well   {wellId: '__SCHEMA_HUB__'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn = 'PH Emp ID', r.description = 'Supervisor productivity is measured against well-level task execution';


// -----------------------------------------------------------------------------
// 6. WELL-KEY COLUMN FLAG
//    Tag every column that IS the well identifier in its table.
//    Useful for graph traversal and LLM context retrieval.
// -----------------------------------------------------------------------------
MATCH (c:Column)
WHERE (c.name = 'Well_ID'           AND c.tableName IN ['ActivityTaskPlan','SAP_DRILLING_SEQUENCE'])
   OR (c.name = 'Well_ID_Project_PO' AND c.tableName = 'WBS_Master_Tracker_')
   OR (c.name = 'well_id'            AND c.tableName IN ['Revenue','task_daily'])
   OR (c.name = 'Well ID'            AND c.tableName IN ['DailyWorkPlan(C)','dbo.Job_Progress_Report_GB'])
   OR (c.name = 'pdo_well_id'        AND c.tableName = 'WellMonitoringReport')
SET c.isWellKey = true;


// -----------------------------------------------------------------------------
// 7. INTER-TABLE JOIN HINTS  (JOINS_ON relationships between shared columns)
//    Documents how tables can be joined — invaluable for LLM query generation.
// -----------------------------------------------------------------------------

// Employee.UId  <->  task_daily.task_assignee
MATCH (c1:Column {name: 'UId',           tableName: 'Employee'})
MATCH (c2:Column {name: 'task_assignee', tableName: 'task_daily'})
MERGE (c1)-[:JOINS_ON {description: 'Employee personnel ID maps to the task assignee in daily execution'}]->(c2);

// Employee.UId  <->  PH_PRODUCTIVITY_WEEKLY_REPORT."PH Emp ID"
MATCH (c1:Column {name: 'UId',      tableName: 'Employee'})
MATCH (c2:Column {name: 'PH Emp ID', tableName: 'PH_PRODUCTIVITY_WEEKLY_REPORT'})
MERGE (c1)-[:JOINS_ON {description: 'Employee UID links to the supervisor PH Emp ID in weekly productivity report'}]->(c2);

// Employee.UId  <->  DailyWorkPlan(C)."PH Emp ID"
MATCH (c1:Column {name: 'UId',      tableName: 'Employee'})
MATCH (c2:Column {name: 'PH Emp ID', tableName: 'DailyWorkPlan(C)'})
MERGE (c1)-[:JOINS_ON {description: 'Employee UID resolves the Project Holder name in daily work plans'}]->(c2);

// task_daily.task_assignee  <->  PH_PRODUCTIVITY_WEEKLY_REPORT."PH Emp ID"
MATCH (c1:Column {name: 'task_assignee', tableName: 'task_daily'})
MATCH (c2:Column {name: 'PH Emp ID',     tableName: 'PH_PRODUCTIVITY_WEEKLY_REPORT'})
MERGE (c1)-[:JOINS_ON {description: 'Task assignee maps to PH Emp ID for productivity scoring'}]->(c2);

// WellMonitoringReport.pdo_well_id  <->  dbo.Job_Progress_Report_GB."Well ID"
MATCH (c1:Column {name: 'pdo_well_id', tableName: 'WellMonitoringReport'})
MATCH (c2:Column {name: 'Well ID',     tableName: 'dbo.Job_Progress_Report_GB'})
MERGE (c1)-[:JOINS_ON {description: 'PDO Well ID is the primary join between WellMonitoringReport and Job Progress Report'}]->(c2);

// WellMonitoringReport.pdo_well_id  <->  Revenue.well_id
MATCH (c1:Column {name: 'pdo_well_id', tableName: 'WellMonitoringReport'})
MATCH (c2:Column {name: 'well_id',     tableName: 'Revenue'})
MERGE (c1)-[:JOINS_ON {description: 'Well ID links monitoring progress to revenue records'}]->(c2);

// WBS_Master_Tracker_.WBS_Code  <->  dbo.Job_Progress_Report_GB."WBS No"
MATCH (c1:Column {name: 'WBS_Code', tableName: 'WBS_Master_Tracker_'})
MATCH (c2:Column {name: 'WBS No',   tableName: 'dbo.Job_Progress_Report_GB'})
MERGE (c1)-[:JOINS_ON {description: 'WBS Code links the tracker to job progress records for cluster and plant context'}]->(c2);

// WBS_Master_Tracker_.Well_ID_Project_PO  <->  WellMonitoringReport.pdo_well_id
MATCH (c1:Column {name: 'Well_ID_Project_PO', tableName: 'WBS_Master_Tracker_'})
MATCH (c2:Column {name: 'pdo_well_id',         tableName: 'WellMonitoringReport'})
MERGE (c1)-[:JOINS_ON {description: 'WBS well/project identifier correlates to PDO Well ID in monitoring report'}]->(c2);

// SAP_DRILLING_SEQUENCE.Well_ID  <->  WellMonitoringReport.pdo_well_id
MATCH (c1:Column {name: 'Well_ID',     tableName: 'SAP_DRILLING_SEQUENCE'})
MATCH (c2:Column {name: 'pdo_well_id', tableName: 'WellMonitoringReport'})
MERGE (c1)-[:JOINS_ON {description: 'SAP Well ID is cross-referenced against PDO Well ID for rig schedule vs actual comparison'}]->(c2);

// ActivityTaskPlan.code  <->  Revenue.code
MATCH (c1:Column {name: 'code', tableName: 'ActivityTaskPlan'})
MATCH (c2:Column {name: 'code', tableName: 'Revenue'})
MERGE (c1)-[:JOINS_ON {description: 'Activity task code links planned tasks to their revenue/purpose value records'}]->(c2);

// ActivityTaskPlan.crew_uid  <->  task_daily.crew_code
MATCH (c1:Column {name: 'crew_uid',  tableName: 'ActivityTaskPlan'})
MATCH (c2:Column {name: 'crew_code', tableName: 'task_daily'})
MERGE (c1)-[:JOINS_ON {description: 'Crew UID in the master plan resolves to crew code in daily execution'}]->(c2);

// DailyWorkPlan(C)."Activity ID"  <->  WBS_Master_Tracker_.Activity_code
MATCH (c1:Column {name: 'Activity ID',   tableName: 'DailyWorkPlan(C)'})
MATCH (c2:Column {name: 'Activity_code', tableName: 'WBS_Master_Tracker_'})
MERGE (c1)-[:JOINS_ON {description: 'Activity ID in daily work plan maps to the WBS activity code'}]->(c2);


// -----------------------------------------------------------------------------
// 8b. LINK NEW WELL-REFERENCING TABLES TO THE CENTRAL Well NODE
// -----------------------------------------------------------------------------

// --- dbo.WellMonitoringReport_Latest  (pdo_well_id) ---
MATCH (t:Table {name: 'dbo.WellMonitoringReport_Latest'})
MATCH (w:Well   {wellId: '__SCHEMA_HUB__'})
MATCH (c:Column {name: 'pdo_well_id', tableName: 'dbo.WellMonitoringReport_Latest'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn = c.name, r.description = 'Latest-week snapshot of well progress keyed on PDO Well ID';

// --- dbo.WellMonitoringReport_Staged  (pdo_well_id) ---
MATCH (t:Table {name: 'dbo.WellMonitoringReport_Staged'})
MATCH (w:Well   {wellId: '__SCHEMA_HUB__'})
MATCH (c:Column {name: 'pdo_well_id', tableName: 'dbo.WellMonitoringReport_Staged'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn = c.name, r.description = 'Staging table for raw WMR import; linked to well via pdo_well_id before promotion to production table';

// --- dbo.ProjectIDs  (indirect — project-level lookup, no direct well FK) ---
MATCH (t:Table {name: 'dbo.ProjectIDs'})
MATCH (w:Well   {wellId: '__SCHEMA_HUB__'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn = 'ID', r.description = 'Master project lookup; wells are grouped under project IDs defined in this table';


// -----------------------------------------------------------------------------
// 8c. WELL-KEY COLUMN FLAG — new tables
// -----------------------------------------------------------------------------
MATCH (c:Column)
WHERE c.name = 'pdo_well_id'
  AND c.tableName IN ['dbo.WellMonitoringReport_Latest', 'dbo.WellMonitoringReport_Staged']
SET c.isWellKey = true;


// -----------------------------------------------------------------------------
// 8d. INTER-TABLE JOIN HINTS — new tables
// -----------------------------------------------------------------------------

// WellMonitoringReport_Latest.pdo_well_id  <->  WellMonitoringReport.pdo_well_id
MATCH (c1:Column {name: 'pdo_well_id', tableName: 'dbo.WellMonitoringReport_Latest'})
MATCH (c2:Column {name: 'pdo_well_id', tableName: 'WellMonitoringReport'})
MERGE (c1)-[:JOINS_ON {description: 'Latest snapshot shares the same PDO Well ID key as the full historical WellMonitoringReport'}]->(c2);

// WellMonitoringReport_Staged.pdo_well_id  <->  WellMonitoringReport.pdo_well_id
MATCH (c1:Column {name: 'pdo_well_id', tableName: 'dbo.WellMonitoringReport_Staged'})
MATCH (c2:Column {name: 'pdo_well_id', tableName: 'WellMonitoringReport'})
MERGE (c1)-[:JOINS_ON {description: 'Staged raw data is promoted to production WellMonitoringReport using pdo_well_id as the join key'}]->(c2);

// WellMonitoringReport_Staged.pdo_well_id  <->  WellMonitoringReport_Latest.pdo_well_id
MATCH (c1:Column {name: 'pdo_well_id', tableName: 'dbo.WellMonitoringReport_Staged'})
MATCH (c2:Column {name: 'pdo_well_id', tableName: 'dbo.WellMonitoringReport_Latest'})
MERGE (c1)-[:JOINS_ON {description: 'Staged data feeds into the latest-week snapshot table via pdo_well_id'}]->(c2);

// WellMonitoringReport_Staged — raw-to-typed column lineage (Week_Number)
MATCH (c1:Column {name: 'Week_Number',   tableName: 'dbo.WellMonitoringReport_Staged'})
MATCH (c2:Column {name: 'Week_Number_d', tableName: 'dbo.WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description: 'Raw text Week_Number is validated and cast to native date type in Week_Number_d'}]->(c2);

// WellMonitoringReport_Staged — raw-to-typed lineage (overall progress)
MATCH (c1:Column {name: 'over_all_progress_percentages', tableName: 'dbo.WellMonitoringReport_Staged'})
MATCH (c2:Column {name: 'overall_progress_p',            tableName: 'dbo.WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description: 'Raw text progress string is cast to decimal in overall_progress_p'}]->(c2);

// ProjectIDs.ID  <->  ActivityTaskPlan.project_id
MATCH (c1:Column {name: 'ID',         tableName: 'dbo.ProjectIDs'})
MATCH (c2:Column {name: 'project_id', tableName: 'ActivityTaskPlan'})
MERGE (c1)-[:JOINS_ON {description: 'Project ID lookup links to project_id in the ActivityTaskPlan execution table'}]->(c2);

// ProjectIDs.ID  <->  task_daily.project_id
MATCH (c1:Column {name: 'ID',         tableName: 'dbo.ProjectIDs'})
MATCH (c2:Column {name: 'project_id', tableName: 'task_daily'})
MERGE (c1)-[:JOINS_ON {description: 'Project ID lookup links to project_id in the daily task execution table'}]->(c2);

// ProjectIDs.ID  <->  WellMonitoringReport.project_id
MATCH (c1:Column {name: 'ID',         tableName: 'dbo.ProjectIDs'})
MATCH (c2:Column {name: 'project_id', tableName: 'WellMonitoringReport'})
MERGE (c1)-[:JOINS_ON {description: 'Project ID lookup resolves project_id in the well monitoring report'}]->(c2);


// -----------------------------------------------------------------------------
// 9. VERIFICATION QUERIES  (run these to confirm the load)
// -----------------------------------------------------------------------------

// Count all nodes by label:
// MATCH (n) RETURN labels(n) AS label, count(n) AS total ORDER BY total DESC;

// Count all relationship types:
// MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS total ORDER BY total DESC;

// Show the full Well-centred subgraph (schema hub):
// MATCH (w:Well {wellId:'__SCHEMA_HUB__'})<-[:REFERENCES_WELL]-(t:Table)-[:HAS_COLUMN]->(c:Column)
// RETURN w, t, c LIMIT 50;

// Find all join paths between two tables:
// MATCH p=(c1:Column {tableName:'task_daily'})-[:JOINS_ON]-(c2:Column)
// RETURN p;

// List all well-key columns:
// MATCH (c:Column {isWellKey: true}) RETURN c.tableName, c.name ORDER BY c.tableName;

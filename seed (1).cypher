// =============================================================================
// Neo4j Seeding Script — AppMasterDB Schema  (v3 — generated from Results.csv)
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
//                 HAS_COLUMN        (Table  -> Column)
//                 JOINS_ON          (Column -> Column)   cross-table FK hints
//                 CASTS_TO          (Column -> Column)   staging raw→typed lineage
//                 MIRRORS           (Table  -> Table)    same-schema siblings
//
// Tables (14):
//   ActivityTaskPlan, Employee, Job_Progress_Report_GB,
//   PH_PRODUCTIVITY_WEEKLY_REPORT, ProjectIDs, Revenue,
//   SAP_DRILLING_SEQUENCE, WBS_Master_Tracker_, WMR_Full,
//   WellMonitoringReport, WellMonitoringReport_Latest,
//   WellMonitoringReport_Staged, schema_metadata, task_daily
//
// Prerequisites:
//   Place tables.csv and columns.csv in Neo4j's import directory
//   (typically $NEO4J_HOME/import/) before running this script.
//   columns.csv now includes a 'dataType' column.
//
// Run with:
//   cypher-shell -u neo4j -p <password> -f seed.cypher
//   or paste into Neo4j Browser statement by statement.
// =============================================================================


// -----------------------------------------------------------------------------
// 0. CLEAN SLATE  (remove if you want an incremental / additive load)
// -----------------------------------------------------------------------------
MATCH (n)
DETACH DELETE n;


// -----------------------------------------------------------------------------
// 1. CONSTRAINTS & INDEXES
// -----------------------------------------------------------------------------

CREATE CONSTRAINT well_id_unique IF NOT EXISTS
  FOR (w:Well) REQUIRE w.wellId IS UNIQUE;

CREATE CONSTRAINT table_name_unique IF NOT EXISTS
  FOR (t:Table) REQUIRE t.name IS UNIQUE;

CREATE CONSTRAINT column_key_unique IF NOT EXISTS
  FOR (c:Column) REQUIRE (c.name, c.tableName) IS UNIQUE;

CREATE FULLTEXT INDEX column_description_ft IF NOT EXISTS
  FOR (c:Column) ON EACH [c.description];

CREATE FULLTEXT INDEX table_description_ft IF NOT EXISTS
  FOR (t:Table) ON EACH [t.description];


// -----------------------------------------------------------------------------
// 2. CENTRAL Well NODE  (schema hub)
// -----------------------------------------------------------------------------
MERGE (w:Well {wellId: '__SCHEMA_HUB__'})
  ON CREATE SET
    w.label       = 'Well (Schema Hub)',
    w.description = 'Central Well node representing all wells tracked across AppMasterDB. '
                  + 'Every table that references a well identifier is linked here. '
                  + 'Replace / extend with real pdo_well_id values when loading live data.',
    w.createdAt   = datetime();


// -----------------------------------------------------------------------------
// 3. SEED TABLE NODES  (from tables.csv)
//    columns: tableName, description
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
//    columns: columnName, tableName, dataType, description
// -----------------------------------------------------------------------------
LOAD CSV WITH HEADERS FROM 'file:///columns.csv' AS row
MATCH (t:Table {name: trim(row.tableName)})
MERGE (c:Column {name: trim(row.columnName), tableName: trim(row.tableName)})
  ON CREATE SET
    c.description = trim(row.description),
    c.dataType    = trim(row.dataType),
    c.createdAt   = datetime()
  ON MATCH SET
    c.description = trim(row.description),
    c.dataType    = trim(row.dataType)
MERGE (c)-[:BELONGS_TO]->(t)
MERGE (t)-[:HAS_COLUMN]->(c);


// -----------------------------------------------------------------------------
// 5. REFERENCES_WELL — link every well-referencing table to the central Well
// -----------------------------------------------------------------------------

MATCH (t:Table {name:'ActivityTaskPlan'}), (w:Well {wellId:'__SCHEMA_HUB__'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn='Well_ID', r.description='Links each task to its well';

MATCH (t:Table {name:'WBS_Master_Tracker_'}), (w:Well {wellId:'__SCHEMA_HUB__'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn='Well_ID_Project_PO', r.description='Links each WBS code to its well/project/PO';

MATCH (t:Table {name:'Revenue'}), (w:Well {wellId:'__SCHEMA_HUB__'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn='well_id', r.description='Links each revenue record to its well';

MATCH (t:Table {name:'SAP_DRILLING_SEQUENCE'}), (w:Well {wellId:'__SCHEMA_HUB__'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn='Well_ID', r.description='Links each SAP rig sequence entry to its well';

MATCH (t:Table {name:'task_daily'}), (w:Well {wellId:'__SCHEMA_HUB__'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn='well_id', r.description='Links each daily task execution record to its well';

MATCH (t:Table {name:'WellMonitoringReport'}), (w:Well {wellId:'__SCHEMA_HUB__'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn='pdo_well_id', r.description='Primary weekly progress snapshot keyed on PDO Well ID';

MATCH (t:Table {name:'WellMonitoringReport_Latest'}), (w:Well {wellId:'__SCHEMA_HUB__'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn='pdo_well_id', r.description='Latest-week snapshot of well progress keyed on PDO Well ID';

MATCH (t:Table {name:'WellMonitoringReport_Staged'}), (w:Well {wellId:'__SCHEMA_HUB__'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn='pdo_well_id', r.description='Staging table for raw WMR import; linked to well via pdo_well_id';

MATCH (t:Table {name:'WMR_Full'}), (w:Well {wellId:'__SCHEMA_HUB__'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn='pdo_well_id', r.description='Full denormalized WMR view keyed on PDO Well ID';

MATCH (t:Table {name:'Job_Progress_Report_GB'}), (w:Well {wellId:'__SCHEMA_HUB__'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn='Well_ID', r.description='Links each weekly job progress row to its well';

MATCH (t:Table {name:'Employee'}), (w:Well {wellId:'__SCHEMA_HUB__'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn='Location', r.description='Employees are deployed to well locations';

MATCH (t:Table {name:'PH_PRODUCTIVITY_WEEKLY_REPORT'}), (w:Well {wellId:'__SCHEMA_HUB__'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn='PH_Emp_ID', r.description='Supervisor productivity measured against well-level task execution';

MATCH (t:Table {name:'ProjectIDs'}), (w:Well {wellId:'__SCHEMA_HUB__'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn='ID', r.description='Master project lookup; wells grouped under project IDs defined here';

MATCH (t:Table {name:'schema_metadata'}), (w:Well {wellId:'__SCHEMA_HUB__'})
MERGE (t)-[r:REFERENCES_WELL]->(w)
  ON CREATE SET r.viaColumn='table_name', r.description='System schema table that describes all tables including well-referencing ones';


// -----------------------------------------------------------------------------
// 6. WELL-KEY COLUMN FLAG
// -----------------------------------------------------------------------------
MATCH (c:Column)
WHERE (c.name = 'Well_ID'    AND c.tableName IN ['ActivityTaskPlan','SAP_DRILLING_SEQUENCE','Job_Progress_Report_GB'])
   OR (c.name = 'Well_ID_Project_PO' AND c.tableName = 'WBS_Master_Tracker_')
   OR (c.name = 'well_id'   AND c.tableName IN ['Revenue','task_daily'])
   OR (c.name = 'pdo_well_id' AND c.tableName IN ['WellMonitoringReport','WellMonitoringReport_Latest','WellMonitoringReport_Staged','WMR_Full'])
SET c.isWellKey = true;


// -----------------------------------------------------------------------------
// 7. MIRRORS — same-schema sibling relationships between WMR tables
// -----------------------------------------------------------------------------
MATCH (t1:Table {name:'WellMonitoringReport'}), (t2:Table {name:'WellMonitoringReport_Latest'})
MERGE (t1)-[:MIRRORS {description:'Latest table is a filtered single-week view of WellMonitoringReport'}]->(t2);

MATCH (t1:Table {name:'WellMonitoringReport_Staged'}), (t2:Table {name:'WellMonitoringReport'})
MERGE (t1)-[:MIRRORS {description:'Staged table is the raw import source promoted to WellMonitoringReport after casting'}]->(t2);

MATCH (t1:Table {name:'WMR_Full'}), (t2:Table {name:'WellMonitoringReport'})
MERGE (t1)-[:MIRRORS {description:'WMR_Full is a denormalized view combining WellMonitoringReport with extended operational columns'}]->(t2);


// -----------------------------------------------------------------------------
// 8. JOINS_ON — cross-table FK / join hint relationships
// -----------------------------------------------------------------------------

MATCH (c1:Column {name:'UId', tableName:'Employee'})
MATCH (c2:Column {name:'task_assignee', tableName:'task_daily'})
MERGE (c1)-[:JOINS_ON {description:'Employee UID maps to the task assignee in daily execution'}]->(c2);

MATCH (c1:Column {name:'UId', tableName:'Employee'})
MATCH (c2:Column {name:'PH_Emp_ID', tableName:'PH_PRODUCTIVITY_WEEKLY_REPORT'})
MERGE (c1)-[:JOINS_ON {description:'Employee UID links to supervisor PH_Emp_ID in weekly productivity report'}]->(c2);

MATCH (c1:Column {name:'task_assignee', tableName:'task_daily'})
MATCH (c2:Column {name:'PH_Emp_ID', tableName:'PH_PRODUCTIVITY_WEEKLY_REPORT'})
MERGE (c1)-[:JOINS_ON {description:'Task assignee maps to PH_Emp_ID for productivity scoring'}]->(c2);

MATCH (c1:Column {name:'pdo_well_id', tableName:'WellMonitoringReport'})
MATCH (c2:Column {name:'Well_ID', tableName:'Job_Progress_Report_GB'})
MERGE (c1)-[:JOINS_ON {description:'PDO Well ID is the primary join between WellMonitoringReport and Job Progress Report'}]->(c2);

MATCH (c1:Column {name:'pdo_well_id', tableName:'WellMonitoringReport'})
MATCH (c2:Column {name:'well_id', tableName:'Revenue'})
MERGE (c1)-[:JOINS_ON {description:'Well ID links monitoring progress to revenue records'}]->(c2);

MATCH (c1:Column {name:'pdo_well_id', tableName:'WellMonitoringReport'})
MATCH (c2:Column {name:'pdo_well_id', tableName:'WMR_Full'})
MERGE (c1)-[:JOINS_ON {description:'WMR_Full shares the same PDO Well ID key as WellMonitoringReport'}]->(c2);

MATCH (c1:Column {name:'pdo_well_id', tableName:'WellMonitoringReport_Latest'})
MATCH (c2:Column {name:'pdo_well_id', tableName:'WellMonitoringReport'})
MERGE (c1)-[:JOINS_ON {description:'Latest snapshot shares PDO Well ID key as full historical WellMonitoringReport'}]->(c2);

MATCH (c1:Column {name:'pdo_well_id', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'pdo_well_id', tableName:'WellMonitoringReport'})
MERGE (c1)-[:JOINS_ON {description:'Staged raw data is promoted to WellMonitoringReport using pdo_well_id'}]->(c2);

MATCH (c1:Column {name:'WBS_Code', tableName:'WBS_Master_Tracker_'})
MATCH (c2:Column {name:'WBS_No', tableName:'Job_Progress_Report_GB'})
MERGE (c1)-[:JOINS_ON {description:'WBS Code links the tracker to job progress records for cluster and plant context'}]->(c2);

MATCH (c1:Column {name:'Well_ID_Project_PO', tableName:'WBS_Master_Tracker_'})
MATCH (c2:Column {name:'pdo_well_id', tableName:'WellMonitoringReport'})
MERGE (c1)-[:JOINS_ON {description:'WBS well/project identifier correlates to PDO Well ID in monitoring report'}]->(c2);

MATCH (c1:Column {name:'Well_ID', tableName:'SAP_DRILLING_SEQUENCE'})
MATCH (c2:Column {name:'pdo_well_id', tableName:'WellMonitoringReport'})
MERGE (c1)-[:JOINS_ON {description:'SAP Well ID cross-referenced against PDO Well ID for rig schedule vs actual comparison'}]->(c2);

MATCH (c1:Column {name:'code', tableName:'ActivityTaskPlan'})
MATCH (c2:Column {name:'code', tableName:'Revenue'})
MERGE (c1)-[:JOINS_ON {description:'Activity task code links planned tasks to revenue/purpose value records'}]->(c2);

MATCH (c1:Column {name:'crew_uid', tableName:'ActivityTaskPlan'})
MATCH (c2:Column {name:'crew_code', tableName:'task_daily'})
MERGE (c1)-[:JOINS_ON {description:'Crew UID in master plan resolves to crew code in daily execution'}]->(c2);

MATCH (c1:Column {name:'ID', tableName:'ProjectIDs'})
MATCH (c2:Column {name:'project_id', tableName:'ActivityTaskPlan'})
MERGE (c1)-[:JOINS_ON {description:'Project ID lookup links to project_id in ActivityTaskPlan'}]->(c2);

MATCH (c1:Column {name:'ID', tableName:'ProjectIDs'})
MATCH (c2:Column {name:'project_id', tableName:'task_daily'})
MERGE (c1)-[:JOINS_ON {description:'Project ID lookup links to project_id in daily task execution table'}]->(c2);

MATCH (c1:Column {name:'ID', tableName:'ProjectIDs'})
MATCH (c2:Column {name:'project_id', tableName:'WellMonitoringReport'})
MERGE (c1)-[:JOINS_ON {description:'Project ID lookup resolves project_id in the well monitoring report'}]->(c2);


// -----------------------------------------------------------------------------
// 9. CASTS_TO — WellMonitoringReport_Staged raw → typed column lineage
// -----------------------------------------------------------------------------

MATCH (c1:Column {name:'Week_Number', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'Week_Number_d', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text Week_Number cast to native date'}]->(c2);

MATCH (c1:Column {name:'over_all_progress_percentages', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'overall_progress_p', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text overall progress cast to decimal'}]->(c2);

MATCH (c1:Column {name:'last_week_cum_progress', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'last_week_cum_progress_p', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw last week cumulative progress cast to decimal'}]->(c2);

MATCH (c1:Column {name:'cum_progress_for_this_week', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'cum_progress_for_this_week_p', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw current week cumulative progress cast to decimal'}]->(c2);

MATCH (c1:Column {name:'actual_rig_on_date', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'actual_rig_on_date_d', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text rig-on date cast to native date'}]->(c2);

MATCH (c1:Column {name:'actual_rig_off_date', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'actual_rig_off_date_d', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text rig-off date cast to native date'}]->(c2);

MATCH (c1:Column {name:'actual_start_date', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'actual_start_date_d', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text actual start date cast to native date'}]->(c2);

MATCH (c1:Column {name:'actual_finish_date', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'actual_finish_date_d', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text actual finish date cast to native date'}]->(c2);

MATCH (c1:Column {name:'flaf_issue_date', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'flaf_issue_date_d', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text FLAF issue date cast to native date'}]->(c2);

MATCH (c1:Column {name:'actual_comm_start_date', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'comm_start_date_d', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text commissioning start date cast to native date'}]->(c2);

MATCH (c1:Column {name:'actual_comm_finish_date_with_in_2_days_from_actual_engg_completion_date', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'comm_finish_date_d', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text commissioning finish date cast to native date'}]->(c2);

MATCH (c1:Column {name:'actual_eng_completion_date', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'eng_completion_date_d', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text engineering completion date cast to native date'}]->(c2);

MATCH (c1:Column {name:'f_l_po_recd_date', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'f_l_po_recd_date_d', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text flowline PO received date cast to native date'}]->(c2);

MATCH (c1:Column {name:'location_po_recvd_date', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'location_po_recvd_date_d', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text location PO received date cast to native date'}]->(c2);

MATCH (c1:Column {name:'flowline_construction_progress', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'flowline_construction_progress_p', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text flowline construction progress cast to decimal'}]->(c2);

MATCH (c1:Column {name:'ohl_progress', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'ohl_progress_p', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text OHL progress cast to decimal'}]->(c2);

MATCH (c1:Column {name:'overall_comm_progress_100', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'overall_comm_progress_p', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text commissioning phase completion cast to decimal'}]->(c2);

MATCH (c1:Column {name:'const_actual_start_date', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'const_actual_start_date_d', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text construction start date cast to native date'}]->(c2);

MATCH (c1:Column {name:'actual_pegged_date', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'actual_pegged_date_d', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text pegged date cast to native date'}]->(c2);

MATCH (c1:Column {name:'ohl_completion_date', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'ohl_completion_date_d', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text OHL completion date cast to native date'}]->(c2);

MATCH (c1:Column {name:'scr_date', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'scr_date_d', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text SCR date cast to native date'}]->(c2);

MATCH (c1:Column {name:'ramz_id_received_date_same_day_as_flaf_issue_date', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'ramz_id_received_date_d', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw RAMZ ID received date cast to native date'}]->(c2);

MATCH (c1:Column {name:'wlctf_acceptanceapproval_from_production', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'wlctf_acceptance_d', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw WLCTF acceptance date cast to native date'}]->(c2);

MATCH (c1:Column {name:'overall_loc_preparation_10_100', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'overall_loc_preparation_p', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text location preparation completion cast to decimal'}]->(c2);

MATCH (c1:Column {name:'overall_engg_10_100', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'overall_engg_p', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text engineering phase completion cast to decimal'}]->(c2);

MATCH (c1:Column {name:'overall_const_10_100', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'overall_const_p', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text construction phase completion cast to decimal'}]->(c2);

MATCH (c1:Column {name:'overall_material_10_100', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'overall_material_p', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text material procurement completion cast to decimal'}]->(c2);

MATCH (c1:Column {name:'overall_ohl_progr_100', tableName:'WellMonitoringReport_Staged'})
MATCH (c2:Column {name:'overall_ohl_p', tableName:'WellMonitoringReport_Staged'})
MERGE (c1)-[:CASTS_TO {description:'Raw text OHL phase completion cast to decimal'}]->(c2);


// =============================================================================
// VERIFICATION QUERIES  (uncomment and run in Neo4j Browser to validate)
// =============================================================================

// Count all nodes by label:
// MATCH (n) RETURN labels(n) AS label, count(n) AS total ORDER BY total DESC;

// Count all relationship types:
// MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS total ORDER BY total DESC;

// Well-centred subgraph — all tables linked to the hub:
// MATCH (w:Well {wellId:'__SCHEMA_HUB__'})<-[:REFERENCES_WELL]-(t:Table)
// RETURN w, t;

// Show all columns of a table with data types:
// MATCH (t:Table {name:'WellMonitoringReport'})-[:HAS_COLUMN]->(c:Column)
// RETURN c.name, c.dataType, c.description ORDER BY c.name;

// All join paths from task_daily:
// MATCH p=(c1:Column {tableName:'task_daily'})-[:JOINS_ON]-(c2:Column)
// RETURN p;

// Staging pipeline lineage:
// MATCH p=(c1:Column {tableName:'WellMonitoringReport_Staged'})-[:CASTS_TO*]->(c2)
// RETURN p LIMIT 25;

// List all well-key columns:
// MATCH (c:Column {isWellKey:true}) RETURN c.tableName, c.name ORDER BY c.tableName;

// WMR mirror relationships:
// MATCH p=(t1:Table)-[:MIRRORS]->(t2:Table) RETURN p;

// Full-text search on column descriptions:
// CALL db.index.fulltext.queryNodes('column_description_ft', 'productivity index week')
// YIELD node RETURN node.tableName, node.name, node.description LIMIT 10;

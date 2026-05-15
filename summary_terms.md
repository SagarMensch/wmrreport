# Term Extractions

## NIRM (Total: 0)

## Alstansim (Total: 0)

## PDO (Total: 76)
- .\columns_updated_new.csv:146: PDO_Well_Type,SAP_DRILLING_SEQUENCE,PDO classification of well type
- .\columns_updated_new.csv:167: pdo_well_id,WellMonitoringReport,PDO unique well identifier primary key for all wells use for counting distinct wells
- .\columns_updated_new.csv:297: pdo_well_id,WellMonitoringReport_Latest,PDO unique well identifier primary key for latest week snapshot
- .\KNOWLEDGE_BANK_COMPLETE.md:323: | PDO_Well_Type | nvarchar | Pdo Well Type |
- .\update_columns.py:24: ('pdo_well_id', 'WellMonitoringReport'): 'PDO unique well identifier primary key for all wells use for counting distinct wells',
- .\update_columns.py:38: ('pdo_well_id', 'WellMonitoringReport_Latest'): 'PDO unique well identifier primary key for latest week snapshot',
- .\update_columns.py:93: ('PDO_Well_Type', 'SAP_DRILLING_SEQUENCE'): 'PDO classification of well type',
- .\USE [AppMasterDB]dailyplanreport.txt:40: CAST(NULL AS NVARCHAR(100)) AS [PDO Permit No],
- .\Bashira-Intelligence\appmasterdb_schema.csv:64: AppMasterDB.dbo.WellMonitoringReport,pdo_well_id,nvarchar,KEY COLUMN: PDO well identifier - PRIMARY KEY
- .\Bashira-Intelligence\appmaster_bm25_documents.json:11: "document": "VIEW COLUMN: AppMasterDB.dbo.WellMonitoringReport.pdo_well_id\n                    Data Type: nvarchar\n                    Meaning: PRIMARY KEY - unique PDO well identifier. Join with ATNM_Dev.WellMonitoringReport.pdo_well_id, Revenue.Well_ID, SAP_DRILLING_SEQUENCE.Well_ID\n                    View Purpose: Comprehensive well monitoring with progress, MOC, dates, SAP data. Links to ATNM_Dev tables via pdo_well_id.\n                    Search Terms: well progress monitoring MOC management change rig schedule timeline",
- .\Bashira-Intelligence\appmaster_bm25_documents.json:13: "semantic": "PRIMARY KEY - unique PDO well identifier. Join with ATNM_Dev.WellMonitoringReport.pdo_well_id, Revenue.Well_ID, SAP_DRILLING_SEQUENCE.Well_ID"
- .\Bashira-Intelligence\appmaster_bm25_documents.json:115: "document": "VIEW COLUMN: AppMasterDB.dbo.vw_JobProgress.Well ID / Project ID\n                    Data Type: int\n                    Meaning: PDO well identifier\n                    View Purpose: Weekly job progress with plan vs actual bucketed by week. Shows Category, Well details, PO numbers, and weekly plan/actual percentages.\n                    Search Terms: job progress weekly plan actual target achievement productivity tracking",
- .\Bashira-Intelligence\appmaster_bm25_documents.json:117: "semantic": "PDO well identifier"
- .\Bashira-Intelligence\appmaster_bm25_documents.json:330: "document": "VIEW COLUMN: AppMasterDB.dbo.vw_JOB_COST.Well ID\n                    Data Type: nvarchar\n                    Meaning: PDO well identifier\n                    View Purpose: Job cost tracking - compares planned vs actual resources (employees and equipment) per well per activity\n                    Search Terms: job cost resource planning actual employee equipment hours rate budget",
- .\Bashira-Intelligence\build_appmaster_kb.py:133: ("pdo_well_id", "nvarchar", "PDO well identifier - PRIMARY KEY"),

## Location PO (Total: 129)
- .\columns_updated_new.csv:173: location_po_no,WellMonitoringReport,Location Po No field in WellMonitoringReport
- .\columns_updated_new.csv:174: location_po_recvd_date,WellMonitoringReport,Location Po Recvd Date field in WellMonitoringReport
- .\columns_updated_new.csv:303: location_po_no,WellMonitoringReport_Latest,Location Po No field in WellMonitoringReport_Latest
- .\columns_updated_new.csv:304: location_po_recvd_date,WellMonitoringReport_Latest,Location Po Recvd Date field in WellMonitoringReport_Latest
- .\DATABASE_MASTER_DUMP.md:534: | location_po_no | nvarchar | YES |
- .\DATABASE_MASTER_DUMP.md:535: | location_po_recvd_date | date | YES |
- .\DATABASE_MASTER_DUMP.md:840: | location_po_recvd_date | nvarchar | YES |
- .\DATABASE_MASTER_DUMP.md:968: | location_po_recvd_date_d | date | YES |
- .\KNOWLEDGE_BANK_COMPLETE.md:376: | location_po_no | nvarchar | Location Po No |
- .\KNOWLEDGE_BANK_COMPLETE.md:377: | location_po_recvd_date | date | Date field |
- .\NEO4J_TABLES_SCHEMA_CHECK.md:235: | 11 | location_po_no | nvarchar | YES | 255 |
- .\NEO4J_TABLES_SCHEMA_CHECK.md:236: | 12 | location_po_recvd_date | nvarchar | YES | 255 |
- .\NEO4J_TABLES_SCHEMA_CHECK.md:371: | 12 | location_po_no | nvarchar | YES | 255 |
- .\NEO4J_TABLES_SCHEMA_CHECK.md:372: | 13 | location_po_recvd_date | date | YES |  |
- .\Results (1).csv:220: WellMonitoringReport,location_po_no,bigint

## Cluster (Total: 325)
- .\BM25_NEO4J_MINILM_INTEGRATION.md:167: - Table linked to Cluster, Rig
- .\BM25_NEO4J_MINILM_INTEGRATION.md:178: 3. `Cluster` - WellMonitoringReport
- .\BM25_NEO4J_MINILM_INTEGRATION.md:186: WHERE Cluster = 'Nimr'
- .\columns_updated_new.csv:153: Cluster,WBS_Master_Tracker_,Operational cluster
- .\columns_updated_new.csv:291: Cluster,WellMonitoringReport,Operational cluster area Nimr or Marmul location grouping
- .\columns_updated_new.csv:421: Cluster,WellMonitoringReport_Latest,Operational cluster Nimr or Marmul
- .\create_knowledge_bank.py:18: 'business': 'Weekly progress snapshot per well - 128 columns covering all construction stages, dates, rig assignments, and progress percentages for Nimr and Marmul clusters.',
- .\create_knowledge_bank.py:19: 'semantic': 'Main well monitoring data with physical progress, schedule dates, and status for all operational wells. Key columns: pdo_well_id (unique well identifier), over_all_progress_percentages (0-1 decimal), Cluster (Nimr/Marmul), rig_no, well_name_after_spud.'
- .\create_knowledge_bank.py:58: 'business': 'Work Breakdown Structure (WBS) codes mapping to wells, plants, clusters, and activities.',
- .\create_knowledge_bank.py:127: elif col_name == 'Cluster':
- .\create_knowledge_bank.py:128: desc = 'Operational cluster (Nimr or Marmul)'
- .\DATABASE_MASTER_DUMP.md:32: - `Cluster` column exists in WellMonitoringReport for filtering by location
- .\DATABASE_MASTER_DUMP.md:497: | Cluster | nvarchar | YES |
- .\DATABASE_MASTER_DUMP.md:508: |Sr_No|WBS_Code|Project_Def|WD_PRJ|Plant_Code|Plant_Name|Cluster|Well_ID_Project_PO|Activity_code|Activity|
- .\INTELLIGENCE_ARCHITECTURE.md:86: | WellMonitoringReport | Weekly progress snapshot per well - 128 columns covering all construction stages, dates, rig assignments, and progress percentages for Nimr and Marmul clusters. | - |

## Flowline (Total: 1539)
- .\columns_updated_new.csv:207: flowline_-_purpose_value,WellMonitoringReport,Flowline - Purpose Value field in WellMonitoringReport
- .\columns_updated_new.csv:219: flowline_construction_progress,WellMonitoringReport,Flowline Construction Progress field in WellMonitoringReport
- .\columns_updated_new.csv:337: flowline_-_purpose_value,WellMonitoringReport_Latest,Flowline - Purpose Value field in WellMonitoringReport_Latest
- .\columns_updated_new.csv:349: flowline_construction_progress,WellMonitoringReport_Latest,Flowline Construction Progress field in WellMonitoringReport_Latest
- .\DATABASE_MASTER_DUMP.md:296: |5|December|2025|2025-12-01|NA|110754265|SHAJI|Sub contractor|Nimr Flowline|FWP-0702|
- .\DATABASE_MASTER_DUMP.md:297: |9|December|2025|2025-12-01|arul|116020874|JEBARAJ|Sub contractor|Nimr Flowline|FWM-0501|
- .\DATABASE_MASTER_DUMP.md:317: |NF0010|Nimr Flowline|2|278c5587-bba7-46ea-9c6a-d79aa8|
- .\DATABASE_MASTER_DUMP.md:568: | flowline_-_purpose_value | nvarchar | YES |
- .\DATABASE_MASTER_DUMP.md:580: | flowline_construction_progress | decimal | YES |
- .\DATABASE_MASTER_DUMP.md:885: | flowline_construction_progress | nvarchar | YES |
- .\DATABASE_MASTER_DUMP.md:981: | flowline_construction_progress_p | decimal | YES |
- .\INTELLIGENCE_ARCHITECTURE.md:31: The practical result is that the system learns the exact language that Al Tasnim's team uses the terms like Purpose Value, ODC South, PH score, Nimr Flowline  and incorporates them correctly into SQL without manual programming.
- .\INTELLIGENCE_ARCHITECTURE.md:158: | Category breakdown | How does average progress differ between Nimr Flowline and Nimr Location categories? | WellMonitoringReport + ProjectIDs |
- .\INTELLIGENCE_ARCHITECTURE.md:164: | Revenue tracking | What is the total actual revenue versus planned revenue for Nimr Flowline wells this month? | Revenue + Job_Progress_Report_GB |
- .\KNOWLEDGE_BANK_COMPLETE.md:410: | flowline_-_purpose_value | nvarchar | Flowline - Purpose Value |

## Rig ID (Total: 54)
- .\columns_updated_new.csv:164: rig_no,WellMonitoringReport,Rig identifier assigned to well for example SWER102 SWER103
- .\columns_updated_new.csv:294: rig_no,WellMonitoringReport_Latest,Rig identifier assigned to well
- .\create_knowledge_bank.py:126: desc = 'Rig identifier (e.g., SWER102)'
- .\KNOWLEDGE_BANK.md:53: - `rig_no` - Rig identifier (e.g., 'SWER102')
- .\KNOWLEDGE_BANK_COMPLETE.md:367: | rig_no | nvarchar | Rig identifier (e.g., SWER102) |
- .\update_columns.py:26: ('rig_no', 'WellMonitoringReport'): 'Rig identifier assigned to well for example SWER102 SWER103',
- .\update_columns.py:40: ('rig_no', 'WellMonitoringReport_Latest'): 'Rig identifier assigned to well',
- .\Bashira-Intelligence\appmasterdb_bm25_documents.json:257: "document": "VIEW: AppMasterDB.dbo.vw_JOB_COST\n                PURPOSE: Job cost - planned vs actual resources (employees, equipment)\n                SOURCE TABLES: dbo.task_daily, dbo.Revenue, dbo.crews, dbo.Employee, dbo.company_employees, dbo.EmployeeType, dbo.Equipment, dbo.EquipmentType, dbo.ActivityMasterMapping\n                \n                KEY COLUMNS:\n                {\n  \"Project\": {\n    \"type\": \"nvarchar\",\n    \"logic\": \"Revenue.rigcode - the rig identifier\"\n  },\n  \"Well ID\": {\n    \"type\": \"nvarchar\",\n    \"logic\": \"task_daily.well_id\"\n  },\n  \"Activity ID\": {\n    \"type\": \"nvarchar\",\n    \"logic\": \"LEFT(task_code, 8) - first 8 characters\"\n  },\n  \"crew code\": {\n    \"type\": \"nvarchar\",\n    \"logic\": \"task_daily.crew_code \\u2192 crews.Code\"\n  },\n  \"Plan Employee Name\": {\n    \"type\": \"nvarchar\",\n    \"logic\": \"FROM crews.Employees JSON \\u2192 Employee table\"\n  },\n  \"Actual Employee Name\": {\n    \"type\": \"nvarchar\",\n    \"logic\": \"FROM task_daily.employee_ids_text JSON \\u2192 Employee\"\n  },\n  \"Effective Work Hours\": {\n    \"type\": \"decimal\",\n    \"logic\": \"JSON_VALUE(daily_data, '$.actual_hours')\"\n  }\n}\n                \n                BUSINESS LOGIC:\n                {\n  \"activity_extraction\": \"LEFT(LTRIM(RTRIM(task_code)), 8)\",\n  \"crew_json_explode\": \"OPENJSON(c.Employees) to get employee IDs\",\n  \"resource_pairing\": \"Full outer join Planned vs Actual on: well_id + ActionOn + ActivityID + resource_type + PGCode + rn\",\n  \"project_prefix\": \"M\\u2192MML, N\\u2192NIM from first letter of rigcode\"\n}\n                \n                SQL PATTERNS:\n                {}",
- .\Bashira-Intelligence\appmasterdb_bm25_documents.json:263: "document": "VIEW COLUMN: AppMasterDB.dbo.vw_JOB_COST.Project\n                    DATA TYPE: nvarchar\n                    DERIVED FROM: \n                    LOGIC: Revenue.rigcode - the rig identifier\n                    \n                    VIEW PURPOSE: Job cost - planned vs actual resources (employees, equipment)",
- .\Bashira-Intelligence\appmasterdb_bm25_documents.json:265: "semantic": "Revenue.rigcode - the rig identifier",
- .\Bashira-Intelligence\appmasterdb_complete_knowledge.json:199: "logic": "Revenue.rigcode - the rig identifier"
- .\Bashira-Intelligence\appmasterdb_complete_knowledge.py:151: "Project": {"type": "nvarchar", "logic": "Revenue.rigcode - the rig identifier"},
- .\Bashira-Intelligence\appmaster_bm25_documents.json:39: "document": "VIEW COLUMN: AppMasterDB.dbo.WellMonitoringReport.rig_no\n                    Data Type: nvarchar\n                    Meaning: Drilling rig identifier - links to crews.Code\n                    View Purpose: Comprehensive well monitoring with progress, MOC, dates, SAP data. Links to ATNM_Dev tables via pdo_well_id.\n                    Search Terms: well progress monitoring MOC management change rig schedule timeline",
- .\Bashira-Intelligence\appmaster_bm25_documents.json:41: "semantic": "Drilling rig identifier - links to crews.Code"
- .\Bashira-Intelligence\appmaster_knowledge_base.json:40: "Project": "Revenue.rigcode - the rig identifier (NL0010, NF0010 etc)",

## Rig (Total: 476)
- .\BM25_NEO4J_MINILM_INTEGRATION.md:167: - Table linked to Cluster, Rig
- .\columns_updated_new.csv:111: rigcode,Revenue,Rig code associated with revenue
- .\columns_updated_new.csv:145: Move_days,SAP_DRILLING_SEQUENCE,Number of days required for rig move
- .\columns_updated_new.csv:164: rig_no,WellMonitoringReport,Rig identifier assigned to well for example SWER102 SWER103
- .\columns_updated_new.csv:176: last_week_exp.rig_on_location_sap_data,WellMonitoringReport,Last Week Exp.Rig On Location Sap Data field in WellMonitoringReport
- .\columns_updated_new.csv:177: latest_exp.rig_on_location_sap_data,WellMonitoringReport,Latest Exp.Rig On Location Sap Data field in WellMonitoringReport
- .\columns_updated_new.csv:178: exp.rig_off_location_sap_data,WellMonitoringReport,Exp.Rig Off Location Sap Data field in WellMonitoringReport
- .\columns_updated_new.csv:218: const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date,WellMonitoringReport,Const. Complete Date Including F L Final Hydro Test 1 Day Before Rig On Date field in WellMonitoringReport
- .\columns_updated_new.csv:225: actual_rig_on_date,WellMonitoringReport,Actual date when rig was moved onto well location
- .\columns_updated_new.csv:226: actual_rig_off_date,WellMonitoringReport,Actual date when rig moved off well location completed
- .\columns_updated_new.csv:231: completion_type_rig_fbu_or_rsr_hoist,WellMonitoringReport,Completion Type Rig Fbu Or Rsr Hoist field in WellMonitoringReport
- .\columns_updated_new.csv:294: rig_no,WellMonitoringReport_Latest,Rig identifier assigned to well
- .\columns_updated_new.csv:306: last_week_exp.rig_on_location_sap_data,WellMonitoringReport_Latest,Last Week Exp.Rig On Location Sap Data field in WellMonitoringReport_Latest
- .\columns_updated_new.csv:307: latest_exp.rig_on_location_sap_data,WellMonitoringReport_Latest,Latest Exp.Rig On Location Sap Data field in WellMonitoringReport_Latest
- .\columns_updated_new.csv:308: exp.rig_off_location_sap_data,WellMonitoringReport_Latest,Exp.Rig Off Location Sap Data field in WellMonitoringReport_Latest


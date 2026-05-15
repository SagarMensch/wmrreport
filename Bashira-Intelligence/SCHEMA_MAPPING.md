# Schema Mapping - Critical Reference

## Primary Well ID (Join Key)
- **WellMonitoringReport.pdo_well_id** ↔ **Revenue.Well_ID** ↔ **SAP_DRILLING_SEQUENCE.Well_ID** ↔ **Job_Progress_PlanSnapshot.Well_ID** ↔ **Job_Progress_Report_GB.Well ID**

## Column Meanings

### WellMonitoringReport
| Column | Meaning | Example |
|--------|---------|---------|
| pdo_well_id | PDO-assigned unique well ID | '34422', '31339' |
| well_location | Physical location name | 'AL BURJ_26_MC_OP2', 'NIMRG_2205240004_AP2' |
| well_name_after_spud | Official well name after spud | 'AL BURJ-280', 'AMIN-580' |
| rig_no | Rig number working on well | 'SWER101', 'SWER149' |
| Cluster | Operational cluster | 'Nimr', 'Marmul' |
| well_type | Well type | 'ESP', 'OP', 'WI' |
| over_all_progress_percentages | Overall completion (0-1 scale) | 0.63 |

### Revenue
| Column | Meaning | Example |
|--------|---------|---------|
| well_id | Links to pdo_well_id | '37230', '31339' |
| rigcode | RIG identifier - NOT location! | 'NF0010', 'NL0010', 'ML0010' |
| acutal_progress | Actual progress (note: misspelled) | 1.0000 |
| planned_progress | Planned progress (nvarchar!) | '1' |
| actual_purpose_value | Actual revenue | 0.0000 |
| planned_purpose_value | Planned revenue (nvarchar!) | '0' |

### SAP_DRILLING_SEQUENCE
| Column | Meaning | Example |
|--------|---------|---------|
| Well_ID | Links to pdo_well_id | '10207', '10239' |
| Well_Name | SAP well name | 'RKDS_2026_OP_LOC18' |
| Well_Location | SAP location | same as Well_Name |
| Field | Oil field name | 'RAKID SOUTH', 'NIMR', 'FAHUD' |
| Well_Function | Well purpose | 'Oil Producer', 'Water Injector' |

### Job_Progress_Report_GB
| Column | Meaning | Example |
|--------|---------|---------|
| Well ID | Links to pdo_well_id | 628, 729 |
| Well Name / Project Name | Human-readable name | (often NULL) |
| Week-1 Actual % | Weekly actual progress | 0.00, 14.17 |
| Week-1 Plan % | Weekly planned progress | 0.33, 13.70 |

## CRITICAL RULES

### 1. RIG CODE vs LOCATION
- NL0010, NF0010, ML0010, MS0010, etc. are **RIG CODES** - use Revenue.rigcode
- These are NOT in well_location - searching well_location for NL0010 returns ZERO results
- Example: `WHERE r.rigcode = 'NL0010'` - CORRECT
- Example: `WHERE w.well_location LIKE '%NL0010%'` - WRONG

### 2. Cluster vs Location
- Cluster is 'Nimr' or 'Marmul' - use WellMonitoringReport.Cluster
- well_location contains detailed location like 'NIMRG_2205240004_AP2'

### 3. Progress Columns
- Revenue: acutal_progress (note the typo), planned_progress (nvarchar!)
- WellMonitoringReport: over_all_progress_percentages (0-1 scale), cum_progress_for_this_week
- Job_Progress_Report_GB: Week-1 Actual %, Week-1 Plan %

### 4. Type Casting
- Revenue.planned_progress is NVARCHAR - MUST CAST before comparison
- Revenue.planned_purpose_value is NVARCHAR - MUST CAST before SUM

### 5. JOIN KEYS
- WellMonitoringReport.pdo_well_id = Revenue.Well_ID
- WellMonitoringReport.pdo_well_id = SAP_DRILLING_SEQUENCE.Well_ID
- WellMonitoringReport.pdo_well_id = Job_Progress_Report_GB.[Well ID]
- WellMonitoringReport.pdo_well_id = Job_Progress_PlanSnapshot.Well_ID

## Common Rig Codes
- NL0010, NF0010, ML0010, MS0010, MF0010
- MCOF10, MCWF10, MROP10, MRWF10
- NCOF10, NNSW10, NS0010

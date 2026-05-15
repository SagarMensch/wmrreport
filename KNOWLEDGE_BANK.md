# ATNM Knowledge Bank

## Database
- **Server**: 10.100.137.11
- **Database**: ATNM_Dev
- **User**: atnm_chatbot (read-only)
- **Driver**: ODBC Driver 18 for SQL Server

---

## Tables Overview (17 tables, ~240K rows)

| Table | Rows | Purpose |
|-------|------|---------|
| ActivityTaskPlan | 100,000 | Task planning with WBS hierarchy |
| WellMonitoringReport | 268 | Historical well weekly progress |
| WellMonitoringReport_Latest | 169 | Current week well progress snapshot |
| WMR_Full | 18,969 | Full denormalized WMR view |
| task_daily | 35,394 | Daily task execution tracking |
| Job_Progress_Report_GB | 439 | Weekly job progress actuals |
| Job_Progress_PlanSnapshot | 439 | Weekly job progress plans |
| Revenue | 21,566 | Revenue tracking by well |
| SAP_DRILLING_SEQUENCE | 6,159 | SAP drilling schedule |
| WBS_Master_Tracker_ | 81,846 | WBS code master data |
| Employee | 5,554 | Employee master |
| company_employees | 5,549 | Company employee data |
| crews | 5,758 | Crew assignments |
| PH_PRODUCTIVITY_WEEKLY_REPORT | 510 | Productivity metrics |
| ProjectIDs | 19 | Project master |
| schema_knowledge_base | 0 | (empty) |
| WellMonitoringReport_Staged | 169 | Staging table |

---

## Key Columns for Wells

### Primary Well Identifier (use for counting unique wells)
```
pdo_well_id → WellMonitoringReport, WellMonitoringReport_Latest, WMR_Full
Well_ID → Job_Progress_Report_GB, Job_Progress_PlanSnapshot, SAP_DRILLING_SEQUENCE, ActivityTaskPlan
well_id → Revenue, task_daily
Well_ID_Project_PO → WBS_Master_Tracker_
```

### Important Progress Columns
- `over_all_progress_percentages` - Overall progress (decimal 0-1, multiply by 100 for %)
- `progress` - Task/activity progress
- `engg_kpi_after_rig-off_days` - Days after rig-off for engineering completion
- `actual_rig_on_date` / `actual_rig_off_date` - Rig dates

### Cluster/Location
- `Cluster` - Operational cluster (e.g., 'Nimr')
- `rig_no` - Rig identifier (e.g., 'SWER102')

---

## Important Join Patterns

### 1. Count unique wells (CORRECT)
```sql
SELECT COUNT(DISTINCT pdo_well_id) FROM WellMonitoringReport_Latest WHERE Cluster = 'Nimr'
```

### 2. Join WellMonitoringReport with Job Progress
```sql
SELECT w.well_name_after_spud, w.rig_no, w.over_all_progress_percentages * 100 AS progress_pct
FROM WellMonitoringReport_Latest w
JOIN Job_Progress_Report_GB j ON w.pdo_well_id = j.[Well ID]
WHERE w.Cluster = 'Nimr'
```

### 3. Filter by progress threshold (use TRY_CAST for nvarchar columns)
```sql
SELECT well_name_after_spud, rig_no, Cluster
FROM WellMonitoringReport_Latest
WHERE TRY_CAST(over_all_progress_percentages AS FLOAT) < 0.5
```

### 4. Get wells with delays
```sql
SELECT well_name_after_spud, engg_kpi_after_rig-off_days, rig_no
FROM WellMonitoringReport_Latest
WHERE TRY_CAST(engg_kpi_after_rig-off_days AS INT) > 2
```

---

## Neo4j Graph Structure

### Node Types
- **Table** - Database tables (name, description, rowCount)
- **Column** - Table columns (name, description, dataType, isWellKey)
- **Well** - Central well hub node

### Relationship Types
- `HAS_COLUMN` / `BELONGS_TO` - Table → Column
- `REFERENCES_WELL` - Tables linking to wells
- `MIRRORS` - Tables with similar schema
- `JOINS_ON` - Foreign key relationships
- `CASTS_TO` - Type conversion lineage

---

## Semantic Search Setup

### BM25 / MiniLM
- Used for natural language query understanding
- Index column descriptions for semantic matching
- Example: "wells with less than 50% progress" → finds `over_all_progress_percentages < 0.5`

### Vector Embeddings
- Store semantic embeddings of table/column descriptions
- Enable similarity matching between user queries and schema

---

## SQL Generation Rules

1. **Always use pdo_well_id** for counting unique wells in WMR tables
2. **Use TRY_CAST** when comparing nvarchar columns to numbers
3. **Prefer WellMonitoringReport_Latest** for current data
4. **Return multiple useful columns** when showing wells (not just names)
5. **Multiply progress by 100** to show as percentage

---

## Common Query Patterns

| User Query | SQL Pattern |
|------------|-------------|
| "show wells in Nimr" | `SELECT * FROM WellMonitoringReport_Latest WHERE Cluster = 'Nimr'` |
| "wells with low progress" | `WHERE TRY_CAST(over_all_progress_percentages AS FLOAT) < 0.5` |
| "rig utilization" | `SELECT rig_no, COUNT(*) FROM WellMonitoringReport GROUP BY rig_no` |
| "wells behind schedule" | `WHERE TRY_CAST(engg_kpi_after_rig-off_days AS INT) > 2` |
| "revenue by well" | `JOIN Revenue ON well_id = pdo_well_id` |

---

## Notes

- All WMR table columns are nvARCHAR - need TRY_CAST for numeric comparisons
- pdo_well_id is the canonical well identifier across all well tables
- Cluster column enables geographic/operational filtering
- Job_Progress_Report_GB uses `[Well ID]` with brackets (contains space)
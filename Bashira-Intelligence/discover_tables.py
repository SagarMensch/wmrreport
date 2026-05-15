"""
Extract ALL table names, view names, column schemas from ATNM_Dev
and save to a comprehensive .md file.
"""
import pyodbc
import os, sys

SQL_SERVER   = "10.100.137.11"
SQL_DATABASE = "ATNM_Dev"
SQL_USER     = "atnm_chatbot"
SQL_PASSWORD = "Chatbot_ReadOnly_2026!"
CONN_STRING = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    f"SERVER={SQL_SERVER};"
    f"DATABASE={SQL_DATABASE};"
    f"UID={SQL_USER};"
    f"PWD={SQL_PASSWORD};"
    "Encrypt=yes;"
    "TrustServerCertificate=yes;"
    "Connection Timeout=15;"
)

OUT_FILE = os.path.join(os.path.dirname(__file__), "prediction_data", "full_schema_dump.md")
os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)

lines = []
def log(msg=""):
    lines.append(msg)
    print(msg)

try:
    conn = pyodbc.connect(CONN_STRING, timeout=15)
    log("✓ Connected to SQL Server")
except Exception as e:
    log(f"✗ Connection failed: {e}")
    sys.exit(1)

cursor = conn.cursor()

# ═══════════════════════════════════════════════════════════════
# SECTION 1: ALL TABLES AND VIEWS
# ═══════════════════════════════════════════════════════════════
log("\n# Full Schema Dump: ATNM_Dev Database")
log(f"\n## 1. All Tables & Views\n")
log("| # | Schema | Name | Type |")
log("|:--|:-------|:-----|:-----|")

cursor.execute("""
    SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE 
    FROM INFORMATION_SCHEMA.TABLES 
    ORDER BY TABLE_TYPE, TABLE_NAME
""")
all_tables = cursor.fetchall()
for i, row in enumerate(all_tables, 1):
    log(f"| {i} | {row[0]} | {row[1]} | {row[2]} |")

log(f"\n**Total: {len(all_tables)} objects**")

# ═══════════════════════════════════════════════════════════════
# SECTION 2: COLUMNS FOR EVERY TABLE/VIEW
# ═══════════════════════════════════════════════════════════════
log(f"\n## 2. Column Details Per Table/View\n")

cursor.execute("""
    SELECT 
        TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, 
        DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
        IS_NULLABLE, ORDINAL_POSITION
    FROM INFORMATION_SCHEMA.COLUMNS
    ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
""")
all_cols = cursor.fetchall()

# Group by table
from collections import defaultdict
table_cols = defaultdict(list)
for row in all_cols:
    key = f"{row[0]}.{row[1]}"
    table_cols[key].append(row)

for table_key in sorted(table_cols.keys()):
    cols = table_cols[table_key]
    tname = cols[0][1]
    tschema = cols[0][0]
    log(f"\n### `{tschema}.{tname}` ({len(cols)} columns)\n")
    log("| # | Column | Type | MaxLen | Nullable |")
    log("|:--|:-------|:-----|:-------|:---------|")
    for c in cols:
        maxlen = str(c[4]) if c[4] else "-"
        log(f"| {c[6]} | {c[2]} | {c[3]} | {maxlen} | {c[5]} |")

# ═══════════════════════════════════════════════════════════════
# SECTION 3: ROW COUNTS FOR KEY TABLES
# ═══════════════════════════════════════════════════════════════
log(f"\n## 3. Row Counts for Key Tables\n")
log("| Table | Row Count |")
log("|:------|:----------|")

key_tables = [
    "WMR", "WellMonitoringReport", "WMR_TaskPlan_csv_imported",
    "WMR_SQL_Bulk_Update", "Job_Progress_Report_GB", 
    "Job_Progress_PlanSnapshot", "PH_Productivity",
    "vw_JOB_COST", "task_daily", "ActivityTaskPlan",
    "Revenue", "Employee", "crews", "Equipment",
    "SAP_DRILLING_SEQUENCE_Staging", "ProjectIDs",
    "DesignTrackerCSVImport", "ActivityCodesNorms",
    "vw_JobProgress", "Daily_Plan_Report", "New_Daily_Plan",
    "data_table_sched_jsons", "WBS_Master_Tracker_",
    "PH_PRODUCTIVITY_WEEKLY_REPORT"
]

for tname in key_tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM [{tname}]")
        cnt = cursor.fetchone()[0]
        log(f"| {tname} | {cnt:,} |")
    except:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM dbo.[{tname}]")
            cnt = cursor.fetchone()[0]
            log(f"| {tname} | {cnt:,} |")
        except Exception as e:
            log(f"| {tname} | ✗ Error: {str(e)[:60]} |")

# ═══════════════════════════════════════════════════════════════
# SECTION 4: WMR HISTORY DEPTH (critical for TimesFM)
# ═══════════════════════════════════════════════════════════════
log(f"\n## 4. WMR Historical Depth Analysis\n")

try:
    cursor.execute("""
        SELECT 
            COUNT(*) as total_rows,
            COUNT(DISTINCT CAST(pdo_well_id AS NVARCHAR(50))) as unique_wells,
            MIN(Week_Number) as earliest_week,
            MAX(Week_Number) as latest_week
        FROM dbo.WMR
        WHERE pdo_well_id IS NOT NULL
    """)
    r = cursor.fetchone()
    log(f"- **Total rows in WMR**: {r[0]:,}")
    log(f"- **Unique wells**: {r[1]:,}")
    log(f"- **Earliest Week_Number**: {r[2]}")
    log(f"- **Latest Week_Number**: {r[3]}")
except Exception as e:
    log(f"✗ WMR query failed: {e}")

# Weeks per well distribution
try:
    cursor.execute("""
        SELECT 
            CAST(pdo_well_id AS NVARCHAR(50)) as well_id,
            COUNT(DISTINCT Week_Number) as week_count
        FROM dbo.WMR
        WHERE pdo_well_id IS NOT NULL
        GROUP BY CAST(pdo_well_id AS NVARCHAR(50))
    """)
    rows = cursor.fetchall()
    week_counts = [r[1] for r in rows]
    log(f"\n### Weeks-per-well distribution:")
    log(f"- Wells with 1 week:  {sum(1 for w in week_counts if w == 1)}")
    log(f"- Wells with 2-3 weeks: {sum(1 for w in week_counts if 2 <= w <= 3)}")
    log(f"- Wells with 4-10 weeks: {sum(1 for w in week_counts if 4 <= w <= 10)}")
    log(f"- Wells with 10-20 weeks: {sum(1 for w in week_counts if 10 < w <= 20)}")
    log(f"- Wells with 20+ weeks: {sum(1 for w in week_counts if w > 20)}")
    log(f"- **Average weeks per well**: {sum(week_counts)/len(week_counts):.1f}")
    log(f"- **Max weeks for any well**: {max(week_counts)}")
except Exception as e:
    log(f"✗ Week distribution query failed: {e}")

# ═══════════════════════════════════════════════════════════════
# SECTION 5: SAMPLE DATA FROM WMR (top 5 wells, all weeks)
# ═══════════════════════════════════════════════════════════════
log(f"\n## 5. Sample WMR Time-Series (5 wells)\n")

try:
    cursor.execute("""
        SELECT TOP 5 CAST(pdo_well_id AS NVARCHAR(50)) as wid
        FROM dbo.WMR 
        WHERE pdo_well_id IS NOT NULL 
        GROUP BY CAST(pdo_well_id AS NVARCHAR(50))
        HAVING COUNT(DISTINCT Week_Number) >= 3
        ORDER BY COUNT(DISTINCT Week_Number) DESC
    """)
    sample_wells = [r[0] for r in cursor.fetchall()]
    
    for wid in sample_wells:
        cursor.execute(f"""
            SELECT 
                CAST(pdo_well_id AS NVARCHAR(50)) as well_id,
                well_name_after_spud,
                Week_Number,
                over_all_progress_percentages,
                rig_no
            FROM dbo.WMR
            WHERE CAST(pdo_well_id AS NVARCHAR(50)) = ?
            ORDER BY Week_Number
        """, wid)
        rows = cursor.fetchall()
        log(f"\n**Well {wid}** ({rows[0][1] if rows else 'N/A'}):")
        log("| Week_Number | Progress | Rig |")
        log("|:------------|:---------|:----|")
        for r in rows:
            log(f"| {r[2]} | {r[3]} | {r[4]} |")
except Exception as e:
    log(f"✗ Sample query failed: {e}")

# ═══════════════════════════════════════════════════════════════
# WRITE TO FILE
# ═══════════════════════════════════════════════════════════════
conn.close()

with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"\n\n{'='*60}")
print(f"✓ Full schema dump saved to: {OUT_FILE}")
print(f"  Total lines: {len(lines)}")
print(f"{'='*60}")

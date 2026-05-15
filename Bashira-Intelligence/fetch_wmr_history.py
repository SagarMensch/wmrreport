"""
Phase 1: Extract ALL data needed for predictive forecasting.
Tables: WMR_Full (history), WellMonitoringReport (latest), 
        Job_Progress_Report_GB (plan vs actual), PH_PRODUCTIVITY_WEEKLY_REPORT
"""
import pyodbc, pandas as pd, os, sys

CONN_STRING = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=10.100.137.11;DATABASE=ATNM_Dev;"
    "UID=atnm_chatbot;PWD=Chatbot_ReadOnly_2026!;"
    "Encrypt=yes;TrustServerCertificate=yes;Connection Timeout=15;"
)
OUT = os.path.join(os.path.dirname(__file__), "prediction_data")
os.makedirs(OUT, exist_ok=True)

conn = pyodbc.connect(CONN_STRING, timeout=15)
print("✓ Connected")

# ═══════════════════════════════════════════════════════════════
# 1. WMR_Full — ALL historical weekly snapshots (THE TIME SERIES)
# ═══════════════════════════════════════════════════════════════
print("\n[1/4] Fetching WMR_Full (historical time-series)...")
try:
    df = pd.read_sql("""
        SELECT 
            pdo_well_id, well_name_after_spud, rig_no, well_type, well_location,
            over_all_progress_percentages, cum_progress_for_this_week,
            last_week_cum_progress, ohl_progress, flowline_construction_progress,
            [overall_loc._preparation_10_100], [overall_engg._10_100],
            [overall_const._10_100], overall_comm_progress_100,
            actual_start_date, actual_finish_date,
            actual_rig_on_date, actual_rig_off_date,
            [actual_eng._completion_date], [actual_comm._start_date],
            [actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date],
            [const._actual_start_date],
            [const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date],
            engineering_actual_start_date, engineering_actual_finish_date,
            actual_hoist_fbu_rsr_on_date, actual_hoist_fbu_rsr_off_date,
            wlctf_acceptanceapproval_from_production,
            flaf_issue_date, moc_raised, moc_approved,
            buffer_status, [engg_kpi_after_rig-off_days],
            access_road_5, earth_work_60, cellar_20,
            beam_pump_base_esp_pcp_foundation_5, hdpe_liner_instalat_4,
            mechani_60, electri_15, instrumentat_20,
            piping_mech_50, elect_30, instr_20,
            project_id, Week_Number
        FROM WMR_Full
        WHERE pdo_well_id IS NOT NULL AND pdo_well_id <> ''
        ORDER BY pdo_well_id, Week_Number
    """, conn)
    df.to_csv(os.path.join(OUT, "wmr_full_history.csv"), index=False)
    wells = df['pdo_well_id'].nunique()
    weeks = df.groupby('pdo_well_id')['Week_Number'].nunique()
    print(f"  ✓ {len(df):,} rows, {wells} wells")
    print(f"  ✓ Avg {weeks.mean():.1f} weeks/well, max {weeks.max()}, min {weeks.min()}")
    print(f"  ✓ Wells with 4+ weeks: {(weeks >= 4).sum()} (TimesFM ready)")
except Exception as e:
    print(f"  ✗ Failed: {e}")

# ═══════════════════════════════════════════════════════════════
# 2. WellMonitoringReport — Latest state per well (130 cols)
# ═══════════════════════════════════════════════════════════════
print("\n[2/4] Fetching WellMonitoringReport (latest state, ALL columns)...")
try:
    df2 = pd.read_sql("SELECT * FROM WellMonitoringReport", conn)
    df2.to_csv(os.path.join(OUT, "wmr_latest.csv"), index=False)
    print(f"  ✓ {len(df2)} wells, {len(df2.columns)} columns")
except Exception as e:
    print(f"  ✗ Failed: {e}")

# ═══════════════════════════════════════════════════════════════
# 3. Job_Progress_Report_GB — Weekly plan vs actual
# ═══════════════════════════════════════════════════════════════
print("\n[3/4] Fetching Job_Progress_Report_GB...")
try:
    df3 = pd.read_sql("SELECT * FROM Job_Progress_Report_GB", conn)
    df3.to_csv(os.path.join(OUT, "job_progress_gb.csv"), index=False)
    print(f"  ✓ {len(df3)} rows, {df3['Well ID'].nunique()} wells")
except Exception as e:
    print(f"  ✗ Failed: {e}")

# ═══════════════════════════════════════════════════════════════
# 4. PH_PRODUCTIVITY_WEEKLY_REPORT — Crew productivity
# ═══════════════════════════════════════════════════════════════
print("\n[4/4] Fetching PH_PRODUCTIVITY_WEEKLY_REPORT...")
try:
    df4 = pd.read_sql("SELECT * FROM PH_PRODUCTIVITY_WEEKLY_REPORT", conn)
    df4.to_csv(os.path.join(OUT, "ph_productivity.csv"), index=False)
    print(f"  ✓ {len(df4)} rows")
except Exception as e:
    print(f"  ✗ Failed: {e}")

conn.close()
print("\n✓ All data extracted to prediction_data/")

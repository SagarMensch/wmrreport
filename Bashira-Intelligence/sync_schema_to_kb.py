import pyodbc
import sys
from config import settings

def execute_renames():
    try:
        print(f"Connecting to: {settings.sql_connection_string}")
        conn = pyodbc.connect(settings.sql_connection_string, autocommit=True)
        cursor = conn.cursor()

        renames = [
            # WellMonitoringReport_Latest
            ("WellMonitoringReport_Latest.overall_loc_preparation_10_100", "overall_loc._preparation_10_100"),
            ("WellMonitoringReport_Latest.overall_const_10_100", "overall_const._10_100"),
            ("WellMonitoringReport_Latest.engg_kpi_after_rig_off_days", "engg_kpi_after_rig-off_days"),
            ("WellMonitoringReport_Latest.exp_rig_off_location_sap_data", "exp.rig_off_location_sap_data"),
            
            # WMR_Full
            ("WMR_Full.overall_loc_preparation_10_100", "overall_loc._preparation_10_100"),
            ("WMR_Full.overall_const_10_100", "overall_const._10_100"),
            ("WMR_Full.engg_kpi_after_rig_off_days", "engg_kpi_after_rig-off_days"),
            ("WMR_Full.exp_rig_off_location_sap_data", "exp.rig_off_location_sap_data")
        ]

        for old_obj, new_col in renames:
            try:
                print(f"Renaming '{old_obj}' -> '{new_col}'")
                cursor.execute(f"EXEC sp_rename '{old_obj}', '{new_col}', 'COLUMN';")
                print("  Success")
            except Exception as e:
                # If it fails, maybe it was already renamed or doesn't exist
                print(f"  Failed (Might already be renamed or invalid): {e}")

        conn.close()
        print("Schema sync complete!")
    except Exception as e:
        print(f"Connection/Execution error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    execute_renames()

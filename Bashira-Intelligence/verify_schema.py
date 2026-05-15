import pyodbc
from config import settings
conn = pyodbc.connect(settings.sql_connection_string)
cursor = conn.cursor()
cursor.execute("SELECT TOP 0 * FROM WellMonitoringReport_Latest")
columns = [column[0] for column in cursor.description]

cursor.execute("SELECT TOP 0 * FROM WMR_Full")
columns_full = [column[0] for column in cursor.description]
conn.close()

expected = [
    "overall_loc._preparation_10_100", 
    "overall_const._10_100", 
    "engg_kpi_after_rig-off_days", 
    "exp.rig_off_location_sap_data"
]

with open('verify_output.txt', 'w', encoding='utf-8') as f:
    f.write("WellMonitoringReport_Latest:\n")
    for c in columns:
        if c in expected:
             f.write(f"FOUND: {c}\n")
    missing = [e for e in expected if e not in columns]
    for m in missing:
        f.write(f"MISSING: {m}\n")
        
    f.write("\nWMR_Full:\n")
    for c in columns_full:
        if c in expected:
             f.write(f"FOUND: {c}\n")
    missing_full = [e for e in expected if e not in columns_full]
    for m in missing_full:
        f.write(f"MISSING: {m}\n")

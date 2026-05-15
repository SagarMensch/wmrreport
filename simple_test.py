"""Simple test"""
import pyodbc

SERVER = "10.100.137.11"
DATABASE = "AppMasterDB"
USERNAME = "atnm_chatbot"
PASSWORD = "Chatbot_ReadOnly_2026!"

conn_str = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes;'
conn = pyodbc.connect(conn_str, timeout=30)
cursor = conn.cursor()

# Get tables
cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' ORDER BY table_name")
tables = [t[0] for t in cursor.fetchall()]
print(f"Tables ({len(tables)}):")
for t in tables[:20]:
    print(f"  {t}")

# Check key tables
for table in ['WellMonitoringReport', 'WellMonitoringReport_Latest', 'Job_Progress_Report_GB']:
    try:
        cursor.execute(f"SELECT TOP 1 * FROM {table}")
        cols = len(cursor.description)
        print(f"\n{table}: {cols} columns - OK")
    except:
        print(f"\n{table}: NOT FOUND")

conn.close()

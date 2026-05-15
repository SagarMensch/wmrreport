"""Get full schema of key tables"""
import pyodbc

SERVER = "10.100.137.11"
DATABASE = "AppMasterDB"
USERNAME = "atnm_chatbot"
PASSWORD = "Chatbot_ReadOnly_2026!"

conn_str = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes;'
conn = pyodbc.connect(conn_str, timeout=60)
cursor = conn.cursor()

# Get WMR columns
print("=== WMR Table ===")
cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'WMR' ORDER BY ordinal_position")
for col in cursor.fetchall():
    print(f"  {col[0]}: {col[1]}")

# Check Job_Progress_Report_GB
print("\n=== Job_Progress_Report_GB ===")
try:
    cursor.execute("SELECT TOP 1 * FROM Job_Progress_Report_GB")
    cols = [d[0] for d in cursor.description]
    print(f"Found! {len(cols)} columns")
except:
    print("NOT FOUND")

# Check other progress tables
print("\n=== Job_Progress_PlanSnapshot ===")
try:
    cursor.execute("SELECT TOP 1 * FROM Job_Progress_PlanSnapshot")
    cols = [d[0] for d in cursor.description]
    print(f"Found! {len(cols)} columns")
    print("First 10:", cols[:10])
except Exception as e:
    print(f"NOT FOUND: {e}")

conn.close()

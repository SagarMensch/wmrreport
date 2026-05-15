"""Find WMR and WellMonitoring tables"""
import pyodbc

SERVER = "10.100.137.11"
DATABASE = "AppMasterDB"
USERNAME = "atnm_chatbot"
PASSWORD = "Chatbot_ReadOnly_2026!"

conn_str = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes;'
conn = pyodbc.connect(conn_str, timeout=60)
cursor = conn.cursor()

# Search for WellMonitoring or WMR tables
cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' AND (table_name LIKE '%Well%' OR table_name LIKE '%WMR%' OR table_name LIKE '%Progress%')")
tables = [t[0] for t in cursor.fetchall()]
print("Found Well/WMR/Progress tables:")
for t in tables:
    print(f"  {t}")

# Check columns for WMR table
print("\n--- WMR columns ---")
cursor.execute("SELECT TOP 1 * FROM WMR")
cols = [desc[0] for desc in cursor.description]
print(f"WMR has {len(cols)} columns")
print("First 10:", cols[:10])

conn.close()

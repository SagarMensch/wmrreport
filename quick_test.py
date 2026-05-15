"""Quick test - just get tables"""
import pyodbc

SERVER = "10.100.137.11"
DATABASE = "AppMasterDB"
USERNAME = "atnm_chatbot"
PASSWORD = "Chatbot_ReadOnly_2026!"

print("Connecting...")
conn_str = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes;'
conn = pyodbc.connect(conn_str, timeout=60)
cursor = conn.cursor()
print("Connected!")

print("Getting tables...")
cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' ORDER BY table_name")
tables = [t[0] for t in cursor.fetchall()]
print(f"Found {len(tables)} tables")

for t in tables:
    print(f"  {t}")

conn.close()

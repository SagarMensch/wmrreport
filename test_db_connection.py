"""Test connection to new SQL Server"""
import pyodbc
import sys

# New database credentials
SERVER = "10.100.137.11"
DATABASE = "AppMasterDB"
USERNAME = "atnm_chatbot"
PASSWORD = "Chatbot_ReadOnly_2026!"

print(f"Testing connection to: {SERVER}")
print(f"Database: {DATABASE}")
print(f"Username: {USERNAME}")
print("-" * 50)

try:
    conn_str = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes;'
    
    print("Attempting connection...")
    conn = pyodbc.connect(conn_str, timeout=30)
    print("[OK] Connected successfully!")
    
    # Test a simple query
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION")
    version = cursor.fetchone()
    print(f"\nSQL Server Version:\n{version[0][:100]}...")
    
    # Get list of tables
    cursor.execute("SELECT TOP 10 table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE'")
    tables = cursor.fetchall()
    print(f"\n[OK] Found {len(tables)} tables. First 10:")
    for t in tables:
        print(f"  - {t[0]}")
    
    conn.close()
    print("\n[SUCCESS] Connection test PASSED!")
    
except Exception as e:
    print(f"\n[FAILED] Connection FAILED!")
    print(f"Error: {str(e)}")
    sys.exit(1)

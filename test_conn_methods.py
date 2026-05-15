"""Test connection with different auth methods"""
import pyodbc
import sys

SERVER = "10.100.137.11"
DATABASE = "AppMasterDB"
USERNAME = "atnm_chatbot"
PASSWORD = "Chatbot_ReadOnly_2026!"

print("Testing different connection methods...\n")

# Method 1: With specific driver
try:
    conn_str = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes;'
    print(f"Method 1: {conn_str[:80]}...")
    conn = pyodbc.connect(conn_str, timeout=30)
    print("[OK] Method 1 worked!")
    conn.close()
except Exception as e:
    print(f"[FAILED] Method 1: {str(e)[:80]}")

# Method 2: With SQL Server auth
try:
    conn_str = f'SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};DRIVER=ODBC Driver 18 for SQL Server'
    print(f"\nMethod 2: {conn_str[:80]}...")
    conn = pyodbc.connect(conn_str, timeout=30)
    print("[OK] Method 2 worked!")
    conn.close()
except Exception as e:
    print(f"[FAILED] Method 2: {str(e)[:80]}")

# Method 3: Check if it's a different auth method
print("\nChecking available drivers...")
import pyodbc
for driver in pyodbc.drivers():
    print(f"  - {driver}")

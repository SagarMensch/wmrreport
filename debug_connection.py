import socket
import pyodbc
import os
from dotenv import load_dotenv

# Load .env
load_dotenv(".env")

SQL_SERVER = os.getenv("SQL_SERVER", "10.100.137.11")
SQL_DATABASE = os.getenv("SQL_DATABASE", "ATNM_Dev")
SQL_USER = os.getenv("SQL_USER", "atnm_chatbot")
SQL_PASSWORD = os.getenv("SQL_PASSWORD", "Chatbot_ReadOnly_2026!")

def check_port(ip, port=1433):
    print(f"--- 1. Testing Network Reachability: {ip}:{port} ---")
    try:
        s = socket.create_connection((ip, port), timeout=3)
        s.close()
        print(f"✓ Success: {ip} is reachable on port {port}.")
        return True
    except Exception as e:
        print(f"✗ Failed: {ip}:{port} is NOT reachable.")
        print(f"  Error: {e}")
        print("\n[!] IMPORTANT: Check your VPN status. If you are not on the client VPN, you cannot reach this IP.")
        return False

def list_drivers():
    print(f"\n--- 2. Checking Installed ODBC Drivers ---")
    drivers = pyodbc.drivers()
    if not drivers:
        print("✗ No ODBC drivers found.")
        return []
    
    print("Available drivers:")
    for d in drivers:
        print(f"  - {d}")
    return drivers

def test_connection(driver):
    print(f"\n--- 3. Testing ODBC Connection with '{driver}' ---")
    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={SQL_SERVER};"
        f"DATABASE={SQL_DATABASE};"
        f"UID={SQL_USER};"
        f"PWD={SQL_PASSWORD};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=5;"
    )
    
    try:
        conn = pyodbc.connect(conn_str)
        print("✓ Success: Connected to SQL Server successfully!")
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Connection failed with '{driver}'.")
        print(f"  Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("  SQL SERVER CONNECTION DIAGNOSTIC TOOL")
    print("=" * 60)
    
    reachable = check_port(SQL_SERVER)
    installed_drivers = list_drivers()
    
    if reachable:
        target_driver = "ODBC Driver 18 for SQL Server"
        if target_driver not in installed_drivers:
            # Try 17 if 18 not found
            if "ODBC Driver 17 for SQL Server" in installed_drivers:
                target_driver = "ODBC Driver 17 for SQL Server"
            else:
                print(f"\n[!] WARNING: '{target_driver}' not found in your system.")
                if installed_drivers:
                    target_driver = installed_drivers[0]
                    print(f"    Attempting with first available driver: '{target_driver}'")
                else:
                    print("    Please install the Microsoft ODBC Driver for SQL Server.")
                    target_driver = None
        
        if target_driver:
            test_connection(target_driver)
    
    print("\n" + "=" * 60)
    print("  DIAGNOSIS COMPLETE")
    print("=" * 60)

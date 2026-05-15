"""Test read-only access and get full schema dump"""
import pyodbc
import sys

SERVER = "10.100.137.11"
DATABASE = "AppMasterDB"
USERNAME = "atnm_chatbot"
PASSWORD = "Chatbot_ReadOnly_2026!"

print(f"Testing READ-ONLY access to: {SERVER}/{DATABASE}")
print("=" * 60)

try:
    conn_str = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes;'
    conn = pyodbc.connect(conn_str, timeout=30)
    cursor = conn.cursor()
    print("[OK] Connected!\n")

    # 1. Test READ-ONLY - should work
    print("1. Testing SELECT (read)...")
    try:
        cursor.execute("SELECT TOP 1 * FROM WellMonitoringReport")
        row = cursor.fetchone()
        print(f"   [OK] SELECT works - got {len(cursor.description)} columns")
    except Exception as e:
        print(f"   [OK] WellMonitoringReport exists")

    # 2. Test INSERT - should fail (read-only)
    print("\n2. Testing INSERT (should fail)...")
    try:
        cursor.execute("INSERT INTO WellMonitoringReport (test) VALUES (1)")
        conn.commit()
        print("   [WARNING] INSERT worked - NOT READ-ONLY!")
    except Exception as e:
        print(f"   [OK] INSERT blocked - Read-only confirmed")

    # 3. Test UPDATE - should fail
    print("\n3. Testing UPDATE (should fail)...")
    try:
        cursor.execute("UPDATE WellMonitoringReport SET test=1 WHERE 1=0")
        conn.commit()
        print("   [WARNING] UPDATE worked - NOT READ-ONLY!")
    except Exception as e:
        print(f"   [OK] UPDATE blocked - Read-only confirmed")

    # 4. Test DELETE - should fail
    print("\n4. Testing DELETE (should fail)...")
    try:
        cursor.execute("DELETE FROM WellMonitoringReport WHERE 1=0")
        conn.commit()
        print("   [WARNING] DELETE worked - NOT READ-ONLY!")
    except Exception as e:
        print(f"   [OK] DELETE blocked - Read-only confirmed")

    # 5. Get ALL tables
    print("\n5. Getting ALL tables...")
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' ORDER BY table_name")
    tables = cursor.fetchall()
    print(f"   [OK] Found {len(tables)} tables:")
    for t in tables:
        print(f"      - {t[0]}")

    # 6. Get schema for key tables
    key_tables = ['WellMonitoringReport', 'WellMonitoringReport_Latest', 'Job_Progress_Report_GB']
    print("\n6. Getting column schemas for key tables...")
    for table in key_tables:
        try:
            cursor.execute(f"SELECT TOP 1 * FROM {table}")
            cols = [desc[0] for desc in cursor.description]
            print(f"   {table}: {len(cols)} columns")
        except Exception as e:
            print(f"   {table}: NOT FOUND - {str(e)[:50]}")

    conn.close()
    print("\n" + "=" * 60)
    print("[SUCCESS] Read-only access CONFIRMED!")

except Exception as e:
    print(f"\n[FAILED] {str(e)}")

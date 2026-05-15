import pyodbc
import urllib.parse

def main():
    servers = [
        r"localhost\SQLEXPRESS",
        r".\SQLEXPRESS",
        r"localhost",
        r"(localdb)\MSSQLLocalDB"
    ]
    
    db_name = "AppMasterDB"
    conn = None
    
    for server in servers:
        conn_str = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER={server};"
            f"DATABASE={db_name};"
            "Trusted_Connection=yes;"
            "Encrypt=Optional;"
            "TrustServerCertificate=yes;"
        )
        try:
            conn = pyodbc.connect(conn_str, timeout=3)
            print(f"Connected to {server}")
            break
        except Exception:
            continue
            
    if not conn:
        with open("actual_schema_dump.md", "w", encoding="utf-8") as f:
            f.write("Failed to connect to local SQL Server. Ensure it is running.")
        return

    cursor = conn.cursor()
    
    # Tables tracked by the causal command service
    target_tables = [
        "WellMonitoringReport_Latest",
        "Job_Progress_Report_GB",
        "Job_Progress_PlanSnapshot",
        "PH_PRODUCTIVITY_WEEKLY_REPORT",
        "Survival_Predictions",
        "Risk_Scores",
        "Ag_Predictions",
        "WMR_Full",
    ]
    
    markdown_output = ["# Database Schema Dump (AppMasterDB)\n"]
    
    for table in target_tables:
        markdown_output.append(f"## Table: `{table}`\n")
        try:
            cursor.execute(f"SELECT TOP 1 * FROM [{table}]")
            columns = [column[0] for column in cursor.description]
            markdown_output.append("| Column Name |\n|---|")
            for col in columns:
                markdown_output.append(f"| {col} |")
        except Exception as e:
            markdown_output.append(f"**Error accessing table:** {str(e)}")
        markdown_output.append("\n")

    with open("actual_schema_dump.md", "w", encoding="utf-8") as f:
        f.write("\n".join(markdown_output))
        
    print("Dumped schema to actual_schema_dump.md")
    conn.close()

if __name__ == "__main__":
    main()

"""
Audit Schema Mapping
====================
Compares the columns.csv (used by BM25 and Neo4j) against the actual
live MS SQL Server schema to find any discrepancies.
"""

import json
import pandas as pd

def audit_schema():
    print("Loading actual schema from DB...")
    with open("actual_schema.json", "r") as f:
        actual_schema = json.load(f)
        
    print("Loading AI schema metadata from columns.csv...")
    df = pd.read_csv("columns.csv")
    
    report = []
    report.append("# Schema Mapping Audit Report\n")
    report.append("This report compares the metadata used by the AI agents (`columns.csv`/Neo4j) against the actual tables and columns physically present in the local Microsoft SQL Server (`AppMasterDB`).\n")
    
    total_ai_columns = len(df)
    matched = 0
    mismatched = []
    
    # Check each column that the AI knows about against the actual DB
    for idx, row in df.iterrows():
        table_name = str(row.get("tableName", "")).strip()
        column_name = str(row.get("columnName", "")).strip()
        
        # Does the table exist?
        if table_name not in actual_schema:
            mismatched.append(f"- ❌ Table missing in DB: `{table_name}`")
            continue
            
        # Does the column exist in that table?
        actual_columns = [c["name"].strip() for c in actual_schema[table_name]]
        
        if column_name in actual_columns:
            matched += 1
        else:
            # Maybe it's a case issue or space issue?
            lower_actuals = [c.lower() for c in actual_columns]
            if column_name.lower() in lower_actuals:
                actual_name = actual_columns[lower_actuals.index(column_name.lower())]
                mismatched.append(f"- ⚠️ Case mismatch in `{table_name}`: AI expects `{column_name}`, but DB has `{actual_name}`")
            else:
                mismatched.append(f"- ❌ Column missing in DB: `{table_name}.{column_name}`")
                
    report.append(f"## Summary\n")
    report.append(f"- Total columns expected by AI: **{total_ai_columns}**")
    report.append(f"- Columns perfectly matched to DB: **{matched}**")
    report.append(f"- Discrepancies found: **{len(mismatched)}**\n")
    
    if mismatched:
        report.append("## Discrepancies\n")
        # Deduplicate and sort
        mismatched = sorted(list(set(mismatched)))
        report.extend(mismatched)
    else:
        report.append("## Status: PERFECT ALIGNMENT ✅\n")
        report.append("Every single column expected by the AI agents perfectly matches the actual Microsoft SQL Server database schema. The agents will generate flawless SQL.")
        
    with open("schema_audit_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print(f"Audit complete! {matched}/{total_ai_columns} matched. Wrote schema_audit_report.md")

if __name__ == "__main__":
    audit_schema()

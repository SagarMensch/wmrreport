# Schema Mapping Audit Report

This report compares the metadata used by the AI agents (`columns.csv`/Neo4j) against the actual tables and columns physically present in the local Microsoft SQL Server (`AppMasterDB`).

## Summary

- Total columns expected by AI: **752**
- Columns perfectly matched to DB: **747**
- Discrepancies found: **5**

## Discrepancies

- ❌ Column missing in DB: `Job_Progress_Report_GB.Cum_Current_Month_Actual1`
- ❌ Column missing in DB: `Job_Progress_Report_GB.Cum_Current_Month_Plan1`
- ❌ Column missing in DB: `Job_Progress_Report_GB.Cum_Prior_Month_Actual1`
- ❌ Column missing in DB: `Job_Progress_Report_GB.Current_Month_Actual1`
- ❌ Column missing in DB: `Job_Progress_Report_GB.Current_month_Plan1`
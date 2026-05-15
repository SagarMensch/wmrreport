# Neo4j Current State Dump

## Tables
- ActivityTaskPlan: The master execution table that records every task planned and executed against each well. Tracks th
- Employee: The master personnel directory for Al Tasnim Enterprises staff. Stores core details of all employees
- Job_Progress_Report_GB: The weekly job progress report table for all wells and projects under the ODC South contract. Each r
- PH_PRODUCTIVITY_WEEKLY_REPORT: A master weekly reporting table that tracks the productivity index (PI) scores and average productiv
- ProjectIDs: A small master reference/lookup directory with approximately 19 rows used to store high-level projec
- Revenue: The financial tracking table that records planned and actual revenue (known as Purpose Value in OMR)
- SAP_DRILLING_SEQUENCE: The primary master table for rig scheduling, activity sequences, and operational timelines synchroni
- WBS_Master_Tracker_: The master tracking and mapping table for Work Breakdown Structure (WBS) codes. Links specific WBS c
- WMR_Full: A comprehensive view or denormalized table that combines the full Well Monitoring Report data with e
- WellMonitoringReport: The master weekly progress snapshot table for all wells across operational clusters (Nimr and Marmul
- WellMonitoringReport_Latest: Contains the same 130-column structure as WellMonitoringReport but filtered to store only the most r
- task_daily: The daily execution tracking table that records day-to-day progress for each task. Captures granular

## Columns

### ActivityTaskPlan
- row_id: Row Id field in ActivityTaskPlan
- source_id: Source Id field in ActivityTaskPlan
- Data: Data field in ActivityTaskPlan
- ancestor: Ancestor field in ActivityTaskPlan
- duration: Duration field in ActivityTaskPlan
- progress: Progress percentage or completion status
- crew_uid: Crew Uid field in ActivityTaskPlan
- crew_type: Crew Type field in ActivityTaskPlan
- qty: Qty field in ActivityTaskPlan
- manhours: Manhours field in ActivityTaskPlan
- weightage: Weightage field in ActivityTaskPlan

## Relationships
- Table -> HAS_COLUMN -> Column: 11
- Column -> BELONGS_TO -> Table: 11
import pyodbc

conn_str = (
    'DRIVER={ODBC Driver 18 for SQL Server};'
    'SERVER=10.100.137.11;'
    'DATABASE=ATNM_Dev;'
    'UID=atnm_chatbot;'
    'PWD=Chatbot_ReadOnly_2026!;'
    'Encrypt=yes;'
    'TrustServerCertificate=yes;'
)

conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

tables = [
    'ActivityTaskPlan', 'Employee', 'Job_Progress_Report_GB', 
    'PH_PRODUCTIVITY_WEEKLY_REPORT', 'ProjectIDs', 'Revenue', 
    'SAP_DRILLING_SEQUENCE', 'WBS_Master_Tracker_', 
    'WellMonitoringReport', 'WellMonitoringReport_Latest', 'task_daily'
]

col_descriptions = {
    ('pdo_well_id', 'WellMonitoringReport'): 'PDO unique well identifier primary key for all wells use for counting distinct wells',
    ('well_name_after_spud', 'WellMonitoringReport'): 'Official well name after spudding operation',
    ('rig_no', 'WellMonitoringReport'): 'Rig identifier assigned to well for example SWER102 SWER103',
    ('Cluster', 'WellMonitoringReport'): 'Operational cluster area Nimr or Marmul location grouping',
    ('over_all_progress_percentages', 'WellMonitoringReport'): 'Overall well completion progress decimal between 0 and 1 multiply by 100 for percentage display',
    ('progress', 'WellMonitoringReport'): 'Physical progress percentage decimal representing completion status',
    ('engg_kpi_after_rig-off_days', 'WellMonitoringReport'): 'Engineering KPI days after rig-off before completion target is less than 2 days',
    ('actual_rig_on_date', 'WellMonitoringReport'): 'Actual date when rig was moved onto well location',
    ('actual_rig_off_date', 'WellMonitoringReport'): 'Actual date when rig moved off well location completed',
    ('scr_no', 'WellMonitoringReport'): 'Service Request Completion document number SCR for well handover',
    ('well_type', 'WellMonitoringReport'): 'Type of well ESP PCP Oil Gas completion method',
    ('well_location', 'WellMonitoringReport'): 'Geographic location coordinates of well site',
    ('actual_start_date', 'WellMonitoringReport'): 'Actual start date of well construction activity',
    ('actual_finish_date', 'WellMonitoringReport'): 'Actual finish completion date of well',
    ('pdo_well_id', 'WellMonitoringReport_Latest'): 'PDO unique well identifier primary key for latest week snapshot',
    ('well_name_after_spud', 'WellMonitoringReport_Latest'): 'Official well name after spudding operation',
    ('rig_no', 'WellMonitoringReport_Latest'): 'Rig identifier assigned to well',
    ('Cluster', 'WellMonitoringReport_Latest'): 'Operational cluster Nimr or Marmul',
    ('over_all_progress_percentages', 'WellMonitoringReport_Latest'): 'Overall completion percentage decimal 0 to 1',
    ('Well ID', 'Job_Progress_Report_GB'): 'Unique well identifier for job progress tracking join key with WellMonitoringReport pdo_well_id',
    ('Well Name / Project Name', 'Job_Progress_Report_GB'): 'Name of well or project for reporting',
    ('PO No', 'Job_Progress_Report_GB'): 'Purchase Order number for contract',
    ('WBS No', 'Job_Progress_Report_GB'): 'Work Breakdown Structure code identifier',
    ('Week-1 Plan %', 'Job_Progress_Report_GB'): 'Week 1 planned progress percentage target',
    ('Week-1 Actual %', 'Job_Progress_Report_GB'): 'Week 1 actual progress achieved percentage',
    ('Current Month Plan %', 'Job_Progress_Report_GB'): 'Current month planned progress percentage',
    ('Current Month Actual %', 'Job_Progress_Report_GB'): 'Current month actual progress achieved percentage',
    ('Purpose Value', 'Job_Progress_Report_GB'): 'Revenue purpose value in OMR currency for contract',
    ('Target End', 'Job_Progress_Report_GB'): 'Target end date for well completion',
    ('Well_ID', 'ActivityTaskPlan'): 'Well identifier linking task to specific well',
    ('project_id', 'ActivityTaskPlan'): 'Project identifier for task grouping',
    ('code', 'ActivityTaskPlan'): 'Task activity code from work breakdown structure',
    ('text', 'ActivityTaskPlan'): 'Task description or name',
    ('progress', 'ActivityTaskPlan'): 'Task completion progress percentage',
    ('duration', 'ActivityTaskPlan'): 'Planned duration for task completion',
    ('crew_uid', 'ActivityTaskPlan'): 'Unique identifier of crew assigned to task',
    ('crew_type', 'ActivityTaskPlan'): 'Type of crew discipline civil electrical mechanical',
    ('task_assignee', 'ActivityTaskPlan'): 'Employee ID or name assigned to complete task',
    ('actual_start', 'ActivityTaskPlan'): 'Actual start date of task execution',
    ('actual_end', 'ActivityTaskPlan'): 'Actual end date of task completion',
    ('well_id', 'task_daily'): 'Well identifier for daily task record',
    ('project_id', 'task_daily'): 'Project identifier',
    ('crew_code', 'task_daily'): 'Crew code assigned to daily task',
    ('crew_type', 'task_daily'): 'Crew discipline type',
    ('task_assignee', 'task_daily'): 'Person assigned to task',
    ('progress', 'task_daily'): 'Daily progress percentage completed',
    ('data_hours', 'task_daily'): 'Actual hours worked on task',
    ('data_qty', 'task_daily'): 'Actual quantity completed',
    ('actual_start', 'task_daily'): 'Actual start date',
    ('actual_end', 'task_daily'): 'Actual end date',
    ('well_id', 'Revenue'): 'Well identifier for revenue record',
    ('rigcode', 'Revenue'): 'Rig code associated with revenue',
    ('code', 'Revenue'): 'Activity code for revenue categorization',
    ('actual_purpose_value', 'Revenue'): 'Actual revenue earned in OMR',
    ('planned_purpose_value', 'Revenue'): 'Planned revenue target in OMR',
    ('total_purpose_value', 'Revenue'): 'Total purpose value for well',
    ('PH Emp ID', 'PH_PRODUCTIVITY_WEEKLY_REPORT'): 'Project Holder employee ID for productivity tracking',
    ('PH Name', 'PH_PRODUCTIVITY_WEEKLY_REPORT'): 'Project Holder name supervisor',
    ('Category', 'PH_PRODUCTIVITY_WEEKLY_REPORT'): 'Category of work for productivity measurement',
    ('Crew Type', 'PH_PRODUCTIVITY_WEEKLY_REPORT'): 'Type of crew discipline',
    ('Average Productivity (%)', 'PH_PRODUCTIVITY_WEEKLY_REPORT'): 'Average productivity percentage score',
    ('Month PI (CMR)', 'PH_PRODUCTIVITY_WEEKLY_REPORT'): 'Monthly Productivity Index using CMR method',
    ('Month PI (T-Wise)', 'PH_PRODUCTIVITY_WEEKLY_REPORT'): 'Monthly Productivity Index using T-Wise method',
    ('Well_ID', 'SAP_DRILLING_SEQUENCE'): 'Well identifier from SAP system',
    ('Well_Name', 'SAP_DRILLING_SEQUENCE'): 'Well name in SAP',
    ('Work_Center', 'SAP_DRILLING_SEQUENCE'): 'SAP work center for operations',
    ('Field', 'SAP_DRILLING_SEQUENCE'): 'Oil field location name',
    ('Earl_start_date', 'SAP_DRILLING_SEQUENCE'): 'Earliest planned start date from SAP',
    ('Move_days', 'SAP_DRILLING_SEQUENCE'): 'Number of days required for rig move',
    ('PDO_Well_Type', 'SAP_DRILLING_SEQUENCE'): 'PDO classification of well type',
    ('UId', 'Employee'): 'Unique employee identifier for Al Tasnim staff',
    ('Name', 'Employee'): 'Employee full name',
    ('Email', 'Employee'): 'Employee email address',
    ('Status', 'Employee'): 'Employment status Active or Inactive',
    ('Supervisor', 'Employee'): 'ID of supervisor manager',
    ('Company', 'Employee'): 'Company name Al Tasnim Enterprises',
    ('Location', 'Employee'): 'Work location code',
    ('Well_ID_Project_PO', 'WBS_Master_Tracker_'): 'Composite well ID with project and PO information',
    ('WBS_Code', 'WBS_Master_Tracker_'): 'Work Breakdown Structure code',
    ('Cluster', 'WBS_Master_Tracker_'): 'Operational cluster',
    ('Project_Def', 'WBS_Master_Tracker_'): 'Project definition identifier',
    ('Activity_code', 'WBS_Master_Tracker_'): 'Activity code for WBS',
    ('Activity', 'WBS_Master_Tracker_'): 'Activity description',
    ('Code', 'ProjectIDs'): 'Project code identifier',
    ('ID', 'ProjectIDs'): 'Project identifier for joins',
}

output = ['columnName,tableName,description']

for table in tables:
    cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table}' ORDER BY ORDINAL_POSITION")
    for col in cursor.fetchall():
        col_name = col[0]
        key = (col_name, table)
        if key in col_descriptions:
            desc = col_descriptions[key]
        else:
            desc = col_name.replace('_', ' ').title() + ' field in ' + table
        output.append(f'{col_name},{table},{desc}')

with open('columns_updated_new.csv', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print(f'Updated columns_updated.csv with {len(output)-1} columns')
conn.close()

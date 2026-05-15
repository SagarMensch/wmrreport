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

tables_info = {
    'WellMonitoringReport': {
        'business': 'Weekly progress snapshot per well - 128 columns covering all construction stages, dates, rig assignments, and progress percentages for Nimr and Marmul clusters.',
        'semantic': 'Main well monitoring data with physical progress, schedule dates, and status for all operational wells. Key columns: pdo_well_id (unique well identifier), over_all_progress_percentages (0-1 decimal), Cluster (Nimr/Marmul), rig_no, well_name_after_spud.'
    },
    'WellMonitoringReport_Latest': {
        'business': 'Most recent week only, used for faster queries when historical trend is not required.',
        'semantic': 'Current week snapshot of well monitoring. Same structure as WellMonitoringReport but filtered to latest week. Use for real-time status queries.'
    },
    'Job_Progress_Report_GB': {
        'business': 'Plan versus actual progress percentage and revenue figures by well, by week, for each month.',
        'semantic': 'Weekly job progress tracking with plan vs actual. Columns include Week-1-5 Plan%, Week-1-5 Actual%, Purpose Value (revenue), Target End date. Well ID column name contains space: [Well ID].'
    },
    'Job_Progress_PlanSnapshot': {
        'business': 'Weekly plan fractions per well - W1 through W5 plus cumulative figures.',
        'semantic': 'Planning snapshots showing planned progress fractions. Used to compare actual vs planned progress.'
    },
    'ActivityTaskPlan': {
        'business': 'Every task planned and executed against each well - progress, manhours, crew assignments, quantities.',
        'semantic': 'Master execution table with WBS hierarchy. Contains task details including code, text, progress, duration, crew assignments, dates.'
    },
    'task_daily': {
        'business': 'Daily execution records - actual start, end, crew, quantity, progress per task.',
        'semantic': 'Daily task execution tracking with granular data. Links to ActivityTaskPlan via schedule_id. Contains actual hours, quantities, employee IDs.'
    },
    'Revenue': {
        'business': 'Planned and actual revenue (Purpose Value in OMR) per activity code per well.',
        'semantic': 'Financial tracking table. Revenue = Purpose Value earned proportionally to physical progress. Links to wells via well_id.'
    },
    'PH_PRODUCTIVITY_WEEKLY_REPORT': {
        'business': 'Weekly productivity index scores per crew supervisor (PH) across all categories.',
        'semantic': 'Productivity tracking for Project Holders. Contains PI scores (CMR and T-Wise methods) by week and month. Links to Employee via PH_Emp_ID.'
    },
    'SAP_DRILLING_SEQUENCE': {
        'business': 'Rig assignments, activity sequences, and move days from SAP.',
        'semantic': 'SAP master data for rig scheduling. Contains expected dates, well classifications, operational statuses. Used to cross-reference SAP schedule vs actual progress.'
    },
    'Employee': {
        'business': 'All Al Tasnim staff with supervisor hierarchy and location codes.',
        'semantic': 'Master personnel directory. Links to PH_PRODUCTIVITY_WEEKLY_REPORT via UId=PH_Emp_ID. Contains organizational hierarchy.'
    },
    'WBS_Master_Tracker_': {
        'business': 'Work Breakdown Structure (WBS) codes mapping to wells, plants, clusters, and activities.',
        'semantic': 'WBS code master with project definitions. Links specific WBS codes to wells via Well_ID_Project_PO.'
    },
    'ProjectIDs': {
        'business': 'Master reference/lookup directory for project identifiers.',
        'semantic': 'Small lookup table (19 rows) for project codes. Links to other tables via project_id.'
    },
    'crews': {
        'business': 'Crew compositions including supervisor, employees, and equipment.',
        'semantic': 'Crew assignment and composition data.'
    }
}

output = []
output.append('# ATNM Knowledge Bank - Complete Business & Semantic Mapping')
output.append('')
output.append('## Database Connection')
output.append('```')
output.append('Server: 10.100.137.11')
output.append('Database: ATNM_Dev')
output.append('User: atnm_chatbot (read-only)')
output.append('```')
output.append('')

cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME")
all_tables = [row[0] for row in cursor.fetchall()]

output.append(f'## All Tables in Production ({len(all_tables)} total)')
output.append('')
for t in all_tables:
    cursor.execute(f'SELECT COUNT(*) FROM {t}')
    count = cursor.fetchone()[0]
    output.append(f'- **{t}**: {count:,} rows')

output.append('')
output.append('---')
output.append('')

for table in sorted(tables_info.keys()):
    info = tables_info[table]
    
    cursor.execute(f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table}' ORDER BY ORDINAL_POSITION")
    cols = cursor.fetchall()
    cursor.execute(f'SELECT COUNT(*) FROM {table}')
    count = cursor.fetchone()[0]
    
    output.append(f'## {table}')
    output.append(f'**Rows:** {count:,}')
    output.append('')
    output.append(f'### Business Meaning')
    output.append(info['business'])
    output.append('')
    output.append(f'### Semantic Meaning')
    output.append(info['semantic'])
    output.append('')
    output.append(f'### Columns')
    output.append('| Column | Type | Description |')
    output.append('|--------|------|-------------|')
    
    for col in cols:
        col_name = col[0]
        dtype = col[1]
        
        if col_name == 'pdo_well_id':
            desc = 'UNIQUE well identifier - use for counting distinct wells'
        elif col_name == 'well_name_after_spud':
            desc = 'Official well name after spudding'
        elif col_name == 'rig_no':
            desc = 'Rig identifier (e.g., SWER102)'
        elif col_name == 'Cluster':
            desc = 'Operational cluster (Nimr or Marmul)'
        elif 'progress' in col_name.lower() and 'percent' in col_name.lower():
            desc = 'Progress percentage (0-1 decimal, multiply by 100 for %)'
        elif col_name == 'Well_ID' or col_name == 'well_id':
            desc = 'Well identifier (join key)'
        elif 'date' in col_name.lower():
            desc = 'Date field'
        else:
            desc = col_name.replace('_', ' ').title()
        
        output.append(f'| {col_name} | {dtype} | {desc} |')
    
    output.append('')

with open('KNOWLEDGE_BANK_COMPLETE.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print(f'Created KNOWLEDGE_BANK_COMPLETE.md with {len(tables_info)} detailed tables')
conn.close()

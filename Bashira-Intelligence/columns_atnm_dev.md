# AppMasterDB Schema Definition: columns_atnm_dev

| Column Name | Table/View Name | Data Type | Description |
| :--- | :--- | :--- | :--- |
| row_id | ActivityTaskPlan | bigint | Row Id field in ActivityTaskPlan |
| source_id | ActivityTaskPlan | nvarchar | Source Id field in ActivityTaskPlan |
| Data | ActivityTaskPlan | nvarchar | Data field in ActivityTaskPlan |
| ancestor | ActivityTaskPlan | nvarchar | Ancestor field in ActivityTaskPlan |
| duration | ActivityTaskPlan | nvarchar | Duration field in ActivityTaskPlan |
| progress | ActivityTaskPlan | nvarchar | Progress percentage or completion status |
| crew_uid | ActivityTaskPlan | nvarchar | Crew Uid field in ActivityTaskPlan |
| crew_type | ActivityTaskPlan | nvarchar | Crew Type field in ActivityTaskPlan |
| qty | ActivityTaskPlan | nvarchar | Qty field in ActivityTaskPlan |
| manhours | ActivityTaskPlan | nvarchar | Manhours field in ActivityTaskPlan |
| weightage | ActivityTaskPlan | nvarchar | Weightage field in ActivityTaskPlan |
| parent | ActivityTaskPlan | nvarchar | Parent field in ActivityTaskPlan |
| start_date | ActivityTaskPlan | datetime2 | Start Date field in ActivityTaskPlan |
| end_date | ActivityTaskPlan | datetime2 | End Date field in ActivityTaskPlan |
| target_start | ActivityTaskPlan | datetime2 | Target Start field in ActivityTaskPlan |
| target_end | ActivityTaskPlan | datetime2 | Target End field in ActivityTaskPlan |
| actual_start | ActivityTaskPlan | datetime2 | Actual Start field in ActivityTaskPlan |
| actual_end | ActivityTaskPlan | datetime2 | Actual End field in ActivityTaskPlan |
| qtyactual | ActivityTaskPlan | nvarchar | Qtyactual field in ActivityTaskPlan |
| qtyforacst | ActivityTaskPlan | nvarchar | Qtyforacst field in ActivityTaskPlan |
| manhoursactual | ActivityTaskPlan | nvarchar | Manhoursactual field in ActivityTaskPlan |
| manhourforacst | ActivityTaskPlan | nvarchar | Manhourforacst field in ActivityTaskPlan |
| code | ActivityTaskPlan | nvarchar | Code field in ActivityTaskPlan |
| text | ActivityTaskPlan | nvarchar | Text field in ActivityTaskPlan |
| type | ActivityTaskPlan | nvarchar | Type field in ActivityTaskPlan |
| schedule_id | ActivityTaskPlan | nvarchar | Schedule Id field in ActivityTaskPlan |
| project_id | ActivityTaskPlan | nvarchar | The project identifier this record belongs to |
| task_assignee | ActivityTaskPlan | nvarchar | Task Assignee field in ActivityTaskPlan |
| supervisor_email | ActivityTaskPlan | nvarchar | Supervisor Email field in ActivityTaskPlan |
| attributes | ActivityTaskPlan | nvarchar | Attributes field in ActivityTaskPlan |
| remaining_duration | ActivityTaskPlan | nvarchar | Remaining Duration field in ActivityTaskPlan |
| Resume_Suspend | ActivityTaskPlan | nvarchar | Resume Suspend field in ActivityTaskPlan |
| data_nonprod | ActivityTaskPlan | nvarchar | Data Nonprod field in ActivityTaskPlan |
| created_at | ActivityTaskPlan | datetime2 | Timestamp when record was created |
| updated_at | ActivityTaskPlan | datetime2 | Timestamp when record was last updated |
| Well_ID | ActivityTaskPlan | nvarchar | The unique well identifier |
| Parent_WBS | ActivityTaskPlan | nvarchar | Parent Wbs field in ActivityTaskPlan |
| Time_Stamp | ActivityTaskPlan | nvarchar | Time Stamp field in ActivityTaskPlan |
| id | company_employees | decimal | Id field in company_employees |
| UId | company_employees | nvarchar | Uid field in company_employees |
| Name | company_employees | nvarchar | Name field in company_employees |
| Status | company_employees | nvarchar | Status field in company_employees |
| locationCode | company_employees | nvarchar | Locationcode field in company_employees |
| Email | company_employees | nvarchar | Email field in company_employees |
| code | company_employees | nvarchar | Code field in company_employees |
| company | company_employees | nvarchar | Company field in company_employees |
| ID | crews | nvarchar | Id field in crews |
| Code | crews | nvarchar | Code field in crews |
| Account | crews | nvarchar | Account field in crews |
| Location | crews | nvarchar | Location field in crews |
| CrewType | crews | nvarchar | Crewtype field in crews |
| Supervisor | crews | nvarchar | Supervisor field in crews |
| Employees | crews | nvarchar | Employees field in crews |
| Equipments | crews | nvarchar | Equipments field in crews |
| id | Employee | int | Id field in Employee |
| UId | Employee | nvarchar | Uid field in Employee |
| Name | Employee | nvarchar | Name field in Employee |
| Email | Employee | nvarchar | Email field in Employee |
| Status | Employee | nvarchar | Status field in Employee |
| Supervisor | Employee | int | Supervisor field in Employee |
| Account | Employee | nvarchar | Account field in Employee |
| EmployeeType | Employee | int | Employeetype field in Employee |
| Company | Employee | nvarchar | Company field in Employee |
| Manager | Employee | int | Manager field in Employee |
| Location | Employee | int | Location field in Employee |
| Well_ID | Job_Progress_PlanSnapshot | nvarchar | The unique well identifier |
| project_id | Job_Progress_PlanSnapshot | nvarchar | The project identifier this record belongs to |
| Cum_Prior_Plan_frac | Job_Progress_PlanSnapshot | decimal | Cum Prior Plan Frac field in Job_Progress_PlanSnapshot |
| W1_Plan_frac | Job_Progress_PlanSnapshot | decimal | W1 Plan Frac field in Job_Progress_PlanSnapshot |
| W2_Plan_frac | Job_Progress_PlanSnapshot | decimal | W2 Plan Frac field in Job_Progress_PlanSnapshot |
| W3_Plan_frac | Job_Progress_PlanSnapshot | decimal | W3 Plan Frac field in Job_Progress_PlanSnapshot |
| W4_Plan_frac | Job_Progress_PlanSnapshot | decimal | W4 Plan Frac field in Job_Progress_PlanSnapshot |
| W5_Plan_frac | Job_Progress_PlanSnapshot | decimal | W5 Plan Frac field in Job_Progress_PlanSnapshot |
| CurrentMonthPlanFrac | Job_Progress_PlanSnapshot | decimal | Currentmonthplanfrac field in Job_Progress_PlanSnapshot |
| CumCurrentMonthPlanFrac | Job_Progress_PlanSnapshot | decimal | Cumcurrentmonthplanfrac field in Job_Progress_PlanSnapshot |
| Latest_Target_End | Job_Progress_PlanSnapshot | date | Latest Target End field in Job_Progress_PlanSnapshot |
| CreatedOn | Job_Progress_PlanSnapshot | datetime | Createdon field in Job_Progress_PlanSnapshot |
| Sl.No | Job_Progress_Report_GB | bigint | Sl.No field in Job_Progress_Report_GB |
| Category | Job_Progress_Report_GB | nvarchar | Category field in Job_Progress_Report_GB |
| Well ID | Job_Progress_Report_GB | nvarchar | Well Id field in Job_Progress_Report_GB |
| Well Name / Project Name | Job_Progress_Report_GB | nvarchar | Well Name / Project Name field in Job_Progress_Report_GB |
| PO No | Job_Progress_Report_GB | nvarchar | Po No field in Job_Progress_Report_GB |
| WBS No | Job_Progress_Report_GB | nvarchar | Wbs No field in Job_Progress_Report_GB |
| Cum-Prior Month Actual % | Job_Progress_Report_GB | decimal | Cum-Prior Month Actual % field in Job_Progress_Report_GB |
| Week-1 Plan % | Job_Progress_Report_GB | decimal | Week-1 Plan % field in Job_Progress_Report_GB |
| Week-1 Actual % | Job_Progress_Report_GB | decimal | Week-1 Actual % field in Job_Progress_Report_GB |
| Week-2 Plan % | Job_Progress_Report_GB | decimal | Week-2 Plan % field in Job_Progress_Report_GB |
| Week-2 Actual % | Job_Progress_Report_GB | decimal | Week-2 Actual % field in Job_Progress_Report_GB |
| Week-3 Plan % | Job_Progress_Report_GB | decimal | Week-3 Plan % field in Job_Progress_Report_GB |
| Week-3 Actual % | Job_Progress_Report_GB | decimal | Week-3 Actual % field in Job_Progress_Report_GB |
| Week-4 Plan % | Job_Progress_Report_GB | decimal | Week-4 Plan % field in Job_Progress_Report_GB |
| Week-4 Actual % | Job_Progress_Report_GB | decimal | Week-4 Actual % field in Job_Progress_Report_GB |
| Week-5 Plan % | Job_Progress_Report_GB | decimal | Week-5 Plan % field in Job_Progress_Report_GB |
| Week-5 Actual % | Job_Progress_Report_GB | decimal | Week-5 Actual % field in Job_Progress_Report_GB |
| Current Month Plan % | Job_Progress_Report_GB | decimal | Current Month Plan % field in Job_Progress_Report_GB |
| Current Month Actual % | Job_Progress_Report_GB | decimal | Current Month Actual % field in Job_Progress_Report_GB |
| Cum-Current Month Plan % | Job_Progress_Report_GB | decimal | Cum-Current Month Plan % field in Job_Progress_Report_GB |
| Cum-Current Month Actual % | Job_Progress_Report_GB | decimal | Cum-Current Month Actual % field in Job_Progress_Report_GB |
| Target End | Job_Progress_Report_GB | date | Target End field in Job_Progress_Report_GB |
| Purpose Value | Job_Progress_Report_GB | decimal | Purpose Value field in Job_Progress_Report_GB |
| Cum-Prior Month Plan | Job_Progress_Report_GB | decimal | Cum-Prior Month Plan field in Job_Progress_Report_GB |
| Cum-Prior Month Actual | Job_Progress_Report_GB | decimal | Cum-Prior Month Actual field in Job_Progress_Report_GB |
| Current month Plan | Job_Progress_Report_GB | decimal | Current Month Plan field in Job_Progress_Report_GB |
| Current Month Actual | Job_Progress_Report_GB | decimal | Current Month Actual field in Job_Progress_Report_GB |
| Cum - Current Month Plan | Job_Progress_Report_GB | decimal | Cum - Current Month Plan field in Job_Progress_Report_GB |
| Cum - Current Month Actual | Job_Progress_Report_GB | decimal | Cum - Current Month Actual field in Job_Progress_Report_GB |
| Remarks | Job_Progress_Report_GB | nvarchar | Remarks field in Job_Progress_Report_GB |
| S.No | PH_PRODUCTIVITY_WEEKLY_REPORT | bigint | S.No field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| Month | PH_PRODUCTIVITY_WEEKLY_REPORT | nvarchar | Month field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| Year | PH_PRODUCTIVITY_WEEKLY_REPORT | int | Year field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| MonthStart | PH_PRODUCTIVITY_WEEKLY_REPORT | date | Monthstart field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| PA Name | PH_PRODUCTIVITY_WEEKLY_REPORT | nvarchar | Pa Name field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| PH Emp ID | PH_PRODUCTIVITY_WEEKLY_REPORT | nvarchar | Ph Emp Id field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| PH Name | PH_PRODUCTIVITY_WEEKLY_REPORT | nvarchar | Ph Name field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| ATNM/Sub Contractor | PH_PRODUCTIVITY_WEEKLY_REPORT | varchar | Atnm/Sub Contractor field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| Category | PH_PRODUCTIVITY_WEEKLY_REPORT | nvarchar | Category field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| Crew Type | PH_PRODUCTIVITY_WEEKLY_REPORT | nvarchar | Crew Type field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| Crew Discipline | PH_PRODUCTIVITY_WEEKLY_REPORT | nvarchar | Crew Discipline field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| Crew Name | PH_PRODUCTIVITY_WEEKLY_REPORT | nvarchar | Crew Name field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| Average Productivity (%) | PH_PRODUCTIVITY_WEEKLY_REPORT | decimal | Average Productivity (%) field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| W1_PI (CMR) | PH_PRODUCTIVITY_WEEKLY_REPORT | varchar | W1 Pi (Cmr) field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| W1_PI (T-Wise) | PH_PRODUCTIVITY_WEEKLY_REPORT | varchar | W1 Pi (T-Wise) field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| W2_PI (CMR) | PH_PRODUCTIVITY_WEEKLY_REPORT | varchar | W2 Pi (Cmr) field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| W2_PI (T-Wise) | PH_PRODUCTIVITY_WEEKLY_REPORT | varchar | W2 Pi (T-Wise) field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| W3_PI (CMR) | PH_PRODUCTIVITY_WEEKLY_REPORT | varchar | W3 Pi (Cmr) field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| W3_PI (T-Wise) | PH_PRODUCTIVITY_WEEKLY_REPORT | varchar | W3 Pi (T-Wise) field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| W4_PI (CMR) | PH_PRODUCTIVITY_WEEKLY_REPORT | varchar | W4 Pi (Cmr) field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| W4_PI (T-Wise) | PH_PRODUCTIVITY_WEEKLY_REPORT | varchar | W4 Pi (T-Wise) field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| W5_PI (CMR) | PH_PRODUCTIVITY_WEEKLY_REPORT | varchar | W5 Pi (Cmr) field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| W5_PI (T-Wise) | PH_PRODUCTIVITY_WEEKLY_REPORT | varchar | W5 Pi (T-Wise) field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| Month PI (CMR) | PH_PRODUCTIVITY_WEEKLY_REPORT | varchar | Month Pi (Cmr) field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| Month PI (T-Wise) | PH_PRODUCTIVITY_WEEKLY_REPORT | varchar | Month Pi (T-Wise) field in PH_PRODUCTIVITY_WEEKLY_REPORT |
| Code | ProjectIDs | nvarchar | Code field in ProjectIDs |
| column2 | ProjectIDs | nvarchar | Column2 field in ProjectIDs |
| Number | ProjectIDs | tinyint | Number field in ProjectIDs |
| ID | ProjectIDs | nvarchar | Id field in ProjectIDs |
| id | Revenue | bigint | Id field in Revenue |
| rigcode | Revenue | nvarchar | Rigcode field in Revenue |
| well_id | Revenue | nvarchar | The unique well identifier |
| code | Revenue | nvarchar | Code field in Revenue |
| pms | Revenue | decimal | Pms field in Revenue |
| step_type | Revenue | nvarchar | Step Type field in Revenue |
| planned_progress | Revenue | nvarchar | Planned Progress field in Revenue |
| plan_percent | Revenue | nvarchar | Plan Percent field in Revenue |
| acutal_progress | Revenue | decimal | Acutal Progress field in Revenue |
| act_percent | Revenue | nvarchar | Act Percent field in Revenue |
| total_purpose_value | Revenue | decimal | Total Purpose Value field in Revenue |
| planned_purpose_value | Revenue | nvarchar | Planned Purpose Value field in Revenue |
| actual_purpose_value | Revenue | decimal | Actual Purpose Value field in Revenue |
| planned_progress_next_week | Revenue | nvarchar | Planned Progress Next Week field in Revenue |
| plan_percent_next_week | Revenue | nvarchar | Plan Percent Next Week field in Revenue |
| planned_purpose_value_next_week | Revenue | nvarchar | Planned Purpose Value Next Week field in Revenue |
| Title | Revenue | nvarchar | Title field in Revenue |
| created_at | Revenue | datetime2 | Timestamp when record was created |
| Work_Center | SAP_DRILLING_SEQUENCE | nvarchar | Work Center field in SAP_DRILLING_SEQUENCE |
| Operation_Short | SAP_DRILLING_SEQUENCE | nvarchar | Operation Short field in SAP_DRILLING_SEQUENCE |
| Activity | SAP_DRILLING_SEQUENCE | nvarchar | Activity field in SAP_DRILLING_SEQUENCE |
| Opr_System_status | SAP_DRILLING_SEQUENCE | nvarchar | Opr System Status field in SAP_DRILLING_SEQUENCE |
| Earl_start_date | SAP_DRILLING_SEQUENCE | date | Earl Start Date field in SAP_DRILLING_SEQUENCE |
| EarliestEndDate | SAP_DRILLING_SEQUENCE | date | Earliestenddate field in SAP_DRILLING_SEQUENCE |
| Station_Code | SAP_DRILLING_SEQUENCE | nvarchar | Station Code field in SAP_DRILLING_SEQUENCE |
| Normal_duration | SAP_DRILLING_SEQUENCE | float | Normal Duration field in SAP_DRILLING_SEQUENCE |
| Norm_duratn_un | SAP_DRILLING_SEQUENCE | nvarchar | Norm Duratn Un field in SAP_DRILLING_SEQUENCE |
| Well_Name | SAP_DRILLING_SEQUENCE | nvarchar | Well Name field in SAP_DRILLING_SEQUENCE |
| Field | SAP_DRILLING_SEQUENCE | nvarchar | Field field in SAP_DRILLING_SEQUENCE |
| Responsible_asset | SAP_DRILLING_SEQUENCE | nvarchar | Responsible Asset field in SAP_DRILLING_SEQUENCE |
| Well_ID | SAP_DRILLING_SEQUENCE | varchar | The unique well identifier |
| Well_Location | SAP_DRILLING_SEQUENCE | nvarchar | Well Location field in SAP_DRILLING_SEQUENCE |
| Well_Function | SAP_DRILLING_SEQUENCE | nvarchar | Well Function field in SAP_DRILLING_SEQUENCE |
| Well_Category | SAP_DRILLING_SEQUENCE | nvarchar | Well Category field in SAP_DRILLING_SEQUENCE |
| PCAP_Category | SAP_DRILLING_SEQUENCE | nvarchar | Pcap Category field in SAP_DRILLING_SEQUENCE |
| Move_days | SAP_DRILLING_SEQUENCE | tinyint | Move Days field in SAP_DRILLING_SEQUENCE |
| PDO_Well_Type | SAP_DRILLING_SEQUENCE | nvarchar | Pdo Well Type field in SAP_DRILLING_SEQUENCE |
| id | schema_knowledge_base | int | Id field in schema_knowledge_base |
| chunk_id | schema_knowledge_base | nvarchar | Chunk Id field in schema_knowledge_base |
| chunk_text | schema_knowledge_base | nvarchar | Chunk Text field in schema_knowledge_base |
| table_name | schema_knowledge_base | nvarchar | Table Name field in schema_knowledge_base |
| chunk_type | schema_knowledge_base | nvarchar | Chunk Type field in schema_knowledge_base |
| embedding | schema_knowledge_base | varbinary | Embedding field in schema_knowledge_base |
| created_at | schema_knowledge_base | datetime2 | Timestamp when record was created |
| id | task_daily | bigint | Id field in task_daily |
| ActionOn | task_daily | date | Actionon field in task_daily |
| task_code | task_daily | nvarchar | Task Code field in task_daily |
| schedule_id | task_daily | bigint | Schedule Id field in task_daily |
| project_id | task_daily | uniqueidentifier | The project identifier this record belongs to |
| required | task_daily | decimal | Required field in task_daily |
| planned | task_daily | decimal | Planned field in task_daily |
| duration | task_daily | decimal | Duration field in task_daily |
| remaining_duration | task_daily | decimal | Remaining Duration field in task_daily |
| progress | task_daily | decimal | Progress percentage or completion status |
| ready | task_daily | bit | Ready field in task_daily |
| completed | task_daily | bit | Completed field in task_daily |
| plan | task_daily | bit | Plan field in task_daily |
| committed_start | task_daily | date | Committed Start field in task_daily |
| committed_end | task_daily | date | Committed End field in task_daily |
| target_start | task_daily | date | Target Start field in task_daily |
| target_end | task_daily | date | Target End field in task_daily |
| actual_start | task_daily | date | Actual Start field in task_daily |
| actual_end | task_daily | date | Actual End field in task_daily |
| startDate | task_daily | date | Startdate field in task_daily |
| endDate | task_daily | date | Enddate field in task_daily |
| crew_type | task_daily | nvarchar | Crew Type field in task_daily |
| crew_code | task_daily | nvarchar | Crew Code field in task_daily |
| planned_crew | task_daily | nvarchar | Planned Crew field in task_daily |
| well_id | task_daily | nvarchar | The unique well identifier |
| task_uom | task_daily | nvarchar | Task Uom field in task_daily |
| data_hours | task_daily | decimal | Data Hours field in task_daily |
| data_qty | task_daily | decimal | Data Qty field in task_daily |
| data_employees | task_daily | nvarchar | Data Employees field in task_daily |
| task_assignee | task_daily | nvarchar | Task Assignee field in task_daily |
| supervisor_email | task_daily | nvarchar | Supervisor Email field in task_daily |
| url | task_daily | nvarchar | Url field in task_daily |
| task_data | task_daily | nvarchar | Task Data field in task_daily |
| daily_data | task_daily | nvarchar | Daily Data field in task_daily |
| created_at | task_daily | datetime2 | Timestamp when record was created |
| updated_at | task_daily | datetime2 | Timestamp when record was last updated |
| daily_ph_name | task_daily | nvarchar | Daily Ph Name field in task_daily |
| daily_equipment_ids | task_daily | nvarchar | Daily Equipment Ids field in task_daily |
| daily_employee_ids | task_daily | nvarchar | Daily Employee Ids field in task_daily |
| daily_actual_quantity | task_daily | decimal | Daily Actual Quantity field in task_daily |
| daily_actual_hours | task_daily | decimal | Daily Actual Hours field in task_daily |
| daily_completed | task_daily | bit | Daily Completed field in task_daily |
| time_stamp | task_daily | nvarchar | Time Stamp field in task_daily |
| Sr_No | WBS_Master_Tracker_ | nvarchar | Sr No field in WBS_Master_Tracker_ |
| WBS_Code | WBS_Master_Tracker_ | nvarchar | Wbs Code field in WBS_Master_Tracker_ |
| Project_Def | WBS_Master_Tracker_ | nvarchar | Project Def field in WBS_Master_Tracker_ |
| WD_PRJ | WBS_Master_Tracker_ | nvarchar | Wd Prj field in WBS_Master_Tracker_ |
| Plant_Code | WBS_Master_Tracker_ | nvarchar | Plant Code field in WBS_Master_Tracker_ |
| Plant_Name | WBS_Master_Tracker_ | nvarchar | Plant Name field in WBS_Master_Tracker_ |
| Cluster | WBS_Master_Tracker_ | nvarchar | The operational cluster/area the well belongs to |
| Well_ID_Project_PO | WBS_Master_Tracker_ | nvarchar | Well Id Project Po field in WBS_Master_Tracker_ |
| Activity_code | WBS_Master_Tracker_ | nvarchar | Activity Code field in WBS_Master_Tracker_ |
| Activity | WBS_Master_Tracker_ | nvarchar | Activity field in WBS_Master_Tracker_ |
| Category | WBS_Master_Tracker_ | nvarchar | Category field in WBS_Master_Tracker_ |
| Sr_No_2 | WBS_Master_Tracker_ | nvarchar | Sr No 2 field in WBS_Master_Tracker_ |
| LMPS | WBS_Master_Tracker_ | nvarchar | Lmps field in WBS_Master_Tracker_ |
| Duplicate_check | WBS_Master_Tracker_ | nvarchar | Duplicate Check field in WBS_Master_Tracker_ |
| Last_Updated_on | WBS_Master_Tracker_ | nvarchar | Last Updated On field in WBS_Master_Tracker_ |
| sl_no | WellMonitoringReport | bigint | Sl No field in WellMonitoringReport |
| sl_no_raw | WellMonitoringReport | nvarchar | Sl Number Raw field in WellMonitoringReport |
| rig_no | WellMonitoringReport | nvarchar | The identifier of the rig assigned to this well |
| well_location | WellMonitoringReport | nvarchar | Geographic location of the well |
| well_name_after_spud | WellMonitoringReport | nvarchar | The official name of the well after spudding |
| pdo_well_id | WellMonitoringReport | nvarchar | The unique PDO well identifier - use for counting unique wells |
| well_type | WellMonitoringReport | nvarchar | Type of well (ESP, PCP, Oil, Gas, etc.) |
| northing | WellMonitoringReport | nvarchar | Northing field in WellMonitoringReport |
| easting | WellMonitoringReport | nvarchar | Easting field in WellMonitoringReport |
| locationdd | WellMonitoringReport | nvarchar | Locationdd or location wbs field in WellMonitoringReport |
| flow_linedl | WellMonitoringReport | nvarchar | Flow Linedl or flowline wbs field in WellMonitoringReport |
| location_po_no | WellMonitoringReport | nvarchar | Location Po Number field in WellMonitoringReport |
| location_po_recvd_date | WellMonitoringReport | date | Location Po Received Date field in WellMonitoringReport |
| location_-_purpose_value | WellMonitoringReport | nvarchar | Location - Purpose Value field in WellMonitoringReport |
| last_week_exp.rig_on_location_sap_data | WellMonitoringReport | date | Last Week Exp.Rig On Location Sap Data field in WellMonitoringReport |
| latest_exp.rig_on_location_sap_data | WellMonitoringReport | date | Latest Expected Rig On Location Sap Data field in WellMonitoringReport |
| exp.rig_off_location_sap_data | WellMonitoringReport | date | Expected Rig Off Location Sap Data field in WellMonitoringReport |
| date_-_material_po_placed | WellMonitoringReport | date | Date - Material Po Placed field in WellMonitoringReport |
| date_-_material_available_at_site | WellMonitoringReport | date | Date - Material Available At Site field in WellMonitoringReport |
| scr_no | WellMonitoringReport | nvarchar | Sequence change request document number |
| scr_date | WellMonitoringReport | date | Scr or sequence change request Date field in WellMonitoringReport |
| moc_raised | WellMonitoringReport | nvarchar | Moc or management of change Raised field in WellMonitoringReport |
| moc_approved | WellMonitoringReport | nvarchar | Moc or management of change Approved field in WellMonitoringReport |
| buffer_status | WellMonitoringReport | varchar | Buffer Status field in WellMonitoringReport |
| actual_pegged_date | WellMonitoringReport | date | Actual Pegged Date field in WellMonitoringReport |
| last_week_cum_progress | WellMonitoringReport | decimal | Last Week Cum or Cummulative Progress field in WellMonitoringReport |
| cum_progress_for_this_week | WellMonitoringReport | decimal | Cum or cummulative Progress For This Week field in WellMonitoringReport |
| actual_start_date | WellMonitoringReport | date | Actual start date of the activity |
| actual_date_odc_requested_field_programmer_oso33x_for_esp_pcp_surface_cables | WellMonitoringReport | date | Actual Date Odc Requested Field Programmer Oso33X For Esp Pcp Surface Cables field in WellMonitoringReport |
| date_oso33x_call_out_for_cable_installation_to_pcp_esp_vendor | WellMonitoringReport | date | Date Oso33X Call Out For Cable Installation To Pcp Esp Vendor field in WellMonitoringReport |
| delivery_of_esp_pcp_surface_cable_by_field_programmer_oso33x | WellMonitoringReport | date | Delivery Of Esp Pcp Surface Cable By Field Programmer Oso33X field in WellMonitoringReport |
| installation_of_esp_pcp_surface_cable_by_vendors | WellMonitoringReport | date | Installation Of Esp Pcp Surface Cable By Vendors field in WellMonitoringReport |
| actual_finish_date | WellMonitoringReport | date | Actual finish/completion date |
| flaf_issue_date | WellMonitoringReport | date | Flaf Issue Date field in WellMonitoringReport |
| ramz_id | WellMonitoringReport | nvarchar | Ramz Id field in WellMonitoringReport |
| ramz_id_received_date_same_day_as_flaf_issue_date | WellMonitoringReport | date | Ramz Id Received Date Same Day As Flaf Issue Date field in WellMonitoringReport |
| date_of_site_survey_report_issuance | WellMonitoringReport | date | Date Of Site Survey Report Issuance field in WellMonitoringReport |
| well_engineer_to_add_location_name_in_edm | WellMonitoringReport | nvarchar | Well Engineer To Add Location Name In Edm field in WellMonitoringReport |
| pt_to_request_for_esp_preliminary_design_through_ald | WellMonitoringReport | nvarchar | Pt To Request For Esp Preliminary Design Through Ald field in WellMonitoringReport |
| actual_date_odc_requested_field_programmer_oso33x_to_install_esp_pcp_skid | WellMonitoringReport | date | Actual Date Odc Requested Field Programmer Oso33X To Install Esp Pcp Skid field in WellMonitoringReport |
| actual_date_field_programmer_oso33x_requested_esp_pcp_vendor_to_install_the_skid | WellMonitoringReport | date | Actual Date Field Programmer Oso33X Requested Esp Pcp Vendor To Install The Skid field in WellMonitoringReport |
| actual_date_pcp_esp_vendor_delivered_the_skid | WellMonitoringReport | date | Actual Date Pcp Esp Vendor Delivered The Skid field in WellMonitoringReport |
| actual_installation_date_by_vendor_of_esp/pcp_skid | WellMonitoringReport | date | Actual Installation Date By Vendor Of Esp/Pcp Skid field in WellMonitoringReport |
| flow_line_po_no | WellMonitoringReport | nvarchar | Flow Line Po No field in WellMonitoringReport |
| f_l_po_recd._date | WellMonitoringReport | date | F L Po Recd. Date field in WellMonitoringReport |
| flowline_-_purpose_value | WellMonitoringReport | nvarchar | Flowline - Purpose Value field in WellMonitoringReport |
| station_name_no | WellMonitoringReport | nvarchar | Station Name Number field in WellMonitoringReport |
| physical_tie_in_port_number | WellMonitoringReport | nvarchar | Physical Tie In Port Number field in WellMonitoringReport |
| date_of_tie_in_port_readiness | WellMonitoringReport | date | Date Of Tie In Port Readiness field in WellMonitoringReport |
| physical_tie_in_port_available_when_flaf_issued | WellMonitoringReport | nvarchar | Physical Tie In Port Available When Flaf Issued field in WellMonitoringReport |
| engineering_actual_start_date | WellMonitoringReport | date | Engineering Actual Start Date field in WellMonitoringReport |
| engineering_actual_finish_date | WellMonitoringReport | date | Engineering Actual Finish Date field in WellMonitoringReport |
| progress | WellMonitoringReport | decimal | Progress percentage or completion status in Engineering  |
| fl_dia | WellMonitoringReport | nvarchar | Fl Dia field in WellMonitoringReport |
| fl_length_meter | WellMonitoringReport | nvarchar | Fl Length Meter field in WellMonitoringReport |
| const._actual_start_date | WellMonitoringReport | date | Construction Actual Start Date or flowline construction actual start field in WellMonitoringReport |
| const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date | WellMonitoringReport | date | Construction Complete Date Including F L Final Hydro Test 1 Day Before Rig On Date field in WellMonitoringReport |
| flowline_construction_progress | WellMonitoringReport | decimal | Flowline Construction Progress field in WellMonitoringReport |
| ohl_length_meter | WellMonitoringReport | nvarchar | Ohl Length Meter field in WellMonitoringReport |
| ohl_progress | WellMonitoringReport | decimal | Ohl Progress field in WellMonitoringReport |
| ohl_completion_date | WellMonitoringReport | date | Ohl Completion Date field in WellMonitoringReport |
| z6_data_submitted_date | WellMonitoringReport | date | Z6 Data Submitted Date field in WellMonitoringReport |
| sap_notification_received_date_z6_2_days_before_eng._completion | WellMonitoringReport | date | Sap Notification Received Date Z6 2 Days Before Eng. Completion field in WellMonitoringReport |
| actual_rig_on_date | WellMonitoringReport | date | Date when rig was moved onto location |
| actual_rig_off_date | WellMonitoringReport | date | Date when rig moved off location |
| wlctf_acceptanceapproval_from_production | WellMonitoringReport | date | Wlctf Acceptanceapproval From Production field in WellMonitoringReport |
| actual_hoist_fbu_rsr_on_date | WellMonitoringReport | date | Actual Hoist Fbu Rsr On Date field in WellMonitoringReport |
| actual_hoist_fbu_rsr_off_date | WellMonitoringReport | date | Actual Hoist Fbu Rsr Off Date field in WellMonitoringReport |
| wellpad_handover-2_from_hoist_fbu_rsr_off_date | WellMonitoringReport | date | Wellpad Handover-2 From Hoist Fbu Rsr Off Date field in WellMonitoringReport |
| completion_type_rig_fbu_or_rsr_hoist | WellMonitoringReport | nvarchar | Completion Type Rig Fbu Or Rsr Hoist field in WellMonitoringReport |
| actual_eng._completion_date | WellMonitoringReport | date | Actual Engineering Completion Date field in WellMonitoringReport |
| actual_comm._start_date | WellMonitoringReport | date | Actual Commissioning Start Date field in WellMonitoringReport |
| actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date | WellMonitoringReport | date | Actual Comm. Finish Date With In 2 Days From Actual Engg. Completion Date field in WellMonitoringReport |
| engg_kpi_after_rig-off_days | WellMonitoringReport | int | Engineering KPI: days after rig-off before completion |
| data_error | WellMonitoringReport | varchar | Data Error field in WellMonitoringReport |
| reason_if_kpi_not_met | WellMonitoringReport | nvarchar | Reason If Kpi Not Met field in WellMonitoringReport |
| remark_status_area_of_attention_issues_ | WellMonitoringReport | nvarchar | Remark Status Area Of Attention Issues  field in WellMonitoringReport |
| rlmu_submitted_to_ho-date_with_in_7_days_from_actual_comm. | WellMonitoringReport | date | Rlmu Submitted To Ho-Date With In 7 Days From Actual Comm. field in WellMonitoringReport |
| flow_line_test_pack_completion_doc._submission_date_to_qs_dept. | WellMonitoringReport | date | Flow Line Test Pack Completion Doc. Submission Date To Qs Dept. field in WellMonitoringReport |
| flow_line_test_pack_completion_progress | WellMonitoringReport | decimal | Flow Line Test Pack Completion Progress field in WellMonitoringReport |
| over_all_progress_percentages | WellMonitoringReport | decimal | Overall project progress as decimal (0-1) |
| ssfd_wells | WellMonitoringReport | nvarchar | Ssfd Wells field in WellMonitoringReport |
| ipm | WellMonitoringReport | nvarchar | Ipm field in WellMonitoringReport |
| access_road_5 | WellMonitoringReport | decimal | Access Road 5 field in WellMonitoringReport |
| earth_work_60 | WellMonitoringReport | decimal | Earth Work 60 field in WellMonitoringReport |
| cellar_20 | WellMonitoringReport | decimal | Cellar 20 field in WellMonitoringReport |
| beam_pump_base_esp_pcp_foundation_5 | WellMonitoringReport | decimal | Beam Pump Base Esp Pcp Foundation 5 field in WellMonitoringReport |
| earthing_1 | WellMonitoringReport | decimal | Earthing 1 field in WellMonitoringReport |
| septic_tank_1 | WellMonitoringReport | decimal | Septic Tank 1 field in WellMonitoringReport |
| water_2 | WellMonitoringReport | decimal | Water 2 field in WellMonitoringReport |
| waste_water_2 | WellMonitoringReport | decimal | Waste Water 2 field in WellMonitoringReport |
| hdpe_liner_instalat_4 | WellMonitoringReport | decimal | Hdpe Liner Instalat 4 field in WellMonitoringReport |
| overall_loc._preparation_10_100 | WellMonitoringReport | decimal | Overall Location Preparation or construction progress 10 100 field in WellMonitoringReport |
| site_survey_5 | WellMonitoringReport | decimal | Site Survey 5 field in WellMonitoringReport |
| survey_report_issue_5 | WellMonitoringReport | decimal | Survey Report Issue 5 field in WellMonitoringReport |
| design_sta_5 | WellMonitoringReport | decimal | Design Sta 5 field in WellMonitoringReport |
| design_completed_issue_for_ta2_5_40 | WellMonitoringReport | decimal | Design Completed Issue For Ta2 5 40 field in WellMonitoringReport |
| approved_by_15 | WellMonitoringReport | decimal | Approved By 15 field in WellMonitoringReport |
| afc_3_30 | WellMonitoringReport | decimal | Afc 3 30 field in WellMonitoringReport |
| overall_engg._10_100 | WellMonitoringReport | decimal | Overall Engineering progress 10 100 field in WellMonitoringReport |
| piping_mech_50 | WellMonitoringReport | decimal | Piping Mech 50 field in WellMonitoringReport |
| elect_30 | WellMonitoringReport | decimal | Elect 30 field in WellMonitoringReport |
| instr_20 | WellMonitoringReport | decimal | Instr 20 field in WellMonitoringReport |
| overall_material_10_100 | WellMonitoringReport | decimal | Overall Material availability 10 100 field in WellMonitoringReport |
| cold_b_2 | WellMonitoringReport | decimal | Cold B 2 field in WellMonitoringReport |
| sleeper_pre_cast_ins_15 | WellMonitoringReport | decimal | Sleeper Pre Cast Ins 15 field in WellMonitoringReport |
| cs_pipe_welding_ndt_10_rt_for_op_100_for_60 | WellMonitoringReport | decimal | Cs Pipe Welding Ndt 10 Rt For Op 100 For 60 field in WellMonitoringReport |
| pe_fussion_pull_20 | WellMonitoringReport | decimal | Pe Fussion Pull 20 field in WellMonitoringReport |
| final_hydro_t_3 | WellMonitoringReport | decimal | Final Hydro T 3 field in WellMonitoringReport |
| overall_const._10_100 | WellMonitoringReport | decimal | Overall flowing Construction progress 10 100 field in WellMonitoringReport |
| pole_hole_drill_40 | WellMonitoringReport | decimal | Pole Hole Drill 40 field in WellMonitoringReport |
| pole_erect_40 | WellMonitoringReport | decimal | Pole Erect 40 field in WellMonitoringReport |
| conductor_string_18 | WellMonitoringReport | decimal | Conductor String 18 field in WellMonitoringReport |
| ohl_ti_2 | WellMonitoringReport | decimal | Ohl Ti 2 field in WellMonitoringReport |
| overall_ohl_progr_100 | WellMonitoringReport | decimal | Overall Ohl Progress 100 field in WellMonitoringReport |
| mechani_60 | WellMonitoringReport | decimal | Mechanical 60 field in WellMonitoringReport |
| electri_15 | WellMonitoringReport | decimal | Electrical 15 field in WellMonitoringReport |
| instrumentat_20 | WellMonitoringReport | decimal | Instrumentation 20 field in WellMonitoringReport |
| overall_comm_mi_5 | WellMonitoringReport | decimal | Overall Commissioning  5 field in WellMonitoringReport |
| overall_comm_progress_100 | WellMonitoringReport | decimal | Overall Commissioning Progress 100 field in WellMonitoringReport |
| location_preparation_status_in_progress_completed | WellMonitoringReport | nvarchar | Location Preparation Status In Progress Completed field in WellMonitoringReport |
| flow_line_const._status_in_progress_completed | WellMonitoringReport | nvarchar | Flow Line Construction Status In Progress Completed field in WellMonitoringReport |
| flow_line_commi._status_in_progress_completed | WellMonitoringReport | nvarchar | Flow Line Commissioning Status In Progress Completed field in WellMonitoringReport |
| well_year_white_space | WellMonitoringReport | nvarchar | Well Year White Space field in WellMonitoringReport |
| reasons_for_year_2018 | WellMonitoringReport | nvarchar | Reasons For Year 2018 field in WellMonitoringReport |
| column7 | WellMonitoringReport | nvarchar | Column7 field in WellMonitoringReport |
| digital_wmr_import_remarks | WellMonitoringReport | nvarchar | Digital Wmr Import Remarks field in WellMonitoringReport |
| project_id | WellMonitoringReport | nvarchar | The project identifier this record belongs to |
| Week_Number | WellMonitoringReport | date | Week Number field in WellMonitoringReport |
| Cluster | WellMonitoringReport | nvarchar | The operational cluster/area the well belongs to |

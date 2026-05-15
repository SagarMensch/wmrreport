# ATNM Knowledge Bank - Complete Business & Semantic Mapping

> Based on: Intelligence system _architecture.docx
> Production Database: ATNM_Dev (10.100.137.11)
> Generated: March 2026

---

## Quick Reference

### Key Query Patterns

| User Question | SQL Pattern |
|---------------|-------------|
| "wells with low progress" | `WHERE TRY_CAST(over_all_progress_percentages AS FLOAT) < 0.5` |
| "wells in Nimr" | `WHERE Cluster = 'Nimr'` |
| "count unique wells" | `COUNT(DISTINCT pdo_well_id)` |
| "rig utilization" | `GROUP BY rig_no` |
| "behind schedule" | `WHERE TRY_CAST(engg_kpi_after_rig-off_days AS INT) > 2` |
| "revenue by well" | `JOIN Revenue ON well_id = pdo_well_id` |

### Join Keys

| Table | Join Column | Joins To |
|-------|-------------|----------|
| WellMonitoringReport | pdo_well_id | Job_Progress_Report_GB.[Well ID] |
| WellMonitoringReport | pdo_well_id | Revenue.well_id |
| ActivityTaskPlan | Well_ID | task_daily.well_id |
| Employee | UId | PH_PRODUCTIVITY_WEEKLY_REPORT.PH_Emp_ID |
| WBS_Master_Tracker_ | Well_ID_Project_PO | WellMonitoringReport.pdo_well_id |

---

## Database Connection
```
Server: 10.100.137.11
Database: ATNM_Dev
User: atnm_chatbot (read-only)
Driver: ODBC Driver 18 for SQL Server
```

## All Tables in Production (17 total)

- **ActivityTaskPlan**: 100,000 rows
- **company_employees**: 5,549 rows
- **crews**: 5,758 rows
- **Employee**: 5,554 rows
- **Job_Progress_PlanSnapshot**: 439 rows
- **Job_Progress_Report_GB**: 439 rows
- **PH_PRODUCTIVITY_WEEKLY_REPORT**: 510 rows
- **ProjectIDs**: 19 rows
- **Revenue**: 21,566 rows
- **SAP_DRILLING_SEQUENCE**: 6,159 rows
- **schema_knowledge_base**: 0 rows
- **task_daily**: 35,394 rows
- **WBS_Master_Tracker_**: 81,846 rows
- **WellMonitoringReport**: 268 rows
- **WellMonitoringReport_Latest**: 169 rows
- **WellMonitoringReport_Staged**: 169 rows
- **WMR_Full**: 18,969 rows

---

## ActivityTaskPlan
**Rows:** 100,000

### Business Meaning
Every task planned and executed against each well - progress, manhours, crew assignments, quantities.

### Semantic Meaning
Master execution table with WBS hierarchy. Contains task details including code, text, progress, duration, crew assignments, dates.

### Columns
| Column | Type | Description |
|--------|------|-------------|
| row_id | bigint | Row Id |
| source_id | nvarchar | Source Id |
| Data | nvarchar | Data |
| ancestor | nvarchar | Ancestor |
| duration | nvarchar | Duration |
| progress | nvarchar | Progress |
| crew_uid | nvarchar | Crew Uid |
| crew_type | nvarchar | Crew Type |
| qty | nvarchar | Qty |
| manhours | nvarchar | Manhours |
| weightage | nvarchar | Weightage |
| parent | nvarchar | Parent |
| start_date | datetime2 | Date field |
| end_date | datetime2 | Date field |
| target_start | datetime2 | Target Start |
| target_end | datetime2 | Target End |
| actual_start | datetime2 | Actual Start |
| actual_end | datetime2 | Actual End |
| qtyactual | nvarchar | Qtyactual |
| qtyforacst | nvarchar | Qtyforacst |
| manhoursactual | nvarchar | Manhoursactual |
| manhourforacst | nvarchar | Manhourforacst |
| code | nvarchar | Code |
| text | nvarchar | Text |
| type | nvarchar | Type |
| schedule_id | nvarchar | Schedule Id |
| project_id | nvarchar | Project Id |
| task_assignee | nvarchar | Task Assignee |
| supervisor_email | nvarchar | Supervisor Email |
| attributes | nvarchar | Attributes |
| remaining_duration | nvarchar | Remaining Duration |
| Resume_Suspend | nvarchar | Resume Suspend |
| data_nonprod | nvarchar | Data Nonprod |
| created_at | datetime2 | Created At |
| updated_at | datetime2 | Date field |
| Well_ID | nvarchar | Well identifier (join key) |
| Parent_WBS | nvarchar | Parent Wbs |
| Time_Stamp | nvarchar | Time Stamp |

## Employee
**Rows:** 5,554

### Business Meaning
All Al Tasnim staff with supervisor hierarchy and location codes.

### Semantic Meaning
Master personnel directory. Links to PH_PRODUCTIVITY_WEEKLY_REPORT via UId=PH_Emp_ID. Contains organizational hierarchy.

### Columns
| Column | Type | Description |
|--------|------|-------------|
| id | int | Id |
| UId | nvarchar | Uid |
| Name | nvarchar | Name |
| Email | nvarchar | Email |
| Status | nvarchar | Status |
| Supervisor | int | Supervisor |
| Account | nvarchar | Account |
| EmployeeType | int | Employeetype |
| Company | nvarchar | Company |
| Manager | int | Manager |
| Location | nvarchar | Location |

## Job_Progress_PlanSnapshot
**Rows:** 439

### Business Meaning
Weekly plan fractions per well - W1 through W5 plus cumulative figures.

### Semantic Meaning
Planning snapshots showing planned progress fractions. Used to compare actual vs planned progress.

### Columns
| Column | Type | Description |
|--------|------|-------------|
| Well_ID | nvarchar | Well identifier (join key) |
| project_id | nvarchar | Project Id |
| Cum_Prior_Plan_frac | decimal | Cum Prior Plan Frac |
| W1_Plan_frac | decimal | W1 Plan Frac |
| W2_Plan_frac | decimal | W2 Plan Frac |
| W3_Plan_frac | decimal | W3 Plan Frac |
| W4_Plan_frac | decimal | W4 Plan Frac |
| W5_Plan_frac | decimal | W5 Plan Frac |
| CurrentMonthPlanFrac | decimal | Currentmonthplanfrac |
| CumCurrentMonthPlanFrac | decimal | Cumcurrentmonthplanfrac |
| Latest_Target_End | date | Latest Target End |
| CreatedOn | datetime | Createdon |

## Job_Progress_Report_GB
**Rows:** 439

### Business Meaning
Plan versus actual progress percentage and revenue figures by well, by week, for each month.

### Semantic Meaning
Weekly job progress tracking with plan vs actual. Columns include Week-1-5 Plan%, Week-1-5 Actual%, Purpose Value (revenue), Target End date. Well ID column name contains space: [Well ID].

### Columns
| Column | Type | Description |
|--------|------|-------------|
| Sl.No | bigint | Sl.No |
| Category | nvarchar | Category |
| Well ID | nvarchar | Well Id |
| Well Name / Project Name | nvarchar | Well Name / Project Name |
| PO No | nvarchar | Po No |
| WBS No | nvarchar | Wbs No |
| Cum-Prior Month Actual % | decimal | Cum-Prior Month Actual % |
| Week-1 Plan % | decimal | Week-1 Plan % |
| Week-1 Actual % | decimal | Week-1 Actual % |
| Week-2 Plan % | decimal | Week-2 Plan % |
| Week-2 Actual % | decimal | Week-2 Actual % |
| Week-3 Plan % | decimal | Week-3 Plan % |
| Week-3 Actual % | decimal | Week-3 Actual % |
| Week-4 Plan % | decimal | Week-4 Plan % |
| Week-4 Actual % | decimal | Week-4 Actual % |
| Week-5 Plan % | decimal | Week-5 Plan % |
| Week-5 Actual % | decimal | Week-5 Actual % |
| Current Month Plan % | decimal | Current Month Plan % |
| Current Month Actual % | decimal | Current Month Actual % |
| Cum-Current Month Plan % | decimal | Cum-Current Month Plan % |
| Cum-Current Month Actual % | decimal | Cum-Current Month Actual % |
| Target End | date | Target End |
| Purpose Value | decimal | Purpose Value |
| Cum-Prior Month Plan | decimal | Cum-Prior Month Plan |
| Cum-Prior Month Actual | decimal | Cum-Prior Month Actual |
| Current month Plan | decimal | Current Month Plan |
| Current Month Actual | decimal | Current Month Actual |
| Cum - Current Month Plan | decimal | Cum - Current Month Plan |
| Cum - Current Month Actual | decimal | Cum - Current Month Actual |
| Remarks | nvarchar | Remarks |

## PH_PRODUCTIVITY_WEEKLY_REPORT
**Rows:** 510

### Business Meaning
Weekly productivity index scores per crew supervisor (PH) across all categories.

### Semantic Meaning
Productivity tracking for Project Holders. Contains PI scores (CMR and T-Wise methods) by week and month. Links to Employee via PH_Emp_ID.

### Columns
| Column | Type | Description |
|--------|------|-------------|
| S.No | bigint | S.No |
| Month | nvarchar | Month |
| Year | int | Year |
| MonthStart | date | Monthstart |
| PA Name | nvarchar | Pa Name |
| PH Emp ID | nvarchar | Ph Emp Id |
| PH Name | nvarchar | Ph Name |
| ATNM/Sub Contractor | varchar | Atnm/Sub Contractor |
| Category | nvarchar | Category |
| Crew Type | nvarchar | Crew Type |
| Crew Discipline | nvarchar | Crew Discipline |
| Crew Name | nvarchar | Crew Name |
| Average Productivity (%) | decimal | Average Productivity (%) |
| W1_PI (CMR) | varchar | W1 Pi (Cmr) |
| W1_PI (T-Wise) | varchar | W1 Pi (T-Wise) |
| W2_PI (CMR) | varchar | W2 Pi (Cmr) |
| W2_PI (T-Wise) | varchar | W2 Pi (T-Wise) |
| W3_PI (CMR) | varchar | W3 Pi (Cmr) |
| W3_PI (T-Wise) | varchar | W3 Pi (T-Wise) |
| W4_PI (CMR) | varchar | W4 Pi (Cmr) |
| W4_PI (T-Wise) | varchar | W4 Pi (T-Wise) |
| W5_PI (CMR) | varchar | W5 Pi (Cmr) |
| W5_PI (T-Wise) | varchar | W5 Pi (T-Wise) |
| Month PI (CMR) | varchar | Month Pi (Cmr) |
| Month PI (T-Wise) | varchar | Month Pi (T-Wise) |

## ProjectIDs
**Rows:** 19

### Business Meaning
Master reference/lookup directory for project identifiers.

### Semantic Meaning
Small lookup table (19 rows) for project codes. Links to other tables via project_id.

### Columns
| Column | Type | Description |
|--------|------|-------------|
| Code | nvarchar | Code |
| column2 | nvarchar | Column2 |
| Number | tinyint | Number |
| ID | nvarchar | Id |

## Revenue
**Rows:** 21,566

### Business Meaning
Planned and actual revenue (Purpose Value in OMR) per activity code per well.

### Semantic Meaning
Financial tracking table. Revenue = Purpose Value earned proportionally to physical progress. Links to wells via well_id.

### Columns
| Column | Type | Description |
|--------|------|-------------|
| id | bigint | Id |
| rigcode | nvarchar | Rigcode |
| well_id | nvarchar | Well identifier (join key) |
| code | nvarchar | Code |
| pms | decimal | Pms |
| step_type | nvarchar | Step Type |
| planned_progress | nvarchar | Planned Progress |
| plan_percent | nvarchar | Plan Percent |
| acutal_progress | decimal | Acutal Progress |
| act_percent | nvarchar | Act Percent |
| total_purpose_value | decimal | Total Purpose Value |
| planned_purpose_value | nvarchar | Planned Purpose Value |
| actual_purpose_value | decimal | Actual Purpose Value |
| planned_progress_next_week | nvarchar | Planned Progress Next Week |
| plan_percent_next_week | nvarchar | Plan Percent Next Week |
| planned_purpose_value_next_week | nvarchar | Planned Purpose Value Next Week |
| Title | nvarchar | Title |
| created_at | datetime2 | Created At |

## SAP_DRILLING_SEQUENCE
**Rows:** 6,159

### Business Meaning
Rig assignments, activity sequences, and move days from SAP.

### Semantic Meaning
SAP master data for rig scheduling. Contains expected dates, well classifications, operational statuses. Used to cross-reference SAP schedule vs actual progress.

### Columns
| Column | Type | Description |
|--------|------|-------------|
| Work_Center | nvarchar | Work Center |
| Operation_Short | nvarchar | Operation Short |
| Activity | nvarchar | Activity |
| Opr_System_status | nvarchar | Opr System Status |
| Earl_start_date | date | Date field |
| EarliestEndDate | date | Date field |
| Station_Code | nvarchar | Station Code |
| Normal_duration | float | Normal Duration |
| Norm_duratn_un | nvarchar | Norm Duratn Un |
| Well_Name | nvarchar | Well Name |
| Field | nvarchar | Field |
| Responsible_asset | nvarchar | Responsible Asset |
| Well_ID | varchar | Well identifier (join key) |
| Well_Location | nvarchar | Well Location |
| Well_Function | nvarchar | Well Function |
| Well_Category | nvarchar | Well Category |
| PCAP_Category | nvarchar | Pcap Category |
| Move_days | tinyint | Move Days |
| PDO_Well_Type | nvarchar | Pdo Well Type |

## WBS_Master_Tracker_
**Rows:** 81,846

### Business Meaning
Work Breakdown Structure (WBS) codes mapping to wells, plants, clusters, and activities.

### Semantic Meaning
WBS code master with project definitions. Links specific WBS codes to wells via Well_ID_Project_PO.

### Columns
| Column | Type | Description |
|--------|------|-------------|
| Sr_No | nvarchar | Sr No |
| WBS_Code | nvarchar | Wbs Code |
| Project_Def | nvarchar | Project Def |
| WD_PRJ | nvarchar | Wd Prj |
| Plant_Code | nvarchar | Plant Code |
| Plant_Name | nvarchar | Plant Name |
| Cluster | nvarchar | Operational cluster (Nimr or Marmul) |
| Well_ID_Project_PO | nvarchar | Well Id Project Po |
| Activity_code | nvarchar | Activity Code |
| Activity | nvarchar | Activity |
| Category | nvarchar | Category |
| Sr_No_2 | nvarchar | Sr No 2 |
| LMPS | nvarchar | Lmps |
| Duplicate_check | nvarchar | Duplicate Check |
| Last_Updated_on | nvarchar | Date field |

## WellMonitoringReport
**Rows:** 268

### Business Meaning
Weekly progress snapshot per well - 128 columns covering all construction stages, dates, rig assignments, and progress percentages for Nimr and Marmul clusters.

### Semantic Meaning
Main well monitoring data with physical progress, schedule dates, and status for all operational wells. Key columns: pdo_well_id (unique well identifier), over_all_progress_percentages (0-1 decimal), Cluster (Nimr/Marmul), rig_no, well_name_after_spud.

### Columns
| Column | Type | Description |
|--------|------|-------------|
| sl_no | bigint | Sl No |
| sl_no_raw | nvarchar | Sl No Raw |
| rig_no | nvarchar | Rig identifier (e.g., SWER102) |
| well_location | nvarchar | Well Location |
| well_name_after_spud | nvarchar | Official well name after spudding |
| pdo_well_id | nvarchar | UNIQUE well identifier - use for counting distinct wells |
| well_type | nvarchar | Well Type |
| northing | nvarchar | Northing |
| easting | nvarchar | Easting |
| locationdd | nvarchar | Locationdd |
| flow_linedl | nvarchar | Flow Linedl |
| location_po_no | nvarchar | Location Po No |
| location_po_recvd_date | date | Date field |
| location_-_purpose_value | nvarchar | Location - Purpose Value |
| last_week_exp.rig_on_location_sap_data | date | Last Week Exp.Rig On Location Sap Data |
| latest_exp.rig_on_location_sap_data | date | Latest Exp.Rig On Location Sap Data |
| exp.rig_off_location_sap_data | date | Exp.Rig Off Location Sap Data |
| date_-_material_po_placed | date | Date field |
| date_-_material_available_at_site | date | Date field |
| scr_no | nvarchar | Scr No |
| scr_date | date | Date field |
| moc_raised | nvarchar | Moc Raised |
| moc_approved | nvarchar | Moc Approved |
| buffer_status | varchar | Buffer Status |
| actual_pegged_date | date | Date field |
| last_week_cum_progress | decimal | Last Week Cum Progress |
| cum_progress_for_this_week | decimal | Cum Progress For This Week |
| actual_start_date | date | Date field |
| actual_date_odc_requested_field_programmer_oso33x_for_esp_pcp_surface_cables | date | Date field |
| date_oso33x_call_out_for_cable_installation_to_pcp_esp_vendor | date | Date field |
| delivery_of_esp_pcp_surface_cable_by_field_programmer_oso33x | date | Delivery Of Esp Pcp Surface Cable By Field Programmer Oso33X |
| installation_of_esp_pcp_surface_cable_by_vendors | date | Installation Of Esp Pcp Surface Cable By Vendors |
| actual_finish_date | date | Date field |
| flaf_issue_date | date | Date field |
| ramz_id | nvarchar | Ramz Id |
| ramz_id_received_date_same_day_as_flaf_issue_date | date | Date field |
| date_of_site_survey_report_issuance | date | Date field |
| well_engineer_to_add_location_name_in_edm | nvarchar | Well Engineer To Add Location Name In Edm |
| pt_to_request_for_esp_preliminary_design_through_ald | nvarchar | Pt To Request For Esp Preliminary Design Through Ald |
| actual_date_odc_requested_field_programmer_oso33x_to_install_esp_pcp_skid | date | Date field |
| actual_date_field_programmer_oso33x_requested_esp_pcp_vendor_to_install_the_skid | date | Date field |
| actual_date_pcp_esp_vendor_delivered_the_skid | date | Date field |
| actual_installation_date_by_vendor_of_esp/pcp_skid | date | Date field |
| flow_line_po_no | nvarchar | Flow Line Po No |
| f_l_po_recd._date | date | Date field |
| flowline_-_purpose_value | nvarchar | Flowline - Purpose Value |
| station_name_no | nvarchar | Station Name No |
| physical_tie_in_port_number | nvarchar | Physical Tie In Port Number |
| date_of_tie_in_port_readiness | date | Date field |
| physical_tie_in_port_available_when_flaf_issued | nvarchar | Physical Tie In Port Available When Flaf Issued |
| engineering_actual_start_date | date | Date field |
| engineering_actual_finish_date | date | Date field |
| progress | decimal | Progress |
| fl_dia | nvarchar | Fl Dia |
| fl_length_meter | nvarchar | Fl Length Meter |
| const._actual_start_date | date | Date field |
| const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date | date | Date field |
| flowline_construction_progress | decimal | Flowline Construction Progress |
| ohl_length_meter | nvarchar | Ohl Length Meter |
| ohl_progress | decimal | Ohl Progress |
| ohl_completion_date | date | Date field |
| z6_data_submitted_date | date | Date field |
| sap_notification_received_date_z6_2_days_before_eng._completion | date | Date field |
| actual_rig_on_date | date | Date field |
| actual_rig_off_date | date | Date field |
| wlctf_acceptanceapproval_from_production | date | Wlctf Acceptanceapproval From Production |
| actual_hoist_fbu_rsr_on_date | date | Date field |
| actual_hoist_fbu_rsr_off_date | date | Date field |
| wellpad_handover-2_from_hoist_fbu_rsr_off_date | date | Date field |
| completion_type_rig_fbu_or_rsr_hoist | nvarchar | Completion Type Rig Fbu Or Rsr Hoist |
| actual_eng._completion_date | date | Date field |
| actual_comm._start_date | date | Date field |
| actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date | date | Date field |
| engg_kpi_after_rig-off_days | int | Engg Kpi After Rig-Off Days |
| data_error | varchar | Data Error |
| reason_if_kpi_not_met | nvarchar | Reason If Kpi Not Met |
| remark_status_area_of_attention_issues_ | nvarchar | Remark Status Area Of Attention Issues  |
| rlmu_submitted_to_ho-date_with_in_7_days_from_actual_comm. | date | Date field |
| flow_line_test_pack_completion_doc._submission_date_to_qs_dept. | date | Date field |
| flow_line_test_pack_completion_progress | decimal | Flow Line Test Pack Completion Progress |
| over_all_progress_percentages | decimal | Progress percentage (0-1 decimal, multiply by 100 for %) |
| ssfd_wells | nvarchar | Ssfd Wells |
| ipm | nvarchar | Ipm |
| access_road_5 | decimal | Access Road 5 |
| earth_work_60 | decimal | Earth Work 60 |
| cellar_20 | decimal | Cellar 20 |
| beam_pump_base_esp_pcp_foundation_5 | decimal | Beam Pump Base Esp Pcp Foundation 5 |
| earthing_1 | decimal | Earthing 1 |
| septic_tank_1 | decimal | Septic Tank 1 |
| water_2 | decimal | Water 2 |
| waste_water_2 | decimal | Waste Water 2 |
| hdpe_liner_instalat_4 | decimal | Hdpe Liner Instalat 4 |
| overall_loc._preparation_10_100 | decimal | Overall Loc. Preparation 10 100 |
| site_survey_5 | decimal | Site Survey 5 |
| survey_report_issue_5 | decimal | Survey Report Issue 5 |
| design_sta_5 | decimal | Design Sta 5 |
| design_completed_issue_for_ta2_5_40 | decimal | Design Completed Issue For Ta2 5 40 |
| approved_by_15 | decimal | Approved By 15 |
| afc_3_30 | decimal | Afc 3 30 |
| overall_engg._10_100 | decimal | Overall Engg. 10 100 |
| piping_mech_50 | decimal | Piping Mech 50 |
| elect_30 | decimal | Elect 30 |
| instr_20 | decimal | Instr 20 |
| overall_material_10_100 | decimal | Overall Material 10 100 |
| cold_b_2 | decimal | Cold B 2 |
| sleeper_pre_cast_ins_15 | decimal | Sleeper Pre Cast Ins 15 |
| cs_pipe_welding_ndt_10_rt_for_op_100_for_60 | decimal | Cs Pipe Welding Ndt 10 Rt For Op 100 For 60 |
| pe_fussion_pull_20 | decimal | Pe Fussion Pull 20 |
| final_hydro_t_3 | decimal | Final Hydro T 3 |
| overall_const._10_100 | decimal | Overall Const. 10 100 |
| pole_hole_drill_40 | decimal | Pole Hole Drill 40 |
| pole_erect_40 | decimal | Pole Erect 40 |
| conductor_string_18 | decimal | Conductor String 18 |
| ohl_ti_2 | decimal | Ohl Ti 2 |
| overall_ohl_progr_100 | decimal | Overall Ohl Progr 100 |
| mechani_60 | decimal | Mechani 60 |
| electri_15 | decimal | Electri 15 |
| instrumentat_20 | decimal | Instrumentat 20 |
| overall_comm_mi_5 | decimal | Overall Comm Mi 5 |
| overall_comm_progress_100 | decimal | Overall Comm Progress 100 |
| location_preparation_status_in_progress_completed | nvarchar | Location Preparation Status In Progress Completed |
| flow_line_const._status_in_progress_completed | nvarchar | Flow Line Const. Status In Progress Completed |
| flow_line_commi._status_in_progress_completed | nvarchar | Flow Line Commi. Status In Progress Completed |
| well_year_white_space | nvarchar | Well Year White Space |
| reasons_for_year_2018 | nvarchar | Reasons For Year 2018 |
| column7 | nvarchar | Column7 |
| digital_wmr_import_remarks | nvarchar | Digital Wmr Import Remarks |
| project_id | nvarchar | Project Id |
| Week_Number | date | Week Number |
| Cluster | nvarchar | Operational cluster (Nimr or Marmul) |

## WellMonitoringReport_Latest
**Rows:** 169

### Business Meaning
Most recent week only, used for faster queries when historical trend is not required.

### Semantic Meaning
Current week snapshot of well monitoring. Same structure as WellMonitoringReport but filtered to latest week. Use for real-time status queries.

### Columns
| Column | Type | Description |
|--------|------|-------------|
| sl_no | bigint | Sl No |
| sl_no_raw | nvarchar | Sl No Raw |
| rig_no | nvarchar | Rig identifier (e.g., SWER102) |
| well_location | nvarchar | Well Location |
| well_name_after_spud | nvarchar | Official well name after spudding |
| pdo_well_id | nvarchar | UNIQUE well identifier - use for counting distinct wells |
| well_type | nvarchar | Well Type |
| northing | nvarchar | Northing |
| easting | nvarchar | Easting |
| locationdd | nvarchar | Locationdd |
| flow_linedl | nvarchar | Flow Linedl |
| location_po_no | nvarchar | Location Po No |
| location_po_recvd_date | date | Date field |
| location_-_purpose_value | nvarchar | Location - Purpose Value |
| last_week_exp.rig_on_location_sap_data | date | Last Week Exp.Rig On Location Sap Data |
| latest_exp.rig_on_location_sap_data | date | Latest Exp.Rig On Location Sap Data |
| exp.rig_off_location_sap_data | date | Exp.Rig Off Location Sap Data |
| date_-_material_po_placed | date | Date field |
| date_-_material_available_at_site | date | Date field |
| scr_no | nvarchar | Scr No |
| scr_date | date | Date field |
| moc_raised | nvarchar | Moc Raised |
| moc_approved | nvarchar | Moc Approved |
| buffer_status | varchar | Buffer Status |
| actual_pegged_date | date | Date field |
| last_week_cum_progress | decimal | Last Week Cum Progress |
| cum_progress_for_this_week | decimal | Cum Progress For This Week |
| actual_start_date | date | Date field |
| actual_date_odc_requested_field_programmer_oso33x_for_esp_pcp_surface_cables | date | Date field |
| date_oso33x_call_out_for_cable_installation_to_pcp_esp_vendor | date | Date field |
| delivery_of_esp_pcp_surface_cable_by_field_programmer_oso33x | date | Delivery Of Esp Pcp Surface Cable By Field Programmer Oso33X |
| installation_of_esp_pcp_surface_cable_by_vendors | date | Installation Of Esp Pcp Surface Cable By Vendors |
| actual_finish_date | date | Date field |
| flaf_issue_date | date | Date field |
| ramz_id | nvarchar | Ramz Id |
| ramz_id_received_date_same_day_as_flaf_issue_date | date | Date field |
| date_of_site_survey_report_issuance | date | Date field |
| well_engineer_to_add_location_name_in_edm | nvarchar | Well Engineer To Add Location Name In Edm |
| pt_to_request_for_esp_preliminary_design_through_ald | nvarchar | Pt To Request For Esp Preliminary Design Through Ald |
| actual_date_odc_requested_field_programmer_oso33x_to_install_esp_pcp_skid | date | Date field |
| actual_date_field_programmer_oso33x_requested_esp_pcp_vendor_to_install_the_skid | date | Date field |
| actual_date_pcp_esp_vendor_delivered_the_skid | date | Date field |
| actual_installation_date_by_vendor_of_esp/pcp_skid | date | Date field |
| flow_line_po_no | nvarchar | Flow Line Po No |
| f_l_po_recd._date | date | Date field |
| flowline_-_purpose_value | nvarchar | Flowline - Purpose Value |
| station_name_no | nvarchar | Station Name No |
| physical_tie_in_port_number | nvarchar | Physical Tie In Port Number |
| date_of_tie_in_port_readiness | date | Date field |
| physical_tie_in_port_available_when_flaf_issued | nvarchar | Physical Tie In Port Available When Flaf Issued |
| engineering_actual_start_date | date | Date field |
| engineering_actual_finish_date | date | Date field |
| progress | decimal | Progress |
| fl_dia | nvarchar | Fl Dia |
| fl_length_meter | nvarchar | Fl Length Meter |
| const._actual_start_date | date | Date field |
| const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date | date | Date field |
| flowline_construction_progress | decimal | Flowline Construction Progress |
| ohl_length_meter | nvarchar | Ohl Length Meter |
| ohl_progress | decimal | Ohl Progress |
| ohl_completion_date | date | Date field |
| z6_data_submitted_date | date | Date field |
| sap_notification_received_date_z6_2_days_before_eng._completion | date | Date field |
| actual_rig_on_date | date | Date field |
| actual_rig_off_date | date | Date field |
| wlctf_acceptanceapproval_from_production | date | Wlctf Acceptanceapproval From Production |
| actual_hoist_fbu_rsr_on_date | date | Date field |
| actual_hoist_fbu_rsr_off_date | date | Date field |
| wellpad_handover-2_from_hoist_fbu_rsr_off_date | date | Date field |
| completion_type_rig_fbu_or_rsr_hoist | nvarchar | Completion Type Rig Fbu Or Rsr Hoist |
| actual_eng._completion_date | date | Date field |
| actual_comm._start_date | date | Date field |
| actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date | date | Date field |
| engg_kpi_after_rig-off_days | int | Engg Kpi After Rig-Off Days |
| data_error | varchar | Data Error |
| reason_if_kpi_not_met | nvarchar | Reason If Kpi Not Met |
| remark_status_area_of_attention_issues_ | nvarchar | Remark Status Area Of Attention Issues  |
| rlmu_submitted_to_ho-date_with_in_7_days_from_actual_comm. | date | Date field |
| flow_line_test_pack_completion_doc._submission_date_to_qs_dept. | date | Date field |
| flow_line_test_pack_completion_progress | decimal | Flow Line Test Pack Completion Progress |
| over_all_progress_percentages | decimal | Progress percentage (0-1 decimal, multiply by 100 for %) |
| ssfd_wells | nvarchar | Ssfd Wells |
| ipm | nvarchar | Ipm |
| access_road_5 | decimal | Access Road 5 |
| earth_work_60 | decimal | Earth Work 60 |
| cellar_20 | decimal | Cellar 20 |
| beam_pump_base_esp_pcp_foundation_5 | decimal | Beam Pump Base Esp Pcp Foundation 5 |
| earthing_1 | decimal | Earthing 1 |
| septic_tank_1 | decimal | Septic Tank 1 |
| water_2 | decimal | Water 2 |
| waste_water_2 | decimal | Waste Water 2 |
| hdpe_liner_instalat_4 | decimal | Hdpe Liner Instalat 4 |
| overall_loc._preparation_10_100 | decimal | Overall Loc. Preparation 10 100 |
| site_survey_5 | decimal | Site Survey 5 |
| survey_report_issue_5 | decimal | Survey Report Issue 5 |
| design_sta_5 | decimal | Design Sta 5 |
| design_completed_issue_for_ta2_5_40 | decimal | Design Completed Issue For Ta2 5 40 |
| approved_by_15 | decimal | Approved By 15 |
| afc_3_30 | decimal | Afc 3 30 |
| overall_engg._10_100 | decimal | Overall Engg. 10 100 |
| piping_mech_50 | decimal | Piping Mech 50 |
| elect_30 | decimal | Elect 30 |
| instr_20 | decimal | Instr 20 |
| overall_material_10_100 | decimal | Overall Material 10 100 |
| cold_b_2 | decimal | Cold B 2 |
| sleeper_pre_cast_ins_15 | decimal | Sleeper Pre Cast Ins 15 |
| cs_pipe_welding_ndt_10_rt_for_op_100_for_60 | decimal | Cs Pipe Welding Ndt 10 Rt For Op 100 For 60 |
| pe_fussion_pull_20 | decimal | Pe Fussion Pull 20 |
| final_hydro_t_3 | decimal | Final Hydro T 3 |
| overall_const._10_100 | decimal | Overall Const. 10 100 |
| pole_hole_drill_40 | decimal | Pole Hole Drill 40 |
| pole_erect_40 | decimal | Pole Erect 40 |
| conductor_string_18 | decimal | Conductor String 18 |
| ohl_ti_2 | decimal | Ohl Ti 2 |
| overall_ohl_progr_100 | decimal | Overall Ohl Progr 100 |
| mechani_60 | decimal | Mechani 60 |
| electri_15 | decimal | Electri 15 |
| instrumentat_20 | decimal | Instrumentat 20 |
| overall_comm_mi_5 | decimal | Overall Comm Mi 5 |
| overall_comm_progress_100 | decimal | Overall Comm Progress 100 |
| location_preparation_status_in_progress_completed | nvarchar | Location Preparation Status In Progress Completed |
| flow_line_const._status_in_progress_completed | nvarchar | Flow Line Const. Status In Progress Completed |
| flow_line_commi._status_in_progress_completed | nvarchar | Flow Line Commi. Status In Progress Completed |
| well_year_white_space | nvarchar | Well Year White Space |
| reasons_for_year_2018 | nvarchar | Reasons For Year 2018 |
| column7 | nvarchar | Column7 |
| digital_wmr_import_remarks | nvarchar | Digital Wmr Import Remarks |
| project_id | nvarchar | Project Id |
| Week_Number | date | Week Number |
| Cluster | nvarchar | Operational cluster (Nimr or Marmul) |

## crews
**Rows:** 5,758

### Business Meaning
Crew compositions including supervisor, employees, and equipment.

### Semantic Meaning
Crew assignment and composition data.

### Columns
| Column | Type | Description |
|--------|------|-------------|
| ID | nvarchar | Id |
| Code | nvarchar | Code |
| Account | nvarchar | Account |
| Location | nvarchar | Location |
| CrewType | nvarchar | Crewtype |
| Supervisor | nvarchar | Supervisor |
| Employees | nvarchar | Employees |
| Equipments | nvarchar | Equipments |

## task_daily
**Rows:** 35,394

### Business Meaning
Daily execution records - actual start, end, crew, quantity, progress per task.

### Semantic Meaning
Daily task execution tracking with granular data. Links to ActivityTaskPlan via schedule_id. Contains actual hours, quantities, employee IDs.

### Columns
| Column | Type | Description |
|--------|------|-------------|
| id | bigint | Id |
| ActionOn | date | Actionon |
| task_code | nvarchar | Task Code |
| schedule_id | bigint | Schedule Id |
| project_id | uniqueidentifier | Project Id |
| required | decimal | Required |
| planned | decimal | Planned |
| duration | decimal | Duration |
| remaining_duration | decimal | Remaining Duration |
| progress | decimal | Progress |
| ready | bit | Ready |
| completed | bit | Completed |
| plan | bit | Plan |
| committed_start | date | Committed Start |
| committed_end | date | Committed End |
| target_start | date | Target Start |
| target_end | date | Target End |
| actual_start | date | Actual Start |
| actual_end | date | Actual End |
| startDate | date | Date field |
| endDate | date | Date field |
| crew_type | nvarchar | Crew Type |
| crew_code | nvarchar | Crew Code |
| planned_crew | nvarchar | Planned Crew |
| well_id | nvarchar | Well identifier (join key) |
| task_uom | nvarchar | Task Uom |
| data_hours | decimal | Data Hours |
| data_qty | decimal | Data Qty |
| data_employees | nvarchar | Data Employees |
| task_assignee | nvarchar | Task Assignee |
| supervisor_email | nvarchar | Supervisor Email |
| url | nvarchar | Url |
| task_data | nvarchar | Task Data |
| daily_data | nvarchar | Daily Data |
| created_at | datetime2 | Created At |
| updated_at | datetime2 | Date field |
| daily_ph_name | nvarchar | Daily Ph Name |
| daily_equipment_ids | nvarchar | Daily Equipment Ids |
| daily_employee_ids | nvarchar | Daily Employee Ids |
| daily_actual_quantity | decimal | Daily Actual Quantity |
| daily_actual_hours | decimal | Daily Actual Hours |
| daily_completed | bit | Daily Completed |
| time_stamp | nvarchar | Time Stamp |

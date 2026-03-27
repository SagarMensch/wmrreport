✓ Connected to SQL Server

# Full Schema Dump: ATNM_Dev Database

## 1. All Tables & Views

| # | Schema | Name | Type |
|:--|:-------|:-----|:-----|
| 1 | dbo | ActivityTaskPlan | BASE TABLE |
| 2 | dbo | company_employees | BASE TABLE |
| 3 | dbo | crews | BASE TABLE |
| 4 | dbo | Employee | BASE TABLE |
| 5 | dbo | Job_Progress_PlanSnapshot | BASE TABLE |
| 6 | dbo | Job_Progress_Report_GB | BASE TABLE |
| 7 | dbo | PH_PRODUCTIVITY_WEEKLY_REPORT | BASE TABLE |
| 8 | dbo | ProjectIDs | BASE TABLE |
| 9 | dbo | Revenue | BASE TABLE |
| 10 | dbo | SAP_DRILLING_SEQUENCE | BASE TABLE |
| 11 | dbo | schema_knowledge_base | BASE TABLE |
| 12 | dbo | task_daily | BASE TABLE |
| 13 | dbo | WBS_Master_Tracker_ | BASE TABLE |
| 14 | dbo | WellMonitoringReport | BASE TABLE |
| 15 | dbo | WellMonitoringReport_Latest | BASE TABLE |
| 16 | dbo | WellMonitoringReport_Staged | BASE TABLE |
| 17 | dbo | WMR_Full | BASE TABLE |

**Total: 17 objects**

## 2. Column Details Per Table/View


### `dbo.ActivityTaskPlan` (38 columns)

| # | Column | Type | MaxLen | Nullable |
|:--|:-------|:-----|:-------|:---------|
| 1 | row_id | bigint | - | NO |
| 2 | source_id | nvarchar | 100 | YES |
| 3 | Data | nvarchar | -1 | YES |
| 4 | ancestor | nvarchar | 255 | YES |
| 5 | duration | nvarchar | 100 | YES |
| 6 | progress | nvarchar | 100 | YES |
| 7 | crew_uid | nvarchar | 255 | YES |
| 8 | crew_type | nvarchar | 50 | YES |
| 9 | qty | nvarchar | 100 | YES |
| 10 | manhours | nvarchar | 100 | YES |
| 11 | weightage | nvarchar | 100 | YES |
| 12 | parent | nvarchar | 100 | YES |
| 13 | start_date | datetime2 | - | YES |
| 14 | end_date | datetime2 | - | YES |
| 15 | target_start | datetime2 | - | YES |
| 16 | target_end | datetime2 | - | YES |
| 17 | actual_start | datetime2 | - | YES |
| 18 | actual_end | datetime2 | - | YES |
| 19 | qtyactual | nvarchar | 100 | YES |
| 20 | qtyforacst | nvarchar | 100 | YES |
| 21 | manhoursactual | nvarchar | 100 | YES |
| 22 | manhourforacst | nvarchar | 100 | YES |
| 23 | code | nvarchar | 200 | YES |
| 24 | text | nvarchar | -1 | YES |
| 25 | type | nvarchar | 100 | YES |
| 26 | schedule_id | nvarchar | 100 | YES |
| 27 | project_id | nvarchar | 100 | YES |
| 28 | task_assignee | nvarchar | 255 | YES |
| 29 | supervisor_email | nvarchar | 255 | YES |
| 30 | attributes | nvarchar | -1 | YES |
| 31 | remaining_duration | nvarchar | 100 | YES |
| 32 | Resume_Suspend | nvarchar | 255 | YES |
| 33 | data_nonprod | nvarchar | -1 | YES |
| 34 | created_at | datetime2 | - | YES |
| 35 | updated_at | datetime2 | - | YES |
| 36 | Well_ID | nvarchar | 50 | YES |
| 37 | Parent_WBS | nvarchar | 255 | YES |
| 38 | Time_Stamp | nvarchar | 255 | YES |

### `dbo.Employee` (11 columns)

| # | Column | Type | MaxLen | Nullable |
|:--|:-------|:-----|:-------|:---------|
| 1 | id | int | - | NO |
| 2 | UId | nvarchar | 100 | YES |
| 3 | Name | nvarchar | 255 | YES |
| 4 | Email | nvarchar | 255 | YES |
| 5 | Status | nvarchar | 50 | YES |
| 6 | Supervisor | int | - | YES |
| 7 | Account | nvarchar | 255 | YES |
| 8 | EmployeeType | int | - | YES |
| 9 | Company | nvarchar | 255 | YES |
| 10 | Manager | int | - | YES |
| 11 | Location | nvarchar | 255 | YES |

### `dbo.Job_Progress_PlanSnapshot` (12 columns)

| # | Column | Type | MaxLen | Nullable |
|:--|:-------|:-----|:-------|:---------|
| 1 | Well_ID | nvarchar | 50 | YES |
| 2 | project_id | nvarchar | 50 | YES |
| 3 | Cum_Prior_Plan_frac | decimal | - | YES |
| 4 | W1_Plan_frac | decimal | - | YES |
| 5 | W2_Plan_frac | decimal | - | YES |
| 6 | W3_Plan_frac | decimal | - | YES |
| 7 | W4_Plan_frac | decimal | - | YES |
| 8 | W5_Plan_frac | decimal | - | YES |
| 9 | CurrentMonthPlanFrac | decimal | - | YES |
| 10 | CumCurrentMonthPlanFrac | decimal | - | YES |
| 11 | Latest_Target_End | date | - | YES |
| 12 | CreatedOn | datetime | - | NO |

### `dbo.Job_Progress_Report_GB` (30 columns)

| # | Column | Type | MaxLen | Nullable |
|:--|:-------|:-----|:-------|:---------|
| 1 | Sl.No | bigint | - | YES |
| 2 | Category | nvarchar | 50 | YES |
| 3 | Well ID | nvarchar | 50 | YES |
| 4 | Well Name / Project Name | nvarchar | 255 | YES |
| 5 | PO No | nvarchar | 255 | YES |
| 6 | WBS No | nvarchar | 50 | YES |
| 7 | Cum-Prior Month Actual % | decimal | - | YES |
| 8 | Week-1 Plan % | decimal | - | YES |
| 9 | Week-1 Actual % | decimal | - | YES |
| 10 | Week-2 Plan % | decimal | - | YES |
| 11 | Week-2 Actual % | decimal | - | YES |
| 12 | Week-3 Plan % | decimal | - | YES |
| 13 | Week-3 Actual % | decimal | - | YES |
| 14 | Week-4 Plan % | decimal | - | YES |
| 15 | Week-4 Actual % | decimal | - | YES |
| 16 | Week-5 Plan % | decimal | - | YES |
| 17 | Week-5 Actual % | decimal | - | YES |
| 18 | Current Month Plan % | decimal | - | YES |
| 19 | Current Month Actual % | decimal | - | YES |
| 20 | Cum-Current Month Plan % | decimal | - | YES |
| 21 | Cum-Current Month Actual % | decimal | - | YES |
| 22 | Target End | date | - | YES |
| 23 | Purpose Value | decimal | - | YES |
| 24 | Cum-Prior Month Plan | decimal | - | YES |
| 25 | Cum-Prior Month Actual | decimal | - | YES |
| 26 | Current month Plan | decimal | - | YES |
| 27 | Current Month Actual | decimal | - | YES |
| 28 | Cum - Current Month Plan | decimal | - | YES |
| 29 | Cum - Current Month Actual | decimal | - | YES |
| 30 | Remarks | nvarchar | 200 | YES |

### `dbo.PH_PRODUCTIVITY_WEEKLY_REPORT` (25 columns)

| # | Column | Type | MaxLen | Nullable |
|:--|:-------|:-----|:-------|:---------|
| 1 | S.No | bigint | - | YES |
| 2 | Month | nvarchar | 30 | YES |
| 3 | Year | int | - | YES |
| 4 | MonthStart | date | - | YES |
| 5 | PA Name | nvarchar | 4000 | NO |
| 6 | PH Emp ID | nvarchar | 50 | NO |
| 7 | PH Name | nvarchar | 255 | NO |
| 8 | ATNM/Sub Contractor | varchar | 14 | NO |
| 9 | Category | nvarchar | 4000 | NO |
| 10 | Crew Type | nvarchar | 4000 | NO |
| 11 | Crew Discipline | nvarchar | 4000 | NO |
| 12 | Crew Name | nvarchar | 4000 | NO |
| 13 | Average Productivity (%) | decimal | - | YES |
| 14 | W1_PI (CMR) | varchar | 2 | YES |
| 15 | W1_PI (T-Wise) | varchar | 2 | YES |
| 16 | W2_PI (CMR) | varchar | 2 | YES |
| 17 | W2_PI (T-Wise) | varchar | 2 | YES |
| 18 | W3_PI (CMR) | varchar | 2 | YES |
| 19 | W3_PI (T-Wise) | varchar | 2 | YES |
| 20 | W4_PI (CMR) | varchar | 2 | YES |
| 21 | W4_PI (T-Wise) | varchar | 2 | YES |
| 22 | W5_PI (CMR) | varchar | 2 | YES |
| 23 | W5_PI (T-Wise) | varchar | 2 | YES |
| 24 | Month PI (CMR) | varchar | 2 | NO |
| 25 | Month PI (T-Wise) | varchar | 2 | NO |

### `dbo.ProjectIDs` (4 columns)

| # | Column | Type | MaxLen | Nullable |
|:--|:-------|:-----|:-------|:---------|
| 1 | Code | nvarchar | 50 | YES |
| 2 | column2 | nvarchar | 50 | YES |
| 3 | Number | tinyint | - | YES |
| 4 | ID | nvarchar | 50 | YES |

### `dbo.Revenue` (18 columns)

| # | Column | Type | MaxLen | Nullable |
|:--|:-------|:-----|:-------|:---------|
| 1 | id | bigint | - | NO |
| 2 | rigcode | nvarchar | 50 | YES |
| 3 | well_id | nvarchar | 50 | YES |
| 4 | code | nvarchar | 100 | YES |
| 5 | pms | decimal | - | YES |
| 6 | step_type | nvarchar | 100 | YES |
| 7 | planned_progress | nvarchar | 255 | YES |
| 8 | plan_percent | nvarchar | 50 | YES |
| 9 | acutal_progress | decimal | - | YES |
| 10 | act_percent | nvarchar | 50 | YES |
| 11 | total_purpose_value | decimal | - | YES |
| 12 | planned_purpose_value | nvarchar | 50 | YES |
| 13 | actual_purpose_value | decimal | - | YES |
| 14 | planned_progress_next_week | nvarchar | 255 | YES |
| 15 | plan_percent_next_week | nvarchar | 50 | YES |
| 16 | planned_purpose_value_next_week | nvarchar | 50 | YES |
| 17 | Title | nvarchar | 255 | YES |
| 18 | created_at | datetime2 | - | YES |

### `dbo.SAP_DRILLING_SEQUENCE` (19 columns)

| # | Column | Type | MaxLen | Nullable |
|:--|:-------|:-----|:-------|:---------|
| 1 | Work_Center | nvarchar | 50 | YES |
| 2 | Operation_Short | nvarchar | 50 | YES |
| 3 | Activity | nvarchar | 50 | YES |
| 4 | Opr_System_status | nvarchar | 50 | YES |
| 5 | Earl_start_date | date | - | YES |
| 6 | EarliestEndDate | date | - | YES |
| 7 | Station_Code | nvarchar | 50 | YES |
| 8 | Normal_duration | float | - | YES |
| 9 | Norm_duratn_un | nvarchar | 50 | YES |
| 10 | Well_Name | nvarchar | 50 | YES |
| 11 | Field | nvarchar | 50 | YES |
| 12 | Responsible_asset | nvarchar | 50 | YES |
| 13 | Well_ID | varchar | 50 | NO |
| 14 | Well_Location | nvarchar | 50 | YES |
| 15 | Well_Function | nvarchar | 50 | YES |
| 16 | Well_Category | nvarchar | 50 | YES |
| 17 | PCAP_Category | nvarchar | 50 | YES |
| 18 | Move_days | tinyint | - | YES |
| 19 | PDO_Well_Type | nvarchar | 50 | YES |

### `dbo.WBS_Master_Tracker_` (15 columns)

| # | Column | Type | MaxLen | Nullable |
|:--|:-------|:-----|:-------|:---------|
| 1 | Sr_No | nvarchar | 50 | YES |
| 2 | WBS_Code | nvarchar | 50 | YES |
| 3 | Project_Def | nvarchar | 50 | YES |
| 4 | WD_PRJ | nvarchar | 50 | YES |
| 5 | Plant_Code | nvarchar | 50 | YES |
| 6 | Plant_Name | nvarchar | 50 | YES |
| 7 | Cluster | nvarchar | 50 | YES |
| 8 | Well_ID_Project_PO | nvarchar | 50 | YES |
| 9 | Activity_code | nvarchar | 50 | YES |
| 10 | Activity | nvarchar | 50 | YES |
| 11 | Category | nvarchar | 50 | YES |
| 12 | Sr_No_2 | nvarchar | 50 | YES |
| 13 | LMPS | nvarchar | 50 | YES |
| 14 | Duplicate_check | nvarchar | 50 | YES |
| 15 | Last_Updated_on | nvarchar | 50 | YES |

### `dbo.WMR_Full` (128 columns)

| # | Column | Type | MaxLen | Nullable |
|:--|:-------|:-----|:-------|:---------|
| 1 | sl_no | nvarchar | 255 | YES |
| 2 | rig_no | nvarchar | 255 | NO |
| 3 | well_location | nvarchar | 255 | YES |
| 4 | well_name_after_spud | nvarchar | 255 | YES |
| 5 | pdo_well_id | nvarchar | 255 | YES |
| 6 | well_type | nvarchar | 255 | YES |
| 7 | northing | nvarchar | 255 | YES |
| 8 | easting | nvarchar | 255 | YES |
| 9 | locationdd | nvarchar | 255 | YES |
| 10 | flow_linedl | nvarchar | 255 | YES |
| 11 | location_po_no | nvarchar | 255 | YES |
| 12 | location_po_recvd_date | nvarchar | 255 | YES |
| 13 | location_-_purpose_value | nvarchar | 255 | YES |
| 14 | last_week_exp.rig_on_location_sap_data | nvarchar | 255 | YES |
| 15 | latest_exp.rig_on_location_sap_data | nvarchar | 255 | YES |
| 16 | exp.rig_off_location_sap_data | nvarchar | 255 | YES |
| 17 | date_-_material_po_placed | nvarchar | 255 | YES |
| 18 | date_-_material_available_at_site | nvarchar | 255 | YES |
| 19 | scr_no | nvarchar | 255 | YES |
| 20 | scr_date | nvarchar | 255 | YES |
| 21 | moc_raised | nvarchar | 255 | YES |
| 22 | moc_approved | nvarchar | 255 | YES |
| 23 | buffer_status | nvarchar | 255 | YES |
| 24 | actual_pegged_date | nvarchar | 255 | YES |
| 25 | last_week_cum_progress | nvarchar | 255 | YES |
| 26 | cum_progress_for_this_week | nvarchar | 255 | YES |
| 27 | actual_start_date | nvarchar | 255 | YES |
| 28 | actual_date_odc_requested_field_programmer_oso33x_for_esp_pcp_surface_cables | nvarchar | 255 | YES |
| 29 | date_oso33x_call_out_for_cable_installation_to_pcp_esp_vendor | nvarchar | 255 | YES |
| 30 | delivery_of_esp_pcp_surface_cable_by_field_programmer_oso33x | nvarchar | 255 | YES |
| 31 | installation_of_esp_pcp_surface_cable_by_vendors | nvarchar | 255 | YES |
| 32 | actual_finish_date | nvarchar | 255 | YES |
| 33 | flaf_issue_date | nvarchar | 255 | YES |
| 34 | ramz_id | nvarchar | 255 | YES |
| 35 | ramz_id_received_date_same_day_as_flaf_issue_date | nvarchar | 255 | YES |
| 36 | date_of_site_survey_report_issuance | nvarchar | 255 | YES |
| 37 | well_engineer_to_add_location_name_in_edm | nvarchar | 255 | YES |
| 38 | pt_to_request_for_esp_preliminary_design_through_ald | nvarchar | 255 | YES |
| 39 | actual_date_odc_requested_field_programmer_oso33x_to_install_esp_pcp_skid | nvarchar | 255 | YES |
| 40 | actual_date_field_programmer_oso33x_requested_esp_pcp_vendor_to_install_the_skid | nvarchar | 255 | YES |
| 41 | actual_date_pcp_esp_vendor_delivered_the_skid | nvarchar | 255 | YES |
| 42 | actual_installation_date_by_vendor_of_esp/pcp_skid | nvarchar | 255 | YES |
| 43 | flow_line_po_no | nvarchar | 255 | YES |
| 44 | f_l_po_recd._date | nvarchar | 255 | YES |
| 45 | flowline_-_purpose_value | nvarchar | 255 | YES |
| 46 | station_name_no | nvarchar | 255 | YES |
| 47 | physical_tie_in_port_number | nvarchar | 255 | YES |
| 48 | date_of_tie_in_port_readiness | nvarchar | 255 | YES |
| 49 | physical_tie_in_port_available_when_flaf_issued | nvarchar | 255 | YES |
| 50 | engineering_actual_start_date | nvarchar | 255 | YES |
| 51 | engineering_actual_finish_date | nvarchar | 255 | YES |
| 52 | progress | nvarchar | 255 | YES |
| 53 | fl_dia | nvarchar | 255 | YES |
| 54 | fl_length_meter | nvarchar | 255 | YES |
| 55 | const._actual_start_date | nvarchar | 255 | YES |
| 56 | const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date | nvarchar | 255 | YES |
| 57 | flowline_construction_progress | nvarchar | 255 | YES |
| 58 | ohl_length_meter | nvarchar | 255 | YES |
| 59 | ohl_progress | nvarchar | 255 | YES |
| 60 | ohl_completion_date | nvarchar | 255 | YES |
| 61 | z6_data_submitted_date | nvarchar | 255 | YES |
| 62 | sap_notification_received_date_z6_2_days_before_eng._completion | nvarchar | 255 | YES |
| 63 | actual_rig_on_date | nvarchar | 255 | YES |
| 64 | actual_rig_off_date | nvarchar | 255 | YES |
| 65 | wlctf_acceptanceapproval_from_production | nvarchar | 255 | YES |
| 66 | actual_hoist_fbu_rsr_on_date | nvarchar | 255 | YES |
| 67 | actual_hoist_fbu_rsr_off_date | nvarchar | 255 | YES |
| 68 | wellpad_handover-2_from_hoist_fbu_rsr_off_date | nvarchar | 255 | YES |
| 69 | completion_type_rig_fbu_or_rsr_hoist | nvarchar | 255 | YES |
| 70 | actual_eng._completion_date | nvarchar | 255 | YES |
| 71 | actual_comm._start_date | nvarchar | 255 | YES |
| 72 | actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date | nvarchar | 255 | YES |
| 73 | engg_kpi_after_rig-off_days | nvarchar | 255 | YES |
| 74 | data_error | nvarchar | 255 | YES |
| 75 | reason_if_kpi_not_met | nvarchar | 255 | YES |
| 76 | remark_status_area_of_attention_issues_ | nvarchar | 255 | YES |
| 77 | rlmu_submitted_to_ho-date_with_in_7_days_from_actual_comm. | nvarchar | 255 | YES |
| 78 | flow_line_test_pack_completion_doc._submission_date_to_qs_dept. | nvarchar | 255 | YES |
| 79 | flow_line_test_pack_completion_progress | nvarchar | 255 | YES |
| 80 | over_all_progress_percentages | nvarchar | 255 | YES |
| 81 | ssfd_wells | nvarchar | 255 | YES |
| 82 | ipm | nvarchar | 255 | YES |
| 83 | access_road_5 | nvarchar | 255 | YES |
| 84 | earth_work_60 | nvarchar | 255 | YES |
| 85 | cellar_20 | nvarchar | 255 | YES |
| 86 | beam_pump_base_esp_pcp_foundation_5 | nvarchar | 255 | YES |
| 87 | earthing_1 | nvarchar | 255 | YES |
| 88 | septic_tank_1 | nvarchar | 255 | YES |
| 89 | water_2 | nvarchar | 255 | YES |
| 90 | waste_water_2 | nvarchar | 255 | YES |
| 91 | hdpe_liner_instalat_4 | nvarchar | 255 | YES |
| 92 | overall_loc._preparation_10_100 | nvarchar | 255 | YES |
| 93 | site_survey_5 | nvarchar | 255 | YES |
| 94 | survey_report_issue_5 | nvarchar | 255 | YES |
| 95 | design_sta_5 | nvarchar | 255 | YES |
| 96 | design_completed_issue_for_ta2_5_40 | nvarchar | 255 | YES |
| 97 | approved_by_15 | nvarchar | 255 | YES |
| 98 | afc_3_30 | nvarchar | 255 | YES |
| 99 | overall_engg._10_100 | nvarchar | 255 | YES |
| 100 | piping_mech_50 | nvarchar | 255 | YES |
| 101 | elect_30 | nvarchar | 255 | YES |
| 102 | instr_20 | nvarchar | 255 | YES |
| 103 | overall_material_10_100 | nvarchar | 255 | YES |
| 104 | cold_b_2 | nvarchar | 255 | YES |
| 105 | sleeper_pre_cast_ins_15 | nvarchar | 255 | YES |
| 106 | cs_pipe_welding_ndt_10_rt_for_op_100_for_60 | nvarchar | 255 | YES |
| 107 | pe_fussion_pull_20 | nvarchar | 255 | YES |
| 108 | final_hydro_t_3 | nvarchar | 255 | YES |
| 109 | overall_const._10_100 | nvarchar | 255 | YES |
| 110 | pole_hole_drill_40 | nvarchar | 255 | YES |
| 111 | pole_erect_40 | nvarchar | 255 | YES |
| 112 | conductor_string_18 | nvarchar | 255 | YES |
| 113 | ohl_ti_2 | nvarchar | 255 | YES |
| 114 | overall_ohl_progr_100 | nvarchar | 255 | YES |
| 115 | mechani_60 | nvarchar | 255 | YES |
| 116 | electri_15 | nvarchar | 255 | YES |
| 117 | instrumentat_20 | nvarchar | 255 | YES |
| 118 | overall_comm_mi_5 | nvarchar | 255 | YES |
| 119 | overall_comm_progress_100 | nvarchar | 255 | YES |
| 120 | location_preparation_status_in_progress_completed | nvarchar | 255 | YES |
| 121 | flow_line_const._status_in_progress_completed | nvarchar | 255 | YES |
| 122 | flow_line_commi._status_in_progress_completed | nvarchar | 255 | YES |
| 123 | well_year_white_space | nvarchar | 255 | YES |
| 124 | reasons_for_year_2018 | nvarchar | 255 | YES |
| 125 | column7 | nvarchar | 255 | YES |
| 126 | digital_wmr_import_remarks | nvarchar | 255 | YES |
| 127 | project_id | nvarchar | 255 | YES |
| 128 | Week_Number | nvarchar | 255 | YES |

### `dbo.WellMonitoringReport` (130 columns)

| # | Column | Type | MaxLen | Nullable |
|:--|:-------|:-----|:-------|:---------|
| 1 | sl_no | bigint | - | YES |
| 2 | sl_no_raw | nvarchar | 255 | YES |
| 3 | rig_no | nvarchar | 255 | YES |
| 4 | well_location | nvarchar | 255 | YES |
| 5 | well_name_after_spud | nvarchar | 255 | YES |
| 6 | pdo_well_id | nvarchar | 255 | YES |
| 7 | well_type | nvarchar | 255 | YES |
| 8 | northing | nvarchar | 255 | YES |
| 9 | easting | nvarchar | 255 | YES |
| 10 | locationdd | nvarchar | 255 | YES |
| 11 | flow_linedl | nvarchar | 255 | YES |
| 12 | location_po_no | nvarchar | 255 | YES |
| 13 | location_po_recvd_date | date | - | YES |
| 14 | location_-_purpose_value | nvarchar | 255 | YES |
| 15 | last_week_exp.rig_on_location_sap_data | date | - | YES |
| 16 | latest_exp.rig_on_location_sap_data | date | - | YES |
| 17 | exp.rig_off_location_sap_data | date | - | YES |
| 18 | date_-_material_po_placed | date | - | YES |
| 19 | date_-_material_available_at_site | date | - | YES |
| 20 | scr_no | nvarchar | 255 | YES |
| 21 | scr_date | date | - | YES |
| 22 | moc_raised | nvarchar | 255 | YES |
| 23 | moc_approved | nvarchar | 255 | YES |
| 24 | buffer_status | varchar | 16 | YES |
| 25 | actual_pegged_date | date | - | YES |
| 26 | last_week_cum_progress | decimal | - | YES |
| 27 | cum_progress_for_this_week | decimal | - | YES |
| 28 | actual_start_date | date | - | YES |
| 29 | actual_date_odc_requested_field_programmer_oso33x_for_esp_pcp_surface_cables | date | - | YES |
| 30 | date_oso33x_call_out_for_cable_installation_to_pcp_esp_vendor | date | - | YES |
| 31 | delivery_of_esp_pcp_surface_cable_by_field_programmer_oso33x | date | - | YES |
| 32 | installation_of_esp_pcp_surface_cable_by_vendors | date | - | YES |
| 33 | actual_finish_date | date | - | YES |
| 34 | flaf_issue_date | date | - | YES |
| 35 | ramz_id | nvarchar | 255 | YES |
| 36 | ramz_id_received_date_same_day_as_flaf_issue_date | date | - | YES |
| 37 | date_of_site_survey_report_issuance | date | - | YES |
| 38 | well_engineer_to_add_location_name_in_edm | nvarchar | 255 | YES |
| 39 | pt_to_request_for_esp_preliminary_design_through_ald | nvarchar | 255 | YES |
| 40 | actual_date_odc_requested_field_programmer_oso33x_to_install_esp_pcp_skid | date | - | YES |
| 41 | actual_date_field_programmer_oso33x_requested_esp_pcp_vendor_to_install_the_skid | date | - | YES |
| 42 | actual_date_pcp_esp_vendor_delivered_the_skid | date | - | YES |
| 43 | actual_installation_date_by_vendor_of_esp/pcp_skid | date | - | YES |
| 44 | flow_line_po_no | nvarchar | 255 | YES |
| 45 | f_l_po_recd._date | date | - | YES |
| 46 | flowline_-_purpose_value | nvarchar | 255 | YES |
| 47 | station_name_no | nvarchar | 255 | YES |
| 48 | physical_tie_in_port_number | nvarchar | 255 | YES |
| 49 | date_of_tie_in_port_readiness | date | - | YES |
| 50 | physical_tie_in_port_available_when_flaf_issued | nvarchar | 255 | YES |
| 51 | engineering_actual_start_date | date | - | YES |
| 52 | engineering_actual_finish_date | date | - | YES |
| 53 | progress | decimal | - | YES |
| 54 | fl_dia | nvarchar | 255 | YES |
| 55 | fl_length_meter | nvarchar | 255 | YES |
| 56 | const._actual_start_date | date | - | YES |
| 57 | const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date | date | - | YES |
| 58 | flowline_construction_progress | decimal | - | YES |
| 59 | ohl_length_meter | nvarchar | 255 | YES |
| 60 | ohl_progress | decimal | - | YES |
| 61 | ohl_completion_date | date | - | YES |
| 62 | z6_data_submitted_date | date | - | YES |
| 63 | sap_notification_received_date_z6_2_days_before_eng._completion | date | - | YES |
| 64 | actual_rig_on_date | date | - | YES |
| 65 | actual_rig_off_date | date | - | YES |
| 66 | wlctf_acceptanceapproval_from_production | date | - | YES |
| 67 | actual_hoist_fbu_rsr_on_date | date | - | YES |
| 68 | actual_hoist_fbu_rsr_off_date | date | - | YES |
| 69 | wellpad_handover-2_from_hoist_fbu_rsr_off_date | date | - | YES |
| 70 | completion_type_rig_fbu_or_rsr_hoist | nvarchar | 510 | YES |
| 71 | actual_eng._completion_date | date | - | YES |
| 72 | actual_comm._start_date | date | - | YES |
| 73 | actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date | date | - | YES |
| 74 | engg_kpi_after_rig-off_days | int | - | YES |
| 75 | data_error | varchar | 5 | YES |
| 76 | reason_if_kpi_not_met | nvarchar | 255 | YES |
| 77 | remark_status_area_of_attention_issues_ | nvarchar | 255 | YES |
| 78 | rlmu_submitted_to_ho-date_with_in_7_days_from_actual_comm. | date | - | YES |
| 79 | flow_line_test_pack_completion_doc._submission_date_to_qs_dept. | date | - | YES |
| 80 | flow_line_test_pack_completion_progress | decimal | - | YES |
| 81 | over_all_progress_percentages | decimal | - | YES |
| 82 | ssfd_wells | nvarchar | 255 | YES |
| 83 | ipm | nvarchar | 255 | YES |
| 84 | access_road_5 | decimal | - | YES |
| 85 | earth_work_60 | decimal | - | YES |
| 86 | cellar_20 | decimal | - | YES |
| 87 | beam_pump_base_esp_pcp_foundation_5 | decimal | - | YES |
| 88 | earthing_1 | decimal | - | YES |
| 89 | septic_tank_1 | decimal | - | YES |
| 90 | water_2 | decimal | - | YES |
| 91 | waste_water_2 | decimal | - | YES |
| 92 | hdpe_liner_instalat_4 | decimal | - | YES |
| 93 | overall_loc._preparation_10_100 | decimal | - | YES |
| 94 | site_survey_5 | decimal | - | YES |
| 95 | survey_report_issue_5 | decimal | - | YES |
| 96 | design_sta_5 | decimal | - | YES |
| 97 | design_completed_issue_for_ta2_5_40 | decimal | - | YES |
| 98 | approved_by_15 | decimal | - | YES |
| 99 | afc_3_30 | decimal | - | YES |
| 100 | overall_engg._10_100 | decimal | - | YES |
| 101 | piping_mech_50 | decimal | - | YES |
| 102 | elect_30 | decimal | - | YES |
| 103 | instr_20 | decimal | - | YES |
| 104 | overall_material_10_100 | decimal | - | YES |
| 105 | cold_b_2 | decimal | - | YES |
| 106 | sleeper_pre_cast_ins_15 | decimal | - | YES |
| 107 | cs_pipe_welding_ndt_10_rt_for_op_100_for_60 | decimal | - | YES |
| 108 | pe_fussion_pull_20 | decimal | - | YES |
| 109 | final_hydro_t_3 | decimal | - | YES |
| 110 | overall_const._10_100 | decimal | - | YES |
| 111 | pole_hole_drill_40 | decimal | - | YES |
| 112 | pole_erect_40 | decimal | - | YES |
| 113 | conductor_string_18 | decimal | - | YES |
| 114 | ohl_ti_2 | decimal | - | YES |
| 115 | overall_ohl_progr_100 | decimal | - | YES |
| 116 | mechani_60 | decimal | - | YES |
| 117 | electri_15 | decimal | - | YES |
| 118 | instrumentat_20 | decimal | - | YES |
| 119 | overall_comm_mi_5 | decimal | - | YES |
| 120 | overall_comm_progress_100 | decimal | - | YES |
| 121 | location_preparation_status_in_progress_completed | nvarchar | 255 | YES |
| 122 | flow_line_const._status_in_progress_completed | nvarchar | 255 | YES |
| 123 | flow_line_commi._status_in_progress_completed | nvarchar | 255 | YES |
| 124 | well_year_white_space | nvarchar | 255 | YES |
| 125 | reasons_for_year_2018 | nvarchar | 255 | YES |
| 126 | column7 | nvarchar | 255 | YES |
| 127 | digital_wmr_import_remarks | nvarchar | 255 | YES |
| 128 | project_id | nvarchar | 255 | YES |
| 129 | Week_Number | date | - | YES |
| 130 | Cluster | nvarchar | 50 | YES |

### `dbo.WellMonitoringReport_Latest` (130 columns)

| # | Column | Type | MaxLen | Nullable |
|:--|:-------|:-----|:-------|:---------|
| 1 | sl_no | bigint | - | YES |
| 2 | sl_no_raw | nvarchar | 255 | YES |
| 3 | rig_no | nvarchar | 255 | YES |
| 4 | well_location | nvarchar | 255 | YES |
| 5 | well_name_after_spud | nvarchar | 255 | YES |
| 6 | pdo_well_id | nvarchar | 255 | YES |
| 7 | well_type | nvarchar | 255 | YES |
| 8 | northing | nvarchar | 255 | YES |
| 9 | easting | nvarchar | 255 | YES |
| 10 | locationdd | nvarchar | 255 | YES |
| 11 | flow_linedl | nvarchar | 255 | YES |
| 12 | location_po_no | nvarchar | 255 | YES |
| 13 | location_po_recvd_date | date | - | YES |
| 14 | location_-_purpose_value | nvarchar | 255 | YES |
| 15 | last_week_exp.rig_on_location_sap_data | date | - | YES |
| 16 | latest_exp.rig_on_location_sap_data | date | - | YES |
| 17 | exp.rig_off_location_sap_data | date | - | YES |
| 18 | date_-_material_po_placed | date | - | YES |
| 19 | date_-_material_available_at_site | date | - | YES |
| 20 | scr_no | nvarchar | 255 | YES |
| 21 | scr_date | date | - | YES |
| 22 | moc_raised | nvarchar | 255 | YES |
| 23 | moc_approved | nvarchar | 255 | YES |
| 24 | buffer_status | varchar | 16 | YES |
| 25 | actual_pegged_date | date | - | YES |
| 26 | last_week_cum_progress | decimal | - | YES |
| 27 | cum_progress_for_this_week | decimal | - | YES |
| 28 | actual_start_date | date | - | YES |
| 29 | actual_date_odc_requested_field_programmer_oso33x_for_esp_pcp_surface_cables | date | - | YES |
| 30 | date_oso33x_call_out_for_cable_installation_to_pcp_esp_vendor | date | - | YES |
| 31 | delivery_of_esp_pcp_surface_cable_by_field_programmer_oso33x | date | - | YES |
| 32 | installation_of_esp_pcp_surface_cable_by_vendors | date | - | YES |
| 33 | actual_finish_date | date | - | YES |
| 34 | flaf_issue_date | date | - | YES |
| 35 | ramz_id | nvarchar | 255 | YES |
| 36 | ramz_id_received_date_same_day_as_flaf_issue_date | date | - | YES |
| 37 | date_of_site_survey_report_issuance | date | - | YES |
| 38 | well_engineer_to_add_location_name_in_edm | nvarchar | 255 | YES |
| 39 | pt_to_request_for_esp_preliminary_design_through_ald | nvarchar | 255 | YES |
| 40 | actual_date_odc_requested_field_programmer_oso33x_to_install_esp_pcp_skid | date | - | YES |
| 41 | actual_date_field_programmer_oso33x_requested_esp_pcp_vendor_to_install_the_skid | date | - | YES |
| 42 | actual_date_pcp_esp_vendor_delivered_the_skid | date | - | YES |
| 43 | actual_installation_date_by_vendor_of_esp/pcp_skid | date | - | YES |
| 44 | flow_line_po_no | nvarchar | 255 | YES |
| 45 | f_l_po_recd._date | date | - | YES |
| 46 | flowline_-_purpose_value | nvarchar | 255 | YES |
| 47 | station_name_no | nvarchar | 255 | YES |
| 48 | physical_tie_in_port_number | nvarchar | 255 | YES |
| 49 | date_of_tie_in_port_readiness | date | - | YES |
| 50 | physical_tie_in_port_available_when_flaf_issued | nvarchar | 255 | YES |
| 51 | engineering_actual_start_date | date | - | YES |
| 52 | engineering_actual_finish_date | date | - | YES |
| 53 | progress | decimal | - | YES |
| 54 | fl_dia | nvarchar | 255 | YES |
| 55 | fl_length_meter | nvarchar | 255 | YES |
| 56 | const._actual_start_date | date | - | YES |
| 57 | const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date | date | - | YES |
| 58 | flowline_construction_progress | decimal | - | YES |
| 59 | ohl_length_meter | nvarchar | 255 | YES |
| 60 | ohl_progress | decimal | - | YES |
| 61 | ohl_completion_date | date | - | YES |
| 62 | z6_data_submitted_date | date | - | YES |
| 63 | sap_notification_received_date_z6_2_days_before_eng._completion | date | - | YES |
| 64 | actual_rig_on_date | date | - | YES |
| 65 | actual_rig_off_date | date | - | YES |
| 66 | wlctf_acceptanceapproval_from_production | date | - | YES |
| 67 | actual_hoist_fbu_rsr_on_date | date | - | YES |
| 68 | actual_hoist_fbu_rsr_off_date | date | - | YES |
| 69 | wellpad_handover-2_from_hoist_fbu_rsr_off_date | date | - | YES |
| 70 | completion_type_rig_fbu_or_rsr_hoist | nvarchar | 510 | YES |
| 71 | actual_eng._completion_date | date | - | YES |
| 72 | actual_comm._start_date | date | - | YES |
| 73 | actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date | date | - | YES |
| 74 | engg_kpi_after_rig-off_days | int | - | YES |
| 75 | data_error | varchar | 5 | YES |
| 76 | reason_if_kpi_not_met | nvarchar | 255 | YES |
| 77 | remark_status_area_of_attention_issues_ | nvarchar | 255 | YES |
| 78 | rlmu_submitted_to_ho-date_with_in_7_days_from_actual_comm. | date | - | YES |
| 79 | flow_line_test_pack_completion_doc._submission_date_to_qs_dept. | date | - | YES |
| 80 | flow_line_test_pack_completion_progress | decimal | - | YES |
| 81 | over_all_progress_percentages | decimal | - | YES |
| 82 | ssfd_wells | nvarchar | 255 | YES |
| 83 | ipm | nvarchar | 255 | YES |
| 84 | access_road_5 | decimal | - | YES |
| 85 | earth_work_60 | decimal | - | YES |
| 86 | cellar_20 | decimal | - | YES |
| 87 | beam_pump_base_esp_pcp_foundation_5 | decimal | - | YES |
| 88 | earthing_1 | decimal | - | YES |
| 89 | septic_tank_1 | decimal | - | YES |
| 90 | water_2 | decimal | - | YES |
| 91 | waste_water_2 | decimal | - | YES |
| 92 | hdpe_liner_instalat_4 | decimal | - | YES |
| 93 | overall_loc._preparation_10_100 | decimal | - | YES |
| 94 | site_survey_5 | decimal | - | YES |
| 95 | survey_report_issue_5 | decimal | - | YES |
| 96 | design_sta_5 | decimal | - | YES |
| 97 | design_completed_issue_for_ta2_5_40 | decimal | - | YES |
| 98 | approved_by_15 | decimal | - | YES |
| 99 | afc_3_30 | decimal | - | YES |
| 100 | overall_engg._10_100 | decimal | - | YES |
| 101 | piping_mech_50 | decimal | - | YES |
| 102 | elect_30 | decimal | - | YES |
| 103 | instr_20 | decimal | - | YES |
| 104 | overall_material_10_100 | decimal | - | YES |
| 105 | cold_b_2 | decimal | - | YES |
| 106 | sleeper_pre_cast_ins_15 | decimal | - | YES |
| 107 | cs_pipe_welding_ndt_10_rt_for_op_100_for_60 | decimal | - | YES |
| 108 | pe_fussion_pull_20 | decimal | - | YES |
| 109 | final_hydro_t_3 | decimal | - | YES |
| 110 | overall_const._10_100 | decimal | - | YES |
| 111 | pole_hole_drill_40 | decimal | - | YES |
| 112 | pole_erect_40 | decimal | - | YES |
| 113 | conductor_string_18 | decimal | - | YES |
| 114 | ohl_ti_2 | decimal | - | YES |
| 115 | overall_ohl_progr_100 | decimal | - | YES |
| 116 | mechani_60 | decimal | - | YES |
| 117 | electri_15 | decimal | - | YES |
| 118 | instrumentat_20 | decimal | - | YES |
| 119 | overall_comm_mi_5 | decimal | - | YES |
| 120 | overall_comm_progress_100 | decimal | - | YES |
| 121 | location_preparation_status_in_progress_completed | nvarchar | 255 | YES |
| 122 | flow_line_const._status_in_progress_completed | nvarchar | 255 | YES |
| 123 | flow_line_commi._status_in_progress_completed | nvarchar | 255 | YES |
| 124 | well_year_white_space | nvarchar | 255 | YES |
| 125 | reasons_for_year_2018 | nvarchar | 255 | YES |
| 126 | column7 | nvarchar | 255 | YES |
| 127 | digital_wmr_import_remarks | nvarchar | 255 | YES |
| 128 | project_id | nvarchar | 255 | YES |
| 129 | Week_Number | date | - | YES |
| 130 | Cluster | nvarchar | 50 | YES |

### `dbo.WellMonitoringReport_Staged` (161 columns)

| # | Column | Type | MaxLen | Nullable |
|:--|:-------|:-----|:-------|:---------|
| 1 | sl_no | nvarchar | 255 | YES |
| 2 | rig_no | nvarchar | 255 | NO |
| 3 | well_location | nvarchar | 255 | YES |
| 4 | well_name_after_spud | nvarchar | 255 | YES |
| 5 | pdo_well_id | nvarchar | 255 | YES |
| 6 | well_type | nvarchar | 255 | YES |
| 7 | northing | nvarchar | 255 | YES |
| 8 | easting | nvarchar | 255 | YES |
| 9 | locationdd | nvarchar | 255 | YES |
| 10 | flow_linedl | nvarchar | 255 | YES |
| 11 | location_po_no | nvarchar | 255 | YES |
| 12 | location_po_recvd_date | nvarchar | 255 | YES |
| 13 | location_-_purpose_value | nvarchar | 255 | YES |
| 14 | last_week_exp.rig_on_location_sap_data | nvarchar | 255 | YES |
| 15 | latest_exp.rig_on_location_sap_data | nvarchar | 255 | YES |
| 16 | exp.rig_off_location_sap_data | nvarchar | 255 | YES |
| 17 | date_-_material_po_placed | nvarchar | 255 | YES |
| 18 | date_-_material_available_at_site | nvarchar | 255 | YES |
| 19 | scr_no | nvarchar | 255 | YES |
| 20 | scr_date | nvarchar | 255 | YES |
| 21 | moc_raised | nvarchar | 255 | YES |
| 22 | moc_approved | nvarchar | 255 | YES |
| 23 | buffer_status | nvarchar | 255 | YES |
| 24 | actual_pegged_date | nvarchar | 255 | YES |
| 25 | last_week_cum_progress | nvarchar | 255 | YES |
| 26 | cum_progress_for_this_week | nvarchar | 255 | YES |
| 27 | actual_start_date | nvarchar | 255 | YES |
| 28 | actual_date_odc_requested_field_programmer_oso33x_for_esp_pcp_surface_cables | nvarchar | 255 | YES |
| 29 | date_oso33x_call_out_for_cable_installation_to_pcp_esp_vendor | nvarchar | 255 | YES |
| 30 | delivery_of_esp_pcp_surface_cable_by_field_programmer_oso33x | nvarchar | 255 | YES |
| 31 | installation_of_esp_pcp_surface_cable_by_vendors | nvarchar | 255 | YES |
| 32 | actual_finish_date | nvarchar | 255 | YES |
| 33 | flaf_issue_date | nvarchar | 255 | YES |
| 34 | ramz_id | nvarchar | 255 | YES |
| 35 | ramz_id_received_date_same_day_as_flaf_issue_date | nvarchar | 255 | YES |
| 36 | date_of_site_survey_report_issuance | nvarchar | 255 | YES |
| 37 | well_engineer_to_add_location_name_in_edm | nvarchar | 255 | YES |
| 38 | pt_to_request_for_esp_preliminary_design_through_ald | nvarchar | 255 | YES |
| 39 | actual_date_odc_requested_field_programmer_oso33x_to_install_esp_pcp_skid | nvarchar | 255 | YES |
| 40 | actual_date_field_programmer_oso33x_requested_esp_pcp_vendor_to_install_the_skid | nvarchar | 255 | YES |
| 41 | actual_date_pcp_esp_vendor_delivered_the_skid | nvarchar | 255 | YES |
| 42 | actual_installation_date_by_vendor_of_esp/pcp_skid | nvarchar | 255 | YES |
| 43 | flow_line_po_no | nvarchar | 255 | YES |
| 44 | f_l_po_recd._date | nvarchar | 255 | YES |
| 45 | flowline_-_purpose_value | nvarchar | 255 | YES |
| 46 | station_name_no | nvarchar | 255 | YES |
| 47 | physical_tie_in_port_number | nvarchar | 255 | YES |
| 48 | date_of_tie_in_port_readiness | nvarchar | 255 | YES |
| 49 | physical_tie_in_port_available_when_flaf_issued | nvarchar | 255 | YES |
| 50 | engineering_actual_start_date | nvarchar | 255 | YES |
| 51 | engineering_actual_finish_date | nvarchar | 255 | YES |
| 52 | progress | nvarchar | 255 | YES |
| 53 | fl_dia | nvarchar | 255 | YES |
| 54 | fl_length_meter | nvarchar | 255 | YES |
| 55 | const._actual_start_date | nvarchar | 255 | YES |
| 56 | const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date | nvarchar | 255 | YES |
| 57 | flowline_construction_progress | nvarchar | 255 | YES |
| 58 | ohl_length_meter | nvarchar | 255 | YES |
| 59 | ohl_progress | nvarchar | 255 | YES |
| 60 | ohl_completion_date | nvarchar | 255 | YES |
| 61 | z6_data_submitted_date | nvarchar | 255 | YES |
| 62 | sap_notification_received_date_z6_2_days_before_eng._completion | nvarchar | 255 | YES |
| 63 | actual_rig_on_date | nvarchar | 255 | YES |
| 64 | actual_rig_off_date | nvarchar | 255 | YES |
| 65 | wlctf_acceptanceapproval_from_production | nvarchar | 255 | YES |
| 66 | actual_hoist_fbu_rsr_on_date | nvarchar | 255 | YES |
| 67 | actual_hoist_fbu_rsr_off_date | nvarchar | 255 | YES |
| 68 | wellpad_handover-2_from_hoist_fbu_rsr_off_date | nvarchar | 255 | YES |
| 69 | completion_type_rig_fbu_or_rsr_hoist | nvarchar | 255 | YES |
| 70 | actual_eng._completion_date | nvarchar | 255 | YES |
| 71 | actual_comm._start_date | nvarchar | 255 | YES |
| 72 | actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date | nvarchar | 255 | YES |
| 73 | engg_kpi_after_rig-off_days | nvarchar | 255 | YES |
| 74 | data_error | nvarchar | 255 | YES |
| 75 | reason_if_kpi_not_met | nvarchar | 255 | YES |
| 76 | remark_status_area_of_attention_issues_ | nvarchar | 255 | YES |
| 77 | rlmu_submitted_to_ho-date_with_in_7_days_from_actual_comm. | nvarchar | 255 | YES |
| 78 | flow_line_test_pack_completion_doc._submission_date_to_qs_dept. | nvarchar | 255 | YES |
| 79 | flow_line_test_pack_completion_progress | nvarchar | 255 | YES |
| 80 | over_all_progress_percentages | nvarchar | 255 | YES |
| 81 | ssfd_wells | nvarchar | 255 | YES |
| 82 | ipm | nvarchar | 255 | YES |
| 83 | access_road_5 | nvarchar | 255 | YES |
| 84 | earth_work_60 | nvarchar | 255 | YES |
| 85 | cellar_20 | nvarchar | 255 | YES |
| 86 | beam_pump_base_esp_pcp_foundation_5 | nvarchar | 255 | YES |
| 87 | earthing_1 | nvarchar | 255 | YES |
| 88 | septic_tank_1 | nvarchar | 255 | YES |
| 89 | water_2 | nvarchar | 255 | YES |
| 90 | waste_water_2 | nvarchar | 255 | YES |
| 91 | hdpe_liner_instalat_4 | nvarchar | 255 | YES |
| 92 | overall_loc._preparation_10_100 | nvarchar | 255 | YES |
| 93 | site_survey_5 | nvarchar | 255 | YES |
| 94 | survey_report_issue_5 | nvarchar | 255 | YES |
| 95 | design_sta_5 | nvarchar | 255 | YES |
| 96 | design_completed_issue_for_ta2_5_40 | nvarchar | 255 | YES |
| 97 | approved_by_15 | nvarchar | 255 | YES |
| 98 | afc_3_30 | nvarchar | 255 | YES |
| 99 | overall_engg._10_100 | nvarchar | 255 | YES |
| 100 | piping_mech_50 | nvarchar | 255 | YES |
| 101 | elect_30 | nvarchar | 255 | YES |
| 102 | instr_20 | nvarchar | 255 | YES |
| 103 | overall_material_10_100 | nvarchar | 255 | YES |
| 104 | cold_b_2 | nvarchar | 255 | YES |
| 105 | sleeper_pre_cast_ins_15 | nvarchar | 255 | YES |
| 106 | cs_pipe_welding_ndt_10_rt_for_op_100_for_60 | nvarchar | 255 | YES |
| 107 | pe_fussion_pull_20 | nvarchar | 255 | YES |
| 108 | final_hydro_t_3 | nvarchar | 255 | YES |
| 109 | overall_const._10_100 | nvarchar | 255 | YES |
| 110 | pole_hole_drill_40 | nvarchar | 255 | YES |
| 111 | pole_erect_40 | nvarchar | 255 | YES |
| 112 | conductor_string_18 | nvarchar | 255 | YES |
| 113 | ohl_ti_2 | nvarchar | 255 | YES |
| 114 | overall_ohl_progr_100 | nvarchar | 255 | YES |
| 115 | mechani_60 | nvarchar | 255 | YES |
| 116 | electri_15 | nvarchar | 255 | YES |
| 117 | instrumentat_20 | nvarchar | 255 | YES |
| 118 | overall_comm_mi_5 | nvarchar | 255 | YES |
| 119 | overall_comm_progress_100 | nvarchar | 255 | YES |
| 120 | location_preparation_status_in_progress_completed | nvarchar | 255 | YES |
| 121 | flow_line_const._status_in_progress_completed | nvarchar | 255 | YES |
| 122 | flow_line_commi._status_in_progress_completed | nvarchar | 255 | YES |
| 123 | well_year_white_space | nvarchar | 255 | YES |
| 124 | reasons_for_year_2018 | nvarchar | 255 | YES |
| 125 | column7 | nvarchar | 255 | YES |
| 126 | digital_wmr_import_remarks | nvarchar | 255 | YES |
| 127 | project_id | nvarchar | 255 | YES |
| 128 | Week_Number | nvarchar | 255 | YES |
| 129 | Week_Number_d | date | - | YES |
| 130 | actual_rig_on_date_d | date | - | YES |
| 131 | actual_rig_off_date_d | date | - | YES |
| 132 | wlctf_acceptance_d | date | - | YES |
| 133 | hoist_on_date_d | date | - | YES |
| 134 | hoist_off_date_d | date | - | YES |
| 135 | handover2_date_d | date | - | YES |
| 136 | eng_completion_date_d | date | - | YES |
| 137 | comm_start_date_d | date | - | YES |
| 138 | comm_finish_date_d | date | - | YES |
| 139 | flaf_issue_date_d | date | - | YES |
| 140 | location_po_recvd_date_d | date | - | YES |
| 141 | scr_date_d | date | - | YES |
| 142 | actual_pegged_date_d | date | - | YES |
| 143 | actual_start_date_d | date | - | YES |
| 144 | actual_finish_date_d | date | - | YES |
| 145 | ramz_id_received_date_d | date | - | YES |
| 146 | site_survey_report_issuance_d | date | - | YES |
| 147 | f_l_po_recd_date_d | date | - | YES |
| 148 | tie_in_port_readiness_d | date | - | YES |
| 149 | const_actual_start_date_d | date | - | YES |
| 150 | ohl_completion_date_d | date | - | YES |
| 151 | last_week_cum_progress_p | decimal | - | YES |
| 152 | cum_progress_for_this_week_p | decimal | - | YES |
| 153 | flowline_construction_progress_p | decimal | - | YES |
| 154 | ohl_progress_p | decimal | - | YES |
| 155 | overall_progress_p | decimal | - | YES |
| 156 | overall_loc_preparation_p | decimal | - | YES |
| 157 | overall_engg_p | decimal | - | YES |
| 158 | overall_material_p | decimal | - | YES |
| 159 | overall_const_p | decimal | - | YES |
| 160 | overall_ohl_p | decimal | - | YES |
| 161 | overall_comm_progress_p | decimal | - | YES |

### `dbo.company_employees` (8 columns)

| # | Column | Type | MaxLen | Nullable |
|:--|:-------|:-----|:-------|:---------|
| 1 | id | decimal | - | NO |
| 2 | UId | nvarchar | 100 | NO |
| 3 | Name | nvarchar | 255 | YES |
| 4 | Status | nvarchar | 50 | YES |
| 5 | locationCode | nvarchar | 100 | YES |
| 6 | Email | nvarchar | 255 | YES |
| 7 | code | nvarchar | 100 | YES |
| 8 | company | nvarchar | 255 | YES |

### `dbo.crews` (8 columns)

| # | Column | Type | MaxLen | Nullable |
|:--|:-------|:-----|:-------|:---------|
| 1 | ID | nvarchar | 255 | YES |
| 2 | Code | nvarchar | 255 | YES |
| 3 | Account | nvarchar | 255 | YES |
| 4 | Location | nvarchar | 255 | YES |
| 5 | CrewType | nvarchar | 255 | YES |
| 6 | Supervisor | nvarchar | 255 | YES |
| 7 | Employees | nvarchar | 255 | YES |
| 8 | Equipments | nvarchar | 255 | YES |

### `dbo.schema_knowledge_base` (7 columns)

| # | Column | Type | MaxLen | Nullable |
|:--|:-------|:-----|:-------|:---------|
| 1 | id | int | - | NO |
| 2 | chunk_id | nvarchar | 200 | NO |
| 3 | chunk_text | nvarchar | -1 | NO |
| 4 | table_name | nvarchar | 200 | YES |
| 5 | chunk_type | nvarchar | 50 | YES |
| 6 | embedding | varbinary | -1 | YES |
| 7 | created_at | datetime2 | - | YES |

### `dbo.task_daily` (43 columns)

| # | Column | Type | MaxLen | Nullable |
|:--|:-------|:-----|:-------|:---------|
| 1 | id | bigint | - | NO |
| 2 | ActionOn | date | - | NO |
| 3 | task_code | nvarchar | 100 | YES |
| 4 | schedule_id | bigint | - | YES |
| 5 | project_id | uniqueidentifier | - | YES |
| 6 | required | decimal | - | YES |
| 7 | planned | decimal | - | YES |
| 8 | duration | decimal | - | YES |
| 9 | remaining_duration | decimal | - | YES |
| 10 | progress | decimal | - | YES |
| 11 | ready | bit | - | YES |
| 12 | completed | bit | - | YES |
| 13 | plan | bit | - | YES |
| 14 | committed_start | date | - | YES |
| 15 | committed_end | date | - | YES |
| 16 | target_start | date | - | YES |
| 17 | target_end | date | - | YES |
| 18 | actual_start | date | - | YES |
| 19 | actual_end | date | - | YES |
| 20 | startDate | date | - | YES |
| 21 | endDate | date | - | YES |
| 22 | crew_type | nvarchar | 50 | YES |
| 23 | crew_code | nvarchar | 100 | YES |
| 24 | planned_crew | nvarchar | 100 | YES |
| 25 | well_id | nvarchar | 50 | YES |
| 26 | task_uom | nvarchar | 50 | YES |
| 27 | data_hours | decimal | - | YES |
| 28 | data_qty | decimal | - | YES |
| 29 | data_employees | nvarchar | -1 | YES |
| 30 | task_assignee | nvarchar | 255 | YES |
| 31 | supervisor_email | nvarchar | 255 | YES |
| 32 | url | nvarchar | 2048 | YES |
| 33 | task_data | nvarchar | -1 | YES |
| 34 | daily_data | nvarchar | -1 | YES |
| 35 | created_at | datetime2 | - | YES |
| 36 | updated_at | datetime2 | - | YES |
| 37 | daily_ph_name | nvarchar | 255 | YES |
| 38 | daily_equipment_ids | nvarchar | 255 | YES |
| 39 | daily_employee_ids | nvarchar | -1 | YES |
| 40 | daily_actual_quantity | decimal | - | YES |
| 41 | daily_actual_hours | decimal | - | YES |
| 42 | daily_completed | bit | - | YES |
| 43 | time_stamp | nvarchar | 255 | YES |

## 3. Row Counts for Key Tables

| Table | Row Count |
|:------|:----------|
| WMR | ✗ Error: ('42S02', "[42S02] [Microsoft][ODBC Driver 18 for SQL Server |
| WellMonitoringReport | 268 |
| WMR_TaskPlan_csv_imported | ✗ Error: ('42S02', "[42S02] [Microsoft][ODBC Driver 18 for SQL Server |
| WMR_SQL_Bulk_Update | ✗ Error: ('42S02', "[42S02] [Microsoft][ODBC Driver 18 for SQL Server |
| Job_Progress_Report_GB | 439 |
| Job_Progress_PlanSnapshot | 439 |
| PH_Productivity | ✗ Error: ('42S02', "[42S02] [Microsoft][ODBC Driver 18 for SQL Server |
| vw_JOB_COST | ✗ Error: ('42S02', "[42S02] [Microsoft][ODBC Driver 18 for SQL Server |
| task_daily | 35,394 |
| ActivityTaskPlan | 100,000 |
| Revenue | 21,566 |
| Employee | 5,554 |
| crews | 5,758 |
| Equipment | ✗ Error: ('42S02', "[42S02] [Microsoft][ODBC Driver 18 for SQL Server |
| SAP_DRILLING_SEQUENCE_Staging | ✗ Error: ('42S02', "[42S02] [Microsoft][ODBC Driver 18 for SQL Server |
| ProjectIDs | 19 |
| DesignTrackerCSVImport | ✗ Error: ('42S02', "[42S02] [Microsoft][ODBC Driver 18 for SQL Server |
| ActivityCodesNorms | ✗ Error: ('42S02', "[42S02] [Microsoft][ODBC Driver 18 for SQL Server |
| vw_JobProgress | ✗ Error: ('42S02', "[42S02] [Microsoft][ODBC Driver 18 for SQL Server |
| Daily_Plan_Report | ✗ Error: ('42S02', "[42S02] [Microsoft][ODBC Driver 18 for SQL Server |
| New_Daily_Plan | ✗ Error: ('42S02', "[42S02] [Microsoft][ODBC Driver 18 for SQL Server |
| data_table_sched_jsons | ✗ Error: ('42S02', "[42S02] [Microsoft][ODBC Driver 18 for SQL Server |
| WBS_Master_Tracker_ | 81,846 |
| PH_PRODUCTIVITY_WEEKLY_REPORT | 510 |

## 4. WMR Historical Depth Analysis

✗ WMR query failed: ('42S02', "[42S02] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]Invalid object name 'dbo.WMR'. (208) (SQLExecDirectW)")
✗ Week distribution query failed: ('42S02', "[42S02] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]Invalid object name 'dbo.WMR'. (208) (SQLExecDirectW)")

## 5. Sample WMR Time-Series (5 wells)

✗ Sample query failed: ('42S02', "[42S02] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]Invalid object name 'dbo.WMR'. (208) (SQLExecDirectW)")
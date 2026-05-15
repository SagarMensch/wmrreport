# Neo4j Tables Schema Detail Check

## ActivityTaskPlan
**Rows:** 100000
**Columns:** 38

| # | Column | DataType | Nullable | MaxLen |
|---|--------|----------|----------|--------|
| 1 | row_id | bigint | NO |  |
| 2 | source_id | nvarchar | YES | 100 |
| 3 | Data | nvarchar | YES | -1 |
| 4 | ancestor | nvarchar | YES | 255 |
| 5 | duration | nvarchar | YES | 100 |
| 6 | progress | nvarchar | YES | 100 |
| 7 | crew_uid | nvarchar | YES | 255 |
| 8 | crew_type | nvarchar | YES | 50 |
| 9 | qty | nvarchar | YES | 100 |
| 10 | manhours | nvarchar | YES | 100 |
| 11 | weightage | nvarchar | YES | 100 |
| 12 | parent | nvarchar | YES | 100 |
| 13 | start_date | datetime2 | YES |  |
| 14 | end_date | datetime2 | YES |  |
| 15 | target_start | datetime2 | YES |  |
| 16 | target_end | datetime2 | YES |  |
| 17 | actual_start | datetime2 | YES |  |
| 18 | actual_end | datetime2 | YES |  |
| 19 | qtyactual | nvarchar | YES | 100 |
| 20 | qtyforacst | nvarchar | YES | 100 |
| 21 | manhoursactual | nvarchar | YES | 100 |
| 22 | manhourforacst | nvarchar | YES | 100 |
| 23 | code | nvarchar | YES | 200 |
| 24 | text | nvarchar | YES | -1 |
| 25 | type | nvarchar | YES | 100 |
| 26 | schedule_id | nvarchar | YES | 100 |
| 27 | project_id | nvarchar | YES | 100 |
| 28 | task_assignee | nvarchar | YES | 255 |
| 29 | supervisor_email | nvarchar | YES | 255 |
| 30 | attributes | nvarchar | YES | -1 |
| 31 | remaining_duration | nvarchar | YES | 100 |
| 32 | Resume_Suspend | nvarchar | YES | 255 |
| 33 | data_nonprod | nvarchar | YES | -1 |
| 34 | created_at | datetime2 | YES |  |
| 35 | updated_at | datetime2 | YES |  |
| 36 | Well_ID | nvarchar | YES | 50 |
| 37 | Parent_WBS | nvarchar | YES | 255 |
| 38 | Time_Stamp | nvarchar | YES | 255 |

## Employee
**Rows:** 5554
**Columns:** 11

| # | Column | DataType | Nullable | MaxLen |
|---|--------|----------|----------|--------|
| 1 | id | int | NO |  |
| 2 | UId | nvarchar | YES | 100 |
| 3 | Name | nvarchar | YES | 255 |
| 4 | Email | nvarchar | YES | 255 |
| 5 | Status | nvarchar | YES | 50 |
| 6 | Supervisor | int | YES |  |
| 7 | Account | nvarchar | YES | 255 |
| 8 | EmployeeType | int | YES |  |
| 9 | Company | nvarchar | YES | 255 |
| 10 | Manager | int | YES |  |
| 11 | Location | nvarchar | YES | 255 |

## Job_Progress_Report_GB
**Rows:** 439
**Columns:** 30

| # | Column | DataType | Nullable | MaxLen |
|---|--------|----------|----------|--------|
| 1 | Sl.No | bigint | YES |  |
| 2 | Category | nvarchar | YES | 50 |
| 3 | Well ID | nvarchar | YES | 50 |
| 4 | Well Name / Project Name | nvarchar | YES | 255 |
| 5 | PO No | nvarchar | YES | 255 |
| 6 | WBS No | nvarchar | YES | 50 |
| 7 | Cum-Prior Month Actual % | decimal | YES |  |
| 8 | Week-1 Plan % | decimal | YES |  |
| 9 | Week-1 Actual % | decimal | YES |  |
| 10 | Week-2 Plan % | decimal | YES |  |
| 11 | Week-2 Actual % | decimal | YES |  |
| 12 | Week-3 Plan % | decimal | YES |  |
| 13 | Week-3 Actual % | decimal | YES |  |
| 14 | Week-4 Plan % | decimal | YES |  |
| 15 | Week-4 Actual % | decimal | YES |  |
| 16 | Week-5 Plan % | decimal | YES |  |
| 17 | Week-5 Actual % | decimal | YES |  |
| 18 | Current Month Plan % | decimal | YES |  |
| 19 | Current Month Actual % | decimal | YES |  |
| 20 | Cum-Current Month Plan % | decimal | YES |  |
| 21 | Cum-Current Month Actual % | decimal | YES |  |
| 22 | Target End | date | YES |  |
| 23 | Purpose Value | decimal | YES |  |
| 24 | Cum-Prior Month Plan | decimal | YES |  |
| 25 | Cum-Prior Month Actual | decimal | YES |  |
| 26 | Current month Plan | decimal | YES |  |
| 27 | Current Month Actual | decimal | YES |  |
| 28 | Cum - Current Month Plan | decimal | YES |  |
| 29 | Cum - Current Month Actual | decimal | YES |  |
| 30 | Remarks | nvarchar | YES | 200 |

## PH_PRODUCTIVITY_WEEKLY_REPORT
**Rows:** 510
**Columns:** 25

| # | Column | DataType | Nullable | MaxLen |
|---|--------|----------|----------|--------|
| 1 | S.No | bigint | YES |  |
| 2 | Month | nvarchar | YES | 30 |
| 3 | Year | int | YES |  |
| 4 | MonthStart | date | YES |  |
| 5 | PA Name | nvarchar | NO | 4000 |
| 6 | PH Emp ID | nvarchar | NO | 50 |
| 7 | PH Name | nvarchar | NO | 255 |
| 8 | ATNM/Sub Contractor | varchar | NO | 14 |
| 9 | Category | nvarchar | NO | 4000 |
| 10 | Crew Type | nvarchar | NO | 4000 |
| 11 | Crew Discipline | nvarchar | NO | 4000 |
| 12 | Crew Name | nvarchar | NO | 4000 |
| 13 | Average Productivity (%) | decimal | YES |  |
| 14 | W1_PI (CMR) | varchar | YES | 2 |
| 15 | W1_PI (T-Wise) | varchar | YES | 2 |
| 16 | W2_PI (CMR) | varchar | YES | 2 |
| 17 | W2_PI (T-Wise) | varchar | YES | 2 |
| 18 | W3_PI (CMR) | varchar | YES | 2 |
| 19 | W3_PI (T-Wise) | varchar | YES | 2 |
| 20 | W4_PI (CMR) | varchar | YES | 2 |
| 21 | W4_PI (T-Wise) | varchar | YES | 2 |
| 22 | W5_PI (CMR) | varchar | YES | 2 |
| 23 | W5_PI (T-Wise) | varchar | YES | 2 |
| 24 | Month PI (CMR) | varchar | NO | 2 |
| 25 | Month PI (T-Wise) | varchar | NO | 2 |

## ProjectIDs
**Rows:** 19
**Columns:** 4

| # | Column | DataType | Nullable | MaxLen |
|---|--------|----------|----------|--------|
| 1 | Code | nvarchar | YES | 50 |
| 2 | column2 | nvarchar | YES | 50 |
| 3 | Number | tinyint | YES |  |
| 4 | ID | nvarchar | YES | 50 |

## Revenue
**Rows:** 21566
**Columns:** 18

| # | Column | DataType | Nullable | MaxLen |
|---|--------|----------|----------|--------|
| 1 | id | bigint | NO |  |
| 2 | rigcode | nvarchar | YES | 50 |
| 3 | well_id | nvarchar | YES | 50 |
| 4 | code | nvarchar | YES | 100 |
| 5 | pms | decimal | YES |  |
| 6 | step_type | nvarchar | YES | 100 |
| 7 | planned_progress | nvarchar | YES | 255 |
| 8 | plan_percent | nvarchar | YES | 50 |
| 9 | acutal_progress | decimal | YES |  |
| 10 | act_percent | nvarchar | YES | 50 |
| 11 | total_purpose_value | decimal | YES |  |
| 12 | planned_purpose_value | nvarchar | YES | 50 |
| 13 | actual_purpose_value | decimal | YES |  |
| 14 | planned_progress_next_week | nvarchar | YES | 255 |
| 15 | plan_percent_next_week | nvarchar | YES | 50 |
| 16 | planned_purpose_value_next_week | nvarchar | YES | 50 |
| 17 | Title | nvarchar | YES | 255 |
| 18 | created_at | datetime2 | YES |  |

## SAP_DRILLING_SEQUENCE
**Rows:** 6159
**Columns:** 19

| # | Column | DataType | Nullable | MaxLen |
|---|--------|----------|----------|--------|
| 1 | Work_Center | nvarchar | YES | 50 |
| 2 | Operation_Short | nvarchar | YES | 50 |
| 3 | Activity | nvarchar | YES | 50 |
| 4 | Opr_System_status | nvarchar | YES | 50 |
| 5 | Earl_start_date | date | YES |  |
| 6 | EarliestEndDate | date | YES |  |
| 7 | Station_Code | nvarchar | YES | 50 |
| 8 | Normal_duration | float | YES |  |
| 9 | Norm_duratn_un | nvarchar | YES | 50 |
| 10 | Well_Name | nvarchar | YES | 50 |
| 11 | Field | nvarchar | YES | 50 |
| 12 | Responsible_asset | nvarchar | YES | 50 |
| 13 | Well_ID | varchar | NO | 50 |
| 14 | Well_Location | nvarchar | YES | 50 |
| 15 | Well_Function | nvarchar | YES | 50 |
| 16 | Well_Category | nvarchar | YES | 50 |
| 17 | PCAP_Category | nvarchar | YES | 50 |
| 18 | Move_days | tinyint | YES |  |
| 19 | PDO_Well_Type | nvarchar | YES | 50 |

## WBS_Master_Tracker_
**Rows:** 81846
**Columns:** 15

| # | Column | DataType | Nullable | MaxLen |
|---|--------|----------|----------|--------|
| 1 | Sr_No | nvarchar | YES | 50 |
| 2 | WBS_Code | nvarchar | YES | 50 |
| 3 | Project_Def | nvarchar | YES | 50 |
| 4 | WD_PRJ | nvarchar | YES | 50 |
| 5 | Plant_Code | nvarchar | YES | 50 |
| 6 | Plant_Name | nvarchar | YES | 50 |
| 7 | Cluster | nvarchar | YES | 50 |
| 8 | Well_ID_Project_PO | nvarchar | YES | 50 |
| 9 | Activity_code | nvarchar | YES | 50 |
| 10 | Activity | nvarchar | YES | 50 |
| 11 | Category | nvarchar | YES | 50 |
| 12 | Sr_No_2 | nvarchar | YES | 50 |
| 13 | LMPS | nvarchar | YES | 50 |
| 14 | Duplicate_check | nvarchar | YES | 50 |
| 15 | Last_Updated_on | nvarchar | YES | 50 |

## WMR_Full
**Rows:** 18969
**Columns:** 128

| # | Column | DataType | Nullable | MaxLen |
|---|--------|----------|----------|--------|
| 1 | sl_no | nvarchar | YES | 255 |
| 2 | rig_no | nvarchar | NO | 255 |
| 3 | well_location | nvarchar | YES | 255 |
| 4 | well_name_after_spud | nvarchar | YES | 255 |
| 5 | pdo_well_id | nvarchar | YES | 255 |
| 6 | well_type | nvarchar | YES | 255 |
| 7 | northing | nvarchar | YES | 255 |
| 8 | easting | nvarchar | YES | 255 |
| 9 | locationdd | nvarchar | YES | 255 |
| 10 | flow_linedl | nvarchar | YES | 255 |
| 11 | location_po_no | nvarchar | YES | 255 |
| 12 | location_po_recvd_date | nvarchar | YES | 255 |
| 13 | location_-_purpose_value | nvarchar | YES | 255 |
| 14 | last_week_exp.rig_on_location_sap_data | nvarchar | YES | 255 |
| 15 | latest_exp.rig_on_location_sap_data | nvarchar | YES | 255 |
| 16 | exp.rig_off_location_sap_data | nvarchar | YES | 255 |
| 17 | date_-_material_po_placed | nvarchar | YES | 255 |
| 18 | date_-_material_available_at_site | nvarchar | YES | 255 |
| 19 | scr_no | nvarchar | YES | 255 |
| 20 | scr_date | nvarchar | YES | 255 |
| 21 | moc_raised | nvarchar | YES | 255 |
| 22 | moc_approved | nvarchar | YES | 255 |
| 23 | buffer_status | nvarchar | YES | 255 |
| 24 | actual_pegged_date | nvarchar | YES | 255 |
| 25 | last_week_cum_progress | nvarchar | YES | 255 |
| 26 | cum_progress_for_this_week | nvarchar | YES | 255 |
| 27 | actual_start_date | nvarchar | YES | 255 |
| 28 | actual_date_odc_requested_field_programmer_oso33x_for_esp_pcp_surface_cables | nvarchar | YES | 255 |
| 29 | date_oso33x_call_out_for_cable_installation_to_pcp_esp_vendor | nvarchar | YES | 255 |
| 30 | delivery_of_esp_pcp_surface_cable_by_field_programmer_oso33x | nvarchar | YES | 255 |
| 31 | installation_of_esp_pcp_surface_cable_by_vendors | nvarchar | YES | 255 |
| 32 | actual_finish_date | nvarchar | YES | 255 |
| 33 | flaf_issue_date | nvarchar | YES | 255 |
| 34 | ramz_id | nvarchar | YES | 255 |
| 35 | ramz_id_received_date_same_day_as_flaf_issue_date | nvarchar | YES | 255 |
| 36 | date_of_site_survey_report_issuance | nvarchar | YES | 255 |
| 37 | well_engineer_to_add_location_name_in_edm | nvarchar | YES | 255 |
| 38 | pt_to_request_for_esp_preliminary_design_through_ald | nvarchar | YES | 255 |
| 39 | actual_date_odc_requested_field_programmer_oso33x_to_install_esp_pcp_skid | nvarchar | YES | 255 |
| 40 | actual_date_field_programmer_oso33x_requested_esp_pcp_vendor_to_install_the_skid | nvarchar | YES | 255 |
| 41 | actual_date_pcp_esp_vendor_delivered_the_skid | nvarchar | YES | 255 |
| 42 | actual_installation_date_by_vendor_of_esp/pcp_skid | nvarchar | YES | 255 |
| 43 | flow_line_po_no | nvarchar | YES | 255 |
| 44 | f_l_po_recd._date | nvarchar | YES | 255 |
| 45 | flowline_-_purpose_value | nvarchar | YES | 255 |
| 46 | station_name_no | nvarchar | YES | 255 |
| 47 | physical_tie_in_port_number | nvarchar | YES | 255 |
| 48 | date_of_tie_in_port_readiness | nvarchar | YES | 255 |
| 49 | physical_tie_in_port_available_when_flaf_issued | nvarchar | YES | 255 |
| 50 | engineering_actual_start_date | nvarchar | YES | 255 |
| 51 | engineering_actual_finish_date | nvarchar | YES | 255 |
| 52 | progress | nvarchar | YES | 255 |
| 53 | fl_dia | nvarchar | YES | 255 |
| 54 | fl_length_meter | nvarchar | YES | 255 |
| 55 | const._actual_start_date | nvarchar | YES | 255 |
| 56 | const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date | nvarchar | YES | 255 |
| 57 | flowline_construction_progress | nvarchar | YES | 255 |
| 58 | ohl_length_meter | nvarchar | YES | 255 |
| 59 | ohl_progress | nvarchar | YES | 255 |
| 60 | ohl_completion_date | nvarchar | YES | 255 |
| 61 | z6_data_submitted_date | nvarchar | YES | 255 |
| 62 | sap_notification_received_date_z6_2_days_before_eng._completion | nvarchar | YES | 255 |
| 63 | actual_rig_on_date | nvarchar | YES | 255 |
| 64 | actual_rig_off_date | nvarchar | YES | 255 |
| 65 | wlctf_acceptanceapproval_from_production | nvarchar | YES | 255 |
| 66 | actual_hoist_fbu_rsr_on_date | nvarchar | YES | 255 |
| 67 | actual_hoist_fbu_rsr_off_date | nvarchar | YES | 255 |
| 68 | wellpad_handover-2_from_hoist_fbu_rsr_off_date | nvarchar | YES | 255 |
| 69 | completion_type_rig_fbu_or_rsr_hoist | nvarchar | YES | 255 |
| 70 | actual_eng._completion_date | nvarchar | YES | 255 |
| 71 | actual_comm._start_date | nvarchar | YES | 255 |
| 72 | actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date | nvarchar | YES | 255 |
| 73 | engg_kpi_after_rig-off_days | nvarchar | YES | 255 |
| 74 | data_error | nvarchar | YES | 255 |
| 75 | reason_if_kpi_not_met | nvarchar | YES | 255 |
| 76 | remark_status_area_of_attention_issues_ | nvarchar | YES | 255 |
| 77 | rlmu_submitted_to_ho-date_with_in_7_days_from_actual_comm. | nvarchar | YES | 255 |
| 78 | flow_line_test_pack_completion_doc._submission_date_to_qs_dept. | nvarchar | YES | 255 |
| 79 | flow_line_test_pack_completion_progress | nvarchar | YES | 255 |
| 80 | over_all_progress_percentages | nvarchar | YES | 255 |
| 81 | ssfd_wells | nvarchar | YES | 255 |
| 82 | ipm | nvarchar | YES | 255 |
| 83 | access_road_5 | nvarchar | YES | 255 |
| 84 | earth_work_60 | nvarchar | YES | 255 |
| 85 | cellar_20 | nvarchar | YES | 255 |
| 86 | beam_pump_base_esp_pcp_foundation_5 | nvarchar | YES | 255 |
| 87 | earthing_1 | nvarchar | YES | 255 |
| 88 | septic_tank_1 | nvarchar | YES | 255 |
| 89 | water_2 | nvarchar | YES | 255 |
| 90 | waste_water_2 | nvarchar | YES | 255 |
| 91 | hdpe_liner_instalat_4 | nvarchar | YES | 255 |
| 92 | overall_loc._preparation_10_100 | nvarchar | YES | 255 |
| 93 | site_survey_5 | nvarchar | YES | 255 |
| 94 | survey_report_issue_5 | nvarchar | YES | 255 |
| 95 | design_sta_5 | nvarchar | YES | 255 |
| 96 | design_completed_issue_for_ta2_5_40 | nvarchar | YES | 255 |
| 97 | approved_by_15 | nvarchar | YES | 255 |
| 98 | afc_3_30 | nvarchar | YES | 255 |
| 99 | overall_engg._10_100 | nvarchar | YES | 255 |
| 100 | piping_mech_50 | nvarchar | YES | 255 |
| 101 | elect_30 | nvarchar | YES | 255 |
| 102 | instr_20 | nvarchar | YES | 255 |
| 103 | overall_material_10_100 | nvarchar | YES | 255 |
| 104 | cold_b_2 | nvarchar | YES | 255 |
| 105 | sleeper_pre_cast_ins_15 | nvarchar | YES | 255 |
| 106 | cs_pipe_welding_ndt_10_rt_for_op_100_for_60 | nvarchar | YES | 255 |
| 107 | pe_fussion_pull_20 | nvarchar | YES | 255 |
| 108 | final_hydro_t_3 | nvarchar | YES | 255 |
| 109 | overall_const._10_100 | nvarchar | YES | 255 |
| 110 | pole_hole_drill_40 | nvarchar | YES | 255 |
| 111 | pole_erect_40 | nvarchar | YES | 255 |
| 112 | conductor_string_18 | nvarchar | YES | 255 |
| 113 | ohl_ti_2 | nvarchar | YES | 255 |
| 114 | overall_ohl_progr_100 | nvarchar | YES | 255 |
| 115 | mechani_60 | nvarchar | YES | 255 |
| 116 | electri_15 | nvarchar | YES | 255 |
| 117 | instrumentat_20 | nvarchar | YES | 255 |
| 118 | overall_comm_mi_5 | nvarchar | YES | 255 |
| 119 | overall_comm_progress_100 | nvarchar | YES | 255 |
| 120 | location_preparation_status_in_progress_completed | nvarchar | YES | 255 |
| 121 | flow_line_const._status_in_progress_completed | nvarchar | YES | 255 |
| 122 | flow_line_commi._status_in_progress_completed | nvarchar | YES | 255 |
| 123 | well_year_white_space | nvarchar | YES | 255 |
| 124 | reasons_for_year_2018 | nvarchar | YES | 255 |
| 125 | column7 | nvarchar | YES | 255 |
| 126 | digital_wmr_import_remarks | nvarchar | YES | 255 |
| 127 | project_id | nvarchar | YES | 255 |
| 128 | Week_Number | nvarchar | YES | 255 |

## WellMonitoringReport
**Rows:** 268
**Columns:** 130

| # | Column | DataType | Nullable | MaxLen |
|---|--------|----------|----------|--------|
| 1 | sl_no | bigint | YES |  |
| 2 | sl_no_raw | nvarchar | YES | 255 |
| 3 | rig_no | nvarchar | YES | 255 |
| 4 | well_location | nvarchar | YES | 255 |
| 5 | well_name_after_spud | nvarchar | YES | 255 |
| 6 | pdo_well_id | nvarchar | YES | 255 |
| 7 | well_type | nvarchar | YES | 255 |
| 8 | northing | nvarchar | YES | 255 |
| 9 | easting | nvarchar | YES | 255 |
| 10 | locationdd | nvarchar | YES | 255 |
| 11 | flow_linedl | nvarchar | YES | 255 |
| 12 | location_po_no | nvarchar | YES | 255 |
| 13 | location_po_recvd_date | date | YES |  |
| 14 | location_-_purpose_value | nvarchar | YES | 255 |
| 15 | last_week_exp.rig_on_location_sap_data | date | YES |  |
| 16 | latest_exp.rig_on_location_sap_data | date | YES |  |
| 17 | exp.rig_off_location_sap_data | date | YES |  |
| 18 | date_-_material_po_placed | date | YES |  |
| 19 | date_-_material_available_at_site | date | YES |  |
| 20 | scr_no | nvarchar | YES | 255 |
| 21 | scr_date | date | YES |  |
| 22 | moc_raised | nvarchar | YES | 255 |
| 23 | moc_approved | nvarchar | YES | 255 |
| 24 | buffer_status | varchar | YES | 16 |
| 25 | actual_pegged_date | date | YES |  |
| 26 | last_week_cum_progress | decimal | YES |  |
| 27 | cum_progress_for_this_week | decimal | YES |  |
| 28 | actual_start_date | date | YES |  |
| 29 | actual_date_odc_requested_field_programmer_oso33x_for_esp_pcp_surface_cables | date | YES |  |
| 30 | date_oso33x_call_out_for_cable_installation_to_pcp_esp_vendor | date | YES |  |
| 31 | delivery_of_esp_pcp_surface_cable_by_field_programmer_oso33x | date | YES |  |
| 32 | installation_of_esp_pcp_surface_cable_by_vendors | date | YES |  |
| 33 | actual_finish_date | date | YES |  |
| 34 | flaf_issue_date | date | YES |  |
| 35 | ramz_id | nvarchar | YES | 255 |
| 36 | ramz_id_received_date_same_day_as_flaf_issue_date | date | YES |  |
| 37 | date_of_site_survey_report_issuance | date | YES |  |
| 38 | well_engineer_to_add_location_name_in_edm | nvarchar | YES | 255 |
| 39 | pt_to_request_for_esp_preliminary_design_through_ald | nvarchar | YES | 255 |
| 40 | actual_date_odc_requested_field_programmer_oso33x_to_install_esp_pcp_skid | date | YES |  |
| 41 | actual_date_field_programmer_oso33x_requested_esp_pcp_vendor_to_install_the_skid | date | YES |  |
| 42 | actual_date_pcp_esp_vendor_delivered_the_skid | date | YES |  |
| 43 | actual_installation_date_by_vendor_of_esp/pcp_skid | date | YES |  |
| 44 | flow_line_po_no | nvarchar | YES | 255 |
| 45 | f_l_po_recd._date | date | YES |  |
| 46 | flowline_-_purpose_value | nvarchar | YES | 255 |
| 47 | station_name_no | nvarchar | YES | 255 |
| 48 | physical_tie_in_port_number | nvarchar | YES | 255 |
| 49 | date_of_tie_in_port_readiness | date | YES |  |
| 50 | physical_tie_in_port_available_when_flaf_issued | nvarchar | YES | 255 |
| 51 | engineering_actual_start_date | date | YES |  |
| 52 | engineering_actual_finish_date | date | YES |  |
| 53 | progress | decimal | YES |  |
| 54 | fl_dia | nvarchar | YES | 255 |
| 55 | fl_length_meter | nvarchar | YES | 255 |
| 56 | const._actual_start_date | date | YES |  |
| 57 | const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date | date | YES |  |
| 58 | flowline_construction_progress | decimal | YES |  |
| 59 | ohl_length_meter | nvarchar | YES | 255 |
| 60 | ohl_progress | decimal | YES |  |
| 61 | ohl_completion_date | date | YES |  |
| 62 | z6_data_submitted_date | date | YES |  |
| 63 | sap_notification_received_date_z6_2_days_before_eng._completion | date | YES |  |
| 64 | actual_rig_on_date | date | YES |  |
| 65 | actual_rig_off_date | date | YES |  |
| 66 | wlctf_acceptanceapproval_from_production | date | YES |  |
| 67 | actual_hoist_fbu_rsr_on_date | date | YES |  |
| 68 | actual_hoist_fbu_rsr_off_date | date | YES |  |
| 69 | wellpad_handover-2_from_hoist_fbu_rsr_off_date | date | YES |  |
| 70 | completion_type_rig_fbu_or_rsr_hoist | nvarchar | YES | 510 |
| 71 | actual_eng._completion_date | date | YES |  |
| 72 | actual_comm._start_date | date | YES |  |
| 73 | actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date | date | YES |  |
| 74 | engg_kpi_after_rig-off_days | int | YES |  |
| 75 | data_error | varchar | YES | 5 |
| 76 | reason_if_kpi_not_met | nvarchar | YES | 255 |
| 77 | remark_status_area_of_attention_issues_ | nvarchar | YES | 255 |
| 78 | rlmu_submitted_to_ho-date_with_in_7_days_from_actual_comm. | date | YES |  |
| 79 | flow_line_test_pack_completion_doc._submission_date_to_qs_dept. | date | YES |  |
| 80 | flow_line_test_pack_completion_progress | decimal | YES |  |
| 81 | over_all_progress_percentages | decimal | YES |  |
| 82 | ssfd_wells | nvarchar | YES | 255 |
| 83 | ipm | nvarchar | YES | 255 |
| 84 | access_road_5 | decimal | YES |  |
| 85 | earth_work_60 | decimal | YES |  |
| 86 | cellar_20 | decimal | YES |  |
| 87 | beam_pump_base_esp_pcp_foundation_5 | decimal | YES |  |
| 88 | earthing_1 | decimal | YES |  |
| 89 | septic_tank_1 | decimal | YES |  |
| 90 | water_2 | decimal | YES |  |
| 91 | waste_water_2 | decimal | YES |  |
| 92 | hdpe_liner_instalat_4 | decimal | YES |  |
| 93 | overall_loc._preparation_10_100 | decimal | YES |  |
| 94 | site_survey_5 | decimal | YES |  |
| 95 | survey_report_issue_5 | decimal | YES |  |
| 96 | design_sta_5 | decimal | YES |  |
| 97 | design_completed_issue_for_ta2_5_40 | decimal | YES |  |
| 98 | approved_by_15 | decimal | YES |  |
| 99 | afc_3_30 | decimal | YES |  |
| 100 | overall_engg._10_100 | decimal | YES |  |
| 101 | piping_mech_50 | decimal | YES |  |
| 102 | elect_30 | decimal | YES |  |
| 103 | instr_20 | decimal | YES |  |
| 104 | overall_material_10_100 | decimal | YES |  |
| 105 | cold_b_2 | decimal | YES |  |
| 106 | sleeper_pre_cast_ins_15 | decimal | YES |  |
| 107 | cs_pipe_welding_ndt_10_rt_for_op_100_for_60 | decimal | YES |  |
| 108 | pe_fussion_pull_20 | decimal | YES |  |
| 109 | final_hydro_t_3 | decimal | YES |  |
| 110 | overall_const._10_100 | decimal | YES |  |
| 111 | pole_hole_drill_40 | decimal | YES |  |
| 112 | pole_erect_40 | decimal | YES |  |
| 113 | conductor_string_18 | decimal | YES |  |
| 114 | ohl_ti_2 | decimal | YES |  |
| 115 | overall_ohl_progr_100 | decimal | YES |  |
| 116 | mechani_60 | decimal | YES |  |
| 117 | electri_15 | decimal | YES |  |
| 118 | instrumentat_20 | decimal | YES |  |
| 119 | overall_comm_mi_5 | decimal | YES |  |
| 120 | overall_comm_progress_100 | decimal | YES |  |
| 121 | location_preparation_status_in_progress_completed | nvarchar | YES | 255 |
| 122 | flow_line_const._status_in_progress_completed | nvarchar | YES | 255 |
| 123 | flow_line_commi._status_in_progress_completed | nvarchar | YES | 255 |
| 124 | well_year_white_space | nvarchar | YES | 255 |
| 125 | reasons_for_year_2018 | nvarchar | YES | 255 |
| 126 | column7 | nvarchar | YES | 255 |
| 127 | digital_wmr_import_remarks | nvarchar | YES | 255 |
| 128 | project_id | nvarchar | YES | 255 |
| 129 | Week_Number | date | YES |  |
| 130 | Cluster | nvarchar | YES | 50 |

## WellMonitoringReport_Latest
**Rows:** 169
**Columns:** 130

| # | Column | DataType | Nullable | MaxLen |
|---|--------|----------|----------|--------|
| 1 | sl_no | bigint | YES |  |
| 2 | sl_no_raw | nvarchar | YES | 255 |
| 3 | rig_no | nvarchar | YES | 255 |
| 4 | well_location | nvarchar | YES | 255 |
| 5 | well_name_after_spud | nvarchar | YES | 255 |
| 6 | pdo_well_id | nvarchar | YES | 255 |
| 7 | well_type | nvarchar | YES | 255 |
| 8 | northing | nvarchar | YES | 255 |
| 9 | easting | nvarchar | YES | 255 |
| 10 | locationdd | nvarchar | YES | 255 |
| 11 | flow_linedl | nvarchar | YES | 255 |
| 12 | location_po_no | nvarchar | YES | 255 |
| 13 | location_po_recvd_date | date | YES |  |
| 14 | location_-_purpose_value | nvarchar | YES | 255 |
| 15 | last_week_exp.rig_on_location_sap_data | date | YES |  |
| 16 | latest_exp.rig_on_location_sap_data | date | YES |  |
| 17 | exp.rig_off_location_sap_data | date | YES |  |
| 18 | date_-_material_po_placed | date | YES |  |
| 19 | date_-_material_available_at_site | date | YES |  |
| 20 | scr_no | nvarchar | YES | 255 |
| 21 | scr_date | date | YES |  |
| 22 | moc_raised | nvarchar | YES | 255 |
| 23 | moc_approved | nvarchar | YES | 255 |
| 24 | buffer_status | varchar | YES | 16 |
| 25 | actual_pegged_date | date | YES |  |
| 26 | last_week_cum_progress | decimal | YES |  |
| 27 | cum_progress_for_this_week | decimal | YES |  |
| 28 | actual_start_date | date | YES |  |
| 29 | actual_date_odc_requested_field_programmer_oso33x_for_esp_pcp_surface_cables | date | YES |  |
| 30 | date_oso33x_call_out_for_cable_installation_to_pcp_esp_vendor | date | YES |  |
| 31 | delivery_of_esp_pcp_surface_cable_by_field_programmer_oso33x | date | YES |  |
| 32 | installation_of_esp_pcp_surface_cable_by_vendors | date | YES |  |
| 33 | actual_finish_date | date | YES |  |
| 34 | flaf_issue_date | date | YES |  |
| 35 | ramz_id | nvarchar | YES | 255 |
| 36 | ramz_id_received_date_same_day_as_flaf_issue_date | date | YES |  |
| 37 | date_of_site_survey_report_issuance | date | YES |  |
| 38 | well_engineer_to_add_location_name_in_edm | nvarchar | YES | 255 |
| 39 | pt_to_request_for_esp_preliminary_design_through_ald | nvarchar | YES | 255 |
| 40 | actual_date_odc_requested_field_programmer_oso33x_to_install_esp_pcp_skid | date | YES |  |
| 41 | actual_date_field_programmer_oso33x_requested_esp_pcp_vendor_to_install_the_skid | date | YES |  |
| 42 | actual_date_pcp_esp_vendor_delivered_the_skid | date | YES |  |
| 43 | actual_installation_date_by_vendor_of_esp/pcp_skid | date | YES |  |
| 44 | flow_line_po_no | nvarchar | YES | 255 |
| 45 | f_l_po_recd._date | date | YES |  |
| 46 | flowline_-_purpose_value | nvarchar | YES | 255 |
| 47 | station_name_no | nvarchar | YES | 255 |
| 48 | physical_tie_in_port_number | nvarchar | YES | 255 |
| 49 | date_of_tie_in_port_readiness | date | YES |  |
| 50 | physical_tie_in_port_available_when_flaf_issued | nvarchar | YES | 255 |
| 51 | engineering_actual_start_date | date | YES |  |
| 52 | engineering_actual_finish_date | date | YES |  |
| 53 | progress | decimal | YES |  |
| 54 | fl_dia | nvarchar | YES | 255 |
| 55 | fl_length_meter | nvarchar | YES | 255 |
| 56 | const._actual_start_date | date | YES |  |
| 57 | const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date | date | YES |  |
| 58 | flowline_construction_progress | decimal | YES |  |
| 59 | ohl_length_meter | nvarchar | YES | 255 |
| 60 | ohl_progress | decimal | YES |  |
| 61 | ohl_completion_date | date | YES |  |
| 62 | z6_data_submitted_date | date | YES |  |
| 63 | sap_notification_received_date_z6_2_days_before_eng._completion | date | YES |  |
| 64 | actual_rig_on_date | date | YES |  |
| 65 | actual_rig_off_date | date | YES |  |
| 66 | wlctf_acceptanceapproval_from_production | date | YES |  |
| 67 | actual_hoist_fbu_rsr_on_date | date | YES |  |
| 68 | actual_hoist_fbu_rsr_off_date | date | YES |  |
| 69 | wellpad_handover-2_from_hoist_fbu_rsr_off_date | date | YES |  |
| 70 | completion_type_rig_fbu_or_rsr_hoist | nvarchar | YES | 510 |
| 71 | actual_eng._completion_date | date | YES |  |
| 72 | actual_comm._start_date | date | YES |  |
| 73 | actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date | date | YES |  |
| 74 | engg_kpi_after_rig-off_days | int | YES |  |
| 75 | data_error | varchar | YES | 5 |
| 76 | reason_if_kpi_not_met | nvarchar | YES | 255 |
| 77 | remark_status_area_of_attention_issues_ | nvarchar | YES | 255 |
| 78 | rlmu_submitted_to_ho-date_with_in_7_days_from_actual_comm. | date | YES |  |
| 79 | flow_line_test_pack_completion_doc._submission_date_to_qs_dept. | date | YES |  |
| 80 | flow_line_test_pack_completion_progress | decimal | YES |  |
| 81 | over_all_progress_percentages | decimal | YES |  |
| 82 | ssfd_wells | nvarchar | YES | 255 |
| 83 | ipm | nvarchar | YES | 255 |
| 84 | access_road_5 | decimal | YES |  |
| 85 | earth_work_60 | decimal | YES |  |
| 86 | cellar_20 | decimal | YES |  |
| 87 | beam_pump_base_esp_pcp_foundation_5 | decimal | YES |  |
| 88 | earthing_1 | decimal | YES |  |
| 89 | septic_tank_1 | decimal | YES |  |
| 90 | water_2 | decimal | YES |  |
| 91 | waste_water_2 | decimal | YES |  |
| 92 | hdpe_liner_instalat_4 | decimal | YES |  |
| 93 | overall_loc._preparation_10_100 | decimal | YES |  |
| 94 | site_survey_5 | decimal | YES |  |
| 95 | survey_report_issue_5 | decimal | YES |  |
| 96 | design_sta_5 | decimal | YES |  |
| 97 | design_completed_issue_for_ta2_5_40 | decimal | YES |  |
| 98 | approved_by_15 | decimal | YES |  |
| 99 | afc_3_30 | decimal | YES |  |
| 100 | overall_engg._10_100 | decimal | YES |  |
| 101 | piping_mech_50 | decimal | YES |  |
| 102 | elect_30 | decimal | YES |  |
| 103 | instr_20 | decimal | YES |  |
| 104 | overall_material_10_100 | decimal | YES |  |
| 105 | cold_b_2 | decimal | YES |  |
| 106 | sleeper_pre_cast_ins_15 | decimal | YES |  |
| 107 | cs_pipe_welding_ndt_10_rt_for_op_100_for_60 | decimal | YES |  |
| 108 | pe_fussion_pull_20 | decimal | YES |  |
| 109 | final_hydro_t_3 | decimal | YES |  |
| 110 | overall_const._10_100 | decimal | YES |  |
| 111 | pole_hole_drill_40 | decimal | YES |  |
| 112 | pole_erect_40 | decimal | YES |  |
| 113 | conductor_string_18 | decimal | YES |  |
| 114 | ohl_ti_2 | decimal | YES |  |
| 115 | overall_ohl_progr_100 | decimal | YES |  |
| 116 | mechani_60 | decimal | YES |  |
| 117 | electri_15 | decimal | YES |  |
| 118 | instrumentat_20 | decimal | YES |  |
| 119 | overall_comm_mi_5 | decimal | YES |  |
| 120 | overall_comm_progress_100 | decimal | YES |  |
| 121 | location_preparation_status_in_progress_completed | nvarchar | YES | 255 |
| 122 | flow_line_const._status_in_progress_completed | nvarchar | YES | 255 |
| 123 | flow_line_commi._status_in_progress_completed | nvarchar | YES | 255 |
| 124 | well_year_white_space | nvarchar | YES | 255 |
| 125 | reasons_for_year_2018 | nvarchar | YES | 255 |
| 126 | column7 | nvarchar | YES | 255 |
| 127 | digital_wmr_import_remarks | nvarchar | YES | 255 |
| 128 | project_id | nvarchar | YES | 255 |
| 129 | Week_Number | date | YES |  |
| 130 | Cluster | nvarchar | YES | 50 |

## task_daily
**Rows:** 35394
**Columns:** 43

| # | Column | DataType | Nullable | MaxLen |
|---|--------|----------|----------|--------|
| 1 | id | bigint | NO |  |
| 2 | ActionOn | date | NO |  |
| 3 | task_code | nvarchar | YES | 100 |
| 4 | schedule_id | bigint | YES |  |
| 5 | project_id | uniqueidentifier | YES |  |
| 6 | required | decimal | YES |  |
| 7 | planned | decimal | YES |  |
| 8 | duration | decimal | YES |  |
| 9 | remaining_duration | decimal | YES |  |
| 10 | progress | decimal | YES |  |
| 11 | ready | bit | YES |  |
| 12 | completed | bit | YES |  |
| 13 | plan | bit | YES |  |
| 14 | committed_start | date | YES |  |
| 15 | committed_end | date | YES |  |
| 16 | target_start | date | YES |  |
| 17 | target_end | date | YES |  |
| 18 | actual_start | date | YES |  |
| 19 | actual_end | date | YES |  |
| 20 | startDate | date | YES |  |
| 21 | endDate | date | YES |  |
| 22 | crew_type | nvarchar | YES | 50 |
| 23 | crew_code | nvarchar | YES | 100 |
| 24 | planned_crew | nvarchar | YES | 100 |
| 25 | well_id | nvarchar | YES | 50 |
| 26 | task_uom | nvarchar | YES | 50 |
| 27 | data_hours | decimal | YES |  |
| 28 | data_qty | decimal | YES |  |
| 29 | data_employees | nvarchar | YES | -1 |
| 30 | task_assignee | nvarchar | YES | 255 |
| 31 | supervisor_email | nvarchar | YES | 255 |
| 32 | url | nvarchar | YES | 2048 |
| 33 | task_data | nvarchar | YES | -1 |
| 34 | daily_data | nvarchar | YES | -1 |
| 35 | created_at | datetime2 | YES |  |
| 36 | updated_at | datetime2 | YES |  |
| 37 | daily_ph_name | nvarchar | YES | 255 |
| 38 | daily_equipment_ids | nvarchar | YES | 255 |
| 39 | daily_employee_ids | nvarchar | YES | -1 |
| 40 | daily_actual_quantity | decimal | YES |  |
| 41 | daily_actual_hours | decimal | YES |  |
| 42 | daily_completed | bit | YES |  |
| 43 | time_stamp | nvarchar | YES | 255 |

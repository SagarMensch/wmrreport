# Database Schema Dump (AppMasterDB)

## Table: `WellMonitoringReport_Latest`

| Column Name |
|---|
| sl_no |
| sl_no_raw |
| rig_no |
| well_location |
| well_name_after_spud |
| pdo_well_id |
| well_type |
| northing |
| easting |
| locationdd |
| flow_linedl |
| location_po_no |
| location_po_recvd_date |
| location_purpose_value |
| last_week_exp_rig_on_location_sap_data |
| latest_exp_rig_on_location_sap_data |
| exp.rig_off_location_sap_data |
| date_material_po_placed |
| date_material_available_at_site |
| scr_no |
| scr_date |
| moc_raised |
| moc_approved |
| buffer_status |
| actual_pegged_date |
| last_week_cum_progress |
| cum_progress_for_this_week |
| actual_start_date |
| actual_date_odc_requested_field_programmer_oso33x_for_esp_pcp_surface_cables |
| date_oso33x_call_out_for_cable_installation_to_pcp_esp_vendor |
| delivery_of_esp_pcp_surface_cable_by_field_programmer_oso33x |
| installation_of_esp_pcp_surface_cable_by_vendors |
| actual_finish_date |
| flaf_issue_date |
| ramz_id |
| ramz_id_received_date_same_day_as_flaf_issue_date |
| date_of_site_survey_report_issuance |
| well_engineer_to_add_location_name_in_edm |
| pt_to_request_for_esp_preliminary_design_through_ald |
| actual_date_odc_requested_field_programmer_oso33x_to_install_esp_pcp_skid |
| actual_date_field_programmer_oso33x_requested_esp_pcp_vendor_to_install_the_skid |
| actual_date_pcp_esp_vendor_delivered_the_skid |
| actual_installation_date_by_vendor_of_esp_pcp_skid |
| flow_line_po_no |
| f_l_po_recd_date |
| flowline_purpose_value |
| station_name_no |
| physical_tie_in_port_number |
| date_of_tie_in_port_readiness |
| physical_tie_in_port_available_when_flaf_issued |
| engineering_actual_start_date |
| engineering_actual_finish_date |
| progress |
| fl_dia |
| fl_length_meter |
| const_actual_start_date |
| const_complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date |
| flowline_construction_progress |
| ohl_length_meter |
| ohl_progress |
| ohl_completion_date |
| z6_data_submitted_date |
| sap_notification_received_date_z6_2_days_before_eng_completion |
| actual_rig_on_date |
| actual_rig_off_date |
| wlctf_acceptanceapproval_from_production |
| actual_hoist_fbu_rsr_on_date |
| actual_hoist_fbu_rsr_off_date |
| wellpad_handover_2_from_hoist_fbu_rsr_off_date |
| completion_type_rig_fbu_or_rsr_hoist |
| actual_eng_completion_date |
| actual_comm_start_date |
| actual_comm_finish_date_with_in_2_days_from_actual_engg_completion_date |
| engg_kpi_after_rig-off_days |
| data_error |
| reason_if_kpi_not_met |
| remark_status_area_of_attention_issues |
| rlmu_submitted_to_ho_date_with_in_7_days_from_actual_comm |
| flow_line_test_pack_completion_doc_submission_date_to_qs_dept |
| flow_line_test_pack_completion_progress |
| over_all_progress_percentages |
| ssfd_wells |
| ipm |
| access_road_5 |
| earth_work_60 |
| cellar_20 |
| beam_pump_base_esp_pcp_foundation_5 |
| earthing_1 |
| septic_tank_1 |
| water_2 |
| waste_water_2 |
| hdpe_liner_instalat_4 |
| overall_loc._preparation_10_100 |
| site_survey_5 |
| survey_report_issue_5 |
| design_sta_5 |
| design_completed_issue_for_ta2_5_40 |
| approved_by_15 |
| afc_3_30 |
| overall_engg_10_100 |
| piping_mech_50 |
| elect_30 |
| instr_20 |
| overall_material_10_100 |
| cold_b_2 |
| sleeper_pre_cast_ins_15 |
| cs_pipe_welding_ndt_10_rt_for_op_100_for_60 |
| pe_fussion_pull_20 |
| final_hydro_t_3 |
| overall_const._10_100 |
| pole_hole_drill_40 |
| pole_erect_40 |
| conductor_string_18 |
| ohl_ti_2 |
| overall_ohl_progr_100 |
| mechani_60 |
| electri_15 |
| instrumentat_20 |
| overall_comm_mi_5 |
| overall_comm_progress_100 |
| location_preparation_status_in_progress_completed |
| flow_line_const_status_in_progress_completed |
| flow_line_commi_status_in_progress_completed |
| well_year_white_space |
| reasons_for_year_2018 |
| column7 |
| digital_wmr_import_remarks |
| project_id |
| Week_Number |
| Cluster |


## Table: `Job_Progress_Report_GB`

| Column Name |
|---|
| Sl.No |
| Category |
| Well ID |
| Well Name / Project Name |
| PO No |
| WBS No |
| Cum-Prior Month Actual % |
| Week-1 Plan % |
| Week-1 Actual % |
| Week-2 Plan % |
| Week-2 Actual % |
| Week-3 Plan % |
| Week-3 Actual % |
| Week-4 Plan % |
| Week-4 Actual % |
| Week-5 Plan % |
| Week-5 Actual % |
| Current Month Plan % |
| Current Month Actual % |
| Cum-Current Month Plan % |
| Cum-Current Month Actual % |
| Target End |
| Purpose Value |
| Cum-Prior Month Plan |
| Cum-Prior Month Actual |
| Current month Plan |
| Current Month Actual |
| Cum - Current Month Plan |
| Cum - Current Month Actual |
| Remarks |


## Table: `Job_Progress_PlanSnapshot`

**Error accessing table:** ('42S02', "[42S02] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]Invalid object name 'Job_Progress_PlanSnapshot'. (208) (SQLExecDirectW)")


## Table: `PH_PRODUCTIVITY_WEEKLY_REPORT`

| Column Name |
|---|
| S_No |
| Month |
| Year |
| MonthStart |
| PA_Name |
| PH_Emp_ID |
| PH_Name |
| ATNM_Sub_Contractor |
| Category |
| Crew_Type |
| Crew_Discipline |
| Crew_Name |
| Average_Productivity |
| W1_PI_CMR |
| W1_PI_T_Wise |
| W2_PI_CMR |
| W2_PI_T_Wise |
| W3_PI_CMR |
| W3_PI_T_Wise |
| W4_PI_CMR |
| W4_PI_T_Wise |
| W5_PI_CMR |
| W5_PI_T_Wise |
| Month_PI_CMR |
| Month_PI_T_Wise |


## Table: `Survival_Predictions`

| Column Name |
|---|
| well_project_key |
| duration |
| event |
| max_progress |
| last_progress |
| rig_no |
| well_type |
| project_id |
| northing |
| easting |
| engg_kpi |
| loc_prep |
| const_progress |
| progress_velocity |
| remaining |
| predicted_completion_week |
| weeks_remaining_predicted |
| predicted_completion_date |
| completion_week_p25 |
| completion_week_p75 |
| completion_date_early |
| completion_date_late |


## Table: `Risk_Scores`

| Column Name |
|---|
| sl_no |
| rig_no |
| well_location |
| well_name_after_spud |
| pdo_well_id |
| well_type |
| northing |
| easting |
| locationdd |
| flow_linedl |
| location_po_no |
| location_po_recvd_date |
| location_-_purpose_value |
| last_week_exp.rig_on_location_sap_data |
| latest_exp.rig_on_location_sap_data |
| exp.rig_off_location_sap_data |
| date_-_material_po_placed |
| date_-_material_available_at_site |
| scr_no |
| scr_date |
| moc_raised |
| moc_approved |
| buffer_status |
| actual_pegged_date |
| last_week_cum_progress |
| cum_progress_for_this_week |
| actual_start_date |
| actual_date_odc_requested_field_programmer_oso33x_for_esp_pcp_surface_cables |
| date_oso33x_call_out_for_cable_installation_to_pcp_esp_vendor |
| delivery_of_esp_pcp_surface_cable_by_field_programmer_oso33x |
| installation_of_esp_pcp_surface_cable_by_vendors |
| actual_finish_date |
| flaf_issue_date |
| ramz_id |
| ramz_id_received_date_same_day_as_flaf_issue_date |
| date_of_site_survey_report_issuance |
| well_engineer_to_add_location_name_in_edm |
| pt_to_request_for_esp_preliminary_design_through_ald |
| actual_date_odc_requested_field_programmer_oso33x_to_install_esp_pcp_skid |
| actual_date_field_programmer_oso33x_requested_esp_pcp_vendor_to_install_the_skid |
| actual_date_pcp_esp_vendor_delivered_the_skid |
| actual_installation_date_by_vendor_of_esp/pcp_skid |
| flow_line_po_no |
| f_l_po_recd._date |
| flowline_-_purpose_value |
| station_name_no |
| physical_tie_in_port_number |
| date_of_tie_in_port_readiness |
| physical_tie_in_port_available_when_flaf_issued |
| engineering_actual_start_date |
| engineering_actual_finish_date |
| progress |
| fl_dia |
| fl_length_meter |
| const._actual_start_date |
| const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date |
| flowline_construction_progress |
| ohl_length_meter |
| ohl_progress |
| ohl_completion_date |
| z6_data_submitted_date |
| sap_notification_received_date_z6_2_days_before_eng._completion |
| actual_rig_on_date |
| actual_rig_off_date |
| wlctf_acceptanceapproval_from_production |
| actual_hoist_fbu_rsr_on_date |
| actual_hoist_fbu_rsr_off_date |
| wellpad_handover-2_from_hoist_fbu_rsr_off_date |
| completion_type_rig_fbu_or_rsr_hoist |
| actual_eng._completion_date |
| actual_comm._start_date |
| actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date |
| engg_kpi_after_rig-off_days |
| data_error |
| reason_if_kpi_not_met |
| remark_status_area_of_attention_issues_ |
| rlmu_submitted_to_ho-date_with_in_7_days_from_actual_comm. |
| flow_line_test_pack_completion_doc._submission_date_to_qs_dept. |
| flow_line_test_pack_completion_progress |
| over_all_progress_percentages |
| ssfd_wells |
| ipm |
| access_road_5 |
| earth_work_60 |
| cellar_20 |
| beam_pump_base_esp_pcp_foundation_5 |
| earthing_1 |
| septic_tank_1 |
| water_2 |
| waste_water_2 |
| hdpe_liner_instalat_4 |
| overall_loc._preparation_10_100 |
| site_survey_5 |
| survey_report_issue_5 |
| design_sta_5 |
| design_completed_issue_for_ta2_5_40 |
| approved_by_15 |
| afc_3_30 |
| overall_engg._10_100 |
| piping_mech_50 |
| elect_30 |
| instr_20 |
| overall_material_10_100 |
| cold_b_2 |
| sleeper_pre_cast_ins_15 |
| cs_pipe_welding_ndt_10_rt_for_op_100_for_60 |
| pe_fussion_pull_20 |
| final_hydro_t_3 |
| overall_const._10_100 |
| pole_hole_drill_40 |
| pole_erect_40 |
| conductor_string_18 |
| ohl_ti_2 |
| overall_ohl_progr_100 |
| mechani_60 |
| electri_15 |
| instrumentat_20 |
| overall_comm_mi_5 |
| overall_comm_progress_100 |
| location_preparation_status_in_progress_completed |
| flow_line_const._status_in_progress_completed |
| flow_line_commi._status_in_progress_completed |
| well_year_white_space |
| reasons_for_year_2018 |
| column7 |
| digital_wmr_import_remarks |
| project_id |
| Week_Number |
| well_project_key |
| exp_rig_off |
| predicted_completion_date |
| completion_date_early |
| completion_date_late |
| weeks_remaining_predicted |
| progress_velocity |
| exp_rig_off_parsed |
| days_to_exp |
| week_number_ord |
| risk_score |
| risk_tier |


## Table: `Ag_Predictions`

| Column Name |
|---|
| target_lead_4w |
| pred_autogluon |
| residual |
| abs_error |


## Table: `WMR_Full`

| Column Name |
|---|
| pdo_well_id |
| well_name_after_spud |
| rig_no |
| well_type |
| well_location |
| over_all_progress_percentages |
| cum_progress_for_this_week |
| last_week_cum_progress |
| ohl_progress |
| flowline_construction_progress |
| overall_loc._preparation_10_100 |
| overall_engg._10_100 |
| overall_const._10_100 |
| overall_comm_progress_100 |
| actual_start_date |
| actual_finish_date |
| actual_rig_on_date |
| actual_rig_off_date |
| actual_eng._completion_date |
| actual_comm._start_date |
| actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date |
| const._actual_start_date |
| const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date |
| engineering_actual_start_date |
| engineering_actual_finish_date |
| actual_hoist_fbu_rsr_on_date |
| actual_hoist_fbu_rsr_off_date |
| wlctf_acceptanceapproval_from_production |
| flaf_issue_date |
| moc_raised |
| moc_approved |
| buffer_status |
| engg_kpi_after_rig-off_days |
| access_road_5 |
| earth_work_60 |
| cellar_20 |
| beam_pump_base_esp_pcp_foundation_5 |
| hdpe_liner_instalat_4 |
| mechani_60 |
| electri_15 |
| instrumentat_20 |
| piping_mech_50 |
| elect_30 |
| instr_20 |
| project_id |
| Week_Number |


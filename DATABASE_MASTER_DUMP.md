# ATNM_Dev Database Master Dump

## Connection Info
```
Server: 10.100.137.11
Database: ATNM_Dev
User: atnm_chatbot
Driver: ODBC Driver 18 for SQL Server
```

## Summary
- **Total Tables:** 17
- **Total Rows:** ~240K+ records
- **Key Tables for Wells:**
  - `WellMonitoringReport` (268 rows, 130 cols) - Historical well data
  - `WellMonitoringReport_Latest` (169 rows, 130 cols) - Latest snapshot
  - `WMR_Full` (18969 rows, 128 cols) - Full denormalized view

## Key Join Columns
| Column | Tables |
|--------|--------|
| `pdo_well_id` | WellMonitoringReport, WellMonitoringReport_Latest, WMR_Full |
| `Well_ID` | Job_Progress_Report_GB, Job_Progress_PlanSnapshot, task_daily, ActivityTaskPlan |
| `well_id` | Revenue, SAP_DRILLING_SEQUENCE |
| `project_id` | ActivityTaskPlan, task_daily, Job_Progress_PlanSnapshot, WBS_Master_Tracker_ |
| `rig_no` | WellMonitoringReport tables |

## Important Notes
- All WellMonitoringReport tables have `pdo_well_id` as the unique well identifier
- Use `pdo_well_id` for counting unique wells (NOT well_name_after_spud)
- Most columns in WMR tables are nvARCHAR - use TRY_CAST for numeric comparisons
- `Cluster` column exists in WellMonitoringReport for filtering by location


## ActivityTaskPlan
**Rows:** 100000
**Columns:** 38

### Schema
| Column | Type | Nullable |
|--------|------|----------|
| row_id | bigint | NO |
| source_id | nvarchar | YES |
| Data | nvarchar | YES |
| ancestor | nvarchar | YES |
| duration | nvarchar | YES |
| progress | nvarchar | YES |
| crew_uid | nvarchar | YES |
| crew_type | nvarchar | YES |
| qty | nvarchar | YES |
| manhours | nvarchar | YES |
| weightage | nvarchar | YES |
| parent | nvarchar | YES |
| start_date | datetime2 | YES |
| end_date | datetime2 | YES |
| target_start | datetime2 | YES |
| target_end | datetime2 | YES |
| actual_start | datetime2 | YES |
| actual_end | datetime2 | YES |
| qtyactual | nvarchar | YES |
| qtyforacst | nvarchar | YES |
| manhoursactual | nvarchar | YES |
| manhourforacst | nvarchar | YES |
| code | nvarchar | YES |
| text | nvarchar | YES |
| type | nvarchar | YES |
| schedule_id | nvarchar | YES |
| project_id | nvarchar | YES |
| task_assignee | nvarchar | YES |
| supervisor_email | nvarchar | YES |
| attributes | nvarchar | YES |
| remaining_duration | nvarchar | YES |
| Resume_Suspend | nvarchar | YES |
| data_nonprod | nvarchar | YES |
| created_at | datetime2 | YES |
| updated_at | datetime2 | YES |
| Well_ID | nvarchar | YES |
| Parent_WBS | nvarchar | YES |
| Time_Stamp | nvarchar | YES |

### Key Columns (for joins)
- 
- 

### Sample Data (first 3 rows)
|row_id|source_id|Data|ancestor|duration|progress|crew_uid|crew_type|qty|manhours|
|---|---|---|---|---|---|---|---|---|---|
|6463352|NULL|{"purpose_value": "1350.0", "s|181824,181822,181817,146346|19.0|0.0|||0.0|0.0|
|6463348|NULL|{"purpose_value": "450.0", "st|181821,181819,181817,146346|2.0|0.0|||1.0|3.875968992248062|
|6463344|NULL|{"purpose_value": "450.0", "st|181821,181819,181817,146346|1.0|1.0|MML_CCL0803_3ATE|LCC-0803|1.0|1.0|

---

## company_employees
**Rows:** 5549
**Columns:** 8

### Schema
| Column | Type | Nullable |
|--------|------|----------|
| id | decimal | NO |
| UId | nvarchar | NO |
| Name | nvarchar | YES |
| Status | nvarchar | YES |
| locationCode | nvarchar | YES |
| Email | nvarchar | YES |
| code | nvarchar | YES |
| company | nvarchar | YES |

### Sample Data (first 3 rows)
|id|UId|Name|Status|locationCode|Email|code|company|
|---|---|---|---|---|---|---|---|
|4809.00|113526|KAMAL AHMAD|Active|3522|mohammad.hedayatullah@altasnim|PG1232|Al Tasnim Enterprises LLC|
|4810.00|113611|BALAKRISHNAN THIAGARAJAN|Active|3526|NULL|PG1094|Al Tasnim Enterprises LLC|
|4811.00|114729|SIBY THANNICKAL PETER|Active|3525|NULL|PG1232|Al Tasnim Enterprises LLC|

---

## crews
**Rows:** 5758
**Columns:** 8

### Schema
| Column | Type | Nullable |
|--------|------|----------|
| ID | nvarchar | YES |
| Code | nvarchar | YES |
| Account | nvarchar | YES |
| Location | nvarchar | YES |
| CrewType | nvarchar | YES |
| Supervisor | nvarchar | YES |
| Employees | nvarchar | YES |
| Equipments | nvarchar | YES |

### Sample Data (first 3 rows)
|ID|Code|Account|Location|CrewType|Supervisor|Employees|Equipments|
|---|---|---|---|---|---|---|---|
|1026|NIM_CUL0604_31|367f58ab-d5e4-43ec-b5ff-ddc274|53|246|5971|[7326, 5971]|[]|
|1157|NIM_EMS0601_18|367f58ab-d5e4-43ec-b5ff-ddc274|53|159|NULL|[]|[]|
|1325|NIM_MWM0603_06|367f58ab-d5e4-43ec-b5ff-ddc274|53|200|7759|[7759]|[]|

---

## Employee
**Rows:** 5554
**Columns:** 11

### Schema
| Column | Type | Nullable |
|--------|------|----------|
| id | int | NO |
| UId | nvarchar | YES |
| Name | nvarchar | YES |
| Email | nvarchar | YES |
| Status | nvarchar | YES |
| Supervisor | int | YES |
| Account | nvarchar | YES |
| EmployeeType | int | YES |
| Company | nvarchar | YES |
| Manager | int | YES |
| Location | nvarchar | YES |

### Sample Data (first 3 rows)
|id|UId|Name|Email|Status|Supervisor|Account|EmployeeType|Company|Manager|
|---|---|---|---|---|---|---|---|---|---|
|4881|604831|ALI HAMED RASHID AL GHEILANI|NULL|Active|0|367f58ab-d5e4-43ec-b5ff-ddc274|1827|39|NULL|
|4882|604866|SARAHAN SALIM SAID AL MAMARI|NULL|Active|0|367f58ab-d5e4-43ec-b5ff-ddc274|1824|39|NULL|
|4883|604874|ABDULLAH BAKHIT SHINOON AL HAJ|NULL|Active|0|367f58ab-d5e4-43ec-b5ff-ddc274|1824|39|NULL|

---

## Job_Progress_PlanSnapshot
**Rows:** 439
**Columns:** 12

### Schema
| Column | Type | Nullable |
|--------|------|----------|
| Well_ID | nvarchar | YES |
| project_id | nvarchar | YES |
| Cum_Prior_Plan_frac | decimal | YES |
| W1_Plan_frac | decimal | YES |
| W2_Plan_frac | decimal | YES |
| W3_Plan_frac | decimal | YES |
| W4_Plan_frac | decimal | YES |
| W5_Plan_frac | decimal | YES |
| CurrentMonthPlanFrac | decimal | YES |
| CumCurrentMonthPlanFrac | decimal | YES |
| Latest_Target_End | date | YES |
| CreatedOn | datetime | NO |

### Key Columns (for joins)
- 
- 

### Sample Data (first 3 rows)
|Well_ID|project_id|Cum_Prior_Plan_frac|W1_Plan_frac|W2_Plan_frac|W3_Plan_frac|W4_Plan_frac|W5_Plan_frac|CurrentMonthPlanFrac|CumCurrentMonthPlanFrac|
|---|---|---|---|---|---|---|---|---|---|
|10207|278c5587-bba7-46ea-9c6a-d79aa8|0.05734944|0.01177941|0.01677941|0.48980603|0.14303572|0.07069444|0.73209502|0.78944446|
|10239|278c5587-bba7-46ea-9c6a-d79aa8|0E-8|0E-8|0E-8|0.17230953|0.26980159|0.12988095|0.57199208|0.57199208|
|10475|6d07e3a5-d89b-47ac-9163-8a71e8|0.19757478|0.04300214|0.02147436|0.00897436|0.00897436|0E-8|0.08242521|0.28000000|

---

## Job_Progress_Report_GB
**Rows:** 439
**Columns:** 30

### Schema
| Column | Type | Nullable |
|--------|------|----------|
| Sl.No | bigint | YES |
| Category | nvarchar | YES |
| Well ID | nvarchar | YES |
| Well Name / Project Name | nvarchar | YES |
| PO No | nvarchar | YES |
| WBS No | nvarchar | YES |
| Cum-Prior Month Actual % | decimal | YES |
| Week-1 Plan % | decimal | YES |
| Week-1 Actual % | decimal | YES |
| Week-2 Plan % | decimal | YES |
| Week-2 Actual % | decimal | YES |
| Week-3 Plan % | decimal | YES |
| Week-3 Actual % | decimal | YES |
| Week-4 Plan % | decimal | YES |
| Week-4 Actual % | decimal | YES |
| Week-5 Plan % | decimal | YES |
| Week-5 Actual % | decimal | YES |
| Current Month Plan % | decimal | YES |
| Current Month Actual % | decimal | YES |
| Cum-Current Month Plan % | decimal | YES |
| Cum-Current Month Actual % | decimal | YES |
| Target End | date | YES |
| Purpose Value | decimal | YES |
| Cum-Prior Month Plan | decimal | YES |
| Cum-Prior Month Actual | decimal | YES |
| Current month Plan | decimal | YES |
| Current Month Actual | decimal | YES |
| Cum - Current Month Plan | decimal | YES |
| Cum - Current Month Actual | decimal | YES |
| Remarks | nvarchar | YES |

### Sample Data (first 3 rows)
|Sl.No|Category|Well ID|Well Name / Project Name|PO No|WBS No|Cum-Prior Month Actual %|Week-1 Plan %|Week-1 Actual %|Week-2 Plan %|
|---|---|---|---|---|---|---|---|---|---|
|1|Marmul SNLP|628|NULL|NULL|WD-3522-24628-SNL-1-L|2.00|0.33|0.00|9.35|
|5|Marmul SNLP|729|NULL|NULL|WD-3522-27291-SNL-1-L|29.25|3.91|0.00|30.37|
|9|Marmul Conversion with Flowlin|1090|NULL|NULL|WD-3522-31090-FLC-1-L|10.85|13.70|14.17|9.01|

---

## PH_PRODUCTIVITY_WEEKLY_REPORT
**Rows:** 510
**Columns:** 25

### Schema
| Column | Type | Nullable |
|--------|------|----------|
| S.No | bigint | YES |
| Month | nvarchar | YES |
| Year | int | YES |
| MonthStart | date | YES |
| PA Name | nvarchar | NO |
| PH Emp ID | nvarchar | NO |
| PH Name | nvarchar | NO |
| ATNM/Sub Contractor | varchar | NO |
| Category | nvarchar | NO |
| Crew Type | nvarchar | NO |
| Crew Discipline | nvarchar | NO |
| Crew Name | nvarchar | NO |
| Average Productivity (%) | decimal | YES |
| W1_PI (CMR) | varchar | YES |
| W1_PI (T-Wise) | varchar | YES |
| W2_PI (CMR) | varchar | YES |
| W2_PI (T-Wise) | varchar | YES |
| W3_PI (CMR) | varchar | YES |
| W3_PI (T-Wise) | varchar | YES |
| W4_PI (CMR) | varchar | YES |
| W4_PI (T-Wise) | varchar | YES |
| W5_PI (CMR) | varchar | YES |
| W5_PI (T-Wise) | varchar | YES |
| Month PI (CMR) | varchar | NO |
| Month PI (T-Wise) | varchar | NO |

### Sample Data (first 3 rows)
|S.No|Month|Year|MonthStart|PA Name|PH Emp ID|PH Name|ATNM/Sub Contractor|Category|Crew Type|
|---|---|---|---|---|---|---|---|---|---|
|1|December|2025|2025-12-01|arul
arunraj
basil
dipukumar
g|NA|NA|Sub contractor|Marmul Conversion with Flowlin|CFD0803
CGR0702
FII-0502
FRL-0|
|5|December|2025|2025-12-01|NA|110754265|SHAJI|Sub contractor|Nimr Flowline|FWP-0702|
|9|December|2025|2025-12-01|arul|116020874|JEBARAJ|Sub contractor|Nimr Flowline|FWM-0501|

---

## ProjectIDs
**Rows:** 19
**Columns:** 4

### Schema
| Column | Type | Nullable |
|--------|------|----------|
| Code | nvarchar | YES |
| column2 | nvarchar | YES |
| Number | tinyint | YES |
| ID | nvarchar | YES |

### Sample Data (first 3 rows)
|Code|column2|Number|ID|
|---|---|---|---|
|NL0010|Nimr Location|1|8c9c6b42-7a12-4eb3-935b-fc0437|
|NF0010|Nimr Flowline|2|278c5587-bba7-46ea-9c6a-d79aa8|
|NS0010|Nimr SNLP|3|6d07e3a5-d89b-47ac-9163-8a71e8|

---

## Revenue
**Rows:** 21566
**Columns:** 18

### Schema
| Column | Type | Nullable |
|--------|------|----------|
| id | bigint | NO |
| rigcode | nvarchar | YES |
| well_id | nvarchar | YES |
| code | nvarchar | YES |
| pms | decimal | YES |
| step_type | nvarchar | YES |
| planned_progress | nvarchar | YES |
| plan_percent | nvarchar | YES |
| acutal_progress | decimal | YES |
| act_percent | nvarchar | YES |
| total_purpose_value | decimal | YES |
| planned_purpose_value | nvarchar | YES |
| actual_purpose_value | decimal | YES |
| planned_progress_next_week | nvarchar | YES |
| plan_percent_next_week | nvarchar | YES |
| planned_purpose_value_next_week | nvarchar | YES |
| Title | nvarchar | YES |
| created_at | datetime2 | YES |

### Key Columns (for joins)
- 

### Sample Data (first 3 rows)
|id|rigcode|well_id|code|pms|step_type|planned_progress|plan_percent|acutal_progress|act_percent|
|---|---|---|---|---|---|---|---|---|---|
|1552|NF0010|37230|FLME1020-37230|0.0000||1|0.005|1.0000|0.005|
|1553|NF0010|37230|FLME1030-37230|0.0000||1|0.005|1.0000|0.005|
|1554|NF0010|37230|FLME1036-37230|0.0000||1|0.005|1.0000|0.005|

---

## SAP_DRILLING_SEQUENCE
**Rows:** 6159
**Columns:** 19

### Schema
| Column | Type | Nullable |
|--------|------|----------|
| Work_Center | nvarchar | YES |
| Operation_Short | nvarchar | YES |
| Activity | nvarchar | YES |
| Opr_System_status | nvarchar | YES |
| Earl_start_date | date | YES |
| EarliestEndDate | date | YES |
| Station_Code | nvarchar | YES |
| Normal_duration | float | YES |
| Norm_duratn_un | nvarchar | YES |
| Well_Name | nvarchar | YES |
| Field | nvarchar | YES |
| Responsible_asset | nvarchar | YES |
| Well_ID | varchar | NO |
| Well_Location | nvarchar | YES |
| Well_Function | nvarchar | YES |
| Well_Category | nvarchar | YES |
| PCAP_Category | nvarchar | YES |
| Move_days | tinyint | YES |
| PDO_Well_Type | nvarchar | YES |

### Key Columns (for joins)
- 

### Sample Data (first 3 rows)
|Work_Center|Operation_Short|Activity|Opr_System_status|Earl_start_date|EarliestEndDate|Station_Code|Normal_duration|Norm_duratn_un|Well_Name|
|---|---|---|---|---|---|---|---|---|---|
|SWER149|Y762-10207|Y762|REL|2026-03-24|2026-03-28|SSFDP|4.5|DAY|RKDS_2026_OP_LOC18|
|SWER149|Y760-10239|Y760|REL|2026-04-25|2026-04-29|SSFDP|4.5|DAY|RKDS_2026_WI_LOC6|
|SWERIG99|6845-10995|6845|REL|2039-12-26|2040-01-21|LEK|26.0|DAY|DMB-LSB-OP-3 (CR)|

---

## schema_knowledge_base
**Rows:** 0
**Columns:** 7

### Schema
| Column | Type | Nullable |
|--------|------|----------|
| id | int | NO |
| chunk_id | nvarchar | NO |
| chunk_text | nvarchar | NO |
| table_name | nvarchar | YES |
| chunk_type | nvarchar | YES |
| embedding | varbinary | YES |
| created_at | datetime2 | YES |

### Sample Data (first 3 rows)
|id|chunk_id|chunk_text|table_name|chunk_type|embedding|created_at|
|---|---|---|---|---|---|---|

---

## task_daily
**Rows:** 35394
**Columns:** 43

### Schema
| Column | Type | Nullable |
|--------|------|----------|
| id | bigint | NO |
| ActionOn | date | NO |
| task_code | nvarchar | YES |
| schedule_id | bigint | YES |
| project_id | uniqueidentifier | YES |
| required | decimal | YES |
| planned | decimal | YES |
| duration | decimal | YES |
| remaining_duration | decimal | YES |
| progress | decimal | YES |
| ready | bit | YES |
| completed | bit | YES |
| plan | bit | YES |
| committed_start | date | YES |
| committed_end | date | YES |
| target_start | date | YES |
| target_end | date | YES |
| actual_start | date | YES |
| actual_end | date | YES |
| startDate | date | YES |
| endDate | date | YES |
| crew_type | nvarchar | YES |
| crew_code | nvarchar | YES |
| planned_crew | nvarchar | YES |
| well_id | nvarchar | YES |
| task_uom | nvarchar | YES |
| data_hours | decimal | YES |
| data_qty | decimal | YES |
| data_employees | nvarchar | YES |
| task_assignee | nvarchar | YES |
| supervisor_email | nvarchar | YES |
| url | nvarchar | YES |
| task_data | nvarchar | YES |
| daily_data | nvarchar | YES |
| created_at | datetime2 | YES |
| updated_at | datetime2 | YES |
| daily_ph_name | nvarchar | YES |
| daily_equipment_ids | nvarchar | YES |
| daily_employee_ids | nvarchar | YES |
| daily_actual_quantity | decimal | YES |
| daily_actual_hours | decimal | YES |
| daily_completed | bit | YES |
| time_stamp | nvarchar | YES |

### Key Columns (for joins)
- 
- 

### Sample Data (first 3 rows)
|id|ActionOn|task_code|schedule_id|project_id|required|planned|duration|remaining_duration|progress|
|---|---|---|---|---|---|---|---|---|---|
|5757|2025-05-19|FLC1080-19252|320|30934CE7-B4E3-41E5-ACA7-C03113|8.780|8.800|2.0000|0.0000|1.0000|
|5758|2025-05-20|FLC1080-19252|320|30934CE7-B4E3-41E5-ACA7-C03113|8.780|8.800|2.0000|0.0000|1.0000|
|5759|2025-05-12|FLC1040-19252|320|30934CE7-B4E3-41E5-ACA7-C03113|0.560|0.600|1.0000|0.0000|1.0000|

---

## WBS_Master_Tracker_
**Rows:** 81846
**Columns:** 15

### Schema
| Column | Type | Nullable |
|--------|------|----------|
| Sr_No | nvarchar | YES |
| WBS_Code | nvarchar | YES |
| Project_Def | nvarchar | YES |
| WD_PRJ | nvarchar | YES |
| Plant_Code | nvarchar | YES |
| Plant_Name | nvarchar | YES |
| Cluster | nvarchar | YES |
| Well_ID_Project_PO | nvarchar | YES |
| Activity_code | nvarchar | YES |
| Activity | nvarchar | YES |
| Category | nvarchar | YES |
| Sr_No_2 | nvarchar | YES |
| LMPS | nvarchar | YES |
| Duplicate_check | nvarchar | YES |
| Last_Updated_on | nvarchar | YES |

### Sample Data (first 3 rows)
|Sr_No|WBS_Code|Project_Def|WD_PRJ|Plant_Code|Plant_Name|Cluster|Well_ID_Project_PO|Activity_code|Activity|
|---|---|---|---|---|---|---|---|---|---|
|2092|PJ-3525-65842-EEI-1-S|PJ-3525-65842-EEI-1|PJ|3525|Birba ODC|GB|65842|EEI|Electrical Equipment Installat|
|2093|PJ-3525-65842-EMR-1-L|PJ-3525-65842-EMR-1|PJ|3525|Birba ODC|GB|65842|EMR|Emergency Works|
|2094|PJ-3525-65842-EMR-1-M|PJ-3525-65842-EMR-1|PJ|3525|Birba ODC|GB|65842|EMR|Emergency Works|

---

## WellMonitoringReport
**Rows:** 268
**Columns:** 130

### Schema
| Column | Type | Nullable |
|--------|------|----------|
| sl_no | bigint | YES |
| sl_no_raw | nvarchar | YES |
| rig_no | nvarchar | YES |
| well_location | nvarchar | YES |
| well_name_after_spud | nvarchar | YES |
| pdo_well_id | nvarchar | YES |
| well_type | nvarchar | YES |
| northing | nvarchar | YES |
| easting | nvarchar | YES |
| locationdd | nvarchar | YES |
| flow_linedl | nvarchar | YES |
| location_po_no | nvarchar | YES |
| location_po_recvd_date | date | YES |
| location_-_purpose_value | nvarchar | YES |
| last_week_exp.rig_on_location_sap_data | date | YES |
| latest_exp.rig_on_location_sap_data | date | YES |
| exp.rig_off_location_sap_data | date | YES |
| date_-_material_po_placed | date | YES |
| date_-_material_available_at_site | date | YES |
| scr_no | nvarchar | YES |
| scr_date | date | YES |
| moc_raised | nvarchar | YES |
| moc_approved | nvarchar | YES |
| buffer_status | varchar | YES |
| actual_pegged_date | date | YES |
| last_week_cum_progress | decimal | YES |
| cum_progress_for_this_week | decimal | YES |
| actual_start_date | date | YES |
| actual_date_odc_requested_field_programmer_oso33x_for_esp_pcp_surface_cables | date | YES |
| date_oso33x_call_out_for_cable_installation_to_pcp_esp_vendor | date | YES |
| delivery_of_esp_pcp_surface_cable_by_field_programmer_oso33x | date | YES |
| installation_of_esp_pcp_surface_cable_by_vendors | date | YES |
| actual_finish_date | date | YES |
| flaf_issue_date | date | YES |
| ramz_id | nvarchar | YES |
| ramz_id_received_date_same_day_as_flaf_issue_date | date | YES |
| date_of_site_survey_report_issuance | date | YES |
| well_engineer_to_add_location_name_in_edm | nvarchar | YES |
| pt_to_request_for_esp_preliminary_design_through_ald | nvarchar | YES |
| actual_date_odc_requested_field_programmer_oso33x_to_install_esp_pcp_skid | date | YES |
| actual_date_field_programmer_oso33x_requested_esp_pcp_vendor_to_install_the_skid | date | YES |
| actual_date_pcp_esp_vendor_delivered_the_skid | date | YES |
| actual_installation_date_by_vendor_of_esp/pcp_skid | date | YES |
| flow_line_po_no | nvarchar | YES |
| f_l_po_recd._date | date | YES |
| flowline_-_purpose_value | nvarchar | YES |
| station_name_no | nvarchar | YES |
| physical_tie_in_port_number | nvarchar | YES |
| date_of_tie_in_port_readiness | date | YES |
| physical_tie_in_port_available_when_flaf_issued | nvarchar | YES |
| engineering_actual_start_date | date | YES |
| engineering_actual_finish_date | date | YES |
| progress | decimal | YES |
| fl_dia | nvarchar | YES |
| fl_length_meter | nvarchar | YES |
| const._actual_start_date | date | YES |
| const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date | date | YES |
| flowline_construction_progress | decimal | YES |
| ohl_length_meter | nvarchar | YES |
| ohl_progress | decimal | YES |
| ohl_completion_date | date | YES |
| z6_data_submitted_date | date | YES |
| sap_notification_received_date_z6_2_days_before_eng._completion | date | YES |
| actual_rig_on_date | date | YES |
| actual_rig_off_date | date | YES |
| wlctf_acceptanceapproval_from_production | date | YES |
| actual_hoist_fbu_rsr_on_date | date | YES |
| actual_hoist_fbu_rsr_off_date | date | YES |
| wellpad_handover-2_from_hoist_fbu_rsr_off_date | date | YES |
| completion_type_rig_fbu_or_rsr_hoist | nvarchar | YES |
| actual_eng._completion_date | date | YES |
| actual_comm._start_date | date | YES |
| actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date | date | YES |
| engg_kpi_after_rig-off_days | int | YES |
| data_error | varchar | YES |
| reason_if_kpi_not_met | nvarchar | YES |
| remark_status_area_of_attention_issues_ | nvarchar | YES |
| rlmu_submitted_to_ho-date_with_in_7_days_from_actual_comm. | date | YES |
| flow_line_test_pack_completion_doc._submission_date_to_qs_dept. | date | YES |
| flow_line_test_pack_completion_progress | decimal | YES |
| over_all_progress_percentages | decimal | YES |
| ssfd_wells | nvarchar | YES |
| ipm | nvarchar | YES |
| access_road_5 | decimal | YES |
| earth_work_60 | decimal | YES |
| cellar_20 | decimal | YES |
| beam_pump_base_esp_pcp_foundation_5 | decimal | YES |
| earthing_1 | decimal | YES |
| septic_tank_1 | decimal | YES |
| water_2 | decimal | YES |
| waste_water_2 | decimal | YES |
| hdpe_liner_instalat_4 | decimal | YES |
| overall_loc._preparation_10_100 | decimal | YES |
| site_survey_5 | decimal | YES |
| survey_report_issue_5 | decimal | YES |
| design_sta_5 | decimal | YES |
| design_completed_issue_for_ta2_5_40 | decimal | YES |
| approved_by_15 | decimal | YES |
| afc_3_30 | decimal | YES |
| overall_engg._10_100 | decimal | YES |
| piping_mech_50 | decimal | YES |
| elect_30 | decimal | YES |
| instr_20 | decimal | YES |
| overall_material_10_100 | decimal | YES |
| cold_b_2 | decimal | YES |
| sleeper_pre_cast_ins_15 | decimal | YES |
| cs_pipe_welding_ndt_10_rt_for_op_100_for_60 | decimal | YES |
| pe_fussion_pull_20 | decimal | YES |
| final_hydro_t_3 | decimal | YES |
| overall_const._10_100 | decimal | YES |
| pole_hole_drill_40 | decimal | YES |
| pole_erect_40 | decimal | YES |
| conductor_string_18 | decimal | YES |
| ohl_ti_2 | decimal | YES |
| overall_ohl_progr_100 | decimal | YES |
| mechani_60 | decimal | YES |
| electri_15 | decimal | YES |
| instrumentat_20 | decimal | YES |
| overall_comm_mi_5 | decimal | YES |
| overall_comm_progress_100 | decimal | YES |
| location_preparation_status_in_progress_completed | nvarchar | YES |
| flow_line_const._status_in_progress_completed | nvarchar | YES |
| flow_line_commi._status_in_progress_completed | nvarchar | YES |
| well_year_white_space | nvarchar | YES |
| reasons_for_year_2018 | nvarchar | YES |
| column7 | nvarchar | YES |
| digital_wmr_import_remarks | nvarchar | YES |
| project_id | nvarchar | YES |
| Week_Number | date | YES |
| Cluster | nvarchar | YES |

### Key Columns (for joins)
- 
- 
- 
- 

### Sample Data (first 3 rows)
|sl_no|sl_no_raw|rig_no|well_location|well_name_after_spud|pdo_well_id|well_type|northing|easting|locationdd|
|---|---|---|---|---|---|---|---|---|---|
|1|1.0|SWER101|AL BURJ_26_MC_OP2|AL BURJ_26_MC_OP2|34422|ESP|2016211.99|352309.00|NULL|
|2|1.0|SWER101|AL BURJ_26_MC_OP3|AL BURJ_26_MC_OP3|37797|ESP|NULL|NULL|NULL|
|3|1.0|SWER101|ALBRG_1405250004_OP1|AL BURJ-280|31339|OP|2013962.96|351529.95|C.AA.NIM.DD.03.WLC.GENRL|

---

## WellMonitoringReport_Latest
**Rows:** 169
**Columns:** 130

### Schema
| Column | Type | Nullable |
|--------|------|----------|
| sl_no | bigint | YES |
| sl_no_raw | nvarchar | YES |
| rig_no | nvarchar | YES |
| well_location | nvarchar | YES |
| well_name_after_spud | nvarchar | YES |
| pdo_well_id | nvarchar | YES |
| well_type | nvarchar | YES |
| northing | nvarchar | YES |
| easting | nvarchar | YES |
| locationdd | nvarchar | YES |
| flow_linedl | nvarchar | YES |
| location_po_no | nvarchar | YES |
| location_po_recvd_date | date | YES |
| location_-_purpose_value | nvarchar | YES |
| last_week_exp.rig_on_location_sap_data | date | YES |
| latest_exp.rig_on_location_sap_data | date | YES |
| exp.rig_off_location_sap_data | date | YES |
| date_-_material_po_placed | date | YES |
| date_-_material_available_at_site | date | YES |
| scr_no | nvarchar | YES |
| scr_date | date | YES |
| moc_raised | nvarchar | YES |
| moc_approved | nvarchar | YES |
| buffer_status | varchar | YES |
| actual_pegged_date | date | YES |
| last_week_cum_progress | decimal | YES |
| cum_progress_for_this_week | decimal | YES |
| actual_start_date | date | YES |
| actual_date_odc_requested_field_programmer_oso33x_for_esp_pcp_surface_cables | date | YES |
| date_oso33x_call_out_for_cable_installation_to_pcp_esp_vendor | date | YES |
| delivery_of_esp_pcp_surface_cable_by_field_programmer_oso33x | date | YES |
| installation_of_esp_pcp_surface_cable_by_vendors | date | YES |
| actual_finish_date | date | YES |
| flaf_issue_date | date | YES |
| ramz_id | nvarchar | YES |
| ramz_id_received_date_same_day_as_flaf_issue_date | date | YES |
| date_of_site_survey_report_issuance | date | YES |
| well_engineer_to_add_location_name_in_edm | nvarchar | YES |
| pt_to_request_for_esp_preliminary_design_through_ald | nvarchar | YES |
| actual_date_odc_requested_field_programmer_oso33x_to_install_esp_pcp_skid | date | YES |
| actual_date_field_programmer_oso33x_requested_esp_pcp_vendor_to_install_the_skid | date | YES |
| actual_date_pcp_esp_vendor_delivered_the_skid | date | YES |
| actual_installation_date_by_vendor_of_esp/pcp_skid | date | YES |
| flow_line_po_no | nvarchar | YES |
| f_l_po_recd._date | date | YES |
| flowline_-_purpose_value | nvarchar | YES |
| station_name_no | nvarchar | YES |
| physical_tie_in_port_number | nvarchar | YES |
| date_of_tie_in_port_readiness | date | YES |
| physical_tie_in_port_available_when_flaf_issued | nvarchar | YES |
| engineering_actual_start_date | date | YES |
| engineering_actual_finish_date | date | YES |
| progress | decimal | YES |
| fl_dia | nvarchar | YES |
| fl_length_meter | nvarchar | YES |
| const._actual_start_date | date | YES |
| const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date | date | YES |
| flowline_construction_progress | decimal | YES |
| ohl_length_meter | nvarchar | YES |
| ohl_progress | decimal | YES |
| ohl_completion_date | date | YES |
| z6_data_submitted_date | date | YES |
| sap_notification_received_date_z6_2_days_before_eng._completion | date | YES |
| actual_rig_on_date | date | YES |
| actual_rig_off_date | date | YES |
| wlctf_acceptanceapproval_from_production | date | YES |
| actual_hoist_fbu_rsr_on_date | date | YES |
| actual_hoist_fbu_rsr_off_date | date | YES |
| wellpad_handover-2_from_hoist_fbu_rsr_off_date | date | YES |
| completion_type_rig_fbu_or_rsr_hoist | nvarchar | YES |
| actual_eng._completion_date | date | YES |
| actual_comm._start_date | date | YES |
| actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date | date | YES |
| engg_kpi_after_rig-off_days | int | YES |
| data_error | varchar | YES |
| reason_if_kpi_not_met | nvarchar | YES |
| remark_status_area_of_attention_issues_ | nvarchar | YES |
| rlmu_submitted_to_ho-date_with_in_7_days_from_actual_comm. | date | YES |
| flow_line_test_pack_completion_doc._submission_date_to_qs_dept. | date | YES |
| flow_line_test_pack_completion_progress | decimal | YES |
| over_all_progress_percentages | decimal | YES |
| ssfd_wells | nvarchar | YES |
| ipm | nvarchar | YES |
| access_road_5 | decimal | YES |
| earth_work_60 | decimal | YES |
| cellar_20 | decimal | YES |
| beam_pump_base_esp_pcp_foundation_5 | decimal | YES |
| earthing_1 | decimal | YES |
| septic_tank_1 | decimal | YES |
| water_2 | decimal | YES |
| waste_water_2 | decimal | YES |
| hdpe_liner_instalat_4 | decimal | YES |
| overall_loc._preparation_10_100 | decimal | YES |
| site_survey_5 | decimal | YES |
| survey_report_issue_5 | decimal | YES |
| design_sta_5 | decimal | YES |
| design_completed_issue_for_ta2_5_40 | decimal | YES |
| approved_by_15 | decimal | YES |
| afc_3_30 | decimal | YES |
| overall_engg._10_100 | decimal | YES |
| piping_mech_50 | decimal | YES |
| elect_30 | decimal | YES |
| instr_20 | decimal | YES |
| overall_material_10_100 | decimal | YES |
| cold_b_2 | decimal | YES |
| sleeper_pre_cast_ins_15 | decimal | YES |
| cs_pipe_welding_ndt_10_rt_for_op_100_for_60 | decimal | YES |
| pe_fussion_pull_20 | decimal | YES |
| final_hydro_t_3 | decimal | YES |
| overall_const._10_100 | decimal | YES |
| pole_hole_drill_40 | decimal | YES |
| pole_erect_40 | decimal | YES |
| conductor_string_18 | decimal | YES |
| ohl_ti_2 | decimal | YES |
| overall_ohl_progr_100 | decimal | YES |
| mechani_60 | decimal | YES |
| electri_15 | decimal | YES |
| instrumentat_20 | decimal | YES |
| overall_comm_mi_5 | decimal | YES |
| overall_comm_progress_100 | decimal | YES |
| location_preparation_status_in_progress_completed | nvarchar | YES |
| flow_line_const._status_in_progress_completed | nvarchar | YES |
| flow_line_commi._status_in_progress_completed | nvarchar | YES |
| well_year_white_space | nvarchar | YES |
| reasons_for_year_2018 | nvarchar | YES |
| column7 | nvarchar | YES |
| digital_wmr_import_remarks | nvarchar | YES |
| project_id | nvarchar | YES |
| Week_Number | date | YES |
| Cluster | nvarchar | YES |

### Key Columns (for joins)
- 
- 
- 
- 

### Sample Data (first 3 rows)
|sl_no|sl_no_raw|rig_no|well_location|well_name_after_spud|pdo_well_id|well_type|northing|easting|locationdd|
|---|---|---|---|---|---|---|---|---|---|
|1|1.0|SWER126|DB_I5_SPOT_EXP_UND_WI1|DB_I5_SPOT_EXP_UND_WI1|25029|NULL|NULL|NULL|NULL|
|2|1.0|SWER126|DB_I5_SPOT_EXP_UND_WI9|DB_I5_SPOT_EXP_UND_WI9|28990|NULL|NULL|NULL|NULL|
|3|1.0|SWER126|HSAK-95U_HZ_500M_13|HSAK-95U_HZ_500M_13|33092|NULL|NULL|NULL|NULL|

---

## WellMonitoringReport_Staged
**Rows:** 169
**Columns:** 161

### Schema
| Column | Type | Nullable |
|--------|------|----------|
| sl_no | nvarchar | YES |
| rig_no | nvarchar | NO |
| well_location | nvarchar | YES |
| well_name_after_spud | nvarchar | YES |
| pdo_well_id | nvarchar | YES |
| well_type | nvarchar | YES |
| northing | nvarchar | YES |
| easting | nvarchar | YES |
| locationdd | nvarchar | YES |
| flow_linedl | nvarchar | YES |
| location_po_no | nvarchar | YES |
| location_po_recvd_date | nvarchar | YES |
| location_-_purpose_value | nvarchar | YES |
| last_week_exp.rig_on_location_sap_data | nvarchar | YES |
| latest_exp.rig_on_location_sap_data | nvarchar | YES |
| exp.rig_off_location_sap_data | nvarchar | YES |
| date_-_material_po_placed | nvarchar | YES |
| date_-_material_available_at_site | nvarchar | YES |
| scr_no | nvarchar | YES |
| scr_date | nvarchar | YES |
| moc_raised | nvarchar | YES |
| moc_approved | nvarchar | YES |
| buffer_status | nvarchar | YES |
| actual_pegged_date | nvarchar | YES |
| last_week_cum_progress | nvarchar | YES |
| cum_progress_for_this_week | nvarchar | YES |
| actual_start_date | nvarchar | YES |
| actual_date_odc_requested_field_programmer_oso33x_for_esp_pcp_surface_cables | nvarchar | YES |
| date_oso33x_call_out_for_cable_installation_to_pcp_esp_vendor | nvarchar | YES |
| delivery_of_esp_pcp_surface_cable_by_field_programmer_oso33x | nvarchar | YES |
| installation_of_esp_pcp_surface_cable_by_vendors | nvarchar | YES |
| actual_finish_date | nvarchar | YES |
| flaf_issue_date | nvarchar | YES |
| ramz_id | nvarchar | YES |
| ramz_id_received_date_same_day_as_flaf_issue_date | nvarchar | YES |
| date_of_site_survey_report_issuance | nvarchar | YES |
| well_engineer_to_add_location_name_in_edm | nvarchar | YES |
| pt_to_request_for_esp_preliminary_design_through_ald | nvarchar | YES |
| actual_date_odc_requested_field_programmer_oso33x_to_install_esp_pcp_skid | nvarchar | YES |
| actual_date_field_programmer_oso33x_requested_esp_pcp_vendor_to_install_the_skid | nvarchar | YES |
| actual_date_pcp_esp_vendor_delivered_the_skid | nvarchar | YES |
| actual_installation_date_by_vendor_of_esp/pcp_skid | nvarchar | YES |
| flow_line_po_no | nvarchar | YES |
| f_l_po_recd._date | nvarchar | YES |
| flowline_-_purpose_value | nvarchar | YES |
| station_name_no | nvarchar | YES |
| physical_tie_in_port_number | nvarchar | YES |
| date_of_tie_in_port_readiness | nvarchar | YES |
| physical_tie_in_port_available_when_flaf_issued | nvarchar | YES |
| engineering_actual_start_date | nvarchar | YES |
| engineering_actual_finish_date | nvarchar | YES |
| progress | nvarchar | YES |
| fl_dia | nvarchar | YES |
| fl_length_meter | nvarchar | YES |
| const._actual_start_date | nvarchar | YES |
| const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date | nvarchar | YES |
| flowline_construction_progress | nvarchar | YES |
| ohl_length_meter | nvarchar | YES |
| ohl_progress | nvarchar | YES |
| ohl_completion_date | nvarchar | YES |
| z6_data_submitted_date | nvarchar | YES |
| sap_notification_received_date_z6_2_days_before_eng._completion | nvarchar | YES |
| actual_rig_on_date | nvarchar | YES |
| actual_rig_off_date | nvarchar | YES |
| wlctf_acceptanceapproval_from_production | nvarchar | YES |
| actual_hoist_fbu_rsr_on_date | nvarchar | YES |
| actual_hoist_fbu_rsr_off_date | nvarchar | YES |
| wellpad_handover-2_from_hoist_fbu_rsr_off_date | nvarchar | YES |
| completion_type_rig_fbu_or_rsr_hoist | nvarchar | YES |
| actual_eng._completion_date | nvarchar | YES |
| actual_comm._start_date | nvarchar | YES |
| actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date | nvarchar | YES |
| engg_kpi_after_rig-off_days | nvarchar | YES |
| data_error | nvarchar | YES |
| reason_if_kpi_not_met | nvarchar | YES |
| remark_status_area_of_attention_issues_ | nvarchar | YES |
| rlmu_submitted_to_ho-date_with_in_7_days_from_actual_comm. | nvarchar | YES |
| flow_line_test_pack_completion_doc._submission_date_to_qs_dept. | nvarchar | YES |
| flow_line_test_pack_completion_progress | nvarchar | YES |
| over_all_progress_percentages | nvarchar | YES |
| ssfd_wells | nvarchar | YES |
| ipm | nvarchar | YES |
| access_road_5 | nvarchar | YES |
| earth_work_60 | nvarchar | YES |
| cellar_20 | nvarchar | YES |
| beam_pump_base_esp_pcp_foundation_5 | nvarchar | YES |
| earthing_1 | nvarchar | YES |
| septic_tank_1 | nvarchar | YES |
| water_2 | nvarchar | YES |
| waste_water_2 | nvarchar | YES |
| hdpe_liner_instalat_4 | nvarchar | YES |
| overall_loc._preparation_10_100 | nvarchar | YES |
| site_survey_5 | nvarchar | YES |
| survey_report_issue_5 | nvarchar | YES |
| design_sta_5 | nvarchar | YES |
| design_completed_issue_for_ta2_5_40 | nvarchar | YES |
| approved_by_15 | nvarchar | YES |
| afc_3_30 | nvarchar | YES |
| overall_engg._10_100 | nvarchar | YES |
| piping_mech_50 | nvarchar | YES |
| elect_30 | nvarchar | YES |
| instr_20 | nvarchar | YES |
| overall_material_10_100 | nvarchar | YES |
| cold_b_2 | nvarchar | YES |
| sleeper_pre_cast_ins_15 | nvarchar | YES |
| cs_pipe_welding_ndt_10_rt_for_op_100_for_60 | nvarchar | YES |
| pe_fussion_pull_20 | nvarchar | YES |
| final_hydro_t_3 | nvarchar | YES |
| overall_const._10_100 | nvarchar | YES |
| pole_hole_drill_40 | nvarchar | YES |
| pole_erect_40 | nvarchar | YES |
| conductor_string_18 | nvarchar | YES |
| ohl_ti_2 | nvarchar | YES |
| overall_ohl_progr_100 | nvarchar | YES |
| mechani_60 | nvarchar | YES |
| electri_15 | nvarchar | YES |
| instrumentat_20 | nvarchar | YES |
| overall_comm_mi_5 | nvarchar | YES |
| overall_comm_progress_100 | nvarchar | YES |
| location_preparation_status_in_progress_completed | nvarchar | YES |
| flow_line_const._status_in_progress_completed | nvarchar | YES |
| flow_line_commi._status_in_progress_completed | nvarchar | YES |
| well_year_white_space | nvarchar | YES |
| reasons_for_year_2018 | nvarchar | YES |
| column7 | nvarchar | YES |
| digital_wmr_import_remarks | nvarchar | YES |
| project_id | nvarchar | YES |
| Week_Number | nvarchar | YES |
| Week_Number_d | date | YES |
| actual_rig_on_date_d | date | YES |
| actual_rig_off_date_d | date | YES |
| wlctf_acceptance_d | date | YES |
| hoist_on_date_d | date | YES |
| hoist_off_date_d | date | YES |
| handover2_date_d | date | YES |
| eng_completion_date_d | date | YES |
| comm_start_date_d | date | YES |
| comm_finish_date_d | date | YES |
| flaf_issue_date_d | date | YES |
| location_po_recvd_date_d | date | YES |
| scr_date_d | date | YES |
| actual_pegged_date_d | date | YES |
| actual_start_date_d | date | YES |
| actual_finish_date_d | date | YES |
| ramz_id_received_date_d | date | YES |
| site_survey_report_issuance_d | date | YES |
| f_l_po_recd_date_d | date | YES |
| tie_in_port_readiness_d | date | YES |
| const_actual_start_date_d | date | YES |
| ohl_completion_date_d | date | YES |
| last_week_cum_progress_p | decimal | YES |
| cum_progress_for_this_week_p | decimal | YES |
| flowline_construction_progress_p | decimal | YES |
| ohl_progress_p | decimal | YES |
| overall_progress_p | decimal | YES |
| overall_loc_preparation_p | decimal | YES |
| overall_engg_p | decimal | YES |
| overall_material_p | decimal | YES |
| overall_const_p | decimal | YES |
| overall_ohl_p | decimal | YES |
| overall_comm_progress_p | decimal | YES |

### Key Columns (for joins)
- 
- 
- 
- 

### Sample Data (first 3 rows)
|sl_no|rig_no|well_location|well_name_after_spud|pdo_well_id|well_type|northing|easting|locationdd|flow_linedl|
|---|---|---|---|---|---|---|---|---|---|
|1.0|SWER126|HSAK-95U_HZ_500M_16|QATA-194|35492|NULL|1993474.84|320497.54|NULL|C.AA.RTQ.DL.04.FLO.35495|
|1.0|SWER126|HSAK-95U_HZ_500M_18|HSAK-95U_HZ_500M_18|35493|NULL|NULL|NULL|NULL|C.AA.RTQ.DL.04.FLO.35495|
|1.0|SWER127|MM-GSR-CNMGLG1_15-OP|MARMUL-1699|33105|NULL|2003390.29|315145.10|NULL|C.AA.MAR.DL.04.FLO.33102|

---

## WMR_Full
**Rows:** 18969
**Columns:** 128

### Schema
| Column | Type | Nullable |
|--------|------|----------|
| sl_no | nvarchar | YES |
| rig_no | nvarchar | NO |
| well_location | nvarchar | YES |
| well_name_after_spud | nvarchar | YES |
| pdo_well_id | nvarchar | YES |
| well_type | nvarchar | YES |
| northing | nvarchar | YES |
| easting | nvarchar | YES |
| locationdd | nvarchar | YES |
| flow_linedl | nvarchar | YES |
| location_po_no | nvarchar | YES |
| location_po_recvd_date | nvarchar | YES |
| location_-_purpose_value | nvarchar | YES |
| last_week_exp.rig_on_location_sap_data | nvarchar | YES |
| latest_exp.rig_on_location_sap_data | nvarchar | YES |
| exp.rig_off_location_sap_data | nvarchar | YES |
| date_-_material_po_placed | nvarchar | YES |
| date_-_material_available_at_site | nvarchar | YES |
| scr_no | nvarchar | YES |
| scr_date | nvarchar | YES |
| moc_raised | nvarchar | YES |
| moc_approved | nvarchar | YES |
| buffer_status | nvarchar | YES |
| actual_pegged_date | nvarchar | YES |
| last_week_cum_progress | nvarchar | YES |
| cum_progress_for_this_week | nvarchar | YES |
| actual_start_date | nvarchar | YES |
| actual_date_odc_requested_field_programmer_oso33x_for_esp_pcp_surface_cables | nvarchar | YES |
| date_oso33x_call_out_for_cable_installation_to_pcp_esp_vendor | nvarchar | YES |
| delivery_of_esp_pcp_surface_cable_by_field_programmer_oso33x | nvarchar | YES |
| installation_of_esp_pcp_surface_cable_by_vendors | nvarchar | YES |
| actual_finish_date | nvarchar | YES |
| flaf_issue_date | nvarchar | YES |
| ramz_id | nvarchar | YES |
| ramz_id_received_date_same_day_as_flaf_issue_date | nvarchar | YES |
| date_of_site_survey_report_issuance | nvarchar | YES |
| well_engineer_to_add_location_name_in_edm | nvarchar | YES |
| pt_to_request_for_esp_preliminary_design_through_ald | nvarchar | YES |
| actual_date_odc_requested_field_programmer_oso33x_to_install_esp_pcp_skid | nvarchar | YES |
| actual_date_field_programmer_oso33x_requested_esp_pcp_vendor_to_install_the_skid | nvarchar | YES |
| actual_date_pcp_esp_vendor_delivered_the_skid | nvarchar | YES |
| actual_installation_date_by_vendor_of_esp/pcp_skid | nvarchar | YES |
| flow_line_po_no | nvarchar | YES |
| f_l_po_recd._date | nvarchar | YES |
| flowline_-_purpose_value | nvarchar | YES |
| station_name_no | nvarchar | YES |
| physical_tie_in_port_number | nvarchar | YES |
| date_of_tie_in_port_readiness | nvarchar | YES |
| physical_tie_in_port_available_when_flaf_issued | nvarchar | YES |
| engineering_actual_start_date | nvarchar | YES |
| engineering_actual_finish_date | nvarchar | YES |
| progress | nvarchar | YES |
| fl_dia | nvarchar | YES |
| fl_length_meter | nvarchar | YES |
| const._actual_start_date | nvarchar | YES |
| const._complete_date_including_f_l_final_hydro_test_1_day_before_rig_on_date | nvarchar | YES |
| flowline_construction_progress | nvarchar | YES |
| ohl_length_meter | nvarchar | YES |
| ohl_progress | nvarchar | YES |
| ohl_completion_date | nvarchar | YES |
| z6_data_submitted_date | nvarchar | YES |
| sap_notification_received_date_z6_2_days_before_eng._completion | nvarchar | YES |
| actual_rig_on_date | nvarchar | YES |
| actual_rig_off_date | nvarchar | YES |
| wlctf_acceptanceapproval_from_production | nvarchar | YES |
| actual_hoist_fbu_rsr_on_date | nvarchar | YES |
| actual_hoist_fbu_rsr_off_date | nvarchar | YES |
| wellpad_handover-2_from_hoist_fbu_rsr_off_date | nvarchar | YES |
| completion_type_rig_fbu_or_rsr_hoist | nvarchar | YES |
| actual_eng._completion_date | nvarchar | YES |
| actual_comm._start_date | nvarchar | YES |
| actual_comm._finish_date_with_in_2_days_from_actual_engg._completion_date | nvarchar | YES |
| engg_kpi_after_rig-off_days | nvarchar | YES |
| data_error | nvarchar | YES |
| reason_if_kpi_not_met | nvarchar | YES |
| remark_status_area_of_attention_issues_ | nvarchar | YES |
| rlmu_submitted_to_ho-date_with_in_7_days_from_actual_comm. | nvarchar | YES |
| flow_line_test_pack_completion_doc._submission_date_to_qs_dept. | nvarchar | YES |
| flow_line_test_pack_completion_progress | nvarchar | YES |
| over_all_progress_percentages | nvarchar | YES |
| ssfd_wells | nvarchar | YES |
| ipm | nvarchar | YES |
| access_road_5 | nvarchar | YES |
| earth_work_60 | nvarchar | YES |
| cellar_20 | nvarchar | YES |
| beam_pump_base_esp_pcp_foundation_5 | nvarchar | YES |
| earthing_1 | nvarchar | YES |
| septic_tank_1 | nvarchar | YES |
| water_2 | nvarchar | YES |
| waste_water_2 | nvarchar | YES |
| hdpe_liner_instalat_4 | nvarchar | YES |
| overall_loc._preparation_10_100 | nvarchar | YES |
| site_survey_5 | nvarchar | YES |
| survey_report_issue_5 | nvarchar | YES |
| design_sta_5 | nvarchar | YES |
| design_completed_issue_for_ta2_5_40 | nvarchar | YES |
| approved_by_15 | nvarchar | YES |
| afc_3_30 | nvarchar | YES |
| overall_engg._10_100 | nvarchar | YES |
| piping_mech_50 | nvarchar | YES |
| elect_30 | nvarchar | YES |
| instr_20 | nvarchar | YES |
| overall_material_10_100 | nvarchar | YES |
| cold_b_2 | nvarchar | YES |
| sleeper_pre_cast_ins_15 | nvarchar | YES |
| cs_pipe_welding_ndt_10_rt_for_op_100_for_60 | nvarchar | YES |
| pe_fussion_pull_20 | nvarchar | YES |
| final_hydro_t_3 | nvarchar | YES |
| overall_const._10_100 | nvarchar | YES |
| pole_hole_drill_40 | nvarchar | YES |
| pole_erect_40 | nvarchar | YES |
| conductor_string_18 | nvarchar | YES |
| ohl_ti_2 | nvarchar | YES |
| overall_ohl_progr_100 | nvarchar | YES |
| mechani_60 | nvarchar | YES |
| electri_15 | nvarchar | YES |
| instrumentat_20 | nvarchar | YES |
| overall_comm_mi_5 | nvarchar | YES |
| overall_comm_progress_100 | nvarchar | YES |
| location_preparation_status_in_progress_completed | nvarchar | YES |
| flow_line_const._status_in_progress_completed | nvarchar | YES |
| flow_line_commi._status_in_progress_completed | nvarchar | YES |
| well_year_white_space | nvarchar | YES |
| reasons_for_year_2018 | nvarchar | YES |
| column7 | nvarchar | YES |
| digital_wmr_import_remarks | nvarchar | YES |
| project_id | nvarchar | YES |
| Week_Number | nvarchar | YES |

### Key Columns (for joins)
- 
- 
- 
- 

### Sample Data (first 3 rows)
|sl_no|rig_no|well_location|well_name_after_spud|pdo_well_id|well_type|northing|easting|locationdd|flow_linedl|
|---|---|---|---|---|---|---|---|---|---|
|1.0|SWER103|AMIN_25869179_OP6|AMIN_25869179_OP6|31382|ESP|2033904.82|366874.29|C.AA.NIM.DD.03.WLC.GENRL|C.AA.NIM.DL.04.FLO.31382|
|1.0|SWER103|AMIN_3946610_OP23|AMIN_3946610_OP23|27365|ESP|2036109.46|366118.81|C.AA.NIM.DD.03.WLC.GENRL|C.AA.NIM.DL.04.FLO.27365|
|1.0|SWER103|AMIN_1673188_OP19|AMIN_1673188_OP19|36073|NULL|NULL|NULL|NULL|NULL|

---

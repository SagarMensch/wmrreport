# SequelForecast — 50 Stress-Test Questions

> **Purpose**: Test the full pipeline end-to-end: Natural Language → SQL → Data → Chart
> 
> **Difficulty**: 🟢 Hard → 🟡 Very Hard → 🔴 Brutal

---

## Category 1: Zero-Progress & Stalled Wells (Q1–Q8)

| # | Question | Why It's Hard |
|---|---|---|
| 1 | Which wells have made zero progress for two consecutive weeks? | Requires LAG window function on `cum_progress_for_this_week` comparing week-over-week |
| 2 | List all wells where current progress is exactly the same as last week's progress | Needs `cum_progress_for_this_week = last_week_cum_progress` comparison |
| 3 | Which wells have been stuck below 10% progress for more than 4 weeks? | Cross-join with historical weeks, COUNT + HAVING |
| 4 | Show me wells that had progress last month but have completely stalled this month | Temporal window: last 4 weeks vs prior 4 weeks, velocity = 0 |
| 5 | Find all wells where location preparation started but no construction progress has been made | Multi-column: `actual_start_date IS NOT NULL AND overall_const._10_100 = 0` |
| 6 | Which wells have rig-on date but zero flowline construction progress? | `actual_rig_on_date IS NOT NULL AND flowline_construction_progress = 0` |
| 7 | How many wells per rig have been stuck at the same progress for 3+ weeks? | GROUP BY rig_no + window function + HAVING |
| 8 | Which CRITICAL risk wells also have zero OHL progress? | Joins risk tier concept with `ohl_progress = 0` |

## Category 2: Multi-Metric Comparisons (Q9–Q16)

| # | Question | Why It's Hard |
|---|---|---|
| 9 | Compare planned vs actual progress for each rig | Needs Job_Progress_Report_GB join, plan vs actual variance |
| 10 | Show me the gap between engineering completion and commissioning start for each well | Date arithmetic: `actual_comm._start_date - actual_eng._completion_date` |
| 11 | What is the average time from rig-on to rig-off across all rigs? | `DATEDIFF(day, actual_rig_on_date, actual_rig_off_date)` + GROUP BY rig_no |
| 12 | Which wells have commissioning finished but overall progress below 90%? | Counter-intuitive filter: `actual_comm._finish_date IS NOT NULL AND over_all_progress < 0.9` |
| 13 | Compare the overall construction progress vs overall engineering progress for each well | Side-by-side: `overall_const._10_100` vs `overall_engg._10_100` |
| 14 | Show total planned wells vs completed wells per project | COUNT with CASE WHEN: total vs `over_all_progress >= 1.0` |
| 15 | What is the ratio of wells with engineering done vs wells with construction done? | Two aggregations: `SUM(CASE WHEN overall_engg >= 1) / SUM(CASE WHEN overall_const >= 1)` |
| 16 | For each rig, show the fastest and slowest well completion time | MIN/MAX of `DATEDIFF(actual_finish_date - actual_start_date)` per rig |

## Category 3: Time-Series & Trend Analysis (Q17–Q25)

| # | Question | Why It's Hard |
|---|---|---|
| 17 | Show me the weekly progress trend for rig SWER149 over the last 8 weeks | Needs week-level pivoting or time-series from WMR historical data |
| 18 | Which wells showed negative progress (went backwards) in any week? | `cum_progress_for_this_week < last_week_cum_progress` |
| 19 | What is the average weekly velocity for each project? | [(current_progress - lag_progress) / weeks](file:///c:/Users/sagar/Downloads/Bashira-Intelligence%20%282%29/Bashira-Intelligence/web/src/components/DecisionStudio.tsx#225-226) per project |
| 20 | Identify wells that accelerated in the last 2 weeks vs the prior 2 weeks | Velocity comparison across time windows |
| 21 | Show month-over-month completion count: how many wells hit 100% each month? | GROUP BY MONTH(actual_finish_date) + COUNT |
| 22 | Which rig improved its average progress the most in the last 4 weeks? | Requires two snapshots (current vs 4 weeks ago), diff per rig |
| 23 | Predict which wells will NOT complete by end of Q2 2026 based on current velocity | Extrapolation: [(1.0 - progress) / velocity > weeks_remaining](file:///c:/Users/sagar/Downloads/Bashira-Intelligence%20%282%29/Bashira-Intelligence/web/src/components/DecisionStudio.tsx#225-226) |
| 24 | What was the peak weekly progress across all wells and when did it happen? | MAX of weekly delta across entire dataset |
| 25 | Show cumulative wells completed over time as a running total | Window function: `SUM(completed) OVER (ORDER BY week)` |

## Category 4: Cross-Table & Deep JOINs (Q26–Q34)

| # | Question | Why It's Hard |
|---|---|---|
| 26 | Show me wells where the SAP drilling sequence expected rig-on date has passed but well hasn't started | JOIN WellMonitoringReport + SAP_DRILLING_SEQUENCE, date comparison |
| 27 | What is the crew productivity index for wells that are behind schedule? | JOIN PH_PRODUCTIVITY_WEEKLY_REPORT with WMR filtered by progress < expected |
| 28 | Which projects have the highest cost overrun based on JobCost data? | JOIN JobCost, compute (actual - planned) / planned per project |
| 29 | Show daily task completion rate for the last 7 days across all active rigs | JOIN task_daily + DailyPlanReport, GROUP BY date |
| 30 | Compare flowline construction progress with the flowline PO received date — which wells received POs months ago but have no progress? | Date diff: `DATEDIFF(month, f_l_po_recd._date, GETDATE()) > 3 AND flowline_construction_progress = 0` |
| 31 | For each rig, how many wells are in buffer status and what's their average progress? | Filter `buffer_status LIKE 'Buffer%'`, GROUP BY rig_no |
| 32 | Which wells have FLAF issued but no RAMZ ID received? | `flaf_issue_date IS NOT NULL AND ramz_id IS NULL` |
| 33 | Show the SAP drilling sequence for rig SWER103 with actual vs planned rig-on dates | JOIN SAP staging + WMR, side-by-side dates |
| 34 | Which wells have their engineering completion date but not their commissioning start date, and how many days ago was engineering done? | Multi-condition + DATEDIFF |

## Category 5: Aggregation & Ranking (Q35–Q42)

| # | Question | Why It's Hard |
|---|---|---|
| 35 | Rank all rigs by average well completion time from start to finish | RANK() OVER + DATEDIFF + AVG |
| 36 | Show the top 5 projects with the most CRITICAL and HIGH_RISK wells | Requires risk scoring logic + GROUP BY + ORDER BY |
| 37 | What percentage of all wells are ahead of schedule vs behind vs on track? | Three-bucket CASE WHEN based on expected vs actual progress |
| 38 | For each cluster, show total wells, average progress, and count by status | GROUP BY Cluster with multiple aggregations |
| 39 | Which 10 wells have the largest gap between expected rig-off date and today? | `DATEDIFF(day, exp.rig_off_location_sap_data, GETDATE())` + TOP 10 |
| 40 | Show me the distribution of wells by well_type with average progress per type | GROUP BY well_type + AVG + COUNT |
| 41 | What is the overall portfolio completion percentage weighted by project size? | Weighted average: `SUM(progress * weight) / SUM(weight)` |
| 42 | Which wells have data errors (rig_off before rig_on, comm before eng_completion)? | Multi-condition date validation checks |

## Category 6: Natural Language Edge Cases (Q43–Q50)

| # | Question | Why It's Hard |
|---|---|---|
| 43 | Show me everything about well NIMR-1621 | Ambiguous "everything" — should return all columns for one well |
| 44 | How are we doing overall? | Extremely vague — must decide what "overall" means (portfolio KPIs) |
| 45 | Why is rig SWERIG82 underperforming? | Requires reasoning, not just SQL — needs multi-metric comparison vs average |
| 46 | What should management focus on this week? | Open-ended — top risk wells + stalled wells + upcoming deadlines |
| 47 | Compare Nimr Flowline project vs Marmul Flowline project on all metrics | Multi-metric comparison between two filtered groups |
| 48 | Which wells are at risk of missing their rig-on target date? | Needs `latest_exp.rig_on_location_sap_data` approaching but no construction complete |
| 49 | Give me a summary suitable for a board presentation | Expects formatted KPIs: total wells, completion rate, risk distribution, rig rankings |
| 50 | If we add 2 more rigs to Nimr Flowline, how much faster would we complete? | Hypothetical — system should explain it can't simulate but show current rig utilization data |

---

## Recommended Testing Order

1. **Start with Q1, Q2, Q14, Q40** — Basic but common management questions
2. **Then Q9, Q11, Q13, Q30** — Multi-metric comparisons
3. **Then Q17, Q18, Q25** — Time-series (hardest for SQL generation)
4. **Then Q26, Q27, Q31** — Cross-table JOINs
5. **Then Q43–Q50** — Natural language edge cases (hardest for NLP)
6. **Finally Q35, Q36, Q23** — Ranking + prediction queries

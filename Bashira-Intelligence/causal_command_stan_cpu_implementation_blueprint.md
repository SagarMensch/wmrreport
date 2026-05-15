# Causal Command - CPU ML + Stan Implementation Blueprint

Version: 1.0  
Date: 31 March 2026  
Author: Codex / Product Engineering  
Status: Technical target design  
Companion document: `causal_command_stan_cpu_prd.md`

---

## 1. Purpose of This Document

This document turns the CPU ML + Stan PRD into an implementation-ready blueprint.

The PRD explains:

- why `CPU ML + Stan` is the right product architecture
- why Julia should be removed from the future design
- how Causal Command should integrate with the rest of the platform

This blueprint explains:

- what services need to exist
- what data contracts they should use
- what models should run in each layer
- how caching and refresh should work
- how the UI should consume the result
- how to migrate safely from the current system

This is the bridge between product intent and engineering execution.

---

## 2. Target Product Definition

The rebuilt Causal Command should be an enterprise management action layer that answers:

1. Which wells deserve management attention right now?
2. What are the strongest modeled causes of pressure on those wells?
3. Which governed intervention is most likely to recover time?
4. What is the credible range of recovery for that intervention?
5. How strong is the supporting evidence?
6. Is the recommendation weakened by poor source-data quality?

The product should not ask users to understand model internals. It should expose:

- ranked wells
- intervention choice
- expected recovery
- uncertainty
- support
- evidence quality

---

## 3. Architectural Principle

The architecture should separate:

- fast operational ranking
- slower posterior estimation

### 3.1 Fast layer

The fast layer should use CPU ML to:

- score all current wells
- rank opportunities
- generate candidate causes
- propose candidate interventions

### 3.2 Deep layer

The deep layer should use Stan to:

- estimate intervention-specific uplift
- pool sparse groups appropriately
- produce conservative / median / upside ranges
- attach uncertainty and evidence confidence

### 3.3 Why this split is correct

If Stan is placed in the hot path, the product will become too slow and operationally fragile.

If only CPU ML is used, the product will rank wells quickly but will remain weak on uncertainty and intervention credibility.

The split is therefore not optional. It is core to the design.

---

## 4. Target Service Layout

Recommended backend file structure:

```text
causal_command_service.py
causal_feature_builder.py
causal_cpu_models.py
causal_stan_service.py
causal_scenario_catalog.py
causal_confidence.py
causal_workspace_contract.py
stan_models/
  delay_uplift_hierarchical.stan
  pace_counterfactual_hierarchical.stan
  support_strength_model.stan
cache/
  causal/
```

### 4.1 `causal_command_service.py`

Responsibilities:

- orchestrate the full workspace
- fetch live data
- call feature builder
- call CPU ranking layer
- trigger or reuse Stan outputs
- merge everything into one response contract

### 4.2 `causal_feature_builder.py`

Responsibilities:

- live SQL joins
- grain normalization
- feature derivation
- join coverage calculation
- data quality linkage fields

### 4.3 `causal_cpu_models.py`

Responsibilities:

- baseline delay / opportunity scoring
- root-cause candidate ranking
- intervention candidate generation
- fallback operation if Stan cache is unavailable

### 4.4 `causal_stan_service.py`

Responsibilities:

- compile Stan models
- prepare modeling inputs
- run posterior refresh jobs
- persist summarized results
- return posterior summaries to orchestrator

### 4.5 `causal_scenario_catalog.py`

Responsibilities:

- define governed interventions
- declare editable levers
- define allowed parameter ranges
- map each scenario to its required features

### 4.6 `causal_confidence.py`

Responsibilities:

- combine posterior uncertainty
- support-case strength
- data integrity penalties
- join-grain penalties
- signal freshness penalties

### 4.7 `causal_workspace_contract.py`

Responsibilities:

- define the final API response structure
- enforce UI-safe naming
- remove engine-specific leakage from payloads

---

## 5. Data Model

The core modeling grain should be:

`one live well state row per current decision cycle`

This row should be enriched from historical and cross-system joins.

### 5.1 Primary identity

Recommended canonical keys:

- `well_id`
- `pdo_well_id` where available
- `project_id`
- `rig_no`
- `cluster`

### 5.2 Current-state fields

These are used for ranking and intervention logic:

- current progress
- delay vs target
- current month plan gap
- five-week plan concentration
- rig identity
- well type
- cluster
- backlog metrics
- material readiness signals
- engineering lag signals
- productivity signals
- activity/task concentration metrics

### 5.3 Historical-state fields

These are needed for comparable-case and posterior estimation:

- historical pace
- completion timing
- rig movement patterns
- plan-actual divergence trajectories
- task completion behavior
- PH productivity linkage where available

### 5.4 Data quality overlay

Each well state should carry:

- integrity exception count
- highest integrity severity
- affected domains
- whether decision-critical fields are degraded

That overlay will be consumed later by the confidence layer.

---

## 6. Feature System

The feature universe should be divided into five groups.

### 6.1 Portfolio pressure features

- `schedule_delay_days`
- `target_delay_days`
- `current_month_gap`
- `five_week_plan_pressure`
- `plan_concentration_score`
- `days_to_target`

### 6.2 Execution quality features

- `daily_task_completion_rate`
- `overdue_daily_tasks`
- `overdue_daily_remaining_duration`
- `weekly_execution_velocity`
- `execution_stall_flag`

### 6.3 Readiness features

- `material_lead_days`
- `material_ready_flag`
- `engg_kpi_days`
- `loc_prep_progress`
- `construction_readiness_gap`

### 6.4 Rig and cluster context features

- `rig_efficiency_weekly`
- `rig_historical_delay_profile`
- `cluster_density`
- `cluster_peer_pace`
- `well_type_peer_pace`

### 6.5 Evidence and trust features

- `support_case_count`
- `join_strength_score`
- `integrity_penalty_score`
- `source_freshness_score`

The system should distinguish:

- predictive features
- intervention-sensitive features
- trust-weighting features

Not every feature should be editable in counterfactual simulation.

---

## 7. CPU ML Layer Design

### 7.1 CPU ML objectives

The CPU layer should learn three things:

1. baseline delay pressure
2. root-cause contribution ranking
3. intervention opportunity ranking

### 7.2 Recommended CPU outputs

For each well:

- `baseline_delay_days`
- `decision_score`
- `primary_issue`
- `root_cause_stack`
- `candidate_actions`
- `support_case_count`
- `signal_quality`

### 7.3 Recommended model families

Use CPU-friendly models:

- LightGBM regressor for baseline delay / recoverable days
- LightGBM classifier for action urgency / weak-support detection
- SHAP-compatible tree models for local root-cause ranking

### 7.4 Why not use Stan here

Stan should not rank the entire portfolio inline. That would waste compute and slow the tab for no product gain.

### 7.5 CPU fallback mode

The CPU layer must be sufficient to render:

- portfolio brief
- intervention ladder
- baseline completion
- root-cause vector

even if no posterior refresh is available.

This is a hard requirement.

---

## 8. CPU ML Model Outputs

### 8.1 Baseline delay model

Target:

- delay days or expected slippage relative to target

Purpose:

- produce a rankable baseline pressure score

### 8.2 Recovery opportunity model

Target:

- recoverable days under governed intervention candidate patterns

Purpose:

- estimate which wells are most action-worthy

### 8.3 Root-cause model

Target:

- local contribution ranking for the current well state

Purpose:

- explain why the well is under pressure in operational language

---

## 9. Stan Layer Design

### 9.1 Stan objectives

Stan should estimate:

- baseline completion pressure under current state
- intervention uplift under governed action
- uncertainty around the uplift
- support-aware pooling across rigs, clusters, and stages

### 9.2 Why hierarchical structure is required

The portfolio is not homogeneous.

Different wells sit inside:

- different rigs
- different clusters
- different stages
- different support densities

Any model that ignores this will either:

- overfit noisy local groups
- or flatten meaningful differences

Stan should therefore use hierarchical random effects and partial pooling.

### 9.3 Recommended first Stan model

Model 1:

- hierarchical delay-uplift model

Target:

- residual delay days or remaining completion pressure

Indexing:

- rig
- cluster
- stage
- well_type

Intervention terms:

- peer pace recovery
- rig reassignment
- material acceleration
- decongestion
- backlog reduction

### 9.4 Conceptual form

```text
y_i ~ normal(mu_i, sigma)

mu_i =
  alpha
  + a_rig[rig_i]
  + a_cluster[cluster_i]
  + a_stage[stage_i]
  + a_welltype[welltype_i]
  + X_i * beta
  + T_i * tau
  + interaction(stage_i, T_i)
```

Where:

- `y_i` is expected remaining delay or pace-adjusted completion pressure
- `X_i` is the current operational feature vector
- `T_i` is a governed intervention coding
- `tau` is the average intervention effect

### 9.5 Posterior summaries required

For each well-action pair:

- `baseline_median_delay`
- `scenario_median_delay`
- `median_recovery_days`
- `recovery_p10`
- `recovery_p50`
- `recovery_p90`
- `credible_interval_low`
- `credible_interval_high`
- `posterior_confidence_score`

### 9.6 Support-aware pooling

The service should expose:

- raw support cases
- pooled group support class
- whether the action relies more on local evidence or portfolio borrowing

This matters for management trust.

---

## 10. Intervention Catalog

The intervention catalog should be code-defined and governed.

### 10.1 Initial actions

1. `peer_pace_recovery`
2. `higher_efficiency_rig`
3. `expedite_material_readiness`
4. `decongest_parallel_workfronts`
5. `reduce_overdue_daily_backlog`
6. `lift_daily_completion_rate`
7. `improve_linked_productivity`

### 10.2 Each scenario must define

- action code
- user-facing label
- description
- editable levers
- preconditions
- ineligible-state rules
- evidence requirements

### 10.3 Example scenario spec

```json
{
  "code": "higher_efficiency_rig",
  "label": "Reassign Higher-Efficiency Rig",
  "editable_levers": ["rig_efficiency_weekly"],
  "requires": ["rig_no", "cluster", "progress_band"],
  "minimum_support_cases": 8,
  "posterior_mode": "hierarchical_uplift"
}
```

---

## 11. Root Cause Layer

### 11.1 Product requirement

Root causes should be expressed in business language, not raw feature IDs.

### 11.2 Translation layer

The system should map modeled features to business concepts such as:

- rig efficiency gap
- material readiness lag
- concentrated near-term plan pressure
- backlog drag
- low daily completion rate
- productivity gap
- engineering lag after rig-off

### 11.3 Root-cause scoring

Recommended structure:

- CPU ML produces local driver magnitude
- mapping layer turns drivers into business labels
- Stan does not rank root causes directly but validates scenario-level intervention credibility

### 11.4 Output format

Each root cause item should include:

- label
- narrative
- direction
- days-equivalent contribution estimate if available
- evidence support note

---

## 12. Confidence Framework

This is one of the most important layers in the rebuilt system.

### 12.1 Final confidence should not come from one thing

Confidence should combine:

1. posterior interval width
2. support-case strength
3. local-vs-pooled reliance
4. data integrity penalties
5. join-grain penalties
6. freshness penalties

### 12.2 Proposed confidence classes

- `High`
- `Moderate`
- `Cautious`
- `Weak Support`

### 12.3 Example penalty logic

If:

- support cases are low
- integrity is degraded
- interval is wide

then action should still appear if the uplift is large, but it should be labeled as weak-support rather than hidden.

---

## 13. Cache and Refresh Strategy

### 13.1 Cache layers

Use three cache layers:

1. joined dataset cache
2. CPU workspace cache
3. Stan posterior summary cache

### 13.2 Refresh cadence

Suggested:

- joined dataset: 5 to 10 minutes
- CPU ranking: every joined dataset refresh
- Stan posterior refresh: on a slightly slower cadence or event-triggered

### 13.3 On-demand refresh

Support a targeted deep refresh for:

- a specific well
- a specific scenario
- a management drilldown action

### 13.4 Cold start behavior

If Stan summaries are absent:

- return CPU workspace immediately
- mark posterior layer as warming
- do not block the tab

---

## 14. API Contract

The UI should continue to receive one unified workspace contract.

### 14.1 Top-level response fields

```json
{
  "generated_at": "...",
  "workspace_name": "Causal Command",
  "objective": "...",
  "analysis_status": {},
  "data_health": {},
  "interactive": {},
  "gaps": []
}
```

### 14.2 Required `interactive` sections

- `portfolio_brief`
- `intervention_ladder`
- `wells`
- `top_drivers`
- `scenario_catalog`
- `feature_lineage`

### 14.3 Well object requirements

Each well should include:

- identity
- baseline completion
- baseline pace
- benchmark scope
- root causes
- scenarios
- confidence
- evidence source trace
- data quality flags

### 14.4 Scenario object requirements

Each scenario should include:

- code
- label
- baseline date
- scenario date
- expected recovery days
- conservative / median / upside
- support cases
- confidence label
- explanation note
- posterior interval

---

## 15. Frontend Product Behavior

### 15.1 First-screen behavior

The tab should load with:

- portfolio brief
- top action
- actionable wells
- top risk cluster
- weak support count
- ranked ladder

without waiting for deep recomputation.

### 15.2 Simulator behavior

When a user chooses a scenario:

- baseline should remain visible
- scenario changes should be explicit
- uncertainty should be shown directly
- evidence support should remain visible

### 15.3 Root-cause presentation

The root-cause vector should show:

- biggest modeled gaps first
- one-line business explanation
- support note

### 15.4 Wording rules

Do not use:

- Julia
- experimental
- black box
- latent tensor
- generic AI filler

Use:

- baseline
- peer benchmark
- posterior interval
- support cases
- confidence
- evidence strength

---

## 16. Integration with Decision Studio

### 16.1 Shared signals

Decision Studio already calculates:

- risk probability
- risk tier
- predicted completion timing
- progress state
- survival metrics

### 16.2 Integration contract

Causal Command should import from Decision Studio:

- current risk tier
- predicted completion baseline
- current progress state
- selected high-signal features when aligned

### 16.3 Product role split

- Decision Studio = predictive portfolio intelligence
- Causal Command = action and intervention intelligence

This separation should remain clear.

---

## 17. Integration with Predictive Studio

### 17.1 Shared concepts

Predictive Studio already contains:

- baseline completion date
- pace
- root-cause framing
- simulator framing

### 17.2 Integration contract

Causal Command should align with Predictive Studio on:

- scenario labels
- baseline completion definitions
- comparable-case language
- support-case language

### 17.3 Product role split

- Predictive Studio = execution cockpit
- Causal Command = management intervention cockpit

---

## 18. Integration with Data Integrity

### 18.1 Why this matters

Data Integrity should directly influence action confidence.

### 18.2 Required inputs

For each well or project scope:

- open critical integrity issues
- affected tables
- affected signal domains
- severity score

### 18.3 Output behavior

If integrity degradation affects a scenario:

- reduce confidence label
- show warning note
- show affected source domain

### 18.4 Example

If backlog reduction is recommended but `task_daily` integrity is degraded, the platform should say:

`Scenario remains directionally useful, but confidence is reduced because linked task execution capture is incomplete.`

---

## 19. Recommended Stan Refresh Modes

### 19.1 Portfolio refresh

Nightly or scheduled:

- refresh posterior baselines for the current live portfolio

### 19.2 On-demand scenario refresh

When a user drills into a specific well and action:

- compute or reuse targeted posterior summaries

### 19.3 Offline model refresh

Less frequent:

- retrain / recalibrate model structures
- reassess priors and pooling choices

---

## 20. Migration Plan from Current System

### Phase A - Stabilize current CPU path

Tasks:

- isolate current CPU ranking logic
- clean payload contract
- remove Julia language from the UI contract

### Phase B - Introduce Stan service in shadow mode

Tasks:

- build Stan inputs from same dataset
- run posterior summaries without exposing them yet
- compare outputs against current enrichment behavior

### Phase C - Expose posterior summaries

Tasks:

- add conservative / median / upside
- add confidence labels
- add support-aware notes

### Phase D - Remove Julia dependency

Tasks:

- cut Julia code path
- remove runtime and monitoring dependencies
- simplify deployment story

---

## 21. Engineering Acceptance Tests

### 21.1 CPU path tests

- full workspace returns without Stan cache
- ladder sorts correctly
- root causes map to business labels

### 21.2 Stan path tests

- posterior summaries generated for supported actions
- intervals remain ordered and valid
- sparse groups use pooled behavior instead of exploding

### 21.3 Integration tests

- Decision Studio signals map correctly
- Data Integrity penalties affect confidence
- Predictive Studio scenario labels stay aligned

### 21.4 UX tests

- first render remains fast
- no Julia wording remains
- management can understand outputs without technical explanation

---

## 22. Recommended Delivery Sequence

### Sprint 1

- finalize data contract
- isolate current CPU ranking layer
- create scenario catalog module

### Sprint 2

- implement feature builder and confidence layer
- stand up Stan service in shadow mode

### Sprint 3

- expose posterior summaries in API
- wire uncertainty and support into UI

### Sprint 4

- integrate Data Integrity penalties
- align with Decision Studio and Predictive Studio
- remove Julia wording and then Julia runtime path

---

## 23. Final Engineering Recommendation

The best technical direction is:

- keep the current workspace-oriented service pattern
- keep CPU ML as the portfolio-scale hot path
- add Stan as the posterior counterfactual engine
- integrate confidence with Data Integrity
- align product language across Decision Studio, Predictive Studio, and Causal Command
- remove Julia from the target architecture completely

This gives the platform:

- fast operational usability
- strong management credibility
- principled uncertainty
- cleaner product positioning
- better long-term maintainability


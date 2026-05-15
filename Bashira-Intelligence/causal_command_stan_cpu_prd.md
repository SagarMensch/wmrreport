# Causal Command PRD - CPU ML + Stan Architecture

Version: 1.0  
Date: 31 March 2026  
Author: Codex / Product Engineering  
Status: Proposed target architecture  
Classification: Internal product design

---

## 1. Executive Summary

This document defines the target product design for rebuilding `Causal Command` as a dual-engine decision system based on:

- fast CPU machine learning for operational ranking and pattern detection
- Stan-based Bayesian modeling for governed counterfactual estimation and uncertainty

The goal is to remove Julia from the product architecture and replace it with a more explainable, auditable, and management-friendly hybrid system.

The result should be a decision surface that can do four things at the same time:

1. rank wells quickly across the live portfolio
2. explain the strongest current drivers of delay pressure
3. simulate governed interventions with uncertainty bands
4. integrate cleanly with Decision Studio, Predictive Studio, and Data Integrity

This is not a pure academic causal-inference platform. It is an enterprise operational decision product. The correct design is:

- CPU ML for speed, scale, ranking, and non-linear interaction capture
- Stan for posterior uncertainty, hierarchical pooling, and counterfactual credibility

That combination is more powerful than CPU heuristics alone and more practical than a pure Bayesian-only serving stack.

---

## 2. Product Thesis

### 2.1 Why CPU ML + Stan is stronger than the current shape

`Causal Command` currently already has a split between:

- a fast operational CPU layer
- a slower enrichment layer

That is the right structure. The weakness is not the split itself. The weakness is that the deeper layer is currently tied to Julia, which increases operational complexity and creates product explanation overhead.

The proposed target architecture keeps the good part and replaces the fragile part:

- keep the fast CPU ranking path
- replace Julia enrichment with Stan posterior inference

This gives the product:

- faster first response
- stronger governance
- better auditability
- clearer uncertainty communication
- more defensible management language

### 2.2 Why this matters for Al Tasnim

Al Tasnim does not need a lab model. It needs a management decision surface that answers:

- which well needs intervention now
- why that well is under pressure
- what action is most likely to recover time
- how much recovery is realistically available
- how confident the platform is in that recommendation

CPU ML answers the first three well. Stan answers the last two well.

---

## 3. Product Goals

### 3.1 Primary goals

1. Deliver a live ranked decision deck over current wells.
2. Show operational root causes in business language, not generic feature names.
3. Simulate governed interventions such as rig reassignment, material acceleration, execution-pace recovery, and workfront decongestion.
4. Return conservative, median, and upside recovery estimates.
5. Expose support strength, uncertainty, and evidence quality for each recommendation.
6. Integrate with the rest of Bashira Intelligence so the platform feels like one system, not disconnected tabs.

### 3.2 Non-goals

1. This is not a fully automatic optimizer that dispatches crews or rigs.
2. This is not a claim of perfect causality from observational data.
3. This is not a real-time MCMC system that resamples on every click.
4. This is not a Julia-dependent analytics product.

---

## 4. Product Principles

### 4.1 Fast first response

The first management view must load quickly from a CPU-scored cached workspace.

### 4.2 Explicit uncertainty

Every counterfactual recommendation should expose a posterior range, not a single point value only.

### 4.3 Governed interventions only

The product should simulate a known intervention catalog, not arbitrary unconstrained parameter edits.

### 4.4 Source-linked evidence

All model signals should map back to live SQL joins and source-traceable fields.

### 4.5 Operational realism

The product must prefer robust decision support over flashy but brittle modeling.

---

## 5. Why Stan Specifically

Stan is proposed because it solves the exact class of problems that Causal Command needs to solve well.

### 5.1 Hierarchical partial pooling

The platform operates across:

- rigs
- clusters
- stages
- well types
- project contexts

These segments are uneven. Some have strong support, some are sparse. Stan lets us estimate effects with partial pooling:

- strong segments retain their own behavior
- sparse segments borrow strength from the wider population

That is far more stable than flat segment averages or overfit local models.

### 5.2 Posterior uncertainty

Management decisions should not be driven by a single "recover 27 days" number with no uncertainty.

Stan gives:

- posterior median
- credible intervals
- posterior distributions of intervention effects

That means Causal Command can say:

- conservative recovery
- central estimate
- upside recovery

instead of pretending certainty where none exists.

### 5.3 Stronger treatment-effect framing

Stan is well suited to modeling:

- baseline outcome
- treatment uplift
- interaction by stage or rig
- uncertainty around all of the above

This makes it a strong engine for governed counterfactual simulation.

### 5.4 Better executive defensibility

For client-facing explanation, "Bayesian hierarchical counterfactual model with uncertainty intervals" is more defensible than a black-box enrichment process.

### 5.5 Cleaner Windows and deployment story than maintaining Julia as a product dependency

Stan via Python integration can live inside the same service and deployment ecosystem already used by the rest of the stack.

---

## 6. Why CPU ML Specifically

CPU ML remains essential. Stan should not replace it.

### 6.1 Fast full-portfolio ranking

We need to score many wells quickly on every refresh.

Tree-based CPU models are strong for:

- non-linear relationships
- mixed structured operational features
- fast inference
- simple caching

### 6.2 Root-cause pattern detection

CPU ML can extract:

- feature importance
- SHAP-style local explanations
- baseline delay predictions
- candidate intervention ranking

### 6.3 Robust fallback path

Even if Stan refresh is delayed or unavailable, the CPU decision layer can still serve the management deck.

### 6.4 Lower serving latency

The UI should never wait for deep posterior sampling to render the first screen.

---

## 7. Why CPU ML + Stan Together Is the Most Powerful Version

The two engines solve different layers of the same decision problem.

### 7.1 CPU ML solves

- Which wells should management look at first?
- Which signals are currently strongest?
- Which governed scenarios appear promising?
- Which wells have weak support or high operating pressure?

### 7.2 Stan solves

- How much uplift should we expect if we intervene?
- How uncertain is that uplift?
- How much of the estimate is specific to this rig, stage, and cluster versus pooled from the broader portfolio?
- Which interventions are robust versus only optimistic?

### 7.3 Combined product effect

Together they create a decision surface that is:

- fast
- ranked
- explainable
- uncertainty-aware
- operationally useful

That is the strongest realistic product design for this use case.

---

## 8. Current Integration Points in the Repo

The current codebase already gives a strong structural base for this migration.

### 8.1 Frontend

- `web/src/components/CausalCommand.tsx`
- `web/src/app/api/causal/route.ts`

The frontend already expects a unified causal workspace payload and can continue to do so.

### 8.2 Backend decision workspace

- `causal_command_service.py`

This file already:

- builds a joined dataset
- runs a fast CPU analysis
- assembles the workspace
- exposes an enrichment slot

This is the correct place to preserve the fast path and swap the enrichment strategy.

### 8.3 Existing CPU operational logic

- `cpu_ml_orchestrator.py`

This file already contains useful CPU-side ideas around:

- risk modeling
- comparable-case logic
- schedule pressure
- execution pace
- scenario framing

Those patterns should be reused, not discarded.

---

## 9. Proposed Target Architecture

### 9.1 Overview

The target architecture should be:

1. SQL data assembly layer
2. feature store / modeling frame builder
3. CPU ML ranking layer
4. Stan posterior counterfactual layer
5. workspace assembler
6. frontend presentation layer

### 9.2 Runtime model

#### Hot path

On dashboard load:

1. build or retrieve cached live dataset
2. score all wells using CPU ML
3. assemble ranked deck immediately
4. return to frontend

#### Warm path

In the background:

1. run or refresh Stan posterior estimates
2. merge posterior summaries into the same workspace
3. refresh counterfactual panels and confidence fields

This preserves responsiveness while enabling deeper reasoning.

---

## 10. Data Sources for Causal Command

The product should continue to rely on live joined SQL sources, including the current set already used by the service:

- `WMR_Full`
- `WellMonitoringReport_Latest` / current WMR latest view
- `Job_Progress_Report_GB`
- `Job_Progress_PlanSnapshot`
- `task_daily`
- `SAP_DRILLING_SEQUENCE`
- `ActivityTaskPlan`
- PH productivity linkage where available

### 10.1 Canonical entity

Primary well identity should be standardized and consistent across the joined dataset.

### 10.2 Join philosophy

The product should keep:

- source-traceable joins
- explicit coverage reporting
- join-grain warnings where mappings are not one-to-one

This is important for trust and for integration with Data Integrity.

---

## 11. CPU ML Layer Design

### 11.1 Purpose

The CPU ML layer is responsible for:

- baseline delay prediction
- intervention ranking
- root-cause feature scoring
- decision ladder generation
- fallback operation when Stan is unavailable

### 11.2 Recommended model families

Use CPU-friendly gradient-boosting and tabular models such as:

- LightGBM
- XGBoost on CPU where helpful
- calibrated logistic / survival-style auxiliary models where needed

### 11.3 CPU ML outputs

For each well:

- baseline delay days
- decision score
- primary issue
- ranked root-cause features
- candidate scenarios
- support-case count
- signal quality / evidence quality

### 11.4 Why CPU ML should stay primary on the ranking side

Ranking every well in the live portfolio is better handled by fast tabular ML than by running a full Bayesian layer inline.

---

## 12. Stan Layer Design

### 12.1 Purpose

The Stan layer is responsible for:

- estimating governed intervention effects
- producing uncertainty intervals
- stabilizing sparse segment behavior through hierarchical pooling
- giving management-grade posterior summaries

### 12.2 Core Stan problem to solve

For a well and a governed action, estimate:

- baseline expected completion delay
- intervention-adjusted expected completion delay
- recovery days
- posterior uncertainty

### 12.3 Proposed model shape

At the first usable version, model delay or weekly execution pace as a hierarchical function of:

- rig
- cluster
- stage
- well type
- progress state
- schedule pressure
- material readiness
- execution backlog
- productivity signals

Then include intervention terms such as:

- rig reassignment effect
- material lead-time reduction effect
- peer-pace recovery effect
- workfront decongestion effect

### 12.4 Example conceptual form

```text
y_i ~ Normal(mu_i, sigma)

mu_i =
  alpha
  + rig_effect[rig_i]
  + cluster_effect[cluster_i]
  + stage_effect[stage_i]
  + beta * x_i
  + tau[action_i]
  + gamma[action_i, stage_i]
```

Where:

- `y_i` can be delay days or weekly pace
- `x_i` is the engineered operational feature vector
- `tau` is the intervention uplift term
- `gamma` captures stage-specific treatment interaction

### 12.5 Stan outputs

For each well-action pair:

- posterior median recovery days
- lower credible bound
- upper credible bound
- posterior confidence
- pooled support strength

### 12.6 Serving format

The Stan layer should return summaries only, not raw chains, to the main product payload.

---

## 13. Counterfactual Design

### 13.1 Governed intervention catalog

The simulator should only allow actions that are operationally interpretable and supported by data.

Initial catalog:

1. Recover to peer execution pace
2. Reassign higher-efficiency rig
3. Expedite material readiness
4. Decongest parallel workfronts
5. Close overdue daily backlog
6. Lift daily task completion rate
7. Improve linked productivity toward peer band

### 13.2 Counterfactual output schema

Each scenario should return:

- scenario code
- scenario label
- baseline completion date
- scenario completion date
- expected recovery days
- conservative recovery
- median recovery
- upside recovery
- support cases
- confidence label
- explanation note

### 13.3 Why Stan is a better fit here

The simulator should not present point-estimate optimism as fact.

Stan lets the simulator say:

- low-confidence uplift
- moderate-confidence uplift
- high-confidence uplift

That is far better for executive decision support.

---

## 14. Root Cause Engine Design

### 14.1 Root cause should not be generic feature importance

The product should translate features into operational language:

- rig efficiency gap
- material readiness lag
- execution backlog concentration
- schedule pressure misalignment
- productivity drag
- plan compression

### 14.2 CPU ML role in root-cause detection

CPU ML should generate:

- ranked local drivers for the current well
- baseline contribution direction
- supporting evidence from comparable patterns

### 14.3 Stan role in root-cause validation

Stan should not replace the ranking of candidate drivers. It should help stabilize and uncertainty-qualify the actionable intervention effects associated with those drivers.

---

## 15. UI Product Changes for Causal Command

### 15.1 Remove Julia from the product vocabulary

The future product must not show:

- Julia enrichment
- Julia warming
- Julia diagnostics
- Julia runtime paths

### 15.2 Replace with product-safe language

Use:

- `CPU decision layer ready`
- `Bayesian counterfactuals current`
- `Posterior intervals current`
- `Scenario engine current`
- `Confidence refreshed`

### 15.3 Panel design

The tab should clearly expose:

1. Portfolio brief
2. Ranked intervention ladder
3. Root cause vector
4. Counterfactual simulator
5. Evidence / support panel
6. Confidence / uncertainty strip

### 15.4 Confidence presentation

Each intervention result should show:

- point estimate
- credible interval
- support cases
- evidence strength

This is one of the biggest product upgrades over the current design.

---

## 16. Backend Service Design

### 16.1 Proposed service structure

Keep the current workspace-oriented service pattern but redesign the enrichment path.

Recommended modules:

- `causal_command_service.py`
- `causal_feature_builder.py`
- `causal_cpu_models.py`
- `causal_stan_service.py`
- `stan_models/`

### 16.2 Proposed backend workflow

1. Load live SQL frames
2. Build unified well-level modeling dataset
3. Run CPU ML scoring across current wells
4. Assemble fast decision workspace
5. Trigger or reuse Stan posterior summaries
6. Merge posterior scenario outputs
7. Return one clean workspace payload to the UI

### 16.3 Stan execution mode

Do not run full posterior inference on every click.

Use:

- scheduled refresh
- cache reuse
- selective scenario recomputation for focused analysis

### 16.4 Recommended Python integration

Use `CmdStanPy` for orchestration from Python so the product remains in the same ecosystem as the rest of the backend.

---

## 17. Integration with Decision Studio

Decision Studio and Causal Command should not operate as separate modeling universes.

### 17.1 What Decision Studio provides

Decision Studio already produces:

- progress predictions
- weeks-to-completion predictions
- risk probabilities
- tiering
- feature importance
- survival outputs

### 17.2 How Causal Command should use that

Causal Command should consume Decision Studio outputs as priors, context, or conditioning signals, not duplicate them blindly.

Examples:

- use Decision Studio risk tier as a portfolio-priority prior
- use predicted completion window as baseline planning context
- use progress-state features from the same governed feature universe

### 17.3 Product advantage

This creates a clean flow:

- Decision Studio tells you which wells are likely to slip
- Causal Command tells you what to do about it

---

## 18. Integration with Predictive Studio

Predictive Studio is the operational execution cockpit. Causal Command should integrate with it directly.

### 18.1 What Predictive Studio provides

- current execution state
- baseline pace
- root-cause surface
- what-if scenario framing

### 18.2 How Causal Command should use it

- import current pace and comparable-case baseline context
- align intervention names and explanation language
- let users move from predictive signal to management action without mental translation

### 18.3 Product advantage

This creates a progression:

- Predictive Studio explains current operating state
- Causal Command converts it into a management decision

---

## 19. Integration with Data Integrity

This integration is critical.

### 19.1 Why

Bad source data should reduce confidence in causal recommendations.

### 19.2 Required behavior

If a well is affected by high-severity integrity exceptions:

- lower confidence label
- show data-quality warning in the scenario result
- expose which source domain is affected

### 19.3 Example

If Task Daily execution fields are incomplete for a well, and the recommended action depends on execution-rate signals, the product should explicitly say that the recommendation carries reduced confidence.

### 19.4 Product advantage

This makes the platform self-governing:

- not just predictive
- not just causal
- also trust-aware

---

## 20. Integration with Operations and Conversations

### 20.1 Operations integration

Actions proposed in Causal Command should be transferable to operational follow-up views:

- well
- recommended intervention
- expected recovery
- confidence
- evidence support

### 20.2 Conversational integration

The command bar should support prompts like:

- highest recovery well
- show weak-support interventions
- compare peer pace vs rig reassignment
- wells where data quality reduces confidence

This makes the tab feel like a command surface, not just a dashboard.

---

## 21. Product Data Contract

The UI should receive one workspace contract containing:

- generated time
- objective
- portfolio brief
- ladder of ranked wells
- per-well baseline
- per-well root causes
- per-well scenarios
- posterior uncertainty
- support counts
- confidence labels
- data-quality adjustments

The frontend should not have to know whether the deeper layer came from Stan internals. It should read a clean product contract only.

---

## 22. Migration Away from Julia

### 22.1 Product decision

Julia is removed from the target design.

### 22.2 What that means

- no Julia runtime requirement in product messaging
- no Julia status state in UI
- no Julia-specific enrichment terminology
- no Julia dependency in target architecture

### 22.3 Technical migration path

1. Preserve CPU workspace builder.
2. Introduce Stan service in parallel.
3. Mirror Julia output schema with Stan summaries.
4. Cut UI wording over to CPU + Bayesian language.
5. Remove Julia-specific service code after parity is achieved.

---

## 23. Phased Delivery Plan

### Phase 1 - CPU ML foundation

Deliver:

- stable joined well dataset
- fast baseline delay model
- ranked ladder
- root-cause scoring
- governed intervention catalog

### Phase 2 - Stan posterior layer

Deliver:

- hierarchical intervention-effect model
- credible intervals
- support strength
- posterior scenario summaries

### Phase 3 - Cross-tab integration

Deliver:

- Decision Studio prior alignment
- Predictive Studio signal alignment
- Data Integrity confidence gating

### Phase 4 - Product polish

Deliver:

- premium wording
- audit panel
- exportable scenario memos
- management-grade explanation flow

---

## 24. Success Metrics

The product should be considered successful when it achieves:

### Operational metrics

- under 3 seconds for cached CPU decision deck load
- under 10 seconds for focused scenario refresh from cached Stan summaries
- stable ranked ladder across normal refreshes

### Modeling metrics

- clear ranking separation between high- and low-recovery interventions
- posterior intervals narrow enough to be decision-useful
- stronger stability in sparse segments than the current non-Bayesian approach

### Product metrics

- management can explain why an action is recommended
- users can distinguish high-confidence from weak-support recommendations
- causal panel language feels institutional, not experimental

---

## 25. Risks and Mitigations

### Risk 1 - Overclaiming causality

Mitigation:

- use governed intervention language
- expose uncertainty
- document assumptions

### Risk 2 - Stan runtime too slow

Mitigation:

- run in background
- cache summaries
- use targeted refresh rather than full recomputation per click

### Risk 3 - Data grain mismatch across tables

Mitigation:

- preserve join coverage reporting
- surface grain caveats in evidence panels
- integrate with Data Integrity confidence adjustments

### Risk 4 - Too much model complexity for users

Mitigation:

- show only decision-relevant summaries
- hide implementation detail behind clear labels

---

## 26. Acceptance Criteria

The rebuilt Causal Command is acceptable only if:

1. The initial deck loads from CPU scoring without waiting for posterior inference.
2. Each recommended intervention shows recovery plus uncertainty.
3. Each intervention shows support strength.
4. The UI contains no Julia-facing terminology.
5. Causal Command reads as a management system, not a research page.
6. The tab integrates with Decision Studio, Predictive Studio, and Data Integrity.
7. The product can explain why a given well is ranked where it is.

---

## 27. Final Recommendation

`Causal Command` should be rebuilt as:

- a fast CPU ML operational ranking engine
- paired with a Stan Bayesian counterfactual engine
- integrated with the rest of the platform as the action layer

This is the strongest realistic architecture because it combines:

- speed
- ranking quality
- operational realism
- uncertainty awareness
- management-grade explainability

That is the right product direction.


# P21 Usability Regression

Date: 2026-03-23  
Task: `P21-I008`  
Status: `completed_on_power_shell_lane`

## Bottom Line

The current operator workflow is now coherent enough to use end to end on the PowerShell lane, but it is still not low-friction.

The replayed evidence says the product is:

- truthful,
- internally aligned,
- workflow-complete enough for careful users,
- but still too artifact-heavy for smooth first-pass scientific use.

That is an improvement over earlier phases, because the main failure mode is no longer "missing core workflow pieces." It is now "too much interpretation overhead for a new operator."

## Evidence Used

This regression is grounded in the already-landed workflow surfaces:

- `docs/reports/p20_user_sim_regression.md`
- `docs/reports/p20_acceptance_matrix.md`
- `docs/reports/p21_onboarding_friction.md`
- `docs/reports/p21_operator_workflow_parity.md`
- `runs/real_data_benchmark/full_results/user_sim_regression.json`
- `scripts/operator_recipes.ps1`
- `scripts/dataset_design_wizard.py`
- `scripts/export_provenance_drilldown.py`
- `scripts/review_workspace.py`

## Replay Summary

The replayed operator path now has a clean shape:

1. Start from the operator surface and recipe commands
2. Move into dataset design
3. Inspect provenance drilldown
4. Review batch triage and acceptance outcomes

That flow is now internally consistent on the PowerShell lane.

The key live counts remain:

- user-sim workflows: `6`
- supported workflows: `1`
- weak workflows: `4`
- blocked workflows: `1`
- dataset-design proposals: `12`
- supported proposals: `1`
- weak proposals: `1`
- blocked proposals: `10`
- provenance drilldown unresolved lanes: `80`

## What Feels Better Now

The operator no longer has to guess whether the workflow surfaces agree with each other.

The positive changes are:

- recipe commands now give a clear workflow entrypoint
- dataset design produces deterministic proposal states instead of ad hoc interpretation
- provenance drilldown keeps missing modalities and empty pair hits explicit
- review workspace gives a concrete promoted / weak / blocked triage grouping
- the WinUI handoff is aligned to the same contract rather than drifting into a second model

This means the workflow is now structurally usable for a careful maintainer or power user.

## Where Friction Still Shows Up

The main friction points remain:

- only `1/6` replayed workflows is fully supported
- only `1/12` current cohort proposals is strong enough to be treated as supported
- the operator still has to traverse multiple artifacts to answer simple trust questions
- the front door is still more state-oriented than question-oriented
- the blocked WinUI environment keeps the future desktop lane in documentation-only mode

In practical terms, the operator can complete the workflow, but still needs repo familiarity to do it confidently.

## Usability Judgment By Lane

### Supported

- acceptance review and rich-coverage dataset planning for `P69905`

This lane is usable and conservative at the same time.

### Weak but usable

- probe-backed or thin-evidence review
- partial packet planning
- prototype-bound benchmark interpretation

These lanes are good enough for expert users who understand the truth boundary.

### Blocked

- weeklong-soak interpretation as completed operational proof
- live WinUI runtime use in the current environment

These remain correctly blocked and should stay blocked until real evidence exists.

## Truth Boundary

This regression does not claim:

- release readiness
- full GUI parity at runtime
- friction-free onboarding
- weeklong unattended durability

It does claim that the current PowerShell-first workflow is now complete enough to replay, evaluate, and critique as one joined operator path.

## Recommended Next Work

The next highest-value usability work is not another core backend.

The biggest wins now are:

- a clearer front-door operator quickstart
- stronger in-surface pointers to acceptance, packet, and provenance views
- a guided interpretation layer for supported / weak / blocked states
- eventual WinUI realization once the environment blocker is truly cleared

## Outcome

`P21-I008` is complete as a truthful usability regression on the current operator lane.

The result is encouraging: the workflow is usable now, but still not easy enough to treat as release-polished.

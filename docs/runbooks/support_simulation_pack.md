# Support Simulation Pack

This runbook is a report-only simulation pack for support and release operations. It is designed to rehearse the most likely incident paths without claiming release readiness or mutating release authorization state.

## Scope

The simulation pack covers four incident classes:

1. `install` and cold-start bootstrap
2. `packet` and packaging deficits
3. `benchmark` and release-grade blockers
4. `recovery` and state restoration after an upgrade or failed transition

Each scenario is intentionally framed against the current prototype truth boundary. The pack should help support staff, reviewers, and operators answer: what is broken, what is partial, what is blocked, and what is safe to retry.

## Current Truth Boundary

The current release posture remains blocked on the release-grade bar. The simulation pack must preserve that honesty.

Observed blockers and limits:

- runtime maturity remains prototype-level
- source coverage depth is still incomplete for the full corpus
- provenance and reporting depth are still blocked on the release-grade bar
- the RC bundle remains `assembled_with_blockers`
- the reference training lane remains summary-only
- schema upgrade and rollback are auditable, but the tagged versioned release lineage is not fully materialized in-tree

## Incident Scenarios

### 1. Install Incident

Objective: verify that a clean machine or fresh checkout can bootstrap without silently skipping prerequisites.

What to check:

- required runtime entrypoints exist
- bootstrap dependencies are present
- the repo can produce a machine-readable install state
- the install path fails closed when prerequisites are missing

Expected support response:

- confirm whether the failure is environmental or repository-local
- point to the bootstrap state artifact
- avoid suggesting production readiness

Relevant evidence:

- `artifacts/status/install_bootstrap_state.json`
- `scripts/install_proteosphere.py`

### 2. Packet Incident

Objective: verify that packet deficits are surfaced honestly and that partial packets do not get treated as complete.

What to check:

- packet counts are visible in the dashboard
- partial packets are listed explicitly
- modality deficits are identified
- source-fix candidates are surfaced without silently widening the cohort

Expected support response:

- identify the missing modality or source lane
- point to the relevant packet deficit dashboard
- avoid auto-promoting partial packets to complete

Relevant evidence:

- `artifacts/status/packet_deficit_dashboard.json`
- `data/packages/LATEST.json`
- `runs/real_data_benchmark/full_results/run_manifest.json`

### 3. Benchmark Incident

Objective: verify that benchmark failures remain explicit and block release claims.

What to check:

- benchmark status is visible in the operator dashboard
- blocker categories are preserved verbatim
- release-grade status remains blocked when the runtime is still prototype-level
- smoke runs and reference pipelines remain partial when the backend is summary-only

Expected support response:

- explain which blocker category is active
- distinguish `prepared` from `release-ready`
- preserve the release-grade blocker language in notes and manifests

Relevant evidence:

- `runs/real_data_benchmark/full_results/release_bundle_manifest.json`
- `runs/real_data_benchmark/full_results/release_notes.md`
- `runs/real_data_benchmark/full_results/release_support_manifest.json`
- `runs/real_data_benchmark/full_results/summary.json`
- `artifacts/status/P1-I019.json`
- `artifacts/status/P1-I020.json`

### 4. Recovery Incident

Objective: verify that schema migration and rollback remain lineage-aware and fail closed.

What to check:

- forward schema migration is additive-only
- rollback requires matching release lineage
- missing lineage artifacts block recovery
- partial output is removed rather than orphaned when recovery is unsafe

Expected support response:

- inspect the source and versioned release manifests
- confirm whether lineage is compatible
- stop if the tagged versioned manifest is absent

Relevant evidence:

- `artifacts/status/P23-T003.json`
- `artifacts/status/P23-T004.json`
- `artifacts/status/P23-I007.json`
- `artifacts/status/P23-I008.json`
- `scripts/schema_migrate.py`
- `scripts/rollback_release.py`

## Runbook Drill Flow

Use this order when rehearsing support incidents:

1. Start with install/bootstrap to establish whether the environment is healthy.
2. Move to packet deficits to see whether the current cohort is complete enough to operate.
3. Check benchmark and release blockers to confirm the current release posture.
4. Finish with recovery validation to confirm upgrade and rollback behavior.

The drill should stop immediately if any step reports a hard blocker. Do not widen the cohort or reinterpret blocker language to make the runbook feel more successful.

## Ownership

- Install/bootstrap owner: keeps the startup path and bootstrap state honest.
- Packet owner: keeps packet deficit reporting and fix suggestions explicit.
- Benchmark owner: keeps release-grade blocker categories visible.
- Recovery owner: keeps schema migration and rollback lineage-aware.
- Operator owner: keeps dashboard truth synchronized with the runtime state.

## Exit Criteria

The simulation pack is complete enough for support use when:

- each of the four incident classes is represented
- each class has a concrete evidence source
- each class has explicit support actions and limits
- no scenario claims release readiness
- no scenario hides current blockers

## Notes for Support Staff

- Treat this pack as a rehearsal aid, not as a release authorization artifact.
- When in doubt, prefer the blocker report over the optimistic interpretation.
- If the current evidence changes, update the related artifact references before changing the runbook language.

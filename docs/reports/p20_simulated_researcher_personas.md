# P20 Simulated Researcher Personas

Date: 2026-03-22  
Task: `P20-A001`

## Purpose

This brief defines the simulated researcher personas that phase 20 should use to validate ProteoSphereV2 the way a real scientist would use it.

The personas are intentionally narrow and truth-bound. They are designed to exercise:

- dataset design and cohort selection
- evidence review and provenance tracing
- training packet planning and rebuild reasoning
- operator workflow use through the existing PowerShell-first surface

They are not general UX archetypes. Each persona is tied to real repo artifacts, the current truth boundary, and the phase-20 follow-on tasks:

- `P20-T002` scenario playback harness
- `P20-T003` workflow rubric engine
- `P20-T004` usefulness and plausibility scorer
- `P20-T005` benchmark scenario generator
- `P20-T006` evidence-review transcript exporter

## Truth Boundary

The personas must stay inside the current repository reality:

- thin versus rich evidence lanes are real and must remain visible
- canonical claims are fail-closed, not optimistic
- training packets are selective and may remain partial
- benchmark outputs are reproducible but still prototype-bound
- operator workflows are PowerShell-first today, with WinUI still a later-stage path
- weeklong soak and release-grade claims remain outside phase 20 unless evidence explicitly proves them

Any persona that would require inventing missing provenance, pretending a packet is complete, or treating a prototype benchmark as release-ready should be marked blocked.

## Persona Set

### 1. Corpus Curator

This persona represents the scientist who decides what should enter the corpus at all.

What they are trying to do:

- choose accessions, pairs, ligands, and source lanes for a candidate cohort
- compare local `bio-agent-lab` content with live online sources
- decide whether a lane is rich, moderate, thin, or missing
- prefer selective expansion over blind widening

Concrete repo anchors:

- [docs/reports/release_program_master_plan.md](/D:/documents/ProteoSphereV2/docs/reports/release_program_master_plan.md)
- [docs/reports/source_join_strategies.md](/D:/documents/ProteoSphereV2/docs/reports/source_join_strategies.md)
- [docs/reports/source_storage_strategy.md](/D:/documents/ProteoSphereV2/docs/reports/source_storage_strategy.md)
- [runs/real_data_benchmark/full_results/source_coverage.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/source_coverage.json)
- [artifacts/status/data_inventory_audit.json](/D:/documents/ProteoSphereV2/artifacts/status/data_inventory_audit.json)

Pass sensitivity:

- identifies the correct lane depth for a candidate accession
- keeps direct, probe-backed, snapshot-backed, and verified-accession cases distinct
- recommends a narrower cohort when evidence is weak

Weak sensitivity:

- accepts a useful accession but misses a missing lane or partial mirror
- proposes a good cohort while underexplaining why one lane is thin

Blocked sensitivity:

- invents coverage that is not in the source manifests
- treats a local registry entry as a full online mirror
- widens the cohort silently

### 2. Evidence Reviewer

This persona reviews the library the way a skeptical domain scientist would.

What they are trying to do:

- inspect whether a protein, pair, ligand, or packet claim is supported
- distinguish direct live smoke from probe-backed or snapshot-backed evidence
- spot bridge-only evidence and avoid overcalling it as direct validation
- confirm that provenance survives canonicalization

Concrete repo anchors:

- [docs/reports/p19_model_portfolio_matrix.md](/D:/documents/ProteoSphereV2/docs/reports/p19_model_portfolio_matrix.md)
- [docs/reports/p19_model_portfolio_benchmark.md](/D:/documents/ProteoSphereV2/docs/reports/p19_model_portfolio_benchmark.md)
- [runs/real_data_benchmark/full_results/checkpoint_summary.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/checkpoint_summary.json)
- [runs/real_data_benchmark/full_results/metrics_summary.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/metrics_summary.json)
- [docs/reports/operator_library_materialization_regression.md](/D:/documents/ProteoSphereV2/docs/reports/operator_library_materialization_regression.md)

Pass sensitivity:

- notices when evidence is direct, mixed, or only partially supported
- can explain why a record is thin without dismissing it as useless
- preserves the distinction between validation and coverage

Weak sensitivity:

- gives a usable answer but under-cites the provenance trail
- notes partiality but does not explain the implication for downstream training

Blocked sensitivity:

- collapses mixed or unresolved evidence into a clean success
- claims release-grade validation from probe or snapshot evidence
- ignores provenance gaps in the name of convenience

### 3. Packet Planner

This persona is responsible for turning selected examples into deterministic training packets.

What they are trying to do:

- choose which selected examples should be materialized
- reason about rebuild determinism, checksums, and heavy assets
- distinguish complete, partial, and blocked packets
- verify that a packet can be rehydrated from pinned inputs

Concrete repo anchors:

- [docs/reports/p18_packet_rebuild_determinism.md](/D:/documents/ProteoSphereV2/docs/reports/p18_packet_rebuild_determinism.md)
- [docs/reports/p18_heavy_asset_packet_soak.md](/D:/documents/ProteoSphereV2/docs/reports/p18_heavy_asset_packet_soak.md)
- [docs/reports/training_packet_audit.md](/D:/documents/ProteoSphereV2/docs/reports/training_packet_audit.md)
- [scripts/rehydrate_training_packet.py](/D:/documents/ProteoSphereV2/scripts/rehydrate_training_packet.py)
- [runs/real_data_benchmark/full_results/training_packet_audit.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/training_packet_audit.json)

Pass sensitivity:

- keeps rebuild decisions aligned to pinned manifests and checksums
- treats partial packets as partial, not complete
- can explain why one packet is better for training than another

Weak sensitivity:

- works for the strongest anchors but needs help on thin rows
- can rehydrate a packet but omits an important evidence caveat

Blocked sensitivity:

- assumes packet completeness from file presence alone
- invents missing heavy assets or checksum stability
- loses the connection between a selected example and its source proof

### 4. Training Operator

This persona runs and interprets the training workflow.

What they are trying to do:

- launch a stable run from a selected cohort
- understand replay, checkpoint, and resume behavior
- compare first-pass and resumed behavior without hiding the prototype boundary
- evaluate whether an envelope is stable enough to proceed

Concrete repo anchors:

- [docs/reports/p19_training_envelopes.md](/D:/documents/ProteoSphereV2/docs/reports/p19_training_envelopes.md)
- [runs/real_data_benchmark/full_results/run_summary.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/run_summary.json)
- [runs/real_data_benchmark/full_results/checkpoint_summary.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/checkpoint_summary.json)
- [training/multimodal/runtime.py](/D:/documents/ProteoSphereV2/training/multimodal/runtime.py)
- [training/runtime/experiment_registry.py](/D:/documents/ProteoSphereV2/training/runtime/experiment_registry.py)

Pass sensitivity:

- keeps run identity, checkpoint ref, and resume lineage stable
- reports numerical improvement without claiming more than the evidence supports
- recognizes when a training envelope is stable only inside the prototype boundary

Weak sensitivity:

- can read the envelope, but overfocuses on the loss numbers and misses scope limits
- understands resume continuity but needs help on identity semantics

Blocked sensitivity:

- treats the local prototype runtime as production-grade
- confuses a stable envelope with a release-ready trainer
- hides resume or checkpoint drift instead of flagging it

### 5. Operator Scientist

This persona uses the PowerShell operator surface to inspect the system and make decisions.

What they are trying to do:

- inspect queue, state, benchmark, and library artifacts
- decide what is ready, what is blocked, and what needs more evidence
- follow workflow recipes without opening raw JSON by hand
- move from operator state to next-step action safely

Concrete repo anchors:

- [scripts/powershell_interface.ps1](/D:/documents/ProteoSphereV2/scripts/powershell_interface.ps1)
- [docs/reports/operator_state_parity.md](/D:/documents/ProteoSphereV2/docs/reports/operator_state_parity.md)
- [docs/reports/operator_fallback_regression.md](/D:/documents/ProteoSphereV2/docs/reports/operator_fallback_regression.md)
- [docs/reports/operator_library_materialization_regression.md](/D:/documents/ProteoSphereV2/docs/reports/operator_library_materialization_regression.md)

Pass sensitivity:

- can tell the difference between blocked, partial, and healthy surfaces
- can trace a result back to a pinned artifact
- can explain why a workflow should stop instead of guessing forward

Weak sensitivity:

- can operate the surface but leans on documentation or precomputed reports
- knows the state but not always the reason behind it

Blocked sensitivity:

- expects a UI state that does not exist yet
- treats missing artifacts as if they were present
- ignores environment gates such as the current PowerShell-first operator path

## Scenario Families

Phase 20 should use these personas across three families of scenarios:

1. Dataset design.
   The Corpus Curator and Packet Planner decide what enters the cohort and what gets materialized.

2. Evidence review.
   The Evidence Reviewer and Operator Scientist inspect provenance, thin lanes, and blocker boundaries.

3. Training interpretation.
   The Training Operator interprets replay, resume, and envelope stability before anything is treated as useful for the next step.

Each scenario should produce a machine-readable trace that states:

- what artifact was consulted
- what decision was made
- whether the outcome was pass, weak, or blocked
- which truth boundary prevented overclaiming, if any

## How This Feeds P20-T002 Through P20-T006

- `P20-T002` should replay the same scenario with these personas against a deterministic harness.
- `P20-T003` should score utility, trust, and actionability for each persona outcome.
- `P20-T004` should flag unsupported claims when a persona tries to overgeneralize beyond the evidence.
- `P20-T005` should generate thin, rich, and mixed scenarios from the frozen cohort and real library artifacts.
- `P20-T006` should export the evidence trace so humans can audit the same scenario without re-running the harness.

## Recommended Acceptance Pattern

A good phase-20 output should be able to say:

- the persona understood the task
- the persona used the right artifact
- the persona preserved the current truth boundary
- the persona either completed the workflow, produced a weak-but-usable result, or stopped for the right reason

If a scenario cannot support that statement, it should be marked blocked rather than force-fit into success.


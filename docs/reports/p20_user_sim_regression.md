# P20 User Simulation Regression

Date: 2026-03-22  
Task: `P20-I007`

## Bottom Line

The phase-20 user simulation regression now runs against real in-repo artifacts and landed user-sim components, not placeholder scenarios.

It is still a prototype-bound regression, not release-grade user validation. The regression names exactly one supported workflow, four weak workflows, and one blocked workflow.

## What Was Executed

The regression combined these landed surfaces:

- scenario generation from [evaluation/user_sim/scenario_generator.py](/D:/documents/ProteoSphereV2/evaluation/user_sim/scenario_generator.py)
- scenario playback from [evaluation/user_sim/scenario_harness.py](/D:/documents/ProteoSphereV2/evaluation/user_sim/scenario_harness.py)
- rubric scoring from [evaluation/user_sim/rubric_engine.py](/D:/documents/ProteoSphereV2/evaluation/user_sim/rubric_engine.py)
- plausibility scoring from [evaluation/user_sim/plausibility.py](/D:/documents/ProteoSphereV2/evaluation/user_sim/plausibility.py)
- transcript rendering from [scripts/export_user_sim_transcripts.py](/D:/documents/ProteoSphereV2/scripts/export_user_sim_transcripts.py)

The real artifact spine remained the frozen benchmark and related reports under [runs/real_data_benchmark/full_results](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results) plus the report set under [docs/reports](/D:/documents/ProteoSphereV2/docs/reports).

## Regression Summary

- Scenario count: `6`
- Trace states: `pass=1`, `weak=4`, `blocked=1`
- Rubric judgments: `pass=1`, `weak=4`, `blocked=1`
- Plausibility judgments: `conservative=1`, `weak_usable=4`, `unsupported=1`
- Supported workflows: `P20-G001-P69905`
- Weak workflows: `P20-G002-P68871, P20-G003-P04637, P20-G004-P31749, P20-G005-Q9NZD4`
- Blocked workflows: `P20-G006-BLOCKED-SOAK`

## Supported Workflow

The only fully supported workflow in this regression is the rich-coverage corpus-curation path for `P69905`.

Why it passed:

- direct live-smoke and multilane evidence is present
- the packet and benchmark surfaces both stay explicit about missing modalities instead of pretending full completeness
- the replay stayed inside the prototype truth boundary

## Weak Workflows

The weak outcomes are still useful because they stop short of overclaiming:

- `P20-G002-P68871`: mixed/probe-backed evidence remains reviewable but weak
- `P20-G003-P04637`: thin packet planning remains explicit and partial
- `P20-G004-P31749`: ligand-linked packet planning remains explicit and partial
- `P20-G005-Q9NZD4`: thin benchmark interpretation remains prototype-bound

These weak workflows are exactly the kind of honest partial success we want phase 20 to preserve.

## Blocked Workflow

`P20-G006-BLOCKED-SOAK` remains blocked for the right reason:

- the acceptance matrix file is not landed yet
- the weeklong soak note still states readiness, not completed soak proof

That blocked result is desirable because it proves the user-sim surface does not silently upgrade missing operational evidence into a pass.

## Truth Boundary

This regression does not claim:

- release-grade user validation
- release-ready operator workflows
- completed weeklong soak proof
- full-corpus validation beyond the frozen benchmark artifacts

The correct reading is narrower: the user-sim surfaces now execute on real artifacts, they distinguish supported from weak from blocked workflows, and they preserve current blocker boundaries explicitly.

## Next Move

Use [user_sim_regression.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/user_sim_regression.json) as the source artifact for the acceptance matrix in `P20-I008`. The acceptance matrix should summarize these six workflows with explicit evidence, weak points, and blocker boundaries rather than flattening them into a single release signal.

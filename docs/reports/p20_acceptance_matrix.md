# P20 Acceptance Matrix

Date: 2026-03-22  
Task: `P20-I008`

## Bottom Line

This matrix publishes the phase-20 user-simulation acceptance view from the real regression artifact in [user_sim_regression.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/user_sim_regression.json).

It is release-signoff ready as a review surface, but it does not upgrade the truth boundary. The regression still shows one supported workflow, four weak workflows, and one blocked workflow, and the blocked weeklong-soak / acceptance-matrix boundary remains explicit.

## Acceptance Summary

| Scenario | Persona | Workflow | Outcome | Evidence Strength | Weak Point | Blocker Boundary | Signoff Readiness |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `P20-G001-P69905` | Corpus Curator | `recipe` | `pass` | direct live-smoke, multilane, useful | still prototype-bound; missing ligand and PPI modalities remain explicit | truth before throughput, selective expansion | ready for phase-20 signoff review |
| `P20-G002-P68871` | Evidence Reviewer | `review` | `weak` | probe-backed, mixed evidence | summary-library probe is not direct assay depth | mixed evidence stays weak | usable, not promotable |
| `P20-G003-P04637` | Packet Planner | `packet` | `weak` | thin packet planning with deterministic rebuild framing | single-lane packet remains partial | partial packets remain partial | usable, not promotable |
| `P20-G004-P31749` | Packet Planner | `packet` | `weak` | ligand-linked packet planning | single-lane packet remains partial | partial packets remain partial, truth before throughput | usable, not promotable |
| `P20-G005-Q9NZD4` | Training Operator | `benchmark` | `weak` | snapshot-backed, identity-safe resume | thin benchmark interpretation only | identity-safe resume, prototype boundary | usable, not promotable |
| `P20-G006-BLOCKED-SOAK` | Operator Scientist | `review` | `blocked` | blocked on missing acceptance matrix and unproven soak | cannot claim completed weeklong soak | weeklong soak remains unproven | blocked by design |

## What The Matrix Says

The matrix supports three clear decisions:

1. `P69905` is the only supported workflow. It is the only case with multilane evidence strong enough to call `pass` without collapsing missing modalities.
2. `P68871`, `P04637`, `P31749`, and `Q9NZD4` are useful but still weak. Each is explicitly partial, and none should be promoted to release-grade workflow proof.
3. `P20-G006-BLOCKED-SOAK` remains blocked for the right reason. The acceptance matrix itself is now landed, but the weeklong soak is still not proven, so the blocked boundary stays intact.

## Evidence Anchors

Primary source artifact:

- [user_sim_regression.json](/D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/user_sim_regression.json)

Supporting report:

- [p20_user_sim_regression.md](/D:/documents/ProteoSphereV2/docs/reports/p20_user_sim_regression.md)

The regression used landed user-sim surfaces and real frozen-cohort artifacts:

- [scenario_generator.py](/D:/documents/ProteoSphereV2/evaluation/user_sim/scenario_generator.py)
- [scenario_harness.py](/D:/documents/ProteoSphereV2/evaluation/user_sim/scenario_harness.py)
- [rubric_engine.py](/D:/documents/ProteoSphereV2/evaluation/user_sim/rubric_engine.py)
- [plausibility.py](/D:/documents/ProteoSphereV2/evaluation/user_sim/plausibility.py)
- [export_user_sim_transcripts.py](/D:/documents/ProteoSphereV2/scripts/export_user_sim_transcripts.py)

## Signoff Notes

This matrix is suitable for RC/GA planning because it is explicit about:

- what passed,
- what stayed weak,
- what is blocked,
- and why the blocked boundary remains blocked.

It is not suitable for claiming:

- release-grade user validation,
- completed weeklong soak proof,
- or full-corpus validation.

Those claims remain outside the current truth boundary until direct evidence exists.

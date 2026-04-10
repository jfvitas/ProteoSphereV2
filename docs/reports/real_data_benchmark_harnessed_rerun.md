# Real Data Benchmark Harnessed Rerun Report

Date: 2026-03-22
Task: `P6-I015`
Status: `blocked / prototype-runtime complete`

## Verdict

The harnessed rerun executed across the frozen 12-accession cohort on the local
prototype runtime and produced real full-results artifacts, but it does not qualify as
a release-grade full benchmark pass.

What completed:

- the frozen 12-accession cohort was processed through the harness
- checkpoint writes and a resume cycle completed
- the full-results tree now contains a run manifest, run summary, checkpoint summary,
  live inputs, logs, and a checkpoint file

What still blocks a release-grade claim:

- the runtime remains a local prototype with surrogate modality embeddings
- the output set still lacks a richer corpus-scale reporting surface beyond the current
  harness summary artifacts
- source-lane coverage and provenance reporting remain thinner than the final benchmark
  bar

## Executed Scope

The harnessed run used:

- frozen cohort size: `12`
- split counts: `8 train / 2 val / 2 test`
- runtime surface: `training/multimodal/runtime.py`
- first pass: `6` examples
- resumed pass: completed to `12` processed examples

## Produced Artifacts

- `runs/real_data_benchmark/full_results/run_manifest.json`
- `runs/real_data_benchmark/full_results/run_summary.json`
- `runs/real_data_benchmark/full_results/checkpoint_summary.json`
- `runs/real_data_benchmark/full_results/live_inputs.json`
- `runs/real_data_benchmark/full_results/logs/full_rerun_stdout.log`
- `runs/real_data_benchmark/full_results/checkpoints/full-cohort-trainer.json`

## Runtime Summary

| Metric | Value |
| --- | --- |
| First-pass processed examples | `6` |
| Resumed processed examples | `12` |
| Checkpoint writes | `2` |
| Checkpoint resumes | `1` |
| Final state | `completed` |
| Resume continuity | `identity-safe` |

## Cohort Summary

| Metric | Value |
| --- | --- |
| Total cohort accessions | `12` |
| Resolved accessions | `12` |
| Unresolved accessions | `0` |
| Train | `8` |
| Val | `2` |
| Test | `2` |

## Remaining Gaps

1. The runtime is still a local prototype, not the final production trainer stack.
2. The harness outputs remain narrower than the ultimate release-ready reporting bar for
   source coverage, provenance tables, and richer benchmark statistics.
3. The hemoglobin pair remains the only explicit PPI sidecar in the current harnessed
   execution path.

## Blocker Categories

- runtime maturity
- source coverage depth
- provenance/reporting depth

## Decision

| Decision | Value |
| --- | --- |
| Harnessed rerun executed | `yes` |
| Release-grade full benchmark pass | `no` |
| Ready for next wave | `yes` |

## Next Work

- deepen the harness outputs into fuller corpus-scale reporting
- expand the source-lane reporting surface across the frozen cohort
- continue hardening the prototype runtime toward the production stack

# Real Data Benchmark Full Rerun Report

Date: 2026-03-22
Task: `P6-I012`
Status: `blocked`

## Verdict

The full 12-accession benchmark rerun did not complete in this workspace.

The repository now has:

- a frozen 12-accession cohort in
  `runs/real_data_benchmark/cohort/cohort_manifest.json`
- accession-level split labels in
  `runs/real_data_benchmark/cohort/split_labels.json`
- a hardened local prototype runtime with identity-safe resume checks

But it does not yet have a truthfully executed full-results tree for the 12-accession
benchmark under `runs/real_data_benchmark/full_results/`.

## What Was Ready

- `P6-T010` froze the 12-accession cohort and split labels.
- `P6-T011` hardened the runtime from count-based resume toward identity-safe resume.
- prior work already produced a truthful live-derived selected-example rerun probe in
  `runs/real_data_benchmark/results/`.

## What Is Still Missing

The following deliverables were still absent at the point of evaluation:

- `runs/real_data_benchmark/full_results/README.md`
- a populated `runs/real_data_benchmark/full_results/` tree
- full-corpus checkpoint artifacts for the 12-accession run
- full-corpus logs
- full-corpus source coverage statistics
- full-corpus train / val / test leakage results

## Why The Run Remains Blocked

1. No full-results tree was produced for the frozen 12-accession cohort.
2. The existing runtime remains a local prototype with surrogate modality embeddings.
3. The only executed rerun evidence on disk is still the narrower selected-example probe.

## Integrity Notes

The blocked status is still a useful forward step, not a regression:

- the frozen cohort is accession-level and leakage-ready
- the runtime resume path is stronger than before
- the prior rerun probe remains truthful and does not overclaim full-corpus scope

## Decision

| Decision | Value |
| --- | --- |
| Full 12-accession rerun complete | `no` |
| Blocker category | `benchmark-setup problem` plus `runtime maturity gap` |
| Ready for next wave | `yes` |

## Next Required Work

- materialize the full input/output harness for the 12-accession benchmark
- execute the frozen cohort through that harness
- write the full-results tree and corpus-scale report

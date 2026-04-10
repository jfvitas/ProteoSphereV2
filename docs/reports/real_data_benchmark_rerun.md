# Real Data Benchmark Rerun Report

Date: 2026-03-22
Task: `P6-I009`
Manifest: `benchmark-corpus-manifest-2026-03-22`
Status: `partial / blocked`

## Verdict

The workspace completed a truthful live-derived rerun probe, not the full corpus-scale
benchmark rerun.

- The rerun probe exercised a real local runtime path, wrote checkpoints, and proved a
  resume cycle on live-derived selected-example inputs.
- The full 12-accession corpus rerun is still blocked because the benchmark bundle is
  still a partial scaffold, split/leakage records for the 12-accession cohort are not
  materialized, and the current trainer runtime is still a local prototype with
  surrogate modality embeddings and count-based resume continuity.

## Scope Executed

The concrete scope executed in this workspace was:

- pair summary id: `pair:4HHB:protein_protein`
- structure anchor: `4HHB`
- protein accessions: `P69905`, `P68871`
- runtime surface: `training/multimodal/runtime.py`
- result root: `runs/real_data_benchmark/results/`

This was a live-derived selected-example rerun probe. It should not be described as the
full 12-accession corpus benchmark.

## Preconditions

| Prerequisite | Status | Notes |
| --- | --- | --- |
| `P5-I012` flagship pipeline | met | already green |
| `P5-I013` package flow | met | already green |
| `P5-T015` executable trainer runtime | met, prototype-only | local prototype runtime only |
| `P6-T008` benchmark corpus bundle | met, partial | scaffold is pinned, not full corpus |
| 12-accession frozen cohort | not met | only a live-derived probe cohort was exercised |
| split assignment / leakage records | not met | not produced for the full benchmark cohort |
| results tree writable | met | outputs written under `runs/real_data_benchmark/results/` |

## Artifacts Produced

- `runs/real_data_benchmark/results/run_summary.json`
- `runs/real_data_benchmark/results/live_inputs.json`
- `runs/real_data_benchmark/results/checkpoint_summary.json`
- `runs/real_data_benchmark/results/checkpoints/live-selected-example-trainer.json`
- `runs/real_data_benchmark/results/logs/rerun_stdout.log`

## Probe Statistics

| Metric | Value |
| --- | --- |
| Planned accessions in probe | `2` |
| Resolved accessions in probe | `2` |
| Missing accessions in probe | `0` |
| Partial accessions in probe | `0` |
| Ambiguous accessions in probe | `0` |
| Checkpoint writes | `2` |
| Checkpoint resumes | `1` |
| Summary-library proteins | `2` |
| Summary-library pairs | `1` |
| Summary-library ligands | `0` |
| Summary-library total records | `3` |

The probe did not produce truthful values for the full corpus metrics below, so they
remain explicitly unavailable in this report:

- full 12-accession train / val / test counts
- accession-level leakage count for the planned `8/2/2` split
- source-lane coverage totals at corpus scale
- mean / median / p90 records per protein across the planned cohort
- full unresolved/conflict totals across the planned benchmark population

## Runtime Evidence

The rerun probe used the new runtime surface and produced this checkpoint evidence:

- first run state: `completed`
- resumed run state: `completed`
- checkpoint path:
  `runs/real_data_benchmark/results/checkpoints/live-selected-example-trainer.json`
- checkpoint ref:
  `checkpoint://multimodal-run:e4286b8ef8eef1f1/package-benchmark-live-probe-001-v1-seed-0019`

The runtime remained honest about its current boundaries:

- backend: `local-prototype-runtime`
- objective: `modality-coverage-regression`
- modality embeddings: deterministic surrogates derived from bundle refs
- resume continuity: count-based, not yet identity-safe across reordered datasets

That means the probe is valid as an executable runtime check, but not yet as evidence of
an unattended-safe production rerun.

## Source Coverage Actually Exercised

The probe exercised a narrower surface than the full benchmark plan:

- UniProt-derived protein identities for `P69905` and `P68871`
- a protein-protein pair summary anchored on `4HHB`
- an RCSB/PDBe structure anchor for `4HHB`

The broader benchmark lanes remain supported by existing live-smoke evidence, but they
were not re-executed at corpus scale in this probe:

- InterPro
- Reactome
- BindingDB
- IntAct / PPI corpus lane
- AlphaFold DB
- Evolutionary / MSA corpus lane

## Remaining Gaps

The full corpus-scale rerun is still blocked by these exact gaps:

1. The pinned 12-accession benchmark corpus bundle is not yet materialized as a complete
   rerun input set.
2. Split assignment and leakage records for the 12-accession cohort are not yet
   produced.
3. The trainer runtime is still a local prototype that uses surrogate modality
   embeddings.
4. Resume continuity is still count-based rather than identity-safe.

## Decision

| Decision | Value |
| --- | --- |
| Full corpus-scale rerun complete | `no` |
| Live-derived rerun probe complete | `yes` |
| Benchmark ready for next wave | `no` |
| Blocker category | `benchmark-setup problem` plus `runtime maturity gap` |

## Next Required Work

- materialize the full 12-accession benchmark corpus bundle and split assignments
- harden runtime checkpoint/resume to use identity-safe progress markers
- rerun the benchmark against the full pinned cohort and report the complete corpus stats

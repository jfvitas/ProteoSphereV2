# Expanded Protein-Protein Benchmark Recommendation

## Summary

- Designed a same-budget expanded benchmark with `517` train and `98` test examples.
- Total selected size: `615` examples, aligned to the original `615`-example budget.
- Added beyond the original set: `615` new examples.
- Retained from the original set: `0` examples.
- Quality verdict: `pass`.
- Training readiness: `training_ready_candidate`.
- Acceptance gate: `ready_for_deeper_sequence_review`.
- Covered structures: `615` / `615`.

## Design Choices

- Universe: exact `Kd, Ki` protein-protein PDBbind measurements with local structure files.
- Leakage guard: shared accession plus `uniref50` component splitting.
- Entanglement control: excluded components larger than `10` structures.
- Labels are derived transparently as `exp_dG = RT ln(K)` at `298.15 K` from local exact PDBbind affinity values.

## Selection Snapshot

- Selected component count: `431`.
- Large entangled components excluded: `17`.
- Measurement mix: `{'Kd': 600, 'Ki': 15}`.
- Selected component size mix: `{1: 318, 2: 71, 3: 27, 4: 9, 5: 4, 10: 1, 8: 1}`.
- Train dG stats: `{'count': 517, 'min': -15.8281, 'max': -3.9373, 'mean': -9.4439, 'median': -9.3478, 'stdev': 1.9693}`.
- Test dG stats: `{'count': 98, 'min': -21.1971, 'max': -6.1509, 'mean': -9.4439, 'median': -9.2694, 'stdev': 2.0044}`.

## Leakage and Robustness Readout

- Direct protein overlap count: `0`.
- Exact sequence overlap count: `0`.
- UniRef90 overlap count: `0`.
- UniRef50 overlap count: `0`.
- Exact protein-set reuse count: `0`.
- Shared-protein different-context count: `0`.
- Shared partner overlap count: `0`.
- Flagged structure-pair count: `0`.
- Sequence audit decision: `no_sequence_level_blockers_detected`.
- Mutation audit decision: `no_non_identical_overlap_pairs_to_review`.
- Structure-state decision: `no_structure_state_overlap_rows`.
- Leakage matrix verdict: `ready_for_deeper_sequence_leakage_assessment`.

## Predicted Hard Test Examples

- `1Z7X`: hardness `6.6183`, `exp_dG=-21.1971`, `Kd`, `resolution=1.95`, component size `1`.
- `1KIG`: hardness `3.6802`, `exp_dG=-13.2942`, `Ki`, `resolution=3.0`, component size `1`.
- `2ABZ`: hardness `2.6795`, `exp_dG=-11.6682`, `Ki`, `resolution=2.16`, component size `1`.
- `1OZS`: hardness `2.6722`, `exp_dG=-6.1509`, `Kd`, `resolution=None`, component size `1`.
- `1PSB`: hardness `2.5403`, `exp_dG=-6.4106`, `Kd`, `resolution=None`, component size `1`.
- `4IOP`: hardness `2.4548`, `exp_dG=-12.5155`, `Kd`, `resolution=3.2`, component size `1`.
- `1WA7`: hardness `2.3189`, `exp_dG=-6.8467`, `Kd`, `resolution=None`, component size `1`.
- `6E2P`: hardness `2.2856`, `exp_dG=-6.4504`, `Kd`, `resolution=2.83`, component size `1`.
- `6A7V`: hardness `2.243`, `exp_dG=-12.5809`, `Kd`, `resolution=1.67`, component size `1`.
- `1P27`: hardness `2.1966`, `exp_dG=-12.4895`, `Kd`, `resolution=2.0`, component size `1`.

## Files

- Train CSV: `D:\documents\ProteoSphereV2\data\reports\expanded_pp_benchmark_candidates\expanded-pp-benchmark-20260406T212320Z\expanded_train_labels.csv`
- Test CSV: `D:\documents\ProteoSphereV2\data\reports\expanded_pp_benchmark_candidates\expanded-pp-benchmark-20260406T212320Z\expanded_test_labels.csv`
- Full artifact JSON: `D:\documents\ProteoSphereV2\data\reports\expanded_pp_benchmark_candidates\expanded-pp-benchmark-20260406T212320Z\expanded_pp_benchmark_candidate.json`
- Preview JSON: `D:\documents\ProteoSphereV2\artifacts\status\expanded_pp_benchmark_preview.json`

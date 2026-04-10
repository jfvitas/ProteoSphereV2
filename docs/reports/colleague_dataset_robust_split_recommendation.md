# Recommended Robust Split for the Colleague Dataset

## Recommendation

Use the generated robust split candidate rooted at:

- [LATEST_ROBUST_SPLIT.json](/D:/documents/ProteoSphereV2/data/reports/robust_split_candidates/LATEST_ROBUST_SPLIT.json)

Current concrete files:

- train:
  - [robust_train_labels.csv](/D:/documents/ProteoSphereV2/data/reports/robust_split_candidates/robust-split-20260406T204433Z/robust_train_labels.csv)
- test:
  - [robust_test_labels.csv](/D:/documents/ProteoSphereV2/data/reports/robust_split_candidates/robust-split-20260406T204433Z/robust_test_labels.csv)
- machine-readable audit:
  - [robust_split_candidate.json](/D:/documents/ProteoSphereV2/data/reports/robust_split_candidates/robust-split-20260406T204433Z/robust_split_candidate.json)
- excluded items:
  - [excluded_from_core_benchmark.json](/D:/documents/ProteoSphereV2/data/reports/robust_split_candidates/robust-split-20260406T204433Z/excluded_from_core_benchmark.json)

## Why this split is better

This split is built from the union of the provided examples, but only keeps the locally covered protein-protein core benchmark.

It uses whole connected components over:

- shared protein accession
- shared `UniRef90` family cluster

That makes it much safer for a GNN-plus-global-features project, because protein neighborhoods are kept together instead of leaking across train and test.

## Core numbers

- core benchmark pool: `566`
- excluded from strict core benchmark: `49`
- robust train size: `453`
- robust test size: `113`

### Train distribution

- mean `exp_dG`: `-9.9912`
- median `exp_dG`: `-9.799`
- std dev: `3.1209`

### Test distribution

- mean `exp_dG`: `-9.9913`
- median `exp_dG`: `-9.9785`
- std dev: `3.1214`

That alignment is unusually good and makes the split much easier to defend.

## Leakage result

The new split removes the two biggest failure modes entirely:

- direct protein overlap count: `0`
- exact sequence overlap count: `0`

Current gate status:

- `overall_decision = review_required`
- not blocked

Remaining review-only issues:

- `8` flagged structure-context rows
- all `8` are only `broad_family_context_overlap`
- no critical overlaps
- no high-risk overlaps
- `1` mutation-like pair remains for manual review

## Residual caveats

The remaining review-only rows are:

- `3G9W` vs `2KGX`
- `3G9W` vs `6BA6`
- `4WEM` vs `4WEU`
- `4WEN` vs `4WEU`
- `4YJ4` vs `1G5J`
- `4YJ4` vs `2M04`
- `4YJ4` vs `3R85`
- `5AYR` vs `4LYL`

These are not direct identity leaks. They are broad-family review cases.

The one mutation-like sequence case is:

- train accession `Q64373`
- test accession `Q07817`

That is worth documenting in any paper, but it is much weaker than the original split's exact-protein and exact-sequence reuse problems.

## Exclusions

The strict benchmark excludes `49` examples from the union because they are not part of a clean, locally covered protein-protein core:

- missing local structure mapping
- or non-protein-protein local complex typing

That is the right trade-off for a defensible benchmark.

## Bottom line

If the goal is:

- minimal leakage
- lower bias
- stronger generalizability claims
- and a split that is appropriate for a GNN-aware project

then this is the best split currently produced by the local tooling from the supplied examples.

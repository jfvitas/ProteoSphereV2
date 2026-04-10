# P53 External Cohort Audit CLI Contract

- Artifact: `p53_external_cohort_audit_cli_contract`
- Status: `report_only`
- Generated at: `2026-04-01T11:00:51.1748269-05:00`

This is the first-executable CLI contract for a read-only external cohort audit. It describes how a future CLI should use the lightweight training-set creator library to score imbalance and leakage risk on an already-existing split list.

## Contracted Command

The target CLI shape is:

```bash
python scripts/audit_external_cohort.py \
  --split-labels runs/real_data_benchmark/cohort/split_labels.json \
  --library-contract artifacts/status/p50_training_set_creator_library_contract.json \
  --output-json artifacts/status/p53_external_cohort_audit_cli_contract.json \
  --output-md docs/reports/p53_external_cohort_audit_cli_contract.md
```

The command is report-only. It must not widen the cohort, mutate manifests, or imply release readiness.

## Inputs

- [split_labels.json](D:/documents/ProteoSphereV2/runs/real_data_benchmark/cohort/split_labels.json)
- [p50_training_set_creator_library_contract.json](D:/documents/ProteoSphereV2/artifacts/status/p50_training_set_creator_library_contract.json)

The audited split list contains 12 accessions:

- Train: 8
- Val: 2
- Test: 2

Coverage buckets are balanced overall at 4 rich, 4 moderate, and 4 sparse-or-control, but the buckets are intentionally stratified across the splits.

## CLI Behavior

The CLI should:

1. Load the existing split labels.
2. Load the lightweight library contract.
3. Map the split rows into library views that preserve provenance and row-level context.
4. Score imbalance from split counts and bucket placement.
5. Score leakage from accession reuse and cross-split duplicates.
6. Emit a short operator summary plus full JSON and markdown outputs.

## Output Contract

The machine-readable output should contain:

- CLI metadata
- input paths
- audited split counts
- imbalance result
- leakage result
- operator next actions
- evidence paths

The markdown output should read like an operator note, with clear headings for:

- What Was Audited
- CLI Contract
- Audit Result
- Operator Read
- Recommended Next Action

## Truth Boundary

The right reading is:

- leakage risk is low because no accession is reused across train, val, or test
- imbalance is attention-needed only if a downstream consumer expects each split to contain every coverage bucket
- overall balance is not the same thing as per-split uniformity

The split is usable with notes, but the report must keep the stratification explicit.

## Exit Semantics

- `0`: audit completed and outputs were written
- `2`: split input was missing or malformed
- `3`: library contract mismatch or unsupported audit shape
- `4`: output write failure

## Recommended Operator Action

Keep the split frozen and describe the stratification honestly. If a downstream consumer needs each split to contain all coverage buckets, rerun split simulation before any claim of broader generalization.

# P51 External Cohort Audit Flow

- Artifact: `p51_external_cohort_audit_flow`
- Status: `report_only`
- Generated at: `2026-04-01T11:00:51.1748269-05:00`

This flow uses the lightweight training-set creator contract to audit an already-existing split list for imbalance and leakage risk. It stays read-only and grounded in the current benchmark split labels.

## What Was Audited

- Canonical split list: [runs/real_data_benchmark/cohort/split_labels.json](D:/documents/ProteoSphereV2/runs/real_data_benchmark/cohort/split_labels.json)
- Lightweight contract: [p50_training_set_creator_library_contract.json](D:/documents/ProteoSphereV2/artifacts/status/p50_training_set_creator_library_contract.json)
- Supporting boundary reports:
  - [training_packet_audit.md](D:/documents/ProteoSphereV2/docs/reports/training_packet_audit.md)
  - [p19_training_envelopes.md](D:/documents/ProteoSphereV2/docs/reports/p19_training_envelopes.md)
  - [p26_data_training_gap_assessment.md](D:/documents/ProteoSphereV2/docs/reports/p26_data_training_gap_assessment.md)

## Flow

1. Load the split labels and the lightweight-library contract.
2. Map the split rows into the lightweight library views that preserve provenance and cross-source context.
3. Score imbalance from split counts and bucket placement.
4. Score leakage from accession reuse and cross-split duplicates.
5. Emit the operator decision with the balance and leakage boundary kept explicit.

## Audit Result

The split is leakage-safe as currently frozen. `accession_level_only` is true, `duplicate_accessions` is empty, and `cross_split_duplicates` is empty. The guard is simple: one accession, one split.

The imbalance story is more subtle. Overall the cohort is balanced at `4` rich-coverage, `4` moderate-coverage, and `4` sparse-or-control accessions. At the split level, though, the allocation is intentionally stratified:

- Train: `8` accessions, all `rich_coverage` or `moderate_coverage`
- Val: `2` accessions, both `sparse_or_control`
- Test: `2` accessions, both `sparse_or_control`

That means the cohort is not uniformly mixed across splits, but that is not a leakage signal. It is a designed split shape and should be described that way.

## Operator Read

The right summary is: leakage risk is low, imbalance risk is attention-needed only if a downstream consumer expects each split to contain every bucket. For the current external-audit use, the split is usable as long as the stratification is stated plainly.

## Recommended Next Action

Keep the split frozen, preserve the bucket stratification in the audit output, and rerun split simulation only if the external use case needs a different split mix. Do not widen the cohort or treat this read-only audit as a materialization step.

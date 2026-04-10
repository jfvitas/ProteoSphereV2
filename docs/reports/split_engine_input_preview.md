# Split Engine Input Preview

- Recipe ID: `protein_spine_first_split_recipe_v1`
- Input artifact: `entity_split_candidate_preview`
- Atomic unit: `entity_signature_row`
- Primary hard group: `protein_spine_group`
- Group rows: `11`
- Candidate rows: `1889`

## Execution Readiness

- Recipe ready: `True`
- Assignment ready: `True`
- Fold export ready: `True`
- Next unlocked stage: `split_fold_export_materialized`
- Ligand governing split ready: `True`

## Supplemental Non-Governing Signals

- Ligand rows: `available_non_governing` / rows=`24` / grounded_accessions=`2`
- Motif/domain compact: `available_non_governing` / rows=`55`
- Interaction similarity: `blocked_candidate_only` / rows=`2`

## Truth Boundary

- This preview is the current split-engine handoff surface. It binds the live recipe preview to the live linked-group assignment preview, but it does not commit folds, CV partitions, or release-grade train/test exports. Supplemental ligand and motif/domain signals are visible here only as non-governing annotations.

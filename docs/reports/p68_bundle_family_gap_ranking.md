# P68 Bundle Family Gap Ranking

This report-only note ranks the next safest missing bundle families after `leakage_groups`.

## Baseline

The lightweight bundle remains in the verified preview state:

- [artifacts/status/lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [artifacts/status/p67_bundle_truth_review.json](/D:/documents/ProteoSphereV2/artifacts/status/p67_bundle_truth_review.json)
- [artifacts/status/p67_ligand_signature_emission_prereqs.json](/D:/documents/ProteoSphereV2/artifacts/status/p67_ligand_signature_emission_prereqs.json)
- [artifacts/status/structure_similarity_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_similarity_signature_preview.json)

Current manifest facts:

- `manifest_status`: `preview_generated_verified_assets`
- `budget_class`: `A`
- compressed size: `239656` bytes
- `structure_similarity_signatures`: `4`
- `leakage_groups`: `11`

## Already Materialized

These are not part of the gap ranking because they are already in the preview bundle:

- `structure_similarity_signatures`
- `leakage_groups`

## Ranked Missing Families

1. `protein_similarity_signatures`
1. `dictionaries`
1. `ligand_similarity_signatures`
1. `interaction_similarity_signatures`
1. `ligands`
1. `interactions`

## Why This Order

`protein_similarity_signatures` is first because it can be derived from the already-materialized protein surface with no new procurement lane.

`dictionaries` comes next because it is packaging-only rather than new biological content, even though it still needs bundle-mechanics work.

`ligand_similarity_signatures` and `interaction_similarity_signatures` stay behind those because the repo has not yet materialized the underlying ligand or interaction families they would summarize.

`ligands` and `interactions` are last because they are source-fusion families, and the ligand prereq note says non-null ligand grouping remains blocked until a real lightweight ligand family exists and deterministic normalization is defined.

## Ligand Prereq Impact

The p67 ligand prereqs make the ligand lane the clearest blocker in this gap set:

- non-null ligand grouping is blocked today
- ligand overlap is not yet materialized in the leakage preview
- the repo still needs a real materialized lightweight ligand family before non-null ligand identity or binding-context groups can be emitted

That means any ligand-dependent missing family stays behind the purely derived protein and packaging slices.

## Structure Preview Impact

The structure similarity preview matters because it shows what already cleared the bar:

- `structure_similarity_signatures` is already a compact four-row preview
- `leakage_groups` is already a compact 11-row preview

So neither belongs in the missing-family ranking anymore.

## Bottom Line

The safest remaining missing family is `protein_similarity_signatures`. After that, the only low-risk gap is `dictionaries`, followed by the ligand- and interaction-dependent families that still need real source-backed materialization.

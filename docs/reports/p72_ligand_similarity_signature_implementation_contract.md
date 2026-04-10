# Ligand Similarity Signature Implementation Contract

## Summary
After dictionaries are included in the preview bundle, the next safest missing family is `ligand_similarity_signatures`.
It is the lowest-risk remaining missing family because it is derived from the eventual lightweight ligand surface rather than from a new acquisition lane.

## Current Ranking After Dictionaries
Already materialized and not ranked:
- `protein_similarity_signatures`
- `structure_similarity_signatures`
- `leakage_groups`
- `dictionaries`

Remaining ranked families:
1. `ligand_similarity_signatures`
2. `ligands`
3. `interaction_similarity_signatures`
4. `interactions`

## Concrete Change Contract
The implementation seam is the same compact preview pattern already used for protein, structure, and dictionary previews.
The required code files are:
- `scripts/export_ligand_similarity_signature_preview.py`
- `scripts/build_lightweight_preview_bundle_assets.py`
- `scripts/export_bundle_manifest.py`
- `scripts/validate_live_bundle_manifest.py`

Why these files:
- A new preview exporter is needed for the ligand similarity surface itself.
- The bundle builder must ingest that preview, persist it, and count it in the release manifest.
- The manifest exporter must add `ligand_similarity_signatures` to the bundle family list and build inputs.
- The validator must include a ligand similarity slice in the live truth assessment.

The required test areas are:
- `tests/unit/test_export_ligand_similarity_signature_preview.py`
- `tests/unit/test_build_lightweight_preview_bundle_assets.py`
- `tests/unit/test_export_bundle_manifest.py`
- `tests/unit/test_validate_live_bundle_manifest.py`

## Truth Boundary
This is a report-only contract.
It does not claim the ligand lane is ready now, because the current manifest still shows `ligands = 0` and `ligand_similarity_signatures = 0`.
It only identifies the next safest implementation target and the exact surfaces that need to move for it.

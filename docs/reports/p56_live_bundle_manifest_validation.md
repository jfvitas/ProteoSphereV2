# P56 Live Bundle Manifest Validation

Report-only validation note for the newly emitted lightweight bundle manifest preview.

## Truth Boundary

- This note is report-only.
- It does not authorize publication or code changes.
- It checks whether the manifest truthfully reflects the current protein, protein_variant, and structure-unit slices.

## Manifest Under Validation

- `artifacts/status/p53_bundle_manifest_example.json`

Manifest shape:

- bundle id: `proteosphere-lite`
- bundle kind: `debug_bundle`
- bundle version: `0.1.0-preview`
- schema version: `1`
- release id: `2026.04.01-protein-preview.1`
- packaging layout: `compressed_sqlite`

## Current Slice Sources

- Protein slice: `artifacts/status/protein_summary_library.json`
- Protein_variant slice baseline: `artifacts/status/summary_library_inventory.json`
- Structure-unit slice: `artifacts/status/structure_unit_summary_library_inventory.json`

## What The Manifest Says

- `proteins`: `11`
- `protein_variants`: `0`
- `structures`: `0`
- `motif_annotations`: `98`
- `pathway_annotations`: `254`
- `provenance_records`: `17`

## Slice Truth Check

| Slice | Manifest Count | Current Count | Status |
| --- | ---: | ---: | --- |
| Protein | 11 | 11 | aligned |
| Protein_variant | 0 | 0 | deferred and truthful |
| Structure_unit | 0 | 4 | missing current slice |

### Protein

The manifest is truthful for the current protein slice. The preview count of `11` matches the current protein summary library.

### Protein_variant

The manifest is also truthful to keep `protein_variants` at `0`. The current inventory has no materialized protein_variant rows yet, even though the p53 evidence hunt supports a narrow first slice for `P04637` and `P31749`.

### Structure_unit

The manifest is not yet truthful for the current structure-unit slice if it is meant to represent the current lightweight bundle state. The structure-unit library now has `4` records, but the manifest still shows `structures=0`.

## Validation Result

Overall status: `partially_truthful_preview`

What is truthful:

- protein
- protein_variant deferred state

What needs update:

- structure_unit

## Operator Note

Treat this manifest as a preview until the structure-unit surface is surfaced explicitly or the bundle scope is narrowed and labeled as protein-only. Do not present it as a complete current-slice bundle manifest while the structure-unit slice still exists separately.

## Validation Gates

Passed:

- Protein family count aligns with the current protein summary library.
- Protein_variant remains correctly deferred at zero.
- The manifest does not invent unsupported variant coverage.

Needs attention:

- The current structure-unit inventory has `4` records, but the manifest still shows `structures=0`.
- If the manifest is meant to reflect the current lightweight bundle, it should incorporate structure-unit truth explicitly.
- If structure-unit is intentionally out of scope, the manifest should say so directly.

## Bottom Line

The lightweight bundle preview is truthful for protein and for a deferred protein_variant surface, but it is not yet a faithful current-slice reflection for structure-unit. The manifest should be updated or narrowly scoped before operators rely on it as a full current bundle view.

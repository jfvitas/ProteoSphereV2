# P57 Bundle Truth Delta

Report-only live bundle manifest truth delta note against the current generated contents/schema docs and the current manifest.

## Truth Boundary

- This note is report-only.
- It does not authorize publication or code changes.
- It checks whether the current lightweight bundle manifest is truthful against the current generated contents contract, schema outline, and live slice inventories.

## Manifest Under Validation

- [artifacts/status/p53_bundle_manifest_example.json](/D:/documents/ProteoSphereV2/artifacts/status/p53_bundle_manifest_example.json)

Manifest shape:

- bundle id: `proteosphere-lite`
- bundle kind: `debug_bundle`
- bundle version: `0.1.0-preview`
- schema version: `1`
- release id: `2026.04.01-protein-preview.1`
- packaging layout: `compressed_sqlite`

## Generated Docs

- [artifacts/status/p56_bundle_contents_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p56_bundle_contents_contract.json)
- [artifacts/status/p56_bundle_schema_doc_outline.json](/D:/documents/ProteoSphereV2/artifacts/status/p56_bundle_schema_doc_outline.json)

## Current Slice Sources

- Protein slice: [artifacts/status/protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- Protein_variant baseline: [artifacts/status/summary_library_inventory.json](/D:/documents/ProteoSphereV2/artifacts/status/summary_library_inventory.json)
- Structure-unit slice: [artifacts/status/structure_unit_summary_library_inventory.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_unit_summary_library_inventory.json)

## What The Manifest Says

- `proteins`: `11`
- `protein_variants`: `0`
- `structures`: `0`
- `motif_annotations`: `98`
- `pathway_annotations`: `254`
- `provenance_records`: `17`

## What The Generated Docs Say

The contents contract currently says:

- `proteins` are included now
- `protein_variants` are declared but not populated
- `structures` are included now from the structure-unit summary library

The schema outline currently says:

- `proteins` are a live table family
- `protein_variants` are reserved
- `structures` are reserved

That means the generated docs do not yet agree with each other on the structures surface.

## Slice Truth Check

| Slice | Manifest Count | Current Count | Contents Contract | Schema Outline | Status |
| --- | ---: | ---: | --- | --- | --- |
| Protein | 11 | 11 | included now | live table family | aligned |
| Protein_variant | 0 | 0 | declared but not populated | reserved family | deferred and truthful |
| Structure_unit | 0 | 4 | included now | reserved family | doc/manifest mismatch |

### Protein

The manifest is truthful for the current protein slice. The preview count of `11` matches the current protein summary library.

### Protein_variant

The manifest is also truthful to keep `protein_variants` at `0`. The current inventory has no materialized protein_variant rows yet, so the zero count is a truthful deferred state.

### Structure_unit

This is the remaining truth delta. The contents contract already says structures are included now, and the current structure-unit inventory has `4` records, but the manifest still shows `structures=0`. The schema outline still reserves structures, so the docs themselves do not yet share a single stance.

## Validation Result

Overall status: `partially_truthful_preview_with_doc_split`

What is truthful:

- protein
- protein_variant deferred state

What needs resolution:

- structure_unit

## Operator Note

Treat this manifest as a preview until the bundle docs pick one truth boundary for structures. If the current lightweight bundle is meant to include structure-unit truth, the manifest is stale; if the bundle is meant to stay protein-only for now, the contents contract should be narrowed to match that scope.

## Validation Gates

Passed:

- Protein family count aligns with the current protein summary library.
- Protein_variant remains correctly deferred at zero.
- The manifest does not invent unsupported variant coverage.

Needs attention:

- The current structure-unit inventory has `4` records, but the manifest still shows `structures=0`.
- The contents contract says structures are included now, while the schema outline still reserves structures.
- The bundle docs need one shared truth boundary before operators should rely on this as a full current-slice bundle view.

## Bottom Line

The lightweight bundle preview is truthful for protein and for a deferred protein_variant surface, but the structures story is split between the generated docs and the manifest. Until that is resolved, this remains a partially truthful preview rather than a complete current bundle surface.

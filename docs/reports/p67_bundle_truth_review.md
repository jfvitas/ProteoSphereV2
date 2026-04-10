# P67 Bundle Truth Review

This is a report-only review of [lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json), [live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json), [proteosphere-lite.release_manifest.json](/D:/documents/ProteoSphereV2/artifacts/bundles/preview/proteosphere-lite.release_manifest.json), [structure_similarity_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_similarity_signature_preview.json), and [leakage_group_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/leakage_group_preview.json). It summarizes what the preview bundle now truthfully contains versus what remains excluded.

## What The Bundle Truthfully Contains

The current preview bundle is aligned with the live inventories and verified assets. It truthfully contains the currently materialized slices that are already reflected in the bundle manifest and validation surface:

- proteins
- protein variants
- structure units
- motif annotations
- pathway annotations
- provenance records
- structure similarity signatures
- leakage groups

The live validation confirms that the bundle counts for `protein`, `protein_variant`, and `structure_unit` are aligned with the current inventories, and the required assets plus docs are present.

## What The Bundle Still Excludes

The bundle still intentionally excludes the families and payload classes that are not yet materialized in the lightweight preview:

- ligands
- interactions
- protein similarity signatures
- ligand similarity signatures
- interaction similarity signatures
- dictionaries
- heavy raw payload classes such as raw mmCIF, assay tables, BioPAX/SBML diagrams, and cryo-EM validation payloads

It also does not claim direct structure-backed variant joins.

## Grounded Examples

- `structure_similarity_signature_preview` already shows 4 structure rows across 2 proteins, but it remains a planning surface and not a claim of direct structure-variant anchoring.
- `leakage_group_preview` already shows 11 linked groups with `test`, `train`, and `val` split labels, but it remains report-only split behavior.
- `P68871` is still a candidate-overlap accession: the bundle contains its structure slice and structure similarity signal, but direct structure-backed variant joining is still deferred.
- `P04637` is still a structure-followup accession: the bundle contains its protein and variant slices, but its structure slice is still deferred.

## Next Truthful Expansion

The next truthful bundle expansion should wait until the deferred families are actually materialized. At that point, the bundle can add their matching preview and validation surfaces without weakening the current aligned counts or the current exclusion list.

That keeps the preview bundle useful for planning while preserving the current truth boundary.

## Boundary

This review is report-only. It does not edit code, does not rewrite protected latest surfaces, and does not claim any excluded family or direct join is already present in the preview bundle.

# P81 Duplicate Cleanup No-Interaction Note

## Conclusion

No direct interaction exists.

Adding the ligand identity pilot family does **not** change duplicate cleanup execution prerequisites.

## Grounding

- [duplicate_cleanup_first_execution_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_first_execution_preview.json) is still `not_yet_executable_today` and is scoped to one exact duplicate removal in `data/raw/local_copies`.
- [p36_storage_dedupe_safety_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p36_storage_dedupe_safety_contract.json) keeps duplicate cleanup tied to:
  - exact byte identity
  - provenance lineage
  - role equivalence
  - allowlisted cleanup scope
- [p50_duplicate_cleanup_staging_map.json](/D:/documents/ProteoSphereV2/artifacts/status/p50_duplicate_cleanup_staging_map.json) keeps the first cleanup cohorts in mirror-copy roots, especially `data/raw/local_copies`.
- [lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json) still reports:
  - `ligands.included = false`
  - `ligands.record_count = 0`
  - `ligand_support_readiness.record_count = 4`

## Why There Is No Interaction

- Duplicate cleanup prerequisites are about raw/local mirror duplicates.
- The ligand identity pilot is not a live ligand bundle family yet.
- Even if the ligand pilot is added later, it would be a bundle or derived-output concern, not a raw mirror cleanup target.

## Explicit Boundary

If a future ligand identity pilot family is emitted, it should remain outside duplicate cleanup candidate classes unless a separate cleanup contract explicitly includes it.

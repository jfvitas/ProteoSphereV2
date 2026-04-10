# P30 Local Reference Blend Snapshot

- Generated at: `2026-03-30T12:18:00-05:00`
- Focus: freeze the best current local blend policy based on what is actually present inside this repo, while the shell remains blocked from running the registry refresh.

## Current Situation

- The authoritative import snapshot at [`data/raw/local_registry_runs/LATEST.json`](D:/documents/ProteoSphereV2/data/raw/local_registry_runs/LATEST.json) is stale.
- It was generated at `2026-03-30T05:45:22Z` against the external storage root `C:\Users\jfvit\Documents\bio-agent-lab`.
- It still marks `biogrid`, `intact`, and `prosite` as missing and does not yet include the newer repo-seed-tracked sources such as `chebi`, `complex_portal`, `rnacentral`, `sifts`, and `pdb_chemical_component_dictionary`.

## Repo Evidence Confirmed In This Run

| Source | Current repo evidence | Operational meaning |
| --- | --- | --- |
| `biogrid` | Four BioGRID bulk ZIPs are present under `data/raw/protein_data_scope_seed/biogrid` | Curated interaction lane is materially present on disk |
| `intact` | `intact.zip` and `mutation.tsv` are present under `data/raw/protein_data_scope_seed/intact` | Curated interaction lane is materially present on disk |
| `prosite` | `prosite.dat`, `prosite.doc`, and `prosite.aux` are present under `data/raw/protein_data_scope_seed/prosite` | Motif lane can be blended locally without another download |
| `chebi` | Seed mirror directory is present | Chemical identity authority is locally available |
| `complex_portal` | Seed mirror directory is present | Complex-context enrichment is locally available |
| `rnacentral` | Seed mirror directory is present | Extended identifier context is locally available |
| `sifts` | Seed mirror directory is present | Structure crosswalk layer is locally available |
| `pdb_chemical_component_dictionary` | Seed mirror directory is present | Ligand normalization authority is locally available |

## Effective Blend Policy

1. Use `uniprot` as the accession spine and `sifts` immediately after it for the protein-to-structure crosswalk.
2. Use `structures_rcsb` and `raw_rcsb` as experimental structure truth; keep AlphaFold in a separate predicted lane.
3. Use `pdb_chemical_component_dictionary` plus `chebi` as the ligand identity authority layer.
4. Use `chembl` as the strongest broad assay-backed ligand source currently trusted for local blending.
5. Keep `bindingdb` bulk under quarantine until the mirrored archives are validated as real dumps rather than placeholder payloads.
6. Use `reactome`, `interpro`, and `prosite` together as the active annotation lane.
7. Treat `complex_portal` as curated complex context only, not direct binary interaction truth.
8. Treat `intact` and `biogrid` as the curated interaction winners once the stale import snapshot is refreshed.
9. Continue to exclude `string` from the effective merge until graph payloads exist beyond metadata.
10. Continue to exclude the repo-seed `alphafold_db` lane from authoritative presence while it only contains a partial archive.

## What I Materialized

- Added [`artifacts/status/p30_local_reference_blend_snapshot.json`](D:/documents/ProteoSphereV2/artifacts/status/p30_local_reference_blend_snapshot.json) as the execution-facing artifact for the current blend state.
- The new artifact records:
  - stale-versus-current registry deltas
  - active merge lanes
  - gated sources that must not be promoted
  - the expected registry changes once execution is available again

## Next Useful Action

When a working Python launcher is available again, run:

```powershell
python scripts\import_local_sources.py --include-missing
```

Then confirm that:

- `biogrid`, `intact`, and `prosite` are no longer marked missing
- `chebi`, `complex_portal`, `rnacentral`, `sifts`, and `pdb_chemical_component_dictionary` appear in the imported snapshot
- `string` remains excluded
- `bindingdb` bulk remains quarantined unless integrity checks pass

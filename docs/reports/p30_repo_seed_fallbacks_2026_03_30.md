# P30 Repo Seed Fallback Hardening

- Generated at: `2026-03-30T10:18:00-05:00`
- Focus: reduce dependence on the external `C:\Users\jfvit\Documents\bio-agent-lab` tree by letting the authoritative local-source registry resolve against repo-local seed mirrors when equivalent payloads already exist in this workspace.

## What Changed

- Extended [`execution/acquire/local_source_registry.py`](D:/documents/ProteoSphereV2/execution/acquire/local_source_registry.py) so three already-important sources can resolve from repo-local seed storage:
  - `chembl`
  - `reactome`
  - `interpro`
- Left `alphafold_db` and `string` unchanged because their repo seed lanes are not yet complete enough to serve as authoritative local payload roots:
  - `alphafold_db` only has `swissprot_cif_v6.tar.part`
  - `string` currently only has `_source_metadata.json`

## Why This Matters

- The current authoritative registry snapshot at `data/raw/local_registry_runs/LATEST.json` still points at the external bio-agent-lab storage root and is stale relative to the source-definition fixes made on 2026-03-30.
- Adding repo-local fallback roots means the next refresh can keep `chembl`, `reactome`, and `interpro` visible even if the external tree is unavailable, moved, or incomplete.
- This makes the merged local reference more self-contained inside the ProteoSphere workspace instead of silently depending on outside state.

## Seed Evidence Used

| Source | Repo-local payloads confirmed | Notes |
| --- | --- | --- |
| `chembl` | `chembl_36_sqlite.tar.gz`, `chembl_36_sqlite.tar.gz__extracted` | Strong repo-local fallback for ligand/reference chemistry |
| `reactome` | `UniProt2Reactome.txt`, `ReactomePathways.txt`, `ReactomePathwaysRelation.txt` | Equivalent pathway hierarchy coverage, though the all-level export is still only partial in seed form |
| `interpro` | `interpro.xml.gz` plus companion metadata tables | Good repo-local fallback for domain/family annotation |
| `alphafold_db` | `swissprot_cif_v6.tar.part` only | Not safe to treat as present |
| `string` | `_source_metadata.json` only | Manifest metadata, not downloaded graph payloads |

## Revised Blend Guidance

1. Treat `chembl`, `bindingdb`, `biolip`, `pdbbind*`, `pdb_chemical_component_dictionary`, and `chebi` as the protein-ligand identity and assay evidence lane.
2. Keep `reactome` and `interpro` in the annotation lane, but prefer repo-local seed mirrors whenever the external bio-agent-lab paths drift.
3. Continue to hold `string` out of the effective merge until real payloads are downloaded, because metadata alone would inflate perceived coverage.
4. Continue to hold repo-seed `alphafold_db` out of the effective merge until the archive is complete rather than partial.

## Blocker

- This shell still does not expose a working `python`, `py`, or `uv` launcher, so the corrected registry cannot be regenerated from here.

## Next Run

```powershell
python scripts\import_local_sources.py --include-missing
```

- Then verify that the refreshed `data/raw/local_registry_runs/LATEST.json` shows:
  - `biogrid`, `intact`, and `prosite` as present from the earlier seed-path fix
  - `chebi`, `complex_portal`, `rnacentral`, `sifts`, and `pdb_chemical_component_dictionary` as newly tracked
  - `chembl`, `reactome`, and `interpro` still present even without relying solely on external storage roots

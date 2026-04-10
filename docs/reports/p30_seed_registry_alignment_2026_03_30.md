# P30 Seed Registry Alignment

- Generated at: `2026-03-30T07:04:04.7350178-05:00`
- Focus: align the local-source registry with the validated `protein_data_scope_seed` mirror so the merged local reference stops reporting false gaps for sources that are already on disk.

## What Changed

- Updated `execution/acquire/local_source_registry.py` so these sources now resolve against the validated seed mirror instead of stale `data_sources/*` placeholders:
  - `uniprot`
  - `biogrid`
  - `intact`
  - `prosite`
- Kept the source categories and join anchors unchanged.
- Tightened the source notes so the registry reflects that these lanes are backed by validated local seed assets.

## Verified Local Assets

- `data/raw/protein_data_scope_seed/uniprot/uniprot_sprot.dat.gz`
- `data/raw/protein_data_scope_seed/uniprot/uniprot_sprot.fasta.gz`
- `data/raw/protein_data_scope_seed/uniprot/idmapping.dat.gz`
- `data/raw/protein_data_scope_seed/biogrid/BIOGRID-ALL-LATEST.mitab.zip`
- `data/raw/protein_data_scope_seed/biogrid/BIOGRID-ORGANISM-LATEST.mitab.zip`
- `data/raw/protein_data_scope_seed/biogrid/BIOGRID-ORGANISM-LATEST.psi.zip`
- `data/raw/protein_data_scope_seed/biogrid/BIOGRID-ORGANISM-LATEST.psi25.zip`
- `data/raw/protein_data_scope_seed/intact/intact.zip`
- `data/raw/protein_data_scope_seed/intact/mutation.tsv`
- `data/raw/protein_data_scope_seed/prosite/prosite.dat`
- `data/raw/protein_data_scope_seed/prosite/prosite.doc`
- `data/raw/protein_data_scope_seed/prosite/prosite.aux`

## Expected Merge Impact

- `uniprot` should move from `partial` to `present` in the authoritative local registry refresh.
- `biogrid`, `intact`, and `prosite` should move from `missing` to `present`.
- The motif and curated interaction lanes should therefore become available to downstream registry-driven materialization and source-coverage reporting.

## Blocker

- The current shell does not expose `python`, `py`, or `uv`, so this run could not execute `scripts/import_local_sources.py` to regenerate `data/raw/local_registry_runs/LATEST.json`.

## Next Step

- Re-run the authoritative local import once a Python launcher is available:

```powershell
python scripts\import_local_sources.py --include-missing
```

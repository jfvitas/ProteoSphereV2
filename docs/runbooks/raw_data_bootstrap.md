# Raw Data Bootstrap

The repo now separates three things clearly:

- `data/raw`: raw source payloads and source manifests
- `data/canonical`, `data/planning_index`, `data/packages`: normalized and derived layers
- `runs/...`: benchmark and evaluation outputs

Right now most live work has been landing in `runs/...` and `artifacts/...`, which is why `data/raw` looked empty. The raw bootstrap path below is the intended fix.

## Script

Run:

```powershell
python scripts\download_raw_data.py --allow-insecure-ssl --download-alphafold-assets --download-mmcif
```

That uses the frozen benchmark cohort from `runs/real_data_benchmark/full_results/usefulness_review.json`.

To target a custom accession set:

```powershell
python scripts\download_raw_data.py `
  --accessions P69905,P68871,P04637,P31749 `
  --sources uniprot,alphafold,bindingdb,intact,rcsb_pdbe,pdbbind `
  --allow-insecure-ssl `
  --download-alphafold-assets `
  --download-mmcif
```

## What It Writes

The script writes under:

- `data/raw/uniprot/<timestamp>/...`
- `data/raw/alphafold/<timestamp>/...`
- `data/raw/bindingdb/<timestamp>/...`
- `data/raw/intact/<timestamp>/...`
- `data/raw/rcsb_pdbe/<timestamp>/...`
- `data/raw/pdbbind/<timestamp>/...`

Each source directory gets a `manifest.json`, and the overall run gets:

- `data/raw/bootstrap_runs/<timestamp>.json`
- `data/raw/bootstrap_runs/LATEST.json`

## Current Source Behavior

- `uniprot`: downloads per-accession JSON, FASTA, and text entries
- `alphafold`: downloads prediction JSON and, if requested, per-accession asset URLs
- `bindingdb`: downloads per-accession ligand-target JSON
- `intact`: downloads interactor JSON plus a small PSICQUIC tab25 slice per accession
- `rcsb_pdbe`: downloads PDBe best-structure mappings and selected RCSB entry JSON, plus mmCIF if requested
- `pdbbind`: currently writes a manual-acquisition placeholder manifest rather than pretending the archive is already mirrored

## Recommended Approach

1. Use this script to build the reproducible raw mirror first.
2. Keep raw files immutable by timestamped run folder.
3. Promote selected releases into canonical ingestion only after the raw manifests are pinned.
4. Treat `PDBBind` as a gated/manual source until we add an explicit authorized ingestion path.
5. Keep bulk mirror state in `data/raw`, not in `runs/...`.

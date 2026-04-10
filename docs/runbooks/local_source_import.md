# Local Source Import

Use this after online raw bootstraps so the large local `bio-agent-lab` corpora are registered into the same manifest-driven raw layer.

## Script

```powershell
python scripts\import_local_sources.py
```

That scans the default local workspace at `C:\Users\jfvit\Documents\bio-agent-lab` and writes inventories plus manifests under:

- `data/raw/local_registry/<timestamp>/...`
- `data/raw/local_registry_runs/<timestamp>.json`
- `data/raw/local_registry_runs/LATEST.json`

## What It Does

- reuses the existing local source registry instead of inventing a second source map
- writes one `inventory.json` and one `manifest.json` per imported source
- keeps heavyweight local archives in place rather than duplicating tens of gigabytes by default
- records counts, total bytes, sample files, join keys, load hints, and missing-root status
- records stable lightweight root fingerprints plus an inventory fingerprint based on relative file paths and byte sizes

## Useful Variants

Import only a few sources:

```powershell
python scripts\import_local_sources.py --sources uniprot,alphafold_db,bindingdb,pdbbind_pp
```

Keep missing sources visible in the raw registry too:

```powershell
python scripts\import_local_sources.py --include-missing
```

## Recommended Workflow

1. Bootstrap online sources into `data/raw/<source>/<timestamp>/...`.
2. Register local `bio-agent-lab` corpora into `data/raw/local_registry/<timestamp>/...`.
3. Pin the run manifests.
4. Build canonical ingestion from those pinned raw manifests instead of from ad hoc live fetches.

# Canonical Materialization

This stage promotes pinned raw source snapshots into canonical records under `data/canonical`.

## Script

```powershell
python scripts\materialize_canonical_store.py
```

By default it reads:

- `data/raw/bootstrap_runs/LATEST.json`
- `data/raw/local_registry_runs/LATEST.json`

and writes:

- `data/canonical/runs/<run_id>/sequence_result.json`
- `data/canonical/runs/<run_id>/structure_result.json`
- `data/canonical/runs/<run_id>/assay_result.json`
- `data/canonical/runs/<run_id>/canonical_store.json`
- `data/canonical/runs/<run_id>/materialization_report.json`
- `data/canonical/LATEST.json`

## Current Conservative Scope

- `UniProt` raw entries feed the canonical protein lane.
- `BindingDB` raw payloads feed the canonical assay lane.
- `AlphaFold DB` raw prediction payloads feed the first structure lane.

`RCSB/PDBe` is currently reported as skipped for local canonical materialization because the present raw bootstrap captures entry JSON and mmCIF, but not the polymer-entity and assembly payloads required by the current structure-bundle parser.

## Useful Variants

```powershell
python scripts\materialize_canonical_store.py --run-id canonical-prod-001
```

```powershell
python scripts\materialize_canonical_store.py --include-all-alphafold-records
```

The default AlphaFold mode is intentionally conservative and only ingests the first prediction record per downloaded accession JSON, because that is the record with pinned local structure assets in the current raw bootstrap.

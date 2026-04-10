# P29 Next Download Wave

- Generated at: `2026-03-30T00:49:28.4244984-05:00`
- Wave file: [`artifacts/status/p29_next_download_wave.json`](/D:/documents/ProteoSphereV2/artifacts/status/p29_next_download_wave.json)

## Ranked Actions

1. `PROSITE` local copy.
2. `Q9UCM0` AlphaFold explicit probe.
3. `ELM` blocked/manual probe.
4. `SABIO-RK` blocked/manual probe.

## Exact Commands

### `PROSITE`

```powershell
Copy-Item -LiteralPath "D:\documents\ProteoSphereV2\protein_data_scope\trial_downloads\prosite\*" -Destination "D:\documents\ProteoSphereV2\data\raw\protein_data_scope_seed\prosite" -Recurse -Force
```

Expected outputs:

- `D:\documents\ProteoSphereV2\data\raw\protein_data_scope_seed\prosite\prosite.dat`
- `D:\documents\ProteoSphereV2\data\raw\protein_data_scope_seed\prosite\prosite.doc`
- `D:\documents\ProteoSphereV2\data\raw\protein_data_scope_seed\prosite\prosite.aux`
- `D:\documents\ProteoSphereV2\data\raw\protein_data_scope_seed\prosite\_source_metadata.json`

### `Q9UCM0` AlphaFold probe

```powershell
python scripts\download_raw_data.py --accessions Q9UCM0 --sources alphafold --raw-root D:\documents\ProteoSphereV2\data\raw --allow-insecure-ssl --download-alphafold-assets
```

Expected outputs if the accession resolves:

- `data/raw/alphafold/<stamp>/Q9UCM0/Q9UCM0.prediction.json`
- `data/raw/alphafold/<stamp>/Q9UCM0/Q9UCM0.bcif.bcif`
- `data/raw/alphafold/<stamp>/Q9UCM0/Q9UCM0.cif.cif`
- `data/raw/alphafold/<stamp>/Q9UCM0/Q9UCM0.pdb.pdb`
- `data/raw/alphafold/<stamp>/Q9UCM0/Q9UCM0.msa.a3m`
- `data/raw/alphafold/<stamp>/Q9UCM0/Q9UCM0.plddt_doc.json`
- `data/raw/alphafold/<stamp>/Q9UCM0/Q9UCM0.pae_doc.json`
- `data/raw/alphafold/<stamp>/Q9UCM0/Q9UCM0.pae_image.png`
- `data/raw/bootstrap_runs/<stamp>.json`

Current honest expectation:

- `status=partial`
- `missing_accessions=['Q9UCM0']`
- no AlphaFold payload if the accession still returns HTTP 404

### `ELM`

```powershell
python protein_data_scope\download_all_sources.py --dest D:\documents\ProteoSphereV2\data\raw\protein_data_scope_seed --sources elm
```

Expected outputs:

- `Warning: unknown source IDs skipped: elm`
- `Sources selected: `
- `data/raw/protein_data_scope_seed/download_run_<timestamp>.log`
- `data/raw/protein_data_scope_seed/download_run_<timestamp>.json` with an empty `sources` array

Status:

- `blocked_manual`

### `SABIO-RK`

```powershell
python protein_data_scope\download_all_sources.py --dest D:\documents\ProteoSphereV2\data\raw\protein_data_scope_seed --sources sabio_rk
```

Expected outputs:

- `Warning: unknown source IDs skipped: sabio_rk`
- `Sources selected: `
- `data/raw/protein_data_scope_seed/download_run_<timestamp>.log`
- `data/raw/protein_data_scope_seed/download_run_<timestamp>.json` with an empty `sources` array

Status:

- `blocked_manual`

## Readout

`PROSITE` is the only immediate copy action that is fully ready now. `Q9UCM0` AlphaFold is the next meaningful probe, but the current evidence says a partial/no-payload outcome is still the most likely result. `ELM` and `SABIO-RK` are honest blocked/manual items until the current downloader manifest grows support for them.

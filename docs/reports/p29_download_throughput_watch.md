# P29 Download Throughput Watch

- Generated at: `2026-03-30T10:27:46.809730+00:00`
- Watch file: [`artifacts/status/p29_download_throughput_watch.json`](/D:/documents/ProteoSphereV2/artifacts/status/p29_download_throughput_watch.json)

## Current Readout

The supervisor is idle now. The last completed lanes were `guarded_sources`, `resolver_safe_bulk`, and `q9ucm0_refresh`.

## Likely Stalls

- `STRING` is the only live-wave lane that showed repeated `WinError 10060` timeouts in the guarded log.
- `ELM` and `SABIO-RK` are blocked by the current downloader manifest, so they are manual/manifest gaps rather than clean download lanes.
- `Q9UCM0` AlphaFold is still likely partial because prior runs already showed HTTP 404 for that accession.

## High-Value Remaining Families

- `interaction_network` is still the biggest breadth gap.
- `motif` has a ready local-copy win in `PROSITE`, but `ELM` stays blocked.
- `structure` still has one useful probe left in `Q9UCM0` AlphaFold.

## Best Next Commands

1. Run the `PROSITE` local copy now.

```powershell
Copy-Item -LiteralPath "D:\documents\ProteoSphereV2\protein_data_scope\trial_downloads\prosite\*" -Destination "D:\documents\ProteoSphereV2\data\raw\protein_data_scope_seed\prosite" -Recurse -Force
```

2. Run the `Q9UCM0` AlphaFold probe next.

```powershell
python scripts\download_raw_data.py --accessions Q9UCM0 --sources alphafold --raw-root D:\documents\ProteoSphereV2\data\raw --allow-insecure-ssl --download-alphafold-assets
```

3. Only retry the guarded wave if `STRING` is explicitly requeued and connectivity is expected to recover.

```powershell
python protein_data_scope\download_all_sources.py --tiers guarded --dest D:\documents\ProteoSphereV2\data\raw\protein_data_scope_seed --timeout 1800 --retries 4
```

## Readout

If the goal is maximum bytes before end of day, the guaranteed win is the `PROSITE` copy. The `Q9UCM0` AlphaFold probe is worth one more attempt, but should be expected to return partial or empty output unless the accession resolves differently than the prior runs. `ELM` and `SABIO-RK` should be treated as blocked until the manifest grows support for them.

# Evolutionary Live Smoke 2026-03-22

## Goal

Run a small, truthful real-data validation on `execution/acquire/evolutionary_snapshot.py` using live upstream data as the seed for a tiny corpus payload.

## Inputs Used

- Live source fetch: `https://rest.uniprot.org/uniprotkb/P69905.json`
- Protein accession: `P69905`
- Derived sequence hash: `sha256:14725a10598943a7aa719eed7d24c7fee599192a6c63c75b051ee6f156341242`
- Temporary corpus file:
  - `C:\Users\jfvit\AppData\Local\Temp\proteosphere_evolutionary_smoke\evolutionary_corpus_live_smoke.json`
- Manifest identity:
  - `source_name`: `Evolutionary / MSA corpus`
  - `release_version`: `2026_03`
  - `retrieval_mode`: `download`
  - `source_locator`: temp corpus path
  - `corpus_snapshot_id`: `live-smoke-p69905`
  - `aligner_version`: `mmseqs2-15`

The temp corpus contained one live-derived record with:

- `accession`: `P69905`
- `sequence_version`: `1`
- `sequence_length`: `142`
- `taxon_id`: `9606`
- `uniref_cluster_ids`: `["UniRef90_P69905"]`
- `orthogroup_ids`: `["OG_HUMAN_GLOBIN"]`
- `quality_flags`: `["live-uniprot-seed", "single-record-smoke"]`
- `source_refs`: `["uniprotkb:P69905", "live-fetch:uniprotkb-json"]`
- `lazy_materialization_refs`: `["msas/P69905.a3m"]`

## Commands Run

First live fetch attempt:

```powershell
python - <<'PY'
from urllib.request import urlopen
urlopen("https://rest.uniprot.org/uniprotkb/P69905.json", timeout=30)
PY
```

This failed in the local Python SSL stack with `CERTIFICATE_VERIFY_FAILED`, so I switched to a shell fetch that could complete against the live endpoint.

Successful live fetch and smoke run:

```powershell
curl.exe -k -L https://rest.uniprot.org/uniprotkb/P69905.json -o %TEMP%\proteosphere_uniprot_P69905.json
```

Then a PowerShell-to-Python smoke script:

```powershell
# fetch live UniProt JSON, derive a one-record corpus payload, write it to
# %TEMP%\proteosphere_evolutionary_smoke\evolutionary_corpus_live_smoke.json,
# then call acquire_evolutionary_snapshot() on that local corpus file
```

## Result

The final smoke succeeded.

- `status`: `ok`
- `reason`: `evolutionary_snapshot_acquired`
- `record_count`: `1`
- `accessions`: `["P69905"]`
- `raw_payload_sha256`: `sha256:41a26fc85c00e7bc985cb42e380b759c048e50b54883bf80b556b2a94a2bc56c`
- `manifest_id`: `Evolutionary / MSA corpus:2026_03:download:77f50ac442e12a86:live-smoke-p69905:mmseqs2-15`

The returned snapshot preserved the live-derived record and provenance:

- `source_refs`: `["uniprotkb:P69905", "live-fetch:uniprotkb-json"]`
- `sequence_hash`: `sha256:14725a10598943a7aa719eed7d24c7fee599192a6c63c75b051ee6f156341242`

## What Failed Along The Way

- The first Python `urlopen()` attempt failed because the local certificate chain could not validate the UniProt TLS certificate.
- The first generated corpus payload was malformed because PowerShell serialized `source_refs` incorrectly and wrote an invalid shape for the loader.

## What This Means Next

- The acquisition path is live-data exercisable today, but the current smoke is still a one-record corpus seeded from live UniProt data and materialized locally before acquisition.
- The next true-data validation wave should use a pinned multi-record corpus snapshot so the loader can be exercised against a broader real payload without relying on ad hoc temp-file assembly.
- If we want a fully automated live corpus run, we still need a small downloader/assembler that writes a validated evolutionary corpus snapshot from live sources before acquisition.

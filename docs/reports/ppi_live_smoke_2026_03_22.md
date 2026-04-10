# PPI Live Smoke Validation

Date: 2026-03-22

This is a first-pass live-data smoke check on one protein-protein interaction source path. I used a local unverified TLS opener only because this workstation's Python `urllib` trust store does not have a usable CA bundle for these endpoints. The requests still went to the live IntAct service.

## Scope

- Source path: IntAct via the official PSICQUIC REST surface
- Real identifier used: `P04637`
- Join cross-check: UniProt accession resolution in the returned participant IDs

## Commands

### Direct live PSICQUIC probe

```powershell
@'
import ssl
from urllib.request import Request, urlopen

ctx = ssl._create_unverified_context()
query_url = 'https://www.ebi.ac.uk/Tools/webservices/psicquic/intact/webservices/current/search/query/id:P04637?format=tab25&firstResult=0&maxResults=3'
req = Request(query_url, headers={'User-Agent': 'ProteoSphereV2-live-smoke/0.1'})
with urlopen(req, timeout=60, context=ctx) as resp:
    print(resp.status)
    print(resp.headers.get('Content-Type'))
    print(resp.read().decode('utf-8', errors='replace')[:2000])
'@ | python -
```

### Repo acquisition wrapper

```powershell
@'
import json
import ssl
from urllib.request import Request, urlopen
from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.intact_snapshot import acquire_intact_snapshot

ctx = ssl._create_unverified_context()
query_url = 'https://www.ebi.ac.uk/Tools/webservices/psicquic/intact/webservices/current/search/query/id:P04637?format=tab25&firstResult=0&maxResults=3'
manifest = SourceReleaseManifest(
    source_name='IntAct',
    release_version='live-smoke',
    release_date='2026-03-22',
    retrieval_mode='query',
    source_locator=query_url,
    provenance=('live-query', 'psicquic', 'intact'),
)

def opener(request, timeout=None):
    if isinstance(request, str):
        request = Request(request, headers={'User-Agent': 'ProteoSphereV2-live-smoke/0.1'})
    return urlopen(request, timeout=timeout, context=ctx)

result = acquire_intact_snapshot(manifest, opener=opener)
print(json.dumps({
    'status': result.status,
    'reason': result.reason,
    'succeeded': result.succeeded,
    'record_count': None if result.snapshot is None else len(result.snapshot.records),
    'first_participant_a_primary_id': None if result.snapshot is None else result.snapshot.records[0].participant_a_primary_id,
    'first_participant_b_primary_id': None if result.snapshot is None else result.snapshot.records[0].participant_b_primary_id,
    'first_participant_a_namespace': None if result.snapshot is None else result.snapshot.records[0].participant_a_identity_namespace,
    'first_participant_b_namespace': None if result.snapshot is None else result.snapshot.records[0].participant_b_identity_namespace,
}, indent=2, sort_keys=True))
'@ | python -
```

## Results

- The live PSICQUIC query returned `200 OK` and `text/plain` content.
- `acquire_intact_snapshot(...)` succeeded with `status = ok` and `record_count = 3`.
- The first parsed record resolved both participant primary IDs to the UniProt accession `P04637` with namespace `uniprotkb`.
- The first live rows were participant-centric MITAB rows for TP53, with evidence such as physical association and direct interaction. The live query surface did not provide a stable interaction AC in the returned tab25 slice.

## What Succeeded

- IntAct is reachable live through PSICQUIC.
- The repo's IntAct acquisition wrapper can ingest a live query URL directly.
- The returned participant IDs are accession-resolved and align with the current join strategy assumptions for protein-bearing pair records.

## What Failed

- Nothing hard-failed in the smoke run.
- The live PSICQUIC `tab25` query is not the right surface if the next validation wave needs canonical IntAct interaction AC or IMEx IDs as the primary join keys. It is good for participant validation, but it is not a full canonical interaction export.

## Implication For The Next Wave

- This source path is usable for live participant-level smoke and join verification.
- The next true-data validation wave should use a richer IntAct export or a full MITAB / PSI-MI payload when interaction AC, IMEx ID, and fuller lineage are required for canonical storage.
- No code changes were needed for this smoke run.

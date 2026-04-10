# Live Source Smoke Validation

Date: 2026-03-22

This is a first-pass live-data smoke check against three tiny representative acquisition paths. I used a local unverified TLS opener only because this workstation's Python `urllib` trust store does not have a usable CA bundle for these endpoints. The requests still went to the live upstream services.

## Scope

- Structure source: RCSB / PDBe
- Sequence reference source: UniProt
- Structure prediction source: AlphaFold DB

## Commands

### RCSB / PDBe

```powershell
$env:PROTEOSPHERE_RCSB_PDBE_SMOKE='1'
@'
import json
import ssl
from urllib.request import Request, urlopen
from execution.acquire.rcsb_pdbe_snapshot import run_live_smoke_snapshot

ctx = ssl._create_unverified_context()
def opener(request, timeout=None):
    if isinstance(request, str):
        request = Request(request, headers={'User-Agent': 'ProteoSphereV2-live-smoke/0.1'})
    return urlopen(request, timeout=timeout, context=ctx)

result = run_live_smoke_snapshot('1CBS', opener=opener, pdbe_opener=opener)
print(json.dumps({
    'status': result.status.value,
    'succeeded': result.succeeded,
    'blockers': [b.to_dict() for b in result.blockers],
    'bundle_count': len(result.structure_bundles),
    'assets': [
        {'source': a.source, 'resource': a.resource, 'identifier': a.identifier}
        for a in result.assets[:5]
    ],
}, indent=2, sort_keys=True))
'@ | python -
```

### UniProt

Live response headers for `P69905` were checked first:

```powershell
@'
import ssl
from urllib.request import Request, urlopen
ctx = ssl._create_unverified_context()
req = Request('https://rest.uniprot.org/uniprotkb/P69905.json', headers={'User-Agent': 'ProteoSphereV2-smoke/0.1'})
with urlopen(req, timeout=30, context=ctx) as resp:
    print(resp.status)
    for key, value in resp.headers.items():
        if 'release' in key.lower() or 'uniprot' in key.lower() or key.lower().startswith('x-'):
            print(f'{key}: {value}')
'@ | python -
```

Acquisition smoke:

```powershell
@'
import json
import ssl
from urllib.request import Request, urlopen
from execution.acquire.uniprot_snapshot import acquire_uniprot_snapshot

ctx = ssl._create_unverified_context()
def opener(request, timeout=None):
    if isinstance(request, str):
        request = Request(request, headers={'User-Agent': 'ProteoSphereV2-live-smoke/0.1'})
    return urlopen(request, timeout=timeout, context=ctx)

manifest = {
    'source': 'UniProt',
    'release': '2026_01',
    'release_date': '2026-01-28',
    'proteome_id': 'UP000005640',
    'proteome_name': 'Homo sapiens',
    'proteome_reference': True,
    'proteome_taxon_id': 9606,
    'accessions': ['P69905'],
    'manifest_id': 'uniprot:live-smoke:P69905',
    'provenance': {
        'source_ids': ['raw/uniprot/P69905.json'],
    },
}
result = acquire_uniprot_snapshot(manifest, opener=opener)
print(json.dumps({
    'status': result.status,
    'blocker_reason': result.blocker_reason,
    'unavailable_reason': result.unavailable_reason,
    'record_count': None if result.snapshot is None else len(result.snapshot.records),
    'first_accession': None if result.snapshot is None else result.snapshot.records[0].accession,
    'first_protein_name': None if result.snapshot is None else result.snapshot.records[0].sequence.protein_name,
}, indent=2, sort_keys=True))
'@ | python -
```

### AlphaFold DB

```powershell
$env:PROTEOSPHERE_ALPHAFOLD_SMOKE='1'
@'
import json
import ssl
from urllib.request import Request, urlopen
from execution.acquire.alphafold_snapshot import run_live_smoke_snapshot

ctx = ssl._create_unverified_context()
def opener(request, timeout=None):
    if isinstance(request, str):
        request = Request(request, headers={'User-Agent': 'ProteoSphereV2-live-smoke/0.1'})
    return urlopen(request, timeout=timeout, context=ctx)

result = run_live_smoke_snapshot('P69905', opener=opener, asset_opener=opener)
print(json.dumps({
    'status': result.status.value,
    'succeeded': result.succeeded,
    'manifest_id': result.manifest.manifest_id,
    'record_count': len(result.records),
    'first_kind': None if not result.records else result.records[0].structure_kind,
    'first_qualifier': None if not result.records else result.records[0].qualifier,
    'asset_count': len(result.assets),
}, indent=2, sort_keys=True))
'@ | python -
```

## Results

- UniProt succeeded for `P69905`.
- AlphaFold DB succeeded for `P69905`.
- RCSB / PDBe failed in the live acquisition path for `1CBS`.

## What Succeeded

- UniProt returned live data for `P69905`. The smoke acquisition completed as `ready`, reported `record_count = 1`, and normalized the first record to `Hemoglobin subunit alpha`.
- AlphaFold DB returned live prediction data for `P69905`. The smoke acquisition completed as `ready` with one prediction record and no asset fetches required for this tiny probe.

## What Failed

- RCSB / PDBe reached the live entry endpoint for `1CBS`, but bundle materialization stopped in parser normalization with `payload does not contain a valid PDB identifier`.
- The live entity and assembly payloads use suffixed identifiers such as `1CBS_1` and `1CBS-1`, while the current parser normalizes `rcsb_id` directly for those payload types. That behavior is visible in `connectors/rcsb/parsers.py:186-188` and `connectors/rcsb/parsers.py:237-239`.

## Implication For The Next Wave

- UniProt and AlphaFold DB are ready for the next live validation wave.
- RCSB / PDBe needs a small parser hardening change before the next wave can be truly end-to-end on live data. The safest fix is to prefer the live `entry_id` field for entity and assembly normalization, or otherwise tolerate the live `rcsb_id` suffix forms without collapsing the entry identity.
- The first smoke pass intentionally reported the blocker before any code change; the remediation smoke below shows the fixed parser now accepts the live payload shape.

## Remediation Smoke

After patching the parser to prefer the nested `entry_id` for entity and assembly payloads, I reran the same live `1CBS` probe and it succeeded:

- `status = complete`
- `succeeded = true`
- `bundle_count = 1`
- `entity_count = 1`
- `assembly_count = 1`
- `first_pdb_id = 1CBS`

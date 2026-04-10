# Annotation / Pathway Live Smoke Validation

Date: 2026-03-22

## Scope

Tiny live-data smoke on the annotation/pathway side that matters for the summary library, anchored on one protein example: `P69905` (`Hemoglobin subunit alpha`).

## Commands

### UniProt anchor

```powershell
@'
import json
import ssl
from urllib.request import Request, urlopen

ctx = ssl._create_unverified_context()
req = Request(
    'https://rest.uniprot.org/uniprotkb/P69905.json',
    headers={'User-Agent': 'ProteoSphereV2-live-smoke/0.1'},
)
with urlopen(req, timeout=60, context=ctx) as resp:
    payload = json.loads(resp.read().decode('utf-8'))
print(json.dumps({
    'accession': payload['primaryAccession'],
    'protein_name': payload['proteinDescription']['recommendedName']['fullName']['value'],
    'length': payload['sequence']['length'],
}, indent=2, sort_keys=True))
'@ | python -
```

### InterPro live annotation probe

```powershell
@'
import json
import ssl
from urllib.request import Request, urlopen

ctx = ssl._create_unverified_context()
req = Request(
    'https://www.ebi.ac.uk/interpro/api/entry/interpro/protein/uniprot/P69905/',
    headers={'User-Agent': 'ProteoSphereV2-live-smoke/0.1'},
)
with urlopen(req, timeout=60, context=ctx) as resp:
    payload = json.loads(resp.read().decode('utf-8'))
first = payload['results'][0]
print(json.dumps({
    'entry_count': payload['count'],
    'first_entry': first['metadata']['accession'],
    'first_entry_name': first['metadata']['name'],
    'first_entry_type': first['metadata']['type'],
    'first_match_accession': first['proteins'][0]['accession'],
    'first_match_length': first['proteins'][0]['protein_length'],
}, indent=2, sort_keys=True))
'@ | python -
```

### Reactome live pathway mapping

```powershell
@'
import json
import ssl
from urllib.request import Request, urlopen

from execution.acquire.reactome_snapshot import acquire_reactome_snapshot

ctx = ssl._create_unverified_context()
reactome = acquire_reactome_snapshot(
    {
        'release': {
            'source_name': 'Reactome',
            'release_version': 'v95',
            'release_date': '2025-12-09',
            'retrieval_mode': 'download',
            'source_locator': 'https://reactome.org/download-data',
        },
        'assets': [
            {
                'asset_name': 'uniprot_pathway_mapping',
                'asset_url': 'https://reactome.org/ContentService/data/mapping/UniProt/P69905/pathways',
                'asset_kind': 'pathway',
                'stable_ids': ['P69905'],
                'species': 'Homo sapiens',
            }
        ],
    },
    acquired_on='2026-03-22',
)
rows = json.loads(reactome.assets[0].text) if reactome.assets and reactome.assets[0].text else []
print(json.dumps({
    'status': reactome.status,
    'reason': reactome.reason,
    'asset_status': reactome.assets[0].status if reactome.assets else None,
    'asset_kind': reactome.assets[0].asset_kind if reactome.assets else None,
    'row_count': len(rows),
    'first_stId': rows[0]['stId'] if rows else None,
    'first_displayName': rows[0]['displayName'] if rows else None,
    'first_speciesName': rows[0]['speciesName'] if rows else None,
}, indent=2, sort_keys=True))
'@ | python -
```

## Identifiers Used

- UniProt accession: `P69905`
- InterPro protein accession: `P69905`
- InterPro first hit: `IPR000971` `Globin`
- Reactome UniProt pathway mapping: `P69905`

## What Succeeded

- UniProt live anchor retrieval succeeded for `P69905`.
- InterPro live protein annotation retrieval succeeded for `P69905`.
- InterPro returned `6` protein-linked entries for `P69905`.
- The first InterPro hit was `IPR000971` `Globin`, and the first returned protein match preserved the same accession and a protein length of `142`.
- Reactome live pathway mapping succeeded for `P69905` through the repo acquisition wrapper.
- Reactome returned `6` pathway rows for the protein mapping, with the first row resolving to `R-HSA-1237044` `Erythrocytes take up carbon dioxide and release oxygen`.

## What Failed

```powershell
@'
import ssl
from urllib.request import Request, urlopen

ctx = ssl._create_unverified_context()
req = Request(
    'https://reactome.org/ContentService/data/query/P69905',
    headers={'User-Agent': 'ProteoSphereV2-live-smoke/0.1'},
)
with urlopen(req, timeout=60, context=ctx) as resp:
    print(resp.status)
'@ | python -
```

- That direct Reactome content-service probe returned `404`.
- That is not a blocker for the smoke, but it is a useful boundary: the working live pathway join is the UniProt mapping endpoint, not the guessed query path.

## Implication For The Next Wave

- The protein-side anchor and both enrichment layers are live and usable today for a small summary-library smoke.
- For the next true-data wave, keep using the UniProt accession as the join spine, then attach InterPro entry annotations and Reactome pathway mappings from the live endpoints that actually return machine-readable data.
- The Reactome query surface should not be assumed; the UniProt mapping endpoint is the safer validation target for now.

# BindingDB Live Smoke Validation

Date: 2026-03-22

## Scope

Small live-data smoke on the protein-ligand acquisition path using a single UniProt target against BindingDB, then a UniProt cross-check for the same protein accession.

## Commands

```powershell
@'
from execution.acquire.bindingdb_snapshot import BindingDBSnapshotManifest, acquire_bindingdb_snapshot
from connectors.bindingdb.client import BindingDBClient
from connectors.uniprot.client import UniProtClient
from connectors.uniprot.parsers import parse_uniprot_entry

accession = 'P31749'
client = BindingDBClient()
raw = client.get_ligands_by_uniprot(accession)
root_key = next(iter(raw)) if isinstance(raw, dict) and raw else None
root = raw[root_key] if root_key else None
first_aff = root.get('bdb.affinities', [None])[0] if isinstance(root, dict) else None

print('bindingdb.root_key=', root_key)
print('bindingdb.primary=', root.get('bdb.primary'))
print('bindingdb.hit=', root.get('bdb.hit'))
print('bindingdb.affinity_count=', len(root.get('bdb.affinities') or []))
print('bindingdb.first_monomerid=', first_aff.get('bdb.monomerid'))
print('bindingdb.first_smile=', first_aff.get('bdb.smile'))
print('bindingdb.first_affinity_type=', first_aff.get('bdb.affinity_type'))
print('bindingdb.first_affinity=', first_aff.get('bdb.affinity'))

manifest = BindingDBSnapshotManifest(
    snapshot_id='live-smoke-P31749',
    query_kind='uniprot',
    query_values=(accession,),
    release_pin='live',
)
result = acquire_bindingdb_snapshot(manifest, acquired_on='2026-03-22')
print('snapshot.status=', result.status)
print('snapshot.reason=', result.reason)
print('snapshot.record_count=', len(result.records))
print('snapshot.first_record=', result.records[0].to_dict() if result.records else None)

u = UniProtClient()
entry = u.get_entry(accession)
parsed = parse_uniprot_entry(entry)
print('uniprot.accession=', parsed.accession)
print('uniprot.protein_name=', parsed.protein_name)
print('uniprot.organism=', parsed.organism_name)
print('uniprot.sequence_length=', parsed.sequence_length)
print('uniprot.reviewed=', parsed.reviewed)
'@ | python -
```

## Identifiers Used

- BindingDB target accession: `P31749`
- UniProt cross-check accession: `P31749`
- BindingDB first ligand hit from the live response:
  - `bdb.monomerid = 2579`
  - `bdb.affinity_type = IC50`
  - `bdb.affinity = 3.8`

## What Succeeded

- Live BindingDB access succeeded for `getLigandsByUniprot(P31749)`.
- The raw BindingDB response contained `bdb.hit = 3518` and `bdb.affinities` entries.
- UniProt cross-check succeeded for `P31749`.
- UniProt resolved `P31749` to `RAC-alpha serine/threonine-protein kinase` with sequence length `480` and `reviewed = True`.

## What Failed

- The current normalized BindingDB acquisition path does not yet decode the live response shape truthfully.
- `acquire_bindingdb_snapshot(...)` returned `status = ok`, but the parsed record was effectively empty because the live JSON nests affinities under `getLindsByUniprotResponse.bdb.affinities`, which the current parser does not flatten.

## Implications

- The external data path is reachable and the protein identifier is consistent end-to-end.
- The next validation wave should add a tight parser regression for the live `getLindsByUniprotResponse` shape before treating BindingDB acquisition as fully integrated.
- I did not change code in this smoke pass; the report is intentionally honest about the current normalization gap.

## Remediation Result

After the parser fix, the same live accession was re-run with the same `P31749` target and the acquisition path now normalized the live payload truthfully.

- `status = ok`
- `reason = bindingdb_snapshot_acquired`
- `record_count = 3518`
- First normalized record:
  - `bdb.monomerid = 2579`
  - `bdb.smile = C[C@@]12[C@@H]([C@@H](C[C@@H](O1)n3c4ccccc4c5c3c6n2c7ccccc7c6c8c5C(=O)NC8)NC)OC`
  - `bdb.affinity_type = IC50`
  - `bdb.affinity = 3.8`
  - `target_uniprot_ids = ("P31749", "B2RAM5", "B7Z5R1", "Q9BWB6")`

This confirms the live BindingDB envelope is now flattened into conservative assay records without losing the target lineage or ligand identity.

# P34 P09105 Fresh-Run Ligand Blocker

- Generated at: `2026-03-31T14:52:43.3965196-05:00`
- Selected gap: `ligand:P09105`
- Fresh-run-only: `yes`
- Basis: [`p34_packet_gap_current_state_ranking.json`](/D:/documents/ProteoSphereV2/artifacts/status/p34_packet_gap_current_state_ranking.json)

## Why P09105

P09105 is the higher-ranked of the two remaining local candidates. It is the more realistic next slice to try from the current ranking, but the fresh local ChEMBL evidence still comes back empty.

## Exact Local Evidence

- [`packet_manifest.json`](/D:/documents/ProteoSphereV2/data/packages/post-local-refresh-20260330T2216Z/packet-p09105/packet_manifest.json)
- [`structure-1.gz`](/D:/documents/ProteoSphereV2/data/packages/post-local-refresh-20260330T2216Z/packet-p09105/artifacts/structure-1.gz)
- [`p34_p09105_local_ligand_source_map.json`](/D:/documents/ProteoSphereV2/artifacts/status/p34_p09105_local_ligand_source_map.json)
- [`p34_p09105_local_chembl_rescue_brief.json`](/D:/documents/ProteoSphereV2/artifacts/status/p34_p09105_local_chembl_rescue_brief.json)
- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db`

## Commands Run

1. `python scripts/probe_local_ligand_source_map.py --accessions P09105 --output artifacts/status/p34_p09105_local_ligand_source_map.json`
2. `python scripts/export_local_chembl_rescue_brief.py --accession P09105 --output artifacts/status/p34_p09105_local_chembl_rescue_brief.json --markdown docs/reports/p34_p09105_local_chembl_rescue_brief.md`
3. `python scripts/export_p00387_ligand_extraction_contract.py --accession P09105 --output artifacts/status/p34_p09105_ligand_extraction_contract.json --markdown docs/reports/p34_p09105_ligand_extraction_contract.md`

The third command was an explicit truth check. It did not create a valid P09105 rescue artifact, so the blocker remains evidence-only.

## Outcome

- The local ligand source map classified P09105 as `structure_companion_only`.
- The local ChEMBL rescue brief returned `no_local_candidate`.
- The local ChEMBL evidence showed `0` target hits.
- No fresh-run ligand packet payload was materialized.

## Truth Boundary

This is a blocker/result slice, not a packet rescue. It is fresh-run-only evidence/reporting and it does not touch the protected latest snapshot or the latest-promotion guardrails.

## What Improved

- The blocker is now explicit and accession-scoped.
- The fresh-run evidence surfaces were refreshed for P09105.

## What Did Not Improve

- The packet deficit did not change.
- The protected latest did not change.
- There is still no run-scoped ligand payload for P09105.

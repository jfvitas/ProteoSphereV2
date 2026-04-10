# P34 Q2TAC2 Fresh-Run Ligand Blocker

- Generated at: `2026-03-31T14:53:54.3783212-05:00`
- Selected gap: `ligand:Q2TAC2`
- Fresh-run-only: `yes`
- Basis: [`p34_packet_gap_current_state_ranking.json`](/D:/documents/ProteoSphereV2/artifacts/status/p34_packet_gap_current_state_ranking.json)

## Why Q2TAC2

Q2TAC2 is the next realistic local ligand lane after the P09105 blocker slice, but the fresh local ChEMBL evidence still comes back empty.

## Exact Local Evidence

- [`packet_manifest.json`](/D:/documents/ProteoSphereV2/data/packages/post-local-refresh-20260330T2216Z/packet-q2tac2/packet_manifest.json)
- [`structure-1.gz`](/D:/documents/ProteoSphereV2/data/packages/post-local-refresh-20260330T2216Z/packet-q2tac2/artifacts/structure-1.gz)
- [`p34_q2tac2_local_ligand_source_map.json`](/D:/documents/ProteoSphereV2/artifacts/status/p34_q2tac2_local_ligand_source_map.json)
- [`p34_q2tac2_local_chembl_rescue_brief.json`](/D:/documents/ProteoSphereV2/artifacts/status/p34_q2tac2_local_chembl_rescue_brief.json)
- `C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db`

## Commands Run

1. `python scripts/probe_local_ligand_source_map.py --accessions Q2TAC2 --output artifacts/status/p34_q2tac2_local_ligand_source_map.json`
2. `python scripts/export_local_chembl_rescue_brief.py --accession Q2TAC2 --output artifacts/status/p34_q2tac2_local_chembl_rescue_brief.json --markdown docs/reports/p34_q2tac2_local_chembl_rescue_brief.md`

## Outcome

- The local ligand source map classified Q2TAC2 as `structure_companion_only`.
- The local ChEMBL rescue brief returned `no_local_candidate`.
- The local ChEMBL evidence showed `0` target hits.
- No fresh-run ligand packet payload was materialized.

## Truth Boundary

This is a blocker/result slice, not a packet rescue. It is fresh-run-only evidence/reporting and it does not touch the protected latest snapshot or the latest-promotion guardrails.

## What Improved

- The blocker is now explicit and accession-scoped.
- The fresh-run evidence surfaces were refreshed for Q2TAC2.

## What Did Not Improve

- The packet deficit did not change.
- The protected latest did not change.
- There is still no run-scoped ligand payload for Q2TAC2.

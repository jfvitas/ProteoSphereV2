# P28 Procurement Watch

- Generated at: `2026-03-29T06:33:50.7772853-05:00`
- Watch file: [`artifacts/status/p28_procurement_watch.json`](/D:/documents/ProteoSphereV2/artifacts/status/p28_procurement_watch.json)

## Started

- `packet_gap_accession_refresh` completed successfully at `2026-03-29T11:32:42.083788+00:00`.
- `guarded_sources` is running for guarded-tier bulk procurement of STRING and BioGRID.
- `resolver_safe_bulk` is running for resolver-safe bulk procurement of AlphaFold DB, IntAct, and BindingDB.

## Pending Next

- The supervisor queue still lists `q9ucm0_refresh` as pending.
- Current packet state remains `7` complete / `5` partial, with deficits concentrated in `ligand=5`, `ppi=1`, and `structure=1`.

## Rerun After Each Tranche

- After `packet_gap_accession_refresh` completes, rerun [`artifacts/status/procurement_status_board.json`](/D:/documents/ProteoSphereV2/artifacts/status/procurement_status_board.json), [`artifacts/status/packet_deficit_dashboard.json`](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json), and [`artifacts/status/q9ucm0_acquisition_proof.json`](/D:/documents/ProteoSphereV2/artifacts/status/q9ucm0_acquisition_proof.json).
- After `guarded_sources` completes, rerun [`artifacts/status/procurement_status_board.json`](/D:/documents/ProteoSphereV2/artifacts/status/procurement_status_board.json), [`artifacts/status/packet_deficit_dashboard.json`](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json), and [`artifacts/status/q9ucm0_acquisition_requirements.json`](/D:/documents/ProteoSphereV2/artifacts/status/q9ucm0_acquisition_requirements.json).
- After `resolver_safe_bulk` completes, rerun [`artifacts/status/procurement_status_board.json`](/D:/documents/ProteoSphereV2/artifacts/status/procurement_status_board.json), [`artifacts/status/packet_deficit_dashboard.json`](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json), and `data/raw/bootstrap_runs/LATEST.json`.

## Readout

The live refresh tranche has already advanced Q9UCM0 across UniProt, BindingDB, IntAct, and RCSB/PDBe. The remaining work is to let the guarded and resolver-safe procurement tranches finish, then immediately rerun the status artifacts so the next integration step reflects the newest source material.

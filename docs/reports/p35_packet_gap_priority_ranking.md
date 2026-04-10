# P35 Packet Gap Priority Ranking

- Generated at: `2026-03-31T14:57:50.3589476-05:00`
- Scope: current unresolved packet refs only
- Fresh-run-only: `yes`
- Basis: `packet_deficit_dashboard.json`, `available_payloads.generated.json`, `local_bridge_ligand_payloads.real.json`, and the Q9UCM0 / ligand blocker artifacts

## Current Truth

The preserved latest still carries five deficits. Fresh-run payload surfaces already include `ligand:P00387` and `ligand:Q9NZD4`, so the ranking below focuses on what still needs either packet-surface reconciliation or fresh acquisition.

## Priority Ranking

1. `ligand:P00387`
   - This is the only lane that is still genuinely actionable from current local evidence.
   - Local ChEMBL already produced a rescue candidate, and the available-payload registry already includes `ligand:P00387`.
   - The next step is surface reconciliation into packet views, not a new acquisition.

2. `structure:Q9UCM0`
   - Blocked.
   - Current local registry, AlphaFold, RCSB, BioLiP, and PDBbind evidence do not provide a truthful accession-clean structure route.

3. `ppi:Q9UCM0`
   - Blocked.
   - IntAct is alias-only for this accession, and BioGRID/STRING are not present in the local inventory.

4. `ligand:Q9UCM0`
   - Blocked.
   - There is no accession-safe local BindingDB or ChEMBL route, and the missing structure lane prevents a truthful structure-backed ligand rescue.

5. `ligand:P09105`
   - Blocked.
   - Fresh local ChEMBL probing returned `no_local_candidate`.

6. `ligand:Q2TAC2`
   - Blocked.
   - Fresh local ChEMBL probing returned `no_local_candidate`.

## Exact Evidence Anchors

- `artifacts/status/packet_deficit_dashboard.json`
- `runs/real_data_benchmark/full_results/available_payloads.generated.json`
- `artifacts/status/local_bridge_ligand_payloads.real.json`
- `artifacts/status/q9ucm0_acquisition_proof.json`
- `artifacts/status/q9ucm0_acquisition_requirements.json`
- `artifacts/status/p34_p00387_local_chembl_rescue_brief.json`
- `artifacts/status/p34_p09105_fresh_run_ligand_blocker.json`
- `artifacts/status/p34_q2tac2_fresh_run_ligand_blocker.json`

## Boundary

This report is a priority surface only. It does not modify the protected latest and does not assert any new packet promotion.

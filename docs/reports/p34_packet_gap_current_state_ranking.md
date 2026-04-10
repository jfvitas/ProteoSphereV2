# Packet Gap Current-State Ranking

- Generated at: `2026-03-31T14:41:05.9810046-05:00`
- Preserved latest: `data/packages/LATEST.json`
- Freshest run-scoped materialization: `data/packages/training-packets-20260331T193611Z`
- Preserved latest remains guarded and unchanged.

## What Changed In The Fresh Run

- `Q9NZD4` is present in the freshest run-scoped packet manifest with `sequence` and `ligand`.
- `Q9UCM0` is present in the freshest run-scoped packet manifest with `sequence` and `ligand`.
- The protected latest snapshot still lags behind those fresh run-scoped states.

## Execution Ranking

| Rank | Source ref | State | Best next move | Exact sources |
| --- | --- | --- | --- | --- |
| 1 | `ligand:P00387` | rescuable_now | Materialize from local ChEMBL evidence | `artifacts/status/p00387_local_chembl_rescue.json`, `artifacts/status/local_chembl_rescue_brief.json`, `data/raw/local_registry/20260323T003221Z/chembl/manifest.json` |
| 2 | `ligand:P09105` | rescuable_now | Extract from existing packet structure | `data/packages/post-local-refresh-20260330T2216Z/packet-p09105/packet_manifest.json`, `data/packages/post-local-refresh-20260330T2216Z/packet-p09105/artifacts/structure-1.gz` |
| 3 | `ligand:Q2TAC2` | rescuable_now | Extract from existing packet structure | `data/packages/post-local-refresh-20260330T2216Z/packet-q2tac2/packet_manifest.json`, `data/packages/post-local-refresh-20260330T2216Z/packet-q2tac2/artifacts/structure-1.gz` |
| 4 | `ligand:Q9UCM0` | current_run_present | Report the fresh run state, do not re-open the lane | `data/packages/training-packets-20260331T193611Z/packet-q9ucm0/packet_manifest.json`, `runs/real_data_benchmark/full_results/available_payloads.generated.json` |
| 5 | `structure:Q9UCM0` | blocked | Keep blocked pending fresh acquisition | `docs/reports/q9ucm0_structure_gap_local_investigation_2026_03_23.md`, `docs/reports/q9ucm0_acquisition_brief_2026_03_23.md` |
| 6 | `ppi:Q9UCM0` | blocked | Keep blocked pending fresh acquisition | `docs/reports/q9ucm0_acquisition_brief_2026_03_23.md`, `docs/reports/q9ucm0_acquisition_checklist_2026_03_23.md` |

## Readout

- `ligand:P00387`, `ligand:P09105`, and `ligand:Q2TAC2` are the next genuinely executable local rescue lanes.
- `ligand:Q9UCM0` is already present in the freshest run-scoped packet manifest, so it belongs in current-state reporting, not in a fresh rescue queue.
- `structure:Q9UCM0` and `ppi:Q9UCM0` remain blocked pending fresh acquisition.
- The protected latest snapshot should stay untouched.

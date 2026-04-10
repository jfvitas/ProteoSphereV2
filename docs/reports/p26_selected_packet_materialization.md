# P26 Selected Packet Materialization

## Current latest packet truth

- Source artifact: `artifacts/status/packet_deficit_dashboard.json`
- Generated at: `2026-03-23T17:54:12.104534+00:00`
- Latest packet status: `complete`
- Packet counts: `{'complete': 7, 'partial': 5}`
- Missing modality counts: `{'ligand': 5, 'ppi': 1, 'structure': 1, 'sequence': 0}`

## What is restored

- The promoted `data/packages/LATEST.json` view is back to a strong latest packet set with `12` packets total.
- `7` packets are fully complete: `P02042`, `P02100`, `P04637`, `P31749`, `P68871`, `P69892`, and `P69905`.
- `5` packets remain partial: `P00387`, `P09105`, `Q2TAC2`, `Q9NZD4`, and `Q9UCM0`.
- The remaining direct deficits are narrow and procurement-facing:
  - ligand gaps on `P00387`, `P09105`, `Q2TAC2`, `Q9NZD4`, `Q9UCM0`
  - one missing PPI lane on `Q9UCM0`
  - one missing structure lane on `Q9UCM0`

## Scoped post-Tier1 regression truth

- Source artifact: `runs/tier1_direct_validation/20260323T180625Z/selected_cohort_materialization.json`
- Scoped rerun status: `partial`
- Scoped packet counts: `{'complete': 7, 'partial': 5}`
- Scoped latest promotion state: `held`
- Scoped release-grade ready: `false`

Race-condition caveat:

- older scoped run artifacts under `runs/tier1_direct_validation/20260323T175411Z` still show the pre-fallback `{'complete': 3, 'partial': 9}` view
- operator/procurement reporting should follow the current scoped run at `20260323T180625Z`
- this matters because the bridge-ligand fallback fix restored `P69905`, `P02042`, `P02100`, and `P69892` into the scoped complete set

This scoped Tier 1 rerun is still a truthful regression probe, not the authoritative packet latest. It now matches the restored `7/5` scoped state after the bridge-ligand fallback fix, while the race-condition caveat keeps the older stale scoped files from being mistaken as current.

## Procurement interpretation

- Packet logic is no longer the primary bottleneck for the latest promoted packet set.
- The remaining highest-leverage procurement work is concentrated in ligand completion for the five partial packets and full modality closure for `Q9UCM0`.
- Tier 1 direct promotion proved the procurement/promotion path can succeed, but the scoped rerun is still only `7/5`, so ligand completion remains the main procurement follow-on.

## Artifact paths

- Latest packet dashboard: `artifacts/status/packet_deficit_dashboard.json`
- Latest packet markdown: `docs/reports/packet_deficit_dashboard.md`
- Scoped Tier 1 materialization: `runs/tier1_direct_validation/20260323T175411Z/selected_cohort_materialization.json`
- Latest packet summary pointer: `data/packages/LATEST.json`

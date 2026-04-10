# Assay Bottleneck Status

Generated from the live canonical and packet artifacts on 2026-03-23.

Current state:
- Canonical assay lane: resolved
- Canonical assay count: `5138`
- Canonical assay unresolved count: `0`
- Packet state: `7 complete / 5 partial`

Current interpretation:
- The assay bottleneck is no longer the canonical unresolved count.
- The live canonical source of truth is back to a resolved assay lane with
  `5138` canonical assay records and `0` unresolved assay cases.
- The remaining bottlenecks are now the narrower packet-layer modality gaps,
  especially ligand completion plus the remaining `Q9UCM0` structure/PPI gaps.

Verified live artifacts:
- `data/canonical/LATEST.json`
  - `status = ready`
  - `record_counts.assay = 5138`
  - `unresolved_counts.assay_unresolved_cases = 0`
- `artifacts/status/post_tier1_direct_pipeline.json`
  - `status = passed`
  - `packet_regression_gate.status = passed`
- `artifacts/status/packet_deficit_dashboard.json`
  - `packet_status_counts = { complete: 7, partial: 5 }`
  - `modality_deficit_counts = { ligand: 5, ppi: 1, structure: 1 }`

Highest-value remaining data work:
1. Reduce the remaining ligand deficits for `P00387`, `P09105`, `Q2TAC2`,
   `Q9NZD4`, and `Q9UCM0`.
2. Resolve the last `Q9UCM0` structure and PPI gaps with truthful new
   acquisition or a bounded local rescue.
3. Keep the canonical assay lane pinned to the stronger restored local
   BindingDB-backed state so later narrow probe runs do not silently degrade it
   again.

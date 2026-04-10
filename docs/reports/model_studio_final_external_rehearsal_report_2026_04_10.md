# Model Studio Final External Rehearsal Report

Date: 2026-04-10

## Scope

This rehearsal covers the frozen controlled-beta surface:

- `release_pp_alpha_benchmark_v1`
- `robust_pp_benchmark_v1`
- `expanded_pp_benchmark_v1`
- `governed_ppi_blended_subset_v2`
- `governed_ppi_external_beta_candidate_v1`
- `governed_pl_bridge_pilot_subset_v1`
- blocked `PyRosetta`
- blocked `Free-state comparison`

## Evidence Bundle

Primary bundle:

- `artifacts/reviews/model_studio_internal_alpha/final_external_rehearsal_2026_04_10`

Key artifacts:

- visual manifest:
  - `artifacts/reviews/model_studio_internal_alpha/final_external_rehearsal_2026_04_10/visual/visual_review_manifest.json`
- blocked-lane trace:
  - `artifacts/reviews/model_studio_internal_alpha/final_external_rehearsal_2026_04_10/blocked/blocked_feature_trace.json`
- PPI guided-flow trace:
  - `artifacts/reviews/model_studio_internal_alpha/final_external_rehearsal_2026_04_10/ppi_flow/user_sim_trace.json`
- ligand guided-flow trace:
  - `artifacts/reviews/model_studio_internal_alpha/final_external_rehearsal_2026_04_10/ligand_flow/user_sim_trace.json`
- ligand launch matrix:
  - `artifacts/reviews/model_studio_internal_alpha/ligand_pilot_round_1/ligand_execution_matrix.json`

## Current Truth

- PPI primary lane is launchable.
- Protein-ligand pilot is launchable.
- Stage 2 scientific tracks are visible, artifact-backed, and blocked.
- The final evidence bundle is complete enough for signoff review.

## Remaining Ship Blockers

- final current-wave reviewer signoff still requires explicit McClintock re-approval after the governance fix

## Parallel Non-Blocking Risk

- `expanded_ppi_procurement_bridge` still contributes 92% of the governed staged candidate rows
- this remains documented and owned as a post-freeze remediation track, not a launch blocker unless a new canonical truth failure appears

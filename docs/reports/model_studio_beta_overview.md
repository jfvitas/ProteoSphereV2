# Model Studio Beta Overview

## What This Beta Includes

This is a controlled user-facing beta for Model Studio with a PPI-first launch surface and one narrow protein-ligand pilot.

Current launchable lane:

- `release_pp_alpha_benchmark_v1`
- `robust_pp_benchmark_v1`
- `expanded_pp_benchmark_v1`
- `governed_ppi_blended_subset_v2`
- `governed_ppi_external_beta_candidate_v1`
- `governed_pl_bridge_pilot_subset_v1`

Active beta lanes with limits:

- atom-native beta
- Studio-local deterministic sequence-embedding beta

Review-pending prototype tracks:

- PyRosetta
- free-state comparison

## What This Beta Does Not Include Yet

- broad non-PPI task activation
- AlphaFold-derived claims
- broad protein-ligand expansion beyond the bridge pilot

## How To Use It Safely

- Prefer launchable pools first.
- Use `governed_pl_bridge_pilot_subset_v1` only for structure-backed `protein-ligand` `delta_G` studies.
- Treat review-pending items as visible for audit, not routine study work.
- Use the guided flow rather than jumping directly into advanced settings unless you know the current truth boundary.

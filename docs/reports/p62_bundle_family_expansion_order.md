# P62 Bundle Family Expansion Order

This report-only note gives the exact safe order for the next 3-5 bundle-family iterations beyond the current verified lightweight preview baseline.

## Current Baseline

The bundle is still a verified preview:

- [artifacts/status/lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [artifacts/status/live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json)

Current baseline facts:

- `manifest_status`: `preview_generated_verified_assets`
- `budget_class`: `A`
- compressed size: `237008` bytes
- soft target: `67108864` bytes
- warning threshold: `134217728` bytes
- hard cap: `268435456` bytes

Verified family counts today:

- proteins: 11
- protein variants: 1874
- structures: 4
- motif annotations: 98
- pathway annotations: 254
- provenance records: 1915

## Safe Expansion Order

The next safe iterations are:

1. `protein_similarity_signatures`
1. `leakage_groups`
1. `structure_similarity_signatures`
1. `ligands`
1. `interactions`

`dictionaries` stays outside this window and should be considered only after the preview has absorbed the families above.

## Why This Order

The order starts with the smallest truth-preserving governance surfaces, then moves toward payload-bearing families:

- `protein_similarity_signatures` is the lightest first growth step because it summarizes already-materialized proteins.
- `leakage_groups` comes next so split governance stays explicit before broader family growth.
- `structure_similarity_signatures` extends the same low-risk pattern to the verified structure surface.
- `ligands` is the first true payload expansion and therefore belongs after the governance layer is in place.
- `interactions` is the broadest step in this window and should come last because it has the highest chance of increasing size and validation complexity.

## Size-Risk Notes

The current preview is only `237008` bytes, far below the soft target. That means the first three iterations should remain lightweight if they stay summary-level and do not invent new payload classes.

The risk rises when the order reaches ligands and interactions:

- similarity and leakage families are expected to be low risk, but they still need a fresh measured bundle size after emission
- ligands are a moderate step because the family is currently empty and must be sourced truthfully
- interactions are the highest-risk family in this window because they are the most likely to expand payload breadth and operator complexity

## Guardrails

1. Add only one new family per iteration.
1. Re-measure bundle size after every family addition.
1. Keep the bundle in budget class `A`.
1. Preserve the verified protein, variant, and structure counts exactly.
1. Do not move into dictionary coding in this growth window.
1. Do not promote any family without a source-backed contract and live validation.

## What This Does Not Allow

This order does not mean the deferred families already exist. It does not authorize release readiness, and it does not permit completeness claims beyond the current verified preview surfaces.

## Bottom Line

If we keep the preview truthful and lightweight, the safest order is: protein similarity signatures, leakage groups, structure similarity signatures, ligands, then interactions. Anything beyond that should wait for a new size and packaging review.

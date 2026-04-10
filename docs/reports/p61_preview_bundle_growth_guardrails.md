# P61 Preview Bundle Growth Guardrails

This report-only note proposes truthful size and family-growth guardrails for expanding the verified lightweight preview bundle beyond the current protein, variant, and structure core.

## Current Baseline

The current bundle is a verified preview, not a release:

- [artifacts/status/lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [artifacts/status/live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json)

Current baseline facts:

- `manifest_status`: `preview_generated_verified_assets`
- `budget_class`: `A`
- compressed size: `237008` bytes
- soft target: `67108864` bytes
- warning threshold: `134217728` bytes
- hard cap: `268435456` bytes

The bundle already carries these verified families:

- proteins: 11
- protein variants: 1874
- structures: 4
- motif annotations: 98
- pathway annotations: 254
- provenance records: 1915

## Proposed Size Guardrails

1. Stay within budget class `A`.
1. Keep the bundle below the current soft target.
1. Treat `1 MiB` compressed as a review checkpoint for any future growth step.
1. Re-check budget compliance after every new family is added.

These guardrails keep the bundle lightweight while still allowing a small, truth-preserving expansion.

## Proposed Family-Growth Guardrails

1. Add at most one new family category per growth step.
1. Do not promote a family unless the manifest, contents doc, and live validation can all name it explicitly.
1. Do not expand zero-evidence families without a source-backed materialization contract.
1. Preserve the current protein, variant, and structure counts exactly while adding new families.
1. Keep heavy payloads out of the preview until the lightweight surfaces are stable.

The deferred growth families are:

- protein similarity signatures
- structure similarity signatures
- ligand similarity signatures
- interaction similarity signatures
- leakage groups
- ligands
- interactions
- dictionaries

## Recommended Growth Order

The safest next steps are:

1. protein similarity signatures
1. leakage groups
1. structure similarity signatures
1. ligands
1. interactions
1. dictionaries

That order keeps the first expansion focused on small governance surfaces before moving into heavier payload classes.

## What This Does Not Allow

This note does not claim any deferred family is already materialized. It does not promote the bundle to release-ready status, and it does not permit completeness claims beyond the current verified surfaces.

## Bottom Line

The preview can grow, but only in small, explicitly verified steps. The safest rule is simple: one new family at a time, measured against the current preview baseline, with no invented coverage and no hidden jump into heavy payloads.

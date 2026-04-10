# P74 Bundle Next Family Ranking

## Scope

This note ranks the next two bundle-family expansions after the current live preview bundle, using the current manifest, live bundle validation, preview growth guardrails, bundle size forecast, ligand stage-1 contracts, and the live packet deficit surface.

## Current Live Bundle Truth

The current live bundle in [artifacts/status/lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json) is still a `debug_bundle` with `compressed_sqlite` packaging, `content_scope = planning_governance_only`, compressed size `265356` bytes, and budget class `A`.

Live included families now are:

- `proteins`
- `protein_variants`
- `structures`
- `motif_annotations`
- `pathway_annotations`
- `provenance_records`
- `protein_similarity_signatures`
- `structure_similarity_signatures`
- `leakage_groups`
- `dictionaries`

Still absent:

- `ligands`
- `interactions`
- `ligand_similarity_signatures`
- `interaction_similarity_signatures`

The live validation artifact in [artifacts/status/live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json) confirms the current emitted slices are aligned, including `dictionary`.

## Ranking

### 1. Ligands

`ligands` is the next family to add.

Why it ranks first:

- It has the strongest live pressure in [artifacts/status/packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json): `5` unresolved ligand refs versus `1` unresolved PPI ref.
- The repo already has a safe staged path for the first ligand slice:
  - [artifacts/status/p69_ligand_signature_stage1_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p69_ligand_signature_stage1_contract.json)
  - [artifacts/status/p70_ligand_signature_stage1_execution_order.json](/D:/documents/ProteoSphereV2/artifacts/status/p70_ligand_signature_stage1_execution_order.json)
- The bundle size forecast in [artifacts/status/p60_bundle_size_expansion_forecast.json](/D:/documents/ProteoSphereV2/artifacts/status/p60_bundle_size_expansion_forecast.json) already ranks ligands as the first major next family.

Safe truth boundary:

- The first ligand slice should be identity-core only.
- It should not emit non-null `ligand_identity_group`.
- It should not emit non-null `binding_context_group`.
- It should not add `ligand_similarity_signatures` yet.
- The safe initial scope is still the four pilot proteins already named in `P69` and `P70`: `P00387`, `P09105`, `Q2TAC2`, and `Q9NZD4`.
- `Q9UCM0` should stay deferred in the first ligand wave.

### 2. Interactions

`interactions` is the second family to add, after ligands.

Why it ranks second:

- It is the other major absent family that would materially improve library usefulness for split governance, coverage analysis, and training-set balance.
- The size forecast already places it immediately after ligands.
- It is less mature than ligands in the current repo state. There is no equivalent interaction stage-1 execution contract already frozen at the same level of detail.
- It has lower immediate live pressure than ligands in the packet surface, with only `ppi:Q9UCM0` currently unresolved.

Safe truth boundary:

- The first interaction family should be summary-level only.
- It should stay provenance-heavy and not become a raw MITAB or STRING dump.
- It should not collapse `STRING`, `IntAct`, `BioGRID`, and related sources into a single equivalence claim without explicit source and confidence handling.
- `interaction_similarity_signatures` should remain absent until the base interaction family is real and validated.

## Families Not Ranked Ahead Of These Two

### Dictionaries

`dictionaries` is already live and validated in the current bundle, so it is not a next expansion family.

### Ligand Similarity Signatures

This family should not outrank `ligands` because it depends on a real ligand family being present first.

### Interaction Similarity Signatures

This family should not outrank `interactions` because it depends on a real interaction family being present first.

## Decision

The next two bundle-family expansions after the current live preview are:

1. `ligands`
2. `interactions`

That order is justified by:

- live packet pressure
- existing staged contracts
- bundle size forecast
- truth-boundary risk
- fit with the current compact preview bundle

## Bottom Line

The ranking is `ligands` first, `interactions` second. Ligands are the next safe expansion because the repo already has a defined compact stage-1 path and the strongest current gap pressure. Interactions are next after that, but only as a summary-level family with strict provenance and no overstated joins.

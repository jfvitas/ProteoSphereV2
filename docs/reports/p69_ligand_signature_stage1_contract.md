# P69 Ligand Signature Stage 1 Contract

## Objective

Define the first safe ligand-signature materialization slice.

Grounding:

- [p68_ligand_family_materialization_order.json](/D:/documents/ProteoSphereV2/artifacts/status/p68_ligand_family_materialization_order.json)
- [p67_ligand_signature_emission_prereqs.json](/D:/documents/ProteoSphereV2/artifacts/status/p67_ligand_signature_emission_prereqs.json)
- [entity_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_signature_preview.json)
- [lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)

## Contract Summary

Stage 1 is not the point where ligand grouping becomes non-null.

Stage 1 is the point where the repo first gains a real lightweight ligand family in the compact bundle, using the smallest safe pilot slice.

That means:

- bundle-level ligand family materialization happens now
- non-null `ligand_identity_group` does not happen yet
- non-null `binding_context_group` does not happen yet

## Current Repo State

The current live state is still fully pre-ligand-family:

- `entity_signature_preview.row_count = 1889`
- `lightweight_bundle_manifest.table_families.ligands.included = false`
- `lightweight_bundle_manifest.record_counts.ligands = 0`
- `ligand_identity_group = null` for every current entity-signature row
- `binding_context_group = null` for every current entity-signature row

The existing `entity_signature_preview` also shows that:

- all current protein rows have `family_readiness.protein_ligand = false`

## Stage 1 Slice Definition

Stage 1 is:

`ligand_identity_core_pilot`

In scope:

- `protein:P00387`
- `protein:P09105`
- `protein:Q2TAC2`
- `protein:Q9NZD4`

Deferred:

- `protein:Q9UCM0`

Reason for deferring `Q9UCM0`:

- it still has unresolved `structure` and `ppi` deficits
- it is not a clean ligand-only pilot row

## Bundle Contract

Stage 1 must change the compact bundle in exactly one important way:

- `ligands` becomes a real bundle family

Required bundle changes:

- `table_families.ligands.included = true`
- `table_families.ligands.record_count > 0`
- `record_counts.ligands > 0`

Minimum first-family fields:

- `ligand_row_id`
- `ligand_identity_namespace`
- `ligand_identity_source_id`
- `ligand_normalization_basis`
- `source_provenance_refs`
- `linked_protein_refs`

The bundle must stay compact:

- keep `compressed_sqlite`
- do not force partitioned packaging
- do not break current size-cap compliance

## Entity-Signature Contract

Stage 1 is intentionally conservative on the signature side.

Required:

- `entity_signature_preview.row_count` stays `1889`

Allowed row changes:

- only these four protein rows may change:
  - `protein:P00387`
  - `protein:P09105`
  - `protein:Q2TAC2`
  - `protein:Q9NZD4`

Allowed change type:

- `family_readiness.protein_ligand` may change from `false` to `true` for those four protein rows, but only after real bundle ligand rows exist

Everything else must remain unchanged:

- `exact_entity_group`
- `protein_spine_group`
- `sequence_equivalence_group`
- `variant_delta_group`
- `structure_chain_group`
- `structure_fold_group`

These fields must remain null for every row:

- `ligand_identity_group`
- `binding_context_group`

Not allowed to change in stage 1:

- any `protein_variant` row
- any `structure_unit` row
- `protein:Q9UCM0`

## Truth Boundary

What stage 1 means:

- the repo now has a real lightweight ligand family
- the four pilot proteins can be marked ligand-family-ready
- the repo is still before ligand grouping

What stage 1 does not mean:

- `ligand_identity_group` can be non-null
- `binding_context_group` can be non-null
- ligand overlap is materialized in leakage groups
- `Q9UCM0` is ready for ligand grouping

## Explicit Exclusions

Do not include these in stage 1:

- non-null `ligand_identity_group`
- non-null `binding_context_group`
- ligand similarity signatures
- interaction families
- leakage-group truth flip to `ligand_overlap_materialized = true`
- `Q9UCM0`
- changes to variant or structure-unit rows

## Acceptance Conditions

Stage 1 is complete only if:

1. the bundle has a real `ligands` family for the four pilot proteins
2. `entity_signature_preview.row_count` is still `1889`
3. every `ligand_identity_group` value is still null
4. every `binding_context_group` value is still null
5. only the four pilot protein rows are eligible for `family_readiness.protein_ligand = true`
6. the compact bundle model remains intact

## Handoff To The Next Stage

The next stage is not part of this contract.

It starts only when:

- the stage-1 ligand family is stable
- normalization is deterministic
- `P67` prerequisites for non-null ligand grouping are satisfied

## Bottom Line

`P69` defines stage 1 as bundle-first ligand family materialization, not ligand grouping. The safe first slice is a compact identity-core pilot for `P00387`, `P09105`, `Q2TAC2`, and `Q9NZD4`. `Q9UCM0`, binding context, ligand similarity, and all non-null ligand grouping remain deferred.

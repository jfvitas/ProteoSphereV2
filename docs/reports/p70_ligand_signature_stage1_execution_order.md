# P70 Ligand Signature Stage 1 Execution Order

## Objective

Define the ordered path for turning the stage1 ligand identity-core pilot into a live preview surface.

Grounding:

- [p69_ligand_signature_stage1_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p69_ligand_signature_stage1_contract.json)
- [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json)
- [entity_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_signature_preview.json)
- [lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)

## Current Live State

The current preview is still pre-ligand-family:

- `entity_signature_preview.row_count = 1889`
- `ligand_identity_group = null` everywhere
- `binding_context_group = null` everywhere
- `family_readiness.protein_ligand = false` for current protein rows

The current bundle is still pre-ligand-family:

- `table_families.ligands.included = false`
- `record_counts.ligands = 0`
- `packaging_layout = compressed_sqlite`
- `budget_class = A`

The stage1 pilot proteins remain:

- `protein:P00387`
- `protein:P09105`
- `protein:Q2TAC2`
- `protein:Q9NZD4`

Deferred:

- `protein:Q9UCM0`

## Execution Order

### 1. Freeze stage1 scope

Lock the stage1 pilot to exactly four protein rows:

- `protein:P00387`
- `protein:P09105`
- `protein:Q2TAC2`
- `protein:Q9NZD4`

Keep out of scope:

- `protein:Q9UCM0`
- all `protein_variant` rows
- all `structure_unit` rows

This is the boundary everything else depends on.

### 2. Freeze the identity-core ligand row shape

Before changing any surface, lock the minimum row shape for the first ligand family:

- `ligand_row_id`
- `ligand_identity_namespace`
- `ligand_identity_source_id`
- `ligand_normalization_basis`
- `source_provenance_refs`
- `linked_protein_refs`

Do not include:

- `binding_context_group`
- `binding_context_components`
- `ligand_similarity_signature`
- interaction overlap fields

### 3. Materialize the pilot ligand rows into the bundle

The bundle must move first.

Required bundle changes:

- `table_families.ligands.included = true`
- `table_families.ligands.record_count > 0`
- `record_counts.ligands > 0`

Must stay true:

- `packaging_layout = compressed_sqlite`
- cap compliance remains true
- ligand similarity signatures stay absent or zero-count
- interactions stay absent or zero-count

### 4. Validate pilot linkage against live packet gaps

The pilot bundle rows should correspond to:

- `ligand:P00387`
- `ligand:P09105`
- `ligand:Q2TAC2`
- `ligand:Q9NZD4`

Do not use as pilot evidence:

- `ligand:Q9UCM0`
- `structure:Q9UCM0`
- `ppi:Q9UCM0`

This keeps the first family tied to the clean ligand-only gaps.

### 5. Reflect readiness into `entity_signature_preview`

Only after the bundle is truthful should the preview change.

Allowed preview change:

- `family_readiness.protein_ligand` may change from `false` to `true` for:
  - `protein:P00387`
  - `protein:P09105`
  - `protein:Q2TAC2`
  - `protein:Q9NZD4`

Everything else must remain unchanged:

- `row_count = 1889`
- all existing grouping fields
- all `protein_variant` rows
- all `structure_unit` rows
- `protein:Q9UCM0`

Also still required:

- `ligand_identity_group = null`
- `binding_context_group = null`

### 6. Run a stage1 acceptance audit

Before publishing the preview, verify:

- row count is still `1889`
- only the four pilot protein rows gained ligand-family readiness
- `Q9UCM0` did not change
- no variant or structure rows changed
- all ligand grouping fields remain null

This is the last hold point before the preview becomes live truth.

### 7. Publish the live stage1 preview

At publish time, the repo may now truthfully say:

- a lightweight ligand family exists in the bundle
- four pilot proteins are ligand-family-ready
- the repo is still pre-ligand-grouping

It may not say:

- `ligand_identity_group` is populated
- `binding_context_group` is populated
- ligand overlap is materialized in leakage groups
- `Q9UCM0` is ready

### 8. Hold the stage boundary

Do not let stage1 bleed into the next stage.

Hard stops:

- no non-null `ligand_identity_group`
- no non-null `binding_context_group`
- no ligand similarity signatures
- no leakage-group truth flip to `ligand_overlap_materialized = true`

Those belong to the next stage only.

## Smallest Useful Live Preview

Stage1 is live and useful when:

- the bundle now includes real ligand rows
- `entity_signature_preview` still has `1889` rows
- exactly these four rows show ligand-family readiness:
  - `protein:P00387`
  - `protein:P09105`
  - `protein:Q2TAC2`
  - `protein:Q9NZD4`
- `protein:Q9UCM0` is still deferred
- all ligand grouping fields are still null

## Unsafe Reordering

Do not do these out of order:

- change the preview before the bundle has ligand rows
- include `Q9UCM0` in the first pilot wave
- populate `ligand_identity_group` before the stage1 preview is published
- add ligand similarity signatures before identity-core ligand rows exist
- treat packet-gap refs as if they were the ligand family

## Bottom Line

The correct order is:

1. freeze scope
2. freeze row shape
3. materialize bundle ligand rows
4. validate pilot linkage
5. reflect readiness into the preview
6. audit
7. publish
8. hold the non-null grouping boundary

That is the smallest safe path from the current repo state to a real stage1 live preview.

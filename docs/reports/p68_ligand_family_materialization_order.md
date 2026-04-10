# P68 Ligand Family Materialization Order

## Objective

Define the safest order to materialize the first lightweight ligand family, grounded in:

- [p67_ligand_signature_emission_prereqs.json](/D:/documents/ProteoSphereV2/artifacts/status/p67_ligand_signature_emission_prereqs.json)
- [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json)
- [lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)

## Current Bundle Truth

The current compact bundle is still explicitly non-ligand:

- `bundle_kind = debug_bundle`
- `packaging_layout = compressed_sqlite`
- `content_scope = planning_governance_only`
- `ligands.included = false`
- `ligands.record_count = 0`
- `ligand_similarity_signatures.record_count = 0`
- `leakage_groups.record_count = 11`

That means the safest first ligand family has to be small, explicit, and compatible with the current compact bundle posture.

## Current Ligand Pressure

The active ligand-only packet gaps are:

- `P00387`
- `P09105`
- `Q2TAC2`
- `Q9NZD4`

The mixed-modality outlier is:

- `Q9UCM0`

`Q9UCM0` is not just missing ligand coverage. It also still has:

- `structure:Q9UCM0`
- `ppi:Q9UCM0`

That makes it the wrong first row for a safe ligand-family pilot.

## Safest Order

### 1. Materialize an identity-core ligand family first

The first lightweight ligand family should only cover identity-core fields:

- stable ligand row id
- ligand identity namespace
- ligand source identifier
- normalization basis
- provenance refs
- linked protein refs

It should not include:

- `binding_context_group`
- ligand similarity signatures
- interaction-family rows
- context-derived leakage logic

Reason: this is the minimum step that satisfies the `P67` requirement for a repo-visible materialized ligand family and deterministic normalization.

### 2. Pilot only on ligand-only gap proteins

The safest first accession set is:

- `P00387`
- `P09105`
- `Q2TAC2`
- `Q9NZD4`

Defer:

- `Q9UCM0`

Reason: the first pilot should not depend on unresolved structure or PPI interpretation.

### 3. Emit ligand rows before any non-null grouping

The repo should first become truthful about having a ligand family at all.

That means:

- bundle `ligands.included = true`
- bundle `ligands.record_count > 0`
- row-level normalized ligand evidence exists for the pilot rows

At this point, `binding_context_group` must still remain null.

### 4. Unlock `ligand_identity_group` only for normalized pilot rows

Once the identity-core family exists and normalization is deterministic, non-null `ligand_identity_group` can be allowed for those normalized rows.

Still blocked at this stage:

- `binding_context_group`
- any context-based grouping
- any row still depending on unresolved non-ligand interpretation

That means `Q9UCM0` is still not a good first unlock candidate.

### 5. Update leakage-group truth after ligand overlap is real

Only after real ligand rows and ligand identity grouping exist should the leakage-group surface move from:

- `ligand_overlap_materialized = false`

to:

- `ligand_overlap_materialized = true`

The key point is that leakage overlap must be driven by materialized ligand rows, not by packet-gap refs.

### 6. Add binding context last

`binding_context_group` should be the final step, not part of the first family.

It requires:

- stable ligand identity rows
- stable row-level ligand grouping
- a deterministic context constructor
- any required structure context already materialized

That makes it strictly later than identity-core family materialization.

## Recommended First Slice

The safest first slice is:

`ligand_identity_core_pilot`

Include first:

- `P00387`
- `P09105`
- `Q2TAC2`
- `Q9NZD4`

Include later:

- `Q9UCM0`

Minimum first-family fields:

- `ligand_row_id`
- `ligand_identity_namespace`
- `ligand_identity_source_id`
- `ligand_normalization_basis`
- `source_provenance_refs`
- `linked_protein_refs`

Explicitly defer:

- `binding_context_group`
- `binding_context_components`
- `ligand_similarity_signature`
- `interaction_overlap_signature`

## Unsafe First Moves

Avoid these:

- starting with `Q9UCM0`
- starting with binding-context materialization
- starting with ligand similarity signatures
- treating packet-gap refs as if they were the ligand family
- flipping `ligands.included` to true without real ligand rows in the bundle

## Bottom Line

The safest first lightweight ligand family is a small identity-core pilot. Materialize normalized ligand rows first for `P00387`, `P09105`, `Q2TAC2`, and `Q9NZD4`; keep `Q9UCM0` deferred; keep binding context and ligand similarity out of the first slice; then unlock non-null `ligand_identity_group` only after that family is real.

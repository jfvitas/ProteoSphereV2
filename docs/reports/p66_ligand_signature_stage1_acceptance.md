# P66 Ligand Signature Stage 1 Acceptance

## Objective

Define the exact conditions that must be true before stage-1 ligand placeholder fields can be safely emitted into the live entity-signature and split-candidate previews.

Grounding:

- [p64_ligand_placeholder_implementation_order.json](/D:/documents/ProteoSphereV2/artifacts/status/p64_ligand_placeholder_implementation_order.json)
- [p63_ligand_signature_placeholder_schema.json](/D:/documents/ProteoSphereV2/artifacts/status/p63_ligand_signature_placeholder_schema.json)
- [entity_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_signature_preview.json)
- [entity_split_candidate_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_split_candidate_preview.json)
- [packet_deficit_dashboard.json](/D:/documents/ProteoSphereV2/artifacts/status/packet_deficit_dashboard.json)

## Current Live Baseline

- `entity_signature_preview` currently has `1889` rows.
- `entity_split_candidate_preview` currently has `1889` rows.
- Both surfaces already contain reserved ligand grouping fields:
  - `ligand_identity_group = null`
  - `binding_context_group = null`
- The live ligand pressure is limited to five packet-gap refs:
  - `ligand:P00387`
  - `ligand:P09105`
  - `ligand:Q2TAC2`
  - `ligand:Q9NZD4`
  - `ligand:Q9UCM0`

The same dashboard also contains non-ligand refs for `Q9UCM0`:

- `structure:Q9UCM0`
- `ppi:Q9UCM0`

Those are explicitly out of scope for stage-1 ligand emission.

## What Stage 1 Is Allowed To Emit

Only additive support-only fields:

For entity signatures:

- `ligand_placeholder_status`
- `ligand_support_refs`
- `ligand_truth_note`

For split candidate metadata:

- `metadata.ligand_placeholder_status`
- `metadata.ligand_support_refs`
- `metadata.ligand_truth_note`

Nothing else is allowed to change.

## Required Acceptance Conditions

### 1. Field set is frozen

Stage 1 is safe only if it uses the support-only field set above and does not introduce any additional ligand-aware keys.

Unsafe:

- adding new ligand grouping keys
- repurposing `ligand_identity_group`
- repurposing `binding_context_group`

### 2. Row counts are unchanged

Both live surfaces must preserve the current row counts exactly:

- `entity_signature_preview = 1889`
- `entity_split_candidate_preview = 1889`

Any added or removed rows fail acceptance.

### 3. Non-ligand grouping stays unchanged

All current grouping and split-assignment fields must remain byte-for-byte stable in meaning:

- `exact_entity_group`
- `protein_spine_group`
- `sequence_equivalence_group`
- `variant_delta_group`
- `structure_chain_group`
- `structure_fold_group`
- `leakage_key`
- `linked_group_id`
- `bucket`
- `validation_class`
- `lane_depth`

If any of those change, stage 1 is not safe.

### 4. Reserved ligand grouping fields stay null

These fields must remain null for every row:

- `ligand_identity_group`
- `binding_context_group`
- `metadata.ligand_identity_group`
- `metadata.binding_context_group`

If any row gets a non-null value in those fields, stage 1 has crossed out of the safe placeholder phase.

### 5. Support refs are allowlisted

Non-empty `ligand_support_refs` are safe only if they point to the current live ligand-gap refs:

- `ligand:P00387`
- `ligand:P09105`
- `ligand:Q2TAC2`
- `ligand:Q9NZD4`
- `ligand:Q9UCM0`

Unsafe:

- `structure:Q9UCM0`
- `ppi:Q9UCM0`
- `CHEMBL:*`
- `BINDINGDB:*`
- `CHEBI:*`
- any normalized ligand identifier

### 6. Support rows are restricted to five proteins

Only the five current ligand-gap protein rows may emit:

- `ligand_placeholder_status = candidate_support_only`

Every other row must stay:

- `ligand_placeholder_status = not_materialized`

Unsafe:

- variant rows carrying ligand support
- structure-unit rows carrying ligand support
- protein rows outside the five live ligand gaps carrying ligand support

### 7. Truth notes must state the boundary

`ligand_truth_note` is safe only if it explicitly communicates:

- support-only behavior
- no ligand join
- no materialized ligand entity

Unsafe:

- implying normalized ligand identity
- implying binding-context materialization
- implying ligand-aware split behavior

### 8. No new families or buckets appear

Stage 1 is not safe if it introduces:

- `entity_family = protein_ligand`
- `bucket = ligand_entity`
- `validation_class = ligand_entity`
- `validation_class = ligand_context`

## Strict No-Join Boundaries

Stage 1 must not do any of the following:

- join canonical ligands into preview rows
- join ChEMBL, BindingDB, ChEBI, PDB CCD, or BioLiP identifiers into stage-1 fields
- infer ligand equivalence from shared protein accession
- derive binding-context groups
- create ligand-based split exclusions

## Safe-to-Emit Definition

Stage-1 ligand fields are safe to emit only when:

- they are additive support metadata only
- they are limited to the five live ligand-gap proteins
- they do not alter row counts
- they do not alter current grouping or split behavior
- they keep all ligand grouping fields null
- they do not perform any ligand join or normalization

## Bottom Line

`P66` is a pre-emission gate, not an implementation note. The stage-1 ligand fields are acceptable only if they remain a narrow, support-only annotation layer over the existing previews with strict allowlists and strict no-join boundaries.

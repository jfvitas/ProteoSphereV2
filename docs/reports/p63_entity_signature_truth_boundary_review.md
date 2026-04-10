# P63 Entity Signature Truth Boundary Review

This is a report-only review of [entity_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/entity_signature_preview.json). It summarizes what the preview supports now, what it intentionally defers, and the next truthful expansion.

## What It Supports Now

The preview is already a compact entity-level signature surface for the materialized lightweight families that exist today:

- `11` proteins
- `1874` protein variants
- `4` structure units
- `1889` total entity rows

It gives each row the same basic identity spine:

- `exact_entity_group`
- `protein_spine_group`
- `sequence_equivalence_group`
- `family_readiness`

It also adds family-specific axes where they are truth-bearing:

- `variant_delta_group` for protein variants
- `structure_chain_group` for structure units
- `structure_fold_group` for structure units

That makes the preview useful for leakage-safe split governance, because each entity row already carries an exact boundary plus the right coarse grouping axes.

## What It Intentionally Defers

The preview keeps the ligand surface explicitly reserved:

- `ligand_identity_group` stays null
- `binding_context_group` stays null
- no `protein_ligand` entity rows are emitted yet

It also keeps direct structure-backed variant joining out of scope:

- `direct_structure_backed_variant_join_materialized` is still false
- structure rows do not claim a variant anchor unless an explicit structure-side `variant_ref` exists

In short, the preview is entity-level truth, not ligand truth and not a structure-variant bridge.

## Grounded Examples

- `protein:P04637` shows the protein spine and sequence-equivalence boundary, but it does not carry structure or ligand axes yet.
- `protein_variant:protein:P31749:E17K` shows a concrete mutation signature through `variant_delta_group = E17K`, while still deferring structure and ligand axes.
- `structure_unit:protein:P68871:4HHB:B` shows the exact structure chain and fold axes, while keeping ligand axes null.

## Next Truthful Expansion

The next truthful expansion should add a ligand-aware entity layer once `protein_ligand` rows are real. That means:

- keep the current protein, protein-variant, and structure-unit axes stable
- add entity rows for `protein_ligand`
- populate `ligand_identity_group` only from explicit ligand identity
- populate `binding_context_group` only from explicit ligand-plus-protein context

The expansion should stay separate from direct structure-backed variant joins. Those still need an explicit structure-side anchor before they can be claimed truthfully.

## Boundary

This review is report-only. It does not edit code, does not rewrite protected latest surfaces, and does not claim ligand or direct structure-backed join support that the preview does not already materialize.

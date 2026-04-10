# Entity Split Recipe Preview

- Recipe ID: `protein_spine_first_split_recipe_v1`
- Input artifact: `entity_split_candidate_preview`
- Atomic unit: `entity_signature_row`
- Primary hard group: `protein_spine_group`

## Grounding

- Candidate rows: `1889`
- Linked groups: `11`
- Simulation assignments: `1889`
- Simulation rejected rows: `0`

## Allowed Families

- `protein`
- `protein_variant`
- `structure_unit`

## Reserved Null Axes

- `ligand_identity_group`
- `binding_context_group`

## Truth Boundary

- This recipe preview is a compact executable-facing view of the current first split recipe contract. It is grounded in the live split simulation, but it does not commit a release split or materialize ligand-aware axes.

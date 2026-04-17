# Policy Resolution Guide

Map the paper’s claimed split to a ProteoSphere canonical policy:

- `strict_unseen_protein` or homology-guarded wording -> `uniref_grouped`
- external source/component holdout wording -> `paper_faithful_external`
- explicit ligand-component grouping -> `protein_ligand_component_grouped`
- plain held-out test without stronger grouping detail -> `accession_grouped`
- if the paper wording is too vague -> `unresolved_policy`

Always report both:
- the claimed split policy
- the resolved canonical split policy

# P29 Consensus Precedence Matrix

Date: 2026-03-30  
Artifact: `p29_consensus_precedence_matrix`

## Purpose

This matrix is the execution-facing precedence table for the first summary-library slice. It turns the trust policy, consensus rules, provenance payload contract, and scope audit into exact winner-selection behavior.

The rule is simple: choose the strongest claim for the claim class that is actually in scope, and keep dissent visible whenever collapsing would change the meaning.

## Scope Audit

The current local registry reports `29` present sources, `2` partial sources, and `8` missing sources.

That means:

- present sources can win directly when they are native to the claim class
- partial sources can win only within the slice they actually cover
- missing staged local corpora cannot win by absence alone
- supporting or context sources may annotate, but they may not override direct evidence

For this first slice, structure, ligand, pathway, and derived-training layers are materially usable, while interaction-network and motif layers must stay conservative unless backed by explicit cached summary shards or other direct provenance.

## Global Rules

1. Normalize identifiers, units, and ontology terms before selecting a winner.
1. Prefer source-native authority for the claim class when it is in scope.
1. Prefer direct curated or experimentally grounded evidence over context-only evidence.
1. Keep experimental and predicted claims separate unless the row explicitly allows a multi-value representation.
1. Retain multi-value sets when collapsing would erase a biologically meaningful distinction.
1. Attach provenance that can reconstruct the winner, alternates, and tie break.

## Precedence Matrix

### Proteins

`UniProt` is the canonical winner for protein identity and sequence.

Choose a single winner when all values normalize to one accession or alias chain, and use the reviewed Swiss-Prot accession as canonical when the only difference is reviewed versus unreviewed status.

Keep multiple values when sequence versions differ, isoforms differ meaningfully, secondary accessions map to different canonical accessions, or local extracted projections conflict with upstream protein identity.

Tie handling:

- do not collapse distinct UniProt accessions
- if the difference is only aliasing, keep the alias chain in provenance and choose the canonical accession
- if hashes differ, preserve both or mark unresolved

Dissent capture:

- `protein_identity_status`
- `alternate_accessions`
- `alternate_isoforms`
- `identity_conflict_notes`

### Structures

`RCSB/PDBe` wins for experimentally grounded structure claims.

`AlphaFold DB` is the predicted companion lane and must stay separate.

Choose a single winner when the experimental structure identity is stable, chain/entity mapping is unambiguous, and quality or resolution differences do not change the structure record identity.

Keep multiple values when experimental and predicted structures both exist for the same protein, multiple assemblies or biological states matter, or the mapping is ambiguous.

Tie handling:

- never merge experimental and predicted truth into one field
- retain both when the claim scope differs
- mark ambiguous mapping rather than guessing chain or entity

Dissent capture:

- `structure_claim_status`
- `experimental_structure_refs`
- `predicted_structure_refs`
- `mapping_conflict_notes`

### Ligands

`ChEBI` is the chemical identity winner when available.

`BindingDB` and `ChEMBL` lead assay-backed ligand claims.

Choose a chemical winner only after standardization proves the candidate values describe the same chemical entity. Choose a single assay winner only after unit normalization, endpoint matching, and target-context compatibility checks.

Keep multiple values when tautomer, salt, or stereochemistry choices materially change the claim, assay-backed values disagree after normalization, or structure-linked and assay-linked ligand claims are both valid but not identical.

Tie handling:

- treat chemical identity and assay measurement as separate subclaims
- collapse unit-equivalent duplicates only
- keep a range or alternate-value set instead of averaging incompatible measurements

Dissent capture:

- `ligand_claim_status`
- `alternate_ligand_ids`
- `alternate_standard_forms`
- `assay_value_alternates`
- `ligand_conflict_notes`

### PPIs

`IntAct` is the curated interaction winner, with `BioGRID` as the next curated authority and `STRING` restricted to breadth/context support.

Choose a single winner only when a direct curated interaction source supports the same normalized accession pair and interaction type.

Keep multiple values when IntAct and BioGRID support different but compatible interaction classes, native complex and binary projection both exist, or only breadth context is available.

Tie handling:

- do not promote breadth context to curated truth
- preserve self rows and duplicates when they explain lineage or density
- if native-complex and binary projections both exist, retain both and mark the projection lineage

Dissent capture:

- `interaction_claim_status`
- `alternate_interaction_types`
- `evidence_class_alternates`
- `projection_lineage`
- `interaction_conflict_notes`

### Motifs

`InterPro` is the motif and domain winner.

Choose the most specific span-resolved InterPro call when the accession and residue span are consistent. Use a broader umbrella term only when it is a strict parent of the specific term and no finer call is available.

Keep multiple values when family, domain, site, and short-motif claims overlap but are not equivalent, namespace-specific labels cannot be safely collapsed, or a local projection compresses a more specific motif into a broader one.

Tie handling:

- preserve the most specific residue-resolved term when available
- retain parent terms only as supporting context
- do not flatten different motif namespaces into one label

Dissent capture:

- `motif_claim_status`
- `alternate_motif_accessions`
- `alternate_spans`
- `motif_namespace_conflict_notes`

### Pathways

`Reactome` is the pathway winner.

Choose Reactome as the winner when stable pathway id and species context agree. Keep the reaction-level specialization if it is more specific than the parent pathway and the claim scope depends on that specificity.

Keep multiple values when species context differs, one value is a parent pathway and another is a reaction-level specialization, or a local projection compresses a richer lineage.

Tie handling:

- do not collapse across species
- keep parent-child lineage explicit
- preserve reaction-level specialization when it changes claim scope

Dissent capture:

- `pathway_claim_status`
- `alternate_pathway_ids`
- `species_context_alternates`
- `pathway_conflict_notes`

### Assays

`BindingDB` and `ChEMBL` lead assay claims.

Choose a single numeric winner only when unit normalization and endpoint matching prove the claims are equivalent, and require construct and target context compatibility before collapsing assay values.

Keep multiple values when endpoints differ meaningfully, construct or species changes interpretation, the safest representation is a range or set, or BindingDB and ChEMBL disagree after normalization.

Tie handling:

- collapse only unit-equivalent duplicates
- do not average incompatible measurements
- prefer the narrower, more precise endpoint only if it is a safe specialization

Dissent capture:

- `assay_claim_status`
- `alternate_numeric_values`
- `alternate_units`
- `alternate_endpoints`
- `assay_conflict_notes`

## Dissent Modes

Use these output modes consistently:

- `resolved`
- `alias_chain`
- `hierarchy_parent`
- `winner_plus_alternates`
- `multi_value_set`
- `unresolved_conflict`

Use `winner_plus_alternates` when one value is canonical but alternates matter for auditability. Use `multi_value_set` when collapsing would erase a meaningful distinction. Use `unresolved_conflict` when the matrix cannot pick a winner without inventing evidence.

## Provenance And Training Safety

Every fused record should carry:

- the winner value
- any retained alternates
- source ranks
- evidence strength
- tie-break reason
- conflict markers
- lineage pointers

A record is training-safe only if the winner is explicit, alternates remain attached when they matter, and conflict markers are visible. It is not safe if experimental and predicted structure are merged, curated PPI and breadth context are collapsed, assay measurements are averaged across incompatible endpoints, or local extracted assets replace upstream evidence.

## Bottom Line

The matrix is intentionally conservative. It gives the builder a concrete, deterministic answer for each claim class while still preserving the disagreements that matter. That is the right first-slice behavior for a summary library that needs to be reproducible, auditable, and safe for training use.

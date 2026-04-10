# P29 Consensus Materialization Rules

Date: 2026-03-30  
Artifact: `p29_consensus_materialization_rules`

## Purpose

This is the execution layer for the summary library. It converts the trust policy into materialization behavior: how to pick a single winner, when to preserve multiple values, how to record dissent, and how to attach provenance so downstream training packets can use the fused value safely.

It is meant to work with the summary-library plan and the source trust policy, not replace them.

## Contract

The summary library stays in `feature_cache` form and keeps the existing top-level record kinds:

- `protein`
- `protein_protein`
- `protein_ligand`

The following attachment kinds should be fused onto those records rather than promoted into separate top-level cards:

- `protein_structure_reference`
- `motif_reference`
- `pathway_reference`
- `assay_claim`

That keeps the library compact, accession-first, and safe to rebuild.

## Global Rule Shape

The materializer should always pass through the same decision ladder:

1. Normalize identifiers, units, and ontology terms.
1. Ask whether the values are actually equivalent.
1. If one value is a safe specialization of another, keep the more specific one.
1. If one source is native authority for the claim class, prefer it.
1. If there is still no honest single winner, preserve the full dissent set.
1. Record why the choice was made, or why no choice was made.

The allowed output modes are:

- `single_winner`
- `winner_plus_alternates`
- `multi_value_set`
- `unresolved_conflict`

## Rule Shapes By Record Kind

### Proteins

Use `UniProt` as the canonical accession spine.

Choose a single winner when:

- all candidate values resolve to the same accession or explicit alias chain
- sequence version and normalized hash agree
- isoform and species context do not conflict

Keep multiple values when:

- sequence versions differ
- isoforms differ in a biologically meaningful way
- secondary accessions could map to more than one canonical record
- local extracted assets disagree with upstream protein identity

Record dissent with:

- alternate accessions
- alternate isoforms
- identity conflict notes
- explicit `protein_identity_status`

Attach provenance with source name, source record id, release or snapshot id, retrieval timestamp, raw value, normalized value, transformation steps, and authority tier. The protein card is safe for training only if the canonical accession is explicit and any alternates stay attached rather than hidden.

### Structures

Use `RCSB/PDBe` as the experimental authority and keep `AlphaFold DB` as predicted support.

Choose a single winner when:

- the experimental structure claim is stable
- chain/entity mapping is unambiguous
- different quality scores do not change the structure identity

Keep multiple values when:

- experimental and predicted structures both exist for the same protein
- multiple biological assemblies or states matter
- mapping is ambiguous

Record dissent with:

- experimental structure refs
- predicted structure refs
- mapping conflict notes
- `structure_claim_status`

Provenance must include structure id, chain id, entity id, assembly id, residue span, and the source lineage. Never merge experimental and predicted structure into one truth cell.

### Ligands

Use `ChEBI` as the canonical chemical identity authority, with `BindingDB` and `ChEMBL` providing assay-backed support.

Choose a single winner when:

- the ligand standardizes to one chemical entity
- salt, tautomer, and stereochemistry choices do not change the intended claim
- the protein target joins cleanly

Keep multiple values when:

- the standard form is genuinely ambiguous
- assay-backed values disagree after normalization
- structure-linked and assay-linked ligand claims are both valid but not identical

Record dissent with:

- alternate ligand ids
- alternate standardized forms
- assay value alternates
- `ligand_claim_status`

Provenance must keep protein accession, ligand id, assay context, units, and normalization steps together. The training packet should be able to tell whether the value is chemical identity, assay value, or both.

### Interactions

Use `IntAct` as the first-choice curated interaction source and `BioGRID` as the other curated interaction authority. Keep `STRING` as breadth/context only.

Choose a single winner when:

- the pair key is normalized
- the interaction type agrees
- the evidence class is direct and curated
- native-complex versus binary projection is clear

Keep multiple values when:

- IntAct and BioGRID are both credible but speak to different interaction scopes
- native-complex and binary projections both matter
- STRING only adds context and should not replace curated evidence

Record dissent with:

- alternate interaction types
- evidence class alternates
- projection lineage
- `interaction_claim_status`

This is especially important for weak or mixed interaction summaries. The library should preserve self rows, duplicates, and breadth-only evidence when they are useful for auditability, but it should not pretend they are the same as direct curated evidence.

### Motifs

Use `InterPro` as the dominant motif and domain authority.

Choose a single winner when:

- the ontology accession and residue span match
- a broader parent term is a safe umbrella over a more specific one
- the motif claim is residue-resolved and stable

Keep multiple values when:

- family, domain, site, and short motif claims overlap but do not mean the same thing
- a source-specific motif label would lose meaning if collapsed
- local extracted assets compress a more specific motif into a broader one

Record dissent with:

- alternate motif accessions
- alternate spans
- motif namespace conflict notes
- `motif_claim_status`

Motif references should stay attached to the protein card and not become pseudo-identity claims.

### Pathways

Use `Reactome` as the pathway and reaction authority.

Choose a single winner when:

- the stable pathway id and species context agree
- the reaction role is consistent
- ancestry is stable

Keep multiple values when:

- species context differs
- one value is a parent pathway and the other is a reaction-level specialization
- local extracted assets compress a richer lineage

Record dissent with:

- alternate pathway ids
- species context alternates
- pathway conflict notes
- `pathway_claim_status`

Pathway references should enrich protein cards, not replace protein identity or structure evidence.

### Assay Claims

Use `BindingDB` and `ChEMBL` as the assay-measurement authorities.

Choose a single winner when:

- units normalize cleanly
- endpoint and assay context match
- construct and target identity are compatible
- the measurement is genuinely the same experimental claim

Keep multiple values when:

- endpoints differ in a meaningful way
- construct or species context changes the interpretation
- the best answer is a range or a set of measurements

Record dissent with:

- alternate numeric values
- alternate units
- alternate endpoints
- assay conflict notes
- `assay_claim_status`

Assay claims are the place where silent averaging is most dangerous. If the values disagree, prefer ranges or alternate-value arrays instead of a collapsed mean unless the normalization path proves true equivalence.

## Dissent Encoding

Every fused record should carry:

- `decision_mode`
- `winner_value`
- `alternate_values`
- `conflict_status`
- `tie_break_reason`
- `retained_source_refs`
- `retained_raw_values`
- `retained_normalized_values`

Recommended status vocabulary:

- `resolved`
- `alias_chain`
- `hierarchy_parent`
- `winner_plus_alternates`
- `multi_value_set`
- `unresolved`

Use `resolved` only when the record truly has a single winner. Use `winner_plus_alternates` when one value is canonical but alternatives still matter. Use `multi_value_set` when a single value would be misleading. Use `unresolved` when no honest choice exists.

## Provenance Attachment

The minimum provenance set for every fused record is:

- source name
- source record id
- release or snapshot id
- retrieval timestamp
- raw value
- normalized value
- transformation steps

Every fused record also needs:

- winner source name
- winner source record id
- contributing source names
- contributing record ids
- decision mode
- tie-break reason
- conflict status

Every alternate needs:

- source name
- source record id
- raw value
- normalized value
- reason retained

Local extracted assets are allowed, but only as derived summaries. They must always point back to upstream source records, and they must never overwrite native evidence without explicit conflict encoding.

## Training-Packet Safety

The fused output is safe for downstream training packets only if:

- the winner or multi-value representation is explicit
- retained alternates are still linked to provenance
- conflict state is visible
- source-specific claim scope is preserved

The fused output is not safe if:

- a conflict was collapsed away
- experimental and predicted structure were merged into one claim
- assay values were averaged across incompatible contexts
- a local extracted asset replaced upstream evidence

## Bottom Line

The consensus materializer should be conservative by default and explicit by design. A single winner is great when the evidence really supports it. When it does not, the correct move is not to guess harder. It is to keep the dissent, label it well, and let the downstream packet builder use the fused record without losing the evidence trail.

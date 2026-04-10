# P31 Join And Consensus Story

This is the slide-ready story for how we connect sources and how we resolve disagreement without inventing consensus.

## Core Message

We join by stable source-native identifiers first, normalize to the canonical spine for each class, preserve lineage, and stop whenever the evidence would need to be guessed.

## Slide Outline

1. **Join by the right spine first**  
   UniProt is the protein accession spine. Aliases, gene names, and secondary accessions help us find the record, but they do not become primary truth.

2. **Structure crosswalks stay separate**  
   RCSB/PDBe owns experimental structure truth. The join is `pdb_id + entity_id + assembly_id + chain ID + residue span + UniProt mapping`. AlphaFold stays in a separate predicted lane.

3. **Ligand identity is not assay value**  
   ChEBI anchors chemical identity. BindingDB and ChEMBL carry assay-backed ligand evidence and measurements. Identity and measurement stay separate.

4. **Curated PPI wins over context**  
   IntAct and BioGRID are the curated interaction lanes. STRING is supporting context only. Native-complex lineage is preserved instead of being flattened away.

5. **Motif spans and pathway context are accessioned**  
   Motifs join by UniProt accession, motif accession, and residue span. Reactome owns pathway and reaction membership, with species context kept explicit.

6. **We resolve disagreements by class, not by force**  
   We normalize identifiers, units, and ontology terms first. Then we apply the trust policy and precedence matrix to choose a winner only when the values are truly equivalent.

7. **We refuse to force consensus**  
   If a join lacks a source-native key, spans, validation data, or release-stamped provenance, the system keeps the ambiguity visible instead of collapsing it.

## Resolution Rules

- Prefer source-native authority for the claim class.
- Prefer direct curated or experimental evidence over context-only evidence.
- Prefer the more specific value when one claim strictly entails another.
- Keep experimental and predicted structure separate.
- Keep ligand identity separate from assay measurement.
- Keep curated PPI separate from breadth-only context.
- Keep motif span joins accessioned and release-stamped.

## Refuse-Consensus Conditions

- Only a display name, gene name, or alias is available.
- Taxon, species, assembly, isoform, construct, or reaction context is still conflicting.
- Experimental and predicted structure would be merged into one claim.
- Ligand identity cannot be standardized to a stable chemical identifier.
- Curated PPI lacks a native interaction ID or accession-resolved participants.
- Motif span, motif accession, or release-stamped provenance is missing.

## Provenance And Dissent

Every fused value must retain source name, source record ID, release or snapshot ID, retrieval timestamp, raw value, normalized value, transformation steps, authority tier, claim class, and confidence or support status. Consensus values also retain contributing sources, contributing record IDs, a normalization pipeline, tie-break reason, retained alternates, and conflict status.

The allowed dissent states are `resolved`, `alias_chain`, `hierarchy_parent`, `winner_plus_alternates`, `multi_value_set`, and `unresolved_conflict`. That is the mechanism that keeps the deck honest: we can show a winner, but only if the data actually supports one.

## Source Grounding

This story is grounded in:

- [p29_identifier_join_contract.json](../../artifacts/status/p29_identifier_join_contract.json)
- [p29_source_trust_policy.json](../../artifacts/status/p29_source_trust_policy.json)
- [p29_consensus_precedence_matrix.json](../../artifacts/status/p29_consensus_precedence_matrix.json)
- [p29_provenance_payload_contract.json](../../artifacts/status/p29_provenance_payload_contract.json)


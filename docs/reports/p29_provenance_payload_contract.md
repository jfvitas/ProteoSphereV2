# P29 Provenance Payload Contract

Date: 2026-03-30  
Artifact: `p29_provenance_payload_contract`

## Purpose

This contract turns the trust policy and consensus rules into one concrete payload shape: `provenance_payload`.

The goal is simple. A fused summary record should carry enough provenance to explain the winner, preserve alternates, expose dissent, rank sources, show evidence strength, and tell the packet builder whether the record is safe for training use.

## Payload Envelope

Every fused summary record should embed a `provenance_payload` object with these top-level fields:

- `record_kind`
- `summary_id`
- `claim_class`
- `decision_mode`
- `conflict_status`
- `winner_value`
- `alternate_values`
- `dissent_markers`
- `source_ranks`
- `evidence_strength`
- `provenance_bundle`
- `training_safe_provenance`

That envelope is the shared contract across proteins, structures, ligands, interactions, motifs, pathways, and assay claims.

## Core Field Shapes

`winner_value` is the canonical fused value object. It should always include:

- `value`
- `normalized_value`
- `raw_value`
- `source_name`
- `source_record_id`
- `source_rank`
- `authority_tier`
- `evidence_strength`
- `selection_reason`
- `claim_scope`
- `release_or_snapshot_id`
- `retrieval_timestamp`

`alternate_values` is an ordered array of retained competitors. Each alternate should include the same value and provenance fields plus:

- `reason_retained`
- `dissent_tag`

`dissent_markers` should make the conflict visible, not implicit. Required fields are:

- `conflict_status`
- `conflict_type`
- `has_competing_values`
- `retained_alternate_count`
- `manual_review_required`
- `notes`

`source_ranks` should be a sorted list of source entries, not just a name list. Each entry should carry:

- `source_name`
- `rank`
- `authority_tier`
- `role`
- `rank_reason`
- `claim_scope`

`evidence_strength` should be a compact categorical summary, preferably paired with a score:

- `label`
- `score`
- `basis`
- `directness`

`provenance_bundle` should be the lineage pack that lets a downstream consumer replay the choice. It should include:

- `winner_source_refs`
- `alternate_source_refs`
- `manifest_refs`
- `transformation_refs`
- `raw_source_refs`

`training_safe_provenance` should tell the packet builder how the fused record may be used:

- `safe_to_train`
- `packet_mode`
- `packet_blockers`
- `lineage_refs`
- `audit_notes`

## Source Rank Model

The rank model is intentionally conservative:

1. `canonical_authority`
1. `direct_curated_evidence`
1. `supporting_class_evidence`
1. `context_proxy`
1. `derived_local`

The point is not to overfit a score. The point is to make the source ordering explicit enough that downstream logic can tell truth-bearing evidence from support and support from local projection.

## Evidence Strength Model

The evidence-strength labels should be easy to scan and stable across runs:

- `direct_primary`
- `direct_curated`
- `supporting_curated`
- `supporting_context`
- `derived_local`

If a record has multiple sources, the payload should still name the strongest basis that actually won the decision.

## Kind-Specific Rules

### Proteins

The winner should normally be a UniProt accession. Alternates should preserve alias chains, secondary accessions, and isoform disagreements when they matter.

Training-safe provenance requires that the canonical accession is explicit and that any unresolved identity conflict is visible.

### Structures

Experimental structure references from RCSB/PDBe must remain separate from predicted structure references from AlphaFold DB. The payload should never collapse those into one truth cell.

Training-safe provenance requires explicit chain, entity, assembly, and residue-span lineage.

### Ligands

Chemical identity should be anchored in ChEBI where possible. BindingDB and ChEMBL measurements stay attached as assay evidence rather than being blended into identity.

Training-safe provenance requires that identity and measurement are not conflated.

### Interactions

IntAct should lead curated interaction claims, with BioGRID as the second curated authority and STRING restricted to context support.

Training-safe provenance requires that binary-vs-native projection lineage is preserved.

### Motifs

InterPro should lead motif and domain claims. Broader umbrella terms may be retained, but they should not erase more specific residue-resolved annotations.

Training-safe provenance requires span-level lineage and namespace clarity.

### Pathways

Reactome should lead pathway claims. Species context and ancestry should remain attached so a parent pathway does not silently replace a reaction-level specialization.

Training-safe provenance requires stable pathway id plus species context.

### Assays

BindingDB and ChEMBL should lead assay claims. If the values disagree, keep the alternate measurements or convert the answer into a range rather than averaging away the disagreement.

Training-safe provenance requires endpoint, unit, construct context, and target accession.

## Dissent Rules

The payload should retain alternates when:

- values are not semantically equivalent
- source-specific scope differs
- experimental and predicted claims both exist
- the safest answer is an interval, set, or ordered list
- local extracted assets conflict with upstream evidence

The payload should mark a field `blocked` or `retrieval_only` for training when the conflict cannot be resolved without inventing evidence.

## Packet Safety

The payload is safe for downstream training when:

- `winner_value` exists and is explicit
- alternates remain attached when they matter
- `dissent_markers` are visible
- `source_ranks` are sorted and traceable
- `evidence_strength` is encoded
- `provenance_bundle` can reconstruct the fused choice
- `training_safe_provenance.safe_to_train` is true

The payload is not safe when:

- a conflict was collapsed without lineage
- experimental and predicted structure were merged into one claim
- assay values were averaged across incompatible contexts
- local extracted assets replaced upstream native evidence

## Practical Outcome

This contract gives the summary library one durable provenance envelope that can be embedded in every fused record. It keeps winner selection explainable, alternates visible, source order explicit, and training use gated by lineage rather than by guesswork.

# P29 Fused Field Truth Table

Date: 2026-03-30  
Artifact: `p29_fused_field_truth_table`

## Purpose

This table defines the first protein-card fields to materialize in the summary library implementation. It is intentionally narrow: one slice, one record kind, one goal.

The point is to make the first protein card deterministic. Every field should have a clear source precedence, a dissent rule, a null rule, and a provenance-payload requirement that keeps the fused card training-safe.

## Slice Boundary

This table applies only to protein cards in the first summary-library slice.

Current schema fields on `ProteinSummaryRecord` are:

- `summary_id`
- `protein_ref`
- `protein_name`
- `organism_name`
- `taxon_id`
- `sequence_checksum`
- `sequence_version`
- `sequence_length`
- `gene_names`
- `aliases`
- `join_status`
- `join_reason`
- `context`
- `notes`

The planning artifact also treats `reviewed` as an important signal, but the current protein record does not expose it as a top-level field. In this first slice, `reviewed` should be treated as index-only metadata.

## Common Provenance Rule

Every fused protein card should embed a provenance payload that can explain:

- the winner value
- any alternates
- source rank order
- evidence strength
- tie-break reason
- conflict markers
- lineage pointers

That payload is what makes a card safe for training packets. If the provenance cannot explain the winner, the card is not ready.

## Truth Table

| Field | Source precedence | Dissent behavior | Null behavior | Provenance payload requirement |
| --- | --- | --- | --- | --- |
| `summary_id` | `UniProt` accession first, then local extracted projection if the accession is already clean | Do not materialize a resolved card if accession normalization yields more than one identity | Not allowed | Must point back to the accession source record and retain any competing accession chain |
| `protein_ref` | `UniProt` first, then local projection | Do not collapse distinct accessions; keep alias chains visible | Not allowed for a materialized card | Winner value must carry source record id, release stamp, and the canonical accession source |
| `protein_name` | `UniProt` recommended name first, then local display label | Keep alternate labels in notes or provenance instead of promoting multiple primary names | Allowed if no trustworthy label exists | Selection reason must say whether the label is canonical or fallback |
| `organism_name` | `UniProt` species annotation first, then local projection | Species mismatches are join conflicts, not formatting issues | Allowed only if taxon provenance is carried alongside the card | Claim scope must identify species-level identity |
| `taxon_id` | `UniProt` species annotation first, then local projection | Treat taxon mismatch as a conflict state | Allowed if species could not be pinned without guessing | Source record id should point to the accession-scoped species source |
| `reviewed` | `UniProt` reviewed status first; keep as planning-index metadata in this slice | If review status differs, keep the card materialized but mark the difference in notes and provenance | Allowed because the current schema does not expose it top-level | Provenance must preserve the reviewed/unreviewed source pointer |
| `sequence_checksum` | `UniProt`, then exact-match `RCSB/PDBe`, `AlphaFold DB`, and local projection | Conflicting checksums mean sequence conflict; keep alternates or unresolved | Allowed if no stable checksum is available | Preserve the exact checksum string and mark training unsafe if sequence identity is unresolved |
| `sequence_version` | `UniProt` first, then local projection | Preserve alternate versions when source records disagree | Allowed if the version was not pinned | Selection reason should state whether the version was authoritative or derived |
| `sequence_length` | `UniProt` first, then exact-match structural support, then local projection | Length disagreement is a sequence conflict, not a convenience issue | Allowed if no sequence source supports the claim | Raw and normalized lengths should both be traceable |
| `gene_names` | `UniProt` gene set first, then local projection | Keep alternate gene symbols distinct; do not flatten them into one synonym blob | Allowed as an empty tuple | Alternate gene symbols should remain source-scoped in provenance |
| `aliases` | `UniProt` secondary accessions and synonyms first, then local projection | If an alias collides with another accession, keep the conflict visible | Allowed as an empty tuple | Each alias should preserve source_name and source_record_id in lineage |
| `join_status` | Consensus materializer and scope audit first | Use `partial`, `ambiguous`, `conflict`, or `unjoined` when anything required remains unresolved | Not allowed | Must be explainable by conflict markers and tie-break reason |
| `join_reason` | Consensus materializer explanation first | Name the missing or conflicting evidence class when the card is not fully resolved | Allowed only for fully joined cards with no special handling | Should echo the selection reason and tie-break reason |
| `notes` | Consensus materializer first, local projection second | Append conflict notes instead of replacing truth-bearing fields | Allowed as an empty tuple for clean cards | Notes should echo alternates and conflict markers without duplicating raw payloads |
| `context.provenance_pointers` | Winning source pointer first, then alternates, then support-only pointers | Keep a pointer for every competing value path so the card can be replayed later | Not allowed for a materialized card | Each pointer should carry provenance_id, source_name, source_record_id, release_version, acquired_at, checksum, and join_status |

## Practical Rules

1. `summary_id` and `protein_ref` are the identity gate. If they are not stable, nothing else should be treated as final.
2. `protein_name`, `organism_name`, `gene_names`, and `aliases` are helpful display and routing fields, but they should never override identity.
3. `sequence_checksum`, `sequence_version`, and `sequence_length` are the first true sequence-truth fields, so conflicts there should stay explicit.
4. `join_status`, `join_reason`, and `notes` are control and explanation fields. They should describe the decision, not replace it.
5. `context.provenance_pointers` is mandatory for any materialized card. If there is no traceable pointer, the card should remain blocked.
6. `reviewed` belongs in the index for this slice, not as a top-level protein card field.

## Null And Conflict Posture

- If identity is unresolved, do not pretend the card is complete.
- If sequence identity conflicts, keep alternates or mark the card unresolved.
- If display labels are missing, leave them blank rather than synthesizing them.
- If provenance pointers are missing, do not materialize the card.

## Training-Safe Posture

A protein card is safe for downstream training only when:

- the canonical accession is explicit
- the field-level winners are explainable
- any alternates remain attached
- the provenance payload can reconstruct the decision

If those conditions are not met, the card may still be useful for inspection or retrieval, but it should not be treated as training-safe.

## Bottom Line

This is the first-slice truth table for protein cards. It keeps the implementation small, deterministic, and auditable, while still allowing partial cards to stay visible when the evidence is incomplete.

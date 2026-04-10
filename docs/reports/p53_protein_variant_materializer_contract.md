# P53 Protein Variant Materializer Contract

This is a report-only contract for the smallest truthful first executable `protein_variant` slice. It is grounded in [core/library/summary_record.py](../../core/library/summary_record.py), [execution/library/protein_summary_materializer.py](../../execution/library/protein_summary_materializer.py), and the existing p29, p51, and v2 bridge plans.

## Scope

- Keep this slice additive and non-destructive.
- Use only already-procured mutation and construct evidence.
- Keep the claim accession-scoped and explicit.
- Do not invent coverage for unsupported isoforms, constructs, or point mutations.

## First Executable Slice

The first materializable slice is accession-scoped, explicit variant evidence that already exists in the current repository inputs:

- a UniProt accession is available
- the mutation or construct signature is already explicit in UniProt or a local extracted asset
- the row can be classified without inferring from names alone
- any mutation list or sequence delta is already grounded in the evidence set

Anything that fails those conditions stays partial or out of slice.

## Source Order

1. UniProt
2. Local extracted assets
3. RCSB/PDBe
4. AlphaFold DB

PDBBind and BioLiP are deferred for this first slice.

## Field Contract

The first slice requires these v2 fields:

- `summary_id`
- `protein_ref`
- `variant_signature`
- `variant_kind`
- `is_partial`

The slice may also carry:

- `parent_protein_ref`
- `mutation_list`
- `sequence_delta_signature`
- `construct_type`
- `organism_name`
- `taxon_id`
- `variant_relation_notes`
- `join_reason`
- `notes`

Population rules:

- `protein_ref` must be accession-first and never widened to a name-only claim.
- `variant_signature` must be the smallest stable mutation or construct signature already evidenced.
- `variant_kind` should only be used when the current source already distinguishes isoform, engineered, truncation, point_mutant, or partial.
- `mutation_list` and `sequence_delta_signature` should stay null or empty unless already grounded in current evidence.
- `construct_type` should come only from explicit construct or isoform labels.
- `is_partial` should be true whenever accession lineage, mutation list, or sequence delta is incomplete.

## Context and Evidence

The record context should preserve the existing planning scaffolding:

- `planning_index_keys` from the existing `SummaryRecordContext` defaults
- `deferred_payloads` for the full annotation and mutation projection payloads
- `materialization_pointers` only when they already exist in the current repository evidence

The materializer already has the right conceptual posture for this slice:

- keep the accession spine from UniProt
- keep construct and mutation claims explicit
- defer richer mutation projection payloads
- preserve source lineage in notes rather than widening the claim

## Fail-Closed Rules

Do not materialize the record if:

- only a display name or alias is present
- the accession candidate is ambiguous
- the claim cannot be anchored to a canonical UniProt accession
- the variant-specific differences would be collapsed into the base protein record

## Backward Compatibility

- Keep current schema v1 payloads readable.
- Keep existing `protein`, `protein_protein`, and `protein_ligand` records unchanged.
- Make `protein_variant` additive rather than overloaded.
- Leave partial rows partial instead of coercing them into a different record kind.

## Practical Outcome

This contract defines the smallest truthful first implementation target for variant materialization: explicit accession-scoped mutation or construct rows already supported by current inputs, with no implied expansion into ungrounded isoform or mutation coverage.

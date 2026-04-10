# P52 Structure Unit Materializer Contract

This is a report-only contract for the smallest truthful first executable `structure_unit` slice. It is grounded in [core/library/summary_record.py](../../core/library/summary_record.py) and [execution/library/protein_summary_materializer.py](../../execution/library/protein_summary_materializer.py), plus the existing p29 and p51 summary-library plans.

## Scope

- Keep this slice additive and non-destructive.
- Use already-parsed SIFTS, CATH, and SCOP evidence only.
- Keep experimental and predicted structures separate.
- Do not invent new procurement or infer structure units from names alone.

## First Executable Slice

The first materializable slice is pointer-gated, experimental, chain-resolved structure evidence:

- a current materialization pointer already exists for the protein/structure row
- a UniProt accession can be projected through an explicit SIFTS-style bridge
- `entity_id`, `chain_id`, `assembly_id`, and residue span are explicit
- CATH and SCOP are optional enrichment lanes when the same PDB and chain already resolve

Anything missing those anchors stays partial or out of slice.

## Source Order

1. Existing materialization pointers
2. PDBe UniProt mapping / SIFTS-style bridge
3. Parsed CATH local copies
4. Parsed SCOP local copies
5. Local extracted assets

AlphaFold DB, PDBBind, and BioLiP are deferred for this first slice.

## Field Contract

The first slice requires these v2 fields:

- `summary_id`
- `protein_ref`
- `structure_source`
- `structure_id`
- `structure_kind`
- `entity_id`
- `chain_id`
- `assembly_id`
- `residue_span_start`
- `residue_span_end`
- `experimental_or_predicted`
- `mapping_status`

The slice may also carry:

- `variant_ref`
- `model_id`
- `resolution_or_confidence`
- `structure_relation_notes`
- `join_reason`
- `notes`

Population rules:

- `protein_ref` must come from an explicit UniProt mapping bridge.
- `structure_source` and `structure_id` must remain source-native.
- `structure_kind` must be `experimental` for this first slice.
- `experimental_or_predicted` must be explicit and never inferred.
- `mapping_status` should be `joined` only when accession, chain, entity, assembly, and span are all explicit.
- `variant_ref` stays empty unless the current pointer already identifies a known variant or construct.
- `resolution_or_confidence` is optional and may remain null when the current parsed evidence does not expose it.

## Context and Evidence

The record context should preserve the existing planning and provenance scaffolding:

- `materialization_pointers` from the current planning index pointer set
- `planning_index_keys` from the existing `SummaryRecordContext` defaults
- `domain_references` for already-parsed CATH or SCOP annotations
- `source_connections` for explicit UniProt-to-structure joins
- `cross_references` when they already exist in the current materialization payload

The materializer already has the right evidence hooks for this slice:

- `_sifts_rows_by_pdb_and_accession(...)`
- `_cath_domain_class_map(...)`
- `_cath_class_label_map(...)`
- `_scope_class_map(...)`
- `_scope_label_map(...)`
- `_extract_classification_references(...)`

## Fail-Closed Rules

Do not materialize the record if:

- `entity_id`, `chain_id`, `assembly_id`, or residue span is missing
- there is no explicit UniProt mapping
- the row is only identified by structure name or structure_id
- experimental and predicted claims would be merged

## Backward Compatibility

- Keep current schema v1 payloads readable.
- Keep existing `protein`, `protein_protein`, and `protein_ligand` records unchanged.
- Make `structure_unit` additive rather than overloaded.
- Leave partial rows partial instead of coercing them into v1 shapes.

## Practical Outcome

This contract defines the smallest truthful first implementation target: explicit experimental structure units already supported by current parsed SIFTS evidence, with CATH and SCOP as optional classification enrichment. It should be enough to start implementation without changing the current code paths or inventing any new procurement.

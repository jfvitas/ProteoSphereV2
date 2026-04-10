# Structure Motif Join Mapping

This report-only mapping describes how motif, pathway, and structural-class sources should land on the first executable lightweight-library surfaces: `protein_variant` and `structure_unit`.

## Grounding

- Motif backbone step-1 contract: `artifacts/status/p46_motif_backbone_step1_contract.json`
- Motif backbone output spec: `artifacts/status/p47_motif_backbone_output_spec.json`
- Motif backbone validation contract: `artifacts/status/p48_motif_backbone_validation_contract.json`
- Lightweight-library backlog: `artifacts/status/p49_lightweight_library_enrichment_backlog.json`
- Motif/pathway tranche: `artifacts/status/p50_motif_pathway_enrichment_tranche.json`
- Summary-library v2 bridge: `artifacts/status/p29_summary_library_v2_bridge.json`
- Summary-library next slices: `artifacts/status/p29_summary_library_next_slices.json`
- Summary record schema: `core/library/summary_record.py`
- Lightweight reference master plan: `docs/reports/lightweight_reference_library_master_plan.md`
- Current coverage truth: `artifacts/status/source_coverage_matrix.json`
- Mirror truth: `artifacts/status/broad_mirror_progress.json`

## First Executable Surfaces

### `protein_variant`

Purpose:

- represent wild-type, engineered, isoform, truncation, and point-mutant variants without collapsing them into the protein spine
- act as the primary protein-bearing annotation carrier for motif, domain, and pathway references

Minimum top-level fields:

- `summary_id`
- `protein_ref`
- `parent_protein_ref`
- `variant_signature`
- `variant_kind`
- `mutation_list`
- `sequence_delta_signature`
- `construct_type`
- `is_partial`
- `organism_name`
- `taxon_id`
- `variant_relation_notes`
- `join_status`
- `join_reason`
- `context`
- `notes`

Context surfaces to use first:

- `motif_references`
- `domain_references`
- `pathway_references`
- `cross_references`
- `provenance_pointers`

### `structure_unit`

Purpose:

- distinguish experimental and predicted structures while preserving chain, entity, assembly, and span lineage
- act as the coordinate-bearing carrier for structural-class and structure-linked annotations

Minimum top-level fields:

- `summary_id`
- `protein_ref`
- `structure_source`
- `structure_id`
- `variant_ref`
- `structure_kind`
- `model_id`
- `entity_id`
- `chain_id`
- `assembly_id`
- `residue_span_start`
- `residue_span_end`
- `resolution_or_confidence`
- `experimental_or_predicted`
- `mapping_status`
- `structure_relation_notes`
- `join_status`
- `join_reason`
- `context`
- `notes`

Context surfaces to use first:

- `motif_references`
- `domain_references`
- `pathway_references`
- `cross_references`
- `provenance_pointers`

## Join Routing

### InterPro

- Primary landing surface: `protein_variant.context.domain_references`
- Secondary landing surface: `structure_unit.context.domain_references` only when a stable protein-to-structure join exists
- Join keys: UniProt accession, explicit `span_start` / `span_end`, and taxon when available
- What stays source-specific: `IPR` accession, member-signature accession, integrated vs unintegrated provenance, clan/set ids
- Current state: ready now from registry-known and pinned seed evidence

### PROSITE

- Primary landing surface: `protein_variant.context.motif_references`
- Secondary landing surface: `structure_unit.context.motif_references` only when a stable protein-to-structure join exists
- Join keys: UniProt accession, explicit `span_start` / `span_end`
- What stays source-specific: `PDOC`, `PS`, and `PRU` accessions, pattern/profile identity, documentation accession
- Current state: ready now from registry-known and pinned seed evidence

### Reactome

- Primary landing surface: `protein_variant.context.pathway_references`
- Secondary landing surface: `structure_unit.context.pathway_references` only as inherited pathway context for a structure-backed protein
- Join keys: UniProt accession plus stable Reactome identifier and species/version context
- What stays source-specific: Reactome stable ID, release/version, pathway ancestry, species
- Current state: ready now from registry-known and pinned seed evidence

### CATH

- Primary landing surface: `structure_unit.cross_references`
- Secondary landing surface: `structure_unit.structure_relation_notes`
- Join keys: `structure_source`, `structure_id`, `entity_id`, `chain_id`, `assembly_id`, and protein_ref when available
- What stays source-specific: CATH class, fold, superfamily, architecture ids
- Current state: local-registry known, no scrape needed

### SCOP

- Primary landing surface: `structure_unit.cross_references`
- Secondary landing surface: `structure_unit.structure_relation_notes`
- Join keys: `structure_source`, `structure_id`, `entity_id`, `chain_id`, `assembly_id`, and protein_ref when available
- What stays source-specific: SCOP class, fold, superfamily, family ids
- Current state: local-registry known, no scrape needed

### ELM

- Primary landing surface: `protein_variant.context.motif_references`
- Secondary landing surface: `structure_unit.context.motif_references` only if a structure-linked variant is already explicit
- Join keys: UniProt accession, explicit `span_start` / `span_end`, and organism
- What stays source-specific: ELME accession, instance row id, evidence count, partner-context hints
- Current state: partial in the local registry, but pinned TSV exports are present; keep it conditional rather than blocking the first build

## Corroboration Rules

- `protein_ref` is the spine that links protein_variant and structure_unit records.
- `variant_signature` and `parent_protein_ref` distinguish the variant row; they must not be inferred from motif or pathway annotations.
- `residue_span_start` and `residue_span_end` are the bridge between protein-bearing annotations and structure-bearing evidence.
- `structure_source`, `structure_id`, `entity_id`, `chain_id`, and `assembly_id` must stay visible on structure_unit rows and must not be replaced by annotation namespaces.
- Motif and pathway sources can corroborate a protein_variant, but they do not create structure identity.
- CATH and SCOP corroborate structure class only; they do not create motif identity.

## Truth Boundaries

- Do not scrape InterPro, PROSITE, Reactome, CATH, or SCOP.
- Do not scrape ELM first; use the pinned TSV exports if the build needs ELM at all.
- Do not synthesize structure ids, variant signatures, or spans from cross-source hints.
- Do not merge experimental and predicted structure into one row.
- Do not let motif or pathway presence imply a structure match without an explicit protein/variant bridge.

## Bottom Line

The first executable library build should route annotation-heavy sources into `protein_variant`, structural-class sources into `structure_unit`, and keep source-native identifiers and spans explicit so the bridge stays reversible.

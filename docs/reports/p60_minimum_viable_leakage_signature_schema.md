# P60 Minimum Viable Leakage Signature Schema

Date: 2026-04-01
Artifact: `p60_minimum_viable_leakage_signature_schema`

## Objective

Define the smallest truthful `leakage-signature schema` the lightweight library can support now, using only fields that are already materialized in current live records.

This is a report-only proposal. It does not add code and does not claim that leakage signatures are already bundled.

It is grounded in:

- [lightweight_reference_library_master_plan.md](/D:/documents/ProteoSphereV2/docs/reports/lightweight_reference_library_master_plan.md)
- [lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- [protein_variant_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_variant_summary_library.json)
- [structure_unit_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_unit_summary_library.json)

## Recommendation

The minimum viable schema should reuse the already declared bundle family name:

- `leakage_groups`

But the row semantics should be:

- one `entity leakage signature` row per currently materialized lightweight entity

That means the family is called `leakage_groups`, but each row is an entity-level signature record carrying conservative split keys.

This is the smallest useful design because it:

- aligns with the bundle manifest vocabulary already present in [lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- uses only fields we already materialize
- supports immediate train/test split guards
- does not require new biology extraction or source acquisition

## Current Feasible Scope

The current live lightweight entities that can receive leakage signatures are:

- `11` protein rows
- `1874` protein-variant rows
- `4` structure-unit rows

So the first executable leakage layer could cover:

- `1889` entity signature rows total

Current real grouping capacity:

- `11` distinct protein-spine groups
- `11` distinct protein sequence-checksum groups
- `9` distinct protein domain-architecture groups
- `1` currently visible structure fold group across the live structure-unit slice

## Minimal Family Shape

The proposed logical family is:

- family name: `leakage_groups`
- row type: `entity_leakage_signature`

Primary key:

- `leakage_signature:{entity_ref}`

Examples:

- `leakage_signature:protein:P04637`
- `leakage_signature:protein_variant:protein:P04637:A119D`
- `leakage_signature:structure_unit:protein:P68871:4HHB:B`

## Required Fields

Each row should contain:

- `signature_id`
- `entity_ref`
- `entity_type`
- `protein_ref`
- `parent_protein_ref`
- `source_manifest_id`
- `signature_schema_version`
- `derivation_status`
- `confidence_tier`

### Exact split keys

- `exact_entity_group_key`
- `protein_spine_group_key`

### Conservative biological leakage axes

- `taxon_group_key`
- `sequence_equivalence_group_key`
- `variant_delta_group_key`
- `motif_domain_architecture_group_key`
- `pathway_context_group_key`
- `structure_chain_group_key`
- `structure_fold_group_key`

### Guidance and provenance

- `axes_present`
- `axes_inherited_from_parent`
- `recommended_split_policy`
- `derivation_notes`

## What Each Axis Means

### `exact_entity_group_key`

Meaning:

- never split the exact same lightweight entity across train/test

Source:

- `summary_id`

Confidence:

- `high`

### `protein_spine_group_key`

Meaning:

- keep all entities tied to the same canonical protein accession together in default leakage-safe mode

Source:

- `protein_ref` or `parent_protein_ref`

Confidence:

- `high`

### `taxon_group_key`

Meaning:

- keep taxonomic lineage available for broader bias and leakage controls

Current source:

- `taxon_id` on protein and variant rows
- inherited from parent protein for structure-unit rows

Confidence:

- `high` when directly present
- `medium` when inherited

### `sequence_equivalence_group_key`

Meaning:

- separate exact sequence-equivalent proteins from other proteins

Current source:

- protein `sequence_checksum`
- inherited protein `sequence_checksum` for structure-unit rows

Variant handling:

- variants do not currently have modified sequence checksums
- for variants, this axis should point to the parent-protein sequence checksum and be marked as inherited

Confidence:

- `high` for protein rows
- `medium` for variant and structure rows when inherited

### `variant_delta_group_key`

Meaning:

- keep exact mutation signatures available as a variant-level leakage axis

Current source:

- `sequence_delta_signature`

Examples:

- `A119D`
- `E17K`
- `A116D`

Confidence:

- `high` for current point-mutation rows

### `motif_domain_architecture_group_key`

Meaning:

- coarse biological similarity axis for proteins sharing the same current motif and domain architecture summary

Current source:

- sorted motif identifiers from `motif_references`
- sorted domain identifiers from `domain_references`

Variant and structure handling:

- inherited from the parent protein in the minimum viable design

Confidence:

- `medium`

Reason:

- current data is already useful, but this is still a compressed architecture proxy rather than a residue-level site signature

### `pathway_context_group_key`

Meaning:

- coarse functional-context grouping for leakage-aware balancing

Current source:

- sorted pathway identifiers from `pathway_references`

Variant and structure handling:

- inherited from the parent protein in the minimum viable design

Confidence:

- `medium`

### `structure_chain_group_key`

Meaning:

- exact structure-chain leakage key

Current source:

- `structure_source`
- `structure_id`
- `chain_id`
- optional residue span

Confidence:

- `high`

### `structure_fold_group_key`

Meaning:

- coarse structure-level similarity key

Current source:

- current structure-unit `domain_references`, especially CATH/SCOPe-derived identifiers

Confidence:

- `medium_high`

Reason:

- grounded in real current structure-unit joins, but still only as broad as the current classification-linked chain slice

## Derivation Rules By Entity Type

### Protein rows

Populate directly from the protein summary record:

- `exact_entity_group_key = summary_id`
- `protein_spine_group_key = protein_ref`
- `taxon_group_key = taxon:{taxon_id}`
- `sequence_equivalence_group_key = protein_seq:{sequence_checksum}`
- `variant_delta_group_key = null`
- `motif_domain_architecture_group_key = motif_domain:{sorted motif ids + sorted domain ids}`
- `pathway_context_group_key = pathway_set:{sorted pathway ids}`
- `structure_chain_group_key = null`
- `structure_fold_group_key = null`

### Protein-variant rows

Populate directly where possible and inherit parent-protein axes where needed:

- `exact_entity_group_key = summary_id`
- `protein_spine_group_key = parent_protein_ref`
- `taxon_group_key = inherited from parent protein`
- `sequence_equivalence_group_key = inherited parent protein sequence checksum`
- `variant_delta_group_key = variant_delta:{parent_protein_ref}:{sequence_delta_signature}`
- `motif_domain_architecture_group_key = inherited from parent protein`
- `pathway_context_group_key = inherited from parent protein`
- `structure_chain_group_key = null`
- `structure_fold_group_key = null`

### Structure-unit rows

Populate directly where possible and inherit parent-protein axes where needed:

- `exact_entity_group_key = summary_id`
- `protein_spine_group_key = protein_ref`
- `taxon_group_key = inherited from parent protein`
- `sequence_equivalence_group_key = inherited parent protein sequence checksum`
- `variant_delta_group_key = null`
- `motif_domain_architecture_group_key = inherited from parent protein`
- `pathway_context_group_key = inherited from parent protein`
- `structure_chain_group_key = structure_chain:{structure_source}:{structure_id}:{chain_id}:{residue_span}`
- `structure_fold_group_key = structure_fold:{sorted structure domain identifiers}`

## Recommended Split Policy

### Default mode

Never split across:

- `exact_entity_group_key`
- `protein_spine_group_key`

Use for balancing and diagnostics:

- `taxon_group_key`
- `motif_domain_architecture_group_key`
- `pathway_context_group_key`

### Strict mode

Never split across:

- `exact_entity_group_key`
- `protein_spine_group_key`
- `sequence_equivalence_group_key`
- `variant_delta_group_key`
- `structure_chain_group_key`
- `structure_fold_group_key`

Use for balancing and diagnostics:

- `taxon_group_key`
- `motif_domain_architecture_group_key`
- `pathway_context_group_key`

## Current Grounded Examples

### `protein:P04637`

Current facts:

- sequence checksum: `md5:C133DFCE69F606F20865E9008199F852`
- motif IDs: `PS00348`
- domain IDs include:
  - `IPR002117`
  - `IPR008967`
  - `IPR010991`
  - `PF00870`
  - `PF08563`
- pathway count: `124`

Useful leakage interpretation:

- all `P04637` protein, variant, and future structure rows should share the same `protein_spine_group_key`
- the `1439` current variant rows for `P04637` should inherit the same protein-level architecture and pathway axes

### `protein_variant:protein:P04637:A119D`

Current facts:

- parent protein: `protein:P04637`
- variant signature: `A119D`
- variant kind: `point_mutation`
- sequence delta signature: `A119D`

Useful leakage interpretation:

- exact-entity leakage stays at the variant row level
- parent-protein leakage stays at `protein:P04637`
- mutation-specific leakage is represented by `variant_delta_group_key`

### `structure_unit:protein:P68871:4HHB:B`

Current facts:

- structure source: `PDB`
- structure ID: `4HHB`
- chain: `B`
- residue span: `2-147`
- structure domain IDs:
  - `1.10.490.10`
  - `a.1.1.2`

Useful leakage interpretation:

- this row needs both a `protein_spine_group_key` and a `structure_chain_group_key`
- fold-level grouping should use `1.10.490.10|a.1.1.2`

### `structure_unit:protein:P69905:4HHB:A`

Current facts:

- same PDB complex family as `P68871`
- same current structure fold group
- different parent protein accession

Useful leakage interpretation:

- `P68871` and `P69905` should stay separated by `protein_spine_group_key`
- they can still collide in strict fold-level controls via `structure_fold_group_key`

That is a good example of why multiple leakage axes are needed instead of one similarity number.

## Explicit Exclusions

The minimum viable schema should not attempt to encode yet:

- ligand-based leakage
- interaction-network leakage
- active-site residue fingerprints
- interface residue fingerprints
- assembly graph similarity
- raw coordinate-derived signatures

Those all need additional materialized families or heavier processing than the current live library supports.

## Bundle Integration Recommendation

Near-term bundle treatment:

- keep the manifest family name `leakage_groups`
- materialize one compact row per live entity
- store the current axis keys as strings or compact encoded values
- mark the family as optional but publishable once emitted

This is compatible with the current bundle posture because it adds governance value without requiring heavy payloads.

## Bottom Line

The minimum viable leakage schema should be conservative and immediate:

- one leakage-signature row per current protein, protein-variant, and structure-unit entity
- exact, protein-spine, sequence, variant-delta, motif/domain, pathway, structure-chain, and structure-fold axes
- inherited parent-protein fields where direct variant/structure values do not exist
- no ligand or interaction leakage until those families are actually materialized

That is enough to start leakage-safe split governance now, using the records already present in the lightweight library.

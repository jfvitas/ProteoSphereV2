# P61 Minimum Leakage Signature Schema

Date: 2026-04-01
Artifact: `p61_minimum_leakage_signature_schema`

## Objective

Propose the smallest next schema expansion after the current [leakage_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/leakage_signature_preview.json) so the lightweight library can support leakage-safe splitting across:

- variants
- structures
- future ligand families

This is a report-only note. It does not add code and does not claim that the expanded schema is already emitted.

It is grounded in:

- [leakage_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/leakage_signature_preview.json)
- [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- [protein_variant_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_variant_summary_library.json)
- [structure_unit_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_unit_summary_library.json)
- [lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json)

## Current Preview Boundary

The current preview is accession-level only.

It currently gives one row per protein accession with fields like:

- `exact_accession_group`
- `sequence_checksum_group`
- `structure_signature_group`
- `domain_signature_group`
- `pathway_signature_group`
- `motif_signature_group`
- `variant_count`
- `structure_ids`
- `candidate_status`
- `leakage_risk_class`

That is useful for operator triage, but it is not enough for leakage-safe splitting across current non-protein entities because it does not create separate split keys for:

- individual variant entities
- individual structure-unit entities
- future ligand entities

## Recommendation

The smallest next expansion should be:

1. keep the current accession-level preview shape as a derived summary layer
2. add one new `entity_signature_rows` layer underneath it

This avoids breaking the current preview while adding the minimum entity-level split surface needed for training-set governance.

## Proposed V2 Shape

Recommended top-level posture:

- keep `leakage_signature_preview` semantics for accession summaries
- add a new schema version and one additional row collection for entity signatures

Recommended top-level sections:

- `accession_summary_rows`
- `entity_signature_rows`
- `family_readiness`
- `truth_boundary`

## Why This Is The Minimum Next Step

This expansion is enough because:

- proteins are already materialized
- variants are already materialized
- structures are already materialized
- ligands are not yet materialized, but the bundle manifest already declares the `ligands` family and canonical state already contains ligand records

Current live counts:

- accession preview rows: `11`
- protein-variant rows: `1874`
- structure-unit rows: `4`
- bundle-visible ligands: `0`
- canonical ligands in [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json): `4124`

So the minimum practical move is not to fully solve ligands now. It is to add entity-level keys for the families we already have, plus reserved ligand hooks.

## `accession_summary_rows` Contract

This layer should remain close to the current preview rows.

Purpose:

- operator-facing summary
- accession-level risk classification
- quick triage and current-state communication

Minimum change:

- rename current `rows` to `accession_summary_rows` in the future schema
- keep current fields stable where possible
- allow each accession summary row to point to counts of entity rows beneath it

New optional summary fields:

- `entity_signature_count`
- `variant_signature_count`
- `structure_signature_count`
- `future_ligand_signature_count`

## `entity_signature_rows` Contract

This is the minimum new layer needed for leakage-safe splitting.

One row per currently materialized entity:

- one row per protein
- one row per protein variant
- one row per structure unit
- future one row per ligand entity when ligands become materialized in the lightweight library

Primary key:

- `entity_signature:{entity_ref}`

Examples:

- `entity_signature:protein:P04637`
- `entity_signature:protein_variant:protein:P04637:A119D`
- `entity_signature:structure_unit:protein:P68871:4HHB:B`

## Required Fields For `entity_signature_rows`

- `entity_signature_id`
- `entity_ref`
- `entity_type`
- `accession`
- `protein_ref`
- `parent_protein_ref`
- `source_manifest_id`
- `signature_schema_version`
- `derivation_status`
- `confidence_tier`

### Required split-group fields

- `exact_entity_group`
- `protein_spine_group`
- `sequence_equivalence_group`
- `variant_delta_group`
- `structure_chain_group`
- `structure_fold_group`
- `ligand_identity_group`
- `binding_context_group`

### Required support fields

- `axes_present`
- `axes_inherited_from_parent`
- `recommended_split_policy`
- `entity_truth_note`

## Meaning Of The New Group Fields

### `exact_entity_group`

Meaning:

- do not split the exact same entity instance

Examples:

- exact protein row
- exact variant row
- exact structure chain row
- future exact ligand row

### `protein_spine_group`

Meaning:

- keep all entities tied to the same canonical protein together in default leakage-safe mode

This is the bridge that lets protein, variant, and structure entities share a conservative split boundary.

### `sequence_equivalence_group`

Meaning:

- prevent splitting exact same-sequence entities even when entity type differs

Current grounding:

- direct for proteins
- inherited for variants and structures

### `variant_delta_group`

Meaning:

- keep exact mutation signatures available as a variant-specific split axis

Current grounding:

- direct from `sequence_delta_signature`

### `structure_chain_group`

Meaning:

- exact structure-unit split boundary

Current grounding:

- `structure_source`
- `structure_id`
- `chain_id`
- residue span

### `structure_fold_group`

Meaning:

- coarse structure similarity boundary

Current grounding:

- current structure-unit domain/fold identifiers from the live structure slice

### `ligand_identity_group`

Meaning:

- exact or normalized ligand identity boundary

Current grounding:

- reserved only

Why it must appear now:

- the schema should not need another breaking change once lightweight ligand rows are introduced

### `binding_context_group`

Meaning:

- future protein-ligand leakage boundary that combines ligand identity with its protein context

Current grounding:

- reserved only

Why it must appear now:

- future ligand-aware split safety will need this axis, and the field can safely stay null until the ligand family is live

## Derivation Rules By Entity Type

### Protein entity rows

Populate:

- `exact_entity_group = summary_id`
- `protein_spine_group = protein_ref`
- `sequence_equivalence_group = sequence_checksum`
- `variant_delta_group = null`
- `structure_chain_group = null`
- `structure_fold_group = null`
- `ligand_identity_group = null`
- `binding_context_group = null`

### Variant entity rows

Populate:

- `exact_entity_group = summary_id`
- `protein_spine_group = parent_protein_ref`
- `sequence_equivalence_group = inherited parent sequence checksum`
- `variant_delta_group = sequence_delta_signature`
- `structure_chain_group = null`
- `structure_fold_group = null`
- `ligand_identity_group = null`
- `binding_context_group = null`

### Structure entity rows

Populate:

- `exact_entity_group = summary_id`
- `protein_spine_group = protein_ref`
- `sequence_equivalence_group = inherited parent sequence checksum`
- `variant_delta_group = null`
- `structure_chain_group = structure_source + structure_id + chain_id + residue span`
- `structure_fold_group = sorted current fold/domain identifiers`
- `ligand_identity_group = null`
- `binding_context_group = null`

### Future ligand entity rows

Populate once the ligand family exists:

- `exact_entity_group = ligand entity identity`
- `protein_spine_group = protein context when ligand is attached to a protein-bound example, otherwise null`
- `sequence_equivalence_group = null`
- `variant_delta_group = null`
- `structure_chain_group = optional if bound to a structure unit`
- `structure_fold_group = optional if bound to a structure-classified structure unit`
- `ligand_identity_group = normalized ligand identity`
- `binding_context_group = normalized ligand identity + protein spine + optional structure context`

## `family_readiness` Section

This section should be added in the next schema version so consumers know which entity types are real.

Minimum fields:

- `proteins_ready`
- `protein_variants_ready`
- `structures_ready`
- `ligands_ready`

Current truthful values:

- proteins: `true`
- variants: `true`
- structures: `true`
- ligands: `false`

## Grounded Examples

### `protein:P04637`

Current live evidence:

- exact accession row exists in [leakage_signature_preview.json](/D:/documents/ProteoSphereV2/artifacts/status/leakage_signature_preview.json)
- `variant_count = 1439`
- no current structure-unit row

Why the expansion helps:

- the accession-level preview says `structure_followup`
- the new entity layer would make each `P04637` variant split-safe instead of only counting them

### `protein_variant:protein:P04637:A119D`

Current live evidence from [protein_variant_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_variant_summary_library.json):

- `variant_signature = A119D`
- `sequence_delta_signature = A119D`
- `parent_protein_ref = protein:P04637`

Why the expansion helps:

- this becomes a first-class leakage entity instead of being collapsed into the protein accession summary

### `structure_unit:protein:P68871:4HHB:B`

Current live evidence from [structure_unit_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_unit_summary_library.json):

- `structure_id = 4HHB`
- `chain_id = B`
- fold/domain support includes:
  - `1.10.490.10`
  - `a.1.1.2`

Why the expansion helps:

- exact structure-chain split boundaries become explicit
- fold-level leakage control becomes possible across current structure rows

### Future ligand hook

Current live truth:

- bundle ligands are still `0` in [lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- canonical ligands are already non-zero in [LATEST.json](/D:/documents/ProteoSphereV2/data/canonical/LATEST.json)

Why the hook belongs in the next schema now:

- it avoids another schema redesign when lightweight ligand rows are introduced
- it does not overclaim current ligand coverage because the fields can remain null while `ligands_ready = false`

## Minimum Compatibility Rule

The smallest safe compatibility rule is:

- current accession preview remains readable
- new consumers may use `entity_signature_rows`
- old consumers can ignore the new section entirely

That makes the expansion additive rather than breaking.

## Explicit Exclusions

This minimum next expansion should still avoid:

- learned similarity clusters
- residue-level active-site fingerprints
- interface fingerprints
- interaction-network leakage
- graph-derived topology signatures
- ligand-class or scaffold leakage until lightweight ligand rows are actually emitted

## Bottom Line

The minimum next schema expansion after the current accession-level preview is:

- keep the accession summary rows
- add one entity-level signature row collection
- add reserved ligand-aware split fields now
- keep all future ligand axes null until ligands are actually materialized

That is the smallest additive schema change that makes leakage-safe splitting possible across current variants and structures, while staying ready for future ligand families.

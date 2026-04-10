# P59 Operator Accession Coverage Surface

Date: 2026-04-01
Artifact: `p59_operator_accession_coverage_surface`

## Objective

Propose the next smallest useful `operator-facing addition` now that these surfaces are already visible:

- [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- [protein_variant_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_variant_summary_library.json)
- [structure_unit_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_unit_summary_library.json)
- [lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json)
- [duplicate_cleanup_executor_status.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_executor_status.json)

This is a report-only proposal. It does not add code and does not change any operator surface.

## Recommendation

The next smallest useful operator-facing addition should be a single accession-centric rollup surface:

- `summary_library_operator_accession_matrix`

Recommended future output path:

- `artifacts/status/summary_library_operator_accession_matrix.json`

## Why This Is The Smallest Useful Next Step

The operator can already answer these slice-level questions:

- how many protein summary rows exist
- how many variant rows exist
- how many structure-unit rows exist
- whether the bundle manifest aligns with live slice counts
- whether the duplicate cleanup executor is safe-first and still report-only

The operator still cannot answer the smallest actionable accession-level question:

- for a specific protein accession, which visible lightweight families are present right now, which are absent, and what is the next obvious action?

That is the current visibility gap.

Bundle validation is slice-level, not accession-level. Duplicate cleanup is storage-level, not biology-level. The next addition should bridge the operator from `library counts` to `accession actionability` without adding a new biological materializer.

## Current Evidence For The Gap

From the currently visible summary-library slices:

- proteins: `11`
- variant-bearing proteins: `4`
- structure-bearing proteins: `2`

Current accession coverage pattern:

- proteins with variants:
  - `P04637`
  - `P31749`
  - `P68871`
  - `P69905`
- proteins with structure units:
  - `P68871`
  - `P69905`
- proteins with variants but no structure units:
  - `P04637`
  - `P31749`
- proteins with protein summaries but no variants:
  - `P00387`
  - `P02042`
  - `P02100`
  - `P09105`
  - `P69892`
  - `Q2TAC2`
  - `Q9NZD4`

That is precisely the kind of operator view that is missing today.

## What The New Surface Should Do

The proposed surface should give one row per protein accession in the current lightweight library and answer:

- is the protein summary present
- how many variant rows exist for that protein
- how many structure-unit rows exist for that protein
- how many motif/domain/pathway/provenance references are visible on the protein summary row
- whether the current bundle manifest includes each relevant family
- what the next smallest operator action is

This is enough to make the current library actionable without introducing ligands, interactions, similarity signatures, or packet logic into the operator layer yet.

## Proposed Minimal Row Shape

Each row should contain:

- `accession`
- `protein_name`
- `protein_summary_present`
- `variant_count`
- `structure_unit_count`
- `motif_reference_count`
- `domain_reference_count`
- `pathway_reference_count`
- `provenance_pointer_count`
- `family_presence`
  - `proteins`
  - `protein_variants`
  - `structures`
- `bundle_projection`
  - `manifest_includes_proteins`
  - `manifest_includes_protein_variants`
  - `manifest_includes_structures`
- `next_operator_action`
- `operator_priority`
- `truth_note`

## Concrete Examples From The Current Repo State

### `P00387`

Grounded in [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json):

- protein summary present
- motif refs: `1`
- domain refs: `9`
- pathway refs: `0`
- provenance refs: `1`
- variant rows: `0`
- structure-unit rows: `0`

Operator interpretation:

- useful protein-only summary exists
- no current variant or structure slice
- next action is not bundle validation or duplicate cleanup
- next action is to keep this visible as `protein_only_current_slice`

### `P04637`

Grounded in [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json) and [protein_variant_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_variant_summary_library.json):

- protein summary present
- motif refs: `1`
- domain refs: `13`
- pathway refs: `124`
- provenance refs: `3`
- variant rows: `1439`
- structure-unit rows: `0`

Operator interpretation:

- this is the clearest current example of `variant-rich but structure-missing`
- next operator action should be `structure_followup_candidate`

### `P68871`

Grounded in [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json), [protein_variant_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_variant_summary_library.json), and [structure_unit_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_unit_summary_library.json):

- protein summary present
- motif refs: `1`
- domain refs: `10`
- pathway refs: `0`
- provenance refs: `1`
- variant rows: `263`
- structure-unit rows: `2`

Operator interpretation:

- this is the clearest current `integrated visible slice` example
- next operator action is not rescue; it is `reference_example_keep_visible`

### `P69905`

- protein summary present
- variant rows: `149`
- structure-unit rows: `2`
- pathway refs: `18`

Operator interpretation:

- another good `fully visible current slice` example
- useful for operator demos and future bundle examples

## Why This Is Better Than The Other Small Options

This is better than another count-only status surface because:

- the counts already exist
- the missing question is per-accession, not per-family total

This is better than adding ligands or interactions to operator right now because:

- those families are not yet visible in the live lightweight bundle surfaces
- the proposal should build on what is already real

This is better than extending duplicate cleanup into the operator biology view because:

- duplicate cleanup is storage safety and reclaimability
- accession coverage is biological/operator triage
- mixing them now would reduce clarity

## Expected Operator Value

This one new surface would let the operator:

- see which accessions are only protein-level
- see which accessions are variant-rich but structure-missing
- identify the best current demo/reference accessions
- choose the next narrow materialization or rescue target without opening three separate library artifacts

## Input Surfaces

The smallest truthful version of this surface only needs:

- [protein_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_summary_library.json)
- [protein_variant_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/protein_variant_summary_library.json)
- [structure_unit_summary_library.json](/D:/documents/ProteoSphereV2/artifacts/status/structure_unit_summary_library.json)
- [lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)
- [live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json)

Optional read-only context:

- [duplicate_cleanup_executor_status.json](/D:/documents/ProteoSphereV2/artifacts/status/duplicate_cleanup_executor_status.json)

## Explicit Exclusions

The proposed addition should not:

- compute new biological joins
- infer ligand or interaction families that are not materialized
- decide release readiness
- mutate bundle manifests
- trigger duplicate cleanup actions

## Bottom Line

The next smallest useful operator-facing addition is not another count surface.

It is a single accession-level coverage matrix that joins the already-visible protein, variant, and structure-unit slices into one operator readout. That is the minimum addition that turns current visibility into immediate triage value.

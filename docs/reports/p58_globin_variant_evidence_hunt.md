# P58 Globin Variant Evidence Hunt

Report-only evidence hunt for whether `P68871` and `P69905` can support a first truthful `protein_variant` slice from already-local artifacts.

## Truth Boundary

- This note is report-only.
- It does not authorize code changes or publication.
- It checks whether the local evidence already supports a narrow accession-first protein_variant slice.

## Question

Can `P68871` and `P69905` support a first truthful protein_variant slice from already-local artifacts?

## Verdict

Yes. A narrow accession-first slice is supportable from the local UniProt payloads alone, and `P68871` also has mirrored IntAct mutation evidence.

Support summary:

- `P68871` is strongly supported by local UniProt variant features plus mirrored IntAct mutation rows.
- `P69905` is supported by local UniProt variant features even without mirrored IntAct mutation rows.

## Current Local Evidence

### P68871

- Local UniProt JSON contains `261` `Natural variant` features out of `325` total features.
- Local UniProt text includes explicit `FT VARIANT` annotations and named hemoglobin variant references.
- Mirrored IntAct `mutation.tsv` contains `31` matching rows for `P68871`.

### P69905

- Local UniProt JSON contains `151` `Natural variant` features out of `213` total features.
- Local UniProt text includes explicit `FT VARIANT` annotations and named hemoglobin variant references.
- Mirrored IntAct `mutation.tsv` does not contain matching rows for `P69905`, but that does not block a truthful first slice because the UniProt payload already carries explicit variant evidence.

## Slice Boundaries

The evidence supports an accession-first first slice with these kinds:

- `natural_variant`
- `point_mutation`
- `small_indel`
- `isoform_variant`

What stays out of scope for now:

- construct-only records without explicit local construct labels
- name-only inference
- broad accession coverage beyond this two-accession globin hunt

## Field Support

- `protein_ref`: supported
- `parent_protein_ref`: supported
- `variant_signature`: supported
- `variant_kind`: supported for the narrow slice kinds above
- `mutation_list`: supported
- `sequence_delta_signature`: supported
- `construct_type`: not yet supported
- `is_partial`: should remain true whenever any anchor is incomplete

## Operator Note

If the next step is a protein_variant materializer, `P68871` is the safest starting point because it has both local UniProt evidence and mirrored IntAct mutation support. `P69905` is still truthful to include, but it is grounded by the local UniProt payloads rather than the mirrored mutation export.

## Validation Gates

Passed:

- Both accessions exist in the current protein summary library.
- Both accessions have explicit local UniProt variant features.
- `P68871` has mirrored IntAct mutation rows already local.

Needs attention:

- Construct support remains deferred.
- The slice should stay accession-first and fail closed on name-only claims.

## Bottom Line

The local artifacts are enough to support a first truthful protein_variant slice for `P68871` and `P69905`. The cleanest operator stance is to start narrow, keep `construct_type` deferred, and treat `P68871` as the higher-confidence accession because it has both UniProt and IntAct support.

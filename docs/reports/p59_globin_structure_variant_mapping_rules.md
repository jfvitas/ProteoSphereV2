# P59 Globin Structure Variant Mapping Rules

Report-only proposal for the first truthful structure-backed variant mapping rules on the current globin overlap surfaces.

## Truth Boundary

- This note is report-only.
- It does not authorize code changes or publication.
- It checks the current globin structure/variant overlap surfaces and proposes rules that stay inside the current evidence boundary.

## What Is Current

The current overlap is accession-level, not yet direct join-level.

- `P68871` has 263 materialized protein_variant rows and 2 structure-unit rows.
- `P69905` has 149 materialized protein_variant rows and 2 structure-unit rows.
- All four globin structure-unit rows still have `variant_ref = null`.

That means the surfaces overlap on accession, but the structure side is still variant-agnostic.

## Proposed First Truthful Rules

1. Require an exact accession match between `protein_variant.protein_ref` and `structure_unit.protein_ref`.
2. Require an explicit `variant_signature` on the protein_variant row.
3. Treat a structure-unit row as joinable only when `variant_ref` is explicit on the structure side.
4. If `variant_ref` is null, keep the row as `candidate_only` or `blocked_no_variant_anchor`.
5. If a structure-backed join is emitted later, require the structure-unit residue span to cover the claimed variant residue.
6. Do not infer variant support from globin family membership, PDB code, or accession overlap alone.

## Globin Cases

### P68871

- Variant evidence exists locally.
- Structure evidence exists locally.
- The current structure-unit rows are still `variant_ref = null`.

Operator status: `candidate_only_no_variant_anchor`

Truth note: P68871 is a strong pilot accession for a future bridge, but it is not yet a truthful direct structure-backed variant join.

### P69905

- Variant evidence exists locally.
- Structure evidence exists locally.
- The current structure-unit rows are still `variant_ref = null`.

Operator status: `candidate_only_no_variant_anchor`

Truth note: P69905 is also a valid pilot accession, but the current structure surface does not yet name a variant anchor.

## Allowed And Not Allowed

Allowed now:

- `accession_overlap_candidate`
- `structure_unit_anchor_present`
- `protein_variant_anchor_present`

Not allowed now:

- `direct_structure_backed_variant_join`
- `variant_ref_inferred`
- `chain_equals_variant_claim`

## Bottom Line

Use `P68871` and `P69905` as the globin pilot accessions for a future structure-backed variant bridge, but keep the current status at candidate-only until the structure side carries an explicit variant anchor.

# P76 Bundle Next Family Ranking

This is a report-only ranking note for the next three safest bundle-facing families after dictionaries, leakage groups, and protein similarity.

## Current Bundle Truth

The current lightweight bundle is still a verified preview:

- `bundle_kind = debug_bundle`
- `packaging_layout = compressed_sqlite`
- `bundle_budget_class = A`
- `bundle_compressed_size_bytes = 265356`
- `operator_go_no_go = no-go`
- `release_grade_status = blocked_on_release_grade_bar`

Live validation says the current preview slices are aligned, including:

- proteins
- protein variants
- structure units
- protein similarity signatures
- dictionaries
- structure similarity signatures
- leakage groups

## Ranked Families

1. `structure_similarity_signatures`

This is the safest first family because it is already materialized and already aligned. It is compact, validated, and directly grounded in the four current structure rows.

2. `structure_followup_payloads`

This is the safest next preview surface because it is narrow and explicit: only `P31749` and `P04637`, both still candidate-only, both still requiring an explicit structure-side `variant_ref` before promotion.

3. `ligand_support_readiness`

This is the safest ligand-adjacent family because it stays support-only, keeps `Q9UCM0` deferred, and does not materialize ligand rows or change bundle inclusion today.

## Why This Order

The order is conservative:

- keep the already-materialized similarity family first
- keep the next structure family narrow and candidate-only
- keep the ligand family support-only until real ligand rows exist

That gives operators useful surfaces without widening the bundle faster than the evidence supports.

## Explicit Deferrals

Still deferred beyond the top three:

- interaction-family materialization
- ligand similarity signatures
- direct structure-backed variant join promotion
- release-grade promotion
- protected latest surface rewrites

## Boundary

This note is report-only. It does not edit code, does not rewrite protected latest surfaces, and does not claim release readiness. Only the first-ranked family is already materialized; the other two remain preview/support surfaces.

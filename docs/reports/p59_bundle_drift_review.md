# P59 Bundle Drift Review

Report-only drift review for the `proteosphere-lite` bundle contents and schema docs against the live manifest.

## What Was Compared

- Contents doc: `docs/reports/proteosphere-lite.contents.md`
- Schema doc: `docs/reports/proteosphere-lite.schema.md`
- Live manifest: `artifacts/status/lightweight_bundle_manifest.json`
- Live validation: `artifacts/status/live_bundle_manifest_validation.json`

## What Matches

- `proteins` is `11` everywhere.
- `protein_variants` is `1874` everywhere.
- `structures` is `4` everywhere.
- Live validation reports `aligned_current_preview`.

This is a count-alignment case, not a numeric drift case.

## Wording Risks

### Protein Variants

The contents doc says `protein_variants is declared for schema v2 but not yet populated`, but the same bundle stack already reports `1874` protein_variant records and the schema doc treats that family as included.

That sentence is the main drift risk. A reader could wrongly conclude that the protein_variant surface is still empty when it is already populated in the current preview slice.

### Preview Completeness

The docs correctly say the numbers are current live counts and not completeness claims, but the repeated tables can still read like a complete bundle inventory if the caveats are skipped.

### Reserved Families

Ligands, interactions, similarity signatures, leakage groups, and dictionaries are consistently reserved or zero-count across the manifest and schema doc. Those omissions are deliberate and truthful, but they should be read as not-yet-materialized surfaces rather than accidental gaps.

### Source Coverage

The manifest reports `48` present sources, `2` partial sources, and `3` missing sources. The human docs do not enumerate which sources fall into each bucket, so a user may overread the bundle as more complete than it is.

## Operator Read

The bundle is current and aligned on its emitted slices, but the contents doc needs one wording fix to avoid misleading users about `protein_variants`. Keep the preview/unverified framing attached to all count tables until a release-grade manifest exists.

## Recommendation

Revise the contents doc so it describes `protein_variants` as populated in the current preview slice, not as “not yet populated,” and preserve the completeness caveats wherever the record counts are shown.

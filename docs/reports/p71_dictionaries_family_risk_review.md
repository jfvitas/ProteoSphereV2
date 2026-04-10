# P71 Dictionaries Family Risk Review

## Objective

Review the truth-boundary and size-budget risks of adding a compact `dictionaries` family to the current preview bundle.

Grounding:

- [p36_storage_dedupe_safety_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p36_storage_dedupe_safety_contract.json)
- [p50_duplicate_cleanup_staging_map.json](/D:/documents/ProteoSphereV2/artifacts/status/p50_duplicate_cleanup_staging_map.json)
- [p51_bundle_manifest_budget_contract.json](/D:/documents/ProteoSphereV2/artifacts/status/p51_bundle_manifest_budget_contract.json)
- [p61_preview_bundle_growth_guardrails.json](/D:/documents/ProteoSphereV2/artifacts/status/p61_preview_bundle_growth_guardrails.json)
- [p60_bundle_size_expansion_forecast.json](/D:/documents/ProteoSphereV2/artifacts/status/p60_bundle_size_expansion_forecast.json)
- [live_bundle_manifest_validation.json](/D:/documents/ProteoSphereV2/artifacts/status/live_bundle_manifest_validation.json)
- [lightweight_bundle_manifest.json](/D:/documents/ProteoSphereV2/artifacts/status/lightweight_bundle_manifest.json)

## Current State

The current bundle is still small and preview-scoped:

- `bundle_kind = debug_bundle`
- `packaging_layout = compressed_sqlite`
- compressed size is about `240929` bytes
- budget class is `A`
- `dictionaries.included = false`
- `dictionaries.record_count = 0`

The current live validated slices are:

- proteins
- protein variants
- structure units
- protein similarity signatures
- structure similarity signatures
- leakage groups

That matters because a `dictionaries` family would be a new family with no current live validation surface.

## Truth-Boundary Risks

### 1. Dictionaries would be truth-weak if nothing consumes them

Right now the preview does not need dictionaries to describe any current family.

The guardrails already say dictionaries should come last, because they are a packaging optimization rather than a core surface. If dictionaries are added now, the bundle would claim a new family without showing that any live slice actually depends on it.

### 2. Dictionaries could imply deferred coverage

This is the biggest truth risk.

Ligands and interactions are still absent from the preview bundle. If a new dictionaries family starts carrying normalized identifiers, labels, or compact encodings for those deferred families, the bundle would appear richer than it really is.

That would cross a truth boundary:

- dictionary rows are not a substitute for a live ligands family
- dictionary rows are not a substitute for a live interactions family

### 3. Validation would be incomplete

The live validation surface currently does not check any dictionary inventory or dictionary usage.

If dictionaries are added now:

- manifest truth would move ahead of validation truth
- the bundle would have a new family with no existing alignment check

### 4. Dictionaries need a clear derived-only role

The duplicate-cleanup rules are strict about role separation:

- `source_of_record`
- `mirror_copy`
- `derived_output`
- `run_manifest`

A future dictionaries family must be `derived_output`, not source coverage. If that role is not explicit, dictionaries could be misread as a source-truth layer instead of a compact lookup layer.

## Size-Budget Risks

### 1. Dictionaries may increase size before they reduce it

The current preview bundle is tiny. In a bundle this small, dictionary tables often add overhead:

- extra tables
- extra keys
- extra manifest references

That means dictionaries can make the bundle larger before there is enough repeated text to justify them.

### 2. They consume the provenance-and-dictionaries budget band

The budget contract allows only `10%` of the bundle for the combined provenance-and-dictionaries band.

Current preview state already includes a substantial provenance surface. If dictionaries are added too early, they can consume budget that would be better reserved for future high-cardinality families.

### 3. They add review churn early

The preview growth guardrails already require careful re-baselining after every family addition and use `1 MiB` compressed as an early review checkpoint.

Even if dictionaries do not threaten the hard cap, they increase complexity and review burden before they produce clear value.

## Duplicate Cleanup Implications

### Dictionaries must never dedupe against source-native raw files

The duplicate-cleanup safety contract prohibits collapsing distinct role classes together.

That means a future dictionaries family must never be treated as reclaimable against:

- raw source payloads
- source-of-record snapshots
- run manifests

### Dictionaries should be marked derived output immediately

If dictionaries are added later, they need a clear role:

- compact derived lookup layer
- not a raw mirror
- not a source-of-record replacement

Without that, future dedupe logic becomes ambiguous.

### Avoid multi-root duplicated dictionary payloads

The current duplicate staging map already shows large reclaimable mirror duplication in the raw layer. A new dictionaries family should not create more duplicated copies across:

- bundle assets
- report attachments
- auxiliary exported lookup files

One canonical bundle copy is enough.

## Net Assessment

Current assessment:

- truth-boundary risk: `high`
- size-budget risk: `medium`
- duplicate-cleanup risk: `medium` unless the role is explicit

Recommendation now:

- **defer adding `dictionaries`**

## Safe Conditions Before Reconsidering

Reconsider only when:

1. at least one high-cardinality live family exists that can actually benefit from dictionary coding
2. the dictionaries family is explicitly defined as `derived_output`
3. live validation can verify dictionary counts and usage
4. the manifest can say which families consume the dictionaries family
5. measured assets show a real compressed-size benefit or a clear scaling need

## Bottom Line

Adding a compact `dictionaries` family now is more likely to weaken bundle truth than to improve size. The preview bundle is still too small, the current live slices do not need dictionary coding, and the duplicate-cleanup model requires a derived-only role that the bundle has not yet established for dictionaries.

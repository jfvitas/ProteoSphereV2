# Release Artifact Hardening

Date: 2026-03-22
Task: `P6-I030`

## Findings

The release artifact surface is stronger now than it was before the leakage, coverage, and bundle fixes.

- The bundle manifest pins `schema.json` as a required release artifact.
- The source coverage artifact is explicitly conservative and says it is a coverage inventory, not release-grade corpus validation.
- The leakage audit remains accession-level clean with no cross-split accessions or leakage keys.

## What Is Now Stronger

1. The bundle contract is clearer.
   - `runs/real_data_benchmark/full_results/release_bundle_manifest.json` now distinguishes required release artifacts from supporting pins.
   - `schema.json` is marked as required, which prevents downstream readers from treating it as optional metadata.

2. The coverage artifact is safer to consume.
   - `runs/real_data_benchmark/full_results/source_coverage.json` now includes explicit semantics stating that it is a conservative source-coverage inventory.
   - Mixed-evidence rows are flagged conservatively instead of being flattened into a generic release-grade label.

3. The leakage audit still reads cleanly.
   - `runs/real_data_benchmark/full_results/leakage_audit.json` shows 12 rows, 12 unique accessions, 12 unique leakage keys, and no cross-split leakage.

## Remaining Audit-Specific Gaps

These gaps are still real and should remain visible in release-facing notes:

- The runtime is still the local prototype surface, not the production trainer stack.
- Source coverage depth remains thin for most accessions.
- The bundle is assembled with blockers, not release-grade closure.

## Release-Oriented Interpretation

The right way to read the current artifacts is:

- the cohort is pinned and leakage-clean,
- the coverage report is explicit but conservative,
- the bundle is launchable as a truthful artifact set,
- but the benchmark is still not a production-equivalent release claim.

That is the strongest honest interpretation supported by the current artifacts.

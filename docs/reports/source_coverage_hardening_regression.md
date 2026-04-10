# Source Coverage Hardening Regression

Date: 2026-03-22
Task: `P10-I014`

## Findings

No blocking issues were found in the hardened source-coverage path.

The source coverage generator still emits a conservative inventory:

- the frozen 12-accession cohort remains leakage-free and accession-level only,
- the verified-accession rows stay explicitly labeled as `verified_accession`,
- those rows remain `thin_coverage: true`,
- and the coverage artifact continues to declare `coverage_not_validation: true` and `release_grade_corpus_validation: false`.

That is the right behavior after the lane hardening tasks. The acquisition layer now has stronger supplemental routing available, but the coverage view should stay honest about what is actually represented in the frozen cohort and current benchmark artifact set.

## What Was Re-Emitted

The source-coverage generator was re-run against the current in-tree benchmark inputs and produced the same conservative structure as the checked-in coverage artifact, aside from the regenerated timestamp.

Stable fields that were revalidated:

- 12 total accessions
- 8/2/2 train/val/test split counts
- 3 direct live-smoke rows
- 1 probe-backed row
- 6 snapshot-backed rows
- 2 verified-accession rows
- no cross-split leakage

## Residual Gap

The verified-accession rows are still thin in the coverage view because the coverage report is a conservative inventory, not a promotion of acquisition-side supplemental lanes into release-grade validation.

That is intentional. The hardened lane acquisition path is useful, but the source-coverage artifact should remain a stable, cautious readout of the frozen cohort.

## Validation

Focused validation for the hardened semantics is:

- `python -m pytest tests/integration/test_source_coverage_hardening.py -q`
- `python -m ruff check scripts/emit_source_coverage.py tests/integration/test_source_coverage_hardening.py`
- `python scripts/emit_source_coverage.py --output <temp path>`

The regenerated source-coverage JSON should match the committed artifact modulo `generated_at`, and the hardened inventory semantics must stay fixed:

- `verified_accession` rows remain thin,
- `mixed_evidence_rows_are_conservative` stays true,
- split leakage stays empty,
- and the verified-accession lane depth remains single-lane.

This regression note is intentionally conservative so the coverage view does not drift into implying release-grade validation.

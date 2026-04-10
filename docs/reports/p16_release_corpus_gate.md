# P16 Release Corpus Gate

Date: 2026-03-22
Task: `P16-I008`
Status: `blocked`

## Verdict

The frozen 12-accession cohort is not RC-capable yet.

- `0/12` rows are release-ready.
- 0/12 rows are release-ready.
- `12/12` rows remain blocked in the emitted release corpus evidence ledger.
- The strongest row is `protein:P69905`, but it is still blocked by packet incompleteness and missing requested modalities.

## Why The Gate Stays Closed

- packet materialization is still partial for all 12 rows
- ligand depth is still missing or only bridge-linked for most of the cohort
- thin coverage still dominates the long tail of the benchmark cohort
- one accession still carries an explicit PPI gap even after the curated slice uplift

## Release Interpretation

- This is an evidence-backed blocked gate, not a failed integration.
- The registry, wave plans, and ledger are now pinned and reproducible.
- Phase 17 should treat this as an evidence-backed blocked gate and build the scientific library on top of it without pretending the corpus is already release-grade.

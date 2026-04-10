# Release Stabilization Regression

Date: 2026-03-22
Task: `P7-I005`

## Gate Check

Both prerequisites were green before the sweep:

- `P7-T001` hardened source-release manifest identity assertions
- `P7-T002` AlphaFold invalid-manifest expectation drift resolution

## Focused Sweep

Executed exactly the release-stabilization slice from the prep note:

- `python -m pytest tests\unit\execution\test_acquire_biogrid_snapshot.py tests\unit\execution\test_acquire_disprot_snapshot.py tests\unit\execution\test_acquire_emdb_snapshot.py tests\unit\execution\test_acquire_intact_snapshot.py tests\unit\execution\test_acquire_reactome_snapshot.py tests\unit\execution\test_ingest_sequences.py tests\unit\execution\test_protein_index.py tests\unit\execution\test_supplemental_scrape_registry.py tests\integration\test_procurement_hardening.py -q`
- `python -m ruff check tests\unit\execution\test_acquire_biogrid_snapshot.py tests\unit\execution\test_acquire_disprot_snapshot.py tests\unit\execution\test_acquire_emdb_snapshot.py tests\unit\execution\test_acquire_intact_snapshot.py tests\unit\execution\test_acquire_reactome_snapshot.py tests\unit\execution\test_ingest_sequences.py tests\unit\execution\test_protein_index.py tests\unit\execution\test_supplemental_scrape_registry.py tests\integration\test_procurement_hardening.py`

## What Passed

- All 36 pytest cases passed in the focused sweep.
- Ruff passed cleanly on the swept files.
- The hardened source-release manifest identity contract stayed aligned with the assertions in the acquisition, ingest, indexing, and supplemental scrape registry tests.
- AlphaFold invalid-manifest handling remained explicit in the procurement hardening path and did not fall back to a silent or unrelated record.

## What Still Fails

No failures were observed in the focused stabilization slice.

## Remaining Repo-Wide Issues

This sweep is intentionally not a repo-wide certification. The following remain outside the release slice and were not revalidated here:

- broader integration paths outside `test_procurement_hardening.py`
- operator-visibility hardening, which was not explicitly included in this sweep window
- unrelated repo areas that may still have their own open work or regressions

## Bottom Line

The release-stabilization regression sweep passes for the hardened procurement and manifest-identity slice. The report is intentionally bounded and does not claim full repository stability.

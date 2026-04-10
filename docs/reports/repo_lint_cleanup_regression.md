# Repo Lint Cleanup Regression

Date: 2026-03-22
Task: `P8-I005`

## Verdict

The cleaned P8 slice is green, but the repo-wide lint sweep is **not** fully clean yet.

## What Is Green

- `core/storage/package_manifest.py`
- `execution/materialization/package_builder.py`
- `execution/materialization/selective_materializer.py`
- `execution/storage_runtime.py`
- The cleaned P8 unit-test slice that was previously stabilized remains lint-clean under `ruff`.

Focused command result:

- `python -m ruff check core\storage\package_manifest.py execution\materialization\package_builder.py execution\materialization\selective_materializer.py execution\storage_runtime.py tests\unit\execution\test_acquire_biogrid_snapshot.py tests\unit\execution\test_acquire_disprot_snapshot.py tests\unit\execution\test_acquire_emdb_snapshot.py tests\unit\execution\test_acquire_intact_snapshot.py tests\unit\execution\test_acquire_reactome_snapshot.py tests\unit\execution\test_ingest_sequences.py tests\unit\execution\test_protein_index.py tests\unit\execution\test_supplemental_scrape_registry.py`
- Result: passed cleanly

## Remaining Lint Debt

The repo-wide `ruff` sweep still reports pre-existing debt outside the cleaned P8 slice:

- `tests/unit/execution/test_package_builder.py:156`
- `tests/unit/execution/test_selective_materializer.py:159`

Both failures are line-length issues (`E501`), and they are outside the owned P8 cleanup slice. They do not change the fact that the cleaned storage/materialization slice is now lint-clean.

Repo-wide command result:

- `python -m ruff check .`
- Result: failed on the two issues above

## Bottom Line

The release-cleaned P8 slice is stable and lint-clean, but the repository still has lint debt elsewhere in older execution tests. This regression note is intentionally bounded to that truth boundary and does not claim full repo-wide cleanup.

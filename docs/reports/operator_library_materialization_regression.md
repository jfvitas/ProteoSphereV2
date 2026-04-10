# Operator Library Materialization Regression

Date: 2026-03-22
Scope: `P11-I006`

## What Was Revalidated

The operator snapshot contract now has a truthful materialized-library branch and still fails closed when the library artifact is absent.

- When no materialized summary-library artifact exists, `library.materialized` stays `false` and the artifact-backed fields remain empty or null.
- When a real `summary_library.json` is present in the benchmark results tree, the PowerShell snapshot surfaces it as a concrete artifact with `materialized_path`, `materialized_library_id`, `materialized_source_manifest_id`, `materialized_record_count`, and `materialized_record_types`.
- The validator checks the same artifact-backed fields and rejects drift instead of inventing values.

## Test Coverage Added

[`tests/integration/test_operator_state_snapshot.py`](/D:/documents/ProteoSphereV2/tests/integration/test_operator_state_snapshot.py) now covers both sides of the contract:

1. The copied benchmark fixture tree has no materialized summary-library file, so the smoke test confirms the absent case remains explicit.
2. A synthetic but real `summary_library.json` is written into the temp benchmark results tree, and the smoke test confirms the operator and validator both expose the materialized artifact fields.

## Truth Boundary

This regression does not claim the live benchmark tree already contains a materialized summary library. It only proves the operator surface is ready to report one truthfully when the file exists, and to stay explicit when it does not.

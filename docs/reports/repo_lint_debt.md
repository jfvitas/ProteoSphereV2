# Repo Lint Debt

Date: 2026-03-22  
Task: `P7-A004`  
Scope: full `ruff` sweep of the repository

## Snapshot

The full `ruff check .` sweep surfaced **50 findings**:

- `E501` line-too-long: 45
- `F401` unused-import: 2
- `I001` unsorted-imports: 1
- `UP017` datetime.UTC alias: 2

The debt is concentrated in the currently active release / materialization surface and its validation tests. I did **not** find a clearly unrelated lint pocket outside that area in this sweep.

## Release-Slice / Newly Active Debt

These are the highest-signal files to clean next because they sit on the current benchmark / materialization path.

- [features/ppi_representation.py](D:/documents/ProteoSphereV2/features/ppi_representation.py#L208) has the largest cluster with 22 `E501` hits, starting at line 208.
- [execution/materialization/selective_materializer.py](D:/documents/ProteoSphereV2/execution/materialization/selective_materializer.py#L15) has 8 hits, including an unused import at line 15 and multiple long lines later in the file.
- [execution/materialization/package_builder.py](D:/documents/ProteoSphereV2/execution/materialization/package_builder.py#L15) has 3 hits, including the same unused selective-materializer import at line 15.
- [datasets/multimodal/adapter.py](D:/documents/ProteoSphereV2/datasets/multimodal/adapter.py#L740) has 1 long line at 740.
- [execution/storage_runtime.py](D:/documents/ProteoSphereV2/execution/storage_runtime.py#L176) has 1 long line at 176.

## Validation Debt Adjacent To The Release Slice

The test surface also has a few visible lint issues:

- [tests/unit/datasets/test_multimodal_adapter.py](D:/documents/ProteoSphereV2/tests/unit/datasets/test_multimodal_adapter.py#L1) has an import-order issue plus long lines and `datetime.UTC` cleanup around lines 205, 260, 264, and 363.
- [tests/integration/test_training_package_materialization.py](D:/documents/ProteoSphereV2/tests/integration/test_training_package_materialization.py#L149) has 3 long lines around 149, 150, and 217.
- [tests/integration/test_storage_runtime.py](D:/documents/ProteoSphereV2/tests/integration/test_storage_runtime.py#L151) has 2 long lines at 151-152.
- [tests/unit/execution/test_package_builder.py](D:/documents/ProteoSphereV2/tests/unit/execution/test_package_builder.py#L156) has 1 long line at 156.
- [tests/unit/execution/test_selective_materializer.py](D:/documents/ProteoSphereV2/tests/unit/execution/test_selective_materializer.py#L159) has 1 long line at 159.

## Lower-Priority Core/Support Debt

- [core/storage/package_manifest.py](D:/documents/ProteoSphereV2/core/storage/package_manifest.py#L275) has 2 long lines at 275 and 280.

## Next Cleanup Order

1. Fix the `features/ppi_representation.py` line-length cluster first. It is the largest single debt pocket and likely cheapest to reduce in bulk.
2. Tackle `execution/materialization/selective_materializer.py` and `execution/materialization/package_builder.py` together, since they share the same release slice and one unused import is already flagged.
3. Clean `datasets/multimodal/adapter.py` and `tests/unit/datasets/test_multimodal_adapter.py` next so the adapter and its regression coverage stay in sync.
4. Finish the smaller runtime/support/test leftovers in `execution/storage_runtime.py`, `tests/integration/test_storage_runtime.py`, and `tests/integration/test_training_package_materialization.py`.

## Evidence

- Full sweep command: `python -m ruff check . --output-format json`
- Sweep total: 50 findings
- Top file counts came from the active benchmark / materialization surface rather than unrelated repo areas.

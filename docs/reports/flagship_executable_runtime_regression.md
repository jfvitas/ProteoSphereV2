# Flagship Executable Runtime Regression

The flagship path remains truthful after `P11-T001` and `P11-T002`.

## Verified

- The pipeline still runs end to end from storage runtime through training, fusion, uncertainty, metrics, and the experiment registry.
- The registry now exposes executable runtime identity instead of collapsing everything to the old prototype-only shape.
- Runtime checkpoint resume is identity-safe: the test confirms checkpoint ref, processed example IDs, processable example IDs, dataset signature, and feature-bundle signature stay stable across resume.
- Resume fails closed when runtime identity changes. In the regression run, a changed feature-bundle payload was rejected with a `run_id` mismatch before any continuation occurred.
- The pipeline remains conservative at the top level. It still records the runtime truth in provenance while keeping the outer flagship view partial rather than overstating readiness.

## Notes

- The executable runtime still uses the local prototype backend, so this is not a release-grade trainer claim.
- The pipeline test intentionally keeps the top-level result partial, but the executable runtime provenance is visible in both the training status payload and the experiment registry record.

## Checks

- `python -m py_compile tests\integration\test_flagship_pipeline.py`
- `python -m ruff check tests\integration\test_flagship_pipeline.py`
- `python -m pytest tests\integration\test_flagship_pipeline.py -q`


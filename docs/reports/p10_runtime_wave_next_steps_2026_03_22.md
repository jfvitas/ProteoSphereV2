# P10 Runtime Wave Next Steps

Date: 2026-03-22

## Bottom Line

`P10-T005` is the right place to land the surrogate-input runtime work first. The next three cuts should be:

1. make the runtime stateful and checkpoint-safe,
2. make `training/multimodal/train.py` a thin executable entrypoint,
3. wire the flagship pipeline and experiment registry to the executable runtime shape.

That sequence matches the current repo state: `training/multimodal/runtime.py` already exists, the checkpoint store already supports explicit versions, and the flagship pipeline still consumes the plan-only training contract.

## P10-T006

### Goal

Turn `training/multimodal/runtime.py` into the authoritative runtime checkpoint path:

- keep the real example cursor,
- persist and reload checkpoint state cleanly,
- preserve feature-bundle provenance and resume identity,
- stop depending on surrogate-only assumptions for continuation.

### Owner Modules

- `training/multimodal/runtime.py`
- `execution/checkpoints/store.py`
- `tests/unit/training/test_multimodal_runtime.py`

### Likely Failure Points

- resume tails drift if example order changes,
- checkpoint schema diverges from the runtime state shape,
- feature-bundle signatures fail to round-trip,
- processed-example counts and `phase` values become inconsistent after resume,
- `checkpoint_ref` / `checkpoint_tag` lose identity stability.

### Validation Commands

```powershell
python -m pytest tests\unit\training\test_multimodal_runtime.py
python -m ruff check training\multimodal\runtime.py execution\checkpoints\store.py tests\unit\training\test_multimodal_runtime.py
```

## P10-T007

### Goal

Convert `training/multimodal/train.py` from a contract planner into a thin executable entrypoint that delegates to the runtime and only emits blockers when the backend is genuinely unavailable.

### Owner Modules

- `training/multimodal/train.py`
- `tests/unit/training/test_multimodal_train.py`

### Likely Failure Points

- the public training result shape drifts from the runtime result shape,
- plan-only blocker semantics get lost or duplicated,
- checkpoint metadata stops matching the runtime checkpoint,
- the entrypoint accidentally hard-codes prototype behavior instead of delegating.

### Validation Commands

```powershell
python -m pytest tests\unit\training\test_multimodal_train.py tests\unit\training\test_multimodal_runtime.py
python -m ruff check training\multimodal\train.py tests\unit\training\test_multimodal_train.py tests\unit\training\test_multimodal_runtime.py
```

## P10-T008

### Goal

Wire `execution/flagship_pipeline.py` and `training/runtime/experiment_registry.py` to the executable runtime result so pipeline identity, checkpoint lineage, and registry records are based on the actual runtime surface.

### Owner Modules

- `execution/flagship_pipeline.py`
- `training/runtime/experiment_registry.py`
- `tests/integration/test_flagship_pipeline.py`
- `tests/unit/training/test_experiment_registry.py`

### Likely Failure Points

- `experiment_id` stays tied to blocked-plan fingerprints instead of runtime identity,
- registry/checkpoint references stop matching the runtime checkpoint path,
- pipeline status becomes overly optimistic or drops blocker details,
- GPU policy and registry wiring diverge from the runtime result shape,
- integration tests still only prove the contract path, not the executable path.

### Validation Commands

```powershell
python -m pytest tests\unit\training\test_experiment_registry.py tests\integration\test_flagship_pipeline.py
python -m ruff check execution\flagship_pipeline.py training\runtime\experiment_registry.py tests\unit\training\test_experiment_registry.py tests\integration\test_flagship_pipeline.py
```

## Recommended Order

1. Finish `P10-T006` first so runtime resume is truthful and durable.
2. Land `P10-T007` next so callers use the executable path by default.
3. Land `P10-T008` last so the flagship pipeline and registry consume the final runtime shape instead of the contract-only planner.

## What To Watch Closely

- keep surrogate-vs-real runtime boundaries explicit until the real trainer exists,
- keep checkpoint identity stable across resume and reordered inputs,
- keep the pipeline honest about partial or blocked status if the runtime still cannot execute a true training loop.

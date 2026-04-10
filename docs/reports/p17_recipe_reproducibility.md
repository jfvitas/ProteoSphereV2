# P17 Recipe Reproducibility

Date: 2026-03-22  
Task: `P17-I008`

## Verdict

The pinned dataset recipe replay is **deterministic** for the frozen benchmark slice.

Using the benchmark cohort manifest together with the release corpus evidence ledger, the replay recipe reproduces the same 12 accessions, the same `8 / 2 / 2` split layout, and the same leakage-safe boundaries when evaluated in forward or reversed candidate order.

## What Was Proven

- The recipe round-trips through `TrainingRecipeSchema.to_dict()` / `from_dict()` without losing semantics.
- Replay from pinned inputs yields the expected accession-level split decisions.
- Reversing the candidate order does not change the result.
- Explicit blocker information from the corpus ledger stays attached to the replay inputs.
- Leakage collisions remain explicit if the replay inputs are perturbed.

## What Remains Explicit

- `P68871` remains probe-backed and mixed.
- `P04637` remains a thin single-lane PPI anchor.
- `P31749` remains ligand-linked only.
- The replay recipe validates the frozen benchmark slice, not a general recipe synthesis engine.

## Evidence Used

- [cohort_manifest.json](D:/documents/ProteoSphereV2/runs/real_data_benchmark/cohort/cohort_manifest.json)
- [release_corpus_evidence_ledger.json](D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/release_corpus_evidence_ledger.json)
- [test_recipe_reproducibility.py](D:/documents/ProteoSphereV2/tests/integration/test_recipe_reproducibility.py)

## Verification

- `python -m pytest tests\\integration\\test_recipe_reproducibility.py -q`
- `python -m ruff check tests\\integration\\test_recipe_reproducibility.py`

## Integration Read

This is the right reproducibility boundary for the current queue: the recipe can replay the frozen cohort faithfully and keep leakage explicit, but it should still be read as a benchmark-slice replay, not as proof that arbitrary new recipes or broader corpora are ready.

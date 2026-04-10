# Model Studio V1 Execution Guide

## Purpose
This guide describes the current executable vertical slice for the ProteoSphereV2 Model Studio. The goal of this wave is not full breadth. It is one honest end-to-end path for protein-binding studies that can be drafted in the GUI, compiled into a deterministic execution graph, launched, and reviewed with persisted artifacts.

## Executable V1 Scope
- Task type: `protein-protein`
- Label type: `delta_G`
- Split strategy: `leakage_resistant_benchmark`
- Default runnable dataset: `expanded_pp_benchmark_v1`
- Structure policy: `experimental_preferred_predicted_fallback` in the spec, but current runnable preprocessing uses local experimental structures only
- Graph recipes: `interface_graph` and `hybrid_graph` are supported in the Studio contract; the runnable path materializes interface-centered residue graphs plus graph-summary features
- Training backends available now:
  - `xgboost` -> `sklearn-hist-gradient-boosting-adapter`
  - `catboost` -> `sklearn-random-forest-adapter`
  - `mlp` -> `sklearn-mlp-regressor`
  - `multimodal_fusion` -> `sklearn-mlp-fusion-adapter`
  - `graphsage` and `gin` -> lightweight torch graph adapter

## End-to-End Flow
1. Open the Studio web app.
2. Select or edit a pipeline draft.
3. Save the draft.
4. Validate the draft and review blockers/warnings.
5. Compile the draft into an execution graph.
6. Launch a Studio run.
7. Inspect stage status in the Execution Console.
8. Inspect metrics, outliers, and recommendations in Analysis and Review.

## Runtime Artifacts
Each run writes to:

`artifacts/runtime/model_studio/runs/<run_id>/`

Expected artifacts:
- `run_manifest.json`
- `execution_graph.json`
- `stage_status.json`
- `canonical_examples.json`
- `split_summary.json`
- `structure_materialization.json`
- `feature_index.json`
- `training_examples.json`
- `packaging_manifest.json`
- `metrics.json`
- `outliers.json`
- `recommendations.json`
- `logs.json`
- `artifacts.json`
- `report.md`

## Stage Semantics
The current deterministic execution graph uses these stages:
1. `source_selection`
2. `canonical_identity_resolution`
3. `split_compilation`
4. `structure_acquisition_materialization`
5. `feature_extraction_materialization`
6. `graph_construction`
7. `training_example_assembly`
8. `train_val_test_packaging`
9. `model_training`
10. `evaluation_and_comparison`
11. `report_export`

Each stage emits:
- `status`
- `adapter_status`
- `detail`
- `artifact_refs`
- `blockers`
- `updated_at`

## Honest Adapter Policy
The Studio does not silently fake unsupported modules.

Rules:
- If a requested module is runnable in this environment, `adapter_status = runnable`
- If a requested module is catalog-visible but not executable in this environment, `adapter_status = blocked_or_stubbed`
- Blocked modules stay visible in the GUI and recommendation payloads

## Current Runnable Data/Feature Path
The executable path currently performs:
- dataset selection from known corpora
- CSV-driven split loading
- local structure presence checks
- PDB parsing
- residue centroid generation
- interface contact detection
- salt-bridge proxy counting
- hydrogen-bond proxy counting
- water-contact proxy counting
- interface graph generation
- tabular + graph-summary feature packaging

## Current Evaluation Outputs
Completed runs produce:
- train/test metrics
- residual-ranked outliers
- leakage summary
- backend resolution summary
- publishable markdown report

## What To Use For Team Demos
Use the default pipeline:
- `pipeline:protein-binding-default-v1`

Recommended demo story:
1. Open default draft
2. Show recommendation warnings
3. Compile graph
4. Launch run
5. Open latest completed run
6. Inspect metrics and outliers
7. Show artifact/log transparency

## Known Limits
- `xgboost` and `catboost` are adapter-backed via currently available sklearn backends
- `cnn`, `unet`, `heterograph`, `PyRosetta`, and `AlphaFold-derived support` remain catalog-visible but not yet fully executable in the Studio runtime
- current structure preprocessing is local-asset dependent
- current graph-native path is lightweight and intended for a truthful v1 slice, not final benchmark SOTA claims

## Next Recommended Build Targets
- richer recommendation engine categories
- run comparison UI polish
- artifact drill-down per stage
- stronger graph recipe previewing
- real portfolio/ablation launch controls from the GUI
- broader execution adapters for advanced preprocessing lanes

# Model Studio Internal Expert Pilot Summary

## Status

The Model Studio now supports a real **study-builder** workflow for the internal expert pilot:

- define a protein-protein training-set request
- preview a candidate structure-backed dataset
- build a concrete study dataset with train/val/test CSVs
- compile a stage-based execution graph
- materialize graph/global/distributed example bundles
- launch released model families
- inspect metrics, outliers, split diagnostics, and study summary information in the GUI

## What Is Now Runnable

- task type: `protein-protein`
- label type: `delta_G`
- structure policy: `experimental_only`
- graph kinds:
  - `interface_graph`
  - `residue_graph`
  - `hybrid_graph`
- preprocessing modules:
  - `PDB acquisition`
  - `chain extraction and canonical mapping`
  - `waters`
  - `salt bridges`
  - `hydrogen-bond/contact summaries`
- model families:
  - `xgboost-like (HistGradientBoosting)`
  - `catboost-like (RandomForest)`
  - `mlp`
  - `fusion_mlp_adapter`
  - `graphsage-lite`

## Review and Verification Evidence

- focused unit tests: `8 passed`
- lint: `ruff` clean
- API smoke:
  - [api_smoke_round_3.json](/D:/documents/ProteoSphereV2/artifacts/reviews/model_studio_internal_alpha/pilot_round_1/api_smoke_round_3.json)
- study-builder execution matrix:
  - [study_builder_matrix.json](/D:/documents/ProteoSphereV2/artifacts/reviews/model_studio_internal_alpha/pilot_round_1/study_builder_matrix.json)
- browser pilot traces:
  - [pilot_trace.json](/D:/documents/ProteoSphereV2/artifacts/reviews/model_studio_internal_alpha/pilot_round_1/pilot_trace.json)
  - [pilot_trace.json](/D:/documents/ProteoSphereV2/artifacts/reviews/model_studio_internal_alpha/pilot_round_2/pilot_trace.json)
- browser screenshots:
  - [desktop_full.png](/D:/documents/ProteoSphereV2/artifacts/reviews/model_studio_internal_alpha/pilot_round_2/desktop_full.png)
  - [desktop_after_preview.png](/D:/documents/ProteoSphereV2/artifacts/reviews/model_studio_internal_alpha/pilot_round_2/desktop_after_preview.png)
  - [desktop_after_build.png](/D:/documents/ProteoSphereV2/artifacts/reviews/model_studio_internal_alpha/pilot_round_2/desktop_after_build.png)
  - [desktop_after_launch.png](/D:/documents/ProteoSphereV2/artifacts/reviews/model_studio_internal_alpha/pilot_round_2/desktop_after_launch.png)

## Remaining Honest Gaps

- cancellation remains only partially cooperative
- resume-in-place is still unsupported
- the runtime is still too monolithic for a stronger release-hardening cycle
- the dataset builder is lower fidelity than the eventual post-procurement full data path
- Rosetta/free-state/relax remains Stage 2 and is not part of the current visible pilot lane
- browser automation works through Selenium/Edge in this environment, but there is still no local Node/npm/Playwright stack

## Bottom Line

The Studio is now materially closer to real-user testing because the user can define the training set they want, build it into a concrete structure-backed study dataset, launch a model pipeline on it, and review the resulting analysis without dropping to the shell.

# Model Studio Ligand Pilot Smoke Report

## Summary

The launchable protein-ligand pilot completed synchronous smoke runs for both allowed beta model families on April 10, 2026.

Pilot truth boundary:

- dataset: `governed_pl_bridge_pilot_subset_v1`
- task: `protein-ligand`
- label: normalized `delta_G`
- split: `protein_ligand_component_grouped`
- structure policy: `experimental_only`
- graph recipe: `whole_complex_graph` + `whole_molecule` + `role_conditioned`
- launchable model families:
  - `graphsage`
  - `multimodal_fusion`

## Completed Runs

### GraphSAGE

- run id: `run-20260410T005824245933Z-protein-binding-default-v1-c710844a`
- status: `completed`
- backend: `torch-graphsage-lite`
- dataset ref: `study_build:training-set-build-20260410T005825757269Z-67fb7c`
- test RMSE: `3.4101`

Artifacts:

- [run_manifest.json](/D:/documents/ProteoSphereV2/artifacts/runtime/model_studio/runs/run-20260410T005824245933Z-protein-binding-default-v1-c710844a/run_manifest.json)
- [metrics.json](/D:/documents/ProteoSphereV2/artifacts/runtime/model_studio/runs/run-20260410T005824245933Z-protein-binding-default-v1-c710844a/metrics.json)
- [analysis.json](/D:/documents/ProteoSphereV2/artifacts/runtime/model_studio/runs/run-20260410T005824245933Z-protein-binding-default-v1-c710844a/analysis.json)
- [packaging_manifest.json](/D:/documents/ProteoSphereV2/artifacts/runtime/model_studio/runs/run-20260410T005824245933Z-protein-binding-default-v1-c710844a/packaging_manifest.json)

### Multimodal Fusion

- run id: `run-20260410T005901359729Z-protein-binding-default-v1-c6977c0c`
- status: `completed`
- backend: `sklearn-mlp-fusion-adapter`
- dataset ref: `study_build:training-set-build-20260410T005902841421Z-b638c3`
- test RMSE: `3.8685`

Artifacts:

- [run_manifest.json](/D:/documents/ProteoSphereV2/artifacts/runtime/model_studio/runs/run-20260410T005901359729Z-protein-binding-default-v1-c6977c0c/run_manifest.json)
- [metrics.json](/D:/documents/ProteoSphereV2/artifacts/runtime/model_studio/runs/run-20260410T005901359729Z-protein-binding-default-v1-c6977c0c/metrics.json)
- [analysis.json](/D:/documents/ProteoSphereV2/artifacts/runtime/model_studio/runs/run-20260410T005901359729Z-protein-binding-default-v1-c6977c0c/analysis.json)
- [packaging_manifest.json](/D:/documents/ProteoSphereV2/artifacts/runtime/model_studio/runs/run-20260410T005901359729Z-protein-binding-default-v1-c6977c0c/packaging_manifest.json)

## Remaining Gap

The ligand pilot now has backend validation, dataset build proof, and execution proof. The remaining beta-launch gap is the final browser/user-facing rehearsal evidence for the ligand flow, plus missing failure-state screenshots.

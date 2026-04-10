# Model Studio Internal Alpha Release Summary

## Status

The Model Studio is now in a **truthful internal-alpha hardening state** for the released
protein-binding path.

What is release-visible now:

- task type: `protein-protein`
- label type: `delta_G`
- split strategy: `leakage_resistant_benchmark`
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

Everything else is kept in the lab catalog and hidden from the main release surface.

## What Changed

- The release benchmark is now frozen at
  [LATEST_RELEASE_PP_ALPHA_BENCHMARK.json](/D:/documents/ProteoSphereV2/data/reports/model_studio_release_benchmarks/LATEST_RELEASE_PP_ALPHA_BENCHMARK.json)
  instead of aliasing the moving expanded benchmark pointer.
- Release catalog options are now driven by one capability registry shared by backend and UI:
  [capabilities.py](/D:/documents/ProteoSphereV2/api/model_studio/capabilities.py)
- `gin` was removed from the release catalog because it was not a distinct executable backend.
- Release-facing runs are filtered so old lab-only runs do not pollute the main UI.
- Run IDs are now collision-resistant and include a nonce.
- Run manifests now include `graph_id`, heartbeat metadata, and frozen release dataset refs.
- Read-time run-state mutation was removed. Stale in-progress recovery now happens through
  explicit recovery logic, not by browsing the run list.
- The GUI now renders release option labels more honestly and shows the selected run’s model
  instead of the live draft’s model.
- Run comparison is now bound to explicit compare selectors in the UI.

## Review Evidence

### Release Matrix

Artifact:
- [release_matrix_round_2.json](/D:/documents/ProteoSphereV2/artifacts/reviews/model_studio_internal_alpha/release_matrix_round_2.json)

Result:
- `15` release-matrix runs completed
- all release model families covered
- all release graph kinds covered
- one distinct backend family per visible released model

Visible release matrix coverage:
- `xgboost-like (HistGradientBoosting)` across `interface_graph`, `residue_graph`, `hybrid_graph`
- `catboost-like (RandomForest)` across `interface_graph`, `residue_graph`, `hybrid_graph`
- `mlp` across `interface_graph`, `residue_graph`, `hybrid_graph`
- `fusion_mlp_adapter` across `interface_graph`, `residue_graph`, `hybrid_graph`
- `graphsage-lite` across `interface_graph`, `residue_graph`, `hybrid_graph`

### User Sim

Artifact:
- [user_sim_trace.json](/D:/documents/ProteoSphereV2/artifacts/reviews/model_studio_internal_alpha/user_sim_round_2/user_sim_trace.json)

Flow covered:
- open Studio
- edit study title
- select release dataset
- choose graph + multimodal configuration
- validate
- compile
- launch
- inspect metrics, outliers, and run comparison

Observed result:
- quality gate: `ready`
- launched run completed successfully
- outliers rendered
- comparison rendered
- selected-run preview reflected the launched run, not the live draft

### Visual Review

Artifacts:
- [desktop_full.png](/D:/documents/ProteoSphereV2/artifacts/reviews/model_studio_internal_alpha/visual_round_2/desktop_full.png)
- [mobile_full.png](/D:/documents/ProteoSphereV2/artifacts/reviews/model_studio_internal_alpha/visual_round_2/mobile_full.png)
- [visual_review_manifest.json](/D:/documents/ProteoSphereV2/artifacts/reviews/model_studio_internal_alpha/visual_round_2/visual_review_manifest.json)

Visual read:
- desktop is strong enough for internal alpha: clear left nav, legible hero, crisp workspace hierarchy
- mobile is usable but dense; acceptable for internal alpha, not yet polished consumer-grade mobile
- the known dataset panel, release status, and draft library are now readable and stable
- the comparison and analysis surfaces are present and understandable

## Remaining Honest Gaps

This is stronger, but still not “ship to external users” ready.

Remaining internal-alpha limitations:

- `cancel` is only partially real:
  - a cancel request can be recorded
  - but the runtime is still mostly synchronous and not fully stage-cooperative
- `resume` is explicitly not supported in-place
- the runtime monolith in
  [runtime.py](/D:/documents/ProteoSphereV2/api/model_studio/runtime.py)
  still needs decomposition for safer hardening
- `multimodal_fusion` is still an honest fusion-MLP adapter, not a fully independent multimodal
  trainer owning the scored path end to end
- `xgboost-like` and `catboost-like` remain adapter-backed families, not the native libraries
- scientific readiness is mixed:
  - some release runs complete cleanly but still generalize weakly
  - this is now surfaced more honestly in recommendations, but it still needs better scientific QA

## Bottom Line

The Studio is now much closer to a release-quality internal alpha because the main release
surface only exposes options that actually run, the benchmark is frozen, the browser evidence
is real, and the visible model matrix passes end to end.

The next highest-value work is:

1. make cancellation truly cooperative
2. split the runtime into stage adapters
3. deepen scientific/runtime warnings
4. optionally promote a second released backend family only when it is genuinely distinct

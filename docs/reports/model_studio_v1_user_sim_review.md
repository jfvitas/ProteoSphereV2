# Model Studio V1 User-Sim Review

## Scenario
Goal: create a leakage-resistant protein-protein pipeline, choose a graph + global multimodal model, launch a run, and inspect outliers and recommendations.

## Walkthrough
1. Open the Model Studio web app.
2. Confirm the default draft is a protein-protein study with `delta_G` and `leakage_resistant_benchmark`.
3. Move through the six workspaces:
   - Project Home
   - Data Strategy Designer
   - Representation Designer
   - Pipeline Composer
   - Execution Console
   - Analysis and Review
4. Save the draft.
5. Validate and compile the draft.
6. Launch a run.
7. Open the resulting run from Recent Runs.
8. Inspect stage timeline, artifacts, metrics, outliers, and recommendations.

## What Worked Well
- The draft-save / validate / compile / launch loop is now linear and understandable.
- The six-workspace shell is coherent for an expert user.
- The Analysis and Review workspace gives immediate value because metrics and outliers are persisted, not ephemeral.
- Recommendation output is visible and understandable.

## Friction Points
- The Data Strategy Designer still presents richer catalog language than the currently runnable lane set.
- Representation Designer needs stronger inline explanation for what is actually materialized now versus what is just selectable in the catalog.
- Execution Console should eventually show stage progress with stronger visual contrast and per-stage drill-down.
- Comparison is available in the backend, but the UI affordance is still minimal.

## User-Sim Verdict
Pass for expert-alpha use.

The Studio is now usable for a technically strong internal user who understands:
- draft specs
- graph/model compatibility
- the difference between runnable and adapter-backed modules

It is not yet novice-ready, and it should not be presented as feature-complete.

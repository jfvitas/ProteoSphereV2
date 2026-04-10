# Model Studio Internal Alpha Review Findings, Round 2

This round folded in findings from role-specific review lanes:

- architect review
- QA/reliability review
- scientific/runtime review
- refactor/hardening review
- browser visual review
- user-sim review

## Closed or Reduced

### Release-catalog truthfulness

- `gin` was removed from the release catalog and kept in the lab catalog only.
- release-visible model labels are now more honest:
  - `xgboost-like (HistGradientBoosting)`
  - `catboost-like (RandomForest)`
  - `fusion_mlp_adapter`
  - `graphsage-lite`
- the release benchmark is now frozen and no longer aliases the moving expanded benchmark pointer.

### Release-facing status truth

- release-facing status is now derived from live service state instead of stale legacy planner output
- the main UI now shows only the frozen release benchmark in the known-dataset panel
- release-facing run lists now filter out lab-only runs such as the old `gin` matrix artifacts

### UI inspection truthfulness

- the run preview now renders the selected run’s model, not the live draft’s model
- run comparison now uses explicit selectors rather than silently comparing the newest two runs
- the browser evidence for the current alpha was regenerated after the hardening fixes

### Run integrity improvements

- run IDs now include a nonce to avoid second-resolution collisions
- run manifests now include `graph_id`
- run manifests now carry heartbeat-style timestamps
- read-time mutation of `running`/`queued` runs was removed
- stale run recovery moved to explicit recovery logic

## Still Open

### Run lifecycle

- cancellation is not fully cooperative yet
- resume-in-place is intentionally not supported yet
- long-run failure handling is improved only partially; the runtime still needs a fuller exception-safe
  stage runner

### Runtime structure

- the Studio runtime is still too monolithic for a mature release hardening cycle
- stage adapters should be split into:
  - dataset resolution
  - materialization
  - graph packaging
  - training dispatch
  - evaluation/reporting
  - run-state persistence

### Scientific/runtime depth

- some release-path runs still show weak holdout generalization
- runtime recommendations are more honest now, but still not as deep as they should be for
  scientific signoff

## Current Recommendation

The Studio now looks and behaves like a credible **internal alpha**, but not a broader release.
The most important next fixes are:

1. cooperative cancellation
2. runtime decomposition into stage adapters
3. stronger runtime-scientific warnings and acceptance gates
4. optional promotion of additional model families only when they are genuinely distinct

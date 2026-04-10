# Release Grade Runbook Preview

- Release-grade status: `frozen_v1_bar_closed`
- Command count: `7`

## Steps

- `refresh_release_surfaces` `Refresh release-grade evidence surfaces`: `python scripts/export_release_grade_readiness_preview.py`
- `refresh_runtime_maturity` `Refresh runtime maturity evidence`: `python scripts/export_release_runtime_maturity_preview.py`
- `refresh_source_coverage_depth` `Refresh source coverage depth evidence`: `python scripts/export_release_source_coverage_depth_preview.py`
- `refresh_provenance_depth` `Refresh provenance depth evidence`: `python scripts/export_release_provenance_depth_preview.py`
- `refresh_closure_queue` `Refresh ranked release closure queue`: `python scripts/export_release_grade_closure_queue_preview.py`
- `review_operator_recipe` `Review release-grade operator recipe`: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/operator_recipes.ps1 -Recipe release-grade-review -AsJson`
- `hold_release_claim` `Hold release claim until blockers are closed`: `python scripts/validate_operator_state.py --json`

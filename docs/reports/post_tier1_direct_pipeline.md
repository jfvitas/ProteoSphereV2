# Post Tier1 Direct Pipeline

- Status: `passed`
- Generated at: `2026-03-23T18:17:33.905750+00:00`
- Promotion path: `data/raw/protein_data_scope_seed/promotions/LATEST.json`
- Promotion ID: `protein-data-scope-seed:20260323T174627`
- Run ID: `20260323T181726Z`
- Scope root: `runs/tier1_direct_validation/20260323T181726Z`

## Canonical Traceability

- Canonical latest path: `runs/tier1_direct_validation/20260323T181726Z/canonical/LATEST.json`
- Canonical run id: `raw-canonical-20260323T181726Z`
- Canonical created at: `2026-03-23T18:17:27.433108+00:00`
- Canonical status / reason: `ready` / `all_manifest_driven_lanes_resolved`
- Canonical bootstrap summary path: `data\raw\bootstrap_runs\LATEST.json`
- Canonical root: `data\canonical`
- Canonical output paths:
  - `data\canonical\runs\raw-canonical-20260323T181726Z\canonical_store.json`
  - `data\canonical\runs\raw-canonical-20260323T181726Z\sequence_result.json`
  - `data\canonical\runs\raw-canonical-20260323T181726Z\structure_result.json`
  - `data\canonical\runs\raw-canonical-20260323T181726Z\assay_result.json`
- BindingDB selection path: `data\raw\bindingdb_dump_local\bindingdb-local-20260323\summary.json`
- BindingDB selection mode: `local_summary`
- BindingDB local rows: `5138`

## Packet Regression Gate

- Status: `passed`
- Baseline path: `D:/documents/ProteoSphereV2/data/packages/LATEST.json`
- Candidate path: `runs/tier1_direct_validation/20260323T181726Z/selected_cohort_materialization.json`

- Baseline selection: `baseline_selector=strongest_materialization_summary, ranking=max_complete,min_unresolved,min_deficit,min_missing`
- Current latest path: `D:/documents/ProteoSphereV2/data/packages/LATEST.json`
- Current latest matches strongest baseline: `True`

- Complete count: `7` -> `7`
- Partial count: `5` -> `5`
- Unresolved count: `0` -> `0`
- Packet deficit count: `5` -> `5`
- Total missing modality count: `7` -> `7`

## Concise Next Wave

- `P00387`: `partial`, present `sequence/structure/ppi`, still missing `ligand`
- `P09105`: `partial`, present `sequence/structure/ppi`, still missing `ligand`
- `Q2TAC2`: `partial`, present `sequence/structure/ppi`, still missing `ligand`
- `Q9UCM0`: `partial`, present `sequence` only, still missing `structure`, `ligand`, and `ppi`
- fresh targeted procurement read:
  - `P09105`: RCSB remained empty, BindingDB remained zero-hit, IntAct is the only moving lane and stays weak-summary-only
  - `Q2TAC2`: RCSB remained empty, BindingDB remained zero-hit, IntAct is the only moving lane and stays weak-summary-only
  - `Q9UCM0`: RCSB remained empty, BindingDB remained zero-hit, IntAct remains reachable-empty / non-resolving
- Highest-value next fix order:
  1. close the three single-ligand packet gaps for `P00387`, `P09105`, and `Q2TAC2`
  2. treat `Q9UCM0` as the only remaining multi-modality closure target in the scoped cohort
  3. keep the race-condition caveat explicit by following the current scope root, not older `20260323T175411Z` artifacts

## canonical

- Label: `Canonical materialization`
- Status: `passed`
- Return code: `0`
- Command: `python scripts\materialize_canonical_store.py --canonical-root D:\documents\ProteoSphereV2\runs\tier1_direct_validation\20260323T181726Z\canonical --run-id tier1-direct-20260323T181726Z`

## source_coverage_matrix

- Label: `Source coverage matrix refresh`
- Status: `passed`
- Return code: `0`
- Command: `python scripts\export_source_coverage_matrix.py --output D:\documents\ProteoSphereV2\runs\tier1_direct_validation\20260323T181726Z\source_coverage_matrix.json --markdown-output D:\documents\ProteoSphereV2\runs\tier1_direct_validation\20260323T181726Z\source_coverage_matrix.md`

## available_payload_registry

- Label: `Available payload registry regeneration`
- Status: `passed`
- Return code: `0`
- Command: `python scripts\generate_available_payload_registry.py --canonical-latest D:\documents\ProteoSphereV2\runs\tier1_direct_validation\20260323T181726Z\canonical\LATEST.json --output D:\documents\ProteoSphereV2\runs\tier1_direct_validation\20260323T181726Z\available_payloads.generated.json`

## selected_packet_materialization

- Label: `Selected packet cohort materialization`
- Status: `passed`
- Return code: `0`
- Command: `python scripts\materialize_selected_packet_cohort.py --available-payloads D:\documents\ProteoSphereV2\runs\tier1_direct_validation\20260323T181726Z\available_payloads.generated.json --output-root D:\documents\ProteoSphereV2\runs\tier1_direct_validation\20260323T181726Z\packages --output D:\documents\ProteoSphereV2\runs\tier1_direct_validation\20260323T181726Z\selected_cohort_materialization.json --run-id tier1-direct-20260323T181726Z`

## packet_deficit_dashboard

- Label: `Packet deficit dashboard refresh`
- Status: `passed`
- Return code: `0`
- Command: `python scripts\export_packet_deficit_dashboard.py --packages-root D:\documents\ProteoSphereV2\runs\tier1_direct_validation\20260323T181726Z\packages --output D:\documents\ProteoSphereV2\runs\tier1_direct_validation\20260323T181726Z\packet_deficit_dashboard.json --markdown-output D:\documents\ProteoSphereV2\runs\tier1_direct_validation\20260323T181726Z\packet_deficit_dashboard.md --latest-only`


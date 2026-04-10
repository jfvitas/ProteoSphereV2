# P32 Processing Sequence

This is the post-download-wave processing order to run in `D:\documents\ProteoSphereV2`. The goal is to reconcile the wave forward in a safe sequence: validate first, refresh local imports, rebuild canonical outputs, rebuild summaries, then rematerialize packets and lock the result with parity checks.

## Current State

The refreshed local registry still reports `29 present`, `2 partial`, and `8 missing` source lanes. Structure, ligand, pathway, and structural-classification lanes are present; motif lanes are still missing; broad interaction-network lanes are still missing. That means the run should stay source-gated and should not overclaim motif or network completeness.

The current summary-library artifacts are small and conservative:

- `artifacts/status/reactome_local_summary_library.json` has `4` records and source manifest `bio-agent-lab/reactome:2026-03-16`.
- `artifacts/status/intact_local_summary_library.json` has `4` records and source manifest `IntAct:20260323T002625Z:download:6a49b82dc9ec053d`.
- `artifacts/status/selected_cohort_materialization.current.json` shows `12` packets with `7` complete, `5` partial, and `0` unresolved.
- `data/packages/LATEST.json` currently matches that same `12 / 7 / 5 / 0` packet baseline.

The canonical artifact is not a flat payload file. `data/canonical/LATEST.json` is a composite bootstrap summary with sections such as `sequence_result`, `structure_result`, `assay_result`, `bindingdb_selection`, `record_counts`, `unresolved_counts`, and `output_paths`. That shape matters because the rebuild step should refresh the whole canonical surface, not just one lane.

## 1. Validate

Run the coverage matrix refresh and the operator-state validation first.

```powershell
python scripts\export_source_coverage_matrix.py --bootstrap-summary data\raw\bootstrap_runs\LATEST.json --local-registry-summary data\raw\local_registry_runs\LATEST.json --output artifacts\status\source_coverage_matrix.json --markdown-output docs\reports\source_coverage_matrix.md
python scripts\validate_operator_state.py
```

Read this stage as the gate for the rest of the run. If the coverage matrix does not reflect the newest wave, or if operator validation fails, stop here and repair before importing or rebuilding anything else.

## 2. Refresh Local Imports

Refresh the raw mirrors and the local registry next.

```powershell
python scripts\import_local_sources.py --include-missing
```

If the new download wave only landed a subset of sources, rerun the importer with a scoped `--sources` list for just the new lanes after the full refresh. The important part is that missing sources stay visible and the registry latest stays authoritative.

Expected output:

- a refreshed `data/raw/local_registry_runs/LATEST.json`
- new timestamped inventories under `data/raw/local_registry/<timestamp>/`
- visible gap rows for still-missing lanes

## 3. Rebuild Canonical Outputs

Rebuild the canonical store after the imports settle.

```powershell
python scripts\materialize_canonical_store.py
```

This step should refresh `data/canonical/LATEST.json` and the corresponding run folder. Treat that file as the canonical bootstrap summary for the wave. Do not move on to summaries if the canonical rebuild does not land cleanly.

Expected output shape:

- `sequence_result`
- `structure_result`
- `assay_result`
- `bindingdb_selection`
- `record_counts`
- `unresolved_counts`
- `output_paths`

## 4. Rebuild Summaries

Refresh the source-specific local summaries before the integrated library rebuild.

```powershell
python scripts\materialize_reactome_local_summary.py --accessions <release-cohort-accessions> --output artifacts\status\reactome_local_summary_library.json
python scripts\materialize_intact_local_summary.py --accessions <release-cohort-accessions> --output artifacts\status\intact_local_summary_library.json
python scripts\materialize_local_bridge_ligand_payloads.py --cohort-slice runs\real_data_benchmark\full_results\p15_upgraded_cohort_slice.json --output artifacts\status\local_bridge_ligand_payloads.json
python scripts\materialize_local_bridge_ppi_payloads.py --cohort-slice runs\real_data_benchmark\full_results\p15_upgraded_cohort_slice.json --output artifacts\status\local_bridge_ppi_payloads.json
python scripts\materialize_weak_ppi_candidate_summary.py --output artifacts\status\weak_ppi_candidate_summary.json --report docs\reports\weak_ppi_candidate_summary.md
python scripts\materialize_protein_summary_library.py --accessions <release-cohort-accessions> --output artifacts\status\protein_summary_library.json
```

The first two commands should keep the current summary artifacts compact and source-backed. The bridge and weak-PPI commands refresh the local ligand and interaction joins. The protein summary library command is the integrated summary handoff point from the p29 code wave, so keep it downstream of the source-specific refreshes.

Expected outputs:

- `artifacts/status/reactome_local_summary_library.json`
- `artifacts/status/intact_local_summary_library.json`
- `artifacts/status/local_bridge_ligand_payloads.json`
- `artifacts/status/local_bridge_ppi_payloads.json`
- `artifacts/status/weak_ppi_candidate_summary.json`
- `artifacts/status/protein_summary_library.json`

## 5. Rematerialize Packets

Once the summary layer is current, regenerate the available payload registry and rematerialize the selected cohort.

```powershell
python scripts\generate_available_payload_registry.py --balanced-plan runs\real_data_benchmark\full_results\balanced_dataset_plan.json --canonical-latest data\canonical\LATEST.json --raw-root data\raw --output runs\real_data_benchmark\full_results\available_payloads.generated.json
python scripts\materialize_selected_packet_cohort.py --available-payloads runs\real_data_benchmark\full_results\available_payloads.generated.json --output-root data\packages --output artifacts\status\selected_cohort_materialization.current.json --run-id <wave-id>
python scripts\rehydrate_training_packet.py --package-manifest <selected packet manifest> --available-artifacts runs\real_data_benchmark\full_results\available_payloads.generated.json --canonical-store data\canonical\LATEST.json --output artifacts\status\packet_rehydration.json
python scripts\export_packet_deficit_dashboard.py --packages-root data\packages --output artifacts\status\packet_deficit_dashboard.json --markdown-output docs\reports\packet_deficit_dashboard.md --latest-only
```

This stage should bring `data/packages/LATEST.json` and `artifacts/status/selected_cohort_materialization.current.json` back in sync with the latest available payloads. The expected packet baseline before a new wave is `12` packets with `7` complete, `5` partial, and `0` unresolved. Any improvement or regression should be traceable to a real payload change, not a silent rematerialization drift.

## 6. Final Validation

Finish by proving the operator surface is in parity with the rebuilt artifacts.

```powershell
python scripts\validate_operator_state.py
python scripts\export_provenance_drilldown.py --output runs\real_data_benchmark\full_results\provenance_drilldown.json
```

If validation fails here, stop and repair before taking the next wave. The end state should leave the coverage matrix, the canonical store, the summary artifacts, the packet materialization, and the provenance drilldown all telling the same story.

## Readability Notes

- Keep motif and interaction-network gaps explicit until procurement actually changes.
- Prefer compact summary artifacts over raw payload dumps.
- Use the coverage matrix and provenance drilldown as the main human-readable sanity checks.
- Do not let packet completeness rise without a matching payload registry refresh.

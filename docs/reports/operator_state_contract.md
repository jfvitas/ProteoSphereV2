# Operator State Contract

Date: 2026-03-22  
Task: `P9-T002`

## Purpose

This contract defines the single operator-state schema that later WinUI work should bind to. It is intentionally a union of two already-existing surfaces:

- the current PowerShell state view from [`scripts/powershell_interface.ps1`](D:/documents/ProteoSphereV2/scripts/powershell_interface.ps1), and
- the benchmark dashboard export from [`runs/real_data_benchmark/full_results/operator_dashboard.json`](D:/documents/ProteoSphereV2/runs/real_data_benchmark/full_results/operator_dashboard.json).

The goal is to keep a single operator model in the repo, not a PowerShell model plus a second WinUI-only model.

## Contract Shape

The canonical snapshot is a single object with these required top-level sections:

| Section | Meaning |
| --- | --- |
| `schema_version` | Contract version for breaking-change control |
| `generated_at` | Snapshot timestamp |
| `task_id` | The benchmark or operator task the snapshot is describing |
| `source_files` | File-path provenance for the snapshot inputs |
| `queue` | PowerShell queue summary |
| `library` | Summary-library readiness and materialization status |
| `benchmark` | Benchmark state view from the current run tree |
| `runtime` | Supervisor and orchestrator runtime state |
| `dashboard` | Read-only release-style projection built from the benchmark artifacts |

The schema lives at [`artifacts/schemas/operator_state.schema.json`](D:/documents/ProteoSphereV2/artifacts/schemas/operator_state.schema.json).

## Source Of Truth Mapping

| Contract section | Grounding artifact |
| --- | --- |
| `queue` | `tasks/task_queue.json` via the PowerShell state view |
| `library` | `artifacts/status/P6-T001.json` and `artifacts/status/P6-T003.json` via the PowerShell state view |
| `benchmark` | `runs/real_data_benchmark/full_results/*` via the PowerShell state view |
| `runtime` | `artifacts/status/orchestrator_state.json` via the PowerShell state view |
| `dashboard` | `runs/real_data_benchmark/full_results/operator_dashboard.json` |

## Binding Rules For Future WinUI Work

- Bind to this schema only. Do not create a second operator model that re-derives queue, library, benchmark, or dashboard state.
- Treat `dashboard` as a projection payload, not as a competing source of truth.
- Preserve blocker arrays, unresolved counts, and explicit readiness labels exactly as emitted.
- Keep `generated_at` and `source_files` visible in the UI so freshness and provenance remain obvious.
- Additive fields inside versioned payloads are acceptable only when they do not change required field meanings. Breaking changes should bump `schema_version`.

## Stability Notes

The following pieces are intended to stay stable for the current release slice:

- top-level section names
- file-provenance fields
- queue/library/runtime readiness booleans and counts
- benchmark blocker lists and truth-boundary fields
- dashboard verdict labels such as `dashboard_status`, `operator_go_no_go`, and `release_grade_status`

What is not stable yet:

- the deeper benchmark payloads that remain prototype-runtime dependent
- any future expansion of dashboard evidence depth
- any additional operator sections that would duplicate the existing model

## Release Interpretation

This schema does not claim release readiness by itself. It only makes the current operator surfaces explicit and bindable.

The honest reading is:

- the operator snapshot is truthful enough to support the current benchmark workflow,
- the dashboard projection remains conservative and blocker-aware,
- the runtime is still the local prototype surface,
- and WinUI should consume the same canonical fields rather than inventing a parallel state graph.

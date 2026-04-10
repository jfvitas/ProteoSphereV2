# ProteoSphereV2

ProteoSphereV2 is an autonomous, multi-agent build repository for a biomolecular ML platform.

The current repository state is based on these packaged spec bundles:
- `specs/parallel_build/`
- `specs/autotask/`
- `master_handoff_package/`
- `ml_platform_level3_spec/`
- `protein_execution_canonical_spec/`
- `protein_platform_lockdown_spec/`
- `protein_platform_max_complete_spec/`

The master handoff package is now the authoritative source-of-truth hierarchy:

1. lockdown spec
2. execution and canonical data spec
3. max-complete spec

The parallel-build and autotask packages remain the orchestration layer around that authoritative technical handoff.

## What Is In This Repo

- A project layout for the target platform.
- A dependency-aware task system that now spans the full release program from baseline implementation through QA, user-simulation validation, release engineering, and GA operations.
- Bootstrap, queue seeding, orchestration, monitoring, and review-prep scripts.
- CI checks for queue integrity and orchestrator selection logic.
- Runbooks for week-long unattended operation through the Codex desktop automation loop.

## Quick Start

1. `python scripts/bootstrap_repo.py`
2. `python scripts/seed_queue.py`
3. `python -m pytest`
4. `python scripts/orchestrator.py --once`
5. Review dispatch manifests under `artifacts/dispatch/`

## Important Constraint

The packaged scripts assume the `codex` CLI can be launched directly from the shell. On this machine, the desktop-installed `codex.exe` resolves on `PATH` but cannot be executed from shell subprocesses because Windows returns `Access is denied.` For that reason, this repository uses:

- Python scripts for queue/state management and manifest generation
- Codex desktop sub-agents for active execution
- a Codex desktop automation prompt for unattended continuation over the next week

## Repository Layout

- `core/`, `connectors/`, `normalization/`, `features/`, `datasets/`, `models/`, `training/`, `evaluation/`, `execution/`, `api/`, `gui/`
- `tasks/` for task queues
- `artifacts/` for status, reports, dispatch manifests, reviews, and blockers
- `docs/runbooks/` for operational guidance
- `specs/` for the imported source specifications

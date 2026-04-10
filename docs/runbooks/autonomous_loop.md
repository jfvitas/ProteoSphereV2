# Autonomous Loop Runbook

This repository runs as a two-layer system:

1. Local Python scripts manage the task queue, state, validation, dispatch manifests, and review manifests.
2. Codex desktop agents execute the actual work by consuming those manifests and writing status or blocker artifacts.

## Why This Split Exists

The packaged orchestration scripts expected to launch `codex` as a subprocess. On this workstation, the desktop `codex.exe` is visible on `PATH` but shell execution fails with `Access is denied.` The unattended loop is therefore driven by Codex desktop automation instead of shell subprocesses.

## Normal Cycle

1. `python scripts/bootstrap_repo.py`
2. `python scripts/seed_queue.py`
3. `python scripts/orchestrator.py --once`
4. Dispatch the generated tasks with Codex agents.
5. Workers write:
   - `artifacts/status/<TASK_ID>.json` on success
   - `artifacts/blockers/<TASK_ID>.md` on blockers
6. `python scripts/reviewer_loop.py --once`
7. Review manifests are generated for completed tasks.
8. `python scripts/auto_task_generator.py`
9. Repeat hourly through Codex automation.

## Week-Long Unattended Guidance

- Use one planner agent, ten coding workers, three data-analysis workers, and one reviewer.
- Keep `MAX_GPU_TRAINING_WORKERS=1`.
- Run a smoke period first with two coding workers and one analysis worker before the long unattended loop.
- Do not mark missing platform architecture as resolved unless a spec file is added to the repository.

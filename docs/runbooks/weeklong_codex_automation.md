# Week-Long Codex Automation

Use the Codex desktop automation loop as the active orchestrator. The local Python scripts manage queue state and dispatch manifests; the automation consumes those manifests and rotates workers as agents finish.

## Automation Responsibilities

1. Read the repository specs under `specs/parallel_build/` and `specs/autotask/`.
2. Read the authoritative handoff chain under `master_handoff_package/` in this order:
   - `00_START_HERE/MASTER_HANDOFF_README.md`
   - `00_START_HERE/AGENT_EXECUTION_ORDER.md`
   - `01_LOCKDOWN_SPEC/`
   - `02_EXECUTION_AND_CANONICAL_SPEC/`
   - `03_MAX_COMPLETE_SPEC/` only after the locked baseline works end-to-end
3. Read `docs/reports/missing_baseline_specs.md` and the spec reconciliation notes before assigning work.
3. Run:
   - `python scripts/bootstrap_repo.py`
   - `python scripts/seed_queue.py`
   - `python scripts/orchestrator.py --once`
   - `python scripts/reviewer_loop.py --once`
   - `python scripts/auto_task_generator.py`
4. Inspect `artifacts/dispatch/*.json` and `artifacts/reviews/*.json`.
5. Maintain the logical topology:
   - 1 planner
   - up to 10 coding workers
   - up to 3 data-analysis workers
   - 1 reviewer
6. Respect the app constraint that only 6 live sub-agent threads can exist at once.
   - Recycle completed agents immediately.
   - Keep the logical role counts in queue/state, even though live concurrency is capped.
7. Enforce one task per agent and no overlapping file ownership.
8. Require each worker to:
   - edit only owned files
   - run focused validation
   - write `artifacts/status/<TASK_ID>.json` on success
   - write `artifacts/blockers/<TASK_ID>.md` if blocked
9. Lock the first build to the exact lockdown pipeline:
   - RCSB + UniProt + BindingDB
   - MMseqs2 chain mapping and cluster splitting
   - ESM2, RDKit, KD-tree contacts
   - EGNN + cross-attention + XGBoost
   - AdamW + cosine + MSE
   - RMSE + Pearson evaluation
10. If a task depends on missing baseline architecture or direct contradiction, log a blocker instead of inventing the design.
11. Re-run `python scripts/orchestrator.py --once` after each wave to free finished tasks and dispatch the next batch.
11. Prefer real-data validation work once the canonical and storage layers are ready.
   - Run true source downloads where permitted.
   - Build summary-library artifacts from real source content.
   - Run end-to-end packet materialization and training/evaluation against actual downloaded data, not only mocks.
12. Keep a usable operator interface in scope.
   - PowerShell or CLI operator surfaces are valid for the near term.
   - WinUI can be developed in a later wave if the app shell is prioritized.

## Supplemental Guidance From bio-agent-lab

Use `C:\Users\jfvit\Documents\bio-agent-lab` as a reference implementation for:

- local-first data packaging
- provenance and source capability reporting
- canonical planning and identity layers
- workflow manifests and stage visibility
- leakage-aware split governance
- multimodal packaging concepts

Do not copy its dirty worktree blindly. Reuse ideas, data strategy, and stable patterns while keeping ProteoSphereV2 as a clean next-generation repository.

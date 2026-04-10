# Launch Steps

1. Place this package in the repository.
2. Ensure `.codex/config.toml` is in the repo root.
3. Run:
   python SCRIPTS/bootstrap_repo.py
4. Seed the queue:
   python SCRIPTS/seed_queue.py
5. Start orchestrator:
   python SCRIPTS/orchestrator.py
6. In another terminal:
   python SCRIPTS/reviewer_loop.py
7. Optional:
   python SCRIPTS/monitor.py

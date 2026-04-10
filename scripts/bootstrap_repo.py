from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.tasklib import save_json

DIRS = [
    "tasks",
    "logs",
    "artifacts/status",
    "artifacts/reports",
    "artifacts/blockers",
    "artifacts/reviews",
    "artifacts/planner",
    "artifacts/dispatch",
    "docs/reports",
]


def main() -> None:
    for directory in DIRS:
        Path(directory).mkdir(parents=True, exist_ok=True)

    queue_path = Path("tasks/task_queue.json")
    if not queue_path.exists():
        queue_path.write_text("[]\n", encoding="utf-8")

    state = {
        "active_workers": [],
        "completed_tasks": [],
        "failed_tasks": [],
        "blocked_tasks": [],
        "review_queue": [],
        "dispatch_queue": [],
        "last_task_generation_ts": None,
    }
    save_json(Path("artifacts/status/orchestrator_state.json"), state)
    print("Bootstrap complete.")


if __name__ == "__main__":
    main()

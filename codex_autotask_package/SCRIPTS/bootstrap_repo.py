import json
from pathlib import Path

dirs = [
    "tasks",
    "logs",
    "artifacts/status",
    "artifacts/reports",
    "artifacts/blockers",
    "artifacts/reviews",
    "artifacts/planner",
]
for d in dirs:
    Path(d).mkdir(parents=True, exist_ok=True)

queue = Path("tasks/task_queue.json")
if not queue.exists():
    queue.write_text("[]\n", encoding="utf-8")

state = {
    "active_workers": [],
    "completed_tasks": [],
    "failed_tasks": [],
    "blocked_tasks": [],
    "last_task_generation_ts": None
}
Path("artifacts/status/orchestrator_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
print("Bootstrap complete.")

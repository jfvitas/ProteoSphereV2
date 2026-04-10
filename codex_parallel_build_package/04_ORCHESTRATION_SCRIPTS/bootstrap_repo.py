import os, json
from pathlib import Path

dirs = [
    "tasks",
    "logs",
    "artifacts/status",
    "artifacts/reports",
    "artifacts/blockers",
    "artifacts/reviews",
]
for d in dirs:
    Path(d).mkdir(parents=True, exist_ok=True)

queue_path = Path("tasks/task_queue.json")
if not queue_path.exists():
    queue_path.write_text("[]\n", encoding="utf-8")

state = {
    "active_workers": [],
    "completed_tasks": [],
    "failed_tasks": [],
    "blocked_tasks": []
}
Path("artifacts/status/orchestrator_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
print("Bootstrap complete.")

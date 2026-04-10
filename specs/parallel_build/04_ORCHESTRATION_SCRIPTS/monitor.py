import json, time
from pathlib import Path

while True:
    q = Path("tasks/task_queue.json")
    s = Path("artifacts/status/orchestrator_state.json")
    if q.exists():
        queue = json.loads(q.read_text(encoding="utf-8"))
        counts = {}
        for t in queue:
            counts[t["status"]] = counts.get(t["status"], 0) + 1
        print("Queue:", counts)
    if s.exists():
        state = json.loads(s.read_text(encoding="utf-8"))
        print("Active workers:", len(state.get("active_workers", [])))
    time.sleep(30)

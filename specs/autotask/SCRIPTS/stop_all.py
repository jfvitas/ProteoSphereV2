import json, os, signal
from pathlib import Path

state_path = Path("artifacts/status/orchestrator_state.json")
if not state_path.exists():
    print("No state file found.")
    raise SystemExit(0)

state = json.loads(state_path.read_text(encoding="utf-8"))
for a in state.get("active_workers", []):
    try:
        os.kill(a["pid"], signal.SIGTERM)
        print("Stopped", a["task_id"], a["pid"])
    except OSError:
        pass

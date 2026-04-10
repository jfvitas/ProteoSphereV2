import json, os, subprocess, time
from pathlib import Path

QUEUE_PATH = Path("tasks/task_queue.json")
STATE_PATH = Path("artifacts/status/orchestrator_state.json")
BLOCKER_DIR = Path("artifacts/blockers")
STATUS_DIR = Path("artifacts/status")
LOG_DIR = Path("logs")

CODEX_CMD = os.environ.get("CODEX_CMD", "codex")
MAX_CODING_WORKERS = int(os.environ.get("MAX_CODING_WORKERS", "10"))
MAX_ANALYSIS_WORKERS = int(os.environ.get("MAX_ANALYSIS_WORKERS", "3"))
POLL_SECONDS = int(os.environ.get("ORCH_POLL_SECONDS", "15"))

def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default

def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def deps_done(task, queue):
    done = {t["id"] for t in queue if t["status"] == "done"}
    return all(dep in done for dep in task.get("dependencies", []))

def available_slot(task_type, active):
    coding = sum(1 for a in active if a["type"] == "coding")
    analysis = sum(1 for a in active if a["type"] == "data_analysis")
    return coding < MAX_CODING_WORKERS if task_type == "coding" else analysis < MAX_ANALYSIS_WORKERS

def prompt_for(task):
    return f"""
You are a worker.
Execute only this task.

TASK_ID: {task['id']}
TITLE: {task['title']}
TYPE: {task['type']}
PHASE: {task['phase']}
FILES: {task['files']}
SUCCESS_CRITERIA: {task['success_criteria']}

Rules:
- work only in assigned files plus direct related tests
- follow the repository specs exactly
- if blocked, write artifacts/blockers/{task['id']}.md and stop
- when done, write artifacts/status/{task['id']}.md and stop
"""

def launch(task):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{task['id']}.log"
    log = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen([CODEX_CMD, prompt_for(task)], stdout=log, stderr=subprocess.STDOUT)
    return proc.pid, str(log_path)

while True:
    queue = load_json(QUEUE_PATH, [])
    state = load_json(STATE_PATH, {"active_workers": [], "completed_tasks": [], "failed_tasks": [], "blocked_tasks": []})

    still_active, finished = [], set()
    for a in state["active_workers"]:
        try:
            os.kill(a["pid"], 0)
            still_active.append(a)
        except OSError:
            finished.add(a["pid"])
    state["active_workers"] = still_active

    for task in queue:
        if task.get("status") == "running" and task.get("pid") in finished:
            blocker = BLOCKER_DIR / f"{task['id']}.md"
            statusf = STATUS_DIR / f"{task['id']}.md"
            if blocker.exists():
                task["status"] = "blocked"
                if task["id"] not in state["blocked_tasks"]:
                    state["blocked_tasks"].append(task["id"])
            elif statusf.exists():
                task["status"] = "done"
                if task["id"] not in state["completed_tasks"]:
                    state["completed_tasks"].append(task["id"])
            else:
                task["status"] = "failed"
                if task["id"] not in state["failed_tasks"]:
                    state["failed_tasks"].append(task["id"])

    for task in queue:
        if task["status"] == "pending" and deps_done(task, queue) and available_slot(task["type"], state["active_workers"]):
            pid, log_path = launch(task)
            task["status"] = "running"
            task["pid"] = pid
            task["log_path"] = log_path
            state["active_workers"].append({"task_id": task["id"], "pid": pid, "type": task["type"], "log_path": log_path})

    save_json(QUEUE_PATH, queue)
    save_json(STATE_PATH, state)
    print(f"Active={len(state['active_workers'])} Done={len(state['completed_tasks'])} Blocked={len(state['blocked_tasks'])} Failed={len(state['failed_tasks'])}")
    time.sleep(POLL_SECONDS)

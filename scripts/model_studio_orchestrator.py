from __future__ import annotations

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.tasklib import conflicts, dependencies_complete, load_json, save_json, task_counts

QUEUE_PATH = Path("tasks/model_studio_wave_queue.json")
STATE_PATH = Path("artifacts/status/model_studio_orchestrator_state.json")
DISPATCH_DIR = Path("artifacts/dispatch/model_studio")
STOP_PATH = Path("artifacts/status/STOP_MODEL_STUDIO")


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def refresh_finished_tasks(queue: list[dict], state: dict) -> None:
    active_lookup = {entry["task_id"]: entry for entry in state.get("active_workers", [])}
    queue_status_by_id = {task["id"]: task["status"] for task in queue}
    completed_or_blocked: set[str] = set()

    for task in queue:
        task_id = task["id"]
        status_file = Path("artifacts/status") / f"{task_id}.json"
        blocker_file = Path("artifacts/blockers") / f"{task_id}.md"
        if blocker_file.exists():
            task["status"] = "blocked"
            if task_id not in state.setdefault("blocked_tasks", []):
                state["blocked_tasks"].append(task_id)
            completed_or_blocked.add(task_id)
            continue
        if status_file.exists():
            task["status"] = "done"
            if task_id not in state.setdefault("completed_tasks", []):
                state["completed_tasks"].append(task_id)
            completed_or_blocked.add(task_id)

    still_active = []
    for entry in state.get("active_workers", []):
        task_id = entry["task_id"]
        if task_id in completed_or_blocked:
            continue
        if queue_status_by_id.get(task_id) not in {"dispatched", "running"}:
            continue
        still_active.append(entry)
    state["active_workers"] = still_active

    for task in queue:
        if task["status"] == "dispatched" and task["id"] not in active_lookup:
            dispatch_file = DISPATCH_DIR / f"{task['id']}.json"
            if dispatch_file.exists():
                task["status"] = "running"
                state["active_workers"].append(
                    {
                        "task_id": task["id"],
                        "type": task["type"],
                        "gpu_heavy": "train" in task["title"].lower(),
                        "branch": task["branch"],
                    }
                )


def reconcile_state_indexes(queue: list[dict], state: dict) -> None:
    state["completed_tasks"] = sorted(
        task["id"] for task in queue if task["status"] in {"done", "reviewed"}
    )
    state["blocked_tasks"] = sorted(task["id"] for task in queue if task["status"] == "blocked")


def promote_ready(queue: list[dict]) -> None:
    for task in queue:
        if task["status"] == "pending" and dependencies_complete(task, queue):
            task["status"] = "ready"


def capacity_available(task: dict, active_workers: list[dict], limits: dict[str, int]) -> bool:
    coding = sum(1 for worker in active_workers if worker["type"] == "coding")
    analysis = sum(1 for worker in active_workers if worker["type"] == "data_analysis")
    integration = sum(1 for worker in active_workers if worker["type"] == "integration")
    docs = sum(1 for worker in active_workers if worker["type"] == "docs_reporting")
    tests = sum(1 for worker in active_workers if worker["type"] == "test_hardening")
    gpu_heavy = sum(1 for worker in active_workers if worker.get("gpu_heavy"))

    if task["type"] == "coding" and coding >= limits["coding"]:
        return False
    if task["type"] == "data_analysis" and analysis >= limits["analysis"]:
        return False
    if task["type"] == "integration" and integration >= limits["integration"]:
        return False
    if task["type"] == "docs_reporting" and docs >= limits["docs"]:
        return False
    if task["type"] == "test_hardening" and tests >= limits["tests"]:
        return False
    if "train" in task["title"].lower() and gpu_heavy >= limits["gpu"]:
        return False
    return True


def write_dispatch_manifest(task: dict) -> None:
    DISPATCH_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_id": task["id"],
        "title": task["title"],
        "type": task["type"],
        "phase": task["phase"],
        "files": task["files"],
        "dependencies": task["dependencies"],
        "success_criteria": task["success_criteria"],
        "branch": task["branch"],
        "studio_program": "model-studio-program:v1",
    }
    save_json(DISPATCH_DIR / f"{task['id']}.json", payload)


def prune_dispatch_manifests(queue: list[dict]) -> None:
    active_dispatch_ids = {
        task["id"] for task in queue if task["status"] in {"dispatched", "running"}
    }
    if not DISPATCH_DIR.exists():
        return
    for path in DISPATCH_DIR.glob("*.json"):
        if path.stem not in active_dispatch_ids:
            path.unlink()


def select_dispatches(queue: list[dict], state: dict, limits: dict[str, int]) -> list[dict]:
    active_tasks = [task for task in queue if task["status"] in {"running", "dispatched"}]
    selected: list[dict] = []
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    for task in sorted(
        [item for item in queue if item["status"] == "ready"],
        key=lambda item: (
            item["phase"],
            priority_rank.get(item["priority"], 3),
            item["id"],
        ),
    ):
        simulated_active = active_tasks + selected
        if conflicts(task, simulated_active):
            continue
        if not capacity_available(task, state.get("active_workers", []), limits):
            continue
        selected.append(task)
        state.setdefault("active_workers", []).append(
            {
                "task_id": task["id"],
                "type": task["type"],
                "gpu_heavy": "train" in task["title"].lower(),
                "branch": task["branch"],
            }
        )
    return selected


def tick(limits: dict[str, int]) -> None:
    queue = load_json(QUEUE_PATH, [])
    state = load_json(
        STATE_PATH,
        {
            "active_workers": [],
            "completed_tasks": [],
            "failed_tasks": [],
            "blocked_tasks": [],
            "review_queue": [],
            "dispatch_queue": [],
            "program_id": "model-studio-program:v1",
        },
    )
    state["last_tick_started_at"] = _utc_now()

    refresh_finished_tasks(queue, state)
    promote_ready(queue)
    reconcile_state_indexes(queue, state)
    state["dispatch_queue"] = []
    for task in select_dispatches(queue, state, limits):
        task["status"] = "dispatched"
        write_dispatch_manifest(task)
        state["dispatch_queue"].append(task["id"])
    prune_dispatch_manifests(queue)

    save_json(QUEUE_PATH, queue)
    state["last_tick_completed_at"] = _utc_now()
    save_json(STATE_PATH, state)
    print(task_counts(queue))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coding-workers", type=int, default=8)
    parser.add_argument("--analysis-workers", type=int, default=3)
    parser.add_argument("--integration-workers", type=int, default=3)
    parser.add_argument("--docs-workers", type=int, default=2)
    parser.add_argument("--test-workers", type=int, default=3)
    parser.add_argument("--gpu-workers", type=int, default=1)
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    limits = {
        "coding": args.coding_workers,
        "analysis": args.analysis_workers,
        "integration": args.integration_workers,
        "docs": args.docs_workers,
        "tests": args.test_workers,
        "gpu": args.gpu_workers,
    }

    while True:
        tick(limits)
        if args.once:
            return
        if STOP_PATH.exists():
            print("Model Studio stop signal observed.")
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()

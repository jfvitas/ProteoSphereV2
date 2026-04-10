from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.task_catalog import build_initial_queue
from scripts.tasklib import load_json, save_json, validate_queue

QUEUE_PATH = Path("tasks/task_queue.json")
STATE_PATH = Path("artifacts/status/orchestrator_state.json")


def replenish_queue(threshold: int, batch_size: int) -> int:
    queue = load_json(QUEUE_PATH, [])
    state = load_json(STATE_PATH, {})
    pending_like = [
        task
        for task in queue
        if task["status"] in {"pending", "ready", "dispatched", "running"}
    ]
    if len(pending_like) >= threshold:
        return 0

    existing_ids = {task["id"] for task in queue}
    additions = []
    for task in build_initial_queue():
        if task["id"] in existing_ids:
            continue
        additions.append(task)
        if len(additions) >= batch_size:
            break

    if additions:
        queue.extend(additions)
        errors = validate_queue(queue)
        if errors:
            raise SystemExit("Queue validation failed:\n- " + "\n- ".join(errors))
        state["last_task_generation_ts"] = int(time.time())
        save_json(QUEUE_PATH, queue)
        save_json(STATE_PATH, state)
    return len(additions)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=25)
    args = parser.parse_args()
    added = replenish_queue(args.threshold, args.batch_size)
    print(f"Added {added} tasks.")


if __name__ == "__main__":
    main()

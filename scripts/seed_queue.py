from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.task_catalog import build_initial_queue
from scripts.tasklib import save_json, validate_queue


def main() -> None:
    queue = build_initial_queue()
    errors = validate_queue(queue)
    if errors:
        raise SystemExit("Queue validation failed:\n- " + "\n- ".join(errors))
    save_json(Path("tasks/task_queue.json"), queue)
    print(f"Seeded {len(queue)} tasks.")


if __name__ == "__main__":
    main()

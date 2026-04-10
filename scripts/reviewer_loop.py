from __future__ import annotations

import argparse
import traceback
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.tasklib import load_json, save_json

QUEUE_PATH = Path("tasks/task_queue.json")
STATE_PATH = Path("artifacts/status/orchestrator_state.json")
REVIEW_DIR = Path("artifacts/reviews")
RUNTIME_DIR = Path("artifacts/runtime")
FAILURE_PATH = RUNTIME_DIR / "reviewer_cycle_failure.json"
STOP_PATH = Path("artifacts/status/STOP")
MAX_IDENTICAL_FAILURES = 3


class ReviewerLoopFailure(RuntimeError):
    def __init__(self, stage: str, task_id: str | None, cause: Exception):
        self.stage = stage
        self.task_id = task_id
        self.cause = cause
        super().__init__(str(cause))


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _failure_signature(stage: str, exc: Exception) -> str:
    return f"{stage}:{type(exc).__name__}:{exc}"


def _build_failure_payload(stage: str, task_id: str | None, exc: Exception) -> dict[str, Any]:
    previous = load_json(FAILURE_PATH, {})
    signature = _failure_signature(stage, exc)
    retry_count = 1
    if previous.get("failure_signature") == signature:
        retry_count = int(previous.get("retry_count") or 0) + 1
    should_stop = retry_count >= MAX_IDENTICAL_FAILURES
    return {
        "stage": stage,
        "task_id": task_id,
        "error_class": type(exc).__name__,
        "error_message": str(exc),
        "failure_signature": signature,
        "retry_count": retry_count,
        "max_identical_failures": MAX_IDENTICAL_FAILURES,
        "stop_triggered": should_stop,
        "observed_at": _utc_now(),
        "traceback": "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        ).strip(),
    }


def _record_failure(stage: str, task_id: str | None, exc: Exception) -> dict[str, Any]:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    payload = _build_failure_payload(stage, task_id, exc)
    save_json(FAILURE_PATH, payload)
    if payload["stop_triggered"]:
        STOP_PATH.parent.mkdir(parents=True, exist_ok=True)
        STOP_PATH.write_text("reviewer_loop repeated identical failure\n", encoding="utf-8")
    return payload


def _clear_failure_record() -> None:
    if FAILURE_PATH.exists():
        FAILURE_PATH.unlink()


def tick() -> None:
    try:
        queue = load_json(QUEUE_PATH, [])
    except Exception as exc:
        raise ReviewerLoopFailure("queue_load", None, exc) from exc
    try:
        state = load_json(STATE_PATH, {})
    except Exception as exc:
        raise ReviewerLoopFailure("state_load", None, exc) from exc

    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    pending_reviews = []
    current_task_id: str | None = None
    try:
        for task in queue:
            current_task_id = task["id"]
            if task["status"] != "done":
                continue
            review_path = REVIEW_DIR / f"{task['id']}.json"
            if review_path.exists():
                continue
            payload = {
                "task_id": task["id"],
                "title": task["title"],
                "phase": task["phase"],
                "branch": task["branch"],
                "files": task["files"],
                "success_criteria": task["success_criteria"],
            }
            save_json(review_path, payload)
    except Exception as exc:
        raise ReviewerLoopFailure("review_manifest", current_task_id, exc) from exc

    try:
        state["review_queue"] = pending_reviews
        save_json(STATE_PATH, state)
    except Exception as exc:
        raise ReviewerLoopFailure("state_write", None, exc) from exc

    print(f"Pending reviews: {len(pending_reviews)}")


def run_cycle() -> bool:
    try:
        tick()
    except ReviewerLoopFailure as exc:
        payload = _record_failure(exc.stage, exc.task_id, exc.cause)
        print(
            "Reviewer loop failure: "
            f"stage={payload['stage']} task_id={payload['task_id']} "
            f"error_class={payload['error_class']} retry_count={payload['retry_count']} "
            f"stop_triggered={payload['stop_triggered']}"
        )
        return False
    except Exception as exc:  # pragma: no cover - defensive fallthrough
        payload = _record_failure("reviewer_loop", None, exc)
        print(
            "Reviewer loop failure: "
            f"stage={payload['stage']} task_id={payload['task_id']} "
            f"error_class={payload['error_class']} retry_count={payload['retry_count']} "
            f"stop_triggered={payload['stop_triggered']}"
        )
        return False

    _clear_failure_record()
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--poll-seconds", type=int, default=180)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    while True:
        run_cycle()
        if args.once:
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()

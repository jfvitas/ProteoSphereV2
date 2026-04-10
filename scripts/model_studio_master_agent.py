from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.model_studio_task_catalog import PROGRAMS, WORKSTREAMS, build_model_studio_tasks
from scripts.tasklib import save_json, task_counts, validate_queue

REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = REPO_ROOT / "tasks" / "model_studio_task_queue.json"
STATE_PATH = REPO_ROOT / "artifacts" / "status" / "model_studio_master_agent_state.json"
PREVIEW_PATH = REPO_ROOT / "artifacts" / "status" / "model_studio_program_preview.json"


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def build_program_preview() -> dict:
    tasks = build_model_studio_tasks()
    return {
        "program_id": "model-studio-program:v1",
        "generated_at": _utc_now(),
        "task_count": len(tasks),
        "program_count": len(PROGRAMS),
        "workstream_count": len(WORKSTREAMS),
        "phase_count": 5,
        "queue_counts": task_counts(tasks),
        "worker_lanes": [
            "frontend-shell-workers",
            "frontend-workspace-workers",
            "backend-api-workers",
            "backend-orchestration-workers",
            "data-pipeline-workers",
            "graph-feature-workers",
            "model-runtime-workers",
            "recommendation-engine-workers",
            "qa-automation-workers",
            "visual-review-workers",
            "usability-sim-workers",
            "refactor-hardening-workers",
            "docs-enablement-workers",
        ],
        "reviewer_lanes": [
            "architecture-reviewer",
            "contract-schema-reviewer",
            "ux-visual-reviewer",
            "scientific-data-quality-reviewer",
            "training-runtime-reviewer",
            "qa-reliability-reviewer",
            "refactoring-reviewer",
        ],
        "programs": [
            {
                "program_id": definition.program_id,
                "slug": definition.slug,
                "title": definition.title,
                "base_path": definition.base_path,
            }
            for definition in PROGRAMS
        ],
        "paths": {
            "queue_path": str(QUEUE_PATH),
            "state_path": str(STATE_PATH),
            "preview_path": str(PREVIEW_PATH),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the Model Studio master-agent queue.")
    parser.add_argument("--write-queue", action="store_true")
    args = parser.parse_args()

    tasks = build_model_studio_tasks()
    errors = validate_queue(tasks)
    if errors:
        raise SystemExit("\n".join(errors))

    preview = build_program_preview()
    save_json(PREVIEW_PATH, preview)
    save_json(
        STATE_PATH,
        {
            "program_id": preview["program_id"],
            "generated_at": preview["generated_at"],
            "status": "ready",
            "task_count": len(tasks),
            "active_workers": [],
            "review_queue": [],
            "dispatch_queue": [],
            "notes": [
                "Model Studio uses a dedicated queue so the broader platform queue stays stable.",
                (
                    "This master-agent state is intended to be consumed by a future "
                    "Studio orchestrator extension."
                ),
            ],
        },
    )
    if args.write_queue:
        save_json(QUEUE_PATH, tasks)
    print(PREVIEW_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

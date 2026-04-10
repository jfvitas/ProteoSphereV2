from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts.repair_overnight_queue import repair_queue


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_repair_demotes_stale_dispatch_and_seeds_ready_tasks(tmp_path: Path) -> None:
    queue_path = tmp_path / "tasks" / "task_queue.json"
    state_path = tmp_path / "artifacts" / "status" / "orchestrator_state.json"
    dispatch_dir = tmp_path / "artifacts" / "dispatch"
    report_path = tmp_path / "artifacts" / "status" / "repair_report.json"
    now = datetime(2026, 4, 3, 21, 0, tzinfo=UTC)

    _write_json(
        queue_path,
        [
            {
                "id": "BASE-T001",
                "title": "Base done task",
                "type": "coding",
                "phase": 1,
                "files": ["scripts/base_done.py"],
                "dependencies": [],
                "status": "done",
                "success_criteria": ["done"],
                "priority": "high",
                "branch": "codex/task/BASE-T001-base-done-task",
                "notes": "",
            },
            {
                "id": "BASE-T002",
                "title": "Stale dispatched task",
                "type": "coding",
                "phase": 1,
                "files": ["scripts/stale_task.py"],
                "dependencies": ["BASE-T001"],
                "status": "dispatched",
                "success_criteria": ["repair me"],
                "priority": "high",
                "branch": "codex/task/BASE-T002-stale-dispatched-task",
                "notes": "",
            },
        ],
    )
    _write_json(
        state_path,
        {
            "active_workers": [{"task_id": "BASE-T002", "type": "coding", "gpu_heavy": False}],
            "completed_tasks": ["BASE-T001"],
            "failed_tasks": [],
            "blocked_tasks": [],
            "review_queue": [],
            "dispatch_queue": ["BASE-T002"],
        },
    )

    dispatch_dir.mkdir(parents=True, exist_ok=True)
    manifest = dispatch_dir / "BASE-T002.json"
    manifest.write_text("{}", encoding="utf-8")
    old_timestamp = (now - timedelta(hours=24)).timestamp()
    manifest.touch()
    import os

    os.utime(manifest, (old_timestamp, old_timestamp))

    report = repair_queue(
        queue_path=queue_path,
        state_path=state_path,
        dispatch_dir=dispatch_dir,
        report_path=report_path,
        stale_after_hours=6,
        seed_tasks=True,
        now=now,
    )

    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    queue_by_id = {task["id"]: task for task in queue}
    state = json.loads(state_path.read_text(encoding="utf-8"))

    assert report["demoted_stale_dispatches"] == ["BASE-T002"]
    assert queue_by_id["BASE-T002"]["status"] == "ready"
    assert "OVR-T001" in report["seeded_task_ids"]
    assert queue_by_id["OVR-T001"]["status"] == "ready"
    assert state["active_workers"] == []
    assert state["dispatch_queue"] == []
    assert not manifest.exists()
    assert report_path.exists()


def test_repair_leaves_fresh_dispatch_untouched_when_manifest_is_recent(tmp_path: Path) -> None:
    queue_path = tmp_path / "tasks" / "task_queue.json"
    state_path = tmp_path / "artifacts" / "status" / "orchestrator_state.json"
    dispatch_dir = tmp_path / "artifacts" / "dispatch"
    report_path = tmp_path / "artifacts" / "status" / "repair_report.json"
    now = datetime(2026, 4, 3, 21, 0, tzinfo=UTC)

    _write_json(
        queue_path,
        [
            {
                "id": "BASE-T003",
                "title": "Fresh dispatched task",
                "type": "coding",
                "phase": 1,
                "files": ["scripts/fresh_task.py"],
                "dependencies": [],
                "status": "dispatched",
                "success_criteria": ["keep me"],
                "priority": "high",
                "branch": "codex/task/BASE-T003-fresh-dispatched-task",
                "notes": "",
            }
        ],
    )
    _write_json(
        state_path,
        {
            "active_workers": [{"task_id": "BASE-T003", "type": "coding", "gpu_heavy": False}],
            "completed_tasks": [],
            "failed_tasks": [],
            "blocked_tasks": [],
            "review_queue": [],
            "dispatch_queue": ["BASE-T003"],
        },
    )

    dispatch_dir.mkdir(parents=True, exist_ok=True)
    manifest = dispatch_dir / "BASE-T003.json"
    manifest.write_text("{}", encoding="utf-8")

    report = repair_queue(
        queue_path=queue_path,
        state_path=state_path,
        dispatch_dir=dispatch_dir,
        report_path=report_path,
        stale_after_hours=6,
        seed_tasks=False,
        now=now,
    )

    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    assert report["demoted_stale_dispatches"] == []
    assert queue[0]["status"] == "dispatched"
    assert manifest.exists()

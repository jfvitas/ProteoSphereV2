from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts.export_overnight_queue_repair_status import main


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_repair_status_reports_repaired_and_redispatched_ids(tmp_path: Path) -> None:
    queue_path = tmp_path / "tasks" / "task_queue.json"
    state_path = tmp_path / "artifacts" / "status" / "orchestrator_state.json"
    repair_report_path = tmp_path / "artifacts" / "status" / "overnight_queue_repair_report.json"
    dispatch_dir = tmp_path / "artifacts" / "dispatch"
    output_json = tmp_path / "artifacts" / "status" / "overnight_queue_repair_status.json"
    output_md = tmp_path / "docs" / "reports" / "overnight_queue_repair_status.md"
    now = datetime(2026, 4, 3, 21, 0, tzinfo=UTC)

    _write_json(
        queue_path,
        [
            {
                "id": "BASE-T001",
                "title": "Redispatched task",
                "type": "coding",
                "phase": 1,
                "files": ["scripts/redispatched_task.py"],
                "dependencies": [],
                "status": "dispatched",
                "success_criteria": ["keep visible"],
                "priority": "high",
                "branch": "codex/task/BASE-T001-redispatched-task",
                "notes": "",
            },
            {
                "id": "BASE-T002",
                "title": "Recovered idle task",
                "type": "coding",
                "phase": 1,
                "files": ["scripts/recovered_idle_task.py"],
                "dependencies": [],
                "status": "pending",
                "success_criteria": ["keep visible"],
                "priority": "high",
                "branch": "codex/task/BASE-T002-recovered-idle-task",
                "notes": "",
            },
        ],
    )
    _write_json(
        state_path,
        {
            "active_workers": [{"task_id": "BASE-T001", "type": "coding", "gpu_heavy": False}],
            "completed_tasks": [],
            "failed_tasks": [],
            "blocked_tasks": [],
            "review_queue": [],
            "dispatch_queue": ["BASE-T001"],
        },
    )
    _write_json(
        repair_report_path,
        {
            "repaired_at": "2026-04-03T20:52:27.973613+00:00",
            "stale_after_hours": 6,
            "demoted_stale_dispatches": ["BASE-T001", "BASE-T002"],
            "deleted_dispatch_manifests": ["BASE-T001"],
            "seeded_task_ids": [],
            "queue_counts": {"pending": 1, "dispatched": 1},
            "active_worker_ids": [],
        },
    )

    dispatch_dir.mkdir(parents=True, exist_ok=True)
    manifest = dispatch_dir / "BASE-T001.json"
    manifest.write_text("{}", encoding="utf-8")
    old_timestamp = (now - timedelta(minutes=30)).timestamp()
    manifest.touch()
    import os

    os.utime(manifest, (old_timestamp, old_timestamp))

    main(
        [
            "--queue-path",
            str(queue_path),
            "--state-path",
            str(state_path),
            "--repair-report-path",
            str(repair_report_path),
            "--dispatch-dir",
            str(dispatch_dir),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--observed-at",
            now.isoformat(),
        ]
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["recovery_state"] == "repaired_and_redispatched"
    assert payload["recovered_and_redispatched_ids"] == ["BASE-T001"]
    assert payload["recovered_and_idle_ids"] == ["BASE-T002"]
    assert payload["current_stale_dispatch_ids"] == []
    assert payload["state_summary"]["active_worker_count"] == 1
    assert "Recovery state: `repaired_and_redispatched`" in output_md.read_text(encoding="utf-8")


def test_repair_status_flags_current_stale_dispatch_when_report_missing(tmp_path: Path) -> None:
    queue_path = tmp_path / "tasks" / "task_queue.json"
    state_path = tmp_path / "artifacts" / "status" / "orchestrator_state.json"
    repair_report_path = tmp_path / "artifacts" / "status" / "overnight_queue_repair_report.json"
    dispatch_dir = tmp_path / "artifacts" / "dispatch"
    output_json = tmp_path / "artifacts" / "status" / "overnight_queue_repair_status.json"
    output_md = tmp_path / "docs" / "reports" / "overnight_queue_repair_status.md"
    now = datetime(2026, 4, 3, 21, 0, tzinfo=UTC)

    _write_json(
        queue_path,
        [
            {
                "id": "BASE-T003",
                "title": "Stale candidate task",
                "type": "coding",
                "phase": 1,
                "files": ["scripts/stale_candidate_task.py"],
                "dependencies": [],
                "status": "dispatched",
                "success_criteria": ["keep visible"],
                "priority": "high",
                "branch": "codex/task/BASE-T003-stale-candidate-task",
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
    stale_timestamp = (now - timedelta(hours=12)).timestamp()
    manifest.touch()
    import os

    os.utime(manifest, (stale_timestamp, stale_timestamp))

    main(
        [
            "--queue-path",
            str(queue_path),
            "--state-path",
            str(state_path),
            "--repair-report-path",
            str(repair_report_path),
            "--dispatch-dir",
            str(dispatch_dir),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--observed-at",
            now.isoformat(),
        ]
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["recovery_state"] == "report_missing"
    assert payload["current_stale_dispatch_ids"] == ["BASE-T003"]
    assert payload["summary"]["current_stale_dispatch_count"] == 1
    assert "Current Stale Candidates" in output_md.read_text(encoding="utf-8")

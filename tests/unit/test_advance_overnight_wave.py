from __future__ import annotations

import json
from pathlib import Path

from scripts.tasklib import save_json


def _write_queue_and_state(
    tmp_path: Path,
    queue: list[dict],
    state: dict | None = None,
) -> tuple[Path, Path]:
    queue_path = tmp_path / "task_queue.json"
    state_path = tmp_path / "orchestrator_state.json"
    save_json(queue_path, queue)
    save_json(state_path, state or {})
    return queue_path, state_path


def test_advance_overnight_wave_runs_sequentially_and_reports_counts(tmp_path, monkeypatch):
    from scripts import advance_overnight_wave as wave

    queue_path, state_path = _write_queue_and_state(
        tmp_path,
        [
            {
                "id": "P1",
                "title": "Initial task",
                "type": "coding",
                "phase": 1,
                "files": ["src/a.py"],
                "dependencies": [],
                "status": "pending",
                "success_criteria": ["ok"],
                "priority": "high",
                "branch": "codex/task/P1-initial-task",
                "notes": "",
            }
        ],
        {"active_workers": []},
    )
    sequence: list[str] = []

    monkeypatch.setattr(wave, "QUEUE_PATH", queue_path)
    monkeypatch.setattr(wave, "STATE_PATH", state_path)

    def fake_replenish_queue(*, threshold: int, batch_size: int) -> int:
        sequence.append("auto_task_generator")
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue.append(
            {
                "id": "P2",
                "title": "Recovered task",
                "type": "coding",
                "phase": 1,
                "files": ["src/b.py"],
                "dependencies": [],
                "status": "pending",
                "success_criteria": ["ok"],
                "priority": "medium",
                "branch": "codex/task/P2-recovered-task",
                "notes": "",
            }
        )
        save_json(queue_path, queue)
        return 1

    def fake_tick(limits: dict[str, int]) -> None:
        sequence.append("orchestrator")
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue[0]["status"] = "dispatched"
        save_json(queue_path, queue)
        save_json(
            state_path,
            {
                "active_workers": [
                    {
                        "task_id": "P1",
                        "type": "coding",
                        "gpu_heavy": False,
                        "branch": "codex/task/P1-initial-task",
                    }
                ],
                "dispatch_queue": ["P1"],
                "review_queue": [],
                "completed_tasks": [],
                "blocked_tasks": [],
            },
        )

    monkeypatch.setattr(wave, "replenish_queue", fake_replenish_queue)
    monkeypatch.setattr(wave, "orchestrator_tick", fake_tick)

    report = wave.advance_overnight_wave(threshold=3, batch_size=1, run_monitor=False)

    assert sequence == ["auto_task_generator", "orchestrator"]
    assert report["pre_queue_total"] == 1
    assert report["post_queue_total"] == 2
    assert report["added_task_count"] == 1
    assert report["dispatched_count"] == 1
    assert report["active_worker_count"] == 1
    assert report["catalog_exhausted"] is False
    assert report["execution_order"] == ["auto_task_generator", "orchestrator"]
    assert report["monitor_summary"]["status"] == "skipped"


def test_advance_overnight_wave_marks_catalog_exhausted_and_includes_monitor(
    tmp_path,
    monkeypatch,
):
    from scripts import advance_overnight_wave as wave

    queue_path, state_path = _write_queue_and_state(
        tmp_path,
        [
            {
                "id": "A",
                "title": "Task A",
                "type": "coding",
                "phase": 1,
                "files": ["src/a.py"],
                "dependencies": [],
                "status": "pending",
                "success_criteria": ["ok"],
                "priority": "high",
                "branch": "codex/task/A-task-a",
                "notes": "",
            },
            {
                "id": "B",
                "title": "Task B",
                "type": "coding",
                "phase": 1,
                "files": ["src/b.py"],
                "dependencies": [],
                "status": "ready",
                "success_criteria": ["ok"],
                "priority": "high",
                "branch": "codex/task/B-task-b",
                "notes": "",
            },
        ],
        {"active_workers": [{"task_id": "B"}], "dispatch_queue": ["B"], "review_queue": []},
    )
    sequence: list[str] = []

    monkeypatch.setattr(wave, "QUEUE_PATH", queue_path)
    monkeypatch.setattr(wave, "STATE_PATH", state_path)
    monkeypatch.setattr(wave, "_catalog_task_ids", lambda: {"A", "B"})

    def fake_replenish_queue(*, threshold: int, batch_size: int) -> int:
        sequence.append("auto_task_generator")
        return 0

    def fake_tick(limits: dict[str, int]) -> None:
        sequence.append("orchestrator")

    def fake_build_monitor_snapshot(queue, state, *, observed_at=None):
        sequence.append("monitor")
        return {
            "ready_count": 0,
            "active_worker_count": len(state.get("active_workers", [])),
            "dispatch_queue_count": len(state.get("dispatch_queue", [])),
            "review_queue_count": len(state.get("review_queue", [])),
            "blocked_count": 0,
            "done_count": 0,
            "queue_counts": {"done": 0, "ready": 0},
        }

    def fake_evaluate_alerts(
        snapshot,
        previous_snapshot,
        *,
        heartbeat=None,
        now=None,
        stagnation_seconds=900,
    ):
        return []

    monkeypatch.setattr(wave, "replenish_queue", fake_replenish_queue)
    monkeypatch.setattr(wave, "orchestrator_tick", fake_tick)
    monkeypatch.setattr(wave, "build_monitor_snapshot", fake_build_monitor_snapshot)
    monkeypatch.setattr(wave, "evaluate_alerts", fake_evaluate_alerts)

    report = wave.advance_overnight_wave(threshold=1, batch_size=1, run_monitor=True)

    assert sequence == ["auto_task_generator", "orchestrator", "monitor"]
    assert report["catalog_exhausted"] is True
    assert report["execution_order"] == ["auto_task_generator", "orchestrator", "monitor"]
    assert report["monitor_summary"]["alerts"] == []
    assert report["monitor_summary"]["snapshot"]["active_worker_count"] == 1


def test_main_can_emit_json(tmp_path, monkeypatch, capsys):
    from scripts import advance_overnight_wave as wave

    queue_path, state_path = _write_queue_and_state(tmp_path, [], {})
    monkeypatch.setattr(wave, "QUEUE_PATH", queue_path)
    monkeypatch.setattr(wave, "STATE_PATH", state_path)
    monkeypatch.setattr(wave, "replenish_queue", lambda *, threshold, batch_size: 0)
    monkeypatch.setattr(wave, "orchestrator_tick", lambda limits: None)
    monkeypatch.setattr(
        wave,
        "build_monitor_snapshot",
        lambda queue, state, *, observed_at=None: {
            "ready_count": 0,
            "active_worker_count": 0,
            "dispatch_queue_count": 0,
            "review_queue_count": 0,
            "blocked_count": 0,
            "done_count": 0,
            "queue_counts": {},
        },
    )
    monkeypatch.setattr(
        wave,
        "evaluate_alerts",
        lambda snapshot, previous_snapshot, *, heartbeat=None, now=None, stagnation_seconds=900: [],
    )

    output_json = tmp_path / "overnight_wave_advance_preview.json"
    exit_code = wave.main(
        ["--json", "--run-monitor", "--output-json", str(output_json)]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    saved_payload = json.loads(output_json.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert payload["status"] == "ok"
    assert saved_payload["status"] == "ok"
    assert payload["monitor_summary"]["alerts"] == []
    assert payload["execution_order"] == ["auto_task_generator", "orchestrator", "monitor"]

from __future__ import annotations

import json
from pathlib import Path

from scripts import model_studio_orchestrator as orchestrator


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_model_studio_orchestrator_dispatches_ready_tasks(tmp_path, monkeypatch) -> None:
    queue_path = tmp_path / "tasks" / "model_studio_task_queue.json"
    state_path = tmp_path / "artifacts" / "status" / "model_studio_orchestrator_state.json"
    dispatch_dir = tmp_path / "artifacts" / "dispatch" / "model_studio"
    queue = [
        {
            "id": "MS01",
            "title": "Model Studio coding task",
            "type": "coding",
            "phase": 20,
            "files": ["api/model_studio/demo.py", "tests/unit/model_studio/test_demo.py"],
            "dependencies": [],
            "status": "pending",
            "success_criteria": ["ready task is dispatched"],
            "priority": "high",
            "branch": "codex/task/MS01-demo",
            "notes": "",
        }
    ]
    _write_json(queue_path, queue)
    monkeypatch.setattr(orchestrator, "QUEUE_PATH", queue_path)
    monkeypatch.setattr(orchestrator, "STATE_PATH", state_path)
    monkeypatch.setattr(orchestrator, "DISPATCH_DIR", dispatch_dir)

    orchestrator.tick(
        {
            "coding": 1,
            "analysis": 0,
            "integration": 0,
            "docs": 0,
            "tests": 0,
            "gpu": 0,
        }
    )

    updated_queue = json.loads(queue_path.read_text(encoding="utf-8"))
    assert updated_queue[0]["status"] == "dispatched"
    assert (dispatch_dir / "MS01.json").exists()


def test_model_studio_orchestrator_respects_overlap_conflicts(tmp_path, monkeypatch) -> None:
    queue_path = tmp_path / "tasks" / "model_studio_task_queue.json"
    state_path = tmp_path / "artifacts" / "status" / "model_studio_orchestrator_state.json"
    dispatch_dir = tmp_path / "artifacts" / "dispatch" / "model_studio"
    queue = [
        {
            "id": "MS01",
            "title": "First task",
            "type": "coding",
            "phase": 20,
            "files": ["api/model_studio/shared.py"],
            "dependencies": [],
            "status": "ready",
            "success_criteria": ["first dispatches"],
            "priority": "high",
            "branch": "codex/task/MS01-first",
            "notes": "",
        },
        {
            "id": "MS02",
            "title": "Second task",
            "type": "coding",
            "phase": 20,
            "files": ["api/model_studio/shared.py"],
            "dependencies": [],
            "status": "ready",
            "success_criteria": ["second waits"],
            "priority": "medium",
            "branch": "codex/task/MS02-second",
            "notes": "",
        },
    ]
    _write_json(queue_path, queue)
    monkeypatch.setattr(orchestrator, "QUEUE_PATH", queue_path)
    monkeypatch.setattr(orchestrator, "STATE_PATH", state_path)
    monkeypatch.setattr(orchestrator, "DISPATCH_DIR", dispatch_dir)

    orchestrator.tick(
        {
            "coding": 2,
            "analysis": 0,
            "integration": 0,
            "docs": 0,
            "tests": 0,
            "gpu": 0,
        }
    )

    updated_queue = json.loads(queue_path.read_text(encoding="utf-8"))
    assert updated_queue[0]["status"] == "dispatched"
    assert updated_queue[1]["status"] == "ready"

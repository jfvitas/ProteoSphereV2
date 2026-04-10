from scripts.reviewer_loop import run_cycle, tick
from scripts.tasklib import load_json, save_json


def test_reviewer_loop_creates_manifest(tmp_path, monkeypatch):
    queue_path = tmp_path / "task_queue.json"
    state_path = tmp_path / "orchestrator_state.json"
    review_dir = tmp_path / "reviews"
    save_json(
        queue_path,
        [
            {
                "id": "P1-T001",
                "title": "Task",
                "phase": 1,
                "branch": "task/P1-T001-task",
                "files": ["foo.py"],
                "status": "done",
                "success_criteria": ["ok"],
            }
        ],
    )
    save_json(state_path, {})
    monkeypatch.setattr("scripts.reviewer_loop.QUEUE_PATH", queue_path)
    monkeypatch.setattr("scripts.reviewer_loop.STATE_PATH", state_path)
    monkeypatch.setattr("scripts.reviewer_loop.REVIEW_DIR", review_dir)
    tick()
    assert (review_dir / "P1-T001.json").exists()
    state = load_json(state_path, {})
    assert state["review_queue"] == []


def test_reviewer_loop_records_structured_failure_envelope(tmp_path, monkeypatch):
    queue_path = tmp_path / "task_queue.json"
    state_path = tmp_path / "orchestrator_state.json"
    review_dir = tmp_path / "reviews"
    runtime_dir = tmp_path / "runtime"
    failure_path = runtime_dir / "reviewer_cycle_failure.json"
    stop_path = tmp_path / "STOP"

    save_json(
        queue_path,
        [
            {
                "id": "P1-T001",
                "phase": 1,
                "branch": "task/P1-T001-task",
                "files": ["foo.py"],
                "status": "done",
                "success_criteria": ["ok"],
            }
        ],
    )
    save_json(state_path, {})
    monkeypatch.setattr("scripts.reviewer_loop.QUEUE_PATH", queue_path)
    monkeypatch.setattr("scripts.reviewer_loop.STATE_PATH", state_path)
    monkeypatch.setattr("scripts.reviewer_loop.REVIEW_DIR", review_dir)
    monkeypatch.setattr("scripts.reviewer_loop.RUNTIME_DIR", runtime_dir)
    monkeypatch.setattr("scripts.reviewer_loop.FAILURE_PATH", failure_path)
    monkeypatch.setattr("scripts.reviewer_loop.STOP_PATH", stop_path)

    succeeded = run_cycle()

    assert succeeded is False
    payload = failure_path.read_text(encoding="utf-8")
    assert "review_manifest" in payload
    assert "P1-T001" in payload
    assert stop_path.exists() is False


def test_reviewer_loop_stops_after_repeated_identical_failures(tmp_path, monkeypatch):
    queue_path = tmp_path / "task_queue.json"
    state_path = tmp_path / "orchestrator_state.json"
    review_dir = tmp_path / "reviews"
    runtime_dir = tmp_path / "runtime"
    failure_path = runtime_dir / "reviewer_cycle_failure.json"
    stop_path = tmp_path / "STOP"

    save_json(
        queue_path,
        [
            {
                "id": "P1-T001",
                "phase": 1,
                "branch": "task/P1-T001-task",
                "files": ["foo.py"],
                "status": "done",
                "success_criteria": ["ok"],
            }
        ],
    )
    save_json(state_path, {})
    monkeypatch.setattr("scripts.reviewer_loop.QUEUE_PATH", queue_path)
    monkeypatch.setattr("scripts.reviewer_loop.STATE_PATH", state_path)
    monkeypatch.setattr("scripts.reviewer_loop.REVIEW_DIR", review_dir)
    monkeypatch.setattr("scripts.reviewer_loop.RUNTIME_DIR", runtime_dir)
    monkeypatch.setattr("scripts.reviewer_loop.FAILURE_PATH", failure_path)
    monkeypatch.setattr("scripts.reviewer_loop.STOP_PATH", stop_path)

    for _ in range(3):
        assert run_cycle() is False

    payload = failure_path.read_text(encoding="utf-8")
    assert '"retry_count": 3' in payload
    assert '"stop_triggered": true' in payload
    assert stop_path.exists() is True

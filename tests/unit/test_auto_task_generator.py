from scripts.auto_task_generator import replenish_queue
from scripts.task_catalog import build_initial_queue
from scripts.tasklib import save_json


def test_replenish_does_not_duplicate_existing_queue(tmp_path, monkeypatch):
    queue_path = tmp_path / "task_queue.json"
    state_path = tmp_path / "orchestrator_state.json"
    queue = build_initial_queue()
    save_json(queue_path, queue)
    save_json(state_path, {})
    monkeypatch.setattr("scripts.auto_task_generator.QUEUE_PATH", queue_path)
    monkeypatch.setattr("scripts.auto_task_generator.STATE_PATH", state_path)
    assert replenish_queue(threshold=200, batch_size=25) == 0

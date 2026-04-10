from scripts.task_catalog import build_initial_queue
from scripts.tasklib import validate_queue


def test_initial_queue_size_and_validity():
    queue = build_initial_queue()
    assert 200 <= len(queue) <= 400
    assert not validate_queue(queue)


def test_queue_contains_all_required_task_types():
    queue = build_initial_queue()
    task_types = {task["type"] for task in queue}
    assert {"coding", "data_analysis", "integration"} <= task_types

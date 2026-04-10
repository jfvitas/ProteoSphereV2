from __future__ import annotations

from scripts.model_studio_master_agent import build_program_preview
from scripts.model_studio_task_catalog import PROGRAMS, WORKSTREAMS, build_model_studio_tasks
from scripts.tasklib import validate_queue


def test_model_studio_task_catalog_is_large_and_valid() -> None:
    tasks = build_model_studio_tasks()
    assert len(tasks) == len(PROGRAMS) * len(WORKSTREAMS) * 5 * 3
    assert not validate_queue(tasks)


def test_model_studio_preview_reports_expected_shape() -> None:
    preview = build_program_preview()
    assert preview["program_count"] == len(PROGRAMS)
    assert preview["workstream_count"] == len(WORKSTREAMS)
    assert preview["task_count"] == len(build_model_studio_tasks())

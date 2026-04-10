from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.install_proteosphere import install_proteosphere, main


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _make_clean_repo_skeleton(repo_root: Path) -> None:
    for relative_path in (
        "scripts",
        "tasks",
        "artifacts/status",
        "artifacts/reports",
        "artifacts/blockers",
        "artifacts/reviews",
        "artifacts/planner",
        "artifacts/dispatch",
        "docs/reports",
    ):
        (repo_root / relative_path).mkdir(parents=True, exist_ok=True)

    for relative_path in (
        "scripts/bootstrap_repo.py",
        "scripts/orchestrator.py",
        "scripts/monitor.py",
        "scripts/tasklib.py",
        "scripts/validate_operator_state.py",
        "scripts/powershell_interface.ps1",
    ):
        (repo_root / relative_path).write_text("# placeholder\n", encoding="utf-8")


def test_install_proteosphere_bootstraps_and_verifies_clean_machine(tmp_path: Path) -> None:
    repo_root = tmp_path / "proteosphere"
    repo_root.mkdir()
    _make_clean_repo_skeleton(repo_root)

    output_path = repo_root / "artifacts" / "status" / "install_bootstrap_state.json"
    payload = install_proteosphere(repo_root=repo_root, output_path=output_path, bootstrap=True)
    saved = _read_json(output_path)

    assert payload == saved
    assert payload["status"] == "ready"
    assert payload["bootstrap_verified"] is True
    assert payload["dependency_verified"] is True
    assert payload["dependency_report"]["status"] == "ready"
    assert payload["bootstrap_report"]["status"] == "ready"
    assert payload["missing_dependencies"] == []
    assert payload["missing_bootstrap_paths"] == []

    queue_path = repo_root / "tasks" / "task_queue.json"
    orchestrator_state_path = repo_root / "artifacts" / "status" / "orchestrator_state.json"
    assert queue_path.exists()
    assert orchestrator_state_path.exists()
    assert json.loads(queue_path.read_text(encoding="utf-8")) == []

    orchestrator_state = _read_json(orchestrator_state_path)
    assert orchestrator_state == {
        "active_workers": [],
        "completed_tasks": [],
        "failed_tasks": [],
        "blocked_tasks": [],
        "review_queue": [],
        "dispatch_queue": [],
        "last_task_generation_ts": None,
    }


def test_install_proteosphere_blocks_when_required_dependency_is_missing(tmp_path: Path) -> None:
    repo_root = tmp_path / "proteosphere"
    repo_root.mkdir()
    _make_clean_repo_skeleton(repo_root)
    (repo_root / "scripts" / "monitor.py").unlink()

    payload = install_proteosphere(
        repo_root=repo_root,
        output_path=repo_root / "artifacts" / "status" / "install_bootstrap_state.json",
        bootstrap=True,
    )

    assert payload["status"] == "blocked"
    assert payload["dependency_report"]["status"] == "blocked"
    assert payload["bootstrap_report"]["status"] == "ready"
    assert "scripts/monitor.py" in payload["missing_dependencies"]


def test_main_honors_cli_arguments(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = tmp_path / "proteosphere"
    repo_root.mkdir()
    _make_clean_repo_skeleton(repo_root)

    output_path = repo_root / "artifacts" / "status" / "install_bootstrap_state.json"
    main(
        [
            "--repo-root",
            str(repo_root),
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["status"] == "ready"
    assert output_path.exists()
    assert payload == _read_json(output_path)

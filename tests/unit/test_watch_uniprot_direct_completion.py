from __future__ import annotations

import json
from pathlib import Path

from scripts import watch_uniprot_direct_completion as watcher


def test_evaluate_watch_state_waits_for_active_process(tmp_path: Path) -> None:
    uniprot_dir = tmp_path / "uniprot"
    uniprot_dir.mkdir(parents=True, exist_ok=True)
    state = watcher.evaluate_watch_state(uniprot_dir=uniprot_dir, active_pids=(1234,))

    assert state.status == "waiting_for_process"
    assert state.active_pids == (1234,)


def test_evaluate_watch_state_waits_for_partial_cleanup(tmp_path: Path) -> None:
    uniprot_dir = tmp_path / "uniprot"
    uniprot_dir.mkdir(parents=True, exist_ok=True)
    (uniprot_dir / "idmapping.dat.gz.part").write_text("", encoding="utf-8")

    state = watcher.evaluate_watch_state(uniprot_dir=uniprot_dir, active_pids=())

    assert state.status == "waiting_for_partial_cleanup"
    assert state.partial_files == ("idmapping.dat.gz.part",)


def test_evaluate_watch_state_is_ready_when_required_files_exist(tmp_path: Path) -> None:
    uniprot_dir = tmp_path / "uniprot"
    uniprot_dir.mkdir(parents=True, exist_ok=True)
    for filename in watcher.REQUIRED_UNIPROT_FILES:
        (uniprot_dir / filename).write_text("ok", encoding="utf-8")

    state = watcher.evaluate_watch_state(uniprot_dir=uniprot_dir, active_pids=())

    assert state.status == "ready"
    assert state.is_ready is True


def test_watch_and_finalize_runs_validation_and_promotion(monkeypatch, tmp_path: Path) -> None:
    uniprot_dir = tmp_path / "uniprot"
    uniprot_dir.mkdir(parents=True, exist_ok=True)
    for filename in watcher.REQUIRED_UNIPROT_FILES:
        (uniprot_dir / filename).write_text("ok", encoding="utf-8")

    validation_path = tmp_path / "validation.json"
    status_path = tmp_path / "watch.json"
    log_path = tmp_path / "watch.log"
    commands: list[list[str]] = []

    class Result:
        def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    monkeypatch.setattr(watcher, "list_active_uniprot_procurement_pids", lambda: ())

    def fake_run_repo_command(args: list[str]) -> Result:
        commands.append(args)
        if args[-1].endswith("validate_protein_data_scope_seed.py"):
            validation_path.write_text(json.dumps({"status": "passed"}), encoding="utf-8")
        return Result(returncode=0)

    monkeypatch.setattr(watcher, "run_repo_command", fake_run_repo_command)

    exit_code = watcher.watch_and_finalize(
        uniprot_dir=uniprot_dir,
        validation_path=validation_path,
        status_path=status_path,
        log_path=log_path,
        poll_seconds=0,
        once=False,
    )

    assert exit_code == 0
    assert commands == [
        ["python", "scripts\\validate_protein_data_scope_seed.py"],
        ["python", "scripts\\promote_protein_data_scope_seed.py"],
        ["python", "scripts\\run_post_tier1_direct_pipeline.py"],
    ]
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["phase"] == "completed"
    assert payload["promotion_status"] == "promoted"
    assert payload["post_pipeline_status"] == "passed"

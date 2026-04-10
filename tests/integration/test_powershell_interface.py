from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _powershell_executable() -> str:
    for candidate in ("powershell.exe", "pwsh.exe"):
        path = shutil.which(candidate)
        if path:
            return path
    raise RuntimeError("PowerShell is required for the operator interface integration test")


def _copy_script_tree(repo_root: Path, temp_root: Path) -> None:
    scripts_dir = temp_root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        repo_root / "scripts" / "powershell_interface.ps1",
        scripts_dir / "powershell_interface.ps1",
    )
    shutil.copy2(repo_root / "scripts" / "monitor.py", scripts_dir / "monitor.py")
    shutil.copy2(repo_root / "scripts" / "tasklib.py", scripts_dir / "tasklib.py")
    shutil.copy2(
        repo_root / "scripts" / "capture_soak_ledger.py",
        scripts_dir / "capture_soak_ledger.py",
    )
    shutil.copy2(
        repo_root / "scripts" / "summarize_soak_ledger.py",
        scripts_dir / "summarize_soak_ledger.py",
    )
    shutil.copy2(
        repo_root / "scripts" / "audit_truth_boundaries.py",
        scripts_dir / "audit_truth_boundaries.py",
    )
    shutil.copy2(
        repo_root / "scripts" / "analyze_soak_anomalies.py",
        scripts_dir / "analyze_soak_anomalies.py",
    )
    shutil.copy2(
        repo_root / "scripts" / "build_operational_readiness_snapshot.py",
        scripts_dir / "build_operational_readiness_snapshot.py",
    )
    shutil.copytree(
        repo_root / "runs" / "real_data_benchmark" / "full_results",
        temp_root / "runs" / "real_data_benchmark" / "full_results",
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _make_temp_repo(tmp_path: Path) -> Path:
    _copy_script_tree(REPO_ROOT, tmp_path)

    queue = [
        {
            "id": "P6-T001",
            "title": "Implement summary library schema",
            "type": "coding",
            "phase": 6,
            "files": ["core/library/summary_record.py"],
            "dependencies": [],
            "status": "done",
            "success_criteria": ["summary record schema exists", "unit tests pass"],
            "priority": "high",
            "branch": "codex/task/P6-T001-implement-summary-library-schema",
            "notes": "",
        },
        {
            "id": "P6-T005",
            "title": "Implement PowerShell operator interface",
            "type": "coding",
            "phase": 6,
            "files": [
                "scripts/powershell_interface.ps1",
                "tests/integration/test_powershell_interface.py",
            ],
            "dependencies": ["SYS-T003", "P6-T003"],
            "status": "ready",
            "success_criteria": [
                "operator interface can inspect queue and library state",
                "integration tests pass",
            ],
            "priority": "medium",
            "branch": "codex/task/P6-T005-implement-powershell-operator-interface",
            "notes": "",
        },
    ]
    _write_json(tmp_path / "tasks" / "task_queue.json", queue)

    _write_json(
        tmp_path / "artifacts" / "status" / "orchestrator_state.json",
        {
            "active_workers": [
                {
                    "task_id": "P5-T005",
                    "type": "coding",
                    "gpu_heavy": False,
                    "branch": "codex/task/P5-T005-implement-multimodal-fusion-model",
                }
            ],
            "completed_tasks": ["P6-T001"],
            "failed_tasks": [],
            "blocked_tasks": ["P1-T010"],
            "review_queue": ["P5-T004"],
            "dispatch_queue": ["P6-T005"],
            "last_task_generation_ts": 1774208418,
        },
    )

    _write_json(
        tmp_path / "artifacts" / "status" / "P6-T001.json",
        {
            "completed_at": "2026-03-22T14:41:00.3354271-05:00",
            "task_id": "P6-T001",
            "status": "done",
            "summary": "summary library schema exists",
            "files": ["core/library/summary_record.py", "tests/unit/core/test_summary_record.py"],
            "verification": [
                "python -m pytest tests\\unit\\core\\test_summary_record.py",
                (
                    "python -m ruff check core\\library\\summary_record.py "
                    "tests\\unit\\core\\test_summary_record.py"
                ),
            ],
            "blockers": [],
        },
    )
    _write_json(
        tmp_path / "artifacts" / "status" / "P6-T003.json",
        {
            "completed_at": "2026-03-22T15:03:55.5131799-05:00",
            "task_id": "P6-T003",
            "status": "done",
            "summary": "summary library builder exists",
            "files": [
                "execution/library/build_summary_library.py",
                "tests/unit/execution/test_build_summary_library.py",
            ],
            "verification": [
                "python -m pytest tests\\unit\\execution\\test_build_summary_library.py",
                (
                    "python -m ruff check execution\\library\\build_summary_library.py "
                    "tests\\unit\\execution\\test_build_summary_library.py"
                ),
            ],
            "blockers": [],
        },
    )
    _write_json(
        tmp_path / "artifacts" / "library" / "summary_library.json",
        {
            "library_id": "summary-library",
            "schema_version": 1,
            "source_manifest_id": "manifest:summary",
            "records": [
                {"summary_id": "protein:P12345", "record_type": "protein"},
                {"summary_id": "pair:ppi:1", "record_type": "protein_protein"},
            ],
            "index_guidance": ["route protein, pair, and ligand summaries accession-first"],
            "storage_guidance": ["treat the summary library as a rebuildable feature-cache layer"],
            "lazy_loading_guidance": ["hydrate heavy source payloads only after selection"],
        },
    )

    return tmp_path


def _run_interface(
    repo_root: Path,
    mode: str,
    *extra_args: str,
) -> subprocess.CompletedProcess[str]:
    command = [
        _powershell_executable(),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(repo_root / "scripts" / "powershell_interface.ps1"),
        "-Mode",
        mode,
        *extra_args,
    ]
    return subprocess.run(
        command,
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_operator_interface_state_mode_reports_queue_library_and_runtime(tmp_path: Path) -> None:
    repo_root = _make_temp_repo(tmp_path / "repo")

    result = _run_interface(repo_root, "state", "-AsJson")
    payload = json.loads(result.stdout)

    assert payload["queue"]["task_count"] == 2
    assert payload["queue"]["status_counts"]["done"] == 1
    assert payload["queue"]["status_counts"]["ready"] == 1
    assert payload["queue"]["ready_task_ids"] == ["P6-T005"]

    assert payload["library"]["schema_task_done"] is True
    assert payload["library"]["builder_task_done"] is True
    assert payload["library"]["materialized"] is True
    assert payload["library"]["materialized_record_count"] == 2
    assert payload["library"]["materialized_library_id"] == "summary-library"
    assert payload["library"]["ready_for_materialization"] is True

    assert payload["benchmark"]["exists"] is True
    assert payload["benchmark"]["benchmark_summary"]["status"] == (
        "blocked_on_release_grade_bar"
    )
    assert payload["benchmark"]["cohort_status"] == (
        "frozen_12_accession_run_complete_on_prototype_runtime"
    )
    assert payload["benchmark"]["release_grade_status"] == "blocked"
    expected_release_blockers = (
        "The runtime is still a local prototype, not the production multimodal trainer stack.",
        "PPI evidence is attached as a sidecar only for the hemoglobin pair and does not "
        "widen the training corpus.",
        "The full benchmark remains bounded by the frozen in-tree cohort and live-derived "
        "evidence available today.",
    )
    assert payload["benchmark"]["release_grade_blockers"][:3] == list(
        expected_release_blockers
    )
    assert len(payload["benchmark"]["release_grade_blockers"]) == len(
        expected_release_blockers
    )
    assert payload["benchmark"]["completion_status"] == "blocked_on_release_grade_bar"
    assert payload["benchmark"]["release_ready"] is False

    assert payload["runtime"]["supervisor_running"] is False
    assert payload["runtime"]["active_worker_count"] == 1
    assert payload["runtime"]["dispatch_queue_count"] == 1
    assert payload["runtime"]["review_queue_count"] == 1
    assert payload["runtime"]["blocked_task_count"] == 1


def test_operator_interface_status_mode_remains_compatible(tmp_path: Path) -> None:
    repo_root = _make_temp_repo(tmp_path / "repo")

    result = _run_interface(repo_root, "status")

    assert "Supervisor: stopped" in result.stdout
    assert "Queue:" in result.stdout
    assert "Active workers:" in result.stdout
    assert "Benchmark release" in result.stdout


def test_operator_interface_surfaces_missing_inputs_explicitly(tmp_path: Path) -> None:
    repo_root = _make_temp_repo(tmp_path / "repo")

    _remove_path(repo_root / "runs" / "real_data_benchmark" / "full_results" / "run_summary.json")
    _remove_path(
        repo_root / "runs" / "real_data_benchmark" / "full_results" / "checkpoint_summary.json"
    )

    result = _run_interface(repo_root, "state", "-AsJson")
    payload = json.loads(result.stdout)

    assert payload["queue"]["error"] is None
    assert payload["library"]["status_files"]["schema"]["error"] is None
    assert payload["benchmark"]["run_summary"]["exists"] is False
    assert "missing input:" in payload["benchmark"]["run_summary"]["error"]
    assert payload["benchmark"]["checkpoint_summary"]["exists"] is False
    assert "missing input:" in payload["benchmark"]["checkpoint_summary"]["error"]
    assert payload["benchmark"]["release_grade_status"] == "blocked"
    missing_blockers = payload["benchmark"]["release_grade_blockers"]
    assert any("missing input:" in blocker for blocker in missing_blockers)
    assert payload["benchmark"]["release_ready"] is False


def test_operator_interface_stop_mode_handles_seeded_pid_file(tmp_path: Path) -> None:
    repo_root = _make_temp_repo(tmp_path / "repo")
    runtime_dir = repo_root / "artifacts" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "supervisor.pid").write_text("999999\n", encoding="utf-8")

    result = _run_interface(repo_root, "stop")

    assert "Supervisor stopped." in result.stdout
    assert not (runtime_dir / "supervisor.pid").exists()


def test_operator_interface_run_once_appends_soak_ledger(tmp_path: Path) -> None:
    repo_root = _make_temp_repo(tmp_path / "repo")

    scripts_dir = repo_root / "scripts"
    (scripts_dir / "orchestrator.py").write_text("print({'done': 1})\n", encoding="utf-8")
    (scripts_dir / "reviewer_loop.py").write_text("print('reviewed')\n", encoding="utf-8")

    result = _run_interface(repo_root, "run-once", "-PollSeconds", "1", "-FullSweepEvery", "0")

    ledger_path = repo_root / "artifacts" / "runtime" / "soak_ledger.jsonl"
    soak_rollup_path = repo_root / "docs" / "reports" / "p22_soak_rollup.md"
    soak_anomaly_path = repo_root / "docs" / "reports" / "p22_soak_anomalies.md"
    truth_audit_path = repo_root / "docs" / "reports" / "p22_truth_boundary_audit.md"
    readiness_snapshot_path = (
        repo_root / "docs" / "reports" / "p22_operational_readiness_snapshot.md"
    )
    assert ledger_path.exists()
    assert soak_rollup_path.exists()
    assert soak_anomaly_path.exists()
    assert truth_audit_path.exists()
    assert readiness_snapshot_path.exists()
    ledger_lines = [line for line in ledger_path.read_text(encoding="utf-8").splitlines() if line]
    assert len(ledger_lines) >= 1
    payload = json.loads(ledger_lines[-1])
    assert payload["truth_boundary"]["weeklong_soak_claim_allowed"] is False
    assert payload["supervisor_heartbeat_history_count"] >= 2
    assert "P22 Rolling Soak Evidence Summary" in soak_rollup_path.read_text(encoding="utf-8")
    soak_anomaly_text = soak_anomaly_path.read_text(encoding="utf-8")
    assert "P22 Soak Anomaly Digest" in soak_anomaly_text
    assert "Incident count" in soak_anomaly_text
    truth_audit_text = truth_audit_path.read_text(encoding="utf-8")
    assert "P22 Truth-Boundary Audit" in truth_audit_text
    assert "Finding count" in truth_audit_text
    readiness_snapshot_text = readiness_snapshot_path.read_text(encoding="utf-8")
    assert "P22 Operational Readiness Snapshot" in readiness_snapshot_text
    assert "Operational readiness ready" in readiness_snapshot_text
    assert "Captured soak ledger entry:" in result.stdout

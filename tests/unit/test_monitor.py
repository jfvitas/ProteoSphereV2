import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts.tasklib import save_json


def test_monitor_inputs_exist(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    save_json(Path("tasks/task_queue.json"), [])
    save_json(Path("artifacts/status/orchestrator_state.json"), {})
    from scripts import monitor

    monkeypatch.setattr(monitor, "_utc_now", lambda: datetime(2026, 3, 22, tzinfo=UTC))
    monitor.main()
    captured = capsys.readouterr()
    assert "Queue:" in captured.out
    assert "Alerts: none" in captured.out


def test_monitor_reports_starvation_for_dependency_ready_pending_work(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.chdir(tmp_path)
    save_json(
        Path("tasks/task_queue.json"),
        [
            {
                "id": "P1",
                "title": "Ready pending task",
                "type": "coding",
                "phase": 1,
                "files": ["foo.py"],
                "dependencies": [],
                "status": "pending",
                "success_criteria": ["done"],
                "priority": "high",
                "branch": "codex/task/P1-ready-pending-task",
                "notes": "",
            }
        ],
    )
    save_json(Path("artifacts/status/orchestrator_state.json"), {})
    from scripts import monitor

    monkeypatch.setattr(monitor, "_utc_now", lambda: datetime(2026, 3, 22, tzinfo=UTC))
    monitor.main()
    captured = capsys.readouterr()
    assert "Dependency-ready pending tasks: 1" in captured.out
    assert "queue starvation:" in captured.out


def test_monitor_suppresses_starvation_during_fresh_cycle_start(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.chdir(tmp_path)
    now = datetime(2026, 3, 22, 0, 0, 30, tzinfo=UTC)
    save_json(
        Path("tasks/task_queue.json"),
        [
            {
                "id": "P1",
                "title": "Ready pending task",
                "type": "coding",
                "phase": 1,
                "files": ["foo.py"],
                "dependencies": [],
                "status": "pending",
                "success_criteria": ["done"],
                "priority": "high",
                "branch": "codex/task/P1-ready-pending-task",
                "notes": "",
            }
        ],
    )
    save_json(Path("artifacts/status/orchestrator_state.json"), {})
    save_json(
        Path("artifacts/runtime/supervisor.heartbeat.json"),
        {
            "phase": "cycle_start",
            "last_heartbeat_at": "2026-03-22T00:00:00+00:00",
        },
    )
    from scripts import monitor

    monkeypatch.setattr(monitor, "_utc_now", lambda: now)
    monitor.main()
    captured = capsys.readouterr()
    assert "Dependency-ready pending tasks: 1" in captured.out
    assert "queue starvation:" not in captured.out
    assert "Alerts: none" in captured.out


def test_monitor_tolerates_bom_prefixed_supervisor_heartbeat(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    save_json(
        Path("tasks/task_queue.json"),
        [
            {
                "id": "P1",
                "title": "Ready pending task",
                "type": "coding",
                "phase": 1,
                "files": ["foo.py"],
                "dependencies": [],
                "status": "pending",
                "success_criteria": ["done"],
                "priority": "high",
                "branch": "codex/task/P1-ready-pending-task",
                "notes": "",
            }
        ],
    )
    save_json(Path("artifacts/status/orchestrator_state.json"), {})
    Path("artifacts/runtime").mkdir(parents=True, exist_ok=True)
    Path("artifacts/runtime/supervisor.heartbeat.json").write_text(
        json.dumps(
            {
                "phase": "cycle_start",
                "last_heartbeat_at": "2026-03-22T00:00:00+00:00",
            }
        ),
        encoding="utf-8-sig",
    )
    from scripts import monitor

    monkeypatch.setattr(
        monitor,
        "_utc_now",
        lambda: datetime(2026, 3, 22, 0, 0, 30, tzinfo=UTC),
    )
    monitor.main()
    captured = capsys.readouterr()
    assert "Alerts: none" in captured.out


def test_monitor_reports_blocked_growth_and_dispatch_stagnation(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.chdir(tmp_path)
    now = datetime(2026, 3, 22, 1, 0, tzinfo=UTC)
    save_json(
        Path("tasks/task_queue.json"),
        [
            {
                "id": "P1",
                "title": "Active task",
                "type": "coding",
                "phase": 1,
                "files": ["foo.py"],
                "dependencies": [],
                "status": "dispatched",
                "success_criteria": ["done"],
                "priority": "high",
                "branch": "codex/task/P1-active-task",
                "notes": "",
            },
            {
                "id": "P2",
                "title": "Blocked task",
                "type": "coding",
                "phase": 1,
                "files": ["bar.py"],
                "dependencies": [],
                "status": "blocked",
                "success_criteria": ["done"],
                "priority": "high",
                "branch": "codex/task/P2-blocked-task",
                "notes": "",
            },
            {
                "id": "P3",
                "title": "Blocked task 2",
                "type": "coding",
                "phase": 1,
                "files": ["baz.py"],
                "dependencies": [],
                "status": "blocked",
                "success_criteria": ["done"],
                "priority": "high",
                "branch": "codex/task/P3-blocked-task-2",
                "notes": "",
            },
            {
                "id": "P4",
                "title": "Pending work",
                "type": "coding",
                "phase": 1,
                "files": ["qux.py"],
                "dependencies": ["P1"],
                "status": "pending",
                "success_criteria": ["done"],
                "priority": "medium",
                "branch": "codex/task/P4-pending-work",
                "notes": "",
            },
        ],
    )
    save_json(
        Path("artifacts/status/orchestrator_state.json"),
        {
            "active_workers": [{"task_id": "P1"}],
            "dispatch_queue": [],
            "review_queue": [],
            "last_tick_completed_at": "2026-03-22T00:40:00+00:00",
        },
    )
    save_json(
        Path("artifacts/runtime/monitor_snapshot.json"),
        {
            "observed_at": (now - timedelta(minutes=20)).isoformat(),
            "queue_counts": {"dispatched": 1, "blocked": 1, "pending": 1},
            "ready_count": 0,
            "dependency_ready_pending_count": 0,
            "active_worker_count": 1,
            "active_worker_ids": ["P1"],
            "dispatch_queue_count": 0,
            "review_queue_count": 0,
            "blocked_count": 1,
            "done_count": 0,
            "last_tick_completed_at": "2026-03-22T00:40:00+00:00",
        },
    )
    from scripts import monitor

    monkeypatch.setattr(monitor, "_utc_now", lambda: now)
    monitor.main()
    captured = capsys.readouterr()
    assert "blocked backlog grew: 1 -> 2 (+1)" in captured.out
    assert "dispatch stagnation:" in captured.out


def test_monitor_surfaces_soak_summary_when_ledger_exists(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    save_json(Path("tasks/task_queue.json"), [])
    save_json(Path("artifacts/status/orchestrator_state.json"), {})
    Path("artifacts/runtime").mkdir(parents=True, exist_ok=True)
    Path("artifacts/runtime/soak_ledger.jsonl").write_text(
        "\n".join(
            [
                (
                    '{"observed_at":"2026-03-23T10:00:00+00:00","queue_counts":{"done":266},'
                    '"supervisor_heartbeat":{"status":"healthy","age_seconds":5},'
                    '"truth_boundary":{"prototype_runtime":true,"weeklong_soak_claim_allowed":false}}'
                ),
                (
                    '{"observed_at":"2026-03-23T10:30:00+00:00","queue_counts":{"done":266},'
                    '"supervisor_heartbeat":{"status":"unavailable","age_seconds":null},'
                    '"truth_boundary":{"prototype_runtime":true,"weeklong_soak_claim_allowed":false}}'
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    from scripts import monitor

    monkeypatch.setattr(monitor, "_utc_now", lambda: datetime(2026, 3, 23, tzinfo=UTC))
    monitor.main()
    captured = capsys.readouterr()
    assert "Soak summary:" in captured.out
    assert "'entries': 2" in captured.out
    assert "'progress_ratio': 0.003" in captured.out
    assert "'remaining_hours': 167.5" in captured.out
    assert "'estimated_weeklong_at': '2026-03-30T10:00:00+00:00'" in captured.out
    assert "'incidents': 1" in captured.out


def test_monitor_surfaces_operational_readiness_snapshot(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    save_json(
        Path("tasks/task_queue.json"),
        [
            {
                "id": "P22-I007",
                "title": "Run weeklong unattended soak validation",
                "type": "integration",
                "phase": 22,
                "files": ["docs/reports/p22_weeklong_soak.md"],
                "dependencies": [],
                "status": "dispatched",
                "success_criteria": ["done"],
                "priority": "high",
                "branch": "codex/task/P22-I007-run-weeklong-unattended-soak-validation",
                "notes": "Keep open until the ledger covers a real weeklong unattended window.",
            }
        ],
    )
    save_json(
        Path("artifacts/status/orchestrator_state.json"),
        {
            "active_workers": [],
            "dispatch_queue": [],
            "review_queue": [],
            "completed_tasks": [],
            "blocked_tasks": [],
        },
    )
    save_json(
        Path("artifacts/runtime/supervisor.heartbeat.json"),
        {
            "status": "healthy",
            "last_heartbeat_at": "2026-03-23T10:30:00+00:00",
            "iteration": 4,
            "phase": "cycle_complete",
        },
    )
    save_json(
        Path("runs/real_data_benchmark/full_results/summary.json"),
        {"status": "blocked_on_release_grade_bar"},
    )
    Path("artifacts/runtime").mkdir(parents=True, exist_ok=True)
    Path("artifacts/runtime/soak_ledger.jsonl").write_text(
        json.dumps(
            {
                "observed_at": "2026-03-23T10:30:00+00:00",
                "queue_counts": {"dispatched": 1},
                "supervisor_heartbeat": {"status": "healthy", "age_seconds": 5},
                "truth_boundary": {
                    "prototype_runtime": True,
                    "weeklong_soak_claim_allowed": False,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    Path("docs/reports").mkdir(parents=True, exist_ok=True)
    Path("docs/reports/p22_weeklong_soak.md").write_text(
        (
            "This note is a readiness assessment, not a claim that a "
            "weeklong run has already completed."
        ),
        encoding="utf-8",
    )
    from scripts import monitor

    monkeypatch.setattr(monitor, "_utc_now", lambda: datetime(2026, 3, 23, 10, 30, 30, tzinfo=UTC))
    monitor.main()
    captured = capsys.readouterr()
    assert "Operational readiness:" in captured.out
    assert "'supervisor': 'healthy'" in captured.out
    assert "'ready': False" in captured.out
    assert "'truth_audit': 'ok'" in captured.out
    assert "'queue_drift': 'aligned'" in captured.out
    assert "'capture_age_seconds': 30" in captured.out
    assert (
        "'blocking_reasons': ['weeklong_soak_window_incomplete', "
        "'weeklong_claim_boundary_closed', "
        "'benchmark_status=blocked_on_release_grade_bar']"
    ) in captured.out


def test_monitor_surfaces_fresh_procurement_supervisor_status_after_resume(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.chdir(tmp_path)
    save_json(
        Path("tasks/task_queue.json"),
        [
            {
                "id": "P22-I007",
                "title": "Run weeklong unattended soak validation",
                "type": "integration",
                "phase": 22,
                "files": ["docs/reports/p22_weeklong_soak.md"],
                "dependencies": [],
                "status": "dispatched",
                "success_criteria": ["done"],
                "priority": "high",
                "branch": "codex/task/P22-I007-run-weeklong-unattended-soak-validation",
                "notes": "Keep open until the ledger covers a real weeklong unattended window.",
            }
        ],
    )
    save_json(Path("artifacts/status/orchestrator_state.json"), {})
    save_json(
        Path("artifacts/runtime/supervisor.heartbeat.json"),
        {
            "status": "stale",
            "last_heartbeat_at": "2026-03-23T09:30:00+00:00",
            "iteration": 4,
            "phase": "cycle_complete",
        },
    )
    save_json(
        Path("artifacts/runtime/procurement_supervisor_state.json"),
        {
            "generated_at": "2026-03-23T10:30:10+00:00",
            "status": "running",
            "observation_status": "available",
            "observed_active": [
                {
                    "task_id": "guarded_sources",
                    "pid": 101,
                    "ownership": "observed_only",
                    "command_line": (
                        "python protein_data_scope/download_all_sources.py "
                        "--tiers guarded"
                    ),
                }
            ],
            "active": [],
            "stale_active": [],
        },
    )
    save_json(
        Path("runs/real_data_benchmark/full_results/summary.json"),
        {"status": "blocked_on_release_grade_bar"},
    )
    Path("artifacts/runtime").mkdir(parents=True, exist_ok=True)
    Path("artifacts/runtime/soak_ledger.jsonl").write_text(
        json.dumps(
            {
                "observed_at": "2026-03-23T10:30:00+00:00",
                "queue_counts": {"dispatched": 1},
                "supervisor_heartbeat": {"status": "healthy", "age_seconds": 5},
                "truth_boundary": {
                    "prototype_runtime": True,
                    "weeklong_soak_claim_allowed": False,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    Path("docs/reports").mkdir(parents=True, exist_ok=True)
    Path("docs/reports/p22_weeklong_soak.md").write_text(
        (
            "This note is a readiness assessment, not a claim that a "
            "weeklong run has already completed."
        ),
        encoding="utf-8",
    )
    from scripts import monitor

    monkeypatch.setattr(monitor, "_utc_now", lambda: datetime(2026, 3, 23, 10, 30, 30, tzinfo=UTC))
    monitor.main()
    captured = capsys.readouterr()
    assert "Operational readiness:" in captured.out
    assert "'supervisor': 'running'" in captured.out
    assert "'ready': False" in captured.out
    assert "'queue_drift': 'aligned'" in captured.out
    assert (
        "'blocking_reasons': ['supervisor_status=running', "
        "'weeklong_soak_window_incomplete', "
        "'weeklong_claim_boundary_closed', "
        "'benchmark_status=blocked_on_release_grade_bar']"
    ) in captured.out


def test_monitor_surfaces_packet_deficit_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    save_json(Path("tasks/task_queue.json"), [])
    save_json(Path("artifacts/status/orchestrator_state.json"), {})
    save_json(
        Path("artifacts/status/packet_deficit_dashboard.json"),
        {
            "summary": {
                "packet_count": 12,
                "complete_packet_count": 7,
                "partial_packet_count": 5,
                "unresolved_packet_count": 0,
                "packet_deficit_count": 5,
                "total_missing_modality_count": 7,
                "modality_deficit_counts": {
                    "ligand": 5,
                    "ppi": 1,
                    "structure": 1,
                    "sequence": 0,
                },
                "highest_leverage_source_fixes": [
                    {"source_ref": "ligand:P00387"},
                    {"source_ref": "ligand:Q9UCM0"},
                    {"source_ref": "ppi:Q9UCM0"},
                ],
            }
        },
    )
    from scripts import monitor

    monkeypatch.setattr(monitor, "_utc_now", lambda: datetime(2026, 3, 23, tzinfo=UTC))
    monitor.main()
    captured = capsys.readouterr()
    assert "Packet deficits:" in captured.out
    assert "'complete': 7" in captured.out
    assert "'partial': 5" in captured.out
    assert (
        "'modality_deficits': {'ligand': 5, 'ppi': 1, 'structure': 1, 'sequence': 0}"
        in captured.out
    )
    assert "'top_source_refs': ['ligand:P00387', 'ligand:Q9UCM0', 'ppi:Q9UCM0']" in captured.out


def test_monitor_surfaces_procurement_supervisor_and_broad_progress(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.chdir(tmp_path)
    save_json(Path("tasks/task_queue.json"), [])
    save_json(Path("artifacts/status/orchestrator_state.json"), {})
    save_json(
        Path("artifacts/runtime/procurement_supervisor_state.json"),
        {
            "status": "stale",
            "observation_status": "available",
            "active": [],
            "observed_active": [
                {
                    "task_id": "guarded_sources",
                    "pid": 101,
                    "ownership": "observed_only",
                    "command_line": (
                        "python protein_data_scope/download_all_sources.py "
                        "--tiers guarded"
                    ),
                }
            ],
            "stale_active": [],
            "pending": ["chembl_rnacentral_bulk"],
            "handoff_required": True,
        },
    )
    save_json(
        Path("artifacts/status/broad_mirror_progress.json"),
        {
            "generated_at": "2026-03-30T22:09:19.726276+00:00",
            "status": "complete",
            "summary": {
                "source_count": 2,
                "total_present_files": 4,
                "total_expected_files": 10,
                "total_missing_files": 6,
                "total_partial_files": 1,
                "file_coverage_percent": 40.0,
                "top_gap_sources": ["string", "reactome"],
            },
            "sources": [
                {
                    "source_id": "string",
                    "source_name": "STRING v12",
                    "status": "partial",
                    "coverage_percent": 12.5,
                    "missing_file_count": 20,
                    "partial_file_count": 1,
                    "priority_rank": 1,
                },
                {
                    "source_id": "reactome",
                    "source_name": "Reactome",
                    "status": "partial",
                    "coverage_percent": 50.0,
                    "missing_file_count": 10,
                    "partial_file_count": 0,
                    "priority_rank": 1,
                },
            ],
            "top_priority_missing_files": [
                {
                    "source_id": "string",
                    "source_name": "STRING v12",
                    "category": "interaction_networks",
                    "priority_rank": 1,
                    "estimated_value": "high",
                    "filename": "protein.links.full.v12.0.txt.gz",
                }
            ],
        },
    )
    from scripts import monitor

    monkeypatch.setattr(monitor, "_probe_live_download_processes", lambda: ([], "unavailable"))
    monkeypatch.setattr(monitor, "_utc_now", lambda: datetime(2026, 3, 30, tzinfo=UTC))
    monitor.main()
    captured = capsys.readouterr()
    assert "Procurement supervisor:" in captured.out
    assert "'status': 'stale'" in captured.out
    assert "Observed active procurement lanes:" in captured.out
    assert "'task_id': 'guarded_sources'" in captured.out
    assert "Broad mirror progress:" in captured.out
    assert "'file_coverage_percent': 40.0" in captured.out
    assert "'top_gap_sources': ['string', 'reactome']" in captured.out


def test_monitor_surfaces_remaining_transfer_status(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.chdir(tmp_path)
    save_json(Path("tasks/task_queue.json"), [])
    save_json(Path("artifacts/status/orchestrator_state.json"), {})
    save_json(
        Path("artifacts/status/broad_mirror_remaining_transfer_status.json"),
        {
            "schema_id": "proteosphere-broad-mirror-remaining-transfer-status-2026-03-31",
            "generated_at": "2026-03-31T19:34:11.338136+00:00",
            "status": "planning",
            "basis": {
                "broad_mirror_progress_path": "artifacts/status/broad_mirror_progress.json",
            },
            "summary": {
                "source_count": 17,
                "remaining_source_count": 2,
                "active_file_count": 6,
                "active_source_counts": {"string": 3, "uniprot": 3},
                "not_yet_started_file_count": 16,
                "broad_mirror_coverage_percent": 86.4,
                "total_gap_files": 22,
            },
            "sources": [
                {
                    "source_id": "string",
                    "source_name": "STRING v12",
                    "status": "partial",
                    "active_file_count": 3,
                    "not_yet_started_file_count": 9,
                    "coverage_percent": 53.8,
                    "representative_missing_files": [
                        "protein.links.detailed.v12.0.txt.gz",
                    ],
                    "representative_partial_files": [
                        "protein.links.v12.0.txt.gz",
                    ],
                },
                {
                    "source_id": "uniprot",
                    "source_name": "UniProt / UniRef / ID Mapping",
                    "status": "partial",
                    "active_file_count": 3,
                    "not_yet_started_file_count": 7,
                    "coverage_percent": 33.3,
                    "representative_missing_files": [
                        "uniprot_trembl.xml.gz",
                    ],
                    "representative_partial_files": [
                        "uniprot_trembl.dat.gz",
                    ],
                },
            ],
            "gap_files": [
                {
                    "source_id": "string",
                    "source_name": "STRING v12",
                    "filename": "protein.links.detailed.v12.0.txt.gz",
                    "gap_kind": "missing",
                    "category": "interaction_networks",
                    "priority_rank": 1,
                },
                {
                    "source_id": "uniprot",
                    "source_name": "UniProt / UniRef / ID Mapping",
                    "filename": "uniprot_trembl.xml.gz",
                    "gap_kind": "missing",
                    "category": "sequence_reference_backbone",
                    "priority_rank": 1,
                },
            ],
        },
    )
    from scripts import monitor

    monkeypatch.setattr(monitor, "_probe_live_download_processes", lambda: ([], "unavailable"))
    monkeypatch.setattr(monitor, "_utc_now", lambda: datetime(2026, 3, 31, tzinfo=UTC))
    monitor.main()
    captured = capsys.readouterr()
    assert "Remaining transfer status:" in captured.out
    assert "'active_file_count': 6" in captured.out
    assert "'not_yet_started_file_count': 16" in captured.out
    assert "Remaining transfer sources:" in captured.out
    assert "Top remaining transfer files:" in captured.out
    assert "'filename': 'protein.links.detailed.v12.0.txt.gz'" in captured.out
    assert "'filename': 'uniprot_trembl.xml.gz'" in captured.out


def test_monitor_uses_live_probe_when_board_and_persisted_state_are_stale():
    from scripts import monitor

    board = {
        "status": "attention",
        "summary": {
            "broad_mirror_coverage_percent": 71.5,
            "broad_mirror_source_count": 17,
            "source_family_status_counts": {"complete": 9, "partial": 8},
            "broad_mirror_total_missing_files": 64,
            "broad_mirror_incomplete_source_count": 8,
            "active_observed_download_count": 0,
            "observed_active_source": "none",
            "local_registry_source_count": 53,
            "local_registry_effective_status_counts": {
                "missing": 3,
                "partial": 2,
                "present": 48,
            },
            "local_registry_gap_family_count": 5,
            "top_remaining_gap_count": 10,
        },
        "broad_mirror": {
            "status": "complete",
            "source_count": 17,
            "file_coverage_percent": 71.5,
            "total_present_files": 90,
            "total_expected_files": 165,
            "total_missing_files": 64,
            "total_partial_files": 11,
            "top_gap_sources": ["string", "uniprot"],
            "sources": [
                {
                    "source_id": "string",
                    "status": "partial",
                    "coverage_percent": 19.2,
                    "missing_file_count": 18,
                    "partial_file_count": 3,
                }
            ],
        },
        "procurement_supervisor": {
            "status": "idle",
            "generated_at": "2026-03-30T23:41:19.755580+00:00",
            "active_observed_download_count": 0,
            "observed_active_source": "none",
            "active_observed_downloads": [],
            "completed_download_count": 4,
        },
        "local_registry_summary": {
            "source_count": 53,
            "effective_status_counts": {
                "missing": 3,
                "partial": 2,
                "present": 48,
            },
            "gap_family_count": 5,
            "top_gap_families": [],
        },
        "top_remaining_gaps": [
            {
                "scope": "broad_mirror",
                "source_id": "string",
                "source_name": "STRING v12",
                "category": "interaction_networks",
                "status": "partial",
                "priority_rank": 1,
                "coverage_percent": 19.2,
                "missing_file_count": 18,
                "partial_file_count": 3,
                "representative_missing_files": ["protein.links.full.v12.0.txt.gz"],
                "representative_partial_files": ["protein.links.v12.0.txt.gz"],
                "rationale": "partial mirror family; 18 missing files",
            }
        ],
    }
    broad_progress = {
        "status": "complete",
        "source_count": 17,
        "file_coverage_percent": 88.9,
        "total_present_files": 147,
        "total_expected_files": 165,
        "total_missing_files": 18,
        "total_partial_files": 8,
        "top_gap_sources": ["string", "uniprot"],
        "sources": [],
    }
    visibility = monitor._summarize_procurement_visibility(
        board=board,
        supervisor_state={
            "status": "idle",
            "observed_active": [],
            "active": [],
            "stale_active": [],
            "pending": [],
            "completed": [],
            "failed": [],
        },
        broad_progress=broad_progress,
        process_probe=lambda: (
            [
                {
                    "pid": 4242,
                    "name": "python.exe",
                    "command_line": (
                        "python protein_data_scope/download_all_sources.py "
                        "--sources string --dest D:/documents/ProteoSphereV2/data/raw/"
                        "protein_data_scope_seed"
                    ),
                    "creation_date": "2026-03-30T23:40:00+00:00",
                }
            ],
            "available",
        ),
    )

    assert visibility is not None
    assert visibility["source"] == "procurement_status_board"
    assert visibility["active_observed_download_count"] == 1
    assert visibility["active_observed_downloads"][0]["pid"] == 4242
    assert visibility["broad_mirror"]["file_coverage_percent"] == 88.9


def test_monitor_prefers_authoritative_board_downloads_over_raw_process_table():
    from scripts import monitor

    board = {
        "status": "attention",
        "summary": {
            "active_observed_download_count": 2,
            "observed_active_source": "remaining_transfer_status",
        },
        "broad_mirror": {
            "status": "complete",
            "source_count": 17,
            "file_coverage_percent": 98.8,
            "total_present_files": 160,
            "total_expected_files": 162,
            "total_missing_files": 0,
            "total_partial_files": 2,
            "top_gap_sources": ["uniprot", "string"],
            "sources": [],
        },
        "procurement_supervisor": {
            "status": "planning",
            "generated_at": "2026-04-03T21:33:40+00:00",
            "active_observed_download_count": 2,
            "observed_active_source": "remaining_transfer_status",
            "active_observed_downloads": [
                {
                    "task_id": "uniprot",
                    "description": "uniref100.xml.gz",
                    "category": "sequence_reference_backbone",
                    "priority": None,
                    "pid": None,
                    "status": "running",
                    "started_at": "",
                },
                {
                    "task_id": "string",
                    "description": "protein.links.full.v12.0.txt.gz",
                    "category": "interaction_networks",
                    "priority": None,
                    "pid": None,
                    "status": "running",
                    "started_at": "",
                },
            ],
            "completed_download_count": 4,
        },
    }

    visibility = monitor._summarize_procurement_visibility(
        board=board,
        supervisor_state={
            "status": "stale",
            "observed_active": [],
            "active": [],
            "stale_active": [],
            "pending": [],
            "completed": [],
            "failed": [],
        },
        broad_progress=None,
        process_probe=lambda: (
            [
                {
                    "pid": 111,
                    "name": "python.exe",
                    "command_line": (
                        "python protein_data_scope/download_all_sources.py "
                        "--sources uniprot"
                    ),
                    "creation_date": "2026-04-03T21:00:00+00:00",
                },
                {
                    "pid": 222,
                    "name": "python.exe",
                    "command_line": (
                        "python protein_data_scope/download_all_sources.py "
                        "--sources uniprot"
                    ),
                    "creation_date": "2026-04-03T21:00:00+00:00",
                },
                {
                    "pid": 333,
                    "name": "python.exe",
                    "command_line": (
                        "python protein_data_scope/download_all_sources.py "
                        "--sources string"
                    ),
                    "creation_date": "2026-04-03T21:00:00+00:00",
                },
            ],
            "available",
        ),
    )

    assert visibility is not None
    assert visibility["source"] == "procurement_status_board"
    assert visibility["observed_active_source"] == "remaining_transfer_status"
    assert visibility["active_observed_download_count"] == 2
    assert [row["task_id"] for row in visibility["active_observed_downloads"]] == [
        "uniprot",
        "string",
    ]
    assert visibility["raw_process_table_active_count"] == 3


def test_monitor_gracefully_handles_missing_supervisor_and_broad_progress_files(
    tmp_path,
    monkeypatch,
    capsys,
):
    monkeypatch.chdir(tmp_path)
    save_json(Path("tasks/task_queue.json"), [])
    save_json(Path("artifacts/status/orchestrator_state.json"), {})
    from scripts import monitor

    monkeypatch.setattr(monitor, "_probe_live_download_processes", lambda: ([], "unavailable"))
    monkeypatch.setattr(monitor, "_utc_now", lambda: datetime(2026, 3, 30, tzinfo=UTC))
    monitor.main()
    captured = capsys.readouterr()
    assert "Procurement supervisor:" not in captured.out
    assert "Broad mirror progress:" not in captured.out
    assert "Alerts: none" in captured.out

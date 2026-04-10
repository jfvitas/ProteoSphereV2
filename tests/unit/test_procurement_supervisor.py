from __future__ import annotations

from pathlib import Path

import scripts.procurement_supervisor as supervisor


def test_load_state_quarantines_loaded_active_entries_as_stale(tmp_path: Path, monkeypatch) -> None:
    runtime_dir = tmp_path / "runtime"
    state_path = runtime_dir / "procurement_supervisor_state.json"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """
        {
          "generated_at": "2026-03-30T00:00:00+00:00",
          "status": "running",
          "active": [{"task_id": "guarded_sources", "pid": 12345}],
          "pending": ["resolver_safe_bulk"],
          "completed": [],
          "failed": []
        }
        """.strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(supervisor, "RUNTIME_DIR", runtime_dir)
    monkeypatch.setattr(supervisor, "STATE_PATH", state_path)

    state = supervisor.load_state()

    assert state["active"] == []
    assert len(state["stale_active"]) == 1
    assert state["handoff_required"] is True


def test_observe_live_download_jobs_marks_known_procurement_processes(monkeypatch) -> None:
    task_map = supervisor.get_task_map()

    def fake_probe():
        return (
            [
                {
                    "pid": 101,
                    "name": "python.exe",
                    "command_line": (
                        "C:\\Python\\python.exe protein_data_scope/download_all_sources.py "
                        "--tiers guarded --dest "
                        "D:\\documents\\ProteoSphereV2\\data\\raw\\protein_data_scope_seed "
                        "--timeout 1800 --retries 4"
                    ),
                    "creation_date": "2026-03-30T20:00:00+00:00",
                },
                {
                    "pid": 202,
                    "name": "python.exe",
                    "command_line": "C:\\Python\\python.exe scripts\\reviewer_loop.py",
                    "creation_date": "2026-03-30T20:00:00+00:00",
                },
            ],
            "available",
        )

    observation = supervisor.observe_live_download_jobs(probe=fake_probe, task_map=task_map)

    assert observation["status"] == "available"
    assert len(observation["observed_active"]) == 1
    assert observation["observed_active"][0]["task_id"] == "guarded_sources"
    assert observation["observed_active"][0]["ownership"] == "observed_only"


def test_fill_slots_respects_live_observed_jobs_and_launches_next_tranche_when_room_exists(
    monkeypatch,
) -> None:
    launched: list[str] = []
    state = {
        "active": [],
        "observed_active": [
            {"pid": 101, "task_id": "guarded_sources", "ownership": "observed_only"}
        ],
        "stale_active": [],
        "pending": ["packet_gap_accession_refresh", "resolver_safe_bulk"],
        "observation_status": "available",
        "handoff_required": False,
    }

    monkeypatch.setattr(
        supervisor,
        "get_task_map",
        lambda: {
            "packet_gap_accession_refresh": supervisor.ProcurementTask(
                task_id="packet_gap_accession_refresh",
                priority=95,
                description=(
                    "Refresh the five deficit accessions across live accession-oriented "
                    "sources."
                ),
                command=["python", "scripts/download_raw_data.py"],
                stdout_log="packet_gap_refresh_stdout.log",
                stderr_log="packet_gap_refresh_stderr.log",
                category="targeted",
            ),
            "resolver_safe_bulk": supervisor.ProcurementTask(
                task_id="resolver_safe_bulk",
                priority=90,
                description=(
                    "Download resolver-tier sources with direct bulk URLs that are "
                    "already known and actionable."
                ),
                command=["python", "protein_data_scope/download_all_sources.py"],
                stdout_log="resolver_safe_bulk_stdout.log",
                stderr_log="resolver_safe_bulk_stderr.log",
                category="bulk",
            ),
        },
    )
    monkeypatch.setattr(
        supervisor,
        "start_task",
        lambda task: launched.append(task.task_id)
        or {
            "task_id": task.task_id,
            "description": task.description,
            "priority": task.priority,
            "category": task.category,
            "pid": 999,
            "started_at": supervisor.utc_now(),
            "stdout_log": task.stdout_log,
            "stderr_log": task.stderr_log,
            "command": task.command,
            "_process": object(),
            "_stdout_handle": object(),
            "_stderr_handle": object(),
        },
    )

    supervisor.fill_slots(state, processes={}, max_parallel=2)

    assert launched == ["packet_gap_accession_refresh"]
    assert state["pending"] == ["resolver_safe_bulk"]
    assert len(state["active"]) == 1


def test_summarize_state_reports_stale_when_only_external_jobs_are_observed() -> None:
    summary = supervisor.summarize_state(
        {
            "active": [],
            "observed_active": [{"pid": 101, "task_id": "guarded_sources"}],
            "stale_active": [],
            "pending": [],
            "completed": [],
            "failed": [],
            "observation_status": "available",
            "handoff_required": True,
        }
    )

    assert summary["status"] == "stale"
    assert summary["observed_active_count"] == 1
    assert summary["handoff_required"] is True


def test_summarize_state_prefers_fresh_observation_over_stale_handoff_after_resume() -> None:
    summary = supervisor.summarize_state(
        {
            "active": [],
            "observed_active": [{"pid": 101, "task_id": "guarded_sources"}],
            "stale_active": [{"pid": 100, "task_id": "guarded_sources"}],
            "pending": [],
            "completed": [],
            "failed": [],
            "observation_status": "available",
            "handoff_required": True,
        }
    )

    assert summary["status"] == "running"
    assert summary["observed_active_count"] == 1
    assert summary["stale_active_count"] == 1
    assert summary["handoff_required"] is True

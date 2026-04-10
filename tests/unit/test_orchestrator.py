from scripts.orchestrator import (
    annotate_restart_state,
    demote_invalid_completions,
    demote_invalid_dispatches,
    enforce_truth_boundaries,
    promote_ready,
    reconcile_state_indexes,
    refresh_finished_tasks,
    select_dispatches,
)


def test_promote_ready_only_when_dependencies_done():
    queue = [
        {"id": "A", "status": "done", "dependencies": [], "files": ["a.py"], "type": "coding", "title": "A", "phase": 1, "priority": "high", "branch": "task/A-a", "success_criteria": ["ok"]},
        {"id": "B", "status": "pending", "dependencies": ["A"], "files": ["b.py"], "type": "coding", "title": "B", "phase": 1, "priority": "high", "branch": "task/B-b", "success_criteria": ["ok"]},
        {"id": "C", "status": "pending", "dependencies": ["Z"], "files": ["c.py"], "type": "coding", "title": "C", "phase": 1, "priority": "high", "branch": "task/C-c", "success_criteria": ["ok"]},
    ]
    promote_ready(queue)
    assert queue[1]["status"] == "ready"
    assert queue[2]["status"] == "pending"


def test_dispatch_selection_avoids_file_overlap():
    queue = [
        {"id": "A", "status": "ready", "dependencies": [], "files": ["connectors/rcsb/client.py"], "type": "coding", "title": "A", "phase": 1, "priority": "high", "branch": "task/A-a", "success_criteria": ["ok"]},
        {"id": "B", "status": "ready", "dependencies": [], "files": ["connectors/rcsb/client.py"], "type": "coding", "title": "B", "phase": 1, "priority": "high", "branch": "task/B-b", "success_criteria": ["ok"]},
        {"id": "C", "status": "ready", "dependencies": [], "files": ["connectors/uniprot/client.py"], "type": "coding", "title": "C", "phase": 1, "priority": "medium", "branch": "task/C-c", "success_criteria": ["ok"]},
    ]
    state = {"active_workers": []}
    selected = select_dispatches(queue, state, {"coding": 10, "analysis": 3, "integration": 3, "gpu": 1})
    selected_ids = {task["id"] for task in selected}
    assert "A" in selected_ids
    assert "B" not in selected_ids
    assert "C" in selected_ids


def test_annotate_restart_state_marks_fresh_bootstrap():
    queue = [{"id": "A"}, {"id": "B"}]
    state = {
        "active_workers": [],
        "dispatch_queue": [],
        "completed_tasks": [],
        "blocked_tasks": [],
    }

    annotate_restart_state(queue, state)

    assert state["resume_cause"] == "fresh_state_bootstrap"
    assert state["restart_marker"]["resume_cause"] == "fresh_state_bootstrap"
    assert state["restart_marker"]["queue_task_count"] == 2


def test_annotate_restart_state_marks_resume_from_prior_cycle():
    queue = [{"id": "A"}]
    state = {
        "active_workers": [{"task_id": "A"}],
        "dispatch_queue": ["A"],
        "completed_tasks": ["Z"],
        "blocked_tasks": [],
        "last_tick_completed_at": "2026-03-23T00:00:00+00:00",
    }

    annotate_restart_state(queue, state)

    assert state["resume_cause"] == "resume_from_prior_cycle"
    assert state["restart_marker"]["prior_active_worker_count"] == 1
    assert state["restart_marker"]["prior_dispatch_queue_count"] == 1


def test_refresh_finished_tasks_prunes_workers_not_still_dispatched_or_running(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.orchestrator.STATUS_DIR", tmp_path / "status")
    monkeypatch.setattr("scripts.orchestrator.BLOCKER_DIR", tmp_path / "blockers")
    monkeypatch.setattr("scripts.orchestrator.DISPATCH_DIR", tmp_path / "dispatch")

    queue = [
        {
            "id": "A",
            "status": "done",
            "dependencies": [],
            "files": ["a.py"],
            "type": "coding",
            "title": "A",
            "phase": 1,
            "priority": "high",
            "branch": "codex/task/A-a",
            "success_criteria": ["ok"],
        },
        {
            "id": "B",
            "status": "pending",
            "dependencies": [],
            "files": ["b.py"],
            "type": "coding",
            "title": "B",
            "phase": 1,
            "priority": "high",
            "branch": "codex/task/B-b",
            "success_criteria": ["ok"],
        },
        {
            "id": "C",
            "status": "dispatched",
            "dependencies": [],
            "files": ["c.py"],
            "type": "coding",
            "title": "C",
            "phase": 1,
            "priority": "high",
            "branch": "codex/task/C-c",
            "success_criteria": ["ok"],
        },
    ]
    state = {
        "active_workers": [
            {"task_id": "A", "type": "coding", "gpu_heavy": False, "branch": "codex/task/A-a"},
            {"task_id": "B", "type": "coding", "gpu_heavy": False, "branch": "codex/task/B-b"},
            {"task_id": "C", "type": "coding", "gpu_heavy": False, "branch": "codex/task/C-c"},
        ],
        "completed_tasks": [],
        "blocked_tasks": [],
    }

    refresh_finished_tasks(queue, state)

    assert state["active_workers"] == [
        {"task_id": "C", "type": "coding", "gpu_heavy": False, "branch": "codex/task/C-c"}
    ]


def test_enforce_truth_boundaries_reopens_readiness_only_done_task():
    queue = [
        {
            "id": "P22-I007",
            "status": "done",
            "dependencies": [],
            "files": ["docs/reports/p22_weeklong_soak.md"],
            "type": "integration",
            "title": "Run weeklong unattended soak validation",
            "phase": 22,
            "priority": "high",
            "branch": "codex/task/P22-I007-run-weeklong-unattended-soak-validation",
            "success_criteria": ["ok"],
            "notes": "Keep open until the ledger covers a real weeklong unattended window.",
        }
    ]
    state = {
        "active_workers": [],
        "completed_tasks": ["P22-I007"],
        "blocked_tasks": [],
    }

    enforce_truth_boundaries(queue, state)

    assert queue[0]["status"] == "dispatched"
    assert "P22-I007" not in state["completed_tasks"]


def test_demote_invalid_dispatches_reverts_downstream_task_when_dependency_reopens():
    queue = [
        {
            "id": "P22-I007",
            "status": "dispatched",
            "dependencies": [],
            "files": ["docs/reports/p22_weeklong_soak.md"],
            "type": "integration",
            "title": "Run weeklong unattended soak validation",
            "phase": 22,
            "priority": "high",
            "branch": "codex/task/P22-I007-run-weeklong-unattended-soak-validation",
            "success_criteria": ["ok"],
            "notes": "Keep open until the ledger covers a real weeklong unattended window.",
        },
        {
            "id": "P22-I008",
            "status": "dispatched",
            "dependencies": ["P22-I007"],
            "files": ["docs/reports/p22_operational_resilience.md"],
            "type": "integration",
            "title": "Validate operational resilience and recovery",
            "phase": 22,
            "priority": "high",
            "branch": "codex/task/P22-I008-validate-operational-resilience-and-recovery",
            "success_criteria": ["ok"],
            "notes": "",
        },
    ]
    state = {
        "active_workers": [
            {
                "task_id": "P22-I008",
                "type": "integration",
                "gpu_heavy": False,
                "branch": "codex/task/P22-I008-validate-operational-resilience-and-recovery",
            }
        ],
        "dispatch_queue": ["P22-I008"],
        "completed_tasks": [],
        "blocked_tasks": [],
    }

    demote_invalid_dispatches(queue, state)

    assert queue[1]["status"] == "pending"
    assert state["active_workers"] == []
    assert state["dispatch_queue"] == []


def test_demote_invalid_completions_reverts_done_task_with_incomplete_dependencies():
    queue = [
        {
            "id": "P22-I007",
            "status": "dispatched",
            "dependencies": [],
            "files": ["docs/reports/p22_weeklong_soak.md"],
            "type": "integration",
            "title": "Run weeklong unattended soak validation",
            "phase": 22,
            "priority": "high",
            "branch": "codex/task/P22-I007-run-weeklong-unattended-soak-validation",
            "success_criteria": ["ok"],
            "notes": "Keep open until the ledger covers a real weeklong unattended window.",
        },
        {
            "id": "P22-I008",
            "status": "done",
            "dependencies": ["P22-I007"],
            "files": ["docs/reports/p22_operational_resilience.md"],
            "type": "integration",
            "title": "Validate operational resilience and recovery",
            "phase": 22,
            "priority": "high",
            "branch": "codex/task/P22-I008-validate-operational-resilience-and-recovery",
            "success_criteria": ["ok"],
            "notes": "",
        },
    ]
    state = {
        "active_workers": [],
        "dispatch_queue": [],
        "completed_tasks": ["P22-I008"],
        "blocked_tasks": [],
    }

    demote_invalid_completions(queue, state)

    assert queue[1]["status"] == "pending"
    assert "P22-I008" not in state["completed_tasks"]


def test_reconcile_state_indexes_matches_queue_statuses():
    queue = [
        {
            "id": "A",
            "status": "done",
            "dependencies": [],
            "files": ["a.py"],
            "type": "coding",
            "title": "A",
            "phase": 1,
            "priority": "high",
            "branch": "codex/task/A-a",
            "success_criteria": ["ok"],
            "notes": "",
        },
        {
            "id": "B",
            "status": "blocked",
            "dependencies": [],
            "files": ["b.py"],
            "type": "coding",
            "title": "B",
            "phase": 1,
            "priority": "high",
            "branch": "codex/task/B-b",
            "success_criteria": ["ok"],
            "notes": "",
        },
        {
            "id": "C",
            "status": "reviewed",
            "dependencies": [],
            "files": ["c.py"],
            "type": "coding",
            "title": "C",
            "phase": 1,
            "priority": "medium",
            "branch": "codex/task/C-c",
            "success_criteria": ["ok"],
            "notes": "",
        },
    ]
    state = {
        "completed_tasks": ["stale-task"],
        "blocked_tasks": ["old-blocker"],
    }

    reconcile_state_indexes(queue, state)

    assert state["completed_tasks"] == ["A", "C"]
    assert state["blocked_tasks"] == ["B"]

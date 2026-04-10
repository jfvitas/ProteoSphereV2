from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import scripts.training_set_builder_cli as cli


def test_parse_args_accepts_known_builder_command(monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "compile-cohort"],
    )

    args = cli.parse_args()

    assert args.command == "compile-cohort"


def test_main_dispatches_to_expected_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "plan-package"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_package_readiness_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_candidate_package_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "candidate-package"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_training_set_candidate_package_manifest_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_split_simulation_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "split-simulation"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_split_simulation_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_entity_resolution_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "build-entity-resolution-sidecar"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_seed_plus_neighbors_entity_resolution_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_preview_hold_exit_criteria_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "preview-hold-exit-criteria"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_training_set_preview_hold_exit_criteria_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_preview_hold_clearance_batch_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "preview-hold-clearance-batch"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith(
        "scripts\\export_training_set_preview_hold_clearance_batch_preview.py"
    )
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_runbook_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "runbook"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_training_set_builder_runbook_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_remediation_plan_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "remediation-plan"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_training_set_remediation_plan_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_cohort_rationale_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "cohort-rationale"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_cohort_inclusion_rationale_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_gating_evidence_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "gating-evidence"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_training_set_gating_evidence_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_execute_post_tail_unlock(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "execute-post-tail-unlock"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\run_post_tail_unlock.py")
    assert "--execute" in command
    assert "--allow-c-overflow-authority" in command
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_run_final_dataset_wave(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "run-final-dataset-wave"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\run_post_tail_completion_wave.py")
    assert "--execute" in command
    assert "--allow-c-overflow-authority" in command
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_packet_completeness_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(sys, "argv", ["training_set_builder_cli.py", "packet-completeness"])
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\export_training_packet_completeness_matrix_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_gate_ladder_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "gate-ladder"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_training_set_gate_ladder_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_unlock_route_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "unlock-route"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_training_set_unlock_route_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_transition_contract_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "transition-contract"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_training_set_transition_contract_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_package_transition_batch_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "package-transition-batch"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_training_set_package_transition_batch_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_package_execution_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "package-execution"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_training_set_package_execution_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_preview_hold_register_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "preview-hold-register"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_training_set_preview_hold_register_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_source_fix_batch_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "source-fix-batch"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_training_set_source_fix_batch_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_action_queue_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "action-queue"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_training_set_action_queue_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_blocker_burndown_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "blocker-burndown"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_training_set_blocker_burndown_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_modality_gap_register_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "modality-gap-register"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_training_set_modality_gap_register_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_package_blocker_matrix_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "package-blocker-matrix"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_training_set_package_blocker_matrix_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_scrape_backlog_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "scrape-backlog"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_scrape_backlog_remaining_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_unblock_plan_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "unblock-plan"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_training_set_unblock_plan_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_execute_scrape_wave_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(sys, "argv", ["training_set_builder_cli.py", "execute-scrape-wave"])
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\run_pre_tail_scrape_wave.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_materialize_string_interaction_lane_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "materialize-string-interaction-lane"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_string_interaction_materialization_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_build_canonical_corpus_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "build-canonical-corpus"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_seed_plus_neighbors_structured_corpus_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_build_baseline_sidecar_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "build-baseline-sidecar"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_seed_plus_neighbors_baseline_sidecar_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_build_multimodal_sidecar_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "build-multimodal-sidecar"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_seed_plus_neighbors_multimodal_sidecar_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_post_tail_unlock_dry_run_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["training_set_builder_cli.py", "post-tail-unlock-dry-run"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\run_post_tail_unlock.py")
    assert cwd == cli.REPO_ROOT

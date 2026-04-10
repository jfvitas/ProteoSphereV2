from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import scripts.external_dataset_assessment_cli as cli


def test_parse_args_accepts_known_assessment_command(monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "assess"],
    )

    args = cli.parse_args()

    assert args.command == "assess"


def test_parse_args_accepts_audit_and_sample_commands(monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "sample-manifests"],
    )

    args = cli.parse_args()

    assert args.command == "sample-manifests"


def test_main_dispatches_to_expected_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "intake-contract"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_external_dataset_intake_contract_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_binding_audit_alias_to_dedicated_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "binding-audit"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\export_external_dataset_binding_audit_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_structure_audit_alias_to_dedicated_exporter(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "structure-audit"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\export_external_dataset_structure_audit_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_sample_manifest_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "sample-manifest-dry-run"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\generate_sample_external_dataset_manifest.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_sample_bundle_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "sample-bundle"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\export_sample_external_dataset_assessment_bundle.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_issue_matrix_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "issue-matrix"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\export_external_dataset_issue_matrix_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_flaw_taxonomy_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "flaw-taxonomy"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\export_external_dataset_flaw_taxonomy_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_risk_register_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "risk-register"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\export_external_dataset_risk_register_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_conflict_register_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "conflict-register"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\export_external_dataset_conflict_register_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_remediation_template_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "remediation-template"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\export_external_dataset_remediation_template_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_fixture_catalog_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "fixture-catalog"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\export_external_dataset_fixture_catalog_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_clearance_delta_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "clearance-delta"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\export_external_dataset_clearance_delta_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_caveat_exit_criteria_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "caveat-exit-criteria"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith(
        "scripts\\export_external_dataset_caveat_exit_criteria_preview.py"
    )
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_caveat_review_batch_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "caveat-review-batch"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith(
        "scripts\\export_external_dataset_caveat_review_batch_preview.py"
    )
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_blocked_acquisition_batch_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "blocked-acquisition-batch"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith(
        "scripts\\export_external_dataset_blocked_acquisition_batch_preview.py"
    )
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_acquisition_unblock_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "acquisition-unblock"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith(
        "scripts\\export_external_dataset_acquisition_unblock_preview.py"
    )
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_advisory_followup_register_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "advisory-followup-register"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith(
        "scripts\\export_external_dataset_advisory_followup_register_preview.py"
    )
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_acceptance_path_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "acceptance-path"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\export_external_dataset_acceptance_path_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_remediation_readiness_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "remediation-readiness"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith(
        "scripts\\export_external_dataset_remediation_readiness_preview.py"
    )
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_caveat_execution_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "caveat-execution"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[0] == sys.executable
    assert command[1].endswith("scripts\\export_external_dataset_caveat_execution_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_manifest_lint_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "manifest-lint"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\export_external_dataset_manifest_lint_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_admission_decision_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "admission-decision"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\export_external_dataset_admission_decision_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_acceptance_gate_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "acceptance-gate"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\export_external_dataset_acceptance_gate_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_resolution_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "resolution"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\export_external_dataset_resolution_preview.py")
    assert cwd == cli.REPO_ROOT


def test_main_dispatches_remediation_queue_command(monkeypatch) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(
        sys,
        "argv",
        ["external_dataset_assessment_cli.py", "remediation-queue"],
    )
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    result = cli.main()

    assert result == 0
    assert len(calls) == 1
    command, cwd = calls[0]
    assert command[1].endswith("scripts\\export_external_dataset_remediation_queue_preview.py")
    assert cwd == cli.REPO_ROOT

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from core.library.summary_record import (
    ProteinProteinSummaryRecord,
    ProteinSummaryRecord,
    StructureUnitSummaryRecord,
    SummaryLibrarySchema,
    SummaryRecordContext,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _powershell_executable() -> str:
    for candidate in ("powershell.exe", "pwsh.exe"):
        path = shutil.which(candidate)
        if path:
            return path
    raise RuntimeError("PowerShell is required for the operator snapshot smoke test")


def _copy_fixture_tree(repo_root: Path, temp_root: Path) -> None:
    (temp_root / "scripts").mkdir(parents=True, exist_ok=True)
    (temp_root / "artifacts" / "status").mkdir(parents=True, exist_ok=True)
    (temp_root / "artifacts" / "runtime").mkdir(parents=True, exist_ok=True)
    (temp_root / "artifacts" / "schemas").mkdir(parents=True, exist_ok=True)
    (temp_root / "data" / "packages").mkdir(parents=True, exist_ok=True)
    (temp_root / "runs" / "real_data_benchmark").mkdir(parents=True, exist_ok=True)
    (temp_root / "tasks").mkdir(parents=True, exist_ok=True)

    for name in (
        "powershell_interface.ps1",
        "validate_operator_state.py",
        "summarize_soak_ledger.py",
        "analyze_soak_anomalies.py",
        "audit_truth_boundaries.py",
        "build_operational_readiness_snapshot.py",
    ):
        shutil.copy2(repo_root / "scripts" / name, temp_root / "scripts" / name)

    shutil.copytree(
        repo_root / "runs" / "real_data_benchmark" / "full_results",
        temp_root / "runs" / "real_data_benchmark" / "full_results",
    )
    shutil.copy2(
        repo_root / "artifacts" / "schemas" / "operator_state.schema.json",
        temp_root / "artifacts" / "schemas" / "operator_state.schema.json",
    )
    shutil.copy2(
        repo_root / "artifacts" / "status" / "orchestrator_state.json",
        temp_root / "artifacts" / "status" / "orchestrator_state.json",
    )
    shutil.copy2(
        repo_root / "artifacts" / "status" / "P6-T001.json",
        temp_root / "artifacts" / "status" / "P6-T001.json",
    )
    shutil.copy2(
        repo_root / "artifacts" / "status" / "P6-T003.json",
        temp_root / "artifacts" / "status" / "P6-T003.json",
    )
    shutil.copy2(repo_root / "tasks" / "task_queue.json", temp_root / "tasks" / "task_queue.json")


def _run_interface(repo_root: Path) -> dict[str, object]:
    command = [
        _powershell_executable(),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(repo_root / "scripts" / "powershell_interface.ps1"),
        "-Mode",
        "state",
        "-AsJson",
    ]
    result = subprocess.run(
        command,
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return json.loads(result.stdout)


def _run_validator(repo_root: Path) -> dict[str, object]:
    command = [
        sys.executable,
        str(repo_root / "scripts" / "validate_operator_state.py"),
        "--json",
    ]
    result = subprocess.run(
        command,
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return json.loads(result.stdout)


def _run_runtime(repo_root: Path) -> dict[str, object]:
    command = [
        _powershell_executable(),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(repo_root / "scripts" / "powershell_interface.ps1"),
        "-Mode",
        "runtime",
        "-AsJson",
    ]
    result = subprocess.run(
        command,
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return json.loads(result.stdout)


def _write_supervisor_heartbeat(
    repo_root: Path,
    *,
    last_heartbeat_at: datetime,
    iteration: int = 1,
    phase: str = "cycle_complete",
) -> Path:
    heartbeat_path = repo_root / "artifacts" / "runtime" / "supervisor.heartbeat.json"
    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
    heartbeat_path.write_text(
        json.dumps(
            {
                "supervisor_pid": 4242,
                "iteration": iteration,
                "phase": phase,
                "last_heartbeat_at": last_heartbeat_at.astimezone(UTC).isoformat(),
                "stale_after_seconds": 300,
                "source": "supervisor_loop",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return heartbeat_path


def _write_supervisor_heartbeat_history(
    repo_root: Path,
    * ,
    timestamps: list[datetime],
) -> Path:
    history_path = repo_root / "artifacts" / "runtime" / "supervisor.heartbeat.history.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for index, timestamp in enumerate(timestamps, start=1):
        lines.append(
            json.dumps(
                {
                    "supervisor_pid": 4242,
                    "iteration": index,
                    "phase": "cycle_complete",
                    "last_heartbeat_at": timestamp.astimezone(UTC).isoformat(),
                    "stale_after_seconds": 300,
                    "source": "supervisor_loop",
                }
            )
        )
    history_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return history_path


def _write_soak_ledger(repo_root: Path, entries: list[dict[str, object]]) -> Path:
    ledger_path = repo_root / "artifacts" / "runtime" / "soak_ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        "\n".join(json.dumps(entry) for entry in entries) + "\n",
        encoding="utf-8",
    )
    return ledger_path


def _write_packet_library_state(repo_root: Path) -> None:
    latest_path = repo_root / "data" / "packages" / "LATEST.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(
        json.dumps(
            {
                "run_id": "selected-cohort-fixture",
                "status": "partial",
                "packet_count": 12,
                "complete_count": 4,
                "partial_count": 8,
                "unresolved_count": 0,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    dashboard_path = repo_root / "artifacts" / "status" / "packet_deficit_dashboard.json"
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_path.write_text(
        json.dumps(
            {
                "summary": {
                    "modality_deficit_counts": {
                        "sequence": 0,
                        "structure": 1,
                        "ligand": 7,
                        "ppi": 1,
                    },
                    "source_fix_candidate_count": 9,
                    "highest_leverage_source_fixes": [
                        {"source_ref": "ligand:P00387"},
                        {"source_ref": "ligand:P09105"},
                        {"source_ref": "ppi:P04637"},
                    ],
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _materialized_summary_library() -> SummaryLibrarySchema:
    return SummaryLibrarySchema(
        library_id="summary-library:materialized",
        source_manifest_id="manifest:materialized",
        records=(
            ProteinSummaryRecord(
                summary_id="protein:P12345",
                protein_ref="protein:P12345",
                protein_name="Example protein",
                organism_name="Homo sapiens",
                taxon_id=9606,
                sequence_checksum="abc123",
                sequence_version="2026_03",
                sequence_length=6,
                gene_names=("GENE1",),
                aliases=("P12345",),
                join_status="joined",
                context=SummaryRecordContext(
                    storage_notes=("already materialized",),
                ),
            ),
            ProteinProteinSummaryRecord(
                summary_id="pair:ppi:materialized",
                protein_a_ref="protein:P12345",
                protein_b_ref="protein:Q99999",
                interaction_type="physical association",
                interaction_id="EBI-0001",
                interaction_refs=("IM-12345-1", "EBI-0001"),
                evidence_refs=("PMID:12345",),
                organism_name="Homo sapiens",
                taxon_id=9606,
                physical_interaction=True,
                join_status="joined",
            ),
        ),
    )


def _write_materialized_summary_library(repo_root: Path) -> Path:
    materialized_path = (
        repo_root / "runs" / "real_data_benchmark" / "full_results" / "summary_library.json"
    )
    materialized_path.write_text(
        json.dumps(_materialized_summary_library().to_dict(), indent=2),
        encoding="utf-8",
    )
    return materialized_path


def _write_reactome_materialized_summary_library(repo_root: Path) -> Path:
    materialized_path = (
        repo_root / "artifacts" / "status" / "reactome_local_summary_library.json"
    )
    materialized_path.parent.mkdir(parents=True, exist_ok=True)
    materialized_path.write_text(
        json.dumps(
            SummaryLibrarySchema(
                library_id="summary-library:reactome-local:test",
                source_manifest_id="bio-agent-lab/reactome:test",
                records=(
                    ProteinSummaryRecord(
                        summary_id="protein:P04637",
                        protein_ref="protein:P04637",
                        protein_name="Cellular tumor antigen p53",
                        organism_name="Homo sapiens",
                        sequence_length=393,
                        gene_names=("TP53", "P53"),
                        aliases=("P04637", "P53_HUMAN"),
                        join_status="joined",
                        context=SummaryRecordContext(),
                    ),
                    ProteinSummaryRecord(
                        summary_id="protein:P09105",
                        protein_ref="protein:P09105",
                        protein_name="",
                        organism_name="",
                        aliases=("P09105",),
                        join_status="partial",
                        join_reason="reactome_empty",
                        context=SummaryRecordContext(),
                        notes=("reactome_only_accession", "reactome_empty"),
                    ),
                ),
            ).to_dict(),
            indent=2,
        ),
        encoding="utf-8",
    )
    return materialized_path


def _write_intact_materialized_summary_library(repo_root: Path) -> Path:
    materialized_path = (
        repo_root / "artifacts" / "status" / "intact_local_summary_library.json"
    )
    materialized_path.parent.mkdir(parents=True, exist_ok=True)
    materialized_path.write_text(
        json.dumps(
            SummaryLibrarySchema(
                library_id="summary-library:intact-local:test",
                source_manifest_id="IntAct:test-release:download:testfingerprint",
                records=(
                    ProteinSummaryRecord(
                        summary_id="protein:P31749",
                        protein_ref="protein:P31749",
                        protein_name="AKT1",
                        organism_name="Homo sapiens",
                        sequence_length=480,
                        gene_names=("AKT1",),
                        aliases=("P31749", "AKT1_HUMAN"),
                        join_status="joined",
                        context=SummaryRecordContext(),
                    ),
                    ProteinProteinSummaryRecord(
                        summary_id="pair:protein_protein:protein:P31749|protein:Q9Y6K9",
                        protein_a_ref="protein:P31749",
                        protein_b_ref="protein:Q9Y6K9",
                        interaction_type='psi-mi:"MI:0407"(direct interaction)',
                        interaction_refs=("EBI-5772682", "IM-17256-1"),
                        evidence_refs=("pubmed:20098747",),
                        taxon_id=9606,
                        physical_interaction=True,
                        join_status="joined",
                        context=SummaryRecordContext(),
                    ),
                ),
            ).to_dict(),
            indent=2,
        ),
        encoding="utf-8",
    )
    return materialized_path


def _write_structure_unit_materialized_summary_library(repo_root: Path) -> Path:
    materialized_path = (
        repo_root / "artifacts" / "status" / "structure_unit_summary_library.json"
    )
    materialized_path.parent.mkdir(parents=True, exist_ok=True)
    materialized_path.write_text(
        json.dumps(
            SummaryLibrarySchema(
                library_id="summary-library:structure-units:test",
                source_manifest_id="manifest:structure-units:test",
                schema_version=2,
                records=(
                    StructureUnitSummaryRecord(
                        summary_id="structure_unit:protein:P69905:4HHB:A",
                        protein_ref="protein:P69905",
                        structure_source="PDB",
                        structure_id="4HHB",
                        chain_id="A",
                        experimental_or_predicted="experimental",
                        mapping_status="joined",
                    ),
                    StructureUnitSummaryRecord(
                        summary_id="structure_unit:protein:P68871:4HHB:B",
                        protein_ref="protein:P68871",
                        structure_source="PDB",
                        structure_id="4HHB",
                        chain_id="B",
                        experimental_or_predicted="experimental",
                        mapping_status="joined",
                    ),
                ),
            ).to_dict(),
            indent=2,
        ),
        encoding="utf-8",
    )
    return materialized_path


def test_operator_snapshot_smoke_matches_validator_contract(tmp_path: Path) -> None:
    if not shutil.which("powershell.exe") and not shutil.which("pwsh.exe"):
        pytest.skip("PowerShell is required for the operator snapshot smoke test")

    repo_root = tmp_path / "repo"
    _copy_fixture_tree(REPO_ROOT, repo_root)

    operator = _run_interface(repo_root)
    validated = _run_validator(repo_root)
    summary = json.loads(
        (repo_root / "runs" / "real_data_benchmark" / "full_results" / "summary.json").read_text(
            encoding="utf-8"
        )
    )
    run_summary = json.loads(
        (
            repo_root / "runs" / "real_data_benchmark" / "full_results" / "run_summary.json"
        ).read_text(encoding="utf-8")
    )

    assert operator["benchmark"]["release_grade_status"] == "blocked"
    assert operator["benchmark"]["release_ready"] is False
    assert operator["benchmark"]["benchmark_summary"]["status"] == summary["status"]
    assert operator["benchmark"]["completion_status"] == summary["status"]
    assert operator["benchmark"]["release_grade_blockers"] == run_summary["remaining_gaps"]
    assert validated["status"] == "ok"
    assert validated["parity"]["completion_status"] == operator["benchmark"]["completion_status"]
    assert validated["parity"]["release_grade_status"] == operator["benchmark"][
        "release_grade_status"
    ]
    assert validated["parity"]["selected_accession_count"] == operator["benchmark"][
        "selected_accession_count"
    ]
    assert validated["live_state"]["benchmark_release_ready"] is False
    assert validated["live_state"]["runtime_supervisor_running"] == operator["runtime"][
        "supervisor_running"
    ]
    assert validated["source_files"]["operator_dashboard_path"].endswith(
        "operator_dashboard.json"
    )
    assert operator["library"]["materialized"] is False
    assert operator["library"]["materialized_path"] is None
    assert operator["library"]["materialized_library_id"] is None
    assert operator["library"]["materialized_source_manifest_id"] is None
    assert operator["library"]["materialized_record_count"] == 0
    assert operator["library"]["materialized_record_types"] == {}
    assert operator["runtime"]["supervisor_heartbeat"]["status"] == "unavailable"
    assert operator["runtime"]["supervisor_staleness"]["status"] == "unavailable"
    assert validated["live_state"]["library_materialized"] is False
    assert validated["live_state"]["library_materialized_path"] is None
    assert validated["live_state"]["library_materialized_library_id"] is None
    assert validated["live_state"]["library_materialized_source_manifest_id"] is None
    assert validated["live_state"]["library_materialized_record_count"] == 0
    assert validated["live_state"]["library_materialized_record_types"] == {}
    assert validated["live_state"]["library_materialized_error"] is None


def test_operator_snapshot_smoke_surfaces_materialized_summary_library_fields(
    tmp_path: Path,
) -> None:
    if not shutil.which("powershell.exe") and not shutil.which("pwsh.exe"):
        pytest.skip("PowerShell is required for the operator snapshot smoke test")

    repo_root = tmp_path / "repo"
    _copy_fixture_tree(REPO_ROOT, repo_root)
    materialized_path = _write_materialized_summary_library(repo_root)

    operator = _run_interface(repo_root)
    validated = _run_validator(repo_root)

    assert operator["library"]["materialized"] is True
    assert operator["library"]["materialized_path"] == str(materialized_path)
    assert operator["library"]["materialized_error"] is None
    assert operator["library"]["materialized_library_id"] == "summary-library:materialized"
    assert operator["library"]["materialized_source_manifest_id"] == "manifest:materialized"
    assert operator["library"]["materialized_record_count"] == 2
    assert operator["library"]["materialized_record_types"] == {
        "protein": 1,
        "protein_protein": 1,
    }
    assert validated["status"] == "ok"
    assert validated["live_state"]["library_materialized"] is True
    assert validated["live_state"]["library_materialized_path"] == str(materialized_path)
    assert validated["live_state"]["library_materialized_library_id"] == (
        "summary-library:materialized"
    )
    assert validated["live_state"]["library_materialized_source_manifest_id"] == (
        "manifest:materialized"
    )
    assert validated["live_state"]["library_materialized_record_count"] == 2
    assert validated["live_state"]["library_materialized_record_types"] == {
        "protein": 1,
        "protein_protein": 1,
    }


def test_operator_snapshot_smoke_surfaces_reactome_materialized_summary_library(
    tmp_path: Path,
) -> None:
    if not shutil.which("powershell.exe") and not shutil.which("pwsh.exe"):
        pytest.skip("PowerShell is required for the operator snapshot smoke test")

    repo_root = tmp_path / "repo"
    _copy_fixture_tree(REPO_ROOT, repo_root)
    materialized_path = _write_reactome_materialized_summary_library(repo_root)

    operator = _run_interface(repo_root)
    validated = _run_validator(repo_root)

    assert operator["library"]["materialized"] is True
    assert operator["library"]["materialized_path"] == str(materialized_path)
    assert operator["library"]["materialized_error"] is None
    assert operator["library"]["materialized_library_id"] == (
        "summary-library:reactome-local:test"
    )
    assert operator["library"]["materialized_source_manifest_id"] == (
        "bio-agent-lab/reactome:test"
    )
    assert operator["library"]["materialized_record_count"] == 2
    assert operator["library"]["materialized_record_types"] == {"protein": 2}
    assert validated["status"] == "ok"
    assert validated["live_state"]["library_materialized"] is True
    assert validated["live_state"]["library_materialized_path"] == str(materialized_path)
    assert validated["live_state"]["library_materialized_library_id"] == (
        "summary-library:reactome-local:test"
    )
    assert validated["live_state"]["library_materialized_source_manifest_id"] == (
        "bio-agent-lab/reactome:test"
    )
    assert validated["live_state"]["library_materialized_record_count"] == 2
    assert validated["live_state"]["library_materialized_record_types"] == {"protein": 2}


def test_operator_snapshot_smoke_surfaces_intact_materialized_summary_library(
    tmp_path: Path,
) -> None:
    if not shutil.which("powershell.exe") and not shutil.which("pwsh.exe"):
        pytest.skip("PowerShell is required for the operator snapshot smoke test")

    repo_root = tmp_path / "repo"
    _copy_fixture_tree(REPO_ROOT, repo_root)
    materialized_path = _write_intact_materialized_summary_library(repo_root)

    operator = _run_interface(repo_root)
    validated = _run_validator(repo_root)

    assert operator["library"]["materialized"] is True
    assert operator["library"]["materialized_path"] == str(materialized_path)
    assert operator["library"]["materialized_error"] is None
    assert operator["library"]["materialized_library_id"] == (
        "summary-library:intact-local:test"
    )
    assert operator["library"]["materialized_source_manifest_id"] == (
        "IntAct:test-release:download:testfingerprint"
    )
    assert operator["library"]["materialized_record_count"] == 2
    assert operator["library"]["materialized_record_types"] == {
        "protein": 1,
        "protein_protein": 1,
    }
    assert validated["status"] == "ok"
    assert validated["live_state"]["library_materialized"] is True
    assert validated["live_state"]["library_materialized_path"] == str(materialized_path)
    assert validated["live_state"]["library_materialized_library_id"] == (
        "summary-library:intact-local:test"
    )
    assert validated["live_state"]["library_materialized_source_manifest_id"] == (
        "IntAct:test-release:download:testfingerprint"
    )
    assert validated["live_state"]["library_materialized_record_count"] == 2
    assert validated["live_state"]["library_materialized_record_types"] == {
        "protein": 1,
        "protein_protein": 1,
    }


def test_operator_snapshot_smoke_surfaces_structure_unit_materialized_summary_library(
    tmp_path: Path,
) -> None:
    if not shutil.which("powershell.exe") and not shutil.which("pwsh.exe"):
        pytest.skip("PowerShell is required for the operator snapshot smoke test")

    repo_root = tmp_path / "repo"
    _copy_fixture_tree(REPO_ROOT, repo_root)
    materialized_path = _write_structure_unit_materialized_summary_library(repo_root)

    operator = _run_interface(repo_root)
    validated = _run_validator(repo_root)

    assert operator["library"]["materialized"] is True
    assert operator["library"]["materialized_path"] == str(materialized_path)
    assert operator["library"]["materialized_error"] is None
    assert operator["library"]["materialized_library_id"] == (
        "summary-library:structure-units:test"
    )
    assert operator["library"]["materialized_source_manifest_id"] == (
        "manifest:structure-units:test"
    )
    assert operator["library"]["materialized_record_count"] == 2
    assert operator["library"]["materialized_record_types"] == {"structure_unit": 2}
    assert validated["status"] == "ok"
    assert validated["live_state"]["library_materialized"] is True
    assert validated["live_state"]["library_materialized_path"] == str(materialized_path)
    assert validated["live_state"]["library_materialized_library_id"] == (
        "summary-library:structure-units:test"
    )
    assert validated["live_state"]["library_materialized_source_manifest_id"] == (
        "manifest:structure-units:test"
    )
    assert validated["live_state"]["library_materialized_record_count"] == 2
    assert validated["live_state"]["library_materialized_record_types"] == {
        "structure_unit": 2
    }


def test_operator_runtime_surfaces_healthy_supervisor_heartbeat(tmp_path: Path) -> None:
    if not shutil.which("powershell.exe") and not shutil.which("pwsh.exe"):
        pytest.skip("PowerShell is required for the operator snapshot smoke test")

    repo_root = tmp_path / "repo"
    _copy_fixture_tree(REPO_ROOT, repo_root)
    _write_supervisor_heartbeat(
        repo_root,
        last_heartbeat_at=datetime.now(UTC) - timedelta(seconds=15),
    )

    runtime = _run_runtime(repo_root)

    assert runtime["supervisor_heartbeat"]["status"] == "healthy"
    assert runtime["supervisor_heartbeat"]["is_stale"] is False
    assert runtime["supervisor_heartbeat"]["age_seconds"] is not None
    assert runtime["supervisor_heartbeat"]["age_seconds"] < 300
    assert runtime["supervisor_staleness"]["status"] == "healthy"
    assert runtime["supervisor_staleness"]["is_stale"] is False
    assert runtime["supervisor_staleness"]["age_seconds"] == runtime["supervisor_heartbeat"][
        "age_seconds"
    ]


def test_operator_runtime_surfaces_stale_supervisor_heartbeat(tmp_path: Path) -> None:
    if not shutil.which("powershell.exe") and not shutil.which("pwsh.exe"):
        pytest.skip("PowerShell is required for the operator snapshot smoke test")

    repo_root = tmp_path / "repo"
    _copy_fixture_tree(REPO_ROOT, repo_root)
    _write_supervisor_heartbeat(
        repo_root,
        last_heartbeat_at=datetime.now(UTC) - timedelta(minutes=20),
        iteration=9,
    )

    runtime = _run_runtime(repo_root)

    assert runtime["supervisor_heartbeat"]["status"] == "stale"
    assert runtime["supervisor_heartbeat"]["is_stale"] is True
    assert runtime["supervisor_heartbeat"]["age_seconds"] >= 300
    assert runtime["supervisor_staleness"]["status"] == "stale"
    assert runtime["supervisor_staleness"]["is_stale"] is True
    assert runtime["supervisor_heartbeat"]["iteration"] == 9
    assert runtime["supervisor_heartbeat"]["phase"] == "cycle_complete"


def test_operator_runtime_surfaces_supervisor_heartbeat_history(tmp_path: Path) -> None:
    if not shutil.which("powershell.exe") and not shutil.which("pwsh.exe"):
        pytest.skip("PowerShell is required for the operator snapshot smoke test")

    repo_root = tmp_path / "repo"
    _copy_fixture_tree(REPO_ROOT, repo_root)
    first = datetime.now(UTC) - timedelta(minutes=2)
    second = datetime.now(UTC) - timedelta(seconds=30)
    history_path = _write_supervisor_heartbeat_history(
        repo_root,
        timestamps=[first, second],
    )
    _write_supervisor_heartbeat(
        repo_root,
        last_heartbeat_at=second,
        iteration=2,
    )

    runtime = _run_runtime(repo_root)

    assert runtime["supervisor_heartbeat_history"]["path"] == str(history_path)
    assert runtime["supervisor_heartbeat_history"]["exists"] is True
    assert runtime["supervisor_heartbeat_history"]["error"] is None
    assert runtime["supervisor_heartbeat_history"]["entry_count"] == 2
    assert runtime["supervisor_heartbeat_history"]["last_heartbeat_at"] is not None


def test_operator_runtime_surfaces_soak_summary(tmp_path: Path) -> None:
    if not shutil.which("powershell.exe") and not shutil.which("pwsh.exe"):
        pytest.skip("PowerShell is required for the operator snapshot smoke test")

    repo_root = tmp_path / "repo"
    _copy_fixture_tree(REPO_ROOT, repo_root)
    _write_soak_ledger(
        repo_root,
        entries=[
            {
                "observed_at": "2026-03-23T10:00:00+00:00",
                "queue_counts": {"done": 261, "pending": 25},
                "benchmark_completion_status": "blocked_on_release_grade_bar",
                "truth_boundary": {
                    "prototype_runtime": True,
                    "weeklong_soak_claim_allowed": False,
                },
                "supervisor_heartbeat": {"status": "healthy", "age_seconds": 12},
            },
            {
                "observed_at": "2026-03-23T10:30:00+00:00",
                "queue_counts": {"done": 261, "pending": 25, "blocked": 12},
                "benchmark_completion_status": "blocked_on_release_grade_bar",
                "truth_boundary": {
                    "prototype_runtime": True,
                    "weeklong_soak_claim_allowed": False,
                },
                "supervisor_heartbeat": {"status": "unavailable", "age_seconds": None},
            },
        ],
    )

    runtime = _run_runtime(repo_root)

    assert runtime["soak_summary"]["exists"] is True
    assert runtime["soak_summary"]["script_exists"] is True
    assert runtime["soak_summary"]["error"] is None
    assert runtime["soak_summary"]["entry_count"] == 2
    assert runtime["soak_summary"]["incident_count"] == 1
    assert runtime["soak_summary"]["observed_window_hours"] == 0.5
    assert runtime["soak_summary"]["observed_window_progress_ratio"] == 0.003
    assert runtime["soak_summary"]["remaining_hours_to_weeklong"] == 167.5
    assert runtime["soak_summary"]["estimated_weeklong_completion_at"] == (
        "2026-03-30T10:00:00+00:00"
    )
    assert runtime["soak_summary"]["latest_queue_counts"]["blocked"] == 12
    assert runtime["soak_summary"]["truth_boundary"]["weeklong_soak_claim_allowed"] is False


def test_operator_runtime_surfaces_soak_anomaly_digest(tmp_path: Path) -> None:
    if not shutil.which("powershell.exe") and not shutil.which("pwsh.exe"):
        pytest.skip("PowerShell is required for the operator snapshot smoke test")

    repo_root = tmp_path / "repo"
    _copy_fixture_tree(REPO_ROOT, repo_root)
    _write_soak_ledger(
        repo_root,
        entries=[
            {
                "observed_at": "2026-03-23T10:00:00+00:00",
                "queue_counts": {"done": 261, "pending": 25},
                "truth_boundary": {
                    "prototype_runtime": True,
                    "weeklong_soak_claim_allowed": False,
                },
                "supervisor_heartbeat": {"status": "unavailable", "age_seconds": None},
            },
            {
                "observed_at": "2026-03-23T10:30:00+00:00",
                "queue_counts": {"done": 261, "pending": 24},
                "truth_boundary": {
                    "prototype_runtime": True,
                    "weeklong_soak_claim_allowed": False,
                },
                "supervisor_heartbeat": {"status": "healthy", "age_seconds": 5},
            },
            {
                "observed_at": "2026-03-23T11:00:00+00:00",
                "queue_counts": {"done": 262, "pending": 24},
                "truth_boundary": {
                    "prototype_runtime": True,
                    "weeklong_soak_claim_allowed": False,
                },
                "supervisor_heartbeat": {"status": "healthy", "age_seconds": 4},
            },
        ],
    )

    runtime = _run_runtime(repo_root)

    assert runtime["soak_anomaly"]["exists"] is True
    assert runtime["soak_anomaly"]["script_exists"] is True
    assert runtime["soak_anomaly"]["error"] is None
    assert runtime["soak_anomaly"]["entry_count"] == 3
    assert runtime["soak_anomaly"]["incident_count"] == 1
    assert runtime["soak_anomaly"]["longest_healthy_streak"] == 2
    assert runtime["soak_anomaly"]["current_healthy_streak"] == 2
    assert runtime["soak_anomaly"]["queue_transition_count"] == 2
    assert runtime["soak_anomaly"]["truth_boundary"]["weeklong_soak_claim_allowed"] is False


def test_operator_runtime_surfaces_operational_readiness_snapshot(tmp_path: Path) -> None:
    if not shutil.which("powershell.exe") and not shutil.which("pwsh.exe"):
        pytest.skip("PowerShell is required for the operator snapshot smoke test")

    repo_root = tmp_path / "repo"
    _copy_fixture_tree(REPO_ROOT, repo_root)
    _write_supervisor_heartbeat(
        repo_root,
        last_heartbeat_at=datetime.now(UTC) - timedelta(seconds=30),
        iteration=7,
    )
    _write_soak_ledger(
        repo_root,
        entries=[
            {
                "observed_at": "2026-03-23T10:00:00+00:00",
                "queue_counts": {"done": 261, "pending": 25, "blocked": 12, "dispatched": 1},
                "truth_boundary": {
                    "prototype_runtime": True,
                    "weeklong_soak_claim_allowed": False,
                },
                "supervisor_heartbeat": {"status": "healthy", "age_seconds": 5},
            },
            {
                "observed_at": "2026-03-23T10:45:00+00:00",
                "queue_counts": {"done": 261, "pending": 25, "blocked": 12, "dispatched": 1},
                "truth_boundary": {
                    "prototype_runtime": True,
                    "weeklong_soak_claim_allowed": False,
                },
                "supervisor_heartbeat": {"status": "healthy", "age_seconds": 4},
            },
        ],
    )

    runtime = _run_runtime(repo_root)

    assert runtime["operational_readiness"]["script_exists"] is True
    assert runtime["operational_readiness"]["error"] is None
    assert runtime["operational_readiness"]["generated_at"] is not None
    assert runtime["operational_readiness"]["supervisor"]["status"] == "healthy"
    assert runtime["operational_readiness"]["soak_summary"]["entry_count"] == 2
    assert runtime["operational_readiness"]["queue_drift"]["has_drift"] is True
    assert runtime["operational_readiness"]["truth_audit"]["status"] == "ok"
    assert (
        runtime["operational_readiness"]["release_gate"]["operational_readiness_ready"]
        is False
    )


def test_operator_runtime_surfaces_packet_library_health(tmp_path: Path) -> None:
    if not shutil.which("powershell.exe") and not shutil.which("pwsh.exe"):
        pytest.skip("PowerShell is required for the operator snapshot smoke test")

    repo_root = tmp_path / "repo"
    _copy_fixture_tree(REPO_ROOT, repo_root)
    _write_packet_library_state(repo_root)

    runtime = _run_runtime(repo_root)

    assert runtime["packet_library"]["latest_exists"] is True
    assert runtime["packet_library"]["dashboard_exists"] is True
    assert runtime["packet_library"]["run_id"] == "selected-cohort-fixture"
    assert runtime["packet_library"]["status"] == "partial"
    assert runtime["packet_library"]["packet_count"] == 12
    assert runtime["packet_library"]["complete_count"] == 4
    assert runtime["packet_library"]["partial_count"] == 8
    assert runtime["packet_library"]["unresolved_count"] == 0
    assert runtime["packet_library"]["modality_deficit_counts"]["ligand"] == 7
    assert runtime["packet_library"]["source_fix_candidate_count"] == 9
    assert runtime["packet_library"]["top_source_fix_refs"][0] == "ligand:P00387"

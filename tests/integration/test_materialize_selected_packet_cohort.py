from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _copy_module(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _make_temp_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    _copy_module(
        REPO_ROOT / "scripts" / "materialize_selected_packet_cohort.py",
        repo_root / "scripts" / "materialize_selected_packet_cohort.py",
    )
    _copy_module(
        REPO_ROOT / "execution" / "materialization" / "training_packet_materializer.py",
        repo_root / "execution" / "materialization" / "training_packet_materializer.py",
    )
    return repo_root


def _balanced_plan() -> dict[str, object]:
    return {
        "generated_at": "2026-03-23T00:00:00Z",
        "requested_modalities": ["sequence", "structure", "ligand", "ppi"],
        "packet_materialization_mode": "materialized_packets_present",
        "selected_rows": [
            {
                "packet_id": "packet-P69905",
                "accession": "P69905",
                "canonical_id": "protein:P69905",
                "split": "train",
                "cohort_bucket": "anchor_rich",
                "status": "supported",
                "score_trace": {"accepted": True, "total_score": 96.0},
                "packet_expectation": {
                    "source": "materialized_packet",
                    "status": "partial",
                    "packet_ready": False,
                    "requested_modalities": ["sequence", "structure", "ligand", "ppi"],
                    "present_modalities": ["sequence", "structure"],
                    "missing_modalities": ["ligand", "ppi"],
                    "notes": ["balanced plan row"],
                },
                "truth": {
                    "registry": {
                        "source_manifest_ids": ["raw:uniprot:P69905", "raw:alphafold:P69905"],
                    }
                },
                "evidence_refs": ["runs/real_data_benchmark/full_results/source_coverage.json"],
                "notes": ["selected row"],
            },
            {
                "packet_id": "packet-P68871",
                "accession": "P68871",
                "canonical_id": "protein:P68871",
                "split": "train",
                "cohort_bucket": "probe_backed",
                "status": "weak",
                "score_trace": {"accepted": True, "total_score": 82.0},
                "packet_expectation": {
                    "source": "materialized_packet",
                    "status": "partial",
                    "packet_ready": False,
                    "requested_modalities": ["sequence", "structure", "ligand", "ppi"],
                    "present_modalities": ["sequence", "ppi"],
                    "missing_modalities": ["structure", "ligand"],
                    "notes": ["probe-backed row"],
                },
                "truth": {
                    "registry": {
                        "source_manifest_ids": ["raw:uniprot:P68871"],
                    }
                },
                "evidence_refs": ["runs/real_data_benchmark/full_results/source_coverage.json"],
                "notes": ["selected row"],
            },
            {
                "packet_id": "packet-P09105",
                "accession": "P09105",
                "canonical_id": "protein:P09105",
                "split": "test",
                "cohort_bucket": "blocked_control",
                "status": "blocked",
                "score_trace": {"accepted": False, "total_score": 14.0},
                "packet_expectation": {
                    "source": "inferred_from_coverage",
                    "status": "partial",
                    "packet_ready": False,
                    "requested_modalities": ["sequence", "structure", "ligand", "ppi"],
                    "present_modalities": ["sequence"],
                    "missing_modalities": ["structure", "ligand", "ppi"],
                    "notes": ["no payloads available"],
                },
                "truth": {"registry": {"source_manifest_ids": []}},
                "notes": ["selected row"],
            },
        ],
    }


def _available_payloads() -> dict[str, object]:
    return {
        "sequence:P69905": {"sequence": "VLSPADK", "length": 7},
        "structure:P69905": {
            "kind": "file_ref",
            "path": "materialized/structures/P69905.cif",
        },
        "sequence:P68871": {"sequence": "VHLTPEE", "length": 7},
        "structure:P68871": {
            "kind": "file_ref",
            "path": "materialized/structures/P68871.cif",
        },
        "ppi:P68871": {
            "kind": "file_ref",
            "path": "materialized/ppi/P68871.json",
        },
        "ligand:P68871": {
            "kind": "file_ref",
            "path": "materialized/ligand/P68871.bindingdb.json",
        },
        "ligand:P69905": {
            "kind": "file_ref",
            "path": "materialized/ligand/P69905.bindingdb.json",
        },
        "ppi:P69905": {
            "kind": "file_ref",
            "path": "materialized/ppi/P69905.txt",
        },
        "structure:P09105": {
            "kind": "file_ref",
            "path": "materialized/structures/P09105.cif",
        },
        "ppi:P09105": {
            "kind": "file_ref",
            "path": "materialized/ppi/P09105.txt",
        },
        "sequence:P09105": {"sequence": "MNNR", "length": 4},
    }


def _write_materialized_file(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def _populate_file_refs(repo_root: Path) -> None:
    _write_materialized_file(
        repo_root / "materialized" / "structures" / "P69905.cif",
        "data_P69905\n#\n",
    )
    _write_materialized_file(
        repo_root / "materialized" / "ppi" / "P69905.txt",
        "uniprotkb:P69905\tuniprotkb:P68871\n",
    )
    _write_materialized_file(
        repo_root / "materialized" / "structures" / "P09105.cif",
        "data_P09105\n#\n",
    )
    _write_materialized_file(
        repo_root / "materialized" / "structures" / "P68871.cif",
        "data_P68871\n#\n",
    )
    _write_materialized_file(
        repo_root / "materialized" / "ppi" / "P09105.txt",
        "uniprotkb:P09105\tuniprotkb:P68871\n",
    )
    _write_materialized_file(
        repo_root / "materialized" / "ppi" / "P68871.json",
        json.dumps(
            {
                "materialized_ref": "materialized/ppi/P68871.json",
                "checksum": "sha256:ppi-p68871",
                "provenance_refs": ["prov:ppi:P68871"],
            },
            indent=2,
        ),
    )
    _write_materialized_file(
        repo_root / "materialized" / "ligand" / "P68871.bindingdb.json",
        json.dumps({"ligand": "HEM"}, indent=2),
    )
    _write_materialized_file(
        repo_root / "materialized" / "ligand" / "P69905.bindingdb.json",
        json.dumps({"ligand": "CMO"}, indent=2),
    )

def test_materialize_selected_packet_cohort_cli_materializes_selected_rows(
    tmp_path: Path,
) -> None:
    repo_root = _make_temp_repo(tmp_path)
    plan_path = repo_root / "runs" / "real_data_benchmark" / "full_results" / "balanced.json"
    payloads_path = repo_root / "runs" / "real_data_benchmark" / "full_results" / "payloads.json"
    output_path = repo_root / "data" / "packages" / "selected_cohort_materialization.json"
    output_root = repo_root / "data" / "packages"
    _write_json(plan_path, _balanced_plan())
    _write_json(payloads_path, _available_payloads())
    _populate_file_refs(repo_root)

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "materialize_selected_packet_cohort.py"),
            "--balanced-plan",
            str(plan_path),
            "--available-payloads",
            str(payloads_path),
            "--output-root",
            str(output_root),
            "--output",
            str(output_path),
            "--run-id",
            "selected-run-1",
            "--json",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    payload = json.loads(result.stdout)
    saved_payload = json.loads(output_path.read_text(encoding="utf-8"))
    latest_payload = json.loads((output_root / "LATEST.json").read_text(encoding="utf-8"))
    latest_partial_payload = json.loads(
        (output_root / "LATEST.partial.json").read_text(encoding="utf-8")
    )
    run_summary = json.loads(
        (
            output_root / "selected-run-1" / "materialization_summary.json"
        ).read_text(encoding="utf-8")
    )

    assert payload == saved_payload
    assert payload["task_id"] == "P26-T010"
    assert payload["selected_count"] == 3
    assert payload["status"] == "partial"
    assert payload["available_payloads"]["file_sha256"]
    assert len(payload["available_payloads"]["file_sha256"]) == 64
    assert payload["available_payloads"]["available_payloads_sha256"]
    assert len(payload["available_payloads"]["available_payloads_sha256"]) == 64
    assert payload["available_payloads"]["registry_fingerprints"]["build_sha256"]
    assert len(payload["available_payloads"]["registry_fingerprints"]["build_sha256"]) == 64
    assert payload["available_payloads"]["registry_fingerprints"]["digest_basis"] == (
        "sorted_json_content"
    )
    assert payload["available_payloads_build_sha256"] == payload["available_payloads"][
        "registry_fingerprints"
    ]["build_sha256"]
    assert payload["materialization"]["release_grade_ready"] is False
    assert payload["materialization"]["latest_promotion_state"] == "held"
    assert payload["latest_summary_consistency"]["guard_active"] is True
    assert payload["latest_summary_consistency"]["status"] == "consistent"
    assert payload["latest_summary_consistency"]["inconsistent_promoted_packet_count"] == 0
    assert payload["summary"]["packet_count"] == 3
    assert payload["summary"]["complete_count"] == 2
    assert payload["summary"]["partial_count"] == 1
    assert payload["summary"]["unresolved_count"] == 0
    assert payload["summary"]["packet_status_counts"] == {
        "complete": 2,
        "partial": 1,
    }
    assert payload["summary"]["expected_status_counts"] == {"partial": 3}
    assert payload["summary"]["missing_modality_counts"] == {
        "ligand": 1,
    }
    assert payload["summary"]["status_mismatch_count"] == 2
    assert payload["summary"]["status_mismatches"][0] == {
        "accession": "P69905",
        "expected_status": "partial",
        "materialized_status": "complete",
    }
    assert payload["summary"]["status_mismatches"][1] == {
        "accession": "P68871",
        "expected_status": "partial",
        "materialized_status": "complete",
    }

    packets = {row["accession"]: row for row in payload["selected_rows"]}
    assert packets["P69905"]["requested_modalities"] == [
        "sequence",
        "structure",
        "ligand",
        "ppi",
    ]
    assert packets["P69905"]["present_modalities"] == ["sequence", "structure", "ligand", "ppi"]
    assert packets["P69905"]["missing_modalities"] == []
    assert packets["P69905"]["expected_status"] == "partial"
    assert packets["P68871"]["status"] == "complete"
    assert packets["P09105"]["status"] == "partial"
    assert packets["P09105"]["expected_status"] == "partial"

    assert latest_payload["packet_count"] == 3
    assert latest_payload["partial_count"] == 1
    assert latest_payload["release_grade_ready"] is False
    assert latest_payload["latest_promotion_state"] == "held"
    latest_packets = {packet["accession"]: packet for packet in latest_payload["packets"]}
    assert latest_packets["P69905"]["status"] == "complete"
    assert latest_packets["P69905"]["release_grade_ready"] is True
    assert latest_packets["P69905"]["latest_promotion_state"] == "held"
    assert latest_partial_payload["status"] == "partial"
    assert run_summary["packet_count"] == 3
    assert run_summary["status"] == "partial"
    packet_manifest = output_root / "selected-run-1" / "packet-p69905" / "packet_manifest.json"
    assert packet_manifest.exists()
    structure_artifact = (
        output_root
        / "selected-run-1"
        / "packet-p69905"
        / "artifacts"
        / "structure-1.cif"
    )
    assert structure_artifact.read_text(encoding="utf-8") == "data_P69905\n#\n"


def test_materialize_selected_packet_cohort_cli_handles_missing_payloads_conservatively(
    tmp_path: Path,
) -> None:
    repo_root = _make_temp_repo(tmp_path)
    plan_path = repo_root / "runs" / "real_data_benchmark" / "full_results" / "balanced.json"
    output_path = repo_root / "data" / "packages" / "selected_cohort_materialization.json"
    output_root = repo_root / "data" / "packages"
    _write_json(
        plan_path,
        {
            "generated_at": "2026-03-23T00:00:00Z",
            "requested_modalities": ["sequence", "structure"],
            "selected_rows": [
                {
                    "packet_id": "packet-P04637",
                    "accession": "P04637",
                    "canonical_id": "protein:P04637",
                    "split": "train",
                    "packet_expectation": {
                        "source": "inferred_from_coverage",
                        "status": "partial",
                        "packet_ready": False,
                        "present_modalities": ["sequence"],
                        "missing_modalities": ["structure"],
                    },
                }
            ],
        },
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "materialize_selected_packet_cohort.py"),
            "--balanced-plan",
            str(plan_path),
            "--output-root",
            str(output_root),
            "--output",
            str(output_path),
            "--run-id",
            "selected-run-2",
            "--json",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode != 0
    assert "available payload registry is required" in result.stderr
    assert output_path.exists() is False
    assert (output_root / "LATEST.json").exists() is False


def test_materialize_selected_packet_cohort_preserves_stronger_existing_root_report(
    tmp_path: Path,
) -> None:
    repo_root = _make_temp_repo(tmp_path)
    plan_path = repo_root / "runs" / "real_data_benchmark" / "full_results" / "balanced.json"
    payloads_path = repo_root / "runs" / "real_data_benchmark" / "full_results" / "payloads.json"
    output_path = repo_root / "data" / "packages" / "selected_cohort_materialization.json"
    output_root = repo_root / "data" / "packages"
    _write_json(plan_path, _balanced_plan())
    _write_json(payloads_path, _available_payloads())
    _populate_file_refs(repo_root)

    stronger_root_report = {
        "status": "partial",
        "summary": {
            "packet_count": 3,
            "complete_count": 3,
            "partial_count": 0,
            "unresolved_count": 0,
        },
        "run_id": "previous-stronger-run",
    }
    _write_json(output_path, stronger_root_report)

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "materialize_selected_packet_cohort.py"),
            "--balanced-plan",
            str(plan_path),
            "--available-payloads",
            str(payloads_path),
            "--output-root",
            str(output_root),
            "--output",
            str(output_path),
            "--run-id",
            "selected-run-weaker",
            "--json",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    current_payload = json.loads(result.stdout)
    preserved_root = json.loads(output_path.read_text(encoding="utf-8"))
    run_scoped = json.loads(
        (
            output_root / "selected-run-weaker" / "selected_cohort_materialization.json"
        ).read_text(encoding="utf-8")
    )

    assert current_payload["summary"]["complete_count"] == 2
    assert preserved_root["run_id"] == "previous-stronger-run"
    assert preserved_root["summary"]["complete_count"] == 3
    assert run_scoped["run_id"] == "selected-run-weaker"
    assert run_scoped["summary"]["complete_count"] == 2

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
        REPO_ROOT / "scripts" / "materialize_balanced_dataset_plan.py",
        repo_root / "scripts" / "materialize_balanced_dataset_plan.py",
    )
    _copy_module(
        REPO_ROOT / "datasets" / "recipes" / "balanced_cohort_scorer.py",
        repo_root / "datasets" / "recipes" / "balanced_cohort_scorer.py",
    )

    _write_json(
        repo_root / "runs" / "real_data_benchmark" / "full_results" / "source_coverage.json",
        {
            "coverage_matrix": [
                {
                    "accession": "P69905",
                    "canonical_id": "protein:P69905",
                    "split": "train",
                    "leakage_key": "P69905",
                    "bucket": "rich_coverage",
                    "evidence_mode": "direct_live_smoke",
                    "validation_class": "direct_live_smoke",
                    "lane_depth": 5,
                    "source_lanes": [
                        "UniProt",
                        "InterPro",
                        "Reactome",
                        "AlphaFold DB",
                        "Evolutionary / MSA",
                    ],
                    "thin_coverage": False,
                    "mixed_evidence": False,
                },
                {
                    "accession": "P68871",
                    "canonical_id": "protein:P68871",
                    "split": "train",
                    "leakage_key": "P68871",
                    "bucket": "rich_coverage",
                    "evidence_mode": "live_summary_library_probe",
                    "validation_class": "probe_backed",
                    "lane_depth": 2,
                    "source_lanes": [
                        "UniProt",
                        "protein-protein summary library",
                    ],
                    "thin_coverage": False,
                    "mixed_evidence": True,
                    "coverage_notes": ["summary-library probe rather than direct assay"],
                },
                {
                    "accession": "P69905",
                    "canonical_id": "protein:P69905-duplicate",
                    "split": "val",
                    "leakage_key": "P69905",
                    "bucket": "moderate_coverage",
                    "evidence_mode": "live_verified_accession",
                    "validation_class": "verified",
                    "lane_depth": 1,
                    "source_lanes": ["UniProt"],
                    "thin_coverage": True,
                    "mixed_evidence": False,
                },
            ]
        },
    )
    _write_json(
        (
            repo_root
            / "runs"
            / "real_data_benchmark"
            / "full_results"
            / "p15_upgraded_cohort_slice.json"
        ),
        {
            "rows": [
                {
                    "accession": "P69905",
                    "canonical_id": "protein:P69905",
                    "split": "train",
                    "protein_depth": {
                        "present_modalities": ["sequence", "structure"],
                        "missing_modalities": ["ligand", "ppi"],
                        "source_lanes": [
                            "UniProt",
                            "InterPro",
                            "Reactome",
                            "AlphaFold DB",
                            "Evolutionary / MSA",
                        ],
                    },
                },
                {
                    "accession": "P68871",
                    "canonical_id": "protein:P68871",
                    "split": "train",
                    "protein_depth": {
                        "present_modalities": ["sequence", "ppi"],
                        "missing_modalities": ["structure", "ligand"],
                        "source_lanes": [
                            "UniProt",
                            "protein-protein summary library",
                        ],
                    },
                },
            ]
        },
    )
    _write_json(
        repo_root / "data" / "packages" / "LATEST.json",
        {
            "run_id": "packet-run-1",
            "output_root": "data/packages/packet-run-1",
            "status": "partial",
            "packet_count": 2,
            "complete_count": 0,
            "partial_count": 2,
            "unresolved_count": 0,
            "packets": [
                {
                    "packet_id": "packet-P69905",
                    "accession": "P69905",
                    "canonical_id": "protein:P69905",
                    "status": "partial",
                    "packet_dir": "data/packages/packet-run-1/packet-p69905",
                    "manifest_path": (
                        "data/packages/packet-run-1/"
                        "packet-p69905/packet_manifest.json"
                    ),
                    "requested_modalities": ["sequence", "structure", "ligand", "ppi"],
                    "present_modalities": ["sequence", "structure"],
                    "missing_modalities": ["ligand", "ppi"],
                    "notes": ["missing payload for ligand:ligand:P69905"],
                },
                {
                    "packet_id": "packet-P68871",
                    "accession": "P68871",
                    "canonical_id": "protein:P68871",
                    "status": "partial",
                    "packet_dir": "data/packages/packet-run-1/packet-p68871",
                    "manifest_path": (
                        "data/packages/packet-run-1/"
                        "packet-p68871/packet_manifest.json"
                    ),
                    "requested_modalities": ["sequence", "structure", "ligand", "ppi"],
                    "present_modalities": ["sequence", "ppi"],
                    "missing_modalities": ["structure", "ligand"],
                    "notes": ["probe-backed packet"],
                },
            ],
        },
    )
    return repo_root


def test_materialize_balanced_dataset_plan_cli_uses_real_artifacts_and_packets(
    tmp_path: Path,
) -> None:
    repo_root = _make_temp_repo(tmp_path)
    output_path = repo_root / "runs" / "real_data_benchmark" / "full_results" / "balanced_plan.json"
    source_coverage_path = (
        repo_root / "runs" / "real_data_benchmark" / "full_results" / "source_coverage.json"
    )
    cohort_slice_path = (
        repo_root
        / "runs"
        / "real_data_benchmark"
        / "full_results"
        / "p15_upgraded_cohort_slice.json"
    )
    packet_summary_path = repo_root / "data" / "packages" / "LATEST.json"

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "materialize_balanced_dataset_plan.py"),
            "--source-coverage",
            str(source_coverage_path),
            "--cohort-slice",
            str(cohort_slice_path),
            "--packet-summary",
            str(packet_summary_path),
            "--requested-modalities",
            "sequence,structure,ligand,ppi",
            "--limit",
            "2",
            "--output",
            str(output_path),
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

    assert payload["requested_modalities"] == ["sequence", "structure", "ligand", "ppi"]
    assert payload["selected_count"] == 2
    assert payload["rejected_count"] == 1
    assert payload["packet_materialization_mode"] == "materialized_packets_present"
    assert payload["summary"]["leakage_safe"] is True
    assert payload["summary"]["selected_packet_status_counts"] == {"partial": 2}

    selected = {row["accession"]: row for row in payload["selected_rows"]}
    assert set(selected) == {"P69905", "P68871"}
    assert (
        selected["P69905"]["packet_expectation"]["source"] == "materialized_packet"
    )
    assert selected["P69905"]["packet_expectation"]["status"] == "partial"
    assert selected["P69905"]["score_trace"]["total_score"] > 0.8
    assert selected["P68871"]["score_trace"]["component_scores"]["diversity"] > 0.0

    rejected = payload["rejected_rows"][0]
    assert rejected["canonical_id"] == "protein:P69905-duplicate"
    assert "leakage_key=P69905 already selected" in rejected["score_trace"]["reasons"]
    assert saved_payload == payload


def test_materialize_balanced_dataset_plan_cli_infers_packet_expectations_when_absent(
    tmp_path: Path,
) -> None:
    repo_root = _make_temp_repo(tmp_path)
    packet_summary_path = repo_root / "data" / "packages" / "LATEST.json"
    packet_summary_path.unlink()
    source_coverage_path = (
        repo_root / "runs" / "real_data_benchmark" / "full_results" / "source_coverage.json"
    )
    cohort_slice_path = (
        repo_root
        / "runs"
        / "real_data_benchmark"
        / "full_results"
        / "p15_upgraded_cohort_slice.json"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "materialize_balanced_dataset_plan.py"),
            "--source-coverage",
            str(source_coverage_path),
            "--cohort-slice",
            str(cohort_slice_path),
            "--packet-summary",
            str(packet_summary_path),
            "--requested-modalities",
            "sequence,structure,ligand,ppi",
            "--limit",
            "1",
            "--json",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    payload = json.loads(result.stdout)
    assert payload["requested_modalities"] == ["sequence", "structure", "ligand", "ppi"]
    assert payload["packet_materialization_mode"] == "inferred_packet_expectations_only"
    assert payload["selected_count"] == 1
    packet_expectation = payload["selected_rows"][0]["packet_expectation"]
    assert packet_expectation["source"] == "inferred_from_coverage"
    assert packet_expectation["status"] == "partial"
    assert packet_expectation["packet_ready"] is False
    assert "packet expectation is inferred conservatively" in packet_expectation["notes"][1]

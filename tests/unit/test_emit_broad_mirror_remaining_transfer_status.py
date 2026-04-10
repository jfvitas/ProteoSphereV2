from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.emit_broad_mirror_remaining_transfer_status import (
    build_remaining_transfer_status,
    render_markdown,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_remaining_gaps(path: Path) -> None:
    _write_json(
        path,
        {
            "schema_id": "proteosphere-broad-mirror-remaining-gaps-2026-03-31",
            "generated_at": "2026-03-31T19:30:00+00:00",
            "status": "planning",
            "basis": {
                "broad_mirror_progress_path": "artifacts/status/broad_mirror_progress.json",
            },
            "summary": {
                "broad_mirror_coverage_percent": 86.4,
                "remaining_source_count": 2,
                "excluded_complete_source_count": 15,
                "source_count": 17,
                "total_gap_files": 22,
                "total_missing_files": 20,
                "total_partial_files": 2,
                "top_gap_sources": ["string", "uniprot"],
            },
            "remaining_sources": [
                {
                    "source_id": "string",
                    "source_name": "STRING v12",
                    "category": "interaction_networks",
                    "status": "partial",
                    "priority_rank": 1,
                    "coverage_percent": 53.8,
                    "missing_file_count": 11,
                    "partial_file_count": 1,
                    "missing_files": [
                        "protein.links.detailed.v12.0.txt.gz",
                        "protein.links.full.v12.0.txt.gz",
                        "protein.physical.links.v12.0.txt.gz",
                    ],
                    "partial_files": ["protein.links.v12.0.txt.gz"],
                    "representative_missing_files": ["protein.links.detailed.v12.0.txt.gz"],
                    "representative_partial_files": ["protein.links.v12.0.txt.gz"],
                },
                {
                    "source_id": "uniprot",
                    "source_name": "UniProt / UniRef / ID Mapping",
                    "category": "sequence_reference_backbone",
                    "status": "partial",
                    "priority_rank": 1,
                    "coverage_percent": 33.3,
                    "missing_file_count": 9,
                    "partial_file_count": 1,
                    "missing_files": [
                        "uniprot_trembl.xml.gz",
                        "uniref100.xml.gz",
                        "uniref90.xml.gz",
                        "idmapping_selected.tab.gz",
                    ],
                    "partial_files": ["uniprot_trembl.dat.gz"],
                    "representative_missing_files": ["uniprot_trembl.xml.gz"],
                    "representative_partial_files": ["uniprot_trembl.dat.gz"],
                },
            ],
            "gap_files": [],
            "notes": [],
        },
    )


def test_build_remaining_transfer_status_splits_active_from_not_started(
    tmp_path: Path,
) -> None:
    remaining_gaps_path = tmp_path / "artifacts" / "status" / "broad_mirror_remaining_gaps.json"
    runtime_dir = tmp_path / "artifacts" / "runtime"
    seed_root = tmp_path / "data" / "raw" / "protein_data_scope_seed"
    _write_remaining_gaps(remaining_gaps_path)

    _write_text(
        runtime_dir / "string_network_bulk_stdout.log",
        "protein.links.v12.0.txt.gz: 17.17% 22.0 GB/128.7 GB 5.1 MB/s\n",
    )
    _write_text(
        runtime_dir / "string_remaining_bulk_stdout.log",
        "protein.links.full.v12.0.txt.gz: 34.02% 67.9 GB/199.6 GB 1.5 MB/s\n",
    )
    _write_text(
        runtime_dir / "uniprot_resume_bulk_stdout.log",
        "uniprot_trembl.dat.gz: 18.56% 27.8 GB/149.8 GB 6.7 MB/s\n",
    )
    _write_text(
        runtime_dir / "uniprot_secondary_bulk_stdout.log",
        "uniprot_trembl.xml.gz: 70.68% 107.3 GB/151.8 GB 2.1 MB/s\n",
    )
    _write_text(
        runtime_dir / "uniprot_xml_bulk_stdout.log",
        "uniref100.xml.gz: 70.68% 107.3 GB/151.8 GB 2.1 MB/s\n",
    )

    _write_text(seed_root / "string" / "protein.links.detailed.v12.0.txt.gz.part", "")
    _write_text(seed_root / "uniprot" / "uniprot_trembl.dat.gz.part", "")
    _write_text(seed_root / "uniprot" / "uniprot_trembl.xml.gz.part", "")

    payload = build_remaining_transfer_status(
        remaining_gaps_path=remaining_gaps_path,
        runtime_dir=runtime_dir,
        seed_root=seed_root,
    )

    assert payload["summary"]["remaining_source_count"] == 2
    assert payload["summary"]["active_file_count"] == 6
    assert payload["summary"]["not_yet_started_file_count"] == 3
    assert payload["summary"]["active_source_counts"] == {"string": 3, "uniprot": 3}

    active = {(row["source_id"], row["filename"]) for row in payload["actively_transferring_now"]}
    assert active == {
        ("string", "protein.links.detailed.v12.0.txt.gz"),
        ("string", "protein.links.full.v12.0.txt.gz"),
        ("string", "protein.links.v12.0.txt.gz"),
        ("uniprot", "uniprot_trembl.dat.gz"),
        ("uniprot", "uniprot_trembl.xml.gz"),
        ("uniprot", "uniref100.xml.gz"),
    }

    not_started = {
        (row["source_id"], row["filename"]) for row in payload["not_yet_started"]
    }
    assert not_started == {
        ("string", "protein.physical.links.v12.0.txt.gz"),
        ("uniprot", "idmapping_selected.tab.gz"),
        ("uniprot", "uniref90.xml.gz"),
    }

    markdown = render_markdown(payload)
    assert "# Remaining Broad Mirror Transfer Status" in markdown
    assert "Actively Transferring Now" in markdown
    assert "Not Yet Started" in markdown
    assert "UniProt / UniRef / ID Mapping" in markdown
    assert "STRING v12" in markdown


def test_main_writes_remaining_transfer_outputs(tmp_path: Path) -> None:
    remaining_gaps_path = tmp_path / "artifacts" / "status" / "broad_mirror_remaining_gaps.json"
    runtime_dir = tmp_path / "artifacts" / "runtime"
    seed_root = tmp_path / "data" / "raw" / "protein_data_scope_seed"
    output_path = tmp_path / "artifacts" / "status" / "broad_mirror_remaining_transfer_status.json"
    markdown_path = tmp_path / "docs" / "reports" / "broad_mirror_remaining_transfer_status.md"
    _write_remaining_gaps(remaining_gaps_path)
    _write_text(runtime_dir / "string_network_bulk_stdout.log", "protein.links.v12.0.txt.gz\n")
    _write_text(seed_root / "string" / "protein.links.detailed.v12.0.txt.gz.part", "")

    result = subprocess.run(
        [
            sys.executable,
            str(
                Path(__file__).resolve().parents[2]
                / "scripts"
                / "emit_broad_mirror_remaining_transfer_status.py"
            ),
            "--remaining-gaps",
            str(remaining_gaps_path),
            "--runtime-dir",
            str(runtime_dir),
            "--seed-root",
            str(seed_root),
            "--output",
            str(output_path),
            "--markdown-output",
            str(markdown_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert "Remaining broad mirror transfer status exported:" in result.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["active_file_count"] >= 1
    assert markdown_path.read_text(encoding="utf-8").startswith(
        "# Remaining Broad Mirror Transfer Status"
    )

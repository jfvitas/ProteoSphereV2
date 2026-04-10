from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.emit_broad_mirror_remaining_gaps import (
    build_remaining_broad_mirror_gaps,
    render_markdown,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_progress(path: Path) -> None:
    _write_json(
        path,
        {
            "generated_at": "2026-03-31T18:00:00+00:00",
            "inputs": {
                "manifest_path": "protein_data_scope/sources_manifest.json",
                "seed_root": "data/raw/protein_data_scope_seed",
            },
            "schema_id": "proteosphere-broad-mirror-progress-2026-03-30",
            "status": "complete",
            "summary": {
                "source_count": 4,
                "file_coverage_percent": 86.4,
                "total_expected_files": 162,
                "total_present_files": 140,
                "total_missing_files": 20,
                "total_partial_files": 2,
                "source_status_counts": {
                    "complete": 2,
                    "partial": 2,
                },
                "complete_source_count": 2,
                "incomplete_source_count": 2,
                "top_gap_sources": ["string", "uniprot"],
            },
            "sources": [
                {
                    "source_id": "complex_portal",
                    "source_name": "Complex Portal",
                    "category": "complexes",
                    "status": "complete",
                    "priority_rank": 4,
                    "coverage_percent": 100.0,
                    "missing_file_count": 0,
                    "partial_file_count": 0,
                    "missing_files": [],
                    "partial_files": [],
                    "representative_missing_files": [],
                    "representative_partial_files": [],
                },
                {
                    "source_id": "reactome",
                    "source_name": "Reactome",
                    "category": "pathways_reactions_complexes",
                    "status": "complete",
                    "priority_rank": 4,
                    "coverage_percent": 100.0,
                    "missing_file_count": 0,
                    "partial_file_count": 0,
                    "missing_files": [],
                    "partial_files": [],
                    "representative_missing_files": [],
                    "representative_partial_files": [],
                },
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
                    "representative_missing_files": [
                        "protein.links.detailed.v12.0.txt.gz",
                        "protein.links.full.v12.0.txt.gz",
                    ],
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
                        "uniprot_sprot_varsplic.fasta.gz",
                        "idmapping_selected.tab.gz",
                    ],
                    "partial_files": ["uniprot_trembl.dat.gz"],
                    "representative_missing_files": [
                        "uniprot_trembl.xml.gz",
                        "uniprot_sprot_varsplic.fasta.gz",
                    ],
                    "representative_partial_files": ["uniprot_trembl.dat.gz"],
                },
            ],
        },
    )


def test_build_remaining_broad_mirror_gaps_filters_complete_sources(
    tmp_path: Path,
) -> None:
    progress_path = tmp_path / "artifacts" / "status" / "broad_mirror_progress.json"
    _write_progress(progress_path)

    payload = build_remaining_broad_mirror_gaps(broad_mirror_progress_path=progress_path)

    assert payload["summary"]["source_count"] == 4
    assert payload["summary"]["remaining_source_count"] == 2
    assert payload["summary"]["excluded_complete_source_count"] == 2
    assert payload["summary"]["total_missing_files"] == 20
    assert payload["summary"]["total_partial_files"] == 2
    assert payload["summary"]["total_gap_files"] == 22
    assert payload["summary"]["top_gap_sources"] == ["string", "uniprot"]
    assert [row["source_id"] for row in payload["remaining_sources"]] == [
        "string",
        "uniprot",
    ]
    assert payload["remaining_sources"][0]["gap_file_count"] == 12
    assert payload["remaining_sources"][1]["gap_file_count"] == 10
    assert payload["gap_files"][0]["source_id"] == "string"
    assert payload["gap_files"][0]["gap_kind"] == "missing"
    assert payload["gap_files"][-1]["source_id"] == "uniprot"
    assert payload["gap_files"][-1]["gap_kind"] == "partial"

    markdown = render_markdown(payload)
    assert "# Remaining Broad Mirror Gaps" in markdown
    assert "UniProt / UniRef / ID Mapping" in markdown
    assert "STRING v12" in markdown
    assert "Complex Portal" not in markdown


def test_main_writes_remaining_gap_outputs(tmp_path: Path) -> None:
    progress_path = tmp_path / "artifacts" / "status" / "broad_mirror_progress.json"
    output_path = tmp_path / "artifacts" / "status" / "broad_mirror_remaining_gaps.json"
    markdown_path = tmp_path / "docs" / "reports" / "broad_mirror_remaining_gaps.md"
    _write_progress(progress_path)

    exit_code = subprocess.run(
        [
            sys.executable,
            str(
                Path(__file__).resolve().parents[2]
                / "scripts"
                / "emit_broad_mirror_remaining_gaps.py"
            ),
            "--broad-mirror-progress",
            str(progress_path),
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

    assert "Remaining broad mirror gaps exported:" in exit_code.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["remaining_source_count"] == 2
    assert markdown_path.read_text(encoding="utf-8").startswith("# Remaining Broad Mirror Gaps")

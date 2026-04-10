from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.emit_broad_mirror_progress import (
    build_broad_mirror_progress,
    render_markdown,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_manifest(path: Path) -> None:
    _write_json(
        path,
        {
            "sources": [
                {
                    "id": "prosite",
                    "name": "PROSITE",
                    "category": "motif",
                    "top_level_files": [
                        {"filename": "prosite.dat"},
                        {"filename": "prosite.doc"},
                    ],
                },
                {
                    "id": "reactome",
                    "name": "Reactome",
                    "category": "pathways_reactions_complexes",
                    "notes": (
                        "ReactionPMIDS.txt and ComplexParticipantsPubMedIdentifiers_human.txt "
                        "are the current Reactome filenames; reactome.graphdb.tgz remains a live "
                        "current-release file but the last sync failed before it landed."
                    ),
                    "top_level_files": [
                        {"filename": "UniProt2Reactome.txt"},
                        {"filename": "UniProt2Reactome_All_Levels.txt"},
                        {"filename": "ReactomePathways.txt"},
                    ],
                },
                {
                    "id": "string",
                    "name": "STRING",
                    "category": "interaction_networks",
                    "top_level_files": [
                        {"filename": "protein.links.v12.0.txt.gz"},
                        {"filename": "protein.info.v12.0.txt.gz"},
                    ],
                },
                {
                    "id": "complex_portal",
                    "name": "Complex Portal",
                    "category": "complexes",
                    "top_level_files": [
                        {"filename": "released_complexes.txt"},
                        {"filename": "complextab/9606.tsv"},
                        {"filename": "complextab/9606_predicted.tsv"},
                    ],
                },
            ]
        },
    )


def _write_sabio_manifest(path: Path) -> None:
    _write_json(
        path,
        {
            "sources": [
                {
                    "id": "sabio_rk",
                    "name": "SABIO-RK",
                    "category": "enzyme_kinetics",
                    "manual_review_required": True,
                    "notes": (
                        "SABIO-RK is query-scoped; the broad procurement mirror "
                        "keeps exactly the stable REST vocabulary and UniProt "
                        "accession suggestion list."
                    ),
                    "top_level_files": [
                        {"filename": "sabio_search_fields.xml"},
                        {"filename": "sabio_uniprotkb_acs.txt"},
                    ],
                }
            ]
        },
    )


def test_build_broad_mirror_progress_counts_present_partial_and_missing_files(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "protein_data_scope" / "sources_manifest.json"
    seed_root = tmp_path / "data" / "raw" / "protein_data_scope_seed"
    _write_manifest(manifest_path)

    prosite_dir = seed_root / "prosite"
    prosite_dir.mkdir(parents=True, exist_ok=True)
    _write_text(prosite_dir / "prosite.dat", "ID TEST\n")
    _write_text(prosite_dir / "prosite.doc", "DOC TEST\n")

    reactome_dir = seed_root / "reactome"
    reactome_dir.mkdir(parents=True, exist_ok=True)
    _write_text(reactome_dir / "UniProt2Reactome.txt", "P12345\tR-HSA-1\n")
    _write_text(reactome_dir / "ReactomePathways.txt.part", "reactome-partial\n")

    string_dir = seed_root / "string"
    string_dir.mkdir(parents=True, exist_ok=True)
    _write_text(string_dir / "protein.links.v12.0.txt.gz.part", "string-partial\n")

    complex_portal_dir = seed_root / "complex_portal"
    complex_portal_dir.mkdir(parents=True, exist_ok=True)
    _write_text(complex_portal_dir / "released_complexes.txt", "released\n")
    complextab_dir = complex_portal_dir / "complextab"
    complextab_dir.mkdir(parents=True, exist_ok=True)
    _write_text(complextab_dir / "9606.tsv", "9606\tcomplex\n")
    _write_text(complextab_dir / "9606_predicted.tsv", "9606\tpredicted\n")

    payload = build_broad_mirror_progress(
        manifest_path=manifest_path,
        seed_root=seed_root,
        download_location_audit_path=None,
    )

    expected_reactome_part_bytes = (
        reactome_dir / "ReactomePathways.txt.part"
    ).stat().st_size
    expected_string_part_bytes = (
        string_dir / "protein.links.v12.0.txt.gz.part"
    ).stat().st_size
    source_map = {row["source_id"]: row for row in payload["sources"]}
    assert payload["summary"]["source_count"] == 4
    assert payload["summary"]["total_expected_files"] == 10
    assert payload["summary"]["total_present_files"] == 6
    assert payload["summary"]["total_partial_files"] == 2
    assert payload["summary"]["total_missing_files"] == 2
    assert payload["summary"]["total_active_part_files"] == 2
    assert payload["summary"]["total_active_part_bytes"] == (
        expected_reactome_part_bytes + expected_string_part_bytes
    )
    assert payload["summary"]["file_coverage_percent"] == 60.0
    assert source_map["prosite"]["status"] == "complete"
    assert source_map["prosite"]["coverage_percent"] == 100.0
    assert source_map["reactome"]["status"] == "partial"
    assert source_map["reactome"]["notes"] == [
        "ReactionPMIDS.txt and ComplexParticipantsPubMedIdentifiers_human.txt "
        "are the current Reactome filenames; reactome.graphdb.tgz remains a live "
        "current-release file but the last sync failed before it landed."
    ]
    assert source_map["reactome"]["present_files"] == ["UniProt2Reactome.txt"]
    assert source_map["reactome"]["partial_files"] == ["ReactomePathways.txt"]
    assert source_map["reactome"]["missing_files"] == ["UniProt2Reactome_All_Levels.txt"]
    assert source_map["reactome"]["active_part_file_count"] == 1
    assert source_map["reactome"]["active_part_bytes"] == expected_reactome_part_bytes
    assert source_map["string"]["status"] == "partial"
    assert source_map["string"]["priority_rank"] == 1
    assert source_map["string"]["active_part_file_count"] == 1
    assert source_map["string"]["active_part_bytes"] == expected_string_part_bytes
    assert source_map["complex_portal"]["status"] == "complete"
    assert source_map["complex_portal"]["coverage_percent"] == 100.0
    assert source_map["complex_portal"]["present_files"] == [
        "released_complexes.txt",
        "complextab/9606.tsv",
        "complextab/9606_predicted.tsv",
    ]
    assert source_map["complex_portal"]["missing_files"] == []
    assert payload["top_missing_files"][0]["source_id"] in {"reactome", "string"}


def test_build_broad_mirror_progress_keeps_sabio_query_lane_complete(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "protein_data_scope" / "sources_manifest.json"
    seed_root = tmp_path / "data" / "raw" / "protein_data_scope_seed"
    _write_sabio_manifest(manifest_path)

    sabio_dir = seed_root / "sabio_rk"
    sabio_dir.mkdir(parents=True, exist_ok=True)
    _write_text(sabio_dir / "sabio_search_fields.xml", "<search/>")
    _write_text(sabio_dir / "sabio_uniprotkb_acs.txt", "P31749\n")

    payload = build_broad_mirror_progress(
        manifest_path=manifest_path,
        seed_root=seed_root,
        download_location_audit_path=None,
    )

    sabio = payload["sources"][0]
    assert payload["summary"]["source_count"] == 1
    assert payload["summary"]["total_expected_files"] == 2
    assert payload["summary"]["total_missing_files"] == 0
    assert payload["summary"]["file_coverage_percent"] == 100.0
    assert sabio["status"] == "complete"
    assert sabio["present_files"] == [
        "sabio_search_fields.xml",
        "sabio_uniprotkb_acs.txt",
    ]
    assert sabio["missing_files"] == []
    assert sabio["notes"] == [
        (
            "SABIO-RK is query-scoped; the broad procurement mirror keeps "
            "exactly the stable REST vocabulary and UniProt accession "
            "suggestion list."
        )
    ]


def test_build_broad_mirror_progress_uses_download_location_audit_for_overflow_completion(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "protein_data_scope" / "sources_manifest.json"
    seed_root = tmp_path / "data" / "raw" / "protein_data_scope_seed"
    audit_path = tmp_path / "artifacts" / "status" / "download_location_audit_preview.json"
    _write_json(
        manifest_path,
        {
            "sources": [
                {
                    "id": "uniprot",
                    "name": "UniProt",
                    "category": "sequence_reference_backbone",
                    "top_level_files": [{"filename": "uniref100.xml.gz"}],
                }
            ]
        },
    )
    _write_json(
        audit_path,
        {
            "source_summaries": [
                {
                    "source_id": "uniprot",
                    "primary_root": str(seed_root / "uniprot").replace("\\", "/"),
                    "overflow_root": str(tmp_path / "overflow" / "uniprot").replace("\\", "/"),
                }
            ],
            "rows": [
                {
                    "source_id": "uniprot",
                    "filename": "uniref100.xml.gz",
                    "state": "downloaded",
                    "final_locations": [
                        {
                            "path": str(
                                tmp_path / "overflow" / "uniprot" / "uniref100.xml.gz"
                            ).replace("\\", "/"),
                            "size_bytes": 10,
                        }
                    ],
                    "in_process_locations": [],
                }
            ],
        },
    )

    payload = build_broad_mirror_progress(
        manifest_path=manifest_path,
        seed_root=seed_root,
        download_location_audit_path=audit_path,
    )

    row = payload["sources"][0]
    assert payload["summary"]["file_coverage_percent"] == 100.0
    assert row["status"] == "complete"
    assert row["authority"] == "download_location_audit_preview"
    assert "overflow root" in " ".join(row["notes"]).lower()


def test_render_markdown_surfaces_priority_sections_and_missing_files() -> None:
    markdown = render_markdown(
        {
            "generated_at": "2026-03-30T16:00:00+00:00",
            "inputs": {
                "manifest_path": "protein_data_scope/sources_manifest.json",
                "seed_root": "data/raw/protein_data_scope_seed",
            },
            "summary": {
                "source_count": 2,
                "total_present_files": 1,
                "total_expected_files": 3,
                "file_coverage_percent": 33.3,
                "complete_source_count": 0,
                "incomplete_source_count": 2,
                "total_missing_files": 2,
                "total_partial_files": 0,
                "total_active_part_files": 0,
                "total_active_part_bytes": 0,
            },
            "sources": [
                {
                    "source_id": "reactome",
                    "status": "partial",
                    "estimated_value": "high",
                    "coverage_percent": 50.0,
                    "missing_file_count": 1,
                    "partial_file_count": 0,
                    "priority_rank": 1,
                    "priority_label": "P1 high-value gap",
                    "notes": [
                        (
                            "ReactionPMIDS.txt and "
                            "ComplexParticipantsPubMedIdentifiers_human.txt "
                            "are current Reactome filenames."
                        )
                    ],
                    "representative_missing_files": ["ReactomePathways.txt"],
                    "missing_files": ["ReactomePathways.txt"],
                },
                {
                    "source_id": "complex_portal",
                    "status": "missing",
                    "estimated_value": "medium",
                    "coverage_percent": 0.0,
                    "missing_file_count": 1,
                    "partial_file_count": 0,
                    "priority_rank": 2,
                    "priority_label": "P2 medium-value gap",
                    "representative_missing_files": ["download_landing_page.html"],
                    "missing_files": ["download_landing_page.html"],
                },
            ],
            "top_missing_files": [
                {
                    "source_id": "reactome",
                    "source_name": "Reactome",
                    "category": "pathways_reactions_complexes",
                    "priority_rank": 1,
                    "estimated_value": "high",
                    "filename": "ReactomePathways.txt",
                },
                {
                    "source_id": "complex_portal",
                    "source_name": "Complex Portal",
                    "category": "complexes",
                    "priority_rank": 2,
                    "estimated_value": "medium",
                    "filename": "download_landing_page.html",
                },
            ],
            "top_priority_missing_files": [
                {
                    "source_id": "reactome",
                    "source_name": "Reactome",
                    "category": "pathways_reactions_complexes",
                    "priority_rank": 1,
                    "estimated_value": "high",
                    "filename": "ReactomePathways.txt",
                },
            ],
        }
    )

    assert "# Broad Mirror Progress" in markdown
    assert "Priority Overview" in markdown
    assert "P1 high-value gap" in markdown
    assert "Active `.part` bytes" in markdown
    assert "Source Notes" in markdown
    assert "current Reactome filenames" in markdown
    assert "`reactome`" in markdown
    assert "`ReactomePathways.txt`" in markdown
    assert "Missing File Index" in markdown
    assert "`download_landing_page.html`" in markdown


def test_main_writes_json_and_markdown_outputs(tmp_path: Path) -> None:
    manifest_path = tmp_path / "protein_data_scope" / "sources_manifest.json"
    seed_root = tmp_path / "data" / "raw" / "protein_data_scope_seed"
    output_path = tmp_path / "artifacts" / "status" / "broad_mirror_progress.json"
    markdown_path = tmp_path / "docs" / "reports" / "broad_mirror_progress.md"
    _write_manifest(manifest_path)
    prosite_dir = seed_root / "prosite"
    prosite_dir.mkdir(parents=True, exist_ok=True)
    _write_text(prosite_dir / "prosite.dat", "ID TEST\n")
    _write_text(prosite_dir / "prosite.doc", "DOC TEST\n")

    exit_code = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[2] / "scripts" / "emit_broad_mirror_progress.py"),
            "--manifest",
            str(manifest_path),
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

    assert "Broad mirror progress exported:" in exit_code.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["source_count"] == 4
    assert markdown_path.read_text(encoding="utf-8").startswith("# Broad Mirror Progress")

from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_manifest(
    path: Path,
    *,
    source_name: str,
    status: str,
    join_keys: tuple[str, ...],
    missing_roots: int = 0,
) -> None:
    path.write_text(
        json.dumps(
            {
                "manifest_id": f"{source_name}:test",
                "source_name": source_name,
                "provenance": [status],
                "reproducibility_metadata": [
                    f"join_keys={','.join(join_keys)}",
                    f"missing_roots={missing_roots}",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_source_metadata(path: Path, filenames: list[str]) -> None:
    path.write_text(
        json.dumps(
            {
                "id": path.parent.name,
                "top_level_files": [
                    {"filename": filename, "url": f"https://example.org/{filename}"}
                    for filename in filenames
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_export_interaction_similarity_signature_preview(tmp_path: Path) -> None:
    biogrid_manifest = tmp_path / "biogrid_manifest.json"
    string_manifest = tmp_path / "string_manifest.json"
    intact_manifest = tmp_path / "intact_manifest.json"
    bundle_manifest = tmp_path / "bundle_manifest.json"
    biogrid_root = tmp_path / "biogrid"
    string_root = tmp_path / "string"
    intact_root = tmp_path / "intact"
    canonical_summary = tmp_path / "canonical_summary.json"
    biogrid_archive = biogrid_root / "BIOGRID-ALL-LATEST.mitab.zip"
    preview_json = tmp_path / "interaction_similarity_signature_preview.json"
    preview_md = tmp_path / "interaction_similarity_signature_preview.md"

    biogrid_root.mkdir()
    string_root.mkdir()
    intact_root.mkdir(parents=True, exist_ok=True)

    _write_manifest(
        biogrid_manifest,
        source_name="BioGRID",
        status="present",
        join_keys=("P69905", "P09105"),
    )
    _write_manifest(
        string_manifest,
        source_name="STRING",
        status="missing",
        join_keys=("P69905", "P09105"),
        missing_roots=3,
    )
    _write_manifest(
        intact_manifest,
        source_name="IntAct",
        status="present",
        join_keys=("P69905", "P09105"),
    )
    bundle_manifest.write_text(
        json.dumps(
            {
                "bundle_id": "proteosphere-lite",
                "bundle_status": "preview_generated_verified_assets",
                "record_counts": {"interaction_similarity_signatures": 0},
                "table_families": [
                    {
                        "family_name": "interaction_similarity_signatures",
                        "included": False,
                        "record_count": 0,
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_source_metadata(
        biogrid_root / "_source_metadata.json",
        ["BIOGRID-ALL-LATEST.mitab.zip"],
    )
    _write_source_metadata(
        string_root / "_source_metadata.json",
        [
            "protein.aliases.v12.0.txt.gz",
            "protein.links.detailed.v12.0.txt.gz",
            "protein.physical.links.detailed.v12.0.txt.gz",
        ],
    )
    (string_root / "protein.aliases.v12.0.txt.gz").write_text("alias", encoding="utf-8")
    (string_root / "protein.links.detailed.v12.0.txt.gz.part").write_text(
        "partial",
        encoding="utf-8",
    )
    intact_snapshot = intact_root / "20260323T154140Z"
    (intact_snapshot / "P69905").mkdir(parents=True, exist_ok=True)
    (intact_snapshot / "P09105").mkdir(parents=True, exist_ok=True)
    (intact_snapshot / "P69905" / "P69905.psicquic.tab25.txt").write_text(
        "\n".join(
            [
                "row1",
                "row2",
                "row3",
                "row4",
                "row5",
            ]
        ),
        encoding="utf-8",
    )
    (intact_snapshot / "P09105" / "P09105.psicquic.tab25.txt").write_text(
        "\n".join(
            [
                "row1",
                "row2",
                "row3",
                "row4",
                "row5",
            ]
        ),
        encoding="utf-8",
    )
    canonical_summary.write_text("{}", encoding="utf-8")
    with zipfile.ZipFile(biogrid_archive, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "BIOGRID-ALL-5.0.255.mitab.txt",
            "\n".join(
                [
                    "BioGRID Interaction ID\tBioGRID ID A\tBioGRID ID B",
                    "1\tuniprotkb:P69905\tuniprotkb:Q9Y6K9",
                    "2\tuniprotkb:P69905\tuniprotkb:Q92831",
                    "3\tuniprotkb:P09105\tuniprotkb:Q92831",
                ]
            ),
        )

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_interaction_similarity_signature_preview.py"),
            "--biogrid-manifest",
            str(biogrid_manifest),
            "--string-manifest",
            str(string_manifest),
            "--intact-manifest",
            str(intact_manifest),
            "--biogrid-archive",
            str(biogrid_archive),
            "--string-root",
            str(string_root),
            "--intact-raw-root",
            str(intact_root),
            "--canonical-summary",
            str(canonical_summary),
            "--bundle-manifest",
            str(bundle_manifest),
            "--output-json",
            str(preview_json),
            "--output-md",
            str(preview_md),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    payload = json.loads(preview_json.read_text(encoding="utf-8"))
    assert payload["status"] == "complete"
    assert payload["row_count"] == 2
    assert payload["summary"]["accession_count"] == 2
    assert payload["summary"]["unique_interaction_similarity_group_count"] == 1
    assert payload["summary"]["biogrid_matched_row_total"] == 3
    assert payload["summary"]["candidate_only_row_count"] == 2
    assert payload["summary"]["string_top_level_file_present_count"] == 1
    assert payload["summary"]["string_top_level_file_partial_count"] == 1
    assert payload["summary"]["string_top_level_file_missing_count"] == 1
    assert payload["source_surfaces"]["biogrid"]["manifest_state"] == "present"
    assert payload["source_surfaces"]["string"]["manifest_state"] == "missing"
    assert payload["source_surfaces"]["string"]["disk_state"] == "partial_on_disk"
    assert payload["source_surfaces"]["intact"]["probe_state"] == "present"
    assert payload["source_surfaces"]["intact"]["probe_row_total"] == 10
    assert payload["rows"][0]["candidate_only"] is True
    assert "Interaction Similarity Signature Preview" in preview_md.read_text(encoding="utf-8")

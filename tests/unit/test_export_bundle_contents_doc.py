from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_bundle_contents_doc(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    contract_path = tmp_path / "contract.json"
    manifest_path.write_text(
        json.dumps(
            {
                "bundle_id": "proteosphere-lite",
                "bundle_kind": "debug_bundle",
                "bundle_version": "0.1.0-preview",
                "release_id": "rel-1",
                "packaging_layout": "compressed_sqlite",
                "manifest_status": "example_only_not_built",
                "validation_status": "warning",
                "artifact_files": [
                    {
                        "filename": "proteosphere-lite.sqlite.zst",
                        "role": "core_bundle",
                        "size_bytes": 100,
                        "required": True,
                    }
                ],
                "table_families": [
                    {"family_name": "proteins", "included": True, "record_count": 11},
                    {
                        "family_name": "protein_variants",
                        "included": True,
                        "record_count": 1874,
                    },
                ],
                "source_coverage_summary": {
                    "source_count": 10,
                    "present_source_count": 9,
                    "partial_source_count": 1,
                    "missing_source_count": 0,
                    "procurement_priority_sources": ["elm"],
                },
                "exclusions": ["raw_mmcif"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    contract_path.write_text(
        json.dumps(
            {
                "bundle_contents_doc": {
                    "wording_constraints": [
                        "record counts are current counts, not completeness claims",
                        "protein_variants is declared for schema v2 but not yet populated",
                    ]
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "contents.md"
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_bundle_contents_doc.py"),
            "--manifest",
            str(manifest_path),
            "--contract",
            str(contract_path),
            "--output",
            str(output_path),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    content = output_path.read_text(encoding="utf-8")
    assert "ProteoSphere Lite Bundle Contents" in content
    assert "`proteins`: `11` records" in content
    assert "`protein_variants`: `1874` records" in content
    assert "protein_variants is declared for schema v2 but not yet populated" not in content

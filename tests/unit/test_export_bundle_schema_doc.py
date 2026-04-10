from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_bundle_schema_doc(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    outline_path = tmp_path / "outline.json"
    manifest_path.write_text(
        json.dumps(
            {
                "bundle_id": "proteosphere-lite",
                "bundle_kind": "debug_bundle",
                "schema_version": 1,
                "packaging_layout": "compressed_sqlite",
                "content_scope": "planning_governance_only",
                "manifest_status": "example_only_not_built",
                "artifact_files": [
                    {
                        "filename": "proteosphere-lite.sqlite.zst",
                        "role": "core_bundle",
                        "required": True,
                    }
                ],
                "table_families": [
                    {"family_name": "proteins", "included": True, "record_count": 11},
                    {"family_name": "protein_variants", "included": False, "record_count": 0},
                ],
                "source_snapshot_ids": [{"source_name": "UniProt", "snapshot_id": "2026-03-23"}],
                "exclusions": ["raw_mmcif"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    outline_path.write_text(
        json.dumps(
            {
                "basis": {
                    "budget_contract": "docs/reports/p51_bundle_manifest_budget_contract.md"
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "schema.md"
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_bundle_schema_doc.py"),
            "--manifest",
            str(manifest_path),
            "--outline",
            str(outline_path),
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
    assert "ProteoSphere Lite Bundle Schema" in content
    assert "`proteins`: `included`, `11` records" in content
    assert "`protein_variants`" in content
    assert "Source Lineage And Trust Notes" in content

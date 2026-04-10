from __future__ import annotations

import json
from pathlib import Path

from scripts.export_procurement_status_board import build_procurement_status_board

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_rnacentral_manifest_replaces_pg_dump_with_public_database_path() -> None:
    manifest = json.loads(
        (REPO_ROOT / "protein_data_scope" / "sources_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    rnacentral = next(
        source for source in manifest["sources"] if source.get("id") == "rnacentral"
    )

    assert rnacentral["manual_review_required"] is True
    assert "public Postgres database" in rnacentral["notes"]
    assert "https://rnacentral.org/help/public-database" in rnacentral["notes"]
    assert all(
        item["filename"] != "pg_dump.sql.gz"
        for item in rnacentral.get("top_level_files", [])
        if isinstance(item, dict)
    )


def test_procurement_board_no_longer_emits_rnacentral_pg_dump(tmp_path: Path) -> None:
    supervisor_state_path = (
        tmp_path / "artifacts" / "runtime" / "procurement_supervisor_state.json"
    )
    _write_json(
        supervisor_state_path,
        {
            "generated_at": "2026-03-30T23:59:00+00:00",
            "status": "idle",
            "active": [],
            "observed_active": [],
            "completed": [],
            "pending": [],
            "failed": [],
        },
    )

    payload = build_procurement_status_board(
        broad_mirror_progress_path=REPO_ROOT
        / "artifacts"
        / "status"
        / "broad_mirror_progress.json",
        supervisor_state_path=supervisor_state_path,
        local_registry_summary_path=REPO_ROOT
        / "artifacts"
        / "status"
        / "source_coverage_matrix.json",
        process_probe=lambda: ([], "unavailable"),
    )

    assert not any(
        row.get("source_id") == "rnacentral"
        for row in payload["broad_mirror"]["top_gap_sources"]
    )
    assert not any(
        row.get("filename") == "pg_dump.sql.gz"
        for row in payload["broad_mirror"]["top_missing_files"]
    )
    assert not any(
        row.get("source_id") == "rnacentral" for row in payload["top_remaining_gaps"]
    )


def test_catalog_summary_uses_public_database_language_for_rnacentral() -> None:
    summary = (REPO_ROOT / "protein_data_scope" / "catalog_summary.md").read_text(
        encoding="utf-8"
    )

    assert "public Postgres database access" in summary
    assert "Postgres dump" not in summary

from __future__ import annotations

import json
from pathlib import Path

from scripts.export_packet_state_comparison import (
    build_packet_state_comparison,
    render_markdown,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_packet_state_comparison_reports_improvement(tmp_path: Path) -> None:
    latest_path = tmp_path / "LATEST.json"
    freshest_path = tmp_path / "selected_cohort_materialization.json"
    _write_json(
        latest_path,
        {
            "complete_count": 1,
            "partial_count": 1,
            "unresolved_count": 0,
            "latest_promotion_state": "held",
            "packets": [
                {
                    "accession": "Q9NZD4",
                    "status": "partial",
                    "missing_modalities": ["ligand", "ppi"],
                    "manifest_path": "latest/q9nzd4.json",
                },
                {
                    "accession": "Q9UCM0",
                    "status": "partial",
                    "missing_modalities": ["ligand", "ppi", "structure"],
                    "manifest_path": "latest/q9ucm0.json",
                },
            ],
        },
    )
    _write_json(
        freshest_path,
        {
            "complete_count": 1,
            "partial_count": 1,
            "unresolved_count": 0,
            "latest_promotion_state": "held",
            "packets": [
                {
                    "accession": "Q9NZD4",
                    "status": "partial",
                    "missing_modalities": ["ppi"],
                    "manifest_path": "fresh/q9nzd4.json",
                },
                {
                    "accession": "Q9UCM0",
                    "status": "partial",
                    "missing_modalities": ["ligand", "ppi", "structure"],
                    "manifest_path": "fresh/q9ucm0.json",
                },
            ],
        },
    )

    payload = build_packet_state_comparison(
        latest_path=latest_path,
        freshest_path=freshest_path,
    )

    assert payload["summary"]["packet_count"] == 2
    assert payload["summary"]["changed_packet_count"] == 1
    assert payload["summary"]["improved_packet_count"] == 1
    assert payload["summary"]["regressed_packet_count"] == 0
    assert payload["summary"]["improved_accessions"] == ["Q9NZD4"]
    assert payload["comparison_boundary"]["latest_label"] == "preserved packet baseline"
    assert payload["comparison_boundary"]["freshest_label"] == "freshest run-scoped packet state"
    row = next(row for row in payload["packets"] if row["accession"] == "Q9NZD4")
    assert row["improvement"] is True
    assert row["freshest_missing_modalities"] == ["ppi"]

    markdown = render_markdown(payload)
    assert "Comparison boundary" in markdown
    assert "preserved packet baseline" in markdown
    assert "freshest run-scoped packet state" in markdown


def test_build_packet_state_comparison_accepts_freshest_directory(tmp_path: Path) -> None:
    latest_path = tmp_path / "LATEST.json"
    freshest_dir = tmp_path / "training-packets-20260331T193611Z"
    manifest_dir = freshest_dir / "packet-q9nzd4"
    manifest_dir.mkdir(parents=True)
    _write_json(
        latest_path,
        {
            "complete_count": 0,
            "partial_count": 1,
            "unresolved_count": 0,
            "latest_promotion_state": "held",
            "packets": [
                {
                    "accession": "Q9NZD4",
                    "status": "partial",
                    "missing_modalities": ["ligand"],
                }
            ],
        },
    )
    _write_json(
        manifest_dir / "packet_manifest.json",
        {
            "accession": "Q9NZD4",
            "status": "complete",
            "missing_modalities": [],
            "manifest_path": str(manifest_dir / "packet_manifest.json"),
        },
    )

    payload = build_packet_state_comparison(
        latest_path=latest_path,
        freshest_path=freshest_dir,
    )

    assert payload["freshest_summary"]["packet_count"] == 1
    assert payload["freshest_summary"]["complete_count"] == 1
    assert payload["summary"]["improved_packet_count"] == 1

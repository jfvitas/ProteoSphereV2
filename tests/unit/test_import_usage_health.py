from __future__ import annotations

import json
from pathlib import Path

from scripts.import_usage_health import build_usage_health_import_report, main


def test_build_usage_health_import_report_marks_absent_when_no_inputs() -> None:
    report = build_usage_health_import_report([])

    assert report["status"] == "absent"
    assert report["summary"]["source_count"] == 0
    assert report["summary"]["present_source_count"] == 0
    assert report["summary"]["missing_source_count"] == 0
    assert report["privacy_boundary"]["privacy_safe"] is True
    assert report["verdict"] == "audit_only"


def test_build_usage_health_import_report_marks_partial_when_aggregate_signals_missing(
    tmp_path: Path,
) -> None:
    partial_source = tmp_path / "usage_health_partial.json"
    partial_source.write_text(
        json.dumps(
            {
                "source_name": "local_monitor",
                "window_start": "2026-04-03T20:00:00Z",
                "window_end": "2026-04-03T21:00:00Z",
                "active_users": 12,
                "sessions": 8,
                "privacy_safe": True,
                "user_ids": ["u1", "u2"],
            }
        ),
        encoding="utf-8",
    )

    report = build_usage_health_import_report([partial_source])

    assert report["status"] == "partial"
    assert report["summary"]["source_count"] == 1
    assert report["summary"]["present_source_count"] == 1
    assert report["summary"]["partial_signal_count"] == 1
    assert report["summary"]["absent_signal_count"] == 0
    assert report["privacy_boundary"]["privacy_safe"] is True
    assert report["sources"][0]["counts"] == {"active_users": 12, "sessions": 8}
    assert "identifier_fields_ignored" in report["sources"][0]["notes"]
    assert "raw_user_ids" in report["truth_boundary"]["forbidden_signals"]


def test_main_writes_report_and_preserves_privacy_boundary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "usage_health_complete.json"
    output = tmp_path / "report.json"
    source.write_text(
        json.dumps(
            {
                "source_name": "release_monitor",
                "window_start": "2026-04-03T20:00:00Z",
                "window_end": "2026-04-03T21:00:00Z",
                "active_users": 3,
                "sessions": 4,
                "events": 11,
                "page_views": 9,
                "errors": 0,
                "privacy_safe": True,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "import_usage_health.py",
            "--input",
            str(source),
            "--output",
            str(output),
        ],
    )
    main()

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "complete"
    assert report["summary"]["complete_signal_count"] == 1
    assert report["privacy_boundary"]["privacy_safe"] is True

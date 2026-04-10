from __future__ import annotations

from pathlib import Path

from scripts.export_download_location_audit_preview import (
    build_download_location_audit_preview,
)


def test_download_location_audit_tracks_downloaded_and_in_process_files(
    tmp_path: Path,
) -> None:
    manifest = {
        "sources": [
            {
                "id": "alpha",
                "name": "Alpha",
                "category": "cat_a",
                "top_level_files": [
                    {"filename": "a.txt", "url": "https://example.test/a.txt"},
                ],
            },
            {
                "id": "beta",
                "name": "Beta",
                "category": "cat_b",
                "top_level_files": [
                    {"filename": "b.txt", "url": "https://example.test/b.txt"},
                ],
            },
        ]
    }
    primary_root = tmp_path / "primary"
    overflow_root = tmp_path / "overflow"
    failed_root = tmp_path / "failed"

    (primary_root / "alpha").mkdir(parents=True)
    (primary_root / "alpha" / "a.txt").write_text("done", encoding="utf-8")

    (overflow_root / "beta").mkdir(parents=True)
    (overflow_root / "beta" / "b.txt.part").write_text("partial", encoding="utf-8")

    payload = build_download_location_audit_preview(
        manifest,
        primary_seed_root=primary_root,
        overflow_seed_root=overflow_root,
        failed_snapshot_root=failed_root,
    )

    assert payload["summary"]["wanted_file_count"] == 2
    assert payload["summary"]["downloaded_count"] == 1
    assert payload["summary"]["in_process_count"] == 1
    assert payload["summary"]["missing_count"] == 0
    assert payload["summary"]["all_wanted_files_accounted_for"] is True

    rows_by_filename = {row["filename"]: row for row in payload["rows"]}
    assert rows_by_filename["a.txt"]["state"] == "downloaded"
    assert rows_by_filename["a.txt"]["primary_location"].endswith("/primary/alpha/a.txt")
    assert rows_by_filename["b.txt"]["state"] == "in_process"
    assert rows_by_filename["b.txt"]["primary_location"].endswith(
        "/overflow/beta/b.txt.part"
    )

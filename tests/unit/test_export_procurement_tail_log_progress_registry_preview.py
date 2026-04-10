from __future__ import annotations

from pathlib import Path

from scripts.export_procurement_tail_log_progress_registry_preview import (
    _match_progress_line,
    build_procurement_tail_log_progress_registry_preview,
)


def test_match_progress_line_parses_total_and_speed() -> None:
    match = _match_progress_line(
        ["  uniref100.xml.gz:   7.31%  11.1 GB/151.8 GB  3.1 MB/s"],
        "uniref100.xml.gz",
    )

    assert match is not None
    assert match["percent_complete"] == 7.31
    assert match["total_bytes_from_log"] > match["current_bytes_from_log"]
    assert match["speed_bytes_per_second_from_log"] > 0


def test_log_progress_registry_preview_parses_matching_log(tmp_path: Path) -> None:
    log_path = tmp_path / "uniprot.log"
    log_path.write_text(
        "Downloading https://example.test/uniref100.xml.gz\n"
        "  uniref100.xml.gz:   7.31%  11.1 GB/151.8 GB  3.1 MB/s\n",
        encoding="utf-8",
    )

    payload = build_procurement_tail_log_progress_registry_preview(
        {
            "actively_transferring_now": [
                {
                    "source_id": "uniprot",
                    "source_name": "UniProt / UniRef / ID Mapping",
                    "filename": "uniref100.xml.gz",
                    "evidence": [
                        {"kind": "stdout_log_tail", "log": str(log_path)}
                    ],
                }
            ]
        }
    )

    assert payload["summary"]["registry_state"] == "fully_parsed"
    assert payload["summary"]["parsed_row_count"] == 1
    assert payload["rows"][0]["match_state"] == "progress_line_parsed"

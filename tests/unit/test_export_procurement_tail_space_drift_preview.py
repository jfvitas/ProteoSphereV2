from __future__ import annotations

from collections import namedtuple
from pathlib import Path

from scripts.export_procurement_tail_space_drift_preview import (
    build_procurement_tail_space_drift_preview,
)

DiskUsage = namedtuple("DiskUsage", ["total", "used", "free"])


def test_tail_space_drift_preview_reports_aligned_growth(tmp_path: Path) -> None:
    file_path = tmp_path / "uniprot" / "uniref100.xml.gz.part"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"x" * 10)

    observed_sizes = iter((10, 30))
    observed_usage = iter(
        (
            DiskUsage(total=1000, used=900, free=100),
            DiskUsage(total=1000, used=920, free=80),
        )
    )

    payload = build_procurement_tail_space_drift_preview(
        board={
            "procurement_supervisor": {
                "active_observed_downloads": [
                    {
                        "task_id": "uniprot",
                        "filename": "uniref100.xml.gz",
                        "source_name": "UniProt / UniRef / ID Mapping",
                    }
                ]
            }
        },
        broad_progress={
            "sources": [{"source_id": "uniprot", "source_root": str(file_path.parent)}]
        },
        sample_window_seconds=5,
        sleep_fn=lambda _: None,
        size_reader=lambda _: next(observed_sizes),
        disk_usage_reader=lambda _: next(observed_usage),
    )

    assert payload["summary"]["drift_state"] == "aligned_with_tail_growth"
    assert payload["summary"]["free_delta_bytes"] == -20
    assert payload["summary"]["total_tail_delta_bytes"] == 20
    assert payload["summary"]["net_space_gap_bytes"] == 0


def test_tail_space_drift_preview_reports_released_space(tmp_path: Path) -> None:
    file_path = tmp_path / "string" / "protein.links.full.v12.0.txt.gz.part"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"x" * 10)

    observed_sizes = iter((0, 2 * 1024 * 1024))
    observed_usage = iter(
        (
            DiskUsage(total=20 * 1024 * 1024, used=15 * 1024 * 1024, free=5 * 1024 * 1024),
            DiskUsage(total=20 * 1024 * 1024, used=10 * 1024 * 1024, free=10 * 1024 * 1024),
        )
    )

    payload = build_procurement_tail_space_drift_preview(
        board={
            "procurement_supervisor": {
                "active_observed_downloads": [
                    {
                        "task_id": "string",
                        "filename": "protein.links.full.v12.0.txt.gz",
                        "source_name": "STRING v12",
                    }
                ]
            }
        },
        broad_progress={
            "sources": [{"source_id": "string", "source_root": str(file_path.parent)}]
        },
        sample_window_seconds=5,
        sleep_fn=lambda _: None,
        size_reader=lambda _: next(observed_sizes),
        disk_usage_reader=lambda _: next(observed_usage),
    )

    assert payload["summary"]["drift_state"] == "free_space_released_during_tail_growth"
    assert payload["summary"]["free_delta_bytes"] == 5 * 1024 * 1024
    assert payload["summary"]["total_tail_delta_bytes"] == 2 * 1024 * 1024

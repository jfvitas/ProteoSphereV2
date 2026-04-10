from __future__ import annotations

from pathlib import Path

from scripts.export_procurement_tail_growth_preview import (
    build_procurement_tail_growth_preview,
)


def test_tail_growth_preview_reports_active_growth(tmp_path: Path) -> None:
    file_path = tmp_path / "uniprot" / "uniref100.xml.gz.part"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"x" * 10)

    observed_sizes = iter((10, 30))

    payload = build_procurement_tail_growth_preview(
        board={
            "procurement_supervisor": {
                "active_observed_downloads": [
                    {
                        "task_id": "uniprot",
                        "filename": "uniref100.xml.gz",
                        "source_name": "UniProt / UniRef / ID Mapping",
                        "category": "sequence_reference_backbone",
                    }
                ]
            }
        },
        broad_progress={
            "sources": [
                {
                    "source_id": "uniprot",
                    "source_root": str(file_path.parent),
                }
            ]
        },
        sample_window_seconds=5,
        sleep_fn=lambda _: None,
        size_reader=lambda _: next(observed_sizes),
    )

    assert payload["summary"]["growth_state"] == "active_growth"
    assert payload["summary"]["positive_growth_file_count"] == 1
    assert payload["summary"]["total_delta_bytes"] == 20
    assert payload["rows"][0]["growth_state"] == "growing"


def test_tail_growth_preview_reports_missing_partial_artifact() -> None:
    payload = build_procurement_tail_growth_preview(
        board={
            "procurement_supervisor": {
                "active_observed_downloads": [
                    {
                        "task_id": "string",
                        "filename": "protein.links.full.v12.0.txt.gz",
                        "source_name": "STRING v12",
                        "category": "interaction_networks",
                    }
                ]
            }
        },
        broad_progress={"sources": [{"source_id": "string", "source_root": "missing_root"}]},
        sample_window_seconds=0,
        sleep_fn=lambda _: None,
    )

    assert payload["summary"]["sampled_tail_file_count"] == 0
    assert payload["summary"]["growth_state"] == "no_tail_files_sampled"
    assert payload["rows"][0]["growth_state"] == "missing_partial_artifact"

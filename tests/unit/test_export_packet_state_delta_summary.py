from __future__ import annotations

import json
from pathlib import Path

from scripts.export_packet_state_summary import (
    build_packet_state_delta_summary,
    main,
    render_markdown,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_inputs(tmp_path: Path) -> dict[str, Path]:
    delta_report_path = tmp_path / "artifacts" / "status" / "packet_state_delta_report.json"
    packet_deficit_path = tmp_path / "artifacts" / "status" / "packet_deficit_dashboard.json"

    _write_json(
        delta_report_path,
        {
            "comparison_boundary": {
                "latest_label": "preserved packet baseline",
                "latest_path": "D:/baseline",
                "freshest_label": "freshest run-scoped packet state",
                "freshest_path": "D:/freshest",
            },
            "summary": {
                "remaining_gap_packet_count": 3,
            },
            "remaining_gaps": [
                {
                    "accession": "Q9NZD4",
                    "packet_level_truth": "fresh-run-regressed",
                    "latest_gap_count": 1,
                    "freshest_gap_count": 2,
                    "latest_missing_modalities": ["ligand"],
                    "freshest_missing_modalities": ["ppi", "structure"],
                    "latest_deficit_source_refs": ["ligand:Q9NZD4"],
                },
                {
                    "accession": "P00387",
                    "packet_level_truth": "fresh-run-regressed",
                    "latest_gap_count": 1,
                    "freshest_gap_count": 3,
                    "latest_missing_modalities": ["ligand"],
                    "freshest_missing_modalities": ["ligand", "ppi", "structure"],
                    "latest_deficit_source_refs": ["ligand:P00387"],
                },
                {
                    "accession": "P02042",
                    "packet_level_truth": "fresh-run-regressed",
                    "latest_gap_count": 0,
                    "freshest_gap_count": 2,
                    "latest_missing_modalities": [],
                    "freshest_missing_modalities": ["ppi", "structure"],
                    "latest_deficit_source_refs": [],
                },
            ],
        },
    )
    _write_json(
        packet_deficit_path,
        {
            "summary": {
                "packet_deficit_count": 2,
                "highest_leverage_source_fixes": [
                    {"source_ref": "ligand:Q9NZD4"},
                    {"source_ref": "ligand:P00387"},
                ],
            }
        },
    )
    return {
        "delta_report_path": delta_report_path,
        "packet_deficit_path": packet_deficit_path,
    }


def test_build_packet_state_delta_summary_splits_operator_actions(
    tmp_path: Path,
) -> None:
    paths = _write_inputs(tmp_path)

    payload = build_packet_state_delta_summary(
        delta_report_path=paths["delta_report_path"],
        packet_deficit_path=paths["packet_deficit_path"],
    )

    assert payload["summary"]["latest_baseline_blocker_count"] == 2
    assert payload["summary"]["fresh_run_not_promotable_count"] == 1
    assert payload["summary"]["actionable_packet_count"] == 3
    assert payload["summary"]["blocker_accessions"] == ["P00387", "Q9NZD4"]
    assert payload["summary"]["not_promotable_accessions"] == ["P02042"]

    blocker_rows = {row["accession"]: row for row in payload["latest_baseline_blockers"]}
    assert blocker_rows["Q9NZD4"]["classification"] == "latest-baseline-blocker"
    assert "ligand:Q9NZD4" in blocker_rows["Q9NZD4"]["recommended_action"]
    assert blocker_rows["P00387"]["recommended_action"].startswith(
        "Resolve the preserved-baseline blocker"
    )

    not_promotable = payload["fresh_run_not_promotable"][0]
    assert not_promotable["accession"] == "P02042"
    assert not_promotable["classification"] == "fresh-run-not-promotable"
    assert not_promotable["recommended_action"] == (
        "Repair the fresh-run regression in ppi, structure before any promotion attempt."
    )

    markdown = render_markdown(payload)
    assert "Still Latest-Baseline Blockers" in markdown
    assert "Fresh-Run Evidence Not Promotable" in markdown
    assert "Q9NZD4" in markdown
    assert "P00387" in markdown
    assert "P02042" in markdown


def test_main_writes_packet_state_delta_summary_outputs(tmp_path: Path, capsys) -> None:
    paths = _write_inputs(tmp_path)
    output_path = tmp_path / "artifacts" / "status" / "packet_state_delta_summary.json"

    exit_code = main(
        [
            "--delta-report",
            str(paths["delta_report_path"]),
            "--packet-deficit",
            str(paths["packet_deficit_path"]),
            "--output",
            str(output_path),
            "--no-markdown",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert "Packet delta summary exported" in captured.out
    assert payload["summary"]["latest_baseline_blocker_count"] == 2
    assert payload["summary"]["fresh_run_not_promotable_count"] == 1

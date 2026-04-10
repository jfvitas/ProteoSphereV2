from __future__ import annotations

import json
from pathlib import Path

from scripts.export_packet_operator_blocker_surface import (
    build_packet_operator_blocker_surface,
    main,
    render_markdown,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_inputs(tmp_path: Path) -> dict[str, Path]:
    delta_report_path = tmp_path / "artifacts" / "status" / "packet_state_delta_report.json"
    delta_summary_path = tmp_path / "artifacts" / "status" / "packet_state_delta_summary.json"
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
                "latest_gap_packet_count": 2,
                "freshest_gap_packet_count": 4,
            },
        },
    )
    _write_json(
        delta_summary_path,
        {
            "comparison_boundary": {
                "latest_label": "preserved packet baseline",
                "latest_path": "D:/baseline",
                "freshest_label": "freshest run-scoped packet state",
                "freshest_path": "D:/freshest",
            },
            "summary": {
                "latest_preserved_gap_packet_count": 2,
                "freshest_remaining_gap_packet_count": 4,
            },
            "latest_baseline_blockers": [
                {
                    "accession": "Q9NZD4",
                    "packet_level_truth": "fresh-run-regressed",
                    "evidence_level_truth": "fresh-run-evidence-regressed",
                    "latest_gap_count": 1,
                    "freshest_gap_count": 2,
                    "latest_missing_modalities": ["ligand"],
                    "freshest_missing_modalities": ["ppi", "structure"],
                    "latest_deficit_source_refs": ["ligand:Q9NZD4"],
                },
                {
                    "accession": "P00387",
                    "packet_level_truth": "fresh-run-regressed",
                    "evidence_level_truth": "fresh-run-evidence-regressed",
                    "latest_gap_count": 1,
                    "freshest_gap_count": 3,
                    "latest_missing_modalities": ["ligand"],
                    "freshest_missing_modalities": ["ligand", "ppi", "structure"],
                    "latest_deficit_source_refs": ["ligand:P00387"],
                },
            ],
            "fresh_run_not_promotable": [
                {
                    "accession": "P02042",
                    "packet_level_truth": "fresh-run-regressed",
                    "evidence_level_truth": "fresh-run-evidence-regressed",
                    "latest_gap_count": 0,
                    "freshest_gap_count": 2,
                    "latest_missing_modalities": [],
                    "freshest_missing_modalities": ["ppi", "structure"],
                    "recommended_action": "Repair the fresh-run regression in ppi, structure before any promotion attempt.",
                },
            ],
        },
    )
    _write_json(
        packet_deficit_path,
        {
            "summary": {
                "packet_deficit_count": 2,
            },
            "modality_deficits": [
                {
                    "modality": "ligand",
                    "missing_packet_count": 2,
                    "source_name": "Ligand sources",
                    "top_source_fix_candidates": [
                        {
                            "source_ref": "ligand:Q9NZD4",
                            "priority_rank": 1,
                            "affected_packet_count": 1,
                            "missing_modality_count": 1,
                            "missing_modalities": ["ligand"],
                            "packet_accessions": ["Q9NZD4"],
                            "packet_ids": ["packet-Q9NZD4"],
                        },
                        {
                            "source_ref": "ligand:P00387",
                            "priority_rank": 2,
                            "affected_packet_count": 1,
                            "missing_modality_count": 1,
                            "missing_modalities": ["ligand"],
                            "packet_accessions": ["P00387"],
                            "packet_ids": ["packet-P00387"],
                        },
                    ],
                },
                {
                    "modality": "structure",
                    "missing_packet_count": 1,
                    "source_name": "Structure sources",
                    "top_source_fix_candidates": [
                        {
                            "source_ref": "structure:Q9UCM0",
                            "priority_rank": 1,
                            "affected_packet_count": 1,
                            "missing_modality_count": 1,
                            "missing_modalities": ["structure"],
                            "packet_accessions": ["Q9UCM0"],
                            "packet_ids": ["packet-Q9UCM0"],
                        }
                    ],
                },
                {
                    "modality": "ppi",
                    "missing_packet_count": 1,
                    "source_name": "PPI sources",
                    "top_source_fix_candidates": [
                        {
                            "source_ref": "ppi:Q9UCM0",
                            "priority_rank": 1,
                            "affected_packet_count": 1,
                            "missing_modality_count": 1,
                            "missing_modalities": ["ppi"],
                            "packet_accessions": ["Q9UCM0"],
                            "packet_ids": ["packet-Q9UCM0"],
                        }
                    ],
                },
            ],
        },
    )

    return {
        "delta_report_path": delta_report_path,
        "delta_summary_path": delta_summary_path,
        "packet_deficit_path": packet_deficit_path,
    }


def test_build_packet_operator_blocker_surface_separates_actions(
    tmp_path: Path,
) -> None:
    paths = _write_inputs(tmp_path)

    payload = build_packet_operator_blocker_surface(
        delta_report_path=paths["delta_report_path"],
        delta_summary_path=paths["delta_summary_path"],
        packet_deficit_path=paths["packet_deficit_path"],
    )

    assert payload["summary"]["preserved_latest_blocker_count"] == 2
    assert payload["summary"]["fresh_run_regression_count"] == 1
    assert payload["summary"]["next_best_rescue_count"] == 4
    assert payload["summary"]["blocker_accessions"] == ["P00387", "Q9NZD4"]
    assert payload["summary"]["not_promotable_accessions"] == ["P02042"]

    blocker_rows = {row["accession"]: row for row in payload["preserved_latest_blockers"]}
    assert blocker_rows["Q9NZD4"]["next_rescue_source_ref"] == "ligand:Q9NZD4"
    assert blocker_rows["P00387"]["next_rescue_source_ref"] == "ligand:P00387"
    assert blocker_rows["Q9NZD4"]["next_rescue_action"].startswith("Apply ligand:Q9NZD4")

    not_promotable = payload["fresh_run_regressions_not_promotable"][0]
    assert not_promotable["accession"] == "P02042"
    assert "promotion attempt" in not_promotable["recommended_action"]

    rescue_rows = {row["source_ref"]: row for row in payload["next_best_actionable_rescues"]}
    assert rescue_rows["ligand:Q9NZD4"]["blocker_accessions"] == ["Q9NZD4"]
    assert rescue_rows["ligand:P00387"]["blocker_accessions"] == ["P00387"]
    assert rescue_rows["ligand:Q9NZD4"]["next_action"].startswith("Apply ligand:Q9NZD4")

    markdown = render_markdown(payload)
    assert "Preserved Latest Blockers" in markdown
    assert "Fresh-Run Regressions Not Promotable" in markdown
    assert "Next-Best Actionable Rescues" in markdown
    assert "Q9NZD4" in markdown
    assert "P00387" in markdown
    assert "P02042" in markdown


def test_main_writes_packet_operator_blocker_surface_outputs(tmp_path: Path, capsys) -> None:
    paths = _write_inputs(tmp_path)
    output_path = tmp_path / "artifacts" / "status" / "packet_operator_blocker_surface.json"

    exit_code = main(
        [
            "--delta-report",
            str(paths["delta_report_path"]),
            "--delta-summary",
            str(paths["delta_summary_path"]),
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
    assert "Packet operator blocker surface exported" in captured.out
    assert payload["summary"]["preserved_latest_blocker_count"] == 2
    assert payload["summary"]["fresh_run_regression_count"] == 1

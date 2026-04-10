from __future__ import annotations

import json
from pathlib import Path

from evaluation.post_tier1_packet_regression import (
    compare_packet_readiness,
    select_strongest_packet_baseline,
)


def test_compare_packet_readiness_flags_regressions() -> None:
    baseline = {
        "packet_count": 12,
        "complete_count": 6,
        "partial_count": 6,
        "unresolved_count": 0,
        "packets": [
            {"accession": "P69905", "status": "complete", "missing_modalities": []},
            {"accession": "P04637", "status": "partial", "missing_modalities": ["ppi"]},
            {"accession": "Q9NZD4", "status": "partial", "missing_modalities": ["ligand"]},
        ],
    }
    candidate = {
        "materialization": {
            "packet_count": 12,
            "complete_count": 3,
            "partial_count": 9,
            "unresolved_count": 0,
            "packets": [
                {"accession": "P69905", "status": "partial", "missing_modalities": ["ligand"]},
                {"accession": "P04637", "status": "complete", "missing_modalities": []},
                {"accession": "Q9NZD4", "status": "partial", "missing_modalities": ["ligand"]},
            ],
        }
    }

    report = compare_packet_readiness(
        baseline,
        candidate,
        baseline_path="data/packages/LATEST.json",
        candidate_path="runs/tier1/selected_cohort_materialization.json",
    )

    assert report.status == "failed"
    assert "complete_count:6->3" in report.regressions
    assert "partial_count:6->9" in report.regressions
    assert "packet_deficit_count:2->2" not in report.regressions
    assert "ligand_deficit_count:1->2" in report.regressions
    assert "ppi_deficit_count:1->0" in report.improvements
    changed = {entry.accession: entry for entry in report.changed_packets}
    assert changed["P69905"].before_status == "complete"
    assert changed["P69905"].after_status == "partial"
    assert changed["P04637"].before_missing_modalities == ("ppi",)
    assert changed["P04637"].after_missing_modalities == ()


def test_compare_packet_readiness_skips_without_baseline() -> None:
    candidate = {
        "materialization": {
            "packet_count": 1,
            "complete_count": 1,
            "partial_count": 0,
            "unresolved_count": 0,
            "packets": [
                {"accession": "P68871", "status": "complete", "missing_modalities": []}
            ],
        }
    }

    report = compare_packet_readiness(
        None,
        candidate,
        baseline_path="data/packages/LATEST.json",
        candidate_path="runs/tier1/selected_cohort_materialization.json",
    )

    assert report.status == "skipped"
    assert "missing_baseline_payload" in report.notes
    assert report.baseline_metrics is None
    assert report.candidate_metrics is None


def test_select_strongest_packet_baseline_prefers_best_historical_summary(
    tmp_path: Path,
) -> None:
    packages_root = tmp_path / "packages"
    latest_path = packages_root / "LATEST.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(
        json.dumps(
            {
                "packet_count": 12,
                "complete_count": 3,
                "partial_count": 9,
                "unresolved_count": 0,
                "packets": [
                    {
                        "accession": "P69905",
                        "status": "partial",
                        "missing_modalities": ["ligand"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    stronger = (
        packages_root
        / "selected-cohort-strict-20260323T1648Z"
        / "materialization_summary.json"
    )
    stronger.parent.mkdir(parents=True, exist_ok=True)
    stronger.write_text(
        json.dumps(
            {
                "packet_count": 12,
                "complete_count": 7,
                "partial_count": 5,
                "unresolved_count": 0,
                "packets": [
                    {"accession": "P69905", "status": "complete", "missing_modalities": []}
                ],
            }
        ),
        encoding="utf-8",
    )

    selection = select_strongest_packet_baseline(
        packages_root,
        current_latest_path=latest_path,
    )

    assert selection.baseline_path is not None
    assert selection.baseline_path.endswith(
        "selected-cohort-strict-20260323T1648Z/materialization_summary.json"
    )
    assert selection.current_latest_matches_strongest is False
    assert selection.baseline_payload is not None

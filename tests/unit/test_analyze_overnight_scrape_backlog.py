from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_export(tmp_path: Path) -> dict[str, object]:
    output_json = tmp_path / "overnight_scrape_wave_analysis.json"
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "analyze_overnight_scrape_backlog.py"),
            "--output-json",
            str(output_json),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return json.loads(output_json.read_text(encoding="utf-8"))


def test_analyze_overnight_scrape_backlog_builds_report_only_wave(tmp_path: Path) -> None:
    payload = _run_export(tmp_path)

    assert payload["status"] == "report_only"
    assert payload["summary"]["active_job_count"] == 2
    assert payload["summary"]["queued_job_count"] == 2
    assert payload["summary"]["catalog_tail_count"] == 22
    assert payload["summary"]["report_only_scrape_prep_count"] == 5
    assert payload["summary"]["gap_lane_state_counts"] == {
        "implemented": 10,
        "missing": 3,
        "partial": 3,
    }
    assert payload["summary"]["live_queue_source_keys"] == ["uniprot", "string"]
    assert payload["summary"]["queued_next_job_ids"] == [
        "chembl_rnacentral_bulk",
        "interpro_complexportal_resolver_small",
    ]
    assert payload["summary"]["report_only_scrape_targets"] == [
        "motif_active_site_enrichment",
        "interaction_context_enrichment",
        "kinetics_pathway_metadata_enrichment",
    ]
    assert payload["summary"]["targeted_page_scrape_accessions"] == ["P04637", "P31749"]
    assert payload["summary"]["deferred_catalog_focus_ids"] == [
        "P2-I016",
        "P3-I014",
        "P3-I018",
    ]
    assert payload["truth_boundary"]["report_only"] is True
    assert payload["truth_boundary"]["non_governing"] is True

    ranked = payload["ranked_actions"]
    assert ranked[0]["action_id"] == "uniprot"
    assert ranked[1]["action_id"] == "string"
    assert ranked[2]["action_id"] == "chembl_rnacentral_bulk"
    assert ranked[3]["action_id"] == "interpro_complexportal_resolver_small"
    assert ranked[4]["action_id"] == "motif_active_site_enrichment"
    assert ranked[7]["action_id"] == "targeted_page_scrape:P04637"
    assert ranked[8]["action_id"] == "targeted_page_scrape:P31749"

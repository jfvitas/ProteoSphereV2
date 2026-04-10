from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads() -> tuple[dict, dict, dict]:
    transition = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {"selected_count": 4},
        "rows": [
            {
                "accession": "P00387",
                "current_transition_state": "source_fix_transition_pending",
                "route_state": "governing_ready_but_package_blocked",
                "training_set_state": "governing_ready",
                "split": "train",
                "bucket": "moderate_coverage",
                "next_transition": "clear_source_fix_route",
                "source_fix_refs": ["ligand:P00387", "ligand:Q9NZD4"],
                "supporting_artifacts": ["training_set_transition_contract_preview"],
            },
            {
                "accession": "Q9UCM0",
                "current_transition_state": "source_fix_transition_pending",
                "route_state": "blocked_pending_acquisition",
                "training_set_state": "blocked_pending_acquisition",
                "split": "test",
                "bucket": "sparse_or_control",
                "next_transition": "clear_source_fix_route",
                "source_fix_refs": ["structure:Q9UCM0", "ppi:Q9UCM0"],
                "supporting_artifacts": ["training_set_transition_contract_preview"],
            },
            {
                "accession": "P69905",
                "current_transition_state": "package_transition_blocked",
                "route_state": "preview_visible_non_governing",
                "training_set_state": "preview_visible_non_governing",
            },
        ],
    }
    unlock = {
        "rows": [
            {
                "accession": "P00387",
                "route_steps": ["keep_visible_for_preview_compilation"],
                "supporting_artifacts": ["training_set_unlock_route_preview"],
            },
            {
                "accession": "Q9UCM0",
                "route_steps": ["wait_for_source_fix:structure:Q9UCM0"],
                "supporting_artifacts": ["training_set_unlock_route_preview"],
            },
        ]
    }
    remediation = {
        "rows": [
            {
                "accession": "P00387",
                "issue_buckets": ["packet_partial_or_missing", "source_fix_available"],
                "missing_modalities": ["structure", "ligand"],
                "recommended_actions": ["prefer_source_fix_refs_from_packet_deficit"],
            },
            {
                "accession": "Q9UCM0",
                "issue_buckets": ["blocked_pending_acquisition", "source_fix_available"],
                "missing_modalities": ["structure", "ppi"],
                "recommended_actions": ["keep_row_non_governing_until_acquisition"],
            },
        ]
    }
    return transition, unlock, remediation


def test_build_training_set_source_fix_batch_preview() -> None:
    from scripts.export_training_set_source_fix_batch_preview import (
        build_training_set_source_fix_batch_preview,
    )

    payload = build_training_set_source_fix_batch_preview(*_sample_payloads())

    assert payload["artifact_id"] == "training_set_source_fix_batch_preview"
    assert payload["summary"]["selected_count"] == 4
    assert payload["summary"]["source_fix_batch_row_count"] == 2
    assert payload["summary"]["current_batch_state"] == "blocked_pending_source_fix_batch"
    assert payload["summary"]["blocked_pending_acquisition_count"] == 1
    assert payload["summary"]["governing_ready_source_fix_count"] == 1
    assert payload["summary"]["next_source_fix_batch"] in {
        "ligand:P00387",
        "structure:Q9UCM0",
    }
    rows = {row["accession"]: row for row in payload["rows"]}
    assert rows["P00387"]["lead_source_fix_ref"] == "ligand:P00387"
    assert rows["Q9UCM0"]["lead_source_fix_ref"] == "structure:Q9UCM0"
    assert payload["truth_boundary"]["package_not_authorized"] is True


def test_main_writes_training_set_source_fix_batch_preview(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_training_set_source_fix_batch_preview as exporter

    transition, unlock, remediation = _sample_payloads()
    paths = {}
    for name, payload in {
        "transition": transition,
        "unlock": unlock,
        "remediation": remediation,
    }.items():
        path = tmp_path / f"{name}.json"
        _write_json(path, payload)
        paths[name] = path

    output_json = tmp_path / "training_set_source_fix_batch_preview.json"
    monkeypatch.setattr(
        exporter, "DEFAULT_TRANSITION_CONTRACT_PREVIEW", paths["transition"]
    )
    monkeypatch.setattr(exporter, "DEFAULT_UNLOCK_ROUTE_PREVIEW", paths["unlock"])
    monkeypatch.setattr(
        exporter, "DEFAULT_REMEDIATION_PLAN_PREVIEW", paths["remediation"]
    )
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)

    exit_code = exporter.main([])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["artifact_id"] == "training_set_source_fix_batch_preview"
    assert output_json.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert saved["summary"]["source_fix_batch_row_count"] == 2

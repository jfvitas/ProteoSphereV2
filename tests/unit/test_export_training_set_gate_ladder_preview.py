from __future__ import annotations

import json
from pathlib import Path

ACCESSIONS = [
    ("P69905", "train", "preview_visible_non_governing", "partial"),
    ("P68871", "train", "preview_visible_non_governing", "partial"),
    ("P04637", "train", "preview_visible_non_governing", "partial"),
    ("P31749", "train", "preview_visible_non_governing", "partial"),
    ("Q9NZD4", "train", "preview_visible_non_governing", "partial"),
    ("Q2TAC2", "train", "blocked_pending_acquisition", "partial"),
    ("P00387", "train", "governing_ready", "partial"),
    ("P02042", "train", "preview_visible_non_governing", "partial"),
    ("P02100", "val", "preview_visible_non_governing", "partial"),
    ("P69892", "val", "preview_visible_non_governing", "partial"),
    ("P09105", "test", "blocked_pending_acquisition", "partial"),
    ("Q9UCM0", "test", "blocked_pending_acquisition", "partial"),
]


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sample_payloads():
    readiness_rows = []
    split_rows = []
    blocker_rows = []
    modality_rows = []
    package_rows = []
    burndown_rows = []

    split_buckets = {
        "train": "rich_coverage",
        "val": "sparse_or_control",
        "test": "sparse_or_control",
    }
    modality_map = {
        "P69905": ["ligand", "ppi"],
        "P68871": ["structure", "ligand"],
        "P04637": ["sequence", "structure", "ligand"],
        "P31749": ["sequence", "structure", "ppi"],
        "Q9NZD4": ["ligand", "structure", "ppi", "variant"],
        "Q2TAC2": ["ligand", "structure", "ppi", "variant"],
        "P00387": ["ligand", "structure", "ppi", "variant"],
        "P02042": ["structure", "ligand", "ppi", "variant"],
        "P02100": ["structure", "ligand", "ppi", "variant"],
        "P69892": ["structure", "ligand", "ppi", "variant"],
        "P09105": ["ligand", "structure", "ppi", "variant"],
        "Q9UCM0": ["ligand", "ppi", "structure"],
    }
    next_step_map = {
        "P69905": "keep_visible_as_support_only",
        "P68871": "keep_visible_as_support_only",
        "P04637": "keep_visible_as_support_only",
        "P31749": "keep_visible_as_support_only",
        "Q9NZD4": "keep_non_governing_until_real_ligand_rows_exist",
        "Q2TAC2": "wait_for_source_fix:ligand:P00387",
        "P00387": "keep_visible_for_preview_compilation",
        "P02042": "keep_visible_as_support_only",
        "P02100": "keep_visible_as_support_only",
        "P69892": "keep_visible_as_support_only",
        "P09105": "wait_for_source_fix:ligand:P00387",
        "Q9UCM0": "wait_for_source_fix:structure:Q9UCM0",
    }

    for accession, split, state, packet_status in ACCESSIONS:
        readiness_rows.append(
            {
                "accession": accession,
                "split": split,
                "training_set_state": state,
                "packet_status": packet_status,
                "recommended_next_step": next_step_map[accession],
            }
        )
        split_rows.append(
            {
                "accession": accession,
                "split": split,
                "bucket": split_buckets[split],
                "status": "resolved",
                "leakage_key": accession,
            }
        )
        blocker_reasons = [
            "packet_partial_or_missing",
            "modality_gap",
            "thin_coverage",
            "package_gate_closed",
            "fold_export_ready=false",
            "cv_fold_export_unlocked=false",
            "split_post_staging_gate_closed",
        ]
        blocker_context = blocker_reasons + ["source_fix_available"]
        if state == "blocked_pending_acquisition":
            blocker_reasons.insert(0, "blocked_pending_acquisition")
            blocker_context.insert(0, "blocked_pending_acquisition")
        if state == "preview_visible_non_governing":
            blocker_context.insert(0, "preview_visible_non_governing")
        if accession == "P68871":
            blocker_context.append("mixed_evidence")
        blocker_rows.append(
            {
                "accession": accession,
                "blocked_reason_count": len(blocker_reasons),
                "blocked_reasons": blocker_reasons,
                "blocker_context": blocker_context,
                "fold_export_blocked": True,
                "modality_blocked": True,
                "modality_gap_categories": modality_map[accession],
                "package_blockers": blocker_context[:6],
                "package_ready": False,
                "priority_bucket": "critical",
                "recommended_next_step": next_step_map[accession],
                "training_set_state": state,
            }
        )
        modality_rows.append(
            {
                "accession": accession,
                "blocked_modality_count": len(modality_map[accession]),
                "gap_categories": modality_map[accession],
                "next_step": next_step_map[accession],
                "package_ready": False,
                "training_set_state": state,
            }
        )
        package_rows.append(
            {
                "accession": accession,
                "blocked_reason_count": len(blocker_reasons),
                "blocked_reasons": blocker_reasons,
                "blocker_context": blocker_context,
                "fold_export_blocked": True,
                "modality_blocked": True,
                "modality_gap_categories": modality_map[accession],
                "package_blockers": blocker_context[:6],
                "package_ready": False,
                "priority_bucket": "critical",
                "recommended_next_step": next_step_map[accession],
                "training_set_state": state,
                "packet_status": packet_status,
                "source_fix_refs": (
                    ["ligand:P00387"]
                    if accession in {"Q2TAC2", "P09105"}
                    else ["structure:Q9UCM0"]
                    if accession == "Q9UCM0"
                    else []
                ),
            }
        )
        burndown_rows.append(
            {
                "accession": accession,
                "action_ref": next_step_map[accession],
                "assignment_ready": True,
                "blocker_context": blocker_context,
                "critical_action": True,
                "package_ready": False,
                "priority_bucket": "critical",
                "top_next_actions": [
                    "preserve_packet_partiality_and_fill_missing_modalities",
                    next_step_map[accession],
                ],
                "top_source_fix_refs": (
                    ["ligand:P00387"]
                    if accession in {"Q2TAC2", "P09105"}
                    else ["structure:Q9UCM0"]
                    if accession == "Q9UCM0"
                    else []
                ),
            }
        )

    readiness = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "accession_count": 12,
            "selected_count": 12,
            "blocked_reasons": [
                "fold_export_ready=false",
                "cv_fold_export_unlocked=false",
                "split_dry_run_not_aligned",
                "split_post_staging_gate_closed",
            ],
            "assignment_ready": True,
            "fold_export_ready": False,
            "package_ready": False,
            "external_audit_decision": "usable_with_notes",
            "release_ready": False,
            "selected_split_counts": {"test": 2, "train": 8, "val": 2},
            "candidate_only_rows_non_governing": True,
        },
        "readiness_rows": readiness_rows,
    }
    package_readiness = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "packet_count": 12,
            "judgment_counts": {},
            "completeness_counts": {},
            "fold_export_ready": False,
            "cv_fold_export_unlocked": False,
            "final_split_committed": False,
            "ready_for_package": False,
            "blocked_reasons": [
                "fold_export_ready=false",
                "cv_fold_export_unlocked=false",
                "split_post_staging_gate_closed",
            ],
        },
        "truth_boundary": {"report_only": True, "non_governing": True},
    }
    split = {
        "artifact_id": "split_simulation_preview",
        "status": "report_only",
        "generated_at": "2026-03-22",
        "summary": {
            "label_count": 12,
            "split_counts": {"test": 2, "train": 8, "val": 2},
            "label_totals": {"total": 12, "train": 8, "val": 2, "test": 2},
            "bucket_counts": {"moderate_coverage": 4, "rich_coverage": 4, "sparse_or_control": 4},
            "dry_run_validation_status": "aligned",
            "fold_export_ready": False,
            "cv_fold_export_unlocked": False,
            "post_staging_gate_status": "blocked_report_emitted",
            "package_ready": False,
            "package_blocking_factors": [
                "fold_export_ready=false",
                "cv_fold_export_unlocked=false",
                "split_post_staging_gate_closed",
            ],
        },
        "rows": split_rows,
    }
    burndown = {
        "generated_at": "2026-04-03T00:00:00Z",
        "rows": burndown_rows,
    }
    modality = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "selected_accession_count": 12,
            "blocked_modality_count": 12,
            "package_ready": False,
            "non_mutating": True,
        },
        "rows": modality_rows,
    }
    package_matrix = {
        "generated_at": "2026-04-03T00:00:00Z",
        "summary": {
            "selected_accession_count": 12,
            "blocked_accession_count": 12,
            "fold_export_blocked_count": 12,
            "modality_blocked_count": 12,
            "package_ready": False,
            "package_blocked_reasons": [
                "fold_export_ready=false",
                "cv_fold_export_unlocked=false",
                "split_post_staging_gate_closed",
            ],
        },
        "rows": package_rows,
    }
    return readiness, package_readiness, split, burndown, modality, package_matrix


def test_build_training_set_gate_ladder_preview_compacts_gate_state() -> None:
    from scripts.export_training_set_gate_ladder_preview import (
        build_training_set_gate_ladder_preview,
    )

    payload = build_training_set_gate_ladder_preview(*_sample_payloads())

    assert payload["artifact_id"] == "training_set_gate_ladder_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["selected_count"] == 12
    assert payload["summary"]["assignment_ready"] is True
    assert payload["summary"]["fold_export_ready"] is False
    assert payload["summary"]["cv_fold_export_unlocked"] is False
    assert payload["summary"]["package_ready"] is False
    assert payload["summary"]["gate_ladder_status"] == "blocked_pending_package_gate"
    assert payload["summary"]["non_mutating"] is True
    assert payload["summary"]["fail_closed"] is True
    assert payload["summary"]["selected_split_counts"] == {"test": 2, "train": 8, "val": 2}
    assert payload["summary"]["gate_ladder_steps"][0]["stage"] == "readiness"
    assert payload["summary"]["gate_ladder_steps"][1]["status"] == "aligned"
    assert any(
        "split_dry_run_not_aligned" in alert
        for alert in payload["summary"]["consistency_alerts"]
    )

    rows = {row["accession"]: row for row in payload["rows"]}
    assert len(rows) == 12
    assert rows["P69905"]["split"] == "train"
    assert rows["P00387"]["inclusion_class"] == "selected"
    assert rows["P00387"]["gate_ladder_state"] == "governing_ready_but_package_blocked"
    assert rows["Q2TAC2"]["inclusion_class"] == "gated"
    assert rows["Q2TAC2"]["source_fix_refs"] == ["ligand:P00387"]
    assert rows["Q9UCM0"]["gate_ladder_state"] == "blocked_pending_acquisition"
    assert rows["P68871"]["modality_gap_categories"] == ["structure", "ligand"]
    assert payload["truth_boundary"]["non_mutating"] is True
    assert payload["truth_boundary"]["fail_closed"] is True


def test_main_writes_outputs_and_fails_closed_for_missing_inputs(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    from scripts import export_training_set_gate_ladder_preview as exporter

    (
        readiness,
        package_readiness,
        split,
        burndown,
        modality,
        package_matrix,
    ) = _sample_payloads()

    paths = {}
    for name, payload in {
        "readiness": readiness,
        "package": package_readiness,
        "split": split,
        "burndown": burndown,
        "modality": modality,
        "package_matrix": package_matrix,
    }.items():
        path = tmp_path / f"{name}.json"
        _write_json(path, payload)
        paths[name] = path

    output_json = tmp_path / "training_set_gate_ladder_preview.json"
    output_md = tmp_path / "training_set_gate_ladder_preview.md"
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_READINESS", paths["readiness"])
    monkeypatch.setattr(exporter, "DEFAULT_PACKAGE_READINESS", paths["package"])
    monkeypatch.setattr(exporter, "DEFAULT_SPLIT_SIMULATION", paths["split"])
    monkeypatch.setattr(
        exporter, "DEFAULT_TRAINING_SET_BLOCKER_BURNDOWN", paths["burndown"]
    )
    monkeypatch.setattr(
        exporter, "DEFAULT_TRAINING_SET_MODALITY_GAP_REGISTER", paths["modality"]
    )
    monkeypatch.setattr(
        exporter,
        "DEFAULT_TRAINING_SET_PACKAGE_BLOCKER_MATRIX",
        paths["package_matrix"],
    )
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_json)
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_MD", output_md)

    exit_code = exporter.main([])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["summary"]["selected_count"] == 12
    assert output_json.exists()
    assert output_md.exists()
    assert "Training Set Gate Ladder Preview" in output_md.read_text(encoding="utf-8")

    missing_split = tmp_path / "missing_split_simulation_preview.json"
    monkeypatch.setattr(exporter, "DEFAULT_SPLIT_SIMULATION", missing_split)
    output_json.unlink()
    output_md.unlink()

    exit_code = exporter.main([])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["summary"]["gate_ladder_status"] == "blocked_missing_inputs"
    assert "split_simulation_preview" in payload["summary"]["missing_inputs"]
    assert output_json.exists()
    assert output_md.exists()

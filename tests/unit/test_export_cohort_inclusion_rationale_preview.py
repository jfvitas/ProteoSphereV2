from __future__ import annotations

import json
from pathlib import Path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_cohort_inclusion_rationale_preview_classifies_rows() -> None:
    from scripts.export_cohort_inclusion_rationale_preview import (
        build_cohort_inclusion_rationale_preview,
    )

    payload = build_cohort_inclusion_rationale_preview(
        {
            "generated_at": "2026-04-03T00:00:00Z",
            "readiness_rows": [
                {
                    "accession": "A1",
                    "training_set_state": "governing_ready",
                    "ligand_readiness_ladder": "grounded preview-safe",
                },
                {
                    "accession": "A2",
                    "training_set_state": "blocked_pending_acquisition",
                    "ligand_readiness_ladder": "support-only",
                },
                {
                    "accession": "A3",
                    "training_set_state": "preview_visible_non_governing",
                    "ligand_readiness_ladder": "candidate-only non-governing",
                },
            ],
        },
        {
            "generated_at": "2026-04-03T00:00:00Z",
            "summary": {"selected_count": 3, "selected_accessions": ["A1", "A2", "A3"]},
            "rows": [
                {
                    "accession": "A1",
                    "split": "train",
                    "bucket": "rich_coverage",
                    "packet_status": "ready",
                    "package_role": "governing_preview_row",
                    "source_lanes": ["UniProt"],
                },
                {
                    "accession": "A2",
                    "split": "train",
                    "bucket": "sparse_or_control",
                    "packet_status": "partial",
                    "package_role": "blocked_pending_acquisition",
                    "source_lanes": ["UniProt"],
                },
                {
                    "accession": "A3",
                    "split": "test",
                    "bucket": "sparse_or_control",
                    "packet_status": "partial",
                    "package_role": "candidate_only_non_governing",
                    "source_lanes": ["UniProt"],
                },
            ],
        },
        {
            "generated_at": "2026-04-03T00:00:00Z",
            "rows": [
                {
                    "accession": "A1",
                    "issue_buckets": [],
                    "recommended_actions": ["preserve_selected_cohort_membership"],
                    "source_fix_refs": [],
                },
                {
                    "accession": "A2",
                    "issue_buckets": ["blocked_pending_acquisition", "modality_gap"],
                    "recommended_actions": ["wait_for_source_fix:A2"],
                    "source_fix_refs": ["ligand:A2"],
                },
                {
                    "accession": "A3",
                    "issue_buckets": ["candidate_only_non_governing", "thin_coverage"],
                    "recommended_actions": ["keep_non_governing_preview_only"],
                    "source_fix_refs": ["ligand:A3"],
                },
            ],
        },
        {
            "summary": {
                "selected_count": 3,
                "split_counts": {"train": 2, "test": 1},
                "bucket_counts": {"rich_coverage": 1, "sparse_or_control": 2},
                "thin_coverage_count": 1,
                "mixed_evidence_count": 0,
                "requested_modalities": ["sequence", "ligand"],
            },
            "rows": [
                {
                    "accession": "A1",
                    "thin_coverage": False,
                    "mixed_evidence": False,
                    "coverage_notes": [],
                    "packet_expectation": {
                        "present_modalities": ["sequence", "ligand"],
                        "missing_modalities": [],
                    },
                },
                {
                    "accession": "A2",
                    "thin_coverage": True,
                    "mixed_evidence": False,
                    "coverage_notes": ["single-lane coverage"],
                    "packet_expectation": {
                        "present_modalities": ["sequence"],
                        "missing_modalities": ["ligand"],
                    },
                },
                {
                    "accession": "A3",
                    "thin_coverage": False,
                    "mixed_evidence": False,
                    "coverage_notes": ["summary-library probe rather than direct assay"],
                    "packet_expectation": {
                        "present_modalities": ["sequence"],
                        "missing_modalities": ["ligand", "ppi"],
                    },
                },
            ],
        },
        {
            "packets": [
                {
                    "accession": "A2",
                    "deficit_source_refs": ["ligand:A2", "ppi:A2"],
                    "missing_source_refs": {"ligand": ["ligand:A2"]},
                },
                {
                    "accession": "A3",
                    "deficit_source_refs": ["ligand:A3"],
                    "missing_source_refs": {"ligand": ["ligand:A3"]},
                },
            ],
            "modality_deficits": [
                {
                    "modality": "ligand",
                    "packet_accessions": ["A2", "A3"],
                    "top_source_fix_refs": ["ligand:A2", "ligand:A3"],
                    "top_source_fix_candidates": [
                        {"source_ref": "ligand:A2"},
                        {"source_ref": "ligand:A3"},
                    ],
                }
            ],
        },
    )

    assert payload["artifact_id"] == "cohort_inclusion_rationale_preview"
    assert payload["status"] == "report_only"
    assert payload["summary"]["selected_count"] == 1
    assert payload["summary"]["gated_count"] == 1
    assert payload["summary"]["preview_only_count"] == 1
    assert payload["summary"]["top_source_fix_refs"][0]["source_fix_ref"] == "ligand:A2"

    row_by_accession = {row["accession"]: row for row in payload["rows"]}
    assert row_by_accession["A1"]["inclusion_class"] == "selected"
    assert "selected_for_cohort" in row_by_accession["A1"]["rationale_tags"]
    assert row_by_accession["A2"]["inclusion_class"] == "gated"
    assert "wait_for_source_fix:A2" in row_by_accession["A2"]["next_actions"]
    assert "source_fix_available" in row_by_accession["A2"]["rationale_tags"]
    assert row_by_accession["A3"]["inclusion_class"] == "preview-only"
    assert "preview_only_non_governing" in row_by_accession["A3"]["rationale_tags"]
    assert payload["truth_boundary"]["non_governing"] is True


def test_main_writes_default_json(tmp_path: Path, monkeypatch, capsys) -> None:
    from scripts import export_cohort_inclusion_rationale_preview as exporter

    readiness_path = tmp_path / "training_set_readiness_preview.json"
    cohort_path = tmp_path / "cohort_compiler_preview.json"
    remediation_path = tmp_path / "training_set_remediation_plan_preview.json"
    balance_path = tmp_path / "balance_diagnostics_preview.json"
    packet_path = tmp_path / "packet_deficit_dashboard.json"
    output_path = tmp_path / "cohort_inclusion_rationale_preview.json"

    _write_json(
        readiness_path,
        {
            "generated_at": "2026-04-03T00:00:00Z",
            "readiness_rows": [
                {
                    "accession": "A1",
                    "training_set_state": "governing_ready",
                    "ligand_readiness_ladder": "grounded preview-safe",
                }
            ],
        },
    )
    _write_json(
        cohort_path,
        {
            "generated_at": "2026-04-03T00:00:00Z",
            "summary": {"selected_count": 1, "selected_accessions": ["A1"]},
            "rows": [
                {
                    "accession": "A1",
                    "split": "train",
                    "bucket": "rich_coverage",
                    "packet_status": "ready",
                    "package_role": "governing_preview_row",
                }
            ],
        },
    )
    _write_json(
        remediation_path,
        {
            "generated_at": "2026-04-03T00:00:00Z",
            "rows": [
                {
                    "accession": "A1",
                    "issue_buckets": [],
                    "recommended_actions": ["preserve_selected_cohort_membership"],
                    "source_fix_refs": [],
                }
            ],
        },
    )
    _write_json(
        balance_path,
        {
            "generated_at": "2026-04-03T00:00:00Z",
            "summary": {
                "selected_count": 1,
                "split_counts": {"train": 1},
                "bucket_counts": {"rich_coverage": 1},
                "thin_coverage_count": 0,
                "mixed_evidence_count": 0,
                "requested_modalities": ["sequence"],
            },
            "rows": [
                {
                    "accession": "A1",
                    "thin_coverage": False,
                    "mixed_evidence": False,
                    "coverage_notes": [],
                    "packet_expectation": {
                        "present_modalities": ["sequence"],
                        "missing_modalities": [],
                    },
                }
            ],
        },
    )
    _write_json(packet_path, {"packets": [], "modality_deficits": []})

    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_READINESS", readiness_path)
    monkeypatch.setattr(exporter, "DEFAULT_COHORT_COMPILER", cohort_path)
    monkeypatch.setattr(exporter, "DEFAULT_TRAINING_SET_REMEDIATION_PLAN", remediation_path)
    monkeypatch.setattr(exporter, "DEFAULT_BALANCE_DIAGNOSTICS", balance_path)
    monkeypatch.setattr(exporter, "DEFAULT_PACKET_DEFICIT", packet_path)
    monkeypatch.setattr(exporter, "DEFAULT_OUTPUT_JSON", output_path)

    exporter.main([])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert payload["artifact_id"] == "cohort_inclusion_rationale_preview"
    assert output_path.exists()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["summary"]["selected_count"] == 1

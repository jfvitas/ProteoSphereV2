from __future__ import annotations

import json
from pathlib import Path

import api.model_studio.paper_evaluator.pipeline as pipeline_module
from api.model_studio.paper_evaluator import (
    apply_llm_gap_decisions,
    build_llm_gap_packet,
    compare_evaluator_reports,
    evaluate_paper_corpus,
    load_paper_corpus,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "paper_dataset_evaluator"


def _load_json(name: str) -> dict:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def test_evaluate_paper_corpus_emits_expected_verdicts_and_reason_codes() -> None:
    corpus = load_paper_corpus(FIXTURE_ROOT / "sample_corpus.json")
    snapshot = _load_json("sample_warehouse_snapshot.json")

    report = evaluate_paper_corpus(corpus, snapshot)
    rows = {row["paper_id"]: row for row in report["papers"]}

    assert report["summary"]["paper_count"] == 3
    assert rows["paper_overlap"]["verdict"] == "unsafe_for_training"
    assert set(rows["paper_overlap"]["reason_codes"]) >= {
        "DIRECT_OVERLAP",
        "ACCESSION_ROOT_OVERLAP",
        "UNIREF_CLUSTER_OVERLAP",
        "SHARED_PARTNER_LEAKAGE",
        "INCOMPLETE_MODALITY_COVERAGE",
    }
    assert rows["paper_overlap"]["resolved_split_policy"]["policy"] == "paper_faithful_external"

    assert rows["paper_cv"]["verdict"] == "unsafe_for_training"
    assert "POLICY_MISMATCH" in rows["paper_cv"]["reason_codes"]
    assert "UNRESOLVED_SPLIT_MEMBERSHIP" in rows["paper_cv"]["reason_codes"]
    assert rows["paper_cv"]["needs_human_review"] is False

    assert rows["paper_unresolved"]["verdict"] == "audit_only"
    assert rows["paper_unresolved"]["resolved_split_policy"]["policy"] == "uniref_grouped"
    assert rows["paper_unresolved"]["needs_human_review"] is False


def test_compare_evaluator_reports_detects_exact_match() -> None:
    corpus = load_paper_corpus(FIXTURE_ROOT / "sample_corpus.json")
    snapshot = _load_json("sample_warehouse_snapshot.json")
    llm_output = _load_json("sample_llm_output.json")

    code_report = evaluate_paper_corpus(corpus, snapshot)
    comparison = compare_evaluator_reports(
        code_report,
        llm_output,
        cohorts=corpus["cohorts"],
    )

    assert comparison["comparison_status"] == "passed"
    assert comparison["summary"]["paper_count"] == 3
    assert comparison["summary"]["exact_match_count"] == 3


def test_gap_packet_and_bounded_bridge_application() -> None:
    corpus = load_paper_corpus(FIXTURE_ROOT / "sample_corpus.json")
    snapshot = _load_json("sample_warehouse_snapshot.json")
    code_report = evaluate_paper_corpus(corpus, snapshot)

    code_report["papers"][1]["needs_human_review"] = True
    gap_packet = build_llm_gap_packet(code_report)
    paper_ids = {row["paper_id"] for row in gap_packet["papers"]}
    assert paper_ids == {"paper_cv"}

    bridged = apply_llm_gap_decisions(
        code_report,
        {
            "artifact_id": "sample_gap_decisions",
            "decision_model": "claude-bridge",
            "papers": [
                {
                    "paper_id": "paper_cv",
                    "needs_human_review": False,
                    "llm_rationale": "Cross-validation mismatch is already decisive and does not require human review."
                }
            ],
        },
    )
    rows = {row["paper_id"]: row for row in bridged["papers"]}
    assert rows["paper_cv"]["needs_human_review"] is False
    assert rows["paper_overlap"]["needs_human_review"] is False
    assert "LLM bridge rationale:" in rows["paper_cv"]["provenance_notes"][-1]


def test_missing_membership_only_stays_blocked_without_supplemental_audit_artifact(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(pipeline_module, "DEFAULT_EXISTING_AUDIT_ROOT", tmp_path)
    corpus = {
        "artifact_id": "manual_corpus",
        "schema_id": "manual",
        "cohorts": {},
        "papers": [
            {
                "paper_id": "paper_external_missing",
                "title": "Paper External Missing",
                "doi": "doi:paper_external_missing",
                "task_group": "ppi_prediction",
                "modality": "sequence_only",
                "claimed_dataset": "external set",
                "source_families": ["rcsb_pdbe"],
                "named_entities": ["external"],
                "claimed_split_description": "External holdout is claimed but no roster is given.",
                "split_style": "paper_specific_external",
            }
        ],
    }
    snapshot = _load_json("sample_warehouse_snapshot.json")
    report = evaluate_paper_corpus(corpus, snapshot)
    row = report["papers"][0]
    assert row["verdict"] == "blocked_pending_mapping"
    assert row["needs_human_review"] is False


def test_missing_membership_audit_only_when_supplemental_artifact_exists(monkeypatch, tmp_path) -> None:
    audit_root = tmp_path / "paper_split_list"
    audit_root.mkdir(parents=True)
    (audit_root / "paper_external_missing.json").write_text(
        json.dumps(
            {
                "supplemental_evidence": {
                    "status": "published_split_located",
                    "artifact_paths": ["D:/tmp/example.tsv"],
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(pipeline_module, "DEFAULT_EXISTING_AUDIT_ROOT", audit_root)
    corpus = {
        "artifact_id": "manual_corpus",
        "schema_id": "manual",
        "cohorts": {},
        "papers": [
            {
                "paper_id": "paper_external_missing",
                "title": "Paper External Missing",
                "doi": "doi:paper_external_missing",
                "task_group": "ppi_prediction",
                "modality": "sequence_only",
                "claimed_dataset": "external set",
                "source_families": ["rcsb_pdbe"],
                "named_entities": ["external"],
                "claimed_split_description": "External holdout is claimed but no roster is given.",
                "split_style": "paper_specific_external",
            }
        ],
    }
    snapshot = _load_json("sample_warehouse_snapshot.json")
    report = evaluate_paper_corpus(corpus, snapshot)
    row = report["papers"][0]
    assert row["verdict"] == "audit_only"
    assert row["supplemental_evidence"]["status"] == "published_split_located"


def test_warehouse_audit_registry_surfaces_identifier_bridge_requirements(monkeypatch, tmp_path) -> None:
    audit_root = tmp_path / "paper_split_list"
    audit_root.mkdir(parents=True)
    registry_path = tmp_path / "paper_split_audit_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "artifact_id": "paper_split_audit_registry",
                "records": [
                    {
                        "paper_id": "paper_bridge",
                        "audit_surface_status": "supplemental_artifact_materialized",
                        "identifier_bridge_requirements": [
                            {
                                "requirement_id": "ensembl_to_uniprot",
                                "source_namespace": "ensembl_protein",
                                "target_namespace": "uniprot_accession",
                                "reason": "Recovered split files use Ensembl protein identifiers.",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(pipeline_module, "DEFAULT_EXISTING_AUDIT_ROOT", audit_root)
    monkeypatch.setattr(pipeline_module, "DEFAULT_WAREHOUSE_AUDIT_REGISTRY", registry_path)
    corpus = {
        "artifact_id": "manual_corpus",
        "schema_id": "manual",
        "cohorts": {},
        "papers": [
            {
                "paper_id": "paper_bridge",
                "title": "Paper Bridge",
                "doi": "doi:paper_bridge",
                "task_group": "ppi_prediction",
                "modality": "sequence_only",
                "claimed_dataset": "bridge set",
                "source_families": ["intact", "uniprot"],
                "named_entities": ["bridge"],
                "claimed_split_description": "External holdout is claimed but identifiers require bridging.",
                "split_style": "external_holdout",
            }
        ],
    }
    snapshot = _load_json("sample_warehouse_snapshot.json")
    report = evaluate_paper_corpus(corpus, snapshot)
    row = report["papers"][0]
    assert row["warehouse_audit_surface"]["audit_surface_status"] == "supplemental_artifact_materialized"
    assert row["identifier_bridge_requirements"][0]["requirement_id"] == "ensembl_to_uniprot"


def test_identifier_bridge_registry_is_attached_to_paper_output(monkeypatch, tmp_path) -> None:
    audit_root = tmp_path / "paper_split_list"
    audit_root.mkdir(parents=True)
    registry_path = tmp_path / "paper_identifier_bridge_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "artifact_id": "paper_identifier_bridge_registry",
                "records": [
                    {
                        "paper_id": "paper_bridge",
                        "bridge_status": "materialized",
                        "exact_mapped_identifier_count": 12,
                        "detail_artifact_path": "D:/tmp/paper_bridge.json",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(pipeline_module, "DEFAULT_EXISTING_AUDIT_ROOT", audit_root)
    monkeypatch.setattr(
        pipeline_module,
        "DEFAULT_WAREHOUSE_IDENTIFIER_BRIDGE_REGISTRY",
        registry_path,
    )
    corpus = {
        "artifact_id": "manual_corpus",
        "schema_id": "manual",
        "cohorts": {},
        "papers": [
            {
                "paper_id": "paper_bridge",
                "title": "Paper Bridge",
                "doi": "doi:paper_bridge",
                "task_group": "ppi_prediction",
                "modality": "sequence_only",
                "claimed_dataset": "bridge set",
                "source_families": ["intact", "uniprot"],
                "named_entities": ["bridge"],
                "claimed_split_description": "Bridge-enhanced audit paper.",
                "split_style": "external_holdout",
            }
        ],
    }
    snapshot = _load_json("sample_warehouse_snapshot.json")
    report = evaluate_paper_corpus(corpus, snapshot)
    row = report["papers"][0]
    assert row["warehouse_identifier_bridge"]["bridge_status"] == "materialized"
    assert row["warehouse_identifier_bridge"]["exact_mapped_identifier_count"] == 12


def test_evaluate_explicit_manifest_reuses_shared_policy_and_reason_contract(tmp_path) -> None:
    source_manifest_path = tmp_path / "source_manifest.json"
    source_manifest_path.write_text(
        json.dumps(
            {
                "records": [
                    {"record_id": "r1", "split": "train", "protein_a": "P11111", "protein_b": "Q11111", "provenance_note": "paper table"},
                    {"record_id": "r2", "split": "val", "protein_a": "P22222", "protein_b": "Q22222", "provenance_note": "paper table"},
                    {"record_id": "r3", "split": "test", "protein_a": "P11111", "protein_b": "Q33333", "provenance_note": "paper table"},
                ]
            }
        ),
        encoding="utf-8",
    )
    assessment = pipeline_module.evaluate_explicit_manifest(
        {
            "manifest_id": "manifest:explicit-overlap",
            "dataset_ref": "custom_study:manifest:explicit-overlap",
            "title": "Explicit overlap manifest",
            "entity_kind": "protein_pair",
            "source_manifest": str(source_manifest_path),
            "validation": {
                "split_counts": {"train": 1, "val": 1, "test": 1},
                "total_uploaded_rows": 3,
                "resolved_rows": 3,
                "unresolved_rows": 0,
                "grounding_coverage": 1.0,
                "unresolved_entities": [],
                "unresolved_record_ids": [],
                "warehouse_resolution": {
                    "uniref_by_accession": {
                        "P11111": "UniRef90_A",
                        "Q11111": "UniRef90_B",
                        "P22222": "UniRef90_C",
                        "Q22222": "UniRef90_D",
                        "Q33333": "UniRef90_E",
                    }
                },
                "warnings": [],
                "blockers": [],
            },
            "row_count": 3,
        },
        {"entity_families": {"proteins": {"default_view": "best_evidence"}}},
    )

    assert assessment["evaluation_mode"] == "explicit_manifest"
    assert assessment["resolved_split_policy"]["policy"] == "explicit_manifest"
    assert assessment["verdict"] == "unsafe_for_training"
    assert set(assessment["reason_codes"]) >= {
        "DIRECT_OVERLAP",
        "ACCESSION_ROOT_OVERLAP",
        "SHARED_PARTNER_LEAKAGE",
    }
    assert assessment["needs_human_review"] is False

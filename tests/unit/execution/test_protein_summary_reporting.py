from __future__ import annotations

import json
from pathlib import Path

from core.library.summary_record import SummaryLibrarySchema
from execution.library.protein_summary_reporting import (
    build_protein_summary_cross_source_view_report,
    build_protein_summary_consensus_reference_surface_report,
    build_protein_summary_consensus_examples_note_report,
    build_protein_summary_disagreement_priority_note_report,
    build_protein_summary_integration_note_report,
    build_protein_summary_packet_gap_library_strength_note_report,
    build_protein_summary_packet_gap_operator_action_note_report,
    build_protein_summary_packet_gap_next_actions_note_report,
    build_protein_summary_reference_library_examples_report,
    build_protein_summary_source_fusion_examples_report,
    build_protein_summary_source_fusion_priority_note_report,
    render_protein_summary_consensus_reference_surface_markdown,
    render_protein_summary_consensus_examples_note_markdown,
    render_protein_summary_disagreement_priority_note_markdown,
    render_protein_summary_integration_note_markdown,
    render_protein_summary_packet_gap_library_strength_note_markdown,
    render_protein_summary_packet_gap_operator_action_note_markdown,
    render_protein_summary_packet_gap_next_actions_note_markdown,
    render_protein_summary_source_fusion_examples_markdown,
    render_protein_summary_source_fusion_priority_note_markdown,
)


def test_cross_source_view_report_matches_materialized_library_artifact() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    library_path = repo_root / "artifacts" / "status" / "protein_summary_library.json"
    report_path = (
        repo_root
        / "artifacts"
        / "status"
        / "protein_summary_cross_source_view_report.json"
    )

    library = SummaryLibrarySchema.from_dict(
        json.loads(library_path.read_text(encoding="utf-8"))
    )
    report = build_protein_summary_cross_source_view_report(library)
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report == saved_report
    assert report["example_count"] == 3
    assert report["examples"][0]["summary_id"] == "protein:P69905"
    assert report["examples"][0]["connection_counts"] == {
        "direct_joins": 4,
        "indirect_bridges": 4,
        "partial_joins": 1,
    }


def test_reference_library_examples_report_matches_current_materialized_output() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    library_path = repo_root / "artifacts" / "status" / "protein_summary_library.json"
    report_path = (
        repo_root
        / "artifacts"
        / "status"
        / "protein_summary_reference_library_examples_report.json"
    )

    library = SummaryLibrarySchema.from_dict(
        json.loads(library_path.read_text(encoding="utf-8"))
    )
    report = build_protein_summary_reference_library_examples_report(
        library,
        accessions=("P00387", "P31749", "Q9NZD4"),
    )
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report == saved_report
    assert report["selected_accessions"] == ["P00387", "P31749", "Q9NZD4"]
    assert report["examples"][0]["summary_id"] == "protein:P00387"
    assert report["examples"][1]["summary_id"] == "protein:P31749"
    assert report["examples"][2]["summary_id"] == "protein:Q9NZD4"
    assert report["examples"][1]["reference_library_use_summary"].startswith("direct=4")
    assert report["examples"][1]["rollups"][0]["status"] == "resolved"


def test_consensus_reference_surface_report_keeps_disagreements_visible() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    library_path = repo_root / "artifacts" / "status" / "protein_summary_library.json"
    report_path = (
        repo_root
        / "artifacts"
        / "status"
        / "protein_summary_consensus_reference_surface_report.json"
    )

    library = SummaryLibrarySchema.from_dict(
        json.loads(library_path.read_text(encoding="utf-8"))
    )
    report = build_protein_summary_consensus_reference_surface_report(
        library,
        accessions=("P00387", "P31749", "Q9NZD4"),
    )
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report == saved_report
    assert report["selected_accessions"] == ["P00387", "P31749", "Q9NZD4"]

    p31749 = next(example for example in report["examples"] if example["summary_id"] == "protein:P31749")
    assert p31749["source_precedence"] == ["UniProt", "Reactome", "IntAct"]
    assert any(field["field_name"] == "protein_name" and field["status"] == "resolved" for field in p31749["consensus_ready_fields"])
    assert any(field["field_name"] == "aliases" and field["status"] == "conflict" for field in p31749["stay_partial_fields"])
    assert "aliases" in p31749["consensus_ready_summary"]
    assert "conflict=1" in p31749["consensus_ready_summary"]

    p00387 = next(example for example in report["examples"] if example["summary_id"] == "protein:P00387")
    assert any(field["field_name"] == "protein_name" and field["status"] == "partial" for field in p00387["stay_partial_fields"])
    assert p00387["cross_source_view"]["partial_joins"]

    q9nzd4 = next(example for example in report["examples"] if example["summary_id"] == "protein:Q9NZD4")
    assert q9nzd4["consensus_ready_fields"] == []
    assert any(field["field_name"] == "aliases" and field["status"] == "partial" for field in q9nzd4["stay_partial_fields"])


def test_consensus_reference_surface_markdown_matches_current_materialized_output() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    library_path = repo_root / "artifacts" / "status" / "protein_summary_library.json"
    report_path = (
        repo_root
        / "artifacts"
        / "status"
        / "protein_summary_consensus_reference_surface_report.json"
    )
    markdown_path = (
        repo_root
        / "artifacts"
        / "status"
        / "protein_summary_consensus_reference_surface_report.md"
    )

    library = SummaryLibrarySchema.from_dict(
        json.loads(library_path.read_text(encoding="utf-8"))
    )
    report = build_protein_summary_consensus_reference_surface_report(
        library,
        accessions=("P00387", "P31749", "Q9NZD4"),
    )
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    markdown = render_protein_summary_consensus_reference_surface_markdown(report)
    saved_markdown = markdown_path.read_text(encoding="utf-8")

    assert report == saved_report
    assert markdown == saved_markdown
    assert "Protein Summary Consensus Reference Surface" in markdown
    assert "P31749" in markdown
    assert "aliases" in markdown and "disagree" in markdown
    assert "Why this stays partial" in markdown


def test_source_fusion_examples_report_matches_current_artifacts() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    library_path = repo_root / "artifacts" / "status" / "protein_summary_library.json"
    report_path = (
        repo_root
        / "artifacts"
        / "status"
        / "protein_summary_source_fusion_examples_report.json"
    )
    markdown_path = (
        repo_root
        / "artifacts"
        / "status"
        / "protein_summary_source_fusion_examples_report.md"
    )

    library = SummaryLibrarySchema.from_dict(
        json.loads(library_path.read_text(encoding="utf-8"))
    )
    report = build_protein_summary_source_fusion_examples_report(library)
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    markdown = render_protein_summary_source_fusion_examples_markdown(report)
    saved_markdown = markdown_path.read_text(encoding="utf-8")

    assert report == saved_report
    assert markdown == saved_markdown
    assert report["selected_accessions"] == ["P31749", "P69905", "P04637"]
    assert report["examples"][0]["case_kind"] == "ligand-heavy"
    assert report["examples"][0]["ligand_bridge"]["ligand_id"] == "CQU"
    assert report["examples"][1]["pathway_summary"]["pathway_reference_count"] == 18
    assert report["examples"][2]["conflict_fields"][0]["field_name"] == "aliases"
    assert "ligand-heavy" in markdown
    assert "pathway-heavy" in markdown
    assert "conflict-heavy" in markdown


def test_integration_note_report_matches_current_artifacts() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    library_path = repo_root / "artifacts" / "status" / "protein_summary_library.json"
    report_path = (
        repo_root
        / "artifacts"
        / "status"
        / "protein_summary_integration_note_report.json"
    )
    markdown_path = (
        repo_root
        / "artifacts"
        / "status"
        / "protein_summary_integration_note_report.md"
    )

    library = SummaryLibrarySchema.from_dict(
        json.loads(library_path.read_text(encoding="utf-8"))
    )
    report = build_protein_summary_integration_note_report(library)
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    markdown = render_protein_summary_integration_note_markdown(report)
    saved_markdown = markdown_path.read_text(encoding="utf-8")

    assert report == saved_report
    assert markdown == saved_markdown
    assert report["selected_accessions"] == ["P31749", "P69905", "P04637"]
    assert report["source_fusion_examples"][0]["case_kind"] == "ligand-heavy"
    assert report["source_fusion_examples"][1]["cross_source_counts"] == {
        "direct_joins": 4,
        "indirect_bridges": 4,
        "partial_joins": 1,
    }
    assert report["motif_breadth_truth"]["current_library_use_ready_source_count"] == 3
    assert report["motif_breadth_truth"]["release_grade_ready"] is False
    assert report["motif_breadth_truth"]["external_gaps"][0]["source_name"] == "mega_motif_base"
    assert "Protein Summary Integration Note" in markdown
    assert "Motif Breadth Truth" in markdown
    assert "elm" in markdown


def test_consensus_examples_note_matches_current_artifacts() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    library_path = repo_root / "artifacts" / "status" / "protein_summary_library.json"
    report_path = (
        repo_root
        / "artifacts"
        / "status"
        / "protein_summary_consensus_examples_note.json"
    )
    markdown_path = (
        repo_root
        / "docs"
        / "reports"
        / "protein_summary_consensus_examples_note.md"
    )

    library = SummaryLibrarySchema.from_dict(
        json.loads(library_path.read_text(encoding="utf-8"))
    )
    report = build_protein_summary_consensus_examples_note_report(library)
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    markdown = render_protein_summary_consensus_examples_note_markdown(report)
    saved_markdown = markdown_path.read_text(encoding="utf-8")

    assert report == saved_report
    assert markdown == saved_markdown
    assert report["selected_accessions"] == ["P00387", "P31749", "Q9NZD4"]
    assert report["summary"]["source_agreement_example_count"] == 1
    assert report["summary"]["preserved_partial_example_count"] == 3
    assert report["examples"][0]["consensus_classification"] == "partial-reference-shell"
    assert report["examples"][1]["consensus_classification"] == "strong-agreement-with-preserved-disagreement"
    assert report["examples"][1]["consensus_ready_fields"] == [
        "protein_name",
        "organism_name",
        "sequence_length",
        "gene_names",
    ]
    assert report["examples"][2]["stay_partial_fields"] == [
        "protein_name",
        "organism_name",
        "taxon_id",
        "sequence_length",
        "sequence_checksum",
        "sequence_version",
        "gene_names",
        "aliases",
    ]
    assert "Protein Summary Consensus Examples Note" in markdown
    assert "strong-agreement-with-preserved-disagreement" in markdown
    assert "partial-reference-shell" in markdown


def test_disagreement_priority_note_matches_current_artifacts() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    library_path = repo_root / "artifacts" / "status" / "protein_summary_library.json"
    report_path = (
        repo_root
        / "artifacts"
        / "status"
        / "protein_summary_disagreement_priority_note.json"
    )
    markdown_path = (
        repo_root
        / "docs"
        / "reports"
        / "protein_summary_disagreement_priority_note.md"
    )

    library = SummaryLibrarySchema.from_dict(
        json.loads(library_path.read_text(encoding="utf-8"))
    )
    report = build_protein_summary_disagreement_priority_note_report(library)
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    markdown = render_protein_summary_disagreement_priority_note_markdown(report)
    saved_markdown = markdown_path.read_text(encoding="utf-8")

    assert report == saved_report
    assert markdown == saved_markdown
    assert report["selected_accessions"] == ["P00387", "P31749", "Q9NZD4"]
    assert report["summary"]["consensus_with_preserved_conflict_example_count"] == 1
    assert report["summary"]["partial_hold_example_count"] == 2
    assert report["examples"][0]["priority_classification"] == "partial-held-back"
    assert report["examples"][1]["priority_classification"] == "consensus-with-preserved-conflict"
    assert report["examples"][1]["resolved_fields"] == [
        "protein_name",
        "organism_name",
        "sequence_length",
        "gene_names",
    ]
    assert report["examples"][1]["conflict_fields"][0]["field_name"] == "aliases"
    assert "Protein Summary Disagreement and Priority Note" in markdown
    assert "preserve disagreement" in markdown
    assert "keep single-source fields partial" in markdown


def test_source_fusion_priority_note_matches_current_artifacts() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    library_path = repo_root / "artifacts" / "status" / "protein_summary_library.json"
    report_path = (
        repo_root
        / "artifacts"
        / "status"
        / "protein_summary_source_fusion_priority_note.json"
    )
    markdown_path = (
        repo_root
        / "docs"
        / "reports"
        / "protein_summary_source_fusion_priority_note.md"
    )

    library = SummaryLibrarySchema.from_dict(
        json.loads(library_path.read_text(encoding="utf-8"))
    )
    report = build_protein_summary_source_fusion_priority_note_report(library)
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    markdown = render_protein_summary_source_fusion_priority_note_markdown(report)
    saved_markdown = markdown_path.read_text(encoding="utf-8")

    assert report == saved_report
    assert markdown == saved_markdown
    assert report["selected_accessions"] == ["P31749", "P69905", "P00387"]
    assert report["summary"]["consensus_example_count"] == 2
    assert report["summary"]["preserved_conflict_example_count"] == 1
    assert report["summary"]["partial_hold_example_count"] == 1
    assert report["examples"][0]["priority_classification"] == "consensus-with-preserved-conflict"
    assert report["examples"][1]["priority_classification"] == "mixed-consensus"
    assert report["examples"][2]["priority_classification"] == "partial-held-back"
    assert report["examples"][0]["conflict_fields"][0]["field_name"] == "aliases"
    assert report["examples"][1]["resolved_fields"] == ["organism_name", "aliases"]
    assert "Protein Summary Source Fusion Priority Note" in markdown
    assert "consensus-with-preserved-conflict" in markdown
    assert "partial-held-back" in markdown


def test_packet_gap_library_strength_note_matches_current_artifacts() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    library_path = repo_root / "artifacts" / "status" / "protein_summary_library.json"
    report_path = (
        repo_root
        / "artifacts"
        / "status"
        / "protein_summary_packet_gap_library_strength_note.json"
    )
    markdown_path = (
        repo_root
        / "docs"
        / "reports"
        / "protein_summary_packet_gap_library_strength_note.md"
    )

    library = SummaryLibrarySchema.from_dict(
        json.loads(library_path.read_text(encoding="utf-8"))
    )
    report = build_protein_summary_packet_gap_library_strength_note_report(library)
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    markdown = render_protein_summary_packet_gap_library_strength_note_markdown(report)
    saved_markdown = markdown_path.read_text(encoding="utf-8")

    assert report == saved_report
    assert markdown == saved_markdown
    assert report["selected_accessions"] == ["P31749", "P04637", "P00387"]
    assert report["packet_audit_summary"]["judgment_counts"]["useful"] == 1
    assert report["current_packet_anchor"]["accession"] == "P69905"
    assert report["examples"][0]["packet_missing_modalities"] == [
        "sequence",
        "structure",
        "ppi",
    ]
    assert report["examples"][1]["packet_source_lanes"] == ["IntAct"]
    assert report["examples"][2]["library_resolved_fields"] == []
    assert "Protein Summary Packet Gap and Library Strength Note" in markdown
    assert "P69905" in markdown
    assert "missing structure" in markdown


def test_packet_gap_operator_action_note_matches_current_artifacts() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    library_path = repo_root / "artifacts" / "status" / "protein_summary_library.json"
    report_path = (
        repo_root
        / "artifacts"
        / "status"
        / "protein_summary_packet_gap_operator_action_note.json"
    )
    markdown_path = (
        repo_root
        / "docs"
        / "reports"
        / "protein_summary_packet_gap_operator_action_note.md"
    )

    library = SummaryLibrarySchema.from_dict(
        json.loads(library_path.read_text(encoding="utf-8"))
    )
    report = build_protein_summary_packet_gap_operator_action_note_report(library)
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    markdown = render_protein_summary_packet_gap_operator_action_note_markdown(report)
    saved_markdown = markdown_path.read_text(encoding="utf-8")

    assert report == saved_report
    assert markdown == saved_markdown
    assert report["selected_accessions"] == ["P31749", "P04637", "P69905"]
    assert report["packet_dashboard_summary"]["complete_packet_count"] == 7
    assert report["packet_delta_summary"]["packet_level_regressed_count"] == 11
    assert report["current_packet_anchor"]["accession"] == "P69905"
    assert report["examples"][0]["freshest_packet_missing_modalities"] == [
        "ppi",
        "structure",
    ]
    assert report["examples"][1]["freshest_packet_missing_modalities"] == [
        "ligand",
        "structure",
    ]
    assert report["examples"][2]["next_operator_action"].startswith(
        "keep as the current packet anchor"
    )
    assert "Protein Summary Packet Gap Operator Action Note" in markdown
    assert "repair the freshest-run regressions" in markdown
    assert "Actionable Source Refs" in markdown
    assert "consensus-with-preserved-conflict" in markdown
    assert "mixed-consensus" in markdown


def test_packet_gap_next_actions_note_matches_current_artifacts() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    library_path = repo_root / "artifacts" / "status" / "protein_summary_library.json"
    report_path = (
        repo_root
        / "artifacts"
        / "status"
        / "protein_summary_packet_gap_next_actions_note.json"
    )
    markdown_path = (
        repo_root
        / "docs"
        / "reports"
        / "protein_summary_packet_gap_next_actions_note.md"
    )

    library = SummaryLibrarySchema.from_dict(
        json.loads(library_path.read_text(encoding="utf-8"))
    )
    report = build_protein_summary_packet_gap_next_actions_note_report(library)
    saved_report = json.loads(report_path.read_text(encoding="utf-8"))
    markdown = render_protein_summary_packet_gap_next_actions_note_markdown(report)
    saved_markdown = markdown_path.read_text(encoding="utf-8")

    assert report == saved_report
    assert markdown == saved_markdown
    assert report["selected_accessions"] == ["P31749", "P04637", "P69905"]
    assert report["packet_delta_summary_snapshot"]["packet_level_regressed_count"] == 11
    assert report["packet_delta_summary_snapshot"]["fresh_run_not_promotable_count"] == 7
    assert report["next_data_actions"][0]["source_ref"] == "ligand:P00387"
    assert report["next_data_actions"][0]["status"] == "actionable_now_surface_reconciliation"
    assert report["next_data_actions"][1]["source_ref"] == "structure:Q9UCM0"
    assert report["next_data_actions"][3]["source_ref"] == "ligand:Q9UCM0"
    assert report["next_data_actions"][4]["source_ref"] == "ligand:P09105"
    assert report["regression_boundary"]["regression_examples"][0]["summary_id"] == "protein:P31749"
    assert "Protein Summary Packet Gap Next Actions Note" in markdown
    assert "fresh-run regressions" in markdown
    assert "Next Data Actions" in markdown
    assert "current-run-present entries" in markdown

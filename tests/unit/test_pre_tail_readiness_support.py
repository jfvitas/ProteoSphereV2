from __future__ import annotations

from pathlib import Path

from scripts.export_procurement_stale_part_audit_preview import (
    build_procurement_stale_part_audit_preview,
)
from scripts.export_scrape_execution_wave_preview import (
    build_scrape_execution_wave_preview,
)
from scripts.pre_tail_readiness_support import (
    build_external_dataset_remediation_template_preview,
    build_external_dataset_resolution_diff_preview,
    build_packet_completeness_matrix_preview,
    build_split_alignment_recheck_preview,
    materialize_pre_tail_packet_stubs,
)


def test_packet_completeness_and_stub_materialization(tmp_path: Path) -> None:
    eligibility = {
        "rows": [
            {
                "accession": "P1",
                "packet_status": "partial",
                "packet_present_modalities": ["sequence", "structure"],
                "variant_count": 1,
                "task_eligibility": {
                    "grounded_ligand_similarity_preview": {"status": "eligible_for_task"},
                    "full_packet_current_latest": {"status": "blocked_pending_acquisition"},
                },
            },
            {
                "accession": "P2",
                "packet_status": "complete",
                "packet_present_modalities": ["sequence", "structure", "ligand", "ppi"],
                "variant_count": 0,
                "task_eligibility": {
                    "grounded_ligand_similarity_preview": {"status": "library_only"},
                    "full_packet_current_latest": {"status": "eligible_for_task"},
                },
            },
        ]
    }
    balanced = {
        "selected_rows": [
            {"accession": "P1", "split": "train", "canonical_id": "protein:P1"},
            {"accession": "P2", "split": "test", "canonical_id": "protein:P2"},
        ]
    }
    packet_deficit = {
        "packets": [
            {
                "accession": "P1",
                "manifest_path": "data/packages/p1.json",
                "deficit_source_refs": ["ligand:P1", "ppi:P1"],
            },
            {
                "accession": "P2",
                "manifest_path": "data/packages/p2.json",
                "deficit_source_refs": [],
            },
        ]
    }

    matrix = build_packet_completeness_matrix_preview(eligibility, balanced, packet_deficit)
    assert matrix["summary"]["selected_accession_count"] == 2
    assert matrix["summary"]["packet_lane_counts"]["governing_ready_but_package_blocked"] == 1
    assert matrix["summary"]["packet_lane_counts"]["non_governing_materializable"] == 1

    queue = materialize_pre_tail_packet_stubs(
        output_root=tmp_path / "stubs",
        eligibility_matrix=eligibility,
        balanced_dataset_plan=balanced,
        packet_deficit_dashboard=packet_deficit,
    )
    assert queue["summary"]["selected_accession_count"] == 2
    first_stub = tmp_path / "stubs" / "P1" / "packet_stub.json"
    assert first_stub.exists()


def test_split_recheck_and_external_outputs() -> None:
    balanced = {
        "selected_rows": [
            {"accession": "P1", "split": "train", "bucket": "rich"},
            {"accession": "P2", "split": "val", "bucket": "sparse"},
        ]
    }
    split_sim = {
        "rows": [
            {"accession": "P1", "split": "train", "bucket": "rich"},
            {"accession": "P2", "split": "test", "bucket": "sparse"},
        ],
        "summary": {"package_ready": False},
    }
    recheck = build_split_alignment_recheck_preview(balanced, split_sim)
    assert recheck["summary"]["matched_accession_count"] == 1
    assert recheck["summary"]["mismatch_count"] == 1

    assessment = {
        "summary": {"overall_verdict": "usable_with_caveats"},
        "sub_audits": {"binding": "usable_with_caveats", "modality": "blocked_pending_mapping"},
    }
    resolution = {
        "summary": {
            "top_issue_categories": [
                {"issue_category": "binding"},
                {"issue_category": "modality"},
            ]
        },
        "accession_resolution_rows": [
            {
                "accession": "P1",
                "resolution_state": "blocked",
                "worst_verdict": "blocked_pending_mapping",
                "blocking_gates": ["modality"],
                "issue_categories": ["binding", "modality"],
            }
        ],
    }
    remediation = build_external_dataset_remediation_template_preview(assessment, resolution)
    assert remediation["summary"]["template_row_count"] >= 2

    diff = build_external_dataset_resolution_diff_preview(split_sim, resolution)
    assert diff["summary"]["claimed_accession_count"] == 2
    assert diff["summary"]["unresolved_or_blocked_count"] >= 1


def test_procurement_stale_part_audit_classifies_stale_residue(tmp_path: Path) -> None:
    final_path = tmp_path / "alpha" / "done.txt"
    part_path = tmp_path / "alpha" / "done.txt.part"
    final_path.parent.mkdir(parents=True)
    final_path.write_text("final", encoding="utf-8")
    part_path.write_text("stale", encoding="utf-8")

    audit = build_procurement_stale_part_audit_preview(
        {
            "rows": [
                {
                    "source_id": "alpha",
                    "filename": "done.txt",
                    "final_locations": [{"path": str(final_path).replace("\\", "/")}],
                    "in_process_locations": [{"path": str(part_path).replace("\\", "/")}],
                }
            ]
        },
        sample_seconds=0,
    )
    assert audit["summary"]["stale_residue_count"] == 1
    assert audit["rows"][0]["classification"] == "stale_residue_after_final"


def test_scrape_execution_wave_uses_pre_tail_execution_registry() -> None:
    scrape_gap = {
        "summary": {"remaining_gap_file_count": 1},
        "rows": [
            {
                "lane_id": "interpro_motif_backbone",
                "lane_label": "InterPro",
                "lane_state": "implemented",
                "source_names": ["interpro"],
                "supporting_scripts": ["scripts/export_motif_domain_site_context_preview.py"],
                "evidence_artifacts": [],
                "manual_blocker": "none",
                "why_now": "now",
            }
        ],
    }
    backlog = {
        "summary": {
            "lane_counts": {
                "active_now": 0,
                "supervisor_pending": 0,
                "overnight_catalog": 0,
            }
        }
    }
    targeted = {"rows": []}
    procurement = {"summary": {"authoritative_tail_file_count": 1}, "authoritative_tail_files": []}
    readiness = {
        "summary": {"top_scrape_targets": ["motif_active_site_enrichment"]},
        "rows": [
            {
                "target_id": "motif_active_site_enrichment",
                "status": "decision_complete_waiting_on_curated_integration",
                "candidate_sources": ["InterPro"],
                "default_ingest_status": "candidate_only_non_governing",
            }
        ],
    }
    execution = {
        "rows": [
            {
                "job_id": "motif_active_site_enrichment",
                "lane_id": "interpro_motif_backbone",
                "execution_status": "completed",
                "completed_at": "2026-04-04T00:00:00+00:00",
                "artifact_paths": ["artifacts/status/motif_domain_site_context_preview.json"],
            }
        ]
    }
    source_completion = {
        "status": "report_only",
        "string_completion_ready": False,
        "uniref_completion_ready": False,
    }

    payload = build_scrape_execution_wave_preview(
        scrape_gap,
        backlog,
        targeted,
        {},
        procurement,
        source_completion,
        readiness,
        execution,
    )

    assert payload["summary"]["executed_structured_job_count"] == 1
    assert payload["truth_boundary"]["scraping_started"] is True
    assert payload["structured_jobs"][0]["execution_status"] == "completed"

"""Tests for scrape execution wave preview."""

# ruff: noqa: E501

from __future__ import annotations

import json
from pathlib import Path

from scripts.export_scrape_execution_wave_preview import (
    build_scrape_execution_wave_preview,
    main,
    render_markdown,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_inputs(tmp_path: Path) -> dict[str, Path]:
    scrape_gap_matrix_path = tmp_path / "artifacts" / "status" / "scrape_gap_matrix_preview.json"
    overnight_queue_backlog_path = (
        tmp_path / "artifacts" / "status" / "overnight_queue_backlog_preview.json"
    )
    targeted_page_registry_path = (
        tmp_path / "artifacts" / "status" / "targeted_page_scrape_registry_preview.json"
    )
    targeted_page_execution_path = (
        tmp_path / "artifacts" / "status" / "targeted_page_scrape_execution_preview.json"
    )
    procurement_process_diagnostics_path = (
        tmp_path / "artifacts" / "status" / "procurement_process_diagnostics_preview.json"
    )
    procurement_source_completion_path = (
        tmp_path / "artifacts" / "status" / "procurement_source_completion_preview.json"
    )
    scrape_readiness_registry_path = (
        tmp_path / "artifacts" / "status" / "scrape_readiness_registry_preview.json"
    )

    _write_json(
        scrape_gap_matrix_path,
        {
            "summary": {
                "remaining_gap_file_count": 2,
                "top_gap_sources": [
                    {
                        "source_id": "uniprot",
                        "status": "partial",
                        "coverage_percent": 93.3,
                        "missing_file_count": 0,
                        "partial_file_count": 1,
                    },
                    {
                        "source_id": "string",
                        "status": "partial",
                        "coverage_percent": 96.2,
                        "missing_file_count": 0,
                        "partial_file_count": 1,
                    },
                ],
            },
            "rows": [
                {
                    "rank": 1,
                    "lane_id": "interpro_motif_backbone",
                    "lane_label": "InterPro / PROSITE / Complex Portal motif backbone",
                    "lane_state": "implemented",
                    "source_names": ["interpro", "prosite", "complex_portal"],
                    "supporting_scripts": ["execution/acquire/interpro_motif_snapshot.py"],
                    "evidence_artifacts": [
                        "artifacts/status/motif_domain_compact_preview_family.json"
                    ],
                    "manual_blocker": "none",
                    "why_now": "The motif lane already has acquisition, resolver, and compact preview surfaces.",
                    "source_status_summary": "present / present / present",
                },
                {
                    "rank": 2,
                    "lane_id": "elm_motif_backbone",
                    "lane_label": "ELM motif backbone",
                    "lane_state": "partial",
                    "source_names": ["elm"],
                    "supporting_scripts": ["execution/acquire/elm_snapshot.py"],
                    "evidence_artifacts": [
                        "artifacts/status/motif_domain_site_context_preview.json"
                    ],
                    "manual_blocker": "Local bio-agent-lab registry only; coverage is partial and degraded.",
                    "why_now": "ELM is reachable through the local registry, but the source is degraded.",
                    "source_status_summary": "partial",
                },
                {
                    "rank": 3,
                    "lane_id": "biogrid_interaction_backbone",
                    "lane_label": "BioGRID interaction backbone",
                    "lane_state": "implemented",
                    "source_names": ["biogrid"],
                    "supporting_scripts": ["execution/acquire/biogrid_snapshot.py"],
                    "evidence_artifacts": [
                        "artifacts/status/interaction_similarity_signature_preview.json"
                    ],
                    "manual_blocker": "none",
                    "why_now": "BioGRID is already feeding the interaction preview family.",
                    "source_status_summary": "present",
                },
                {
                    "rank": 4,
                    "lane_id": "intact_interaction_backbone",
                    "lane_label": "IntAct interaction backbone",
                    "lane_state": "implemented",
                    "source_names": ["intact"],
                    "supporting_scripts": ["execution/acquire/intact_snapshot.py"],
                    "evidence_artifacts": ["artifacts/status/interaction_context_preview.json"],
                    "manual_blocker": "none",
                    "why_now": "IntAct has both acquisition and cohort-slice support.",
                    "source_status_summary": "present",
                },
                {
                    "rank": 5,
                    "lane_id": "sabio_rk_kinetics_backbone",
                    "lane_label": "SABIO-RK kinetics backbone",
                    "lane_state": "partial",
                    "source_names": ["sabio_rk"],
                    "supporting_scripts": ["execution/acquire/sabio_rk_snapshot.py"],
                    "evidence_artifacts": ["artifacts/status/kinetics_enzyme_support_preview.json"],
                    "manual_blocker": "Local bio-agent-lab registry only; coverage is partial and degraded.",
                    "why_now": "SABIO-RK is usable as support, but coverage remains partial.",
                    "source_status_summary": "partial",
                },
                {
                    "rank": 6,
                    "lane_id": "rcsb_pdbe_sifts_structure_backbone",
                    "lane_label": "RCSB / PDBe / SIFTS structure backbone",
                    "lane_state": "implemented",
                    "source_names": ["rcsb_pdbe"],
                    "supporting_scripts": ["execution/acquire/rcsb_pdbe_snapshot.py"],
                    "evidence_artifacts": ["artifacts/status/pdb_enrichment_harvest_preview.json"],
                    "manual_blocker": "none",
                    "why_now": "The structure enrichment lane already has scrape registry, harvest, and validation surfaces.",
                    "source_status_summary": "present",
                },
                {
                    "rank": 7,
                    "lane_id": "bindingdb_assay_bridge_backbone",
                    "lane_label": "BindingDB assay / bridge backbone",
                    "lane_state": "implemented",
                    "source_names": ["bindingdb"],
                    "supporting_scripts": ["execution/acquire/bindingdb_snapshot.py"],
                    "evidence_artifacts": [
                        "artifacts/status/binding_measurement_registry_preview.json"
                    ],
                    "manual_blocker": "none",
                    "why_now": "BindingDB has a real acquisition lane plus bridge and measurement previews.",
                    "source_status_summary": "present",
                },
                {
                    "rank": 8,
                    "lane_id": "pdbbind_measurement_backbone",
                    "lane_label": "PDBbind measurement backbone",
                    "lane_state": "partial",
                    "source_names": ["pdbbind"],
                    "supporting_scripts": [
                        "scripts/export_binding_measurement_registry_preview.py"
                    ],
                    "evidence_artifacts": [
                        "artifacts/status/binding_measurement_registry_preview.json"
                    ],
                    "manual_blocker": "No standalone acquisition lane; local coverage is degraded and fingerprint drift is noted.",
                    "why_now": "PDBbind is consumed by the measurement registry, but it still lacks a separate acquisition lane.",
                    "source_status_summary": "present",
                },
                {
                    "rank": 9,
                    "lane_id": "string_interaction_backbone",
                    "lane_label": "STRING interaction backbone",
                    "lane_state": "missing",
                    "source_names": ["string"],
                    "supporting_scripts": [
                        "scripts/export_string_interaction_materialization_plan_preview.py"
                    ],
                    "evidence_artifacts": ["artifacts/status/procurement_status_board.json"],
                    "manual_blocker": "Broad mirror tail is still partial; interaction plan remains report-only.",
                    "why_now": "STRING has planning and preview surfaces, but the acquisition lane is not fully governing.",
                    "source_status_summary": "missing",
                },
            ],
        },
    )
    _write_json(
        overnight_queue_backlog_path,
        {
            "summary": {
                "lane_counts": {"active_now": 2, "supervisor_pending": 2, "overnight_catalog": 22},
                "observed_active_source_keys": ["uniprot", "string"],
            }
        },
    )
    _write_json(
        targeted_page_registry_path,
        {
            "rows": [
                {
                    "accession": "P04637",
                    "target_family": "elm_motif_context",
                    "candidate_pages": [
                        "https://elm.eu.org/",
                        "https://rest.uniprot.org/uniprotkb/P04637.json",
                    ],
                    "default_ingest_status": "candidate_only_non_governing",
                    "page_scraping_started": False,
                },
                {
                    "accession": "P31749",
                    "target_family": "elm_motif_context",
                    "candidate_pages": [
                        "https://elm.eu.org/",
                        "https://rest.uniprot.org/uniprotkb/P31749.json",
                    ],
                    "default_ingest_status": "candidate_only_non_governing",
                    "page_scraping_started": False,
                },
            ]
        },
    )
    _write_json(
        targeted_page_execution_path,
        {
            "rows": [
                {
                    "accession": "P04637",
                    "target_family": "elm_motif_context",
                    "execution_status": "captured_candidate_only_payloads",
                    "page_scraping_started": True,
                    "payload_capture_started": True,
                    "captured_payload_count": 2,
                    "generated_at": "2026-04-04T17:00:00+00:00",
                },
                {
                    "accession": "P31749",
                    "target_family": "elm_motif_context",
                    "execution_status": "captured_candidate_only_payloads",
                    "page_scraping_started": True,
                    "payload_capture_started": True,
                    "captured_payload_count": 1,
                    "generated_at": "2026-04-04T17:05:00+00:00",
                },
            ]
        },
    )
    _write_json(
        procurement_process_diagnostics_path,
        {
            "summary": {
                "authoritative_tail_file_count": 1,
                "raw_process_table_active_count": 8,
                "raw_process_table_duplicate_count": 3,
            },
            "authoritative_tail_files": [
                {"source_id": "uniprot", "filename": "uniref100.xml.gz"},
            ],
        },
    )
    _write_json(
        procurement_source_completion_path,
        {
            "status": "report_only",
            "string_completion_status": "complete",
            "uniprot_completion_status": "partial",
            "string_completion_ready": True,
            "uniref_completion_ready": False,
        },
    )
    _write_json(
        scrape_readiness_registry_path,
        {
            "summary": {
                "top_scrape_targets": [
                    "motif_active_site_enrichment",
                    "interaction_context_enrichment",
                    "kinetics_pathway_metadata_enrichment",
                ]
            },
            "rows": [
                {
                    "target_id": "motif_active_site_enrichment",
                    "status": "decision_complete_waiting_on_curated_integration",
                    "why_now": "Motif and active-site breadth still has high scientific payoff.",
                    "candidate_sources": ["PROSITE", "ELM", "InterPro complements"],
                    "provenance_tags": ["scraped_support", "source_quality_tagged"],
                    "default_ingest_status": "candidate_only_non_governing",
                },
                {
                    "target_id": "interaction_context_enrichment",
                    "status": "decision_complete_waiting_on_string_tail",
                    "why_now": "Interaction context enrichment can be prepared now, but it must stay non-governing until the remaining STRING mirror tail is complete.",
                    "candidate_sources": [
                        "BioGRID complements",
                        "IntAct complements",
                        "literature context",
                    ],
                    "provenance_tags": ["scraped_support", "curated_backfill_only"],
                    "default_ingest_status": "candidate_only_non_governing",
                },
                {
                    "target_id": "kinetics_pathway_metadata_enrichment",
                    "status": "decision_complete_waiting_on_curated_integration",
                    "why_now": "Kinetics support is bundle-safe but still compact and non-governing.",
                    "candidate_sources": ["SABIO-RK complements", "pathway narrative metadata"],
                    "provenance_tags": ["scraped_support", "explanatory_metadata_only"],
                    "default_ingest_status": "support-only",
                },
            ],
        },
    )
    return {
        "gap_matrix": scrape_gap_matrix_path,
        "backlog": overnight_queue_backlog_path,
        "page_registry": targeted_page_registry_path,
        "page_execution": targeted_page_execution_path,
        "procurement": procurement_process_diagnostics_path,
        "source_completion": procurement_source_completion_path,
        "readiness": scrape_readiness_registry_path,
    }


def test_build_scrape_execution_wave_preview_ranks_structured_page_and_tail_blocked_jobs(
    tmp_path: Path,
) -> None:
    paths = _write_inputs(tmp_path)
    payload = build_scrape_execution_wave_preview(
        json.loads(paths["gap_matrix"].read_text(encoding="utf-8")),
        json.loads(paths["backlog"].read_text(encoding="utf-8")),
        json.loads(paths["page_registry"].read_text(encoding="utf-8")),
        json.loads(paths["page_execution"].read_text(encoding="utf-8")),
        json.loads(paths["procurement"].read_text(encoding="utf-8")),
        json.loads(paths["source_completion"].read_text(encoding="utf-8")),
        json.loads(paths["readiness"].read_text(encoding="utf-8")),
    )

    assert payload["status"] == "report_only"
    assert payload["summary"]["structured_job_count"] == 8
    assert payload["summary"]["page_job_count"] == 2
    assert payload["summary"]["captured_page_job_count"] == 2
    assert payload["summary"]["tail_blocked_job_count"] == 0
    assert payload["structured_jobs"][0]["job_id"] == "motif_active_site_enrichment"
    assert payload["structured_jobs"][0]["lane_id"] == "interpro_motif_backbone"
    assert {
        row["lane_id"]
        for row in payload["structured_jobs"]
        if row["job_id"] == "interaction_context_enrichment"
    } == {
        "biogrid_interaction_backbone",
        "intact_interaction_backbone",
    }
    assert [row["accession"] for row in payload["page_jobs"]] == ["P04637", "P31749"]
    assert payload["page_jobs"][0]["execution_status"] == "captured_candidate_only_payloads"
    assert payload["page_jobs"][0]["captured_payload_count"] == 2
    assert payload["tail_blocked_jobs"] == []
    assert payload["truth_boundary"]["report_only"] is True
    assert payload["truth_boundary"]["launch_blocked_for_active_jobs"] is True
    assert payload["truth_boundary"]["page_scraping_started"] is True
    assert "Structured Jobs" in render_markdown(payload)
    assert "Tail-Blocked Jobs" in render_markdown(payload)


def test_main_writes_scrape_execution_wave_outputs(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)
    output_json = tmp_path / "artifacts" / "status" / "scrape_execution_wave_preview.json"
    output_md = tmp_path / "docs" / "reports" / "scrape_execution_wave_preview.md"

    exit_code = main(
        [
            "--scrape-gap-matrix",
            str(paths["gap_matrix"]),
            "--overnight-queue-backlog",
            str(paths["backlog"]),
            "--targeted-page-scrape-registry",
            str(paths["page_registry"]),
            "--targeted-page-scrape-execution",
            str(paths["page_execution"]),
            "--procurement-process-diagnostics",
            str(paths["procurement"]),
            "--procurement-source-completion",
            str(paths["source_completion"]),
            "--scrape-readiness-registry",
            str(paths["readiness"]),
            "--string-materialization",
            str(tmp_path / "artifacts" / "status" / "missing_string_interaction_materialization_preview.json"),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
        ]
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["artifact_id"] == "scrape_execution_wave_preview"
    assert payload["summary"]["structured_job_count"] == 8
    assert output_md.exists()
    assert "Scrape Execution Wave Preview" in output_md.read_text(encoding="utf-8")

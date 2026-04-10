from __future__ import annotations

import json
from pathlib import Path

from execution.materialization.ligand_packet_enricher import (
    LigandPacketEnrichmentEntry,
    LigandPacketEnrichmentResult,
    enrich_ligand_packets,
    enrich_ligand_packets_from_artifacts,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RESULTS_DIR = REPO_ROOT / "runs" / "real_data_benchmark" / "full_results"


def _packet(
    accession: str,
    *,
    split: str,
    bucket: str,
    evidence_mode: str,
    lane_depth: int,
    thin_coverage: bool,
    mixed_evidence: bool,
    source_lanes: list[str],
    present_modalities: list[str],
    missing_modalities: list[str],
    coverage_notes: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    provenance_pointers: list[str] | None = None,
    planning_index_ref: str | None = None,
    row_index: int = 1,
) -> dict[str, object]:
    return {
        "accession": accession,
        "canonical_id": f"protein:{accession}",
        "split": split,
        "bucket": bucket,
        "evidence_mode": evidence_mode,
        "lane_depth": lane_depth,
        "thin_coverage": thin_coverage,
        "mixed_evidence": mixed_evidence,
        "source_lanes": source_lanes,
        "present_modalities": present_modalities,
        "missing_modalities": missing_modalities,
        "coverage_notes": coverage_notes or [],
        "evidence_refs": evidence_refs or [],
        "provenance_pointers": provenance_pointers or [],
        "planning_index_ref": planning_index_ref or f"planning/{accession}",
        "leakage_key": accession,
        "runtime_surface": (
            "local prototype runtime with surrogate modality embeddings and "
            "identity-safe resume continuity"
        ),
        "row_index": row_index,
        "validation_class": evidence_mode,
    }


def _coverage_row(
    accession: str,
    *,
    source_lanes: list[str],
    coverage_notes: list[str] | None = None,
    evidence_refs: list[str] | None = None,
) -> dict[str, object]:
    return {
        "accession": accession,
        "source_lanes": source_lanes,
        "coverage_notes": coverage_notes or [],
        "evidence_refs": evidence_refs or [],
    }


def test_enrich_ligand_packets_distinguishes_thin_and_structure_linked_states() -> None:
    audit_payload = {
        "benchmark_task": "P18-T003",
        "results_dir": "runs/real_data_benchmark/full_results",
        "selected_accession_count": 3,
        "packets": [
            _packet(
                "P31749",
                split="train",
                bucket="rich_coverage",
                evidence_mode="direct_live_smoke",
                lane_depth=1,
                thin_coverage=True,
                mixed_evidence=False,
                source_lanes=["BindingDB"],
                present_modalities=["ligand"],
                missing_modalities=["sequence", "structure", "ppi"],
                coverage_notes=["single-lane coverage"],
                evidence_refs=["docs/reports/bindingdb_live_smoke_2026_03_22.md"],
                provenance_pointers=["planning/P31749"],
                row_index=4,
            ),
            _packet(
                "P69905",
                split="train",
                bucket="rich_coverage",
                evidence_mode="direct_live_smoke",
                lane_depth=5,
                thin_coverage=False,
                mixed_evidence=False,
                source_lanes=[
                    "UniProt",
                    "InterPro",
                    "Reactome",
                    "AlphaFold DB",
                    "Evolutionary / MSA",
                ],
                present_modalities=["sequence", "structure"],
                missing_modalities=["ligand", "ppi"],
                evidence_refs=["docs/reports/live_source_smoke_2026_03_22.md"],
                provenance_pointers=["planning/P69905"],
                row_index=1,
            ),
            _packet(
                "P00001",
                split="test",
                bucket="sparse_or_control",
                evidence_mode="live_verified_accession",
                lane_depth=1,
                thin_coverage=True,
                mixed_evidence=False,
                source_lanes=["UniProt"],
                present_modalities=["sequence"],
                missing_modalities=["structure", "ligand", "ppi"],
                evidence_refs=["docs/reports/evolutionary_live_smoke_2026_03_22.md"],
                provenance_pointers=["planning/P00001"],
                row_index=9,
            ),
        ],
    }
    coverage_payload = {
        "generated_at": "2026-03-22T00:00:00Z",
        "coverage_matrix": [
            _coverage_row(
                "P31749",
                source_lanes=["BindingDB"],
                coverage_notes=["single-lane coverage"],
                evidence_refs=["docs/reports/bindingdb_live_smoke_2026_03_22.md"],
            ),
            _coverage_row(
                "P69905",
                source_lanes=[
                    "UniProt",
                    "InterPro",
                    "Reactome",
                    "AlphaFold DB",
                    "Evolutionary / MSA",
                ],
                evidence_refs=["docs/reports/live_source_smoke_2026_03_22.md"],
            ),
            _coverage_row(
                "P00001",
                source_lanes=["UniProt"],
                coverage_notes=["single-lane coverage"],
                evidence_refs=["docs/reports/evolutionary_live_smoke_2026_03_22.md"],
            ),
        ],
    }

    result = enrich_ligand_packets(audit_payload, coverage_payload, results_dir=RESULTS_DIR)
    by_accession = {entry.accession: entry for entry in result.packets}

    assert result.benchmark_task == "P18-T003"
    assert result.selected_accession_count == 3
    assert result.summary["packet_state_counts"]["thin"] == 1
    assert result.summary["packet_state_counts"]["structure_linked"] == 1
    assert result.summary["packet_state_counts"]["unavailable"] == 1
    assert result.summary["thin_accessions"] == ["P31749"]
    assert result.summary["structure_linked_accessions"] == ["P69905"]

    p31749 = by_accession["P31749"]
    assert p31749.packet_state == "thin"
    assert p31749.chemical_context_state == "present"
    assert p31749.assay_context_state == "present"
    assert p31749.structure_context_state == "missing"
    assert any(issue.kind == "thin_coverage" for issue in p31749.issues)

    p69905 = by_accession["P69905"]
    assert p69905.packet_state == "structure_linked"
    assert p69905.chemical_context_state == "missing"
    assert p69905.assay_context_state == "missing"
    assert p69905.structure_context_state == "present"
    assert any(issue.kind == "missing_ligand_context" for issue in p69905.issues)
    assert any(issue.kind == "missing_assay_context" for issue in p69905.issues)

    p00001 = by_accession["P00001"]
    assert p00001.packet_state == "unavailable"
    assert p00001.issues[0].kind == "unavailable_accession"

    payload = json.loads(json.dumps(result.to_dict()))
    round_tripped = LigandPacketEnrichmentResult.from_dict(payload)
    assert round_tripped.packets[0].packet_state in {
        "thin",
        "structure_linked",
        "unavailable",
    }


def test_enrich_ligand_packets_uses_real_benchmark_artifacts() -> None:
    result = enrich_ligand_packets_from_artifacts(results_dir=RESULTS_DIR)

    assert result.benchmark_task == "P6-T013"
    assert result.selected_accession_count == 12
    assert result.packet_count == 12
    assert result.summary["packet_state_counts"]["thin"] == 1
    assert result.summary["packet_state_counts"]["structure_linked"] == 1
    assert result.summary["packet_state_counts"]["unavailable"] == 10

    by_accession = {entry.accession: entry for entry in result.packets}
    assert by_accession["P31749"].packet_state == "thin"
    assert by_accession["P31749"].chemical_context_state == "present"
    assert by_accession["P69905"].packet_state == "structure_linked"
    assert by_accession["P69905"].structure_context_state == "present"
    assert by_accession["P69905"].missing_modalities == ("ligand", "ppi")
    assert "planning/P31749" in by_accession["P31749"].provenance_pointers

    assert result.source_files["training_packet_audit"].endswith("training_packet_audit.json")
    assert result.source_files["source_coverage"].endswith("source_coverage.json")
    assert result.generated_at
    assert result.generated_at.startswith("2026-03-22T")
    assert all(isinstance(entry, LigandPacketEnrichmentEntry) for entry in result.packets)

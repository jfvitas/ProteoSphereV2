from __future__ import annotations

import json
from pathlib import Path

from execution.library.weak_ppi_candidate_summary import (
    materialize_weak_ppi_candidate_summary,
    render_weak_ppi_candidate_summary_report,
    write_weak_ppi_candidate_summary_artifact,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_snapshot_row(
    path: Path,
    *,
    accession_a: str,
    accession_b: str,
    detection_method: str,
    interaction_type: str,
    publication_ids: str,
    interaction_ids: str,
    confidence: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = "\t".join(
        (
            f"uniprotkb:{accession_a}",
            f"uniprotkb:{accession_b}",
            f"intact:ALT-{accession_a}",
            f"intact:ALT-{accession_b}",
            f"psi-mi:{accession_a}(display_short)",
            f"psi-mi:{accession_b}(display_short)",
            detection_method,
            "Example et al. (2026)",
            publication_ids,
            "taxid:9606(Homo sapiens)",
            "taxid:9606(Homo sapiens)",
            interaction_type,
            'psi-mi:"MI:0469"(IntAct)',
            interaction_ids,
            confidence,
        )
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{row}\n")


def test_materialize_weak_ppi_candidate_summary_marks_weak_inclusion_and_packet_ready_blockers(
    tmp_path: Path,
) -> None:
    snapshot_root = tmp_path / "intact" / "20260323T182231Z"

    _write_json(
        snapshot_root / "P09105" / "P09105.interactor.json",
        {"accession": "P09105"},
    )
    _write_snapshot_row(
        snapshot_root / "P09105" / "P09105.psicquic.tab25.txt",
        accession_a="P09105",
        accession_b="P69905",
        detection_method='psi-mi:"MI:0397"(two hybrid array)',
        interaction_type='psi-mi:"MI:0915"(physical association)',
        publication_ids="pubmed:32296183|imex:IM-25472",
        interaction_ids="intact:EBI-1|imex:IM-1",
        confidence="intact-miscore:0.56",
    )
    _write_snapshot_row(
        snapshot_root / "P09105" / "P09105.psicquic.tab25.txt",
        accession_a="O43865",
        accession_b="P09105",
        detection_method='psi-mi:"MI:0397"(two hybrid array)',
        interaction_type='psi-mi:"MI:0915"(physical association)',
        publication_ids="pubmed:32296183|imex:IM-25472",
        interaction_ids="intact:EBI-2|imex:IM-2",
        confidence="intact-miscore:0.60",
    )
    _write_snapshot_row(
        snapshot_root / "P09105" / "P09105.psicquic.tab25.txt",
        accession_a="Q96HA8",
        accession_b="P09105",
        detection_method='psi-mi:"MI:0397"(two hybrid array)',
        interaction_type='psi-mi:"MI:0915"(physical association)',
        publication_ids="pubmed:32296183|imex:IM-25472",
        interaction_ids="intact:EBI-3|imex:IM-3",
        confidence="intact-miscore:0.56",
    )
    _write_snapshot_row(
        snapshot_root / "P09105" / "P09105.psicquic.tab25.txt",
        accession_a="O43865",
        accession_b="P09105",
        detection_method='psi-mi:"MI:0397"(two hybrid array)',
        interaction_type='psi-mi:"MI:0915"(physical association)',
        publication_ids="pubmed:32296183|imex:IM-25472",
        interaction_ids="intact:EBI-4|imex:IM-4",
        confidence="intact-miscore:0.60",
    )
    _write_snapshot_row(
        snapshot_root / "P09105" / "P09105.psicquic.tab25.txt",
        accession_a="Q8TAC1",
        accession_b="P09105",
        detection_method='psi-mi:"MI:0397"(two hybrid array)',
        interaction_type='psi-mi:"MI:0915"(physical association)',
        publication_ids="pubmed:32296183|imex:IM-25472",
        interaction_ids="intact:EBI-5|imex:IM-5",
        confidence="intact-miscore:0.78",
    )

    _write_json(
        snapshot_root / "Q2TAC2" / "Q2TAC2.interactor.json",
        {"accession": "Q2TAC2"},
    )
    _write_snapshot_row(
        snapshot_root / "Q2TAC2" / "Q2TAC2.psicquic.tab25.txt",
        accession_a="Q2TAC2",
        accession_b="Q2TAC2",
        detection_method='psi-mi:"MI:0397"(two hybrid array)',
        interaction_type='psi-mi:"MI:0915"(physical association)',
        publication_ids="imex:IM-23318|pubmed:25416956",
        interaction_ids="intact:EBI-10|imex:IM-10",
        confidence="intact-miscore:0.37",
    )
    _write_snapshot_row(
        snapshot_root / "Q2TAC2" / "Q2TAC2.psicquic.tab25.txt",
        accession_a="Q9NRI5",
        accession_b="Q2TAC2",
        detection_method='psi-mi:"MI:0399"(two hybrid fragment pooling approach)',
        interaction_type='psi-mi:"MI:0915"(physical association)',
        publication_ids="pubmed:31413325|imex:IM-26801",
        interaction_ids="intact:EBI-11|imex:IM-11",
        confidence="intact-miscore:0.37",
    )
    _write_snapshot_row(
        snapshot_root / "Q2TAC2" / "Q2TAC2.psicquic.tab25.txt",
        accession_a="Q9UBD0",
        accession_b="Q2TAC2",
        detection_method='psi-mi:"MI:0007"(anti tag coimmunoprecipitation)',
        interaction_type='psi-mi:"MI:0914"(association)',
        publication_ids="pubmed:25036637|imex:IM-22301",
        interaction_ids="intact:EBI-12|imex:IM-12",
        confidence="intact-miscore:0.35",
    )
    _write_snapshot_row(
        snapshot_root / "Q2TAC2" / "Q2TAC2.psicquic.tab25.txt",
        accession_a="Q13451",
        accession_b="Q2TAC2",
        detection_method='psi-mi:"MI:0729"(luminescence based mammalian interactome mapping)',
        interaction_type='psi-mi:"MI:0915"(physical association)',
        publication_ids="pubmed:25036637|imex:IM-22301",
        interaction_ids="intact:EBI-13|imex:IM-13",
        confidence="intact-miscore:0.40",
    )
    _write_snapshot_row(
        snapshot_root / "Q2TAC2" / "Q2TAC2.psicquic.tab25.txt",
        accession_a="P18615",
        accession_b="Q2TAC2",
        detection_method='psi-mi:"MI:1356"(validated two hybrid)',
        interaction_type='psi-mi:"MI:0915"(physical association)',
        publication_ids="pubmed:25416956|imex:IM-23318",
        interaction_ids="intact:EBI-14|imex:IM-14",
        confidence="intact-miscore:0.56",
    )

    artifact = materialize_weak_ppi_candidate_summary(
        accessions=("P09105", "Q2TAC2"),
        raw_root=snapshot_root.parent,
    )

    payload = artifact.to_dict()
    assert payload["source_name"] == "IntAct"
    assert payload["truth_boundary"]["eligible_for_summary_library_inclusion"] is True
    assert payload["truth_boundary"]["eligible_for_strong_curated_packet_ready_ppi"] is False
    assert payload["decision_counts"]["accession_count"] == 2
    assert payload["decision_counts"]["summary_library_inclusion_count"] == 2
    assert payload["decision_counts"]["strong_curated_packet_ready_ppi_count"] == 0

    by_accession = {entry["accession"]: entry for entry in payload["accession_entries"]}
    p09105 = by_accession["P09105"]
    q2tac2 = by_accession["Q2TAC2"]

    assert p09105["suitable_for_summary_library_inclusion"] is True
    assert p09105["confidence_tier"] == "weak"
    assert p09105["confidence_subtier"] == "non_direct"
    assert p09105["summary_library_classification"] == "weak_non_direct_summary_candidate"
    assert p09105["evidence_counts"]["total_rows"] == 5
    assert p09105["evidence_counts"]["nonself_rows"] == 5
    assert p09105["evidence_counts"]["self_rows"] == 0
    assert p09105["evidence_counts"]["unique_pair_rows"] == 4
    assert p09105["evidence_counts"]["duplicate_nonself_rows"] == 1
    assert p09105["evidence_characterization"]["methods"] == [
        'psi-mi:"MI:0397"(two hybrid array)'
    ]
    assert p09105["strong_curated_packet_ready_ppi"] is False
    assert "no_direct_binary_confirmation" in p09105["packet_ready_blockers"]
    assert "duplicate non-self row(s) repeat existing pair evidence" in " ".join(
        p09105["decision_notes"]
    )

    assert q2tac2["suitable_for_summary_library_inclusion"] is True
    assert q2tac2["confidence_tier"] == "weak"
    assert q2tac2["confidence_subtier"] == "noisy"
    assert q2tac2["summary_library_classification"] == "weak_noisy_summary_candidate"
    assert q2tac2["evidence_counts"]["total_rows"] == 5
    assert q2tac2["evidence_counts"]["nonself_rows"] == 4
    assert q2tac2["evidence_counts"]["self_rows"] == 1
    assert q2tac2["evidence_counts"]["unique_pair_rows"] == 4
    assert q2tac2["evidence_characterization"]["direct_binary_supported"] is False
    assert q2tac2["strong_curated_packet_ready_ppi"] is False
    assert "self_rows_must_be_excluded_from_pair_summaries" in q2tac2[
        "packet_ready_blockers"
    ]
    assert "heterogeneous_assay_methods" in q2tac2["packet_ready_blockers"]
    assert "self row(s) must be excluded" in " ".join(q2tac2["decision_notes"])

    report = render_weak_ppi_candidate_summary_report(artifact)
    assert "Weak PPI Candidate Summary Decision" in report
    assert "P09105" in report
    assert "Q2TAC2" in report
    assert "Strong curated packet-ready PPI allowed: `False`" in report

    output_path = tmp_path / "artifacts" / "status" / "decision.json"
    report_path = tmp_path / "docs" / "reports" / "decision.md"
    write_weak_ppi_candidate_summary_artifact(
        artifact,
        output_path=output_path,
        report_path=report_path,
    )
    assert output_path.exists()
    assert report_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8"))["artifact_id"] == (
        "p27_weak_ppi_summary_decision_p09105_q2tac2"
    )

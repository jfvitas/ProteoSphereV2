from __future__ import annotations

from core.library.summary_record import ProteinSummaryRecord, SummaryRecordContext, SummaryReference
from execution.library.family_motif_consensus import build_family_motif_consensus


def _protein_record(
    summary_id: str,
    protein_ref: str,
    *,
    motif_references: tuple[SummaryReference, ...] = (),
    domain_references: tuple[SummaryReference, ...] = (),
) -> ProteinSummaryRecord:
    return ProteinSummaryRecord(
        summary_id=summary_id,
        protein_ref=protein_ref,
        context=SummaryRecordContext(
            motif_references=motif_references,
            domain_references=domain_references,
        ),
    )


def test_family_motif_consensus_builds_conservative_consensus_entries() -> None:
    motif = SummaryReference(
        reference_kind="motif",
        namespace="InterPro",
        identifier="IPR000001",
        label="Helix motif",
        join_status="joined",
        source_name="InterPro",
        evidence_refs=("ipr:IPR000001",),
    )
    domain = SummaryReference(
        reference_kind="domain",
        namespace="Pfam",
        identifier="PF00001",
        label="Example domain",
        join_status="joined",
        source_name="Pfam",
        evidence_refs=("pfam:PF00001",),
    )

    consensus = build_family_motif_consensus(
        (
            _protein_record(
                "protein:P1",
                "protein:P1",
                motif_references=(motif,),
                domain_references=(domain,),
            ),
            _protein_record(
                "protein:P2",
                "protein:P2",
                motif_references=(motif,),
                domain_references=(domain,),
            ),
        ),
        group_id="family:example",
    )

    assert consensus.group_id == "family:example"
    assert consensus.motif_state == "consensus"
    assert consensus.domain_state == "consensus"
    assert consensus.overall_state == "consensus"
    assert consensus.motif_entries[0].support_count == 2
    assert consensus.motif_entries[0].support_ratio == 1.0
    assert consensus.domain_entries[0].consensus_state == "consensus"


def test_family_motif_consensus_marks_mixed_motif_evidence_explicitly() -> None:
    joined_motif = SummaryReference(
        reference_kind="motif",
        namespace="InterPro",
        identifier="IPR100000",
        label="Shared motif",
        join_status="joined",
        source_name="InterPro",
    )
    candidate_motif = SummaryReference(
        reference_kind="motif",
        namespace="InterPro",
        identifier="IPR100000",
        label="Shared motif",
        join_status="candidate",
        source_name="InterPro",
    )

    consensus = build_family_motif_consensus(
        (
            _protein_record("protein:P1", "protein:P1", motif_references=(joined_motif,)),
            _protein_record("protein:P2", "protein:P2", motif_references=(candidate_motif,)),
        ),
    )

    assert consensus.motif_state == "mixed"
    assert consensus.overall_state == "mixed"
    assert consensus.domain_state == "empty"
    assert "mixed_consensus_requires_trace_review" in consensus.notes
    entry = consensus.motif_entries[0]
    assert entry.consensus_state == "mixed"
    assert "contains_non_joined_evidence" in entry.notes
    assert set(entry.join_statuses) == {"joined", "candidate"}


def test_family_motif_consensus_preserves_empty_state_when_no_references_exist() -> None:
    consensus = build_family_motif_consensus(
        (
            _protein_record("protein:P1", "protein:P1"),
            _protein_record("protein:P2", "protein:P2"),
        ),
        group_id="family:empty",
    )

    assert consensus.group_id == "family:empty"
    assert consensus.motif_entries == ()
    assert consensus.domain_entries == ()
    assert consensus.motif_state == "empty"
    assert consensus.domain_state == "empty"
    assert consensus.overall_state == "empty"
    assert "motif_consensus_empty" in consensus.notes
    assert "domain_consensus_empty" in consensus.notes

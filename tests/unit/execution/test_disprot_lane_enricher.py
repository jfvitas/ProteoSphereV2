from __future__ import annotations

from execution.acquire.disprot_candidate_probe import (
    DisProtCandidateProbeManifest,
    DisProtCandidateProbeRecord,
    DisProtCandidateProbeResult,
)
from execution.materialization.disprot_lane_enricher import (
    build_disprot_lane_enrichment,
)


def _probe_result() -> DisProtCandidateProbeResult:
    manifest = DisProtCandidateProbeManifest(
        accessions=("P04637", "P31749", "Q9NZD4", "P69905"),
    )
    records = (
        DisProtCandidateProbeRecord(
            accession="P04637",
            probe_url="https://disprot.org/api/search?acc=P04637",
            status="positive_hit",
            returned_record_count=1,
            matched_record_count=1,
            returned_accessions=("P04637",),
            matched_accessions=("P04637",),
            returned_disprot_ids=("DP00086",),
            matched_disprot_ids=("DP00086",),
            returned_records=({"acc": "P04637", "disprot_id": "DP00086"},),
            matched_records=({"acc": "P04637", "disprot_id": "DP00086"},),
        ),
        DisProtCandidateProbeRecord(
            accession="P31749",
            probe_url="https://disprot.org/api/search?acc=P31749",
            status="positive_hit",
            returned_record_count=1,
            matched_record_count=1,
            returned_accessions=("P31749",),
            matched_accessions=("P31749",),
            returned_disprot_ids=("DP03300",),
            matched_disprot_ids=("DP03300",),
            returned_records=({"acc": "P31749", "disprot_id": "DP03300"},),
            matched_records=({"acc": "P31749", "disprot_id": "DP03300"},),
        ),
        DisProtCandidateProbeRecord(
            accession="Q9NZD4",
            probe_url="https://disprot.org/api/search?acc=Q9NZD4",
            status="positive_hit",
            returned_record_count=1,
            matched_record_count=1,
            returned_accessions=("Q9NZD4",),
            matched_accessions=("Q9NZD4",),
            returned_disprot_ids=("DP03619",),
            matched_disprot_ids=("DP03619",),
            returned_records=({"acc": "Q9NZD4", "disprot_id": "DP03619"},),
            matched_records=({"acc": "Q9NZD4", "disprot_id": "DP03619"},),
        ),
        DisProtCandidateProbeRecord(
            accession="P69905",
            probe_url="https://disprot.org/api/search?acc=P69905",
            status="reachable_empty",
            returned_record_count=0,
            matched_record_count=0,
            returned_accessions=(),
            matched_accessions=(),
            returned_disprot_ids=(),
            matched_disprot_ids=(),
            returned_records=(),
            matched_records=(),
        ),
    )
    return DisProtCandidateProbeResult(manifest=manifest, records=records)


def test_build_disprot_lane_enrichment_preserves_positive_empty_and_unresolved_states() -> None:
    result = build_disprot_lane_enrichment(
        ["P04637", "P31749", "Q9NZD4", "P69905", "Q2TAC2"],
        probe_result=_probe_result(),
    )

    assert result.cohort_accessions == (
        "P04637",
        "P31749",
        "Q9NZD4",
        "P69905",
        "Q2TAC2",
    )
    assert result.positive_accessions == ("P04637", "P31749", "Q9NZD4")
    assert result.reachable_empty_accessions == ("P69905",)
    assert result.unresolved_accessions == ("P69905", "Q2TAC2")
    assert result.blocked_accessions == ()

    assert tuple(lane.lane_state for lane in result.packet_lanes) == (
        "positive_hit",
        "positive_hit",
        "positive_hit",
        "unresolved",
        "unresolved",
    )
    assert result.packet_lanes[0].lane_depth == 1
    assert result.packet_lanes[0].disprot_ids == ("DP00086",)
    assert result.packet_lanes[1].disprot_ids == ("DP03300",)
    assert result.packet_lanes[2].disprot_ids == ("DP03619",)
    assert result.packet_lanes[3].lane_depth == 0
    assert result.packet_lanes[3].disprot_ids == ()
    assert result.packet_lanes[3].notes == ("reachable but empty accession probe",)
    assert result.packet_lanes[4].lane_state == "unresolved"
    assert result.packet_lanes[4].lane_depth == 0
    assert result.packet_lanes[4].disprot_ids == ()
    assert "no positive DisProt lane" in result.packet_lanes[4].notes[0]

    summary = result.summary
    assert summary["cohort_accession_count"] == 5
    assert summary["lane_count"] == 5
    assert summary["positive_count"] == 3
    assert summary["reachable_empty_count"] == 1
    assert summary["unresolved_count"] == 2
    assert summary["blocked_count"] == 0
    assert len(result.to_dict()["packet_lanes"]) == 5


def test_build_disprot_lane_enrichment_falls_back_to_current_positive_defaults() -> None:
    result = build_disprot_lane_enrichment(["P04637", "Q2TAC2"])

    assert result.positive_accessions == ("P04637",)
    assert result.unresolved_accessions == ("Q2TAC2",)
    assert result.packet_lanes[0].lane_state == "positive_hit"
    assert result.packet_lanes[0].disprot_ids == ("DP00086",)
    assert result.packet_lanes[0].notes == (
        "integrated from the current DisProt-positive cohort set",
    )
    assert result.packet_lanes[1].lane_state == "unresolved"
    assert result.packet_lanes[1].lane_depth == 0


def test_build_disprot_lane_enrichment_preserves_blocked_state_explicitly() -> None:
    manifest = DisProtCandidateProbeManifest(accessions=("P04637",))
    probe_result = DisProtCandidateProbeResult(
        manifest=manifest,
        records=(
            DisProtCandidateProbeRecord(
                accession="P04637",
                probe_url="https://disprot.org/api/search?acc=P04637",
                status="blocked",
                blocker_reason="DisProt request failed for P04637: network down",
            ),
        ),
    )

    result = build_disprot_lane_enrichment(["P04637"], probe_result=probe_result)

    assert result.blocked_accessions == ("P04637",)
    assert result.packet_lanes[0].lane_state == "blocked"
    assert result.packet_lanes[0].blocker_reason == (
        "DisProt request failed for P04637: network down"
    )
    assert result.packet_lanes[0].lane_depth == 0

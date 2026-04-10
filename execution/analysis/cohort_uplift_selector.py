from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CohortUpliftCandidate:
    accession: str
    canonical_id: str
    split: str
    judgment: str
    evidence_mode: str
    validation_class: str
    lane_depth: int
    mixed_evidence: bool
    thin_coverage: bool
    present_modalities: tuple[str, ...]
    missing_modalities: tuple[str, ...]
    source_lanes: tuple[str, ...]
    planning_index_ref: str
    priority_class: str
    priority_score: int
    rationale: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "accession": self.accession,
            "canonical_id": self.canonical_id,
            "split": self.split,
            "judgment": self.judgment,
            "evidence_mode": self.evidence_mode,
            "validation_class": self.validation_class,
            "lane_depth": self.lane_depth,
            "mixed_evidence": self.mixed_evidence,
            "thin_coverage": self.thin_coverage,
            "present_modalities": list(self.present_modalities),
            "missing_modalities": list(self.missing_modalities),
            "source_lanes": list(self.source_lanes),
            "planning_index_ref": self.planning_index_ref,
            "priority_class": self.priority_class,
            "priority_score": self.priority_score,
            "rationale": list(self.rationale),
        }


@dataclass(frozen=True, slots=True)
class CohortUpliftSelection:
    candidates: tuple[CohortUpliftCandidate, ...]

    @property
    def top_accessions(self) -> tuple[str, ...]:
        return tuple(candidate.accession for candidate in self.candidates)

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_count": len(self.candidates),
            "top_accessions": list(self.top_accessions),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _build_packet_lookup(packet_audit_payload: dict) -> dict[str, dict]:
    packets = packet_audit_payload.get("packets", ())
    lookup: dict[str, dict] = {}
    for packet in packets:
        accession = str(packet.get("accession", "")).strip()
        if accession:
            lookup[accession] = packet
    return lookup


def _split_score(split: str) -> int:
    if split == "train":
        return 3
    if split == "val":
        return 1
    if split == "test":
        return 0
    return -1


def _priority_details(review: dict, packet: dict | None) -> tuple[str, int, tuple[str, ...]]:
    accession = str(review.get("accession", "")).strip()
    split = str(review.get("split", "")).strip().casefold()
    judgment = str(review.get("judgment", "")).strip().casefold()
    evidence_mode = str(review.get("evidence_mode", "")).strip()
    validation_class = str(review.get("validation_class", "")).strip()
    lane_depth = int(review.get("lane_depth", 0) or 0)
    mixed_evidence = bool(review.get("mixed_evidence", False))
    thin_coverage = bool(review.get("thin_coverage", False))

    notes: list[str] = []
    score = lane_depth * 4

    if mixed_evidence:
        score += 120
        priority_class = "mixed_upgrade"
        notes.append("mixed or probe-backed evidence should be upgraded first")
    elif judgment == "useful" and not thin_coverage:
        score -= 100
        priority_class = "reference_anchor"
        notes.append("already-strong anchor should stay as the cohort reference")
    elif evidence_mode == "direct_live_smoke" and thin_coverage:
        score += 80
        priority_class = "single_lane_direct_anchor"
        notes.append("direct live single-lane row has strong multimodal upside")
    elif validation_class == "snapshot_backed" and split == "train":
        score += 55
        priority_class = "accession_clean_train"
        notes.append("accession-clean train row can absorb more depth without ambiguity")
    elif validation_class == "snapshot_backed":
        score += 25
        priority_class = "control_snapshot"
        notes.append("snapshot-backed control row is worth deepening after train rows")
    elif validation_class == "verified_accession":
        score += 10
        priority_class = "verified_control"
        notes.append("verified accession remains a later control-style uplift target")
    else:
        score += 15
        priority_class = "general_uplift"
        notes.append("row is eligible for a later uplift pass")

    score += _split_score(split) * 5

    if packet is not None:
        missing_modalities = tuple(packet.get("missing_modalities", ()))
        present_modalities = tuple(packet.get("present_modalities", ()))
        if "ppi" in missing_modalities and mixed_evidence:
            notes.append("needs direct curated PPI to replace the current weak lane")
        if "structure" in missing_modalities and evidence_mode == "direct_live_smoke":
            notes.append("would benefit from structure bridge depth")
        if "ligand" in missing_modalities and accession == "P69905":
            notes.append("reference anchor is still partial and should not be overpromoted")
        if present_modalities:
            notes.append("present modalities: " + ", ".join(present_modalities))

    return priority_class, score, tuple(notes)


def build_cohort_uplift_selection(
    usefulness_review_payload: dict,
    training_packet_audit_payload: dict,
) -> CohortUpliftSelection:
    reviews = usefulness_review_payload.get("example_reviews", ())
    packet_lookup = _build_packet_lookup(training_packet_audit_payload)
    candidates: list[CohortUpliftCandidate] = []

    for review in reviews:
        accession = str(review.get("accession", "")).strip()
        if not accession:
            continue
        packet = packet_lookup.get(accession)
        priority_class, priority_score, rationale = _priority_details(review, packet)
        candidates.append(
            CohortUpliftCandidate(
                accession=accession,
                canonical_id=str(review.get("canonical_id", "")).strip(),
                split=str(review.get("split", "")).strip(),
                judgment=str(review.get("judgment", "")).strip(),
                evidence_mode=str(review.get("evidence_mode", "")).strip(),
                validation_class=str(review.get("validation_class", "")).strip(),
                lane_depth=int(review.get("lane_depth", 0) or 0),
                mixed_evidence=bool(review.get("mixed_evidence", False)),
                thin_coverage=bool(review.get("thin_coverage", False)),
                present_modalities=tuple(packet.get("present_modalities", ())) if packet else (),
                missing_modalities=tuple(packet.get("missing_modalities", ())) if packet else (),
                source_lanes=tuple(review.get("source_lanes", ())),
                planning_index_ref=str(packet.get("planning_index_ref", "")).strip()
                if packet
                else "",
                priority_class=priority_class,
                priority_score=priority_score,
                rationale=rationale,
            )
        )

    ordered = tuple(
        sorted(
            candidates,
            key=lambda candidate: (
                -candidate.priority_score,
                candidate.accession,
            ),
        )
    )
    return CohortUpliftSelection(candidates=ordered)


def build_cohort_uplift_selection_from_artifacts(
    usefulness_review_path: str | Path,
    training_packet_audit_path: str | Path,
) -> CohortUpliftSelection:
    return build_cohort_uplift_selection(
        usefulness_review_payload=_load_json(usefulness_review_path),
        training_packet_audit_payload=_load_json(training_packet_audit_path),
    )


__all__ = [
    "CohortUpliftCandidate",
    "CohortUpliftSelection",
    "build_cohort_uplift_selection",
    "build_cohort_uplift_selection_from_artifacts",
]

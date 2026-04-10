from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from execution.analysis.cohort_uplift_selector import build_cohort_uplift_selection

DEFAULT_RESULTS_DIR = Path("runs/real_data_benchmark/full_results")
DEFAULT_LIVE_INPUTS_PATH = Path("runs/real_data_benchmark/results/live_inputs.json")
DEFAULT_PROBE_MATRIX_PATH = Path("artifacts/status/p13_missing_source_probe_matrix.json")
DEFAULT_WAVE_ID = "release-ligand-wave:v1"

ReleaseLigandLaneClass = Literal[
    "assay_linked",
    "structure_linked",
    "held_sparse_gap",
]
ReleaseLigandLaneProfile = Literal["sparse", "deep"]
ReleaseLigandCandidateStatus = Literal["ranked", "held", "unresolved"]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Sequence):
        return tuple(values)
    return (values,)


def _clean_text_tuple(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _lookup_by_accession(
    payload: Mapping[str, Any],
    *keys: str,
) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for key in keys or ("example_reviews",):
        items = payload.get(key)
        if items is None:
            continue
        for item in _iter_values(items):
            if not isinstance(item, Mapping):
                continue
            accession = _clean_text(item.get("accession"))
            if accession:
                lookup[accession.casefold()] = dict(item)
        if lookup:
            break
    return lookup


def _probe_lookup(payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for item in _iter_values(payload.get("entries") or ()):
        if not isinstance(item, Mapping):
            continue
        source_name = _clean_text(item.get("source_name"))
        if source_name:
            lookup[source_name.casefold()] = dict(item)
    return lookup


def _pair_structure_refs(live_inputs_payload: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    refs: dict[str, set[str]] = {}
    summary_library = live_inputs_payload.get("summary_library")
    if not isinstance(summary_library, Mapping):
        return {}
    for record in _iter_values(summary_library.get("records") or ()):
        if not isinstance(record, Mapping):
            continue
        if _clean_text(record.get("record_type")) != "protein_protein":
            continue
        interaction_refs = tuple(
            ref
            for ref in _clean_text_tuple(record.get("interaction_refs") or ())
            if len(ref) == 4 and ref.isalnum()
        )
        if not interaction_refs:
            continue
        protein_refs = (
            _clean_text(record.get("protein_a_ref")),
            _clean_text(record.get("protein_b_ref")),
        )
        for protein_ref in protein_refs:
            if not protein_ref.startswith("protein:"):
                continue
            accession = protein_ref.split(":", 1)[1].strip()
            if not accession:
                continue
            refs.setdefault(accession.casefold(), set()).update(interaction_refs)
    return {
        accession: tuple(sorted(values))
        for accession, values in refs.items()
    }


def _source_probe_notes(
    probe_lookup: Mapping[str, Mapping[str, Any]],
    *,
    source_name: str,
) -> tuple[str, ...]:
    entry = probe_lookup.get(source_name.casefold())
    if not entry:
        return ()
    notes: list[str] = []
    probe_state = _clean_text(entry.get("probe_state"))
    verdict = _clean_text(entry.get("verdict"))
    next_step = _clean_text(entry.get("next_step"))
    if source_name.casefold() == "sabio-rk" and probe_state == "reachable_no_target_data":
        notes.append("SABIO-RK returned no target data for this anchor")
    if source_name.casefold() == "rcsb/pdbe bridge" and probe_state == "structured_response":
        notes.append("RCSB/PDBe bridge returned structured response")
    if verdict:
        notes.append(f"{source_name} probe verdict={verdict}")
    if next_step:
        notes.append(next_step)
    return tuple(notes)


def _evidence_bonus(evidence_mode: str) -> int:
    normalized = _clean_text(evidence_mode).casefold()
    if normalized == "direct_live_smoke":
        return 10
    if normalized == "live_summary_library_probe":
        return 5
    if normalized == "in_tree_live_snapshot":
        return 3
    if normalized == "live_verified_accession":
        return 1
    return 0


def _lane_profile(lane_depth: int, thin_coverage: bool) -> ReleaseLigandLaneProfile:
    if lane_depth >= 2 and not thin_coverage:
        return "deep"
    return "sparse"


def _classify_candidate(
    *,
    accession: str,
    present_modalities: tuple[str, ...],
    source_lanes: tuple[str, ...],
    pair_structure_refs: tuple[str, ...],
) -> ReleaseLigandLaneClass:
    lower_source_lanes = {lane.casefold() for lane in source_lanes}
    if "ligand" in {mod.casefold() for mod in present_modalities}:
        return "assay_linked"
    if lower_source_lanes.intersection(
        {
            "bindingdb",
            "sabio-rk",
        }
    ):
        return "assay_linked"
    if lower_source_lanes.intersection(
        {
            "alphafold db",
            "rcsb/pdbe bridge",
            "protein-protein summary library",
            "biolip",
            "pdbbind",
            "structures_rcsb",
            "raw_rcsb",
        }
    ):
        return "structure_linked"
    if pair_structure_refs:
        return "structure_linked"
    return "held_sparse_gap"


def _kind_bonus(kind: ReleaseLigandLaneClass) -> int:
    if kind == "assay_linked":
        return 300
    if kind == "structure_linked":
        return 250
    return 0


@dataclass(frozen=True, slots=True)
class ReleaseLigandWaveCandidate:
    accession: str
    canonical_id: str
    split: str
    bucket: str
    selector_rank: int | None = None
    selector_priority_class: str = ""
    selector_priority_score: int | None = None
    lane_depth: int = 0
    thin_coverage: bool = False
    mixed_evidence: bool = False
    evidence_mode: str = ""
    validation_class: str = ""
    present_modalities: tuple[str, ...] = ()
    missing_modalities: tuple[str, ...] = ()
    source_lanes: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    ligand_lane_class: ReleaseLigandLaneClass = "held_sparse_gap"
    lane_profile: ReleaseLigandLaneProfile = "sparse"
    structure_refs: tuple[str, ...] = ()
    probe_notes: tuple[str, ...] = ()
    rank_score: int = 0
    rank_reason: tuple[str, ...] = ()
    status: ReleaseLigandCandidateStatus = "held"
    unresolved_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "accession", _clean_text(self.accession).upper())
        object.__setattr__(self, "canonical_id", _clean_text(self.canonical_id))
        object.__setattr__(self, "split", _clean_text(self.split))
        object.__setattr__(self, "bucket", _clean_text(self.bucket))
        object.__setattr__(
            self,
            "selector_priority_class",
            _clean_text(self.selector_priority_class),
        )
        object.__setattr__(
            self,
            "selector_priority_score",
            None if self.selector_priority_score is None else int(self.selector_priority_score),
        )
        object.__setattr__(self, "lane_depth", int(self.lane_depth))
        object.__setattr__(self, "thin_coverage", bool(self.thin_coverage))
        object.__setattr__(self, "mixed_evidence", bool(self.mixed_evidence))
        object.__setattr__(self, "evidence_mode", _clean_text(self.evidence_mode))
        object.__setattr__(self, "validation_class", _clean_text(self.validation_class))
        object.__setattr__(self, "present_modalities", _clean_text_tuple(self.present_modalities))
        object.__setattr__(self, "missing_modalities", _clean_text_tuple(self.missing_modalities))
        object.__setattr__(self, "source_lanes", _clean_text_tuple(self.source_lanes))
        object.__setattr__(self, "evidence_refs", _clean_text_tuple(self.evidence_refs))
        object.__setattr__(self, "structure_refs", _clean_text_tuple(self.structure_refs))
        object.__setattr__(self, "probe_notes", _clean_text_tuple(self.probe_notes))
        object.__setattr__(self, "rank_score", int(self.rank_score))
        object.__setattr__(self, "rank_reason", _clean_text_tuple(self.rank_reason))
        object.__setattr__(self, "unresolved_reason", _clean_text(self.unresolved_reason) or None)
        if self.ligand_lane_class not in {
            "assay_linked",
            "structure_linked",
            "held_sparse_gap",
        }:
            raise ValueError(
                "ligand_lane_class must be assay_linked, structure_linked, or held_sparse_gap"
            )
        if self.lane_profile not in {"sparse", "deep"}:
            raise ValueError("lane_profile must be sparse or deep")
        if self.status not in {"ranked", "held", "unresolved"}:
            raise ValueError("status must be ranked, held, or unresolved")
        if not self.accession:
            raise ValueError("accession must not be empty")
        if not self.canonical_id:
            raise ValueError("canonical_id must not be empty")
        if self.status == "unresolved" and not self.unresolved_reason:
            raise ValueError("unresolved candidates require an unresolved_reason")

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "canonical_id": self.canonical_id,
            "split": self.split,
            "bucket": self.bucket,
            "selector_rank": self.selector_rank,
            "selector_priority_class": self.selector_priority_class,
            "selector_priority_score": self.selector_priority_score,
            "lane_depth": self.lane_depth,
            "thin_coverage": self.thin_coverage,
            "mixed_evidence": self.mixed_evidence,
            "evidence_mode": self.evidence_mode,
            "validation_class": self.validation_class,
            "present_modalities": list(self.present_modalities),
            "missing_modalities": list(self.missing_modalities),
            "source_lanes": list(self.source_lanes),
            "evidence_refs": list(self.evidence_refs),
            "ligand_lane_class": self.ligand_lane_class,
            "lane_profile": self.lane_profile,
            "structure_refs": list(self.structure_refs),
            "probe_notes": list(self.probe_notes),
            "rank_score": self.rank_score,
            "rank_reason": list(self.rank_reason),
            "status": self.status,
            "unresolved_reason": self.unresolved_reason,
        }


@dataclass(frozen=True, slots=True)
class ReleaseLigandWavePlan:
    wave_id: str
    candidates: tuple[ReleaseLigandWaveCandidate, ...]
    notes: tuple[str, ...] = ()
    probe_summary: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "wave_id", _clean_text(self.wave_id))
        object.__setattr__(self, "candidates", tuple(self.candidates))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        object.__setattr__(self, "probe_summary", dict(self.probe_summary))
        if not self.wave_id:
            raise ValueError("wave_id must not be empty")

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    @property
    def assay_linked_count(self) -> int:
        return sum(
            1 for candidate in self.candidates if candidate.ligand_lane_class == "assay_linked"
        )

    @property
    def structure_linked_count(self) -> int:
        return sum(
            1 for candidate in self.candidates if candidate.ligand_lane_class == "structure_linked"
        )

    @property
    def held_sparse_gap_count(self) -> int:
        return sum(
            1 for candidate in self.candidates if candidate.ligand_lane_class == "held_sparse_gap"
        )

    @property
    def deep_lane_count(self) -> int:
        return sum(1 for candidate in self.candidates if candidate.lane_profile == "deep")

    @property
    def sparse_lane_count(self) -> int:
        return sum(1 for candidate in self.candidates if candidate.lane_profile == "sparse")

    @property
    def top_accessions(self) -> tuple[str, ...]:
        return tuple(candidate.accession for candidate in self.candidates)

    def to_dict(self) -> dict[str, Any]:
        return {
            "wave_id": self.wave_id,
            "candidate_count": self.candidate_count,
            "assay_linked_count": self.assay_linked_count,
            "structure_linked_count": self.structure_linked_count,
            "held_sparse_gap_count": self.held_sparse_gap_count,
            "deep_lane_count": self.deep_lane_count,
            "sparse_lane_count": self.sparse_lane_count,
            "top_accessions": list(self.top_accessions),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "notes": list(self.notes),
            "probe_summary": dict(self.probe_summary),
        }


def _build_selection_lookup(
    usefulness_review_payload: Mapping[str, Any],
    training_packet_audit_payload: Mapping[str, Any],
) -> dict[str, tuple[Any, int]]:
    selection = build_cohort_uplift_selection(
        usefulness_review_payload=dict(usefulness_review_payload),
        training_packet_audit_payload=dict(training_packet_audit_payload),
    )
    return {
        candidate.accession.casefold(): (candidate, index)
        for index, candidate in enumerate(selection.candidates, start=1)
    }


def _score_candidate(
    *,
    selector_score: int,
    ligand_lane_class: ReleaseLigandLaneClass,
    lane_profile: ReleaseLigandLaneProfile,
    evidence_mode: str,
    mixed_evidence: bool,
    thin_coverage: bool,
) -> tuple[int, tuple[str, ...]]:
    score = selector_score + _kind_bonus(ligand_lane_class)
    reasons = [f"selector_score={selector_score}", f"ligand_lane_class={ligand_lane_class}"]
    if lane_profile == "deep":
        score += 25
        reasons.append("lane_profile=deep")
    else:
        reasons.append("lane_profile=sparse")
    score += _evidence_bonus(evidence_mode)
    reasons.append(f"evidence_mode={_clean_text(evidence_mode)}")
    if mixed_evidence:
        score -= 20
        reasons.append("mixed_evidence=True")
    else:
        reasons.append("mixed_evidence=False")
    if thin_coverage:
        score -= 5
        reasons.append("thin_coverage=True")
    else:
        reasons.append("thin_coverage=False")
    return score, tuple(reasons)


def build_release_ligand_wave_plan(
    usefulness_review_payload: Mapping[str, Any],
    training_packet_audit_payload: Mapping[str, Any],
    source_coverage_payload: Mapping[str, Any],
    live_probe_matrix_payload: Mapping[str, Any] | None = None,
    live_inputs_payload: Mapping[str, Any] | None = None,
    *,
    wave_id: str = DEFAULT_WAVE_ID,
    notes: Sequence[str] = (),
) -> ReleaseLigandWavePlan:
    selection_lookup = _build_selection_lookup(
        usefulness_review_payload,
        training_packet_audit_payload,
    )
    coverage_lookup = _lookup_by_accession(
        source_coverage_payload,
        "coverage_matrix",
        "example_reviews",
    )
    pair_structure_refs = (
        _pair_structure_refs(live_inputs_payload) if live_inputs_payload is not None else {}
    )
    probe_lookup = _probe_lookup(live_probe_matrix_payload or {})
    candidates: list[ReleaseLigandWaveCandidate] = []

    for accession_key, coverage in coverage_lookup.items():
        selector_entry = selection_lookup.get(accession_key)
        selector = selector_entry[0] if selector_entry else None
        selector_rank = selector_entry[1] if selector_entry else None
        accession = _clean_text(coverage.get("accession"))
        present_modalities = tuple(coverage.get("source_lanes") or ())
        source_lanes = tuple(coverage.get("source_lanes") or ())
        structure_refs = pair_structure_refs.get(accession_key, ())
        ligand_lane_class = _classify_candidate(
            accession=accession,
            present_modalities=present_modalities,
            source_lanes=source_lanes,
            pair_structure_refs=structure_refs,
        )
        lane_profile = _lane_profile(
            int(coverage.get("lane_depth", 0) or 0),
            bool(coverage.get("thin_coverage", False)),
        )
        probe_notes: list[str] = []
        if ligand_lane_class == "assay_linked":
            probe_notes.extend(_source_probe_notes(probe_lookup, source_name="SABIO-RK"))
        if ligand_lane_class == "structure_linked":
            probe_notes.extend(_source_probe_notes(probe_lookup, source_name="RCSB/PDBe bridge"))
        score, rank_reason = _score_candidate(
            selector_score=int(getattr(selector, "priority_score", 0) or 0),
            ligand_lane_class=ligand_lane_class,
            lane_profile=lane_profile,
            evidence_mode=_clean_text(coverage.get("evidence_mode")),
            mixed_evidence=bool(coverage.get("mixed_evidence", False)),
            thin_coverage=bool(coverage.get("thin_coverage", False)),
        )
        status: ReleaseLigandCandidateStatus
        unresolved_reason: str | None
        if ligand_lane_class == "held_sparse_gap":
            status = "held"
            unresolved_reason = (
                "no assay or structure-linked ligand signal in current benchmark artifacts"
            )
        else:
            status = "ranked"
            unresolved_reason = None
        candidates.append(
            ReleaseLigandWaveCandidate(
                accession=accession,
                canonical_id=_clean_text(coverage.get("canonical_id")) or f"protein:{accession}",
                split=_clean_text(coverage.get("split")),
                bucket=_clean_text(coverage.get("bucket")),
                selector_rank=selector_rank,
                selector_priority_class=getattr(selector, "priority_class", ""),
                selector_priority_score=getattr(selector, "priority_score", None),
                lane_depth=int(coverage.get("lane_depth", 0) or 0),
                thin_coverage=bool(coverage.get("thin_coverage", False)),
                mixed_evidence=bool(coverage.get("mixed_evidence", False)),
                evidence_mode=_clean_text(coverage.get("evidence_mode")),
                validation_class=_clean_text(coverage.get("validation_class")),
                present_modalities=tuple(coverage.get("present_modalities") or ()),
                missing_modalities=tuple(coverage.get("missing_modalities") or ()),
                source_lanes=source_lanes,
                evidence_refs=tuple(coverage.get("evidence_refs") or ()),
                ligand_lane_class=ligand_lane_class,
                lane_profile=lane_profile,
                structure_refs=structure_refs,
                probe_notes=tuple(probe_notes),
                rank_score=score,
                rank_reason=rank_reason
                + (
                    f"structure_refs={','.join(structure_refs)}" if structure_refs else "",
                ),
                status=status,
                unresolved_reason=unresolved_reason,
            )
        )

    candidates = sorted(
        candidates,
        key=lambda candidate: (
            0
            if candidate.ligand_lane_class == "assay_linked"
            else 1
            if candidate.ligand_lane_class == "structure_linked"
            else 2,
            -candidate.rank_score,
            candidate.accession,
        ),
    )
    ranked_candidates: list[ReleaseLigandWaveCandidate] = []
    for index, candidate in enumerate(candidates, start=1):
        ranked_candidates.append(
            ReleaseLigandWaveCandidate(
                **{
                    **candidate.to_dict(),
                    "selector_rank": candidate.selector_rank,
                    "selector_priority_class": candidate.selector_priority_class,
                    "selector_priority_score": candidate.selector_priority_score,
                    "ligand_lane_class": candidate.ligand_lane_class,
                    "lane_profile": candidate.lane_profile,
                    "rank_score": candidate.rank_score,
                    "rank_reason": candidate.rank_reason + (f"wave_rank={index}",),
                    "status": candidate.status,
                    "unresolved_reason": candidate.unresolved_reason,
                }
            )
        )

    probe_summary = {
        "probe_matrix_sources": sorted(
            _clean_text(entry.get("source_name"))
            for entry in _iter_values((live_probe_matrix_payload or {}).get("entries") or ())
            if isinstance(entry, Mapping) and _clean_text(entry.get("source_name"))
        ),
        "structured_probe_sources": sorted(
            _clean_text(entry.get("source_name"))
            for entry in probe_lookup.values()
            if _clean_text(entry.get("probe_state")) == "structured_response"
        ),
        "empty_target_probe_sources": sorted(
            _clean_text(entry.get("source_name"))
            for entry in probe_lookup.values()
            if _clean_text(entry.get("probe_state")) == "reachable_no_target_data"
        ),
    }
    return ReleaseLigandWavePlan(
        wave_id=wave_id,
        candidates=tuple(ranked_candidates),
        notes=tuple(notes)
        + (
            "assay-linked candidates stay separate from structure-linked candidates",
            "sparse ligand gaps remain explicit instead of being upgraded by inference",
            (
                "current ranking is grounded in the cohort selector, "
                "source coverage, and live probe matrix"
            ),
        ),
        probe_summary=probe_summary,
    )


def build_release_ligand_wave_plan_from_artifacts(
    *,
    results_dir: str | Path = DEFAULT_RESULTS_DIR,
    live_inputs_path: str | Path = DEFAULT_LIVE_INPUTS_PATH,
    probe_matrix_path: str | Path = DEFAULT_PROBE_MATRIX_PATH,
    wave_id: str = DEFAULT_WAVE_ID,
    notes: Sequence[str] = (),
) -> ReleaseLigandWavePlan:
    root = Path(results_dir)
    return build_release_ligand_wave_plan(
        usefulness_review_payload=_load_json(root / "usefulness_review.json"),
        training_packet_audit_payload=_load_json(root / "training_packet_audit.json"),
        source_coverage_payload=_load_json(root / "source_coverage.json"),
        live_probe_matrix_payload=_load_json(probe_matrix_path),
        live_inputs_payload=_load_json(live_inputs_path),
        wave_id=wave_id,
        notes=notes,
    )


__all__ = [
    "DEFAULT_PROBE_MATRIX_PATH",
    "DEFAULT_LIVE_INPUTS_PATH",
    "DEFAULT_RESULTS_DIR",
    "DEFAULT_WAVE_ID",
    "ReleaseLigandCandidateStatus",
    "ReleaseLigandLaneClass",
    "ReleaseLigandLaneProfile",
    "ReleaseLigandWaveCandidate",
    "ReleaseLigandWavePlan",
    "build_release_ligand_wave_plan",
    "build_release_ligand_wave_plan_from_artifacts",
]

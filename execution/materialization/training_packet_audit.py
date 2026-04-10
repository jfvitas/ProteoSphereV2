from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

DEFAULT_RESULTS_DIR = Path("runs/real_data_benchmark/full_results")
DEFAULT_REQUESTED_MODALITIES = ("sequence", "structure", "ligand", "ppi")

AuditJudgment = Literal["useful", "weak", "blocked"]
AuditCompleteness = Literal["complete", "partial", "blocked"]

_LANE_TO_MODALITIES: dict[str, tuple[str, ...]] = {
    "UniProt": ("sequence",),
    "AlphaFold DB": ("structure",),
    "BindingDB": ("ligand",),
    "BioLiP": ("ligand",),
    "IntAct": ("ppi",),
    "protein-protein summary library": ("ppi",),
    "InterPro": ("annotation",),
    "Reactome": ("pathway",),
    "Evolutionary / MSA": ("sequence",),
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Iterable):
        return tuple(values)
    return (values,)


def _dedupe_text(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _requested_modalities(payload: Mapping[str, Any]) -> tuple[str, ...]:
    modalities = payload.get("requested_modalities") or ()
    cleaned = _dedupe_text(modalities)
    return cleaned or DEFAULT_REQUESTED_MODALITIES


def _modality_presence(
    source_lanes: Iterable[str],
    requested_modalities: Iterable[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    requested = tuple(_dedupe_text(requested_modalities))
    requested_lookup = {item.casefold(): item for item in requested}
    present_ordered: list[str] = []
    supporting_ordered: list[str] = []
    seen_present: set[str] = set()
    seen_supporting: set[str] = set()

    for lane in _dedupe_text(source_lanes):
        for modality in _LANE_TO_MODALITIES.get(lane, ()):
            key = modality.casefold()
            if key in requested_lookup:
                if key not in seen_present:
                    seen_present.add(key)
                    present_ordered.append(requested_lookup[key])
            elif key not in seen_supporting:
                seen_supporting.add(key)
                supporting_ordered.append(modality)

    return tuple(present_ordered), tuple(supporting_ordered)


def _missing_modalities(
    requested_modalities: Iterable[str],
    present_modalities: Iterable[str],
) -> tuple[str, ...]:
    requested = tuple(_dedupe_text(requested_modalities))
    present_lookup = {item.casefold() for item in _dedupe_text(present_modalities)}
    return tuple(item for item in requested if item.casefold() not in present_lookup)


def _pick_row(
    rows: Iterable[Mapping[str, Any]],
    accession: str,
) -> Mapping[str, Any] | None:
    for row in rows:
        if _clean_text(row.get("accession")) == accession:
            return row
    return None


def _checkpoint_pointers(row: Mapping[str, Any]) -> tuple[str, ...]:
    pointers: list[str] = []
    completion_state = row.get("completion_state")
    if isinstance(completion_state, Mapping):
        checkpoint = completion_state.get("checkpoint_coverage")
        if isinstance(checkpoint, Mapping):
            for key in ("first_checkpoint_index", "final_checkpoint_index"):
                value = checkpoint.get(key)
                if value is not None:
                    pointers.append(f"checkpoint_coverage.{key}={value}")

    runtime_provenance = row.get("runtime_provenance")
    if isinstance(runtime_provenance, Mapping):
        checkpoint_ref = _clean_text(runtime_provenance.get("checkpoint_ref"))
        if checkpoint_ref:
            pointers.append(checkpoint_ref)
        runtime_surface = _clean_text(runtime_provenance.get("runtime_surface"))
        if runtime_surface:
            pointers.append(runtime_surface)

    evidence_refs = row.get("evidence_refs")
    for ref in _dedupe_text(evidence_refs):
        pointers.append(ref)

    provenance_notes = _clean_text(row.get("provenance_notes"))
    if provenance_notes:
        pointers.append(provenance_notes)

    return tuple(_dedupe_text(pointers))


def _packet_judgment(
    coverage_row: Mapping[str, Any] | None,
    provenance_row: Mapping[str, Any] | None,
    *,
    present_modalities: tuple[str, ...],
    missing_modalities: tuple[str, ...],
) -> tuple[AuditJudgment, AuditCompleteness, tuple[str, ...]]:
    rationale: list[str] = []
    if coverage_row is None or provenance_row is None:
        rationale.append("missing coverage or provenance row")
        return "blocked", "blocked", tuple(rationale)

    coverage_status = _clean_text(coverage_row.get("status"))
    provenance_status = _clean_text(provenance_row.get("status"))
    if coverage_status != "resolved" or provenance_status != "resolved":
        rationale.append(
            f"row status is not resolved: coverage={coverage_status or 'missing'}, "
            f"provenance={provenance_status or 'missing'}"
        )
        return "blocked", "blocked", tuple(rationale)

    evidence_mode = _clean_text(coverage_row.get("evidence_mode"))
    lane_depth = int(coverage_row.get("lane_depth") or 0)
    mixed_evidence = bool(coverage_row.get("mixed_evidence"))
    thin_coverage = bool(coverage_row.get("thin_coverage"))
    checkpoint_visible = bool(
        (provenance_row.get("completion_state") or {})
        .get("checkpoint_coverage", {})
        .get("first_pass_visible")
    ) and bool(
        (provenance_row.get("completion_state") or {})
        .get("checkpoint_coverage", {})
        .get("resumed_visible")
    )

    if missing_modalities:
        rationale.append("requested modalities are not fully present")
    if present_modalities:
        rationale.append("present modalities: " + ", ".join(present_modalities))
    if evidence_mode:
        rationale.append(f"evidence_mode={evidence_mode}")
    rationale.append(f"lane_depth={lane_depth}")
    rationale.append(f"mixed_evidence={mixed_evidence}")
    rationale.append(f"thin_coverage={thin_coverage}")
    rationale.append(f"checkpoint_visibility={checkpoint_visible}")

    if (
        evidence_mode == "direct_live_smoke"
        and lane_depth >= 3
        and not mixed_evidence
        and not thin_coverage
        and checkpoint_visible
    ):
        rationale.insert(0, "direct live smoke with multilane coverage")
        return "useful", "partial", tuple(rationale)

    if mixed_evidence:
        rationale.insert(0, "mixed evidence should stay weak")
    elif thin_coverage or lane_depth <= 1:
        rationale.insert(0, "single-lane or thin coverage should stay weak")
    elif evidence_mode != "direct_live_smoke":
        rationale.insert(0, f"non-direct evidence mode: {evidence_mode}")
    else:
        rationale.insert(0, "coverage is resolved but not strong enough for useful")

    return "weak", "partial", tuple(rationale)


@dataclass(frozen=True, slots=True)
class TrainingPacketAuditPacket:
    accession: str
    canonical_id: str | None
    planning_index_ref: str | None
    split: str
    judgment: AuditJudgment
    completeness: AuditCompleteness
    leakage_key: str | None
    evidence_mode: str
    lane_depth: int
    source_lanes: tuple[str, ...]
    present_modalities: tuple[str, ...]
    supporting_modalities: tuple[str, ...]
    missing_modalities: tuple[str, ...]
    mixed_evidence: bool
    thin_coverage: bool
    coverage_notes: tuple[str, ...] = field(default_factory=tuple)
    provenance_pointers: tuple[str, ...] = field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    checkpoint_ref: str | None = None
    runtime_surface: str | None = None
    row_index: int | None = None
    bucket: str | None = None
    validation_class: str | None = None
    rationale: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "canonical_id": self.canonical_id,
            "planning_index_ref": self.planning_index_ref,
            "split": self.split,
            "judgment": self.judgment,
            "completeness": self.completeness,
            "leakage_key": self.leakage_key,
            "evidence_mode": self.evidence_mode,
            "lane_depth": self.lane_depth,
            "source_lanes": list(self.source_lanes),
            "present_modalities": list(self.present_modalities),
            "supporting_modalities": list(self.supporting_modalities),
            "missing_modalities": list(self.missing_modalities),
            "mixed_evidence": self.mixed_evidence,
            "thin_coverage": self.thin_coverage,
            "coverage_notes": list(self.coverage_notes),
            "provenance_pointers": list(self.provenance_pointers),
            "evidence_refs": list(self.evidence_refs),
            "checkpoint_ref": self.checkpoint_ref,
            "runtime_surface": self.runtime_surface,
            "row_index": self.row_index,
            "bucket": self.bucket,
            "validation_class": self.validation_class,
            "rationale": list(self.rationale),
        }


@dataclass(frozen=True, slots=True)
class TrainingPacketAuditResult:
    benchmark_task: str
    results_dir: str
    selected_accession_count: int
    requested_modalities: tuple[str, ...]
    packets: tuple[TrainingPacketAuditPacket, ...]
    summary: dict[str, Any]
    source_files: dict[str, str]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_task": self.benchmark_task,
            "results_dir": self.results_dir,
            "selected_accession_count": self.selected_accession_count,
            "requested_modalities": list(self.requested_modalities),
            "packets": [packet.to_dict() for packet in self.packets],
            "summary": self.summary,
            "source_files": dict(self.source_files),
            "generated_at": self.generated_at,
        }


def audit_training_packets(
    results_dir: str | Path = DEFAULT_RESULTS_DIR,
) -> TrainingPacketAuditResult:
    results_path = Path(results_dir)
    source_coverage = _load_json(results_path / "source_coverage.json")
    provenance_table = _load_json(results_path / "provenance_table.json")
    usefulness_review = _load_json(results_path / "usefulness_review.json")
    run_summary = _load_json(results_path / "run_summary.json")
    metrics_summary = _load_json(results_path / "metrics_summary.json")

    requested_modalities = _requested_modalities(run_summary)
    if requested_modalities == DEFAULT_REQUESTED_MODALITIES:
        requested_modalities = _requested_modalities(
            metrics_summary.get("checkpoint_summary", {})
            .get("resumed_run", {})
            .get("provenance", {})
        )
    coverage_rows = tuple(source_coverage.get("coverage_matrix") or ())
    usefulness_rows = tuple(
        usefulness_review.get("example_reviews") or ()
    )
    provenance_rows = tuple((provenance_table.get("cohort_summary") or {}).get("rows") or ())
    packets: list[TrainingPacketAuditPacket] = []

    for row in usefulness_rows:
        accession = _clean_text(row.get("accession"))
        if not accession:
            continue
        coverage_row = _pick_row(coverage_rows, accession)
        provenance_row = _pick_row(provenance_rows, accession) or {}
        source_lanes = tuple((coverage_row or {}).get("source_lanes") or ())
        present_modalities, supporting_modalities = _modality_presence(
            source_lanes,
            requested_modalities,
        )
        missing_modalities = _missing_modalities(requested_modalities, present_modalities)
        judgment, completeness, rationale = _packet_judgment(
            coverage_row,
            row,
            present_modalities=present_modalities,
            missing_modalities=missing_modalities,
        )
        checkpoint_ref = None
        runtime_surface = None
        runtime_provenance = row.get("runtime_provenance")
        if isinstance(runtime_provenance, Mapping):
            checkpoint_ref = _clean_text(runtime_provenance.get("checkpoint_ref")) or None
            runtime_surface = _clean_text(runtime_provenance.get("runtime_surface")) or None

        packets.append(
            TrainingPacketAuditPacket(
                accession=accession,
                canonical_id=_clean_text(provenance_row.get("canonical_id")) or None,
                planning_index_ref=_clean_text(provenance_row.get("planning_index_ref")) or None,
                split=_clean_text((coverage_row or row).get("split")),
                judgment=judgment,
                completeness=completeness,
                leakage_key=_clean_text((coverage_row or row).get("leakage_key")) or None,
                evidence_mode=_clean_text((coverage_row or row).get("evidence_mode")),
                lane_depth=int((coverage_row or row).get("lane_depth") or 0),
                source_lanes=source_lanes,
                present_modalities=present_modalities,
                supporting_modalities=supporting_modalities,
                missing_modalities=missing_modalities,
                mixed_evidence=bool((coverage_row or row).get("mixed_evidence")),
                thin_coverage=bool((coverage_row or row).get("thin_coverage")),
                coverage_notes=tuple((coverage_row or {}).get("coverage_notes") or ()),
                provenance_pointers=_dedupe_text(
                    (
                        *_checkpoint_pointers(row),
                        provenance_row.get("planning_index_ref"),
                        *(provenance_row.get("evidence_refs") or ()),
                    )
                ),
                evidence_refs=tuple((coverage_row or {}).get("evidence_refs") or ()),
                checkpoint_ref=checkpoint_ref,
                runtime_surface=runtime_surface,
                row_index=int(row.get("row_index") or (coverage_row or {}).get("row_index") or 0)
                or None,
                bucket=_clean_text((coverage_row or row).get("bucket")) or None,
                validation_class=_clean_text((coverage_row or row).get("validation_class"))
                or None,
                rationale=rationale,
            )
        )

    summary_counts = {
        "packet_count": len(packets),
        "judgment_counts": {
            "useful": sum(1 for packet in packets if packet.judgment == "useful"),
            "weak": sum(1 for packet in packets if packet.judgment == "weak"),
            "blocked": sum(1 for packet in packets if packet.judgment == "blocked"),
        },
        "completeness_counts": {
            "complete": sum(1 for packet in packets if packet.completeness == "complete"),
            "partial": sum(1 for packet in packets if packet.completeness == "partial"),
            "blocked": sum(1 for packet in packets if packet.completeness == "blocked"),
        },
        "missing_modality_counts": {
            modality: sum(1 for packet in packets if modality in packet.missing_modalities)
            for modality in requested_modalities
        },
        "useful_accessions": [
            packet.accession for packet in packets if packet.judgment == "useful"
        ],
        "weak_accessions": [packet.accession for packet in packets if packet.judgment == "weak"],
        "blocked_accessions": [
            packet.accession for packet in packets if packet.judgment == "blocked"
        ],
        "checkpoint_surface": {
            "backend": _clean_text(
                usefulness_review.get("runtime_provenance", {}).get("backend")
                if isinstance(usefulness_review.get("runtime_provenance"), Mapping)
                else ""
            ),
            "runtime_surface": _clean_text(
                usefulness_review.get("runtime_provenance", {}).get("runtime_surface")
                if isinstance(usefulness_review.get("runtime_provenance"), Mapping)
                else ""
            ),
            "selected_accession_count": int(
                usefulness_review.get("runtime_provenance", {}).get("selected_accession_count")
                if isinstance(usefulness_review.get("runtime_provenance"), Mapping)
                and usefulness_review.get("runtime_provenance", {}).get("selected_accession_count")
                is not None
                else run_summary.get("selected_accession_count")
                or 0
            ),
        },
        "metrics": {
            "example_count": len(packets),
            "lane_depth_counts": source_coverage.get("summary", {}).get("lane_depth_counts", {}),
            "evidence_mode_counts": source_coverage.get("summary", {}).get(
                "evidence_mode_counts", {}
            ),
        },
    }

    source_files = {
        "run_summary": str(results_path / "run_summary.json"),
        "source_coverage": str(results_path / "source_coverage.json"),
        "provenance_table": str(results_path / "provenance_table.json"),
        "metrics_summary": str(results_path / "metrics_summary.json"),
        "usefulness_review": str(results_path / "usefulness_review.json"),
    }

    return TrainingPacketAuditResult(
        benchmark_task=_clean_text(run_summary.get("benchmark_task"))
        or _clean_text(provenance_table.get("task_id")),
        results_dir=str(results_path),
        selected_accession_count=int(run_summary.get("selected_accession_count") or 0),
        requested_modalities=requested_modalities,
        packets=tuple(sorted(packets, key=lambda packet: packet.row_index or 0)),
        summary=summary_counts,
        source_files=source_files,
        generated_at=_clean_text(source_coverage.get("generated_at"))
        or _clean_text(provenance_table.get("generated_at")),
    )


def audit_training_packet_payload(payload: Mapping[str, Any]) -> TrainingPacketAuditResult:
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")
    packets = tuple(
        packet
        if isinstance(packet, TrainingPacketAuditPacket)
        else TrainingPacketAuditPacket(**packet)
        for packet in _iter_values(payload.get("packets") or ())
    )
    return TrainingPacketAuditResult(
        benchmark_task=_clean_text(payload.get("benchmark_task")),
        results_dir=_clean_text(payload.get("results_dir")),
        selected_accession_count=int(payload.get("selected_accession_count") or 0),
        requested_modalities=tuple(_dedupe_text(payload.get("requested_modalities") or ())),
        packets=packets,
        summary=dict(payload.get("summary") or {}),
        source_files=dict(payload.get("source_files") or {}),
        generated_at=_clean_text(payload.get("generated_at")),
    )


__all__ = [
    "AuditCompleteness",
    "AuditJudgment",
    "DEFAULT_RESULTS_DIR",
    "TrainingPacketAuditPacket",
    "TrainingPacketAuditResult",
    "audit_training_packet_payload",
    "audit_training_packets",
]

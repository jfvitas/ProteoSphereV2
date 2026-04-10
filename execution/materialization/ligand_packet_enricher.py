from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

DEFAULT_RESULTS_DIR = Path("runs/real_data_benchmark/full_results")

LigandPacketState = Literal[
    "packet_complete",
    "assay_linked",
    "structure_linked",
    "thin",
    "unavailable",
]
LigandContextState = Literal["present", "missing"]
LigandPacketIssueKind = Literal[
    "missing_ligand_context",
    "missing_assay_context",
    "missing_structure_context",
    "thin_coverage",
    "unavailable_accession",
]

_ASSAY_SOURCE_LANES = {
    "BindingDB",
    "SABIO-RK",
    "ChEMBL",
}
_CHEMICAL_SOURCE_LANES = {
    "BindingDB",
    "BioLiP",
    "ChEMBL",
    "SABIO-RK",
    "PDBbind",
}
_STRUCTURE_SOURCE_LANES = {
    "AlphaFold DB",
    "BioLiP",
    "PDBbind",
    "RCSB/PDBe bridge",
    "raw_rcsb",
    "structures_rcsb",
}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _required_text(value: Any, field_name: str) -> str:
    text = _clean_text(value)
    if not text:
        raise ValueError(f"{field_name} must be a non-empty string")
    return text


def _optional_text(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


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


def _json_ready(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError("ligand packet payload must be a JSON object")
    return dict(payload)


def _pick_row(rows: Iterable[Mapping[str, Any]], accession: str) -> Mapping[str, Any] | None:
    for row in rows:
        if _clean_text(row.get("accession")) == accession:
            return row
    return None


def _lane_state(source_lanes: Iterable[str], lane_group: set[str]) -> bool:
    return bool({lane.casefold() for lane in _dedupe_text(source_lanes)}.intersection(
        lane.casefold() for lane in lane_group
    ))


def _context_state(present: bool) -> LigandContextState:
    return "present" if present else "missing"


def _packet_state(
    *,
    chemical_present: bool,
    assay_present: bool,
    structure_present: bool,
    lane_depth: int,
    thin_coverage: bool,
    mixed_evidence: bool,
) -> LigandPacketState:
    if not (chemical_present or assay_present or structure_present):
        return "unavailable"
    if (
        chemical_present
        and assay_present
        and structure_present
        and lane_depth >= 2
        and not thin_coverage
        and not mixed_evidence
    ):
        return "packet_complete"
    if structure_present and not chemical_present and not assay_present:
        return "structure_linked"
    if chemical_present and assay_present:
        return "thin" if thin_coverage or lane_depth <= 1 else "assay_linked"
    if chemical_present or assay_present or structure_present:
        return "thin"
    return "unavailable"


def _packet_issues(
    *,
    packet_state: LigandPacketState,
    chemical_present: bool,
    assay_present: bool,
    structure_present: bool,
    thin_coverage: bool,
) -> tuple[dict[str, Any], ...]:
    issues: list[dict[str, Any]] = []
    if not (chemical_present or assay_present or structure_present):
        issues.append(
            {
                "kind": "unavailable_accession",
                "message": (
                    "benchmark artifacts do not expose ligand, assay, or structure context "
                    "for this accession"
                ),
            }
        )
        return tuple(issues)
    if not chemical_present:
        issues.append(
            {
                "kind": "missing_ligand_context",
                "message": "ligand context is not present in the current benchmark artifacts",
            }
        )
    if not assay_present:
        issues.append(
            {
                "kind": "missing_assay_context",
                "message": "assay context is not present in the current benchmark artifacts",
            }
        )
    if not structure_present:
        issues.append(
            {
                "kind": "missing_structure_context",
                "message": "structure context is not present in the current benchmark artifacts",
            }
        )
    if packet_state == "thin" or thin_coverage:
        issues.append(
            {
                "kind": "thin_coverage",
                "message": "packet remains thin and should not be treated as multimodal",
            }
        )
    return tuple(issues)


@dataclass(frozen=True, slots=True)
class LigandPacketEnrichmentIssue:
    kind: LigandPacketIssueKind
    message: str
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _clean_text(self.kind))
        object.__setattr__(self, "message", _required_text(self.message, "message"))
        object.__setattr__(self, "details", dict(self.details))
        if self.kind not in {
            "missing_ligand_context",
            "missing_assay_context",
            "missing_structure_context",
            "thin_coverage",
            "unavailable_accession",
        }:
            raise ValueError(f"unsupported issue kind: {self.kind!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "message": self.message,
            "details": _json_ready(dict(self.details)),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> LigandPacketEnrichmentIssue:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            kind=payload.get("kind") or "thin_coverage",
            message=payload.get("message") or "",
            details=payload.get("details") or payload.get("metadata") or {},
        )


@dataclass(frozen=True, slots=True)
class LigandPacketEnrichmentEntry:
    accession: str
    canonical_id: str
    split: str
    bucket: str
    packet_state: LigandPacketState
    chemical_context_state: LigandContextState
    assay_context_state: LigandContextState
    structure_context_state: LigandContextState
    lane_depth: int = 0
    thin_coverage: bool = False
    mixed_evidence: bool = False
    evidence_mode: str = ""
    validation_class: str = ""
    present_modalities: tuple[str, ...] = ()
    missing_modalities: tuple[str, ...] = ()
    source_lanes: tuple[str, ...] = ()
    coverage_notes: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    provenance_pointers: tuple[str, ...] = ()
    planning_index_ref: str | None = None
    leakage_key: str | None = None
    runtime_surface: str | None = None
    row_index: int | None = None
    issues: tuple[LigandPacketEnrichmentIssue, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "accession", _required_text(self.accession, "accession"))
        object.__setattr__(self, "canonical_id", _required_text(self.canonical_id, "canonical_id"))
        object.__setattr__(self, "split", _clean_text(self.split))
        object.__setattr__(self, "bucket", _clean_text(self.bucket))
        object.__setattr__(self, "packet_state", _clean_text(self.packet_state))
        object.__setattr__(
            self,
            "chemical_context_state",
            _clean_text(self.chemical_context_state),
        )
        object.__setattr__(self, "assay_context_state", _clean_text(self.assay_context_state))
        object.__setattr__(
            self,
            "structure_context_state",
            _clean_text(self.structure_context_state),
        )
        object.__setattr__(self, "lane_depth", int(self.lane_depth))
        object.__setattr__(self, "thin_coverage", bool(self.thin_coverage))
        object.__setattr__(self, "mixed_evidence", bool(self.mixed_evidence))
        object.__setattr__(self, "evidence_mode", _clean_text(self.evidence_mode))
        object.__setattr__(self, "validation_class", _clean_text(self.validation_class))
        object.__setattr__(self, "present_modalities", _dedupe_text(self.present_modalities))
        object.__setattr__(self, "missing_modalities", _dedupe_text(self.missing_modalities))
        object.__setattr__(self, "source_lanes", _dedupe_text(self.source_lanes))
        object.__setattr__(self, "coverage_notes", _dedupe_text(self.coverage_notes))
        object.__setattr__(self, "evidence_refs", _dedupe_text(self.evidence_refs))
        object.__setattr__(self, "provenance_pointers", _dedupe_text(self.provenance_pointers))
        object.__setattr__(self, "planning_index_ref", _optional_text(self.planning_index_ref))
        object.__setattr__(self, "leakage_key", _optional_text(self.leakage_key))
        object.__setattr__(self, "runtime_surface", _optional_text(self.runtime_surface))
        object.__setattr__(
            self,
            "row_index",
            None if self.row_index is None else int(self.row_index),
        )
        object.__setattr__(self, "issues", tuple(self.issues))
        if self.packet_state not in {
            "packet_complete",
            "assay_linked",
            "structure_linked",
            "thin",
            "unavailable",
        }:
            raise ValueError(f"unsupported packet_state: {self.packet_state!r}")
        if self.chemical_context_state not in {"present", "missing"}:
            raise ValueError("chemical_context_state must be present or missing")
        if self.assay_context_state not in {"present", "missing"}:
            raise ValueError("assay_context_state must be present or missing")
        if self.structure_context_state not in {"present", "missing"}:
            raise ValueError("structure_context_state must be present or missing")
        if not self.accession:
            raise ValueError("accession must not be empty")
        if not self.canonical_id:
            raise ValueError("canonical_id must not be empty")

    @property
    def packet_complete(self) -> bool:
        return self.packet_state == "packet_complete"

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "canonical_id": self.canonical_id,
            "split": self.split,
            "bucket": self.bucket,
            "packet_state": self.packet_state,
            "chemical_context_state": self.chemical_context_state,
            "assay_context_state": self.assay_context_state,
            "structure_context_state": self.structure_context_state,
            "lane_depth": self.lane_depth,
            "thin_coverage": self.thin_coverage,
            "mixed_evidence": self.mixed_evidence,
            "evidence_mode": self.evidence_mode,
            "validation_class": self.validation_class,
            "present_modalities": list(self.present_modalities),
            "missing_modalities": list(self.missing_modalities),
            "source_lanes": list(self.source_lanes),
            "coverage_notes": list(self.coverage_notes),
            "evidence_refs": list(self.evidence_refs),
            "provenance_pointers": list(self.provenance_pointers),
            "planning_index_ref": self.planning_index_ref,
            "leakage_key": self.leakage_key,
            "runtime_surface": self.runtime_surface,
            "row_index": self.row_index,
            "issues": [issue.to_dict() for issue in self.issues],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> LigandPacketEnrichmentEntry:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            accession=payload.get("accession") or "",
            canonical_id=payload.get("canonical_id") or "",
            split=payload.get("split") or "",
            bucket=payload.get("bucket") or "",
            packet_state=payload.get("packet_state") or "unavailable",
            chemical_context_state=payload.get("chemical_context_state") or "missing",
            assay_context_state=payload.get("assay_context_state") or "missing",
            structure_context_state=payload.get("structure_context_state") or "missing",
            lane_depth=int(payload.get("lane_depth") or 0),
            thin_coverage=bool(payload.get("thin_coverage")),
            mixed_evidence=bool(payload.get("mixed_evidence")),
            evidence_mode=payload.get("evidence_mode") or "",
            validation_class=payload.get("validation_class") or "",
            present_modalities=payload.get("present_modalities") or (),
            missing_modalities=payload.get("missing_modalities") or (),
            source_lanes=payload.get("source_lanes") or (),
            coverage_notes=payload.get("coverage_notes") or (),
            evidence_refs=payload.get("evidence_refs") or (),
            provenance_pointers=payload.get("provenance_pointers") or (),
            planning_index_ref=payload.get("planning_index_ref"),
            leakage_key=payload.get("leakage_key"),
            runtime_surface=payload.get("runtime_surface"),
            row_index=payload.get("row_index"),
            issues=tuple(
                issue
                if isinstance(issue, LigandPacketEnrichmentIssue)
                else LigandPacketEnrichmentIssue.from_dict(issue)
                for issue in _iter_values(payload.get("issues") or ())
            ),
        )


@dataclass(frozen=True, slots=True)
class LigandPacketEnrichmentResult:
    benchmark_task: str
    results_dir: str
    selected_accession_count: int
    packets: tuple[LigandPacketEnrichmentEntry, ...]
    summary: dict[str, Any]
    source_files: dict[str, str]
    generated_at: str

    @property
    def packet_count(self) -> int:
        return len(self.packets)

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_task": self.benchmark_task,
            "results_dir": self.results_dir,
            "selected_accession_count": self.selected_accession_count,
            "packets": [packet.to_dict() for packet in self.packets],
            "summary": self.summary,
            "source_files": dict(self.source_files),
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> LigandPacketEnrichmentResult:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            benchmark_task=_clean_text(payload.get("benchmark_task")),
            results_dir=_clean_text(payload.get("results_dir")),
            selected_accession_count=int(payload.get("selected_accession_count") or 0),
            packets=tuple(
                packet
                if isinstance(packet, LigandPacketEnrichmentEntry)
                else LigandPacketEnrichmentEntry.from_dict(packet)
                for packet in _iter_values(payload.get("packets") or ())
            ),
            summary=dict(payload.get("summary") or {}),
            source_files=dict(payload.get("source_files") or {}),
            generated_at=_clean_text(payload.get("generated_at")),
        )


def _context_flags(row: Mapping[str, Any]) -> tuple[bool, bool, bool]:
    source_lanes = _dedupe_text(row.get("source_lanes") or ())
    present_modalities = {
        mod.casefold() for mod in _dedupe_text(row.get("present_modalities") or ())
    }
    chemical_present = bool(present_modalities.intersection({"ligand"})) or _lane_state(
        source_lanes,
        _CHEMICAL_SOURCE_LANES,
    )
    assay_present = _lane_state(source_lanes, _ASSAY_SOURCE_LANES)
    structure_present = bool(present_modalities.intersection({"structure"})) or _lane_state(
        source_lanes,
        _STRUCTURE_SOURCE_LANES,
    )
    return chemical_present, assay_present, structure_present


def _provenance_pointers(
    row: Mapping[str, Any],
    coverage_row: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    pointers: list[str] = []
    for value in _iter_values(row.get("provenance_pointers") or ()):
        pointers.append(_clean_text(value))
    for value in _iter_values(row.get("evidence_refs") or ()):
        pointers.append(_clean_text(value))
    if coverage_row is not None:
        for value in _iter_values(coverage_row.get("evidence_refs") or ()):
            pointers.append(_clean_text(value))
        for value in _iter_values(coverage_row.get("coverage_notes") or ()):
            pointers.append(_clean_text(value))
    planning_ref = _clean_text(row.get("planning_index_ref"))
    if planning_ref:
        pointers.append(planning_ref)
    runtime_surface = _clean_text(row.get("runtime_surface"))
    if runtime_surface:
        pointers.append(runtime_surface)
    return _dedupe_text(pointers)


def _entry_for_packet(
    row: Mapping[str, Any],
    coverage_row: Mapping[str, Any] | None,
) -> LigandPacketEnrichmentEntry:
    chemical_present, assay_present, structure_present = _context_flags(row)
    lane_depth = int(row.get("lane_depth") or 0)
    thin_coverage = bool(row.get("thin_coverage"))
    mixed_evidence = bool(row.get("mixed_evidence"))
    packet_state = _packet_state(
        chemical_present=chemical_present,
        assay_present=assay_present,
        structure_present=structure_present,
        lane_depth=lane_depth,
        thin_coverage=thin_coverage,
        mixed_evidence=mixed_evidence,
    )
    issues = tuple(
        LigandPacketEnrichmentIssue.from_dict(item) for item in _packet_issues(
            packet_state=packet_state,
            chemical_present=chemical_present,
            assay_present=assay_present,
            structure_present=structure_present,
            thin_coverage=thin_coverage,
        )
    )
    source_lanes = tuple(row.get("source_lanes") or ())
    coverage_notes = tuple((coverage_row or row).get("coverage_notes") or ())
    evidence_refs = tuple((coverage_row or row).get("evidence_refs") or ())
    missing_modalities = tuple(row.get("missing_modalities") or ())
    present_modalities = tuple(row.get("present_modalities") or ())
    return LigandPacketEnrichmentEntry(
        accession=_clean_text(row.get("accession")),
        canonical_id=_clean_text(row.get("canonical_id")),
        split=_clean_text(row.get("split")),
        bucket=_clean_text(row.get("bucket")),
        packet_state=packet_state,
        chemical_context_state=_context_state(chemical_present),
        assay_context_state=_context_state(assay_present),
        structure_context_state=_context_state(structure_present),
        lane_depth=lane_depth,
        thin_coverage=thin_coverage,
        mixed_evidence=mixed_evidence,
        evidence_mode=_clean_text(row.get("evidence_mode")),
        validation_class=_clean_text(row.get("validation_class")),
        present_modalities=present_modalities,
        missing_modalities=missing_modalities,
        source_lanes=source_lanes,
        coverage_notes=coverage_notes,
        evidence_refs=evidence_refs,
        provenance_pointers=_provenance_pointers(row, coverage_row),
        planning_index_ref=_clean_text(row.get("planning_index_ref")) or None,
        leakage_key=_clean_text(row.get("leakage_key")) or None,
        runtime_surface=_clean_text(row.get("runtime_surface")) or None,
        row_index=int(row.get("row_index") or 0) or None,
        issues=issues,
    )


def enrich_ligand_packets(
    training_packet_audit_payload: Mapping[str, Any],
    source_coverage_payload: Mapping[str, Any],
    *,
    results_dir: str | Path = DEFAULT_RESULTS_DIR,
) -> LigandPacketEnrichmentResult:
    packets_input = tuple(training_packet_audit_payload.get("packets") or ())
    coverage_rows = tuple(source_coverage_payload.get("coverage_matrix") or ())
    coverage_lookup = {
        _clean_text(row.get("accession")).casefold(): row
        for row in coverage_rows
        if _clean_text(row.get("accession"))
    }
    entries: list[LigandPacketEnrichmentEntry] = []

    for row in packets_input:
        accession = _clean_text(row.get("accession"))
        if not accession:
            continue
        coverage_row = coverage_lookup.get(accession.casefold())
        entries.append(_entry_for_packet(row, coverage_row))

    entries = sorted(entries, key=lambda entry: (entry.row_index or 0, entry.accession))
    summary = {
        "packet_count": len(entries),
        "packet_state_counts": {
            "packet_complete": sum(
                1 for entry in entries if entry.packet_state == "packet_complete"
            ),
            "assay_linked": sum(1 for entry in entries if entry.packet_state == "assay_linked"),
            "structure_linked": sum(
                1 for entry in entries if entry.packet_state == "structure_linked"
            ),
            "thin": sum(1 for entry in entries if entry.packet_state == "thin"),
            "unavailable": sum(1 for entry in entries if entry.packet_state == "unavailable"),
        },
        "context_counts": {
            "chemical_present": sum(
                1 for entry in entries if entry.chemical_context_state == "present"
            ),
            "assay_present": sum(1 for entry in entries if entry.assay_context_state == "present"),
            "structure_present": sum(
                1 for entry in entries if entry.structure_context_state == "present"
            ),
        },
        "thin_accessions": [
            entry.accession for entry in entries if entry.packet_state == "thin"
        ],
        "structure_linked_accessions": [
            entry.accession for entry in entries if entry.packet_state == "structure_linked"
        ],
        "assay_linked_accessions": [
            entry.accession for entry in entries if entry.packet_state == "assay_linked"
        ],
        "packet_complete_accessions": [
            entry.accession for entry in entries if entry.packet_state == "packet_complete"
        ],
        "unavailable_accessions": [
            entry.accession for entry in entries if entry.packet_state == "unavailable"
        ],
    }
    source_files = {
        "training_packet_audit": str(Path(results_dir) / "training_packet_audit.json"),
        "source_coverage": str(Path(results_dir) / "source_coverage.json"),
    }
    generated_at = _clean_text(source_coverage_payload.get("generated_at")) or _clean_text(
        training_packet_audit_payload.get("generated_at")
    )
    benchmark_task = _clean_text(training_packet_audit_payload.get("benchmark_task"))
    if not benchmark_task:
        benchmark_task = _clean_text(source_coverage_payload.get("benchmark_task"))
    return LigandPacketEnrichmentResult(
        benchmark_task=benchmark_task,
        results_dir=str(results_dir),
        selected_accession_count=int(
            training_packet_audit_payload.get("selected_accession_count") or 0
        ),
        packets=tuple(entries),
        summary=summary,
        source_files=source_files,
        generated_at=generated_at,
    )


def enrich_ligand_packets_from_artifacts(
    *,
    results_dir: str | Path = DEFAULT_RESULTS_DIR,
) -> LigandPacketEnrichmentResult:
    root = Path(results_dir)
    return enrich_ligand_packets(
        training_packet_audit_payload=_load_json(root / "training_packet_audit.json"),
        source_coverage_payload=_load_json(root / "source_coverage.json"),
        results_dir=root,
    )


__all__ = [
    "DEFAULT_RESULTS_DIR",
    "LigandContextState",
    "LigandPacketEnrichmentEntry",
    "LigandPacketEnrichmentIssue",
    "LigandPacketEnrichmentResult",
    "LigandPacketIssueKind",
    "LigandPacketState",
    "enrich_ligand_packets",
    "enrich_ligand_packets_from_artifacts",
]

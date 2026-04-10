from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.intact_snapshot import (
    IntActInteractionRecord,
    IntActSnapshotResult,
    acquire_intact_snapshot,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INTACT_RAW_ROOT = ROOT / "data" / "raw" / "intact"
DEFAULT_OUTPUT_PATH = (
    ROOT / "artifacts" / "status" / "p27_weak_ppi_summary_decision_p09105_q2tac2.json"
)
DEFAULT_REPORT_PATH = (
    ROOT / "docs" / "reports" / "p27_weak_ppi_summary_decision_p09105_q2tac2.md"
)
DEFAULT_ACCESSIONS = ("P09105", "Q2TAC2")
DEFAULT_SOURCE_NAME = "IntAct"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_accessions(values: Sequence[str]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        accession = _clean_text(value).upper()
        if accession:
            ordered.setdefault(accession.casefold(), accession)
    return tuple(ordered.values())


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _timestamp_slug() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _release_date_from_snapshot_root(snapshot_root: Path) -> str | None:
    match = re.match(r"(?P<date>\d{8})T\d{6}Z$", snapshot_root.name)
    if match is None:
        return None
    stamp = match.group("date")
    return f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}"


def _resolve_snapshot_root(raw_root: Path) -> Path:
    if not raw_root.exists():
        raise FileNotFoundError(f"IntAct raw root was not found: {raw_root}")
    if any(raw_root.glob("*/*.psicquic.tab25.txt")):
        return raw_root
    candidates = sorted(
        (path for path in raw_root.iterdir() if path.is_dir()),
        key=lambda path: path.name.casefold(),
    )
    if not candidates:
        raise FileNotFoundError(
            f"IntAct raw root does not contain snapshot directories: {raw_root}"
        )
    return candidates[-1]


def _snapshot_path(snapshot_root: Path, accession: str) -> Path:
    return snapshot_root / accession / f"{accession}.psicquic.tab25.txt"


def _interactor_path(snapshot_root: Path, accession: str) -> Path:
    return snapshot_root / accession / f"{accession}.interactor.json"


def _relativize(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _build_source_manifest(
    snapshot_root: Path,
    accession: str,
    payload_path: Path,
) -> SourceReleaseManifest:
    release_version = snapshot_root.name
    release_date = _release_date_from_snapshot_root(snapshot_root) or _utc_now().date().isoformat()
    return SourceReleaseManifest(
        source_name=DEFAULT_SOURCE_NAME,
        release_version=release_version,
        release_date=release_date,
        retrieval_mode="download",
        source_locator=str(payload_path),
        local_artifact_refs=(str(payload_path),),
        provenance=(
            "raw_mirror:intact",
            f"snapshot_root:{snapshot_root}",
            f"accession:{accession}",
        ),
    )


def _load_snapshot_result(
    snapshot_root: Path,
    accession: str,
) -> tuple[IntActSnapshotResult | None, str | None]:
    payload_path = _snapshot_path(snapshot_root, accession)
    if not payload_path.exists():
        return None, f"missing IntAct payload: {payload_path}"
    manifest = _build_source_manifest(snapshot_root, accession, payload_path)
    return acquire_intact_snapshot(manifest), None


def _primary_accession(record: IntActInteractionRecord) -> tuple[str, str] | None:
    accession_a = _clean_text(record.participant_a_primary_id).upper()
    accession_b = _clean_text(record.participant_b_primary_id).upper()
    if not accession_a or not accession_b or accession_a == accession_b:
        return None
    return tuple(sorted((accession_a, accession_b)))


def _direct_binary_supported(records: Sequence[IntActInteractionRecord]) -> bool:
    direct_signals = (
        "direct interaction",
        "direct binding",
    )
    for record in records:
        haystack = " ".join(
            (
                record.interaction_type,
                record.detection_method,
                record.interaction_representation,
            )
        ).casefold()
        if any(signal in haystack for signal in direct_signals):
            return True
    return False


def _unique_text(values: Sequence[str]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(sorted(ordered.values(), key=lambda item: item.casefold()))


def _row_summary(
    accession: str,
    records: Sequence[IntActInteractionRecord],
) -> tuple[dict[str, Any], tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    focus_accession = _clean_text(accession).upper()
    total_rows = len(records)
    self_rows = 0
    nonself_rows = 0
    unique_pairs: dict[tuple[str, str], IntActInteractionRecord] = {}
    partner_accessions: dict[str, str] = {}
    interaction_types: dict[str, str] = {}
    detection_methods: dict[str, str] = {}
    confidence_values: dict[str, str] = {}

    for record in records:
        accession_pair = _primary_accession(record)
        if accession_pair is None:
            self_rows += 1
        else:
            nonself_rows += 1
            unique_pairs.setdefault(accession_pair, record)
            accession_a, accession_b = accession_pair
            if accession_a == focus_accession:
                partner = accession_b
            elif accession_b == focus_accession:
                partner = accession_a
            else:
                partner = accession_b
            if partner and partner != focus_accession:
                partner_accessions.setdefault(partner.casefold(), partner)
        interaction_types.setdefault(
            record.interaction_type.casefold(),
            _clean_text(record.interaction_type),
        )
        detection_methods.setdefault(
            record.detection_method.casefold(),
            _clean_text(record.detection_method),
        )
        for value in record.confidence_values:
            confidence_values.setdefault(_clean_text(value).casefold(), _clean_text(value))

    unique_pair_rows = len(unique_pairs)
    duplicate_nonself_rows = max(nonself_rows - unique_pair_rows, 0)
    evidence_counts = {
        "total_rows": total_rows,
        "nonself_rows": nonself_rows,
        "self_rows": self_rows,
        "unique_pair_rows": unique_pair_rows,
        "duplicate_nonself_rows": duplicate_nonself_rows,
    }
    return (
        evidence_counts,
        tuple(sorted(partner_accessions.values(), key=lambda item: item.casefold())),
        tuple(sorted(interaction_types.values(), key=lambda item: item.casefold())),
        tuple(sorted(detection_methods.values(), key=lambda item: item.casefold())),
        tuple(sorted(confidence_values.values(), key=lambda item: item.casefold())),
    )


def _classification(
    *,
    self_rows: int,
    detection_methods: Sequence[str],
    direct_binary_supported: bool,
) -> tuple[str, str]:
    if self_rows > 0 or len(_unique_text(detection_methods)) > 1:
        return "weak_noisy_summary_candidate", "noisy"
    if not direct_binary_supported:
        return "weak_non_direct_summary_candidate", "non_direct"
    return "weak_summary_candidate", "non_direct"


def _packet_ready_blockers(
    *,
    self_rows: int,
    unique_pair_rows: int,
    detection_methods: Sequence[str],
    interaction_types: Sequence[str],
    direct_binary_supported: bool,
) -> tuple[str, ...]:
    blockers: list[str] = []
    if unique_pair_rows == 0:
        blockers.append("no_nonself_pair_evidence")
    if self_rows > 0:
        blockers.append("self_rows_must_be_excluded_from_pair_summaries")
    if len(_unique_text(detection_methods)) > 1:
        blockers.append("heterogeneous_assay_methods")
    if len(_unique_text(interaction_types)) > 1:
        blockers.append("mixed_interaction_types")
    if not direct_binary_supported:
        blockers.append("no_direct_binary_confirmation")
    blockers.append("curated_assay_context_not_packet_ready")
    return tuple(dict.fromkeys(blockers))


def _entry_notes(
    *,
    accession: str,
    evidence_counts: Mapping[str, Any],
    detection_methods: Sequence[str],
    interaction_types: Sequence[str],
    direct_binary_supported: bool,
) -> tuple[str, ...]:
    notes: list[str] = []
    total_rows = evidence_counts["total_rows"]
    nonself_rows = evidence_counts["nonself_rows"]
    self_rows = evidence_counts["self_rows"]
    unique_pair_rows = evidence_counts["unique_pair_rows"]
    duplicate_nonself_rows = evidence_counts["duplicate_nonself_rows"]

    notes.append(f"{total_rows} total IntAct rows observed for {accession}")
    notes.append(f"{nonself_rows} non-self rows remain after exclusion")
    if self_rows:
        notes.append(f"{self_rows} self row(s) must be excluded from pair summaries")
    if duplicate_nonself_rows:
        notes.append(
            f"{duplicate_nonself_rows} duplicate non-self row(s) repeat existing pair evidence"
        )
    if len(_unique_text(detection_methods)) == 1:
        assay_family = ", ".join(_unique_text(detection_methods))
        notes.append(
            f"all non-self rows use the same assay family: {assay_family}"
        )
    elif detection_methods:
        notes.append(
            "assay methods are heterogeneous: " + ", ".join(_unique_text(detection_methods))
        )
    if interaction_types:
        notes.append(
            "interaction types observed: " + ", ".join(_unique_text(interaction_types))
        )
    if not direct_binary_supported:
        notes.append(
            "the rows provide curated interaction context, but not direct-binary packet-ready proof"
        )
    if unique_pair_rows:
        notes.append(f"{unique_pair_rows} unique non-self pair(s) are usable for summary inclusion")
    return tuple(notes)


def _entry_artifact_refs(snapshot_root: Path, accession: str) -> dict[str, str]:
    return {
        "interactor_json": _relativize(_interactor_path(snapshot_root, accession)),
        "psicquic_tab25": _relativize(_snapshot_path(snapshot_root, accession)),
    }


@dataclass(frozen=True, slots=True)
class WeakPPICandidateEntry:
    accession: str
    suitable_for_summary_library_inclusion: bool
    confidence_tier: str
    confidence_subtier: str
    summary_library_classification: str
    pair_summary_grade: str
    include_nonself_rows: bool
    exclude_self_rows: bool
    strong_curated_packet_ready_ppi: bool
    packet_ready_blockers: tuple[str, ...]
    evidence_counts: dict[str, Any]
    evidence_characterization: dict[str, Any]
    partner_accessions: tuple[str, ...]
    artifact_refs: dict[str, str]
    decision_notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "suitable_for_summary_library_inclusion": self.suitable_for_summary_library_inclusion,
            "confidence_tier": self.confidence_tier,
            "confidence_subtier": self.confidence_subtier,
            "summary_library_classification": self.summary_library_classification,
            "pair_summary_grade": self.pair_summary_grade,
            "include_nonself_rows": self.include_nonself_rows,
            "exclude_self_rows": self.exclude_self_rows,
            "strong_curated_packet_ready_ppi": self.strong_curated_packet_ready_ppi,
            "packet_ready_blockers": list(self.packet_ready_blockers),
            "evidence_counts": dict(self.evidence_counts),
            "evidence_characterization": dict(self.evidence_characterization),
            "partner_accessions": list(self.partner_accessions),
            "artifact_refs": dict(self.artifact_refs),
            "decision_notes": list(self.decision_notes),
        }


@dataclass(frozen=True, slots=True)
class WeakPPICandidateSummaryArtifact:
    artifact_id: str
    schema_id: str
    generated_at: str
    planning_grade_only: bool
    summary_grade_only: bool
    source_name: str
    source_snapshot: str
    scope: dict[str, Any]
    truth_boundary: dict[str, bool]
    decision_counts: dict[str, int]
    accession_entries: tuple[WeakPPICandidateEntry, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "schema_id": self.schema_id,
            "generated_at": self.generated_at,
            "planning_grade_only": self.planning_grade_only,
            "summary_grade_only": self.summary_grade_only,
            "source_name": self.source_name,
            "source_snapshot": self.source_snapshot,
            "scope": dict(self.scope),
            "truth_boundary": dict(self.truth_boundary),
            "decision_counts": dict(self.decision_counts),
            "accession_entries": [entry.to_dict() for entry in self.accession_entries],
        }


def materialize_weak_ppi_candidate_summary(
    *,
    accessions: Sequence[str] = DEFAULT_ACCESSIONS,
    raw_root: Path = DEFAULT_INTACT_RAW_ROOT,
) -> WeakPPICandidateSummaryArtifact:
    selected = _normalize_accessions(accessions)
    snapshot_root = _resolve_snapshot_root(raw_root)
    snapshot_source = _relativize(snapshot_root)

    entries: list[WeakPPICandidateEntry] = []
    total_rows = 0
    nonself_rows = 0
    self_rows = 0
    strong_packet_ready_count = 0

    for accession in selected:
        snapshot_result, missing_reason = _load_snapshot_result(snapshot_root, accession)
        if snapshot_result is None or snapshot_result.snapshot is None:
            evidence_counts = {
                "total_rows": 0,
                "nonself_rows": 0,
                "self_rows": 0,
                "unique_pair_rows": 0,
                "duplicate_nonself_rows": 0,
            }
            entry = WeakPPICandidateEntry(
                accession=accession,
                suitable_for_summary_library_inclusion=False,
                confidence_tier="weak",
                confidence_subtier="unavailable",
                summary_library_classification="weak_unavailable_summary_candidate",
                pair_summary_grade="weak",
                include_nonself_rows=False,
                exclude_self_rows=False,
                strong_curated_packet_ready_ppi=False,
                packet_ready_blockers=tuple(
                    item
                    for item in ("intact_snapshot_unavailable", missing_reason or "")
                    if item
                ),
                evidence_counts=evidence_counts,
                evidence_characterization={
                    "interaction_types": [],
                    "methods": [],
                    "direct_binary_supported": False,
                    "notes": [missing_reason or "IntAct snapshot unavailable"],
                },
                partner_accessions=(),
                artifact_refs=_entry_artifact_refs(snapshot_root, accession),
                decision_notes=(missing_reason or "IntAct snapshot unavailable",),
            )
            entries.append(entry)
            continue

        records = snapshot_result.snapshot.records
        (
            evidence_counts,
            partner_accessions,
            interaction_types,
            detection_methods,
            confidence_values,
        ) = _row_summary(accession, records)
        direct_binary_supported = _direct_binary_supported(records)
        summary_classification, confidence_subtier = _classification(
            self_rows=evidence_counts["self_rows"],
            detection_methods=detection_methods,
            direct_binary_supported=direct_binary_supported,
        )
        packet_ready_blockers = _packet_ready_blockers(
            self_rows=evidence_counts["self_rows"],
            unique_pair_rows=evidence_counts["unique_pair_rows"],
            detection_methods=detection_methods,
            interaction_types=interaction_types,
            direct_binary_supported=direct_binary_supported,
        )
        notes = _entry_notes(
            accession=accession,
            evidence_counts=evidence_counts,
            detection_methods=detection_methods,
            interaction_types=interaction_types,
            direct_binary_supported=direct_binary_supported,
        )
        suitable = evidence_counts["unique_pair_rows"] > 0
        packet_ready = False
        if packet_ready:
            strong_packet_ready_count += 1
        total_rows += evidence_counts["total_rows"]
        nonself_rows += evidence_counts["nonself_rows"]
        self_rows += evidence_counts["self_rows"]
        entries.append(
            WeakPPICandidateEntry(
                accession=accession,
                suitable_for_summary_library_inclusion=suitable,
                confidence_tier="weak",
                confidence_subtier=confidence_subtier,
                summary_library_classification=summary_classification,
                pair_summary_grade="weak",
                include_nonself_rows=suitable,
                exclude_self_rows=evidence_counts["self_rows"] > 0,
                strong_curated_packet_ready_ppi=packet_ready,
                packet_ready_blockers=packet_ready_blockers,
                evidence_counts={
                    **evidence_counts,
                    "confidence_values": list(confidence_values),
                },
                evidence_characterization={
                    "interaction_types": list(interaction_types),
                    "methods": list(detection_methods),
                    "direct_binary_supported": direct_binary_supported,
                    "notes": list(notes),
                },
                partner_accessions=partner_accessions,
                artifact_refs=_entry_artifact_refs(snapshot_root, accession),
                decision_notes=notes,
            )
        )

    artifact_id = "p27_weak_ppi_summary_decision_p09105_q2tac2"
    schema_id = "proteosphere-weak-ppi-candidate-summary-2026-03-23"
    return WeakPPICandidateSummaryArtifact(
        artifact_id=artifact_id,
        schema_id=schema_id,
        generated_at=_utc_now().isoformat().replace("+00:00", "Z"),
        planning_grade_only=True,
        summary_grade_only=True,
        source_name=DEFAULT_SOURCE_NAME,
        source_snapshot=snapshot_source,
        scope={
            "accessions": list(selected),
            "purpose": "weak_ppi_summary_decision",
        },
        truth_boundary={
            "eligible_for_summary_library_inclusion": True,
            "eligible_for_strong_curated_packet_ready_ppi": False,
            "eligible_for_direct_binary_claims": False,
            "self_rows_must_be_excluded_from_pair_summaries": True,
        },
        decision_counts={
            "accession_count": len(entries),
            "summary_library_inclusion_count": sum(
                1 for entry in entries if entry.suitable_for_summary_library_inclusion
            ),
            "strong_curated_packet_ready_ppi_count": strong_packet_ready_count,
            "total_row_count": total_rows,
            "nonself_row_count": nonself_rows,
            "self_row_count": self_rows,
        },
        accession_entries=tuple(entries),
    )


def render_weak_ppi_candidate_summary_report(
    artifact: WeakPPICandidateSummaryArtifact,
) -> str:
    payload = artifact.to_dict()
    lines = [
        "# Weak PPI Candidate Summary Decision",
        "",
        f"Date: {artifact.generated_at[:10]}",
        "",
        "## Artifact",
        "",
        f"- `artifacts/status/{artifact.artifact_id}.json`",
        f"- `docs/reports/{artifact.artifact_id}.md`",
        "",
        "## Scope",
        "",
        f"- Source: `{artifact.source_name}`",
        f"- Snapshot: `{artifact.source_snapshot}`",
        f"- Accessions: {', '.join(payload['scope']['accessions'])}",
        "",
        "## Decision Summary",
        "",
        (
            "- Summary-library inclusion allowed: "
            f"`{artifact.truth_boundary['eligible_for_summary_library_inclusion']}`"
        ),
        (
            "- Strong curated packet-ready PPI allowed: "
            f"`{artifact.truth_boundary['eligible_for_strong_curated_packet_ready_ppi']}`"
        ),
        (
            "- Direct binary claims allowed: "
            f"`{artifact.truth_boundary['eligible_for_direct_binary_claims']}`"
        ),
        (
            "- Self rows must be excluded: "
            f"`{artifact.truth_boundary['self_rows_must_be_excluded_from_pair_summaries']}`"
        ),
        "",
        "## Accessions",
        "",
    ]
    lines.extend(
        [
            (
                "| accession | include in summary library | confidence tier | "
                "classification | total / non-self / self / unique pairs | "
                "packet-ready | blockers |"
            ),
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for entry in artifact.accession_entries:
        counts = entry.evidence_counts
        lines.append(
            (
                "| {accession} | {include} | {tier} | {classification} | "
                "{total} / {nonself} / {self_rows} / {unique} | {packet_ready} | "
                "{blockers} |"
            ).format(
                accession=entry.accession,
                include=str(entry.suitable_for_summary_library_inclusion).lower(),
                tier=entry.confidence_tier,
                classification=entry.summary_library_classification,
                total=counts["total_rows"],
                nonself=counts["nonself_rows"],
                self_rows=counts["self_rows"],
                unique=counts["unique_pair_rows"],
                packet_ready=str(entry.strong_curated_packet_ready_ppi).lower(),
                blockers=", ".join(entry.packet_ready_blockers),
            )
        )

    lines.extend(
        [
            "",
            "## Entry Notes",
            "",
        ]
    )
    for entry in artifact.accession_entries:
        lines.append(f"### {entry.accession}")
        for note in entry.decision_notes:
            lines.append(f"- {note}")
        lines.append("")

    lines.extend(
        [
            "## Interpretation",
            "",
            (
                "Both accessions are suitable for summary-library inclusion at weak "
                "confidence, but neither should be promoted to strong curated "
                "packet-ready PPI evidence. `P09105` is all non-self rows yet remains "
                "assay-style, non-direct evidence with one duplicated partner pair in "
                "the slice. `Q2TAC2` is weaker still because one self row must be "
                "removed and the remaining rows span heterogeneous IntAct assay "
                "methods without direct-binary confirmation."
            ),
        ]
    )
    return "\n".join(lines)


def write_weak_ppi_candidate_summary_artifact(
    artifact: WeakPPICandidateSummaryArtifact,
    *,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact.to_dict(), indent=2),
        encoding="utf-8",
    )
    report_path.write_text(
        render_weak_ppi_candidate_summary_report(artifact),
        encoding="utf-8",
    )


__all__ = [
    "DEFAULT_ACCESSIONS",
    "DEFAULT_INTACT_RAW_ROOT",
    "DEFAULT_OUTPUT_PATH",
    "DEFAULT_REPORT_PATH",
    "WeakPPICandidateEntry",
    "WeakPPICandidateSummaryArtifact",
    "materialize_weak_ppi_candidate_summary",
    "render_weak_ppi_candidate_summary_report",
    "write_weak_ppi_candidate_summary_artifact",
]

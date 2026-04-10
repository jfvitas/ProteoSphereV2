from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

RegressionGateStatus = Literal["passed", "failed", "skipped"]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


@dataclass(frozen=True, slots=True)
class PacketReadinessMetrics:
    packet_count: int
    complete_count: int
    partial_count: int
    unresolved_count: int
    packet_deficit_count: int
    total_missing_modality_count: int
    modality_deficit_counts: Mapping[str, int]

    def to_dict(self) -> dict[str, object]:
        return {
            "packet_count": self.packet_count,
            "complete_count": self.complete_count,
            "partial_count": self.partial_count,
            "unresolved_count": self.unresolved_count,
            "packet_deficit_count": self.packet_deficit_count,
            "total_missing_modality_count": self.total_missing_modality_count,
            "modality_deficit_counts": dict(self.modality_deficit_counts),
        }


@dataclass(frozen=True, slots=True)
class PacketRegressionChange:
    accession: str
    before_status: str
    after_status: str
    before_missing_modalities: tuple[str, ...]
    after_missing_modalities: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "accession": self.accession,
            "before_status": self.before_status,
            "after_status": self.after_status,
            "before_missing_modalities": list(self.before_missing_modalities),
            "after_missing_modalities": list(self.after_missing_modalities),
        }


@dataclass(frozen=True, slots=True)
class PacketRegressionReport:
    status: RegressionGateStatus
    baseline_path: str | None
    candidate_path: str | None
    baseline_metrics: PacketReadinessMetrics | None
    candidate_metrics: PacketReadinessMetrics | None
    regressions: tuple[str, ...]
    improvements: tuple[str, ...]
    changed_packets: tuple[PacketRegressionChange, ...]
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "baseline_path": self.baseline_path,
            "candidate_path": self.candidate_path,
            "baseline_metrics": None
            if self.baseline_metrics is None
            else self.baseline_metrics.to_dict(),
            "candidate_metrics": None
            if self.candidate_metrics is None
            else self.candidate_metrics.to_dict(),
            "regressions": list(self.regressions),
            "improvements": list(self.improvements),
            "changed_packets": [change.to_dict() for change in self.changed_packets],
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class PacketBaselineSelection:
    baseline_path: str | None
    baseline_payload: Mapping[str, Any] | None
    current_latest_path: str | None
    current_latest_matches_strongest: bool
    selection_notes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "baseline_path": self.baseline_path,
            "current_latest_path": self.current_latest_path,
            "current_latest_matches_strongest": self.current_latest_matches_strongest,
            "selection_notes": list(self.selection_notes),
        }


def _normalize_packets(payload: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    if "materialization" in payload:
        materialization = payload.get("materialization")
        if isinstance(materialization, Mapping):
            packets = materialization.get("packets", ())
            if isinstance(packets, list):
                return tuple(packet for packet in packets if isinstance(packet, Mapping))
    packets = payload.get("packets", ())
    if isinstance(packets, list):
        return tuple(packet for packet in packets if isinstance(packet, Mapping))
    return ()


def packet_readiness_metrics_from_payload(
    payload: Mapping[str, Any],
) -> PacketReadinessMetrics:
    packets = _normalize_packets(payload)
    summary = payload.get("summary")
    materialization = payload.get("materialization")
    modality_counts = Counter()
    packet_deficit_count = 0
    for packet in packets:
        missing_modalities = tuple(
            sorted(
                _clean_text(modality)
                for modality in packet.get("missing_modalities", ())
                if _clean_text(modality)
            )
        )
        if missing_modalities:
            packet_deficit_count += 1
        modality_counts.update(missing_modalities)

    if isinstance(summary, Mapping):
        packet_count = int(summary.get("packet_count", len(packets)) or len(packets))
        complete_count = int(summary.get("complete_count", 0) or 0)
        partial_count = int(summary.get("partial_count", 0) or 0)
        unresolved_count = int(summary.get("unresolved_count", 0) or 0)
        packet_deficit_count = int(
            summary.get("packet_deficit_count", packet_deficit_count) or packet_deficit_count
        )
        total_missing = int(
            summary.get("total_missing_modality_count", sum(modality_counts.values()))
            or sum(modality_counts.values())
        )
        summary_modality_counts = summary.get("missing_modality_counts", {})
        if isinstance(summary_modality_counts, Mapping):
            modality_counts = Counter(
                {
                    _clean_text(key): int(value or 0)
                    for key, value in summary_modality_counts.items()
                    if _clean_text(key)
                }
            )
    elif isinstance(materialization, Mapping):
        packet_count = int(materialization.get("packet_count", len(packets)) or len(packets))
        complete_count = int(materialization.get("complete_count", 0) or 0)
        partial_count = int(materialization.get("partial_count", 0) or 0)
        unresolved_count = int(materialization.get("unresolved_count", 0) or 0)
        total_missing = sum(modality_counts.values())
    else:
        packet_count = int(payload.get("packet_count", len(packets)) or len(packets))
        complete_count = int(payload.get("complete_count", 0) or 0)
        partial_count = int(payload.get("partial_count", 0) or 0)
        unresolved_count = int(payload.get("unresolved_count", 0) or 0)
        total_missing = sum(modality_counts.values())

    return PacketReadinessMetrics(
        packet_count=packet_count,
        complete_count=complete_count,
        partial_count=partial_count,
        unresolved_count=unresolved_count,
        packet_deficit_count=packet_deficit_count,
        total_missing_modality_count=total_missing,
        modality_deficit_counts=dict(sorted(modality_counts.items())),
    )


def _read_json(path: Path) -> Mapping[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _baseline_sort_key(metrics: PacketReadinessMetrics) -> tuple[int, int, int, int, int]:
    return (
        metrics.complete_count,
        -metrics.unresolved_count,
        -metrics.packet_deficit_count,
        -metrics.total_missing_modality_count,
        metrics.packet_count,
    )


def select_strongest_packet_baseline(
    packages_root: Path,
    *,
    current_latest_path: Path | None = None,
) -> PacketBaselineSelection:
    notes = [
        "baseline_selector=strongest_materialization_summary",
        "ranking=max_complete,min_unresolved,min_deficit,min_missing",
    ]
    candidate_paths: list[Path] = []
    if current_latest_path is not None and current_latest_path.exists():
        candidate_paths.append(current_latest_path)
    if packages_root.exists():
        candidate_paths.extend(
            path
            for path in packages_root.glob("*/materialization_summary.json")
            if path.is_file()
        )

    deduped_paths: list[Path] = []
    seen_paths: set[str] = set()
    for path in candidate_paths:
        normalized = str(path.resolve())
        if normalized in seen_paths:
            continue
        seen_paths.add(normalized)
        deduped_paths.append(path)

    best_path: Path | None = None
    best_payload: Mapping[str, Any] | None = None
    best_metrics: PacketReadinessMetrics | None = None
    for path in deduped_paths:
        payload = _read_json(path)
        metrics = packet_readiness_metrics_from_payload(payload)
        if best_metrics is None or _baseline_sort_key(metrics) > _baseline_sort_key(best_metrics):
            best_path = path
            best_payload = payload
            best_metrics = metrics

    resolved_latest = None
    if current_latest_path is not None:
        resolved_latest = str(current_latest_path).replace("\\", "/")
    resolved_best = None
    if best_path is not None:
        resolved_best = str(best_path).replace("\\", "/")

    return PacketBaselineSelection(
        baseline_path=resolved_best,
        baseline_payload=best_payload,
        current_latest_path=resolved_latest,
        current_latest_matches_strongest=resolved_best == resolved_latest,
        selection_notes=tuple(notes),
    )


def compare_packet_readiness(
    baseline_payload: Mapping[str, Any] | None,
    candidate_payload: Mapping[str, Any] | None,
    *,
    baseline_path: str | None = None,
    candidate_path: str | None = None,
) -> PacketRegressionReport:
    notes: list[str] = [
        "bounded_packet_regression_gate",
        "compares current package latest to scoped post-tier1 packet state",
    ]
    if baseline_payload is None:
        return PacketRegressionReport(
            status="skipped",
            baseline_path=baseline_path,
            candidate_path=candidate_path,
            baseline_metrics=None,
            candidate_metrics=None,
            regressions=(),
            improvements=(),
            changed_packets=(),
            notes=tuple([*notes, "missing_baseline_payload"]),
        )
    if candidate_payload is None:
        return PacketRegressionReport(
            status="skipped",
            baseline_path=baseline_path,
            candidate_path=candidate_path,
            baseline_metrics=packet_readiness_metrics_from_payload(baseline_payload),
            candidate_metrics=None,
            regressions=(),
            improvements=(),
            changed_packets=(),
            notes=tuple([*notes, "missing_candidate_payload"]),
        )

    before = packet_readiness_metrics_from_payload(baseline_payload)
    after = packet_readiness_metrics_from_payload(candidate_payload)
    regressions: list[str] = []
    improvements: list[str] = []

    if after.complete_count < before.complete_count:
        regressions.append(f"complete_count:{before.complete_count}->{after.complete_count}")
    elif after.complete_count > before.complete_count:
        improvements.append(f"complete_count:{before.complete_count}->{after.complete_count}")

    if after.partial_count > before.partial_count:
        regressions.append(f"partial_count:{before.partial_count}->{after.partial_count}")
    elif after.partial_count < before.partial_count:
        improvements.append(f"partial_count:{before.partial_count}->{after.partial_count}")

    if after.unresolved_count > before.unresolved_count:
        regressions.append(
            f"unresolved_count:{before.unresolved_count}->{after.unresolved_count}"
        )
    elif after.unresolved_count < before.unresolved_count:
        improvements.append(
            f"unresolved_count:{before.unresolved_count}->{after.unresolved_count}"
        )

    if after.packet_deficit_count > before.packet_deficit_count:
        regressions.append(
            f"packet_deficit_count:{before.packet_deficit_count}->{after.packet_deficit_count}"
        )
    elif after.packet_deficit_count < before.packet_deficit_count:
        improvements.append(
            f"packet_deficit_count:{before.packet_deficit_count}->{after.packet_deficit_count}"
        )

    if after.total_missing_modality_count > before.total_missing_modality_count:
        regressions.append(
            "total_missing_modality_count:"
            f"{before.total_missing_modality_count}->{after.total_missing_modality_count}"
        )
    elif after.total_missing_modality_count < before.total_missing_modality_count:
        improvements.append(
            "total_missing_modality_count:"
            f"{before.total_missing_modality_count}->{after.total_missing_modality_count}"
        )

    for modality in ("ligand", "structure", "ppi"):
        before_count = int(before.modality_deficit_counts.get(modality, 0) or 0)
        after_count = int(after.modality_deficit_counts.get(modality, 0) or 0)
        if after_count > before_count:
            regressions.append(f"{modality}_deficit_count:{before_count}->{after_count}")
        elif after_count < before_count:
            improvements.append(f"{modality}_deficit_count:{before_count}->{after_count}")

    before_packets = {
        _clean_text(packet.get("accession")): packet
        for packet in _normalize_packets(baseline_payload)
        if _clean_text(packet.get("accession"))
    }
    after_packets = {
        _clean_text(packet.get("accession")): packet
        for packet in _normalize_packets(candidate_payload)
        if _clean_text(packet.get("accession"))
    }
    changed_packets: list[PacketRegressionChange] = []
    for accession in sorted(set(before_packets) & set(after_packets)):
        before_packet = before_packets[accession]
        after_packet = after_packets[accession]
        before_missing = tuple(
            sorted(
                _clean_text(modality)
                for modality in before_packet.get("missing_modalities", ())
                if _clean_text(modality)
            )
        )
        after_missing = tuple(
            sorted(
                _clean_text(modality)
                for modality in after_packet.get("missing_modalities", ())
                if _clean_text(modality)
            )
        )
        before_status = _clean_text(before_packet.get("status"))
        after_status = _clean_text(after_packet.get("status"))
        if before_status != after_status or before_missing != after_missing:
            changed_packets.append(
                PacketRegressionChange(
                    accession=accession,
                    before_status=before_status,
                    after_status=after_status,
                    before_missing_modalities=before_missing,
                    after_missing_modalities=after_missing,
                )
            )

    return PacketRegressionReport(
        status="failed" if regressions else "passed",
        baseline_path=baseline_path,
        candidate_path=candidate_path,
        baseline_metrics=before,
        candidate_metrics=after,
        regressions=tuple(regressions),
        improvements=tuple(improvements),
        changed_packets=tuple(changed_packets),
        notes=tuple(notes),
    )


def compare_packet_readiness_paths(
    baseline_path: Path,
    candidate_path: Path,
) -> PacketRegressionReport:
    baseline_payload = None
    if baseline_path.exists():
        import json

        baseline_payload = json.loads(baseline_path.read_text(encoding="utf-8-sig"))
    candidate_payload = None
    if candidate_path.exists():
        import json

        candidate_payload = json.loads(candidate_path.read_text(encoding="utf-8-sig"))
    return compare_packet_readiness(
        baseline_payload,
        candidate_payload,
        baseline_path=str(baseline_path).replace("\\", "/"),
        candidate_path=str(candidate_path).replace("\\", "/"),
    )


__all__ = [
    "PacketBaselineSelection",
    "PacketReadinessMetrics",
    "PacketRegressionChange",
    "PacketRegressionReport",
    "compare_packet_readiness",
    "compare_packet_readiness_paths",
    "packet_readiness_metrics_from_payload",
    "select_strongest_packet_baseline",
]

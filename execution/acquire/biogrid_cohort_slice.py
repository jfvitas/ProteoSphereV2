from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from core.procurement.source_release_manifest import (
    SourceReleaseManifest,
    validate_source_release_manifest_payload,
)
from core.storage.planning_index_schema import (
    PlanningIndexCoverage,
    PlanningIndexEntry,
    PlanningIndexMaterializationPointer,
    PlanningIndexSourceRecord,
)
from execution.acquire.biogrid_snapshot import (
    BioGRIDSnapshot,
    BioGRIDSnapshotResult,
)

SOURCE_NAME = "BioGRID"
COHORT_SLICE_ID = "biogrid-cohort-slice:v1"

BioGRIDCohortSliceStatus = Literal[
    "surface_only",
    "materialized",
    "empty",
    "unavailable",
    "blocked",
]
BioGRIDCohortSliceEntryKind = Literal["surface", "row"]
BioGRIDCohortSliceEntryStatus = Literal[
    "candidate",
    "materialized",
    "empty",
    "unavailable",
    "blocked",
]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, tuple | list):  # type: ignore[arg-type]
        return tuple(values)
    return (values,)


def _coerce_manifest(manifest: SourceReleaseManifest | Mapping[str, Any]) -> SourceReleaseManifest:
    if isinstance(manifest, SourceReleaseManifest):
        return manifest
    if not isinstance(manifest, Mapping):
        raise TypeError("manifest must be a SourceReleaseManifest or mapping")
    return validate_source_release_manifest_payload(dict(manifest))


def _release_stamp(manifest: SourceReleaseManifest) -> str:
    return manifest.release_version or manifest.release_date or manifest.manifest_id or "unreleased"


def _compact_source_keys(mapping: Mapping[str, Any]) -> dict[str, str]:
    compacted: dict[str, str] = {}
    for key, value in mapping.items():
        text = _clean_text(value)
        if text:
            compacted[key] = text
    return compacted


def _surface_reachable(
    manifest: SourceReleaseManifest,
    snapshot_result: BioGRIDSnapshotResult | None,
    override: bool | None,
) -> bool:
    if override is not None:
        return override
    return bool(
        manifest.local_artifact_refs
        or manifest.source_locator
        or snapshot_result is not None
    )


def _header_index(header: Sequence[str]) -> dict[str, int]:
    return {str(cell).strip().casefold(): index for index, cell in enumerate(header)}


def _pick_cell(header: Sequence[str], record: Sequence[str], *candidates: str) -> str:
    index = _header_index(header)
    for candidate in candidates:
        cell_index = index.get(candidate.casefold())
        if cell_index is None or cell_index >= len(record):
            continue
        value = _clean_text(record[cell_index])
        if value:
            return value
    return ""


def _interaction_id(header: Sequence[str], record: Sequence[str], row_index: int) -> str:
    return _pick_cell(header, record, "BioGRID Interaction ID", "Interaction ID", "ID") or (
        f"row:{row_index}"
    )


def _row_source_keys(
    header: Sequence[str],
    record: Sequence[str],
    *,
    row_index: int,
    interaction_id: str,
    row_acquired: bool,
    surface_reachable: bool,
) -> dict[str, str]:
    return _compact_source_keys(
        {
            "interaction_id": interaction_id,
            "row_index": str(row_index),
            "biogrid_id_a": _pick_cell(header, record, "BioGRID ID A", "BioGRID ID Interactor A"),
            "biogrid_id_b": _pick_cell(header, record, "BioGRID ID B", "BioGRID ID Interactor B"),
            "experimental_system": _pick_cell(header, record, "Experimental System"),
            "experimental_system_type": _pick_cell(header, record, "Experimental System Type"),
            "publication_source": _pick_cell(header, record, "Publication Source"),
            "pubmed_id": _pick_cell(header, record, "Pubmed ID", "PubMed ID", "PMID"),
            "uniprot_a": _pick_cell(header, record, "UniProt A", "UniProtKB A"),
            "uniprot_b": _pick_cell(header, record, "UniProt B", "UniProtKB B"),
            "taxid_a": _pick_cell(header, record, "Taxid Interactor A", "Tax ID A"),
            "taxid_b": _pick_cell(header, record, "Taxid Interactor B", "Tax ID B"),
            "source_database": _pick_cell(header, record, "Source Database"),
            "row_acquired": str(bool(row_acquired)).lower(),
            "surface_reachable": str(bool(surface_reachable)).lower(),
            "breadth_semantics": "curated_breadth_row",
        }
    )


def _surface_source_keys(
    manifest: SourceReleaseManifest,
    *,
    surface_reachable: bool,
    row_acquired: bool,
    selected_row_count: int,
    source_record_count: int,
) -> dict[str, str]:
    return _compact_source_keys(
        {
            "manifest_id": manifest.manifest_id,
            "release_stamp": _release_stamp(manifest),
            "source_locator": manifest.source_locator or "",
            "local_artifact_ref_count": str(len(manifest.local_artifact_refs)),
            "surface_reachable": str(bool(surface_reachable)).lower(),
            "row_acquired": str(bool(row_acquired)).lower(),
            "selected_row_count": str(selected_row_count),
            "source_record_count": str(source_record_count),
            "breadth_semantics": "curated_breadth_surface",
        }
    )


def _surface_materialization_pointer(
    manifest: SourceReleaseManifest,
    *,
    release_stamp: str,
) -> PlanningIndexMaterializationPointer:
    pointer = manifest.source_locator or (
        manifest.local_artifact_refs[0] if manifest.local_artifact_refs else ""
    )
    return PlanningIndexMaterializationPointer(
        materialization_kind="table",
        pointer=pointer or f"biogrid-surface:{release_stamp}",
        selector="download_surface",
        source_name=SOURCE_NAME,
        source_record_id=f"surface:{release_stamp}",
        notes=("release-aware download surface",),
    )


def _row_materialization_pointer(
    manifest: SourceReleaseManifest,
    *,
    interaction_id: str,
) -> PlanningIndexMaterializationPointer:
    pointer = manifest.local_artifact_refs[0] if manifest.local_artifact_refs else (
        manifest.source_locator or ""
    )
    return PlanningIndexMaterializationPointer(
        materialization_kind="table",
        pointer=pointer or f"biogrid-row:{interaction_id}",
        selector=f"row:{interaction_id}",
        source_name=SOURCE_NAME,
        source_record_id=interaction_id,
        notes=("curated breadth row",),
    )


def _surface_entry(
    manifest: SourceReleaseManifest,
    *,
    surface_reachable: bool,
    row_acquired: bool,
    selected_row_count: int,
    source_record_count: int,
    snapshot_status: str,
    snapshot_reason: str,
) -> PlanningIndexEntry:
    release_stamp = _release_stamp(manifest)
    source_record = PlanningIndexSourceRecord(
        source_name=SOURCE_NAME,
        source_record_id=f"surface:{release_stamp}",
        release_version=manifest.release_version,
        release_date=manifest.release_date,
        source_locator=manifest.source_locator,
        manifest_id=manifest.manifest_id,
        source_keys=_surface_source_keys(
            manifest,
            surface_reachable=surface_reachable,
            row_acquired=row_acquired,
            selected_row_count=selected_row_count,
            source_record_count=source_record_count,
        ),
    )
    coverage_state = "present" if surface_reachable and row_acquired else "partial"
    return PlanningIndexEntry(
        planning_id=f"biogrid:{release_stamp}:surface",
        source_records=(source_record,),
        join_status="deferred",
        coverage=(
            PlanningIndexCoverage(
                coverage_kind="source",
                label="BioGRID curated breadth surface",
                coverage_state=coverage_state,
                source_names=(SOURCE_NAME,),
                notes=("surface metadata is not row acquisition",),
            ),
        ),
        lazy_materialization_pointers=(
            _surface_materialization_pointer(manifest, release_stamp=release_stamp),
        ),
        metadata={
            "surface_reachable": surface_reachable,
            "row_acquired": row_acquired,
            "selected_row_count": selected_row_count,
            "source_record_count": source_record_count,
            "breadth_semantics": "curated_breadth_surface",
            "release_aware": True,
            "snapshot_status": snapshot_status,
            "snapshot_reason": snapshot_reason,
        },
    )


def _row_entries(
    manifest: SourceReleaseManifest,
    snapshot: BioGRIDSnapshot,
    *,
    surface_reachable: bool,
    row_limit: int,
) -> tuple[PlanningIndexEntry, ...]:
    header = snapshot.header
    rows = snapshot.records[:row_limit] if row_limit > 0 else ()
    release_stamp = _release_stamp(manifest)
    entries: list[PlanningIndexEntry] = []
    for row_index, record in enumerate(rows, start=1):
        interaction_id = _interaction_id(header, record, row_index)
        source_record = PlanningIndexSourceRecord(
            source_name=SOURCE_NAME,
            source_record_id=interaction_id,
            release_version=manifest.release_version,
            release_date=manifest.release_date,
            source_locator=manifest.source_locator,
            manifest_id=manifest.manifest_id,
            source_keys=_row_source_keys(
                header,
                record,
                row_index=row_index,
                interaction_id=interaction_id,
                row_acquired=True,
                surface_reachable=surface_reachable,
            ),
        )
        metadata = {
            "entry_kind": "row",
            "row_index": row_index,
            "interaction_id": interaction_id,
            "row_acquired": True,
            "surface_reachable": surface_reachable,
            "breadth_semantics": "curated_breadth_row",
            "experimental_system": _pick_cell(header, record, "Experimental System"),
            "experimental_system_type": _pick_cell(header, record, "Experimental System Type"),
            "publication_source": _pick_cell(header, record, "Publication Source"),
        }
        entries.append(
            PlanningIndexEntry(
                planning_id=f"biogrid:{release_stamp}:row:{row_index}:{interaction_id}",
                source_records=(source_record,),
                join_status="partial",
                coverage=(
                    PlanningIndexCoverage(
                        coverage_kind="source",
                        label="BioGRID curated breadth row",
                        coverage_state="present",
                        source_names=(SOURCE_NAME,),
                        notes=("row-level interaction acquired from a release-pinned snapshot",),
                        confidence=1.0,
                    ),
                ),
                lazy_materialization_pointers=(
                    _row_materialization_pointer(manifest, interaction_id=interaction_id),
                ),
                metadata=metadata,
            )
        )
    return tuple(entries)


@dataclass(frozen=True, slots=True)
class BioGRIDCohortSliceEntry:
    entry_kind: BioGRIDCohortSliceEntryKind
    planning_entry: PlanningIndexEntry
    surface_reachable: bool
    row_acquired: bool
    breadth_semantics: str
    source_record_id: str
    interaction_id: str = ""
    status: BioGRIDCohortSliceEntryStatus = "candidate"
    notes: tuple[str, ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "entry_kind", _clean_text(self.entry_kind))  # type: ignore[arg-type]
        object.__setattr__(self, "source_record_id", _clean_text(self.source_record_id))
        object.__setattr__(self, "interaction_id", _clean_text(self.interaction_id))
        object.__setattr__(self, "breadth_semantics", _clean_text(self.breadth_semantics))
        object.__setattr__(
            self,
            "notes",
            tuple(
                cleaned_note
                for note in self.notes
                if (cleaned_note := _clean_text(note))
            ),
        )
        object.__setattr__(self, "provenance", dict(self.provenance or {}))
        if not self.source_record_id:
            raise ValueError("source_record_id must not be empty")
        if self.entry_kind not in {"surface", "row"}:
            raise ValueError("entry_kind must be surface or row")
        if self.status not in {"candidate", "materialized", "empty", "unavailable", "blocked"}:
            raise ValueError("unsupported entry status")

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_kind": self.entry_kind,
            "planning_entry": self.planning_entry.to_dict(),
            "surface_reachable": self.surface_reachable,
            "row_acquired": self.row_acquired,
            "breadth_semantics": self.breadth_semantics,
            "source_record_id": self.source_record_id,
            "interaction_id": self.interaction_id,
            "status": self.status,
            "notes": list(self.notes),
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class BioGRIDCohortSlice:
    slice_id: str
    manifest: SourceReleaseManifest
    status: BioGRIDCohortSliceStatus
    surface_reachable: bool
    row_acquired: bool
    entries: tuple[BioGRIDCohortSliceEntry, ...]
    source_snapshot_status: str = ""
    source_snapshot_reason: str = ""
    row_limit: int = 25
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "slice_id", _clean_text(self.slice_id))
        if not self.slice_id:
            raise ValueError("slice_id must not be empty")
        if self.status not in {"surface_only", "materialized", "empty", "unavailable", "blocked"}:
            raise ValueError("unsupported slice status")
        object.__setattr__(self, "entries", tuple(self.entries))
        object.__setattr__(self, "source_snapshot_status", _clean_text(self.source_snapshot_status))
        object.__setattr__(self, "source_snapshot_reason", _clean_text(self.source_snapshot_reason))
        object.__setattr__(self, "provenance", dict(self.provenance or {}))

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    @property
    def surface_entry_count(self) -> int:
        return sum(1 for entry in self.entries if entry.entry_kind == "surface")

    @property
    def row_entry_count(self) -> int:
        return sum(1 for entry in self.entries if entry.entry_kind == "row")

    @property
    def selected_row_count(self) -> int:
        return sum(1 for entry in self.entries if entry.entry_kind == "row" and entry.row_acquired)

    @property
    def source_record_count(self) -> int:
        if self.status == "materialized":
            return int(self.provenance.get("source_record_count", self.row_entry_count))
        return int(self.provenance.get("source_record_count", 0))

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "slice_id": self.slice_id,
            "status": self.status,
            "manifest": self.manifest.to_dict(),
            "surface_reachable": self.surface_reachable,
            "row_acquired": self.row_acquired,
            "entry_count": self.entry_count,
            "surface_entry_count": self.surface_entry_count,
            "row_entry_count": self.row_entry_count,
            "selected_row_count": self.selected_row_count,
            "source_record_count": self.source_record_count,
            "source_snapshot_status": self.source_snapshot_status,
            "source_snapshot_reason": self.source_snapshot_reason,
            "row_limit": self.row_limit,
            "entries": [entry.to_dict() for entry in self.entries],
            "provenance": dict(self.provenance),
        }


def _build_provenance(
    manifest: SourceReleaseManifest,
    *,
    surface_reachable: bool,
    row_acquired: bool,
    snapshot_result: BioGRIDSnapshotResult | None,
    selected_row_count: int,
    source_record_count: int,
) -> dict[str, Any]:
    provenance = {
        "source_name": SOURCE_NAME,
        "manifest_id": manifest.manifest_id,
        "release_version": manifest.release_version,
        "release_date": manifest.release_date,
        "source_locator": manifest.source_locator,
        "local_artifact_refs": list(manifest.local_artifact_refs),
        "retrieval_mode": manifest.retrieval_mode,
        "surface_reachable": surface_reachable,
        "row_acquired": row_acquired,
        "selected_row_count": selected_row_count,
        "source_record_count": source_record_count,
        "breadth_semantics": "curated_breadth_surface",
        "release_aware": True,
    }
    if snapshot_result is not None:
        provenance.update(
            {
                "snapshot_status": snapshot_result.status,
                "snapshot_reason": snapshot_result.reason,
                "snapshot_provenance": dict(snapshot_result.provenance),
            }
        )
    return provenance


def build_biogrid_cohort_slice(
    manifest: SourceReleaseManifest | Mapping[str, Any],
    *,
    snapshot_result: BioGRIDSnapshotResult | None = None,
    surface_reachable: bool | None = None,
    row_limit: int = 25,
) -> BioGRIDCohortSlice:
    normalized_manifest = _coerce_manifest(manifest)
    if normalized_manifest.source_name.casefold() != SOURCE_NAME.casefold():
        return BioGRIDCohortSlice(
            slice_id=f"biogrid:{_release_stamp(normalized_manifest)}:blocked",
            manifest=normalized_manifest,
            status="blocked",
            surface_reachable=False,
            row_acquired=False,
            entries=(),
            source_snapshot_status=snapshot_result.status if snapshot_result else "blocked",
            source_snapshot_reason="biogrid_manifest_source_mismatch",
            row_limit=row_limit,
            provenance=_build_provenance(
                normalized_manifest,
                surface_reachable=False,
                row_acquired=False,
                snapshot_result=snapshot_result,
                selected_row_count=0,
                source_record_count=0,
            ),
        )

    release_stamp = _release_stamp(normalized_manifest)
    resolved_surface_reachable = _surface_reachable(
        normalized_manifest,
        snapshot_result,
        surface_reachable,
    )

    if snapshot_result is None:
        surface_entry = _surface_entry(
            normalized_manifest,
            surface_reachable=resolved_surface_reachable,
            row_acquired=False,
            selected_row_count=0,
            source_record_count=0,
            snapshot_status="surface_only",
            snapshot_reason="biogrid_download_surface_metadata_only",
        )
        return BioGRIDCohortSlice(
            slice_id=f"biogrid:{release_stamp}:surface",
            manifest=normalized_manifest,
            status="surface_only",
            surface_reachable=resolved_surface_reachable,
            row_acquired=False,
            entries=(BioGRIDCohortSliceEntry(
                entry_kind="surface",
                planning_entry=surface_entry,
                surface_reachable=resolved_surface_reachable,
                row_acquired=False,
                breadth_semantics="curated_breadth_surface",
                source_record_id=f"surface:{release_stamp}",
                status="candidate",
                notes=("download-surface metadata only; row acquisition not claimed",),
                provenance={
                    "release_aware": True,
                    "surface_reachable": resolved_surface_reachable,
                    "row_acquired": False,
                },
            ),),
            source_snapshot_status="surface_only",
            source_snapshot_reason="biogrid_download_surface_metadata_only",
            row_limit=row_limit,
            provenance=_build_provenance(
                normalized_manifest,
                surface_reachable=resolved_surface_reachable,
                row_acquired=False,
                snapshot_result=None,
                selected_row_count=0,
                source_record_count=0,
            ),
        )

    snapshot = snapshot_result.snapshot
    snapshot_status = snapshot_result.status
    snapshot_reason = snapshot_result.reason
    if snapshot_status == "ok" and snapshot is not None:
        row_entries = _row_entries(
            normalized_manifest,
            snapshot,
            surface_reachable=resolved_surface_reachable,
            row_limit=row_limit,
        )
        surface_entry = _surface_entry(
            normalized_manifest,
            surface_reachable=resolved_surface_reachable,
            row_acquired=bool(row_entries),
            selected_row_count=len(row_entries),
            source_record_count=snapshot.record_count,
            snapshot_status=snapshot_status,
            snapshot_reason=snapshot_reason,
        )
        entries = (
            BioGRIDCohortSliceEntry(
                entry_kind="surface",
                planning_entry=surface_entry,
                surface_reachable=resolved_surface_reachable,
                row_acquired=bool(row_entries),
                breadth_semantics="curated_breadth_surface",
                source_record_id=f"surface:{release_stamp}",
                status="candidate",
                notes=("release-pinned download surface retained alongside row candidates",),
                provenance={
                    "release_aware": True,
                    "surface_reachable": resolved_surface_reachable,
                    "row_acquired": bool(row_entries),
                    "selected_row_count": len(row_entries),
                    "source_record_count": snapshot.record_count,
                },
            ),
            *(
                BioGRIDCohortSliceEntry(
                    entry_kind="row",
                    planning_entry=row_entry,
                    surface_reachable=resolved_surface_reachable,
                    row_acquired=True,
                    breadth_semantics="curated_breadth_row",
                    source_record_id=row_entry.source_records[0].source_record_id,
                    interaction_id=row_entry.source_records[0].source_record_id,
                    status="materialized",
                    notes=("row-level acquisition is explicit for this selected breadth slice",),
                    provenance={
                        "release_aware": True,
                        "surface_reachable": resolved_surface_reachable,
                        "row_acquired": True,
                        "selected_row_count": len(row_entries),
                        "source_record_count": snapshot.record_count,
                    },
                )
                for row_entry in row_entries
            ),
        )
        return BioGRIDCohortSlice(
            slice_id=f"biogrid:{release_stamp}:materialized",
            manifest=normalized_manifest,
            status="materialized",
            surface_reachable=resolved_surface_reachable,
            row_acquired=bool(row_entries),
            entries=entries,
            source_snapshot_status=snapshot_status,
            source_snapshot_reason=snapshot_reason,
            row_limit=row_limit,
            provenance=_build_provenance(
                normalized_manifest,
                surface_reachable=resolved_surface_reachable,
                row_acquired=bool(row_entries),
                snapshot_result=snapshot_result,
                selected_row_count=len(row_entries),
                source_record_count=snapshot.record_count,
            ),
        )

    empty_like = snapshot_status == "unavailable" and snapshot_reason in {
        "biogrid_empty_payload",
        "biogrid_no_interaction_rows",
    }
    slice_status: BioGRIDCohortSliceStatus = "empty" if empty_like else "unavailable"
    surface_entry = _surface_entry(
        normalized_manifest,
        surface_reachable=resolved_surface_reachable,
        row_acquired=False,
        selected_row_count=0,
        source_record_count=0,
        snapshot_status=snapshot_status,
        snapshot_reason=snapshot_reason,
    )
    return BioGRIDCohortSlice(
        slice_id=f"biogrid:{release_stamp}:{slice_status}",
        manifest=normalized_manifest,
        status=slice_status,
        surface_reachable=resolved_surface_reachable,
        row_acquired=False,
        entries=(
            BioGRIDCohortSliceEntry(
                entry_kind="surface",
                planning_entry=surface_entry,
                surface_reachable=resolved_surface_reachable,
                row_acquired=False,
                breadth_semantics="curated_breadth_surface",
                source_record_id=f"surface:{release_stamp}",
                status="candidate",
                notes=("snapshot did not yield acquired rows",),
                provenance={
                    "release_aware": True,
                    "surface_reachable": resolved_surface_reachable,
                    "row_acquired": False,
                    "snapshot_status": snapshot_status,
                    "snapshot_reason": snapshot_reason,
                },
            ),
        ),
        source_snapshot_status=snapshot_status,
        source_snapshot_reason=snapshot_reason,
        row_limit=row_limit,
        provenance=_build_provenance(
            normalized_manifest,
            surface_reachable=resolved_surface_reachable,
            row_acquired=False,
            snapshot_result=snapshot_result,
            selected_row_count=0,
            source_record_count=0,
        ),
    )


__all__ = [
    "BioGRIDCohortSlice",
    "BioGRIDCohortSliceEntry",
    "BioGRIDCohortSliceEntryKind",
    "BioGRIDCohortSliceEntryStatus",
    "BioGRIDCohortSliceStatus",
    "COHORT_SLICE_ID",
    "SOURCE_NAME",
    "build_biogrid_cohort_slice",
]

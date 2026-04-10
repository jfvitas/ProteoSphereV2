from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from connectors.uniprot.client import UniProtClient, UniProtClientError
from connectors.uniprot.parsers import UniProtSequenceRecord, parse_uniprot_entry
from execution.acquire.supplemental_scrape_registry import (
    DEFAULT_SUPPLEMENTAL_SCRAPE_REGISTRY,
    SupplementalScrapeRegistry,
    plan_accession_supplemental_lanes,
)

SOURCE_NAME = "UniProt"


@dataclass(frozen=True, slots=True)
class UniProtSnapshotContract:
    """Normalized manifest contract for a pinned UniProt snapshot."""

    source: str
    release: str
    release_date: str
    proteome_id: str
    proteome_name: str
    proteome_reference: bool
    proteome_taxon_id: int | None
    accessions: tuple[str, ...]
    manifest_id: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "release": self.release,
            "release_date": self.release_date,
            "proteome_id": self.proteome_id,
            "proteome_name": self.proteome_name,
            "proteome_reference": self.proteome_reference,
            "proteome_taxon_id": self.proteome_taxon_id,
            "accessions": list(self.accessions),
            "manifest_id": self.manifest_id,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class UniProtSnapshotRecord:
    """A single accession resolved against a pinned UniProt release."""

    accession: str
    sequence: UniProtSequenceRecord
    release: str
    release_date: str
    proteome_id: str
    proteome_name: str
    proteome_reference: bool
    proteome_taxon_id: int | None
    supplemental_lanes: tuple[dict[str, Any], ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)
    raw_entry: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "sequence": self.sequence.to_dict(),
            "release": self.release,
            "release_date": self.release_date,
            "proteome_id": self.proteome_id,
            "proteome_name": self.proteome_name,
            "proteome_reference": self.proteome_reference,
            "proteome_taxon_id": self.proteome_taxon_id,
            "supplemental_lanes": [dict(lane) for lane in self.supplemental_lanes],
            "provenance": dict(self.provenance),
            "raw_entry": dict(self.raw_entry),
        }


@dataclass(frozen=True, slots=True)
class UniProtSnapshot:
    """Complete UniProt snapshot payload for downstream acquisition stages."""

    source_release: dict[str, Any]
    proteome: dict[str, Any]
    provenance: dict[str, Any]
    records: tuple[UniProtSnapshotRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_release": dict(self.source_release),
            "proteome": dict(self.proteome),
            "provenance": dict(self.provenance),
            "records": [record.to_dict() for record in self.records],
        }


@dataclass(frozen=True, slots=True)
class UniProtSnapshotResult:
    """Result wrapper that reports ready, blocked, or unavailable states honestly."""

    status: str
    manifest: dict[str, Any] = field(default_factory=dict)
    contract: UniProtSnapshotContract | None = None
    snapshot: UniProtSnapshot | None = None
    blocker_reason: str = ""
    unavailable_reason: str = ""
    missing_fields: tuple[str, ...] = ()
    invalid_accessions: tuple[str, ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "manifest": dict(self.manifest),
            "contract": self.contract.to_dict() if self.contract is not None else None,
            "snapshot": self.snapshot.to_dict() if self.snapshot is not None else None,
            "blocker_reason": self.blocker_reason,
            "unavailable_reason": self.unavailable_reason,
            "missing_fields": list(self.missing_fields),
            "invalid_accessions": list(self.invalid_accessions),
            "provenance": dict(self.provenance),
        }


def acquire_uniprot_snapshot(
    manifest: dict[str, Any] | None,
    *,
    client: UniProtClient | None = None,
    opener: Any | None = None,
    supplemental_registry: SupplementalScrapeRegistry | None = None,
) -> UniProtSnapshotResult:
    """Resolve a manifest-pinned UniProt snapshot into a normalized payload."""

    manifest_data = dict(manifest or {})
    provenance = _build_manifest_provenance(manifest_data)
    supplemental_request_map = _build_supplemental_request_map(manifest_data)
    resolved_supplemental_registry = (
        supplemental_registry or DEFAULT_SUPPLEMENTAL_SCRAPE_REGISTRY
    )
    contract, missing_fields, invalid_accessions, blocker_reason = _normalize_contract(
        manifest_data,
        provenance,
    )
    if blocker_reason:
        return UniProtSnapshotResult(
            status="blocked",
            manifest=manifest_data,
            blocker_reason=blocker_reason,
            missing_fields=missing_fields,
            invalid_accessions=invalid_accessions,
            provenance=provenance,
        )

    assert contract is not None
    resolved_client = client or UniProtClient()
    records: list[UniProtSnapshotRecord] = []
    supplemental_lane_count = 0
    supplemental_lane_approved_count = 0
    supplemental_lane_blocked_count = 0

    for accession in contract.accessions:
        try:
            entry = resolved_client.get_entry(accession, opener=opener)
            sequence = parse_uniprot_entry(entry)
        except (UniProtClientError, ValueError) as exc:
            return UniProtSnapshotResult(
                status="unavailable",
                manifest=manifest_data,
                contract=contract,
                unavailable_reason=f"UniProt snapshot acquisition unavailable: {exc}",
                provenance=provenance,
            )

        if sequence.accession != accession:
            return UniProtSnapshotResult(
                status="unavailable",
                manifest=manifest_data,
                contract=contract,
            unavailable_reason=(
                "UniProt snapshot acquisition unavailable: "
                f"requested accession {accession} resolved to {sequence.accession}"
            ),
            provenance=provenance,
        )

        supplemental_lanes = _build_supplemental_lanes(
            accession,
            supplemental_request_map,
            registry=resolved_supplemental_registry,
        )
        supplemental_lane_count += len(supplemental_lanes)
        supplemental_lane_approved_count += sum(
            1 for lane in supplemental_lanes if lane.get("status") == "approved"
        )
        supplemental_lane_blocked_count += sum(
            1 for lane in supplemental_lanes if lane.get("status") == "blocked"
        )

        record_provenance = _build_record_provenance(contract, accession, provenance)
        record_provenance.update(
            {
                "supplemental_lane_count": len(supplemental_lanes),
                "supplemental_lane_approved_count": sum(
                    1 for lane in supplemental_lanes if lane.get("status") == "approved"
                ),
                "supplemental_lane_blocked_count": sum(
                    1 for lane in supplemental_lanes if lane.get("status") == "blocked"
                ),
            }
        )
        records.append(
            UniProtSnapshotRecord(
                accession=accession,
                sequence=sequence,
                release=contract.release,
                release_date=contract.release_date,
                proteome_id=contract.proteome_id,
                proteome_name=contract.proteome_name,
                proteome_reference=contract.proteome_reference,
                proteome_taxon_id=contract.proteome_taxon_id,
                supplemental_lanes=supplemental_lanes,
                provenance=record_provenance,
                raw_entry=dict(entry),
            )
        )

    snapshot = UniProtSnapshot(
        source_release={
            "source": contract.source,
            "release": contract.release,
            "release_date": contract.release_date,
            "manifest_id": contract.manifest_id,
            "accessions": list(contract.accessions),
        },
        proteome={
            "proteome_id": contract.proteome_id,
            "proteome_name": contract.proteome_name,
            "proteome_reference": contract.proteome_reference,
            "proteome_taxon_id": contract.proteome_taxon_id,
        },
        provenance={
            **provenance,
            "record_count": len(records),
            "source": contract.source,
            "release": contract.release,
            "release_date": contract.release_date,
            "proteome_id": contract.proteome_id,
            "supplemental_lane_count": supplemental_lane_count,
            "supplemental_lane_approved_count": supplemental_lane_approved_count,
            "supplemental_lane_blocked_count": supplemental_lane_blocked_count,
        },
        records=tuple(records),
    )
    return UniProtSnapshotResult(
        status="ready",
        manifest=manifest_data,
        contract=contract,
        snapshot=snapshot,
        provenance=snapshot.provenance,
    )


def _normalize_contract(
    manifest: dict[str, Any],
    provenance: dict[str, Any],
) -> tuple[
    UniProtSnapshotContract | None,
    tuple[str, ...],
    tuple[str, ...],
    str,
]:
    missing_fields: list[str] = []

    source = _first_text(
        manifest,
        "source",
        "source_name",
        default=SOURCE_NAME,
    )
    if source.strip().lower() not in {"", "uniprot", "uniprotkb"}:
        return None, (), (), f"UniProt snapshot manifest must describe source {SOURCE_NAME!r}"

    release = _first_text(
        manifest,
        "release",
        "release_id",
        "source_release.release",
        "source_release.release_id",
    )
    if not release:
        missing_fields.append("release")

    release_date = _first_text(
        manifest,
        "release_date",
        "source_release.release_date",
        "source_release.published",
    )
    if not release_date:
        missing_fields.append("release_date")

    proteome_id = _first_text(
        manifest,
        "proteome_id",
        "proteome.id",
        "source_release.proteome_id",
    )
    if not proteome_id:
        missing_fields.append("proteome_id")

    accessions, invalid_accessions = _coerce_accessions(
        _lookup(manifest, "accessions", "accession", "source_release.accessions"),
    )
    if invalid_accessions:
        return None, (), invalid_accessions, (
            "UniProt snapshot manifest contains invalid accessions: "
            + ", ".join(invalid_accessions)
        )
    if not accessions:
        missing_fields.append("accessions")

    provenance_payload = _lookup(manifest, "provenance", "source_provenance")
    if provenance_payload is None:
        missing_fields.append("provenance")
        provenance_payload = provenance
    elif not isinstance(provenance_payload, dict):
        missing_fields.append("provenance")
        provenance_payload = {}

    if missing_fields:
        missing = tuple(dict.fromkeys(missing_fields))
        return None, missing, (), (
            "UniProt snapshot manifest is missing required fields: " + ", ".join(missing)
        )

    proteome_name = _first_text(
        manifest,
        "proteome_name",
        "proteome.name",
        default="",
    )
    proteome_reference = _coerce_bool(
        _lookup(manifest, "proteome_reference", "proteome.reference"),
    )
    proteome_taxon_id = _coerce_int_or_none(
        _lookup(manifest, "proteome_taxon_id", "proteome.taxon_id"),
    )
    manifest_id = _first_text(manifest, "manifest_id", "id", "source_manifest_id")

    contract = UniProtSnapshotContract(
        source=SOURCE_NAME,
        release=release,
        release_date=release_date,
        proteome_id=proteome_id,
        proteome_name=proteome_name,
        proteome_reference=proteome_reference,
        proteome_taxon_id=proteome_taxon_id,
        accessions=accessions,
        manifest_id=manifest_id,
        provenance=dict(provenance_payload),
    )
    return contract, (), (), ""


def _build_supplemental_request_map(manifest: dict[str, Any]) -> dict[str, tuple[Any, ...]]:
    payload = _lookup(
        manifest,
        "supplemental_requests",
        "supplemental_lanes",
        "supplemental_scrapes",
    )
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        return {}

    request_map: dict[str, tuple[Any, ...]] = {}
    for key, value in payload.items():
        accession = _normalize_accession(key)
        if not accession:
            continue
        if isinstance(value, (list, tuple)):
            request_map[accession] = tuple(value)
        else:
            request_map[accession] = (value,)
    return request_map


def _build_supplemental_lanes(
    accession: str,
    request_map: dict[str, tuple[Any, ...]],
    *,
    registry: SupplementalScrapeRegistry,
) -> tuple[dict[str, Any], ...]:
    lane_specs = request_map.get(accession, ())
    if not lane_specs:
        return ()
    return tuple(
        result.to_dict()
        for result in plan_accession_supplemental_lanes(
            accession,
            lane_specs,
            registry=registry,
        )
    )


def _build_manifest_provenance(manifest: dict[str, Any]) -> dict[str, Any]:
    provenance: dict[str, Any] = {}
    payload = _lookup(manifest, "provenance", "source_provenance")
    if isinstance(payload, dict):
        provenance.update(payload)

    for key in ("manifest_id", "id", "source_manifest_id", "source_url"):
        value = manifest.get(key)
        if value not in (None, "") and key not in provenance:
            provenance[key] = value

    if "acquired_at" not in provenance:
        value = manifest.get("acquired_at")
        if value not in (None, ""):
            provenance["acquired_at"] = value
        else:
            provenance["acquired_at"] = datetime.now(UTC).isoformat()

    source_ids = provenance.get("source_ids")
    if isinstance(source_ids, list):
        provenance["source_ids"] = tuple(source_ids)
    elif isinstance(source_ids, str):
        provenance["source_ids"] = (source_ids,)
    elif source_ids is None:
        provenance["source_ids"] = ()
    return provenance


def _build_record_provenance(
    contract: UniProtSnapshotContract,
    accession: str,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    record_provenance = dict(provenance)
    record_provenance.update(
        {
            "accession": accession,
            "source": contract.source,
            "release": contract.release,
            "release_date": contract.release_date,
            "proteome_id": contract.proteome_id,
            "proteome_reference": contract.proteome_reference,
        }
    )
    return record_provenance


def _lookup(mapping: dict[str, Any], *paths: str) -> Any:
    for path in paths:
        value = mapping
        for key in path.split("."):
            if not isinstance(value, dict) or key not in value:
                value = None
                break
            value = value[key]
        if value not in (None, ""):
            return value
    return None


def _first_text(
    mapping: dict[str, Any],
    *paths: str,
    default: str = "",
) -> str:
    value = _lookup(mapping, *paths)
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _coerce_accessions(value: Any) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if value is None:
        return (), ()
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple)):
        values = list(value)
    else:
        values = [value]

    normalized: list[str] = []
    invalid: list[str] = []
    for item in values:
        accession = _normalize_accession(item)
        if accession:
            if accession not in normalized:
                normalized.append(accession)
        else:
            text = str(item or "").strip().upper()
            if text:
                invalid.append(text)
    return tuple(normalized), tuple(dict.fromkeys(invalid))


def _normalize_accession(value: Any) -> str:
    accession = str(value or "").strip().upper()
    if not accession:
        return ""
    if not 6 <= len(accession) <= 10 or not accession.isalnum():
        return ""
    return accession


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _coerce_int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return int(value)
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


__all__ = [
    "SOURCE_NAME",
    "UniProtSnapshot",
    "UniProtSnapshotContract",
    "UniProtSnapshotRecord",
    "UniProtSnapshotResult",
    "acquire_uniprot_snapshot",
]

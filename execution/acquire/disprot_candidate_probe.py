from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

DEFAULT_DISPROT_API_BASE_URL = "https://disprot.org/api"
DISPROT_CANDIDATE_PROBE_TIMEOUT = 30.0
DISPROT_CANDIDATE_PROBE_USER_AGENT = "ProteoSphereV2-DisProtCandidateProbe/0.1"
DisProtCandidateProbeStatus = Literal["positive_hit", "reachable_empty", "blocked"]


class DisProtCandidateProbeError(ValueError):
    """Raised when a DisProt candidate probe manifest or payload is invalid."""


def _normalize_text(value: object | None, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise DisProtCandidateProbeError(f"{field_name} must be a non-empty string")
    return text


def _normalize_optional_text(value: object | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _coerce_sequence(values: object | None) -> tuple[object, ...]:
    if values in (None, ""):
        return ()
    if isinstance(values, Sequence) and not isinstance(values, (str, bytes, Mapping)):
        return tuple(values)
    return (values,)


def _normalize_accession(value: object | None) -> str:
    accession = str(value or "").strip().upper()
    if not accession:
        return ""
    if not 6 <= len(accession) <= 10 or not accession.isalnum():
        return ""
    return accession


def _coerce_accessions(values: object | None) -> tuple[tuple[str, ...], tuple[str, ...]]:
    normalized: list[str] = []
    invalid: list[str] = []
    seen: set[str] = set()
    for raw_value in _coerce_sequence(values):
        accession = _normalize_accession(raw_value)
        if accession:
            if accession in seen:
                continue
            seen.add(accession)
            normalized.append(accession)
            continue
        text = str(raw_value or "").strip().upper()
        if text:
            invalid.append(text)
    return tuple(normalized), tuple(dict.fromkeys(invalid))


def _clone_jsonish(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _clone_jsonish(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clone_jsonish(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_clone_jsonish(item) for item in value)
    return value


def _coerce_raw_records(value: Any) -> tuple[dict[str, Any], ...]:
    if value in (None, ""):
        return ()
    if isinstance(value, Mapping):
        items = [value]
    elif isinstance(value, list):
        items = value
    elif isinstance(value, tuple):
        items = list(value)
    else:
        raise DisProtCandidateProbeError("DisProt payload must be a mapping or sequence")

    records: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, Mapping):
            raise DisProtCandidateProbeError("DisProt payload items must be mappings")
        records.append({str(key): _clone_jsonish(value) for key, value in item.items()})
    return tuple(records)


def _payload_to_records(payload: Any) -> tuple[dict[str, Any], ...]:
    if payload is None:
        return ()
    if isinstance(payload, Mapping):
        for key in ("data", "results", "items", "entries"):
            value = payload.get(key)
            if isinstance(value, list):
                return _coerce_raw_records(value)
            if isinstance(value, tuple):
                return _coerce_raw_records(value)
        return _coerce_raw_records(payload)
    return _coerce_raw_records(payload)


def _response_size(payload: Any, records: Sequence[Mapping[str, Any]]) -> int | None:
    if not isinstance(payload, Mapping):
        return len(records)
    for key in ("size", "count", "total", "total_count"):
        value = payload.get(key)
        if value in (None, ""):
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return len(records)


def _record_accessions(record: Mapping[str, Any]) -> tuple[str, ...]:
    candidates: list[str] = []
    for key in ("acc", "accession", "uniprotAccession", "uniprot_accession", "uniprot_accessions"):
        value = record.get(key)
        for item in _coerce_sequence(value):
            accession = _normalize_accession(item)
            if accession and accession not in candidates:
                candidates.append(accession)
    return tuple(candidates)


def _record_disprot_ids(record: Mapping[str, Any]) -> tuple[str, ...]:
    candidates: list[str] = []
    for key in ("disprot_id", "disprotId", "id"):
        value = record.get(key)
        text = _normalize_optional_text(value)
        if text and text not in candidates:
            candidates.append(text)
    return tuple(candidates)


def _build_probe_url(api_base_url: str, accession: str) -> str:
    return f"{api_base_url.rstrip('/')}/search?acc={quote(accession)}"


@dataclass(frozen=True, slots=True)
class DisProtCandidateProbeManifest:
    """Conservative probe contract for DisProt accession candidates."""

    accessions: tuple[str, ...]
    api_base_url: str = DEFAULT_DISPROT_API_BASE_URL
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        accessions, invalid_accessions = _coerce_accessions(self.accessions)
        if invalid_accessions:
            raise DisProtCandidateProbeError(
                "manifest contains invalid accession(s): " + ", ".join(invalid_accessions)
            )
        if not accessions:
            raise DisProtCandidateProbeError("manifest must contain at least one accession")
        if not isinstance(self.metadata, Mapping):
            raise DisProtCandidateProbeError("metadata must be a mapping")

        object.__setattr__(self, "accessions", accessions)
        object.__setattr__(self, "api_base_url", _normalize_text(self.api_base_url, "api_base_url"))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def source_name(self) -> str:
        return "DisProt"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "accessions": list(self.accessions),
            "api_base_url": self.api_base_url,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> DisProtCandidateProbeManifest:
        if not isinstance(payload, Mapping):
            raise DisProtCandidateProbeError("manifest must be a mapping")
        accessions = (
            payload.get("accessions")
            or payload.get("accession")
            or payload.get("candidate_accessions")
            or payload.get("candidates")
            or ()
        )
        if isinstance(accessions, Sequence) and not isinstance(accessions, (str, bytes)):
            accessions = tuple(accessions)
        else:
            accessions = (accessions,)
        metadata = payload.get("metadata") or {}
        if not metadata and payload.get("notes") is not None:
            metadata = {"notes": payload.get("notes")}
        return cls(
            accessions=accessions,
            api_base_url=str(payload.get("api_base_url") or DEFAULT_DISPROT_API_BASE_URL),
            metadata=metadata,
        )


@dataclass(frozen=True, slots=True)
class DisProtCandidateProbeRecord:
    accession: str
    probe_url: str
    status: DisProtCandidateProbeStatus
    returned_record_count: int = 0
    matched_record_count: int = 0
    response_size: int | None = None
    returned_accessions: tuple[str, ...] = ()
    matched_accessions: tuple[str, ...] = ()
    returned_disprot_ids: tuple[str, ...] = ()
    matched_disprot_ids: tuple[str, ...] = ()
    returned_records: tuple[dict[str, Any], ...] = ()
    matched_records: tuple[dict[str, Any], ...] = ()
    blocker_reason: str = ""

    def __post_init__(self) -> None:
        accession = _normalize_accession(self.accession)
        if not accession:
            raise DisProtCandidateProbeError("accession must be a valid UniProt accession")
        probe_url = _normalize_text(self.probe_url, "probe_url")
        status = str(self.status).strip()
        if status not in {"positive_hit", "reachable_empty", "blocked"}:
            raise DisProtCandidateProbeError("status must describe a candidate probe outcome")

        returned_records = _coerce_raw_records(self.returned_records)
        matched_records = _coerce_raw_records(self.matched_records)
        returned_accessions = tuple(
            dict.fromkeys(
                accession
                for record in returned_records
                for accession in _record_accessions(record)
            )
        )
        matched_accessions = tuple(
            dict.fromkeys(
                accession for record in matched_records for accession in _record_accessions(record)
            )
        )
        returned_disprot_ids = tuple(
            dict.fromkeys(
                disprot_id
                for record in returned_records
                for disprot_id in _record_disprot_ids(record)
            )
        )
        matched_disprot_ids = tuple(
            dict.fromkeys(
                disprot_id
                for record in matched_records
                for disprot_id in _record_disprot_ids(record)
            )
        )

        if self.returned_record_count != len(returned_records):
            raise DisProtCandidateProbeError(
                "returned_record_count does not match returned_records"
            )
        if self.matched_record_count != len(matched_records):
            raise DisProtCandidateProbeError("matched_record_count does not match matched_records")
        if self.response_size is not None and self.response_size < 0:
            raise DisProtCandidateProbeError("response_size must be non-negative")
        if self.response_size is None and status != "blocked":
            object.__setattr__(self, "response_size", len(returned_records))
        if status == "blocked":
            if (
                returned_records
                or matched_records
                or self.returned_record_count
                or self.matched_record_count
            ):
                raise DisProtCandidateProbeError("blocked probe records cannot carry result rows")
            if not self.blocker_reason:
                raise DisProtCandidateProbeError("blocked probe records require blocker_reason")
        else:
            if self.blocker_reason:
                raise DisProtCandidateProbeError(
                    "non-blocked probe records must not carry blocker_reason"
                )
            if status == "positive_hit" and not matched_records:
                raise DisProtCandidateProbeError(
                    "positive_hit records require at least one matched row"
                )

        object.__setattr__(self, "accession", accession)
        object.__setattr__(self, "probe_url", probe_url)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "returned_records", returned_records)
        object.__setattr__(self, "matched_records", matched_records)
        object.__setattr__(self, "returned_accessions", returned_accessions)
        object.__setattr__(self, "matched_accessions", matched_accessions)
        object.__setattr__(self, "returned_disprot_ids", returned_disprot_ids)
        object.__setattr__(self, "matched_disprot_ids", matched_disprot_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "probe_url": self.probe_url,
            "status": self.status,
            "returned_record_count": self.returned_record_count,
            "matched_record_count": self.matched_record_count,
            "response_size": self.response_size,
            "returned_accessions": list(self.returned_accessions),
            "matched_accessions": list(self.matched_accessions),
            "returned_disprot_ids": list(self.returned_disprot_ids),
            "matched_disprot_ids": list(self.matched_disprot_ids),
            "returned_records": [_clone_jsonish(record) for record in self.returned_records],
            "matched_records": [_clone_jsonish(record) for record in self.matched_records],
            "blocker_reason": self.blocker_reason,
        }


@dataclass(frozen=True, slots=True)
class DisProtCandidateProbeResult:
    manifest: DisProtCandidateProbeManifest
    records: tuple[DisProtCandidateProbeRecord, ...]

    @property
    def positive_accessions(self) -> tuple[str, ...]:
        return tuple(record.accession for record in self.records if record.status == "positive_hit")

    @property
    def reachable_empty_accessions(self) -> tuple[str, ...]:
        return tuple(
            record.accession for record in self.records if record.status == "reachable_empty"
        )

    @property
    def blocked_accessions(self) -> tuple[str, ...]:
        return tuple(record.accession for record in self.records if record.status == "blocked")

    @property
    def positive_count(self) -> int:
        return len(self.positive_accessions)

    @property
    def reachable_empty_count(self) -> int:
        return len(self.reachable_empty_accessions)

    @property
    def blocked_count(self) -> int:
        return len(self.blocked_accessions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest": self.manifest.to_dict(),
            "records": [record.to_dict() for record in self.records],
            "summary": {
                "positive_count": self.positive_count,
                "reachable_empty_count": self.reachable_empty_count,
                "blocked_count": self.blocked_count,
                "requested_accession_count": len(self.manifest.accessions),
            },
            "positive_accessions": list(self.positive_accessions),
            "reachable_empty_accessions": list(self.reachable_empty_accessions),
            "blocked_accessions": list(self.blocked_accessions),
        }


def build_disprot_candidate_probe_manifest(
    accessions: Sequence[str] | str,
    *,
    api_base_url: str = DEFAULT_DISPROT_API_BASE_URL,
    metadata: Mapping[str, Any] | None = None,
) -> DisProtCandidateProbeManifest:
    if isinstance(accessions, Sequence) and not isinstance(accessions, str):
        normalized_accessions = accessions
    else:
        normalized_accessions = (accessions,)
    return DisProtCandidateProbeManifest(
        accessions=normalized_accessions,
        api_base_url=api_base_url,
        metadata=metadata or {},
    )


def normalize_disprot_candidate_probe_manifest(
    manifest: DisProtCandidateProbeManifest | Mapping[str, Any] | Sequence[str] | str,
) -> DisProtCandidateProbeManifest:
    if isinstance(manifest, DisProtCandidateProbeManifest):
        return manifest
    if isinstance(manifest, Mapping):
        return DisProtCandidateProbeManifest.from_mapping(manifest)
    return build_disprot_candidate_probe_manifest(manifest)


def probe_disprot_candidate(
    accession: str,
    *,
    api_base_url: str = DEFAULT_DISPROT_API_BASE_URL,
    opener: Callable[..., Any] = urlopen,
    timeout: float = DISPROT_CANDIDATE_PROBE_TIMEOUT,
) -> DisProtCandidateProbeResult:
    manifest = build_disprot_candidate_probe_manifest(accession, api_base_url=api_base_url)
    return probe_disprot_candidates(manifest, opener=opener, timeout=timeout)


def probe_disprot_candidates(
    manifest: DisProtCandidateProbeManifest | Mapping[str, Any] | Sequence[str] | str,
    *,
    opener: Callable[..., Any] = urlopen,
    timeout: float = DISPROT_CANDIDATE_PROBE_TIMEOUT,
) -> DisProtCandidateProbeResult:
    normalized_manifest = normalize_disprot_candidate_probe_manifest(manifest)
    probe_records: list[DisProtCandidateProbeRecord] = []

    for accession in normalized_manifest.accessions:
        probe_url = _build_probe_url(normalized_manifest.api_base_url, accession)
        request = Request(probe_url, headers={"User-Agent": DISPROT_CANDIDATE_PROBE_USER_AGENT})
        try:
            response = opener(request, timeout=timeout)
            with response as handle:
                payload = json.loads(handle.read().decode("utf-8"))
        except (
            HTTPError,
            URLError,
            OSError,
            json.JSONDecodeError,
            DisProtCandidateProbeError,
        ) as exc:
            probe_records.append(
                DisProtCandidateProbeRecord(
                    accession=accession,
                    probe_url=probe_url,
                    status="blocked",
                    blocker_reason=(
                        f"DisProt request failed for {accession}: {exc}"
                    ),
                )
            )
            continue
        except Exception as exc:  # pragma: no cover - defensive blocker
            probe_records.append(
                DisProtCandidateProbeRecord(
                    accession=accession,
                    probe_url=probe_url,
                    status="blocked",
                    blocker_reason=(
                        "DisProt request failed for "
                        f"{accession}: unexpected runtime failure: {type(exc).__name__}: {exc}"
                    ),
                )
            )
            continue

        returned_records = _payload_to_records(payload)
        matched_records = tuple(
            record for record in returned_records if accession in _record_accessions(record)
        )
        response_size = _response_size(payload, returned_records)
        returned_accessions = tuple(
            dict.fromkeys(
                returned_accession
                for record in returned_records
                for returned_accession in _record_accessions(record)
            )
        )
        matched_accessions = tuple(
            dict.fromkeys(
                matched_accession
                for record in matched_records
                for matched_accession in _record_accessions(record)
            )
        )
        returned_disprot_ids = tuple(
            dict.fromkeys(
                disprot_id
                for record in returned_records
                for disprot_id in _record_disprot_ids(record)
            )
        )
        matched_disprot_ids = tuple(
            dict.fromkeys(
                disprot_id
                for record in matched_records
                for disprot_id in _record_disprot_ids(record)
            )
        )
        probe_records.append(
            DisProtCandidateProbeRecord(
                accession=accession,
                probe_url=probe_url,
                status="positive_hit" if matched_records else "reachable_empty",
                returned_record_count=len(returned_records),
                matched_record_count=len(matched_records),
                response_size=response_size,
                returned_accessions=returned_accessions,
                matched_accessions=matched_accessions,
                returned_disprot_ids=returned_disprot_ids,
                matched_disprot_ids=matched_disprot_ids,
                returned_records=returned_records,
                matched_records=matched_records,
            )
        )

    return DisProtCandidateProbeResult(manifest=normalized_manifest, records=tuple(probe_records))


__all__ = [
    "DEFAULT_DISPROT_API_BASE_URL",
    "DISPROT_CANDIDATE_PROBE_TIMEOUT",
    "DISPROT_CANDIDATE_PROBE_USER_AGENT",
    "DisProtCandidateProbeError",
    "DisProtCandidateProbeManifest",
    "DisProtCandidateProbeRecord",
    "DisProtCandidateProbeResult",
    "DisProtCandidateProbeStatus",
    "build_disprot_candidate_probe_manifest",
    "normalize_disprot_candidate_probe_manifest",
    "probe_disprot_candidate",
    "probe_disprot_candidates",
]

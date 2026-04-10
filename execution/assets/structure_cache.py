from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

StructureAssetKind = Literal["pdb", "mmcif", "alphafold"]
StructureCacheState = Literal["hit", "miss", "checksum_drift"]
StructureChecksumState = Literal["consistent", "missing", "drift"]
StructureFamily = Literal["experimental", "predicted"]

_ASSET_KIND_ALIASES: dict[str, StructureAssetKind] = {
    "pdb": "pdb",
    "mmcif": "mmcif",
    "cif": "mmcif",
    "alphafold": "alphafold",
    "alpha_fold": "alphafold",
    "predicted": "alphafold",
    "prediction": "alphafold",
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


def _first_text(values: Any) -> str:
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            return text
    return ""


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


def _normalize_asset_kind(value: Any) -> StructureAssetKind:
    text = _required_text(value, "asset_kind").replace("-", "_").replace(" ", "_").casefold()
    normalized = _ASSET_KIND_ALIASES.get(text)
    if normalized is None:
        raise ValueError(f"unsupported asset_kind: {value!r}")
    return normalized


def _normalize_identity_fragment(value: Any) -> str:
    return _clean_text(value).replace(" ", "")


def _build_cache_key(asset: StructureCacheAsset) -> str:
    parts = [f"kind={asset.asset_kind}"]
    if asset.asset_kind in {"pdb", "mmcif"}:
        parts.append(f"pdb_id={asset.pdb_id}")
        if asset.selector:
            parts.append(f"selector={asset.selector}")
        if asset.entity_id:
            parts.append(f"entity_id={asset.entity_id}")
        if asset.assembly_id:
            parts.append(f"assembly_id={asset.assembly_id}")
    else:
        parts.append(f"accession={asset.accession}")
        if asset.model_entity_id:
            parts.append(f"model_entity_id={asset.model_entity_id}")
        if asset.sequence_checksum:
            parts.append(f"sequence_checksum={asset.sequence_checksum}")
        if asset.selector:
            parts.append(f"selector={asset.selector}")
    return "structure-cache|" + "|".join(parts)


def _structure_family(asset_kind: StructureAssetKind) -> StructureFamily:
    if asset_kind == "alphafold":
        return "predicted"
    return "experimental"


@dataclass(frozen=True, slots=True)
class StructureCacheAsset:
    source_name: str
    asset_kind: StructureAssetKind
    pointer: str
    pdb_id: str = ""
    selector: str = ""
    entity_id: str = ""
    assembly_id: str = ""
    accession: str = ""
    model_entity_id: str = ""
    sequence_checksum: str = ""
    checksum: str | None = None
    source_record_id: str = ""
    notes: tuple[str, ...] = ()
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", _required_text(self.source_name, "source_name"))
        object.__setattr__(self, "asset_kind", _normalize_asset_kind(self.asset_kind))
        object.__setattr__(self, "pointer", _required_text(self.pointer, "pointer"))
        object.__setattr__(self, "pdb_id", _normalize_identity_fragment(self.pdb_id).upper())
        object.__setattr__(self, "selector", _normalize_identity_fragment(self.selector))
        object.__setattr__(self, "entity_id", _normalize_identity_fragment(self.entity_id))
        object.__setattr__(self, "assembly_id", _normalize_identity_fragment(self.assembly_id))
        object.__setattr__(self, "accession", _normalize_identity_fragment(self.accession).upper())
        object.__setattr__(
            self,
            "model_entity_id",
            _normalize_identity_fragment(self.model_entity_id),
        )
        object.__setattr__(
            self,
            "sequence_checksum",
            _normalize_identity_fragment(self.sequence_checksum),
        )
        object.__setattr__(self, "checksum", _optional_text(self.checksum))
        object.__setattr__(
            self,
            "source_record_id",
            _normalize_identity_fragment(self.source_record_id),
        )
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        if not isinstance(self.provenance, Mapping):
            raise TypeError("provenance must be a mapping")
        object.__setattr__(self, "provenance", dict(self.provenance))
        if self.asset_kind in {"pdb", "mmcif"} and not self.pdb_id:
            raise ValueError("pdb/mmcif assets require pdb_id")
        if self.asset_kind == "alphafold" and not self.accession:
            raise ValueError("alphafold assets require accession")

    @property
    def structure_family(self) -> StructureFamily:
        return _structure_family(self.asset_kind)

    @property
    def cache_key(self) -> str:
        return _build_cache_key(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "asset_kind": self.asset_kind,
            "pointer": self.pointer,
            "pdb_id": self.pdb_id,
            "selector": self.selector or None,
            "entity_id": self.entity_id or None,
            "assembly_id": self.assembly_id or None,
            "accession": self.accession or None,
            "model_entity_id": self.model_entity_id or None,
            "sequence_checksum": self.sequence_checksum or None,
            "checksum": self.checksum,
            "source_record_id": self.source_record_id or None,
            "notes": list(self.notes),
            "provenance": _json_ready(dict(self.provenance)),
            "structure_family": self.structure_family,
            "cache_key": self.cache_key,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> StructureCacheAsset:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            source_name=_first_text(payload.get("source_name") or payload.get("source")),
            asset_kind=payload.get("asset_kind")
            or payload.get("kind")
            or payload.get("artifact_kind")
            or "pdb",
            pointer=payload.get("pointer") or payload.get("path") or payload.get("uri") or "",
            pdb_id=payload.get("pdb_id") or payload.get("pdb") or payload.get("pdbId") or "",
            selector=payload.get("selector")
            or payload.get("selection")
            or payload.get("chain_id")
            or payload.get("chainId")
            or "",
            entity_id=payload.get("entity_id") or payload.get("entityId") or "",
            assembly_id=payload.get("assembly_id") or payload.get("assemblyId") or "",
            accession=_first_text(
                payload.get("accession")
                or payload.get("uniprot_accession")
                or payload.get("uniprotAccession")
                or payload.get("uniprot")
            ),
            model_entity_id=payload.get("model_entity_id")
            or payload.get("model_id")
            or payload.get("modelId")
            or "",
            sequence_checksum=payload.get("sequence_checksum")
            or payload.get("sequenceChecksum")
            or "",
            checksum=payload.get("checksum")
            or payload.get("digest")
            or payload.get("payload_sha256"),
            source_record_id=payload.get("source_record_id")
            or payload.get("record_id")
            or payload.get("sourceRecordId")
            or payload.get("identifier")
            or "",
            notes=payload.get("notes") or payload.get("note") or (),
            provenance=payload.get("provenance") or {},
        )


@dataclass(frozen=True, slots=True)
class StructureCacheEntry:
    cache_key: str
    asset_kind: StructureAssetKind
    structure_family: StructureFamily
    cache_state: StructureCacheState
    checksum_state: StructureChecksumState
    asset_count: int
    source_names: tuple[str, ...] = ()
    source_record_ids: tuple[str, ...] = ()
    pointers: tuple[str, ...] = ()
    observed_checksums: tuple[str, ...] = ()
    checksum: str | None = None
    pdb_id: str = ""
    selector: str = ""
    entity_id: str = ""
    assembly_id: str = ""
    accession: str = ""
    model_entity_id: str = ""
    sequence_checksum: str = ""
    assets: tuple[StructureCacheAsset, ...] = ()
    notes: tuple[str, ...] = ()
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "cache_key", _required_text(self.cache_key, "cache_key"))
        object.__setattr__(self, "asset_kind", _normalize_asset_kind(self.asset_kind))
        object.__setattr__(self, "source_names", _dedupe_text(self.source_names))
        object.__setattr__(self, "source_record_ids", _dedupe_text(self.source_record_ids))
        object.__setattr__(self, "pointers", _dedupe_text(self.pointers))
        object.__setattr__(self, "observed_checksums", _dedupe_text(self.observed_checksums))
        object.__setattr__(self, "pdb_id", _normalize_identity_fragment(self.pdb_id).upper())
        object.__setattr__(self, "selector", _normalize_identity_fragment(self.selector))
        object.__setattr__(self, "entity_id", _normalize_identity_fragment(self.entity_id))
        object.__setattr__(self, "assembly_id", _normalize_identity_fragment(self.assembly_id))
        object.__setattr__(self, "accession", _normalize_identity_fragment(self.accession).upper())
        object.__setattr__(
            self,
            "model_entity_id",
            _normalize_identity_fragment(self.model_entity_id),
        )
        object.__setattr__(
            self,
            "sequence_checksum",
            _normalize_identity_fragment(self.sequence_checksum),
        )
        object.__setattr__(self, "checksum", _optional_text(self.checksum))
        object.__setattr__(self, "assets", tuple(self.assets))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        if not isinstance(self.provenance, Mapping):
            raise TypeError("provenance must be a mapping")
        object.__setattr__(self, "provenance", dict(self.provenance))
        if self.asset_count != len(self.assets):
            raise ValueError("asset_count must match the number of assets")
        if self.cache_state not in {"hit", "miss", "checksum_drift"}:
            raise ValueError(f"unsupported cache_state: {self.cache_state!r}")
        if self.checksum_state not in {"consistent", "missing", "drift"}:
            raise ValueError(f"unsupported checksum_state: {self.checksum_state!r}")

    @property
    def reusable(self) -> bool:
        return self.cache_state == "hit"

    def to_dict(self) -> dict[str, Any]:
        return {
            "cache_key": self.cache_key,
            "asset_kind": self.asset_kind,
            "structure_family": self.structure_family,
            "cache_state": self.cache_state,
            "checksum_state": self.checksum_state,
            "asset_count": self.asset_count,
            "source_names": list(self.source_names),
            "source_record_ids": list(self.source_record_ids),
            "pointers": list(self.pointers),
            "observed_checksums": list(self.observed_checksums),
            "checksum": self.checksum,
            "pdb_id": self.pdb_id or None,
            "selector": self.selector or None,
            "entity_id": self.entity_id or None,
            "assembly_id": self.assembly_id or None,
            "accession": self.accession or None,
            "model_entity_id": self.model_entity_id or None,
            "sequence_checksum": self.sequence_checksum or None,
            "assets": [asset.to_dict() for asset in self.assets],
            "notes": list(self.notes),
            "provenance": _json_ready(dict(self.provenance)),
            "reusable": self.reusable,
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> StructureCacheEntry:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        assets_payload = payload.get("assets")
        if assets_payload:
            if isinstance(assets_payload, Sequence) and not isinstance(
                assets_payload,
                (str, bytes),
            ):
                assets = tuple(
                    item
                    if isinstance(item, StructureCacheAsset)
                    else StructureCacheAsset.from_mapping(item)
                    for item in assets_payload
                )
            else:
                raise TypeError("assets must be a sequence")
        else:
            assets = (StructureCacheAsset.from_mapping(payload),)
        return _build_entry(assets, cache_key=payload.get("cache_key"))


@dataclass(frozen=True, slots=True)
class StructureCacheCatalog:
    cache_id: str
    entries: tuple[StructureCacheEntry, ...]
    notes: tuple[str, ...] = ()
    schema_version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "cache_id", _required_text(self.cache_id, "cache_id"))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        if self.schema_version < 1:
            raise ValueError("schema_version must be >= 1")
        entries_by_key: dict[str, StructureCacheEntry] = {}
        for entry in self.entries:
            if not isinstance(entry, StructureCacheEntry):
                raise TypeError("entries must contain StructureCacheEntry objects")
            if entry.cache_key in entries_by_key:
                raise ValueError(f"duplicate cache_key: {entry.cache_key}")
            entries_by_key[entry.cache_key] = entry
        object.__setattr__(self, "entries", tuple(entries_by_key.values()))

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    @property
    def hit_count(self) -> int:
        return sum(1 for entry in self.entries if entry.cache_state == "hit")

    @property
    def miss_count(self) -> int:
        return sum(1 for entry in self.entries if entry.cache_state == "miss")

    @property
    def checksum_drift_count(self) -> int:
        return sum(1 for entry in self.entries if entry.cache_state == "checksum_drift")

    @property
    def reusable_count(self) -> int:
        return self.hit_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "cache_id": self.cache_id,
            "entry_count": self.entry_count,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "checksum_drift_count": self.checksum_drift_count,
            "reusable_count": self.reusable_count,
            "notes": list(self.notes),
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> StructureCacheCatalog:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        entries = tuple(
            item
            if isinstance(item, StructureCacheEntry)
            else StructureCacheEntry.from_mapping(item)
            for item in (payload.get("entries") or ())
        )
        return cls(
            cache_id=payload.get("cache_id") or payload.get("catalog_id") or "structure-cache",
            entries=entries,
            notes=payload.get("notes") or (),
            schema_version=int(payload.get("schema_version") or 1),
        )


def normalize_structure_assets(
    assets: Sequence[StructureCacheAsset | Mapping[str, Any]],
) -> tuple[StructureCacheAsset, ...]:
    normalized: list[StructureCacheAsset] = []
    for asset in assets:
        normalized.append(
            asset
            if isinstance(asset, StructureCacheAsset)
            else StructureCacheAsset.from_mapping(asset)
        )
    return tuple(normalized)


def _build_entry(
    assets: Sequence[StructureCacheAsset],
    *,
    cache_key: Any | None = None,
) -> StructureCacheEntry:
    if not assets:
        raise ValueError("assets must not be empty")

    primary = assets[0]
    observed_checksums = _dedupe_text(asset.checksum for asset in assets if asset.checksum)
    missing_checksum_count = sum(1 for asset in assets if not asset.checksum)
    source_names = _dedupe_text(asset.source_name for asset in assets)
    source_record_ids = _dedupe_text(
        asset.source_record_id for asset in assets if asset.source_record_id
    )
    pointers = _dedupe_text(asset.pointer for asset in assets)
    extra_notes: tuple[str, ...] = ()
    if len(observed_checksums) > 1:
        extra_notes = ("checksum drift detected",)
    elif not observed_checksums:
        extra_notes = ("missing checksum; cache reuse cannot be confirmed",)
    elif missing_checksum_count:
        extra_notes = ("one or more source copies are missing checksums",)
    aggregated_notes: list[str] = []
    for asset in assets:
        aggregated_notes.extend(asset.notes)
    notes = _dedupe_text((*aggregated_notes, *extra_notes))

    if len(observed_checksums) > 1:
        cache_state: StructureCacheState = "checksum_drift"
        checksum_state: StructureChecksumState = "drift"
        checksum = None
    elif not observed_checksums:
        cache_state = "miss"
        checksum_state = "missing"
        checksum = None
    else:
        cache_state = "hit"
        checksum_state = "consistent"
        checksum = observed_checksums[0]

    return StructureCacheEntry(
        cache_key=_clean_text(cache_key) or primary.cache_key,
        asset_kind=primary.asset_kind,
        structure_family=primary.structure_family,
        cache_state=cache_state,
        checksum_state=checksum_state,
        asset_count=len(assets),
        source_names=source_names,
        source_record_ids=source_record_ids,
        pointers=pointers,
        observed_checksums=observed_checksums,
        checksum=checksum,
        pdb_id=primary.pdb_id,
        selector=primary.selector,
        entity_id=primary.entity_id,
        assembly_id=primary.assembly_id,
        accession=primary.accession,
        model_entity_id=primary.model_entity_id,
        sequence_checksum=primary.sequence_checksum,
        assets=tuple(assets),
        notes=notes,
        provenance={
            "source_names": list(source_names),
            "source_record_ids": list(source_record_ids),
            "pointers": list(pointers),
            "observed_checksums": list(observed_checksums),
            "asset_kinds": [primary.asset_kind],
        },
    )


def build_structure_cache(
    assets: Sequence[StructureCacheAsset | Mapping[str, Any]],
    *,
    cache_id: str = "structure-cache",
    notes: Sequence[str] = (),
) -> StructureCacheCatalog:
    normalized_assets = normalize_structure_assets(assets)
    grouped: dict[str, list[StructureCacheAsset]] = {}
    order: list[str] = []
    for asset in normalized_assets:
        key = asset.cache_key
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(asset)
    entries = tuple(_build_entry(grouped[key], cache_key=key) for key in order)
    return StructureCacheCatalog(cache_id=cache_id, entries=entries, notes=notes)


__all__ = [
    "StructureAssetKind",
    "StructureCacheAsset",
    "StructureCacheCatalog",
    "StructureCacheEntry",
    "StructureCacheState",
    "StructureChecksumState",
    "StructureFamily",
    "build_structure_cache",
    "normalize_structure_assets",
]

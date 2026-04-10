from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Literal

from core.storage.package_manifest import (
    ArtifactKind,
    PackageManifestArtifactPointer,
)

RetentionTier = Literal["preload", "cache", "lazy"]
RetentionState = Literal["retain", "refresh", "expire"]

_PRELOAD_KINDS = {
    "feature",
    "embedding",
}
_CACHE_KINDS = {
    "structure",
    "coordinates",
    "map",
    "alignment",
    "table",
    "evidence_text",
    "diagram",
}
_LAZY_KINDS = {
    "other",
}
_PROTECTED_SELECTORS = {
    "package_manifest",
    "raw_manifest",
    "raw_manifest_lineage",
    "pinned_manifest",
    "release_manifest",
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


def _normalize_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _optional_text(value)


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _normalize_tier(value: Any) -> RetentionTier:
    text = _required_text(value, "retention_tier").replace("-", "_").replace(" ", "_").casefold()
    if text not in {"preload", "cache", "lazy"}:
        raise ValueError("retention_tier must be preload, cache, or lazy")
    return text  # type: ignore[return-value]


def _kind_tier(kind: ArtifactKind | str) -> RetentionTier:
    normalized = _clean_text(kind).replace("-", "_").replace(" ", "_").casefold()
    if normalized in _PRELOAD_KINDS:
        return "preload"
    if normalized in _CACHE_KINDS:
        return "cache"
    if normalized in _LAZY_KINDS:
        return "lazy"
    return "lazy"


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    return _clean_text(value).casefold() in {"1", "true", "yes", "y", "on"}


def _coerce_asset(asset: RetentionAsset | Mapping[str, Any]) -> RetentionAsset:
    if isinstance(asset, RetentionAsset):
        return asset
    return RetentionAsset.from_mapping(asset)


@dataclass(frozen=True, slots=True)
class RetentionAsset:
    artifact_kind: ArtifactKind | str
    pointer: str
    selector: str | None = None
    source_name: str | None = None
    source_record_id: str | None = None
    tier: RetentionTier | None = None
    expires_at: str | None = None
    pinned: bool = False
    protected: bool = False
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_kind", _clean_text(self.artifact_kind))
        object.__setattr__(self, "pointer", _required_text(self.pointer, "pointer"))
        object.__setattr__(self, "selector", _optional_text(self.selector))
        object.__setattr__(self, "source_name", _optional_text(self.source_name))
        object.__setattr__(self, "source_record_id", _optional_text(self.source_record_id))
        object.__setattr__(self, "tier", _normalize_tier(self.tier) if self.tier else None)
        object.__setattr__(self, "expires_at", _normalize_timestamp(self.expires_at))
        object.__setattr__(self, "pinned", bool(self.pinned))
        object.__setattr__(self, "protected", bool(self.protected))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        if not self.artifact_kind:
            raise ValueError("artifact_kind must not be empty")

    @property
    def effective_tier(self) -> RetentionTier:
        return self.tier or _kind_tier(self.artifact_kind)

    @property
    def expired(self) -> bool:
        if self.expires_at is not None:
            expires_at = _parse_datetime(self.expires_at)
            if expires_at is None:
                return True
            return expires_at < datetime.now(tz=UTC)
        return False

    @property
    def retention_state(self) -> RetentionState:
        if self.protected or self.pinned:
            return "retain"
        if self.expired:
            return "expire"
        return "retain"

    def to_pointer(self) -> PackageManifestArtifactPointer:
        return PackageManifestArtifactPointer(
            artifact_kind=self.artifact_kind,
            pointer=self.pointer,
            selector=self.selector,
            source_name=self.source_name,
            source_record_id=self.source_record_id,
            notes=self.notes,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_kind": self.artifact_kind,
            "pointer": self.pointer,
            "selector": self.selector,
            "source_name": self.source_name,
            "source_record_id": self.source_record_id,
            "tier": self.effective_tier,
            "expires_at": self.expires_at,
            "pinned": self.pinned,
            "protected": self.protected,
            "retention_state": self.retention_state,
            "notes": list(self.notes),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> RetentionAsset:
        if not isinstance(value, Mapping):
            raise TypeError("value must be a mapping")
        return cls(
            artifact_kind=value.get("artifact_kind") or value.get("kind") or "other",
            pointer=value.get("pointer") or value.get("uri") or value.get("path") or "",
            selector=value.get("selector") or value.get("selection"),
            source_name=value.get("source_name") or value.get("source"),
            source_record_id=value.get("source_record_id")
            or value.get("record_id")
            or value.get("identifier"),
            tier=value.get("tier") or value.get("retention_tier"),
            expires_at=value.get("expires_at") or value.get("expiry"),
            pinned=_truthy(value.get("pinned") or value.get("pinning")),
            protected=_truthy(value.get("protected") or value.get("protected_artifact")),
            notes=value.get("notes") or value.get("note") or (),
        )


@dataclass(frozen=True, slots=True)
class RetentionDecision:
    asset: RetentionAsset
    state: RetentionState
    reason: str
    expiry_policy: str = ""
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", _required_text(self.state, "state").casefold())
        object.__setattr__(self, "reason", _required_text(self.reason, "reason"))
        object.__setattr__(self, "expiry_policy", _optional_text(self.expiry_policy) or "")
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        if self.state not in {"retain", "refresh", "expire"}:
            raise ValueError("state must be retain, refresh, or expire")

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset": self.asset.to_dict(),
            "state": self.state,
            "reason": self.reason,
            "expiry_policy": self.expiry_policy or None,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    policy_id: str
    assets: tuple[RetentionAsset, ...]
    expiry_window_days: int = 30
    protected_selectors: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _required_text(self.policy_id, "policy_id"))
        object.__setattr__(self, "assets", tuple(self.assets))
        object.__setattr__(self, "expiry_window_days", int(self.expiry_window_days))
        object.__setattr__(self, "protected_selectors", _dedupe_text(self.protected_selectors))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        if self.expiry_window_days < 0:
            raise ValueError("expiry_window_days must be non-negative")
        if not self.assets:
            raise ValueError("policy must include at least one asset")

    @property
    def asset_count(self) -> int:
        return len(self.assets)

    @property
    def preload_assets(self) -> tuple[RetentionAsset, ...]:
        return tuple(asset for asset in self.assets if asset.effective_tier == "preload")

    @property
    def cache_assets(self) -> tuple[RetentionAsset, ...]:
        return tuple(asset for asset in self.assets if asset.effective_tier == "cache")

    @property
    def lazy_assets(self) -> tuple[RetentionAsset, ...]:
        return tuple(asset for asset in self.assets if asset.effective_tier == "lazy")

    @property
    def protected_assets(self) -> tuple[RetentionAsset, ...]:
        protected_selectors = {selector.casefold() for selector in self.protected_selectors}
        return tuple(
            asset
            for asset in self.assets
            if asset.protected
            or asset.pinned
            or _clean_text(asset.selector).casefold() in protected_selectors
            or _clean_text(asset.selector).casefold() in _PROTECTED_SELECTORS
        )

    def decide(self, asset: RetentionAsset) -> RetentionDecision:
        normalized_asset = _coerce_asset(asset)
        selector = _clean_text(normalized_asset.selector).casefold()
        protected_selectors = {item.casefold() for item in self.protected_selectors}
        if normalized_asset.protected or normalized_asset.pinned:
            return RetentionDecision(
                asset=normalized_asset,
                state="retain",
                reason="pinned or protected artifact must not expire",
                expiry_policy="protected",
                notes=("protected artifact",),
            )
        if selector in protected_selectors or selector in _PROTECTED_SELECTORS:
            return RetentionDecision(
                asset=normalized_asset,
                state="retain",
                reason="protected artifact must not expire",
                expiry_policy="protected",
                notes=("protected artifact",),
            )
        if normalized_asset.pinned:
            return RetentionDecision(
                asset=normalized_asset,
                state="retain",
                reason="pinned asset is retained",
                expiry_policy="pinned",
                notes=("pinned asset",),
            )
        if normalized_asset.expired:
            return RetentionDecision(
                asset=normalized_asset,
                state="expire",
                reason="asset expired before the current retention check",
                expiry_policy=f"expiry_window={self.expiry_window_days}d",
                notes=("expired asset",),
            )
        if normalized_asset.effective_tier == "preload":
            return RetentionDecision(
                asset=normalized_asset,
                state="retain",
                reason="preload asset belongs in the hot path",
                expiry_policy="hot-path",
                notes=("preload asset",),
            )
        if normalized_asset.effective_tier == "cache":
            return RetentionDecision(
                asset=normalized_asset,
                state="refresh",
                reason="cache asset should be refreshed when stale",
                expiry_policy=f"refresh-window={self.expiry_window_days}d",
                notes=("cache asset",),
            )
        return RetentionDecision(
            asset=normalized_asset,
            state="refresh",
            reason="lazy asset is deferred until selected",
            expiry_policy="lazy",
            notes=("lazy asset",),
        )

    def classify(self, asset: RetentionAsset | Mapping[str, Any]) -> RetentionDecision:
        normalized_asset = _coerce_asset(asset)
        return self.decide(normalized_asset)

    def classify_many(
        self,
        assets: Iterable[RetentionAsset | Mapping[str, Any]],
    ) -> tuple[RetentionDecision, ...]:
        return tuple(self.classify(asset) for asset in assets)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "asset_count": self.asset_count,
            "expiry_window_days": self.expiry_window_days,
            "protected_selectors": list(self.protected_selectors),
            "preload_assets": [asset.to_dict() for asset in self.preload_assets],
            "cache_assets": [asset.to_dict() for asset in self.cache_assets],
            "lazy_assets": [asset.to_dict() for asset in self.lazy_assets],
            "protected_assets": [asset.to_dict() for asset in self.protected_assets],
            "notes": list(self.notes),
        }


def build_retention_policy(
    assets: Sequence[RetentionAsset | Mapping[str, Any]],
    *,
    policy_id: str = "retention-policy:v1",
    expiry_window_days: int = 30,
    protected_selectors: Sequence[str] = (),
    notes: Sequence[str] = (),
) -> RetentionPolicy:
    return RetentionPolicy(
        policy_id=policy_id,
        assets=tuple(
            asset if isinstance(asset, RetentionAsset) else RetentionAsset.from_mapping(asset)
            for asset in assets
        ),
        expiry_window_days=expiry_window_days,
        protected_selectors=tuple(protected_selectors),
        notes=tuple(notes),
    )


__all__ = [
    "RetentionAsset",
    "RetentionDecision",
    "RetentionPolicy",
    "RetentionState",
    "RetentionTier",
    "build_retention_policy",
]

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from core.procurement.source_release_manifest import (
    SourceReleaseManifest,
    validate_source_release_manifest_payload,
)

SupplementalTargetFamily = Literal["motif", "disorder", "pathway", "related"]
SupplementalExtractionMode = Literal["html_document", "search_results", "api_json", "download_text"]
SupplementalRunStatus = Literal["approved", "blocked"]
SupplementalBlockerCode = Literal[
    "target_not_registered",
    "target_disabled",
    "unsupported_extraction_mode",
    "missing_release_pin",
    "scope_too_broad",
]

_ALLOWED_EXTRACTION_MODES = frozenset(
    {"html_document", "search_results", "api_json", "download_text"}
)
_BROAD_SCOPE_MARKERS = ("*", "all pages", "crawl", "crawler", "spider", "sitewide", "unbounded")


def _clean_text(value: object | None) -> str:
    return str(value or "").strip()


def _clean_optional_text(value: object | None) -> str | None:
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


def _clean_list(values: Any) -> tuple[str, ...]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in _iter_values(values):
        text = _clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return tuple(cleaned)


def _normalize_family(value: object | None) -> SupplementalTargetFamily:
    family = _clean_text(value).casefold()
    if family not in {"motif", "disorder", "pathway", "related"}:
        raise ValueError("family must be one of: motif, disorder, pathway, related")
    return family  # type: ignore[return-value]


def _normalize_extraction_mode(value: object | None) -> SupplementalExtractionMode:
    mode = _clean_text(value).replace("-", "_").replace(" ", "_").casefold()
    aliases = {
        "html": "html_document",
        "document": "html_document",
        "page": "html_document",
        "pages": "html_document",
        "search": "search_results",
        "results": "search_results",
        "api": "api_json",
        "endpoint": "api_json",
        "json": "api_json",
        "download": "download_text",
        "text": "download_text",
    }
    normalized = aliases.get(mode, mode)
    if normalized not in _ALLOWED_EXTRACTION_MODES:
        raise ValueError(
            "extraction_mode must be one of: html_document, search_results, api_json, download_text"
        )
    return normalized  # type: ignore[return-value]


def _is_broad_scope(scope: str) -> bool:
    lowered = scope.casefold()
    return any(marker in lowered for marker in _BROAD_SCOPE_MARKERS)


def _coerce_source_release(
    value: SourceReleaseManifest | Mapping[str, Any] | None,
) -> SourceReleaseManifest | None:
    if value is None:
        return None
    if isinstance(value, SourceReleaseManifest):
        return value
    if isinstance(value, Mapping):
        return validate_source_release_manifest_payload(dict(value))
    raise TypeError("source_release must be a SourceReleaseManifest or mapping")


def _coerce_accession_lane_request(
    accession: str,
    value: SupplementalScrapeRunRequest | Mapping[str, Any] | object,
    *,
    source_release: SourceReleaseManifest | Mapping[str, Any] | None = None,
) -> SupplementalScrapeRunRequest:
    resolved_source_release = _coerce_source_release(source_release)
    if isinstance(value, SupplementalScrapeRunRequest):
        request = value
    elif isinstance(value, Mapping):
        payload = dict(value)
        if not payload.get("scope") and not payload.get("query") and not payload.get(
            "identifier"
        ):
            payload["scope"] = accession
        if resolved_source_release is not None and "source_release" not in payload:
            payload["source_release"] = resolved_source_release
        request = SupplementalScrapeRunRequest.from_mapping(payload)
    else:
        request = SupplementalScrapeRunRequest(
            target_id=str(value),
            extraction_mode="html_document",
            scope=accession,
            source_release=resolved_source_release,
        )

    if not request.scope:
        request = SupplementalScrapeRunRequest(
            target_id=request.target_id,
            extraction_mode=request.extraction_mode,
            scope=accession,
            source_release=request.source_release,
            source_locator=request.source_locator,
            provenance=request.provenance,
            reproducibility_metadata=request.reproducibility_metadata,
        )
    return request


@dataclass(frozen=True, slots=True)
class SupplementalScrapeBlocker:
    code: SupplementalBlockerCode
    message: str
    detail: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "message", _clean_text(self.message))
        object.__setattr__(self, "detail", _clean_optional_text(self.detail))

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class SupplementalScrapeTarget:
    target_id: str
    source_name: str
    family: SupplementalTargetFamily
    source_locator_prefix: str
    allowed_extraction_modes: tuple[SupplementalExtractionMode, ...]
    required_release_pin: bool = True
    provenance_rules: tuple[str, ...] = ()
    reproducibility_rules: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    enabled: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_id", _clean_text(self.target_id))
        object.__setattr__(self, "source_name", _clean_text(self.source_name))
        object.__setattr__(self, "family", _normalize_family(self.family))
        object.__setattr__(
            self,
            "source_locator_prefix",
            _clean_text(self.source_locator_prefix),
        )
        modes = tuple(_normalize_extraction_mode(mode) for mode in self.allowed_extraction_modes)
        if not modes:
            raise ValueError("allowed_extraction_modes must not be empty")
        object.__setattr__(self, "allowed_extraction_modes", modes)
        object.__setattr__(self, "required_release_pin", bool(self.required_release_pin))
        object.__setattr__(self, "provenance_rules", _clean_list(self.provenance_rules))
        object.__setattr__(self, "reproducibility_rules", _clean_list(self.reproducibility_rules))
        object.__setattr__(self, "notes", _clean_list(self.notes))
        object.__setattr__(self, "enabled", bool(self.enabled))

        if not self.target_id:
            raise ValueError("target_id must not be empty")
        if not self.source_name:
            raise ValueError("source_name must not be empty")
        if not self.source_locator_prefix:
            raise ValueError("source_locator_prefix must not be empty")

        unsupported = set(modes) - _ALLOWED_EXTRACTION_MODES
        if unsupported:
            raise ValueError(
                "allowed_extraction_modes contain unsupported values: "
                + ", ".join(sorted(unsupported))
            )

    def allows_mode(self, extraction_mode: str) -> bool:
        return _normalize_extraction_mode(extraction_mode) in self.allowed_extraction_modes

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "source_name": self.source_name,
            "family": self.family,
            "source_locator_prefix": self.source_locator_prefix,
            "allowed_extraction_modes": list(self.allowed_extraction_modes),
            "required_release_pin": self.required_release_pin,
            "provenance_rules": list(self.provenance_rules),
            "reproducibility_rules": list(self.reproducibility_rules),
            "notes": list(self.notes),
            "enabled": self.enabled,
        }


@dataclass(frozen=True, slots=True)
class SupplementalScrapeRunRequest:
    target_id: str
    extraction_mode: str
    scope: str
    source_release: SourceReleaseManifest | Mapping[str, Any] | None = None
    source_locator: str | None = None
    provenance: tuple[str, ...] = ()
    reproducibility_metadata: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_id", _clean_text(self.target_id))
        object.__setattr__(
            self,
            "extraction_mode",
            _normalize_extraction_mode(self.extraction_mode),
        )
        object.__setattr__(self, "scope", _clean_text(self.scope))
        object.__setattr__(self, "source_locator", _clean_optional_text(self.source_locator))
        object.__setattr__(self, "provenance", _clean_list(self.provenance))
        object.__setattr__(
            self,
            "reproducibility_metadata",
            _clean_list(self.reproducibility_metadata),
        )

        if not self.target_id:
            raise ValueError("target_id must not be empty")
        if not self.scope:
            raise ValueError("scope must not be empty")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> SupplementalScrapeRunRequest:
        if not isinstance(value, Mapping):
            raise TypeError("request must be a mapping")
        return cls(
            target_id=value.get("target_id") or value.get("target") or value.get("id") or "",
            extraction_mode=value.get("extraction_mode")
            or value.get("mode")
            or value.get("retrieval_mode")
            or "html_document",
            scope=value.get("scope") or value.get("query") or value.get("identifier") or "",
            source_release=value.get("source_release") or value.get("release_manifest"),
            source_locator=value.get("source_locator") or value.get("url") or None,
            provenance=_iter_values(value.get("provenance") or value.get("evidence")),
            reproducibility_metadata=_iter_values(
                value.get("reproducibility_metadata")
                or value.get("reproducibility")
                or value.get("metadata")
            ),
        )

    @property
    def request_id(self) -> str:
        release_id = (
            self.source_release.manifest_id
            if isinstance(self.source_release, SourceReleaseManifest)
            else "unreleased"
        )
        return f"{self.target_id}:{release_id}:{self.extraction_mode}:{self.scope}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "target_id": self.target_id,
            "extraction_mode": self.extraction_mode,
            "scope": self.scope,
            "source_release": (
                self.source_release.to_dict()
                if isinstance(self.source_release, SourceReleaseManifest)
                else dict(self.source_release)
                if isinstance(self.source_release, Mapping)
                else None
            ),
            "source_locator": self.source_locator,
            "provenance": list(self.provenance),
            "reproducibility_metadata": list(self.reproducibility_metadata),
        }


@dataclass(frozen=True, slots=True)
class SupplementalScrapeRunResult:
    status: SupplementalRunStatus
    reason: str
    request: SupplementalScrapeRunRequest
    target: SupplementalScrapeTarget | None = None
    blocker: SupplementalScrapeBlocker | None = None
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.status == "approved"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "request": self.request.to_dict(),
            "target": None if self.target is None else self.target.to_dict(),
            "blocker": None if self.blocker is None else self.blocker.to_dict(),
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class SupplementalScrapeBlockedTarget:
    target_id: str
    blocker: SupplementalScrapeBlocker
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "target_id", _clean_text(self.target_id))
        object.__setattr__(self, "notes", _clean_list(self.notes))
        if not self.target_id:
            raise ValueError("target_id must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "blocker": self.blocker.to_dict(),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class SupplementalScrapeRegistry:
    registry_id: str
    approved_targets: tuple[SupplementalScrapeTarget, ...]
    blocked_targets: tuple[SupplementalScrapeBlockedTarget, ...] = ()
    provenance_rules: tuple[str, ...] = ()
    reproducibility_rules: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "registry_id", _clean_text(self.registry_id))
        object.__setattr__(self, "provenance_rules", _clean_list(self.provenance_rules))
        object.__setattr__(self, "reproducibility_rules", _clean_list(self.reproducibility_rules))
        if not self.registry_id:
            raise ValueError("registry_id must not be empty")

        approved: dict[str, SupplementalScrapeTarget] = {}
        for target in self.approved_targets:
            if target.target_id in approved:
                raise ValueError(f"duplicate approved target_id: {target.target_id}")
            approved[target.target_id] = target
        object.__setattr__(self, "approved_targets", tuple(approved.values()))

        blocked: dict[str, SupplementalScrapeBlockedTarget] = {}
        for target in self.blocked_targets:
            if target.target_id in blocked:
                raise ValueError(f"duplicate blocked target_id: {target.target_id}")
            blocked[target.target_id] = target
        object.__setattr__(self, "blocked_targets", tuple(blocked.values()))

    @property
    def approved_target_ids(self) -> tuple[str, ...]:
        return tuple(target.target_id for target in self.approved_targets)

    def get_target(self, target_id: str) -> SupplementalScrapeTarget | None:
        normalized = _clean_text(target_id)
        for target in self.approved_targets:
            if target.target_id == normalized:
                return target
        return None

    def plan_run(
        self,
        request: SupplementalScrapeRunRequest | Mapping[str, Any],
    ) -> SupplementalScrapeRunResult:
        normalized_request = _coerce_request(request)
        target = self.get_target(normalized_request.target_id)
        blocked_target = self._blocked_target(normalized_request.target_id)

        if blocked_target is not None:
            return self._blocked_result(
                request=normalized_request,
                blocker=blocked_target.blocker,
                reason="target_blocked",
            )

        if target is None:
            return self._blocked_result(
                request=normalized_request,
                blocker=SupplementalScrapeBlocker(
                    code="target_not_registered",
                    message="supplemental target is not in the approved allowlist",
                    detail=normalized_request.target_id,
                ),
                reason="target_not_registered",
            )

        if not target.enabled:
            return self._blocked_result(
                request=normalized_request,
                blocker=SupplementalScrapeBlocker(
                    code="target_disabled",
                    message="supplemental target is registered but disabled",
                    detail=target.target_id,
                ),
                reason="target_disabled",
                target=target,
            )

        if not target.allows_mode(normalized_request.extraction_mode):
            return self._blocked_result(
                request=normalized_request,
                blocker=SupplementalScrapeBlocker(
                    code="unsupported_extraction_mode",
                    message="requested extraction mode is not approved for this target",
                    detail=normalized_request.extraction_mode,
                ),
                reason="unsupported_extraction_mode",
                target=target,
            )

        if _is_broad_scope(normalized_request.scope):
            return self._blocked_result(
                request=normalized_request,
                blocker=SupplementalScrapeBlocker(
                    code="scope_too_broad",
                    message="supplemental scrape scope is too broad for the allowlist",
                    detail=normalized_request.scope,
                ),
                reason="scope_too_broad",
                target=target,
            )

        try:
            source_release = _coerce_source_release(normalized_request.source_release)
        except (TypeError, ValueError) as exc:
            return self._blocked_result(
                request=normalized_request,
                blocker=SupplementalScrapeBlocker(
                    code="missing_release_pin",
                    message="supplemental scrape runs must pin a source release manifest",
                    detail=str(exc),
                ),
                reason="missing_release_pin",
                target=target,
            )
        if target.required_release_pin and source_release is None:
            return self._blocked_result(
                request=normalized_request,
                blocker=SupplementalScrapeBlocker(
                    code="missing_release_pin",
                    message="supplemental scrape runs must pin a source release manifest",
                    detail=normalized_request.target_id,
                ),
                reason="missing_release_pin",
                target=target,
            )

        provenance = {
            "registry_id": self.registry_id,
            "target_id": target.target_id,
            "source_name": target.source_name,
            "family": target.family,
            "extraction_mode": normalized_request.extraction_mode,
            "scope": normalized_request.scope,
            "source_locator_prefix": target.source_locator_prefix,
            "source_release_manifest_id": (
                None if source_release is None else source_release.manifest_id
            ),
            "source_release_version": (
                None if source_release is None else source_release.release_version
            ),
            "source_release_date": None if source_release is None else source_release.release_date,
            "source_release_locator": (
                None if source_release is None else source_release.source_locator
            ),
            "request_id": normalized_request.request_id,
            "request_provenance": list(normalized_request.provenance),
            "request_reproducibility_metadata": list(
                normalized_request.reproducibility_metadata
            ),
            "target_provenance_rules": list(target.provenance_rules),
            "target_reproducibility_rules": list(target.reproducibility_rules),
            "registry_provenance_rules": list(self.provenance_rules),
            "registry_reproducibility_rules": list(self.reproducibility_rules),
        }
        return SupplementalScrapeRunResult(
            status="approved",
            reason="supplemental_scrape_approved",
            request=normalized_request,
            target=target,
            provenance=provenance,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "registry_id": self.registry_id,
            "approved_targets": [target.to_dict() for target in self.approved_targets],
            "blocked_targets": [target.to_dict() for target in self.blocked_targets],
            "provenance_rules": list(self.provenance_rules),
            "reproducibility_rules": list(self.reproducibility_rules),
            "approved_target_ids": list(self.approved_target_ids),
        }

    def _blocked_target(self, target_id: str) -> SupplementalScrapeBlockedTarget | None:
        normalized = _clean_text(target_id)
        for blocked in self.blocked_targets:
            if blocked.target_id == normalized:
                return blocked
        return None

    def _blocked_result(
        self,
        *,
        request: SupplementalScrapeRunRequest,
        blocker: SupplementalScrapeBlocker,
        reason: str,
        target: SupplementalScrapeTarget | None = None,
    ) -> SupplementalScrapeRunResult:
        return SupplementalScrapeRunResult(
            status="blocked",
            reason=reason,
            request=request,
            target=target,
            blocker=blocker,
            provenance={
                "registry_id": self.registry_id,
                "request_id": request.request_id,
            },
        )

    def plan_accession_lanes(
        self,
        accession: str,
        lane_specs: Any,
        *,
        source_release: SourceReleaseManifest | Mapping[str, Any] | None = None,
    ) -> tuple[SupplementalScrapeRunResult, ...]:
        normalized_accession = _clean_text(accession)
        if not normalized_accession:
            raise ValueError("accession must not be empty")

        results: list[SupplementalScrapeRunResult] = []
        for lane_spec in _iter_values(lane_specs):
            request = _coerce_accession_lane_request(
                normalized_accession,
                lane_spec,
                source_release=source_release,
            )
            results.append(self.plan_run(request))
        return tuple(results)


def _coerce_request(
    request: SupplementalScrapeRunRequest | Mapping[str, Any],
) -> SupplementalScrapeRunRequest:
    if isinstance(request, SupplementalScrapeRunRequest):
        return request
    if not isinstance(request, Mapping):
        raise TypeError("request must be a SupplementalScrapeRunRequest or mapping")
    return SupplementalScrapeRunRequest.from_mapping(request)


def build_default_supplemental_scrape_registry() -> SupplementalScrapeRegistry:
    provenance_rules = (
        "record source release manifest id for every run",
        "preserve the exact target scope and locator prefix",
        "record the extraction mode used for the run",
    )
    reproducibility_rules = (
        "do not crawl beyond the registered target scope",
        "store parser or extractor version alongside each run",
        "pin the source release before recording enrichment output",
    )
    approved_targets = (
        SupplementalScrapeTarget(
            target_id="motif_interpro_entry",
            source_name="InterPro",
            family="motif",
            source_locator_prefix="https://www.ebi.ac.uk/interpro/entry/",
            allowed_extraction_modes=("html_document",),
            provenance_rules=(
                "prefer accession-scoped entry pages over directory navigation",
                "retain member-database back-links as provenance",
            ),
            reproducibility_rules=(
                "capture the exact InterPro entry accession",
                "avoid broad entry listing pages",
            ),
        ),
        SupplementalScrapeTarget(
            target_id="motif_prosite_details",
            source_name="PROSITE",
            family="motif",
            source_locator_prefix="https://prosite.expasy.org/",
            allowed_extraction_modes=("html_document",),
            provenance_rules=(
                "record the pattern or profile accession",
                "keep documentation page references separate from motif calls",
            ),
            reproducibility_rules=(
                "pin the PROSITE release or documentation timestamp when available",
                "capture the exact accessioned page only",
            ),
        ),
        SupplementalScrapeTarget(
            target_id="motif_elm_class",
            source_name="ELM",
            family="motif",
            source_locator_prefix="https://elm.eu.org/elms/elmPages/",
            allowed_extraction_modes=("html_document",),
            provenance_rules=(
                "record the ELM class accession and instance evidence count",
                "preserve organism and partner-context hints where present",
            ),
            reproducibility_rules=(
                "capture the class page accession only",
                "avoid exploratory traversal across unrelated ELM pages",
            ),
        ),
        SupplementalScrapeTarget(
            target_id="disorder_disprot_entry",
            source_name="DisProt",
            family="disorder",
            source_locator_prefix="https://disprot.org/",
            allowed_extraction_modes=("html_document",),
            provenance_rules=(
                "record the DisProt accession and region span evidence",
                "preserve the curated disorder term namespace",
            ),
            reproducibility_rules=(
                "pin the DisProt release manifest before recording the page",
                "limit capture to the accessioned entry page",
            ),
        ),
        SupplementalScrapeTarget(
            target_id="pathway_reactome_pathway",
            source_name="Reactome",
            family="pathway",
            source_locator_prefix="https://reactome.org/content/detail/",
            allowed_extraction_modes=("html_document",),
            provenance_rules=(
                "record the stable identifier and version suffix",
                "keep compartment and reaction context explicit",
            ),
            reproducibility_rules=(
                "pin the Reactome release snapshot before recording output",
                "avoid pathway hierarchy crawling outside the target page",
            ),
        ),
        SupplementalScrapeTarget(
            target_id="related_rcsb_sequence_motif_search",
            source_name="RCSB",
            family="related",
            source_locator_prefix="https://www.rcsb.org/search?",
            allowed_extraction_modes=("search_results",),
            provenance_rules=(
                "record the exact motif query and search filters",
                "preserve the matched structure identifiers and residue spans",
            ),
            reproducibility_rules=(
                "record the search parameters verbatim",
                "do not expand search results beyond the requested query scope",
            ),
        ),
        SupplementalScrapeTarget(
            target_id="related_rcsb_3d_motif_search",
            source_name="RCSB",
            family="related",
            source_locator_prefix="https://www.rcsb.org/search?",
            allowed_extraction_modes=("search_results",),
            provenance_rules=(
                "record the exact 3D motif query fingerprint",
                "preserve matched structure and chain context",
            ),
            reproducibility_rules=(
                "record the search parameters verbatim",
                "limit retrieval to the submitted motif query",
            ),
        ),
    )

    blocked_targets = (
        SupplementalScrapeBlockedTarget(
            target_id="sitewide_crawl",
            blocker=SupplementalScrapeBlocker(
                code="target_not_registered",
                message="sitewide crawling is not an approved supplemental target",
                detail="broad crawl paths are out of scope",
            ),
            notes=("broad crawl", "not allowlisted"),
        ),
        SupplementalScrapeBlockedTarget(
            target_id="browser_walk",
            blocker=SupplementalScrapeBlocker(
                code="target_not_registered",
                message="browser-driven traversal is not an approved supplemental target",
                detail="do not use uncontrolled navigation",
            ),
            notes=("browser traversal", "not allowlisted"),
        ),
        SupplementalScrapeBlockedTarget(
            target_id="search_engine_discovery",
            blocker=SupplementalScrapeBlocker(
                code="target_not_registered",
                message="search-engine discovery is not an approved supplemental target",
                detail="do not discover pages outside the registry",
            ),
            notes=("search engine discovery", "not allowlisted"),
        ),
    )

    return SupplementalScrapeRegistry(
        registry_id="supplemental-scrape-registry:v1",
        approved_targets=approved_targets,
        blocked_targets=blocked_targets,
        provenance_rules=provenance_rules,
        reproducibility_rules=reproducibility_rules,
    )


DEFAULT_SUPPLEMENTAL_SCRAPE_REGISTRY = build_default_supplemental_scrape_registry()


def record_supplemental_scrape_run(
    request: SupplementalScrapeRunRequest | Mapping[str, Any],
    *,
    registry: SupplementalScrapeRegistry | None = None,
) -> SupplementalScrapeRunResult:
    return (registry or DEFAULT_SUPPLEMENTAL_SCRAPE_REGISTRY).plan_run(request)


def plan_accession_supplemental_lanes(
    accession: str,
    lane_specs: Any,
    *,
    registry: SupplementalScrapeRegistry | None = None,
    source_release: SourceReleaseManifest | Mapping[str, Any] | None = None,
) -> tuple[SupplementalScrapeRunResult, ...]:
    return (registry or DEFAULT_SUPPLEMENTAL_SCRAPE_REGISTRY).plan_accession_lanes(
        accession,
        lane_specs,
        source_release=source_release,
    )


__all__ = [
    "DEFAULT_SUPPLEMENTAL_SCRAPE_REGISTRY",
    "SupplementalBlockerCode",
    "SupplementalExtractionMode",
    "SupplementalRunStatus",
    "SupplementalScrapeBlockedTarget",
    "SupplementalScrapeBlocker",
    "SupplementalScrapeRegistry",
    "SupplementalScrapeRunRequest",
    "SupplementalScrapeRunResult",
    "SupplementalScrapeTarget",
    "SupplementalTargetFamily",
    "build_default_supplemental_scrape_registry",
    "plan_accession_supplemental_lanes",
    "record_supplemental_scrape_run",
]

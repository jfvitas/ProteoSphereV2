from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

ExternalSourceCategory = Literal[
    "interaction_network",
    "assay",
    "motif",
    "bridge",
    "disorder",
    "structure_depth",
    "evolutionary",
]
ExternalSourceAcquisitionMode = Literal[
    "release_download",
    "api_query",
    "targeted_query",
    "accession_scoped_query",
    "export_download",
    "bridge_query",
    "analysis_job",
]
ExternalSourceScope = Literal["primary", "related"]
ExternalSourceMissingState = Literal["missing_local", "partial_local"]
ExternalSourceBlockerState = Literal[
    "needs_acquisition",
    "needs_live_probe",
    "access_gated",
]

_ALLOWED_CATEGORIES = {
    "interaction_network",
    "assay",
    "motif",
    "bridge",
    "disorder",
    "structure_depth",
    "evolutionary",
}
_ALLOWED_ACQUISITION_MODES = {
    "release_download",
    "api_query",
    "targeted_query",
    "accession_scoped_query",
    "export_download",
    "bridge_query",
    "analysis_job",
}
_ALLOWED_SCOPES = {"primary", "related"}
_ALLOWED_MISSING_STATES = {"missing_local", "partial_local"}
_ALLOWED_BLOCKER_STATES = {"needs_acquisition", "needs_live_probe", "access_gated"}


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


def _clean_text_tuple(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _dedupe_names(values: Sequence[str]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _normalize_category(value: Any) -> ExternalSourceCategory:
    text = _clean_text(value).replace("-", "_").replace(" ", "_").casefold()
    aliases = {
        "interaction": "interaction_network",
        "ppi": "interaction_network",
        "motif_system": "motif",
        "structure": "structure_depth",
        "msa": "evolutionary",
        "evolutionary_msa": "evolutionary",
    }
    normalized = aliases.get(text, text)
    if normalized not in _ALLOWED_CATEGORIES:
        raise ValueError(
            "category must be one of: " + ", ".join(sorted(_ALLOWED_CATEGORIES))
        )
    return normalized  # type: ignore[return-value]


def _normalize_acquisition_mode(value: Any) -> ExternalSourceAcquisitionMode:
    text = _clean_text(value).replace("-", "_").replace(" ", "_").casefold()
    aliases = {
        "download": "release_download",
        "release": "release_download",
        "export": "export_download",
        "query": "targeted_query",
        "targeted": "targeted_query",
        "api": "api_query",
        "bridge": "bridge_query",
        "job": "analysis_job",
        "alignment": "analysis_job",
    }
    normalized = aliases.get(text, text)
    if normalized not in _ALLOWED_ACQUISITION_MODES:
        raise ValueError(
            "acquisition_mode must be one of: "
            + ", ".join(sorted(_ALLOWED_ACQUISITION_MODES))
        )
    return normalized  # type: ignore[return-value]


def _normalize_scope(value: Any) -> ExternalSourceScope:
    text = _clean_text(value).replace("-", "_").replace(" ", "_").casefold()
    if text not in _ALLOWED_SCOPES:
        raise ValueError("scope must be one of: primary, related")
    return text  # type: ignore[return-value]


def _normalize_missing_state(value: Any) -> ExternalSourceMissingState:
    text = _clean_text(value).replace("-", "_").replace(" ", "_").casefold()
    if text not in _ALLOWED_MISSING_STATES:
        raise ValueError("missing_state must be one of: missing_local, partial_local")
    return text  # type: ignore[return-value]


def _normalize_blocker_state(value: Any) -> ExternalSourceBlockerState:
    text = _clean_text(value).replace("-", "_").replace(" ", "_").casefold()
    if text not in _ALLOWED_BLOCKER_STATES:
        raise ValueError(
            "blocker_state must be one of: needs_acquisition, needs_live_probe, access_gated"
        )
    return text  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class ExternalSourceBacklogDefinition:
    source_name: str
    category: ExternalSourceCategory
    acquisition_mode: ExternalSourceAcquisitionMode
    minimal_live_probe_target: str
    expected_join_anchors: tuple[str, ...]
    priority: int
    scope: ExternalSourceScope = "primary"
    missing_state: ExternalSourceMissingState = "missing_local"
    blocker_state: ExternalSourceBlockerState = "needs_acquisition"
    blocker_reason: str = ""
    evidence_refs: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", _clean_text(self.source_name))
        object.__setattr__(self, "category", _normalize_category(self.category))
        object.__setattr__(
            self,
            "acquisition_mode",
            _normalize_acquisition_mode(self.acquisition_mode),
        )
        object.__setattr__(
            self,
            "minimal_live_probe_target",
            _clean_text(self.minimal_live_probe_target),
        )
        object.__setattr__(
            self,
            "expected_join_anchors",
            _clean_text_tuple(self.expected_join_anchors),
        )
        object.__setattr__(self, "priority", int(self.priority))
        object.__setattr__(self, "scope", _normalize_scope(self.scope))
        object.__setattr__(self, "missing_state", _normalize_missing_state(self.missing_state))
        object.__setattr__(self, "blocker_state", _normalize_blocker_state(self.blocker_state))
        object.__setattr__(self, "blocker_reason", _clean_text(self.blocker_reason))
        object.__setattr__(self, "evidence_refs", _clean_text_tuple(self.evidence_refs))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))

        if not self.source_name:
            raise ValueError("source_name must not be empty")
        if not self.minimal_live_probe_target:
            raise ValueError("minimal_live_probe_target must not be empty")
        if not self.expected_join_anchors:
            raise ValueError("expected_join_anchors must not be empty")
        if self.priority < 0:
            raise ValueError("priority must be non-negative")
        if not self.blocker_reason:
            object.__setattr__(
                self,
                "blocker_reason",
                f"{self.source_name} is missing locally and needs acquisition",
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "category": self.category,
            "acquisition_mode": self.acquisition_mode,
            "minimal_live_probe_target": self.minimal_live_probe_target,
            "expected_join_anchors": list(self.expected_join_anchors),
            "priority": self.priority,
            "scope": self.scope,
            "missing_state": self.missing_state,
            "blocker_state": self.blocker_state,
            "blocker_reason": self.blocker_reason,
            "evidence_refs": list(self.evidence_refs),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class ExternalSourceBacklogManifest:
    manifest_id: str
    entries: tuple[ExternalSourceBacklogDefinition, ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "manifest_id", _clean_text(self.manifest_id))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if not self.manifest_id:
            raise ValueError("manifest_id must not be empty")

        entries_by_name: dict[str, ExternalSourceBacklogDefinition] = {}
        for entry in self.entries:
            if not isinstance(entry, ExternalSourceBacklogDefinition):
                raise TypeError("entries must contain ExternalSourceBacklogDefinition objects")
            if entry.source_name in entries_by_name:
                raise ValueError(f"duplicate source_name: {entry.source_name}")
            entries_by_name[entry.source_name] = entry
        object.__setattr__(
            self,
            "entries",
            tuple(
                sorted(entries_by_name.values(), key=lambda item: item.priority)
            ),
        )

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    @property
    def primary_entries(self) -> tuple[ExternalSourceBacklogDefinition, ...]:
        return tuple(entry for entry in self.entries if entry.scope == "primary")

    @property
    def related_entries(self) -> tuple[ExternalSourceBacklogDefinition, ...]:
        return tuple(entry for entry in self.entries if entry.scope == "related")

    @property
    def category_counts(self) -> dict[str, int]:
        return dict(Counter(entry.category for entry in self.entries))

    @property
    def acquisition_mode_counts(self) -> dict[str, int]:
        return dict(Counter(entry.acquisition_mode for entry in self.entries))

    @property
    def missing_state_counts(self) -> dict[str, int]:
        return dict(Counter(entry.missing_state for entry in self.entries))

    @property
    def blocker_state_counts(self) -> dict[str, int]:
        return dict(Counter(entry.blocker_state for entry in self.entries))

    def get_entry(self, source_name: str) -> ExternalSourceBacklogDefinition | None:
        normalized = _clean_text(source_name)
        for entry in self.entries:
            if entry.source_name == normalized:
                return entry
        return None

    def by_category(
        self,
        category: ExternalSourceCategory | str,
    ) -> tuple[ExternalSourceBacklogDefinition, ...]:
        normalized = _normalize_category(category)
        return tuple(entry for entry in self.entries if entry.category == normalized)

    def by_scope(
        self,
        scope: ExternalSourceScope | str,
    ) -> tuple[ExternalSourceBacklogDefinition, ...]:
        normalized = _normalize_scope(scope)
        return tuple(entry for entry in self.entries if entry.scope == normalized)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "entry_count": self.entry_count,
            "primary_entry_count": len(self.primary_entries),
            "related_entry_count": len(self.related_entries),
            "category_counts": dict(self.category_counts),
            "acquisition_mode_counts": dict(self.acquisition_mode_counts),
            "missing_state_counts": dict(self.missing_state_counts),
            "blocker_state_counts": dict(self.blocker_state_counts),
            "entries": [entry.to_dict() for entry in self.entries],
            "notes": list(self.notes),
        }


DEFAULT_EXTERNAL_SOURCE_BACKLOG_DEFINITIONS: tuple[
    ExternalSourceBacklogDefinition,
    ...,
] = (
    ExternalSourceBacklogDefinition(
        source_name="IntAct",
        category="interaction_network",
        acquisition_mode="release_download",
        minimal_live_probe_target="Interaction AC / IMEx record for P69905",
        expected_join_anchors=("P69905", "P09105"),
        priority=1,
        scope="primary",
        blocker_state="needs_acquisition",
        blocker_reason="curated interaction layer needs release-stamped acquisition",
        evidence_refs=(
            "docs/reports/source_intact.md",
            "docs/reports/local_source_reuse_strategy.md",
            "docs/reports/p13_t004_p13_i005_missing_source_procurement_prep_2026_03_22.md",
        ),
        notes=("highest-priority curated PPI source",),
    ),
    ExternalSourceBacklogDefinition(
        source_name="BioGRID",
        category="interaction_network",
        acquisition_mode="release_download",
        minimal_live_probe_target="TAB3 interaction row for P69905 neighborhood",
        expected_join_anchors=("P69905", "P09105"),
        priority=2,
        scope="primary",
        blocker_state="needs_acquisition",
        blocker_reason="broad curated interaction breadth needs release-stamped acquisition",
        evidence_refs=(
            "docs/reports/source_biogrid.md",
            "docs/reports/local_source_reuse_strategy.md",
            "docs/reports/p13_t004_p13_i005_missing_source_procurement_prep_2026_03_22.md",
        ),
        notes=("broad curated PPI breadth source",),
    ),
    ExternalSourceBacklogDefinition(
        source_name="STRING",
        category="interaction_network",
        acquisition_mode="targeted_query",
        minimal_live_probe_target="protein neighborhood slice for P69905",
        expected_join_anchors=("P69905", "P09105"),
        priority=3,
        scope="primary",
        blocker_state="needs_live_probe",
        blocker_reason="targeted query probe is enough to verify breadth and identifier shape",
        evidence_refs=(
            "docs/reports/local_source_reuse_strategy.md",
            "docs/reports/p13_t004_p13_i005_missing_source_procurement_prep_2026_03_22.md",
        ),
        notes=("breadth layer, not curated authority",),
    ),
    ExternalSourceBacklogDefinition(
        source_name="SABIO-RK",
        category="assay",
        acquisition_mode="accession_scoped_query",
        minimal_live_probe_target="accession-scoped enzyme/reaction query for P31749",
        expected_join_anchors=("P31749",),
        priority=4,
        scope="primary",
        blocker_state="needs_live_probe",
        blocker_reason="probe a single enzyme/reaction record before bulk procurement",
        evidence_refs=(
            "docs/reports/p13_t004_p13_i005_missing_source_procurement_prep_2026_03_22.md",
        ),
        notes=("kinetics/assay gap-fill source",),
    ),
    ExternalSourceBacklogDefinition(
        source_name="PROSITE",
        category="motif",
        acquisition_mode="release_download",
        minimal_live_probe_target="PDOCxxxxx + PSxxxxx/PRUxxxxx motif record for P69905",
        expected_join_anchors=("P69905",),
        priority=5,
        scope="primary",
        blocker_state="needs_acquisition",
        blocker_reason="accessioned motif profiles should be release-pinned before use",
        evidence_refs=(
            "docs/reports/source_motif_systems.md",
            "docs/reports/p13_t004_p13_i005_missing_source_procurement_prep_2026_03_22.md",
        ),
        notes=("precise sequence-motif source",),
    ),
    ExternalSourceBacklogDefinition(
        source_name="ELM",
        category="motif",
        acquisition_mode="export_download",
        minimal_live_probe_target="ELME##### class page plus one instance row",
        expected_join_anchors=("P69905",),
        priority=6,
        scope="primary",
        blocker_state="needs_live_probe",
        blocker_reason="class and instance scope should be checked with one live probe first",
        evidence_refs=(
            "docs/reports/source_motif_systems.md",
            "docs/reports/p13_t004_p13_i005_missing_source_procurement_prep_2026_03_22.md",
        ),
        notes=("short linear motif and partner-context source",),
    ),
    ExternalSourceBacklogDefinition(
        source_name="MegaMotifBase",
        category="motif",
        acquisition_mode="release_download",
        minimal_live_probe_target="one accession-scoped motif record",
        expected_join_anchors=("P69905",),
        priority=7,
        scope="primary",
        blocker_state="needs_live_probe",
        blocker_reason="probe the record shape before treating it as a reusable corpus",
        evidence_refs=(
            "docs/reports/p13_t004_p13_i005_missing_source_procurement_prep_2026_03_22.md",
        ),
        notes=("follow-on motif candidate",),
    ),
    ExternalSourceBacklogDefinition(
        source_name="Motivated Proteins",
        category="motif",
        acquisition_mode="release_download",
        minimal_live_probe_target="one accession-scoped motif record",
        expected_join_anchors=("P69905",),
        priority=8,
        scope="primary",
        blocker_state="needs_live_probe",
        blocker_reason="probe the record shape before treating it as a reusable corpus",
        evidence_refs=(
            "docs/reports/p13_t004_p13_i005_missing_source_procurement_prep_2026_03_22.md",
        ),
        notes=("follow-on motif candidate",),
    ),
    ExternalSourceBacklogDefinition(
        source_name="RCSB/PDBe bridge",
        category="bridge",
        acquisition_mode="bridge_query",
        minimal_live_probe_target="RCSB Data API / GraphQL fetch for 1FC2 or 10JU",
        expected_join_anchors=("1FC2", "10JU"),
        priority=9,
        scope="related",
        blocker_state="needs_live_probe",
        blocker_reason="the bridge must be probed before it is used as provenance glue",
        evidence_refs=(
            "docs/reports/p13_remaining_corpus_gaps.md",
            "docs/reports/source_rcsb_pdbe.md",
        ),
        notes=("related bridge gap rather than a corpus mirror",),
    ),
    ExternalSourceBacklogDefinition(
        source_name="DisProt",
        category="disorder",
        acquisition_mode="api_query",
        minimal_live_probe_target="DisProt API search record for P69905",
        expected_join_anchors=("P69905",),
        priority=10,
        scope="related",
        blocker_state="needs_live_probe",
        blocker_reason="probe a single disorder record before widening the disorder lane",
        evidence_refs=(
            "docs/reports/source_disprot.md",
            "docs/reports/p13_remaining_corpus_gaps.md",
        ),
        notes=("disorder/function evidence layer",),
    ),
    ExternalSourceBacklogDefinition(
        source_name="EMDB",
        category="structure_depth",
        acquisition_mode="release_download",
        minimal_live_probe_target="entry header for linked protein complex or map",
        expected_join_anchors=("1FC2", "10JU"),
        priority=11,
        scope="related",
        blocker_state="needs_acquisition",
        blocker_reason="map-depth evidence should be release-stamped before use",
        evidence_refs=(
            "docs/reports/source_emdb.md",
            "docs/reports/p13_remaining_corpus_gaps.md",
        ),
        notes=("structure-depth evidence overlay",),
    ),
    ExternalSourceBacklogDefinition(
        source_name="Evolutionary / MSA",
        category="evolutionary",
        acquisition_mode="analysis_job",
        minimal_live_probe_target="single-family MSA slice for P69905",
        expected_join_anchors=("P69905", "P68871"),
        priority=12,
        scope="related",
        blocker_state="needs_live_probe",
        blocker_reason="the family slice should be proven on one accession before scaling",
        evidence_refs=(
            "docs/reports/source_evolutionary_msa.md",
            "docs/reports/p13_remaining_corpus_gaps.md",
        ),
        notes=("sequence-context and split-governance gap",),
    ),
)


def _normalize_source_names(values: Any) -> tuple[str, ...]:
    return _dedupe_names(tuple(str(item) for item in _iter_values(values)))


def _resolve_entries(
    entries: Sequence[ExternalSourceBacklogDefinition],
    source_names: Sequence[str] | None,
) -> tuple[ExternalSourceBacklogDefinition, ...]:
    if source_names is None:
        return tuple(entries)

    selected: list[ExternalSourceBacklogDefinition] = []
    for source_name in _normalize_source_names(source_names):
        matched = None
        for entry in entries:
            if entry.source_name == source_name:
                matched = entry
                break
        if matched is None:
            raise KeyError(f"source_name not found in external source backlog: {source_name}")
        selected.append(matched)
    return tuple(selected)


def build_external_source_backlog(
    *,
    source_names: Sequence[str] | None = None,
    manifest_id: str = "external-source-backlog:v1",
    notes: Sequence[str] = (),
) -> ExternalSourceBacklogManifest:
    entries = _resolve_entries(DEFAULT_EXTERNAL_SOURCE_BACKLOG_DEFINITIONS, source_names)
    return ExternalSourceBacklogManifest(
        manifest_id=manifest_id,
        entries=entries,
        notes=tuple(notes)
        + (
            "missing online sources remain explicit until live acquisition lands",
            "primary entries come from the P13 procurement prep note",
            "related entries carry broader release-gap context from the gap audit",
        ),
    )


DEFAULT_EXTERNAL_SOURCE_BACKLOG = build_external_source_backlog()


__all__ = [
    "DEFAULT_EXTERNAL_SOURCE_BACKLOG",
    "DEFAULT_EXTERNAL_SOURCE_BACKLOG_DEFINITIONS",
    "ExternalSourceAcquisitionMode",
    "ExternalSourceBacklogDefinition",
    "ExternalSourceBacklogManifest",
    "ExternalSourceBlockerState",
    "ExternalSourceCategory",
    "ExternalSourceMissingState",
    "ExternalSourceScope",
    "build_external_source_backlog",
]

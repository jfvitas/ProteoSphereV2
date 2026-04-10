from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

LocalSourceStatus = Literal["present", "partial", "missing"]
LocalSourceLoadHint = Literal["preload", "index", "lazy"]
LocalSourceCategory = Literal[
    "sequence",
    "structure",
    "protein_protein",
    "protein_ligand",
    "pathway_annotation",
    "interaction_network",
    "motif",
    "structural_classification",
    "derived_training",
    "release_artifact",
    "metadata",
    "missing_source",
]

DEFAULT_LOCAL_SOURCE_ROOT = Path(r"C:\Users\jfvit\Documents\bio-agent-lab")
REPO_ROOT = Path(__file__).resolve().parents[2]
_REPO_LOCAL_PREFIXES = ("data/raw/protein_data_scope_seed/",)


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


def _normalize_category(value: Any) -> LocalSourceCategory:
    text = _clean_text(value).replace("-", "_").replace(" ", "_").casefold()
    aliases = {
        "pathway": "pathway_annotation",
        "annotation": "pathway_annotation",
        "structure_classification": "structural_classification",
        "derived": "derived_training",
        "release": "release_artifact",
        "meta": "metadata",
        "missing": "missing_source",
    }
    normalized = aliases.get(text, text)
    allowed = {
        "sequence",
        "structure",
        "protein_protein",
        "protein_ligand",
        "pathway_annotation",
        "interaction_network",
        "motif",
        "structural_classification",
        "derived_training",
        "release_artifact",
        "metadata",
        "missing_source",
    }
    if normalized not in allowed:
        raise ValueError(
            "category must be one of: "
            + ", ".join(sorted(allowed))
        )
    return normalized  # type: ignore[return-value]


def _normalize_load_hint(value: Any) -> LocalSourceLoadHint:
    text = _clean_text(value).replace("-", "_").replace(" ", "_").casefold()
    aliases = {
        "preload": "preload",
        "index": "index",
        "search": "index",
        "lookup": "index",
        "lazy": "lazy",
        "defer": "lazy",
        "deferred": "lazy",
    }
    normalized = aliases.get(text)
    if normalized is None:
        raise ValueError("load_hints must contain preload, index, or lazy")
    return normalized  # type: ignore[return-value]


def _dedupe_roots(values: Sequence[str]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _resolve_root_path(storage_root: Path, candidate: str) -> str:
    path = Path(candidate)
    if not path.is_absolute():
        normalized = candidate.replace("\\", "/")
        if any(normalized.startswith(prefix) for prefix in _REPO_LOCAL_PREFIXES):
            path = REPO_ROOT / path
        else:
            path = storage_root / path
    return str(path)


def _resolve_candidate_roots(storage_root: Path, candidate_roots: Any) -> tuple[str, ...]:
    normalized_candidates = tuple(str(item) for item in _iter_values(candidate_roots))
    return tuple(
        _resolve_root_path(storage_root, candidate_root)
        for candidate_root in _dedupe_roots(normalized_candidates)
    )


@dataclass(frozen=True, slots=True)
class LocalSourceDefinition:
    source_name: str
    category: LocalSourceCategory
    candidate_roots: tuple[str, ...]
    likely_join_anchors: tuple[str, ...] = ()
    load_hints: tuple[LocalSourceLoadHint, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", _clean_text(self.source_name))
        object.__setattr__(self, "category", _normalize_category(self.category))
        object.__setattr__(self, "candidate_roots", _dedupe_roots(self.candidate_roots))
        object.__setattr__(self, "likely_join_anchors", _clean_text_tuple(self.likely_join_anchors))
        object.__setattr__(
            self,
            "load_hints",
            tuple(_normalize_load_hint(hint) for hint in _clean_text_tuple(self.load_hints)),
        )
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if not self.source_name:
            raise ValueError("source_name must not be empty")
        if not self.candidate_roots:
            raise ValueError("candidate_roots must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "category": self.category,
            "candidate_roots": list(self.candidate_roots),
            "likely_join_anchors": list(self.likely_join_anchors),
            "load_hints": list(self.load_hints),
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class LocalSourceEntry:
    source_name: str
    category: LocalSourceCategory
    candidate_roots: tuple[str, ...]
    present_roots: tuple[str, ...]
    missing_roots: tuple[str, ...]
    likely_join_anchors: tuple[str, ...] = ()
    load_hints: tuple[LocalSourceLoadHint, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", _clean_text(self.source_name))
        object.__setattr__(self, "category", _normalize_category(self.category))
        object.__setattr__(self, "candidate_roots", _dedupe_roots(self.candidate_roots))
        object.__setattr__(self, "present_roots", _dedupe_roots(self.present_roots))
        object.__setattr__(self, "missing_roots", _dedupe_roots(self.missing_roots))
        object.__setattr__(self, "likely_join_anchors", _clean_text_tuple(self.likely_join_anchors))
        object.__setattr__(
            self,
            "load_hints",
            tuple(_normalize_load_hint(hint) for hint in _clean_text_tuple(self.load_hints)),
        )
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if not self.source_name:
            raise ValueError("source_name must not be empty")
        if not self.candidate_roots:
            raise ValueError("candidate_roots must not be empty")
        if set(self.present_roots).union(self.missing_roots) != set(self.candidate_roots):
            raise ValueError("present_roots and missing_roots must partition candidate_roots")
        if set(self.present_roots).intersection(self.missing_roots):
            raise ValueError("present_roots and missing_roots must be disjoint")

    @property
    def status(self) -> LocalSourceStatus:
        if self.present_roots and self.missing_roots:
            return "partial"
        if self.present_roots:
            return "present"
        return "missing"

    @property
    def preload_worthy(self) -> bool:
        return "preload" in self.load_hints

    @property
    def index_worthy(self) -> bool:
        return "index" in self.load_hints

    @property
    def lazy_import_worthy(self) -> bool:
        return "lazy" in self.load_hints

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "category": self.category,
            "candidate_roots": list(self.candidate_roots),
            "present_roots": list(self.present_roots),
            "missing_roots": list(self.missing_roots),
            "status": self.status,
            "likely_join_anchors": list(self.likely_join_anchors),
            "load_hints": list(self.load_hints),
            "preload_worthy": self.preload_worthy,
            "index_worthy": self.index_worthy,
            "lazy_import_worthy": self.lazy_import_worthy,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class LocalSourceRegistry:
    registry_id: str
    storage_root: str
    entries: tuple[LocalSourceEntry, ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "registry_id", _clean_text(self.registry_id))
        object.__setattr__(self, "storage_root", _clean_text(self.storage_root))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if not self.registry_id:
            raise ValueError("registry_id must not be empty")
        if not self.storage_root:
            raise ValueError("storage_root must not be empty")

        entries_by_name: dict[str, LocalSourceEntry] = {}
        for entry in self.entries:
            if not isinstance(entry, LocalSourceEntry):
                raise TypeError("entries must contain LocalSourceEntry objects")
            if entry.source_name in entries_by_name:
                raise ValueError(f"duplicate source_name: {entry.source_name}")
            entries_by_name[entry.source_name] = entry
        object.__setattr__(self, "entries", tuple(entries_by_name.values()))

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    @property
    def present_entries(self) -> tuple[LocalSourceEntry, ...]:
        return tuple(entry for entry in self.entries if entry.status == "present")

    @property
    def partial_entries(self) -> tuple[LocalSourceEntry, ...]:
        return tuple(entry for entry in self.entries if entry.status == "partial")

    @property
    def missing_entries(self) -> tuple[LocalSourceEntry, ...]:
        return tuple(entry for entry in self.entries if entry.status == "missing")

    @property
    def preload_worthy_entries(self) -> tuple[LocalSourceEntry, ...]:
        return tuple(entry for entry in self.entries if entry.preload_worthy)

    @property
    def index_worthy_entries(self) -> tuple[LocalSourceEntry, ...]:
        return tuple(entry for entry in self.entries if entry.index_worthy)

    @property
    def lazy_import_worthy_entries(self) -> tuple[LocalSourceEntry, ...]:
        return tuple(entry for entry in self.entries if entry.lazy_import_worthy)

    def get(self, source_name: str) -> LocalSourceEntry | None:
        normalized = _clean_text(source_name)
        for entry in self.entries:
            if entry.source_name == normalized:
                return entry
        return None

    def by_category(self, category: LocalSourceCategory | str) -> tuple[LocalSourceEntry, ...]:
        normalized = _normalize_category(category)
        return tuple(entry for entry in self.entries if entry.category == normalized)

    def to_dict(self) -> dict[str, Any]:
        return {
            "registry_id": self.registry_id,
            "storage_root": self.storage_root,
            "entry_count": self.entry_count,
            "present_entry_count": len(self.present_entries),
            "partial_entry_count": len(self.partial_entries),
            "missing_entry_count": len(self.missing_entries),
            "preload_worthy_entry_count": len(self.preload_worthy_entries),
            "index_worthy_entry_count": len(self.index_worthy_entries),
            "lazy_import_worthy_entry_count": len(self.lazy_import_worthy_entries),
            "entries": [entry.to_dict() for entry in self.entries],
            "notes": list(self.notes),
        }


def _resolve_definition(storage_root: Path, definition: LocalSourceDefinition) -> LocalSourceEntry:
    resolved_roots = _resolve_candidate_roots(storage_root, definition.candidate_roots)
    present_roots = tuple(path for path in resolved_roots if Path(path).exists())
    missing_roots = tuple(path for path in resolved_roots if not Path(path).exists())
    return LocalSourceEntry(
        source_name=definition.source_name,
        category=definition.category,
        candidate_roots=resolved_roots,
        present_roots=present_roots,
        missing_roots=missing_roots,
        likely_join_anchors=definition.likely_join_anchors,
        load_hints=definition.load_hints,
        notes=definition.notes,
    )


def build_local_source_registry(
    storage_root: str | Path,
    definitions: Sequence[LocalSourceDefinition],
    *,
    registry_id: str = "bio-agent-lab-local-source-registry:v1",
    notes: Sequence[str] = (),
) -> LocalSourceRegistry:
    root = Path(storage_root)
    entries = tuple(_resolve_definition(root, definition) for definition in definitions)
    return LocalSourceRegistry(
        registry_id=registry_id,
        storage_root=str(root),
        entries=entries,
        notes=tuple(notes),
    )


DEFAULT_LOCAL_SOURCE_DEFINITIONS: tuple[LocalSourceDefinition, ...] = (
    LocalSourceDefinition(
        source_name="catalog",
        category="metadata",
        candidate_roots=("data/catalog",),
        load_hints=("preload",),
        notes=("workspace source catalog and stage metadata",),
    ),
    LocalSourceDefinition(
        source_name="audit",
        category="metadata",
        candidate_roots=("data/audit",),
        load_hints=("preload",),
        notes=("audit summary and source-health rollups",),
    ),
    LocalSourceDefinition(
        source_name="reports",
        category="metadata",
        candidate_roots=("data/reports",),
        load_hints=("preload",),
        notes=("operator-facing report outputs and diagnostics",),
    ),
    LocalSourceDefinition(
        source_name="releases_test_v1",
        category="release_artifact",
        candidate_roots=("data/releases/test_v1",),
        load_hints=("preload",),
        likely_join_anchors=("custom_training_set", "master_pdb_repository"),
        notes=("frozen release snapshot and training-package manifests",),
    ),
    LocalSourceDefinition(
        source_name="splits",
        category="metadata",
        candidate_roots=("data/splits",),
        load_hints=("preload",),
        notes=("split metadata and diagnostics",),
    ),
    LocalSourceDefinition(
        source_name="training_examples",
        category="derived_training",
        candidate_roots=("data/training_examples",),
        load_hints=("index",),
        likely_join_anchors=("P69905", "P31749"),
        notes=("assembled training-example layer",),
    ),
    LocalSourceDefinition(
        source_name="features",
        category="derived_training",
        candidate_roots=("data/features",),
        load_hints=("index",),
        likely_join_anchors=("P69905", "1A00"),
        notes=("feature manifest and microstate/physics feature records",),
    ),
    LocalSourceDefinition(
        source_name="graph",
        category="derived_training",
        candidate_roots=("data/graph",),
        load_hints=("index",),
        likely_join_anchors=("P69905", "5JJM"),
        notes=("graph nodes, edges, and graph manifest",),
    ),
    LocalSourceDefinition(
        source_name="model_studio",
        category="derived_training",
        candidate_roots=("data/models/model_studio",),
        load_hints=("index", "lazy"),
        likely_join_anchors=("P69905", "5JJM"),
        notes=("model-studio payloads, PyG-ready samples, and demo runs",),
    ),
    LocalSourceDefinition(
        source_name="raw_rcsb",
        category="structure",
        candidate_roots=("data/raw/rcsb",),
        load_hints=("index", "lazy"),
        likely_join_anchors=("10JU", "4HHB", "9LWP"),
        notes=("raw RCSB JSON payloads",),
    ),
    LocalSourceDefinition(
        source_name="structures_rcsb",
        category="structure",
        candidate_roots=("data/structures/rcsb",),
        load_hints=("index", "lazy"),
        likely_join_anchors=("10JU", "4HHB", "9LWP"),
        notes=("mmCIF structure assets",),
    ),
    LocalSourceDefinition(
        source_name="extracted_assays",
        category="protein_ligand",
        candidate_roots=("data/extracted/assays",),
        load_hints=("index", "lazy"),
        likely_join_anchors=("10JU", "1A00"),
        notes=("per-accession extracted assay views",),
    ),
    LocalSourceDefinition(
        source_name="extracted_bound_objects",
        category="protein_ligand",
        candidate_roots=("data/extracted/bound_objects",),
        load_hints=("index", "lazy"),
        likely_join_anchors=("10JU", "1A00"),
        notes=("per-accession extracted bound-object views",),
    ),
    LocalSourceDefinition(
        source_name="extracted_chains",
        category="structure",
        candidate_roots=("data/extracted/chains",),
        load_hints=("index", "lazy"),
        likely_join_anchors=("10JU", "4HHB"),
        notes=("per-accession extracted chain views",),
    ),
    LocalSourceDefinition(
        source_name="extracted_entry",
        category="structure",
        candidate_roots=("data/extracted/entry",),
        load_hints=("index", "lazy"),
        likely_join_anchors=("10JU", "4HHB"),
        notes=("per-accession extracted entry views",),
    ),
    LocalSourceDefinition(
        source_name="extracted_interfaces",
        category="protein_protein",
        candidate_roots=("data/extracted/interfaces",),
        load_hints=("index", "lazy"),
        likely_join_anchors=("10JU", "4HHB"),
        notes=("per-accession extracted interface views",),
    ),
    LocalSourceDefinition(
        source_name="extracted_provenance",
        category="metadata",
        candidate_roots=("data/extracted/provenance",),
        load_hints=("index", "lazy"),
        likely_join_anchors=("10JU", "4HHB"),
        notes=("per-accession provenance views",),
    ),
    LocalSourceDefinition(
        source_name="uniprot",
        category="sequence",
        candidate_roots=(
            "data/raw/protein_data_scope_seed/uniprot/uniprot_sprot.dat.gz",
            "data/raw/protein_data_scope_seed/uniprot/uniprot_sprot.fasta.gz",
            "data/raw/protein_data_scope_seed/uniprot/idmapping.dat.gz",
        ),
        likely_join_anchors=("P69905", "P68871", "P09105", "Q9UCM0"),
        load_hints=("index",),
        notes=("validated Swiss-Prot seed mirror with accession and idmapping anchors",),
    ),
    LocalSourceDefinition(
        source_name="alphafold_db",
        category="structure",
        candidate_roots=(
            "data_sources/alphafold/swissprot_pdb_v6.tar",
            "data_sources/alphafold",
        ),
        likely_join_anchors=("P69905", "P68871"),
        load_hints=("index", "lazy"),
        notes=(
            "predicted single-chain structure archive and extracted metadata",
            "repo-seed mirror is currently partial only and must not be treated as authoritative fallback presence",
        ),
    ),
    LocalSourceDefinition(
        source_name="bindingdb",
        category="protein_ligand",
        candidate_roots=(
            "data_sources/bindingdb/BDB-mySQL_All_202603_dmp.zip",
            "data/raw/bindingdb",
        ),
        likely_join_anchors=("1BB0", "5Q16", "5TQF"),
        load_hints=("index", "lazy"),
        notes=(
            "bulk dump plus per-PDB cache payloads",
            "repo-seed placeholder ZIP stubs under data/raw/protein_data_scope_seed/bindingdb are not authoritative fallback payloads",
        ),
    ),
    LocalSourceDefinition(
        source_name="chembl",
        category="protein_ligand",
        candidate_roots=(
            "data_sources/chembl/chembl_36_sqlite.tar.gz",
            "data_sources/chembl/chembl_36_sqlite/chembl_36/chembl_36_sqlite/chembl_36.db",
            "data/raw/protein_data_scope_seed/chembl/chembl_36_sqlite.tar.gz",
            "data/raw/protein_data_scope_seed/chembl/chembl_36_sqlite.tar.gz__extracted",
        ),
        likely_join_anchors=("5JJM", "P31749"),
        load_hints=("lazy",),
        notes=("large local SQLite snapshot with repo-local seed fallback",),
    ),
    LocalSourceDefinition(
        source_name="biolip",
        category="protein_ligand",
        candidate_roots=(
            "data_sources/biolip/BioLiP.txt",
            "data_sources/biolip/BioLiP.txt.gz",
            "data_sources/biolip/BioLiP_extracted",
        ),
        likely_join_anchors=("4HHB", "9S6C"),
        load_hints=("index", "lazy"),
        notes=("binding-site annotation snapshot",),
    ),
    LocalSourceDefinition(
        source_name="pdbbind_pl",
        category="protein_ligand",
        candidate_roots=(
            "data_sources/pdbbind/P-L.tar.gz",
            "data_sources/pdbbind/index/INDEX_general_PL.2020R1.lst",
            "data_sources/pdbbind/P-L",
        ),
        likely_join_anchors=("6O3O", "1ARJ", "1BYJ"),
        load_hints=("index", "lazy"),
        notes=("curated protein-ligand affinity index and structure subtree",),
    ),
    LocalSourceDefinition(
        source_name="pdbbind_pp",
        category="protein_protein",
        candidate_roots=(
            "data_sources/pdbbind/P-P.tar.gz",
            "data_sources/pdbbind/index/INDEX_general_PP.2020R1.lst",
            "data_sources/pdbbind/P-P",
        ),
        likely_join_anchors=("9LWP", "9QTN", "9SYV"),
        load_hints=("index", "lazy"),
        notes=("curated protein-protein affinity index and structure subtree",),
    ),
    LocalSourceDefinition(
        source_name="pdbbind_na_l",
        category="protein_ligand",
        candidate_roots=(
            "data_sources/pdbbind/NA-L.tar.gz",
            "data_sources/pdbbind/index/INDEX_general_NL.2020R1.lst",
            "data_sources/pdbbind/NA-L",
        ),
        likely_join_anchors=("1ARJ", "1BYJ"),
        load_hints=("index", "lazy"),
        notes=("nucleic-acid / ligand subtree",),
    ),
    LocalSourceDefinition(
        source_name="pdbbind_p_na",
        category="protein_ligand",
        candidate_roots=(
            "data_sources/pdbbind/P-NA.tar.gz",
            "data_sources/pdbbind/index/INDEX_general_PN.2020R1.lst",
            "data_sources/pdbbind/P-NA",
        ),
        likely_join_anchors=("1ARJ", "1BYJ"),
        load_hints=("index", "lazy"),
        notes=("protein / nucleic-acid subtree",),
    ),
    LocalSourceDefinition(
        source_name="reactome",
        category="pathway_annotation",
        candidate_roots=(
            "data_sources/reactome/UniProt2Reactome_All_Levels.txt",
            "data_sources/reactome/ReactomePathways.txt",
            "data_sources/reactome/ReactomePathwaysRelation.txt",
            "data/raw/protein_data_scope_seed/reactome/UniProt2Reactome.txt",
            "data/raw/protein_data_scope_seed/reactome/ReactomePathways.txt",
            "data/raw/protein_data_scope_seed/reactome/ReactomePathwaysRelation.txt",
        ),
        likely_join_anchors=("P69905", "P09105"),
        load_hints=("preload", "index"),
        notes=("pathway mapping and hierarchy tables with repo-local seed fallback",),
    ),
    LocalSourceDefinition(
        source_name="chebi",
        category="protein_ligand",
        candidate_roots=("data/raw/protein_data_scope_seed/chebi",),
        likely_join_anchors=("CHEBI:15377", "CHEBI:15422", "ATP"),
        load_hints=("index", "lazy"),
        notes=("validated seed mirror for chemical identity and ontology assets",),
    ),
    LocalSourceDefinition(
        source_name="complex_portal",
        category="interaction_network",
        candidate_roots=("data/raw/protein_data_scope_seed/complex_portal",),
        likely_join_anchors=("P69905", "P09105", "9606"),
        load_hints=("index", "lazy"),
        notes=("validated seed mirror for curated complex membership and predicted complexes",),
    ),
    LocalSourceDefinition(
        source_name="interpro",
        category="pathway_annotation",
        candidate_roots=(
            "data_sources/interpro/interpro.xml.gz",
            "data/raw/protein_data_scope_seed/interpro/interpro.xml.gz",
        ),
        likely_join_anchors=("P69905",),
        load_hints=("index", "lazy"),
        notes=("domain and family annotation snapshot with repo-local seed fallback",),
    ),
    LocalSourceDefinition(
        source_name="rnacentral",
        category="metadata",
        candidate_roots=("data/raw/protein_data_scope_seed/rnacentral",),
        likely_join_anchors=("URS000075C808", "P69905"),
        load_hints=("index", "lazy"),
        notes=("validated seed mirror for resolver-side RNAcentral mappings and sequence payloads",),
    ),
    LocalSourceDefinition(
        source_name="sifts",
        category="structure",
        candidate_roots=("data/raw/protein_data_scope_seed/sifts",),
        likely_join_anchors=("P69905", "4HHB", "10JU"),
        load_hints=("preload", "index"),
        notes=("validated seed mirror for the strongest UniProt-to-structure crosswalk tables",),
    ),
    LocalSourceDefinition(
        source_name="pfam",
        category="pathway_annotation",
        candidate_roots=(
            "data_sources/pfam/Pfam-A.full.gz",
            "data_sources/pfam/Pfam-A.clans.tsv.gz",
        ),
        likely_join_anchors=("P69905",),
        load_hints=("index", "lazy"),
        notes=("domain-family and clan tables",),
    ),
    LocalSourceDefinition(
        source_name="cath",
        category="structural_classification",
        candidate_roots=(
            "data_sources/cath/cath-domain-list.txt",
            "data_sources/cath/cath-domain-boundaries.txt",
            "data_sources/cath/cath-names.txt",
            "data_sources/cath/cath-superfamily-list.txt",
        ),
        likely_join_anchors=("10JU", "4HHB"),
        load_hints=("index",),
        notes=("fold and architecture classification tables",),
    ),
    LocalSourceDefinition(
        source_name="scope",
        category="structural_classification",
        candidate_roots=(
            "data_sources/scope/dir.cla.scope.2.08-stable.txt",
            "data_sources/scope/dir.des.scope.txt",
        ),
        likely_join_anchors=("10JU", "4HHB"),
        load_hints=("index",),
        notes=("SCOPe classification and description tables",),
    ),
    LocalSourceDefinition(
        source_name="string",
        category="interaction_network",
        candidate_roots=(
            "data_sources/string/protein.links_latest.txt_latest",
            "data_sources/string/protein.info_latest.txt_latest",
            "data_sources/string/protein.aliases_latest.txt_latest",
        ),
        likely_join_anchors=("P69905", "P09105"),
        load_hints=("index", "lazy"),
        notes=(
            "currently missing from the local inventory",
            "repo-seed metadata stub alone must not be promoted as graph presence",
        ),
    ),
    LocalSourceDefinition(
        source_name="biogrid",
        category="interaction_network",
        candidate_roots=(
            "data/raw/protein_data_scope_seed/biogrid/BIOGRID-ALL-LATEST.mitab.zip",
            "data/raw/protein_data_scope_seed/biogrid/BIOGRID-ORGANISM-LATEST.mitab.zip",
            "data/raw/protein_data_scope_seed/biogrid/BIOGRID-ORGANISM-LATEST.psi.zip",
            "data/raw/protein_data_scope_seed/biogrid/BIOGRID-ORGANISM-LATEST.psi25.zip",
        ),
        likely_join_anchors=("P69905", "P09105"),
        load_hints=("index", "lazy"),
        notes=("validated seed mirror for curated BioGRID interaction exports",),
    ),
    LocalSourceDefinition(
        source_name="intact",
        category="interaction_network",
        candidate_roots=(
            "data/raw/protein_data_scope_seed/intact/intact.zip",
            "data/raw/protein_data_scope_seed/intact/mutation.tsv",
        ),
        likely_join_anchors=("P69905", "P09105"),
        load_hints=("index", "lazy"),
        notes=("validated seed mirror for IntAct bulk payloads and mutation table",),
    ),
    LocalSourceDefinition(
        source_name="sabio_rk",
        category="metadata",
        candidate_roots=(
            "data_sources/sabio_rk/sabio_rk_query_manifest_latest.json",
            "data_sources/sabio_rk/sabio_rk_export_latest.tsv_latest",
            "data/raw/protein_data_scope_seed/sabio_rk/sabio_search_fields.xml",
            "data/raw/protein_data_scope_seed/sabio_rk/sabio_uniprotkb_acs.txt",
            "data/raw/protein_data_scope_seed/sabio_rk/sabio_p31749_entry_ids.txt",
            "data/raw/protein_data_scope_seed/sabio_rk/sabio_p31749_sbml.xml",
        ),
        likely_join_anchors=("P31749",),
        load_hints=("lazy",),
        notes=(
            "query-scoped kinetics lane; prefer accession-anchored exports over pretending SABIO-RK is a bulk mirror",
            "repo-seed REST vocabulary and P31749 probe are acceptable truthful fallback evidence when present",
        ),
    ),
    LocalSourceDefinition(
        source_name="prosite",
        category="motif",
        candidate_roots=(
            "data/raw/protein_data_scope_seed/prosite/prosite.dat",
            "data/raw/protein_data_scope_seed/prosite/prosite.doc",
            "data/raw/protein_data_scope_seed/prosite/prosite.aux",
        ),
        likely_join_anchors=("P69905",),
        load_hints=("index", "lazy"),
        notes=("validated seed mirror for PROSITE motif and documentation assets",),
    ),
    LocalSourceDefinition(
        source_name="pdb_chemical_component_dictionary",
        category="protein_ligand",
        candidate_roots=("data/raw/protein_data_scope_seed/pdb_chemical_component_dictionary",),
        likely_join_anchors=("HEM", "ATP", "NAG"),
        load_hints=("preload", "index"),
        notes=("validated seed mirror for PDB chemical component dictionary and ligand authority",),
    ),
    LocalSourceDefinition(
        source_name="elm",
        category="motif",
        candidate_roots=(
            "data_sources/elm/elm_classes_latest.tsv_latest",
            "data_sources/elm/elm_instances_latest.tsv_latest",
            "data/raw/protein_data_scope_seed/elm/elm_classes.tsv",
            "data/raw/protein_data_scope_seed/elm/elm_interaction_domains.tsv",
        ),
        likely_join_anchors=("P69905",),
        load_hints=("index", "lazy"),
        notes=(
            "motif-class regex and motif-domain interaction priors",
            "repo-seed ELM TSV exports are acceptable fallback presence even before a larger local mirror exists",
        ),
    ),
    LocalSourceDefinition(
        source_name="mega_motif_base",
        category="motif",
        candidate_roots=(
            "data_sources/mega_motif_base/mega_motif_base_latest.json_latest",
            "data_sources/mega_motif_base/mega_motif_base_latest.tsv_latest",
        ),
        likely_join_anchors=("P69905",),
        load_hints=("index", "lazy"),
        notes=("currently missing from the local inventory",),
    ),
    LocalSourceDefinition(
        source_name="motivated_proteins",
        category="motif",
        candidate_roots=(
            "data_sources/motivated_proteins/motivated_proteins_lookup_manifest_latest.json",
            "data_sources/motivated_proteins/motivated_proteins_export_latest.json_latest",
        ),
        likely_join_anchors=("P69905",),
        load_hints=("index", "lazy"),
        notes=("currently missing from the local inventory",),
    ),
)


def build_default_local_source_registry(
    storage_root: str | Path = DEFAULT_LOCAL_SOURCE_ROOT,
) -> LocalSourceRegistry:
    return build_local_source_registry(
        storage_root,
        DEFAULT_LOCAL_SOURCE_DEFINITIONS,
        notes=(
            "inventory drawn from the local bio-agent-lab corpus and metadata tree",
            "missing roots are kept explicit so the registry stays conservative",
        ),
    )


DEFAULT_LOCAL_SOURCE_REGISTRY = build_default_local_source_registry()


__all__ = [
    "DEFAULT_LOCAL_SOURCE_DEFINITIONS",
    "DEFAULT_LOCAL_SOURCE_REGISTRY",
    "DEFAULT_LOCAL_SOURCE_ROOT",
    "LocalSourceCategory",
    "LocalSourceDefinition",
    "LocalSourceEntry",
    "LocalSourceLoadHint",
    "LocalSourceRegistry",
    "LocalSourceStatus",
    "build_default_local_source_registry",
    "build_local_source_registry",
]

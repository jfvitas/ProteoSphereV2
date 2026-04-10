from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.library.summary_record import (
    ProteinSummaryRecord,
    SummaryBiologicalOrigin,
    SummaryLibrarySchema,
    SummaryProvenancePointer,
    SummaryRecordContext,
    SummaryReference,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REACTOME_MAPPING_PATH = Path(
    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\reactome\UniProt2Reactome_All_Levels.txt"
)
DEFAULT_REACTOME_PATHWAYS_PATH = Path(
    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\reactome\ReactomePathways.txt"
)
DEFAULT_REACTOME_RELATIONS_PATH = Path(
    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\reactome\ReactomePathwaysRelation.txt"
)
DEFAULT_CANONICAL_SUMMARY_PATH = ROOT / "data" / "canonical" / "LATEST.json"


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


def _file_release_version(path: Path) -> str:
    timestamp = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return timestamp.date().isoformat()


@dataclass(frozen=True, slots=True)
class ReactomePathwayAssignment:
    accession: str
    stable_id: str
    pathway_name: str
    evidence_code: str
    species: str
    pathway_url: str
    ancestor_ids: tuple[str, ...] = ()
    ancestor_names: tuple[str, ...] = ()

    def to_summary_reference(self) -> SummaryReference:
        notes = tuple(
            note
            for note in (
                f"species:{self.species}" if self.species else "",
                f"url:{self.pathway_url}" if self.pathway_url else "",
                (
                    "ancestors:" + "|".join(self.ancestor_ids)
                    if self.ancestor_ids
                    else ""
                ),
                (
                    "ancestor_names:" + "|".join(self.ancestor_names)
                    if self.ancestor_names
                    else ""
                ),
            )
            if note
        )
        return SummaryReference(
            reference_kind="pathway",
            namespace="Reactome",
            identifier=self.stable_id,
            label=self.pathway_name,
            join_status="joined",
            source_name="Reactome",
            source_record_id=self.stable_id,
            evidence_refs=(self.evidence_code,) if self.evidence_code else (),
            notes=notes,
        )


def _load_pathway_names(path: Path) -> dict[str, tuple[str, str]]:
    names: dict[str, tuple[str, str]] = {}
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            stable_id, pathway_name, species = (_clean_text(part) for part in parts[:3])
            if stable_id:
                names[stable_id] = (pathway_name, species)
    return names


def _load_parent_relations(path: Path) -> dict[str, tuple[str, ...]]:
    parents_by_child: dict[str, list[str]] = defaultdict(list)
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            parent_id, child_id = (_clean_text(part) for part in parts[:2])
            if parent_id and child_id and parent_id not in parents_by_child[child_id]:
                parents_by_child[child_id].append(parent_id)
    return {child_id: tuple(parent_ids) for child_id, parent_ids in parents_by_child.items()}


def _ancestor_chain(
    stable_id: str,
    *,
    parents_by_child: Mapping[str, Sequence[str]],
    names_by_stable_id: Mapping[str, tuple[str, str]],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    ordered_ids: list[str] = []
    visited: set[str] = set()
    stack = list(reversed(parents_by_child.get(stable_id, ())))
    while stack:
        parent_id = stack.pop()
        if parent_id in visited:
            continue
        visited.add(parent_id)
        ordered_ids.append(parent_id)
        for grandparent_id in reversed(parents_by_child.get(parent_id, ())):
            if grandparent_id not in visited:
                stack.append(grandparent_id)
    ordered_names = [
        names_by_stable_id[parent_id][0]
        for parent_id in ordered_ids
        if parent_id in names_by_stable_id and names_by_stable_id[parent_id][0]
    ]
    return tuple(ordered_ids), tuple(ordered_names)


def load_reactome_pathway_assignments(
    *,
    accessions: Sequence[str],
    mapping_path: Path = DEFAULT_REACTOME_MAPPING_PATH,
    pathways_path: Path = DEFAULT_REACTOME_PATHWAYS_PATH,
    relations_path: Path = DEFAULT_REACTOME_RELATIONS_PATH,
) -> dict[str, tuple[ReactomePathwayAssignment, ...]]:
    selected = set(_normalize_accessions(accessions))
    names_by_stable_id = _load_pathway_names(pathways_path)
    parents_by_child = _load_parent_relations(relations_path)
    assignments_by_accession: dict[str, list[ReactomePathwayAssignment]] = {
        accession: [] for accession in selected
    }
    seen_pairs: set[tuple[str, str]] = set()

    with mapping_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 6:
                continue
            accession, stable_id, pathway_url, pathway_name, evidence_code, species = (
                _clean_text(part) for part in parts[:6]
            )
            accession = accession.upper()
            if accession not in selected or not stable_id:
                continue
            key = (accession, stable_id)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            resolved_name, resolved_species = names_by_stable_id.get(
                stable_id,
                (pathway_name, species),
            )
            ancestor_ids, ancestor_names = _ancestor_chain(
                stable_id,
                parents_by_child=parents_by_child,
                names_by_stable_id=names_by_stable_id,
            )
            assignments_by_accession[accession].append(
                ReactomePathwayAssignment(
                    accession=accession,
                    stable_id=stable_id,
                    pathway_name=resolved_name or pathway_name,
                    evidence_code=evidence_code,
                    species=resolved_species or species,
                    pathway_url=pathway_url,
                    ancestor_ids=ancestor_ids,
                    ancestor_names=ancestor_names,
                )
            )

    return {
        accession: tuple(
            sorted(
                assignments,
                key=lambda item: (item.pathway_name.casefold(), item.stable_id.casefold()),
            )
        )
        for accession, assignments in assignments_by_accession.items()
    }


def _canonical_protein_map(canonical_summary_path: Path) -> dict[str, dict[str, Any]]:
    if not canonical_summary_path.exists():
        return {}
    payload = _read_json(canonical_summary_path)
    proteins = ((payload.get("sequence_result") or {}).get("canonical_proteins") or ())
    result: dict[str, dict[str, Any]] = {}
    for protein in proteins:
        if not isinstance(protein, Mapping):
            continue
        accession = _clean_text(protein.get("accession")).upper()
        if accession:
            result[accession] = dict(protein)
    return result


def _minimal_record(accession: str) -> ProteinSummaryRecord:
    return ProteinSummaryRecord(
        summary_id=f"protein:{accession}",
        protein_ref=f"protein:{accession}",
        protein_name="",
        organism_name="",
        aliases=(accession,),
        join_status="partial",
        join_reason="reactome_only_accession",
        notes=("reactome_only_accession",),
    )


def _canonical_record(protein: Mapping[str, Any]) -> ProteinSummaryRecord:
    accession = _clean_text(protein.get("accession")).upper()
    return ProteinSummaryRecord(
        summary_id=f"protein:{accession}",
        protein_ref=f"protein:{accession}",
        protein_name=_clean_text(protein.get("name") or protein.get("description")),
        organism_name=_clean_text(protein.get("organism")),
        sequence_length=protein.get("sequence_length"),
        gene_names=tuple(str(item) for item in protein.get("gene_names") or ()),
        aliases=tuple(
            dict.fromkeys(
                [accession, *[str(item) for item in protein.get("aliases") or ()]]
            )
        ),
        join_status="joined",
    )


def materialize_reactome_local_summary_library(
    *,
    accessions: Sequence[str],
    canonical_summary_path: Path = DEFAULT_CANONICAL_SUMMARY_PATH,
    mapping_path: Path = DEFAULT_REACTOME_MAPPING_PATH,
    pathways_path: Path = DEFAULT_REACTOME_PATHWAYS_PATH,
    relations_path: Path = DEFAULT_REACTOME_RELATIONS_PATH,
    library_id: str | None = None,
) -> SummaryLibrarySchema:
    normalized_accessions = _normalize_accessions(accessions)
    assignments_by_accession = load_reactome_pathway_assignments(
        accessions=normalized_accessions,
        mapping_path=mapping_path,
        pathways_path=pathways_path,
        relations_path=relations_path,
    )
    canonical_proteins = _canonical_protein_map(canonical_summary_path)
    release_version = _file_release_version(mapping_path)
    records: list[ProteinSummaryRecord] = []

    for accession in normalized_accessions:
        base_record = (
            _canonical_record(canonical_proteins[accession])
            if accession in canonical_proteins
            else _minimal_record(accession)
        )
        assignments = assignments_by_accession.get(accession, ())
        provenance = SummaryProvenancePointer(
            provenance_id=f"reactome-local:{accession}",
            source_name="Reactome",
            source_record_id=accession,
            release_version=release_version,
            acquired_at=_utc_now().isoformat(),
            join_status="joined" if assignments else "partial",
            notes=(
                "local reactome mapping tables",
                f"pathway_count:{len(assignments)}",
            ),
        )
        organism_name = ""
        if assignments:
            species_values = tuple(
                dict.fromkeys(item.species for item in assignments if item.species)
            )
            if len(species_values) == 1:
                organism_name = species_values[0]
        biological_origin = (
            SummaryBiologicalOrigin(organism_name=organism_name)
            if organism_name
            else None
        )
        context = SummaryRecordContext(
            provenance_pointers=(provenance,),
            pathway_references=tuple(
                assignment.to_summary_reference() for assignment in assignments
            ),
            biological_origin=biological_origin,
            storage_notes=(
                "local reactome pathway references derived from pinned mapping tables",
                "empty reactome hits are preserved as explicit partial protein summaries",
            ),
            lazy_loading_guidance=(
                "hydrate full reactome event neighborhoods only after selection",
            ),
        )
        records.append(
            ProteinSummaryRecord(
                summary_id=base_record.summary_id,
                protein_ref=base_record.protein_ref,
                protein_name=base_record.protein_name,
                organism_name=base_record.organism_name or organism_name,
                taxon_id=base_record.taxon_id,
                sequence_checksum=base_record.sequence_checksum,
                sequence_version=base_record.sequence_version,
                sequence_length=base_record.sequence_length,
                gene_names=base_record.gene_names,
                aliases=base_record.aliases,
                join_status=base_record.join_status if assignments else "partial",
                join_reason=base_record.join_reason if assignments else "reactome_empty",
                context=context,
                notes=base_record.notes
                + (() if assignments else ("reactome_empty",)),
            )
        )

    resolved_library_id = library_id or f"summary-library:reactome-local:{_timestamp_slug()}"
    return SummaryLibrarySchema(
        library_id=resolved_library_id,
        source_manifest_id=f"bio-agent-lab/reactome:{release_version}",
        records=tuple(records),
    )


__all__ = [
    "DEFAULT_CANONICAL_SUMMARY_PATH",
    "DEFAULT_REACTOME_MAPPING_PATH",
    "DEFAULT_REACTOME_PATHWAYS_PATH",
    "DEFAULT_REACTOME_RELATIONS_PATH",
    "ReactomePathwayAssignment",
    "load_reactome_pathway_assignments",
    "materialize_reactome_local_summary_library",
]

from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes, Path)):
        return (values,)
    if isinstance(values, tuple):
        return values
    if isinstance(values, list):
        return tuple(values)
    if isinstance(values, Mapping):
        return tuple(values.values())
    try:
        return tuple(values)
    except TypeError:
        return (values,)


def _dedupe_text(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv_rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple(dict(row) for row in csv.DictReader(handle))


def _modality_from_source_ref(source_ref: str) -> str:
    return _clean_text(source_ref.partition(":")[0]).casefold()


def _accession_from_source_ref(source_ref: str) -> str:
    return _clean_text(source_ref.partition(":")[2]).upper()


def _token_matches_path(path: Path, token: str) -> bool:
    token_lower = token.casefold()
    return token_lower in path.name.casefold()


def _split_field_tokens(value: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for raw_value in _iter_values(value):
        for part in str(raw_value).replace(",", ";").split(";"):
            text = _clean_text(part)
            if text:
                ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _source_matches_modality(source: Mapping[str, Any], modality: str) -> bool:
    source_name = _clean_text(source.get("source_name")).casefold()
    category = _clean_text(source.get("category")).casefold()
    if modality == "structure":
        return category == "structure" or "alphafold" in source_name or "rcsb" in source_name
    if modality == "ligand":
        return category == "protein_ligand" or source_name in {"chembl", "bindingdb", "biolip"}
    if modality == "ppi":
        return category == "protein_protein" or category == "interaction_network"
    return False


def _join_key_hints(source: Mapping[str, Any], accession: str) -> tuple[str, ...]:
    keys = _dedupe_text(source.get("join_keys") or ())
    return tuple(key for key in keys if key.casefold() == accession.casefold())


def _sample_path_hints(source: Mapping[str, Any], accession: str) -> tuple[str, ...]:
    hints: list[str] = []
    for root_summary in _iter_values(source.get("present_root_summaries") or ()):
        if not isinstance(root_summary, Mapping):
            continue
        root_path = Path(_clean_text(root_summary.get("path")))
        if not root_path.exists():
            continue
        if root_path.is_file():
            if _token_matches_path(root_path, accession):
                hints.append(str(root_path))
            continue
        matched = 0
        for path in root_path.rglob("*"):
            if matched >= 5:
                break
            if not _token_matches_path(path, accession):
                continue
            hints.append(str(path))
            matched += 1
    return _dedupe_text(hints)


def _registry_sources(local_registry_summary: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    imported = local_registry_summary.get("imported_sources") or ()
    if not isinstance(imported, Sequence) or isinstance(imported, (str, bytes)):
        return ()
    return tuple(dict(item) for item in imported if isinstance(item, Mapping))


def _resolve_master_repository_path(
    local_registry_summary: Mapping[str, Any],
    master_pdb_repository_path: str | Path | None,
) -> Path | None:
    if master_pdb_repository_path is not None:
        path = Path(master_pdb_repository_path)
        return path if path.exists() else None

    storage_root = _clean_text(local_registry_summary.get("storage_root"))
    if not storage_root:
        return None
    path = Path(storage_root) / "master_pdb_repository.csv"
    return path if path.exists() else None


def _rows_for_accession(
    master_rows: Sequence[Mapping[str, str]],
    accession: str,
) -> tuple[dict[str, str], ...]:
    hits: list[dict[str, str]] = []
    accession_key = accession.casefold()
    for row in master_rows:
        proteins = _split_field_tokens(row.get("protein_chain_uniprot_ids"))
        if any(token.casefold() == accession_key for token in proteins):
            hits.append(dict(row))
    return tuple(hits)


def _resolve_master_row_path(
    value: Any,
    *,
    storage_root: Path | None,
) -> Path | None:
    text = _clean_text(value)
    if not text:
        return None
    path = Path(text)
    if not path.is_absolute():
        if storage_root is None:
            return None
        path = storage_root / path
    return path if path.exists() else None


def _master_hint_capable_source(source: Mapping[str, Any], modality: str) -> bool:
    source_name = _clean_text(source.get("source_name")).casefold()
    if modality == "structure":
        return source_name in {"structures_rcsb", "raw_rcsb", "extracted_entry", "extracted_chains"}
    if modality == "ppi":
        return source_name in {"extracted_interfaces", "structures_rcsb", "raw_rcsb"}
    return False


def _master_repository_path_hints(
    source: Mapping[str, Any],
    *,
    modality: str,
    accession: str,
    storage_root: Path | None,
    master_rows: Sequence[Mapping[str, str]],
) -> tuple[tuple[str, ...], tuple[str, ...], str]:
    if not _master_hint_capable_source(source, modality):
        return (), (), ""

    inferred_paths: list[str] = []
    matched_pdb_ids: list[str] = []
    source_name = _clean_text(source.get("source_name")).casefold()

    for row in _rows_for_accession(master_rows, accession):
        pdb_id = _clean_text(row.get("pdb_id")).upper()
        if not pdb_id:
            continue

        row_paths: list[Path] = []
        if modality == "structure":
            if source_name == "structures_rcsb":
                path = _resolve_master_row_path(
                    row.get("structure_file_cif_path"),
                    storage_root=storage_root,
                )
                if path is not None:
                    row_paths.append(path)
            else:
                path = _resolve_master_row_path(
                    row.get("raw_file_path"),
                    storage_root=storage_root,
                )
                if path is not None:
                    row_paths.append(path)
        elif modality == "ppi":
            interface_count = _clean_text(row.get("interface_count"))
            if interface_count and interface_count != "0":
                interface_path = _resolve_master_row_path(
                    Path("data") / "extracted" / "interfaces" / f"{pdb_id}.json",
                    storage_root=storage_root,
                )
                if interface_path is not None:
                    row_paths.append(interface_path)
            structure_path = _resolve_master_row_path(
                row.get("structure_file_cif_path"),
                storage_root=storage_root,
            )
            if structure_path is not None and source_name == "structures_rcsb":
                row_paths.append(structure_path)
            raw_path = _resolve_master_row_path(
                row.get("raw_file_path"),
                storage_root=storage_root,
            )
            if raw_path is not None and source_name == "raw_rcsb":
                row_paths.append(raw_path)

        if row_paths:
            matched_pdb_ids.append(pdb_id)
            inferred_paths.extend(str(path) for path in row_paths)

    deduped_pdb_ids = _dedupe_text(matched_pdb_ids)
    if len(deduped_pdb_ids) > 1:
        return (), deduped_pdb_ids, "ambiguous_master_bridge"

    return _dedupe_text(inferred_paths), deduped_pdb_ids, ""


@dataclass(frozen=True, slots=True)
class LocalGapCandidate:
    source_ref: str
    accession: str
    modality: str
    source_name: str
    category: str
    evidence_strength: str
    status: str
    recovery_candidate: bool
    rationale: str
    join_key_hits: tuple[str, ...]
    path_hints: tuple[str, ...]
    master_pdb_ids: tuple[str, ...]
    inventory_path: str
    manifest_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_ref": self.source_ref,
            "accession": self.accession,
            "modality": self.modality,
            "source_name": self.source_name,
            "category": self.category,
            "evidence_strength": self.evidence_strength,
            "status": self.status,
            "recovery_candidate": self.recovery_candidate,
            "rationale": self.rationale,
            "join_key_hits": list(self.join_key_hits),
            "path_hints": list(self.path_hints),
            "master_pdb_ids": list(self.master_pdb_ids),
            "inventory_path": self.inventory_path,
            "manifest_path": self.manifest_path,
        }


def probe_local_gap_candidates(
    *,
    packet_deficit_dashboard: Mapping[str, Any],
    local_registry_summary: Mapping[str, Any],
    master_pdb_repository_path: str | Path | None = None,
) -> dict[str, Any]:
    source_fix_candidates = packet_deficit_dashboard.get("source_fix_candidates") or ()
    if not isinstance(source_fix_candidates, Sequence) or isinstance(
        source_fix_candidates,
        (str, bytes),
    ):
        source_fix_candidates = ()

    sources = _registry_sources(local_registry_summary)
    resolved_master_repository = _resolve_master_repository_path(
        local_registry_summary,
        master_pdb_repository_path,
    )
    master_rows = (
        _read_csv_rows(resolved_master_repository)
        if resolved_master_repository is not None
        else ()
    )
    storage_root_text = _clean_text(local_registry_summary.get("storage_root"))
    storage_root = Path(storage_root_text) if storage_root_text else None
    candidates: list[LocalGapCandidate] = []

    for item in source_fix_candidates:
        if not isinstance(item, Mapping):
            continue
        source_ref = _clean_text(item.get("source_ref"))
        if not source_ref:
            continue
        modality = _modality_from_source_ref(source_ref)
        accession = _accession_from_source_ref(source_ref)
        for source in sources:
            if not _source_matches_modality(source, modality):
                continue
            status = _clean_text(source.get("status")) or "unknown"
            join_hits = _join_key_hints(source, accession)
            path_hints = _sample_path_hints(source, accession)
            master_path_hints: tuple[str, ...] = ()
            master_pdb_ids: tuple[str, ...] = ()
            master_guard_reason = ""
            if not path_hints and master_rows:
                (
                    master_path_hints,
                    master_pdb_ids,
                    master_guard_reason,
                ) = _master_repository_path_hints(
                    source,
                    modality=modality,
                    accession=accession,
                    storage_root=storage_root,
                    master_rows=master_rows,
                )
                if master_path_hints:
                    path_hints = master_path_hints
            if path_hints:
                evidence_strength = "exact_path_hint"
                recovery_candidate = True
                if master_pdb_ids:
                    rationale = (
                        "local master repository links the accession to concrete local "
                        "structure/interface artifacts"
                    )
                else:
                    rationale = (
                        "local corpus contains accession-named paths under a relevant source"
                    )
            elif join_hits:
                evidence_strength = "join_key_hint"
                recovery_candidate = False
                rationale = (
                    "local registry join keys mention the accession, "
                    "but no accession-named path was found"
                )
                if master_guard_reason == "ambiguous_master_bridge":
                    rationale = (
                        "local registry join keys mention the accession, but the master "
                        "repository matched multiple concrete bridge artifacts, so the "
                        "fallback was withheld"
                    )
            else:
                evidence_strength = "category_only"
                recovery_candidate = False
                rationale = "source category is relevant, but no accession-specific hint was found"
                if master_guard_reason == "ambiguous_master_bridge":
                    rationale = (
                        "source category is relevant, but the master repository matched "
                        "multiple concrete bridge artifacts, so the fallback was withheld"
                    )
            candidates.append(
                LocalGapCandidate(
                    source_ref=source_ref,
                    accession=accession,
                    modality=modality,
                    source_name=_clean_text(source.get("source_name")),
                    category=_clean_text(source.get("category")),
                    evidence_strength=evidence_strength,
                    status=status,
                    recovery_candidate=recovery_candidate,
                    rationale=rationale,
                    join_key_hits=join_hits,
                    path_hints=path_hints,
                    master_pdb_ids=master_pdb_ids,
                    inventory_path=_clean_text(source.get("inventory_path")),
                    manifest_path=_clean_text(source.get("manifest_path")),
                )
            )

    sorted_candidates = sorted(
        candidates,
        key=lambda item: (
            item.source_ref.casefold(),
            {"exact_path_hint": 0, "join_key_hint": 1, "category_only": 2}.get(
                item.evidence_strength, 3
            ),
            item.source_name.casefold(),
        ),
    )
    return {
        "master_pdb_repository_path": (
            str(resolved_master_repository) if resolved_master_repository is not None else ""
        ),
        "master_pdb_repository_available": resolved_master_repository is not None,
        "candidate_count": len(sorted_candidates),
        "recovery_candidate_count": sum(1 for item in sorted_candidates if item.recovery_candidate),
        "candidates": [item.to_dict() for item in sorted_candidates],
    }

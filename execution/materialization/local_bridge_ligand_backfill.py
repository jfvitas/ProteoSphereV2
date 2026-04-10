from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from execution.acquire.local_pair_ligand_bridge import (
    LocalBridgeRecord,
    bridge_local_protein_ligand,
)
from execution.acquire.local_source_registry import (
    DEFAULT_LOCAL_SOURCE_ROOT,
    LocalSourceEntry,
    build_default_local_source_registry,
)

BridgeLigandBackfillStatus = Literal["resolved", "unresolved"]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _optional_text(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes, Path)):
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


def _split_semicolon_text(value: Any) -> tuple[str, ...]:
    text = _clean_text(value)
    if not text:
        return ()
    return _dedupe_text(part for part in text.split(";"))


def _normalize_mapping(payload: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return dict(payload)


def _normalize_row(payload: Mapping[str, Any]) -> dict[str, Any]:
    return dict(payload)


@dataclass(frozen=True, slots=True)
class BoundObjectLigandCandidate:
    pdb_id: str
    component_id: str
    component_type: str
    component_role: str
    chain_ids: tuple[str, ...] = ()
    smiles: str = ""
    inchi_key: str = ""
    component_name: str = ""
    source_row: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "pdb_id", _clean_text(self.pdb_id).upper())
        object.__setattr__(self, "component_id", _clean_text(self.component_id))
        object.__setattr__(self, "component_type", _clean_text(self.component_type))
        object.__setattr__(self, "component_role", _clean_text(self.component_role))
        object.__setattr__(self, "chain_ids", _dedupe_text(self.chain_ids))
        object.__setattr__(self, "smiles", _clean_text(self.smiles))
        object.__setattr__(self, "inchi_key", _clean_text(self.inchi_key))
        object.__setattr__(self, "component_name", _clean_text(self.component_name))
        object.__setattr__(self, "source_row", dict(self.source_row))
        if not self.pdb_id:
            raise ValueError("pdb_id must not be empty")
        if not self.component_id:
            raise ValueError("component_id must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "pdb_id": self.pdb_id,
            "component_id": self.component_id,
            "component_type": self.component_type,
            "component_role": self.component_role,
            "chain_ids": list(self.chain_ids),
            "smiles": self.smiles,
            "inchi_key": self.inchi_key,
            "component_name": self.component_name,
            "source_row": dict(self.source_row),
        }


@dataclass(frozen=True, slots=True)
class BridgeLigandBackfillEntry:
    accession: str
    canonical_id: str
    split: str | None
    pdb_id: str
    status: BridgeLigandBackfillStatus
    bridge_state: str
    bridge_kind: str | None
    selected_ligand: BoundObjectLigandCandidate | None = None
    bridge_record: LocalBridgeRecord | None = None
    notes: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "accession", _clean_text(self.accession))
        object.__setattr__(self, "canonical_id", _clean_text(self.canonical_id))
        object.__setattr__(self, "split", _optional_text(self.split))
        object.__setattr__(self, "pdb_id", _clean_text(self.pdb_id).upper())
        object.__setattr__(self, "bridge_state", _clean_text(self.bridge_state))
        object.__setattr__(self, "bridge_kind", _optional_text(self.bridge_kind))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        object.__setattr__(self, "issues", _dedupe_text(self.issues))
        if self.status not in {"resolved", "unresolved"}:
            raise ValueError(f"unsupported status: {self.status!r}")
        if not self.accession:
            raise ValueError("accession must not be empty")
        if not self.canonical_id:
            raise ValueError("canonical_id must not be empty")
        if not self.pdb_id:
            raise ValueError("pdb_id must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "canonical_id": self.canonical_id,
            "split": self.split,
            "pdb_id": self.pdb_id,
            "status": self.status,
            "bridge_state": self.bridge_state,
            "bridge_kind": self.bridge_kind,
            "selected_ligand": (
                self.selected_ligand.to_dict() if self.selected_ligand is not None else None
            ),
            "bridge_record": (
                self.bridge_record.to_dict() if self.bridge_record is not None else None
            ),
            "notes": list(self.notes),
            "issues": list(self.issues),
        }


def _candidate_from_row(payload: Mapping[str, Any]) -> BoundObjectLigandCandidate:
    row = _normalize_row(payload)
    return BoundObjectLigandCandidate(
        pdb_id=row.get("pdb_id") or "",
        component_id=row.get("component_id") or row.get("ligand_id") or "",
        component_type=row.get("component_type") or "",
        component_role=row.get("component_role") or "",
        chain_ids=row.get("chain_ids") or (),
        smiles=row.get("component_smiles") or row.get("ligand_smiles") or "",
        inchi_key=row.get("component_inchikey") or row.get("ligand_inchi_key") or "",
        component_name=row.get("component_name") or "",
        source_row=row,
    )


def load_bound_object_rows(path: Path) -> tuple[dict[str, Any], ...]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise TypeError(f"bound-object payload at {path} must be a JSON list")
    return tuple(_normalize_row(row) for row in payload if isinstance(row, Mapping))


def _read_csv_rows(path: Path) -> tuple[dict[str, Any], ...]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.DictReader(handle)
        return tuple(dict(row) for row in rows)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _master_repository_path(local_source_root: Path = DEFAULT_LOCAL_SOURCE_ROOT) -> Path:
    root_path = local_source_root / "master_pdb_repository.csv"
    if root_path.exists():
        return root_path
    release_path = local_source_root / "data" / "releases" / "test_v1" / "master_pdb_repository.csv"
    return release_path


def _safe_float(value: Any) -> float:
    text = _clean_text(value)
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _local_source_root_from_bound_objects(bound_object_root: Path) -> Path | None:
    try:
        data_root = bound_object_root.parents[1]
    except IndexError:
        return None
    if data_root.name.casefold() != "data":
        return None
    return data_root.parent


def _local_source_root_from_master_repository(master_repository_path: Path | None) -> Path | None:
    if master_repository_path is None:
        return None
    parent = master_repository_path.parent
    if (parent / "data").exists():
        return parent
    for candidate in master_repository_path.parents:
        if (candidate / "data").exists():
            return candidate
    return None


def _resolve_local_path(path_text: Any, *, local_source_root: Path | None) -> Path | None:
    text = _clean_text(path_text)
    if not text:
        return None
    path = Path(text)
    if not path.is_absolute():
        if local_source_root is None:
            return None
        path = local_source_root / path
    return path if path.exists() else None


def _target_chain_ids_from_raw_payload(
    raw_payload_path: Path | None,
    *,
    accession: str,
) -> tuple[str, ...]:
    if raw_payload_path is None or not raw_payload_path.exists():
        return ()
    payload = _read_json(raw_payload_path)
    if not isinstance(payload, Mapping):
        return ()
    accession_key = _clean_text(accession).upper()
    chain_ids: list[str] = []
    for entity in payload.get("polymer_entities") or ():
        if not isinstance(entity, Mapping):
            continue
        identifiers = entity.get("rcsb_polymer_entity_container_identifiers")
        if not isinstance(identifiers, Mapping):
            continue
        uniprot_ids = {
            _clean_text(value).upper() for value in identifiers.get("uniprot_ids") or ()
        }
        if accession_key not in uniprot_ids:
            continue
        chain_ids.extend(
            _clean_text(value) for value in identifiers.get("auth_asym_ids") or ()
        )
    return _dedupe_text(chain_ids)


def _alternate_bridge_candidates(
    *,
    accession: str,
    current_pdb_id: str,
    master_repository_path: Path | None,
    bound_object_root: Path,
) -> tuple[dict[str, Any], ...]:
    if master_repository_path is None or not master_repository_path.exists():
        return ()
    accession_key = accession.upper()
    current_key = current_pdb_id.upper()
    local_source_root = _local_source_root_from_bound_objects(bound_object_root)
    if local_source_root is None:
        local_source_root = _local_source_root_from_master_repository(master_repository_path)
    candidates: list[tuple[float, str, dict[str, Any]]] = []
    for row in _read_csv_rows(master_repository_path):
        pdb_id = _clean_text(row.get("pdb_id")).upper()
        if not pdb_id or pdb_id == current_key:
            continue
        observed_accessions = {
            value.upper()
            for value in _split_semicolon_text(row.get("protein_chain_uniprot_ids"))
        }
        if accession_key not in observed_accessions:
            continue
        bound_object_path = bound_object_root / f"{pdb_id}.json"
        if not bound_object_path.exists():
            continue
        raw_payload_path = _resolve_local_path(
            row.get("raw_file_path"),
            local_source_root=local_source_root,
        )
        target_chain_ids = _target_chain_ids_from_raw_payload(
            raw_payload_path,
            accession=accession,
        )
        ligand_types = {
            value.casefold() for value in _split_semicolon_text(row.get("ligand_types"))
        }
        ligand_component_ids = _split_semicolon_text(row.get("ligand_component_ids"))
        has_small_molecule = "small_molecule" in ligand_types
        has_ligand_signal = _clean_text(row.get("has_ligand_signal")).casefold() == "true"
        score = (
            (1000.0 if has_small_molecule else 0.0)
            + (100.0 if has_ligand_signal else 0.0)
            + (10.0 if ligand_component_ids else 0.0)
            + _safe_float(row.get("quality_score"))
        )
        candidates.append(
            (
                score,
                pdb_id,
                {
                    "pdb_id": pdb_id,
                    "quality_score": _safe_float(row.get("quality_score")),
                    "ligand_types": tuple(sorted(ligand_types)),
                    "ligand_component_ids": ligand_component_ids,
                    "observed_accessions": tuple(sorted(observed_accessions)),
                    "target_chain_ids": target_chain_ids,
                },
            )
        )
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return tuple(item[2] for item in candidates)


def select_primary_small_molecule_candidate(
    rows: Iterable[Mapping[str, Any]],
    *,
    bridge_chain_ids: Sequence[str] = (),
) -> tuple[BoundObjectLigandCandidate | None, tuple[str, ...]]:
    candidates = []
    for row in rows:
        try:
            candidates.append(_candidate_from_row(row))
        except (TypeError, ValueError):
            continue
    candidates = tuple(candidates)
    eligible = tuple(
        candidate
        for candidate in candidates
        if candidate.component_role == "primary_binder"
        and candidate.component_type == "small_molecule"
    )
    if not eligible:
        return None, ("no_primary_small_molecule_bound_object",)

    bridge_lookup = {chain_id.casefold() for chain_id in _dedupe_text(bridge_chain_ids)}
    if bridge_lookup:
        overlapping = tuple(
            candidate
            for candidate in eligible
            if not candidate.chain_ids
            or bridge_lookup.intersection(chain_id.casefold() for chain_id in candidate.chain_ids)
        )
        if not overlapping:
            return None, ("no_primary_small_molecule_on_target_chains",)
        eligible = overlapping

    distinct_component_ids = {candidate.component_id for candidate in eligible}
    if len(distinct_component_ids) > 1:
        return None, ("ambiguous_primary_small_molecule_candidates",)
    return eligible[0], ()


def build_bridge_ligand_backfill_entry(
    cohort_row: Mapping[str, Any],
    *,
    bound_object_rows: Iterable[Mapping[str, Any]],
    source_entry: LocalSourceEntry | None = None,
) -> BridgeLigandBackfillEntry:
    row = _normalize_mapping(cohort_row, "cohort_row")
    accession = _clean_text(row.get("accession"))
    canonical_id = _clean_text(row.get("canonical_id")) or f"protein:{accession}"
    split = _optional_text(row.get("split"))
    bridge = row.get("bridge")
    if not isinstance(bridge, Mapping):
        raise ValueError("cohort_row must include a bridge mapping")

    bridge_state = _clean_text(bridge.get("state"))
    bridge_kind = _optional_text(bridge.get("bridge_kind"))
    pdb_id = _clean_text(bridge.get("pdb_id")).upper()
    bridge_chain_ids = _dedupe_text(bridge.get("chain_ids") or ())

    if bridge_state not in {"positive_hit", "ready_now"} or not pdb_id:
        return BridgeLigandBackfillEntry(
            accession=accession,
            canonical_id=canonical_id,
            split=split,
            pdb_id=pdb_id or "UNKNOWN",
            status="unresolved",
            bridge_state=bridge_state or "absent",
            bridge_kind=bridge_kind,
            notes=("bridge_payload_not_positive_hit",),
            issues=("bridge_payload_not_positive_hit",),
        )

    selected, issues = select_primary_small_molecule_candidate(
        bound_object_rows,
        bridge_chain_ids=bridge_chain_ids,
    )
    if selected is None:
        return BridgeLigandBackfillEntry(
            accession=accession,
            canonical_id=canonical_id,
            split=split,
            pdb_id=pdb_id,
            status="unresolved",
            bridge_state=bridge_state,
            bridge_kind=bridge_kind,
            notes=("primary_binder_small_molecule_rule_failed",),
            issues=issues,
        )

    bridge_record = bridge_local_protein_ligand(
        source_name="extracted_bound_objects",
        source_record_id=f"{accession}:{pdb_id}:{selected.component_id}",
        pdb_id=pdb_id,
        protein_accessions=(accession,),
        protein_chain_ids=bridge_chain_ids,
        ligand_id=selected.component_id,
        ligand_inchi_key=selected.inchi_key,
        ligand_smiles=selected.smiles,
        ligand_role="small_molecule",
        source_entry=source_entry,
    )
    status: BridgeLigandBackfillStatus = "resolved"
    final_issues = tuple(issues)
    if bridge_record.status != "resolved":
        status = "unresolved"
        final_issues = final_issues + tuple(issue.code for issue in bridge_record.issues)

    return BridgeLigandBackfillEntry(
        accession=accession,
        canonical_id=canonical_id,
        split=split,
        pdb_id=pdb_id,
        status=status,
        bridge_state=bridge_state,
        bridge_kind=bridge_kind,
        selected_ligand=selected,
        bridge_record=bridge_record,
        notes=("primary_binder_small_molecule_backfill",),
        issues=final_issues,
    )


def materialize_selected_cohort_bridge_ligand_entries(
    cohort_rows: Iterable[Mapping[str, Any]],
    *,
    bound_object_root: Path,
    source_entry: LocalSourceEntry | None = None,
    master_repository_path: Path | None = None,
) -> tuple[BridgeLigandBackfillEntry, ...]:
    resolved_master_repository_path = (
        master_repository_path
        if master_repository_path is not None
        else default_master_repository_path()
    )
    entries: list[BridgeLigandBackfillEntry] = []
    for row in cohort_rows:
        if not isinstance(row, Mapping):
            continue
        bridge = row.get("bridge")
        if not isinstance(bridge, Mapping):
            continue
        pdb_id = _clean_text(bridge.get("pdb_id")).upper()
        if not pdb_id:
            continue
        bound_object_path = bound_object_root / f"{pdb_id}.json"
        accession = _clean_text(row.get("accession"))
        canonical_id = _clean_text(row.get("canonical_id")) or f"protein:{accession}"
        if bound_object_path.exists():
            entry = build_bridge_ligand_backfill_entry(
                row,
                bound_object_rows=load_bound_object_rows(bound_object_path),
                source_entry=source_entry,
            )
        else:
            entry = BridgeLigandBackfillEntry(
                accession=accession,
                canonical_id=canonical_id,
                split=_optional_text(row.get("split")),
                pdb_id=pdb_id,
                status="unresolved",
                bridge_state=_clean_text(bridge.get("state")) or "absent",
                bridge_kind=_optional_text(bridge.get("bridge_kind")),
                notes=("bound_object_payload_missing",),
                issues=("bound_object_payload_missing",),
            )

        if entry.status == "resolved":
            entries.append(entry)
            continue

        fallback_issues = {issue.casefold() for issue in entry.issues}
        if fallback_issues.intersection(
            {
                "bound_object_payload_missing",
                "no_primary_small_molecule_bound_object",
                "no_primary_small_molecule_on_target_chains",
            }
        ):
            fallback_entry: BridgeLigandBackfillEntry | None = None
            for candidate in _alternate_bridge_candidates(
                accession=accession,
                current_pdb_id=pdb_id,
                master_repository_path=resolved_master_repository_path,
                bound_object_root=bound_object_root,
            ):
                candidate_chain_ids = _dedupe_text(candidate.get("target_chain_ids") or ())
                if not candidate_chain_ids:
                    continue
                fallback_row = dict(row)
                fallback_bridge = dict(bridge)
                fallback_bridge["pdb_id"] = candidate["pdb_id"]
                fallback_bridge["chain_ids"] = candidate_chain_ids
                fallback_row["bridge"] = fallback_bridge
                candidate_entry = build_bridge_ligand_backfill_entry(
                    fallback_row,
                    bound_object_rows=load_bound_object_rows(
                        bound_object_root / f"{candidate['pdb_id']}.json"
                    ),
                    source_entry=source_entry,
                )
                if candidate_entry.status != "resolved":
                    continue
                fallback_entry = BridgeLigandBackfillEntry(
                    accession=candidate_entry.accession,
                    canonical_id=candidate_entry.canonical_id,
                    split=candidate_entry.split,
                    pdb_id=candidate_entry.pdb_id,
                    status=candidate_entry.status,
                    bridge_state=candidate_entry.bridge_state,
                    bridge_kind=candidate_entry.bridge_kind,
                    selected_ligand=candidate_entry.selected_ligand,
                    bridge_record=candidate_entry.bridge_record,
                    notes=(
                        *candidate_entry.notes,
                        "fallback_bridge_candidate_from_master_repository",
                        f"fallback_from={pdb_id}",
                    ),
                    issues=candidate_entry.issues,
                )
                break
            if fallback_entry is not None:
                entries.append(fallback_entry)
                continue

        entries.append(entry)
    return tuple(entries)


def default_bound_object_root(local_source_root: Path = DEFAULT_LOCAL_SOURCE_ROOT) -> Path:
    return local_source_root / "data" / "extracted" / "bound_objects"


def default_master_repository_path(
    local_source_root: Path = DEFAULT_LOCAL_SOURCE_ROOT,
) -> Path:
    return _master_repository_path(local_source_root)


def default_bound_object_source_entry(
    local_source_root: Path = DEFAULT_LOCAL_SOURCE_ROOT,
) -> LocalSourceEntry | None:
    registry = build_default_local_source_registry(local_source_root)
    return registry.get("extracted_bound_objects")


__all__ = [
    "BoundObjectLigandCandidate",
    "BridgeLigandBackfillEntry",
    "BridgeLigandBackfillStatus",
    "build_bridge_ligand_backfill_entry",
    "default_bound_object_root",
    "default_master_repository_path",
    "default_bound_object_source_entry",
    "load_bound_object_rows",
    "materialize_selected_cohort_bridge_ligand_entries",
    "select_primary_small_molecule_candidate",
]

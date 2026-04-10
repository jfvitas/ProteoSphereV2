from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from execution.acquire.local_pair_ligand_bridge import (
    LocalBridgeRecord,
    bridge_local_protein_pair,
)
from execution.acquire.local_source_registry import (
    DEFAULT_LOCAL_SOURCE_ROOT,
    LocalSourceEntry,
    build_default_local_source_registry,
)

BridgePpiBackfillStatus = Literal["resolved", "unresolved"]
BridgePpiState = Literal["positive_hit", "reachable_empty", "unavailable"]
BridgePpiChainState = Literal["not_asserted", "ambiguous", "unresolved"]


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


def _normalize_pdb_id(value: Any) -> str:
    text = _clean_text(value).upper()
    if len(text) != 4 or not text.isalnum():
        raise ValueError(f"invalid pdb_id: {value!r}")
    return text


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_csv_rows(path: Path) -> tuple[dict[str, Any], ...]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.DictReader(handle)
        return tuple(dict(row) for row in rows)


def _load_json_rows(path: Path) -> tuple[dict[str, Any], ...]:
    payload = _read_json(path)
    if not isinstance(payload, list):
        raise TypeError(f"{path} must contain a JSON list")
    return tuple(dict(item) for item in payload if isinstance(item, Mapping))


def _cohort_rows(payload: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    for key in ("rows", "selected_rows", "selected_examples", "proposals"):
        rows = payload.get(key) or ()
        if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes)):
            return tuple(dict(row) for row in rows if isinstance(row, Mapping))
    return ()


def _selected_accessions_from_rows(rows: Iterable[Mapping[str, Any]]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for row in rows:
        accession = _clean_text(row.get("accession"))
        if accession:
            ordered.setdefault(accession.casefold(), accession)
    return tuple(ordered.values())


def _selected_accessions(value: str) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for accession in _dedupe_text(value.split(",")):
        ordered.setdefault(accession.casefold(), accession)
    return tuple(ordered.values())


def _master_repository_path(local_source_root: Path = DEFAULT_LOCAL_SOURCE_ROOT) -> Path:
    root_path = local_source_root / "master_pdb_repository.csv"
    if root_path.exists():
        return root_path
    release_path = local_source_root / "data" / "releases" / "test_v1" / "master_pdb_repository.csv"
    return release_path


def _default_interface_root(local_source_root: Path = DEFAULT_LOCAL_SOURCE_ROOT) -> Path:
    return local_source_root / "data" / "extracted" / "interfaces"


def _default_structure_root(local_source_root: Path = DEFAULT_LOCAL_SOURCE_ROOT) -> Path:
    return local_source_root / "data" / "structures" / "rcsb"


def _ppi_source_entry(
    local_source_root: Path = DEFAULT_LOCAL_SOURCE_ROOT,
) -> LocalSourceEntry | None:
    registry = build_default_local_source_registry(local_source_root)
    return registry.get("extracted_interfaces")


def _resolve_structure_path(row: Mapping[str, Any], structure_root: Path, pdb_id: str) -> Path:
    row_path = _optional_text(row.get("structure_file_cif_path"))
    if row_path:
        candidate = Path(row_path)
        if candidate.exists():
            return candidate
    candidate = structure_root / f"{pdb_id}.cif"
    return candidate


def _resolve_interface_path(interface_root: Path, pdb_id: str) -> Path:
    return interface_root / f"{pdb_id}.json"


def _interface_record_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "pdb_id": _clean_text(payload.get("pdb_id")),
        "interface_type": _clean_text(payload.get("interface_type")),
        "partner_a_chain_ids": [
            _clean_text(value) for value in payload.get("partner_a_chain_ids") or ()
        ],
        "partner_b_chain_ids": [
            _clean_text(value) for value in payload.get("partner_b_chain_ids") or ()
        ],
        "entity_id_a": _optional_text(payload.get("entity_id_a")),
        "entity_id_b": _optional_text(payload.get("entity_id_b")),
        "interface_is_symmetric": bool(payload.get("interface_is_symmetric", False)),
        "is_hetero": bool(payload.get("is_hetero", False)),
    }


def _structure_summary(row: Mapping[str, Any], structure_path: Path) -> dict[str, Any]:
    return {
        "pdb_id": _clean_text(row.get("pdb_id")),
        "protein_chain_ids": _split_semicolon_text(row.get("protein_chain_ids")),
        "protein_chain_uniprot_ids": _split_semicolon_text(row.get("protein_chain_uniprot_ids")),
        "interface_count": int(row.get("interface_count") or 0),
        "interface_types": _split_semicolon_text(row.get("interface_types")),
        "structure_file_cif_path": str(structure_path),
        "raw_file_path": _optional_text(row.get("raw_file_path")),
    }


@dataclass(frozen=True, slots=True)
class PpiBridgeBackfillEntry:
    pdb_id: str
    accession_a: str
    accession_b: str | None
    canonical_id_a: str
    canonical_id_b: str | None
    status: BridgePpiBackfillStatus
    bridge_state: BridgePpiState
    bridge_kind: str | None
    chain_assignment_state: BridgePpiChainState
    observed_accessions: tuple[str, ...]
    observed_chain_ids: tuple[str, ...]
    interface_records: tuple[dict[str, Any], ...]
    structure_file_path: str
    interface_file_path: str
    source_record_id: str
    pair_canonical_id: str | None = None
    bridge_record: LocalBridgeRecord | None = None
    source_name: str = "master_pdb_repository"
    source_entry_id: str = ""
    notes: tuple[str, ...] = field(default_factory=tuple)
    issues: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "pdb_id", _normalize_pdb_id(self.pdb_id))
        object.__setattr__(self, "accession_a", _clean_text(self.accession_a))
        object.__setattr__(self, "accession_b", _optional_text(self.accession_b))
        object.__setattr__(self, "canonical_id_a", _clean_text(self.canonical_id_a))
        object.__setattr__(self, "canonical_id_b", _optional_text(self.canonical_id_b))
        object.__setattr__(self, "bridge_kind", _optional_text(self.bridge_kind))
        object.__setattr__(self, "observed_accessions", _dedupe_text(self.observed_accessions))
        object.__setattr__(self, "observed_chain_ids", _dedupe_text(self.observed_chain_ids))
        object.__setattr__(
            self,
            "interface_records",
            tuple(dict(row) for row in self.interface_records),
        )
        object.__setattr__(self, "structure_file_path", _clean_text(self.structure_file_path))
        object.__setattr__(self, "interface_file_path", _clean_text(self.interface_file_path))
        object.__setattr__(self, "source_record_id", _clean_text(self.source_record_id))
        object.__setattr__(
            self,
            "source_name",
            _clean_text(self.source_name) or "master_pdb_repository",
        )
        object.__setattr__(self, "source_entry_id", _clean_text(self.source_entry_id))
        object.__setattr__(self, "notes", _dedupe_text(self.notes))
        object.__setattr__(self, "issues", _dedupe_text(self.issues))
        if self.status not in {"resolved", "unresolved"}:
            raise ValueError(f"unsupported status: {self.status!r}")
        if self.bridge_state not in {"positive_hit", "reachable_empty", "unavailable"}:
            raise ValueError(f"unsupported bridge_state: {self.bridge_state!r}")
        if self.chain_assignment_state not in {"not_asserted", "ambiguous", "unresolved"}:
            raise ValueError(
                f"unsupported chain_assignment_state: {self.chain_assignment_state!r}"
            )
        if not self.pdb_id:
            raise ValueError("pdb_id must not be empty")
        if not self.accession_a:
            raise ValueError("accession_a must not be empty")
        if not self.canonical_id_a:
            raise ValueError("canonical_id_a must not be empty")
        if self.status == "resolved":
            if not self.accession_b:
                raise ValueError("resolved entries must include accession_b")
            if not self.canonical_id_b:
                raise ValueError("resolved entries must include canonical_id_b")
            if self.pair_canonical_id is None:
                raise ValueError("resolved entries must include pair_canonical_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "pdb_id": self.pdb_id,
            "accession_a": self.accession_a,
            "accession_b": self.accession_b,
            "canonical_id_a": self.canonical_id_a,
            "canonical_id_b": self.canonical_id_b,
            "status": self.status,
            "bridge_state": self.bridge_state,
            "bridge_kind": self.bridge_kind,
            "chain_assignment_state": self.chain_assignment_state,
            "observed_accessions": list(self.observed_accessions),
            "observed_chain_ids": list(self.observed_chain_ids),
            "interface_records": [dict(record) for record in self.interface_records],
            "structure_file_path": self.structure_file_path,
            "interface_file_path": self.interface_file_path,
            "source_record_id": self.source_record_id,
            "source_name": self.source_name,
            "source_entry_id": self.source_entry_id,
            "pair_canonical_id": self.pair_canonical_id,
            "bridge_record": (
                self.bridge_record.to_dict() if self.bridge_record is not None else None
            ),
            "notes": list(self.notes),
            "issues": list(self.issues),
        }


def _bridge_notes(
    *,
    pdb_id: str,
    interface_records: tuple[dict[str, Any], ...],
    chain_assignment_state: BridgePpiChainState,
) -> tuple[str, ...]:
    notes = [
        "pair_accessions_resolved_from_master_repository",
        f"interface_count={len(interface_records)}",
        f"pdb_id={pdb_id}",
    ]
    if chain_assignment_state == "not_asserted":
        notes.append("chain_assignment_not_asserted_from_local_files")
    return tuple(notes)


def _bridge_issues(
    *,
    observed_accessions: tuple[str, ...],
    structure_file_path: Path,
    interface_file_path: Path,
) -> tuple[str, ...]:
    issues: list[str] = []
    if not structure_file_path.exists():
        issues.append("missing_structure_payload")
    if not interface_file_path.exists():
        issues.append("missing_interface_payload")
    if len(observed_accessions) < 2:
        issues.append("missing_partner_accession")
    if len(observed_accessions) > 2:
        issues.append("ambiguous_pair_accessions")
    return tuple(issues)


def build_local_bridge_ppi_backfill_entry(
    master_row: Mapping[str, Any],
    *,
    interface_root: Path,
    structure_root: Path,
    source_entry: LocalSourceEntry | None = None,
) -> PpiBridgeBackfillEntry:
    row = dict(master_row)
    pdb_id = _normalize_pdb_id(row.get("pdb_id"))
    observed_accessions = _split_semicolon_text(row.get("protein_chain_uniprot_ids"))
    observed_chain_ids = _split_semicolon_text(row.get("protein_chain_ids"))
    structure_path = _resolve_structure_path(row, structure_root, pdb_id)
    interface_path = _resolve_interface_path(interface_root, pdb_id)
    interface_records = (
        _load_json_rows(interface_path) if interface_path.exists() else ()
    )
    interface_summaries = tuple(
        _interface_record_summary(record)
        for record in interface_records
        if isinstance(record, Mapping)
    )
    source_record_id = f"{pdb_id}:{':'.join(observed_accessions) or 'unresolved'}"
    source_entry_id = source_entry.source_name if source_entry is not None else ""
    issues = _bridge_issues(
        observed_accessions=observed_accessions,
        structure_file_path=structure_path,
        interface_file_path=interface_path,
    )

    if issues:
        bridge_state: BridgePpiState = (
            "unavailable"
            if (
                "missing_structure_payload" in issues
                or "missing_interface_payload" in issues
            )
            else "reachable_empty"
        )
        chain_state: BridgePpiChainState = (
            "unresolved"
            if bridge_state == "unavailable"
            else (
                "ambiguous"
                if (
                    "ambiguous_pair_accessions" in issues
                    or "missing_partner_accession" in issues
                )
                else "not_asserted"
            )
        )
        accession_a = observed_accessions[0] if observed_accessions else ""
        accession_b = observed_accessions[1] if len(observed_accessions) > 1 else None
        return PpiBridgeBackfillEntry(
            pdb_id=pdb_id,
            accession_a=accession_a,
            accession_b=accession_b,
            canonical_id_a=f"protein:{accession_a}" if accession_a else "",
            canonical_id_b=f"protein:{accession_b}" if accession_b else None,
            status="unresolved",
            bridge_state=bridge_state,
            bridge_kind="bridge_only",
            chain_assignment_state=chain_state,
            observed_accessions=observed_accessions,
            observed_chain_ids=observed_chain_ids,
            interface_records=interface_summaries,
            structure_file_path=str(structure_path),
            interface_file_path=str(interface_path),
            source_record_id=source_record_id,
            source_name="master_pdb_repository",
            source_entry_id=source_entry_id,
            notes=_dedupe_text(
                (
                    "local_ppi_backfill_requires_complete_pair_evidence",
                    *issues,
                )
            ),
            issues=issues,
        )

    accession_a, accession_b = observed_accessions[:2]
    bridge_record = bridge_local_protein_pair(
        source_name="master_pdb_repository",
        source_record_id=source_record_id,
        pdb_id=pdb_id,
        receptor_accessions=(accession_a,),
        partner_accessions=(accession_b,),
        source_entry=source_entry,
    )
    bridge_state = (
        "positive_hit" if bridge_record.status == "resolved" else "reachable_empty"
    )
    status: BridgePpiBackfillStatus = (
        "resolved" if bridge_record.status == "resolved" else "unresolved"
    )
    pair_canonical_id = (
        bridge_record.pair_canonical_id if bridge_record.status == "resolved" else None
    )
    notes = _bridge_notes(
        pdb_id=pdb_id,
        interface_records=interface_summaries,
        chain_assignment_state="not_asserted",
    )
    issues = tuple(issue.code for issue in bridge_record.issues)
    if not interface_summaries:
        status = "unresolved"
        bridge_state = "reachable_empty"
        issues = issues + ("empty_interface_payload",)
    return PpiBridgeBackfillEntry(
        pdb_id=pdb_id,
        accession_a=accession_a,
        accession_b=accession_b,
        canonical_id_a=f"protein:{accession_a}",
        canonical_id_b=f"protein:{accession_b}",
        status=status,
        bridge_state=bridge_state,
        bridge_kind="bridge_only",
        chain_assignment_state="not_asserted",
        observed_accessions=observed_accessions,
        observed_chain_ids=observed_chain_ids,
        interface_records=interface_summaries,
        structure_file_path=str(structure_path),
        interface_file_path=str(interface_path),
        source_record_id=source_record_id,
        pair_canonical_id=pair_canonical_id,
        bridge_record=bridge_record if status == "resolved" else None,
        source_name="master_pdb_repository",
        source_entry_id=source_entry_id,
        notes=notes,
        issues=issues,
    )


def materialize_selected_cohort_bridge_ppi_entries(
    cohort_rows: Iterable[Mapping[str, Any]],
    *,
    master_repository_path: Path,
    interface_root: Path,
    structure_root: Path,
    source_entry: LocalSourceEntry | None = None,
    selected_accessions: Sequence[str] = (),
) -> tuple[PpiBridgeBackfillEntry, ...]:
    selected_lookup = {accession.casefold() for accession in _dedupe_text(selected_accessions)}
    master_rows = _read_csv_rows(master_repository_path)
    entries: list[PpiBridgeBackfillEntry] = []
    seen_keys: set[tuple[str, tuple[str, ...]]] = set()

    for master_row in master_rows:
        pdb_id = _clean_text(master_row.get("pdb_id")).upper()
        if not pdb_id:
            continue
        observed_accessions = _split_semicolon_text(master_row.get("protein_chain_uniprot_ids"))
        if not observed_accessions:
            continue
        if selected_lookup and not any(
            accession.casefold() in selected_lookup for accession in observed_accessions
        ):
            continue
        key = (pdb_id, observed_accessions)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        entries.append(
            build_local_bridge_ppi_backfill_entry(
                master_row,
                interface_root=interface_root,
                structure_root=structure_root,
                source_entry=source_entry,
            )
        )
    return tuple(entries)


def default_master_repository_path(
    local_source_root: Path = DEFAULT_LOCAL_SOURCE_ROOT,
) -> Path:
    return _master_repository_path(local_source_root)


def default_interface_root(local_source_root: Path = DEFAULT_LOCAL_SOURCE_ROOT) -> Path:
    return _default_interface_root(local_source_root)


def default_structure_root(local_source_root: Path = DEFAULT_LOCAL_SOURCE_ROOT) -> Path:
    return _default_structure_root(local_source_root)


def default_ppi_source_entry(
    local_source_root: Path = DEFAULT_LOCAL_SOURCE_ROOT,
) -> LocalSourceEntry | None:
    return _ppi_source_entry(local_source_root)


__all__ = [
    "BridgePpiBackfillStatus",
    "BridgePpiChainState",
    "BridgePpiState",
    "PpiBridgeBackfillEntry",
    "build_local_bridge_ppi_backfill_entry",
    "default_interface_root",
    "default_master_repository_path",
    "default_ppi_source_entry",
    "default_structure_root",
    "materialize_selected_cohort_bridge_ppi_entries",
]

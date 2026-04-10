from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from random import Random
from typing import Any, Literal

SplitName = Literal["train", "val", "test"]

DEFAULT_SPLIT_ORDER: tuple[SplitName, ...] = ("train", "val", "test")
DEFAULT_SPLIT_RATIOS: dict[SplitName, float] = {
    "train": 0.70,
    "val": 0.15,
    "test": 0.15,
}
DEFAULT_PROTEIN_IDENTITY_THRESHOLD = 0.30

LigandScaffoldResolver = Callable[["LockedSplitRecord"], str | None]
ProteinClusterResolver = Callable[[Sequence["LockedSplitRecord"], float], Mapping[str, str | None]]


@dataclass(frozen=True, slots=True)
class LockedSplitRecord:
    record_id: str
    protein_cluster_id: str | None = None
    protein_sequence: str | None = None
    ligand_id: str | None = None
    ligand_smiles: str | None = None
    ligand_scaffold_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "record_id", _clean_text(self.record_id))
        object.__setattr__(self, "protein_cluster_id", _clean_text(self.protein_cluster_id))
        object.__setattr__(self, "protein_sequence", _clean_text(self.protein_sequence))
        object.__setattr__(self, "ligand_id", _clean_text(self.ligand_id))
        object.__setattr__(self, "ligand_smiles", _clean_text(self.ligand_smiles))
        object.__setattr__(self, "ligand_scaffold_id", _clean_text(self.ligand_scaffold_id))
        if not self.record_id:
            raise ValueError("record_id is required")

    @property
    def has_protein_cluster(self) -> bool:
        return bool(self.protein_cluster_id)

    @property
    def has_ligand_scaffold(self) -> bool:
        return bool(self.ligand_scaffold_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "protein_cluster_id": self.protein_cluster_id,
            "protein_sequence": self.protein_sequence,
            "ligand_id": self.ligand_id,
            "ligand_smiles": self.ligand_smiles,
            "ligand_scaffold_id": self.ligand_scaffold_id,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any] | Any) -> LockedSplitRecord:
        if isinstance(payload, LockedSplitRecord):
            return payload
        if isinstance(payload, Mapping):
            return cls(
                record_id=str(
                    _first_present(payload, ("record_id", "id", "example_id", "sample_id")) or ""
                ),
                protein_cluster_id=str(
                    _first_present(
                        payload,
                        ("protein_cluster_id", "cluster_id", "mmseqs_cluster_id"),
                    )
                    or "",
                ),
                protein_sequence=str(
                    _first_present(payload, ("protein_sequence", "sequence", "protein_seq"))
                    or "",
                ),
                ligand_id=str(_first_present(payload, ("ligand_id", "compound_id")) or ""),
                ligand_smiles=str(_first_present(payload, ("ligand_smiles", "smiles")) or ""),
                ligand_scaffold_id=str(
                    _first_present(payload, ("ligand_scaffold_id", "murcko_scaffold", "scaffold"))
                    or "",
                ),
            )

        return cls(
            record_id=str(
                _first_present(payload, ("record_id", "id", "example_id", "sample_id")) or ""
            ),
            protein_cluster_id=str(
                _first_present(payload, ("protein_cluster_id", "cluster_id", "mmseqs_cluster_id"))
                or "",
            ),
            protein_sequence=str(
                _first_present(payload, ("protein_sequence", "sequence", "protein_seq")) or ""
            ),
            ligand_id=str(_first_present(payload, ("ligand_id", "compound_id")) or ""),
            ligand_smiles=str(_first_present(payload, ("ligand_smiles", "smiles")) or ""),
            ligand_scaffold_id=str(
                _first_present(payload, ("ligand_scaffold_id", "murcko_scaffold", "scaffold"))
                or "",
            ),
        )


@dataclass(frozen=True, slots=True)
class LockedSplitAssignment:
    record_id: str
    split: SplitName
    component_id: str
    component_size: int
    protein_cluster_id: str
    ligand_scaffold_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "split": self.split,
            "component_id": self.component_id,
            "component_size": self.component_size,
            "protein_cluster_id": self.protein_cluster_id,
            "ligand_scaffold_id": self.ligand_scaffold_id,
        }


@dataclass(frozen=True, slots=True)
class LockedSplitUnresolvedRecord:
    record_id: str
    reasons: tuple[str, ...]
    protein_cluster_id: str | None = None
    ligand_scaffold_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "reasons": list(self.reasons),
            "protein_cluster_id": self.protein_cluster_id,
            "ligand_scaffold_id": self.ligand_scaffold_id,
        }


@dataclass(frozen=True, slots=True)
class LockedSplitResult:
    assignments: tuple[LockedSplitAssignment, ...]
    unresolved: tuple[LockedSplitUnresolvedRecord, ...]
    split_counts: dict[str, int]
    target_counts: dict[str, int]
    seed: int
    protein_identity_threshold: float = DEFAULT_PROTEIN_IDENTITY_THRESHOLD
    split_ratios: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_SPLIT_RATIOS))

    def to_dict(self) -> dict[str, Any]:
        return {
            "assignments": [assignment.to_dict() for assignment in self.assignments],
            "unresolved": [record.to_dict() for record in self.unresolved],
            "split_counts": dict(self.split_counts),
            "target_counts": dict(self.target_counts),
            "seed": self.seed,
            "protein_identity_threshold": self.protein_identity_threshold,
            "split_ratios": dict(self.split_ratios),
        }


@dataclass(frozen=True, slots=True)
class _Component:
    record_indices: tuple[int, ...]
    protein_cluster_ids: tuple[str, ...]
    ligand_scaffold_ids: tuple[str, ...]

    @property
    def size(self) -> int:
        return len(self.record_indices)

    @property
    def component_id(self) -> str:
        joined = "+".join(self._labels())
        return f"locked-component:{joined}"

    def _labels(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {"record:" + str(index) for index in self.record_indices}
                | {"protein:" + cluster for cluster in self.protein_cluster_ids}
                | {"scaffold:" + scaffold for scaffold in self.ligand_scaffold_ids}
            )
        )


class _UnionFind:
    def __init__(self, size: int) -> None:
        self._parent = list(range(size))
        self._rank = [0] * size

    def find(self, index: int) -> int:
        parent = self._parent[index]
        if parent != index:
            self._parent[index] = self.find(parent)
        return self._parent[index]

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if self._rank[left_root] < self._rank[right_root]:
            self._parent[left_root] = right_root
            return
        if self._rank[left_root] > self._rank[right_root]:
            self._parent[right_root] = left_root
            return
        self._parent[right_root] = left_root
        self._rank[left_root] += 1


def assign_locked_splits(
    records: Sequence[Mapping[str, Any] | Any | LockedSplitRecord],
    *,
    seed: int = 0,
    protein_identity_threshold: float = DEFAULT_PROTEIN_IDENTITY_THRESHOLD,
    split_ratios: Mapping[SplitName, float] | None = None,
    protein_cluster_resolver: ProteinClusterResolver | None = None,
    ligand_scaffold_resolver: LigandScaffoldResolver | None = None,
) -> LockedSplitResult:
    split_ratios_map = dict(split_ratios or DEFAULT_SPLIT_RATIOS)
    normalized_records = tuple(_coerce_record(record) for record in records)

    protein_cluster_overrides = (
        dict(protein_cluster_resolver(normalized_records, protein_identity_threshold))
        if protein_cluster_resolver is not None
        else {}
    )

    resolved_records: list[tuple[int, LockedSplitRecord, str, str]] = []
    unresolved_records: list[LockedSplitUnresolvedRecord] = []

    for index, record in enumerate(normalized_records):
        protein_cluster_id = _clean_text(
            record.protein_cluster_id or protein_cluster_overrides.get(record.record_id)
        )

        ligand_scaffold_id = record.ligand_scaffold_id
        if not ligand_scaffold_id and ligand_scaffold_resolver is not None:
            ligand_scaffold_id = _clean_text(ligand_scaffold_resolver(record))

        if not ligand_scaffold_id and record.ligand_smiles:
            ligand_scaffold_id = _clean_text(_murcko_scaffold_from_smiles(record.ligand_smiles))

        reasons: list[str] = []
        if not protein_cluster_id:
            reasons.append("missing_protein_cluster")
        if not ligand_scaffold_id:
            reasons.append("missing_ligand_scaffold")

        if reasons:
            unresolved_records.append(
                LockedSplitUnresolvedRecord(
                    record_id=record.record_id,
                    reasons=tuple(reasons),
                    protein_cluster_id=protein_cluster_id,
                    ligand_scaffold_id=ligand_scaffold_id,
                )
            )
            continue

        resolved_records.append((index, record, protein_cluster_id, ligand_scaffold_id))

    if not resolved_records:
        return LockedSplitResult(
            assignments=(),
            unresolved=tuple(unresolved_records),
            split_counts={"train": 0, "val": 0, "test": 0},
            target_counts=_compute_split_targets(0, split_ratios_map),
            seed=seed,
            protein_identity_threshold=protein_identity_threshold,
            split_ratios=split_ratios_map,
        )

    components = _build_components(resolved_records)
    targets = _compute_split_targets(len(resolved_records), split_ratios_map)
    assignments_by_split: dict[SplitName, list[LockedSplitAssignment]] = {
        "train": [],
        "val": [],
        "test": [],
    }
    counts: dict[SplitName, int] = {"train": 0, "val": 0, "test": 0}

    ordered_components = list(components)
    Random(seed).shuffle(ordered_components)
    ordered_components.sort(key=lambda component: component.size, reverse=True)

    resolved_lookup = {
        record_index: record
        for record_index, record, _protein_cluster_id, _ligand_scaffold_id in resolved_records
    }

    for component in ordered_components:
        split = _choose_split(component.size, counts, targets)
        counts[split] += component.size
        for record_index in component.record_indices:
            record = resolved_lookup[record_index]
            assignments_by_split[split].append(
                LockedSplitAssignment(
                    record_id=record.record_id,
                    split=split,
                    component_id=component.component_id,
                    component_size=component.size,
                    protein_cluster_id=component.protein_cluster_ids[0],
                    ligand_scaffold_id=component.ligand_scaffold_ids[0],
                )
            )

    assignments = tuple(
        assignment
        for split in DEFAULT_SPLIT_ORDER
        for assignment in sorted(assignments_by_split[split], key=lambda item: item.record_id)
    )

    split_counts = {split: counts[split] for split in DEFAULT_SPLIT_ORDER}
    return LockedSplitResult(
        assignments=assignments,
        unresolved=tuple(sorted(unresolved_records, key=lambda item: item.record_id)),
        split_counts=split_counts,
        target_counts=targets,
        seed=seed,
        protein_identity_threshold=protein_identity_threshold,
        split_ratios=split_ratios_map,
    )


def _choose_split(
    component_size: int,
    counts: Mapping[SplitName, int],
    targets: Mapping[SplitName, int],
) -> SplitName:
    best_split = DEFAULT_SPLIT_ORDER[0]
    best_score: tuple[int, int] | None = None
    for split in DEFAULT_SPLIT_ORDER:
        projected = counts[split] + component_size
        target = targets[split]
        remaining = target - projected
        score = (-remaining, DEFAULT_SPLIT_ORDER.index(split))
        if best_score is None or score < best_score:
            best_score = score
            best_split = split
    return best_split


def _build_components(
    resolved_records: Sequence[tuple[int, LockedSplitRecord, str, str]],
) -> tuple[_Component, ...]:
    if not resolved_records:
        return ()

    uf = _UnionFind(len(resolved_records))
    protein_groups: dict[str, list[int]] = defaultdict(list)
    scaffold_groups: dict[str, list[int]] = defaultdict(list)

    for resolved_index, (
        _original_index,
        _record,
        protein_cluster_id,
        ligand_scaffold_id,
    ) in enumerate(resolved_records):
        protein_groups[protein_cluster_id].append(resolved_index)
        scaffold_groups[ligand_scaffold_id].append(resolved_index)

    for indices in protein_groups.values():
        for left, right in zip(indices, indices[1:], strict=False):
            uf.union(left, right)

    for indices in scaffold_groups.values():
        for left, right in zip(indices, indices[1:], strict=False):
            uf.union(left, right)

    component_members: dict[int, list[int]] = defaultdict(list)
    for resolved_index in range(len(resolved_records)):
        component_members[uf.find(resolved_index)].append(resolved_index)

    components: list[_Component] = []
    for indices in component_members.values():
        record_indices = tuple(
            sorted(resolved_records[resolved_index][0] for resolved_index in indices)
        )
        protein_cluster_ids = tuple(
            sorted({resolved_records[resolved_index][2] for resolved_index in indices})
        )
        ligand_scaffold_ids = tuple(
            sorted({resolved_records[resolved_index][3] for resolved_index in indices})
        )
        components.append(
            _Component(
                record_indices=record_indices,
                protein_cluster_ids=protein_cluster_ids,
                ligand_scaffold_ids=ligand_scaffold_ids,
            )
        )

    return tuple(components)


def _compute_split_targets(
    total_records: int,
    split_ratios: Mapping[SplitName, float],
) -> dict[str, int]:
    raw_targets = {
        split: total_records * split_ratios.get(split, 0.0)
        for split in DEFAULT_SPLIT_ORDER
    }
    base_targets = {split: int(value) for split, value in raw_targets.items()}
    remainder = total_records - sum(base_targets.values())
    fractional_parts = sorted(
        (
            (raw_targets[split] - base_targets[split], -DEFAULT_SPLIT_ORDER.index(split), split)
            for split in DEFAULT_SPLIT_ORDER
        ),
        reverse=True,
    )
    targets = dict(base_targets)
    for _fraction, _order, split in fractional_parts[:remainder]:
        targets[split] += 1
    return targets


def _murcko_scaffold_from_smiles(smiles: str | None) -> str | None:
    text = _clean_text(smiles)
    if not text:
        return None
    try:
        from rdkit import Chem  # type: ignore
        from rdkit.Chem.Scaffolds import MurckoScaffold  # type: ignore
    except Exception:
        return None

    molecule = Chem.MolFromSmiles(text)
    if molecule is None:
        return None
    scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol=molecule)
    return _clean_text(scaffold)


def _coerce_record(payload: Mapping[str, Any] | Any | LockedSplitRecord) -> LockedSplitRecord:
    if isinstance(payload, LockedSplitRecord):
        return payload
    return LockedSplitRecord.from_payload(payload)


def _first_present(payload: Mapping[str, Any] | Any, keys: Sequence[str]) -> Any:
    if isinstance(payload, Mapping):
        for key in keys:
            if key in payload and payload[key] not in (None, ""):
                return payload[key]
        return None
    for key in keys:
        if hasattr(payload, key):
            value = getattr(payload, key)
            if value not in (None, ""):
                return value
    return None


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


__all__ = [
    "DEFAULT_PROTEIN_IDENTITY_THRESHOLD",
    "DEFAULT_SPLIT_ORDER",
    "DEFAULT_SPLIT_RATIOS",
    "LockedSplitAssignment",
    "LockedSplitRecord",
    "LockedSplitResult",
    "LockedSplitUnresolvedRecord",
    "assign_locked_splits",
]

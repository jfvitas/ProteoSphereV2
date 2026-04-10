from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from importlib import import_module
from math import sqrt
from typing import Any


class InterfaceContactError(ValueError):
    """Raised when interface contact extraction cannot be completed."""


@dataclass(frozen=True, slots=True)
class InterfaceContact:
    left_atom_id: str
    right_atom_id: str
    left_chain_id: str
    right_chain_id: str
    left_residue_key: str
    right_residue_key: str
    left_residue_name: str
    right_residue_name: str
    left_residue_number: int | None
    right_residue_number: int | None
    distance: float
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "left_atom_id": self.left_atom_id,
            "right_atom_id": self.right_atom_id,
            "left_chain_id": self.left_chain_id,
            "right_chain_id": self.right_chain_id,
            "left_residue_key": self.left_residue_key,
            "right_residue_key": self.right_residue_key,
            "left_residue_name": self.left_residue_name,
            "right_residue_name": self.right_residue_name,
            "left_residue_number": self.left_residue_number,
            "right_residue_number": self.right_residue_number,
            "distance": self.distance,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class InterfaceContactSummary:
    pdb_id: str
    cutoff: float
    backend: str
    atom_contacts: tuple[InterfaceContact, ...]
    atom_count: int
    chain_pair_counts: dict[str, int]
    residue_pair_counts: dict[str, int]
    contacting_chains: tuple[str, ...]
    contacting_residues_by_chain: dict[str, tuple[str, ...]]
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def contact_count(self) -> int:
        return len(self.atom_contacts)

    def to_dict(self) -> dict[str, object]:
        return {
            "pdb_id": self.pdb_id,
            "cutoff": self.cutoff,
            "backend": self.backend,
            "atom_contacts": [contact.to_dict() for contact in self.atom_contacts],
            "atom_count": self.atom_count,
            "contact_count": self.contact_count,
            "chain_pair_counts": dict(self.chain_pair_counts),
            "residue_pair_counts": dict(self.residue_pair_counts),
            "contacting_chains": list(self.contacting_chains),
            "contacting_residues_by_chain": {
                chain_id: list(residue_keys)
                for chain_id, residue_keys in self.contacting_residues_by_chain.items()
            },
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class _SciPyKDTreeModules:
    cKDTree: Any


@dataclass(frozen=True, slots=True)
class _MDAnalysisModules:
    distances: Any


_SCIPY_CACHE: _SciPyKDTreeModules | None = None
_SCIPY_IMPORT_FAILED = False
_MDANALYSIS_CACHE: _MDAnalysisModules | None = None
_MDANALYSIS_IMPORT_FAILED = False


def _row_value(row: Any, *names: str) -> Any:
    if isinstance(row, Mapping):
        for name in names:
            if name in row:
                return row[name]
        return None
    for name in names:
        if hasattr(row, name):
            return getattr(row, name)
    return None


def _as_text(value: Any, *, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise InterfaceContactError(f"{field_name} must be a non-empty string")
    return text


def _optional_text(value: Any) -> str:
    return str(value or "").strip()


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_coords(row: Any) -> tuple[float, float, float] | None:
    raw_coords = _row_value(row, "coordinates", "coord")
    if raw_coords is not None:
        try:
            x, y, z = raw_coords
            coords = (float(x), float(y), float(z))
            return coords
        except (TypeError, ValueError):
            pass

    x = _optional_float(_row_value(row, "x", "cartn_x"))
    y = _optional_float(_row_value(row, "y", "cartn_y"))
    z = _optional_float(_row_value(row, "z", "cartn_z"))
    if None in {x, y, z}:
        return None
    return (x, y, z)  # type: ignore[return-value]


def _normalize_pdb_id(pdb_id: str) -> str:
    return _as_text(pdb_id, field_name="pdb_id").upper()


def _build_residue_key(chain_id: str, residue_number: int | None, residue_name: str) -> str:
    suffix = str(residue_number) if residue_number is not None else residue_name or "unknown"
    return f"{chain_id}:{suffix}"


def _pair_key(left_chain_id: str, right_chain_id: str) -> str:
    ordered = tuple(sorted((left_chain_id, right_chain_id)))
    return f"{ordered[0]}|{ordered[1]}"


def _residue_pair_key(
    left_chain_id: str,
    left_residue_key: str,
    right_chain_id: str,
    right_residue_key: str,
) -> str:
    if left_chain_id <= right_chain_id:
        return f"{left_residue_key}|{right_residue_key}"
    return f"{right_residue_key}|{left_residue_key}"


def _normalize_chain_pairs(
    chain_pairs: Iterable[tuple[str, str]] | None,
) -> set[tuple[str, str]] | None:
    if chain_pairs is None:
        return None
    normalized: set[tuple[str, str]] = set()
    for left_chain_id, right_chain_id in chain_pairs:
        left = _as_text(left_chain_id, field_name="chain_id")
        right = _as_text(right_chain_id, field_name="chain_id")
        normalized.add(tuple(sorted((left, right))))
    return normalized


def _pair_allowed(
    left_chain_id: str,
    right_chain_id: str,
    allowed_pairs: set[tuple[str, str]] | None,
) -> bool:
    if left_chain_id == right_chain_id:
        return False
    if allowed_pairs is None:
        return True
    return tuple(sorted((left_chain_id, right_chain_id))) in allowed_pairs


def _distance(left: Sequence[float], right: Sequence[float]) -> float:
    dx = left[0] - right[0]
    dy = left[1] - right[1]
    dz = left[2] - right[2]
    return sqrt(dx * dx + dy * dy + dz * dz)


def _load_scipy_kdtree_modules() -> _SciPyKDTreeModules | None:
    global _SCIPY_CACHE, _SCIPY_IMPORT_FAILED
    if _SCIPY_CACHE is not None:
        return _SCIPY_CACHE
    if _SCIPY_IMPORT_FAILED:
        return None
    try:
        spatial = import_module("scipy.spatial")
    except ModuleNotFoundError:
        _SCIPY_IMPORT_FAILED = True
        return None
    _SCIPY_CACHE = _SciPyKDTreeModules(cKDTree=spatial.cKDTree)
    return _SCIPY_CACHE


def _load_mdanalysis_modules() -> _MDAnalysisModules | None:
    global _MDANALYSIS_CACHE, _MDANALYSIS_IMPORT_FAILED
    if _MDANALYSIS_CACHE is not None:
        return _MDANALYSIS_CACHE
    if _MDANALYSIS_IMPORT_FAILED:
        return None
    try:
        distances = import_module("MDAnalysis.lib.distances")
    except ModuleNotFoundError:
        _MDANALYSIS_IMPORT_FAILED = True
        return None
    _MDANALYSIS_CACHE = _MDAnalysisModules(distances=distances)
    return _MDANALYSIS_CACHE


def scipy_kdtree_available() -> bool:
    return _load_scipy_kdtree_modules() is not None


def mdanalysis_kdtree_available() -> bool:
    return _load_mdanalysis_modules() is not None


def interface_contact_backends(*, include_python_fallback: bool = False) -> tuple[str, ...]:
    backends = []
    if scipy_kdtree_available():
        backends.append("scipy-kdtree")
    if mdanalysis_kdtree_available():
        backends.append("mdanalysis-kdtree")
    if include_python_fallback:
        backends.append("python-fallback")
    return tuple(backends)


@dataclass(frozen=True, slots=True)
class _AtomRecord:
    atom_id: str
    chain_id: str
    residue_key: str
    residue_name: str
    residue_number: int | None
    coordinates: tuple[float, float, float]


def _parse_atom_records(
    atom_rows: Iterable[Mapping[str, Any] | Any],
) -> list[_AtomRecord]:
    records: list[_AtomRecord] = []
    for row in atom_rows:
        atom_id = _as_text(_row_value(row, "atom_id", "id", "auth_atom_id"), field_name="atom_id")
        chain_id = _as_text(
            _row_value(row, "chain_id", "auth_asym_id"), field_name="chain_id"
        )
        residue_name = _optional_text(
            _row_value(row, "residue_name", "auth_comp_id", "label_comp_id")
        )
        residue_number = _optional_int(
            _row_value(row, "residue_number", "auth_seq_id", "label_seq_id")
        )
        residue_key = _optional_text(_row_value(row, "residue_key")) or _build_residue_key(
            chain_id, residue_number, residue_name
        )
        coordinates = _optional_coords(row)
        if coordinates is None:
            continue
        records.append(
            _AtomRecord(
                atom_id=atom_id,
                chain_id=chain_id,
                residue_key=residue_key,
                residue_name=residue_name,
                residue_number=residue_number,
                coordinates=coordinates,
            )
        )
    return records


def _pairs_via_python(records: Sequence[_AtomRecord], cutoff: float) -> set[tuple[int, int]]:
    pairs: set[tuple[int, int]] = set()
    for left_index, left in enumerate(records):
        for right_index in range(left_index + 1, len(records)):
            right = records[right_index]
            if _distance(left.coordinates, right.coordinates) <= cutoff:
                pairs.add((left_index, right_index))
    return pairs


def _pairs_via_scipy(records: Sequence[_AtomRecord], cutoff: float) -> set[tuple[int, int]]:
    modules = _load_scipy_kdtree_modules()
    if modules is None:
        return _pairs_via_python(records, cutoff)
    tree = modules.cKDTree([record.coordinates for record in records])
    raw_pairs = tree.query_pairs(cutoff)
    return {
        (int(left_index), int(right_index))
        for left_index, right_index in raw_pairs
    }


def _pairs_via_mdanalysis(records: Sequence[_AtomRecord], cutoff: float) -> set[tuple[int, int]]:
    modules = _load_mdanalysis_modules()
    if modules is None:
        return _pairs_via_python(records, cutoff)
    numpy = import_module("numpy")
    coords = numpy.asarray([record.coordinates for record in records], dtype=float)
    pairs, _distances = modules.distances.capped_distance(
        coords,
        coords,
        max_cutoff=cutoff,
        method="pkdtree",
        return_distances=True,
    )
    return {
        (int(left_index), int(right_index))
        for left_index, right_index in pairs
        if int(left_index) < int(right_index)
    }


def _resolve_backend(preferred_backend: str) -> str:
    backend = _optional_text(preferred_backend).lower() or "auto"
    if backend == "auto":
        if scipy_kdtree_available():
            return "scipy-kdtree"
        if mdanalysis_kdtree_available():
            return "mdanalysis-kdtree"
        raise InterfaceContactError(
            "No registered interface-contact backend is available; set backend='python-fallback' "
            "to use the explicit Python fallback in tests or development."
        )
    if backend in {"scipy", "scipy-kdtree"}:
        if scipy_kdtree_available():
            return "scipy-kdtree"
        raise InterfaceContactError(
            "SciPy backend requested but scipy.spatial.cKDTree is unavailable; "
            "set backend='python-fallback' for the explicit Python fallback."
        )
    if backend in {"mdanalysis", "mdanalysis-kdtree"}:
        if mdanalysis_kdtree_available():
            return "mdanalysis-kdtree"
        raise InterfaceContactError(
            "MDAnalysis backend requested but MDAnalysis.lib.distances is unavailable; "
            "set backend='python-fallback' for the explicit Python fallback."
        )
    if backend in {"python", "python-fallback", "fallback"}:
        return "python-fallback"
    raise InterfaceContactError(
        "backend must be one of auto, scipy, mdanalysis, or python-fallback"
    )


def _candidate_pairs(
    records: Sequence[_AtomRecord],
    cutoff: float,
    backend: str,
) -> set[tuple[int, int]]:
    if backend == "scipy-kdtree":
        return _pairs_via_scipy(records, cutoff)
    if backend == "mdanalysis-kdtree":
        return _pairs_via_mdanalysis(records, cutoff)
    return _pairs_via_python(records, cutoff)


def extract_interface_contacts(
    atom_rows: Iterable[Mapping[str, Any] | Any],
    *,
    pdb_id: str,
    cutoff: float = 5.0,
    chain_pairs: Iterable[tuple[str, str]] | None = None,
    backend: str = "auto",
) -> InterfaceContactSummary:
    if cutoff <= 0:
        raise InterfaceContactError("cutoff must be greater than zero")

    normalized_pdb_id = _normalize_pdb_id(pdb_id)
    requested_backend = _optional_text(backend).lower() or "auto"
    records = _parse_atom_records(atom_rows)
    if not records:
        raise InterfaceContactError("No atom rows with coordinates were provided")

    allowed_pairs = _normalize_chain_pairs(chain_pairs)
    chosen_backend = _resolve_backend(backend)
    candidate_pairs = _candidate_pairs(records, cutoff, chosen_backend)

    contacts: list[InterfaceContact] = []
    chain_pair_counts: dict[str, int] = defaultdict(int)
    residue_pair_counts: dict[str, int] = defaultdict(int)
    contacting_residues_by_chain: dict[str, set[str]] = defaultdict(set)

    for left_index, right_index in sorted(candidate_pairs):
        left = records[left_index]
        right = records[right_index]
        if not _pair_allowed(left.chain_id, right.chain_id, allowed_pairs):
            continue
        distance = _distance(left.coordinates, right.coordinates)
        contact = InterfaceContact(
            left_atom_id=left.atom_id,
            right_atom_id=right.atom_id,
            left_chain_id=left.chain_id,
            right_chain_id=right.chain_id,
            left_residue_key=left.residue_key,
            right_residue_key=right.residue_key,
            left_residue_name=left.residue_name,
            right_residue_name=right.residue_name,
            left_residue_number=left.residue_number,
            right_residue_number=right.residue_number,
            distance=distance,
            provenance={
                "pdb_id": normalized_pdb_id,
                "requested_backend": requested_backend,
                "resolved_backend": chosen_backend,
                "backend": chosen_backend,
                "cutoff": cutoff,
            },
        )
        contacts.append(contact)
        chain_pair_counts[_pair_key(left.chain_id, right.chain_id)] += 1
        residue_pair_counts[
            _residue_pair_key(left.chain_id, left.residue_key, right.chain_id, right.residue_key)
        ] += 1
        contacting_residues_by_chain[left.chain_id].add(left.residue_key)
        contacting_residues_by_chain[right.chain_id].add(right.residue_key)

    contacts.sort(
        key=lambda contact: (
            contact.left_chain_id,
            contact.right_chain_id,
            contact.left_residue_key,
            contact.right_residue_key,
            contact.left_atom_id,
            contact.right_atom_id,
        )
    )

    return InterfaceContactSummary(
        pdb_id=normalized_pdb_id,
        cutoff=cutoff,
        backend=chosen_backend,
        atom_contacts=tuple(contacts),
        atom_count=len(records),
        chain_pair_counts=dict(sorted(chain_pair_counts.items())),
        residue_pair_counts=dict(sorted(residue_pair_counts.items())),
        contacting_chains=tuple(sorted(contacting_residues_by_chain)),
        contacting_residues_by_chain={
            chain_id: tuple(sorted(residue_keys))
            for chain_id, residue_keys in sorted(contacting_residues_by_chain.items())
        },
        provenance={
            "input_atom_rows": len(records),
            "candidate_pairs": len(candidate_pairs),
            "requested_backend": requested_backend,
            "resolved_backend": chosen_backend,
            "backend_candidates": interface_contact_backends(
                include_python_fallback=chosen_backend == "python-fallback"
            ),
        },
    )

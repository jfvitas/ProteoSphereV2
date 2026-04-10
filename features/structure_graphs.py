from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from math import sqrt
from typing import Any

from connectors.rcsb.parsers import RCSBEntityRecord, RCSBStructureBundle


class StructureGraphError(ValueError):
    """Raised when structure graph extraction cannot be completed."""


def _text(value: Any, *, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise StructureGraphError(f"{field_name} must be a non-empty string")
    return text


def _optional_text(value: Any) -> str:
    return str(value or "").strip()


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except TypeError, ValueError:
        return None


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except TypeError, ValueError:
        return None


def _coalesce(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _text_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)):
        text = str(value).strip()
        return (text,) if text else ()
    if isinstance(value, Iterable) and not isinstance(value, dict):
        seen: dict[str, None] = {}
        for item in value:
            text = str(item or "").strip()
            if text:
                seen[text] = None
        return tuple(seen)
    text = str(value).strip()
    return (text,) if text else ()


def _normalize_chain_id(value: Any, *, field_name: str = "chain_id") -> str:
    chain_id = str(value or "").strip()
    if not chain_id:
        raise StructureGraphError(f"{field_name} must be a non-empty string")
    return chain_id


def _coords_from_row(row: Mapping[str, Any]) -> tuple[float, float, float] | None:
    x = _optional_float(_coalesce(row.get("x"), row.get("cartn_x")))
    y = _optional_float(_coalesce(row.get("y"), row.get("cartn_y")))
    z = _optional_float(_coalesce(row.get("z"), row.get("cartn_z")))
    if None in (x, y, z):
        return None
    return (x, y, z)


def _residue_key(
    chain_id: str,
    residue_number: int | None,
    residue_name: str,
    insertion_code: str = "",
) -> str:
    suffix = ""
    if residue_number is not None:
        suffix = str(residue_number)
        if insertion_code:
            suffix = f"{suffix}{insertion_code}"
    elif residue_name:
        suffix = residue_name
    else:
        suffix = "unknown"
    return f"{chain_id}:{suffix}"


def _iter_sequence_residues(entity: RCSBEntityRecord) -> Iterable[tuple[int, str]]:
    for index, residue in enumerate(entity.sequence, start=1):
        residue = residue.strip()
        if residue:
            yield index, residue


def _coerce_row_list(rows: Iterable[Mapping[str, Any]] | None) -> list[Mapping[str, Any]]:
    if rows is None:
        return []
    return list(rows)


def _bond_partners(row: Mapping[str, Any]) -> tuple[str, ...]:
    raw = (
        row.get("bond_partners")
        or row.get("bonded_atom_ids")
        or row.get("bonded_atoms")
        or row.get("bonded_atom_serials")
    )
    if raw is None:
        return ()
    if isinstance(raw, (str, bytes)):
        return tuple(token.strip() for token in re.split(r"[;,|]", str(raw)) if token.strip())
    if isinstance(raw, Iterable) and not isinstance(raw, dict):
        return _text_tuple(raw)
    return _text_tuple(raw)


def _mean_coordinates(coords: list[tuple[float, float, float]]) -> tuple[float, float, float]:
    if not coords:
        raise StructureGraphError("cannot compute a centroid without coordinates")
    count = float(len(coords))
    return (
        sum(point[0] for point in coords) / count,
        sum(point[1] for point in coords) / count,
        sum(point[2] for point in coords) / count,
    )


def _distance(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    dx = left[0] - right[0]
    dy = left[1] - right[1]
    dz = left[2] - right[2]
    return sqrt(dx * dx + dy * dy + dz * dz)


@dataclass(frozen=True, slots=True)
class AtomNode:
    atom_id: str
    pdb_id: str
    chain_id: str
    residue_key: str
    residue_name: str
    residue_number: int | None
    atom_name: str
    element: str
    coordinates: tuple[float, float, float] | None
    occupancy: float | None = None
    b_factor: float | None = None
    uniprot_ids: tuple[str, ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ResidueNode:
    residue_key: str
    pdb_id: str
    chain_id: str
    residue_name: str
    residue_number: int | None
    sequence_position: int | None
    one_letter_code: str | None
    uniprot_ids: tuple[str, ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GraphEdge:
    source: str
    target: str
    kind: str
    weight: float | None = None
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AtomGraph:
    pdb_id: str
    nodes: tuple[AtomNode, ...]
    edges: tuple[GraphEdge, ...]
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def node_ids(self) -> tuple[str, ...]:
        return tuple(node.atom_id for node in self.nodes)


@dataclass(frozen=True, slots=True)
class ResidueGraph:
    pdb_id: str
    nodes: tuple[ResidueNode, ...]
    edges: tuple[GraphEdge, ...]
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def node_ids(self) -> tuple[str, ...]:
        return tuple(node.residue_key for node in self.nodes)


def _bundle_provenance(bundle: RCSBStructureBundle) -> dict[str, Any]:
    return {
        "entry_title": bundle.entry.title,
        "experimental_methods": list(bundle.entry.experimental_methods),
        "assembly_ids": list(bundle.entry.assembly_ids),
        "polymer_entity_ids": list(bundle.entry.polymer_entity_ids),
        "chain_to_entity_ids": {
            chain_id: list(entity_ids)
            for chain_id, entity_ids in bundle.chain_to_entity_ids.items()
        },
    }


def _chain_uniprot_ids(bundle: RCSBStructureBundle, chain_id: str) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for entity in bundle.entities:
        if chain_id not in entity.chain_ids:
            continue
        for uniprot_id in entity.uniprot_ids:
            seen[uniprot_id] = None
    return tuple(seen)


def _atom_residue_key(row: Mapping[str, Any]) -> tuple[str, str, int | None, str, str]:
    chain_id = _normalize_chain_id(
        _coalesce(row.get("chain_id"), row.get("auth_asym_id"), row.get("label_asym_id"))
    )
    residue_name = _optional_text(
        _coalesce(row.get("residue_name"), row.get("auth_comp_id"), row.get("label_comp_id"))
    )
    residue_number = _optional_int(
        _coalesce(row.get("residue_number"), row.get("auth_seq_id"), row.get("label_seq_id"))
    )
    insertion_code = _optional_text(
        _coalesce(row.get("insertion_code"), row.get("pdbx_PDB_ins_code"))
    )
    residue_key = _optional_text(row.get("residue_key")) or _residue_key(
        chain_id,
        residue_number,
        residue_name,
        insertion_code,
    )
    return chain_id, residue_key, residue_number, residue_name, insertion_code


def _row_to_atom_node(
    bundle: RCSBStructureBundle,
    row: Mapping[str, Any],
    *,
    row_index: int,
) -> AtomNode:
    atom_id = _text(
        _coalesce(
            row.get("atom_id"),
            row.get("id"),
            row.get("auth_atom_id"),
            row.get("label_atom_id"),
        ),
        field_name="atom_id",
    )
    chain_id, residue_key, residue_number, residue_name, _ = _atom_residue_key(row)
    atom_name = (
        _optional_text(
            _coalesce(row.get("atom_name"), row.get("auth_atom_name"), row.get("label_atom_id"))
        )
        or atom_id
    )
    element = _optional_text(_coalesce(row.get("element"), row.get("type_symbol")))
    return AtomNode(
        atom_id=atom_id,
        pdb_id=bundle.pdb_id,
        chain_id=chain_id,
        residue_key=residue_key,
        residue_name=residue_name,
        residue_number=residue_number,
        atom_name=atom_name,
        element=element,
        coordinates=_coords_from_row(row),
        occupancy=_optional_float(row.get("occupancy")),
        b_factor=_optional_float(row.get("b_factor") or row.get("b_iso_or_equiv")),
        uniprot_ids=_chain_uniprot_ids(bundle, chain_id),
        provenance={
            "entry": bundle.pdb_id,
            "row_index": row_index,
            "chain_id": chain_id,
            "entity_ids": list(bundle.chain_to_entity_ids.get(chain_id, ())),
        },
    )


def _row_to_residue_node(
    bundle: RCSBStructureBundle,
    row: Mapping[str, Any],
    *,
    row_index: int,
    source_kind: str,
) -> ResidueNode:
    chain_id, residue_key, residue_number, residue_name, insertion_code = _atom_residue_key(row)
    sequence_position = _optional_int(_coalesce(row.get("sequence_position"), row.get("seq_id")))
    one_letter_code = (
        _optional_text(_coalesce(row.get("one_letter_code"), row.get("residue_code"))) or None
    )
    return ResidueNode(
        residue_key=residue_key,
        pdb_id=bundle.pdb_id,
        chain_id=chain_id,
        residue_name=residue_name,
        residue_number=residue_number,
        sequence_position=sequence_position if sequence_position is not None else residue_number,
        one_letter_code=one_letter_code,
        uniprot_ids=_text_tuple(
            _coalesce(
                row.get("uniprot_ids"),
                row.get("uniprot_id"),
                row.get("uniprot_accession"),
            )
        ),
        provenance={
            "entry": bundle.pdb_id,
            "row_index": row_index,
            "source_kind": source_kind,
            "chain_id": chain_id,
            "insertion_code": insertion_code,
        },
    )


def extract_atom_graph(
    bundle: RCSBStructureBundle,
    atom_rows: Iterable[Mapping[str, Any]],
    *,
    contact_cutoff: float = 4.5,
) -> AtomGraph:
    rows = _coerce_row_list(atom_rows)
    atom_nodes: list[AtomNode] = []
    atom_by_id: dict[str, AtomNode] = {}
    edges: list[GraphEdge] = []
    seen_bonds: set[tuple[str, str]] = set()

    for row_index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise StructureGraphError("atom_rows must contain mapping rows")
        node = _row_to_atom_node(bundle, row, row_index=row_index)
        atom_nodes.append(node)
        atom_by_id[node.atom_id] = node
        edges.append(
            GraphEdge(
                source=node.atom_id,
                target=node.residue_key,
                kind="atom_to_residue",
                provenance={
                    "entry": bundle.pdb_id,
                    "chain_id": node.chain_id,
                    "entity_ids": list(bundle.chain_to_entity_ids.get(node.chain_id, ())),
                },
            )
        )

    for row_index, row in enumerate(rows):
        atom_id = _optional_text(
            _coalesce(
                row.get("atom_id"),
                row.get("id"),
                row.get("auth_atom_id"),
                row.get("label_atom_id"),
            )
        )
        if not atom_id or atom_id not in atom_by_id:
            continue
        for partner_id in _bond_partners(row):
            if partner_id not in atom_by_id:
                continue
            pair = tuple(sorted((atom_id, partner_id)))
            if pair in seen_bonds:
                continue
            seen_bonds.add(pair)
            edges.append(
                GraphEdge(
                    source=pair[0],
                    target=pair[1],
                    kind="bond",
                    provenance={
                        "entry": bundle.pdb_id,
                        "row_index": row_index,
                    },
                )
            )

    seen_contacts: set[tuple[str, str]] = set()
    for index, left in enumerate(atom_nodes):
        if left.coordinates is None:
            continue
        for right in atom_nodes[index + 1 :]:
            if right.coordinates is None:
                continue
            if left.residue_key == right.residue_key:
                continue
            pair = tuple(sorted((left.atom_id, right.atom_id)))
            if pair in seen_contacts:
                continue
            distance = _distance(left.coordinates, right.coordinates)
            if distance > contact_cutoff:
                continue
            seen_contacts.add(pair)
            edges.append(
                GraphEdge(
                    source=pair[0],
                    target=pair[1],
                    kind="spatial_contact",
                    weight=distance,
                    provenance={
                        "entry": bundle.pdb_id,
                        "cutoff": contact_cutoff,
                        "chain_ids": [left.chain_id, right.chain_id],
                    },
                )
            )

    return AtomGraph(
        pdb_id=bundle.pdb_id,
        nodes=tuple(atom_nodes),
        edges=tuple(edges),
        provenance=_bundle_provenance(bundle),
    )


def extract_residue_graph(
    bundle: RCSBStructureBundle,
    atom_rows: Iterable[Mapping[str, Any]] | None = None,
    residue_rows: Iterable[Mapping[str, Any]] | None = None,
    *,
    contact_cutoff: float = 8.0,
) -> ResidueGraph:
    atom_rows_list = _coerce_row_list(atom_rows)
    residue_rows_list = _coerce_row_list(residue_rows)

    residue_nodes: list[ResidueNode] = []
    residue_by_key: dict[str, ResidueNode] = {}
    edges: list[GraphEdge] = []

    for row_index, row in enumerate(residue_rows_list):
        if not isinstance(row, Mapping):
            raise StructureGraphError("residue_rows must contain mapping rows")
        node = _row_to_residue_node(bundle, row, row_index=row_index, source_kind="explicit")
        residue_nodes.append(node)
        residue_by_key[node.residue_key] = node

    for row_index, row in enumerate(atom_rows_list):
        if not isinstance(row, Mapping):
            raise StructureGraphError("atom_rows must contain mapping rows")
        chain_id, residue_key, residue_number, residue_name, insertion_code = _atom_residue_key(row)
        if residue_key in residue_by_key:
            continue
        node = ResidueNode(
            residue_key=residue_key,
            pdb_id=bundle.pdb_id,
            chain_id=chain_id,
            residue_name=residue_name,
            residue_number=residue_number,
            sequence_position=residue_number,
            one_letter_code=None,
            uniprot_ids=_chain_uniprot_ids(bundle, chain_id),
            provenance={
                "entry": bundle.pdb_id,
                "row_index": row_index,
                "source_kind": "atom_derived",
                "chain_id": chain_id,
                "insertion_code": insertion_code,
            },
        )
        residue_nodes.append(node)
        residue_by_key[residue_key] = node

    for entity in bundle.entities:
        if not entity.sequence:
            continue
        for chain_id in entity.chain_ids:
            normalized_chain = _normalize_chain_id(chain_id)
            for position, code in _iter_sequence_residues(entity):
                residue_key = _residue_key(normalized_chain, position, code)
                if residue_key in residue_by_key:
                    continue
                node = ResidueNode(
                    residue_key=residue_key,
                    pdb_id=bundle.pdb_id,
                    chain_id=normalized_chain,
                    residue_name=code,
                    residue_number=position,
                    sequence_position=position,
                    one_letter_code=code,
                    uniprot_ids=entity.uniprot_ids,
                    provenance={
                        "entry": bundle.pdb_id,
                        "entity_id": entity.entity_id,
                        "source_kind": "entity_sequence",
                    },
                )
                residue_nodes.append(node)
                residue_by_key[residue_key] = node

    residues_by_chain: dict[str, list[ResidueNode]] = defaultdict(list)
    for node in residue_nodes:
        residues_by_chain[node.chain_id].append(node)

    for chain_id, nodes in residues_by_chain.items():
        nodes.sort(
            key=lambda node: (
                node.sequence_position is None,
                node.sequence_position
                if node.sequence_position is not None
                else (node.residue_number or 0),
                node.residue_key,
            )
        )
        for left, right in zip(nodes, nodes[1:], strict=False):
            edges.append(
                GraphEdge(
                    source=left.residue_key,
                    target=right.residue_key,
                    kind="sequence_adjacent",
                    provenance={
                        "entry": bundle.pdb_id,
                        "chain_id": chain_id,
                    },
                )
            )

    residue_centroids: dict[str, list[tuple[float, float, float]]] = defaultdict(list)
    for row in atom_rows_list:
        if not isinstance(row, Mapping):
            raise StructureGraphError("atom_rows must contain mapping rows")
        chain_id, residue_key, residue_number, residue_name, insertion_code = _atom_residue_key(row)
        coords = _coords_from_row(row)
        if coords is None:
            continue
        residue_centroids[residue_key].append(coords)
        if residue_key not in residue_by_key:
            node = ResidueNode(
                residue_key=residue_key,
                pdb_id=bundle.pdb_id,
                chain_id=chain_id,
                residue_name=residue_name,
                residue_number=residue_number,
                sequence_position=residue_number,
                one_letter_code=None,
                uniprot_ids=_chain_uniprot_ids(bundle, chain_id),
                provenance={
                    "entry": bundle.pdb_id,
                    "source_kind": "atom_derived_only",
                    "chain_id": chain_id,
                    "insertion_code": insertion_code,
                },
            )
            residue_nodes.append(node)
            residue_by_key[residue_key] = node

    residue_positions = {
        residue_key: _mean_coordinates(coords)
        for residue_key, coords in residue_centroids.items()
        if coords
    }
    seen_contacts: set[tuple[str, str]] = set()
    residue_keys = list(residue_positions)
    for index, left_key in enumerate(residue_keys):
        left_position = residue_positions[left_key]
        for right_key in residue_keys[index + 1 :]:
            right_position = residue_positions[right_key]
            pair = tuple(sorted((left_key, right_key)))
            if pair in seen_contacts:
                continue
            distance = _distance(left_position, right_position)
            if distance > contact_cutoff:
                continue
            seen_contacts.add(pair)
            edges.append(
                GraphEdge(
                    source=pair[0],
                    target=pair[1],
                    kind="spatial_contact",
                    weight=distance,
                    provenance={
                        "entry": bundle.pdb_id,
                        "cutoff": contact_cutoff,
                    },
                )
            )

    return ResidueGraph(
        pdb_id=bundle.pdb_id,
        nodes=tuple(residue_nodes),
        edges=tuple(edges),
        provenance=_bundle_provenance(bundle),
    )


def extract_structure_graphs(
    bundle: RCSBStructureBundle,
    atom_rows: Iterable[Mapping[str, Any]] | None = None,
    residue_rows: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, AtomGraph | ResidueGraph]:
    atom_rows_list = _coerce_row_list(atom_rows)
    residue_rows_list = _coerce_row_list(residue_rows)
    atom_graph = extract_atom_graph(bundle, atom_rows_list)
    residue_graph = extract_residue_graph(
        bundle,
        atom_rows=atom_rows_list,
        residue_rows=residue_rows_list,
    )
    return {"atom": atom_graph, "residue": residue_graph}

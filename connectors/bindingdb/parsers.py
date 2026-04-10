from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

_AFFINITY_KEYS = (
    "affinity_value_nM",
    "affinity_value",
    "binding_affinity_value",
    "value",
    "measurement_value",
    "bdb.affinity",
)
_AFFINITY_TYPE_KEYS = (
    "affinity_type",
    "Affinity Type",
    "binding_affinity_type",
    "measurement_type",
    "type",
    "bdb.affinity_type",
)
_ASSAY_DESCRIPTION_KEYS = (
    "assay_description",
    "Assay Description",
    "description",
    "assay",
)
_CURATION_DATE_KEYS = ("curation_date", "BindingDB Curation Date", "date_in_bdb")
_PUBLICATION_DATE_KEYS = ("publication_date", "Publication Date", "date_published")
_LIGAND_SMILES_KEYS = (
    "ligand_smiles",
    "Ligand SMILES",
    "smiles",
    "SMILES",
    "bdb.smile",
)
_LIGAND_INCHI_KEYS = (
    "ligand_inchi_key",
    "Ligand InChI Key",
    "inchi_key",
    "InChIKey",
)
_MONOMER_ID_KEYS = (
    "monomer_id",
    "BindingDB MonomerID",
    "monomerID",
    "bdb.monomerid",
)
_REACTANT_SET_ID_KEYS = (
    "reactant_set_id",
    "BindingDB Reactant_set_id",
)
_TARGET_NAME_KEYS = ("target_name", "Target Name", "protein_name")
_TARGET_UNIPROT_KEYS = (
    "target_uniprot_id",
    "target_uniprot_ids",
    "UniProtKB/SwissProt",
    "uniprot",
    "bdb.primary",
)
_TARGET_PDB_KEYS = ("target_pdb_id", "target_pdb_ids", "PDB", "pdb")


@dataclass(frozen=True)
class BindingDBAssayRecord:
    """Normalized view of a BindingDB assay row."""

    reactant_set_id: str = ""
    monomer_id: str = ""
    ligand_smiles: str = ""
    ligand_inchi_key: str = ""
    target_name: str = ""
    target_uniprot_ids: tuple[str, ...] = ()
    target_pdb_ids: tuple[str, ...] = ()
    affinity_type: str = ""
    affinity_value_nM: float | None = None
    assay_description: str = ""
    publication_date: str = ""
    curation_date: str = ""
    source: str = ""
    raw: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "reactant_set_id": self.reactant_set_id,
            "monomer_id": self.monomer_id,
            "ligand_smiles": self.ligand_smiles,
            "ligand_inchi_key": self.ligand_inchi_key,
            "target_name": self.target_name,
            "target_uniprot_ids": list(self.target_uniprot_ids),
            "target_pdb_ids": list(self.target_pdb_ids),
            "affinity_type": self.affinity_type,
            "affinity_value_nM": self.affinity_value_nM,
            "assay_description": self.assay_description,
            "publication_date": self.publication_date,
            "curation_date": self.curation_date,
            "source": self.source,
            "raw": self.raw,
        }


def parse_bindingdb_assays(
    payload: Any,
    *,
    source: str = "",
) -> list[BindingDBAssayRecord]:
    """Normalize BindingDB service or TSV rows into assay records."""
    rows = _coerce_rows(payload)
    return [parse_bindingdb_assay_row(row, source=source) for row in rows]


def parse_bindingdb_assay_row(
    row: Mapping[str, Any],
    *,
    source: str = "",
) -> BindingDBAssayRecord:
    values = dict(row)
    reactant_set_id = _first_text(values, _REACTANT_SET_ID_KEYS)
    monomer_id = _first_text(values, _MONOMER_ID_KEYS)
    ligand_smiles = _first_text(values, _LIGAND_SMILES_KEYS)
    ligand_inchi_key = _first_text(values, _LIGAND_INCHI_KEYS)
    target_name = _first_text(values, _TARGET_NAME_KEYS)
    target_uniprot_ids = _normalize_id_list(
        (
            _first_value(values, _TARGET_UNIPROT_KEYS),
            values.get("bdb.alternative"),
        ),
        uppercase=True,
    )
    target_pdb_ids = _normalize_id_list(_first_text(values, _TARGET_PDB_KEYS), uppercase=True)
    affinity_type = _first_text(values, _AFFINITY_TYPE_KEYS)
    affinity_value_nM = _parse_affinity_value(_first_text(values, _AFFINITY_KEYS))
    assay_description = _first_text(values, _ASSAY_DESCRIPTION_KEYS)
    publication_date = _first_text(values, _PUBLICATION_DATE_KEYS)
    curation_date = _first_text(values, _CURATION_DATE_KEYS)
    return BindingDBAssayRecord(
        reactant_set_id=reactant_set_id,
        monomer_id=monomer_id,
        ligand_smiles=ligand_smiles,
        ligand_inchi_key=ligand_inchi_key,
        target_name=target_name,
        target_uniprot_ids=target_uniprot_ids,
        target_pdb_ids=target_pdb_ids,
        affinity_type=affinity_type,
        affinity_value_nM=affinity_value_nM,
        assay_description=assay_description,
        publication_date=publication_date,
        curation_date=curation_date,
        source=source,
        raw=values,
    )


def _coerce_rows(payload: Any) -> list[Mapping[str, Any]]:
    if payload is None or payload == "":
        return []
    if isinstance(payload, list):
        rows: list[Mapping[str, Any]] = []
        for row in payload:
            rows.extend(_coerce_rows(row))
        return rows
    if isinstance(payload, Mapping):
        if "getLindsByUniprotResponse" in payload and isinstance(
            payload["getLindsByUniprotResponse"],
            Mapping,
        ):
            return _coerce_rows(payload["getLindsByUniprotResponse"])
        if "records" in payload and isinstance(payload["records"], list):
            return _coerce_rows(payload["records"])
        if "results" in payload and isinstance(payload["results"], list):
            return _coerce_rows(payload["results"])
        affinities = payload.get("bdb.affinities")
        if isinstance(affinities, list):
            base = {
                key: value
                for key, value in payload.items()
                if key != "bdb.affinities"
            }
            rows = [
                {**base, **row}
                for row in affinities
                if isinstance(row, Mapping)
            ]
            if rows:
                return rows
        if any(isinstance(value, list) for value in payload.values()):
            for value in payload.values():
                if isinstance(value, list) and all(isinstance(row, Mapping) for row in value):
                    return list(value)
        for value in payload.values():
            if isinstance(value, Mapping):
                nested_rows = _coerce_rows(value)
                if nested_rows:
                    return nested_rows
        return [payload]
    return []


def _first_value(values: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key not in values:
            continue
        value = values[key]
        if isinstance(value, str) and not value.strip():
            continue
        if value is None:
            continue
        return value
    return None


def _first_text(values: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = values.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _normalize_id_list(raw: Any, *, uppercase: bool = False) -> tuple[str, ...]:
    if raw is None or raw == "":
        return ()
    if isinstance(raw, str):
        parts = [
            part.strip()
            for part in re.split(r"[;,|/]", raw)
            if part.strip()
        ]
    elif isinstance(raw, Sequence) and not isinstance(raw, (bytes, bytearray)):
        parts = []
        for item in raw:
            parts.extend(_normalize_id_list(item, uppercase=uppercase))
        return tuple(dict.fromkeys(parts))
    else:
        return _normalize_id_list(str(raw), uppercase=uppercase)
    if uppercase:
        parts = [part.upper() for part in parts]
    return tuple(dict.fromkeys(parts))


def _parse_affinity_value(raw: str) -> float | None:
    if not raw:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", raw)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None

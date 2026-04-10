from __future__ import annotations

import json
import zipfile
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "polymer": (
        "component_id",
        "comments",
        "topology",
        "weight",
        "source_organism",
        "unpid2",
        "scientific_name",
        "type",
        "display_name",
        "res_count",
        "sequence",
        "n_pdb_ids",
        "taxid",
        "unpid1",
        "polymerid",
        "pdb_ids",
        "short_name",
        "common_name",
        "chembl_id",
    ),
    "poly_name": ("polymerid", "name"),
    "enzyme_reactant_set": (
        "enzyme",
        "comments",
        "sources",
        "reactant_set_id",
        "inhibitor_complexid",
        "inhibitor_polymerid",
        "entryid",
        "e_prep",
        "enzyme_monomerid",
        "substrate_monomerid",
        "inhibitor",
        "s_prep",
        "inhibitor_monomerid",
        "enzyme_complexid",
        "substrate_complexid",
        "substrate_polymerid",
        "enzyme_polymerid",
        "category",
        "substrate",
        "i_prep",
    ),
    "assay": ("assayid", "description", "assay_name", "entryid"),
    "entry": (
        "depoid",
        "comments",
        "entrydate",
        "entrytitle",
        "entrantid",
        "revised",
        "entryid",
        "meas_tech",
        "hold",
        "ezid",
    ),
    "monomer": (
        "n_pdb_ids_sub",
        "pdb_ids_exact",
        "comments",
        "emp_form",
        "het_pdb",
        "display_name",
        "inchi_key",
        "pdb_ids_sub",
        "chembl_id",
        "monomerid",
        "inchi",
        "weight",
        "type",
        "n_pdb_ids_exact",
        "smiles_string",
        "rdmid",
    ),
    "ki_result": (
        "kd_uncert",
        "ic50",
        "ki_result_id",
        "koff_uncert",
        "reactant_set_id",
        "kon",
        "solution_id",
        "ic_percent",
        "vmax_uncert",
        "delta_g",
        "k_cat",
        "k_cat_uncert",
        "ec50",
        "koff",
        "data_fit_meth_id",
        "ic_percent_def",
        "kd",
        "vmax",
        "ph_uncert",
        "e_conc_range",
        "ec50_uncert",
        "press",
        "i_conc_range",
        "temp_uncert",
        "ki",
        "kon_uncert",
        "temp",
        "km",
        "comments",
        "instrumentid",
        "assayid",
        "ic50_uncert",
        "biological_data",
        "entryid",
        "delta_g_uncert",
        "s_conc_range",
        "km_uncert",
        "ki_uncert",
        "ph",
        "ic_percent_uncert",
        "press_uncert",
    ),
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _timestamp_slug() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _normalize_accessions(values: Sequence[str]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        accession = _text(value).upper()
        if accession:
            ordered.setdefault(accession.casefold(), accession)
    return tuple(ordered.values())


def _split_identifiers(value: Any) -> tuple[str, ...]:
    raw = _text(value)
    if not raw or raw.lower() == "null":
        return ()
    normalized = raw.replace(";", ",")
    ordered: dict[str, str] = {}
    for part in normalized.split(","):
        item = part.strip().upper()
        if item:
            ordered.setdefault(item.casefold(), item)
    return tuple(ordered.values())


def _coerce_int(value: Any) -> int | None:
    text = _text(value)
    if not text or text.upper() == "NULL":
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _measurement_fields(result_row: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    resolved: list[tuple[str, str]] = []
    for field_name, label in (("ki", "Ki"), ("ic50", "IC50"), ("ec50", "EC50"), ("kd", "Kd")):
        value = _text(result_row.get(field_name))
        if value and value.upper() != "NULL":
            resolved.append((label, value))
    return tuple(resolved)


def _decode_sql_token(token: str) -> Any:
    text = token.strip()
    if not text:
        return ""
    if text.upper() == "NULL":
        return None
    return text


def _parse_insert_values(payload: str) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    current_row: list[Any] = []
    current_value: list[str] = []
    in_string = False
    escape = False
    in_tuple = False

    for char in payload:
        if in_string:
            if escape:
                current_value.append(char)
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == "'":
                in_string = False
                continue
            current_value.append(char)
            continue

        if char == "'":
            in_string = True
            continue
        if char == "(":
            in_tuple = True
            current_row = []
            current_value = []
            continue
        if char == ")" and in_tuple:
            current_row.append(_decode_sql_token("".join(current_value)))
            rows.append(tuple(current_row))
            current_row = []
            current_value = []
            in_tuple = False
            continue
        if char == "," and in_tuple:
            current_row.append(_decode_sql_token("".join(current_value)))
            current_value = []
            continue
        if char == ";" and not in_tuple:
            break
        if in_tuple:
            current_value.append(char)

    return rows


def _default_dump_entry_name(zip_path: Path) -> str:
    stem = zip_path.stem
    if stem.endswith("_dmp"):
        stem = stem[:-4]
    return f"{stem}.dmp"


def _resolve_dump_entry_name(zip_path: Path, dump_entry_name: str | None) -> str:
    if dump_entry_name:
        return dump_entry_name
    default_name = _default_dump_entry_name(zip_path)
    with zipfile.ZipFile(zip_path) as archive:
        if default_name in archive.namelist():
            return default_name
        dump_candidates = sorted(
            name for name in archive.namelist() if name.casefold().endswith(".dmp")
        )
        if len(dump_candidates) == 1:
            return dump_candidates[0]
    return default_name


def iter_table_rows(
    zip_path: Path,
    table_name: str,
    *,
    dump_entry_name: str | None = None,
) -> Iterable[dict[str, Any]]:
    columns = TABLE_COLUMNS.get(table_name)
    if columns is None:
        raise KeyError(f"unsupported table_name: {table_name}")
    entry_name = _resolve_dump_entry_name(zip_path, dump_entry_name)
    prefix = f"INSERT INTO `{table_name}` VALUES "
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open(entry_name) as handle:
            for raw_line in handle:
                line = raw_line.decode("utf-8", errors="ignore").rstrip("\n")
                if not line.startswith(prefix):
                    continue
                for row in _parse_insert_values(line[len(prefix) :]):
                    if len(row) != len(columns):
                        continue
                    yield dict(zip(columns, row, strict=False))


@dataclass(frozen=True, slots=True)
class BindingDBDumpAccessionSlice:
    accession: str
    polymers: tuple[dict[str, Any], ...]
    reactant_sets: tuple[dict[str, Any], ...]
    assays: tuple[dict[str, Any], ...]
    entries: tuple[dict[str, Any], ...]
    monomers: tuple[dict[str, Any], ...]
    measurement_results: tuple[dict[str, Any], ...]
    assay_rows: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "polymer_count": len(self.polymers),
            "reactant_set_count": len(self.reactant_sets),
            "assay_count": len(self.assays),
            "entry_count": len(self.entries),
            "monomer_count": len(self.monomers),
            "measurement_result_count": len(self.measurement_results),
            "assay_row_count": len(self.assay_rows),
            "polymers": [dict(item) for item in self.polymers],
            "reactant_sets": [dict(item) for item in self.reactant_sets],
            "assays": [dict(item) for item in self.assays],
            "entries": [dict(item) for item in self.entries],
            "monomers": [dict(item) for item in self.monomers],
            "measurement_results": [dict(item) for item in self.measurement_results],
            "assay_rows": [dict(item) for item in self.assay_rows],
        }


@dataclass(frozen=True, slots=True)
class BindingDBDumpExtractResult:
    zip_path: str
    dump_entry_name: str
    generated_at: str
    accessions: tuple[str, ...]
    slices: tuple[BindingDBDumpAccessionSlice, ...]
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "zip_path": self.zip_path,
            "dump_entry_name": self.dump_entry_name,
            "generated_at": self.generated_at,
            "accessions": list(self.accessions),
            "slice_count": len(self.slices),
            "slices": [item.to_dict() for item in self.slices],
            "notes": list(self.notes),
        }


def extract_bindingdb_dump_records(
    zip_path: Path,
    accessions: Sequence[str],
    *,
    dump_entry_name: str | None = None,
) -> BindingDBDumpExtractResult:
    normalized_accessions = _normalize_accessions(accessions)
    if not normalized_accessions:
        raise ValueError("at least one accession is required")
    entry_name = _resolve_dump_entry_name(zip_path, dump_entry_name)

    accession_to_polymer_ids: dict[str, set[int]] = {item: set() for item in normalized_accessions}
    polymer_rows_by_id: dict[int, dict[str, Any]] = {}
    polymer_names_by_id: dict[int, set[str]] = defaultdict(set)

    for row in iter_table_rows(zip_path, "polymer", dump_entry_name=entry_name):
        polymer_id = _coerce_int(row.get("polymerid"))
        if polymer_id is None:
            continue
        row_accessions = {
            accession
            for accession in normalized_accessions
            if accession in {
                *_split_identifiers(row.get("unpid1")),
                *_split_identifiers(row.get("unpid2")),
            }
        }
        if not row_accessions:
            continue
        polymer_rows_by_id[polymer_id] = dict(row)
        for accession in row_accessions:
            accession_to_polymer_ids[accession].add(polymer_id)

    if polymer_rows_by_id:
        for row in iter_table_rows(zip_path, "poly_name", dump_entry_name=entry_name):
            polymer_id = _coerce_int(row.get("polymerid"))
            if polymer_id is None or polymer_id not in polymer_rows_by_id:
                continue
            name = _text(row.get("name"))
            if name:
                polymer_names_by_id[polymer_id].add(name)
        for polymer_id, polymer_row in polymer_rows_by_id.items():
            names = sorted(polymer_names_by_id.get(polymer_id, ()))
            if names:
                polymer_row["names"] = names

    selected_polymer_ids = {
        polymer_id
        for polymer_ids in accession_to_polymer_ids.values()
        for polymer_id in polymer_ids
    }
    reactant_rows_by_id: dict[int, dict[str, Any]] = {}
    monomer_rows_needed: set[int] = set()
    entry_rows_needed: set[int] = set()
    accession_to_reactant_ids: dict[str, set[int]] = {item: set() for item in normalized_accessions}

    for row in iter_table_rows(zip_path, "enzyme_reactant_set", dump_entry_name=entry_name):
        enzyme_polymer_id = _coerce_int(row.get("enzyme_polymerid"))
        reactant_set_id = _coerce_int(row.get("reactant_set_id"))
        if enzyme_polymer_id is None or reactant_set_id is None:
            continue
        if enzyme_polymer_id not in selected_polymer_ids:
            continue
        reactant_rows_by_id[reactant_set_id] = dict(row)
        inhibitor_monomer_id = _coerce_int(row.get("inhibitor_monomerid"))
        if inhibitor_monomer_id is not None:
            monomer_rows_needed.add(inhibitor_monomer_id)
        entry_id = _coerce_int(row.get("entryid"))
        if entry_id is not None:
            entry_rows_needed.add(entry_id)
        for accession, polymer_ids in accession_to_polymer_ids.items():
            if enzyme_polymer_id in polymer_ids:
                accession_to_reactant_ids[accession].add(reactant_set_id)

    assay_rows_by_entry_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in iter_table_rows(zip_path, "assay", dump_entry_name=entry_name):
        entry_id = _coerce_int(row.get("entryid"))
        if entry_id is None or entry_id not in entry_rows_needed:
            continue
        assay_rows_by_entry_id[entry_id].append(dict(row))

    entry_rows_by_id: dict[int, dict[str, Any]] = {}
    for row in iter_table_rows(zip_path, "entry", dump_entry_name=entry_name):
        entry_id = _coerce_int(row.get("entryid"))
        if entry_id is None or entry_id not in entry_rows_needed:
            continue
        entry_rows_by_id[entry_id] = dict(row)

    monomer_rows_by_id: dict[int, dict[str, Any]] = {}
    for row in iter_table_rows(zip_path, "monomer", dump_entry_name=entry_name):
        monomer_id = _coerce_int(row.get("monomerid"))
        if monomer_id is None or monomer_id not in monomer_rows_needed:
            continue
        monomer_rows_by_id[monomer_id] = dict(row)

    measurement_rows_by_reactant_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in iter_table_rows(zip_path, "ki_result", dump_entry_name=entry_name):
        reactant_set_id = _coerce_int(row.get("reactant_set_id"))
        if reactant_set_id is None or reactant_set_id not in reactant_rows_by_id:
            continue
        measurement_rows_by_reactant_id[reactant_set_id].append(dict(row))

    slices: list[BindingDBDumpAccessionSlice] = []
    for accession in normalized_accessions:
        polymer_ids = accession_to_polymer_ids.get(accession, set())
        reactant_ids = accession_to_reactant_ids.get(accession, set())
        accession_reactants = [reactant_rows_by_id[item] for item in sorted(reactant_ids)]
        accession_entry_ids = {
            entry_id
            for entry_id in (_coerce_int(item.get("entryid")) for item in accession_reactants)
            if entry_id is not None
        }
        accession_monomer_ids = {
            monomer_id
            for monomer_id in (
                _coerce_int(item.get("inhibitor_monomerid")) for item in accession_reactants
            )
            if monomer_id is not None
        }
        polymer_rows = tuple(polymer_rows_by_id[item] for item in sorted(polymer_ids))
        polymer_by_id = {
            _coerce_int(item.get("polymerid")): item
            for item in polymer_rows
            if _coerce_int(item.get("polymerid")) is not None
        }
        monomer_rows = tuple(monomer_rows_by_id[item] for item in sorted(accession_monomer_ids))
        monomer_by_id = {
            _coerce_int(item.get("monomerid")): item
            for item in monomer_rows
            if _coerce_int(item.get("monomerid")) is not None
        }
        measurement_rows = tuple(
            measurement
            for reactant_id in sorted(reactant_ids)
            for measurement in measurement_rows_by_reactant_id.get(reactant_id, ())
        )
        assay_by_entry_and_id = {
            (_coerce_int(item.get("entryid")), _coerce_int(item.get("assayid"))): item
            for item in (
                assay
                for entry_id in sorted(accession_entry_ids)
                for assay in assay_rows_by_entry_id.get(entry_id, ())
            )
        }
        entry_by_id = {
            entry_id: entry_rows_by_id[entry_id] for entry_id in sorted(accession_entry_ids)
        }
        assay_rows: list[dict[str, Any]] = []
        for measurement in measurement_rows:
            reactant_set_id = _coerce_int(measurement.get("reactant_set_id"))
            reactant = (
                reactant_rows_by_id.get(reactant_set_id)
                if reactant_set_id is not None
                else None
            )
            if reactant is None:
                continue
            polymer_id = _coerce_int(reactant.get("enzyme_polymerid"))
            polymer = polymer_by_id.get(polymer_id)
            monomer_id = _coerce_int(reactant.get("inhibitor_monomerid"))
            monomer = monomer_by_id.get(monomer_id)
            entry_id = _coerce_int(measurement.get("entryid"))
            assay_id = _coerce_int(measurement.get("assayid"))
            assay = assay_by_entry_and_id.get((entry_id, assay_id))
            entry = entry_by_id.get(entry_id)
            for measurement_type, measurement_value in _measurement_fields(measurement):
                row = {
                    "BindingDB Reactant_set_id": _text(reactant.get("reactant_set_id")),
                    "BindingDB MonomerID": _text(reactant.get("inhibitor_monomerid")),
                    "Ligand SMILES": _text(monomer.get("smiles_string") if monomer else None),
                    "Ligand InChI Key": _text(monomer.get("inchi_key") if monomer else None),
                    "Target Name": _text(
                        polymer.get("display_name") if polymer else reactant.get("enzyme")
                    ),
                    "UniProtKB/SwissProt": accession,
                    "Affinity Type": measurement_type,
                    "affinity_value_nM": measurement_value,
                    "Assay Description": _text(assay.get("description") if assay else None),
                    "Publication Date": _text(entry.get("entrydate") if entry else None),
                    "BindingDB Curation Date": _text(entry.get("entrydate") if entry else None),
                    "DOI": _text(entry.get("ezid") if entry else None),
                    "bindingdb_result_id": _text(measurement.get("ki_result_id")),
                    "bindingdb_assay_id": _text(measurement.get("assayid")),
                    "bindingdb_entry_id": _text(measurement.get("entryid")),
                    "bindingdb_source_id": (
                        f"{_text(reactant.get('reactant_set_id'))}:"
                        f"{_text(measurement.get('ki_result_id'))}:"
                        f"{measurement_type.upper()}"
                    ),
                }
                if polymer is not None:
                    alternative = tuple(
                        item
                        for item in _split_identifiers(polymer.get("unpid2"))
                        if item != accession
                    )
                    if alternative:
                        row["bindingdb_target_uniprot_aliases"] = list(alternative)
                assay_rows.append(row)
        slices.append(
            BindingDBDumpAccessionSlice(
                accession=accession,
                polymers=polymer_rows,
                reactant_sets=tuple(accession_reactants),
                assays=tuple(
                    assay
                    for entry_id in sorted(accession_entry_ids)
                    for assay in assay_rows_by_entry_id.get(entry_id, ())
                ),
                entries=tuple(entry_rows_by_id[item] for item in sorted(accession_entry_ids)),
                monomers=monomer_rows,
                measurement_results=measurement_rows,
                assay_rows=tuple(assay_rows),
            )
        )

    notes = (
        (
            "line-oriented SQL dump parsing is conservative and optimized for "
            "accession-scoped extraction"
        ),
        (
            "the local BindingDB dump provides reactant_set_id values missing from "
            "the lightweight REST lane"
        ),
    )
    return BindingDBDumpExtractResult(
        zip_path=str(zip_path),
        dump_entry_name=entry_name,
        generated_at=_utc_now().isoformat(),
        accessions=normalized_accessions,
        slices=tuple(slices),
        notes=notes,
    )


def write_bindingdb_dump_extract(
    result: BindingDBDumpExtractResult,
    *,
    output_root: Path,
    run_id: str | None = None,
) -> dict[str, str]:
    resolved_run_id = _text(run_id) or f"bindingdb-dump-{_timestamp_slug()}"
    run_root = output_root / resolved_run_id
    run_root.mkdir(parents=True, exist_ok=True)

    for slice_result in result.slices:
        accession_root = run_root / slice_result.accession
        accession_root.mkdir(parents=True, exist_ok=True)
        (accession_root / f"{slice_result.accession}.bindingdb_dump.json").write_text(
            json.dumps(slice_result.to_dict(), indent=2),
            encoding="utf-8",
        )

    summary_path = run_root / "summary.json"
    latest_path = output_root / "LATEST.json"
    summary_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    latest_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    return {
        "run_root": str(run_root),
        "summary": str(summary_path),
        "latest": str(latest_path),
    }


__all__ = [
    "BindingDBDumpAccessionSlice",
    "BindingDBDumpExtractResult",
    "extract_bindingdb_dump_records",
    "iter_table_rows",
    "write_bindingdb_dump_extract",
]

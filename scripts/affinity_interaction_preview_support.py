from __future__ import annotations

import math
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PDBBIND_CLASS_MAP = {
    "PL": "protein_ligand",
    "PP": "protein_protein",
    "PN": "protein_nucleic_acid",
    "NL": "nucleic_acid_ligand",
}

PDBBIND_FILE_MAP = {
    "PL": "INDEX_general_PL.2020R1.lst",
    "PP": "INDEX_general_PP.2020R1.lst",
    "PN": "INDEX_general_PN.2020R1.lst",
    "NL": "INDEX_general_NL.2020R1.lst",
}

PDBBIND_LINE_RE = re.compile(
    r"^(?P<pdb_id>[0-9A-Za-z]{4})\s+"
    r"(?P<resolution>\S+)\s+"
    r"(?P<release_year>\d{4})\s+"
    r"(?P<binding_data>.+?)\s+//\s+"
    r"(?P<comment>.+)$"
)

AFFINITY_RE = re.compile(
    r"^(?P<measurement_type>Kd|Ki|IC50|EC50|kon|koff|ΔG|ΔH|-TΔS|Activity|Methemoglobin)"
    r"\s*(?P<relation>>=|<=|=|>|<|~)?\s*"
    r"(?P<value>[-+]?\d+(?:\.\d+)?)"
    r"(?P<remainder>.*)$",
    flags=re.IGNORECASE,
)

PAREN_RE = re.compile(r"\(([^()]*)\)")

UNIT_SCALE_TO_MOLAR = {
    "m": 1.0,
    "mm": 1e-3,
    "um": 1e-6,
    "μm": 1e-6,
    "µm": 1e-6,
    "nm": 1e-9,
    "pm": 1e-12,
    "fm": 1e-15,
}

R_KCAL_PER_MOL_K = 0.00198720425864083
DEFAULT_TEMPERATURE_K = 298.15

ENTRY_FIELDS = [
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
]

ASSAY_FIELDS = [
    "assayid",
    "description",
    "assay_name",
    "entryid",
]

ENZYME_REACTANT_SET_FIELDS = [
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
]

KI_RESULT_FIELDS = [
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
]

COMPLEX_FIELDS = [
    "n_pdb_ids",
    "comments",
    "pdb_ids",
    "weight",
    "complexid",
    "component_count",
    "type",
    "display_name",
    "chembl_id",
]

MONOMER_FIELDS = [
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
]

POLYMER_FIELDS = [
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
]


@dataclass(slots=True)
class ParsedBindingMeasurement:
    measurement_type: str | None
    relation: str | None
    raw_value: float | None
    raw_unit: str | None
    normalized_molar: float | None
    p_affinity: float | None
    delta_g_reported_kcal_per_mol: float | None
    delta_g_derived_298k_kcal_per_mol: float | None
    derivation_method: str | None
    confidence_for_normalization: str


def _normalize_possible_utf8_mojibake(value: str | None) -> str | None:
    text = str(value) if value is not None else None
    if text is None:
        return None
    text = (
        text.replace("Î”", "Δ")
        .replace("Î¼", "μ")
        .replace("Âµ", "µ")
        .replace("Ãƒ", "Ã")
        .replace("Ã‚", "Â")
        .replace("ÃŽ", "Î")
        .replace("Ã¢", "â")
        .replace("Ã", "Ï")
    )
    if not any(marker in text for marker in ("Ã", "Â", "Î", "â", "Ï")):
        return text
    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return text
    return repaired or text


def _clean_unit(text: str | None) -> str | None:
    unit = str(_normalize_possible_utf8_mojibake(text) or "").strip()
    return unit or None


def _maybe_convert_concentration_to_molar(
    value: float | None,
    unit: str | None,
) -> float | None:
    if value is None or unit is None:
        return None
    normalized = unit.strip().lower().replace(" ", "")
    scale = UNIT_SCALE_TO_MOLAR.get(normalized)
    if scale is None:
        return None
    return value * scale


def _derive_delta_g_from_dissociation_molar(value_molar: float | None) -> float | None:
    if value_molar is None or value_molar <= 0:
        return None
    return R_KCAL_PER_MOL_K * DEFAULT_TEMPERATURE_K * math.log(value_molar)


def parse_binding_measurement(raw_affinity_string: str) -> ParsedBindingMeasurement:
    text = str(_normalize_possible_utf8_mojibake(raw_affinity_string) or "").strip()
    match = AFFINITY_RE.match(text)
    if match is None:
        return ParsedBindingMeasurement(
            measurement_type=None,
            relation=None,
            raw_value=None,
            raw_unit=None,
            normalized_molar=None,
            p_affinity=None,
            delta_g_reported_kcal_per_mol=None,
            delta_g_derived_298k_kcal_per_mol=None,
            derivation_method=None,
            confidence_for_normalization="unparsed",
        )

    measurement_type = str(match.group("measurement_type") or "").strip()
    relation = str(match.group("relation") or "").strip() or "="
    raw_value = float(match.group("value"))
    remainder = str(match.group("remainder") or "").strip()

    plus_minus_split = remainder.split("+/-", 1)[0].strip()
    raw_unit = _clean_unit(plus_minus_split or None)

    normalized_molar = None
    p_affinity = None
    delta_g_reported = None
    delta_g_derived = None
    derivation_method = None
    confidence = "non_comparable"

    if relation == "=" and measurement_type in {"Kd", "Ki", "IC50", "EC50"}:
        normalized_molar = _maybe_convert_concentration_to_molar(raw_value, raw_unit)
        if normalized_molar is not None and normalized_molar > 0:
            p_affinity = -math.log10(normalized_molar)
            confidence = "exact_relation_unit_converted"
        else:
            confidence = "exact_relation_unit_unconverted"
        if measurement_type in {"Kd", "Ki"} and normalized_molar is not None:
            delta_g_derived = _derive_delta_g_from_dissociation_molar(normalized_molar)
            derivation_method = "RTlnK_at_298.15K"
    elif measurement_type == "Î”G" and relation == "=":
        delta_g_reported = raw_value
        confidence = "reported_thermodynamic_value"
    elif relation == "=":
        confidence = "exact_relation_non_comparable"
    else:
        confidence = "non_exact_relation"

    return ParsedBindingMeasurement(
        measurement_type=measurement_type,
        relation=relation,
        raw_value=raw_value,
        raw_unit=raw_unit,
        normalized_molar=normalized_molar,
        p_affinity=p_affinity,
        delta_g_reported_kcal_per_mol=delta_g_reported,
        delta_g_derived_298k_kcal_per_mol=delta_g_derived,
        derivation_method=derivation_method,
        confidence_for_normalization=confidence,
    )


def parse_pdbbind_line(line: str, source_record_id: str) -> dict[str, Any] | None:
    text = str(line or "").strip()
    if not text or text.startswith("#"):
        return None
    match = PDBBIND_LINE_RE.match(text)
    if match is None:
        return None

    pdb_id = str(match.group("pdb_id") or "").strip().upper()
    resolution_raw = str(match.group("resolution") or "").strip()
    resolution = None if resolution_raw.upper() == "NMR" else float(resolution_raw)
    release_year = int(match.group("release_year"))
    raw_binding_string = str(match.group("binding_data") or "").strip()
    comment = str(match.group("comment") or "").strip()
    parsed = parse_binding_measurement(raw_binding_string)
    parenthetical_tokens = [token.strip() for token in PAREN_RE.findall(comment) if token.strip()]

    return {
        "pdb_id": pdb_id,
        "resolution_angstrom": resolution,
        "resolution_raw": resolution_raw,
        "release_year": release_year,
        "raw_binding_string": raw_binding_string,
        "source_comment": comment,
        "reference_stub": comment.split(" ", 1)[0],
        "measurement_type": parsed.measurement_type,
        "relation": parsed.relation,
        "raw_value": parsed.raw_value,
        "raw_unit": parsed.raw_unit,
        "value_molar_normalized": parsed.normalized_molar,
        "p_affinity": parsed.p_affinity,
        "delta_g_reported_kcal_per_mol": parsed.delta_g_reported_kcal_per_mol,
        "delta_g_derived_298k_kcal_per_mol": parsed.delta_g_derived_298k_kcal_per_mol,
        "derivation_method": parsed.derivation_method,
        "confidence_for_normalization": parsed.confidence_for_normalization,
        "parenthetical_tokens": parenthetical_tokens,
        "source_record_id": source_record_id,
    }


def iter_pdbbind_rows(index_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for short_type, filename in PDBBIND_FILE_MAP.items():
        path = index_dir / filename
        source_record_id = f"pdbbind:{short_type}"
        complex_type = PDBBIND_CLASS_MAP[short_type]
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            parsed = parse_pdbbind_line(line, source_record_id)
            if parsed is None:
                continue
            parsed["complex_type"] = complex_type
            parsed["measurement_origin"] = "pdbbind"
            parsed["source_name"] = "PDBbind"
            parsed["measurement_id"] = (
                f"binding_measurement:pdbbind:{short_type}:{parsed['pdb_id']}:"
                f"{parsed.get('measurement_type') or 'unknown'}"
            )
            rows.append(parsed)
    return rows


def build_ligand_row_measurements(
    ligand_row_materialization_preview: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in ligand_row_materialization_preview.get("rows") or []:
        if not isinstance(row, dict):
            continue
        raw_affinity_string = ""
        if row.get("standard_type") and row.get("standard_value") is not None:
            raw_affinity_string = (
                f"{row['standard_type']}{row.get('standard_relation') or '='}"
                f"{row['standard_value']}{row.get('standard_units') or ''}"
            )
        parsed = parse_binding_measurement(raw_affinity_string)
        accession = str(row.get("accession") or "").strip()
        ligand_identifier = str(row.get("ligand_identifier") or "").strip()
        rows.append(
            {
                "measurement_id": (
                    f"binding_measurement:chembl_lightweight:{accession}:{ligand_identifier}:"
                    f"{row.get('representative_activity_id')}"
                ),
                "source_name": "ChEMBL lightweight ligand row",
                "source_record_id": row.get("representative_activity_id"),
                "complex_type": "protein_ligand",
                "measurement_origin": "chembl_lightweight",
                "primary_structure_or_target_ref": f"protein:{accession}",
                "accession": accession,
                "ligand_ref": row.get("ligand_ref"),
                "ligand_label": row.get("ligand_label"),
                "measurement_type": parsed.measurement_type or row.get("standard_type"),
                "relation": parsed.relation or row.get("standard_relation"),
                "raw_value": parsed.raw_value,
                "raw_unit": parsed.raw_unit or row.get("standard_units"),
                "raw_affinity_string": raw_affinity_string,
                "source_comment": row.get("evidence_kind"),
                "value_molar_normalized": parsed.normalized_molar,
                "p_affinity": parsed.p_affinity,
                "delta_g_reported_kcal_per_mol": parsed.delta_g_reported_kcal_per_mol,
                "delta_g_derived_298k_kcal_per_mol": parsed.delta_g_derived_298k_kcal_per_mol,
                "derivation_method": parsed.derivation_method,
                "confidence_for_normalization": parsed.confidence_for_normalization,
                "candidate_only": bool(row.get("candidate_only")),
            }
        )
    return rows


def summarize_best_exact_affinity(measurements: list[dict[str, Any]]) -> dict[str, Any] | None:
    comparable = [
        row for row in measurements if isinstance(row, dict) and row.get("p_affinity") is not None
    ]
    if not comparable:
        return None
    best = max(comparable, key=lambda row: float(row["p_affinity"]))
    return {
        "measurement_type": best.get("measurement_type"),
        "raw_affinity_string": best.get("raw_affinity_string"),
        "p_affinity": best.get("p_affinity"),
        "value_molar_normalized": best.get("value_molar_normalized"),
    }


def bindingdb_zip_inventory(zip_path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(zip_path, "r") as archive:
        entries = [
            {
                "full_name": entry.filename,
                "compressed_size": entry.compress_size,
                "uncompressed_size": entry.file_size,
            }
            for entry in archive.infolist()
        ]
    return {
        "zip_path": str(zip_path).replace("\\", "/"),
        "entry_count": len(entries),
        "entries": entries,
        "has_mysql_dump": any(
            str(entry["full_name"]).lower().endswith(".dmp") for entry in entries
        ),
    }


def parse_mitab_confidences(text: str) -> dict[str, float]:
    values: dict[str, float] = {}
    for token in str(text or "").split("|"):
        token = token.strip()
        if ":" not in token:
            continue
        key, raw = token.split(":", 1)
        try:
            values[key.strip()] = float(raw.strip())
        except ValueError:
            continue
    return values


def parse_psicquic_tab25(path: Path, accession: str) -> list[dict[str, Any]]:
    accession = accession.strip().upper()
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 15:
            continue
        interactor_a = parts[0]
        interactor_b = parts[1]
        alias_a = parts[4]
        alias_b = parts[5]
        detection_method = parts[6]
        publication = parts[8]
        interaction_type = parts[11]
        source_db = parts[12]
        interaction_ids = parts[13]
        confidence = parts[14]
        a_upper = interactor_a.upper()
        b_upper = interactor_b.upper()
        if accession not in a_upper and accession not in b_upper:
            continue
        focal_side = "A" if accession in a_upper else "B"
        partner = interactor_b if focal_side == "A" else interactor_a
        partner_alias = alias_b if focal_side == "A" else alias_a
        rows.append(
            {
                "focal_accession": accession,
                "partner_ref": partner,
                "partner_aliases": partner_alias.split("|") if partner_alias else [],
                "detection_method": detection_method,
                "publication": publication,
                "interaction_type": interaction_type,
                "source_db": source_db,
                "interaction_ids": interaction_ids.split("|") if interaction_ids else [],
                "confidence_scores": parse_mitab_confidences(confidence),
            }
        )
    return rows


def _map_table_row(fields: list[str], values: list[str | None]) -> dict[str, str | None]:
    return {
        field: _normalize_possible_utf8_mojibake(values[index]) if index < len(values) else None
        for index, field in enumerate(fields)
    }


def iter_sql_insert_tuples(line: str) -> list[str]:
    tuples: list[str] = []
    in_quote = False
    escape = False
    depth = 0
    start = -1
    for index, char in enumerate(line):
        if in_quote:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == "'":
                in_quote = False
            continue
        if char == "'":
            in_quote = True
            continue
        if char == "(":
            if depth == 0:
                start = index
            depth += 1
            continue
        if char == ")":
            if depth == 0:
                continue
            depth -= 1
            if depth == 0 and start >= 0:
                tuples.append(line[start : index + 1])
                start = -1
    return tuples


def split_sql_tuple_values(tuple_text: str) -> list[str | None]:
    text = tuple_text.strip()
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]

    values: list[str | None] = []
    current: list[str] = []
    in_quote = False
    escape = False
    for char in text:
        if in_quote:
            if escape:
                current.append(char)
                escape = False
            elif char == "\\":
                escape = True
            elif char == "'":
                in_quote = False
            else:
                current.append(char)
            continue
        if char == "'":
            in_quote = True
            continue
        if char == ",":
            token = "".join(current).strip()
            values.append(None if token.upper() == "NULL" else token)
            current = []
            continue
        current.append(char)
    token = "".join(current).strip()
    values.append(None if token.upper() == "NULL" else token)
    return values


def iter_table_rows(
    zip_path: Path,
    table_name: str,
    fields: list[str],
) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    insert_prefix = f"INSERT INTO `{table_name}`"
    with zipfile.ZipFile(zip_path, "r") as archive:
        dump_member = next(
            (
                entry
                for entry in archive.infolist()
                if str(entry.filename).lower().endswith(".dmp")
            ),
            None,
        )
        if dump_member is None:
            return rows
        with archive.open(dump_member, "r") as handle:
            for raw in handle:
                line = raw.decode("latin-1", errors="replace")
                if not line.startswith(insert_prefix):
                    continue
                for tuple_text in iter_sql_insert_tuples(line):
                    rows.append(_map_table_row(fields, split_sql_tuple_values(tuple_text)))
    return rows


def find_table_tuples_containing(
    zip_path: Path,
    table_name: str,
    needles: list[str],
) -> dict[str, list[str | None]]:
    remaining = {needle: needle for needle in needles}
    found: dict[str, list[str | None]] = {}
    insert_prefix = f"INSERT INTO `{table_name}`"
    with zipfile.ZipFile(zip_path, "r") as archive:
        dump_member = next(
            (
                entry
                for entry in archive.infolist()
                if str(entry.filename).lower().endswith(".dmp")
            ),
            None,
        )
        if dump_member is None:
            return found
        with archive.open(dump_member, "r") as handle:
            for raw in handle:
                line = raw.decode("latin-1", errors="replace")
                if not line.startswith(insert_prefix):
                    continue
                for tuple_text in iter_sql_insert_tuples(line):
                    matched_needles = [
                        needle for needle in tuple(remaining.values()) if needle in tuple_text
                    ]
                    if not matched_needles:
                        continue
                    values = split_sql_tuple_values(tuple_text)
                    for needle in matched_needles:
                        found[needle] = values
                        remaining.pop(needle, None)
                    if not remaining:
                        return found
    return found


def _non_empty_string(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _split_id_list(value: str | None) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _bindingdb_complex_type(
    reactant_row: dict[str, str | None],
    polymer_lookup: dict[str, dict[str, str | None]],
) -> str:
    partner_polymer_ids = [
        reactant_row.get("inhibitor_polymerid"),
        reactant_row.get("substrate_polymerid"),
    ]
    if _non_empty_string(reactant_row.get("inhibitor_monomerid")) or _non_empty_string(
        reactant_row.get("substrate_monomerid")
    ):
        return "protein_ligand"
    for partner_polymer_id in partner_polymer_ids:
        partner_polymer = polymer_lookup.get(str(partner_polymer_id or "").strip()) or {}
        partner_type = str(partner_polymer.get("type") or "").lower()
        if any(token in partner_type for token in ("rna", "dna", "nucleic", "oligo")):
            return "protein_nucleic_acid"
    if any(_non_empty_string(partner_id) for partner_id in partner_polymer_ids):
        return "protein_protein"
    return "protein_ligand"


def _build_bindingdb_measurement_row(
    *,
    accession: str,
    polymer_id: str,
    target_role: str,
    reactant_row: dict[str, str | None],
    ki_result_row: dict[str, str | None],
    entry_row: dict[str, str | None] | None,
    assay_row: dict[str, str | None] | None,
    polymer_lookup: dict[str, dict[str, str | None]],
    monomer_lookup: dict[str, dict[str, str | None]],
    complex_lookup: dict[str, dict[str, str | None]],
    measurement_type: str,
    raw_value: str,
) -> dict[str, Any]:
    normalized_type = measurement_type
    raw_value_clean = str(raw_value).strip()
    raw_affinity_string = f"{normalized_type}={raw_value_clean}"
    parsed = parse_binding_measurement(raw_affinity_string)
    partner_complex_ids = [
        reactant_row.get("enzyme_complexid"),
        reactant_row.get("inhibitor_complexid"),
        reactant_row.get("substrate_complexid"),
    ]
    partner_complex_names = [
        complex_lookup.get(str(complex_id or "").strip(), {}).get("display_name")
        for complex_id in partner_complex_ids
        if _non_empty_string(complex_id)
    ]
    partner_monomer_ids = [
        reactant_row.get("inhibitor_monomerid"),
        reactant_row.get("substrate_monomerid"),
        reactant_row.get("enzyme_monomerid"),
    ]
    partner_monomer_names = [
        monomer_lookup.get(str(monomer_id or "").strip(), {}).get("display_name")
        for monomer_id in partner_monomer_ids
        if _non_empty_string(monomer_id)
    ]
    partner_monomer_refs = []
    for monomer_id in partner_monomer_ids:
        monomer_key = str(monomer_id or "").strip()
        if not monomer_key:
            continue
        monomer_row = monomer_lookup.get(monomer_key) or {}
        pdb_ids_exact_sample = _split_id_list(monomer_row.get("pdb_ids_exact"))[:10]
        partner_monomer_refs.append(
            {
                "monomer_id": monomer_key,
                "display_name": monomer_row.get("display_name"),
                "chembl_id": monomer_row.get("chembl_id"),
                "het_pdb": monomer_row.get("het_pdb"),
                "type": monomer_row.get("type"),
                "inchi_key_present": bool(_non_empty_string(monomer_row.get("inchi_key"))),
                "smiles_present": bool(_non_empty_string(monomer_row.get("smiles_string"))),
                "pdb_ids_exact_sample": pdb_ids_exact_sample,
            }
        )
    source_comment_parts = [
        _non_empty_string(ki_result_row.get("comments")),
        _non_empty_string(reactant_row.get("comments")),
        _non_empty_string(assay_row.get("description") if assay_row else None),
    ]
    source_comment = " | ".join(part for part in source_comment_parts if part)
    row: dict[str, Any] = {
        "measurement_id": (
            "binding_measurement:bindingdb:"
            f"{ki_result_row.get('ki_result_id')}:{normalized_type}:{accession}"
        ),
        "source_name": "BindingDB local dump",
        "source_record_id": ki_result_row.get("ki_result_id"),
        "complex_type": _bindingdb_complex_type(reactant_row, polymer_lookup),
        "measurement_origin": "bindingdb",
        "primary_structure_or_target_ref": f"protein:{accession}",
        "accession": accession,
        "bindingdb_polymer_id": polymer_id,
        "bindingdb_target_role": target_role,
        "bindingdb_reactant_set_id": reactant_row.get("reactant_set_id"),
        "bindingdb_entry_id": ki_result_row.get("entryid"),
        "bindingdb_assay_id": ki_result_row.get("assayid"),
        "bindingdb_entry_title": entry_row.get("entrytitle") if entry_row else None,
        "bindingdb_measurement_technique": entry_row.get("meas_tech") if entry_row else None,
        "bindingdb_assay_name": assay_row.get("assay_name") if assay_row else None,
        "bindingdb_partner_complex_names": [
            name for name in partner_complex_names if _non_empty_string(name)
        ],
        "bindingdb_partner_monomer_names": [
            name for name in partner_monomer_names if _non_empty_string(name)
        ],
        "bindingdb_partner_monomer_ids": [
            ref["monomer_id"] for ref in partner_monomer_refs if ref.get("monomer_id")
        ],
        "bindingdb_partner_monomer_refs": partner_monomer_refs,
        "measurement_type": parsed.measurement_type or normalized_type,
        "relation": parsed.relation or "=",
        "raw_value": parsed.raw_value,
        "raw_unit": parsed.raw_unit,
        "raw_affinity_string": raw_affinity_string,
        "source_comment": source_comment or None,
        "value_molar_normalized": parsed.normalized_molar,
        "p_affinity": parsed.p_affinity,
        "delta_g_reported_kcal_per_mol": parsed.delta_g_reported_kcal_per_mol,
        "delta_g_derived_298k_kcal_per_mol": parsed.delta_g_derived_298k_kcal_per_mol,
        "derivation_method": parsed.derivation_method,
        "confidence_for_normalization": (
            "bindingdb_exact_value_without_unit"
            if parsed.confidence_for_normalization == "exact_relation_unit_unconverted"
            else parsed.confidence_for_normalization
        ),
        "reported_temperature_celsius": (
            float(ki_result_row["temp"]) if _non_empty_string(ki_result_row.get("temp")) else None
        ),
        "reported_pH": (
            float(ki_result_row["ph"]) if _non_empty_string(ki_result_row.get("ph")) else None
        ),
        "assay_context": {
            "i_conc_range": _non_empty_string(ki_result_row.get("i_conc_range")),
            "e_conc_range": _non_empty_string(ki_result_row.get("e_conc_range")),
            "s_conc_range": _non_empty_string(ki_result_row.get("s_conc_range")),
            "biological_data": _non_empty_string(ki_result_row.get("biological_data")),
        },
        "candidate_only": True,
    }
    if normalized_type == "Î”G" and _non_empty_string(ki_result_row.get("delta_g")):
        row.update(
            {
                "raw_value": float(str(ki_result_row["delta_g"]).strip()),
                "raw_unit": "kcal/mol",
                "raw_affinity_string": f"Î”G={str(ki_result_row['delta_g']).strip()} kcal/mol",
                "delta_g_reported_kcal_per_mol": float(str(ki_result_row["delta_g"]).strip()),
                "delta_g_derived_298k_kcal_per_mol": None,
                "derivation_method": None,
                "confidence_for_normalization": "reported_thermodynamic_value",
            }
        )
    if row.get("measurement_type") == "ÃŽâ€G":
        row["measurement_type"] = "Î”G"
    raw_affinity_string_text = str(row.get("raw_affinity_string") or "")
    if "ÃŽâ€" in raw_affinity_string_text:
        row["raw_affinity_string"] = raw_affinity_string_text.replace("ÃŽâ€", "Î”")
    return row


def build_bindingdb_subset_measurements(
    zip_path: Path,
    accession_polymer_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    accession_by_polymer_id = {
        str(row.get("bindingdb_polymer_id")): str(row.get("accession"))
        for row in accession_polymer_rows
        if _non_empty_string(str(row.get("bindingdb_polymer_id") or ""))
    }
    target_polymer_ids = set(accession_by_polymer_id)
    if not target_polymer_ids:
        return []

    polymer_rows = iter_table_rows(zip_path, "polymer", POLYMER_FIELDS)
    polymer_lookup = {
        str(row.get("polymerid") or "").strip(): row
        for row in polymer_rows
        if _non_empty_string(row.get("polymerid"))
    }

    matched_reactants = []
    for row in iter_table_rows(zip_path, "enzyme_reactant_set", ENZYME_REACTANT_SET_FIELDS):
        matched_roles = []
        for role_key, role_name in (
            ("enzyme_polymerid", "enzyme"),
            ("inhibitor_polymerid", "inhibitor"),
            ("substrate_polymerid", "substrate"),
        ):
            polymer_id = str(row.get(role_key) or "").strip()
            if polymer_id in target_polymer_ids:
                matched_roles.append((polymer_id, role_name))
        if matched_roles:
            enriched_row = dict(row)
            enriched_row["_matched_roles"] = matched_roles
            matched_reactants.append(enriched_row)

    reactant_ids = {
        str(row.get("reactant_set_id") or "").strip()
        for row in matched_reactants
        if _non_empty_string(row.get("reactant_set_id"))
    }
    entry_ids = {
        str(row.get("entryid") or "").strip()
        for row in matched_reactants
        if _non_empty_string(row.get("entryid"))
    }
    ki_result_rows = [
        row
        for row in iter_table_rows(zip_path, "ki_result", KI_RESULT_FIELDS)
        if str(row.get("reactant_set_id") or "").strip() in reactant_ids
    ]
    entry_lookup = {
        str(row.get("entryid") or "").strip(): row
        for row in iter_table_rows(zip_path, "entry", ENTRY_FIELDS)
        if str(row.get("entryid") or "").strip() in entry_ids
    }
    assay_lookup = {
        (
            str(row.get("entryid") or "").strip(),
            str(row.get("assayid") or "").strip(),
        ): row
        for row in iter_table_rows(zip_path, "assay", ASSAY_FIELDS)
        if str(row.get("entryid") or "").strip() in entry_ids
    }
    monomer_ids = {
        str(row.get(key) or "").strip()
        for row in matched_reactants
        for key in ("inhibitor_monomerid", "substrate_monomerid", "enzyme_monomerid")
        if _non_empty_string(row.get(key))
    }
    complex_ids = {
        str(row.get(key) or "").strip()
        for row in matched_reactants
        for key in ("enzyme_complexid", "inhibitor_complexid", "substrate_complexid")
        if _non_empty_string(row.get(key))
    }
    monomer_lookup = {
        str(row.get("monomerid") or "").strip(): row
        for row in iter_table_rows(zip_path, "monomer", MONOMER_FIELDS)
        if str(row.get("monomerid") or "").strip() in monomer_ids
    }
    complex_lookup = {
        str(row.get("complexid") or "").strip(): row
        for row in iter_table_rows(zip_path, "complex", COMPLEX_FIELDS)
        if str(row.get("complexid") or "").strip() in complex_ids
    }

    reactant_lookup = {
        str(row.get("reactant_set_id") or "").strip(): row for row in matched_reactants
    }
    rows: list[dict[str, Any]] = []
    measurement_fields = (
        ("ki", "Ki"),
        ("kd", "Kd"),
        ("ic50", "IC50"),
        ("ec50", "EC50"),
        ("kon", "kon"),
        ("koff", "koff"),
        ("delta_g", "Î”G"),
    )
    for ki_result_row in ki_result_rows:
        reactant_row = reactant_lookup.get(str(ki_result_row.get("reactant_set_id") or "").strip())
        if reactant_row is None:
            continue
        entry_row = entry_lookup.get(str(ki_result_row.get("entryid") or "").strip())
        assay_row = assay_lookup.get(
            (
                str(ki_result_row.get("entryid") or "").strip(),
                str(ki_result_row.get("assayid") or "").strip(),
            )
        )
        for polymer_id, target_role in reactant_row.get("_matched_roles") or []:
            accession = accession_by_polymer_id.get(str(polymer_id))
            if not accession:
                continue
            for field_name, measurement_type in measurement_fields:
                raw_value = _non_empty_string(ki_result_row.get(field_name))
                if raw_value is None:
                    continue
                rows.append(
                    _build_bindingdb_measurement_row(
                        accession=accession,
                        polymer_id=str(polymer_id),
                        target_role=str(target_role),
                        reactant_row=reactant_row,
                        ki_result_row=ki_result_row,
                        entry_row=entry_row,
                        assay_row=assay_row,
                        polymer_lookup=polymer_lookup,
                        monomer_lookup=monomer_lookup,
                        complex_lookup=complex_lookup,
                        measurement_type=measurement_type,
                        raw_value=raw_value,
                    )
                )
    return rows



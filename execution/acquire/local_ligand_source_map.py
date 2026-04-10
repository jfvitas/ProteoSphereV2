from __future__ import annotations

import csv
import gzip
import json
import sqlite3
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from execution.materialization.local_bridge_ligand_backfill import (
    load_bound_object_rows,
    select_primary_small_molecule_candidate,
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _read_master_rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple(dict(row) for row in csv.DictReader(handle))


def _split_tokens(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        parts = value.replace(",", ";").split(";")
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        parts = []
        for item in value:
            parts.extend(str(item).replace(",", ";").split(";"))
    else:
        parts = str(value).replace(",", ";").split(";")
    return _dedupe(part for part in parts)


def _rows_for_accession(
    rows: Sequence[dict[str, str]],
    accession: str,
) -> tuple[dict[str, str], ...]:
    key = accession.casefold()
    matches: list[dict[str, str]] = []
    for row in rows:
        proteins = _split_tokens(row.get("protein_chain_uniprot_ids"))
        if any(token.casefold() == key for token in proteins):
            matches.append(dict(row))
    return tuple(matches)


def _biolip_pdb_ids(path: Path, accession: str) -> tuple[str, ...]:
    hits: list[str] = []
    key = accession.casefold()
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if key not in line.casefold():
                continue
            row = line.rstrip("\n").split("\t")
            if row:
                pdb_id = _clean_text(row[0]).upper()
                if pdb_id:
                    hits.append(pdb_id)
    return _dedupe(hits)


def _existing_structure_payloads(
    storage_root: Path,
    accession: str,
    pdb_ids: Sequence[str],
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for pdb_id in _dedupe(pdb_ids):
        row = {
            "pdb_id": pdb_id,
            "raw_json_path": str(storage_root / "data" / "raw" / "rcsb" / f"{pdb_id}.json"),
            "cif_path": str(storage_root / "data" / "structures" / "rcsb" / f"{pdb_id}.cif"),
            "entry_path": str(storage_root / "data" / "extracted" / "entry" / f"{pdb_id}.json"),
            "bound_objects_path": str(
                storage_root / "data" / "extracted" / "bound_objects" / f"{pdb_id}.json"
            ),
        }
        row["raw_json_exists"] = Path(row["raw_json_path"]).exists()
        row["cif_exists"] = Path(row["cif_path"]).exists()
        row["entry_exists"] = Path(row["entry_path"]).exists()
        row["bound_objects_exists"] = Path(row["bound_objects_path"]).exists()
        row["target_chain_ids"] = []
        row["chain_truthful_ligand_issue_codes"] = []
        row["chain_truthful_small_molecule"] = False
        if row["raw_json_exists"]:
            row["target_chain_ids"] = list(
                _target_chain_ids_from_raw_payload(
                    Path(row["raw_json_path"]),
                    accession=accession,
                )
            )
        if row["bound_objects_exists"]:
            candidate, issues = select_primary_small_molecule_candidate(
                load_bound_object_rows(Path(row["bound_objects_path"])),
                bridge_chain_ids=row["target_chain_ids"],
            )
            row["chain_truthful_small_molecule"] = candidate is not None
            row["chain_truthful_ligand_issue_codes"] = list(issues)
        row["actionable_structure_bridge"] = all(
            (
                row["raw_json_exists"],
                row["cif_exists"],
                row["entry_exists"],
                row["bound_objects_exists"],
                row["chain_truthful_small_molecule"],
            )
        )
        rows.append(row)
    return tuple(rows)


def _target_chain_ids_from_raw_payload(
    raw_payload_path: Path,
    *,
    accession: str,
) -> tuple[str, ...]:
    try:
        payload = json.loads(raw_payload_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return ()
    if not isinstance(payload, dict):
        return ()
    accession_key = _clean_text(accession).upper()
    chain_ids: list[str] = []
    for entity in payload.get("polymer_entities") or ():
        if not isinstance(entity, dict):
            continue
        identifiers = entity.get("rcsb_polymer_entity_container_identifiers")
        if not isinstance(identifiers, dict):
            continue
        uniprot_ids = {
            _clean_text(value).upper() for value in identifiers.get("uniprot_ids") or ()
        }
        if accession_key not in uniprot_ids:
            continue
        chain_ids.extend(_clean_text(value) for value in identifiers.get("auth_asym_ids") or ())
    return _dedupe(chain_ids)


def _query_chembl_targets(path: Path, accession: str) -> tuple[dict[str, Any], ...]:
    if not path.exists():
        return ()
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        tables = {
            row[0]
            for row in cur.execute(
                "select name from sqlite_master where type='table'"
            ).fetchall()
        }
        required = {
            "component_sequences",
            "target_components",
            "target_dictionary",
            "assays",
            "activities",
        }
        if not required.issubset(tables):
            return ()
        cur.execute(
            """
            select cs.accession, td.chembl_id, td.pref_name, count(distinct act.activity_id)
            from component_sequences cs
            join target_components tc on tc.component_id = cs.component_id
            join target_dictionary td on td.tid = tc.tid
            left join assays a on a.tid = td.tid
            left join activities act on act.assay_id = a.assay_id
            where cs.accession = ?
            group by cs.accession, td.chembl_id, td.pref_name
            order by count(distinct act.activity_id) desc, td.chembl_id
            """,
            (accession,),
        )
        return tuple(
            {
                "accession": row[0],
                "chembl_id": row[1],
                "pref_name": row[2],
                "activity_count": int(row[3] or 0),
            }
            for row in cur.fetchall()
        )
    except sqlite3.DatabaseError:
        return ()
    finally:
        conn.close()


def _bindingdb_index_hits(path: Path, accession: str) -> tuple[dict[str, Any], ...]:
    if not path.exists():
        return ()
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        tables = tuple(
            row[0]
            for row in cur.execute("select name from sqlite_master where type='table'").fetchall()
        )
        hits: list[dict[str, Any]] = []
        candidate_columns = {
            "uniprot_accession",
            "accession",
            "protein_accession",
            "target_accession",
            "target_unpid1",
            "target_unpid2",
            "unpid1",
            "unpid2",
        }
        for table in tables:
            columns = tuple(
                row[1] for row in cur.execute(f"pragma table_info({table})").fetchall()
            )
            matched_columns = tuple(
                value for value in columns if value.casefold() in candidate_columns
            )
            if not matched_columns:
                continue
            for column in matched_columns:
                try:
                    count = cur.execute(
                        f"select count(*) from {table} where {column} = ?",
                        (accession,),
                    ).fetchone()[0]
                except sqlite3.DatabaseError:
                    continue
                if count:
                    hits.append({"table": table, "column": column, "count": int(count)})
        return tuple(hits)
    finally:
        conn.close()


def _alphafold_hits(path: Path, accession: str) -> tuple[dict[str, Any], ...]:
    if not path.exists():
        return ()
    hits: list[dict[str, Any]] = []
    key = accession.casefold()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if _clean_text(record.get("accession")).casefold() != key:
                continue
            hits.append(
                {
                    "accession": _clean_text(record.get("accession")),
                    "entry_id": _clean_text(record.get("entry_id")),
                    "member_name": _clean_text(record.get("member_name")),
                    "model_version": _clean_text(record.get("model_version")),
                    "size_bytes": int(record.get("size_bytes") or 0),
                }
            )
    return tuple(hits)


def _classify_accession(
    *,
    structure_rows: Sequence[dict[str, Any]],
    chembl_hits: Sequence[dict[str, Any]],
    bindingdb_hits: Sequence[dict[str, Any]],
    alphafold_hits: Sequence[dict[str, Any]],
) -> tuple[str, str]:
    if any(row.get("actionable_structure_bridge") for row in structure_rows):
        return "structure_bridge_actionable", "ingest_local_structure_bridge"
    if bindingdb_hits:
        return "bulk_assay_actionable", "ingest_local_bulk_assay"
    if chembl_hits:
        return "bulk_assay_actionable", "extract_local_bulk_assay_first"
    if structure_rows:
        return "structure_bridge_backfill_needed", "backfill_local_structure_bridge"
    if alphafold_hits:
        return "structure_companion_only", "hold_for_ligand_acquisition"
    return "no_local_candidate", "fresh_acquisition_required"


def build_local_ligand_source_map(
    *,
    accessions: Sequence[str],
    storage_root: Path,
    master_pdb_repository_path: Path,
    biolip_path: Path,
    chembl_path: Path,
    bindingdb_index_path: Path,
    alphafold_index_path: Path,
) -> dict[str, Any]:
    master_rows = (
        _read_master_rows(master_pdb_repository_path)
        if master_pdb_repository_path.exists()
        else ()
    )
    entries: list[dict[str, Any]] = []

    for accession in _dedupe(accessions):
        master_hits = _rows_for_accession(master_rows, accession)
        master_pdb_ids = _dedupe(_clean_text(row.get("pdb_id")).upper() for row in master_hits)
        biolip_pdb_ids = _biolip_pdb_ids(biolip_path, accession) if biolip_path.exists() else ()
        structure_rows = _existing_structure_payloads(
            storage_root,
            accession,
            tuple(list(master_pdb_ids) + list(biolip_pdb_ids)),
        )
        chembl_hits = _query_chembl_targets(chembl_path, accession)
        bindingdb_hits = _bindingdb_index_hits(bindingdb_index_path, accession)
        alphafold_hits = _alphafold_hits(alphafold_index_path, accession)
        classification, next_action = _classify_accession(
            structure_rows=structure_rows,
            chembl_hits=chembl_hits,
            bindingdb_hits=bindingdb_hits,
            alphafold_hits=alphafold_hits,
        )
        entries.append(
            {
                "accession": accession,
                "classification": classification,
                "recommended_next_action": next_action,
                "master_repository_pdb_ids": list(master_pdb_ids),
                "biolip_pdb_ids": list(biolip_pdb_ids),
                "structure_rows": list(structure_rows),
                "chembl_hits": list(chembl_hits),
                "bindingdb_hits": list(bindingdb_hits),
                "alphafold_hits": list(alphafold_hits),
            }
        )

    return {
        "entry_count": len(entries),
        "entries": entries,
        "inputs": {
            "storage_root": str(storage_root),
            "master_pdb_repository_path": str(master_pdb_repository_path),
            "biolip_path": str(biolip_path),
            "chembl_path": str(chembl_path),
            "bindingdb_index_path": str(bindingdb_index_path),
            "alphafold_index_path": str(alphafold_index_path),
        },
    }


__all__ = ["build_local_ligand_source_map"]

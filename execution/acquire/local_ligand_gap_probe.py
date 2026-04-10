from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

DEFAULT_ACCESSIONS = ("P09105", "Q2TAC2", "Q9NZD4", "Q9UCM0")
RAW_SOURCE_NAMES = (
    "alphafold",
    "alphafold_local",
    "bindingdb",
    "bindingdb_dump_local",
    "rcsb_pdbe",
    "intact",
    "uniprot",
)


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


def _split_tokens(value: Any) -> tuple[str, ...]:
    tokens: list[str] = []
    for raw_value in _iter_values(value):
        for part in str(raw_value).replace(",", ";").split(";"):
            text = _clean_text(part)
            if text:
                tokens.append(text)
    return _dedupe_text(tokens)


def _normalize_accessions(values: Sequence[str] | None) -> tuple[str, ...]:
    if values is None:
        return DEFAULT_ACCESSIONS
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value).upper()
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _resolve_path(value: Any, *, storage_root: Path) -> Path | None:
    text = _clean_text(value)
    if not text:
        return None
    path = Path(text)
    if not path.is_absolute():
        path = storage_root / path
    return path


def _load_registry_sources(local_registry_summary: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    imported_sources = local_registry_summary.get("imported_sources") or ()
    if not isinstance(imported_sources, Sequence) or isinstance(imported_sources, (str, bytes)):
        return ()
    return tuple(dict(item) for item in imported_sources if isinstance(item, Mapping))


def _source_status_map(local_registry_summary: Mapping[str, Any]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for source in _load_registry_sources(local_registry_summary):
        source_name = _clean_text(source.get("source_name"))
        status = _clean_text(source.get("status")) or "unknown"
        if source_name:
            statuses[source_name] = status
    return statuses


def _find_accession_files(raw_root: Path, source_name: str, accession: str) -> tuple[str, ...]:
    source_root = raw_root / source_name
    if not source_root.exists():
        return ()
    accession_key = accession.casefold()
    hits: list[str] = []
    for path in source_root.rglob("*"):
        if path.is_file() and accession_key in str(path).casefold():
            hits.append(str(path))
    return _dedupe_text(hits)


def _bindingdb_summary(paths: Sequence[str]) -> dict[str, Any]:
    summary = {
        "paths": list(paths),
        "path_count": len(paths),
        "state": "missing",
        "entry_count": 0,
        "assay_count": 0,
        "measurement_result_count": 0,
        "assay_row_count": 0,
    }
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            continue
        try:
            payload = _read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        entry_count = int(payload.get("entry_count") or len(payload.get("entries") or ()))
        assay_count = int(payload.get("assay_count") or len(payload.get("assays") or ()))
        measurement_count = int(
            payload.get("measurement_result_count")
            or len(payload.get("measurement_results") or ())
        )
        assay_row_count = int(
            payload.get("assay_row_count") or len(payload.get("assay_rows") or ())
        )
        summary["entry_count"] = max(summary["entry_count"], entry_count)
        summary["assay_count"] = max(summary["assay_count"], assay_count)
        summary["measurement_result_count"] = max(
            summary["measurement_result_count"],
            measurement_count,
        )
        summary["assay_row_count"] = max(summary["assay_row_count"], assay_row_count)
    if any(
        summary[key] > 0
        for key in ("entry_count", "assay_count", "measurement_result_count", "assay_row_count")
    ):
        summary["state"] = "positive"
    elif summary["path_count"] > 0:
        summary["state"] = "empty"
    return summary


def _rcsb_pdbe_summary(paths: Sequence[str]) -> dict[str, Any]:
    summary = {
        "paths": list(paths),
        "path_count": len(paths),
        "state": "missing",
        "best_structure_count": 0,
        "pdb_ids": [],
    }
    pdb_ids: list[str] = []
    best_structure_count = 0
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            continue
        try:
            payload = _read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, list):
            best_structure_count += len(payload)
            for item in payload:
                if not isinstance(item, Mapping):
                    continue
                pdb_id = _clean_text(item.get("pdb_id")).upper()
                if pdb_id:
                    pdb_ids.append(pdb_id)
        elif isinstance(payload, dict):
            for value in payload.values():
                if isinstance(value, list):
                    best_structure_count += len(value)
                    for item in value:
                        if not isinstance(item, Mapping):
                            continue
                        pdb_id = _clean_text(item.get("pdb_id")).upper()
                        if pdb_id:
                            pdb_ids.append(pdb_id)
    summary["best_structure_count"] = best_structure_count
    summary["pdb_ids"] = list(_dedupe_text(pdb_ids))
    if best_structure_count > 0:
        summary["state"] = "positive"
    elif summary["path_count"] > 0:
        summary["state"] = "empty"
    return summary


def _alphafold_summary(paths: Sequence[str]) -> dict[str, Any]:
    summary = {
        "paths": list(paths),
        "path_count": len(paths),
        "state": "missing",
        "entry_ids": [],
        "model_entity_ids": [],
        "accessions": [],
    }
    entry_ids: list[str] = []
    model_entity_ids: list[str] = []
    accessions: list[str] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            continue
        if path.name.casefold().endswith(".json"):
            try:
                payload = _read_json(path)
            except (OSError, json.JSONDecodeError):
                continue
            records = payload if isinstance(payload, list) else [payload]
            for record in records:
                if not isinstance(record, Mapping):
                    continue
                entry_id = _clean_text(record.get("entryId") or record.get("entry_id"))
                model_entity_id = _clean_text(
                    record.get("modelEntityId") or record.get("model_entity_id")
                )
                accession = _clean_text(
                    record.get("uniprotAccession") or record.get("accession")
                ).upper()
                if entry_id:
                    entry_ids.append(entry_id)
                if model_entity_id:
                    model_entity_ids.append(model_entity_id)
                if accession:
                    accessions.append(accession)
        else:
            stem = path.name
            if stem.endswith(".gz"):
                stem = stem[:-3]
            if stem:
                entry_ids.append(stem)
    summary["entry_ids"] = list(_dedupe_text(entry_ids))
    summary["model_entity_ids"] = list(_dedupe_text(model_entity_ids))
    summary["accessions"] = list(_dedupe_text(accessions))
    if summary["path_count"] > 0:
        summary["state"] = "present"
    return summary


def _master_repository_rows(
    *,
    storage_root: Path,
    master_pdb_repository_path: Path | None,
) -> tuple[dict[str, str], ...]:
    if master_pdb_repository_path is not None:
        path = master_pdb_repository_path
    else:
        path = storage_root / "master_pdb_repository.csv"
    if not path.exists():
        return ()
    return _read_csv_rows(path)


def _rows_for_accession(
    rows: Sequence[Mapping[str, str]],
    accession: str,
) -> tuple[dict[str, str], ...]:
    matches: list[dict[str, str]] = []
    accession_key = accession.casefold()
    for row in rows:
        proteins = _split_tokens(row.get("protein_chain_uniprot_ids"))
        if any(token.casefold() == accession_key for token in proteins):
            matches.append(dict(row))
    return tuple(matches)


def _structure_bridge_summary(
    *,
    storage_root: Path,
    accession: str,
    master_rows: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    candidate_pdb_ids: list[str] = []
    concrete_paths: list[str] = []
    for row in _rows_for_accession(master_rows, accession):
        pdb_id = _clean_text(row.get("pdb_id")).upper()
        if not pdb_id:
            continue
        row_cif = _resolve_path(row.get("structure_file_cif_path"), storage_root=storage_root)
        row_raw = _resolve_path(row.get("raw_file_path"), storage_root=storage_root)
        row_entry = storage_root / "data" / "extracted" / "entry" / f"{pdb_id}.json"
        row_bound = storage_root / "data" / "extracted" / "bound_objects" / f"{pdb_id}.json"
        present_paths = [
            str(path)
            for path in (row_cif, row_raw, row_entry, row_bound)
            if path is not None and path.exists()
        ]
        candidate_pdb_ids.append(pdb_id)
        concrete_paths.extend(present_paths)
        rows.append(
            {
                "pdb_id": pdb_id,
                "category": _clean_text(row.get("category")),
                "resolution": _clean_text(row.get("resolution")),
                "protein_chain_uniprot_ids": _clean_text(row.get("protein_chain_uniprot_ids")),
                "structure_file_cif_path": str(row_cif) if row_cif is not None else "",
                "raw_file_path": str(row_raw) if row_raw is not None else "",
                "present_artifacts": present_paths,
            }
        )

    best_row = next(
        (
            row
            for row in rows
            if row["category"].casefold() == "protein_ligand" and row["present_artifacts"]
        ),
        next((row for row in rows if row["present_artifacts"]), {}),
    )
    best_source_path = _clean_text(best_row.get("structure_file_cif_path")) or _clean_text(
        best_row.get("raw_file_path")
    )
    if not best_source_path and concrete_paths:
        best_source_path = concrete_paths[0]
    return {
        "matched_pdb_ids": list(_dedupe_text(candidate_pdb_ids)),
        "concrete_paths": list(_dedupe_text(concrete_paths)),
        "rows": rows,
        "best_pdb_id": _clean_text(best_row.get("pdb_id")),
        "best_source_path": best_source_path,
        "state": "ready_now" if concrete_paths else "bridge_only",
    }


def _secondary_context(
    *,
    raw_root: Path,
    accession: str,
) -> dict[str, Any]:
    intact_paths = _find_accession_files(raw_root, "intact", accession)
    uniprot_paths = _find_accession_files(raw_root, "uniprot", accession)

    intact_count = 0
    if intact_paths:
        for raw_path in intact_paths:
            path = Path(raw_path)
            if not path.exists():
                continue
            try:
                payload = _read_json(path)
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                content = payload.get("content")
                if isinstance(content, list):
                    intact_count = max(intact_count, len(content))
                if isinstance(payload.get("totalElements"), int):
                    intact_count = max(intact_count, int(payload.get("totalElements") or 0))

    return {
        "intact_paths": list(intact_paths),
        "intact_interactor_count": intact_count,
        "uniprot_paths": list(uniprot_paths),
        "uniprot_present": bool(uniprot_paths),
    }


def _build_accession_record(
    *,
    accession: str,
    storage_root: Path,
    raw_root: Path,
    registry_source_statuses: Mapping[str, str],
    master_rows: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    source_paths = {
        source_name: _find_accession_files(raw_root, source_name, accession)
        for source_name in RAW_SOURCE_NAMES
    }
    bridge = _structure_bridge_summary(
        storage_root=storage_root,
        accession=accession,
        master_rows=master_rows,
    )
    alphafold = _alphafold_summary(source_paths["alphafold"] + source_paths["alphafold_local"])
    bindingdb = _bindingdb_summary(source_paths["bindingdb"] + source_paths["bindingdb_dump_local"])
    rcsb_pdbe = _rcsb_pdbe_summary(source_paths["rcsb_pdbe"])
    secondary_context = _secondary_context(raw_root=raw_root, accession=accession)

    if bridge["state"] == "ready_now" and bridge["concrete_paths"]:
        classification = "rescuable_now"
        best_next_source = bridge["best_source_path"] or bridge["concrete_paths"][0]
        best_next_action = (
            f"Ingest the local structure bridge for {accession} using {bridge['best_pdb_id']}"
            if bridge["best_pdb_id"]
            else f"Ingest the local structure bridge for {accession}"
        )
        rationale = (
            "A concrete local bridge exists in the master PDB repository and local "
            "structure files."
        )
    elif alphafold["path_count"] > 0:
        classification = "requires_extraction"
        best_next_source = (
            source_paths["alphafold_local"][0]
            if source_paths["alphafold_local"]
            else source_paths["alphafold"][0]
        )
        best_next_action = (
            f"Extract the AlphaFold raw model for {accession} into a reusable structure companion"
        )
        rationale = (
            "AlphaFold raw material is present, but no concrete local ligand rescue or "
            "structure bridge is available yet."
        )
    elif bindingdb["state"] == "positive":
        classification = "requires_extraction"
        best_next_source = bindingdb["paths"][0]
        best_next_action = f"Extract the BindingDB raw ligand evidence for {accession}"
        rationale = "BindingDB contains non-empty raw ligand evidence that still needs extraction."
    elif rcsb_pdbe["state"] == "positive":
        classification = "requires_extraction"
        best_next_source = rcsb_pdbe["paths"][0]
        best_next_action = f"Extract the RCSB-PDBe raw structure hits for {accession}"
        rationale = (
            "RCSB-PDBe contains non-empty raw structure evidence that still needs "
            "extraction."
        )
    else:
        classification = "not_found"
        best_next_source = ""
        best_next_action = (
            f"Fresh acquisition required for {accession}; no truthful local ligand "
            "rescue candidate was found"
        )
        rationale = (
            "No concrete ligand-bearing local source or extractable raw companion was found."
        )

    return {
        "accession": accession,
        "classification": classification,
        "best_next_source": best_next_source,
        "best_next_action": best_next_action,
        "rationale": rationale,
        "registry_source_statuses": dict(sorted(registry_source_statuses.items())),
        "evidence": {
            "structure_bridge": bridge,
            "alphafold_raw": alphafold,
            "bindingdb_raw": bindingdb,
            "rcsb_pdbe_raw": rcsb_pdbe,
            "secondary_context": secondary_context,
            "raw_source_paths": {
                source_name: list(paths) for source_name, paths in source_paths.items() if paths
            },
        },
    }


def probe_local_ligand_gap_candidates(
    *,
    accessions: Sequence[str] | None = None,
    local_registry_summary: Mapping[str, Any],
    storage_root: str | Path,
    raw_root: str | Path,
    master_pdb_repository_path: str | Path | None = None,
) -> dict[str, Any]:
    selected_accessions = _normalize_accessions(accessions)
    resolved_storage_root = Path(storage_root)
    resolved_raw_root = Path(raw_root)
    resolved_master_path = (
        Path(master_pdb_repository_path)
        if master_pdb_repository_path is not None
        else None
    )
    registry_source_statuses = _source_status_map(local_registry_summary)
    master_rows = _master_repository_rows(
        storage_root=resolved_storage_root,
        master_pdb_repository_path=resolved_master_path,
    )
    entries = [
        _build_accession_record(
            accession=accession,
            storage_root=resolved_storage_root,
            raw_root=resolved_raw_root,
            registry_source_statuses=registry_source_statuses,
            master_rows=master_rows,
        )
        for accession in selected_accessions
    ]
    classification_counts = {
        "rescuable_now": sum(1 for entry in entries if entry["classification"] == "rescuable_now"),
        "requires_extraction": sum(
            1 for entry in entries if entry["classification"] == "requires_extraction"
        ),
        "not_found": sum(1 for entry in entries if entry["classification"] == "not_found"),
    }
    return {
        "selected_accessions": list(selected_accessions),
        "entry_count": len(entries),
        "classification_counts": classification_counts,
        "registry_source_count": len(registry_source_statuses),
        "registered_sources": [
            {"source_name": source_name, "status": status}
            for source_name, status in sorted(registry_source_statuses.items())
        ],
        "entries": entries,
    }


__all__ = ["DEFAULT_ACCESSIONS", "probe_local_ligand_gap_candidates"]

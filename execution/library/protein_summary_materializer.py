from __future__ import annotations

import csv
import gzip
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import replace
from functools import cache
from pathlib import Path
from typing import Any

from core.canonical.protein import CanonicalProtein
from core.library.summary_record import (
    ProteinSummaryRecord,
    SummaryCrossSourceView,
    SummaryLibrarySchema,
    SummaryProvenancePointer,
    SummaryRecordContext,
    SummaryReference,
    SummarySourceClaim,
    SummarySourceConnection,
    SummarySourceRollup,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CANONICAL_LATEST_PATH = ROOT / "data" / "canonical" / "LATEST.json"
DEFAULT_REACTOME_SUMMARY_PATH = (
    ROOT / "artifacts" / "status" / "reactome_local_summary_library.json"
)
DEFAULT_INTACT_SUMMARY_PATH = (
    ROOT / "artifacts" / "status" / "intact_local_summary_library.json"
)
DEFAULT_LOCAL_REGISTRY_SUMMARY_PATH = ROOT / "data" / "raw" / "local_registry_runs" / "LATEST.json"
DEFAULT_SIFTS_ROOT = ROOT / "data" / "raw" / "protein_data_scope_seed" / "sifts"
DEFAULT_CATH_DOMAIN_LIST_PATH = (
    ROOT / "data" / "raw" / "local_copies" / "cath" / "cath-domain-list.txt"
)
DEFAULT_CATH_SUPERFAMILY_LIST_PATH = (
    ROOT / "data" / "raw" / "local_copies" / "cath" / "cath-superfamily-list.txt"
)
DEFAULT_SCOPE_CLA_PATH = (
    ROOT / "data" / "raw" / "local_copies" / "scope" / "dir.cla.scope.2.08-stable.txt"
)
DEFAULT_SCOPE_DES_PATH = ROOT / "data" / "raw" / "local_copies" / "scope" / "dir.des.scope.txt"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "status" / "protein_summary_library.json"
DEFAULT_LIBRARY_ID = "summary-library:protein-materialized:v1"
_SCALAR_CONSENSUS_SOURCE_ORDER = ("UniProt", "Reactome", "IntAct")
_SCALAR_CONSENSUS_FIELDS = (
    ("protein_name", "identity"),
    ("organism_name", "identity"),
    ("taxon_id", "identity"),
    ("sequence_checksum", "sequence"),
    ("sequence_version", "sequence"),
    ("sequence_length", "sequence"),
    ("gene_names", "identity"),
    ("aliases", "identity"),
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _optional_text(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _json_ready_scalar(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_ready_scalar(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready_scalar(item) for item in value]
    if isinstance(value, list):
        return [_json_ready_scalar(item) for item in value]
    return value


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Iterable):
        return tuple(values)
    return (values,)


def _dedupe_text(values: Iterable[Any]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _dedupe_provenance_pointers(
    pointers: Iterable[SummaryProvenancePointer],
) -> tuple[SummaryProvenancePointer, ...]:
    ordered: dict[
        tuple[str, str | None, str | None, str | None, str | None],
        SummaryProvenancePointer,
    ] = {}
    for pointer in pointers:
        key = (
            pointer.source_name.casefold(),
            pointer.source_record_id.casefold() if pointer.source_record_id else None,
            pointer.release_version,
            pointer.release_date,
            pointer.checksum,
        )
        ordered.setdefault(key, pointer)
    return tuple(ordered.values())


def _dedupe_references(references: Iterable[SummaryReference]) -> tuple[SummaryReference, ...]:
    ordered: dict[
        tuple[str, str, str, str | None, int | None, int | None],
        SummaryReference,
    ] = {}
    for reference in references:
        key = (
            reference.reference_kind,
            reference.namespace.casefold(),
            reference.identifier.casefold(),
            reference.source_record_id.casefold() if reference.source_record_id else None,
            reference.span_start,
            reference.span_end,
        )
        ordered.setdefault(key, reference)
    return tuple(ordered.values())


def _dedupe_connections(
    connections: Iterable[SummarySourceConnection],
) -> tuple[SummarySourceConnection, ...]:
    ordered: dict[
        tuple[
            str,
            tuple[str, ...],
            tuple[str, ...],
            tuple[str, ...],
            tuple[str, ...],
            str | None,
            str,
            str,
        ],
        SummarySourceConnection,
    ] = {}
    for connection in connections:
        key = (
            connection.connection_kind,
            connection.source_names,
            connection.direct_sources,
            connection.indirect_sources,
            connection.bridge_ids,
            connection.bridge_source,
            connection.join_mode,
            connection.join_status,
        )
        ordered.setdefault(key, connection)
    return tuple(ordered.values())


def _cross_source_view(
    connections: Iterable[SummarySourceConnection],
) -> SummaryCrossSourceView | None:
    view = SummaryCrossSourceView.from_connections(connections)
    if not (view.direct_joins or view.indirect_bridges or view.partial_joins):
        return None
    return view


def _registry_summary(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    payload = _read_json(path)
    imported_sources = payload.get("imported_sources") or ()
    if not isinstance(imported_sources, Iterable):
        return {}
    statuses: dict[str, str] = {}
    join_keys: dict[str, tuple[str, ...]] = {}
    for item in _iter_values(imported_sources):
        if not isinstance(item, Mapping):
            continue
        source_name = _clean_text(item.get("source_name")).casefold()
        if not source_name:
            continue
        statuses[source_name] = _clean_text(item.get("status"))
        join_keys[source_name] = _dedupe_text(item.get("join_keys") or ())
    return {
        "registry_id": _optional_text(payload.get("registry_id")),
        "manifest_id": _optional_text(payload.get("manifest_id")),
        "generated_at": _optional_text(payload.get("generated_at")),
        "statuses": statuses,
        "join_keys": join_keys,
    }


def _clean_xref_properties(properties: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in _iter_values(properties):
        if not isinstance(item, Mapping):
            continue
        key = _clean_text(item.get("key"))
        value = _clean_text(item.get("value"))
        if key and value:
            result[key.casefold()] = value
    return result


def _xref_label(xref: Mapping[str, Any]) -> str:
    properties = _clean_xref_properties(xref.get("properties"))
    for key in ("entryname", "description", "name"):
        value = properties.get(key)
        if value and value != "-":
            return value
    return ""


def _protein_pdb_ids(raw_payload: Mapping[str, Any]) -> tuple[str, ...]:
    pdb_ids: dict[str, str] = {}
    for xref in _iter_values(raw_payload.get("uniProtKBCrossReferences") or ()):
        if not isinstance(xref, Mapping):
            continue
        if _clean_text(xref.get("database")).casefold() != "pdb":
            continue
        pdb_id = _clean_text(xref.get("id")).upper()
        if pdb_id:
            pdb_ids.setdefault(pdb_id, pdb_id)
    return tuple(pdb_ids.values())


def _iter_tsv_rows(path: Path) -> Iterable[dict[str, str]]:
    if not path.exists():
        return ()
    rows: list[dict[str, str]] = []
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        header: list[str] | None = None
        for line in handle:
            if line.startswith("#") or not line.strip():
                continue
            header = line.rstrip("\n").split("\t")
            break
        if header is None:
            return ()
        reader = csv.DictReader(handle, fieldnames=header, delimiter="\t")
        for row in reader:
            if row and any(value for value in row.values()):
                rows.append({str(key): str(value or "") for key, value in row.items()})
    return rows


@cache
def _cath_domain_class_map(path_text: str) -> dict[str, str]:
    path = Path(path_text)
    mapping: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 5:
            mapping[parts[0].strip().casefold()] = ".".join(parts[1:5])
    return mapping


@cache
def _cath_class_label_map(path_text: str) -> dict[str, str]:
    path = Path(path_text)
    labels: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 4:
            labels[parts[0].strip().casefold()] = parts[3].strip().lstrip(":")
    return labels


@cache
def _scope_class_map(path_text: str) -> dict[str, str]:
    path = Path(path_text)
    mapping: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 4 and parts[0]:
            mapping[parts[0].strip().casefold()] = parts[3].strip()
    return mapping


@cache
def _scope_label_map(path_text: str) -> dict[str, str]:
    path = Path(path_text)
    labels: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 5:
            scoped_id = parts[2].strip().casefold()
            label = parts[4].strip()
            if scoped_id and label and label != "-":
                labels[scoped_id] = label
    return labels


def _sifts_rows_by_pdb_and_accession(
    path: Path,
    accession: str,
    pdb_ids: set[str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not path.exists():
        return rows
    accession_upper = accession.upper()
    pdb_id_set = {pdb_id.upper() for pdb_id in pdb_ids}
    for row in _iter_tsv_rows(path):
        if _clean_text(row.get("SP_PRIMARY")).upper() != accession_upper:
            continue
        pdb_id = _clean_text(row.get("PDB")).upper()
        if pdb_id in pdb_id_set:
            rows.append(row)
    return rows


def _annotation_lane_notes(
    *,
    registry_statuses: Mapping[str, str],
    protein_pdb_ids: tuple[str, ...],
    joined_lanes: Mapping[str, int],
    partial_lanes: Iterable[str] = (),
) -> tuple[str, ...]:
    notes: list[str] = []
    if protein_pdb_ids:
        notes.append("protein_pdb_ids:" + "|".join(protein_pdb_ids))
    for lane_name in ("interpro", "pfam", "prosite", "elm", "cath", "scope"):
        status = _clean_text(registry_statuses.get(lane_name, "missing")).casefold() or "missing"
        joined_count = joined_lanes.get(lane_name, 0)
        notes.append(f"registry_lane:{lane_name}={status}")
        if joined_count:
            notes.append(f"joined_lane:{lane_name}={joined_count}")
    for lane_name in partial_lanes:
        notes.append(f"partial_lane:{lane_name}")
    return _dedupe_text(notes)


def _extract_source_references(
    raw_payload: Mapping[str, Any],
    *,
    accession: str,
    registry_summary: Mapping[str, Any] | None = None,
) -> tuple[
    tuple[SummaryReference, ...],
    tuple[SummaryReference, ...],
    tuple[SummarySourceConnection, ...],
    tuple[str, ...],
    dict[str, int],
]:
    domain_references: list[SummaryReference] = []
    motif_references: list[SummaryReference] = []
    connections: list[SummarySourceConnection] = []
    lane_counts: dict[str, int] = {
        "interpro": 0,
        "pfam": 0,
        "prosite": 0,
        "elm": 0,
        "cath": 0,
        "scope": 0,
    }
    lane_bridge_ids: dict[str, list[str]] = {
        "interpro": [],
        "pfam": [],
        "prosite": [],
    }
    elm_bridge_ids: list[str] = []
    registry_statuses = (registry_summary or {}).get("statuses") or {}
    partial_lanes: list[str] = []

    for xref in _iter_values(raw_payload.get("uniProtKBCrossReferences") or ()):
        if not isinstance(xref, Mapping):
            continue
        database = _clean_text(xref.get("database"))
        identifier = _clean_text(xref.get("id"))
        if not database or not identifier:
            continue
        label = _xref_label(xref)
        properties = _clean_xref_properties(xref.get("properties"))
        if database.casefold() == "interpro":
            lane_counts["interpro"] += 1
            lane_bridge_ids["interpro"].append(identifier)
            domain_references.append(
                SummaryReference(
                    reference_kind="domain",
                    namespace="InterPro",
                    identifier=identifier,
                    label=label,
                    join_status="joined",
                    source_name="InterPro",
                    source_record_id=identifier,
                    notes=(
                        f"captured_from:UniProt:{accession}",
                        *(
                            f"{key}:{value}"
                            for key, value in properties.items()
                            if key in {"entryname", "matchstatus"}
                        ),
                    ),
                )
            )
        elif database.casefold() == "pfam":
            lane_counts["pfam"] += 1
            lane_bridge_ids["pfam"].append(identifier)
            domain_references.append(
                SummaryReference(
                    reference_kind="domain",
                    namespace="Pfam",
                    identifier=identifier,
                    label=label,
                    join_status="joined",
                    source_name="Pfam",
                    source_record_id=identifier,
                    notes=(
                        f"captured_from:UniProt:{accession}",
                        *(
                            f"{key}:{value}"
                            for key, value in properties.items()
                            if key in {"entryname", "matchstatus"}
                        ),
                    ),
                )
            )
        elif database.casefold() == "prosite":
            lane_counts["prosite"] += 1
            lane_bridge_ids["prosite"].append(identifier)
            motif_references.append(
                SummaryReference(
                    reference_kind="motif",
                    namespace="PROSITE",
                    identifier=identifier,
                    label=label,
                    join_status="joined",
                    source_name="PROSITE",
                    source_record_id=identifier,
                    notes=(
                        f"captured_from:UniProt:{accession}",
                        *(
                            f"{key}:{value}"
                            for key, value in properties.items()
                            if key in {"entryname", "matchstatus"}
                        ),
                    ),
                )
            )
        elif database.casefold() == "elm":
            lane_counts["elm"] += 1
            if identifier.casefold().startswith("elme"):
                elm_bridge_ids.append(identifier)
                motif_references.append(
                    SummaryReference(
                        reference_kind="motif",
                        namespace="ELM",
                        identifier=identifier,
                        label=label,
                        join_status="joined",
                        source_name="ELM",
                        source_record_id=identifier,
                        notes=(f"captured_from:UniProt:{accession}",),
                    )
                )
            else:
                partial_lanes.append("elm")
        elif database.casefold() == "pdb":
            continue

    for lane_name, source_name, bridge_kind in (
        ("interpro", "InterPro", "domain"),
        ("pfam", "Pfam", "domain"),
        ("prosite", "PROSITE", "motif"),
    ):
        bridge_ids = tuple(lane_bridge_ids[lane_name])
        if bridge_ids:
            connections.append(
                SummarySourceConnection(
                    connection_kind=bridge_kind,
                    source_names=("UniProt", source_name),
                    direct_sources=("UniProt", source_name),
                    bridge_ids=bridge_ids,
                    bridge_source="UniProt xref",
                    join_mode="direct",
                    join_status="joined",
                    notes=(f"captured_from:UniProt:{accession}",),
                )
            )

    elm_status = _clean_text(registry_statuses.get("elm")).casefold()
    if elm_bridge_ids:
        connections.append(
            SummarySourceConnection(
                connection_kind="motif",
                source_names=("UniProt", "ELM"),
                direct_sources=("UniProt", "ELM"),
                bridge_ids=tuple(elm_bridge_ids),
                bridge_source="UniProt xref",
                join_mode="direct",
                join_status="joined",
                notes=(f"captured_from:UniProt:{accession}",),
            )
        )
    elif elm_status in {"present", "partial"} or lane_counts["elm"] > 0 or "elm" in partial_lanes:
        connections.append(
            SummarySourceConnection(
                connection_kind="motif",
                source_names=("UniProt", "ELM"),
                direct_sources=("UniProt",),
                bridge_ids=("registry:elm",),
                bridge_source="local_registry_runs/LATEST.json",
                join_mode="partial",
                join_status="partial",
                notes=(
                    f"captured_from:UniProt:{accession}",
                    "no accession-scoped ELM join available in current artifacts",
                ),
            )
        )

    return (
        tuple(_dedupe_references(domain_references)),
        tuple(_dedupe_references(motif_references)),
        tuple(_dedupe_connections(connections)),
        tuple(sorted(set(partial_lanes))),
        lane_counts,
    )


def _extract_classification_references(
    *,
    accession: str,
    raw_payload: Mapping[str, Any],
    registry_summary: Mapping[str, Any],
) -> tuple[
    tuple[SummaryReference, ...],
    tuple[SummarySourceConnection, ...],
    tuple[str, ...],
    dict[str, int],
]:
    protein_pdb_ids = set(_protein_pdb_ids(raw_payload))
    registry_join_keys = registry_summary.get("join_keys") or {}
    registry_statuses = registry_summary.get("statuses") or {}
    cath_pdb_ids = {
        pdb_id.upper()
        for pdb_id in _iter_values(registry_join_keys.get("cath") or ())
        if _clean_text(pdb_id)
    }
    scope_pdb_ids = {
        pdb_id.upper()
        for pdb_id in _iter_values(registry_join_keys.get("scope") or ())
        if _clean_text(pdb_id)
    }
    eligible_cath_pdbs = protein_pdb_ids & cath_pdb_ids
    eligible_scope_pdbs = protein_pdb_ids & scope_pdb_ids
    classification_references: list[SummaryReference] = []
    connections: list[SummarySourceConnection] = []
    lane_counts: dict[str, int] = {"cath": 0, "scope": 0}
    partial_lanes: list[str] = []

    if eligible_cath_pdbs:
        uniprot_rows = _sifts_rows_by_pdb_and_accession(
            DEFAULT_SIFTS_ROOT / "pdb_chain_uniprot.tsv.gz",
            accession,
            eligible_cath_pdbs,
        )
        cath_rows = _sifts_rows_by_pdb_and_accession(
            DEFAULT_SIFTS_ROOT / "pdb_chain_cath_uniprot.tsv.gz",
            accession,
            eligible_cath_pdbs,
        )
        uniprot_by_key = {
            (_clean_text(row.get("PDB")).upper(), _clean_text(row.get("CHAIN")).upper()): row
            for row in uniprot_rows
        }
        cath_by_key = {
            (_clean_text(row.get("PDB")).upper(), _clean_text(row.get("CHAIN")).upper()): row
            for row in cath_rows
        }
        cath_domain_map = _cath_domain_class_map(str(DEFAULT_CATH_DOMAIN_LIST_PATH))
        cath_label_map = _cath_class_label_map(str(DEFAULT_CATH_SUPERFAMILY_LIST_PATH))
        for key in sorted(set(uniprot_by_key) & set(cath_by_key)):
            pdb_id, chain = key
            uniprot_row = uniprot_by_key[key]
            cath_row = cath_by_key[key]
            domain_id = _clean_text(cath_row.get("CATH_ID"))
            if not domain_id:
                continue
            class_id = cath_domain_map.get(domain_id.casefold(), "")
            if not class_id:
                continue
            class_label = cath_label_map.get(class_id.casefold(), "")
            span_start = _clean_text(uniprot_row.get("SP_BEG"))
            span_end = _clean_text(uniprot_row.get("SP_END"))
            lane_counts["cath"] += 1
            classification_references.append(
                SummaryReference(
                    reference_kind="domain",
                    namespace="CATH",
                    identifier=class_id,
                    label=class_label,
                    join_status="joined",
                    source_name="SIFTS",
                    source_record_id=domain_id,
                    span_start=(
                        int(span_start)
                        if span_start and span_start.casefold() != "none"
                        else None
                    ),
                    span_end=(
                        int(span_end)
                        if span_end and span_end.casefold() != "none"
                        else None
                    ),
                    evidence_refs=(f"SIFTS:{pdb_id}:{chain}:{domain_id}",),
                    notes=(
                        "captured_from:local_copies/cath",
                        f"pdb_id:{pdb_id}",
                        f"chain:{chain}",
                        f"entry_span:{span_start}-{span_end}",
                        f"domain_id:{domain_id}",
                    ),
                )
            )
            connections.append(
                SummarySourceConnection(
                    connection_kind="structure",
                    source_names=("UniProt", "CATH"),
                    direct_sources=("UniProt", "SIFTS"),
                    indirect_sources=("CATH",),
                    bridge_ids=(
                        f"PDB:{pdb_id}",
                        f"CHAIN:{chain}",
                        f"SIFTS:{domain_id}",
                        f"CATH:{class_id}",
                    ),
                    bridge_source="SIFTS",
                    join_mode="indirect",
                    join_status="joined",
                    notes=(
                        "captured_from:local_copies/cath",
                        f"entry_span:{span_start}-{span_end}",
                    ),
                )
            )
        cath_status = _clean_text(registry_statuses.get("cath")).casefold()
        cath_join_keys = set(registry_join_keys.get("cath") or ())
        if (
            lane_counts["cath"] == 0
            and protein_pdb_ids & cath_join_keys
            and cath_status in {"present", "partial"}
        ):
            partial_lanes.append("cath")

    if eligible_scope_pdbs:
        uniprot_rows = _sifts_rows_by_pdb_and_accession(
            DEFAULT_SIFTS_ROOT / "pdb_chain_uniprot.tsv.gz",
            accession,
            eligible_scope_pdbs,
        )
        scope_rows = _sifts_rows_by_pdb_and_accession(
            DEFAULT_SIFTS_ROOT / "pdb_chain_scop_uniprot.tsv.gz",
            accession,
            eligible_scope_pdbs,
        )
        uniprot_by_key = {
            (_clean_text(row.get("PDB")).upper(), _clean_text(row.get("CHAIN")).upper()): row
            for row in uniprot_rows
        }
        scope_by_key = {
            (_clean_text(row.get("PDB")).upper(), _clean_text(row.get("CHAIN")).upper()): row
            for row in scope_rows
        }
        scope_class_map = _scope_class_map(str(DEFAULT_SCOPE_CLA_PATH))
        scope_label_map = _scope_label_map(str(DEFAULT_SCOPE_DES_PATH))
        for key in sorted(set(uniprot_by_key) & set(scope_by_key)):
            pdb_id, chain = key
            uniprot_row = uniprot_by_key[key]
            scope_row = scope_by_key[key]
            scop_id = _clean_text(scope_row.get("SCOP_ID"))
            if not scop_id:
                continue
            class_id = scope_class_map.get(scop_id.casefold(), "")
            if not class_id:
                continue
            class_label = scope_label_map.get(class_id.casefold(), "")
            span_start = _clean_text(uniprot_row.get("SP_BEG"))
            span_end = _clean_text(uniprot_row.get("SP_END"))
            lane_counts["scope"] += 1
            classification_references.append(
                SummaryReference(
                    reference_kind="domain",
                    namespace="SCOPe",
                    identifier=class_id,
                    label=class_label,
                    join_status="joined",
                    source_name="SIFTS",
                    source_record_id=scop_id,
                    span_start=(
                        int(span_start)
                        if span_start and span_start.casefold() != "none"
                        else None
                    ),
                    span_end=(
                        int(span_end)
                        if span_end and span_end.casefold() != "none"
                        else None
                    ),
                    evidence_refs=(f"SIFTS:{pdb_id}:{chain}:{scop_id}",),
                    notes=(
                        "captured_from:local_copies/scope",
                        f"pdb_id:{pdb_id}",
                        f"chain:{chain}",
                        f"entry_span:{span_start}-{span_end}",
                        f"scop_id:{scop_id}",
                    ),
                )
            )
            connections.append(
                SummarySourceConnection(
                    connection_kind="structure",
                    source_names=("UniProt", "SCOPe"),
                    direct_sources=("UniProt", "SIFTS"),
                    indirect_sources=("SCOPe",),
                    bridge_ids=(
                        f"PDB:{pdb_id}",
                        f"CHAIN:{chain}",
                        f"SIFTS:{scop_id}",
                        f"SCOPe:{class_id}",
                    ),
                    bridge_source="SIFTS",
                    join_mode="indirect",
                    join_status="joined",
                    notes=(
                        "captured_from:local_copies/scope",
                        f"entry_span:{span_start}-{span_end}",
                    ),
                )
            )
        scope_status = _clean_text(registry_statuses.get("scope")).casefold()
        scope_join_keys = set(registry_join_keys.get("scope") or ())
        if (
            lane_counts["scope"] == 0
            and protein_pdb_ids & scope_join_keys
            and scope_status in {"present", "partial"}
        ):
            partial_lanes.append("scope")

    return (
        tuple(_dedupe_references(classification_references)),
        tuple(_dedupe_connections(connections)),
        tuple(sorted(set(partial_lanes))),
        lane_counts,
    )


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise TypeError(f"{path} must contain a JSON object")
    return dict(payload)


def _sequence_result(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    sequence_result = payload.get("sequence_result") or {}
    if not isinstance(sequence_result, Mapping):
        raise TypeError("canonical latest sequence_result must be a mapping")
    return sequence_result


def _source_release_manifest_id(sequence_result: Mapping[str, Any]) -> str | None:
    source_release = sequence_result.get("source_release") or {}
    if not isinstance(source_release, Mapping):
        return None
    return _optional_text(source_release.get("manifest_id") or source_release.get("id"))


def _canonical_record_map(sequence_result: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    records = sequence_result.get("records") or ()
    canonical_records: dict[str, dict[str, Any]] = {}
    for record in _iter_values(records):
        if not isinstance(record, Mapping):
            continue
        accession = _clean_text(record.get("accession")).upper()
        if accession:
            canonical_records[accession] = dict(record)
    return canonical_records


def _canonical_accession_order(sequence_result: Mapping[str, Any]) -> tuple[str, ...]:
    canonical_ids = sequence_result.get("canonical_ids") or ()
    if isinstance(canonical_ids, Iterable) and not isinstance(canonical_ids, (str, bytes)):
        accessions = [
            _protein_accession(item) or ""
            for item in canonical_ids
            if _protein_accession(item)
        ]
        if accessions:
            return _dedupe_text(accessions)
    accessions = []
    for record in _iter_values(sequence_result.get("records") or ()):
        if not isinstance(record, Mapping):
            continue
        accession = _clean_text(record.get("accession")).upper()
        if accession:
            accessions.append(accession)
    return _dedupe_text(accessions)


def _protein_accession(value: Any) -> str | None:
    text = _clean_text(value).upper()
    if not text:
        return None
    return text.split(":", 1)[1] if text.startswith("PROTEIN:") else text


def _canonical_summary_pointer(
    accession: str,
    record: Mapping[str, Any],
    sequence_result: Mapping[str, Any],
) -> SummaryProvenancePointer:
    provenance_record = record.get("provenance_record") or {}
    if not isinstance(provenance_record, Mapping):
        provenance_record = {}
    provenance_source = provenance_record.get("source") or {}
    if not isinstance(provenance_source, Mapping):
        provenance_source = {}
    source_release = (
        (provenance_record.get("metadata") or {}).get("source_release")
        or sequence_result.get("source_release")
        or {}
    )
    if not isinstance(source_release, Mapping):
        source_release = {}
    return SummaryProvenancePointer(
        provenance_id=_clean_text(
            provenance_record.get("provenance_id") or f"sequence:{accession}"
        ),
        source_name=_clean_text(provenance_source.get("source_name") or "UniProt"),
        source_record_id=_clean_text(record.get("source_id") or accession),
        release_version=_optional_text(
            provenance_source.get("release_version") or source_release.get("release_version")
        ),
        release_date=_optional_text(
            provenance_source.get("release_date") or source_release.get("release_date")
        ),
        acquired_at=_optional_text(provenance_record.get("acquired_at")),
        checksum=_optional_text(provenance_record.get("checksum")),
        join_status="joined",
        notes=(
            _optional_text(provenance_record.get("transformation_step")) or "canonical_sequence",
            f"source_kind:{_clean_text(record.get('source_kind') or record.get('source'))}",
        ),
    )


def _canonical_protein_from_record(
    record: Mapping[str, Any],
    *,
    sequence_result: Mapping[str, Any],
    registry_summary: Mapping[str, Any] | None = None,
) -> ProteinSummaryRecord:
    canonical = CanonicalProtein.from_dict(
        {
            "accession": record.get("accession"),
            "sequence": record.get("sequence") or "",
            "name": record.get("name") or record.get("protein_name") or "",
            "gene_names": record.get("gene_names") or (),
            "organism": record.get("organism") or "",
            "description": record.get("description") or record.get("name") or "",
            "source": record.get("source") or "UniProt",
            "aliases": record.get("aliases") or (),
            "annotations": record.get("annotations") or (),
        }
    )
    raw_payload = record.get("raw_payload") or {}
    if not isinstance(raw_payload, Mapping):
        raw_payload = {}
    sequence = raw_payload.get("sequence") or {}
    if not isinstance(sequence, Mapping):
        sequence = {}
    entry_audit = raw_payload.get("entryAudit") or {}
    if not isinstance(entry_audit, Mapping):
        entry_audit = {}
    taxon_id = record.get("proteome_taxon_id")
    organism_block = raw_payload.get("organism") or {}
    if taxon_id is None and isinstance(organism_block, Mapping):
        taxon_id = organism_block.get("taxonId")
    sequence_checksum = _optional_text(sequence.get("md5") or sequence.get("crc64"))
    if sequence_checksum and not sequence_checksum.startswith(("md5:", "crc64:")):
        sequence_checksum = f"md5:{sequence_checksum}"
    sequence_version = _optional_text(
        entry_audit.get("sequenceVersion") or record.get("release") or record.get("release_date")
    )
    provenance_pointer = _canonical_summary_pointer(canonical.accession, record, sequence_result)
    registry_summary = dict(registry_summary or {})
    (
        source_domain_refs,
        source_motif_refs,
        source_connections,
        source_partial_lanes,
        source_lane_counts,
    ) = (
        _extract_source_references(
            raw_payload,
            accession=canonical.accession,
            registry_summary=registry_summary,
        )
    )
    (
        classification_refs,
        classification_connections,
        classification_partial_lanes,
        classification_lane_counts,
    ) = (
        _extract_classification_references(
            accession=canonical.accession,
            raw_payload=raw_payload,
            registry_summary=registry_summary,
        )
    )
    registry_statuses = registry_summary.get("statuses") or {}
    protein_pdb_ids = _protein_pdb_ids(raw_payload)
    lane_counts = {
        "interpro": source_lane_counts.get("interpro", 0),
        "pfam": source_lane_counts.get("pfam", 0),
        "prosite": source_lane_counts.get("prosite", 0),
        "elm": source_lane_counts.get("elm", 0),
        "cath": classification_lane_counts.get("cath", 0),
        "scope": classification_lane_counts.get("scope", 0),
    }
    partial_lanes = tuple(sorted({*source_partial_lanes, *classification_partial_lanes}))
    notes = _dedupe_text(
        (
            "canonical_sequence_spine",
            f"source:{_clean_text(record.get('source') or 'UniProt')}",
            (
                f"reviewed:{str(record.get('reviewed')).lower()}"
                if record.get("reviewed") is not None
                else ""
            ),
            "annotation_refs:"
            f"domain={len(source_domain_refs) + len(classification_refs)}"
            f"|motif={len(source_motif_refs)}"
            f"|partial={len(partial_lanes)}",
            *(f"annotation_partial_lane:{lane}" for lane in partial_lanes),
        )
    )
    storage_notes = [
        "canonical protein summary materialized from data/canonical/LATEST.json",
    ]
    if registry_summary.get("manifest_id"):
        storage_notes.append(f"registry_manifest:{registry_summary['manifest_id']}")
    storage_notes.extend(
        _annotation_lane_notes(
            registry_statuses=registry_statuses,
            protein_pdb_ids=protein_pdb_ids,
            joined_lanes=lane_counts,
            partial_lanes=partial_lanes,
        )
    )
    return ProteinSummaryRecord(
        summary_id=canonical.canonical_id,
        protein_ref=canonical.canonical_id,
        protein_name=canonical.name or canonical.description,
        organism_name=canonical.organism,
        taxon_id=taxon_id,
        sequence_checksum=sequence_checksum,
        sequence_version=sequence_version,
        sequence_length=canonical.sequence_length,
        gene_names=canonical.gene_names,
        aliases=(canonical.accession, *canonical.aliases),
        join_status="joined",
        join_reason="canonical_sequence_record",
    context=SummaryRecordContext(
            provenance_pointers=(provenance_pointer,),
            domain_references=source_domain_refs + classification_refs,
            motif_references=source_motif_refs,
            source_connections=source_connections + classification_connections,
            storage_notes=tuple(storage_notes),
        ),
        notes=notes,
    )


def _library_or_none(path: Path) -> SummaryLibrarySchema | None:
    return SummaryLibrarySchema.from_dict(_read_json(path)) if path.exists() else None


def _protein_records_by_accession(
    library: SummaryLibrarySchema | None,
) -> dict[str, ProteinSummaryRecord]:
    if library is None:
        return {}
    result: dict[str, ProteinSummaryRecord] = {}
    for record in library.protein_records:
        accession = _protein_accession(record.protein_ref)
        if accession:
            result[accession] = record
    return result


def _source_scalar_value(
    field_name: str,
    record: ProteinSummaryRecord | None,
) -> tuple[Any, Any] | None:
    if record is None:
        return None
    value = getattr(record, field_name)
    if value is None:
        return None
    if field_name in {"protein_name", "organism_name", "sequence_checksum", "sequence_version"}:
        text = _optional_text(value)
        if not text:
            return None
        return text, text.casefold()
    if field_name in {"taxon_id", "sequence_length"}:
        if isinstance(value, bool):
            return None
        try:
            number = int(value)
        except (TypeError, ValueError):
            return None
        return number, number
    if field_name in {"gene_names", "aliases"}:
        items = _dedupe_text(value)
        if not items:
            return None
        return items, tuple(item.casefold() for item in items)
    raise KeyError(f"unsupported scalar consensus field: {field_name}")


def _scalar_consensus_notes(
    *,
    canonical_record: ProteinSummaryRecord | None,
    reactome_record: ProteinSummaryRecord | None,
    intact_record: ProteinSummaryRecord | None,
) -> tuple[
    tuple[SummarySourceRollup, ...],
    tuple[str, ...],
    tuple[str, ...],
    dict[str, int],
]:
    source_records = tuple(
        (source_name, record)
        for source_name, record in zip(
            _SCALAR_CONSENSUS_SOURCE_ORDER,
            (canonical_record, reactome_record, intact_record),
            strict=True,
        )
    )
    notes: list[str] = []
    field_statuses: list[str] = []
    rollups: list[SummarySourceRollup] = []
    status_counts: dict[str, int] = {"resolved": 0, "partial": 0, "conflict": 0}
    for field_name, claim_class in _SCALAR_CONSENSUS_FIELDS:
        candidates: list[dict[str, Any]] = []
        for source_name, record in source_records:
            scalar_value = _source_scalar_value(field_name, record)
            if scalar_value is None:
                continue
            winner_value, normalized_value = scalar_value
            candidates.append(
                {
                    "source_name": source_name,
                    "winner_value": winner_value,
                    "normalized_value": normalized_value,
                }
            )
        winner = candidates[0] if candidates else None
        supporting_sources: list[str] = []
        disagreeing_sources: list[str] = []
        status = "partial"
        partial_reason = "single_source_value"
        if winner is not None:
            for candidate in candidates[1:]:
                if candidate["normalized_value"] == winner["normalized_value"]:
                    supporting_sources.append(candidate["source_name"])
                else:
                    disagreeing_sources.append(candidate["source_name"])
            if disagreeing_sources:
                status = "conflict"
                partial_reason = "source_disagreement"
            elif supporting_sources:
                status = "resolved"
                partial_reason = ""
        else:
            partial_reason = "no_source_value"
        status_counts[status] += 1
        field_statuses.append(f"{field_name}={status}")
        source_values = tuple(
            SummarySourceClaim(
                source_name=candidate["source_name"],
                value=candidate["winner_value"],
            )
            for candidate in candidates
        )
        rollups.append(
            SummarySourceRollup(
                field_name=field_name,
                claim_class=claim_class,
                source_precedence=_SCALAR_CONSENSUS_SOURCE_ORDER,
                source_values=source_values,
                winner_source=winner["source_name"] if winner is not None else None,
                winner_value=(
                    _json_ready_scalar(winner["winner_value"]) if winner is not None else None
                ),
                corroborating_sources=tuple(supporting_sources),
                disagreeing_sources=tuple(disagreeing_sources),
                status=status,
                partial=status == "partial",
                partial_reason=partial_reason,
                trust_policy="p29_source_trust_policy",
            )
        )
        note_payload: dict[str, Any] = {
            "field": field_name,
            "claim_class": claim_class,
            "winner_source": winner["source_name"] if winner is not None else None,
            "winner_value": (
                _json_ready_scalar(winner["winner_value"]) if winner is not None else None
            ),
            "supporting_sources": supporting_sources,
            "disagreeing_sources": disagreeing_sources,
            "status": status,
            "partial": status == "partial",
        }
        if partial_reason:
            note_payload["partial_reason"] = partial_reason
        notes.append(
            "scalar_consensus:" + json.dumps(note_payload, sort_keys=True, separators=(",", ":"))
        )
    return tuple(rollups), tuple(notes), tuple(field_statuses), status_counts


def _intact_pair_references(
    library: SummaryLibrarySchema | None,
) -> dict[str, tuple[SummaryReference, ...]]:
    if library is None:
        return {}
    pair_refs_by_accession: dict[str, list[SummaryReference]] = defaultdict(list)
    for record in library.pair_records:
        reference_id = _optional_text(record.interaction_id) or record.summary_id
        interaction_refs = _dedupe_text(record.interaction_refs)
        evidence_refs = _dedupe_text(record.evidence_refs)
        reference = SummaryReference(
            reference_kind="cross_reference",
            namespace="IntAct",
            identifier=reference_id,
            label=record.interaction_type,
            join_status="joined" if reference_id else "partial",
            source_name="IntAct",
            source_record_id=reference_id,
            evidence_refs=interaction_refs + evidence_refs,
            notes=(
                f"pair_summary_id:{record.summary_id}",
                f"physical_interaction:{record.physical_interaction}",
                f"confidence:{record.confidence}" if record.confidence is not None else "",
            ),
        )
        for participant in (record.protein_a_ref, record.protein_b_ref):
            accession = _protein_accession(participant)
            if accession:
                pair_refs_by_accession[accession].append(reference)
    return {
        accession: _dedupe_references(references)
        for accession, references in pair_refs_by_accession.items()
    }


def _merge_context(
    *,
    canonical_record: ProteinSummaryRecord | None,
    reactome_record: ProteinSummaryRecord | None,
    intact_record: ProteinSummaryRecord | None,
    intact_pair_refs: tuple[SummaryReference, ...],
) -> SummaryRecordContext:
    provenance_pointers = []
    cross_references = []
    motif_references = []
    domain_references = []
    pathway_references = []
    source_connections = []
    storage_notes = [
        "materialized protein summary library slice",
        "canonical spine from data/canonical/LATEST.json",
    ]
    lazy_loading_guidance = ["hydrate source-specific payloads only after selection"]
    if canonical_record is not None:
        provenance_pointers.extend(canonical_record.context.provenance_pointers)
        cross_references.extend(canonical_record.context.cross_references)
        motif_references.extend(canonical_record.context.motif_references)
        domain_references.extend(canonical_record.context.domain_references)
        source_connections.extend(canonical_record.context.source_connections)
        storage_notes.extend(canonical_record.context.storage_notes)
        lazy_loading_guidance.extend(canonical_record.context.lazy_loading_guidance)
    if reactome_record is not None:
        provenance_pointers.extend(reactome_record.context.provenance_pointers)
        pathway_references.extend(reactome_record.context.pathway_references)
        source_connections.extend(reactome_record.context.source_connections)
        storage_notes.append("reactome pathway context attached")
    if intact_record is not None:
        provenance_pointers.extend(intact_record.context.provenance_pointers)
        cross_references.extend(intact_record.context.cross_references)
        source_connections.extend(intact_record.context.source_connections)
        storage_notes.append("intact summary provenance attached")
        lazy_loading_guidance.extend(intact_record.context.lazy_loading_guidance)
    if intact_pair_refs:
        cross_references.extend(intact_pair_refs)
        storage_notes.append(f"intact_pair_crossrefs:{len(intact_pair_refs)}")
    storage_notes.append(
        "reactome_pathways:"
        f"{len(reactome_record.context.pathway_references) if reactome_record else 0}"
    )
    storage_notes.append(
        "intact_provenance:"
        f"{len(intact_record.context.provenance_pointers) if intact_record else 0}"
    )
    return SummaryRecordContext(
        provenance_pointers=_dedupe_provenance_pointers(provenance_pointers),
        cross_references=_dedupe_references(cross_references),
        motif_references=_dedupe_references(motif_references),
        domain_references=_dedupe_references(domain_references),
        pathway_references=_dedupe_references(pathway_references),
        source_connections=_dedupe_connections(source_connections),
        storage_notes=_dedupe_text(storage_notes),
        lazy_loading_guidance=_dedupe_text(lazy_loading_guidance),
    )


def _join_reason(
    *,
    canonical_record: ProteinSummaryRecord | None,
    reactome_record: ProteinSummaryRecord | None,
    intact_record: ProteinSummaryRecord | None,
) -> str:
    parts = []
    if canonical_record is not None:
        parts.append("canonical")
    if reactome_record is not None:
        parts.append("reactome")
    if intact_record is not None:
        parts.append("intact")
    return "_plus_".join(parts) if parts else "artifact_only"


def _build_record(
    accession: str,
    *,
    canonical_record: ProteinSummaryRecord | None,
    reactome_record: ProteinSummaryRecord | None,
    intact_record: ProteinSummaryRecord | None,
    intact_pair_refs: tuple[SummaryReference, ...],
) -> ProteinSummaryRecord:
    source_record = canonical_record or reactome_record or intact_record
    if source_record is None:
        raise ValueError("at least one source record is required")
    protein_name = source_record.protein_name
    organism_name = source_record.organism_name
    taxon_id = source_record.taxon_id
    sequence_checksum = source_record.sequence_checksum
    sequence_version = source_record.sequence_version
    sequence_length = source_record.sequence_length
    gene_names = source_record.gene_names
    aliases = source_record.aliases
    if canonical_record is not None:
        protein_name = canonical_record.protein_name or protein_name
        organism_name = canonical_record.organism_name or organism_name
        taxon_id = canonical_record.taxon_id if canonical_record.taxon_id is not None else taxon_id
        sequence_checksum = canonical_record.sequence_checksum or sequence_checksum
        sequence_version = canonical_record.sequence_version or sequence_version
        sequence_length = canonical_record.sequence_length or sequence_length
        gene_names = canonical_record.gene_names or gene_names
        aliases = canonical_record.aliases or aliases
    elif reactome_record is not None:
        protein_name = reactome_record.protein_name or protein_name
        organism_name = reactome_record.organism_name or organism_name
        taxon_id = reactome_record.taxon_id if reactome_record.taxon_id is not None else taxon_id
        sequence_length = reactome_record.sequence_length or sequence_length
        gene_names = reactome_record.gene_names or gene_names
        aliases = reactome_record.aliases or aliases
    elif intact_record is not None:
        protein_name = intact_record.protein_name or protein_name
        organism_name = intact_record.organism_name or organism_name
        taxon_id = intact_record.taxon_id if intact_record.taxon_id is not None else taxon_id
        sequence_length = intact_record.sequence_length or sequence_length
        gene_names = intact_record.gene_names or gene_names
        aliases = intact_record.aliases or aliases
    context = _merge_context(
        canonical_record=canonical_record,
        reactome_record=reactome_record,
        intact_record=intact_record,
        intact_pair_refs=intact_pair_refs,
    )
    accession_sources = tuple(
        source_name
        for source_name, record in (
            ("UniProt", canonical_record),
            ("Reactome", reactome_record),
            ("IntAct", intact_record),
        )
        if record is not None
    )
    accession_connections = (
        SummarySourceConnection(
            connection_kind="accession",
            source_names=accession_sources,
            direct_sources=accession_sources,
            bridge_ids=(f"accession:{accession}",),
            bridge_source="accession",
            join_mode="direct",
            join_status="joined",
            notes=(f"accession_join_key:{accession}",),
        )
        if len(accession_sources) >= 2
        else None
    )
    (
        scalar_consensus_rollups,
        scalar_consensus_notes,
        scalar_consensus_statuses,
        scalar_consensus_counts,
    ) = (
        _scalar_consensus_notes(
            canonical_record=canonical_record,
            reactome_record=reactome_record,
            intact_record=intact_record,
        )
    )
    source_connections = _dedupe_connections(
        (
            *context.source_connections,
            *((accession_connections,) if accession_connections is not None else ()),
        )
    )
    context = replace(
        context,
        storage_notes=(
            *context.storage_notes,
            "scalar_consensus_policy:p29_source_trust_policy",
            "scalar_consensus_summary:"
            + json.dumps(
                {
                    "field_statuses": scalar_consensus_statuses,
                    "status_counts": scalar_consensus_counts,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
        ),
        source_rollups=scalar_consensus_rollups,
        source_connections=source_connections,
        cross_source_view=_cross_source_view(source_connections),
    )
    notes = _dedupe_text(
        (
            f"protein_summary_materialized:{accession}",
            (
                "join_reason:"
                + _join_reason(
                    canonical_record=canonical_record,
                    reactome_record=reactome_record,
                    intact_record=intact_record,
                )
            ),
            *(canonical_record.notes if canonical_record is not None else ()),
            *(reactome_record.notes if reactome_record is not None else ()),
            *(intact_record.notes if intact_record is not None else ()),
            "reactome_refs:"
            f"{len(reactome_record.context.pathway_references) if reactome_record else 0}",
            "intact_provenance:"
            f"{len(intact_record.context.provenance_pointers) if intact_record else 0}",
            f"intact_pair_refs:{len(intact_pair_refs)}",
            *scalar_consensus_notes,
        )
    )
    return ProteinSummaryRecord(
        summary_id=f"protein:{accession}",
        protein_ref=f"protein:{accession}",
        protein_name=protein_name,
        organism_name=organism_name,
        taxon_id=taxon_id,
        sequence_checksum=sequence_checksum,
        sequence_version=sequence_version,
        sequence_length=sequence_length,
        gene_names=gene_names,
        aliases=aliases,
        join_status="joined" if canonical_record is not None else "partial",
        join_reason=_join_reason(
            canonical_record=canonical_record,
            reactome_record=reactome_record,
            intact_record=intact_record,
        ),
        context=context,
        notes=notes,
    )


def materialize_protein_summary_library(
    *,
    canonical_latest_path: Path = DEFAULT_CANONICAL_LATEST_PATH,
    reactome_summary_path: Path = DEFAULT_REACTOME_SUMMARY_PATH,
    intact_summary_path: Path = DEFAULT_INTACT_SUMMARY_PATH,
    local_registry_summary_path: Path = DEFAULT_LOCAL_REGISTRY_SUMMARY_PATH,
    library_id: str = DEFAULT_LIBRARY_ID,
) -> SummaryLibrarySchema:
    canonical_payload = _read_json(canonical_latest_path)
    sequence_result = _sequence_result(canonical_payload)
    canonical_records = _canonical_record_map(sequence_result)
    canonical_order = _canonical_accession_order(sequence_result)
    canonical_release_manifest_id = _source_release_manifest_id(sequence_result)
    reactome_library = _library_or_none(reactome_summary_path)
    intact_library = _library_or_none(intact_summary_path)
    registry_summary = _registry_summary(local_registry_summary_path)
    reactome_by_accession = _protein_records_by_accession(reactome_library)
    intact_by_accession = _protein_records_by_accession(intact_library)
    intact_pair_refs_by_accession = _intact_pair_references(intact_library)
    accession_order = list(canonical_order)
    for accession in sorted(set(reactome_by_accession) | set(intact_by_accession)):
        if accession not in accession_order:
            accession_order.append(accession)
    records: list[ProteinSummaryRecord] = []
    for accession in accession_order:
        canonical_payload_record = canonical_records.get(accession)
        canonical_record = (
            _canonical_protein_from_record(
                canonical_payload_record,
                sequence_result=sequence_result,
                registry_summary=registry_summary,
            )
            if canonical_payload_record is not None
            else None
        )
        reactome_record = reactome_by_accession.get(accession)
        intact_record = intact_by_accession.get(accession)
        pair_refs = intact_pair_refs_by_accession.get(accession, ())
        if canonical_record is None and reactome_record is None and intact_record is None:
            continue
        records.append(
            _build_record(
                accession,
                canonical_record=canonical_record,
                reactome_record=reactome_record,
                intact_record=intact_record,
                intact_pair_refs=pair_refs,
            )
        )
    source_manifest_id = "|".join(
        part
        for part in (
            canonical_release_manifest_id,
            reactome_library.source_manifest_id if reactome_library else None,
            intact_library.source_manifest_id if intact_library else None,
            registry_summary.get("manifest_id"),
        )
        if part
    )
    return SummaryLibrarySchema(
        library_id=library_id,
        source_manifest_id=source_manifest_id or None,
        records=tuple(records),
        index_guidance=(
            "route protein summaries accession-first",
            "preserve pathway and interaction lineage on protein records",
            "keep unresolved or artifact-only proteins visible rather than hiding them",
        ),
        storage_guidance=(
            "materialize only protein summary records in this slice",
            (
                "attach Reactome pathway context, IntAct provenance, and "
                "registry-backed annotation lanes to protein records"
            ),
            "defer pair, structure, and ligand payloads to their own materializers",
        ),
        lazy_loading_guidance=(
            "hydrate heavy source payloads only after selection",
            "preserve source-specific provenance pointers alongside the protein spine",
        ),
    )


__all__ = [
    "DEFAULT_CANONICAL_LATEST_PATH",
    "DEFAULT_INTACT_SUMMARY_PATH",
    "DEFAULT_LIBRARY_ID",
    "DEFAULT_OUTPUT_PATH",
    "DEFAULT_REACTOME_SUMMARY_PATH",
    "materialize_protein_summary_library",
]

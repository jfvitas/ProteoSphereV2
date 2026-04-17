from __future__ import annotations

import csv
import gzip
import json
import pickle
import tempfile
import zipfile
from collections import defaultdict
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from typing import Any

import duckdb


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WAREHOUSE_ROOT = Path(r"D:\ProteoSphere\reference_library")
DEFAULT_WAREHOUSE_CATALOG = DEFAULT_WAREHOUSE_ROOT / "catalog" / "reference_library.duckdb"
DEFAULT_ALIAS_PATH = (
    REPO_ROOT / "data" / "raw" / "protein_data_scope_seed" / "string" / "protein.aliases.v12.0.txt.gz"
)
DEFAULT_AUDIT_REGISTRY = DEFAULT_WAREHOUSE_ROOT / "control" / "paper_split_audit_registry.json"
DEFAULT_OUTPUT_REGISTRY = DEFAULT_WAREHOUSE_ROOT / "control" / "paper_identifier_bridge_registry.json"
DEFAULT_OUTPUT_DETAIL_DIR = DEFAULT_WAREHOUSE_ROOT / "control" / "paper_identifier_bridge_details"
DEFAULT_DSCRIPT_DIR = REPO_ROOT / "artifacts" / "status" / "paper_split_external" / "dscript"
DEFAULT_RAPPPID_ZIP = (
    REPO_ROOT / "artifacts" / "status" / "paper_split_external" / "rapppid" / "rapppid_data.zip"
)


def _write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must decode to an object")
    return payload


def _extract_dscript_members() -> dict[str, set[str]]:
    members: dict[str, set[str]] = defaultdict(set)
    for split_name, filename in {
        "human_train": "human_train.tsv",
        "human_test": "human_test.tsv",
        "fly_test": "fly_test.tsv",
    }.items():
        path = DEFAULT_DSCRIPT_DIR / filename
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 2:
                    continue
                members[split_name].add(parts[0].strip())
                members[split_name].add(parts[1].strip())
    return members


def _extract_rapppid_members() -> dict[str, set[str]]:
    members: dict[str, set[str]] = defaultdict(set)
    if not DEFAULT_RAPPPID_ZIP.exists():
        return members
    with zipfile.ZipFile(DEFAULT_RAPPPID_ZIP) as archive:
        targets = [
            name
            for name in archive.namelist()
            if name.startswith("rapppid/comparatives/string_c")
            and name.endswith("_pairs.pkl.gz")
        ]
        for name in targets:
            stem = name.split("/")[-2:]
            cohort = stem[0]
            leaf = stem[1]
            if leaf.endswith("_pairs.pkl.gz"):
                split_name = f"{cohort}_{leaf.replace('_pairs.pkl.gz', '')}"
            with archive.open(name) as raw_handle:
                with gzip.GzipFile(fileobj=raw_handle) as gz_handle:
                    payload = pickle.load(gz_handle)
            if isinstance(payload, list):
                for row in payload:
                    if isinstance(row, (list, tuple)) and len(row) >= 2:
                        members[split_name].add(str(row[0]).strip())
                        members[split_name].add(str(row[1]).strip())
    return members


def _write_identifier_csv(target_ids: set[str]) -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8", newline="")
    with handle:
        writer = csv.DictWriter(handle, fieldnames=["string_protein_id"])
        writer.writeheader()
        for identifier in sorted(target_ids):
            writer.writerow({"string_protein_id": identifier})
    return Path(handle.name)


def _query_alias_bridge(target_ids: set[str]) -> dict[str, dict[str, Any]]:
    if not target_ids:
        return {}
    target_csv = _write_identifier_csv(target_ids)
    try:
        con = duckdb.connect()
        con.execute("PRAGMA threads=8")
        rows = con.execute(
            """
            SELECT
                a.string_protein_id,
                a.alias AS accession,
                a.source
            FROM read_csv_auto(?, columns={'string_protein_id':'VARCHAR'}) t
            JOIN read_csv_auto(
                ?,
                delim='\t',
                header=true,
                columns={'string_protein_id':'VARCHAR','alias':'VARCHAR','source':'VARCHAR'}
            ) a
              ON a.string_protein_id = t.string_protein_id
            WHERE a.source IN ('UniProt_AC', 'BLAST_UniProt_AC')
            ORDER BY 1, 3, 2
            """,
            [str(target_csv), str(DEFAULT_ALIAS_PATH)],
        ).fetchall()
    finally:
        target_csv.unlink(missing_ok=True)
        try:
            con.close()
        except Exception:
            pass

    indexed: dict[str, dict[str, Any]] = {}
    for string_protein_id, accession, source in rows:
        entry = indexed.setdefault(
            str(string_protein_id),
            {
                "candidate_accessions": [],
                "candidate_sources": [],
            },
        )
        if accession and accession not in entry["candidate_accessions"]:
            entry["candidate_accessions"].append(str(accession))
        if source and source not in entry["candidate_sources"]:
            entry["candidate_sources"].append(str(source))
    for entry in indexed.values():
        entry["candidate_accessions"].sort()
        entry["candidate_sources"].sort()
    return indexed


def _write_accession_csv(accessions: set[str]) -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8", newline="")
    with handle:
        writer = csv.DictWriter(handle, fieldnames=["accession"])
        writer.writeheader()
        for accession in sorted(accessions):
            writer.writerow({"accession": accession})
    return Path(handle.name)


def _query_protein_lookup(accessions: set[str]) -> dict[str, dict[str, Any]]:
    if not accessions:
        return {}
    accessions_csv = _write_accession_csv(accessions)
    try:
        with duckdb.connect(str(DEFAULT_WAREHOUSE_CATALOG), read_only=True) as con:
            rows = con.execute(
                """
                SELECT
                    p.accession,
                    p.protein_ref,
                    p.uniref100_cluster,
                    p.uniref90_cluster,
                    p.uniref50_cluster,
                    p.taxon_id
                FROM proteins p
                JOIN read_csv_auto(?, columns={'accession':'VARCHAR'}) t
                  ON p.accession = t.accession
                """,
                [str(accessions_csv)],
            ).fetchall()
    finally:
        accessions_csv.unlink(missing_ok=True)

    lookup: dict[str, dict[str, Any]] = {}
    for accession, protein_ref, uniref100, uniref90, uniref50, taxon_id in rows:
        lookup[str(accession)] = {
            "protein_ref": str(protein_ref or ""),
            "uniref100_cluster": str(uniref100 or ""),
            "uniref90_cluster": str(uniref90 or ""),
            "uniref50_cluster": str(uniref50 or ""),
            "taxon_id": int(taxon_id) if taxon_id is not None else None,
        }
    return lookup


def _strip_namespace(identifier: str) -> str:
    text = str(identifier or "").strip()
    if "." in text:
        return text.split(".", 1)[1]
    return text


def _taxon_prefix(identifier: str) -> str:
    text = str(identifier or "").strip()
    if "." in text:
        return text.split(".", 1)[0]
    return ""


def _build_identifier_rows(
    split_members: dict[str, set[str]],
    alias_lookup: dict[str, dict[str, Any]],
    protein_lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    membership_index: dict[str, list[str]] = defaultdict(list)
    for split_name, identifiers in split_members.items():
        for identifier in identifiers:
            membership_index[identifier].append(split_name)
    rows: list[dict[str, Any]] = []
    for identifier in sorted(membership_index):
        alias_payload = dict(alias_lookup.get(identifier) or {})
        candidate_accessions = [
            accession
            for accession in alias_payload.get("candidate_accessions") or []
            if accession in protein_lookup
        ]
        exact_accession = candidate_accessions[0] if len(candidate_accessions) == 1 else ""
        exact_payload = dict(protein_lookup.get(exact_accession) or {})
        rows.append(
            {
                "identifier": identifier,
                "stripped_identifier": _strip_namespace(identifier),
                "taxon_prefix": _taxon_prefix(identifier),
                "split_memberships": sorted(membership_index[identifier]),
                "candidate_accessions": sorted(candidate_accessions),
                "candidate_sources": sorted(alias_payload.get("candidate_sources") or []),
                "mapping_status": (
                    "exact"
                    if exact_accession
                    else "ambiguous"
                    if candidate_accessions
                    else "unresolved"
                ),
                "exact_accession": exact_accession,
                "protein_ref": str(exact_payload.get("protein_ref") or ""),
                "uniref100_cluster": str(exact_payload.get("uniref100_cluster") or ""),
                "uniref90_cluster": str(exact_payload.get("uniref90_cluster") or ""),
                "uniref50_cluster": str(exact_payload.get("uniref50_cluster") or ""),
                "taxon_id": exact_payload.get("taxon_id"),
            }
        )
    return rows


def _split_summary(split_name: str, identifiers: set[str], row_lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = [row_lookup[identifier] for identifier in sorted(identifiers) if identifier in row_lookup]
    exact_rows = [row for row in rows if row.get("mapping_status") == "exact"]
    ambiguous_rows = [row for row in rows if row.get("mapping_status") == "ambiguous"]
    unresolved_rows = [row for row in rows if row.get("mapping_status") == "unresolved"]
    return {
        "split_name": split_name,
        "identifier_count": len(identifiers),
        "exact_mapped_identifier_count": len(exact_rows),
        "ambiguous_identifier_count": len(ambiguous_rows),
        "unresolved_identifier_count": len(unresolved_rows),
        "exact_accession_count": len({row["exact_accession"] for row in exact_rows if row.get("exact_accession")}),
        "exact_uniref90_count": len(
            {row["uniref90_cluster"] for row in exact_rows if row.get("uniref90_cluster")}
        ),
        "sample_unresolved_identifiers": [row["identifier"] for row in unresolved_rows[:10]],
    }


def _overlap_summary(
    left_name: str,
    right_name: str,
    split_members: dict[str, set[str]],
    row_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    left_ids = set(split_members.get(left_name) or set())
    right_ids = set(split_members.get(right_name) or set())
    left_rows = [row_lookup[item] for item in left_ids if item in row_lookup]
    right_rows = [row_lookup[item] for item in right_ids if item in row_lookup]
    left_exact = [row for row in left_rows if row.get("mapping_status") == "exact"]
    right_exact = [row for row in right_rows if row.get("mapping_status") == "exact"]
    left_accessions = {row["exact_accession"] for row in left_exact if row.get("exact_accession")}
    right_accessions = {row["exact_accession"] for row in right_exact if row.get("exact_accession")}
    left_uniref90 = {row["uniref90_cluster"] for row in left_exact if row.get("uniref90_cluster")}
    right_uniref90 = {row["uniref90_cluster"] for row in right_exact if row.get("uniref90_cluster")}
    return {
        "left_split": left_name,
        "right_split": right_name,
        "direct_identifier_overlap_count": len(left_ids & right_ids),
        "exact_accession_overlap_count": len(left_accessions & right_accessions),
        "exact_uniref90_overlap_count": len(left_uniref90 & right_uniref90),
        "left_exact_mapped_identifier_count": len(left_exact),
        "right_exact_mapped_identifier_count": len(right_exact),
        "left_unresolved_identifier_count": len(
            [row for row in left_rows if row.get("mapping_status") == "unresolved"]
        ),
        "right_unresolved_identifier_count": len(
            [row for row in right_rows if row.get("mapping_status") == "unresolved"]
        ),
    }


def _paper_summary(
    paper_id: str,
    split_members: dict[str, set[str]],
    identifier_rows: list[dict[str, Any]],
    detail_path: Path,
) -> dict[str, Any]:
    row_lookup = {row["identifier"]: row for row in identifier_rows}
    split_summaries = {
        split_name: _split_summary(split_name, identifiers, row_lookup)
        for split_name, identifiers in sorted(split_members.items())
    }
    overlap_pairs = list(combinations(sorted(split_members), 2))
    if paper_id == "szymborski2022rapppid":
        overlap_pairs = [
            (left_name, right_name)
            for left_name, right_name in overlap_pairs
            if left_name.rsplit("_", 1)[0] == right_name.rsplit("_", 1)[0]
        ]
    overlap_summaries = [
        _overlap_summary(left_name, right_name, split_members, row_lookup)
        for left_name, right_name in overlap_pairs
    ]
    exact_rows = [row for row in identifier_rows if row.get("mapping_status") == "exact"]
    ambiguous_rows = [row for row in identifier_rows if row.get("mapping_status") == "ambiguous"]
    unresolved_rows = [row for row in identifier_rows if row.get("mapping_status") == "unresolved"]
    return {
        "paper_id": paper_id,
        "bridge_method": "string_aliases_to_uniprot_accession",
        "bridge_status": "materialized" if exact_rows else "unresolved",
        "identifier_namespace": "string_protein_id",
        "total_identifier_count": len(identifier_rows),
        "exact_mapped_identifier_count": len(exact_rows),
        "ambiguous_identifier_count": len(ambiguous_rows),
        "unresolved_identifier_count": len(unresolved_rows),
        "exact_accession_count": len(
            {row["exact_accession"] for row in exact_rows if row.get("exact_accession")}
        ),
        "exact_uniref90_count": len(
            {row["uniref90_cluster"] for row in exact_rows if row.get("uniref90_cluster")}
        ),
        "split_summaries": split_summaries,
        "overlap_summaries": overlap_summaries,
        "sample_unresolved_identifiers": [row["identifier"] for row in unresolved_rows[:20]],
        "detail_artifact_path": str(detail_path),
    }


def build_registry() -> dict[str, Any]:
    audit_registry = _load_json(DEFAULT_AUDIT_REGISTRY) if DEFAULT_AUDIT_REGISTRY.exists() else {}
    papers_to_process = {"sledzieski2021dscript", "szymborski2022rapppid"}
    if audit_registry:
        records = audit_registry.get("records") or []
        filtered = {
            str(row.get("paper_id") or "")
            for row in records
            if isinstance(row, dict) and row.get("identifier_bridge_requirements")
        }
        if filtered:
            papers_to_process &= filtered

    paper_members: dict[str, dict[str, set[str]]] = {}
    if "sledzieski2021dscript" in papers_to_process:
        paper_members["sledzieski2021dscript"] = _extract_dscript_members()
    if "szymborski2022rapppid" in papers_to_process:
        paper_members["szymborski2022rapppid"] = _extract_rapppid_members()

    target_ids = {
        identifier
        for split_members in paper_members.values()
        for identifiers in split_members.values()
        for identifier in identifiers
    }
    alias_lookup = _query_alias_bridge(target_ids)
    candidate_accessions = {
        accession
        for payload in alias_lookup.values()
        for accession in payload.get("candidate_accessions") or []
    }
    protein_lookup = _query_protein_lookup(candidate_accessions)

    records: list[dict[str, Any]] = []
    for paper_id, split_members in sorted(paper_members.items()):
        identifier_rows = _build_identifier_rows(split_members, alias_lookup, protein_lookup)
        detail_path = DEFAULT_OUTPUT_DETAIL_DIR / f"{paper_id}.json"
        detail_payload = {
            "artifact_id": f"{paper_id}_identifier_bridge_detail",
            "schema_id": "proteosphere-paper-identifier-bridge-detail-v1",
            "generated_at": datetime.now(UTC).isoformat(),
            "paper_id": paper_id,
            "identifier_rows": identifier_rows,
        }
        _write_json(detail_path, detail_payload)
        records.append(_paper_summary(paper_id, split_members, identifier_rows, detail_path))

    return {
        "artifact_id": "paper_identifier_bridge_registry",
        "schema_id": "proteosphere-paper-identifier-bridge-registry-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "warehouse_root": str(DEFAULT_WAREHOUSE_ROOT),
        "catalog_path": str(DEFAULT_WAREHOUSE_CATALOG),
        "source_inputs": {
            "string_aliases": str(DEFAULT_ALIAS_PATH),
            "paper_split_audit_registry": str(DEFAULT_AUDIT_REGISTRY),
            "dscript_dir": str(DEFAULT_DSCRIPT_DIR),
            "rapppid_zip": str(DEFAULT_RAPPPID_ZIP),
        },
        "records": records,
    }


def main() -> None:
    payload = build_registry()
    _write_json(DEFAULT_OUTPUT_REGISTRY, payload)
    print(
        json.dumps(
            {
                "status": "ok",
                "record_count": len(payload.get("records") or []),
                "output_path": str(DEFAULT_OUTPUT_REGISTRY),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

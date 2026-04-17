from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

from api.model_studio.capabilities import option_reason
from api.model_studio.reference_library import (
    load_public_reference_manifest,
    load_paper_identifier_bridge_registry,
    load_paper_split_audit_registry,
    load_source_registry,
    normalize_source_family_name,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_WAREHOUSE_ROOT = Path(
    os.environ.get("PROTEOSPHERE_WAREHOUSE_ROOT", r"D:\ProteoSphere\reference_library")
)
DEFAULT_CORPUS_PATH = Path(__file__).resolve().parent / "real_paper_corpus.json"
DEFAULT_EXISTING_AUDIT_ROOT = REPO_ROOT / "artifacts" / "status" / "paper_split_list"
DEFAULT_WAREHOUSE_AUDIT_REGISTRY = DEFAULT_WAREHOUSE_ROOT / "control" / "paper_split_audit_registry.json"
DEFAULT_WAREHOUSE_IDENTIFIER_BRIDGE_REGISTRY = (
    DEFAULT_WAREHOUSE_ROOT / "control" / "paper_identifier_bridge_registry.json"
)

CANONICAL_REASON_CODES = (
    "DIRECT_OVERLAP",
    "ACCESSION_ROOT_OVERLAP",
    "UNIREF_CLUSTER_OVERLAP",
    "SHARED_PARTNER_LEAKAGE",
    "INSUFFICIENT_PROVENANCE",
    "INCOMPLETE_MODALITY_COVERAGE",
    "CANDIDATE_ONLY_NON_GOVERNING",
    "AUDIT_ONLY_EVIDENCE",
    "UNRESOLVED_ENTITY_MAPPING",
    "UNRESOLVED_SPLIT_MEMBERSHIP",
    "POLICY_MISMATCH",
    "WAREHOUSE_COVERAGE_GAP",
)

BLOCKER_REASON_CODES = {
    "DIRECT_OVERLAP",
    "ACCESSION_ROOT_OVERLAP",
    "UNIREF_CLUSTER_OVERLAP",
    "SHARED_PARTNER_LEAKAGE",
    "UNRESOLVED_ENTITY_MAPPING",
    "UNRESOLVED_SPLIT_MEMBERSHIP",
    "POLICY_MISMATCH",
    "WAREHOUSE_COVERAGE_GAP",
}

REASON_MESSAGES = {
    "DIRECT_OVERLAP": "Train/test members overlap directly in the resolved entity roster.",
    "ACCESSION_ROOT_OVERLAP": "Train/test members reuse the same accession-root identifiers.",
    "UNIREF_CLUSTER_OVERLAP": "Train/test members overlap at the UniRef cluster level.",
    "SHARED_PARTNER_LEAKAGE": "Train/test members retain shared partner or component leakage signatures.",
    "INSUFFICIENT_PROVENANCE": "Paper evidence is too weak to treat the claimed split as governing.",
    "INCOMPLETE_MODALITY_COVERAGE": "Required modalities are missing or incomplete for the resolved members.",
    "CANDIDATE_ONLY_NON_GOVERNING": "Some evidence remains candidate-only and cannot govern training decisions.",
    "AUDIT_ONLY_EVIDENCE": "Some evidence remains audit-only or non-redistributable in the condensed warehouse.",
    "UNRESOLVED_ENTITY_MAPPING": "Some explicit paper members could not be resolved against the warehouse.",
    "UNRESOLVED_SPLIT_MEMBERSHIP": "The paper does not expose enough roster detail to reconstruct the split deterministically.",
    "POLICY_MISMATCH": "The claimed split strategy does not satisfy ProteoSphere training policy as written.",
    "WAREHOUSE_COVERAGE_GAP": "The warehouse does not fully materialize the source or benchmark surface needed for this paper.",
}


@dataclass(frozen=True)
class PaperClaim:
    paper_id: str
    title: str
    doi: str
    task_group: str
    modality: str
    claimed_dataset: str
    source_families: tuple[str, ...]
    named_entities: tuple[str, ...]
    claimed_split_description: str
    split_style: str
    train_members: tuple[str, ...] = ()
    val_members: tuple[str, ...] = ()
    test_members: tuple[str, ...] = ()
    member_type: str = ""
    notes: tuple[str, ...] = ()
    paper_text_excerpt: str = ""


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_existing_paper_audit(paper_id: str) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    if DEFAULT_WAREHOUSE_AUDIT_REGISTRY.exists():
        registry = load_paper_split_audit_registry(DEFAULT_WAREHOUSE_AUDIT_REGISTRY)
        for row in registry.get("records") or []:
            if isinstance(row, dict) and str(row.get("paper_id") or "") == paper_id:
                merged["warehouse_audit_surface"] = row
                break
    if DEFAULT_WAREHOUSE_IDENTIFIER_BRIDGE_REGISTRY.exists():
        registry = load_paper_identifier_bridge_registry(DEFAULT_WAREHOUSE_IDENTIFIER_BRIDGE_REGISTRY)
        for row in registry.get("records") or []:
            if isinstance(row, dict) and str(row.get("paper_id") or "") == paper_id:
                merged["warehouse_identifier_bridge"] = row
                break
    path = DEFAULT_EXISTING_AUDIT_ROOT / f"{paper_id}.json"
    if path.exists():
        payload = _load_json(path)
        if isinstance(payload, dict):
            merged.update(payload)
    return merged


def load_paper_corpus(path: Path | None = None) -> dict[str, Any]:
    target = path or DEFAULT_CORPUS_PATH
    payload = _load_json(target)
    if not isinstance(payload, dict):
        raise ValueError(f"{target} must decode to a JSON object.")
    papers = payload.get("papers")
    if not isinstance(papers, list) or not papers:
        raise ValueError(f"{target} must include a non-empty `papers` list.")
    normalized: list[dict[str, Any]] = []
    for paper in papers:
        if not isinstance(paper, dict):
            raise ValueError(f"{target} paper entries must be JSON objects.")
        normalized.append(_paper_claim_from_dict(paper).__dict__)
    return {
        "artifact_id": str(payload.get("artifact_id") or "paper_dataset_corpus"),
        "schema_id": str(payload.get("schema_id") or "proteosphere-paper-dataset-corpus-v1"),
        "default_view": str(payload.get("default_view") or "best_evidence"),
        "cohorts": dict(payload.get("cohorts") or {}),
        "papers": normalized,
        "source_path": str(target),
    }


def _paper_claim_from_dict(payload: dict[str, Any]) -> PaperClaim:
    def _strings(value: Any) -> tuple[str, ...]:
        if not value:
            return ()
        if isinstance(value, (list, tuple)):
            return tuple(str(item).strip() for item in value if str(item).strip())
        return (str(value).strip(),)

    return PaperClaim(
        paper_id=str(payload.get("paper_id") or "").strip(),
        title=str(payload.get("title") or "").strip(),
        doi=str(payload.get("doi") or "").strip(),
        task_group=str(payload.get("task_group") or "").strip(),
        modality=str(payload.get("modality") or "").strip(),
        claimed_dataset=str(payload.get("claimed_dataset") or "").strip(),
        source_families=_strings(payload.get("source_families")),
        named_entities=_strings(payload.get("named_entities")),
        claimed_split_description=str(payload.get("claimed_split_description") or "").strip(),
        split_style=str(payload.get("split_style") or "").strip(),
        train_members=_strings(payload.get("train_members")),
        val_members=_strings(payload.get("val_members")),
        test_members=_strings(payload.get("test_members")),
        member_type=str(payload.get("member_type") or "").strip(),
        notes=_strings(payload.get("notes")),
        paper_text_excerpt=str(payload.get("paper_text_excerpt") or "").strip(),
    )


def load_live_warehouse_snapshot(warehouse_root: Path | None = None) -> dict[str, Any]:
    root = warehouse_root or DEFAULT_WAREHOUSE_ROOT
    manifest_path = root / "warehouse_manifest.json"
    runtime_validation_path = root / "control" / "runtime_validation.latest.json"
    source_registry_path = root / "control" / "source_registry.json"
    catalog_path = root / "catalog" / "reference_library.duckdb"
    manifest_payload = load_public_reference_manifest(manifest_path)
    runtime_validation_payload = _load_json(runtime_validation_path) if runtime_validation_path.exists() else {}
    source_registry_payload = load_source_registry(source_registry_path)
    with duckdb.connect(str(catalog_path), read_only=True) as con:
        snapshot = {
            "warehouse_root": str(root),
            "catalog_path": str(catalog_path),
            "default_view": "best_evidence",
            "manifest": manifest_payload,
            "runtime_validation": runtime_validation_payload,
            "source_registry": source_registry_payload,
            "source_lookup": _query_source_rows(con),
            "profile": _query_profile(con, runtime_validation_payload),
            "member_resolution_overrides": {},
        }
    return snapshot


def _query_source_rows(con: duckdb.DuckDBPyConnection) -> dict[str, dict[str, Any]]:
    rows = con.execute(
        """
        SELECT
            source_key,
            source_name,
            availability_status,
            category,
            license_scope,
            public_export_allowed,
            redistributable,
            retrieval_mode,
            scope_tier
        FROM warehouse_sources
        """
    ).fetchall()
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = normalize_source_family_name(row[0] or row[1] or "")
        indexed[key] = {
            "source_key": row[0],
            "source_name": row[1],
            "availability_status": row[2],
            "category": row[3],
            "license_scope": row[4],
            "public_export_allowed": bool(row[5]),
            "redistributable": bool(row[6]),
            "retrieval_mode": row[7],
            "scope_tier": row[8],
        }
    return indexed


def _query_profile(
    con: duckdb.DuckDBPyConnection,
    runtime_validation_payload: dict[str, Any],
) -> dict[str, Any]:
    ppi_sources = {
        row[0]: {"row_count": int(row[1]), "resolved_endpoint_count": int(row[2])}
        for row in con.execute(
            """
            SELECT
                interaction_source,
                COUNT(*) AS row_count,
                COUNT(*) FILTER (
                    WHERE protein_a_ref IS NOT NULL
                      AND protein_b_ref IS NOT NULL
                ) AS resolved_endpoint_count
            FROM protein_protein_edges
            GROUP BY 1
            """
        ).fetchall()
    }
    proteins, uniref100, uniref90, uniref50 = con.execute(
        """
        SELECT
            COUNT(*) AS proteins,
            COUNT(*) FILTER (WHERE uniref100_cluster IS NOT NULL) AS uniref100,
            COUNT(*) FILTER (WHERE uniref90_cluster IS NOT NULL) AS uniref90,
            COUNT(*) FILTER (WHERE uniref50_cluster IS NOT NULL) AS uniref50
        FROM proteins
        """
    ).fetchone()
    return {
        "protein_uniref_coverage": {
            "proteins": int(proteins),
            "uniref100": int(uniref100),
            "uniref90": int(uniref90),
            "uniref50": int(uniref50),
        },
        "connectivity_validation": dict(
            ((runtime_validation_payload.get("checks") or {}).get("connectivity_validation") or {})
        ),
        "ppi_sources": ppi_sources,
        "variant_rows": int(con.execute("SELECT COUNT(*) FROM protein_variants").fetchone()[0]),
        "joined_variant_rows": int(
            con.execute(
                "SELECT COUNT(*) FROM protein_variants WHERE join_status = 'joined'"
            ).fetchone()[0]
        ),
        "pdb_entry_rows": int(con.execute("SELECT COUNT(*) FROM pdb_entries").fetchone()[0]),
        "structure_unit_rows": int(con.execute("SELECT COUNT(*) FROM structure_units").fetchone()[0]),
    }


def _claimed_split_policy(split_style: str) -> str:
    text = str(split_style or "").strip()
    return text or "unresolved_policy"


def _resolved_split_policy(split_style: str) -> str:
    if split_style in {"strict_unseen_protein", "uniref_or_homology_guard"}:
        return "uniref_grouped"
    if split_style in {"external_holdout", "source_held_out", "paper_specific_external"}:
        return "paper_faithful_external"
    if split_style == "protein_ligand_component_grouped":
        return "protein_ligand_component_grouped"
    if split_style in {"held_out_test", "cross_validation"}:
        return "accession_grouped"
    return "unresolved_policy"


def _split_parse_confidence(paper: PaperClaim) -> str:
    if paper.train_members and paper.test_members and paper.member_type:
        return "high"
    if paper.claimed_split_description and paper.split_style:
        return "medium"
    return "low"


def _mapping_input_completeness(paper: PaperClaim) -> str:
    if paper.train_members or paper.test_members or paper.val_members:
        return "explicit_membership"
    if paper.named_entities or paper.claimed_split_description:
        return "paper_notes_only"
    return "minimal"


def _structure_expected(paper: PaperClaim) -> bool:
    text = paper.modality.casefold()
    return "structure" in text or "surface" in text or paper.task_group in {
        "interface_prediction",
        "binding_site_prediction",
        "contact_prediction",
        "complex_prediction",
        "mutation_effect_prediction",
        "affinity_prediction",
    }


def _resolve_member_roster(paper: PaperClaim, snapshot: dict[str, Any]) -> dict[str, Any]:
    overrides = dict(snapshot.get("member_resolution_overrides") or {})
    if paper.paper_id in overrides:
        return dict(overrides[paper.paper_id])
    all_members = {
        "train": list(paper.train_members),
        "val": list(paper.val_members),
        "test": list(paper.test_members),
    }
    if not any(all_members.values()):
        return {
            "status": "missing_membership",
            "member_type": paper.member_type or "",
            "resolved_members": {"train": {}, "val": {}, "test": {}},
            "unresolved_members": {"train": [], "val": [], "test": []},
        }
    member_type = paper.member_type.casefold()
    if member_type != "pdb_id":
        unresolved = {name: list(values) for name, values in all_members.items()}
        return {
            "status": "unsupported_member_type",
            "member_type": paper.member_type,
            "resolved_members": {"train": {}, "val": {}, "test": {}},
            "unresolved_members": unresolved,
        }

    catalog_path = Path(str(snapshot.get("catalog_path") or ""))
    resolved_members: dict[str, dict[str, Any]] = {"train": {}, "val": {}, "test": {}}
    unresolved_members: dict[str, list[str]] = {"train": [], "val": [], "test": []}
    all_ids = sorted({item.upper() for values in all_members.values() for item in values})
    if not catalog_path.exists():
        return {
            "status": "catalog_missing",
            "member_type": paper.member_type,
            "resolved_members": resolved_members,
            "unresolved_members": {name: list(values) for name, values in all_members.items()},
        }
    placeholders = ", ".join("?" for _ in all_ids)
    query = f"""
        SELECT
            UPPER(pe.entry_id) AS member_id,
            MAX(CASE WHEN pe.has_local_structure_file THEN 1 ELSE 0 END) AS has_structure,
            LIST(DISTINCT p.accession) FILTER (WHERE p.accession IS NOT NULL) AS accessions,
            LIST(DISTINCT regexp_replace(p.accession, '-.*$', '')) FILTER (WHERE p.accession IS NOT NULL) AS accession_roots,
            LIST(DISTINCT p.uniref100_cluster) FILTER (WHERE p.uniref100_cluster IS NOT NULL) AS uniref100_clusters,
            LIST(DISTINCT p.uniref90_cluster) FILTER (WHERE p.uniref90_cluster IS NOT NULL) AS uniref90_clusters,
            LIST(DISTINCT p.uniref50_cluster) FILTER (WHERE p.uniref50_cluster IS NOT NULL) AS uniref50_clusters
        FROM pdb_entries pe
        LEFT JOIN structure_units su ON su.structure_id = pe.structure_id
        LEFT JOIN proteins p ON p.protein_ref = su.protein_ref
        WHERE UPPER(pe.entry_id) IN ({placeholders})
        GROUP BY 1
    """
    with duckdb.connect(str(catalog_path), read_only=True) as con:
        rows = con.execute(query, all_ids).fetchall()
    by_member = {
        row[0]: {
            "has_structure": bool(row[1]),
            "accessions": sorted(str(item) for item in (row[2] or []) if str(item).strip()),
            "accession_roots": sorted(
                str(item) for item in (row[3] or []) if str(item).strip()
            ),
            "uniref100_clusters": sorted(
                str(item) for item in (row[4] or []) if str(item).strip()
            ),
            "uniref90_clusters": sorted(
                str(item) for item in (row[5] or []) if str(item).strip()
            ),
            "uniref50_clusters": sorted(
                str(item) for item in (row[6] or []) if str(item).strip()
            ),
        }
        for row in rows
    }
    for split_name, members in all_members.items():
        for member in members:
            normalized = member.upper()
            payload = by_member.get(normalized)
            if payload is None:
                unresolved_members[split_name].append(normalized)
            else:
                resolved_members[split_name][normalized] = payload
    return {
        "status": "resolved",
        "member_type": paper.member_type,
        "resolved_members": resolved_members,
        "unresolved_members": unresolved_members,
    }


def _metrics_from_member_resolution(
    paper: PaperClaim,
    member_resolution: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    empty_metrics = {
        "direct_overlap_count": 0,
        "accession_root_overlap_count": 0,
        "uniref100_overlap_count": 0,
        "uniref90_overlap_count": 0,
        "uniref50_overlap_count": 0,
        "shared_partner_overlap_count": 0,
        "train_resolved_count": 0,
        "test_resolved_count": 0,
        "train_unresolved_count": len(paper.train_members),
        "test_unresolved_count": len(paper.test_members),
    }
    if member_resolution.get("status") != "resolved":
        return empty_metrics, []

    train_members = dict(member_resolution["resolved_members"]["train"])
    test_members = dict(member_resolution["resolved_members"]["test"])
    train_ids = set(train_members)
    test_ids = set(test_members)
    train_accession_roots = {
        item
        for payload in train_members.values()
        for item in payload.get("accession_roots", [])
    }
    test_accession_roots = {
        item for payload in test_members.values() for item in payload.get("accession_roots", [])
    }
    train_uniref100 = {
        item for payload in train_members.values() for item in payload.get("uniref100_clusters", [])
    }
    test_uniref100 = {
        item for payload in test_members.values() for item in payload.get("uniref100_clusters", [])
    }
    train_uniref90 = {
        item for payload in train_members.values() for item in payload.get("uniref90_clusters", [])
    }
    test_uniref90 = {
        item for payload in test_members.values() for item in payload.get("uniref90_clusters", [])
    }
    train_uniref50 = {
        item for payload in train_members.values() for item in payload.get("uniref50_clusters", [])
    }
    test_uniref50 = {
        item for payload in test_members.values() for item in payload.get("uniref50_clusters", [])
    }
    train_accessions = {
        item for payload in train_members.values() for item in payload.get("accessions", [])
    }
    test_accessions = {
        item for payload in test_members.values() for item in payload.get("accessions", [])
    }
    shared_partner_overlap = train_accessions & test_accessions
    metrics = {
        "direct_overlap_count": len(train_ids & test_ids),
        "accession_root_overlap_count": len(train_accession_roots & test_accession_roots),
        "uniref100_overlap_count": len(train_uniref100 & test_uniref100),
        "uniref90_overlap_count": len(train_uniref90 & test_uniref90),
        "uniref50_overlap_count": len(train_uniref50 & test_uniref50),
        "shared_partner_overlap_count": len(shared_partner_overlap),
        "train_resolved_count": len(train_ids),
        "test_resolved_count": len(test_ids),
        "train_unresolved_count": len(member_resolution["unresolved_members"]["train"]),
        "test_unresolved_count": len(member_resolution["unresolved_members"]["test"]),
    }
    leakage_flags: list[str] = []
    if metrics["direct_overlap_count"] > 0:
        leakage_flags.append("direct_overlap")
    if metrics["accession_root_overlap_count"] > 0:
        leakage_flags.append("accession_root_overlap")
    if any(
        metrics[name] > 0
        for name in ("uniref100_overlap_count", "uniref90_overlap_count", "uniref50_overlap_count")
    ):
        leakage_flags.append("uniref_cluster_overlap")
    if metrics["shared_partner_overlap_count"] > 0:
        leakage_flags.append("shared_partner_overlap")
    return metrics, leakage_flags


def _mapping_confidence(paper: PaperClaim, member_resolution: dict[str, Any]) -> str:
    if member_resolution.get("status") == "resolved":
        resolved_total = sum(
            len(member_resolution["resolved_members"][split_name])
            for split_name in ("train", "val", "test")
        )
        unresolved_total = sum(
            len(member_resolution["unresolved_members"][split_name])
            for split_name in ("train", "val", "test")
        )
        if resolved_total and not unresolved_total:
            return "high"
        if resolved_total:
            return "medium"
        return "low"
    if paper.named_entities or paper.source_families:
        return "medium"
    return "low"


def _source_family_findings(
    paper: PaperClaim,
    snapshot: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    source_lookup = dict(snapshot.get("source_lookup") or {})
    profile = dict(snapshot.get("profile") or {})
    findings: list[str] = []
    warnings: list[str] = []
    reason_codes: list[str] = []
    for family in paper.source_families:
        normalized = normalize_source_family_name(family)
        source_row = source_lookup.get(normalized)
        if source_row is None:
            reason_codes.append("WAREHOUSE_COVERAGE_GAP")
            warnings.append(
                f"Source family `{family}` is not materialized in `warehouse_sources`."
            )
            continue
        findings.append(
            f"{source_row['source_name']} is present with scope tier `{source_row['scope_tier']}` and license scope `{source_row['license_scope']}`."
        )
        if not source_row["public_export_allowed"] or not source_row["redistributable"]:
            reason_codes.append("AUDIT_ONLY_EVIDENCE")
            warnings.append(
                f"{source_row['source_name']} remains audit-facing or non-redistributable in the condensed library."
            )
        availability_status = str(source_row.get("availability_status") or "").strip().casefold()
        if availability_status and availability_status not in {
            "promoted",
            "ready",
            "active",
            "beta",
            "present",
        }:
            reason_codes.append("CANDIDATE_ONLY_NON_GOVERNING")
            warnings.append(
                f"{source_row['source_name']} is currently `{availability_status}` and should not govern training decisions."
            )
    if paper.task_group == "ppi_prediction":
        ppi_sources = set((profile.get("ppi_sources") or {}).keys())
        expected = {
            normalize_source_family_name(item) for item in paper.source_families if item
        }
        if expected & {"intact", "string"} and not (ppi_sources & {"intact", "string"}):
            reason_codes.append("WAREHOUSE_COVERAGE_GAP")
            warnings.append(
                "The current best-evidence `protein_protein_edges` surface does not materialize IntAct/STRING benchmark roster rows."
            )
    return findings, warnings, sorted(set(reason_codes))


def _modality_status(
    paper: PaperClaim,
    member_resolution: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    structure_required = _structure_expected(paper)
    reason_codes: list[str] = []
    if member_resolution.get("status") != "resolved":
        return {
            "required_modality": paper.modality,
            "structure_required": structure_required,
            "status": "not_member_validated",
            "missing_modalities": [],
        }, reason_codes
    resolved_members = {
        member_id: payload
        for split_name in ("train", "val", "test")
        for member_id, payload in member_resolution["resolved_members"][split_name].items()
    }
    missing_structures = sorted(
        member_id for member_id, payload in resolved_members.items() if not payload.get("has_structure")
    )
    status = "complete"
    if structure_required and missing_structures:
        status = "incomplete"
        reason_codes.append("INCOMPLETE_MODALITY_COVERAGE")
    return {
        "required_modality": paper.modality,
        "structure_required": structure_required,
        "status": status,
        "missing_modalities": ["structure"] if missing_structures else [],
        "missing_structure_members": missing_structures,
    }, reason_codes


def _provenance_grade(
    paper: PaperClaim,
    member_resolution: dict[str, Any],
    source_reason_codes: list[str],
) -> str:
    if member_resolution.get("status") == "resolved" and not any(
        code in source_reason_codes for code in ("WAREHOUSE_COVERAGE_GAP", "AUDIT_ONLY_EVIDENCE")
    ):
        return "strong"
    if _split_parse_confidence(paper) == "high":
        return "acceptable"
    if paper.claimed_split_description and paper.source_families:
        return "weak"
    return "insufficient"


def _reason_codes(
    paper: PaperClaim,
    member_resolution: dict[str, Any],
    overlap_metrics: dict[str, Any],
    source_reason_codes: list[str],
    modality_reason_codes: list[str],
    provenance_grade: str,
) -> list[str]:
    reason_codes = set(source_reason_codes)
    if member_resolution.get("status") in {"catalog_missing", "unsupported_member_type"}:
        reason_codes.add("UNRESOLVED_ENTITY_MAPPING")
    if member_resolution.get("status") == "resolved":
        if overlap_metrics["train_unresolved_count"] or overlap_metrics["test_unresolved_count"]:
            reason_codes.add("UNRESOLVED_ENTITY_MAPPING")
        if overlap_metrics["direct_overlap_count"] > 0:
            reason_codes.add("DIRECT_OVERLAP")
        if overlap_metrics["accession_root_overlap_count"] > 0:
            reason_codes.add("ACCESSION_ROOT_OVERLAP")
        if any(
            overlap_metrics[name] > 0
            for name in ("uniref100_overlap_count", "uniref90_overlap_count", "uniref50_overlap_count")
        ):
            reason_codes.add("UNIREF_CLUSTER_OVERLAP")
        if overlap_metrics["shared_partner_overlap_count"] > 0:
            reason_codes.add("SHARED_PARTNER_LEAKAGE")
    else:
        if not (paper.train_members or paper.test_members or paper.val_members):
            reason_codes.add("UNRESOLVED_SPLIT_MEMBERSHIP")
    if paper.split_style == "cross_validation":
        reason_codes.add("POLICY_MISMATCH")
    if provenance_grade in {"weak", "insufficient"}:
        reason_codes.add("INSUFFICIENT_PROVENANCE")
    reason_codes.update(modality_reason_codes)
    return [code for code in CANONICAL_REASON_CODES if code in reason_codes]


def _eligibility_status(reason_codes: list[str]) -> str:
    if any(code in reason_codes for code in ("DIRECT_OVERLAP", "POLICY_MISMATCH")):
        return "unsafe_for_training"
    if any(code in reason_codes for code in ("UNRESOLVED_ENTITY_MAPPING", "UNRESOLVED_SPLIT_MEMBERSHIP")):
        return "audit_only"
    if any(code in reason_codes for code in ("AUDIT_ONLY_EVIDENCE", "CANDIDATE_ONLY_NON_GOVERNING")):
        return "candidate_only"
    return "training_eligible"


def _verdict(
    paper: PaperClaim,
    reason_codes: list[str],
    split_parse_confidence: str,
    supplemental_evidence: dict[str, Any] | None = None,
) -> str:
    codes = set(reason_codes)
    resolved_policy = _resolved_split_policy(paper.split_style)
    if codes & {"DIRECT_OVERLAP", "ACCESSION_ROOT_OVERLAP", "UNIREF_CLUSTER_OVERLAP", "SHARED_PARTNER_LEAKAGE", "POLICY_MISMATCH"}:
        return "unsafe_for_training"
    if "UNRESOLVED_ENTITY_MAPPING" in codes:
        return "blocked_pending_mapping"
    if "UNRESOLVED_SPLIT_MEMBERSHIP" in codes:
        if resolved_policy == "uniref_grouped" and split_parse_confidence != "low":
            return "audit_only"
        if (
            resolved_policy == "paper_faithful_external"
            and split_parse_confidence != "low"
            and (paper.split_style == "external_holdout" or supplemental_evidence)
        ):
            return "audit_only"
        return "blocked_pending_mapping"
    if codes & {"INCOMPLETE_MODALITY_COVERAGE", "INSUFFICIENT_PROVENANCE", "AUDIT_ONLY_EVIDENCE", "CANDIDATE_ONLY_NON_GOVERNING"}:
        return "usable_with_caveats"
    return "usable"


def _needs_human_review(
    split_parse_confidence: str,
    provenance_grade: str,
    reason_codes: list[str],
    resolved_policy: dict[str, Any],
    verdict: str,
) -> bool:
    codes = set(reason_codes)
    deterministic_rule_failure = bool(
        "POLICY_MISMATCH" in codes
        or verdict in {"blocked_pending_mapping", "unsafe_for_training"}
        or (
            verdict == "audit_only"
            and resolved_policy.get("policy") in {"paper_faithful_external", "uniref_grouped"}
            and "UNRESOLVED_SPLIT_MEMBERSHIP" in codes
        )
    )
    if deterministic_rule_failure:
        return False
    return (
        split_parse_confidence == "low"
        or provenance_grade == "insufficient"
        or resolved_policy.get("policy") == "unresolved_policy"
    )


def _messages_for_reason_codes(reason_codes: list[str]) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    for code in reason_codes:
        message = REASON_MESSAGES.get(code, code)
        if code in BLOCKER_REASON_CODES:
            blockers.append(message)
        else:
            warnings.append(message)
    return blockers, warnings


def _policy_payload(split_style: str) -> dict[str, Any]:
    policy = _resolved_split_policy(split_style)
    return {
        "policy": policy,
        "reason": option_reason("split_strategies", policy) if policy != "unresolved_policy" else "No canonical ProteoSphere split policy could be resolved from the supplied paper description.",
        "recommended_for_training": policy in {"accession_grouped", "uniref_grouped"},
        "paper_faithful_only": policy == "paper_faithful_external",
    }


def evaluate_paper_corpus(
    corpus_payload: dict[str, Any],
    warehouse_snapshot: dict[str, Any],
) -> dict[str, Any]:
    papers = [_paper_claim_from_dict(item) for item in corpus_payload.get("papers") or []]
    evaluated = [evaluate_paper_record(paper, warehouse_snapshot) for paper in papers]
    verdict_counts = dict(sorted(Counter(item["verdict"] for item in evaluated).items()))
    reason_code_counts = dict(
        sorted(Counter(code for item in evaluated for code in item["reason_codes"]).items())
    )
    human_review_count = sum(1 for item in evaluated if item["needs_human_review"])
    return {
        "artifact_id": "paper_dataset_evaluator_report",
        "schema_id": "proteosphere-paper-dataset-evaluator-report-v1",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "warehouse_root": str(warehouse_snapshot.get("warehouse_root") or ""),
        "catalog_path": str(warehouse_snapshot.get("catalog_path") or ""),
        "default_view": str(warehouse_snapshot.get("default_view") or "best_evidence"),
        "corpus_artifact_id": str(corpus_payload.get("artifact_id") or ""),
        "cohorts": dict(corpus_payload.get("cohorts") or {}),
        "summary": {
            "paper_count": len(evaluated),
            "verdict_counts": verdict_counts,
            "reason_code_counts": reason_code_counts,
            "needs_human_review_count": human_review_count,
        },
        "papers": evaluated,
    }


def evaluate_explicit_manifest(
    manifest_payload: dict[str, Any],
    warehouse_snapshot: dict[str, Any],
) -> dict[str, Any]:
    manifest = dict(manifest_payload or {})
    validation = dict(manifest.get("validation") or {})
    split_counts = dict(validation.get("split_counts") or {})
    unresolved_rows = int(validation.get("unresolved_rows") or 0)
    total_rows = int(validation.get("total_uploaded_rows") or manifest.get("row_count") or 0)
    grounding_coverage = float(validation.get("grounding_coverage") or 0.0)
    unresolved_entities = list(validation.get("unresolved_entities") or [])
    unresolved_record_ids = list(validation.get("unresolved_record_ids") or [])
    resolution = dict(validation.get("warehouse_resolution") or {})
    uniref_by_accession = dict(resolution.get("uniref_by_accession") or {})
    source_manifest_text = str(manifest.get("source_manifest") or "").strip()
    source_manifest_path = Path(source_manifest_text) if source_manifest_text else None
    source_manifest = (
        _load_json(source_manifest_path)
        if source_manifest_path is not None and source_manifest_path.is_file()
        else {}
    )
    source_records = source_manifest.get("records") or manifest.get("records") or []

    split_accessions: dict[str, set[str]] = {"train": set(), "val": set(), "test": set()}
    for record in source_records:
        if not isinstance(record, dict):
            continue
        split = str(record.get("split") or "").strip().lower()
        if split not in split_accessions:
            continue
        accessions = {
            *(str(item).strip() for item in record.get("protein_accessions", []) if str(item).strip()),
            *([str(record.get("protein_a") or "").strip()] if str(record.get("protein_a") or "").strip() else []),
            *([str(record.get("protein_b") or "").strip()] if str(record.get("protein_b") or "").strip() else []),
        }
        split_accessions[split].update(item for item in accessions if item)

    test_and_holdout_accessions = split_accessions["test"] | split_accessions["val"]
    direct_overlap = len(split_accessions["train"] & test_and_holdout_accessions)
    train_uniref = {
        uniref_by_accession.get(accession, "")
        for accession in split_accessions["train"]
        if uniref_by_accession.get(accession, "")
    }
    holdout_uniref = {
        uniref_by_accession.get(accession, "")
        for accession in test_and_holdout_accessions
        if uniref_by_accession.get(accession, "")
    }
    uniref_overlap = len(train_uniref & holdout_uniref)
    overlap_metrics = {
        "direct_overlap_count": direct_overlap,
        "accession_root_overlap_count": direct_overlap,
        "uniref_cluster_overlap_count": uniref_overlap,
        "shared_partner_overlap_count": direct_overlap,
        "grounded_row_count": max(total_rows - unresolved_rows, 0),
        "total_row_count": total_rows,
        "train_count": int(split_counts.get("train") or 0),
        "val_count": int(split_counts.get("val") or 0),
        "test_count": int(split_counts.get("test") or 0),
    }
    leakage_flags = []
    if direct_overlap:
        leakage_flags.append("shared_explicit_accessions")
    if uniref_overlap:
        leakage_flags.append("shared_uniref_clusters")

    provenance_note_count = sum(
        1
        for record in source_records
        if isinstance(record, dict) and str(record.get("provenance_note") or "").strip()
    )
    provenance_grade = (
        "strong"
        if total_rows and provenance_note_count == total_rows
        else "acceptable"
        if provenance_note_count
        else "weak"
    )
    modality_status = {
        "complete": unresolved_rows == 0,
        "missing_modalities": [] if unresolved_rows == 0 else ["grounding"],
        "entity_kind": manifest.get("entity_kind") or "unknown",
    }
    reason_codes: list[str] = []
    if unresolved_rows or unresolved_entities:
        reason_codes.append("UNRESOLVED_ENTITY_MAPPING")
    if direct_overlap:
        reason_codes.extend(["DIRECT_OVERLAP", "ACCESSION_ROOT_OVERLAP", "SHARED_PARTNER_LEAKAGE"])
    if uniref_overlap:
        reason_codes.append("UNIREF_CLUSTER_OVERLAP")
    if provenance_grade == "weak":
        reason_codes.append("INSUFFICIENT_PROVENANCE")
    if unresolved_rows:
        reason_codes.append("WAREHOUSE_COVERAGE_GAP")
    reason_codes = [code for code in CANONICAL_REASON_CODES if code in set(reason_codes)]

    if unresolved_rows:
        verdict = "blocked_pending_mapping"
    elif direct_overlap or uniref_overlap:
        verdict = "unsafe_for_training"
    elif provenance_grade == "weak":
        verdict = "usable_with_caveats"
    else:
        verdict = "usable"

    blockers, warnings = _messages_for_reason_codes(reason_codes)
    warnings = list(dict.fromkeys([*warnings, *(validation.get("warnings") or [])]))
    blockers = list(dict.fromkeys([*blockers, *(validation.get("blockers") or [])]))
    recommended_next_action = (
        "Fix unresolved identifiers and re-import the manifest before building a study dataset."
        if verdict == "blocked_pending_mapping"
        else "Revise the split to remove overlap between train and held-out members."
        if verdict == "unsafe_for_training"
        else "Add stronger provenance notes before treating this split as a stable recreation target."
        if verdict == "usable_with_caveats"
        else "Proceed with preview/build and compare the resulting run against the intended study."
    )
    return {
        "artifact_id": "custom_split_assessment",
        "schema_id": "proteosphere-custom-split-assessment-v1",
        "evaluation_mode": "explicit_manifest",
        "manifest_id": manifest.get("manifest_id"),
        "dataset_ref": manifest.get("dataset_ref"),
        "title": manifest.get("label") or manifest.get("title") or manifest.get("manifest_id"),
        "claimed_split_policy": "explicit_manifest",
        "resolved_split_policy": {"policy": "explicit_manifest", "rationale": "Uploaded manifest membership is treated as explicit split truth."},
        "mapping_confidence": "high" if grounding_coverage >= 0.95 else "medium" if grounding_coverage >= 0.75 else "low",
        "split_parse_confidence": "high",
        "provenance_grade": provenance_grade,
        "grounding_coverage": grounding_coverage,
        "overlap_metrics": overlap_metrics,
        "leakage_flags": leakage_flags,
        "modality_status": modality_status,
        "eligibility_status": "training_eligible" if verdict == "usable" else "review_required",
        "verdict": verdict,
        "reason_codes": reason_codes,
        "warnings": warnings,
        "blockers": blockers,
        "needs_human_review": False,
        "recommended_next_action": recommended_next_action,
        "provenance_notes": [
            "Primary evidence came from the condensed warehouse catalog and explicit uploaded split membership.",
            "best_evidence was treated as the default logical read view.",
            f"Warehouse root: {warehouse_snapshot.get('warehouse_root') or ''}",
        ],
        "unresolved_entities": unresolved_entities,
        "unresolved_record_ids": unresolved_record_ids,
    }


def evaluate_paper_record(paper: PaperClaim, warehouse_snapshot: dict[str, Any]) -> dict[str, Any]:
    existing_audit = _load_existing_paper_audit(paper.paper_id)
    supplemental_evidence = dict(existing_audit.get("supplemental_evidence") or {})
    warehouse_audit_surface = dict(existing_audit.get("warehouse_audit_surface") or {})
    warehouse_identifier_bridge = dict(existing_audit.get("warehouse_identifier_bridge") or {})
    identifier_bridge_requirements = list(warehouse_audit_surface.get("identifier_bridge_requirements") or [])
    split_parse_confidence = _split_parse_confidence(paper)
    mapping_input_completeness = _mapping_input_completeness(paper)
    member_resolution = _resolve_member_roster(paper, warehouse_snapshot)
    overlap_metrics, leakage_flags = _metrics_from_member_resolution(paper, member_resolution)
    source_findings, source_warnings, source_reason_codes = _source_family_findings(
        paper,
        warehouse_snapshot,
    )
    modality_status, modality_reason_codes = _modality_status(paper, member_resolution)
    provenance_grade = _provenance_grade(
        paper,
        member_resolution,
        source_reason_codes,
    )
    reason_codes = _reason_codes(
        paper,
        member_resolution,
        overlap_metrics,
        source_reason_codes,
        modality_reason_codes,
        provenance_grade,
    )
    blockers, warnings = _messages_for_reason_codes(reason_codes)
    warnings.extend(item for item in source_warnings if item not in warnings)
    claimed_policy = _claimed_split_policy(paper.split_style)
    resolved_policy = _policy_payload(paper.split_style)
    eligibility_status = _eligibility_status(reason_codes)
    verdict = _verdict(paper, reason_codes, split_parse_confidence, supplemental_evidence)
    needs_human_review = _needs_human_review(
        split_parse_confidence,
        provenance_grade,
        reason_codes,
        resolved_policy,
        verdict,
    )
    provenance_notes = [
        "Primary evidence came from the condensed warehouse catalog, manifest, runtime validation artifact, source registry, and Model Studio split-policy logic.",
        "best_evidence was treated as the default logical read view.",
    ]
    if member_resolution.get("status") == "resolved":
        provenance_notes.append("Explicit train/test members were resolved against warehouse tables directly.")
    else:
        provenance_notes.append("No explicit roster was resolved, so the verdict relies on paper-level claims plus warehouse capabilities.")
    if supplemental_evidence:
        provenance_notes.append(
            "Previously recovered paper-specific audit artifacts were reused as supplemental evidence without reopening raw/archive roots."
        )
    if warehouse_audit_surface:
        provenance_notes.append(
            "A warehouse-facing paper split audit surface is available under the reference library control root."
        )
    if warehouse_identifier_bridge:
        provenance_notes.append(
            "A warehouse-facing identifier bridge summary is available under the reference library control root."
        )
    return {
        "paper_id": paper.paper_id,
        "title": paper.title,
        "doi": paper.doi,
        "task_group": paper.task_group,
        "claimed_dataset": paper.claimed_dataset,
        "claimed_split": {
            "description": paper.claimed_split_description,
            "style": paper.split_style,
            "member_type": paper.member_type or "unspecified",
            "train_member_count": len(paper.train_members),
            "val_member_count": len(paper.val_members),
            "test_member_count": len(paper.test_members),
            "mapping_input_completeness": mapping_input_completeness,
        },
        "claimed_split_policy": claimed_policy,
        "resolved_split_policy": resolved_policy,
        "mapping_confidence": _mapping_confidence(paper, member_resolution),
        "split_parse_confidence": split_parse_confidence,
        "provenance_grade": provenance_grade,
        "overlap_metrics": overlap_metrics,
        "leakage_flags": leakage_flags,
        "modality_status": modality_status,
        "eligibility_status": eligibility_status,
        "verdict": verdict,
        "reason_codes": reason_codes,
        "warnings": warnings,
        "blockers": blockers,
        "needs_human_review": needs_human_review,
        "provenance_notes": provenance_notes,
        "source_family_findings": source_findings,
        "member_resolution": member_resolution,
        "named_entities": list(paper.named_entities),
        "notes": list(paper.notes),
        "supplemental_evidence": supplemental_evidence or None,
        "warehouse_audit_surface": warehouse_audit_surface or None,
        "warehouse_identifier_bridge": warehouse_identifier_bridge or None,
        "identifier_bridge_requirements": identifier_bridge_requirements,
    }


def render_evaluation_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Paper Dataset Evaluator Report",
        "",
        f"- Generated at: {report.get('generated_at', '')}",
        f"- Warehouse root: `{report.get('warehouse_root', '')}`",
        f"- Default view: `{report.get('default_view', 'best_evidence')}`",
        "",
        "## Summary",
        "",
        f"- Paper count: `{report.get('summary', {}).get('paper_count', 0)}`",
        f"- Needs human review: `{report.get('summary', {}).get('needs_human_review_count', 0)}`",
        "",
        "## Summary Table",
        "",
        "| Paper | Verdict | Reasons | Resolved policy | Human review |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report.get("papers", []):
        lines.append(
            f"| `{row['paper_id']}` | `{row['verdict']}` | `{', '.join(row['reason_codes']) or 'none'}` | `{row['resolved_split_policy']['policy']}` | `{str(bool(row['needs_human_review'])).lower()}` |"
        )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in report.get("papers", []):
        grouped[row["verdict"]].append(row)
    for verdict in (
        "usable",
        "usable_with_caveats",
        "audit_only",
        "blocked_pending_mapping",
        "blocked_pending_cleanup",
        "unsafe_for_training",
    ):
        items = grouped.get(verdict) or []
        if not items:
            continue
        lines.extend(["", f"## {verdict}", ""])
        for row in items:
            lines.append(
                f"- `{row['paper_id']}`: reasons=`{', '.join(row['reason_codes']) or 'none'}`; policy=`{row['resolved_split_policy']['policy']}`; human_review=`{str(bool(row['needs_human_review'])).lower()}`."
            )
    return "\n".join(lines) + "\n"

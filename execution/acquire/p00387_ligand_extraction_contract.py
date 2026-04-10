from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_CHEMBL_PATH = Path(
    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db"
)

CONTRACT_SCHEMA_ID = "proteosphere-p00387-ligand-extraction-contract-2026-03-23"

TABLE_ROLE_COLUMNS: tuple[dict[str, Any], ...] = (
    {
        "table": "component_sequences",
        "role": "accession anchor",
        "join_columns": ["component_id", "accession"],
        "candidate_columns": [
            "component_id",
            "accession",
            "sequence",
            "description",
            "tax_id",
            "organism",
            "db_source",
            "db_version",
        ],
    },
    {
        "table": "target_components",
        "role": "component-to-target bridge",
        "join_columns": ["component_id", "tid"],
        "candidate_columns": ["component_id", "tid", "targcomp_id", "homologue"],
    },
    {
        "table": "target_dictionary",
        "role": "target identity",
        "join_columns": ["tid", "chembl_id"],
        "candidate_columns": [
            "tid",
            "target_type",
            "pref_name",
            "tax_id",
            "organism",
            "chembl_id",
            "species_group_flag",
        ],
    },
    {
        "table": "assays",
        "role": "assay grain",
        "join_columns": ["tid", "assay_id"],
        "candidate_columns": [
            "assay_id",
            "doc_id",
            "description",
            "assay_type",
            "assay_test_type",
            "assay_category",
            "assay_organism",
            "assay_tax_id",
            "assay_strain",
            "assay_tissue",
            "assay_cell_type",
            "assay_subcellular_fraction",
            "tid",
            "relationship_type",
            "confidence_score",
            "curated_by",
            "src_id",
            "src_assay_id",
            "chembl_id",
            "cell_id",
            "bao_format",
            "tissue_id",
            "variant_id",
            "aidx",
            "assay_group",
        ],
    },
    {
        "table": "activities",
        "role": "activity grain",
        "join_columns": ["assay_id", "activity_id"],
        "candidate_columns": [
            "activity_id",
            "assay_id",
            "doc_id",
            "record_id",
            "molregno",
            "standard_relation",
            "standard_value",
            "standard_units",
            "standard_flag",
            "standard_type",
            "activity_comment",
            "data_validity_comment",
            "potential_duplicate",
            "pchembl_value",
            "bao_endpoint",
            "uo_units",
            "qudt_units",
            "toid",
            "upper_value",
            "standard_upper_value",
            "src_id",
            "type",
            "relation",
            "value",
            "units",
            "text_value",
            "standard_text_value",
            "action_type",
        ],
    },
)

JOIN_CHAIN: tuple[dict[str, str], ...] = (
    {
        "from_table": "component_sequences",
        "from_column": "component_id",
        "to_table": "target_components",
        "to_column": "component_id",
        "purpose": "carry the P00387 accession into the target bridge",
    },
    {
        "from_table": "target_components",
        "from_column": "tid",
        "to_table": "target_dictionary",
        "to_column": "tid",
        "purpose": "resolve the ChEMBL target identity",
    },
    {
        "from_table": "target_dictionary",
        "from_column": "tid",
        "to_table": "assays",
        "to_column": "tid",
        "purpose": "count the assays tied to the target",
    },
    {
        "from_table": "assays",
        "from_column": "assay_id",
        "to_table": "activities",
        "to_column": "assay_id",
        "purpose": "count the activity records tied to those assays",
    },
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _table_names(path: Path) -> tuple[str, ...]:
    if not path.exists():
        return ()
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        return tuple(
            row[0]
            for row in cur.execute(
                "select name from sqlite_master where type='table' order by name"
            ).fetchall()
        )
    except sqlite3.DatabaseError:
        return ()
    finally:
        conn.close()


def _table_columns(path: Path, table: str) -> tuple[str, ...]:
    if not path.exists():
        return ()
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        return tuple(row[1] for row in cur.execute(f"pragma table_info({table})").fetchall())
    except sqlite3.DatabaseError:
        return ()
    finally:
        conn.close()


def _query_target_hits(path: Path, accession: str) -> tuple[dict[str, Any], ...]:
    if not path.exists():
        return ()
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        tables = {
            row[0]
            for row in cur.execute(
                "select name from sqlite_master where type='table' order by name"
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


def _candidate_table_payload(path: Path) -> tuple[dict[str, Any], ...]:
    payload: list[dict[str, Any]] = []
    for role_entry in TABLE_ROLE_COLUMNS:
        table_name = str(role_entry["table"])
        observed_columns = _table_columns(path, table_name)
        payload.append(
            {
                "table": table_name,
                "role": role_entry["role"],
                "join_columns": list(role_entry["join_columns"]),
                "candidate_columns": list(role_entry["candidate_columns"]),
                "observed_columns": list(observed_columns),
                "present_candidate_columns": [
                    column
                    for column in role_entry["candidate_columns"]
                    if column in observed_columns
                ],
            }
        )
    return tuple(payload)


def _expected_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "required": [
            "schema_id",
            "report_type",
            "generated_at",
            "accession",
            "source_db_path",
            "candidate_tables",
            "join_chain",
            "live_signal",
            "expected_output_schema",
            "success_criteria",
            "blockers",
            "truth_boundary_notes",
        ],
        "properties": {
            "schema_id": {"type": "string"},
            "report_type": {"type": "string"},
            "generated_at": {"type": "string"},
            "accession": {"type": "string"},
            "source_db_path": {"type": "string"},
            "candidate_tables": {"type": "array"},
            "join_chain": {"type": "array"},
            "live_signal": {"type": "object"},
            "expected_output_schema": {"type": "object"},
            "success_criteria": {"type": "array"},
            "blockers": {"type": "array"},
            "truth_boundary_notes": {"type": "array"},
            "next_step": {"type": "object"},
        },
    }


def build_p00387_ligand_extraction_contract(
    *,
    accession: str = "P00387",
    chembl_path: Path = DEFAULT_CHEMBL_PATH,
    output_path: Path | None = None,
) -> dict[str, Any]:
    normalized_accession = _clean_text(accession).upper()
    target_hits = _query_target_hits(chembl_path, normalized_accession)
    selected_target = target_hits[0] if target_hits else None
    total_activity_count = sum(int(hit.get("activity_count") or 0) for hit in target_hits)
    contract_ready = bool(target_hits)
    blockers = (
        []
        if contract_ready
        else [
            "no_local_chembl_accession_hit",
            "hold_for_fresh_acquisition_or_schema_repair",
        ]
    )

    payload: dict[str, Any] = {
        "schema_id": CONTRACT_SCHEMA_ID,
        "report_type": "p00387_ligand_extraction_contract",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "accession": normalized_accession,
        "contract_status": "ready_for_next_step" if contract_ready else "blocked",
        "rescue_claim": {
            "permitted": False,
            "reason": "planning-grade local ChEMBL signal only",
        },
        "source_db_path": str(chembl_path),
        "source_db_exists": chembl_path.exists(),
        "source_table_names": list(_table_names(chembl_path)),
        "candidate_tables": list(_candidate_table_payload(chembl_path)),
        "join_chain": list(JOIN_CHAIN),
        "live_signal": {
            "target_hit_count": len(target_hits),
            "activity_count": total_activity_count,
            "target_hits": list(target_hits),
            "selected_target_hit": selected_target,
            "planning_grade": contract_ready,
        },
        "expected_output_schema": _expected_output_schema(),
        "success_criteria": [
            "the local ChEMBL accession join stays accession-clean for P00387",
            "the contract records the source DB path, candidate tables, and join chain",
            (
                "the next-step output preserves the boundary between planning signal and "
                "rescue completion"
            ),
            (
                "any follow-on extraction can materialize a ligand-lane artifact without "
                "asserting completion"
            ),
        ],
        "blockers": blockers,
        "truth_boundary_notes": [
            "this artifact is planning-grade and does not claim ligand rescue is complete",
            "a ChEMBL target hit confirms local target evidence, not canonical assay resolution",
            (
                "activity counts are evidence volume only and do not imply potency, "
                "selectivity, or readiness to promote"
            ),
            (
                "the rescue claim stays false until a downstream ligand extraction lane "
                "is validated separately"
            ),
        ],
        "next_step": {
            "name": "bounded_p00387_ligand_extraction",
            "description": (
                "Use the local ChEMBL hit as the starting point for a bounded ligand "
                "extraction pass, then validate whether the result can support a truthful "
                "ligand lane without promotion claims."
            ),
            "do_not_claim": [
                "rescue complete",
                "canonical assay resolution",
                "packet promotion",
            ],
        },
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return payload


__all__ = ["build_p00387_ligand_extraction_contract"]

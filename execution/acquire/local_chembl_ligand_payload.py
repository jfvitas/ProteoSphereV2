from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_CHEMBL_PATH = Path(
    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db"
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _query_target_rows(
    path: Path,
    accession: str,
    *,
    max_rows: int,
) -> tuple[dict[str, Any], ...]:
    if not path.exists():
        return ()
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        rows = cur.execute(
            """
            select
                seq.accession,
                td.chembl_id as target_chembl_id,
                td.pref_name as target_pref_name,
                a.assay_id,
                a.assay_type,
                a.description,
                act.activity_id,
                act.standard_type,
                act.standard_relation,
                act.standard_value,
                act.standard_units,
                act.pchembl_value,
                md.molregno,
                md.chembl_id as ligand_chembl_id,
                md.pref_name as ligand_pref_name,
                md.max_phase,
                md.molecule_type,
                cs.canonical_smiles,
                cp.full_mwt,
                cp.alogp,
                cp.qed_weighted
            from component_sequences seq
            join target_components tc on tc.component_id = seq.component_id
            join target_dictionary td on td.tid = tc.tid
            join assays a on a.tid = td.tid
            join activities act on act.assay_id = a.assay_id
            join molecule_dictionary md on md.molregno = act.molregno
            left join compound_structures cs on cs.molregno = md.molregno
            left join compound_properties cp on cp.molregno = md.molregno
            where seq.accession = ?
            order by
                case when act.pchembl_value is null then 1 else 0 end,
                act.pchembl_value desc,
                case when act.standard_value is null then 1 else 0 end,
                act.standard_value asc,
                md.chembl_id asc
            limit ?
            """,
            (accession, max_rows),
        ).fetchall()
        return tuple(
            {
                "accession": _clean_text(row[0]).upper(),
                "target_chembl_id": _clean_text(row[1]),
                "target_pref_name": _clean_text(row[2]),
                "assay_id": int(row[3]) if row[3] is not None else None,
                "assay_type": _clean_text(row[4]),
                "assay_description": _clean_text(row[5]),
                "activity_id": int(row[6]) if row[6] is not None else None,
                "standard_type": _clean_text(row[7]),
                "standard_relation": _clean_text(row[8]),
                "standard_value": row[9],
                "standard_units": _clean_text(row[10]),
                "pchembl_value": row[11],
                "molregno": int(row[12]) if row[12] is not None else None,
                "ligand_chembl_id": _clean_text(row[13]),
                "ligand_pref_name": _clean_text(row[14]),
                "ligand_max_phase": int(row[15]) if row[15] is not None else None,
                "ligand_molecule_type": _clean_text(row[16]),
                "canonical_smiles": _clean_text(row[17]),
                "full_mwt": row[18],
                "alogp": row[19],
                "qed_weighted": row[20],
            }
            for row in rows
        )
    except sqlite3.DatabaseError:
        return ()
    finally:
        conn.close()


def _query_activity_count(path: Path, accession: str) -> int:
    if not path.exists():
        return 0
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        row = cur.execute(
            """
            select count(distinct act.activity_id)
            from component_sequences seq
            join target_components tc on tc.component_id = seq.component_id
            join target_dictionary td on td.tid = tc.tid
            join assays a on a.tid = td.tid
            join activities act on act.assay_id = a.assay_id
            where seq.accession = ?
            """,
            (accession,),
        ).fetchone()
        return int((row or [0])[0] or 0)
    except sqlite3.DatabaseError:
        return 0
    finally:
        conn.close()


def build_local_chembl_ligand_payload(
    *,
    accession: str = "P00387",
    chembl_path: Path = DEFAULT_CHEMBL_PATH,
    max_rows: int = 25,
    output_path: Path | None = None,
) -> dict[str, Any]:
    normalized_accession = _clean_text(accession).upper()
    rows = _query_target_rows(chembl_path, normalized_accession, max_rows=max_rows)
    activity_count = _query_activity_count(chembl_path, normalized_accession)
    unique_ligands = {
        row["ligand_chembl_id"]
        for row in rows
        if _clean_text(row.get("ligand_chembl_id"))
    }
    unique_assays = {
        row["assay_id"]
        for row in rows
        if row.get("assay_id") is not None
    }
    top_row = rows[0] if rows else {}
    payload: dict[str, Any] = {
        "schema_id": "proteosphere-local-chembl-ligand-payload-2026-03-31",
        "report_type": "local_chembl_ligand_payload",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "accession": normalized_accession,
        "packet_source_ref": f"ligand:{normalized_accession}",
        "source_db_path": str(chembl_path),
        "status": "resolved" if rows else "no_local_ligand_payload",
        "truth_boundary": {
            "fresh_run_scope_only": True,
            "can_promote_latest_now": False,
            "canonical_assay_resolution": False,
            "notes": [
                "This payload is a local ChEMBL ligand evidence extract for fresh-run use.",
                "It does not by itself promote the protected latest packet snapshot.",
                "It does not claim canonical assay reconciliation across sources.",
            ],
        },
        "summary": {
            "target_chembl_id": _clean_text(top_row.get("target_chembl_id")),
            "target_pref_name": _clean_text(top_row.get("target_pref_name")),
            "activity_count_total": activity_count,
            "rows_emitted": len(rows),
            "distinct_ligand_count_in_payload": len(unique_ligands),
            "distinct_assay_count_in_payload": len(unique_assays),
            "top_ligand_chembl_id": _clean_text(top_row.get("ligand_chembl_id")),
            "top_ligand_pref_name": _clean_text(top_row.get("ligand_pref_name")),
        },
        "rows": list(rows),
    }
    if output_path is not None:
        _write_json(output_path, payload)
    return payload


__all__ = ["DEFAULT_CHEMBL_PATH", "build_local_chembl_ligand_payload"]

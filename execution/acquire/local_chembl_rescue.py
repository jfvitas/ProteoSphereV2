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


def _query_chembl_target_hits(path: Path, accession: str) -> tuple[dict[str, Any], ...]:
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


def build_local_chembl_rescue_brief(
    *,
    accession: str = "P00387",
    chembl_path: Path = DEFAULT_CHEMBL_PATH,
    output_path: Path | None = None,
) -> dict[str, Any]:
    target_hits = _query_chembl_target_hits(chembl_path, accession)
    local_rescue_candidate = bool(target_hits)
    activity_count = sum(int(hit.get("activity_count") or 0) for hit in target_hits)
    extraction_ready = local_rescue_candidate
    blockers = (
        []
        if local_rescue_candidate
        else ["no_local_chembl_target_hit", "fall_back_to_online_procurement"]
    )
    brief: dict[str, Any] = {
        "schema_id": "proteosphere-local-chembl-rescue-2026-03-23",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "accession": _clean_text(accession).upper(),
        "packet_source_ref": f"ligand:{_clean_text(accession).upper()}",
        "status": "local_rescue_candidate" if local_rescue_candidate else "no_local_candidate",
        "wired_into_proteosphere": {
            "discovery": True,
            "planning": True,
            "canonical_assay_resolution": False,
            "packet_promotion": False,
        },
        "evidence": {
            "source_file": str(chembl_path),
            "source_tables": [
                "component_sequences",
                "target_components",
                "target_dictionary",
                "assays",
                "activities",
            ],
            "source_columns": [
                "component_sequences.accession",
                "target_dictionary.chembl_id",
                "target_dictionary.pref_name",
                "activities.activity_id",
            ],
            "target_hits": list(target_hits),
        },
        "packet_planning_input": {
            "packet_id": f"packet-{_clean_text(accession).upper()}",
            "accession": _clean_text(accession).upper(),
            "canonical_id": f"protein:{_clean_text(accession).upper()}",
            "modality": "ligand",
            "packet_source_ref": f"ligand:{_clean_text(accession).upper()}",
            "status": "planning_only",
            "availability_hint": "local_chembl",
            "can_promote": False,
            "canonical_assay_resolution": False,
            "packet_ready": False,
            "assay_count": activity_count,
            "activity_count": activity_count,
            "target_hit_count": len(target_hits),
            "extraction_readiness": {
                "state": "ready_for_planning" if extraction_ready else "blocked",
                "can_package": extraction_ready,
                "can_promote": False,
                "canonical_assay_resolution": False,
            },
            "recommended_next_step": (
                "Prioritize ligand procurement/planning around local ChEMBL evidence"
                if extraction_ready
                else "Fall through to online procurement"
            ),
            "blockers": blockers,
        },
        "planning_note": (
            "Use this as a ligand-planning signal only; do not treat it as canonical assay "
            "resolution or packet completion."
        ),
    }
    if target_hits:
        brief["packet_recommendation"] = {
            "accession": brief["accession"],
            "modalities_affected": ["ligand"],
            "next_action": "prioritize ligand procurement/planning around local ChEMBL evidence",
            "expected_effect": (
                "can reduce ligand deficit pressure without promoting the packet"
            ),
            "extraction_readiness": "ready_for_planning",
            "blockers": [],
        }
    else:
        brief["packet_recommendation"] = {
            "accession": brief["accession"],
            "modalities_affected": ["ligand"],
            "next_action": "fall through to online procurement",
            "expected_effect": "no local ligand rescue available",
            "extraction_readiness": "blocked",
            "blockers": blockers,
        }
    if output_path is not None:
        _write_json(output_path, brief)
    return brief


__all__ = ["build_local_chembl_rescue_brief"]

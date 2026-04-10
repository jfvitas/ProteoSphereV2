from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from execution.acquire.local_chembl_rescue import build_local_chembl_rescue_brief


def _write_chembl(
    path: Path,
    accession: str,
    chembl_id: str,
    pref_name: str,
    activity_count: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.cursor()
        cur.executescript(
            """
            create table component_sequences (component_id integer, accession text);
            create table target_components (component_id integer, tid integer);
            create table target_dictionary (tid integer, chembl_id text, pref_name text);
            create table assays (assay_id integer, tid integer);
            create table activities (activity_id integer, assay_id integer);
            """
        )
        cur.execute("insert into component_sequences values (1, ?)", (accession,))
        cur.execute("insert into target_components values (1, 11)")
        cur.execute("insert into target_dictionary values (11, ?, ?)", (chembl_id, pref_name))
        cur.execute("insert into assays values (101, 11)")
        for idx in range(activity_count):
            cur.execute("insert into activities values (?, 101)", (idx + 1,))
        conn.commit()
    finally:
        conn.close()


def test_build_local_chembl_rescue_brief_reports_planning_only_candidate(tmp_path: Path) -> None:
    chembl_path = tmp_path / "chembl.db"
    output_path = tmp_path / "brief.json"
    _write_chembl(chembl_path, "P00387", "CHEMBL2146", "NADH-cytochrome b5 reductase", 93)

    brief = build_local_chembl_rescue_brief(
        accession="P00387",
        chembl_path=chembl_path,
        output_path=output_path,
    )

    assert brief["accession"] == "P00387"
    assert brief["packet_source_ref"] == "ligand:P00387"
    assert brief["status"] == "local_rescue_candidate"
    assert brief["wired_into_proteosphere"]["discovery"] is True
    assert brief["wired_into_proteosphere"]["planning"] is True
    assert brief["wired_into_proteosphere"]["canonical_assay_resolution"] is False
    assert brief["evidence"]["source_columns"] == [
        "component_sequences.accession",
        "target_dictionary.chembl_id",
        "target_dictionary.pref_name",
        "activities.activity_id",
    ]
    assert brief["evidence"]["target_hits"] == [
        {
            "accession": "P00387",
            "activity_count": 93,
            "chembl_id": "CHEMBL2146",
            "pref_name": "NADH-cytochrome b5 reductase",
        }
    ]
    assert brief["packet_planning_input"]["status"] == "planning_only"
    assert brief["packet_planning_input"]["availability_hint"] == "local_chembl"
    assert brief["packet_planning_input"]["assay_count"] == 93
    assert brief["packet_planning_input"]["activity_count"] == 93
    assert brief["packet_planning_input"]["extraction_readiness"]["state"] == "ready_for_planning"
    assert brief["packet_planning_input"]["recommended_next_step"].startswith(
        "Prioritize ligand procurement/planning"
    )
    assert brief["packet_planning_input"]["blockers"] == []
    assert brief["packet_recommendation"]["modalities_affected"] == ["ligand"]
    assert brief["packet_recommendation"]["extraction_readiness"] == "ready_for_planning"
    assert output_path.exists()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["status"] == "local_rescue_candidate"
    assert written["packet_planning_input"]["can_promote"] is False


def test_build_local_chembl_rescue_brief_stays_honest_when_missing(tmp_path: Path) -> None:
    chembl_path = tmp_path / "chembl.db"
    _write_chembl(chembl_path, "OTHER", "CHEMBL1", "Other target", 1)

    brief = build_local_chembl_rescue_brief(
        accession="P09105",
        chembl_path=chembl_path,
    )

    assert brief["status"] == "no_local_candidate"
    assert brief["evidence"]["target_hits"] == []
    assert brief["packet_recommendation"]["next_action"] == "fall through to online procurement"
    assert brief["packet_planning_input"]["extraction_readiness"]["state"] == "blocked"
    assert brief["packet_planning_input"]["blockers"] == [
        "no_local_chembl_target_hit",
        "fall_back_to_online_procurement",
    ]

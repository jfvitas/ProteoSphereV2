from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from execution.acquire.p00387_ligand_extraction_contract import (
    build_p00387_ligand_extraction_contract,
)


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
            create table component_sequences (
                component_id integer,
                accession text,
                sequence text,
                description text,
                tax_id integer,
                organism text,
                db_source text,
                db_version text
            );
            create table target_components (
                component_id integer,
                tid integer,
                targcomp_id integer,
                homologue integer
            );
            create table target_dictionary (
                tid integer,
                target_type text,
                pref_name text,
                tax_id integer,
                organism text,
                chembl_id text,
                species_group_flag integer
            );
            create table assays (
                assay_id integer,
                tid integer
            );
            create table activities (
                activity_id integer,
                assay_id integer
            );
            """
        )
        cur.execute(
            "insert into component_sequences values (1, ?, '', '', 0, '', '', '')",
            (accession,),
        )
        cur.execute("insert into target_components values (1, 11, 101, 0)")
        cur.execute(
            "insert into target_dictionary values (11, '', ?, 0, '', ?, 0)",
            (pref_name, chembl_id),
        )
        cur.execute("insert into assays values (101, 11)")
        for idx in range(activity_count):
            cur.execute("insert into activities values (?, 101)", (idx + 1,))
        conn.commit()
    finally:
        conn.close()


def test_build_contract_reports_live_signal_and_truth_boundary(tmp_path: Path) -> None:
    chembl_path = tmp_path / "chembl.db"
    output_path = tmp_path / "contract.json"
    _write_chembl(chembl_path, "P00387", "CHEMBL2146", "NADH-cytochrome b5 reductase", 93)

    payload = build_p00387_ligand_extraction_contract(
        accession="P00387",
        chembl_path=chembl_path,
        output_path=output_path,
    )

    assert payload["accession"] == "P00387"
    assert payload["source_db_path"] == str(chembl_path)
    assert payload["contract_status"] == "ready_for_next_step"
    assert payload["rescue_claim"]["permitted"] is False
    assert payload["candidate_tables"][0]["table"] == "component_sequences"
    assert payload["candidate_tables"][0]["present_candidate_columns"] == [
        "component_id",
        "accession",
        "sequence",
        "description",
        "tax_id",
        "organism",
        "db_source",
        "db_version",
    ]
    assert payload["live_signal"]["target_hit_count"] == 1
    assert payload["live_signal"]["activity_count"] == 93
    assert payload["live_signal"]["selected_target_hit"] == {
        "accession": "P00387",
        "activity_count": 93,
        "chembl_id": "CHEMBL2146",
        "pref_name": "NADH-cytochrome b5 reductase",
    }
    assert "does not claim ligand rescue is complete" in payload["truth_boundary_notes"][0]
    assert "source_db_path" in payload["expected_output_schema"]["required"]
    assert output_path.exists()
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["contract_status"] == "ready_for_next_step"


def test_build_contract_blocks_when_no_local_hit(tmp_path: Path) -> None:
    chembl_path = tmp_path / "chembl.db"
    _write_chembl(chembl_path, "OTHER", "CHEMBL1", "Other target", 1)

    payload = build_p00387_ligand_extraction_contract(
        accession="P00387",
        chembl_path=chembl_path,
    )

    assert payload["contract_status"] == "blocked"
    assert payload["live_signal"]["target_hit_count"] == 0
    assert payload["blockers"] == [
        "no_local_chembl_accession_hit",
        "hold_for_fresh_acquisition_or_schema_repair",
    ]
    assert payload["live_signal"]["target_hits"] == []

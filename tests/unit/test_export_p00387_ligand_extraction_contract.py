from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from scripts.export_p00387_ligand_extraction_contract import render_markdown


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


def test_render_markdown_surfaces_execution_contract() -> None:
    markdown = render_markdown(
        {
            "generated_at": "2026-03-23T20:00:00+00:00",
            "accession": "P00387",
            "contract_status": "ready_for_next_step",
            "rescue_claim": {"permitted": False},
            "source_db_path": "chembl.db",
            "source_db_exists": True,
            "source_table_names": [
                "activities",
                "assays",
                "component_sequences",
                "target_components",
                "target_dictionary",
            ],
            "candidate_tables": [
                {
                    "table": "component_sequences",
                    "role": "accession anchor",
                    "candidate_columns": ["accession", "component_id"],
                    "present_candidate_columns": ["accession", "component_id"],
                }
            ],
            "join_chain": [
                {
                    "from_table": "component_sequences",
                    "from_column": "component_id",
                    "to_table": "target_components",
                    "to_column": "component_id",
                    "purpose": "carry the P00387 accession into the target bridge",
                }
            ],
            "live_signal": {
                "target_hit_count": 1,
                "activity_count": 93,
                "selected_target_hit": {
                    "accession": "P00387",
                    "chembl_id": "CHEMBL2146",
                    "pref_name": "NADH-cytochrome b5 reductase",
                    "activity_count": 93,
                },
            },
            "expected_output_schema": {
                "required": [
                    "schema_id",
                    "report_type",
                    "generated_at",
                    "accession",
                    "source_db_path",
                ]
            },
            "success_criteria": ["preserve the truth boundary"],
            "blockers": ["no_local_chembl_accession_hit"],
            "truth_boundary_notes": [
                "this artifact is planning-grade and does not claim ligand rescue is complete",
            ],
            "next_step": {
                "name": "bounded_p00387_ligand_extraction",
                "description": (
                    "Use the local ChEMBL hit as the starting point for a bounded ligand "
                    "extraction pass."
                ),
                "do_not_claim": ["rescue complete"],
            },
        }
    )

    assert "# P00387 Ligand Extraction Contract" in markdown
    assert "Source DB path" in markdown
    assert "candidate columns" in markdown
    assert "rescue is complete" in markdown


def test_cli_exports_status_and_markdown(tmp_path: Path) -> None:
    chembl_path = tmp_path / "chembl.db"
    output_path = tmp_path / "artifacts" / "status" / "p00387_ligand_extraction_contract.json"
    markdown_path = tmp_path / "docs" / "reports" / "p00387_ligand_extraction_contract.md"
    _write_chembl(chembl_path, "P00387", "CHEMBL2146", "NADH-cytochrome b5 reductase", 93)

    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "scripts\\export_p00387_ligand_extraction_contract.py",
            "--chembl",
            str(chembl_path),
            "--output",
            str(output_path),
            "--markdown",
            str(markdown_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "P00387 ligand extraction contract exported" in result.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["report_type"] == "p00387_ligand_extraction_contract"
    assert payload["contract_status"] == "ready_for_next_step"
    assert markdown_path.exists()

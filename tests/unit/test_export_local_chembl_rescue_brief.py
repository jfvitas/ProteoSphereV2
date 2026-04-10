from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from scripts.export_local_chembl_rescue_brief import render_markdown


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


def test_render_markdown_surfaces_planning_only_brief() -> None:
    markdown = render_markdown(
        {
            "generated_at": "2026-03-23T18:20:00+00:00",
            "accession": "P00387",
            "packet_source_ref": "ligand:P00387",
            "status": "local_rescue_candidate",
            "planning_note": (
                "Use this as a ligand-planning signal only; do not treat it as canonical "
                "assay resolution or packet completion."
            ),
            "evidence": {
                "source_file": "chembl.db",
                "source_tables": ["component_sequences", "activities"],
                "source_columns": ["component_sequences.accession", "activities.activity_id"],
                "target_hits": [
                    {
                        "accession": "P00387",
                        "chembl_id": "CHEMBL2146",
                        "pref_name": "NADH-cytochrome b5 reductase",
                        "activity_count": 93,
                    }
                ],
            },
            "packet_recommendation": {
                "next_action": (
                    "prioritize ligand procurement/planning around local ChEMBL evidence"
                ),
                "expected_effect": (
                    "can reduce ligand deficit pressure without promoting the packet"
                ),
                "extraction_readiness": "ready_for_planning",
                "blockers": [],
            },
            "packet_planning_input": {
                "extraction_readiness": {"state": "ready_for_planning"},
                "assay_count": 93,
                "activity_count": 93,
                "blockers": [],
            },
        }
    )

    assert "# Local ChEMBL Rescue Brief" in markdown
    assert "`P00387`" in markdown
    assert "planning-only, not canonical resolution" in markdown
    assert "CHEMBL2146" in markdown
    assert "Extraction readiness" in markdown
    assert "Assay / activity counts" in markdown


def test_cli_exports_status_and_markdown(tmp_path: Path) -> None:
    chembl_path = tmp_path / "chembl.db"
    output_path = tmp_path / "artifacts" / "status" / "local_chembl_rescue_brief.json"
    markdown_path = tmp_path / "docs" / "reports" / "local_chembl_rescue_brief.md"
    _write_chembl(chembl_path, "P00387", "CHEMBL2146", "NADH-cytochrome b5 reductase", 93)

    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "scripts\\export_local_chembl_rescue_brief.py",
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

    assert "Local ChEMBL rescue brief exported" in result.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["report_type"] == "local_chembl_rescue_brief"
    assert payload["status"] == "local_rescue_candidate"
    assert payload["packet_planning_input"]["extraction_readiness"]["state"] == "ready_for_planning"
    assert markdown_path.exists()

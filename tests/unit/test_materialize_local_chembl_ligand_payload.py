from __future__ import annotations

import json
from pathlib import Path

from scripts.materialize_local_chembl_ligand_payload import main
from tests.unit.execution.test_local_chembl_ligand_payload import _seed_db


def test_materialize_local_chembl_ligand_payload_writes_outputs(tmp_path: Path) -> None:
    chembl_path = tmp_path / "chembl.db"
    output_path = tmp_path / "payload.json"
    markdown_path = tmp_path / "payload.md"
    _seed_db(chembl_path)

    exit_code = main(
        [
            "--accession",
            "P00387",
            "--chembl",
            str(chembl_path),
            "--output",
            str(output_path),
            "--markdown",
            str(markdown_path),
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "resolved"
    assert "CHEMBL506" in output_path.read_text(encoding="utf-8")
    assert "P00387 Local ChEMBL Ligand Payload" in markdown_path.read_text(encoding="utf-8")

from __future__ import annotations

import json
from pathlib import Path


def test_cli_exports_planning_only_shortlist(tmp_path: Path) -> None:
    output_path = tmp_path / "artifacts" / "status" / "fresh_acquisition_shortlist.json"
    markdown_path = tmp_path / "docs" / "reports" / "fresh_acquisition_shortlist.md"

    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "scripts\\export_fresh_acquisition_shortlist.py",
            "--accessions",
            "P09105,Q2TAC2",
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

    assert "Fresh acquisition shortlist exported" in result.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["status"] == "planning_only"
    assert payload["selected_accessions"] == ["P09105", "Q2TAC2"]
    assert payload["entries"][0]["planning_status"] == "local_signal_only"
    assert payload["entries"][0]["classification"] == "structure_companion_only"
    assert payload["shortlist_note"].startswith("This is a planning-grade shortlist")
    assert markdown_path.exists()

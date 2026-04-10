from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_import_local_sources_cli_scoped_run_does_not_overwrite_latest(tmp_path: Path) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    raw_root = tmp_path / "repo" / "data" / "raw"
    (storage_root / "data" / "catalog").mkdir(parents=True)
    (storage_root / "data" / "catalog" / "download_manifest.csv").write_text(
        "source\nuniprot\n",
        encoding="utf-8",
    )

    script = Path("scripts/import_local_sources.py")
    scoped_run = subprocess.run(
        [
            sys.executable,
            str(script),
            "--storage-root",
            str(storage_root),
            "--raw-root",
            str(raw_root),
            "--sources",
            "catalog",
        ],
        cwd=Path.cwd(),
        check=True,
        capture_output=True,
        text=True,
    )
    scoped_summary = json.loads(scoped_run.stdout)
    latest_path = raw_root / "local_registry_runs" / "LATEST.json"

    assert scoped_summary["authoritative_refresh"] is False
    assert scoped_summary["latest_updated"] is False
    assert latest_path.exists() is False

    full_run = subprocess.run(
        [
            sys.executable,
            str(script),
            "--storage-root",
            str(storage_root),
            "--raw-root",
            str(raw_root),
        ],
        cwd=Path.cwd(),
        check=True,
        capture_output=True,
        text=True,
    )
    full_summary = json.loads(full_run.stdout)

    assert full_summary["authoritative_refresh"] is True
    assert full_summary["latest_updated"] is True
    assert latest_path.exists()

    latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
    assert latest_payload["stamp"] == full_summary["stamp"]

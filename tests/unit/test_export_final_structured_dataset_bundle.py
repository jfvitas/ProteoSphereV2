from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_export_final_structured_dataset_bundle_writes_versioned_bundle(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "final_structured_datasets"
    latest_path = output_root / "LATEST.json"
    output_json = tmp_path / "final_structured_dataset_bundle_preview.json"
    output_md = tmp_path / "final_structured_dataset_bundle_preview.md"

    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "export_final_structured_dataset_bundle.py"),
            "--output-root",
            str(output_root),
            "--latest-path",
            str(latest_path),
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--run-id",
            "final-structured-dataset-test",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    preview = json.loads(output_json.read_text(encoding="utf-8"))
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    bundle_root = output_root / "final-structured-dataset-test"

    assert preview["status"] == "completed"
    assert preview["summary"]["corpus_row_count"] >= 12
    assert preview["summary"]["strict_governing_training_view_count"] == 2
    assert latest["run_id"] == "final-structured-dataset-test"
    assert bundle_root.exists()
    assert (bundle_root / "bundle_manifest.json").exists()
    assert (bundle_root / "seed_plus_neighbors_structured_corpus.json").exists()

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.package_sample_projects import build_sample_project_package


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _set_mtime(path: Path, moment: datetime) -> None:
    timestamp = moment.timestamp()
    os.utime(path, (timestamp, timestamp))


def test_build_sample_project_package_packages_release_user_inputs(tmp_path: Path) -> None:
    output_json = tmp_path / "sample_project_tutorial_package_preview.json"
    output_md = tmp_path / "sample_project_tutorial_package_preview.md"

    payload = build_sample_project_package(
        output_json=output_json,
        output_md=output_md,
    )

    assert payload["package_identity"]["package_id"] == "sample-projects-and-tutorials"
    assert payload["summary"]["sample_project_count"] == 2
    assert payload["summary"]["tutorial_doc_count"] == 2
    assert payload["summary"]["release_user_ready"] is True
    assert payload["sample_projects"][0]["manifest"]["source_name"] == "bio-agent-lab/demo"
    assert (
        payload["sample_projects"][1]["manifest"]["source_name"]
        == "bio-agent-lab/training_examples"
    )
    assert all(not doc["stale"] for doc in payload["tutorial_docs"])
    assert output_json.exists()
    assert output_md.exists()
    assert "Sample Project and Tutorial Package Preview" in output_md.read_text(encoding="utf-8")


def test_build_sample_project_package_rejects_missing_artifact(tmp_path: Path) -> None:
    manifest_path = tmp_path / "demo" / "manifest.json"
    _write_json(
        manifest_path,
        {
            "manifest_id": "demo:package:001",
            "source_name": "demo",
            "release_version": "2026-04-03",
            "retrieval_mode": "download",
            "source_locator": str(tmp_path / "demo"),
            "local_artifact_refs": [
                str(tmp_path / "demo"),
                str(tmp_path / "demo" / "missing-inventory.json"),
            ],
            "provenance": ["local_source_mirror"],
        },
    )

    tutorial_doc = tmp_path / "tutorial.md"
    tutorial_doc.write_text("# Tutorial\n", encoding="utf-8")
    _set_mtime(tutorial_doc, datetime.now(UTC))

    with pytest.raises(FileNotFoundError, match="missing required sample project artifacts"):
        build_sample_project_package(
            source_manifest_paths=(manifest_path,),
            tutorial_doc_paths=(tutorial_doc,),
            output_json=tmp_path / "out.json",
            output_md=tmp_path / "out.md",
        )


def test_build_sample_project_package_rejects_stale_tutorial_docs(tmp_path: Path) -> None:
    project_root = tmp_path / "sample_project"
    project_root.mkdir()
    artifact = project_root / "inventory.json"
    artifact.write_text("{}", encoding="utf-8")

    manifest_path = tmp_path / "manifest.json"
    source_moment = datetime.now(UTC)
    _write_json(
        manifest_path,
        {
            "manifest_id": "demo:package:002",
            "source_name": "demo",
            "release_version": "2026-04-03",
            "retrieval_mode": "download",
            "source_locator": str(project_root),
            "local_artifact_refs": [
                str(project_root),
                str(artifact),
            ],
            "provenance": ["local_source_mirror"],
        },
    )
    _set_mtime(manifest_path, source_moment)
    _set_mtime(artifact, source_moment)

    tutorial_doc = tmp_path / "tutorial.md"
    tutorial_doc.write_text("# Stale tutorial\n", encoding="utf-8")
    _set_mtime(tutorial_doc, source_moment - timedelta(days=1))

    with pytest.raises(ValueError, match="stale tutorial docs block release packaging"):
        build_sample_project_package(
            source_manifest_paths=(manifest_path,),
            tutorial_doc_paths=(tutorial_doc,),
            output_json=tmp_path / "out.json",
            output_md=tmp_path / "out.md",
        )

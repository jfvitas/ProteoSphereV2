from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.promote_protein_data_scope_seed import (
    build_seed_promotion,
    render_seed_promotion_markdown,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_seed_promotion_requires_passed_validation(tmp_path: Path) -> None:
    validation_path = tmp_path / "validation.json"
    _write_json(
        validation_path,
        {
            "status": "partial",
            "sources": [],
        },
    )

    with pytest.raises(ValueError, match="seed validation must be passed"):
        build_seed_promotion(validation_path=validation_path, seed_root=tmp_path / "seed")


def test_build_seed_promotion_emits_source_release_manifests(tmp_path: Path) -> None:
    seed_root = tmp_path / "data" / "raw" / "protein_data_scope_seed"
    source_dir = seed_root / "reactome"
    source_dir.mkdir(parents=True, exist_ok=True)
    uni = source_dir / "UniProt2Reactome.txt"
    path_file = source_dir / "ReactomePathways.txt"
    rel = source_dir / "ReactomePathwaysRelation.txt"
    uni.write_text("P12345\tR-HSA-1\n", encoding="utf-8")
    path_file.write_text("R-HSA-1\tName\tHomo sapiens\n", encoding="utf-8")
    rel.write_text("R-HSA-1\tR-HSA-2\n", encoding="utf-8")

    manifest_path = seed_root / "download_run_20260323_121948.json"
    _write_json(
        manifest_path,
        {
            "generated_at": "2026-03-23T17:19:32Z",
            "sources": [
                {
                    "id": "reactome",
                    "items": [
                        {
                            "filename": "UniProt2Reactome.txt",
                            "path": str(uni),
                            "sha256": "sha-uni",
                            "url": "https://reactome.org/download/current/UniProt2Reactome.txt",
                        },
                        {
                            "filename": "ReactomePathways.txt",
                            "path": str(path_file),
                            "sha256": "sha-path",
                            "url": "https://reactome.org/download/current/ReactomePathways.txt",
                        },
                        {
                            "filename": "ReactomePathwaysRelation.txt",
                            "path": str(rel),
                            "sha256": "sha-rel",
                            "url": "https://reactome.org/download/current/ReactomePathwaysRelation.txt",
                        },
                    ],
                }
            ],
        },
    )

    validation_path = tmp_path / "artifacts" / "status" / "protein_data_scope_seed_validation.json"
    _write_json(
        validation_path,
        {
            "status": "passed",
            "sources": [
                {
                    "source_id": "reactome",
                    "status": "passed",
                    "manifest_path": str(manifest_path),
                    "validated_artifacts": [
                        {
                            "filename": "UniProt2Reactome.txt",
                            "path": str(uni),
                            "size_bytes": uni.stat().st_size,
                            "sha256": "badhash",
                        }
                    ],
                }
            ],
        },
    )

    with pytest.raises(ValueError, match="validated_artifact_set_mismatch"):
        build_seed_promotion(validation_path=validation_path, seed_root=seed_root)

    validation_payload = json.loads(validation_path.read_text(encoding="utf-8"))
    validation_payload["sources"][0]["validated_artifacts"] = [
        {
            "filename": "UniProt2Reactome.txt",
            "path": str(uni),
            "size_bytes": uni.stat().st_size,
            "sha256": hashlib.sha256(uni.read_bytes()).hexdigest(),
        },
        {
            "filename": "ReactomePathways.txt",
            "path": str(path_file),
            "size_bytes": path_file.stat().st_size,
            "sha256": hashlib.sha256(path_file.read_bytes()).hexdigest(),
        },
        {
            "filename": "ReactomePathwaysRelation.txt",
            "path": str(rel),
            "size_bytes": rel.stat().st_size,
            "sha256": hashlib.sha256(rel.read_bytes()).hexdigest(),
        },
    ]
    validation_path.write_text(json.dumps(validation_payload), encoding="utf-8")

    payload = build_seed_promotion(validation_path=validation_path, seed_root=seed_root)

    assert payload["status"] == "promoted"
    assert payload["source_count"] == 1
    source_release = payload["sources"][0]["source_release"]
    assert source_release["source_name"] == "reactome"
    assert source_release["release_version"] == "protein-data-scope-seed-20260323_121948"
    assert source_release["release_date"] == "2026-03-23"
    assert len(source_release["local_artifact_refs"]) == 3
    assert source_release["local_artifact_refs"][0].endswith(
        "data/raw/protein_data_scope_seed/reactome/UniProt2Reactome.txt"
    )
    assert source_release["local_artifact_refs"][1].endswith(
        "data/raw/protein_data_scope_seed/reactome/ReactomePathways.txt"
    )
    assert source_release["local_artifact_refs"][2].endswith(
        "data/raw/protein_data_scope_seed/reactome/ReactomePathwaysRelation.txt"
    )

    markdown = render_seed_promotion_markdown(payload)
    assert "# Protein Data Scope Seed Publish" in markdown
    assert "## reactome" in markdown
    assert source_release["manifest_id"] in markdown

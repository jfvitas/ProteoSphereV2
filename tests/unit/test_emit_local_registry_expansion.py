from __future__ import annotations

import json
from pathlib import Path

from scripts.emit_local_registry_expansion import (
    build_local_registry_expansion_report,
    main,
    render_markdown,
)


def _prepare_context_root(storage_root: Path) -> None:
    for relative_path in (
        "data/conformations",
        "data/custom_training_sets",
        "data/demo",
        "data/external",
        "data/identity",
        "data/interim",
        "data/models",
        "data/packaged",
        "data/prediction",
        "data/processed",
        "data/qa",
        "data/raw",
        "data/risk",
    ):
        (storage_root / relative_path).mkdir(parents=True, exist_ok=True)


def test_build_local_registry_expansion_report_tracks_new_context_groups(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    _prepare_context_root(storage_root)

    payload = build_local_registry_expansion_report(storage_root)

    assert payload["baseline_source_count"] == 44
    assert payload["expanded_source_count"] == 57
    assert payload["source_count_delta"] == 13
    assert payload["new_source_count"] == 13

    names = [item["source_name"] for item in payload["new_source_groups"]]
    assert names == sorted(names, key=str.casefold)
    assert names == [
        "conformations",
        "custom_training_sets",
        "demo",
        "external",
        "identity",
        "interim",
        "models",
        "packaged",
        "prediction",
        "processed",
        "qa",
        "raw",
        "risk",
    ]

    by_name = {item["source_name"]: item for item in payload["new_source_groups"]}
    assert by_name["processed"]["category"] == "derived_training"
    assert by_name["processed"]["load_hints"] == ["index", "lazy"]
    assert by_name["packaged"]["category"] == "release_artifact"
    assert by_name["packaged"]["load_hints"] == ["preload"]
    assert by_name["raw"]["category"] == "metadata"
    assert by_name["raw"]["load_hints"] == ["index", "lazy"]

    markdown = render_markdown(payload)
    assert "# Local Registry Expansion" in markdown
    assert "| Source | Category | Load hints | Present roots |" in markdown


def test_main_writes_registry_expansion_outputs(tmp_path: Path) -> None:
    storage_root = tmp_path / "bio-agent-lab"
    _prepare_context_root(storage_root)
    output_json = tmp_path / "registry_expansion.json"
    output_md = tmp_path / "registry_expansion.md"

    exit_code = main(
        [
            "--storage-root",
            str(storage_root),
            "--output",
            str(output_json),
            "--markdown",
            str(output_md),
            "--json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["expanded_source_count"] == 57
    assert output_md.exists()
    assert "conformations" in output_md.read_text(encoding="utf-8")

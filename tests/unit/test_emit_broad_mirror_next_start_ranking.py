from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.emit_broad_mirror_next_start_ranking import (
    build_next_start_ranking,
    render_markdown,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_fixture_files(tmp_path: Path) -> dict[str, Path]:
    remaining_transfer_status_path = (
        tmp_path / "artifacts" / "status" / "broad_mirror_remaining_transfer_status.json"
    )
    source_policy_path = tmp_path / "protein_data_scope" / "source_policy.json"

    _write_json(
        remaining_transfer_status_path,
        {
            "schema_id": "proteosphere-broad-mirror-remaining-transfer-status-2026-03-31",
            "generated_at": "2026-03-31T19:34:11.338136+00:00",
            "status": "planning",
            "basis": {
                "remaining_gaps_path": "artifacts/status/broad_mirror_remaining_gaps.json",
                "runtime_dir": "artifacts/runtime",
                "seed_root": "data/raw/protein_data_scope_seed",
            },
            "summary": {
                "broad_mirror_coverage_percent": 86.4,
                "remaining_source_count": 2,
                "active_file_count": 6,
                "not_yet_started_file_count": 16,
                "active_source_counts": {"string": 3, "uniprot": 3},
            },
            "sources": [
                {
                    "source_id": "uniprot",
                    "source_name": "UniProt / UniRef / ID Mapping",
                    "category": "sequence_reference_backbone",
                    "status": "partial",
                    "coverage_percent": 33.3,
                    "not_yet_started": [
                        {"filename": "uniref50.fasta.gz", "gap_kind": "missing"},
                        {"filename": "idmapping_selected.tab.gz", "gap_kind": "missing"},
                        {"filename": "uniprot_sprot_varsplic.fasta.gz", "gap_kind": "missing"},
                        {"filename": "uniref90.xml.gz", "gap_kind": "missing"},
                    ],
                },
                {
                    "source_id": "string",
                    "source_name": "STRING v12",
                    "category": "interaction_networks",
                    "status": "partial",
                    "coverage_percent": 53.8,
                    "not_yet_started": [
                        {"filename": "database.schema.v12.0.pdf", "gap_kind": "missing"},
                        {"filename": "protein.network.embeddings.v12.0.h5", "gap_kind": "missing"},
                        {"filename": "protein.physical.links.v12.0.txt.gz", "gap_kind": "missing"},
                    ],
                },
            ],
            "notes": [],
            "actively_transferring_now": [],
        },
    )

    _write_json(
        source_policy_path,
        {
            "policy_version": "2026-03-23",
            "tiers": {
                "direct": {
                    "description": "Safe to automate immediately.",
                    "source_ids": ["uniprot"],
                },
                "guarded": {
                    "description": "Automatable with pinned releases.",
                    "source_ids": ["string"],
                },
                "resolver": {
                    "description": "Requires URL resolution.",
                    "source_ids": [],
                },
            },
        },
    )

    return {
        "remaining_transfer_status_path": remaining_transfer_status_path,
        "source_policy_path": source_policy_path,
    }


def test_build_next_start_ranking_orders_direct_before_guarded(tmp_path: Path) -> None:
    paths = _write_fixture_files(tmp_path)

    payload = build_next_start_ranking(
        remaining_transfer_status_path=paths["remaining_transfer_status_path"],
        source_policy_path=paths["source_policy_path"],
    )

    order = [
        (row["source_id"], row["filename"])
        for row in payload["recommended_sidecar_launch_order"]
    ]
    assert order == [
        ("uniprot", "idmapping_selected.tab.gz"),
        ("uniprot", "uniprot_sprot_varsplic.fasta.gz"),
        ("uniprot", "uniref90.xml.gz"),
        ("uniprot", "uniref50.fasta.gz"),
        ("string", "protein.physical.links.v12.0.txt.gz"),
        ("string", "database.schema.v12.0.pdf"),
        ("string", "protein.network.embeddings.v12.0.h5"),
    ]
    assert payload["summary"]["remaining_source_count"] == 2
    assert payload["summary"]["ranked_file_count"] == 7
    assert payload["source_rankings"][0]["source_id"] == "uniprot"
    assert payload["source_rankings"][0]["source_role"] == "direct"
    assert payload["source_rankings"][1]["source_id"] == "string"
    assert payload["source_rankings"][1]["source_role"] == "guarded"

    markdown = render_markdown(payload)
    assert "# Broad Mirror Next-Start Ranking" in markdown
    assert "Launch Order" in markdown
    assert "`uniprot` | direct | `idmapping_selected.tab.gz`" in markdown


def test_main_writes_next_start_outputs(tmp_path: Path) -> None:
    paths = _write_fixture_files(tmp_path)
    output_path = tmp_path / "artifacts" / "status" / "broad_mirror_next_start_ranking.json"
    markdown_path = tmp_path / "docs" / "reports" / "broad_mirror_next_start_ranking.md"

    result = subprocess.run(
        [
            sys.executable,
            str(
                Path(__file__).resolve().parents[2]
                / "scripts"
                / "emit_broad_mirror_next_start_ranking.py"
            ),
            "--remaining-transfer-status",
            str(paths["remaining_transfer_status_path"]),
            "--source-policy",
            str(paths["source_policy_path"]),
            "--output",
            str(output_path),
            "--markdown-output",
            str(markdown_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert "Broad mirror next-start ranking exported:" in result.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["ranked_file_count"] == 7
    assert markdown_path.read_text(encoding="utf-8").startswith(
        "# Broad Mirror Next-Start Ranking"
    )

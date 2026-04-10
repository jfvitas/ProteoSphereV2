from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.emit_broad_mirror_lane_plan import build_lane_plan, render_markdown


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
            "generated_at": "2026-03-31T19:43:28.297227+00:00",
            "status": "planning",
            "basis": {
                "remaining_gaps_path": "artifacts/status/broad_mirror_remaining_gaps.json",
                "runtime_dir": "artifacts/runtime",
                "seed_root": "data/raw/protein_data_scope_seed",
            },
            "summary": {
                "broad_mirror_coverage_percent": 86.4,
                "remaining_source_count": 2,
                "active_file_count": 8,
                "not_yet_started_file_count": 14,
                "active_source_counts": {"string": 4, "uniprot": 4},
            },
            "sources": [
                {
                    "source_id": "string",
                    "source_name": "STRING v12",
                    "category": "interaction_networks",
                    "status": "partial",
                    "coverage_percent": 53.8,
                    "not_yet_started": [
                        {"filename": "protein.physical.links.detailed.v12.0.txt.gz", "gap_kind": "missing"},
                        {"filename": "protein.physical.links.full.v12.0.txt.gz", "gap_kind": "missing"},
                        {"filename": "protein.network.embeddings.v12.0.h5", "gap_kind": "missing"},
                        {"filename": "protein.sequence.embeddings.v12.0.h5", "gap_kind": "missing"},
                        {"filename": "items_schema.v12.0.sql.gz", "gap_kind": "missing"},
                        {"filename": "network_schema.v12.0.sql.gz", "gap_kind": "missing"},
                        {"filename": "evidence_schema.v12.0.sql.gz", "gap_kind": "missing"},
                        {"filename": "database.schema.v12.0.pdf", "gap_kind": "missing"},
                    ],
                },
                {
                    "source_id": "uniprot",
                    "source_name": "UniProt / UniRef / ID Mapping",
                    "category": "sequence_reference_backbone",
                    "status": "partial",
                    "coverage_percent": 33.3,
                    "not_yet_started": [
                        {"filename": "uniprot_sprot_varsplic.fasta.gz", "gap_kind": "missing"},
                        {"filename": "uniref100.fasta.gz", "gap_kind": "missing"},
                        {"filename": "uniref90.fasta.gz", "gap_kind": "missing"},
                        {"filename": "uniref90.xml.gz", "gap_kind": "missing"},
                        {"filename": "uniref50.fasta.gz", "gap_kind": "missing"},
                        {"filename": "uniref50.xml.gz", "gap_kind": "missing"},
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
                    "description": "Safe to automate immediately with direct file URLs and fail-closed download checks.",
                    "source_ids": ["uniprot"],
                },
                "guarded": {
                    "description": "Automatable, but only with release pinning and snapshot metadata capture.",
                    "source_ids": ["string"],
                },
                "resolver": {
                    "description": "Requires release discovery, URL resolution, or source-specific validation before download.",
                    "source_ids": [],
                },
            },
        },
    )

    return {
        "remaining_transfer_status_path": remaining_transfer_status_path,
        "source_policy_path": source_policy_path,
    }


def test_build_lane_plan_groups_into_three_batches(tmp_path: Path) -> None:
    paths = _write_fixture_files(tmp_path)

    payload = build_lane_plan(
        remaining_transfer_status_path=paths["remaining_transfer_status_path"],
        source_policy_path=paths["source_policy_path"],
    )

    batches = payload["recommended_sidecar_launch_order"]
    assert [batch["batch_id"] for batch in batches] == [
        "uniprot-core-backbone",
        "uniprot-tail-representatives",
        "string-guarded-network-pack",
    ]
    assert [batch["value_class"] for batch in batches] == [
        "direct-value",
        "deferred-value",
        "deferred-value",
    ]
    assert batches[0]["files"] == [
        "uniprot_sprot_varsplic.fasta.gz",
        "uniref100.fasta.gz",
        "uniref90.fasta.gz",
    ]
    assert batches[1]["files"] == [
        "uniref90.xml.gz",
        "uniref50.fasta.gz",
        "uniref50.xml.gz",
    ]
    assert batches[2]["files"] == [
        "protein.physical.links.detailed.v12.0.txt.gz",
        "protein.physical.links.full.v12.0.txt.gz",
        "items_schema.v12.0.sql.gz",
        "network_schema.v12.0.sql.gz",
        "evidence_schema.v12.0.sql.gz",
        "database.schema.v12.0.pdf",
        "protein.network.embeddings.v12.0.h5",
        "protein.sequence.embeddings.v12.0.h5",
    ]
    assert payload["summary"]["recommended_sidecar_batch_count"] == 3
    assert payload["summary"]["direct_value_file_count"] == 3
    assert payload["summary"]["deferred_value_file_count"] == 11
    assert payload["summary"]["source_role_counts"] == {"direct": 1, "guarded": 1}

    markdown = render_markdown(payload)
    assert "# Broad Mirror Lane Plan" in markdown
    assert "Recommended sidecar batches" in markdown
    assert "uniprot-core-backbone" in markdown
    assert "string-guarded-network-pack" in markdown


def test_main_writes_lane_plan_outputs(tmp_path: Path) -> None:
    paths = _write_fixture_files(tmp_path)
    output_path = tmp_path / "artifacts" / "status" / "broad_mirror_lane_plan.json"
    markdown_path = tmp_path / "docs" / "reports" / "broad_mirror_lane_plan.md"

    result = subprocess.run(
        [
            sys.executable,
            str(
                Path(__file__).resolve().parents[2]
                / "scripts"
                / "emit_broad_mirror_lane_plan.py"
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

    assert "Broad mirror lane plan exported:" in result.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["recommended_sidecar_batch_count"] == 3
    assert markdown_path.read_text(encoding="utf-8").startswith("# Broad Mirror Lane Plan")

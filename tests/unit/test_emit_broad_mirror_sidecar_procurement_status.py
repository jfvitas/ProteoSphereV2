from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.emit_broad_mirror_sidecar_procurement_status import (
    build_sidecar_procurement_status,
    render_markdown,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _fixture(tmp_path: Path) -> dict[str, Path]:
    remaining_transfer_status_path = (
        tmp_path / "artifacts" / "status" / "broad_mirror_remaining_transfer_status.json"
    )
    source_policy_path = tmp_path / "protein_data_scope" / "source_policy.json"
    runtime_dir = tmp_path / "artifacts" / "runtime"
    seed_root = tmp_path / "data" / "raw" / "protein_data_scope_seed"

    _write_json(
        remaining_transfer_status_path,
        {
            "summary": {
                "broad_mirror_coverage_percent": 86.4,
                "remaining_source_count": 2,
                "active_file_count": 9,
                "not_yet_started_file_count": 14,
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
            "actively_transferring_now": [
                {"source_id": "string", "source_name": "STRING v12", "filename": "protein.links.detailed.v12.0.txt.gz", "gap_kind": "missing"},
                {"source_id": "string", "source_name": "STRING v12", "filename": "protein.links.full.v12.0.txt.gz", "gap_kind": "missing"},
                {"source_id": "string", "source_name": "STRING v12", "filename": "protein.physical.links.v12.0.txt.gz", "gap_kind": "missing"},
                {"source_id": "string", "source_name": "STRING v12", "filename": "protein.network.embeddings.v12.0.h5", "gap_kind": "missing"},
                {"source_id": "string", "source_name": "STRING v12", "filename": "protein.links.v12.0.txt.gz", "gap_kind": "partial"},
                {"source_id": "uniprot", "source_name": "UniProt / UniRef / ID Mapping", "filename": "uniprot_trembl.xml.gz", "gap_kind": "missing"},
                {"source_id": "uniprot", "source_name": "UniProt / UniRef / ID Mapping", "filename": "idmapping_selected.tab.gz", "gap_kind": "missing"},
                {"source_id": "uniprot", "source_name": "UniProt / UniRef / ID Mapping", "filename": "uniref100.xml.gz", "gap_kind": "missing"},
                {"source_id": "uniprot", "source_name": "UniProt / UniRef / ID Mapping", "filename": "uniprot_trembl.dat.gz", "gap_kind": "partial"},
            ],
            "not_yet_started": [
                {"source_id": "string", "source_name": "STRING v12", "filename": "protein.physical.links.detailed.v12.0.txt.gz", "gap_kind": "missing"},
                {"source_id": "string", "source_name": "STRING v12", "filename": "protein.physical.links.full.v12.0.txt.gz", "gap_kind": "missing"},
                {"source_id": "string", "source_name": "STRING v12", "filename": "protein.network.embeddings.v12.0.h5", "gap_kind": "missing"},
                {"source_id": "string", "source_name": "STRING v12", "filename": "protein.sequence.embeddings.v12.0.h5", "gap_kind": "missing"},
                {"source_id": "string", "source_name": "STRING v12", "filename": "items_schema.v12.0.sql.gz", "gap_kind": "missing"},
                {"source_id": "string", "source_name": "STRING v12", "filename": "network_schema.v12.0.sql.gz", "gap_kind": "missing"},
                {"source_id": "string", "source_name": "STRING v12", "filename": "evidence_schema.v12.0.sql.gz", "gap_kind": "missing"},
                {"source_id": "string", "source_name": "STRING v12", "filename": "database.schema.v12.0.pdf", "gap_kind": "missing"},
                {"source_id": "uniprot", "source_name": "UniProt / UniRef / ID Mapping", "filename": "uniprot_sprot_varsplic.fasta.gz", "gap_kind": "missing"},
                {"source_id": "uniprot", "source_name": "UniProt / UniRef / ID Mapping", "filename": "uniref100.fasta.gz", "gap_kind": "missing"},
                {"source_id": "uniprot", "source_name": "UniProt / UniRef / ID Mapping", "filename": "uniref90.fasta.gz", "gap_kind": "missing"},
                {"source_id": "uniprot", "source_name": "UniProt / UniRef / ID Mapping", "filename": "uniref90.xml.gz", "gap_kind": "missing"},
                {"source_id": "uniprot", "source_name": "UniProt / UniRef / ID Mapping", "filename": "uniref50.fasta.gz", "gap_kind": "missing"},
                {"source_id": "uniprot", "source_name": "UniProt / UniRef / ID Mapping", "filename": "uniref50.xml.gz", "gap_kind": "missing"},
            ],
        },
    )
    _write_json(
        source_policy_path,
        {
            "tiers": {
                "direct": {"source_ids": ["uniprot"]},
                "guarded": {"source_ids": ["string"]},
            }
        },
    )

    for rel in [
        "uniprot_core_backbone_stdout.log",
        "uniprot_core_backbone_stderr.log",
        "uniprot_tail_sidecar_stdout.log",
        "uniprot_tail_sidecar_stderr.log",
        "string_schema_sidecar_stdout.log",
        "string_schema_sidecar_stderr.log",
        "string_physical_tail_sidecar_stdout.log",
        "string_physical_tail_sidecar_stderr.log",
    ]:
        (runtime_dir / rel).parent.mkdir(parents=True, exist_ok=True)
        (runtime_dir / rel).write_text("", encoding="utf-8")

    for rel in [
        "uniprot/uniref100.fasta.gz.part",
        "uniprot/uniref90.xml.gz.part",
        "string/protein.physical.links.detailed.v12.0.txt.gz.part",
        "string/protein.physical.links.full.v12.0.txt.gz.part",
        "string/protein.network.embeddings.v12.0.h5.part",
    ]:
        path = seed_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    return {
        "remaining_transfer_status_path": remaining_transfer_status_path,
        "source_policy_path": source_policy_path,
        "runtime_dir": runtime_dir,
        "seed_root": seed_root,
    }


def test_build_sidecar_procurement_status_classifies_buckets(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    payload = build_sidecar_procurement_status(
        remaining_transfer_status_path=paths["remaining_transfer_status_path"],
        source_policy_path=paths["source_policy_path"],
        runtime_dir=paths["runtime_dir"],
        seed_root=paths["seed_root"],
    )

    assert payload["summary"] == {
        "remaining_file_count": 23,
        "active_sidecar_file_count": 14,
        "active_bulk_file_count": 8,
        "still_uncovered_file_count": 0,
        "active_sidecar_overlap_file_count": 1,
        "active_sidecar_overlap_filenames": ["protein.network.embeddings.v12.0.h5"],
        "active_sidecar_count": 4,
        "active_bulk_source_count": 2,
        "source_role_counts": {"direct": 1, "guarded": 1},
    }
    assert [row["batch_id"] for row in payload["active_sidecars"]] == [
        "uniprot-core",
        "uniprot-tail",
        "string-schema",
        "string-physical-tail",
    ]
    assert [Path(path).name for path in payload["active_sidecars"][0]["observed_partial_files"]] == [
        "uniref100.fasta.gz.part"
    ]
    assert [Path(path).name for path in payload["active_sidecars"][1]["observed_partial_files"]] == [
        "uniref90.xml.gz.part"
    ]
    assert len(payload["active_bulk"]) == 8
    assert payload["still_uncovered_backlog"] == []

    markdown = render_markdown(payload)
    assert "# Broad Mirror Sidecar Procurement Status" in markdown
    assert "Active Sidecars" in markdown
    assert "Active Bulk" in markdown


def test_main_writes_sidecar_procurement_outputs(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    output_path = tmp_path / "artifacts" / "status" / "broad_mirror_sidecar_procurement_status.json"
    markdown_path = tmp_path / "docs" / "reports" / "broad_mirror_sidecar_procurement_status.md"

    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[2] / "scripts" / "emit_broad_mirror_sidecar_procurement_status.py"),
            "--remaining-transfer-status",
            str(paths["remaining_transfer_status_path"]),
            "--source-policy",
            str(paths["source_policy_path"]),
            "--runtime-dir",
            str(paths["runtime_dir"]),
            "--seed-root",
            str(tmp_path / "data" / "raw" / "protein_data_scope_seed"),
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

    assert "Broad mirror sidecar procurement status exported:" in result.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["summary"]["still_uncovered_file_count"] == 0
    assert markdown_path.read_text(encoding="utf-8").startswith(
        "# Broad Mirror Sidecar Procurement Status"
    )

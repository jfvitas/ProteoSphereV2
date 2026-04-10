from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.emit_broad_mirror_launcher_contract import build_launcher_contract, render_markdown


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_fixture_files(tmp_path: Path) -> dict[str, Path]:
    lane_plan_path = tmp_path / "artifacts" / "status" / "broad_mirror_lane_plan.json"
    transfer_status_path = (
        tmp_path / "artifacts" / "status" / "broad_mirror_remaining_transfer_status.json"
    )
    source_downloader = tmp_path / "protein_data_scope" / "download_all_sources.py"
    dest_root = tmp_path / "data" / "raw" / "protein_data_scope_seed"

    _write_json(
        lane_plan_path,
        {
            "schema_id": "proteosphere-broad-mirror-lane-plan-2026-03-31",
            "generated_at": "2026-03-31T19:45:53.738450+00:00",
            "status": "planning",
            "basis": {
                "remaining_transfer_status_path": "artifacts/status/broad_mirror_remaining_transfer_status.json",
                "source_policy_path": "protein_data_scope/source_policy.json",
            },
            "summary": {
                "remaining_source_count": 2,
                "not_yet_started_file_count": 14,
                "recommended_sidecar_batch_count": 3,
                "source_role_counts": {"direct": 1, "guarded": 1},
                "direct_value_file_count": 3,
                "deferred_value_file_count": 11,
            },
            "recommended_sidecar_launch_order": [
                {
                    "rank": 1,
                    "batch_id": "uniprot-core-backbone",
                    "source_id": "uniprot",
                    "source_name": "UniProt / UniRef / ID Mapping",
                    "source_role": "direct",
                    "value_class": "direct-value",
                    "file_count": 3,
                    "files": [
                        "uniprot_sprot_varsplic.fasta.gz",
                        "uniref100.fasta.gz",
                        "uniref90.fasta.gz",
                    ],
                    "rationale": "Highest immediate library value.",
                    "expected_impact": "Restores the core sequence reference layer first.",
                },
                {
                    "rank": 2,
                    "batch_id": "uniprot-tail-representatives",
                    "source_id": "uniprot",
                    "source_name": "UniProt / UniRef / ID Mapping",
                    "source_role": "direct",
                    "value_class": "deferred-value",
                    "file_count": 3,
                    "files": [
                        "uniref90.xml.gz",
                        "uniref50.fasta.gz",
                        "uniref50.xml.gz",
                    ],
                    "rationale": "Tail batch.",
                    "expected_impact": "Completes remaining UniProt coverage.",
                },
            ],
            "notes": [],
        },
    )

    _write_json(
        transfer_status_path,
        {
            "schema_id": "proteosphere-broad-mirror-remaining-transfer-status-2026-03-31",
            "generated_at": "2026-03-31T19:38:13.468063+00:00",
            "status": "planning",
            "basis": {
                "remaining_gaps_path": "artifacts/status/broad_mirror_remaining_gaps.json",
                "runtime_dir": "artifacts/runtime",
                "seed_root": "data/raw/protein_data_scope_seed",
            },
            "summary": {
                "broad_mirror_coverage_percent": 86.4,
                "remaining_source_count": 2,
                "active_file_count": 9,
                "not_yet_started_file_count": 14,
                "active_source_counts": {"string": 5, "uniprot": 4},
            },
            "sources": [],
            "actively_transferring_now": [
                {"source_id": "string", "filename": "protein.links.detailed.v12.0.txt.gz"},
                {"source_id": "string", "filename": "protein.links.full.v12.0.txt.gz"},
                {"source_id": "string", "filename": "protein.physical.links.v12.0.txt.gz"},
                {"source_id": "string", "filename": "protein.network.embeddings.v12.0.h5"},
                {"source_id": "string", "filename": "protein.links.v12.0.txt.gz"},
                {"source_id": "uniprot", "filename": "uniprot_trembl.xml.gz"},
                {"source_id": "uniprot", "filename": "idmapping_selected.tab.gz"},
                {"source_id": "uniprot", "filename": "uniref100.xml.gz"},
                {"source_id": "uniprot", "filename": "uniprot_trembl.dat.gz"},
            ],
            "not_yet_started": [],
        },
    )

    _write_json(source_downloader, {"stub": True})

    return {
        "lane_plan_path": lane_plan_path,
        "transfer_status_path": transfer_status_path,
        "source_downloader": source_downloader,
        "dest_root": dest_root,
    }


def test_build_launcher_contract_targets_only_safe_uniprot_batch(tmp_path: Path) -> None:
    paths = _write_fixture_files(tmp_path)

    payload = build_launcher_contract(
        lane_plan_path=paths["lane_plan_path"],
        transfer_status_path=paths["transfer_status_path"],
        source_downloader=paths["source_downloader"],
        dest_root=paths["dest_root"],
    )

    assert payload["selected_batch"]["batch_id"] == "uniprot-core-backbone"
    assert payload["selected_batch"]["value_class"] == "direct-value"
    assert payload["summary"]["selected_file_count"] == 3
    assert payload["summary"]["overlap_count"] == 0
    assert payload["launch"]["command_argv"][0] == "python"
    assert payload["launch"]["command_argv"][1].endswith("download_all_sources.py")
    assert payload["launch"]["command_argv"][2:4] == [
        "--dest",
        paths["dest_root"].resolve().as_posix(),
    ]
    assert payload["launch"]["command_argv"][-3:] == [
        "uniprot_sprot_varsplic.fasta.gz",
        "uniref100.fasta.gz",
        "uniref90.fasta.gz",
    ]
    assert "protein.links.full.v12.0.txt.gz" in payload["duplicate_process_avoidance"]["active_files_observed"]
    assert payload["duplicate_process_avoidance"]["overlapping_files"] == []

    expected_output_paths = [item["path"] for item in payload["expected_outputs"]]
    assert "data/raw/protein_data_scope_seed/uniprot/uniprot_sprot_varsplic.fasta.gz" in expected_output_paths
    assert "data/raw/protein_data_scope_seed/uniprot/_source_metadata.json" in expected_output_paths
    assert "data/raw/protein_data_scope_seed/download_run_<UTC timestamp>.json" in expected_output_paths

    markdown = render_markdown(payload)
    assert "# Broad Mirror Launcher Contract" in markdown
    assert "Launch Command" in markdown
    assert "Duplicate-Process Avoidance" in markdown


def test_main_writes_launcher_contract_outputs(tmp_path: Path) -> None:
    paths = _write_fixture_files(tmp_path)
    output_path = tmp_path / "artifacts" / "status" / "broad_mirror_launcher_contract.json"
    markdown_path = tmp_path / "docs" / "reports" / "broad_mirror_launcher_contract.md"

    result = subprocess.run(
        [
            sys.executable,
            str(
                Path(__file__).resolve().parents[2]
                / "scripts"
                / "emit_broad_mirror_launcher_contract.py"
            ),
            "--lane-plan",
            str(paths["lane_plan_path"]),
            "--transfer-status",
            str(paths["transfer_status_path"]),
            "--source-downloader",
            str(paths["source_downloader"]),
            "--dest-root",
            str(paths["dest_root"]),
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

    assert "Broad mirror launcher contract exported:" in result.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["selected_batch"]["batch_id"] == "uniprot-core-backbone"
    assert markdown_path.read_text(encoding="utf-8").startswith("# Broad Mirror Launcher Contract")

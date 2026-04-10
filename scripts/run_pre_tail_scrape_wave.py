from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "pre_tail_scrape_wave_execution_preview.json"
)
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "pre_tail_scrape_wave_execution_preview.md"

JOB_SPECS: tuple[dict[str, Any], ...] = (
    {
        "job_id": "motif_active_site_enrichment",
        "lane_id": "interpro_motif_backbone",
        "commands": [["scripts/export_motif_domain_site_context_preview.py"]],
        "artifact_paths": ["artifacts/status/motif_domain_site_context_preview.json"],
    },
    {
        "job_id": "interaction_context_enrichment",
        "lane_id": "biogrid_interaction_backbone",
        "commands": [["scripts/export_interaction_context_preview.py"]],
        "artifact_paths": ["artifacts/status/interaction_context_preview.json"],
    },
    {
        "job_id": "interaction_context_enrichment",
        "lane_id": "intact_interaction_backbone",
        "commands": [["scripts/export_interaction_context_preview.py"]],
        "artifact_paths": ["artifacts/status/interaction_context_preview.json"],
    },
    {
        "job_id": "bindingdb_assay_bridge_backbone",
        "lane_id": "bindingdb_assay_bridge_backbone",
        "commands": [
            ["scripts/export_bindingdb_target_polymer_context_preview.py"],
            ["scripts/export_binding_measurement_registry_preview.py"],
        ],
        "artifact_paths": [
            "artifacts/status/bindingdb_target_polymer_context_preview.json",
            "artifacts/status/binding_measurement_registry_preview.json",
        ],
    },
    {
        "job_id": "rcsb_pdbe_sifts_structure_backbone",
        "lane_id": "rcsb_pdbe_sifts_structure_backbone",
        "commands": [
            ["scripts/export_bindingdb_future_structure_registry_preview.py"],
            ["scripts/export_bindingdb_future_structure_context_preview.py"],
            ["scripts/export_bindingdb_future_structure_alignment_preview.py"],
            ["scripts/export_bindingdb_future_structure_triage_preview.py"],
        ],
        "artifact_paths": [
            "artifacts/status/bindingdb_future_structure_registry_preview.json",
            "artifacts/status/bindingdb_future_structure_context_preview.json",
            "artifacts/status/bindingdb_future_structure_alignment_preview.json",
            "artifacts/status/bindingdb_future_structure_triage_preview.json",
        ],
    },
    {
        "job_id": "pdbbind_measurement_backbone",
        "lane_id": "pdbbind_measurement_backbone",
        "commands": [
            ["execution/acquire/pdbbind_snapshot.py"],
            ["scripts/export_binding_measurement_registry_preview.py"],
        ],
        "artifact_paths": [
            "artifacts/status/pdbbind_local_snapshot_preview.json",
            "artifacts/status/binding_measurement_registry_preview.json",
        ],
    },
    {
        "job_id": "motif_active_site_enrichment",
        "lane_id": "elm_motif_backbone",
        "commands": [["scripts/export_elm_accession_cache_preview.py"]],
        "artifact_paths": ["artifacts/status/elm_accession_cache_preview.json"],
    },
    {
        "job_id": "kinetics_pathway_metadata_enrichment",
        "lane_id": "sabio_rk_kinetics_backbone",
        "commands": [["execution/acquire/sabio_rk_snapshot.py"]],
        "artifact_paths": ["artifacts/status/sabio_rk_accession_cache_preview.json"],
    },
    {
        "job_id": "string_interaction_materialization",
        "lane_id": "string_interaction_backbone",
        "commands": [["scripts/export_string_interaction_materialization_preview.py"]],
        "artifact_paths": [
            "artifacts/status/string_interaction_materialization_preview.json",
        ],
    },
)


def _run_command(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        [sys.executable, str(REPO_ROOT / command[0])],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode, (completed.stdout or completed.stderr or "").strip()


def build_pre_tail_scrape_wave_execution_preview(*, dry_run: bool) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for order, spec in enumerate(JOB_SPECS, start=1):
        started_at = datetime.now(UTC).isoformat()
        command_results: list[dict[str, Any]] = []
        overall_status = "dry_run_ready"
        if not dry_run:
            overall_status = "completed"
            for command in spec["commands"]:
                returncode, output = _run_command(command)
                command_results.append(
                    {
                        "command": [sys.executable, str(REPO_ROOT / command[0])],
                        "returncode": returncode,
                        "output_excerpt": output[-4000:],
                    }
                )
                if returncode != 0:
                    overall_status = "failed"
                    break
        rows.append(
            {
                "execution_order": order,
                "job_id": spec["job_id"],
                "lane_id": spec["lane_id"],
                "execution_status": overall_status,
                "started_at": started_at,
                "completed_at": datetime.now(UTC).isoformat(),
                "artifact_paths": [
                    str(REPO_ROOT / relative_path).replace("\\", "/")
                    for relative_path in spec["artifact_paths"]
                ],
                "command_results": command_results,
                "non_governing": True,
            }
        )
    return {
        "artifact_id": "pre_tail_scrape_wave_execution_preview",
        "schema_id": "proteosphere-pre-tail-scrape-wave-execution-preview-2026-04-04",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": {
            "structured_job_count": len(rows),
            "completed_job_count": sum(1 for row in rows if row["execution_status"] == "completed"),
            "failed_job_count": sum(1 for row in rows if row["execution_status"] == "failed"),
            "dry_run": dry_run,
        },
        "rows": rows,
        "truth_boundary": {
            "summary": (
                "This execution registry records the pre-tail structured scrape wave. All outputs "
                "remain additive and non-governing."
            ),
            "report_only": True,
            "non_governing": True,
            "structured_wave_executed": not dry_run,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Pre-Tail Scrape Wave Execution Preview",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Dry run: `{payload.get('summary', {}).get('dry_run')}`",
        "",
    ]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['execution_order']}` `{row['job_id']}` / `{row['execution_status']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute the pre-tail structured scrape wave in the planned order."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_pre_tail_scrape_wave_execution_preview(dry_run=args.dry_run)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(payload), encoding="utf-8")
    print(args.output_json)


if __name__ == "__main__":
    main()

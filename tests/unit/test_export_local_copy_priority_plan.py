from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import export_local_copy_priority_plan as planner  # noqa: E402


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_local_copy_priority_plan_infers_destinations_and_skips_existing_targets(
    tmp_path: Path,
) -> None:
    bio_root = tmp_path / "bio-agent-lab"
    local_copies_root = tmp_path / "repo" / "data" / "raw" / "local_copies"
    bio_root.mkdir(parents=True)
    local_copies_root.mkdir(parents=True)

    releases_src = bio_root / "data" / "releases" / "test_v1"
    releases_src.mkdir(parents=True)
    extracted_entry_src = bio_root / "data" / "extracted" / "entry"
    extracted_entry_src.mkdir(parents=True)
    skempi_src = bio_root / "data" / "raw" / "skempi"
    skempi_src.mkdir(parents=True)
    (skempi_src / "skempi_v2.csv").write_text("id,score\n", encoding="utf-8")
    pdbbind_src = bio_root / "data_sources" / "pdbbind"
    pdbbind_src.mkdir(parents=True)
    (pdbbind_src / "P-L.tar.gz").write_text("archive", encoding="utf-8")

    existing_target = local_copies_root / "extracted_entry"
    existing_target.mkdir(parents=True)

    priority_json = tmp_path / "p32_local_copy_priority.json"
    _write_json(
        priority_json,
        {
            "schema_id": "proteosphere-p32-local-copy-priority-2026-03-30",
            "generated_at": "2026-03-30T02:25:00-05:00",
            "uncopied_priority": [
                {
                    "priority": 1,
                    "path": str(releases_src),
                    "kind": "release_artifact",
                    "present_file_count": 17,
                    "present_total_bytes": 2333456,
                    "value": "Frozen cohort and release-manifest slice",
                    "why_now": "Anchor reproducibility",
                },
                {
                    "priority": 2,
                    "path": str(extracted_entry_src),
                    "kind": "extracted_structure_projection",
                    "present_file_count": 19416,
                    "present_total_bytes": 96957110,
                    "value": "Entry-level normalized structure summary projection",
                    "why_now": "Compact structure summaries",
                },
                {
                    "priority": 3,
                    "path": str(skempi_src / "skempi_v2.csv"),
                    "kind": "raw_benchmark_slice",
                    "present_file_count": 1,
                    "present_total_bytes": 1602208,
                    "value": "Protein-protein mutation and affinity benchmark slice",
                    "why_now": "Unique benchmark signal",
                },
                {
                    "priority": 4,
                    "path": str(pdbbind_src / "P-L.tar.gz"),
                    "kind": "source_archive",
                    "present_file_count": 1,
                    "present_total_bytes": 3340256670,
                    "value": "PDBbind protein-ligand archive",
                    "why_now": "Largest missing ligand/complex archive",
                },
            ],
        },
    )

    payload = planner.build_local_copy_priority_plan(
        priority_json_path=priority_json,
        bio_agent_lab_root=bio_root,
        local_copies_root=local_copies_root,
    )

    assert payload["status"] == "planning_only"
    assert payload["total_items"] == 4
    assert payload["pending_count"] == 3
    assert payload["skipped_count"] == 1
    assert payload["blocked_count"] == 0

    pending_by_slug = {item["destination_slug"]: item for item in payload["pending_items"]}
    assert pending_by_slug["releases_test_v1"]["copy_mode"] == "mirror_directory"
    assert pending_by_slug["releases_test_v1"]["destination_path"] == str(
        local_copies_root / "releases_test_v1"
    )
    assert pending_by_slug["skempi"]["copy_mode"] == "copy_file"
    assert pending_by_slug["skempi"]["destination_path"] == str(
        local_copies_root / "skempi" / "skempi_v2.csv"
    )
    assert pending_by_slug["pdbbind_pl"]["copy_mode"] == "copy_file"
    assert pending_by_slug["pdbbind_pl"]["destination_path"] == str(
        local_copies_root / "pdbbind_pl" / "P-L.tar.gz"
    )

    skipped = payload["skipped_items"]
    assert len(skipped) == 1
    assert skipped[0]["destination_slug"] == "extracted_entry"
    assert skipped[0]["mirror_status"] == "already_mirrored"
    assert skipped[0]["destination_exists"] is True
    assert skipped[0]["skip_reason"] == "destination already exists in local_copies"


def test_main_writes_output_json_without_mutating_inputs(tmp_path: Path, capsys) -> None:
    bio_root = tmp_path / "bio-agent-lab"
    local_copies_root = tmp_path / "repo" / "data" / "raw" / "local_copies"
    bio_root.mkdir(parents=True)
    local_copies_root.mkdir(parents=True)

    source_dir = bio_root / "data" / "releases" / "test_v1"
    source_dir.mkdir(parents=True)

    priority_json = tmp_path / "priority.json"
    _write_json(
        priority_json,
        {
            "schema_id": "proteosphere-p32-local-copy-priority-2026-03-30",
            "generated_at": "2026-03-30T02:25:00-05:00",
            "uncopied_priority": [
                {
                    "priority": 1,
                    "path": str(source_dir),
                    "kind": "release_artifact",
                    "present_file_count": 17,
                    "present_total_bytes": 2333456,
                    "value": "Frozen cohort and release-manifest slice",
                    "why_now": "Anchor reproducibility",
                }
            ],
        },
    )
    output_path = tmp_path / "plan.json"

    assert (
        planner.main(
            [
                "--priority-json",
                str(priority_json),
                "--bio-agent-lab-root",
                str(bio_root),
                "--local-copies-root",
                str(local_copies_root),
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert '"pending_count": 1' in captured.out
    assert output_path.exists()

    plan = json.loads(output_path.read_text(encoding="utf-8"))
    assert plan["pending_count"] == 1
    assert plan["pending_items"][0]["destination_slug"] == "releases_test_v1"
    assert plan["pending_items"][0]["destination_path"] == str(
        local_copies_root / "releases_test_v1"
    )

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import summarize_local_copy_status as status  # noqa: E402


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_local_copy_status_classifies_complete_in_progress_and_pending(
    tmp_path: Path,
) -> None:
    bio_root = tmp_path / "bio-agent-lab"
    local_copies_root = tmp_path / "repo" / "data" / "raw" / "local_copies"
    bio_root.mkdir(parents=True)
    local_copies_root.mkdir(parents=True)

    releases_src = bio_root / "data" / "releases" / "test_v1"
    releases_src.mkdir(parents=True)
    (local_copies_root / "releases_test_v1").mkdir(parents=True)
    (local_copies_root / "releases_test_v1" / "dataset_release_manifest.json").write_text(
        "{}",
        encoding="utf-8",
    )

    skempi_src = bio_root / "data" / "raw" / "skempi"
    skempi_src.mkdir(parents=True)
    (skempi_src / "skempi_v2.csv").write_text("id,score\n1,2\n", encoding="utf-8")

    pdbbind_src = bio_root / "data_sources" / "pdbbind"
    pdbbind_src.mkdir(parents=True)
    (pdbbind_src / "P-L.tar.gz").write_text("archive", encoding="utf-8")

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
                    "path": str(skempi_src / "skempi_v2.csv"),
                    "kind": "raw_benchmark_slice",
                    "present_file_count": 1,
                    "present_total_bytes": 1602208,
                    "value": "Protein-protein mutation and affinity benchmark slice",
                    "why_now": "Unique benchmark signal",
                },
                {
                    "priority": 3,
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

    log_root = tmp_path / "logs"
    log_root.mkdir(parents=True)
    (log_root / "robocopy_pdbbind_pl.log").write_text(
        "\n".join(
            [
                "ROBOCOPY :: Robust File Copy",
                "Source : C:\\Users\\jfvit\\Documents\\bio-agent-lab\\data_sources\\pdbbind",
                "Destination : D:\\documents\\ProteoSphereV2\\data\\raw\\local_copies\\pdbbind_pl",
                "Files : *.*",
            ]
        ),
        encoding="utf-8",
    )

    payload = status.build_local_copy_status(
        priority_json_path=priority_json,
        bio_agent_lab_root=bio_root,
        local_copies_root=local_copies_root,
        robocopy_logs=(),
        robocopy_log_roots=(log_root,),
    )

    assert payload["item_status_counts"] == {
        "complete": 1,
        "in_progress": 1,
        "pending": 1,
    }

    items = {item["destination_slug"]: item for item in payload["items"]}
    assert items["releases_test_v1"]["copy_status"] == "complete"
    assert items["releases_test_v1"]["destination_path"] == str(
        local_copies_root / "releases_test_v1"
    )
    assert items["releases_test_v1"]["destination_stats"]["file_count"] == 1
    assert items["skempi"]["copy_status"] == "pending"
    assert items["skempi"]["destination_path"].endswith(r"skempi\skempi_v2.csv")
    assert items["pdbbind_pl"]["copy_status"] == "in_progress"
    assert items["pdbbind_pl"]["matched_log_paths"] == [str(log_root / "robocopy_pdbbind_pl.log")]
    assert items["pdbbind_pl"]["status_reason"] == "matching active robocopy log found"


def test_main_writes_json_and_markdown_outputs(tmp_path: Path, capsys) -> None:
    bio_root = tmp_path / "bio-agent-lab"
    local_copies_root = tmp_path / "repo" / "data" / "raw" / "local_copies"
    bio_root.mkdir(parents=True)
    local_copies_root.mkdir(parents=True)

    source_dir = bio_root / "data" / "releases" / "test_v1"
    source_dir.mkdir(parents=True)
    (local_copies_root / "releases_test_v1").mkdir(parents=True)
    (local_copies_root / "releases_test_v1" / "dataset_release_manifest.json").write_text(
        "{}",
        encoding="utf-8",
    )

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

    output_path = tmp_path / "status.json"
    markdown_path = tmp_path / "status.md"

    assert (
        status.main(
            [
                "--priority-json",
                str(priority_json),
                "--bio-agent-lab-root",
                str(bio_root),
                "--local-copies-root",
                str(local_copies_root),
                "--output",
                str(output_path),
                "--markdown",
                str(markdown_path),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert "Local copy status exported" in captured.out
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["items"][0]["copy_status"] == "complete"
    assert markdown_path.exists()

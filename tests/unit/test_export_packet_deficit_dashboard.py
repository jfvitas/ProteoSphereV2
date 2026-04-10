from __future__ import annotations

import json
from pathlib import Path

from scripts.export_packet_deficit_dashboard import (
    build_packet_deficit_dashboard,
    main,
    render_markdown,
)


def _write_packet_manifest(
    root: Path,
    *,
    run_name: str,
    packet_name: str,
    packet_id: str,
    accession: str,
    status: str,
    requested_modalities: tuple[str, ...],
    present_modalities: tuple[str, ...],
    missing_modalities: tuple[str, ...],
    modality_sources: dict[str, tuple[str, ...]],
) -> Path:
    packet_dir = root / run_name / packet_name
    packet_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "packet_id": packet_id,
        "accession": accession,
        "canonical_id": f"protein:{accession}",
        "status": status,
        "packet_dir": str(packet_dir),
        "manifest_path": str(packet_dir / "packet_manifest.json"),
        "requested_modalities": list(requested_modalities),
        "present_modalities": list(present_modalities),
        "missing_modalities": list(missing_modalities),
        "modality_sources": {
            modality: list(refs) for modality, refs in modality_sources.items()
        },
        "raw_manifest_ids": [f"raw:{accession}"],
        "provenance_refs": [f"prov:{packet_id}"],
        "notes": ["materialized packet"],
        "artifacts": [
            {
                "modality": modality,
                "source_ref": refs[0],
                "relative_path": f"artifacts/{modality}.json",
                "payload_kind": "json",
                "size_bytes": 1,
                "notes": [],
            }
            for modality, refs in modality_sources.items()
            if modality in present_modalities and refs
        ],
    }
    path = packet_dir / "packet_manifest.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_build_packet_deficit_dashboard_summarizes_packet_deficits_and_source_fixes(
    tmp_path: Path,
) -> None:
    packages_root = tmp_path / "data" / "packages"
    _write_packet_manifest(
        packages_root,
        run_name="run-001",
        packet_name="packet-a",
        packet_id="packet-a",
        accession="P12345",
        status="partial",
        requested_modalities=("sequence", "structure", "ligand", "ppi"),
        present_modalities=("sequence", "ligand"),
        missing_modalities=("structure", "ppi"),
        modality_sources={
            "sequence": ("sequence:P12345",),
            "structure": ("structure:P12345",),
            "ligand": ("ligand:P12345",),
            "ppi": ("ppi:P12345",),
        },
    )
    _write_packet_manifest(
        packages_root,
        run_name="run-001",
        packet_name="packet-b",
        packet_id="packet-b",
        accession="P31749",
        status="unresolved",
        requested_modalities=("sequence", "structure", "ligand", "ppi"),
        present_modalities=("sequence",),
        missing_modalities=("structure", "ligand", "ppi"),
        modality_sources={
            "sequence": ("sequence:P31749",),
            "structure": ("structure:P31749",),
            "ligand": ("ligand:P31749",),
            "ppi": ("ppi:P31749",),
        },
    )
    _write_packet_manifest(
        packages_root,
        run_name="run-002",
        packet_name="packet-c",
        packet_id="packet-c",
        accession="P69905",
        status="complete",
        requested_modalities=("sequence", "structure"),
        present_modalities=("sequence", "structure"),
        missing_modalities=(),
        modality_sources={
            "sequence": ("sequence:P69905",),
            "structure": ("structure:P69905",),
        },
    )

    payload = build_packet_deficit_dashboard(packages_root=packages_root)

    assert payload["summary"]["packet_count"] == 3
    assert payload["summary"]["packet_status_counts"] == {
        "complete": 1,
        "partial": 1,
        "unresolved": 1,
    }
    assert payload["summary"]["packet_deficit_count"] == 2
    assert payload["summary"]["total_missing_modality_count"] == 5
    assert payload["summary"]["modality_deficit_counts"] == {
        "sequence": 0,
        "structure": 2,
        "ligand": 1,
        "ppi": 2,
    }

    packets = {row["packet_id"]: row for row in payload["packets"]}
    assert packets["packet-a"]["missing_modalities"] == ["structure", "ppi"]
    assert packets["packet-a"]["deficit_source_refs"] == [
        "structure:P12345",
        "ppi:P12345",
    ]
    assert packets["packet-b"]["missing_modality_count"] == 3
    assert packets["packet-c"]["status"] == "complete"

    source_fixes = {row["source_ref"]: row for row in payload["source_fix_candidates"]}
    assert source_fixes["structure:P31749"]["missing_modality_count"] == 1
    assert source_fixes["ppi:P12345"]["affected_packet_count"] == 1
    assert source_fixes["ligand:P31749"]["missing_modalities"] == ["ligand"]

    markdown = render_markdown(payload)
    assert "# Packet Deficit Dashboard" in markdown
    assert "`structure:P12345`" in markdown
    assert "`packet-b`" in markdown


def test_main_writes_dashboard_outputs(tmp_path: Path, capsys) -> None:
    packages_root = tmp_path / "data" / "packages"
    _write_packet_manifest(
        packages_root,
        run_name="run-001",
        packet_name="packet-a",
        packet_id="packet-a",
        accession="P12345",
        status="partial",
        requested_modalities=("sequence", "structure"),
        present_modalities=("sequence",),
        missing_modalities=("structure",),
        modality_sources={
            "sequence": ("sequence:P12345",),
            "structure": ("structure:P12345",),
        },
    )

    output = tmp_path / "artifacts" / "status" / "packet_deficit_dashboard.json"
    markdown_output = tmp_path / "docs" / "reports" / "packet_deficit_dashboard.md"
    exit_code = main(
        [
            "--packages-root",
            str(packages_root),
            "--output",
            str(output),
            "--markdown-output",
            str(markdown_output),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Packet deficit dashboard exported" in captured.out
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["summary"]["packet_count"] == 1
    assert markdown_output.exists()


def test_build_packet_deficit_dashboard_latest_only_uses_latest_summary(tmp_path: Path) -> None:
    packages_root = tmp_path / "data" / "packages"
    _write_packet_manifest(
        packages_root,
        run_name="run-001",
        packet_name="packet-a",
        packet_id="packet-a",
        accession="P12345",
        status="partial",
        requested_modalities=("sequence", "structure"),
        present_modalities=("sequence",),
        missing_modalities=("structure",),
        modality_sources={
            "sequence": ("sequence:P12345",),
            "structure": ("structure:P12345",),
        },
    )
    _write_packet_manifest(
        packages_root,
        run_name="run-002",
        packet_name="packet-a",
        packet_id="packet-a",
        accession="P12345",
        status="complete",
        requested_modalities=("sequence", "structure"),
        present_modalities=("sequence", "structure"),
        missing_modalities=(),
        modality_sources={
            "sequence": ("sequence:P12345",),
            "structure": ("structure:P12345",),
        },
    )
    latest_payload = {
        "run_id": "run-002",
        "packet_count": 1,
        "complete_count": 1,
        "partial_count": 0,
        "unresolved_count": 0,
        "packets": [
            {
                "packet_id": "packet-a",
                "accession": "P12345",
                "canonical_id": "protein:P12345",
                "status": "complete",
                "packet_dir": str(packages_root / "run-002" / "packet-a"),
                "manifest_path": str(
                    packages_root / "run-002" / "packet-a" / "packet_manifest.json"
                ),
                "requested_modalities": ["sequence", "structure"],
                "present_modalities": ["sequence", "structure"],
                "missing_modalities": [],
                "artifacts": [],
                "raw_manifest_ids": ["raw:P12345"],
                "provenance_refs": ["prov:packet-a"],
                "notes": ["latest packet only"],
            }
        ],
    }
    (packages_root / "LATEST.json").write_text(
        json.dumps(latest_payload, indent=2),
        encoding="utf-8",
    )

    payload = build_packet_deficit_dashboard(packages_root=packages_root, latest_only=True)

    assert payload["inputs"]["latest_only"] is True
    assert payload["summary"]["packet_count"] == 1
    assert payload["summary"]["packet_status_counts"] == {"complete": 1}
    assert payload["summary"]["packet_deficit_count"] == 0


def test_latest_only_dashboard_recovers_manifest_source_refs_from_sparse_summary(
    tmp_path: Path,
) -> None:
    packages_root = tmp_path / "data" / "packages"
    packet_manifest = _write_packet_manifest(
        packages_root,
        run_name="run-001",
        packet_name="packet-a",
        packet_id="packet-a",
        accession="Q9UCM0",
        status="partial",
        requested_modalities=("sequence", "structure", "ligand", "ppi"),
        present_modalities=("sequence", "ppi"),
        missing_modalities=("structure", "ligand"),
        modality_sources={
            "sequence": ("sequence:Q9UCM0",),
            "structure": ("structure:Q9UCM0",),
            "ligand": ("ligand:Q9UCM0",),
            "ppi": ("ppi:Q9UCM0",),
        },
    )
    latest_payload = {
        "run_id": "run-001",
        "packet_count": 1,
        "complete_count": 0,
        "partial_count": 1,
        "unresolved_count": 0,
        "packets": [
            {
                "packet_id": "packet-a",
                "accession": "Q9UCM0",
                "canonical_id": "protein:Q9UCM0",
                "status": "partial",
                "packet_dir": str(packages_root / "run-001" / "packet-a"),
                "manifest_path": str(packet_manifest),
                "requested_modalities": ["sequence", "structure", "ligand", "ppi"],
                "present_modalities": ["sequence", "ppi"],
                "missing_modalities": ["structure", "ligand"],
                "modality_sources": {},
                "artifacts": [],
                "raw_manifest_ids": [],
                "provenance_refs": [],
                "notes": ["sparse latest summary"],
            }
        ],
    }
    (packages_root / "LATEST.json").write_text(
        json.dumps(latest_payload, indent=2),
        encoding="utf-8",
    )

    payload = build_packet_deficit_dashboard(packages_root=packages_root, latest_only=True)

    packet = payload["packets"][0]
    assert packet["missing_source_refs"]["structure"] == ["structure:Q9UCM0"]
    assert packet["missing_source_refs"]["ligand"] == ["ligand:Q9UCM0"]
    source_fixes = {row["source_ref"]: row for row in payload["source_fix_candidates"]}
    assert "structure:Q9UCM0" in source_fixes
    assert "ligand:Q9UCM0" in source_fixes


def test_build_packet_deficit_dashboard_latest_only_recovers_manifest_modality_sources(
    tmp_path: Path,
) -> None:
    packages_root = tmp_path / "data" / "packages"
    manifest_path = _write_packet_manifest(
        packages_root,
        run_name="run-001",
        packet_name="packet-a",
        packet_id="packet-a",
        accession="P12345",
        status="partial",
        requested_modalities=("sequence", "structure", "ppi"),
        present_modalities=("sequence",),
        missing_modalities=("structure", "ppi"),
        modality_sources={
            "sequence": ("sequence:P12345",),
            "structure": ("structure:P12345",),
            "ppi": ("ppi:P12345",),
        },
    )
    latest_payload = {
        "run_id": "run-001",
        "packet_count": 1,
        "complete_count": 0,
        "partial_count": 1,
        "unresolved_count": 0,
        "packets": [
            {
                "packet_id": "packet-a",
                "accession": "P12345",
                "canonical_id": "protein:P12345",
                "status": "partial",
                "packet_dir": str(packages_root / "run-001" / "packet-a"),
                "manifest_path": str(manifest_path),
                "requested_modalities": ["sequence", "structure", "ppi"],
                "present_modalities": ["sequence"],
                "missing_modalities": ["structure", "ppi"],
                "artifacts": [],
                "raw_manifest_ids": ["raw:P12345"],
                "provenance_refs": ["prov:packet-a"],
                "notes": ["latest packet only"],
            }
        ],
    }
    (packages_root / "LATEST.json").write_text(
        json.dumps(latest_payload, indent=2),
        encoding="utf-8",
    )

    payload = build_packet_deficit_dashboard(packages_root=packages_root, latest_only=True)

    assert payload["inputs"]["latest_only"] is True
    assert payload["summary"]["packet_count"] == 1
    assert payload["summary"]["packet_deficit_count"] == 1
    packet = payload["packets"][0]
    assert packet["missing_source_refs"] == {
        "structure": ["structure:P12345"],
        "ppi": ["ppi:P12345"],
    }
    assert packet["deficit_source_refs"] == ["structure:P12345", "ppi:P12345"]
    source_fixes = {row["source_ref"]: row for row in payload["source_fix_candidates"]}
    assert source_fixes["structure:P12345"]["missing_modalities"] == ["structure"]
    assert source_fixes["ppi:P12345"]["missing_modalities"] == ["ppi"]

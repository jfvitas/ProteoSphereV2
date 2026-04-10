from __future__ import annotations

import json
from pathlib import Path

import pytest

from execution.materialization.training_packet_materializer import (
    TrainingPacketRequest,
    materialize_training_packets,
)


def test_materialize_training_packets_writes_complete_packet_bundle(tmp_path: Path) -> None:
    structure_source = tmp_path / "inputs" / "P12345.cif"
    structure_source.parent.mkdir(parents=True, exist_ok=True)
    structure_source.write_text("data_example", encoding="utf-8")

    result = materialize_training_packets(
        (
            TrainingPacketRequest(
                packet_id="packet-1",
                accession="P12345",
                canonical_id="protein:P12345",
                requested_modalities=("sequence", "structure", "ligand", "ppi"),
                modality_sources={
                    "sequence": ("sequence:P12345",),
                    "structure": ("structure:P12345",),
                    "ligand": ("ligand:P12345",),
                    "ppi": ("ppi:P12345",),
                },
                raw_manifest_ids=("manifest:uniprot", "manifest:alphafold"),
                provenance_refs=("prov:packet-1",),
            ),
        ),
        available_payloads={
            "sequence:P12345": {"sequence": "MKT", "length": 3},
            "structure:P12345": structure_source,
            "ligand:P12345": [{"ligand_id": "L1", "name": "ATP"}],
            "ppi:P12345": {"interactors": ["Q99999"]},
        },
        output_root=tmp_path / "data" / "packages",
        run_id="packet-run-1",
    )

    assert result.status == "complete"
    assert result.release_grade_ready is True
    assert result.latest_promotion_state == "promoted"
    assert result.complete_count == 1
    assert result.partial_count == 0
    packet = result.packets[0]
    assert packet.status == "complete"
    assert packet.present_modalities == ("sequence", "structure", "ligand", "ppi")
    assert packet.missing_modalities == ()
    assert len(packet.artifacts) == 4
    assert (tmp_path / "data" / "packages" / "LATEST.json").exists()
    assert (tmp_path / "data" / "packages" / "LATEST.release.json").exists()
    summary_path = (
        tmp_path / "data" / "packages" / "packet-run-1" / "materialization_summary.json"
    )
    summary_payload = json.loads(
        summary_path.read_text(encoding="utf-8")
    )
    assert summary_payload["status"] == "complete"
    assert summary_payload["release_grade_ready"] is True
    assert summary_payload["latest_promotion_state"] == "promoted"
    assert summary_payload["packets"][0]["release_grade_ready"] is True
    assert summary_payload["packets"][0]["latest_promotion_state"] == "promoted"
    assert summary_payload["packets"][0]["modality_sources"] == {
        "sequence": ["sequence:P12345"],
        "structure": ["structure:P12345"],
        "ligand": ["ligand:P12345"],
        "ppi": ["ppi:P12345"],
    }
    manifest_payload = json.loads(Path(packet.manifest_path).read_text(encoding="utf-8"))
    assert manifest_payload["status"] == "complete"
    assert sorted(manifest_payload["present_modalities"]) == [
        "ligand",
        "ppi",
        "sequence",
        "structure",
    ]


def test_materialize_training_packets_stays_conservative_about_missing_modalities(
    tmp_path: Path,
) -> None:
    result = materialize_training_packets(
        (
            {
                "packet_id": "packet-2",
                "accession": "P31749",
                "canonical_id": "protein:P31749",
                "requested_modalities": ("sequence", "structure", "ligand", "ppi"),
                "modality_sources": {
                    "sequence": ("sequence:P31749",),
                    "structure": ("structure:P31749",),
                    "ligand": ("ligand:P31749",),
                    "ppi": ("ppi:P31749",),
                },
                "notes": ("frozen cohort row",),
            },
        ),
        available_payloads={
            "sequence:P31749": {"sequence": "MSDVA", "length": 5},
            "ligand:P31749": {"ligands": ["LIG1", "LIG2"]},
        },
        output_root=tmp_path / "data" / "packages",
        run_id="packet-run-2",
    )

    assert result.status == "partial"
    assert result.release_grade_ready is False
    assert result.latest_promotion_state == "held"
    assert result.complete_count == 0
    assert result.partial_count == 1
    assert result.unresolved_count == 0
    packet = result.packets[0]
    assert packet.status == "partial"
    assert packet.present_modalities == ("sequence", "ligand")
    assert packet.missing_modalities == ("structure", "ppi")
    manifest_payload = json.loads(Path(packet.manifest_path).read_text(encoding="utf-8"))
    assert manifest_payload["status"] == "partial"
    assert manifest_payload["release_grade_ready"] is False
    assert manifest_payload["latest_promotion_state"] == "held"
    assert manifest_payload["missing_modalities"] == ["structure", "ppi"]
    assert "missing payload for structure:structure:P31749" in manifest_payload["notes"]
    assert "missing payload for ppi:ppi:P31749" in manifest_payload["notes"]
    assert (tmp_path / "data" / "packages" / "LATEST.partial.json").exists()


def test_materialize_training_packets_holds_per_packet_latest_state_when_run_is_partial(
    tmp_path: Path,
) -> None:
    result = materialize_training_packets(
        (
            TrainingPacketRequest(
                packet_id="packet-complete",
                accession="P68871",
                canonical_id="protein:P68871",
                requested_modalities=("sequence", "structure", "ligand", "ppi"),
                modality_sources={
                    "sequence": ("sequence:P68871",),
                    "structure": ("structure:P68871",),
                    "ligand": ("ligand:P68871",),
                    "ppi": ("ppi:P68871",),
                },
            ),
            TrainingPacketRequest(
                packet_id="packet-partial",
                accession="Q9UCM0",
                canonical_id="protein:Q9UCM0",
                requested_modalities=("sequence", "structure", "ligand", "ppi"),
                modality_sources={
                    "sequence": ("sequence:Q9UCM0",),
                    "structure": ("structure:Q9UCM0",),
                    "ligand": ("ligand:Q9UCM0",),
                    "ppi": ("ppi:Q9UCM0",),
                },
            ),
        ),
        available_payloads={
            "sequence:P68871": {"sequence": "VHLTPEE", "length": 7},
            "structure:P68871": {"pdb_id": "1A3N"},
            "ligand:P68871": {"ligand": "HEM"},
            "ppi:P68871": {"interactors": ["P69905"]},
            "sequence:Q9UCM0": {"sequence": "MKT", "length": 3},
        },
        output_root=tmp_path / "data" / "packages",
        run_id="packet-run-mixed",
    )

    assert result.status == "partial"
    assert result.latest_promotion_state == "held"
    packets = {packet.accession: packet for packet in result.packets}
    assert packets["P68871"].status == "complete"
    assert packets["P68871"].release_grade_ready is True
    assert packets["P68871"].latest_promotion_state == "held"
    complete_manifest = json.loads(
        Path(packets["P68871"].manifest_path).read_text(encoding="utf-8")
    )
    assert complete_manifest["status"] == "complete"
    assert complete_manifest["release_grade_ready"] is True
    assert complete_manifest["latest_promotion_state"] == "held"


def test_materialize_training_packets_marks_unresolved_when_no_payloads_exist(
    tmp_path: Path,
) -> None:
    result = materialize_training_packets(
        (
            TrainingPacketRequest(
                packet_id="packet-3",
                accession="P04637",
                canonical_id="protein:P04637",
                requested_modalities=("sequence", "structure"),
                modality_sources={
                    "sequence": ("sequence:P04637",),
                    "structure": ("structure:P04637",),
                },
            ),
        ),
        available_payloads={},
        output_root=tmp_path / "data" / "packages",
        run_id="packet-run-3",
    )

    assert result.status == "unresolved"
    assert result.release_grade_ready is False
    assert result.latest_promotion_state == "held"
    assert result.unresolved_count == 1
    packet = result.packets[0]
    assert packet.status == "unresolved"
    assert packet.present_modalities == ()
    assert packet.missing_modalities == ("sequence", "structure")
    manifest_payload = json.loads(Path(packet.manifest_path).read_text(encoding="utf-8"))
    assert manifest_payload["artifacts"] == []
    assert manifest_payload["status"] == "unresolved"
    assert manifest_payload["release_grade_ready"] is False
    assert manifest_payload["latest_promotion_state"] == "held"


def test_materialize_training_packets_latest_summary_keeps_modality_sources(
    tmp_path: Path,
) -> None:
    result = materialize_training_packets(
        (
            TrainingPacketRequest(
                packet_id="packet-4",
                accession="Q9UCM0",
                canonical_id="protein:Q9UCM0",
                requested_modalities=("sequence", "structure", "ligand", "ppi"),
                modality_sources={
                    "sequence": ("sequence:Q9UCM0",),
                    "structure": ("structure:Q9UCM0",),
                    "ligand": ("ligand:Q9UCM0",),
                    "ppi": ("ppi:Q9UCM0",),
                },
            ),
        ),
        available_payloads={
            "sequence:Q9UCM0": {"sequence": "MKT", "length": 3},
            "ppi:Q9UCM0": {"interactors": ["Q99999"]},
        },
        output_root=tmp_path / "data" / "packages",
        run_id="packet-run-4",
    )

    latest_payload = json.loads(
        (tmp_path / "data" / "packages" / "LATEST.json").read_text(encoding="utf-8")
    )

    assert result.status == "partial"
    assert result.release_grade_ready is False
    assert result.latest_promotion_state == "held"
    assert latest_payload["packets"][0]["modality_sources"] == {
        "sequence": ["sequence:Q9UCM0"],
        "structure": ["structure:Q9UCM0"],
        "ligand": ["ligand:Q9UCM0"],
        "ppi": ["ppi:Q9UCM0"],
    }
    assert latest_payload["packets"][0]["release_grade_ready"] is False
    assert latest_payload["packets"][0]["latest_promotion_state"] == "held"
    assert latest_payload["release_grade_ready"] is False
    assert latest_payload["latest_promotion_state"] == "held"


def test_materialize_training_packets_does_not_replace_stronger_latest_with_weaker_partial(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "data" / "packages"
    stronger = materialize_training_packets(
        (
            TrainingPacketRequest(
                packet_id="packet-strong",
                accession="P68871",
                canonical_id="protein:P68871",
                requested_modalities=("sequence", "structure", "ligand", "ppi"),
                modality_sources={
                    "sequence": ("sequence:P68871",),
                    "structure": ("structure:P68871",),
                    "ligand": ("ligand:P68871",),
                    "ppi": ("ppi:P68871",),
                },
            ),
        ),
        available_payloads={
            "sequence:P68871": {"sequence": "VHLTPEE", "length": 7},
            "structure:P68871": {"pdb_id": "1A3N"},
            "ligand:P68871": {"ligand": "HEM"},
            "ppi:P68871": {"interactors": ["P69905"]},
        },
        output_root=output_root,
        run_id="packet-run-strong",
    )

    weaker = materialize_training_packets(
        (
            TrainingPacketRequest(
                packet_id="packet-weak",
                accession="Q9UCM0",
                canonical_id="protein:Q9UCM0",
                requested_modalities=("sequence", "structure", "ligand", "ppi"),
                modality_sources={
                    "sequence": ("sequence:Q9UCM0",),
                    "structure": ("structure:Q9UCM0",),
                    "ligand": ("ligand:Q9UCM0",),
                    "ppi": ("ppi:Q9UCM0",),
                },
            ),
        ),
        available_payloads={
            "sequence:Q9UCM0": {"sequence": "MKT", "length": 3},
        },
        output_root=output_root,
        run_id="packet-run-weak",
    )

    latest_payload = json.loads((output_root / "LATEST.json").read_text(encoding="utf-8"))
    latest_partial_payload = json.loads(
        (output_root / "LATEST.partial.json").read_text(encoding="utf-8")
    )

    assert stronger.status == "complete"
    assert weaker.status == "partial"
    assert latest_payload["run_id"] == "packet-run-strong"
    assert latest_payload["status"] == "complete"
    assert latest_partial_payload["run_id"] == "packet-run-weak"
    assert latest_partial_payload["status"] == "partial"


def test_materialize_training_packets_normalizes_inconsistent_preserved_latest(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "data" / "packages"
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "LATEST.json").write_text(
        json.dumps(
            {
                "run_id": "older-partial-run",
                "status": "partial",
                "release_grade_ready": False,
                "latest_promotion_state": "held",
                "packet_count": 1,
                "complete_count": 1,
                "partial_count": 0,
                "unresolved_count": 0,
                "packets": [
                    {
                        "packet_id": "packet-older",
                        "accession": "P68871",
                        "status": "complete",
                        "release_grade_ready": True,
                        "latest_promotion_state": "promoted",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = materialize_training_packets(
        (
            TrainingPacketRequest(
                packet_id="packet-weak",
                accession="Q9UCM0",
                canonical_id="protein:Q9UCM0",
                requested_modalities=("sequence", "structure", "ligand", "ppi"),
                modality_sources={
                    "sequence": ("sequence:Q9UCM0",),
                    "structure": ("structure:Q9UCM0",),
                    "ligand": ("ligand:Q9UCM0",),
                    "ppi": ("ppi:Q9UCM0",),
                },
            ),
        ),
        available_payloads={
            "sequence:Q9UCM0": {"sequence": "MKT", "length": 3},
        },
        output_root=output_root,
        run_id="packet-run-weak-normalize",
    )

    latest_payload = json.loads((output_root / "LATEST.json").read_text(encoding="utf-8"))

    assert result.status == "partial"
    assert latest_payload["run_id"] == "older-partial-run"
    assert latest_payload["latest_promotion_state"] == "held"
    assert latest_payload["packets"][0]["status"] == "complete"
    assert latest_payload["packets"][0]["latest_promotion_state"] == "held"


def test_materialize_training_packets_rejects_ambiguous_string_file_refs(
    tmp_path: Path,
) -> None:
    with pytest.raises(TypeError, match="ambiguous string payload looks like a file reference"):
        materialize_training_packets(
            (
                TrainingPacketRequest(
                    packet_id="packet-5",
                    accession="P69905",
                    canonical_id="protein:P69905",
                    requested_modalities=("structure",),
                    modality_sources={"structure": ("structure:P69905",)},
                ),
            ),
            available_payloads={
                "structure:P69905": "data/raw/alphafold/20260323T154140Z/P69905/P69905.cif.cif"
            },
            output_root=tmp_path / "data" / "packages",
            run_id="packet-run-5",
        )

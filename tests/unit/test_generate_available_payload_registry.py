from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_generate_available_payload_registry_cli(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    balanced_plan = tmp_path / "balanced.json"
    canonical_latest = tmp_path / "canonical" / "LATEST.json"
    raw_root = tmp_path / "raw"
    output = tmp_path / "available_payloads.generated.json"

    _write_json(
        balanced_plan,
        {
            "selected_rows": [
                {
                    "accession": "P12345",
                    "canonical_id": "protein:P12345",
                    "packet_expectation": {
                        "requested_modalities": ["sequence", "structure"],
                        "present_modalities": ["sequence"],
                        "missing_modalities": ["structure"],
                    },
                }
            ]
        },
    )
    _write_json(
        canonical_latest,
        {
            "sequence_result": {
                "canonical_proteins": [
                    {
                        "accession": "P12345",
                        "canonical_id": "protein:P12345",
                        "sequence": "MKT",
                        "sequence_length": 3,
                    }
                ]
            }
        },
    )
    (raw_root / "alphafold" / "20260323T100000Z" / "P12345").mkdir(parents=True, exist_ok=True)
    (raw_root / "alphafold" / "20260323T100000Z" / "P12345" / "P12345.cif.cif").write_text(
        "cif",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "generate_available_payload_registry.py"),
            "--balanced-plan",
            str(balanced_plan),
            "--canonical-latest",
            str(canonical_latest),
            "--raw-root",
            str(raw_root),
            "--output",
            str(output),
            "--json",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    payload = json.loads(result.stdout)
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert payload == saved
    assert payload["available_payload_count"] == 2
    assert payload["missing_payload_count"] == 0
    assert payload["input_fingerprints"]["balanced_plan_sha256"]
    assert len(payload["input_fingerprints"]["balanced_plan_sha256"]) == 64
    assert payload["input_fingerprints"]["canonical_latest_sha256"]
    assert len(payload["input_fingerprints"]["canonical_latest_sha256"]) == 64
    assert payload["registry_fingerprints"]["available_payloads_sha256"]
    assert len(payload["registry_fingerprints"]["available_payloads_sha256"]) == 64
    assert payload["registry_fingerprints"]["build_sha256"]
    assert len(payload["registry_fingerprints"]["build_sha256"]) == 64
    assert payload["registry_fingerprints"]["digest_basis"] == "sorted_json_content"
    assert payload["available_payloads"]["sequence:P12345"]["sequence"] == "MKT"
    assert payload["available_payloads"]["structure:P12345"] == {
        "kind": "file_ref",
        "path": str(
            raw_root / "alphafold" / "20260323T100000Z" / "P12345" / "P12345.cif.cif"
        ).replace("\\", "/"),
    }

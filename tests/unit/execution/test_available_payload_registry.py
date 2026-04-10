from __future__ import annotations

import json
from pathlib import Path

import pytest

from execution.materialization.available_payload_registry import (
    build_available_payload_registry,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_available_payload_registry_resolves_modalities_from_canonical_and_raw(
    tmp_path: Path,
) -> None:
    balanced_plan = {
        "selected_rows": [
            {
                "accession": "P12345",
                "canonical_id": "protein:P12345",
                "packet_expectation": {
                    "requested_modalities": ["sequence", "structure", "ligand", "ppi"],
                    "present_modalities": ["sequence", "structure", "ligand", "ppi"],
                    "missing_modalities": [],
                },
            },
            {
                "accession": "Q99999",
                "canonical_id": "protein:Q99999",
                "packet_expectation": {
                    "requested_modalities": ["sequence", "structure"],
                    "present_modalities": ["sequence"],
                    "missing_modalities": ["structure"],
                },
            },
        ]
    }
    canonical_latest = tmp_path / "data" / "canonical" / "LATEST.json"
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
                        "source": "UniProt",
                    },
                    {
                        "accession": "Q99999",
                        "canonical_id": "protein:Q99999",
                        "sequence": "AAAA",
                        "sequence_length": 4,
                        "source": "UniProt",
                    },
                ]
            }
        },
    )
    raw_root = tmp_path / "data" / "raw"
    (raw_root / "alphafold" / "20260323T100000Z" / "P12345").mkdir(parents=True, exist_ok=True)
    (raw_root / "alphafold" / "20260323T100000Z" / "P12345" / "P12345.cif.cif").write_text(
        "cif",
        encoding="utf-8",
    )
    (raw_root / "bindingdb" / "20260323T100000Z" / "P12345").mkdir(parents=True, exist_ok=True)
    _write_json(
        raw_root / "bindingdb" / "20260323T100000Z" / "P12345" / "P12345.bindingdb.json",
        {
            "getLindsByUniprotResponse": {
                "bdb.primary": "P12345",
                "bdb.affinities": [
                    {
                        "reactant_set_id": "R-1",
                        "monomer_id": "M-1",
                        "ligand_smiles": "CCO",
                    }
                ],
            }
        },
    )
    (raw_root / "intact" / "20260323T100000Z" / "P12345").mkdir(parents=True, exist_ok=True)
    (
        raw_root / "intact" / "20260323T100000Z" / "P12345" / "P12345.psicquic.tab25.txt"
    ).write_text(
        "uniprotkb:P12345\tuniprotkb:Q99998\tintact:EBI-1\tintact:EBI-2\tpsi-mi:P12345\t"
        "psi-mi:Q99998\tpsi-mi:\"MI:0018\"(two hybrid)\tAuthor et al.\tpubmed:1\t"
        "taxid:9606(Homo sapiens)\ttaxid:9606(Homo sapiens)\t"
        "psi-mi:\"MI:0915\"(physical association)\tpsi-mi:\"MI:0469\"(IntAct)\t"
        "intact:EBI-999|imex:IM-999\tintact-miscore:0.98\tspoke expansion\n",
        encoding="utf-8",
    )

    registry = build_available_payload_registry(
        balanced_plan=balanced_plan,
        canonical_latest_path=canonical_latest,
        raw_root=raw_root,
    )

    payload = registry.to_dict()
    assert payload["available_payload_count"] == 5
    assert payload["missing_payload_refs"] == ["structure:Q99999"]
    assert payload["available_payloads"]["sequence:P12345"]["sequence"] == "MKT"
    assert payload["available_payloads"]["structure:P12345"] == {
        "kind": "file_ref",
        "path": str(
            raw_root / "alphafold" / "20260323T100000Z" / "P12345" / "P12345.cif.cif"
        ).replace("\\", "/"),
    }
    assert payload["available_payloads"]["ligand:P12345"] == {
        "kind": "file_ref",
        "path": str(
            raw_root / "bindingdb" / "20260323T100000Z" / "P12345" / "P12345.bindingdb.json"
        ).replace("\\", "/"),
    }
    assert payload["available_payloads"]["ppi:P12345"] == {
        "kind": "file_ref",
        "path": str(
            raw_root / "intact" / "20260323T100000Z" / "P12345" / "P12345.psicquic.tab25.txt"
        ).replace("\\", "/"),
    }


def test_build_available_payload_registry_uses_local_alphafold_and_bridge_ligand_backfill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    balanced_plan = {
        "selected_rows": [
            {
                "accession": "Q2TAC2",
                "canonical_id": "protein:Q2TAC2",
                "packet_expectation": {
                    "requested_modalities": ["sequence", "structure", "ligand"],
                    "present_modalities": ["sequence"],
                    "missing_modalities": ["structure", "ligand"],
                },
            },
            {
                "accession": "P02042",
                "canonical_id": "protein:P02042",
                "packet_expectation": {
                    "requested_modalities": ["sequence", "ligand"],
                    "present_modalities": ["sequence"],
                    "missing_modalities": ["ligand"],
                },
            },
        ]
    }
    canonical_latest = tmp_path / "data" / "canonical" / "LATEST.json"
    _write_json(
        canonical_latest,
        {
            "sequence_result": {
                "canonical_proteins": [
                    {
                        "accession": "Q2TAC2",
                        "canonical_id": "protein:Q2TAC2",
                        "sequence": "MKT",
                        "sequence_length": 3,
                    },
                    {
                        "accession": "P02042",
                        "canonical_id": "protein:P02042",
                        "sequence": "AAAA",
                        "sequence_length": 4,
                    },
                ]
            }
        },
    )
    raw_root = tmp_path / "data" / "raw"
    (raw_root / "alphafold_local" / "20260323T100000Z" / "Q2TAC2").mkdir(
        parents=True,
        exist_ok=True,
    )
    (
        raw_root
        / "alphafold_local"
        / "20260323T100000Z"
        / "Q2TAC2"
        / "AF-Q2TAC2-F1-model_v6.pdb.gz"
    ).write_text("pdb", encoding="utf-8")

    bridge_path = tmp_path / "artifacts" / "status" / "local_bridge_ligand_payloads.real.json"
    _write_json(
        bridge_path,
        {
            "entries": [
                {
                    "accession": "P02042",
                    "pdb_id": "1SHR",
                    "bridge_kind": "bridge_only",
                    "selected_ligand": {"component_id": "CYN"},
                    "bridge_record": {
                        "source_name": "extracted_bound_objects",
                        "source_record_id": "P02042:1SHR:CYN",
                    },
                }
            ]
        },
    )
    monkeypatch.setattr(
        "execution.materialization.available_payload_registry.ROOT",
        tmp_path,
    )

    registry = build_available_payload_registry(
        balanced_plan=balanced_plan,
        canonical_latest_path=canonical_latest,
        raw_root=raw_root,
    )

    payload = registry.to_dict()
    assert payload["available_payloads"]["structure:Q2TAC2"] == {
        "kind": "file_ref",
        "path": str(
            raw_root
            / "alphafold_local"
            / "20260323T100000Z"
            / "Q2TAC2"
            / "AF-Q2TAC2-F1-model_v6.pdb.gz"
        ).replace("\\", "/"),
    }
    assert payload["available_payloads"]["ligand:P02042"]["source"] == "local_bridge_ligand"
    assert payload["available_payloads"]["ligand:P02042"]["bridge_record"]["source_record_id"] == (
        "P02042:1SHR:CYN"
    )


def test_build_available_payload_registry_accepts_default_bridge_ligand_filename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    balanced_plan = {
        "selected_rows": [
            {
                "accession": "P02100",
                "canonical_id": "protein:P02100",
                "packet_expectation": {
                    "requested_modalities": ["sequence", "ligand"],
                    "present_modalities": ["sequence"],
                    "missing_modalities": ["ligand"],
                },
            }
        ]
    }
    canonical_latest = tmp_path / "data" / "canonical" / "LATEST.json"
    _write_json(
        canonical_latest,
        {
            "sequence_result": {
                "canonical_proteins": [
                    {
                        "accession": "P02100",
                        "canonical_id": "protein:P02100",
                        "sequence": "MVHFTA",
                        "sequence_length": 6,
                    }
                ]
            }
        },
    )
    raw_root = tmp_path / "data" / "raw"
    bridge_path = tmp_path / "artifacts" / "status" / "local_bridge_ligand_payloads.json"
    _write_json(
        bridge_path,
        {
            "entries": [
                {
                    "accession": "P02100",
                    "pdb_id": "1A9W",
                    "bridge_kind": "bridge_only",
                    "selected_ligand": {"component_id": "CMO"},
                    "bridge_record": {
                        "source_name": "extracted_bound_objects",
                        "source_record_id": "P02100:1A9W:CMO",
                    },
                }
            ]
        },
    )
    monkeypatch.setattr(
        "execution.materialization.available_payload_registry.ROOT",
        tmp_path,
    )

    registry = build_available_payload_registry(
        balanced_plan=balanced_plan,
        canonical_latest_path=canonical_latest,
        raw_root=raw_root,
    )

    payload = registry.to_dict()
    assert payload["available_payloads"]["ligand:P02100"]["source"] == "local_bridge_ligand"
    assert payload["available_payloads"]["ligand:P02100"]["bridge_record"]["source_record_id"] == (
        "P02100:1A9W:CMO"
    )


def test_build_available_payload_registry_uses_q9nzd4_ready_now_bridge_ligand_backfill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    balanced_plan = {
        "selected_rows": [
            {
                "accession": "Q9NZD4",
                "canonical_id": "protein:Q9NZD4",
                "packet_expectation": {
                    "requested_modalities": ["sequence", "structure", "ligand", "ppi"],
                    "present_modalities": ["sequence"],
                    "missing_modalities": ["structure", "ligand", "ppi"],
                },
            }
        ]
    }
    canonical_latest = tmp_path / "data" / "canonical" / "LATEST.json"
    _write_json(
        canonical_latest,
        {
            "sequence_result": {
                "canonical_proteins": [
                    {
                        "accession": "Q9NZD4",
                        "canonical_id": "protein:Q9NZD4",
                        "sequence": "MALLKANKDL",
                        "sequence_length": 10,
                    }
                ]
            }
        },
    )
    raw_root = tmp_path / "data" / "raw"
    bridge_path = tmp_path / "artifacts" / "status" / "local_bridge_ligand_payloads.real.json"
    _write_json(
        bridge_path,
        {
            "entries": [
                {
                    "accession": "Q9NZD4",
                    "pdb_id": "1Y01",
                    "bridge_kind": "bridge_only",
                    "bridge_state": "ready_now",
                    "selected_ligand": {"component_id": "CHK"},
                    "bridge_record": {
                        "source_name": "extracted_bound_objects",
                        "source_record_id": "Q9NZD4:1Y01:CHK",
                    },
                }
            ]
        },
    )
    monkeypatch.setattr(
        "execution.materialization.available_payload_registry.ROOT",
        tmp_path,
    )

    registry = build_available_payload_registry(
        balanced_plan=balanced_plan,
        canonical_latest_path=canonical_latest,
        raw_root=raw_root,
    )

    payload = registry.to_dict()
    assert payload["available_payloads"]["ligand:Q9NZD4"]["source"] == "local_bridge_ligand"
    assert payload["available_payloads"]["ligand:Q9NZD4"]["bridge_record"]["source_record_id"] == (
        "Q9NZD4:1Y01:CHK"
    )


def test_build_available_payload_registry_accepts_local_chembl_ligand_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    balanced_plan = {
        "selected_rows": [
            {
                "accession": "P00387",
                "canonical_id": "protein:P00387",
                "packet_expectation": {
                    "requested_modalities": ["ligand"],
                    "present_modalities": [],
                    "missing_modalities": ["ligand"],
                },
            }
        ]
    }
    canonical_latest = tmp_path / "data" / "canonical" / "LATEST.json"
    _write_json(canonical_latest, {"sequence_result": {"canonical_proteins": []}})
    raw_root = tmp_path / "data" / "raw"
    chembl_payload_path = (
        tmp_path / "artifacts" / "status" / "p00387_local_chembl_ligand_payload.json"
    )
    _write_json(
        chembl_payload_path,
        {
            "accession": "P00387",
            "status": "resolved",
            "packet_source_ref": "ligand:P00387",
            "source_db_path": "C:/bio-agent-lab/chembl.db",
            "summary": {
                "target_chembl_id": "CHEMBL2146",
                "activity_count_total": 93,
            },
            "truth_boundary": {
                "fresh_run_scope_only": True,
                "can_promote_latest_now": False,
            },
            "rows": [
                {
                    "ligand_chembl_id": "CHEMBL506",
                    "ligand_pref_name": "PRIMAQUINE",
                    "canonical_smiles": "COc1cc(NC(C)CCCN)c2ncccc2c1",
                }
            ],
        },
    )
    monkeypatch.setattr(
        "execution.materialization.available_payload_registry.ROOT",
        tmp_path,
    )

    registry = build_available_payload_registry(
        balanced_plan=balanced_plan,
        canonical_latest_path=canonical_latest,
        raw_root=raw_root,
    )

    payload = registry.to_dict()
    assert payload["missing_payload_count"] == 0
    assert payload["available_payloads"]["ligand:P00387"]["source"] == "local_chembl_ligand"
    assert payload["available_payloads"]["ligand:P00387"]["summary"]["target_chembl_id"] == (
        "CHEMBL2146"
    )
    assert payload["available_payloads"]["ligand:P00387"]["rows"][0]["ligand_chembl_id"] == (
        "CHEMBL506"
    )


def test_build_available_payload_registry_prefers_local_bridge_ppi_backfill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    balanced_plan = {
        "selected_rows": [
            {
                "accession": "P04637",
                "canonical_id": "protein:P04637",
                "packet_expectation": {
                    "requested_modalities": ["ppi"],
                    "present_modalities": [],
                    "missing_modalities": ["ppi"],
                },
            }
        ]
    }
    canonical_latest = tmp_path / "data" / "canonical" / "LATEST.json"
    _write_json(canonical_latest, {"sequence_result": {"canonical_proteins": []}})
    raw_root = tmp_path / "data" / "raw"
    bridge_path = tmp_path / "artifacts" / "status" / "local_bridge_ppi_payloads.real.json"
    _write_json(
        bridge_path,
        {
            "entries": [
                {
                    "pdb_id": "1GZH",
                    "accession_a": "P04637",
                    "accession_b": "Q12888",
                    "canonical_id_a": "protein:P04637",
                    "canonical_id_b": "protein:Q12888",
                    "status": "resolved",
                    "bridge_state": "positive_hit",
                    "bridge_kind": "bridge_only",
                    "chain_assignment_state": "not_asserted",
                    "observed_accessions": ["P04637", "Q12888"],
                    "observed_chain_ids": ["A", "B", "D"],
                    "pair_canonical_id": "pair:P04637--Q12888",
                    "bridge_record": {
                        "source_name": "master_pdb_repository",
                        "source_kind": "protein_protein",
                        "source_record_id": "1GZH:P04637:Q12888",
                        "source_entry_id": "extracted_interfaces",
                        "pdb_id": "1GZH",
                        "status": "resolved",
                        "pair_canonical_id": "pair:P04637--Q12888",
                        "protein_canonical_ids": ["protein:P04637", "protein:Q12888"],
                        "proteins": [],
                        "ligands": [],
                        "issues": [],
                        "provenance": {"source_name": "extracted_interfaces"},
                    },
                    "notes": ["pair_accessions_resolved_from_master_repository"],
                    "issues": [],
                }
            ]
        },
    )
    monkeypatch.setattr(
        "execution.materialization.available_payload_registry.ROOT",
        tmp_path,
    )

    registry = build_available_payload_registry(
        balanced_plan=balanced_plan,
        canonical_latest_path=canonical_latest,
        raw_root=raw_root,
    )

    payload = registry.to_dict()
    assert payload["missing_payload_count"] == 0
    assert payload["available_payloads"]["ppi:P04637"]["accession_a"] == "P04637"
    assert payload["available_payloads"]["ppi:P04637"]["accession_b"] == "Q12888"
    assert payload["available_payloads"]["ppi:P04637"]["pair_canonical_id"] == (
        "pair:P04637--Q12888"
    )


def test_build_available_payload_registry_falls_back_to_raw_uniprot_sequence(
    tmp_path: Path,
) -> None:
    balanced_plan = {
        "selected_rows": [
            {
                "accession": "P69905",
                "canonical_id": "protein:P69905",
                "packet_expectation": {
                    "requested_modalities": ["sequence"],
                    "present_modalities": [],
                    "missing_modalities": ["sequence"],
                },
            }
        ]
    }
    canonical_latest = tmp_path / "data" / "canonical" / "LATEST.json"
    _write_json(canonical_latest, {"sequence_result": {"canonical_proteins": []}})
    raw_root = tmp_path / "data" / "raw"
    (raw_root / "uniprot" / "20260323T100000Z" / "P69905").mkdir(parents=True, exist_ok=True)
    (raw_root / "uniprot" / "20260323T100000Z" / "P69905" / "P69905.fasta").write_text(
        ">P69905\nMVLSPADK\n",
        encoding="utf-8",
    )

    registry = build_available_payload_registry(
        balanced_plan=balanced_plan,
        canonical_latest_path=canonical_latest,
        raw_root=raw_root,
    )

    payload = registry.to_dict()
    assert payload["missing_payload_count"] == 0
    assert payload["available_payloads"]["sequence:P69905"] == {
        "kind": "file_ref",
        "path": str(
            raw_root / "uniprot" / "20260323T100000Z" / "P69905" / "P69905.fasta"
        ).replace("\\", "/"),
    }


def test_build_available_payload_registry_rejects_empty_bindingdb_and_self_only_intact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    balanced_plan = {
        "selected_rows": [
            {
                "accession": "P69905",
                "canonical_id": "protein:P69905",
                "packet_expectation": {
                    "requested_modalities": ["ligand"],
                    "present_modalities": [],
                    "missing_modalities": ["ligand"],
                },
            },
            {
                "accession": "P04637",
                "canonical_id": "protein:P04637",
                "packet_expectation": {
                    "requested_modalities": ["ppi"],
                    "present_modalities": [],
                    "missing_modalities": ["ppi"],
                },
            },
        ]
    }
    canonical_latest = tmp_path / "data" / "canonical" / "LATEST.json"
    _write_json(canonical_latest, {"sequence_result": {"canonical_proteins": []}})
    raw_root = tmp_path / "data" / "raw"
    (raw_root / "bindingdb" / "20260323T100000Z" / "P69905").mkdir(parents=True, exist_ok=True)
    _write_json(
        raw_root / "bindingdb" / "20260323T100000Z" / "P69905" / "P69905.bindingdb.json",
        {
            "getLindsByUniprotResponse": {
                "bdb.hit": "0",
                "bdb.primary": "P69905",
                "bdb.affinities": [],
            }
        },
    )
    (raw_root / "intact" / "20260323T100000Z" / "P04637").mkdir(parents=True, exist_ok=True)
    (
        raw_root / "intact" / "20260323T100000Z" / "P04637" / "P04637.psicquic.tab25.txt"
    ).write_text(
        "uniprotkb:P04637\tuniprotkb:P04637\tintact:EBI-1\tintact:EBI-2\tpsi-mi:TP53\t"
        "psi-mi:TP53\tpsi-mi:\"MI:0018\"(two hybrid)\tAuthor et al.\tpubmed:1\t"
        "taxid:9606(Homo sapiens)\ttaxid:9606(Homo sapiens)\t"
        "psi-mi:\"MI:0915\"(physical association)\tpsi-mi:\"MI:0469\"(IntAct)\t"
        "intact:EBI-999|imex:IM-999\tintact-miscore:0.98\tspoke expansion\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "execution.materialization.available_payload_registry.ROOT",
        tmp_path,
    )

    registry = build_available_payload_registry(
        balanced_plan=balanced_plan,
        canonical_latest_path=canonical_latest,
        raw_root=raw_root,
    )

    payload = registry.to_dict()
    assert payload["available_payload_count"] == 0
    assert payload["missing_payload_count"] == 2
    assert sorted(payload["missing_payload_refs"]) == ["ligand:P69905", "ppi:P04637"]

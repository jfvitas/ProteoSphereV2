from __future__ import annotations

import gzip
import json
from pathlib import Path

from scripts.validate_protein_data_scope_seed import build_seed_validation


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_gzip_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(text)


def test_build_seed_validation_passes_for_complete_source(tmp_path: Path) -> None:
    prosite_dir = tmp_path / "seed" / "prosite"
    dat_path = prosite_dir / "prosite.dat"
    doc_path = prosite_dir / "prosite.doc"
    aux_path = prosite_dir / "prosite.aux"
    dat_path.parent.mkdir(parents=True, exist_ok=True)
    dat_path.write_text("ID   TEST\n", encoding="utf-8")
    doc_path.write_text("DOC TEST\n", encoding="utf-8")
    aux_path.write_text("AUX TEST\n", encoding="utf-8")

    manifest_path = tmp_path / "manifest.json"
    _write_json(
        manifest_path,
        {
            "sources": [
                {
                    "id": "prosite",
                    "items": [
                        {
                            "filename": "prosite.dat",
                            "status": "downloaded",
                            "path": str(dat_path),
                            "size_bytes": dat_path.stat().st_size,
                        },
                        {
                            "filename": "prosite.doc",
                            "status": "downloaded",
                            "path": str(doc_path),
                            "size_bytes": doc_path.stat().st_size,
                        },
                        {
                            "filename": "prosite.aux",
                            "status": "downloaded",
                            "path": str(aux_path),
                            "size_bytes": aux_path.stat().st_size,
                        },
                    ],
                }
            ]
        },
    )
    policy_path = tmp_path / "policy.json"
    _write_json(
        policy_path,
        {
            "sources": {
                "prosite": {
                    "required_core_files": ["prosite.dat", "prosite.doc", "prosite.aux"]
                }
            }
        },
    )

    payload = build_seed_validation(manifest_path=manifest_path, policy_path=policy_path)

    assert payload["status"] == "passed"
    assert payload["summary"]["passed_count"] == 1
    assert payload["sources"][0]["status"] == "passed"
    assert payload["sources"][0]["validated_artifacts"][0]["sha256"]


def test_build_seed_validation_detects_missing_source_and_gzip_failures(tmp_path: Path) -> None:
    sifts_dir = tmp_path / "seed" / "sifts"
    sifts_dir.mkdir(parents=True, exist_ok=True)
    bad_gzip = sifts_dir / "pdb_chain_uniprot.tsv.gz"
    bad_gzip.write_bytes(b"not-a-gzip")
    go_gzip = sifts_dir / "pdb_chain_go.tsv.gz"
    pfam_gzip = sifts_dir / "pdb_chain_pfam.tsv.gz"
    pdb_gzip = sifts_dir / "uniprot_pdb.tsv.gz"
    _write_gzip_text(go_gzip, "header\tvalue\n")
    _write_gzip_text(pfam_gzip, "header\tvalue\n")
    _write_gzip_text(pdb_gzip, "header\tvalue\n")

    manifest_path = tmp_path / "manifest.json"
    _write_json(
        manifest_path,
        {
            "sources": [
                {
                    "id": "sifts",
                    "items": [
                        {
                            "filename": "pdb_chain_uniprot.tsv.gz",
                            "status": "downloaded",
                            "path": str(bad_gzip),
                            "size_bytes": bad_gzip.stat().st_size,
                        },
                        {
                            "filename": "pdb_chain_go.tsv.gz",
                            "status": "downloaded",
                            "path": str(go_gzip),
                            "size_bytes": go_gzip.stat().st_size,
                        },
                        {
                            "filename": "pdb_chain_pfam.tsv.gz",
                            "status": "downloaded",
                            "path": str(pfam_gzip),
                            "size_bytes": pfam_gzip.stat().st_size,
                        },
                        {
                            "filename": "uniprot_pdb.tsv.gz",
                            "status": "downloaded",
                            "path": str(pdb_gzip),
                            "size_bytes": pdb_gzip.stat().st_size,
                        },
                    ],
                }
            ]
        },
    )
    policy_path = tmp_path / "policy.json"
    _write_json(
        policy_path,
        {
            "sources": {
                "sifts": {
                    "required_core_files": [
                        "pdb_chain_uniprot.tsv.gz",
                        "pdb_chain_go.tsv.gz",
                        "pdb_chain_pfam.tsv.gz",
                        "uniprot_pdb.tsv.gz",
                    ]
                },
                "uniprot": {
                    "required_core_files": [
                        "uniprot_sprot.dat.gz",
                        "uniprot_sprot.fasta.gz",
                        "idmapping.dat.gz",
                    ]
                },
            }
        },
    )

    payload = build_seed_validation(manifest_path=manifest_path, policy_path=policy_path)

    statuses = {item["source_id"]: item for item in payload["sources"]}
    assert payload["status"] == "failed"
    assert statuses["sifts"]["status"] == "failed"
    assert "gzip_validation_failed" in statuses["sifts"]["failures"]
    assert statuses["uniprot"]["status"] == "not_run"
    assert "source_not_present_in_manifest" in statuses["uniprot"]["failures"]


def test_build_seed_validation_aggregates_latest_source_entries(tmp_path: Path) -> None:
    seed_root = tmp_path / "seed"
    prosite_dir = seed_root / "prosite"
    pdb_dir = seed_root / "pdb_chemical_component_dictionary"
    prosite_dir.mkdir(parents=True, exist_ok=True)
    pdb_dir.mkdir(parents=True, exist_ok=True)

    prosite_dat = prosite_dir / "prosite.dat"
    prosite_doc = prosite_dir / "prosite.doc"
    prosite_aux = prosite_dir / "prosite.aux"
    prosite_dat.write_text("ID TEST\n", encoding="utf-8")
    prosite_doc.write_text("DOC TEST\n", encoding="utf-8")
    prosite_aux.write_text("AUX TEST\n", encoding="utf-8")

    components = pdb_dir / "components.cif.gz"
    aa_variants = pdb_dir / "aa-variants-v1.cif.gz"
    chem_comp_model = pdb_dir / "chem_comp_model.cif.gz"
    _write_gzip_text(components, "data_component\n")
    _write_gzip_text(aa_variants, "data_variant\n")
    _write_gzip_text(chem_comp_model, "data_model\n")

    _write_json(
        seed_root / "download_run_20260323_000001.json",
        {
            "sources": [
                {
                    "id": "prosite",
                    "items": [
                        {
                            "filename": "prosite.dat",
                            "status": "downloaded",
                            "path": str(prosite_dat),
                            "size_bytes": prosite_dat.stat().st_size,
                        },
                        {
                            "filename": "prosite.doc",
                            "status": "downloaded",
                            "path": str(prosite_doc),
                            "size_bytes": prosite_doc.stat().st_size,
                        },
                        {
                            "filename": "prosite.aux",
                            "status": "downloaded",
                            "path": str(prosite_aux),
                            "size_bytes": prosite_aux.stat().st_size,
                        },
                    ],
                }
            ]
        },
    )
    _write_json(
        seed_root / "download_run_20260323_000002.json",
        {
            "sources": [
                {
                    "id": "pdb_chemical_component_dictionary",
                    "items": [
                        {
                            "filename": "components.cif.gz",
                            "status": "downloaded",
                            "path": str(components),
                            "size_bytes": components.stat().st_size,
                        },
                        {
                            "filename": "aa-variants-v1.cif.gz",
                            "status": "downloaded",
                            "path": str(aa_variants),
                            "size_bytes": aa_variants.stat().st_size,
                        },
                        {
                            "filename": "chem_comp_model.cif.gz",
                            "status": "downloaded",
                            "path": str(chem_comp_model),
                            "size_bytes": chem_comp_model.stat().st_size,
                        },
                    ],
                }
            ]
        },
    )
    policy_path = tmp_path / "policy.json"
    _write_json(
        policy_path,
        {
            "sources": {
                "prosite": {
                    "required_core_files": ["prosite.dat", "prosite.doc", "prosite.aux"]
                },
                "pdb_chemical_component_dictionary": {
                    "required_core_files": [
                        "components.cif.gz",
                        "aa-variants-v1.cif.gz",
                        "chem_comp_model.cif.gz",
                    ]
                },
            }
        },
    )

    payload = build_seed_validation(
        seed_root=seed_root,
        manifest_path=Path("__aggregate__"),
        policy_path=policy_path,
    )

    assert payload["status"] == "passed"
    assert payload["summary"]["passed_count"] == 2


def test_build_seed_validation_detects_partial_download_residue(tmp_path: Path) -> None:
    source_dir = tmp_path / "seed" / "prosite"
    source_dir.mkdir(parents=True, exist_ok=True)
    dat_path = source_dir / "prosite.dat"
    doc_path = source_dir / "prosite.doc"
    aux_path = source_dir / "prosite.aux"
    residue_path = source_dir / "prosite_extra.dat.part"
    dat_path.write_text("ID   TEST\n", encoding="utf-8")
    doc_path.write_text("DOC TEST\n", encoding="utf-8")
    aux_path.write_text("AUX TEST\n", encoding="utf-8")
    residue_path.write_text("", encoding="utf-8")

    manifest_path = tmp_path / "manifest.json"
    _write_json(
        manifest_path,
        {
            "sources": [
                {
                    "id": "prosite",
                    "items": [
                        {
                            "filename": "prosite.dat",
                            "status": "downloaded",
                            "path": str(dat_path),
                            "size_bytes": dat_path.stat().st_size,
                        },
                        {
                            "filename": "prosite.doc",
                            "status": "downloaded",
                            "path": str(doc_path),
                            "size_bytes": doc_path.stat().st_size,
                        },
                        {
                            "filename": "prosite.aux",
                            "status": "downloaded",
                            "path": str(aux_path),
                            "size_bytes": aux_path.stat().st_size,
                        },
                    ],
                }
            ]
        },
    )
    policy_path = tmp_path / "policy.json"
    _write_json(
        policy_path,
        {
            "sources": {
                "prosite": {
                    "required_core_files": ["prosite.dat", "prosite.doc", "prosite.aux"]
                }
            }
        },
    )

    payload = build_seed_validation(manifest_path=manifest_path, policy_path=policy_path)

    assert payload["status"] == "failed"
    assert "partial_download_residue" in payload["sources"][0]["failures"]


def test_build_seed_validation_applies_reactome_schema_smoke(tmp_path: Path) -> None:
    reactome_dir = tmp_path / "seed" / "reactome"
    reactome_dir.mkdir(parents=True, exist_ok=True)
    u2r = reactome_dir / "UniProt2Reactome.txt"
    pathways = reactome_dir / "ReactomePathways.txt"
    relations = reactome_dir / "ReactomePathwaysRelation.txt"
    u2r.write_text(
        (
            "P12345\tR-HSA-199420\t"
            "https://reactome.org/PathwayBrowser/#/R-HSA-199420\t"
            "Pathway Name\tTAS\tHomo sapiens\n"
        ),
        encoding="utf-8",
    )
    pathways.write_text(
        "R-HSA-199420\tPathway Name\tHomo sapiens\n",
        encoding="utf-8",
    )
    relations.write_text(
        "R-HSA-199420\tR-HSA-199421\n",
        encoding="utf-8",
    )

    manifest_path = tmp_path / "manifest.json"
    _write_json(
        manifest_path,
        {
            "sources": [
                {
                    "id": "reactome",
                    "items": [
                        {
                            "filename": "UniProt2Reactome.txt",
                            "status": "downloaded",
                            "path": str(u2r),
                            "size_bytes": u2r.stat().st_size,
                        },
                        {
                            "filename": "ReactomePathways.txt",
                            "status": "downloaded",
                            "path": str(pathways),
                            "size_bytes": pathways.stat().st_size,
                        },
                        {
                            "filename": "ReactomePathwaysRelation.txt",
                            "status": "downloaded",
                            "path": str(relations),
                            "size_bytes": relations.stat().st_size,
                        },
                    ],
                }
            ]
        },
    )
    policy_path = tmp_path / "policy.json"
    _write_json(
        policy_path,
        {
            "sources": {
                "reactome": {
                    "required_core_files": [
                        "UniProt2Reactome.txt",
                        "ReactomePathways.txt",
                        "ReactomePathwaysRelation.txt",
                    ]
                }
            }
        },
    )

    payload = build_seed_validation(manifest_path=manifest_path, policy_path=policy_path)

    assert payload["status"] == "passed"
    assert payload["sources"][0]["status"] == "passed"
    assert len(payload["sources"][0]["validated_artifacts"]) == 3


def test_build_seed_validation_reactome_cross_file_mismatch_fails(tmp_path: Path) -> None:
    reactome_dir = tmp_path / "seed" / "reactome"
    reactome_dir.mkdir(parents=True, exist_ok=True)
    u2r = reactome_dir / "UniProt2Reactome.txt"
    pathways = reactome_dir / "ReactomePathways.txt"
    relations = reactome_dir / "ReactomePathwaysRelation.txt"
    u2r.write_text(
        (
            "P12345\tR-HSA-199420\t"
            "https://reactome.org/PathwayBrowser/#/R-HSA-199420\t"
            "Pathway Name\tTAS\tHomo sapiens\n"
        ),
        encoding="utf-8",
    )
    pathways.write_text(
        "R-HSA-199999\tOther Pathway\tHomo sapiens\n",
        encoding="utf-8",
    )
    relations.write_text(
        "R-HSA-199420\tR-HSA-199421\n",
        encoding="utf-8",
    )

    manifest_path = tmp_path / "manifest.json"
    _write_json(
        manifest_path,
        {
            "sources": [
                {
                    "id": "reactome",
                    "items": [
                        {
                            "filename": "UniProt2Reactome.txt",
                            "status": "downloaded",
                            "path": str(u2r),
                            "size_bytes": u2r.stat().st_size,
                        },
                        {
                            "filename": "ReactomePathways.txt",
                            "status": "downloaded",
                            "path": str(pathways),
                            "size_bytes": pathways.stat().st_size,
                        },
                        {
                            "filename": "ReactomePathwaysRelation.txt",
                            "status": "downloaded",
                            "path": str(relations),
                            "size_bytes": relations.stat().st_size,
                        },
                    ],
                }
            ]
        },
    )
    policy_path = tmp_path / "policy.json"
    _write_json(
        policy_path,
        {
            "sources": {
                "reactome": {
                    "required_core_files": [
                        "UniProt2Reactome.txt",
                        "ReactomePathways.txt",
                        "ReactomePathwaysRelation.txt",
                    ]
                }
            }
        },
    )

    payload = build_seed_validation(manifest_path=manifest_path, policy_path=policy_path)

    assert payload["status"] == "failed"
    assert payload["sources"][0]["status"] == "failed"
    assert "cross_file_integrity_failed" in payload["sources"][0]["failures"]


def test_build_seed_validation_applies_sifts_cross_file_integrity(tmp_path: Path) -> None:
    sifts_dir = tmp_path / "seed" / "sifts"
    sifts_dir.mkdir(parents=True, exist_ok=True)
    chain_gzip = sifts_dir / "pdb_chain_uniprot.tsv.gz"
    go_gzip = sifts_dir / "pdb_chain_go.tsv.gz"
    pfam_gzip = sifts_dir / "pdb_chain_pfam.tsv.gz"
    pdb_gzip = sifts_dir / "uniprot_pdb.tsv.gz"
    _write_gzip_text(
        chain_gzip,
        "PDB\tCHAIN\tSP_PRIMARY\n1ABC\tA\tP12345\n",
    )
    _write_gzip_text(
        go_gzip,
        "PDB\tCHAIN\tSP_PRIMARY\tGO_ID\n1ABC\tA\tP12345\tGO:0008150\n",
    )
    _write_gzip_text(
        pfam_gzip,
        "PDB\tCHAIN\tSP_PRIMARY\tPFAM_ID\n1ABC\tA\tP12345\tPF00001\n",
    )
    _write_gzip_text(
        pdb_gzip,
        "SP_PRIMARY\tPDB\nP12345\t1ABC;2XYZ\n",
    )

    manifest_path = tmp_path / "manifest.json"
    _write_json(
        manifest_path,
        {
            "sources": [
                {
                    "id": "sifts",
                    "items": [
                        {
                            "filename": "pdb_chain_uniprot.tsv.gz",
                            "status": "downloaded",
                            "path": str(chain_gzip),
                            "size_bytes": chain_gzip.stat().st_size,
                        },
                        {
                            "filename": "pdb_chain_go.tsv.gz",
                            "status": "downloaded",
                            "path": str(go_gzip),
                            "size_bytes": go_gzip.stat().st_size,
                        },
                        {
                            "filename": "pdb_chain_pfam.tsv.gz",
                            "status": "downloaded",
                            "path": str(pfam_gzip),
                            "size_bytes": pfam_gzip.stat().st_size,
                        },
                        {
                            "filename": "uniprot_pdb.tsv.gz",
                            "status": "downloaded",
                            "path": str(pdb_gzip),
                            "size_bytes": pdb_gzip.stat().st_size,
                        },
                    ],
                }
            ]
        },
    )
    policy_path = tmp_path / "policy.json"
    _write_json(
        policy_path,
        {
            "sources": {
                "sifts": {
                    "required_core_files": [
                        "pdb_chain_uniprot.tsv.gz",
                        "pdb_chain_go.tsv.gz",
                        "pdb_chain_pfam.tsv.gz",
                        "uniprot_pdb.tsv.gz",
                    ]
                }
            }
        },
    )

    payload = build_seed_validation(manifest_path=manifest_path, policy_path=policy_path)

    assert payload["status"] == "passed"
    assert payload["sources"][0]["status"] == "passed"


def test_build_seed_validation_applies_uniprot_cross_file_integrity(tmp_path: Path) -> None:
    uniprot_dir = tmp_path / "seed" / "uniprot"
    uniprot_dir.mkdir(parents=True, exist_ok=True)
    dat_gzip = uniprot_dir / "uniprot_sprot.dat.gz"
    fasta_gzip = uniprot_dir / "uniprot_sprot.fasta.gz"
    idmapping_gzip = uniprot_dir / "idmapping.dat.gz"
    _write_gzip_text(
        dat_gzip,
        (
            "ID   TEST_HUMAN              Reviewed;         100 AA.\n"
            "AC   P12345;\n"
            "SQ   SEQUENCE   100 AA;  11000 MW;  0000000000000000 CRC64;\n"
            "MSEQUENCE\n"
            "//\n"
        ),
    )
    _write_gzip_text(
        fasta_gzip,
        ">sp|P12345|TEST_HUMAN Test protein\nMSEQUENCE\n",
    )
    _write_gzip_text(
        idmapping_gzip,
        "P12345\tGene_Name\tTEST\n",
    )

    manifest_path = tmp_path / "manifest.json"
    _write_json(
        manifest_path,
        {
            "sources": [
                {
                    "id": "uniprot",
                    "items": [
                        {
                            "filename": "uniprot_sprot.dat.gz",
                            "status": "downloaded",
                            "path": str(dat_gzip),
                            "size_bytes": dat_gzip.stat().st_size,
                        },
                        {
                            "filename": "uniprot_sprot.fasta.gz",
                            "status": "downloaded",
                            "path": str(fasta_gzip),
                            "size_bytes": fasta_gzip.stat().st_size,
                        },
                        {
                            "filename": "idmapping.dat.gz",
                            "status": "downloaded",
                            "path": str(idmapping_gzip),
                            "size_bytes": idmapping_gzip.stat().st_size,
                        },
                    ],
                }
            ]
        },
    )
    policy_path = tmp_path / "policy.json"
    _write_json(
        policy_path,
        {
            "sources": {
                "uniprot": {
                    "required_core_files": [
                        "uniprot_sprot.dat.gz",
                        "uniprot_sprot.fasta.gz",
                        "idmapping.dat.gz",
                    ]
                }
            }
        },
    )

    payload = build_seed_validation(manifest_path=manifest_path, policy_path=policy_path)

    assert payload["status"] == "passed"
    assert payload["sources"][0]["status"] == "passed"

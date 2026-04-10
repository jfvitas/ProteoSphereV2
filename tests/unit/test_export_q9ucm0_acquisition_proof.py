from __future__ import annotations

import json
from pathlib import Path

from execution.acquire.bio_agent_lab_imports import (
    BioAgentLabImportManifest,
    BioAgentLabImportSource,
)
from scripts.export_q9ucm0_acquisition_proof import (
    build_q9ucm0_acquisition_proof,
    render_markdown,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _source(
    *,
    source_name: str,
    category: str,
    status: str,
    candidate_roots: tuple[str, ...],
    present_roots: tuple[str, ...],
    missing_roots: tuple[str, ...],
    join_keys: tuple[str, ...],
) -> BioAgentLabImportSource:
    return BioAgentLabImportSource(
        source_name=source_name,
        category=category,
        status=status,  # type: ignore[arg-type]
        candidate_roots=candidate_roots,
        present_roots=present_roots,
        missing_roots=missing_roots,
        join_keys=join_keys,
        load_hints=("index",),
        provenance={
            "registry_id": "temp-registry",
            "storage_root": r"C:\Users\jfvit\Documents\bio-agent-lab",
            "source_name": source_name,
            "category": category,
            "status": status,
            "candidate_root_count": len(candidate_roots),
            "present_root_count": len(present_roots),
            "missing_root_count": len(missing_roots),
            "load_hints": ["index"],
            "notes": [],
        },
        notes=(),
    )


def _local_manifest() -> BioAgentLabImportManifest:
    return BioAgentLabImportManifest(
        manifest_id="temp-manifest",
        storage_root=r"C:\Users\jfvit\Documents\bio-agent-lab",
        registry_id="temp-registry",
        sources=(
            _source(
                source_name="uniprot",
                category="sequence",
                status="partial",
                candidate_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\uniprot\uniprot_sprot.dat.gz",
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\uniprot\uniprot_trembl_latest.gz",
                ),
                present_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\uniprot\uniprot_sprot.dat.gz",
                ),
                missing_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\uniprot\uniprot_trembl_latest.gz",
                ),
                join_keys=("P69905", "P68871", "P09105", "Q9UCM0"),
            ),
            _source(
                source_name="alphafold_db",
                category="structure",
                status="present",
                candidate_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\alphafold\swissprot_pdb_v6.tar",
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\alphafold",
                ),
                present_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\alphafold\swissprot_pdb_v6.tar",
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\alphafold",
                ),
                missing_roots=(),
                join_keys=("P69905", "P68871"),
            ),
            _source(
                source_name="raw_rcsb",
                category="structure",
                status="present",
                candidate_roots=(r"C:\Users\jfvit\Documents\bio-agent-lab\data\raw\rcsb",),
                present_roots=(r"C:\Users\jfvit\Documents\bio-agent-lab\data\raw\rcsb",),
                missing_roots=(),
                join_keys=("10JU", "4HHB", "9LWP"),
            ),
            _source(
                source_name="structures_rcsb",
                category="structure",
                status="present",
                candidate_roots=(r"C:\Users\jfvit\Documents\bio-agent-lab\data\structures\rcsb",),
                present_roots=(r"C:\Users\jfvit\Documents\bio-agent-lab\data\structures\rcsb",),
                missing_roots=(),
                join_keys=("10JU", "4HHB", "9LWP"),
            ),
            _source(
                source_name="bindingdb",
                category="protein_ligand",
                status="present",
                candidate_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\bindingdb\BDB-mySQL_All_202603_dmp.zip",
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data\raw\bindingdb",
                ),
                present_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\bindingdb\BDB-mySQL_All_202603_dmp.zip",
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data\raw\bindingdb",
                ),
                missing_roots=(),
                join_keys=("1BB0", "5Q16", "5TQF"),
            ),
            _source(
                source_name="chembl",
                category="protein_ligand",
                status="present",
                candidate_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db",
                ),
                present_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\chembl\chembl_36_sqlite\chembl_36\chembl_36_sqlite\chembl_36.db",
                ),
                missing_roots=(),
                join_keys=("5JJM", "P31749"),
            ),
            _source(
                source_name="biolip",
                category="protein_ligand",
                status="present",
                candidate_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biolip\BioLiP.txt",
                ),
                present_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biolip\BioLiP.txt",
                ),
                missing_roots=(),
                join_keys=("4HHB", "9S6C"),
            ),
            _source(
                source_name="extracted_assays",
                category="protein_ligand",
                status="missing",
                candidate_roots=(r"C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\assays",),
                present_roots=(),
                missing_roots=(r"C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\assays",),
                join_keys=("10JU", "1A00"),
            ),
            _source(
                source_name="extracted_bound_objects",
                category="protein_ligand",
                status="missing",
                candidate_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\bound_objects",
                ),
                present_roots=(),
                missing_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\bound_objects",
                ),
                join_keys=("10JU", "1A00"),
            ),
            _source(
                source_name="intact",
                category="interaction_network",
                status="missing",
                candidate_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\intact\intact_latest.mitab_latest",
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\intact\README_latest",
                ),
                present_roots=(),
                missing_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\intact\intact_latest.mitab_latest",
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\intact\README_latest",
                ),
                join_keys=("P69905", "P09105"),
            ),
            _source(
                source_name="biogrid",
                category="interaction_network",
                status="missing",
                candidate_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biogrid\BIOGRID-ALL-_latest.tab3.txt_latest",
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biogrid\BIOGRID-_latest.zip",
                ),
                present_roots=(),
                missing_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biogrid\BIOGRID-ALL-_latest.tab3.txt_latest",
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\biogrid\BIOGRID-_latest.zip",
                ),
                join_keys=("P69905", "P09105"),
            ),
            _source(
                source_name="string",
                category="interaction_network",
                status="missing",
                candidate_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\string\protein.links_latest.txt_latest",
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\string\protein.info_latest.txt_latest",
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\string\protein.aliases_latest.txt_latest",
                ),
                present_roots=(),
                missing_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\string\protein.links_latest.txt_latest",
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\string\protein.info_latest.txt_latest",
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\string\protein.aliases_latest.txt_latest",
                ),
                join_keys=("P69905", "P09105"),
            ),
            _source(
                source_name="pdbbind_pp",
                category="protein_protein",
                status="present",
                candidate_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\pdbbind\P-P.tar.gz",
                ),
                present_roots=(
                    r"C:\Users\jfvit\Documents\bio-agent-lab\data_sources\pdbbind\P-P.tar.gz",
                ),
                missing_roots=(),
                join_keys=("9LWP", "9QTN", "9SYV"),
            ),
            _source(
                source_name="extracted_interfaces",
                category="protein_protein",
                status="present",
                candidate_roots=(r"C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\interfaces",),
                present_roots=(r"C:\Users\jfvit\Documents\bio-agent-lab\data\extracted\interfaces",),
                missing_roots=(),
                join_keys=("10JU", "4HHB"),
            ),
        ),
    )


def _prepare_temp_inputs(tmp_path: Path) -> tuple[Path, Path]:
    raw_root = tmp_path / "data" / "raw"
    local_registry_runs_root = raw_root / "local_registry_runs"
    local_registry_root = raw_root / "local_registry" / "20260323T003221Z"

    _write_json(local_registry_runs_root / "LATEST.json", {"stamp": "20260323T003221Z"})
    _write_json(
        local_registry_root / "import_manifest.json",
        {
            "imported_sources": [
                {"source_name": "uniprot", "join_keys": ["Q9UCM0"]},
                {"source_name": "bindingdb", "join_keys": ["1BB0"]},
                {"source_name": "intact", "join_keys": ["P69905"]},
            ]
        },
    )
    _write_json(
        raw_root / "rcsb_pdbe" / "20260323T182231Z" / "Q9UCM0" / "Q9UCM0.best_structures.json",
        [],
    )
    _write_json(
        raw_root / "bindingdb" / "20260323T182231Z" / "Q9UCM0" / "Q9UCM0.bindingdb.json",
        {
            "getLindsByUniprotResponse": {
                "bdb.hit": "0",
                "bdb.primary": "Q9UCM0",
                "bdb.alternative": ["P69905", "Q9UCM0"],
                "bdb.affinities": [],
            }
        },
    )
    _write_json(
        raw_root / "intact" / "20260323T182231Z" / "Q9UCM0" / "Q9UCM0.interactor.json",
        {
            "content": [
                {
                    "interactorPreferredIdentifier": "P69905",
                    "interactorDescription": "Hemoglobin subunit alpha",
                    "interactorAlias": ["Q9UCM0"],
                    "interactionCount": 213,
                }
            ]
        },
    )
    _write_text(
        raw_root / "intact" / "20260323T182231Z" / "Q9UCM0" / "Q9UCM0.psicquic.tab25.txt",
        "\n".join(
            [
                "uniprotkb:P10636-8\tuniprotkb:P69905\tintact:EBI-366233\tintact:EBI-714680",
                (
                    "uniprotkb:P10636-8\tuniprotkb:P69905\t"
                    "intact:EBI-111111|uniprotkb:Q9UCM0\tintact:EBI-222222"
                ),
            ]
        ),
    )
    return raw_root, local_registry_runs_root


def test_build_q9ucm0_acquisition_proof_surfaces_real_absence(tmp_path: Path) -> None:
    raw_root, local_registry_runs_root = _prepare_temp_inputs(tmp_path)
    payload = build_q9ucm0_acquisition_proof(
        raw_root=raw_root,
        local_registry_runs_root=local_registry_runs_root,
        local_source_manifest=_local_manifest(),
    )

    assert payload["status"] == "unresolved_requires_new_acquisition"
    assert payload["current_truth"] == {
        "structure": "missing",
        "ligand": "missing",
        "ppi": "missing",
    }
    assert payload["proof_summary"]["q9ucm0_join_key_sources"] == ["uniprot"]
    assert payload["modalities"]["structure"]["raw_snapshot"]["record_count"] == 0
    assert payload["modalities"]["ligand"]["raw_snapshot"]["hit_count"] == 0
    assert payload["modalities"]["ppi"]["raw_snapshot"]["state"] == "alias_only"
    assert payload["modalities"]["ppi"]["raw_snapshot"]["preferred_identifiers"] == [
        "P69905"
    ]
    assert payload["modalities"]["structure"]["checked_sources"]["alphafold_db"][
        "contains_accession"
    ] is False
    assert payload["modalities"]["ppi"]["checked_sources"]["intact"]["status"] == "missing"
    assert payload["modalities"]["ppi"]["raw_snapshot"]["state"] == "alias_only"
    assert payload["next_acquisition_actions"][0] == "AlphaFold DB explicit accession probe"


def test_render_markdown_highlights_absence_and_next_action(tmp_path: Path) -> None:
    raw_root, local_registry_runs_root = _prepare_temp_inputs(tmp_path)
    payload = build_q9ucm0_acquisition_proof(
        raw_root=raw_root,
        local_registry_runs_root=local_registry_runs_root,
        local_source_manifest=_local_manifest(),
    )

    markdown = render_markdown(payload)

    assert "# Q9UCM0 Acquisition Proof" in markdown
    assert "`structure=missing`" in markdown
    assert "AlphaFold DB explicit accession probe" in markdown
    assert "`ppi:Q9UCM0`" in markdown

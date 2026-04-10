from __future__ import annotations

from execution.materialization.local_bridge_ligand_backfill import (
    build_bridge_ligand_backfill_entry,
    materialize_selected_cohort_bridge_ligand_entries,
    select_primary_small_molecule_candidate,
)


def test_select_primary_small_molecule_candidate_prefers_bridge_chain_overlap() -> None:
    candidate, issues = select_primary_small_molecule_candidate(
        (
            {
                "pdb_id": "1ABC",
                "component_id": "HEM",
                "component_type": "cofactor",
                "component_role": "catalytic_cofactor",
                "chain_ids": ["A"],
            },
            {
                "pdb_id": "1ABC",
                "component_id": "CMO",
                "component_type": "small_molecule",
                "component_role": "primary_binder",
                "chain_ids": ["B"],
            },
            {
                "pdb_id": "1ABC",
                "component_id": "SO4",
                "component_type": "small_molecule",
                "component_role": "buffer_artifact",
                "chain_ids": ["B"],
            },
        ),
        bridge_chain_ids=("B",),
    )

    assert issues == ()
    assert candidate is not None
    assert candidate.component_id == "CMO"


def test_build_bridge_ligand_backfill_entry_resolves_primary_small_molecule() -> None:
    entry = build_bridge_ligand_backfill_entry(
        {
            "accession": "P02100",
            "canonical_id": "protein:P02100",
            "split": "val",
            "bridge": {
                "state": "positive_hit",
                "bridge_kind": "bridge_only",
                "pdb_id": "1A9W",
                "chain_ids": ["A", "C"],
            },
        },
        bound_object_rows=(
            {
                "pdb_id": "1A9W",
                "component_id": "HEM",
                "component_type": "cofactor",
                "component_role": "catalytic_cofactor",
                "chain_ids": ["A", "C"],
            },
            {
                "pdb_id": "1A9W",
                "component_id": "CMO",
                "component_type": "small_molecule",
                "component_role": "primary_binder",
                "component_smiles": "[C-]#[O+]",
                "component_inchikey": "UGFAIRIUMAVXCW-UHFFFAOYSA-N",
                "chain_ids": ["A", "C"],
            },
        ),
    )

    assert entry.status == "resolved"
    assert entry.selected_ligand is not None
    assert entry.selected_ligand.component_id == "CMO"
    assert entry.bridge_record is not None
    assert entry.bridge_record.status == "resolved"
    assert entry.bridge_record.ligands[0].canonical_id == "ligand:CMO"
    assert entry.bridge_record.protein_canonical_ids == ("protein:P02100",)


def test_build_bridge_ligand_backfill_entry_resolves_ready_now_bridge_state() -> None:
    entry = build_bridge_ligand_backfill_entry(
        {
            "accession": "Q9NZD4",
            "canonical_id": "protein:Q9NZD4",
            "split": None,
            "bridge": {
                "state": "ready_now",
                "bridge_kind": "bridge_only",
                "pdb_id": "1Y01",
                "chain_ids": [],
            },
        },
        bound_object_rows=(
            {
                "pdb_id": "1Y01",
                "component_id": "HEM",
                "component_type": "cofactor",
                "component_role": "catalytic_cofactor",
                "chain_ids": ["B"],
            },
            {
                "pdb_id": "1Y01",
                "component_id": "CHK",
                "component_type": "small_molecule",
                "component_role": "primary_binder",
                "component_smiles": "CCO",
                "component_inchikey": "TEST-INCHI",
                "chain_ids": ["B"],
            },
        ),
    )

    assert entry.status == "resolved"
    assert entry.bridge_state == "ready_now"
    assert entry.selected_ligand is not None
    assert entry.selected_ligand.component_id == "CHK"
    assert entry.bridge_record is not None
    assert entry.bridge_record.status == "resolved"
    assert entry.bridge_record.source_record_id == "Q9NZD4:1Y01:CHK"


def test_build_bridge_ligand_backfill_entry_keeps_ambiguous_candidates_unresolved() -> None:
    entry = build_bridge_ligand_backfill_entry(
        {
            "accession": "P02042",
            "canonical_id": "protein:P02042",
            "split": "train",
            "bridge": {
                "state": "positive_hit",
                "bridge_kind": "bridge_only",
                "pdb_id": "1SHR",
                "chain_ids": ["A", "B"],
            },
        },
        bound_object_rows=(
            {
                "pdb_id": "1SHR",
                "component_id": "CYN",
                "component_type": "small_molecule",
                "component_role": "primary_binder",
                "chain_ids": ["A"],
            },
            {
                "pdb_id": "1SHR",
                "component_id": "CMO",
                "component_type": "small_molecule",
                "component_role": "primary_binder",
                "chain_ids": ["B"],
            },
        ),
    )

    assert entry.status == "unresolved"
    assert entry.selected_ligand is None
    assert "ambiguous_primary_small_molecule_candidates" in entry.issues


def test_materialize_selected_cohort_bridge_ligand_entries_falls_back_to_master_repository(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "execution.materialization.local_bridge_ligand_backfill.DEFAULT_LOCAL_SOURCE_ROOT",
        tmp_path,
    )
    bound_object_root = tmp_path / "data" / "extracted" / "bound_objects"
    bound_object_root.mkdir(parents=True)
    (bound_object_root / "1A9W.json").write_text(
        """[
  {
    "pdb_id": "1A9W",
    "component_id": "HEM",
    "component_type": "cofactor",
    "component_role": "catalytic_cofactor",
    "chain_ids": ["A", "C", "E", "F"]
  },
  {
    "pdb_id": "1A9W",
    "component_id": "CMO",
    "component_type": "small_molecule",
    "component_role": "primary_binder",
    "component_smiles": "[C-]#[O+]",
    "component_inchikey": "UGFAIRIUMAVXCW-UHFFFAOYSA-N",
    "chain_ids": ["A", "C", "E", "F"]
  }
]""",
        encoding="utf-8",
    )
    (bound_object_root / "4MQJ.json").write_text(
        """[
  {
    "pdb_id": "4MQJ",
    "component_id": "HEM",
    "component_type": "cofactor",
    "component_role": "catalytic_cofactor",
    "chain_ids": ["A", "B", "C", "D", "E", "F", "G", "H"]
  },
  {
    "pdb_id": "4MQJ",
    "component_id": "CMO",
    "component_type": "small_molecule",
    "component_role": "primary_binder",
    "component_smiles": "[C-]#[O+]",
    "component_inchikey": "UGFAIRIUMAVXCW-UHFFFAOYSA-N",
    "chain_ids": ["A", "C", "E", "G"]
  }
]""",
        encoding="utf-8",
    )
    raw_root = tmp_path / "data" / "raw" / "rcsb"
    raw_root.mkdir(parents=True)
    (raw_root / "1A9W.json").write_text(
        """{
  "polymer_entities": [
    {
      "rcsb_polymer_entity_container_identifiers": {
        "auth_asym_ids": ["A", "C"],
        "uniprot_ids": ["P69905"]
      }
    },
    {
      "rcsb_polymer_entity_container_identifiers": {
        "auth_asym_ids": ["E", "F"],
        "uniprot_ids": ["P02100"]
      }
    }
  ]
}""",
        encoding="utf-8",
    )
    (raw_root / "4MQJ.json").write_text(
        """{
  "polymer_entities": [
    {
      "rcsb_polymer_entity_container_identifiers": {
        "auth_asym_ids": ["A", "C"],
        "uniprot_ids": ["P69905"]
      }
    },
    {
      "rcsb_polymer_entity_container_identifiers": {
        "auth_asym_ids": ["G", "H"],
        "uniprot_ids": ["P69892"]
      }
    }
  ]
}""",
        encoding="utf-8",
    )
    master_repository = tmp_path / "master_pdb_repository.csv"
    master_repository.write_text(
        "\n".join(
            [
                (
                    "pdb_id,protein_chain_uniprot_ids,ligand_types,"
                    "ligand_component_ids,has_ligand_signal,quality_score,raw_file_path"
                ),
                "1BAB,P69905,cofactor,HEM,true,0.80,data/raw/rcsb/1BAB.json",
                (
                    "1A9W,P69905; P02100,cofactor; small_molecule,"
                    "HEM; CMO,true,0.95,data/raw/rcsb/1A9W.json"
                ),
                "7QU4,P69892,cofactor,HEM,true,0.85,data/raw/rcsb/7QU4.json",
                (
                    "4MQJ,P69905; P69892,cofactor; small_molecule,"
                    "HEM; CMO,true,0.97,data/raw/rcsb/4MQJ.json"
                ),
            ]
        ),
        encoding="utf-8",
    )

    entries = materialize_selected_cohort_bridge_ligand_entries(
        (
            {
                "accession": "P69905",
                "canonical_id": "protein:P69905",
                "split": "train",
                "bridge": {
                    "state": "positive_hit",
                    "bridge_kind": "bridge_only",
                    "pdb_id": "1BAB",
                    "chain_ids": ["A", "C", "B", "D"],
                },
            },
            {
                "accession": "P69892",
                "canonical_id": "protein:P69892",
                "split": "val",
                "bridge": {
                    "state": "positive_hit",
                    "bridge_kind": "bridge_only",
                    "pdb_id": "7QU4",
                    "chain_ids": ["G", "H", "A", "B"],
                },
            },
        ),
        bound_object_root=bound_object_root,
    )

    assert len(entries) == 2
    p69905 = next(entry for entry in entries if entry.accession == "P69905")
    p69892 = next(entry for entry in entries if entry.accession == "P69892")

    assert p69905.status == "resolved"
    assert p69905.pdb_id == "1A9W"
    assert p69905.selected_ligand is not None
    assert p69905.selected_ligand.component_id == "CMO"
    assert "fallback_bridge_candidate_from_master_repository" in p69905.notes

    assert p69892.status == "resolved"
    assert p69892.pdb_id == "4MQJ"
    assert p69892.selected_ligand is not None
    assert p69892.selected_ligand.component_id == "CMO"
    assert "fallback_bridge_candidate_from_master_repository" in p69892.notes


def test_materialize_selected_cohort_bridge_ligand_entries_keeps_partner_only_fallback_unresolved(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "execution.materialization.local_bridge_ligand_backfill.DEFAULT_LOCAL_SOURCE_ROOT",
        tmp_path,
    )
    bound_object_root = tmp_path / "data" / "extracted" / "bound_objects"
    bound_object_root.mkdir(parents=True)
    (bound_object_root / "1Z8U.json").write_text(
        """[
  {
    "pdb_id": "1Z8U",
    "component_id": "HEM",
    "component_type": "cofactor",
    "component_role": "catalytic_cofactor",
    "chain_ids": ["B", "D"]
  }
]""",
        encoding="utf-8",
    )
    (bound_object_root / "1Y01.json").write_text(
        """[
  {
    "pdb_id": "1Y01",
    "component_id": "HEM",
    "component_type": "cofactor",
    "component_role": "catalytic_cofactor",
    "chain_ids": ["B"]
  },
  {
    "pdb_id": "1Y01",
    "component_id": "CHK",
    "component_type": "small_molecule",
    "component_role": "primary_binder",
    "chain_ids": ["B"]
  }
]""",
        encoding="utf-8",
    )
    raw_root = tmp_path / "data" / "raw" / "rcsb"
    raw_root.mkdir(parents=True)
    (raw_root / "1Y01.json").write_text(
        """{
  "polymer_entities": [
    {
      "rcsb_polymer_entity_container_identifiers": {
        "auth_asym_ids": ["A"],
        "uniprot_ids": ["Q9NZD4"]
      }
    },
    {
      "rcsb_polymer_entity_container_identifiers": {
        "auth_asym_ids": ["B"],
        "uniprot_ids": ["P69905"]
      }
    }
  ]
}""",
        encoding="utf-8",
    )
    master_repository = tmp_path / "master_pdb_repository.csv"
    master_repository.write_text(
        "\n".join(
            [
                (
                    "pdb_id,protein_chain_uniprot_ids,ligand_types,"
                    "ligand_component_ids,has_ligand_signal,quality_score,raw_file_path"
                ),
                (
                    "1Y01,P69905; Q9NZD4,cofactor; small_molecule,"
                    "HEM; CHK,true,0.95,data/raw/rcsb/1Y01.json"
                ),
            ]
        ),
        encoding="utf-8",
    )

    entries = materialize_selected_cohort_bridge_ligand_entries(
        (
            {
                "accession": "Q9NZD4",
                "canonical_id": "protein:Q9NZD4",
                "split": "train",
                "bridge": {
                    "state": "positive_hit",
                    "bridge_kind": "bridge_only",
                    "pdb_id": "1Z8U",
                    "chain_ids": ["A", "C"],
                },
            },
        ),
        bound_object_root=bound_object_root,
        master_repository_path=master_repository,
    )

    assert len(entries) == 1
    entry = entries[0]
    assert entry.accession == "Q9NZD4"
    assert entry.status == "unresolved"
    assert entry.pdb_id == "1Z8U"
    assert entry.selected_ligand is None
    assert "no_primary_small_molecule_bound_object" in entry.issues

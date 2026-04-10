from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[3] / "datasets" / "splits" / "locked_split.py"
_SPEC = spec_from_file_location("locked_split_under_test", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

LockedSplitRecord = _MODULE.LockedSplitRecord
assign_locked_splits = _MODULE.assign_locked_splits


def test_assign_locked_splits_hits_target_ratios_and_is_seed_deterministic() -> None:
    records = [
        LockedSplitRecord(
            record_id=f"R{i:02d}",
            protein_cluster_id=f"PC{i:02d}",
            ligand_scaffold_id=f"SC{i:02d}",
        )
        for i in range(20)
    ]

    first = assign_locked_splits(records, seed=17)
    second = assign_locked_splits(records, seed=17)
    third = assign_locked_splits(records, seed=3)

    assert first.unresolved == ()
    assert first.target_counts == {"train": 14, "val": 3, "test": 3}
    assert first.split_counts == {"train": 14, "val": 3, "test": 3}
    assert [(item.record_id, item.split) for item in first.assignments] == [
        (item.record_id, item.split) for item in second.assignments
    ]
    assert [(item.record_id, item.split) for item in first.assignments] != [
        (item.record_id, item.split) for item in third.assignments
    ]


def test_assign_locked_splits_keeps_leakage_domains_together_and_reports_unresolved() -> None:
    records = [
        LockedSplitRecord(record_id="A1", protein_cluster_id="PC1", ligand_scaffold_id="SC1"),
        LockedSplitRecord(record_id="A2", protein_cluster_id="PC1", ligand_scaffold_id="SC2"),
        LockedSplitRecord(record_id="A3", protein_cluster_id="PC2", ligand_scaffold_id="SC2"),
        LockedSplitRecord(record_id="B1", protein_cluster_id="PC3", ligand_scaffold_id="SC3"),
        LockedSplitRecord(record_id="B2", protein_cluster_id="PC4", ligand_scaffold_id="SC4"),
        LockedSplitRecord(record_id="U1", protein_cluster_id="PC5", ligand_smiles="CCO"),
    ]

    result = assign_locked_splits(records, seed=11)

    assert any(item.record_id == "U1" for item in result.unresolved)
    assert result.unresolved[0].reasons == ("missing_ligand_scaffold",)

    split_by_record = {item.record_id: item.split for item in result.assignments}
    assert len({split_by_record["A1"], split_by_record["A2"], split_by_record["A3"]}) == 1

    protein_clusters_by_split: dict[str, set[str]] = {"train": set(), "val": set(), "test": set()}
    scaffolds_by_split: dict[str, set[str]] = {"train": set(), "val": set(), "test": set()}
    for item in result.assignments:
        protein_clusters_by_split[item.split].add(item.protein_cluster_id)
        scaffolds_by_split[item.split].add(item.ligand_scaffold_id)

    assert protein_clusters_by_split["train"].isdisjoint(protein_clusters_by_split["val"])
    assert protein_clusters_by_split["train"].isdisjoint(protein_clusters_by_split["test"])
    assert protein_clusters_by_split["val"].isdisjoint(protein_clusters_by_split["test"])
    assert scaffolds_by_split["train"].isdisjoint(scaffolds_by_split["val"])
    assert scaffolds_by_split["train"].isdisjoint(scaffolds_by_split["test"])
    assert scaffolds_by_split["val"].isdisjoint(scaffolds_by_split["test"])

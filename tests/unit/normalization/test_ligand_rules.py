from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from core.canonical.ligand import CanonicalLigand

MODULE_PATH = (
    Path(__file__).resolve().parents[3] / "normalization" / "conflicts" / "ligand_rules.py"
)
SPEC = importlib.util.spec_from_file_location("ligand_rules", MODULE_PATH)
assert SPEC and SPEC.loader
ligand_rules = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ligand_rules
SPEC.loader.exec_module(ligand_rules)

resolve_ligand_conflicts = ligand_rules.resolve_ligand_conflicts


def test_resolve_ligand_conflicts_merges_clean_duplicate_observations() -> None:
    result = resolve_ligand_conflicts(
        [
            make_ligand(
                "lig-001",
                "ATP",
                "BindingDB",
                "5001",
                smiles="CCO",
                provenance=("bindingdb:5001",),
                synonyms=("adenosine triphosphate",),
            ),
            make_ligand(
                "lig-001",
                "ATP",
                "BindingDB",
                "5001",
                smiles="CCO",
                provenance=("pubchem:1234",),
                synonyms=("triphosphate",),
            ),
        ]
    )

    assert result.status == "resolved"
    assert result.reason == "compatible_merge"
    assert result.resolved_ligand is not None
    assert result.resolved_ligand.ligand_id == "lig-001"
    assert result.resolved_ligand.source == "CANONICAL"
    assert result.resolved_ligand.source_id == "merge:lig-001"
    assert result.resolved_ligand.synonyms == (
        "ATP",
        "adenosine triphosphate",
        "triphosphate",
    )
    assert result.resolved_ligand.provenance == ("bindingdb:5001", "pubchem:1234")
    assert result.issues == ()


def test_resolve_ligand_conflicts_flags_identifier_collisions() -> None:
    result = resolve_ligand_conflicts(
        [
            make_ligand("lig-002", "NAD+", "PubChem", "2001", smiles="C1=NC=NC2=O"),
            make_ligand("lig-002", "NAD+", "PubChem", "2001", smiles="C1=NC=NC2=N"),
        ]
    )

    assert result.status == "unresolved"
    assert result.reason == "identifier_collision"
    assert result.resolved_ligand is None
    assert result.issues[0].kind == "identifier_collision"
    assert result.issues[0].fields == ("smiles",)
    assert result.preserved_ligands[0].ligand_id == "lig-002"
    assert result.preserved_ligands[1].ligand_id == "lig-002"


def test_resolve_ligand_conflicts_marks_synonym_only_matches_as_ambiguous() -> None:
    result = resolve_ligand_conflicts(
        [
            make_ligand("lig-003", "ATP", "RCSB", "3001"),
            make_ligand("lig-004", "ATP", "BindingDB", "3002"),
        ]
    )

    assert result.status == "ambiguous"
    assert result.reason == "synonym_only_ambiguity"
    assert result.resolved_ligand is None
    assert result.issues[0].kind == "synonym_only_ambiguity"
    assert result.issues[0].identifiers == ("atp",)
    assert result.preserved_ligands[0].ligand_id == "lig-003"
    assert result.preserved_ligands[1].ligand_id == "lig-004"


def test_resolve_ligand_conflicts_preserves_unresolved_conflict_records() -> None:
    first = make_ligand(
        "lig-005",
        "Ligand X",
        "ChEMBL",
        "4001",
        smiles="CCN",
        provenance=("chembl:4001",),
    )
    second = make_ligand(
        "lig-006",
        "Ligand X",
        "ChEMBL",
        "4001",
        smiles="CCO",
        provenance=("chembl:4001-revised",),
    )

    result = resolve_ligand_conflicts([first, second])

    assert result.status == "unresolved"
    assert result.reason == "identifier_collision"
    assert result.resolved_ligand is None
    assert result.preserved_ligands == (first, second)
    assert result.issues[0].kind == "identifier_collision"
    assert result.issues[0].records == ("chembl:4001", "chembl:4001")


def make_ligand(
    ligand_id: str,
    name: str,
    source: str,
    source_id: str,
    *,
    smiles: str | None = None,
    inchi: str | None = None,
    inchikey: str | None = None,
    formula: str | None = None,
    charge: int | None = None,
    synonyms: tuple[str, ...] = (),
    provenance: tuple[str, ...] = (),
) -> CanonicalLigand:
    return CanonicalLigand(
        ligand_id=ligand_id,
        name=name,
        source=source,
        source_id=source_id,
        smiles=smiles,
        inchi=inchi,
        inchikey=inchikey,
        formula=formula,
        charge=charge,
        synonyms=synonyms,
        provenance=provenance,
    )

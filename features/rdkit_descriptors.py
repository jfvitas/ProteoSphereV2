from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any


class RdkitUnavailableError(RuntimeError):
    """Raised when RDKit-backed descriptor extraction is requested but unavailable."""


@dataclass(frozen=True, slots=True)
class LigandDescriptorResult:
    smiles: str
    canonical_smiles: str
    descriptors: dict[str, float | int]
    source: str = "rdkit"
    provenance: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "smiles": self.smiles,
            "canonical_smiles": self.canonical_smiles,
            "descriptors": dict(self.descriptors),
            "source": self.source,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class _RDKitModules:
    Chem: Any
    Descriptors: Any
    Lipinski: Any
    rdMolDescriptors: Any
    Crippen: Any


_RDKit_CACHE: _RDKitModules | None = None
_RDKit_IMPORT_FAILED = False


def _load_rdkit_modules() -> _RDKitModules | None:
    global _RDKit_CACHE, _RDKit_IMPORT_FAILED
    if _RDKit_CACHE is not None:
        return _RDKit_CACHE
    if _RDKit_IMPORT_FAILED:
        return None
    try:
        chem = import_module("rdkit.Chem")
        descriptors = import_module("rdkit.Chem.Descriptors")
        lipinski = import_module("rdkit.Chem.Lipinski")
        rd_mol_descriptors = import_module("rdkit.Chem.rdMolDescriptors")
        crippen = import_module("rdkit.Chem.Crippen")
    except ModuleNotFoundError:
        _RDKit_IMPORT_FAILED = True
        return None
    _RDKit_CACHE = _RDKitModules(
        Chem=chem,
        Descriptors=descriptors,
        Lipinski=lipinski,
        rdMolDescriptors=rd_mol_descriptors,
        Crippen=crippen,
    )
    return _RDKit_CACHE


def rdkit_available() -> bool:
    return _load_rdkit_modules() is not None


def _require_rdkit() -> _RDKitModules:
    modules = _load_rdkit_modules()
    if modules is None:
        raise RdkitUnavailableError(
            "RDKit is not available. Install rdkit to enable ligand descriptor extraction."
        )
    return modules


def _coerce_smiles(smiles: str) -> str:
    text = smiles.strip()
    if not text:
        raise ValueError("smiles must not be empty")
    return text


def _build_descriptors(modules: _RDKitModules, mol: Any) -> dict[str, float | int]:
    descriptors = {
        "molecular_weight": float(modules.Descriptors.MolWt(mol)),
        "exact_molecular_weight": float(modules.Descriptors.ExactMolWt(mol)),
        "heavy_atom_count": int(modules.Descriptors.HeavyAtomCount(mol)),
        "hetero_atom_count": int(modules.Descriptors.NumHeteroatoms(mol)),
        "rotatable_bonds": int(modules.Lipinski.NumRotatableBonds(mol)),
        "h_bond_donors": int(modules.Lipinski.NumHDonors(mol)),
        "h_bond_acceptors": int(modules.Lipinski.NumHAcceptors(mol)),
        "ring_count": int(modules.rdMolDescriptors.CalcNumRings(mol)),
        "aromatic_ring_count": int(modules.rdMolDescriptors.CalcNumAromaticRings(mol)),
        "tpsa": float(modules.rdMolDescriptors.CalcTPSA(mol)),
        "logp": float(modules.Crippen.MolLogP(mol)),
        "fraction_csp3": float(modules.rdMolDescriptors.CalcFractionCSP3(mol)),
    }

    formal_charge_getter = getattr(modules.Chem, "GetFormalCharge", None)
    if callable(formal_charge_getter):
        descriptors["formal_charge"] = int(formal_charge_getter(mol))
    else:
        descriptors["formal_charge"] = 0
    return descriptors


def describe_smiles(smiles: str) -> LigandDescriptorResult:
    modules = _require_rdkit()
    normalized_smiles = _coerce_smiles(smiles)
    mol = modules.Chem.MolFromSmiles(normalized_smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES string: {smiles!r}")
    canonical_smiles = modules.Chem.MolToSmiles(mol, canonical=True)
    return LigandDescriptorResult(
        smiles=normalized_smiles,
        canonical_smiles=canonical_smiles,
        descriptors=_build_descriptors(modules, mol),
        provenance={
            "backend": type(modules).__name__,
            "input_kind": "smiles",
            "canonicalization": "rdkit_canonical_smiles",
        },
    )


def describe_mol(mol: Any, *, smiles: str = "") -> LigandDescriptorResult:
    modules = _require_rdkit()
    if mol is None:
        raise ValueError("mol must not be None")
    canonical_smiles = modules.Chem.MolToSmiles(mol, canonical=True)
    display_smiles = smiles.strip() or canonical_smiles
    return LigandDescriptorResult(
        smiles=display_smiles,
        canonical_smiles=canonical_smiles,
        descriptors=_build_descriptors(modules, mol),
        provenance={
            "backend": type(modules).__name__,
            "input_kind": "mol",
            "canonicalization": "rdkit_canonical_smiles",
        },
    )

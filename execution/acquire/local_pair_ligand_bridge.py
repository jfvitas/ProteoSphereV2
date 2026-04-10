from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from execution.acquire.local_source_registry import LocalSourceEntry

LocalBridgeStatus = Literal["resolved", "unresolved"]
LocalBridgeKind = Literal["protein_protein", "protein_ligand"]
LigandRole = Literal["small_molecule", "peptide", "metal", "artifact", "unknown"]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Iterable):
        return tuple(values)
    return (values,)


def _clean_text_tuple(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def canonical_protein_id(accession: str) -> str:
    normalized = _clean_text(accession)
    if not normalized:
        raise ValueError("accession must not be empty")
    return f"protein:{normalized}"


def canonical_ligand_id(*, ligand_id: str = "", inchi_key: str = "") -> str:
    normalized_ligand_id = _clean_text(ligand_id)
    if normalized_ligand_id:
        return f"ligand:{normalized_ligand_id}"
    normalized_inchi_key = _clean_text(inchi_key)
    if normalized_inchi_key:
        return f"ligand-inchi:{normalized_inchi_key}"
    raise ValueError("ligand_id or inchi_key must be provided")


def canonical_pair_id(accessions: Sequence[str]) -> str:
    normalized = tuple(sorted(_clean_text_tuple(accessions)))
    if len(normalized) < 2:
        raise ValueError("pair_id requires at least two accessions")
    return "pair:" + "--".join(normalized)


@dataclass(frozen=True, slots=True)
class LocalBridgeIssue:
    code: str
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", _clean_text(self.code))
        object.__setattr__(self, "message", _clean_text(self.message))
        if not self.code:
            raise ValueError("issue code must not be empty")
        if not self.message:
            raise ValueError("issue message must not be empty")

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True, slots=True)
class ProteinParticipantBridge:
    role: str
    accession: str
    canonical_id: str
    chain_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        normalized_accession = _clean_text(self.accession)
        object.__setattr__(self, "role", _clean_text(self.role))
        object.__setattr__(self, "accession", normalized_accession)
        object.__setattr__(self, "canonical_id", canonical_protein_id(normalized_accession))
        object.__setattr__(self, "chain_ids", _clean_text_tuple(self.chain_ids))
        if not self.role:
            raise ValueError("protein participant role must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "accession": self.accession,
            "canonical_id": self.canonical_id,
            "chain_ids": list(self.chain_ids),
        }


@dataclass(frozen=True, slots=True)
class LigandBridge:
    role: LigandRole
    ligand_id: str = ""
    inchi_key: str = ""
    smiles: str = ""
    canonical_id: str | None = None
    unresolved_reason: str | None = None

    def __post_init__(self) -> None:
        normalized_role = _clean_text(self.role).replace("-", "_").casefold() or "unknown"
        allowed_roles = {"small_molecule", "peptide", "metal", "artifact", "unknown"}
        if normalized_role not in allowed_roles:
            raise ValueError(f"invalid ligand role: {self.role}")
        normalized_ligand_id = _clean_text(self.ligand_id)
        normalized_inchi = _clean_text(self.inchi_key)
        normalized_smiles = _clean_text(self.smiles)
        normalized_reason = _clean_text(self.unresolved_reason) or None

        canonical_id = self.canonical_id
        if canonical_id is None and normalized_role == "small_molecule":
            if normalized_ligand_id or normalized_inchi:
                canonical_id = canonical_ligand_id(
                    ligand_id=normalized_ligand_id,
                    inchi_key=normalized_inchi,
                )
        if canonical_id is None and normalized_reason is None:
            if normalized_role != "small_molecule":
                normalized_reason = f"{normalized_role}_ligand_not_promoted_to_canonical"
            else:
                normalized_reason = "missing_stable_ligand_identity"

        object.__setattr__(self, "role", normalized_role)
        object.__setattr__(self, "ligand_id", normalized_ligand_id)
        object.__setattr__(self, "inchi_key", normalized_inchi)
        object.__setattr__(self, "smiles", normalized_smiles)
        object.__setattr__(self, "canonical_id", _clean_text(canonical_id) or None)
        object.__setattr__(self, "unresolved_reason", normalized_reason)

    @property
    def resolved(self) -> bool:
        return self.canonical_id is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "ligand_id": self.ligand_id,
            "inchi_key": self.inchi_key,
            "smiles": self.smiles,
            "canonical_id": self.canonical_id,
            "unresolved_reason": self.unresolved_reason,
        }


@dataclass(frozen=True, slots=True)
class LocalBridgeRecord:
    source_name: str
    source_kind: LocalBridgeKind
    source_record_id: str
    source_entry_id: str = ""
    pdb_id: str = ""
    status: LocalBridgeStatus = "unresolved"
    pair_canonical_id: str | None = None
    protein_canonical_ids: tuple[str, ...] = ()
    proteins: tuple[ProteinParticipantBridge, ...] = ()
    ligands: tuple[LigandBridge, ...] = ()
    issues: tuple[LocalBridgeIssue, ...] = ()
    provenance: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", _clean_text(self.source_name))
        object.__setattr__(self, "source_kind", _clean_text(self.source_kind).replace("-", "_"))
        object.__setattr__(self, "source_record_id", _clean_text(self.source_record_id))
        object.__setattr__(self, "source_entry_id", _clean_text(self.source_entry_id))
        object.__setattr__(self, "pdb_id", _clean_text(self.pdb_id))
        object.__setattr__(
            self,
            "protein_canonical_ids",
            _clean_text_tuple(self.protein_canonical_ids),
        )
        object.__setattr__(self, "issues", tuple(self.issues))
        object.__setattr__(self, "proteins", tuple(self.proteins))
        object.__setattr__(self, "ligands", tuple(self.ligands))
        if self.source_kind not in {"protein_protein", "protein_ligand"}:
            raise ValueError("source_kind must be protein_protein or protein_ligand")
        if not self.source_name:
            raise ValueError("source_name must not be empty")
        if not self.source_record_id:
            raise ValueError("source_record_id must not be empty")
        if self.status not in {"resolved", "unresolved"}:
            raise ValueError("status must be resolved or unresolved")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_kind": self.source_kind,
            "source_record_id": self.source_record_id,
            "source_entry_id": self.source_entry_id,
            "pdb_id": self.pdb_id,
            "status": self.status,
            "pair_canonical_id": self.pair_canonical_id,
            "protein_canonical_ids": list(self.protein_canonical_ids),
            "proteins": [protein.to_dict() for protein in self.proteins],
            "ligands": [ligand.to_dict() for ligand in self.ligands],
            "issues": [issue.to_dict() for issue in self.issues],
            "provenance": dict(self.provenance or {}),
        }


def _source_provenance(entry: LocalSourceEntry | None) -> dict[str, Any]:
    if entry is None:
        return {}
    return {
        "source_name": entry.source_name,
        "category": entry.category,
        "status": entry.status,
        "present_roots": list(entry.present_roots),
        "missing_roots": list(entry.missing_roots),
        "load_hints": list(entry.load_hints),
    }


def bridge_local_protein_pair(
    *,
    source_name: str,
    source_record_id: str,
    pdb_id: str = "",
    receptor_accessions: Sequence[str] = (),
    partner_accessions: Sequence[str] = (),
    receptor_chain_ids: Sequence[str] = (),
    partner_chain_ids: Sequence[str] = (),
    source_entry: LocalSourceEntry | None = None,
) -> LocalBridgeRecord:
    receptor = _clean_text_tuple(receptor_accessions)
    partner = _clean_text_tuple(partner_accessions)
    issues: list[LocalBridgeIssue] = []
    proteins: list[ProteinParticipantBridge] = []

    if not receptor:
        issues.append(
            LocalBridgeIssue(
                code="missing_receptor_accession",
                message=(
                    "receptor accession mapping is required "
                    "for canonical protein-pair bridging"
                ),
            )
        )
    elif len(receptor) > 1:
        issues.append(
            LocalBridgeIssue(
                code="multiple_receptor_accessions",
                message="receptor accession mapping is ambiguous and must stay unresolved",
            )
        )
    else:
        proteins.append(
            ProteinParticipantBridge(
                role="receptor",
                accession=receptor[0],
                canonical_id="",
                chain_ids=receptor_chain_ids,
            )
        )

    if not partner:
        issues.append(
            LocalBridgeIssue(
                code="missing_partner_accession",
                message="partner accession mapping is required for canonical protein-pair bridging",
            )
        )
    elif len(partner) > 1:
        issues.append(
            LocalBridgeIssue(
                code="multiple_partner_accessions",
                message="partner accession mapping is ambiguous and must stay unresolved",
            )
        )
    else:
        proteins.append(
            ProteinParticipantBridge(
                role="partner",
                accession=partner[0],
                canonical_id="",
                chain_ids=partner_chain_ids,
            )
        )

    if issues:
        return LocalBridgeRecord(
            source_name=source_name,
            source_kind="protein_protein",
            source_record_id=source_record_id,
            source_entry_id=source_entry.source_name if source_entry else "",
            pdb_id=pdb_id,
            status="unresolved",
            proteins=tuple(proteins),
            protein_canonical_ids=tuple(
                protein.canonical_id for protein in proteins if protein.canonical_id
            ),
            issues=tuple(issues),
            provenance=_source_provenance(source_entry),
        )

    pair_accessions = tuple(protein.accession for protein in proteins)
    return LocalBridgeRecord(
        source_name=source_name,
        source_kind="protein_protein",
        source_record_id=source_record_id,
        source_entry_id=source_entry.source_name if source_entry else "",
        pdb_id=pdb_id,
        status="resolved",
        pair_canonical_id=canonical_pair_id(pair_accessions),
        proteins=tuple(proteins),
        protein_canonical_ids=tuple(protein.canonical_id for protein in proteins),
        issues=(),
        provenance=_source_provenance(source_entry),
    )


def bridge_local_protein_ligand(
    *,
    source_name: str,
    source_record_id: str,
    pdb_id: str = "",
    protein_accessions: Sequence[str] = (),
    protein_chain_ids: Sequence[str] = (),
    ligand_id: str = "",
    ligand_inchi_key: str = "",
    ligand_smiles: str = "",
    ligand_role: LigandRole = "small_molecule",
    source_entry: LocalSourceEntry | None = None,
) -> LocalBridgeRecord:
    accessions = _clean_text_tuple(protein_accessions)
    issues: list[LocalBridgeIssue] = []
    proteins: list[ProteinParticipantBridge] = []
    ligands = (
        LigandBridge(
            role=ligand_role,
            ligand_id=ligand_id,
            inchi_key=ligand_inchi_key,
            smiles=ligand_smiles,
        ),
    )

    if not accessions:
        issues.append(
            LocalBridgeIssue(
                code="missing_protein_accession",
                message=(
                    "protein accession mapping is required "
                    "for canonical protein-ligand bridging"
                ),
            )
        )
    elif len(accessions) > 1:
        issues.append(
            LocalBridgeIssue(
                code="multiple_protein_accessions",
                message="protein accession mapping is ambiguous and must stay unresolved",
            )
        )
    else:
        proteins.append(
            ProteinParticipantBridge(
                role="receptor",
                accession=accessions[0],
                canonical_id="",
                chain_ids=protein_chain_ids,
            )
        )

    if not ligands[0].resolved:
        issues.append(
            LocalBridgeIssue(
                code="unresolved_ligand_identity",
                message=ligands[0].unresolved_reason or "ligand identity remains unresolved",
            )
        )

    status: LocalBridgeStatus = "resolved" if not issues else "unresolved"
    return LocalBridgeRecord(
        source_name=source_name,
        source_kind="protein_ligand",
        source_record_id=source_record_id,
        source_entry_id=source_entry.source_name if source_entry else "",
        pdb_id=pdb_id,
        status=status,
        proteins=tuple(proteins),
        ligands=ligands,
        protein_canonical_ids=tuple(protein.canonical_id for protein in proteins),
        issues=tuple(issues),
        provenance=_source_provenance(source_entry),
    )


def bridge_local_record(
    payload: Mapping[str, Any],
    *,
    source_name: str,
    source_kind: LocalBridgeKind,
    source_entry: LocalSourceEntry | None = None,
) -> LocalBridgeRecord:
    record_id = _clean_text(
        payload.get("source_record_id") or payload.get("pdb_id") or payload.get("id")
    )
    if not record_id:
        raise ValueError("payload must include source_record_id, pdb_id, or id")
    pdb_id = _clean_text(payload.get("pdb_id"))
    if source_kind == "protein_protein":
        return bridge_local_protein_pair(
            source_name=source_name,
            source_record_id=record_id,
            pdb_id=pdb_id,
            receptor_accessions=(
                payload.get("receptor_accessions") or payload.get("uniprot_ids_1") or ()
            ),
            partner_accessions=(
                payload.get("partner_accessions") or payload.get("uniprot_ids_2") or ()
            ),
            receptor_chain_ids=(
                payload.get("receptor_chain_ids") or payload.get("chain_ids_1") or ()
            ),
            partner_chain_ids=payload.get("partner_chain_ids") or payload.get("chain_ids_2") or (),
            source_entry=source_entry,
        )
    return bridge_local_protein_ligand(
        source_name=source_name,
        source_record_id=record_id,
        pdb_id=pdb_id,
        protein_accessions=payload.get("protein_accessions") or payload.get("uniprot_ids") or (),
        protein_chain_ids=payload.get("protein_chain_ids") or payload.get("chain_ids") or (),
        ligand_id=_clean_text(payload.get("ligand_id")),
        ligand_inchi_key=_clean_text(payload.get("ligand_inchi_key")),
        ligand_smiles=_clean_text(payload.get("ligand_smiles")),
        ligand_role=_clean_text(payload.get("ligand_role") or "small_molecule") or "small_molecule",
        source_entry=source_entry,
    )


__all__ = [
    "LigandBridge",
    "LigandRole",
    "LocalBridgeIssue",
    "LocalBridgeKind",
    "LocalBridgeRecord",
    "LocalBridgeStatus",
    "ProteinParticipantBridge",
    "bridge_local_protein_ligand",
    "bridge_local_protein_pair",
    "bridge_local_record",
    "canonical_ligand_id",
    "canonical_pair_id",
    "canonical_protein_id",
]

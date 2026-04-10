from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from hashlib import sha256
from json import JSONDecodeError
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from connectors.rcsb.client import RCSBClient, RCSBClientError
from execution.acquire.local_pair_ligand_bridge import canonical_protein_id

DEFAULT_RCSB_BASE_URL = "https://data.rcsb.org/rest/v1"
DEFAULT_PDBe_BASE_URL = "https://www.ebi.ac.uk/pdbe/api"
DEFAULT_USER_AGENT = "ProteoSphereV2-StructureBridgeProbe/0.1"
SOURCE_NAME = "RCSB/PDBe bridge"
PROBE_KIND = "bridge_only"

StructureBridgeProbeStatus = Literal["ok", "blocked", "unavailable"]
StructureBridgeRecordState = Literal["positive_hit", "reachable_empty"]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_text_tuple(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        raw_values = (values,)
    elif isinstance(values, Sequence):
        raw_values = values
    else:
        raw_values = (values,)
    ordered: dict[str, str] = {}
    for value in raw_values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _normalize_accession(accession: Any) -> str:
    text = _clean_text(accession).upper()
    if not text:
        raise ValueError("accession must not be empty")
    return text


def _normalize_pdb_id(pdb_id: Any) -> str:
    text = _clean_text(pdb_id).upper()
    if len(text) != 4 or not text.isalnum():
        raise ValueError("pdb_id must be a 4-character alphanumeric identifier")
    return text


def _json_fetch(
    url: str,
    *,
    opener: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    request_opener = opener or urlopen
    with request_opener(request, timeout=30.0) as response:
        payload = response.read()
    try:
        parsed = json.loads(payload.decode("utf-8"))
    except JSONDecodeError as exc:
        raise ValueError(f"bridge payload at {url!r} was not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"bridge payload at {url!r} did not return a JSON object")
    return parsed


def _pdbe_uniprot_url(base_url: str, pdb_id: str) -> str:
    return f"{base_url.rstrip('/')}/mappings/uniprot/{pdb_id.lower()}"


def _rcsb_entry_url(base_url: str, pdb_id: str) -> str:
    return f"{base_url.rstrip('/')}/core/entry/{pdb_id.lower()}"


def _rcsb_entity_url(base_url: str, pdb_id: str, entity_id: str) -> str:
    return f"{base_url.rstrip('/')}/core/polymer_entity/{pdb_id.lower()}/{entity_id}"


def _dict_text(mapping: Mapping[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        text = _clean_text(value)
        if text:
            return text
    return default


def _dict_tuple(mapping: Mapping[str, Any], *keys: str) -> tuple[str, ...]:
    for key in keys:
        if key not in mapping:
            continue
        return _clean_text_tuple(mapping[key])
    return ()


def _dict_mapping(mapping: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, Mapping):
            return dict(value)
    return {}


def _entry_title(entry_payload: Mapping[str, Any]) -> str:
    struct = _dict_mapping(entry_payload, "struct")
    return _dict_text(struct, "title")


def _normalize_accession_targets(value: Mapping[str, Sequence[str]]) -> dict[str, tuple[str, ...]]:
    normalized: dict[str, tuple[str, ...]] = {}
    for accession, pdb_ids in value.items():
        normalized_accession = _normalize_accession(accession)
        normalized_ids = []
        seen: set[str] = set()
        for pdb_id in _clean_text_tuple(pdb_ids):
            normalized_pdb_id = _normalize_pdb_id(pdb_id)
            if normalized_pdb_id in seen:
                continue
            seen.add(normalized_pdb_id)
            normalized_ids.append(normalized_pdb_id)
        normalized[normalized_accession] = tuple(normalized_ids)
    return normalized


def _manifest_signature(accession_targets: Mapping[str, Sequence[str]]) -> str:
    ordered_items = sorted(
        (
            _normalize_accession(accession),
            tuple(_normalize_pdb_id(pdb_id) for pdb_id in pdb_ids),
        )
        for accession, pdb_ids in accession_targets.items()
    )
    payload = "|".join(f"{accession}:{','.join(pdb_ids)}" for accession, pdb_ids in ordered_items)
    return sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class StructureBridgeCandidate:
    accession: str
    pdb_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "accession", _normalize_accession(self.accession))
        object.__setattr__(
            self,
            "pdb_ids",
            tuple(dict.fromkeys(_normalize_pdb_id(pdb_id) for pdb_id in self.pdb_ids)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"accession": self.accession, "pdb_ids": list(self.pdb_ids)}


@dataclass(frozen=True, slots=True)
class StructureBridgeCandidateProbeManifest:
    candidates: tuple[StructureBridgeCandidate, ...]
    rcsb_base_url: str = DEFAULT_RCSB_BASE_URL
    pdbe_base_url: str = DEFAULT_PDBe_BASE_URL
    source_name: str = SOURCE_NAME
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidates", tuple(self.candidates))
        object.__setattr__(self, "rcsb_base_url", _clean_text(self.rcsb_base_url))
        object.__setattr__(self, "pdbe_base_url", _clean_text(self.pdbe_base_url))
        object.__setattr__(self, "source_name", _clean_text(self.source_name) or SOURCE_NAME)
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        if not self.candidates:
            raise ValueError("manifest must include at least one candidate")

    @property
    def manifest_id(self) -> str:
        payload = {
            candidate.accession: candidate.pdb_ids for candidate in self.candidates
        }
        return f"structure-bridge-candidate-probe:{_manifest_signature(payload)}"

    @property
    def candidate_accessions(self) -> tuple[str, ...]:
        return tuple(candidate.accession for candidate in self.candidates)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "source_name": self.source_name,
            "rcsb_base_url": self.rcsb_base_url,
            "pdbe_base_url": self.pdbe_base_url,
            "notes": list(self.notes),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> StructureBridgeCandidateProbeManifest:
        candidates_payload = value.get("candidates")
        if candidates_payload is None:
            bridge_targets = value.get("accession_bridge_targets") or {}
            candidates_payload = [
                {"accession": accession, "pdb_ids": pdb_ids}
                for accession, pdb_ids in bridge_targets.items()
            ]
        candidates = tuple(
            StructureBridgeCandidate(
                accession=item.get("accession"),
                pdb_ids=tuple(item.get("pdb_ids") or item.get("bridge_pdb_ids") or ()),
            )
            for item in candidates_payload
            if isinstance(item, Mapping)
        )
        return cls(
            candidates=candidates,
            rcsb_base_url=(
                value.get("rcsb_base_url") or value.get("base_url") or DEFAULT_RCSB_BASE_URL
            ),
            pdbe_base_url=value.get("pdbe_base_url") or DEFAULT_PDBe_BASE_URL,
            source_name=value.get("source_name") or SOURCE_NAME,
            notes=tuple(value.get("notes") or ()),
        )


@dataclass(frozen=True, slots=True)
class StructureBridgeCandidateRecord:
    source_name: str
    source_record_id: str
    accession: str
    canonical_id: str
    pdb_id: str
    bridge_state: StructureBridgeRecordState
    bridge_kind: str = PROBE_KIND
    entry_title: str = ""
    entity_ids: tuple[str, ...] = ()
    chain_ids: tuple[str, ...] = ()
    matched_uniprot_ids: tuple[str, ...] = ()
    observed_uniprot_ids: tuple[str, ...] = ()
    rcsb_entry_ref: str = ""
    rcsb_entity_refs: tuple[str, ...] = ()
    pdbe_bridge_ref: str = ""
    evidence_refs: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_name", _clean_text(self.source_name) or SOURCE_NAME)
        object.__setattr__(self, "source_record_id", _clean_text(self.source_record_id))
        object.__setattr__(self, "accession", _normalize_accession(self.accession))
        object.__setattr__(self, "canonical_id", canonical_protein_id(self.accession))
        object.__setattr__(self, "pdb_id", _normalize_pdb_id(self.pdb_id))
        object.__setattr__(self, "bridge_state", _clean_text(self.bridge_state))  # type: ignore[arg-type]
        object.__setattr__(self, "bridge_kind", _clean_text(self.bridge_kind) or PROBE_KIND)
        object.__setattr__(self, "entry_title", _clean_text(self.entry_title))
        object.__setattr__(self, "entity_ids", _clean_text_tuple(self.entity_ids))
        object.__setattr__(self, "chain_ids", _clean_text_tuple(self.chain_ids))
        object.__setattr__(self, "matched_uniprot_ids", _clean_text_tuple(self.matched_uniprot_ids))
        object.__setattr__(
            self,
            "observed_uniprot_ids",
            _clean_text_tuple(self.observed_uniprot_ids),
        )
        object.__setattr__(self, "rcsb_entry_ref", _clean_text(self.rcsb_entry_ref))
        object.__setattr__(self, "rcsb_entity_refs", _clean_text_tuple(self.rcsb_entity_refs))
        object.__setattr__(self, "pdbe_bridge_ref", _clean_text(self.pdbe_bridge_ref))
        object.__setattr__(self, "evidence_refs", _clean_text_tuple(self.evidence_refs))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        object.__setattr__(self, "provenance", dict(self.provenance))
        if not self.source_record_id:
            raise ValueError("source_record_id must not be empty")
        if self.bridge_state not in {"positive_hit", "reachable_empty"}:
            raise ValueError("bridge_state must be positive_hit or reachable_empty")
        if self.bridge_kind != PROBE_KIND:
            raise ValueError("bridge_kind must remain bridge_only")

    @property
    def resolved(self) -> bool:
        return self.bridge_state == "positive_hit"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_record_id": self.source_record_id,
            "accession": self.accession,
            "canonical_id": self.canonical_id,
            "pdb_id": self.pdb_id,
            "bridge_state": self.bridge_state,
            "bridge_kind": self.bridge_kind,
            "entry_title": self.entry_title,
            "entity_ids": list(self.entity_ids),
            "chain_ids": list(self.chain_ids),
            "matched_uniprot_ids": list(self.matched_uniprot_ids),
            "observed_uniprot_ids": list(self.observed_uniprot_ids),
            "rcsb_entry_ref": self.rcsb_entry_ref,
            "rcsb_entity_refs": list(self.rcsb_entity_refs),
            "pdbe_bridge_ref": self.pdbe_bridge_ref,
            "evidence_refs": list(self.evidence_refs),
            "notes": list(self.notes),
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class StructureBridgeCandidateProbeResult:
    status: StructureBridgeProbeStatus
    reason: str
    manifest: StructureBridgeCandidateProbeManifest
    records: tuple[StructureBridgeCandidateRecord, ...]
    blockers: tuple[str, ...] = ()
    unavailable_reason: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason", _clean_text(self.reason))
        object.__setattr__(self, "records", tuple(self.records))
        object.__setattr__(self, "blockers", _clean_text_tuple(self.blockers))
        object.__setattr__(self, "unavailable_reason", _clean_text(self.unavailable_reason))
        object.__setattr__(self, "provenance", dict(self.provenance))
        if self.status not in {"ok", "blocked", "unavailable"}:
            raise ValueError("status must be ok, blocked, or unavailable")

    @property
    def succeeded(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "manifest": self.manifest.to_dict(),
            "records": [record.to_dict() for record in self.records],
            "blockers": list(self.blockers),
            "unavailable_reason": self.unavailable_reason,
            "provenance": dict(self.provenance),
        }


def build_structure_bridge_candidate_probe_manifest(
    accession_bridge_targets: Mapping[str, Sequence[str]],
    *,
    rcsb_base_url: str = DEFAULT_RCSB_BASE_URL,
    pdbe_base_url: str = DEFAULT_PDBe_BASE_URL,
    source_name: str = SOURCE_NAME,
    notes: Sequence[str] = (),
) -> StructureBridgeCandidateProbeManifest:
    candidates = tuple(
        StructureBridgeCandidate(accession=accession, pdb_ids=tuple(pdb_ids))
        for accession, pdb_ids in _normalize_accession_targets(accession_bridge_targets).items()
    )
    return StructureBridgeCandidateProbeManifest(
        candidates=candidates,
        rcsb_base_url=rcsb_base_url,
        pdbe_base_url=pdbe_base_url,
        source_name=source_name,
        notes=tuple(notes),
    )


def _extract_entry_entity_ids(entry_payload: Mapping[str, Any]) -> tuple[str, ...]:
    identifiers = _dict_mapping(entry_payload, "rcsb_entry_container_identifiers")
    return _dict_tuple(identifiers, "polymer_entity_ids")


def _extract_entity_chain_ids(entity_payload: Mapping[str, Any]) -> tuple[str, ...]:
    identifiers = _dict_mapping(entity_payload, "rcsb_polymer_entity_container_identifiers")
    return _dict_tuple(identifiers, "auth_asym_ids")


def _extract_entity_uniprot_ids(entity_payload: Mapping[str, Any]) -> tuple[str, ...]:
    identifiers = _dict_mapping(entity_payload, "rcsb_polymer_entity_container_identifiers")
    return _dict_tuple(identifiers, "uniprot_ids")


def _extract_pdbe_bridge(
    pdbe_payload: Mapping[str, Any],
    *,
    pdb_id: str,
    accession: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    root = (
        pdbe_payload.get(pdb_id.lower())
        or pdbe_payload.get(pdb_id.upper())
        or pdbe_payload.get(pdb_id)
    )
    if not isinstance(root, Mapping):
        return (), ()
    uniprot_block: Mapping[str, Any] | None = None
    for key, value in root.items():
        if _clean_text(key).casefold() in {"uniprot", "uniprotkb"} and isinstance(value, Mapping):
            uniprot_block = value
            break
    if uniprot_block is None:
        return (), ()
    accession_block = uniprot_block.get(accession) or uniprot_block.get(accession.upper())
    if not isinstance(accession_block, Mapping):
        return (), ()
    chain_ids: list[str] = []
    entity_ids: list[str] = []
    for mapping in accession_block.get("mappings") or ():
        if not isinstance(mapping, Mapping):
            continue
        chain_id = _dict_text(mapping, "chain_id", "struct_asym_id", "auth_asym_id")
        if chain_id and chain_id not in chain_ids:
            chain_ids.append(chain_id)
        entity_id = _dict_text(mapping, "entity_id")
        if entity_id and entity_id not in entity_ids:
            entity_ids.append(entity_id)
    return tuple(chain_ids), tuple(entity_ids)


def _record_provenance(
    *,
    accession: str,
    pdb_id: str,
    bridge_state: StructureBridgeRecordState,
    entry_title: str,
    entity_ids: tuple[str, ...],
    chain_ids: tuple[str, ...],
    matched_uniprot_ids: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "accession": accession,
        "pdb_id": pdb_id,
        "bridge_state": bridge_state,
        "entry_title": entry_title,
        "entity_ids": list(entity_ids),
        "chain_ids": list(chain_ids),
        "matched_uniprot_ids": list(matched_uniprot_ids),
        "bridge_semantics": PROBE_KIND,
    }


def probe_structure_bridge_candidates(
    manifest: StructureBridgeCandidateProbeManifest | Mapping[str, Any],
    *,
    client: RCSBClient | None = None,
    opener: Callable[..., Any] | None = None,
) -> StructureBridgeCandidateProbeResult:
    if not isinstance(manifest, StructureBridgeCandidateProbeManifest):
        manifest = StructureBridgeCandidateProbeManifest.from_mapping(dict(manifest))
    if not manifest.candidates:
        return StructureBridgeCandidateProbeResult(
            status="blocked",
            reason="structure_bridge_probe_requires_candidates",
            manifest=manifest,
            records=(),
            blockers=("missing_accession_bridge_targets",),
            provenance={"bridge_semantics": PROBE_KIND},
        )

    client = client or RCSBClient(base_url=manifest.rcsb_base_url)
    records: list[StructureBridgeCandidateRecord] = []
    blockers: list[str] = []
    unavailable_targets: list[str] = []

    for candidate in manifest.candidates:
        if not candidate.pdb_ids:
            blockers.append(f"{candidate.accession}:missing_bridge_targets")
            continue
        for pdb_id in candidate.pdb_ids:
            source_record_id = f"{candidate.accession}:{pdb_id}"
            rcsb_entry_ref = _rcsb_entry_url(manifest.rcsb_base_url, pdb_id)
            pdbe_bridge_ref = _pdbe_uniprot_url(manifest.pdbe_base_url, pdb_id)
            try:
                entry_payload = client.get_entry(pdb_id, opener=opener)
                entry_title = _entry_title(entry_payload)
                entity_ids = _extract_entry_entity_ids(entry_payload)
                observed_uniprot_ids: list[str] = []
                matched_uniprot_ids: list[str] = []
                chain_ids: list[str] = []
                rcsb_entity_refs: list[str] = []

                for entity_id in entity_ids:
                    entity_ref = _rcsb_entity_url(manifest.rcsb_base_url, pdb_id, entity_id)
                    entity_payload = client.get_entity(pdb_id, entity_id, opener=opener)
                    rcsb_entity_refs.append(entity_ref)
                    entity_uniprot_ids = _extract_entity_uniprot_ids(entity_payload)
                    for item in entity_uniprot_ids:
                        if item not in observed_uniprot_ids:
                            observed_uniprot_ids.append(item)
                    entity_chain_ids = _extract_entity_chain_ids(entity_payload)
                    for chain_id in entity_chain_ids:
                        if chain_id not in chain_ids:
                            chain_ids.append(chain_id)
                    if (
                        candidate.accession in entity_uniprot_ids
                        and candidate.accession not in matched_uniprot_ids
                    ):
                        matched_uniprot_ids.append(candidate.accession)

                pdbe_payload = _json_fetch(pdbe_bridge_ref, opener=opener)
                pdbe_chain_ids, pdbe_entity_ids = _extract_pdbe_bridge(
                    pdbe_payload,
                    pdb_id=pdb_id,
                    accession=candidate.accession,
                )
                for chain_id in pdbe_chain_ids:
                    if chain_id not in chain_ids:
                        chain_ids.append(chain_id)
                for entity_id in pdbe_entity_ids:
                    if entity_id not in entity_ids:
                        entity_ids = tuple((*entity_ids, entity_id))

                matched = bool(matched_uniprot_ids or pdbe_chain_ids or pdbe_entity_ids)
                bridge_state: StructureBridgeRecordState = (
                    "positive_hit" if matched else "reachable_empty"
                )
                notes = (
                    "bridge_only_evidence",
                )
                if not matched:
                    notes = (
                        "bridge_lookup_reachable_but_accession_not_linked",
                    )
                records.append(
                    StructureBridgeCandidateRecord(
                        source_name=manifest.source_name,
                        source_record_id=source_record_id,
                        accession=candidate.accession,
                        canonical_id=canonical_protein_id(candidate.accession),
                        pdb_id=pdb_id,
                        bridge_state=bridge_state,
                        entry_title=entry_title,
                        entity_ids=entity_ids,
                        chain_ids=tuple(chain_ids),
                        matched_uniprot_ids=tuple(matched_uniprot_ids),
                        observed_uniprot_ids=tuple(observed_uniprot_ids),
                        rcsb_entry_ref=rcsb_entry_ref,
                        rcsb_entity_refs=tuple(rcsb_entity_refs),
                        pdbe_bridge_ref=pdbe_bridge_ref,
                        evidence_refs=(rcsb_entry_ref, *rcsb_entity_refs, pdbe_bridge_ref),
                        notes=notes,
                        provenance=_record_provenance(
                            accession=candidate.accession,
                            pdb_id=pdb_id,
                            bridge_state=bridge_state,
                            entry_title=entry_title,
                            entity_ids=entity_ids,
                            chain_ids=tuple(chain_ids),
                            matched_uniprot_ids=tuple(matched_uniprot_ids),
                        ),
                    )
                )
            except (HTTPError, RCSBClientError, URLError, OSError, ValueError) as exc:
                unavailable_targets.append(f"{candidate.accession}:{pdb_id}:{exc}")

    if unavailable_targets and not records:
        return StructureBridgeCandidateProbeResult(
            status="unavailable",
            reason="structure_bridge_probe_unavailable",
            manifest=manifest,
            records=(),
            unavailable_reason=unavailable_targets[0],
            provenance={"bridge_semantics": PROBE_KIND, "unavailable_targets": unavailable_targets},
        )

    if blockers and not records:
        return StructureBridgeCandidateProbeResult(
            status="blocked",
            reason="structure_bridge_probe_blocked",
            manifest=manifest,
            records=(),
            blockers=tuple(blockers),
            provenance={"bridge_semantics": PROBE_KIND},
        )

    return StructureBridgeCandidateProbeResult(
        status="ok",
        reason="structure_bridge_probe_completed",
        manifest=manifest,
        records=tuple(records),
        blockers=tuple(blockers),
        unavailable_reason=unavailable_targets[0] if unavailable_targets and not records else "",
        provenance={
            "bridge_semantics": PROBE_KIND,
            "candidate_count": len(manifest.candidates),
            "record_count": len(records),
            "positive_hit_count": sum(
                1 for record in records if record.bridge_state == "positive_hit"
            ),
            "reachable_empty_count": sum(
                1 for record in records if record.bridge_state == "reachable_empty"
            ),
        },
    )


__all__ = [
    "DEFAULT_PDBe_BASE_URL",
    "DEFAULT_RCSB_BASE_URL",
    "PROBE_KIND",
    "SOURCE_NAME",
    "StructureBridgeCandidate",
    "StructureBridgeCandidateProbeManifest",
    "StructureBridgeCandidateProbeResult",
    "StructureBridgeCandidateRecord",
    "StructureBridgeProbeStatus",
    "StructureBridgeRecordState",
    "build_structure_bridge_candidate_probe_manifest",
    "probe_structure_bridge_candidates",
]

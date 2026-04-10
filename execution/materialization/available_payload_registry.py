from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from connectors.bindingdb.parsers import parse_bindingdb_assays
from core.procurement.source_release_manifest import SourceReleaseManifest
from execution.acquire.intact_snapshot import acquire_intact_snapshot

ROOT = Path(__file__).resolve().parents[2]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes, Path)):
        return (values,)
    if isinstance(values, tuple):
        return values
    if isinstance(values, list):
        return tuple(values)
    if isinstance(values, Mapping):
        return tuple(values.values())
    try:
        return tuple(values)
    except TypeError:
        return (values,)


def _dedupe_text(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _json_ready_payload(payload: Any) -> Any:
    if isinstance(payload, Path):
        return {
            "kind": "file_ref",
            "path": str(payload).replace("\\", "/"),
        }
    if isinstance(payload, tuple):
        return [_json_ready_payload(item) for item in payload]
    if isinstance(payload, list):
        return [_json_ready_payload(item) for item in payload]
    if isinstance(payload, Mapping):
        return {str(key): _json_ready_payload(item) for key, item in payload.items()}
    return payload


def _selected_rows(payload: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    for key in ("selected_rows", "selected_examples", "rows", "proposals"):
        rows = payload.get(key) or ()
        if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes)):
            return tuple(dict(row) for row in rows if isinstance(row, Mapping))
    return ()


def _requested_modalities(row: Mapping[str, Any]) -> tuple[str, ...]:
    expectation = row.get("packet_expectation")
    if isinstance(expectation, Mapping):
        requested = _dedupe_text(
            (
                *_iter_values(expectation.get("requested_modalities")),
                *_iter_values(expectation.get("present_modalities")),
                *_iter_values(expectation.get("missing_modalities")),
            )
        )
        if requested:
            return requested
    requested = _dedupe_text(row.get("requested_modalities"))
    if requested:
        return requested
    return ("sequence", "structure", "ligand", "ppi")


def _modality_source_refs(row: Mapping[str, Any], accession: str) -> dict[str, tuple[str, ...]]:
    requested = _requested_modalities(row)
    modality_sources = row.get("modality_sources")
    resolved: dict[str, tuple[str, ...]] = {}
    for modality in requested:
        refs: tuple[str, ...] = ()
        if isinstance(modality_sources, Mapping):
            refs = _dedupe_text(modality_sources.get(modality))
        if not refs:
            refs = (f"{modality}:{accession}",)
        resolved[modality] = refs
    return resolved


def _canonical_sequence_index(canonical_latest_path: Path) -> dict[str, dict[str, Any]]:
    if not canonical_latest_path.exists():
        return {}
    payload = _read_json(canonical_latest_path)
    if not isinstance(payload, Mapping):
        return {}
    sequence_result = payload.get("sequence_result")
    if not isinstance(sequence_result, Mapping):
        return {}
    proteins = sequence_result.get("canonical_proteins") or ()
    if not isinstance(proteins, Sequence) or isinstance(proteins, (str, bytes)):
        return {}
    index: dict[str, dict[str, Any]] = {}
    for protein in proteins:
        if not isinstance(protein, Mapping):
            continue
        accession = _clean_text(protein.get("accession"))
        if accession:
            index[accession.upper()] = dict(protein)
    return index


def _find_uniprot_sequence_payload(raw_root: Path, accession: str) -> Path | None:
    run_dir = _latest_run_dir(raw_root / "uniprot")
    if run_dir is None:
        return None
    accession_dir = run_dir / accession
    if not accession_dir.exists():
        return None
    matches = sorted(accession_dir.glob("*.fasta"))
    if matches:
        return matches[0]
    return None


def _latest_run_dir(source_root: Path) -> Path | None:
    if not source_root.exists():
        return None
    candidates = sorted(
        (path for path in source_root.iterdir() if path.is_dir()),
        key=lambda path: path.name,
    )
    return candidates[-1] if candidates else None


def _find_alphafold_payload(raw_root: Path, accession: str) -> Path | None:
    for source_name in ("alphafold", "alphafold_local"):
        run_dir = _latest_run_dir(raw_root / source_name)
        if run_dir is None:
            continue
        accession_dir = run_dir / accession
        if not accession_dir.exists():
            continue
        for suffix in (".cif.cif", ".pdb.pdb", ".pdb.gz", ".bcif.bcif", ".prediction.json"):
            matches = sorted(accession_dir.glob(f"*{suffix}"))
            if matches:
                return matches[0]
    return None


def _bridge_ligand_payload(raw_root: Path, accession: str) -> dict[str, Any] | None:
    candidate_paths = (
        ROOT / "artifacts" / "status" / "local_bridge_ligand_payloads.real.json",
        ROOT / "artifacts" / "status" / "local_bridge_ligand_payloads.json",
    )
    bridge_path = next((path for path in candidate_paths if path.exists()), None)
    if bridge_path is None:
        return None
    payload = _read_json(bridge_path)
    if not isinstance(payload, Mapping):
        return None
    for entry in _iter_values(payload.get("entries")):
        if not isinstance(entry, Mapping):
            continue
        if _clean_text(entry.get("accession")).upper() != accession.upper():
            continue
        bridge_record = entry.get("bridge_record")
        selected_ligand = entry.get("selected_ligand")
        if not isinstance(bridge_record, Mapping):
            return None
        return {
            "source": "local_bridge_ligand",
            "accession": accession,
            "pdb_id": _clean_text(entry.get("pdb_id")),
            "bridge_kind": _clean_text(entry.get("bridge_kind")),
            "selected_ligand": (
                dict(selected_ligand) if isinstance(selected_ligand, Mapping) else None
            ),
            "bridge_record": dict(bridge_record),
        }
    return None


def _local_chembl_ligand_payload(raw_root: Path, accession: str) -> dict[str, Any] | None:
    candidate_paths = (
        ROOT / "artifacts" / "status" / f"{accession.lower()}_local_chembl_ligand_payload.json",
        ROOT / "artifacts" / "status" / "p00387_local_chembl_ligand_payload.json",
    )
    payload_path = next((path for path in candidate_paths if path.exists()), None)
    if payload_path is None:
        return None
    payload = _read_json(payload_path)
    if not isinstance(payload, Mapping):
        return None
    if _clean_text(payload.get("accession")).upper() != accession.upper():
        return None
    if _clean_text(payload.get("status")).casefold() != "resolved":
        return None
    rows = payload.get("rows")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        return None
    return {
        "source": "local_chembl_ligand",
        "accession": accession,
        "packet_source_ref": _clean_text(payload.get("packet_source_ref"))
        or f"ligand:{accession.upper()}",
        "summary": dict(payload.get("summary") or {}),
        "rows": [dict(row) for row in rows if isinstance(row, Mapping)],
        "truth_boundary": dict(payload.get("truth_boundary") or {}),
        "source_db_path": _clean_text(payload.get("source_db_path")),
    }


def _bridge_ppi_payload(raw_root: Path, accession: str) -> dict[str, Any] | None:
    candidate_paths = (
        ROOT / "artifacts" / "status" / "local_bridge_ppi_payloads.real.json",
        ROOT / "artifacts" / "status" / "local_bridge_ppi_payloads.json",
    )
    bridge_path = next((path for path in candidate_paths if path.exists()), None)
    if bridge_path is None:
        return None
    payload = _read_json(bridge_path)
    if not isinstance(payload, Mapping):
        return None
    accession_key = accession.upper()
    best_match: dict[str, Any] | None = None
    for entry in _iter_values(payload.get("entries")):
        if not isinstance(entry, Mapping):
            continue
        status = _clean_text(entry.get("status")).casefold()
        if status != "resolved":
            continue
        observed_accessions = {
            _clean_text(value).upper() for value in _iter_values(entry.get("observed_accessions"))
        }
        accession_a = _clean_text(entry.get("accession_a")).upper()
        accession_b = _clean_text(entry.get("accession_b")).upper()
        if accession_key not in observed_accessions.union({accession_a, accession_b}):
            continue
        best_match = dict(entry)
        break
    return best_match


def _find_bindingdb_payload(raw_root: Path, accession: str) -> Path | None:
    run_dir = _latest_run_dir(raw_root / "bindingdb")
    if run_dir is None:
        return None
    accession_dir = run_dir / accession
    if not accession_dir.exists():
        return None
    matches = sorted(accession_dir.glob("*.bindingdb.json"))
    for match in matches:
        if _bindingdb_payload_has_meaningful_assays(match, accession):
            return match
    return None


def _find_intact_payload(raw_root: Path, accession: str) -> Path | None:
    run_dir = _latest_run_dir(raw_root / "intact")
    if run_dir is None:
        return None
    accession_dir = run_dir / accession
    if not accession_dir.exists():
        return None
    matches = sorted(accession_dir.glob("*.psicquic.tab25.txt"))
    for match in matches:
        if _intact_payload_has_non_self_pair(match, accession):
            return match
    return None


def _bindingdb_payload_has_meaningful_assays(path: Path, accession: str) -> bool:
    try:
        payload = _read_json(path)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return False
    try:
        records = parse_bindingdb_assays(payload, source="bindingdb_raw")
    except (TypeError, ValueError):
        return False
    accession_key = accession.upper()
    for record in records:
        if accession_key not in {item.upper() for item in record.target_uniprot_ids}:
            continue
        if any(
            (
                _clean_text(record.reactant_set_id),
                _clean_text(record.monomer_id),
                _clean_text(record.ligand_smiles),
                _clean_text(record.ligand_inchi_key),
                record.affinity_value_nM is not None,
            )
        ):
            return True
    return False


def _intact_payload_has_non_self_pair(path: Path, accession: str) -> bool:
    try:
        manifest = SourceReleaseManifest(
            source_name="IntAct",
            release_version=path.parent.parent.name or "local",
            retrieval_mode="download",
            source_locator=str(path),
            local_artifact_refs=(str(path),),
            provenance=("local", "intact", "payload-registry"),
        )
        result = acquire_intact_snapshot(manifest)
    except (OSError, TypeError, ValueError):
        return False
    snapshot = result.snapshot
    if not result.succeeded or snapshot is None:
        return False
    accession_key = accession.upper()
    for record in snapshot.records:
        accession_a = _clean_text(record.participant_a_primary_id).upper()
        accession_b = _clean_text(record.participant_b_primary_id).upper()
        if accession_key not in {accession_a, accession_b}:
            continue
        if accession_a and accession_b and accession_a != accession_b:
            return True
    return False


def _resolve_payload(
    *,
    modality: str,
    accession: str,
    canonical_sequences: Mapping[str, dict[str, Any]],
    raw_root: Path,
) -> Any | None:
    accession_key = accession.upper()
    if modality == "sequence":
        protein = canonical_sequences.get(accession_key)
        if protein is not None:
            return {
                "accession": _clean_text(protein.get("accession")) or accession,
                "canonical_id": _clean_text(protein.get("canonical_id"))
                or _clean_text(protein.get("canonical_protein_id"))
                or f"protein:{accession}",
                "sequence": _clean_text(protein.get("sequence")),
                "sequence_length": protein.get("sequence_length"),
                "source": _clean_text(protein.get("source")) or "canonical_sequence",
            }
        return _find_uniprot_sequence_payload(raw_root, accession)
    if modality == "structure":
        return _find_alphafold_payload(raw_root, accession)
    if modality == "ligand":
        bridge_payload = _bridge_ligand_payload(raw_root, accession)
        if bridge_payload is not None:
            return bridge_payload
        chembl_payload = _local_chembl_ligand_payload(raw_root, accession)
        if chembl_payload is not None:
            return chembl_payload
        return _find_bindingdb_payload(raw_root, accession)
    if modality == "ppi":
        bridge_payload = _bridge_ppi_payload(raw_root, accession)
        if bridge_payload is not None:
            return bridge_payload
        return _find_intact_payload(raw_root, accession)
    return None


@dataclass(frozen=True, slots=True)
class AvailablePayloadRegistry:
    available_payloads: dict[str, Any]
    missing_payload_refs: tuple[str, ...]
    packet_rows: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "available_payloads": {
                ref: _json_ready_payload(payload)
                for ref, payload in self.available_payloads.items()
            },
            "missing_payload_refs": list(self.missing_payload_refs),
            "packet_rows": list(self.packet_rows),
            "available_payload_count": len(self.available_payloads),
            "missing_payload_count": len(self.missing_payload_refs),
        }


def build_available_payload_registry(
    *,
    balanced_plan: Mapping[str, Any],
    canonical_latest_path: Path,
    raw_root: Path,
) -> AvailablePayloadRegistry:
    canonical_sequences = _canonical_sequence_index(canonical_latest_path)
    available_payloads: dict[str, Any] = {}
    missing_payload_refs: list[str] = []
    packet_rows: list[dict[str, Any]] = []

    for row in _selected_rows(balanced_plan):
        accession = _clean_text(row.get("accession"))
        if not accession:
            continue
        modality_source_refs = _modality_source_refs(row, accession)
        resolved_modalities: dict[str, list[str]] = {}
        missing_modalities: dict[str, list[str]] = {}

        for modality, refs in modality_source_refs.items():
            payload = _resolve_payload(
                modality=modality,
                accession=accession,
                canonical_sequences=canonical_sequences,
                raw_root=raw_root,
            )
            if payload is None:
                missing_modalities[modality] = list(refs)
                missing_payload_refs.extend(refs)
                continue
            resolved_modalities[modality] = list(refs)
            for ref in refs:
                available_payloads[ref] = payload

        packet_rows.append(
            {
                "accession": accession,
                "canonical_id": _clean_text(row.get("canonical_id")) or f"protein:{accession}",
                "resolved_modalities": resolved_modalities,
                "missing_modalities": missing_modalities,
            }
        )

    return AvailablePayloadRegistry(
        available_payloads=available_payloads,
        missing_payload_refs=_dedupe_text(missing_payload_refs),
        packet_rows=tuple(packet_rows),
    )

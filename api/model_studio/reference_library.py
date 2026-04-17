from __future__ import annotations

import json
import zlib
from pathlib import Path
from typing import Any


CHUNK_MAGIC = b"PROTEOSPHERE-LITE-CHUNK\n"
DECODER_VERSION = "proteosphere-lite-decoder-v1"
DEFAULT_PUBLIC_WARNING = (
    "Public export omits full internal detail and raw corpora. "
    "Use the local warehouse for full-fidelity validation, enrichment, and packet hydration."
)
SOURCE_NAME_FAMILY_ALIASES = {
    "alphafold db": "alphafold",
    "alphafold": "alphafold",
    "bindingdb": "bindingdb",
    "biogrid": "biogrid",
    "biolip": "biolip",
    "intact": "intact",
    "reactome": "reactome",
    "uniprot": "uniprot",
}


def encode_chunk_payload(payload: dict[str, Any]) -> bytes:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return CHUNK_MAGIC + zlib.compress(body, level=9)


def decode_chunk_payload_bytes(data: bytes) -> dict[str, Any]:
    if not data.startswith(CHUNK_MAGIC):
        raise ValueError("Unsupported chunk payload format.")
    raw = zlib.decompress(data[len(CHUNK_MAGIC):])
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Chunk payload must decode to an object.")
    return payload


def decode_chunk_payload(path: Path) -> dict[str, Any]:
    return decode_chunk_payload_bytes(path.read_bytes())


def build_public_warning_banner(payload: dict[str, Any] | None = None) -> str:
    export_policy = {}
    warehouse_id = None
    bundle_version = None
    if isinstance(payload, dict):
        export_policy = payload.get("export_policy") or {}
        warehouse_id = payload.get("warehouse_id")
        bundle_version = payload.get("bundle_version")
    warning = export_policy.get("warning_banner") if isinstance(export_policy, dict) else None
    warning_text = str(warning or DEFAULT_PUBLIC_WARNING).strip()
    lines = [warning_text]
    if warehouse_id:
        lines.append(f"Warehouse: {warehouse_id}")
    if bundle_version:
        lines.append(f"Bundle: {bundle_version}")
    return "\n".join(lines)


def load_public_reference_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Public reference manifest must decode to an object.")
    return payload


def extract_claim_view(record: dict[str, Any], view: str = "best_evidence") -> Any:
    if not isinstance(record, dict):
        raise TypeError("record must be a mapping-like object")
    normalized_view = str(view or "best_evidence").strip().casefold()
    has_claim_surfaces = any(
        key in record
        for key in (
            "best_evidence_claims",
            "raw_claims",
            "derived_claims",
            "scraped_claims",
        )
    )
    if not has_claim_surfaces:
        return {
            "mode": "summary_record",
            "selected_view": normalized_view,
            "summary_record": record,
        }
    if normalized_view in {"best_evidence", "best-evidence"}:
        payload = record.get("best_evidence_claims")
    elif normalized_view in {"raw", "raw_claims", "raw-claims"}:
        payload = record.get("raw_claims")
    elif normalized_view in {
        "derived_or_scraped",
        "derived",
        "scraped",
        "derived_claims",
        "derived-or-scraped",
    }:
        derived_payload = record.get("derived_claims")
        scraped_payload = record.get("scraped_claims")
        if derived_payload and not scraped_payload:
            payload = derived_payload
        elif scraped_payload and not derived_payload:
            payload = scraped_payload
        elif isinstance(derived_payload, list) and isinstance(scraped_payload, list):
            payload = [*derived_payload, *scraped_payload]
        else:
            payload = {
                "derived_claims": derived_payload or [],
                "scraped_claims": scraped_payload or [],
            }
    else:
        raise ValueError(f"unsupported reference-library claim view: {view!r}")
    if payload is None:
        return {}
    if isinstance(payload, (dict, list)):
        return payload
    return {}


def build_entity_conflict_summary(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise TypeError("record must be a mapping-like object")
    has_claim_surfaces = any(
        key in record
        for key in (
            "best_evidence_claims",
            "raw_claims",
            "derived_claims",
            "scraped_claims",
        )
    )
    payload = record.get("conflict_summary") or {}
    if not isinstance(payload, dict):
        payload = {}
    extra_notes = []
    if not has_claim_surfaces and not payload:
        extra_notes.append(
            "physical table row is a summarized warehouse record; claim surfaces are not materialized here"
        )
    return {
        "has_conflicts": bool(
            payload.get("has_conflicts", payload.get("conflict_detected", False))
        ),
        "compared_surfaces": list(payload.get("compared_surfaces") or []),
        "conflict_fields": list(payload.get("conflict_fields") or []),
        "selected_view": str(
            payload.get("selected_view") or ("best_evidence" if (has_claim_surfaces or payload) else "summary_record")
        ),
        "notes": list(payload.get("notes") or []) + extra_notes,
        "summary_contract": not has_claim_surfaces,
    }


def load_source_registry(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(payload, dict):
        raise ValueError("source registry must decode to an object")
    return payload


def load_paper_split_audit_registry(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(payload, dict):
        raise ValueError("paper split audit registry must decode to an object")
    return payload


def load_paper_identifier_bridge_registry(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(payload, dict):
        raise ValueError("paper identifier bridge registry must decode to an object")
    return payload


def normalize_source_family_name(value: str) -> str:
    text = str(value or "").strip().casefold()
    if not text:
        return ""
    normalized = text.replace("-", "_").replace(" ", "_")
    return SOURCE_NAME_FAMILY_ALIASES.get(text, normalized)


def resolve_materialization_route(
    route_record: dict[str, Any],
    source_registry_payload: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(route_record, dict):
        raise TypeError("route_record must be a mapping-like object")
    if not isinstance(source_registry_payload, dict):
        raise TypeError("source_registry_payload must be a mapping-like object")

    source_name = str(route_record.get("source_name") or "").strip()
    source_key = normalize_source_family_name(source_name)
    snapshot_id = str(route_record.get("snapshot_id") or "").strip()
    records = source_registry_payload.get("source_records") or source_registry_payload.get("records") or []
    matched = []
    for row in records:
        if not isinstance(row, dict):
            continue
        family = str(row.get("source_family") or row.get("source_key") or "").strip().casefold()
        row_snapshot = str(row.get("snapshot_id") or "").strip()
        if family != source_key:
            continue
        if snapshot_id and row_snapshot and row_snapshot != snapshot_id:
            continue
        matched.append(row)
    chosen = next(
        (
            row
            for row in matched
            if str(row.get("integration_status") or "").strip().casefold() == "promoted"
        ),
        matched[0] if matched else None,
    )
    asset_pack_root = str((chosen or {}).get("asset_pack_root") or "").strip()
    canonical_root = asset_pack_root or str((chosen or {}).get("authoritative_root") or "").strip()
    original_pointer = str(route_record.get("pointer") or "").strip()
    pointer_lower = original_pointer.replace("\\", "/").casefold()
    is_library_owned_pointer = pointer_lower.startswith(
        ("d:/proteosphere/reference_library/", "e:/proteosphere/reference_library/")
    )
    resolution_mode = "library_owned_pointer"
    if "/asset_packs/" in pointer_lower:
        resolution_mode = "library_owned_asset_pack_pointer"
    if is_library_owned_pointer:
        return {
            "resolution_mode": resolution_mode,
            "source_name": source_name,
            "snapshot_id": snapshot_id,
            "route_id": str(route_record.get("route_id") or "").strip(),
            "original_pointer": original_pointer,
            "selector": str(route_record.get("selector") or "").strip(),
            "canonical_root": canonical_root,
            "asset_pack_root": asset_pack_root,
            "direct_pointer_is_external": False,
            "direct_pointer_exists": Path(original_pointer).exists() if original_pointer else False,
            "canonical_root_exists": Path(canonical_root).exists() if canonical_root else False,
        }
    return {
        "resolution_mode": "source_registry_anchor" if canonical_root else "unresolved",
        "source_name": source_name,
        "snapshot_id": snapshot_id,
        "route_id": str(route_record.get("route_id") or "").strip(),
        "original_pointer": original_pointer,
        "selector": str(route_record.get("selector") or "").strip(),
        "canonical_root": canonical_root,
        "asset_pack_root": asset_pack_root,
        "direct_pointer_is_external": original_pointer.lower().startswith(("c:/", "d:/", "e:/")),
        "direct_pointer_exists": Path(original_pointer).exists() if original_pointer else False,
        "canonical_root_exists": Path(canonical_root).exists() if canonical_root else False,
    }

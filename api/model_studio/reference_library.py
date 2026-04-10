from __future__ import annotations

import json
import zlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

CHUNK_MAGIC = b"PROTEOSPHERE-LITE-CHUNK\n"
DECODER_VERSION = "proteosphere-lite-decoder-v1"
DEFAULT_PUBLIC_WARNING = (
    "Public export omits full internal detail and raw corpora. Use the local warehouse "
    "for full-fidelity validation, enrichment, and packet hydration."
)


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


def build_public_warning_banner(payload: Mapping[str, Any] | None) -> str:
    manifest = payload if isinstance(payload, Mapping) else {}
    export_policy = manifest.get("export_policy")
    if isinstance(export_policy, Mapping):
        warning_text = str(export_policy.get("warning_banner") or "").strip()
    else:
        warning_text = ""
    warehouse_id = str(manifest.get("warehouse_id") or "unknown-warehouse").strip()
    bundle_version = str(manifest.get("bundle_version") or "unknown-bundle").strip()
    return (
        "ProteoSphere public metadata export\n"
        f"Warehouse: {warehouse_id}\n"
        f"Bundle version: {bundle_version}\n"
        f"Warning: {warning_text or DEFAULT_PUBLIC_WARNING}"
    )


def load_public_reference_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Public reference manifest must decode to an object.")
    return payload

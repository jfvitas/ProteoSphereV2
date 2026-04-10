from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def render_markdown_summary(title: str, bullets: list[str]) -> str:
    lines = [f"# {title}", ""]
    for bullet in bullets:
        text = str(bullet).strip()
        if text:
            lines.append(f"- {text}")
    lines.append("")
    return "\n".join(lines)


def fetch_json(url: str, *, timeout: int = 60) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ProteoSphereV2 enrichment preview harvester/1.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def accession_rows(training_set_eligibility_matrix: dict[str, Any]) -> list[dict[str, Any]]:
    rows = training_set_eligibility_matrix.get("rows") or []
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        accession = str(row.get("accession") or "").strip()
        if not accession:
            continue
        result.append(dict(row))
    return result


def collect_seed_structures(
    structure_unit_summary_library: dict[str, Any],
    q9nzd4_bridge_validation_preview: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for record in structure_unit_summary_library.get("records") or []:
        if not isinstance(record, dict):
            continue
        structure_id = str(record.get("structure_id") or "").strip().upper()
        if not structure_id:
            continue
        protein_ref = str(record.get("protein_ref") or "").strip()
        accession = protein_ref.split("protein:", 1)[-1] if protein_ref.startswith("protein:") else ""
        entry = indexed.setdefault(
            structure_id,
            {
                "structure_id": structure_id,
                "seed_kind": "structure_unit",
                "seed_accessions": [],
                "seed_chain_ids": [],
                "seed_sources": ["structure_unit_summary_library"],
            },
        )
        chain_id = str(record.get("chain_id") or "").strip()
        if accession and accession not in entry["seed_accessions"]:
            entry["seed_accessions"].append(accession)
        if chain_id and chain_id not in entry["seed_chain_ids"]:
            entry["seed_chain_ids"].append(chain_id)

    if isinstance(q9nzd4_bridge_validation_preview, dict):
        bridge_structure_id = str(
            q9nzd4_bridge_validation_preview.get("best_pdb_id")
            or q9nzd4_bridge_validation_preview.get("structure_id")
            or ""
        ).strip().upper()
        bridge_accession = str(q9nzd4_bridge_validation_preview.get("accession") or "").strip()
        if bridge_structure_id:
            entry = indexed.setdefault(
                bridge_structure_id,
                {
                    "structure_id": bridge_structure_id,
                    "seed_kind": "ligand_bridge",
                    "seed_accessions": [],
                    "seed_chain_ids": [],
                    "seed_sources": ["q9nzd4_bridge_validation_preview"],
                },
            )
            if bridge_accession and bridge_accession not in entry["seed_accessions"]:
                entry["seed_accessions"].append(bridge_accession)
            for chain_id in q9nzd4_bridge_validation_preview.get("chain_ids") or []:
                chain_text = str(chain_id).strip()
                if chain_text and chain_text not in entry["seed_chain_ids"]:
                    entry["seed_chain_ids"].append(chain_text)
            if "q9nzd4_bridge_validation_preview" not in entry["seed_sources"]:
                entry["seed_sources"].append("q9nzd4_bridge_validation_preview")

    rows = list(indexed.values())
    rows.sort(key=lambda row: row["structure_id"])
    return rows


def yyyy_mm_dd(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    if "T" in text:
        return text.split("T", 1)[0]
    return text


def first(items: list[Any] | None) -> Any:
    if not items:
        return None
    return items[0]

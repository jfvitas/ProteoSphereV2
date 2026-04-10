from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.acquire.local_ligand_source_map import build_local_ligand_source_map  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORAGE_ROOT = Path(r"C:\Users\jfvit\Documents\bio-agent-lab")
DEFAULT_MASTER_PDB_REPOSITORY = DEFAULT_STORAGE_ROOT / "master_pdb_repository.csv"
DEFAULT_BIOLIP_PATH = DEFAULT_STORAGE_ROOT / "data_sources" / "biolip" / "BioLiP.txt"
DEFAULT_CHEMBL_PATH = (
    DEFAULT_STORAGE_ROOT
    / "data_sources"
    / "chembl"
    / "chembl_36_sqlite"
    / "chembl_36"
    / "chembl_36_sqlite"
    / "chembl_36.db"
)
DEFAULT_BINDINGDB_INDEX_PATH = (
    DEFAULT_STORAGE_ROOT / "metadata" / "source_indexes" / "bindingdb_bulk_index.sqlite"
)
DEFAULT_ALPHAFOLD_INDEX_PATH = (
    DEFAULT_STORAGE_ROOT / "metadata" / "source_indexes" / "alphafold_archive_index.jsonl.gz"
)
DEFAULT_OUTPUT_PATH = REPO_ROOT / "artifacts" / "status" / "fresh_acquisition_shortlist.json"
DEFAULT_MARKDOWN_PATH = REPO_ROOT / "docs" / "reports" / "fresh_acquisition_shortlist.md"
DEFAULT_ACCESSIONS = ("P09105", "Q2TAC2")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _selected_accessions(value: str) -> tuple[str, ...]:
    if not value.strip():
        return DEFAULT_ACCESSIONS
    ordered: dict[str, str] = {}
    for part in value.split(","):
        text = str(part or "").strip()
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def build_fresh_acquisition_shortlist(
    *,
    accessions: tuple[str, ...],
    storage_root: Path,
    master_pdb_repository_path: Path,
    biolip_path: Path,
    chembl_path: Path,
    bindingdb_index_path: Path,
    alphafold_index_path: Path,
) -> dict[str, Any]:
    raw_map = build_local_ligand_source_map(
        accessions=accessions,
        storage_root=storage_root,
        master_pdb_repository_path=master_pdb_repository_path,
        biolip_path=biolip_path,
        chembl_path=chembl_path,
        bindingdb_index_path=bindingdb_index_path,
        alphafold_index_path=alphafold_index_path,
    )
    entries: list[dict[str, Any]] = []
    for entry in raw_map["entries"]:
        if not isinstance(entry, dict):
            continue
        entries.append(
            {
                "accession": entry.get("accession"),
                "classification": entry.get("classification"),
                "recommended_next_action": entry.get("recommended_next_action"),
                "source_lane_summary": {
                    "master_repository_pdb_ids": list(entry.get("master_repository_pdb_ids") or ()),
                    "biolip_pdb_ids": list(entry.get("biolip_pdb_ids") or ()),
                    "chembl_hit_count": len(entry.get("chembl_hits") or ()),
                    "bindingdb_hit_count": len(entry.get("bindingdb_hits") or ()),
                    "alphafold_hit_count": len(entry.get("alphafold_hits") or ()),
                },
                "planning_status": (
                    "fresh_acquisition_required"
                    if entry.get("classification") == "no_local_candidate"
                    else "local_signal_only"
                ),
            }
        )
    return {
        "schema_id": "proteosphere-fresh-acquisition-shortlist-2026-03-23",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "status": "planning_only",
        "selected_accessions": list(accessions),
        "entries": entries,
        "shortlist_note": (
            "This is a planning-grade shortlist for procurement prioritization only; it does "
            "not imply any actual acquisition or packet completion."
        ),
        "source_inputs": raw_map.get("inputs", {}),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Fresh Acquisition Shortlist",
        "",
        f"- Generated at: `{payload.get('generated_at')}`",
        f"- Status: `{payload.get('status')}`",
        f"- Selected accessions: `{payload.get('selected_accessions')}`",
        "",
        "## Entries",
        "",
    ]
    for entry in payload.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        lane = entry.get("source_lane_summary") or {}
        lines.extend(
            [
                f"- `{entry.get('accession')}` -> `{entry.get('planning_status')}`",
                f"  - classification: `{entry.get('classification')}`",
                f"  - next action: `{entry.get('recommended_next_action')}`",
                "  - signals: "
                f"master={lane.get('master_repository_pdb_ids')} "
                f"biolip={lane.get('biolip_pdb_ids')} "
                f"chembl={lane.get('chembl_hit_count')} "
                f"bindingdb={lane.get('bindingdb_hit_count')} "
                f"alphafold={lane.get('alphafold_hit_count')}",
            ]
        )
    lines.extend(
        [
            "",
            "## Note",
            "",
            f"- {payload.get('shortlist_note')}",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a planning-only fresh acquisition shortlist."
    )
    parser.add_argument("--accessions", default=",".join(DEFAULT_ACCESSIONS))
    parser.add_argument("--storage-root", type=Path, default=DEFAULT_STORAGE_ROOT)
    parser.add_argument(
        "--master-pdb-repository",
        type=Path,
        default=DEFAULT_MASTER_PDB_REPOSITORY,
    )
    parser.add_argument("--biolip", type=Path, default=DEFAULT_BIOLIP_PATH)
    parser.add_argument("--chembl", type=Path, default=DEFAULT_CHEMBL_PATH)
    parser.add_argument("--bindingdb-index", type=Path, default=DEFAULT_BINDINGDB_INDEX_PATH)
    parser.add_argument("--alphafold-index", type=Path, default=DEFAULT_ALPHAFOLD_INDEX_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN_PATH)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_fresh_acquisition_shortlist(
        accessions=_selected_accessions(args.accessions),
        storage_root=args.storage_root,
        master_pdb_repository_path=args.master_pdb_repository,
        biolip_path=args.biolip,
        chembl_path=args.chembl,
        bindingdb_index_path=args.bindingdb_index,
        alphafold_index_path=args.alphafold_index,
    )
    _write_json(args.output, payload)
    _write_text(args.markdown, render_markdown(payload))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Fresh acquisition shortlist exported: "
            f"accessions={len(payload['selected_accessions'])} status={payload['status']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

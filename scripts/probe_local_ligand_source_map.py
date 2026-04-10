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
DEFAULT_OUTPUT_PATH = REPO_ROOT / "artifacts" / "status" / "local_ligand_source_map.json"
DEFAULT_ACCESSIONS = ("Q9NZD4", "P00387", "P09105", "Q2TAC2", "Q9UCM0")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _selected_accessions(value: str) -> tuple[str, ...]:
    if not value.strip():
        return DEFAULT_ACCESSIONS
    ordered: dict[str, str] = {}
    for part in value.split(","):
        text = str(part or "").strip()
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def build_local_ligand_source_map_report(
    *,
    accessions: tuple[str, ...],
    storage_root: Path,
    master_pdb_repository_path: Path,
    biolip_path: Path,
    chembl_path: Path,
    bindingdb_index_path: Path,
    alphafold_index_path: Path,
) -> dict[str, Any]:
    payload = build_local_ligand_source_map(
        accessions=accessions,
        storage_root=storage_root,
        master_pdb_repository_path=master_pdb_repository_path,
        biolip_path=biolip_path,
        chembl_path=chembl_path,
        bindingdb_index_path=bindingdb_index_path,
        alphafold_index_path=alphafold_index_path,
    )
    return {
        "schema_id": "proteosphere-local-ligand-source-map-2026-03-23",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "selected_accessions": list(accessions),
        **payload,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Probe local bio-agent-lab datasets for accession-scoped "
            "ligand ingestion lanes."
        )
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
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_local_ligand_source_map_report(
        accessions=_selected_accessions(args.accessions),
        storage_root=args.storage_root,
        master_pdb_repository_path=args.master_pdb_repository,
        biolip_path=args.biolip,
        chembl_path=args.chembl,
        bindingdb_index_path=args.bindingdb_index,
        alphafold_index_path=args.alphafold_index,
    )
    _write_json(args.output, payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Local ligand source map exported: "
            f"entries={payload['entry_count']} accessions={len(payload['selected_accessions'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

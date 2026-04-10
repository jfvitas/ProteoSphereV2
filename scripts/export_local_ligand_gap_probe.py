from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.acquire.local_ligand_gap_probe import (  # noqa: E402
    DEFAULT_ACCESSIONS,
    probe_local_ligand_gap_candidates,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORAGE_ROOT = Path(r"C:\Users\jfvit\Documents\bio-agent-lab")
DEFAULT_RAW_ROOT = REPO_ROOT / "data" / "raw"
DEFAULT_LOCAL_REGISTRY_PATH = DEFAULT_RAW_ROOT / "local_registry_runs" / "LATEST.json"
DEFAULT_MASTER_PDB_REPOSITORY = DEFAULT_STORAGE_ROOT / "master_pdb_repository.csv"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "artifacts" / "status" / "local_ligand_gap_probe.json"
DEFAULT_MARKDOWN_PATH = REPO_ROOT / "docs" / "reports" / "local_ligand_gap_probe.md"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
        text = str(part or "").strip().upper()
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def build_local_ligand_gap_probe_report(
    *,
    accessions: tuple[str, ...],
    storage_root: Path,
    raw_root: Path,
    local_registry_path: Path,
    master_pdb_repository_path: Path | None = None,
) -> dict[str, Any]:
    local_registry_summary = _read_json(local_registry_path)
    if not isinstance(local_registry_summary, dict):
        raise TypeError("local registry summary must be a JSON object")
    payload = probe_local_ligand_gap_candidates(
        accessions=accessions,
        local_registry_summary=local_registry_summary,
        storage_root=storage_root,
        raw_root=raw_root,
        master_pdb_repository_path=master_pdb_repository_path,
    )
    return {
        "report_type": "local_ligand_gap_probe",
        "schema_id": "proteosphere-local-ligand-gap-probe-2026-03-23",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "storage_root": str(storage_root),
        "raw_root": str(raw_root),
        "local_registry_path": str(local_registry_path),
        "master_pdb_repository_path": (
            str(master_pdb_repository_path)
            if master_pdb_repository_path is not None
            else str(DEFAULT_MASTER_PDB_REPOSITORY)
        ),
        **payload,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("classification_counts") or {}
    entries = payload.get("entries") or []
    lines = [
        "# Local Ligand Gap Probe",
        "",
        f"- Generated at: `{payload.get('generated_at')}`",
        f"- Storage root: `{payload.get('storage_root')}`",
        f"- Raw root: `{payload.get('raw_root')}`",
        f"- Local registry: `{payload.get('local_registry_path')}`",
        f"- Classification counts: `{summary}`",
        "",
        "## Results",
        "",
        "| Accession | Classification | Best next source | Best next action |",
        "| --- | --- | --- | --- |",
    ]
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        lines.append(
            "| "
            + f"`{entry.get('accession')}` | "
            + f"`{entry.get('classification')}` | "
            + f"`{entry.get('best_next_source') or 'none'}` | "
            + f"{entry.get('best_next_action')} |"
        )
    lines.extend(["", "## Evidence", ""])
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        evidence = entry.get("evidence") if isinstance(entry.get("evidence"), dict) else {}
        bridge_value = evidence.get("structure_bridge")
        alphafold_value = evidence.get("alphafold_raw")
        bindingdb_value = evidence.get("bindingdb_raw")
        rcsb_pdbe_value = evidence.get("rcsb_pdbe_raw")
        secondary_value = evidence.get("secondary_context")
        bridge = bridge_value if isinstance(bridge_value, dict) else {}
        alphafold = alphafold_value if isinstance(alphafold_value, dict) else {}
        bindingdb = bindingdb_value if isinstance(bindingdb_value, dict) else {}
        rcsb_pdbe = rcsb_pdbe_value if isinstance(rcsb_pdbe_value, dict) else {}
        secondary = secondary_value if isinstance(secondary_value, dict) else {}
        lines.extend(
            [
                f"### `{entry.get('accession')}`",
                "",
                f"- Classification: `{entry.get('classification')}`",
                f"- Rationale: {entry.get('rationale')}",
                f"- Bridge PDB IDs: `{bridge.get('matched_pdb_ids')}`",
                f"- Bridge concrete paths: `{bridge.get('concrete_paths')}`",
                f"- AlphaFold raw paths: `{alphafold.get('paths')}`",
                (
                    f"- BindingDB raw state: `{bindingdb.get('state')}` "
                    f"(`{bindingdb.get('entry_count')}` entries)"
                ),
                (
                    f"- RCSB-PDBe raw state: `{rcsb_pdbe.get('state')}` "
                    f"(`{rcsb_pdbe.get('best_structure_count')}` hits)"
                ),
                (
                    "- Secondary context: "
                    f"IntAct count `{secondary.get('intact_interactor_count')}`; "
                    f"UniProt present `{secondary.get('uniprot_present')}`"
                ),
                "",
            ]
        )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe local bio-agent-lab sources for ligand-gap rescue candidates."
    )
    parser.add_argument("--accessions", default=",".join(DEFAULT_ACCESSIONS))
    parser.add_argument("--storage-root", type=Path, default=DEFAULT_STORAGE_ROOT)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument(
        "--local-registry",
        type=Path,
        default=DEFAULT_LOCAL_REGISTRY_PATH,
    )
    parser.add_argument(
        "--master-pdb-repository",
        type=Path,
        default=DEFAULT_MASTER_PDB_REPOSITORY,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN_PATH)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_local_ligand_gap_probe_report(
        accessions=_selected_accessions(args.accessions),
        storage_root=args.storage_root,
        raw_root=args.raw_root,
        local_registry_path=args.local_registry,
        master_pdb_repository_path=args.master_pdb_repository,
    )
    _write_json(args.output, payload)
    _write_text(args.markdown, render_markdown(payload))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Local ligand gap probe exported: "
            f"entries={payload['entry_count']} "
            f"rescuable_now={payload['classification_counts']['rescuable_now']} "
            f"requires_extraction={payload['classification_counts']['requires_extraction']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

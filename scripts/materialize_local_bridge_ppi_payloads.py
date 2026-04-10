from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.materialization.local_bridge_ppi_backfill import (  # noqa: E402
    default_interface_root,
    default_master_repository_path,
    default_ppi_source_entry,
    default_structure_root,
    materialize_selected_cohort_bridge_ppi_entries,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COHORT_SLICE_PATH = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "p15_upgraded_cohort_slice.json"
)
DEFAULT_OUTPUT_PATH = REPO_ROOT / "artifacts" / "status" / "local_bridge_ppi_payloads.json"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _cohort_rows(payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    rows = payload.get("rows") or payload.get("selected_rows") or ()
    if not isinstance(rows, list):
        return ()
    return tuple(dict(row) for row in rows if isinstance(row, dict))


def _selected_accessions(value: str) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for accession in (_clean_text(part) for part in value.split(",")):
        if accession:
            ordered.setdefault(accession.casefold(), accession)
    return tuple(ordered.values())


def _selected_accessions_from_rows(rows: tuple[dict[str, Any], ...]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for row in rows:
        accession = _clean_text(row.get("accession"))
        if accession:
            ordered.setdefault(accession.casefold(), accession)
    return tuple(ordered.values())


def build_local_bridge_ppi_payload_report(
    *,
    cohort_slice_path: Path,
    master_repository_path: Path,
    interface_root: Path,
    structure_root: Path,
    selected_accessions: tuple[str, ...] = (),
) -> dict[str, Any]:
    payload = _read_json(cohort_slice_path)
    if not isinstance(payload, dict):
        raise TypeError("cohort slice must be a JSON object")
    rows = _cohort_rows(payload)
    cohort_accessions = _selected_accessions_from_rows(rows)
    effective_accessions = selected_accessions or cohort_accessions
    source_entry = default_ppi_source_entry()
    entries = materialize_selected_cohort_bridge_ppi_entries(
        rows,
        master_repository_path=master_repository_path,
        interface_root=interface_root,
        structure_root=structure_root,
        source_entry=source_entry,
        selected_accessions=effective_accessions,
    )
    resolved_count = sum(1 for entry in entries if entry.status == "resolved")
    unresolved_count = len(entries) - resolved_count
    return {
        "task_id": "local_bridge_ppi_payloads",
        "cohort_slice_path": str(cohort_slice_path),
        "master_repository_path": str(master_repository_path),
        "interface_root": str(interface_root),
        "structure_root": str(structure_root),
        "selected_accessions": list(effective_accessions),
        "selected_row_count": len(rows),
        "entry_count": len(entries),
        "resolved_count": resolved_count,
        "unresolved_count": unresolved_count,
        "entries": [entry.to_dict() for entry in entries],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize conservative local PPI bridge payloads from selected cohort "
            "rows plus the local master repository and interface extracts."
        )
    )
    parser.add_argument("--cohort-slice", type=Path, default=DEFAULT_COHORT_SLICE_PATH)
    parser.add_argument(
        "--master-repository", type=Path, default=default_master_repository_path()
    )
    parser.add_argument("--interface-root", type=Path, default=default_interface_root())
    parser.add_argument("--structure-root", type=Path, default=default_structure_root())
    parser.add_argument("--accessions", default="")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = build_local_bridge_ppi_payload_report(
        cohort_slice_path=args.cohort_slice,
        master_repository_path=args.master_repository,
        interface_root=args.interface_root,
        structure_root=args.structure_root,
        selected_accessions=_selected_accessions(args.accessions),
    )
    _write_json(args.output, report)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "Local bridge-ppi payloads: "
            f"entries={report['entry_count']} resolved={report['resolved_count']} "
            f"unresolved={report['unresolved_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

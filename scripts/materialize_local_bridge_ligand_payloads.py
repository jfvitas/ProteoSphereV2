from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.materialization.local_bridge_ligand_backfill import (  # noqa: E402
    default_bound_object_root,
    default_bound_object_source_entry,
    default_master_repository_path,
    materialize_selected_cohort_bridge_ligand_entries,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COHORT_SLICE_PATH = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "p15_upgraded_cohort_slice.json"
)
DEFAULT_GAP_PROBE_PATH = REPO_ROOT / "artifacts" / "status" / "local_ligand_gap_probe.json"
DEFAULT_OUTPUT_PATH = (
    REPO_ROOT / "artifacts" / "status" / "local_bridge_ligand_payloads.json"
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _cohort_rows(payload: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    rows = payload.get("rows") or ()
    if not isinstance(rows, list):
        return ()
    return tuple(dict(row) for row in rows if isinstance(row, dict))


def _row_accession(row: Mapping[str, Any]) -> str:
    return _clean_text(row.get("accession")).upper()


def _selected_accessions(value: str) -> tuple[str, ...]:
    accessions = tuple(
        text for text in (_clean_text(part) for part in value.split(",")) if text
    )
    ordered: dict[str, str] = {}
    for accession in accessions:
        ordered.setdefault(accession.casefold(), accession)
    return tuple(ordered.values())


def _load_gap_probe_entries(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return {}
    entries = payload.get("entries") or ()
    if not isinstance(entries, list):
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        accession = _clean_text(entry.get("accession")).upper()
        if accession:
            indexed[accession.casefold()] = dict(entry)
    return indexed


def _synthesize_probe_row(entry: Mapping[str, Any]) -> dict[str, Any] | None:
    accession = _clean_text(entry.get("accession")).upper()
    evidence = entry.get("evidence") if isinstance(entry.get("evidence"), dict) else {}
    bridge = evidence.get("structure_bridge") if isinstance(evidence, dict) else {}
    if not accession or not isinstance(bridge, dict):
        return None
    if _clean_text(bridge.get("state")) != "ready_now":
        return None
    pdb_id = _clean_text(bridge.get("best_pdb_id")).upper()
    if not pdb_id:
        matched_pdb_ids = bridge.get("matched_pdb_ids") or ()
        if isinstance(matched_pdb_ids, list) and matched_pdb_ids:
            pdb_id = _clean_text(matched_pdb_ids[0]).upper()
    if not pdb_id:
        return None
    return {
        "accession": accession,
        "canonical_id": f"protein:{accession}",
        "split": None,
        "bridge": {
            "state": "ready_now",
            "bridge_kind": "bridge_only",
            "pdb_id": pdb_id,
            "chain_ids": [],
        },
        "notes": ["synthesized_from_local_ligand_gap_probe"],
    }


def _merge_probe_bridge(
    row: Mapping[str, Any],
    entry: Mapping[str, Any],
) -> dict[str, Any] | None:
    synthesized = _synthesize_probe_row(entry)
    if synthesized is None:
        return None
    merged = dict(row)
    merged["bridge"] = dict(synthesized["bridge"])
    notes = []
    existing_notes = row.get("notes")
    if isinstance(existing_notes, list):
        notes.extend(_clean_text(value) for value in existing_notes if _clean_text(value))
    notes.append("bridge_upgraded_from_local_ligand_gap_probe")
    merged["notes"] = notes
    return merged


def build_local_bridge_ligand_payload_report(
    *,
    cohort_slice_path: Path,
    bound_object_root: Path,
    master_repository_path: Path,
    gap_probe_path: Path,
    selected_accessions: tuple[str, ...] = (),
) -> dict[str, Any]:
    payload = _read_json(cohort_slice_path)
    if not isinstance(payload, dict):
        raise TypeError("cohort slice must be a JSON object")
    rows = list(_cohort_rows(payload))
    cohort_accessions = {_row_accession(row) for row in rows}
    row_by_accession = {
        _row_accession(row).casefold(): index
        for index, row in enumerate(rows)
        if _row_accession(row)
    }
    synthetic_accessions: list[str] = []
    upgraded_accessions: list[str] = []
    if selected_accessions:
        probe_entries = _load_gap_probe_entries(gap_probe_path)
        for accession in selected_accessions:
            accession_key = accession.casefold()
            probe_entry = probe_entries.get(accession_key)
            if probe_entry is None:
                continue
            existing_index = row_by_accession.get(accession_key)
            if existing_index is not None:
                upgraded_row = _merge_probe_bridge(rows[existing_index], probe_entry)
                if upgraded_row is None:
                    continue
                rows[existing_index] = upgraded_row
                upgraded_accessions.append(accession)
                continue
            synthetic_row = _synthesize_probe_row(probe_entry)
            if synthetic_row is None:
                continue
            rows.append(synthetic_row)
            synthetic_accessions.append(accession)
    source_entry = default_bound_object_source_entry()
    entries = materialize_selected_cohort_bridge_ligand_entries(
        rows,
        bound_object_root=bound_object_root,
        source_entry=source_entry,
        master_repository_path=master_repository_path,
    )
    resolved_count = sum(1 for entry in entries if entry.status == "resolved")
    unresolved_count = len(entries) - resolved_count
    return {
        "task_id": "local_bridge_ligand_payloads",
        "cohort_slice_path": str(cohort_slice_path),
        "gap_probe_path": str(gap_probe_path),
        "bound_object_root": str(bound_object_root),
        "master_repository_path": str(master_repository_path),
        "selected_accessions": list(selected_accessions),
        "cohort_accessions": sorted(cohort_accessions),
        "synthetic_accessions": synthetic_accessions,
        "upgraded_accessions": upgraded_accessions,
        "entry_count": len(entries),
        "resolved_count": resolved_count,
        "unresolved_count": unresolved_count,
        "entries": [entry.to_dict() for entry in entries],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize reproducible bridge-ligand payloads from selected cohort "
            "bridge rows plus local bound-object extracts."
        )
    )
    parser.add_argument("--cohort-slice", type=Path, default=DEFAULT_COHORT_SLICE_PATH)
    parser.add_argument("--gap-probe", type=Path, default=DEFAULT_GAP_PROBE_PATH)
    parser.add_argument("--bound-object-root", type=Path, default=default_bound_object_root())
    parser.add_argument("--master-repository", type=Path, default=default_master_repository_path())
    parser.add_argument("--accessions", default="")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)

    report = build_local_bridge_ligand_payload_report(
        cohort_slice_path=args.cohort_slice,
        bound_object_root=args.bound_object_root,
        master_repository_path=args.master_repository,
        gap_probe_path=args.gap_probe,
        selected_accessions=_selected_accessions(args.accessions),
    )
    _write_json(args.output, report)
    print(
        "Local bridge-ligand payloads: "
        f"entries={report['entry_count']} resolved={report['resolved_count']} "
        f"unresolved={report['unresolved_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

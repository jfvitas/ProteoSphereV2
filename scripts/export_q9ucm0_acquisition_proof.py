from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.acquire.bio_agent_lab_imports import (  # noqa: E402
    BioAgentLabImportManifest,
    build_bio_agent_lab_import_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_ROOT = REPO_ROOT / "data" / "raw"
DEFAULT_LOCAL_REGISTRY_RUNS_ROOT = DEFAULT_RAW_ROOT / "local_registry_runs"
DEFAULT_LOCAL_SOURCE_ROOT = Path(r"C:\Users\jfvit\Documents\bio-agent-lab")
DEFAULT_OUTPUT_PATH = REPO_ROOT / "artifacts" / "status" / "q9ucm0_acquisition_proof.json"
DEFAULT_MARKDOWN_PATH = REPO_ROOT / "docs" / "reports" / "q9ucm0_acquisition_proof.md"
DEFAULT_ACCESSION = "Q9UCM0"

LOCAL_SOURCE_GROUPS: dict[str, tuple[str, ...]] = {
    "structure": (
        "uniprot",
        "alphafold_db",
        "raw_rcsb",
        "structures_rcsb",
        "extracted_entry",
        "extracted_interfaces",
    ),
    "ligand": (
        "uniprot",
        "bindingdb",
        "chembl",
        "biolip",
        "extracted_assays",
        "extracted_bound_objects",
    ),
    "ppi": (
        "uniprot",
        "intact",
        "biogrid",
        "string",
        "pdbbind_pp",
        "extracted_interfaces",
    ),
}
DEFAULT_LOCAL_SOURCE_NAMES = tuple(
    dict.fromkeys(name for names in LOCAL_SOURCE_GROUPS.values() for name in names)
)
NEXT_ACQUISITION_ACTIONS = (
    "AlphaFold DB explicit accession probe",
    "RCSB/PDBe fresh best-structures re-probe",
    "BioGRID guarded procurement first wave",
    "STRING guarded procurement first wave",
    "BindingDB / ChEMBL accession probe",
)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any] | list[Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing input: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _find_latest_snapshot_dir(root: Path, accession: str) -> Path | None:
    if not root.exists():
        return None
    candidates = [
        path
        for path in root.iterdir()
        if path.is_dir() and (path / accession).exists()
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.name.casefold())[-1]


def _normalize_accession_values(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        values = (values,)
    ordered: dict[str, str] = {}
    for value in values:
        text = str(value or "").strip()
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _source_group(source_name: str) -> str:
    normalized = source_name.casefold()
    for group_name, source_names in LOCAL_SOURCE_GROUPS.items():
        if normalized in {item.casefold() for item in source_names}:
            return group_name
    return "other"


def _source_summary(
    source_name: str,
    manifest: BioAgentLabImportManifest,
    *,
    accession: str,
) -> dict[str, Any]:
    source = manifest.get_source(source_name)
    if source is None:
        return {
            "source_name": source_name,
            "source_group": _source_group(source_name),
            "category": "missing_source",
            "status": "missing",
            "candidate_roots": [],
            "present_roots": [],
            "missing_roots": [],
            "join_keys": [],
            "contains_accession": False,
            "notes": ["source not present in the provided manifest"],
        }

    join_keys = list(source.join_keys)
    contains_accession = accession.casefold() in {join_key.casefold() for join_key in join_keys}
    return {
        "source_name": source.source_name,
        "source_group": _source_group(source.source_name),
        "category": source.category,
        "status": source.status,
        "candidate_roots": list(source.candidate_roots),
        "present_roots": list(source.present_roots),
        "missing_roots": list(source.missing_roots),
        "join_keys": join_keys,
        "contains_accession": contains_accession,
        "notes": list(source.notes),
    }


def _load_latest_local_registry_run(
    local_registry_runs_root: Path,
    *,
    accession: str,
) -> dict[str, Any]:
    summary_path = local_registry_runs_root / "LATEST.json"
    summary = _read_json(summary_path)
    if not isinstance(summary, dict):
        raise ValueError(f"expected object in {summary_path}")
    stamp = str(summary.get("stamp") or "").strip()
    import_manifest_path = (
        local_registry_runs_root.parent / "local_registry" / stamp / "import_manifest.json"
    )
    import_manifest = _read_json(import_manifest_path)
    if not isinstance(import_manifest, dict):
        raise ValueError(f"expected object in {import_manifest_path}")

    join_key_index = (
        import_manifest.get("join_key_index")
        if isinstance(import_manifest.get("join_key_index"), dict)
        else {}
    )
    accession_key = accession.casefold()
    q9ucm0_source_names = [
        str(source_name)
        for source_name in join_key_index.get(accession, [])
        if str(source_name).strip()
    ]
    if not q9ucm0_source_names:
        imported_sources = [
            item
            for item in import_manifest.get("imported_sources") or []
            if isinstance(item, dict)
        ]
        q9ucm0_source_names = [
            str(item.get("source_name"))
            for item in imported_sources
            if accession_key
            in {str(join_key).casefold() for join_key in item.get("join_keys") or []}
        ]
    q9ucm0_source_names = list(dict.fromkeys(name for name in q9ucm0_source_names if name))
    sources_payload = import_manifest.get("sources") or []
    source_count = int(
        import_manifest.get("source_count")
        or len(sources_payload)
        or len(import_manifest.get("imported_sources") or [])
    )
    q9ucm0_source_names_by_group = {
        group_name: [
            source_name
            for source_name in q9ucm0_source_names
            if _source_group(source_name) == group_name
        ]
        for group_name in LOCAL_SOURCE_GROUPS
    }
    return {
        "summary_path": str(summary_path),
        "import_manifest_path": str(import_manifest_path),
        "stamp": stamp,
        "selected_source_count": int(summary.get("selected_source_count") or 0),
        "imported_source_count": source_count,
        "q9ucm0_source_names": q9ucm0_source_names,
        "q9ucm0_source_names_by_group": q9ucm0_source_names_by_group,
    }


def _structure_snapshot(raw_root: Path, accession: str) -> dict[str, Any]:
    source_root = raw_root / "rcsb_pdbe"
    snapshot_dir = _find_latest_snapshot_dir(source_root, accession)
    snapshot_path = (
        snapshot_dir / accession / f"{accession}.best_structures.json"
        if snapshot_dir is not None
        else source_root / accession / f"{accession}.best_structures.json"
    )
    payload = _read_json(snapshot_path) if snapshot_path.exists() else []
    if isinstance(payload, list):
        targets = [str(item) for item in payload if str(item).strip()]
        return {
            "source_name": "rcsb_pdbe",
            "snapshot_dir": str(snapshot_dir) if snapshot_dir is not None else "",
            "snapshot_path": str(snapshot_path),
            "exists": snapshot_path.exists(),
            "state": "empty" if not targets else "non_empty",
            "record_count": len(payload),
            "targets": targets,
            "finding": (
                "empty best-structures list"
                if not targets
                else "candidate structure target(s) present"
            ),
        }
    if isinstance(payload, dict):
        targets = [
            str(item)
            for item in _normalize_accession_values(
                payload.get("best_structures") or payload.get("content") or payload.values()
            )
        ]
        return {
            "source_name": "rcsb_pdbe",
            "snapshot_dir": str(snapshot_dir) if snapshot_dir is not None else "",
            "snapshot_path": str(snapshot_path),
            "exists": snapshot_path.exists(),
            "state": "empty" if not targets else "non_empty",
            "record_count": len(targets),
            "targets": targets,
            "finding": (
                "empty best-structures object"
                if not targets
                else "candidate structure target(s) present"
            ),
        }
    return {
        "source_name": "rcsb_pdbe",
        "snapshot_dir": str(snapshot_dir) if snapshot_dir is not None else "",
        "snapshot_path": str(snapshot_path),
        "exists": snapshot_path.exists(),
        "state": "missing",
        "record_count": 0,
        "targets": [],
        "finding": "unparseable best-structures payload",
    }


def _ligand_snapshot(raw_root: Path, accession: str) -> dict[str, Any]:
    source_root = raw_root / "bindingdb"
    snapshot_dir = _find_latest_snapshot_dir(source_root, accession)
    snapshot_path = (
        snapshot_dir / accession / f"{accession}.bindingdb.json"
        if snapshot_dir is not None
        else source_root / accession / f"{accession}.bindingdb.json"
    )
    payload = _read_json(snapshot_path) if snapshot_path.exists() else {}
    response = payload.get("getLindsByUniprotResponse") if isinstance(payload, dict) else {}
    if not isinstance(response, dict):
        response = {}
    alternatives = _normalize_accession_values(response.get("bdb.alternative"))
    affinities = response.get("bdb.affinities") or []
    hit_count = int(response.get("bdb.hit") or 0)
    return {
        "source_name": "bindingdb",
        "snapshot_dir": str(snapshot_dir) if snapshot_dir is not None else "",
        "snapshot_path": str(snapshot_path),
        "exists": snapshot_path.exists(),
        "state": "empty" if hit_count == 0 and not affinities else "non_empty",
        "hit_count": hit_count,
        "primary_accession": str(response.get("bdb.primary") or ""),
        "uniprot_length": str(response.get("bdb.uniprot_length") or ""),
        "alternative_accessions": list(alternatives),
        "affinity_count": len(affinities),
        "finding": (
            "bindingdb hit count is zero"
            if hit_count == 0
            else "bindingdb accession hit present"
        ),
    }


def _extract_uniprot_ids(field: str) -> tuple[str, ...]:
    hits: list[str] = []
    for item in field.split("|"):
        text = item.strip()
        if text.lower().startswith("uniprotkb:"):
            hits.append(text.split(":", 1)[1].strip())
    return _normalize_accession_values(hits)


def _ppi_snapshot(raw_root: Path, accession: str) -> dict[str, Any]:
    source_root = raw_root / "intact"
    snapshot_dir = _find_latest_snapshot_dir(source_root, accession)
    interactor_path = (
        snapshot_dir / accession / f"{accession}.interactor.json"
        if snapshot_dir is not None
        else source_root / accession / f"{accession}.interactor.json"
    )
    tab_path = (
        snapshot_dir / accession / f"{accession}.psicquic.tab25.txt"
        if snapshot_dir is not None
        else source_root / accession / f"{accession}.psicquic.tab25.txt"
    )

    interactor_payload = _read_json(interactor_path) if interactor_path.exists() else {}
    if not isinstance(interactor_payload, dict):
        interactor_payload = {}
    content = [
        item for item in interactor_payload.get("content") or [] if isinstance(item, dict)
    ]
    preferred_identifiers = _normalize_accession_values(
        item.get("interactorPreferredIdentifier") for item in content
    )
    direct_interactor_count = sum(
        1
        for item in content
        if str(item.get("interactorPreferredIdentifier") or "").casefold() == accession.casefold()
    )

    tab_lines = (
        tab_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if tab_path.exists()
        else []
    )
    direct_rows: list[str] = []
    alias_only_rows: list[str] = []
    partner_accessions: set[str] = set()
    accession_token = f"uniprotkb:{accession}".casefold()
    for line in tab_lines:
        if accession.casefold() not in line.casefold():
            continue
        columns = line.split("\t")
        if len(columns) < 2:
            continue
        participant_a = columns[0].casefold()
        participant_b = columns[1].casefold()
        if accession_token in participant_a or accession_token in participant_b:
            direct_rows.append(line)
        else:
            alias_only_rows.append(line)
            partner_accessions.update(_extract_uniprot_ids(columns[0]))
            partner_accessions.update(_extract_uniprot_ids(columns[1]))

    if direct_interactor_count > 0 or direct_rows:
        state = "direct"
    elif alias_only_rows or preferred_identifiers:
        state = "alias_only"
    else:
        state = "missing"

    return {
        "source_name": "intact",
        "snapshot_dir": str(snapshot_dir) if snapshot_dir is not None else "",
        "snapshot_path": str(interactor_path),
        "interactor_path": str(interactor_path),
        "tab_path": str(tab_path),
        "exists": interactor_path.exists() and tab_path.exists(),
        "state": state,
        "interactor_count": len(content),
        "direct_interactor_count": direct_interactor_count,
        "preferred_identifiers": list(preferred_identifiers),
        "direct_row_count": len(direct_rows),
        "alias_only_row_count": len(alias_only_rows),
        "partner_accessions": sorted(partner_accessions),
        "finding": (
            "IntAct resolves to a partner accession and alias-only row(s)"
            if state == "alias_only"
            else (
                "IntAct direct canonical rows present"
                if state == "direct"
                else "IntAct snapshot absent"
            )
        ),
        "alias_only_rows": alias_only_rows[:3],
    }


def _build_registered_local_sources(
    local_source_manifest: BioAgentLabImportManifest,
    *,
    accession: str,
) -> dict[str, dict[str, Any]]:
    source_names = list(DEFAULT_LOCAL_SOURCE_NAMES)
    for source in local_source_manifest.sources:
        if source.source_name not in source_names:
            source_names.append(source.source_name)
    return {
        source_name: _source_summary(source_name, local_source_manifest, accession=accession)
        for source_name in source_names
    }


def _modality_checked_sources(
    registered_local_sources: dict[str, dict[str, Any]],
    modality: str,
) -> dict[str, dict[str, Any]]:
    return {
        source_name: registered_local_sources[source_name]
        for source_name in LOCAL_SOURCE_GROUPS[modality]
        if source_name in registered_local_sources
    }


def build_q9ucm0_acquisition_proof(
    *,
    raw_root: Path = DEFAULT_RAW_ROOT,
    local_registry_runs_root: Path = DEFAULT_LOCAL_REGISTRY_RUNS_ROOT,
    local_source_root: Path = DEFAULT_LOCAL_SOURCE_ROOT,
    local_source_manifest: BioAgentLabImportManifest | None = None,
) -> dict[str, Any]:
    accession = DEFAULT_ACCESSION
    resolved_local_source_manifest = (
        local_source_manifest
        if local_source_manifest is not None
        else build_bio_agent_lab_import_manifest(
            local_source_root,
            source_names=DEFAULT_LOCAL_SOURCE_NAMES,
        )
    )
    registered_local_sources = _build_registered_local_sources(
        resolved_local_source_manifest,
        accession=accession,
    )
    local_registry_run = _load_latest_local_registry_run(
        local_registry_runs_root,
        accession=accession,
    )
    online_snapshots = {
        "structure": _structure_snapshot(raw_root, accession),
        "ligand": _ligand_snapshot(raw_root, accession),
        "ppi": _ppi_snapshot(raw_root, accession),
    }
    q9ucm0_join_key_sources = local_registry_run["q9ucm0_source_names"]
    q9ucm0_join_key_sources_by_group = local_registry_run["q9ucm0_source_names_by_group"]
    modalities: dict[str, dict[str, Any]] = {}
    for modality in ("structure", "ligand", "ppi"):
        checked_sources = _modality_checked_sources(registered_local_sources, modality)
        modality_sources = {
            source_name: summary
            for source_name, summary in checked_sources.items()
            if source_name != "uniprot"
        }
        local_join_key_sources = [
            source_name
            for source_name, summary in modality_sources.items()
            if summary["contains_accession"]
        ]
        absent_reasons = []
        if online_snapshots[modality]["state"] in {"empty", "missing"}:
            absent_reasons.append(
                f"current online {modality} snapshot is {online_snapshots[modality]['state']}"
            )
        if modality == "structure":
            absent_reasons.append(
                "local registry maps Q9UCM0 only to uniprot, not to a structure source"
            )
        elif modality == "ligand":
            absent_reasons.append("local registry does not expose a Q9UCM0 ligand join key")
        else:
            absent_reasons.append("local registry does not expose a Q9UCM0 PPI join key")
        if local_join_key_sources:
            absent_reasons.append(
                "registered local "
                f"{modality} sources with Q9UCM0 join keys: {local_join_key_sources}"
            )
        else:
            absent_reasons.append(
                "registered local "
                f"{modality} sources checked: {', '.join(modality_sources)}"
            )

        modalities[modality] = {
            "state": "missing",
            "raw_snapshot": online_snapshots[modality],
            "checked_sources": checked_sources,
            "q9ucm0_join_key_sources": local_join_key_sources,
            "absent_reasons": absent_reasons,
            "next_acquisition_action": NEXT_ACQUISITION_ACTIONS[
                {"structure": 0, "ligand": 4, "ppi": 2}[modality]
            ],
        }

    current_truth = {modality: "missing" for modality in ("structure", "ligand", "ppi")}
    return {
        "report_type": "q9ucm0_acquisition_proof",
        "schema_id": "proteosphere-q9ucm0-acquisition-proof-2026-03-23",
        "accession": accession,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "status": "unresolved_requires_new_acquisition",
        "reference_state": {
            "sequence": "present",
            "sequence_source_names": q9ucm0_join_key_sources,
        },
        "current_truth": current_truth,
        "checked": {
            "online_raw_snapshots": online_snapshots,
            "local_registry_run": local_registry_run,
            "registered_local_sources": registered_local_sources,
        },
        "modalities": modalities,
        "next_acquisition_actions": list(NEXT_ACQUISITION_ACTIONS),
        "proof_summary": {
            "checked_online_snapshot_count": len(online_snapshots),
            "registered_local_source_count": len(registered_local_sources),
            "q9ucm0_join_key_sources": q9ucm0_join_key_sources,
            "q9ucm0_join_key_sources_by_group": q9ucm0_join_key_sources_by_group,
            "absent_modalities": [
                modality for modality, state in current_truth.items() if state == "missing"
            ],
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    modalities = payload.get("modalities") if isinstance(payload.get("modalities"), dict) else {}
    checked = payload.get("checked") if isinstance(payload.get("checked"), dict) else {}
    online_snapshots = (
        checked.get("online_raw_snapshots")
        if isinstance(checked.get("online_raw_snapshots"), dict)
        else {}
    )
    registered_local_sources = (
        checked.get("registered_local_sources")
        if isinstance(checked.get("registered_local_sources"), dict)
        else {}
    )
    lines = [
        "# Q9UCM0 Acquisition Proof",
        "",
        f"- Generated at: `{payload.get('generated_at')}`",
        f"- Status: `{payload.get('status')}`",
        f"- Truth: `structure={payload.get('current_truth', {}).get('structure')}`, "
        f"`ligand={payload.get('current_truth', {}).get('ligand')}`, "
        f"`ppi={payload.get('current_truth', {}).get('ppi')}`",
        f"- Sequence reference: `{payload.get('reference_state', {}).get('sequence')}` "
        f"via `{payload.get('reference_state', {}).get('sequence_source_names')}`",
        "",
        "## What Was Checked",
        "",
        f"- Online raw snapshots: {', '.join(f'`{key}`' for key in online_snapshots) or 'none'}",
        (
            "- Registered local sources: "
            f"{', '.join(f'`{key}`' for key in registered_local_sources) or 'none'}"
        ),
        f"- Local registry run: `{checked.get('local_registry_run', {}).get('summary_path')}`",
        f"- Import manifest: `{checked.get('local_registry_run', {}).get('import_manifest_path')}`",
        "",
        "## Summary",
        "",
        "| Modality | Online snapshot | Registered local sources | State | Next action |",
        "| --- | --- | --- | --- | --- |",
    ]
    for modality in ("structure", "ligand", "ppi"):
        modality_payload = modalities.get(modality, {})
        snapshot = modality_payload.get("raw_snapshot", {})
        checked_sources = modality_payload.get("checked_sources", {})
        source_bits = []
        for source_name, summary in checked_sources.items():
            status = summary.get("status")
            join_keys = ", ".join(summary.get("join_keys") or []) or "none"
            source_bits.append(f"{source_name}:{status} [{join_keys}]")
        lines.append(
            "| {modality} | {snapshot} | {sources} | {state} | {action} |".format(
                modality=modality,
                snapshot=snapshot.get("finding") or snapshot.get("state"),
                sources="; ".join(source_bits),
                state=modality_payload.get("state"),
                action=modality_payload.get("next_acquisition_action"),
            )
        )
    lines.extend(
        [
            "",
            "## Findings",
            "",
        ]
    )
    for modality in ("structure", "ligand", "ppi"):
        modality_payload = modalities.get(modality, {})
        snapshot = modality_payload.get("raw_snapshot", {})
        lines.extend(
            [
                f"### `{modality}:Q9UCM0`",
                "",
                f"- Online raw snapshot: `{snapshot.get('snapshot_path')}`",
                f"- Online state: `{snapshot.get('state')}`",
                f"- Absent: {', '.join(modality_payload.get('absent_reasons') or [])}",
                f"- Next acquisition action: `{modality_payload.get('next_acquisition_action')}`",
                "",
                "Checked local sources:",
            ]
        )
        checked_sources = modality_payload.get("checked_sources") or {}
        for source_name, summary in checked_sources.items():
            lines.append(
                f"- `{source_name}` -> `{summary.get('status')}`; "
                f"join_keys={summary.get('join_keys')}; "
                f"contains_Q9UCM0=`{summary.get('contains_accession')}`"
            )
        lines.append("")
    lines.extend(
        [
            "## Next Acquisition Order",
            "",
        ]
    )
    for action in payload.get("next_acquisition_actions") or ():
        lines.append(f"- `{action}`")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export the Q9UCM0 acquisition proof bundle.")
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument(
        "--local-registry-runs-root",
        type=Path,
        default=DEFAULT_LOCAL_REGISTRY_RUNS_ROOT,
    )
    parser.add_argument("--local-source-root", type=Path, default=DEFAULT_LOCAL_SOURCE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN_PATH)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_q9ucm0_acquisition_proof(
        raw_root=args.raw_root,
        local_registry_runs_root=args.local_registry_runs_root,
        local_source_root=args.local_source_root,
    )
    _write_json(args.output, payload)
    _write_text(args.markdown, render_markdown(payload))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Q9UCM0 acquisition proof exported: "
            f"status={payload['status']} sequence={payload['reference_state']['sequence']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

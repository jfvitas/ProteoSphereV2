from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DASHBOARD_PATH = REPO_ROOT / "artifacts" / "status" / "packet_deficit_dashboard.json"
DEFAULT_LOCAL_LIGAND_SOURCE_MAP_PATH = (
    REPO_ROOT / "artifacts" / "status" / "local_ligand_source_map.json"
)
DEFAULT_OUTPUT_PATH = REPO_ROOT / "artifacts" / "status" / "packet_gap_execution_plan.json"
DEFAULT_MARKDOWN_PATH = REPO_ROOT / "docs" / "reports" / "packet_gap_execution_plan.md"
DEFAULT_EVIDENCE_ARTIFACT_PATHS = (
    REPO_ROOT / "docs" / "reports" / "p26_packet_deficit_source_hunt.md",
    REPO_ROOT / "docs" / "reports" / "p26_selected_packet_materialization.md",
    REPO_ROOT / "docs" / "reports" / "p26_packet_deficit_rerun.md",
    REPO_ROOT / "docs" / "reports" / "p00387_local_chembl_rescue.md",
    REPO_ROOT / "docs" / "reports" / "p27_no_local_rescue_acquisition_priority_p09105_q2tac2.md",
    REPO_ROOT / "docs" / "reports" / "p27_fresh_acquisition_shortlist_p09105_q2tac2.md",
    REPO_ROOT / "docs" / "reports" / "q9ucm0_acquisition_brief_2026_03_23.md",
    REPO_ROOT / "docs" / "reports" / "q9ucm0_acquisition_checklist_2026_03_23.md",
    REPO_ROOT / "docs" / "reports" / "q9ucm0_structure_gap_local_investigation_2026_03_23.md",
)

PLAN_ORDER = (
    "ligand:Q9NZD4",
    "ligand:P00387",
    "ligand:P09105",
    "ligand:Q2TAC2",
    "structure:Q9UCM0",
    "ppi:Q9UCM0",
    "ligand:Q9UCM0",
)

PLAN_BLUEPRINTS: dict[str, dict[str, Any]] = {
    "ligand:Q9NZD4": {
        "work_class": "quick_local_extraction",
        "confidence": "high",
        "next_action": (
            "Mine the existing 1Z8U bound_objects lane first, then validate the entry, "
            "raw, and CIF lineage before promoting any accession-clean small-molecule rows."
        ),
        "expected_effect": (
            "fastest path to a truthful local ligand extraction because the bridge-backed "
            "structure assets already exist on disk"
        ),
        "uncertainty": (
            "The local bridge is already present, but the extraction still has to prove "
            "that the surviving rows are accession-clean and really ligand-bearing."
        ),
        "stop_condition": (
            "Stop if the extracted rows collapse to partner-chain noise, solvent, or any "
            "non-target structure annotation."
        ),
        "evidence_artifacts": (
            REPO_ROOT / "docs" / "reports" / "p26_packet_deficit_source_hunt.md",
            REPO_ROOT / "docs" / "reports" / "p26_selected_packet_materialization.md",
            REPO_ROOT / "docs" / "reports" / "packet_deficit_dashboard.md",
        ),
    },
    "ligand:P00387": {
        "work_class": "quick_local_extraction",
        "confidence": "medium",
        "next_action": (
            "Use the local ChEMBL lane first, then cross-check BioLiP support and the local "
            "ligand source map before deciding whether the result stays ligand-only."
        ),
        "expected_effect": (
            "recover ligand or assay evidence without claiming a structure rescue"
        ),
        "uncertainty": (
            "There is local assay evidence, but the direct 1UMK structure bridge is absent "
            "locally, so this may stay a ligand-only recovery."
        ),
        "stop_condition": (
            "Stop if the accession-scoped extraction cannot be made clean without inventing "
            "a missing local structure bridge."
        ),
        "evidence_artifacts": (
            REPO_ROOT / "artifacts" / "status" / "local_ligand_source_map.json",
            REPO_ROOT / "docs" / "reports" / "p00387_local_chembl_rescue.md",
            REPO_ROOT / "docs" / "reports" / "p26_packet_deficit_source_hunt.md",
        ),
    },
    "ligand:P09105": {
        "work_class": "local_bulk_assay_extraction",
        "confidence": "medium",
        "next_action": (
            "Query BindingDB first, then ChEMBL, for accession-clean assay rows and retain "
            "the row-level provenance for any survivor."
        ),
        "expected_effect": (
            "best chance to recover ligand supervision from local bulk assay sources"
        ),
        "uncertainty": (
            "No local bridge or BioLiP support was found, so this is a heavier extraction "
            "lane rather than a quick rescue."
        ),
        "stop_condition": (
            "Stop closed if both BindingDB and ChEMBL remain empty or only produce "
            "ambiguous text matches."
        ),
        "evidence_artifacts": (
            REPO_ROOT / "artifacts" / "status" / "local_ligand_source_map.json",
            REPO_ROOT
            / "docs"
            / "reports"
            / ("p27_no_local_rescue_acquisition_priority_" "p09105_q2tac2.md"),
            REPO_ROOT / "docs" / "reports" / "p27_fresh_acquisition_shortlist_p09105_q2tac2.md",
        ),
    },
    "ligand:Q2TAC2": {
        "work_class": "local_bulk_assay_extraction",
        "confidence": "medium",
        "next_action": (
            "Run the same BindingDB-first, then ChEMBL accession extraction as P09105, "
            "keeping the result fail-closed on ambiguous joins."
        ),
        "expected_effect": (
            "recover ligand supervision from local bulk assay sources if the accession is "
            "present there"
        ),
        "uncertainty": (
            "The current local source map only shows structure-companion context, not a true "
            "local ligand rescue lane."
        ),
        "stop_condition": (
            "Stop if the extraction only finds companion structure context or no accession-"
            "clean ligand rows."
        ),
        "evidence_artifacts": (
            REPO_ROOT / "artifacts" / "status" / "local_ligand_source_map.json",
            REPO_ROOT
            / "docs"
            / "reports"
            / ("p27_no_local_rescue_acquisition_priority_" "p09105_q2tac2.md"),
            REPO_ROOT / "docs" / "reports" / "p27_fresh_acquisition_shortlist_p09105_q2tac2.md",
        ),
    },
    "structure:Q9UCM0": {
        "work_class": "fresh_acquisition_blocker",
        "confidence": "high",
        "next_action": (
            "Run the AlphaFold DB explicit accession probe first, then the RCSB/PDBe "
            "best-structures re-probe if that fails."
        ),
        "expected_effect": (
            "either confirm a new structure payload or truthfully close the structure gap"
        ),
        "uncertainty": (
            "The local registry, local AlphaFold archive, and mirrored RCSB/PDBe probes all "
            "stay empty for Q9UCM0 structure."
        ),
        "stop_condition": (
            "Stop if no accession-scoped AlphaFold or RCSB/PDBe target is returned."
        ),
        "evidence_artifacts": (
            REPO_ROOT
            / "docs"
            / "reports"
            / ("q9ucm0_structure_gap_local_investigation_" "2026_03_23.md"),
            REPO_ROOT / "docs" / "reports" / "q9ucm0_acquisition_brief_2026_03_23.md",
            REPO_ROOT / "docs" / "reports" / "q9ucm0_acquisition_checklist_2026_03_23.md",
        ),
    },
    "ppi:Q9UCM0": {
        "work_class": "fresh_acquisition_blocker",
        "confidence": "high",
        "next_action": (
            "Run guarded BioGRID procurement first, then STRING if BioGRID remains empty; "
            "treat alias-only IntAct noise as non-rescue evidence."
        ),
        "expected_effect": (
            "either recover a canonical curated PPI lane or close the PPI gap without guesswork"
        ),
        "uncertainty": (
            "Current curated PPI evidence is reachable-empty or alias-only, so this needs "
            "fresh curated acquisition rather than reinterpretation."
        ),
        "stop_condition": (
            "Stop if neither BioGRID nor STRING yields a direct accession-mappable pair."
        ),
        "evidence_artifacts": (
            REPO_ROOT / "docs" / "reports" / "q9ucm0_acquisition_brief_2026_03_23.md",
            REPO_ROOT / "docs" / "reports" / "q9ucm0_acquisition_checklist_2026_03_23.md",
        ),
    },
    "ligand:Q9UCM0": {
        "work_class": "fresh_acquisition_blocker",
        "confidence": "high",
        "next_action": (
            "Treat ligand acquisition as downstream of the structure and PPI probes; only "
            "then try BindingDB and ChEMBL accession extraction."
        ),
        "expected_effect": (
            "either recover a truthful ligand lane or confirm that no local fallback exists"
        ),
        "uncertainty": (
            "No truthful local ligand fallback exists yet, and any rescue claim would overstate "
            "the current evidence."
        ),
        "stop_condition": (
            "Stop if structure or curated PPI acquisition does not produce a usable entry to "
            "anchor ligand extraction."
        ),
        "evidence_artifacts": (
            REPO_ROOT / "docs" / "reports" / "q9ucm0_acquisition_brief_2026_03_23.md",
            REPO_ROOT / "docs" / "reports" / "q9ucm0_acquisition_checklist_2026_03_23.md",
            REPO_ROOT
            / "docs"
            / "reports"
            / ("q9ucm0_structure_gap_local_investigation_" "2026_03_23.md"),
        ),
    },
}


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
    if isinstance(values, dict):
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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _markdown_path(path: Path) -> str:
    return f"/{path.resolve().as_posix()}"


def _load_dashboard(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise TypeError("packet deficit dashboard must be a JSON object")
    return payload


def _load_local_ligand_source_map(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return {}
    entries = payload.get("entries") or ()
    if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        accession = _clean_text(entry.get("accession"))
        if accession:
            mapped[accession.casefold()] = dict(entry)
    return mapped


def _resolve_evidence_artifacts(paths: Sequence[Path]) -> tuple[Path, ...]:
    resolved: list[Path] = []
    for path in paths:
        if path.exists():
            resolved.append(path)
    return tuple(resolved)


def _source_fix_lookup(
    dashboard: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for item in _iter_values(dashboard.get("source_fix_candidates") or ()):
        if not isinstance(item, dict):
            continue
        source_ref = _clean_text(item.get("source_ref"))
        if source_ref:
            lookup[source_ref.casefold()] = dict(item)
    return lookup


def _packet_accession(item: dict[str, Any]) -> str:
    accessions = _dedupe_text(item.get("packet_accessions") or ())
    if accessions:
        return accessions[0]
    source_ref = _clean_text(item.get("source_ref"))
    return source_ref.partition(":")[2].upper()


def _normalize_artifact_paths(paths: Sequence[Path]) -> list[str]:
    return [_markdown_path(path) for path in paths]


def _plan_item(
    *,
    source_ref: str,
    candidate: dict[str, Any],
    local_ligand_state: dict[str, Any] | None,
) -> dict[str, Any]:
    blueprint = PLAN_BLUEPRINTS[source_ref]
    packet_ids = list(_dedupe_text(candidate.get("packet_ids") or ()))
    packet_accessions = list(_dedupe_text(candidate.get("packet_accessions") or ()))
    accession = _packet_accession(candidate)
    if not packet_accessions and accession:
        packet_accessions = [accession]

    item: dict[str, Any] = {
        "source_ref": source_ref,
        "modality": source_ref.partition(":")[0],
        "accession": accession,
        "packet_ids": packet_ids,
        "packet_accessions": packet_accessions,
        "missing_modality_count": int(candidate.get("missing_modality_count") or 0),
        "affected_packet_count": int(candidate.get("affected_packet_count") or 0),
        "missing_modalities": list(_dedupe_text(candidate.get("missing_modalities") or ())),
        "work_class": blueprint["work_class"],
        "confidence": blueprint["confidence"],
        "next_action": blueprint["next_action"],
        "expected_effect": blueprint["expected_effect"],
        "uncertainty": blueprint["uncertainty"],
        "stop_condition": blueprint["stop_condition"],
        "evidence_artifacts": _normalize_artifact_paths(blueprint["evidence_artifacts"]),
        "evidence_notes": [],
    }

    if local_ligand_state is not None:
        item["local_ligand_source_map"] = {
            "classification": _clean_text(local_ligand_state.get("classification")),
            "recommended_next_action": _clean_text(
                local_ligand_state.get("recommended_next_action")
            ),
            "chembl_hit_count": len(_iter_values(local_ligand_state.get("chembl_hits") or ())),
            "bindingdb_hit_count": len(
                _iter_values(local_ligand_state.get("bindingdb_hits") or ())
            ),
            "biolip_pdb_ids": list(_dedupe_text(local_ligand_state.get("biolip_pdb_ids") or ())),
            "alphafold_hit_count": len(
                _iter_values(local_ligand_state.get("alphafold_hits") or ())
            ),
        }

    if source_ref == "ligand:P00387" and local_ligand_state is not None:
        item["evidence_notes"] = [
            "Local source map marks the accession as bulk_assay_actionable.",
            "The rescue brief reports CHEMBL2146 with 93 activities.",
        ]
    elif source_ref == "ligand:P09105" and local_ligand_state is not None:
        item["evidence_notes"] = [
            "Local source map only shows structure-companion context.",
            "No local ligand rescue lane was identified in the source map.",
        ]
    elif source_ref == "ligand:Q2TAC2" and local_ligand_state is not None:
        item["evidence_notes"] = [
            "Local source map only shows structure-companion context.",
            "No local ligand rescue lane was identified in the source map.",
        ]
    elif source_ref == "structure:Q9UCM0":
        item["evidence_notes"] = [
            "Local structure investigation found no AlphaFold, RCSB, or master-catalog rescue.",
        ]
    elif source_ref == "ppi:Q9UCM0":
        item["evidence_notes"] = [
            "Current curated PPI evidence is reachable-empty or alias-only.",
        ]
    elif source_ref == "ligand:Q9UCM0":
        item["evidence_notes"] = [
            "Ligand acquisition should wait until the structure and PPI probes have run.",
        ]
    elif source_ref == "ligand:Q9NZD4":
        item["evidence_notes"] = [
            (
                "The source hunt already points to local 1Z8U bound_objects as the "
                "quickest rescue lane."
            ),
        ]

    return item


def build_packet_gap_execution_plan(
    *,
    dashboard_path: Path = DEFAULT_DASHBOARD_PATH,
    local_ligand_source_map_path: Path = DEFAULT_LOCAL_LIGAND_SOURCE_MAP_PATH,
    evidence_artifact_paths: Sequence[Path] | None = None,
) -> dict[str, Any]:
    dashboard = _load_dashboard(dashboard_path)
    source_fix_lookup = _source_fix_lookup(dashboard)
    local_ligand_source_map = _load_local_ligand_source_map(local_ligand_source_map_path)
    requested_evidence_paths = tuple(evidence_artifact_paths or DEFAULT_EVIDENCE_ARTIFACT_PATHS)
    consumed_evidence_paths = _resolve_evidence_artifacts(requested_evidence_paths)
    support_artifacts = (
        dashboard_path,
        local_ligand_source_map_path,
    )
    consumed_support_artifacts = tuple(
        path for path in support_artifacts if path.exists()
    ) + consumed_evidence_paths

    ranked_items: list[dict[str, Any]] = []
    for rank, source_ref in enumerate(PLAN_ORDER, start=1):
        candidate = source_fix_lookup.get(source_ref.casefold())
        if candidate is None:
            continue
        accession = _packet_accession(candidate)
        local_ligand_state = local_ligand_source_map.get(accession.casefold())
        ranked_items.append(
            {
                "rank": rank,
                **_plan_item(
                    source_ref=source_ref,
                    candidate=candidate,
                    local_ligand_state=local_ligand_state,
                ),
            }
        )

    work_class_counts = Counter(item["work_class"] for item in ranked_items)
    return {
        "schema_id": "proteosphere-packet-gap-execution-plan-2026-03-23",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "status": "planning_only",
        "dashboard_path": _markdown_path(dashboard_path),
        "local_ligand_source_map_path": _markdown_path(local_ligand_source_map_path),
        "dashboard_generated_at": _clean_text(dashboard.get("generated_at")),
        "dashboard_summary": dict(dashboard.get("summary") or {}),
        "requested_support_artifacts": _normalize_artifact_paths(support_artifacts),
        "consumed_support_artifacts": _normalize_artifact_paths(consumed_support_artifacts),
        "requested_evidence_artifacts": _normalize_artifact_paths(requested_evidence_paths),
        "consumed_evidence_artifacts": _normalize_artifact_paths(consumed_evidence_paths),
        "summary": {
            "ranked_source_ref_count": len(ranked_items),
            "quick_local_extraction_count": int(work_class_counts.get("quick_local_extraction", 0)),
            "local_bulk_assay_extraction_count": int(
                work_class_counts.get("local_bulk_assay_extraction", 0)
            ),
            "fresh_acquisition_blocker_count": int(
                work_class_counts.get("fresh_acquisition_blocker", 0)
            ),
            "dashboard_source_fix_candidate_count": len(
                _iter_values(dashboard.get("source_fix_candidates") or ())
            ),
            "dashboard_packet_count": int(
                (dashboard.get("summary") or {}).get("packet_count") or 0
            ),
            "dashboard_packet_deficit_count": int(
                (dashboard.get("summary") or {}).get("packet_deficit_count") or 0
            ),
            "dashboard_total_missing_modality_count": int(
                (dashboard.get("summary") or {}).get("total_missing_modality_count") or 0
            ),
        },
        "ranked_items": ranked_items,
        "truth_boundary_note": (
            "This is a planning-grade execution order built from the current packet deficit "
            "dashboard plus the available rescue/proof artifacts. It distinguishes local "
            "extraction from fresh acquisition and does not promote any missing modality on its "
            "own."
        ),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Packet Gap Execution Plan",
        "",
        f"- Generated at: `{payload.get('generated_at')}`",
        f"- Status: `{payload.get('status')}`",
        f"- Dashboard: `{payload.get('dashboard_path')}`",
        f"- Local ligand source map: `{payload.get('local_ligand_source_map_path')}`",
        f"- Dashboard generated at: `{payload.get('dashboard_generated_at')}`",
        f"- Ranked source refs: `{summary.get('ranked_source_ref_count')}`",
        f"- Quick local extraction: `{summary.get('quick_local_extraction_count')}`",
        f"- Local bulk assay extraction: `{summary.get('local_bulk_assay_extraction_count')}`",
        f"- Fresh acquisition blockers: `{summary.get('fresh_acquisition_blocker_count')}`",
        "",
        "## Ranked Plan",
        "",
    ]
    for item in payload.get("ranked_items") or []:
        if not isinstance(item, dict):
            continue
        evidence = ", ".join(
            f"[{Path(path).name}]({path})" for path in item.get("evidence_artifacts") or ()
        ) or "none"
        notes = "; ".join(item.get("evidence_notes") or ()) or "none"
        packet_ids = ", ".join(item.get("packet_ids") or ()) or "none"
        missing_modalities = ", ".join(item.get("missing_modalities") or ()) or "none"
        lines.append(
            "- "
            + f"`{item.get('rank')}` "
            + f"`{item.get('source_ref')}` "
            + f"class=`{item.get('work_class')}` "
            + f"confidence=`{item.get('confidence')}` "
            + f"packets=`{packet_ids}` "
            + f"missing=`{missing_modalities}` "
            + f"action=`{item.get('next_action')}` "
            + f"uncertainty=`{item.get('uncertainty')}` "
            + f"evidence=`{evidence}` "
            + f"notes=`{notes}`"
        )
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            f"- {payload.get('truth_boundary_note')}",
        ]
    )
    return "\n".join(lines)

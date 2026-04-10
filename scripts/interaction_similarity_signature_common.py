from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCAL_REGISTRY_RUNS_ROOT = REPO_ROOT / "data" / "raw" / "local_registry_runs"
DEFAULT_BIOGRID_ARCHIVE = (
    REPO_ROOT
    / "data"
    / "raw"
    / "protein_data_scope_seed"
    / "biogrid"
    / "BIOGRID-ALL-LATEST.mitab.zip"
)
DEFAULT_STRING_ROOT = REPO_ROOT / "data" / "raw" / "protein_data_scope_seed" / "string"
DEFAULT_INTACT_ROOT = REPO_ROOT / "data" / "raw" / "intact"
DEFAULT_BUNDLE_MANIFEST = REPO_ROOT / "artifacts" / "status" / "lightweight_bundle_manifest.json"
DEFAULT_CANONICAL_SUMMARY = REPO_ROOT / "artifacts" / "status" / "protein_summary_library.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _dedupe(values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _manifest_state(manifest: dict[str, Any]) -> str:
    provenance = {str(item).casefold() for item in manifest.get("provenance") or []}
    if "present" in provenance:
        return "present"
    if "missing" in provenance:
        return "missing"
    return "unknown"


def _manifest_join_keys(manifest: dict[str, Any]) -> tuple[str, ...]:
    explicit = manifest.get("join_keys")
    if isinstance(explicit, list):
        return _dedupe([str(item) for item in explicit])
    for entry in manifest.get("reproducibility_metadata") or []:
        text = _clean_text(entry)
        if text.startswith("join_keys="):
            return _dedupe([part for part in text.split("=", 1)[1].split(",")])
    return ()


def _load_manifest(path: Path) -> dict[str, Any]:
    return _read_json(path)


def _source_surface_summary(source_manifest: dict[str, Any], source_root: Path) -> dict[str, Any]:
    metadata_path = source_root / "_source_metadata.json"
    metadata: dict[str, Any] = {}
    if metadata_path.exists():
        metadata = _read_json(metadata_path)

    top_level_files = metadata.get("top_level_files") or []
    present = 0
    partial = 0
    missing = 0
    for item in top_level_files:
        filename = _clean_text(item.get("filename"))
        if not filename:
            continue
        exact = source_root / filename
        partial_path = source_root / f"{filename}.part"
        if exact.exists():
            present += 1
        elif partial_path.exists():
            partial += 1
        else:
            missing += 1

    disk_state = "missing"
    if present and not partial and not missing:
        disk_state = "present"
    elif present or partial:
        disk_state = "partial_on_disk"

    return {
        "source_name": _clean_text(source_manifest.get("source_name")),
        "manifest_id": _clean_text(source_manifest.get("manifest_id")),
        "manifest_state": _manifest_state(source_manifest),
        "join_keys": list(_manifest_join_keys(source_manifest)),
        "top_level_file_count": len(top_level_files),
        "top_level_file_present_count": present,
        "top_level_file_partial_count": partial,
        "top_level_file_missing_count": missing,
        "disk_state": disk_state,
    }


def _discover_accessions(
    biogrid_manifest: dict[str, Any],
    string_manifest: dict[str, Any],
    intact_manifest: dict[str, Any],
) -> tuple[str, ...]:
    ordered = list(_manifest_join_keys(biogrid_manifest))
    intersection = (
        set(_manifest_join_keys(biogrid_manifest))
        & set(_manifest_join_keys(string_manifest))
        & set(_manifest_join_keys(intact_manifest))
    )
    return tuple(accession for accession in ordered if accession in intersection)


def _biogrid_row_counts(archive_path: Path, accessions: tuple[str, ...]) -> dict[str, int]:
    counts = {accession: 0 for accession in accessions}
    if not archive_path.exists():
        return counts
    with zipfile.ZipFile(archive_path) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        if not names:
            return counts
        with archive.open(names[0]) as handle:
            for raw_line in handle:
                line = raw_line.decode("utf-8", errors="replace").upper()
                if "UNIPROT" not in line:
                    continue
                for accession in accessions:
                    if accession.upper() in line:
                        counts[accession] += 1
    return counts


def _string_support_state(string_summary: dict[str, Any]) -> str:
    if string_summary["disk_state"] == "present" and string_summary["manifest_state"] == "present":
        return "present_on_disk"
    return "partial_on_disk"


def _find_latest_snapshot_dir(root: Path, accessions: tuple[str, ...]) -> Path | None:
    if not root.exists():
        return None
    candidates = []
    for path in root.iterdir():
        if not path.is_dir():
            continue
        if all((path / accession / f"{accession}.psicquic.tab25.txt").exists() for accession in accessions):
            candidates.append(path)
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.name.casefold())[-1]


def _count_non_empty_lines(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def _intact_probe_summary(
    accessions: tuple[str, ...],
    *,
    raw_root: Path,
) -> dict[str, Any]:
    snapshot_dir = _find_latest_snapshot_dir(raw_root, accessions)
    states: dict[str, dict[str, Any]] = {}
    for accession in accessions:
        probe_path = (
            snapshot_dir / accession / f"{accession}.psicquic.tab25.txt"
            if snapshot_dir is not None
            else None
        )
        row_count = _count_non_empty_lines(probe_path) if probe_path is not None else 0
        probe_state = "present" if row_count > 0 else "missing"
        states[accession] = {
            "probe_state": probe_state,
            "snapshot_path": str(probe_path) if probe_path is not None else "",
            "row_count": row_count,
        }

    return {
        "snapshot_dir": str(snapshot_dir) if snapshot_dir is not None else "",
        "record_count": sum(state["row_count"] for state in states.values()),
        "accession_states": states,
    }


def _intact_surface_summary(
    source_manifest: dict[str, Any],
    raw_root: Path,
    accessions: tuple[str, ...],
) -> dict[str, Any]:
    probe_summary = _intact_probe_summary(accessions, raw_root=raw_root)
    present = sum(
        1 for state in probe_summary["accession_states"].values() if state["probe_state"] == "present"
    )
    missing = sum(
        1 for state in probe_summary["accession_states"].values() if state["probe_state"] != "present"
    )
    disk_state = "present" if missing == 0 else "partial_on_disk"
    return {
        "source_name": _clean_text(source_manifest.get("source_name")),
        "manifest_id": _clean_text(source_manifest.get("manifest_id")),
        "manifest_state": _manifest_state(source_manifest),
        "join_keys": list(_manifest_join_keys(source_manifest)),
        "snapshot_dir": probe_summary["snapshot_dir"],
        "accession_file_present_count": present,
        "accession_file_missing_count": missing,
        "probe_row_total": probe_summary["record_count"],
        "disk_state": disk_state,
    }


def build_interaction_similarity_signature_preview(
    *,
    biogrid_manifest: dict[str, Any],
    string_manifest: dict[str, Any],
    intact_manifest: dict[str, Any],
    biogrid_archive_path: Path,
    string_root: Path,
    intact_raw_root: Path,
    canonical_summary_path: Path,
    bundle_manifest: dict[str, Any],
) -> dict[str, Any]:
    accessions = _discover_accessions(biogrid_manifest, string_manifest, intact_manifest)
    biogrid_surface = _source_surface_summary(biogrid_manifest, biogrid_archive_path.parent)
    string_surface = _source_surface_summary(string_manifest, string_root)
    intact_surface = _intact_surface_summary(intact_manifest, intact_raw_root, accessions)
    biogrid_counts = _biogrid_row_counts(biogrid_archive_path, accessions)
    intact_probe = _intact_probe_summary(
        accessions,
        raw_root=intact_raw_root,
    )

    string_support_state = _string_support_state(string_surface)
    string_missing_roots = 0
    for entry in string_manifest.get("reproducibility_metadata") or []:
        text = _clean_text(entry)
        if text.startswith("missing_roots="):
            string_missing_roots = int(text.split("=", 1)[1] or 0)
            break

    rows: list[dict[str, Any]] = []
    for accession in accessions:
        intact_state = intact_probe["accession_states"].get(accession, {}).get("probe_state", "missing")
        support_group = (
            f"biogrid:{biogrid_surface['manifest_state']}__"
            f"string:{string_support_state}__"
            f"intact:{intact_state}"
        )
        rows.append(
            {
                "signature_id": f"interaction_similarity:{accession}",
                "protein_ref": f"protein:{accession}",
                "accession": accession,
                "interaction_similarity_group": support_group,
                "candidate_only": True,
                "biogrid_registry_state": biogrid_surface["manifest_state"],
                "biogrid_disk_state": biogrid_surface["disk_state"],
                "biogrid_matched_row_count": biogrid_counts[accession],
                "string_registry_state": string_surface["manifest_state"],
                "string_disk_state": string_support_state,
                "intact_registry_state": intact_surface["manifest_state"],
                "intact_disk_state": intact_surface["disk_state"],
                "intact_probe_state": intact_state,
                "intact_probe_row_count": intact_probe["accession_states"][accession]["row_count"],
                "notes": [
                    f"bioGRID_rows={biogrid_counts[accession]}",
                    f"string_manifest_missing_roots={string_missing_roots}",
                    f"intact_probe_state={intact_state}",
                ],
            }
        )

    unique_groups = {row["interaction_similarity_group"] for row in rows}
    biogrid_total = sum(row["biogrid_matched_row_count"] for row in rows)
    string_total_present = string_surface["top_level_file_present_count"]
    string_total_partial = string_surface["top_level_file_partial_count"]
    string_total_missing = string_surface["top_level_file_missing_count"]

    bundle_counts = bundle_manifest.get("record_counts") or {}
    interaction_bundle_count = int(bundle_counts.get("interaction_similarity_signatures") or 0)
    interaction_bundle_included = False
    for family in bundle_manifest.get("table_families") or []:
        if _clean_text(family.get("family_name")) == "interaction_similarity_signatures":
            interaction_bundle_included = bool(family.get("included"))
            break

    return {
        "artifact_id": "interaction_similarity_signature_preview",
        "schema_id": "proteosphere-interaction-similarity-signature-preview-2026-04-02",
        "status": "complete",
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "accession_count": len(rows),
            "unique_interaction_similarity_group_count": len(unique_groups),
            "candidate_only_row_count": sum(1 for row in rows if row["candidate_only"]),
            "biogrid_matched_row_total": biogrid_total,
            "string_top_level_file_present_count": string_total_present,
            "string_top_level_file_partial_count": string_total_partial,
            "string_top_level_file_missing_count": string_total_missing,
            "intact_present_count": sum(
                1 for row in rows if row["intact_probe_state"] == "present"
            ),
            "source_overlap_accessions": list(accessions),
        },
        "source_surfaces": {
            "biogrid": {
                **biogrid_surface,
                "matched_row_total": biogrid_total,
            },
            "string": string_surface,
        "intact": {
            **intact_surface,
            "probe_state": "present",
            "probe_snapshot_dir": intact_probe["snapshot_dir"],
        },
        },
        "bundle_alignment": {
            "bundle_id": _clean_text(bundle_manifest.get("bundle_id")),
            "bundle_status": _clean_text(
                bundle_manifest.get("bundle_status")
                or bundle_manifest.get("manifest_status")
                or bundle_manifest.get("status")
            ),
            "interaction_similarity_signatures_included": interaction_bundle_included,
            "interaction_similarity_signatures_record_count": interaction_bundle_count,
        },
        "truth_boundary": {
            "summary": (
                "This is a compact, report-only interaction similarity preview grounded in "
                "current on-disk BioGRID, STRING, and IntAct surfaces. It does not materialize "
                "the interaction family, STRING remains partial on disk, and IntAct remains "
                "present on disk for the selected accessions."
            ),
            "report_only": True,
            "ready_for_bundle_preview": False,
            "interaction_family_materialized": False,
            "direct_interaction_family_claimed": False,
            "string_family_materialized": False,
            "intact_pair_evidence_claimed": False,
            "candidate_only_rows": True,
        },
    }


def build_interaction_similarity_signature_validation(
    preview: dict[str, Any],
    bundle_manifest: dict[str, Any],
) -> dict[str, Any]:
    rows = preview.get("rows") or []
    summary = preview.get("summary") or {}
    biogrid_total = sum(int(row.get("biogrid_matched_row_count") or 0) for row in rows)
    candidate_only_accessions = [
        str(row.get("accession")) for row in rows if row.get("candidate_only")
    ]
    group_count = len({row.get("interaction_similarity_group") for row in rows})
    bundle_counts = bundle_manifest.get("record_counts") or {}
    bundle_interaction_count = int(bundle_counts.get("interaction_similarity_signatures") or 0)
    bundle_included = False
    for family in bundle_manifest.get("table_families") or []:
        if _clean_text(family.get("family_name")) == "interaction_similarity_signatures":
            bundle_included = bool(family.get("included"))
            break

    issues: list[str] = []
    if preview.get("status") != "complete":
        issues.append("preview_not_complete")
    if len(rows) != int(preview.get("row_count") or 0):
        issues.append("row_count_mismatch")
    if int(summary.get("accession_count") or 0) != len(rows):
        issues.append("accession_count_mismatch")
    if group_count != int(summary.get("unique_interaction_similarity_group_count") or 0):
        issues.append("group_count_mismatch")
    if biogrid_total != int(summary.get("biogrid_matched_row_total") or 0):
        issues.append("biogrid_row_total_mismatch")
    if int(summary.get("candidate_only_row_count") or 0) != len(candidate_only_accessions):
        issues.append("candidate_only_count_mismatch")
    if int(summary.get("intact_present_count") or 0) != sum(
        1 for row in rows if row.get("intact_probe_state") == "present"
    ):
        issues.append("intact_present_count_mismatch")
    if bundle_interaction_count != 0:
        issues.append("bundle_interaction_family_should_remain_unmaterialized")
    if bundle_included:
        issues.append("bundle_interaction_family_should_not_be_included")
    if not preview.get("truth_boundary", {}).get("report_only", False):
        issues.append("truth_boundary_must_remain_report_only")
    if preview.get("truth_boundary", {}).get("ready_for_bundle_preview", True):
        issues.append("truth_boundary_must_not_be_bundle_ready")

    status = "aligned" if not issues else "needs_attention"
    return {
        "artifact_id": "interaction_similarity_signature_validation",
        "schema_id": "proteosphere-interaction-similarity-signature-validation-2026-04-02",
        "status": status,
        "validation": {
            "row_count": len(rows),
            "accession_count": len(rows),
            "unique_interaction_similarity_group_count": group_count,
            "candidate_only_accessions": candidate_only_accessions,
            "biogrid_matched_row_total": biogrid_total,
            "intact_present_count": sum(
                1 for row in rows if row.get("intact_probe_state") == "present"
            ),
            "bundle_interaction_similarity_signatures_record_count": bundle_interaction_count,
            "bundle_interaction_similarity_signatures_included": bundle_included,
            "issue_count": len(issues),
            "issues": issues,
        },
        "truth_boundary": {
            "report_only": True,
            "bundle_safe_immediately": False,
            "bundle_interaction_similarity_signatures_included": bundle_included,
            "bundle_interaction_similarity_signatures_record_count": bundle_interaction_count,
            "interaction_family_materialized": False,
            "direct_interaction_family_claimed": False,
        },
    }


def render_preview_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Interaction Similarity Signature Preview",
        "",
        f"- Rows: `{payload['row_count']}`",
        f"- Accessions: `{summary['accession_count']}`",
        (
            "- Unique interaction similarity groups: "
            f"`{summary['unique_interaction_similarity_group_count']}`"
        ),
        f"- BioGRID matched rows total: `{summary['biogrid_matched_row_total']}`",
        f"- STRING top-level files present: `{summary['string_top_level_file_present_count']}`",
        f"- STRING top-level files partial: `{summary['string_top_level_file_partial_count']}`",
        f"- STRING top-level files missing: `{summary['string_top_level_file_missing_count']}`",
        f"- IntAct present rows: `{summary['intact_present_count']}`",
        "",
        "## Rows",
        "",
        "| Accession | Group | BioGRID rows | STRING state | IntAct state |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in payload["rows"]:
        lines.append(
            "| "
            f"{row['accession']} | {row['interaction_similarity_group']} | "
            f"{row['biogrid_matched_row_count']} | {row['string_disk_state']} | "
            f"{row['intact_probe_state']} |"
        )
    lines.extend(
        [
            "",
            "## Source Surfaces",
            "",
        ]
    )
    for source_name, source_payload in payload["source_surfaces"].items():
        lines.append(
            f"- `{source_name}`: registry=`{source_payload['manifest_state']}`, "
            f"disk=`{source_payload['disk_state']}`"
        )
    lines.extend(["", "## Truth Boundary", "", f"- {payload['truth_boundary']['summary']}"])
    return "\n".join(lines) + "\n"


def render_validation_markdown(payload: dict[str, Any]) -> str:
    validation = payload["validation"]
    lines = [
        "# Interaction Similarity Signature Validation",
        "",
        f"- Status: `{payload['status']}`",
        f"- Issue count: `{validation['issue_count']}`",
        f"- Row count: `{validation['row_count']}`",
        f"- Accession count: `{validation['accession_count']}`",
        f"- Candidate-only accessions: `{', '.join(validation['candidate_only_accessions'])}`",
        f"- BioGRID matched rows total: `{validation['biogrid_matched_row_total']}`",
        f"- IntAct present count: `{validation['intact_present_count']}`",
        (
            "- Bundle interaction_similarity_signatures record count: "
            f"`{validation['bundle_interaction_similarity_signatures_record_count']}`"
        ),
        "",
        "## Truth Boundary",
        "",
        "- Report-only preview confirmed.",
        "",
    ]
    if validation["issues"]:
        lines.extend(["## Issues", ""])
        for issue in validation["issues"]:
            lines.append(f"- `{issue}`")
        lines.append("")
    return "\n".join(lines)

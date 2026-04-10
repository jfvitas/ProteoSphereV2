from __future__ import annotations

import csv
import gzip
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ACCESSION_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "summary_library_operator_accession_matrix.json"
)
DEFAULT_SABIO_ACCESSION_SEED = (
    REPO_ROOT / "data" / "raw" / "protein_data_scope_seed" / "sabio_rk" / "sabio_uniprotkb_acs.txt"
)
DEFAULT_SABIO_SEARCH_FIELDS = (
    REPO_ROOT / "data" / "raw" / "protein_data_scope_seed" / "sabio_rk" / "sabio_search_fields.xml"
)
DEFAULT_PDB_CHAIN_ENZYME = (
    REPO_ROOT / "data" / "raw" / "protein_data_scope_seed" / "sifts" / "pdb_chain_enzyme.tsv.gz"
)
DEFAULT_OPERATOR_DASHBOARD = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "operator_dashboard.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "kinetics_enzyme_support_preview.json"
)
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "kinetics_enzyme_support_preview.md"
DEFAULT_VALIDATION_JSON = (
    REPO_ROOT / "artifacts" / "status" / "kinetics_enzyme_support_validation.json"
)
DEFAULT_VALIDATION_MD = (
    REPO_ROOT / "docs" / "reports" / "kinetics_enzyme_support_validation.md"
)

SABIO_QUERY_SCOPE_FIELD = "UniProtKB_AC"
SABIO_SOURCE = "sabio_rk"
PDB_CHAIN_ENZYME_SOURCE = "pdb_chain_enzyme"
SUPPORTED_STATUS = "supported_now"
UNSUPPORTED_STATUS = "no_local_accession_resolved_support"
POLICY_LABEL = "preview_bundle_safe_non_governing"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_accession_seed(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _search_field_present(search_fields_xml: str) -> bool:
    try:
        root = ET.fromstring(search_fields_xml)
    except ET.ParseError:
        return False
    return any(
        (element.text or "").strip() == SABIO_QUERY_SCOPE_FIELD
        for element in root.findall(".//field")
    )


def _read_pdb_chain_enzyme_support(path: Path) -> tuple[int, dict[str, list[dict[str, str]]]]:
    row_count = 0
    evidence_map: dict[str, list[dict[str, str]]] = {}
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        _ = next(handle)
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            row_count += 1
            accession = str(row.get("ACCESSION") or "").strip()
            if not accession:
                continue
            evidence_map.setdefault(accession, []).append(
                {
                    "pdb": str(row.get("PDB") or "").strip(),
                    "chain": str(row.get("CHAIN") or "").strip(),
                    "ec_number": str(row.get("EC_NUMBER") or "").strip(),
                }
            )
    return row_count, evidence_map


def _support_sources(
    accession: str,
    sabio_accession_seed: set[str],
    pdb_chain_enzyme_support: dict[str, list[dict[str, str]]],
) -> list[str]:
    sources: list[str] = []
    if accession in sabio_accession_seed:
        sources.append(SABIO_SOURCE)
    if accession in pdb_chain_enzyme_support:
        sources.append(PDB_CHAIN_ENZYME_SOURCE)
    return sources


def _support_status(sources: list[str]) -> str:
    return SUPPORTED_STATUS if sources else UNSUPPORTED_STATUS


def _blocker_for_support_sources(sources: list[str]) -> str:
    if sources:
        return "local_accession_resolved_support_only_no_live_kinetics_verified"
    return "no_local_accession_resolved_support"


def _next_stage_for_support_sources(sources: list[str]) -> str:
    if sources:
        return "verify_accession_scoped_kinetics_export"
    return "hold_for_local_kinetics_acquisition"


def _truth_note_for_support_sources(sources: list[str]) -> str:
    if not sources:
        return (
            "No local SABIO-RK or PDB-chain-enzyme accession-resolved support overlaps "
            "this accession yet."
        )
    if sources == [SABIO_SOURCE]:
        return (
            "Local SABIO-RK accession seed overlaps this accession, but live kinetics "
            "remain unverified."
        )
    if sources == [PDB_CHAIN_ENZYME_SOURCE]:
        return (
            "Local PDB-chain-enzyme accession mapping overlaps this accession, but live "
            "kinetics remain unverified."
        )
    return (
        "Local SABIO-RK seed and local PDB-chain-enzyme mapping both overlap this "
        "accession, but live kinetics remain unverified."
    )


def build_kinetics_enzyme_support_preview(
    accession_matrix: dict[str, Any],
    sabio_accession_seed_text: str,
    sabio_search_fields_xml: str,
    pdb_chain_enzyme_path: Path,
    operator_dashboard: dict[str, Any],
) -> dict[str, Any]:
    rows = [row for row in accession_matrix.get("rows") or [] if isinstance(row, dict)]
    sabio_accessions = [
        accession
        for accession in (
            line.strip() for line in sabio_accession_seed_text.splitlines()
        )
        if accession
    ]
    sabio_accession_seed = set(sabio_accessions)
    pdb_chain_enzyme_row_count, pdb_chain_enzyme_support = _read_pdb_chain_enzyme_support(
        pdb_chain_enzyme_path
    )
    supported_rows: list[dict[str, Any]] = []
    unsupported_rows: list[dict[str, Any]] = []

    for row in rows:
        accession = str(row.get("accession") or "").strip()
        if not accession:
            continue

        support_sources = _support_sources(
            accession, sabio_accession_seed, pdb_chain_enzyme_support
        )
        sabio_match = accession in sabio_accession_seed
        enzyme_matches = pdb_chain_enzyme_support.get(accession) or []
        support_status = _support_status(support_sources)
        support_row = {
            "accession": accession,
            "protein_ref": row.get("protein_ref") or f"protein:{accession}",
            "protein_name": row.get("protein_name"),
            "protein_summary_present": bool(row.get("protein_summary_present")),
            "variant_count": int(row.get("variant_count") or 0),
            "structure_unit_count": int(row.get("structure_unit_count") or 0),
            "motif_reference_count": int(row.get("motif_reference_count") or 0),
            "domain_reference_count": int(row.get("domain_reference_count") or 0),
            "pathway_reference_count": int(row.get("pathway_reference_count") or 0),
            "provenance_pointer_count": int(row.get("provenance_pointer_count") or 0),
            "family_presence": row.get("family_presence") or {
                "protein": bool(row.get("protein_summary_present")),
                "protein_variant": bool(row.get("variant_count")),
                "structure_unit": bool(row.get("structure_unit_count")),
            },
            "operator_priority": row.get("operator_priority"),
            "bundle_projection": row.get("bundle_projection"),
            "sabio_seed_match": sabio_match,
            "sabio_support_status": (
                SUPPORTED_STATUS if sabio_match else UNSUPPORTED_STATUS
            ),
            "enzyme_chain_match_count": len(enzyme_matches),
            "enzyme_support_status": (
                SUPPORTED_STATUS if enzyme_matches else UNSUPPORTED_STATUS
            ),
            "support_sources": support_sources,
            "support_source_count": len(support_sources),
            "kinetics_support_status": support_status,
            "current_blocker": _blocker_for_support_sources(support_sources),
            "next_truthful_stage": _next_stage_for_support_sources(support_sources),
            "source_provenance_refs": [
                "summary_library_operator_accession_matrix",
                "sabio_uniprotkb_acs",
                "pdb_chain_enzyme",
                "sabio_search_fields",
                "operator_dashboard",
            ],
            "truth_note": _truth_note_for_support_sources(support_sources),
        }
        if support_sources:
            supported_rows.append(support_row)
        else:
            unsupported_rows.append(support_row)

    supported_accessions = [row["accession"] for row in supported_rows]
    unsupported_accessions = [row["accession"] for row in unsupported_rows]
    sabio_supported_accessions = [
        row["accession"] for row in supported_rows if row["sabio_seed_match"]
    ]
    enzyme_supported_accessions = [
        row["accession"] for row in supported_rows if row["enzyme_chain_match_count"] > 0
    ]
    query_scope_present = _search_field_present(sabio_search_fields_xml)
    dashboard_status = str(operator_dashboard.get("dashboard_status") or "")
    operator_go_no_go = str(operator_dashboard.get("operator_go_no_go") or "")
    ready_for_next_wave = bool(
        (operator_dashboard.get("benchmark_summary") or {}).get("ready_for_next_wave")
    )
    return {
        "artifact_id": "kinetics_enzyme_support_preview",
        "schema_id": "proteosphere-kinetics-enzyme-support-preview-2026-04-02",
        "status": "complete",
        "surface_kind": "accession_level_kinetics_enzyme_support_matrix",
        "policy_family": "kinetics_support_compact_family",
        "policy_label": POLICY_LABEL,
        "row_count": len(rows),
        "rows": supported_rows + unsupported_rows,
        "summary": {
            "matrix_accession_count": len(rows),
            "sabio_seed_accession_count": len(sabio_accessions),
            "pdb_chain_enzyme_row_count": pdb_chain_enzyme_row_count,
            "pdb_chain_enzyme_accession_count": len(pdb_chain_enzyme_support),
            "supported_accession_count": len(supported_rows),
            "unsupported_accession_count": len(unsupported_rows),
            "supported_accessions": supported_accessions,
            "unsupported_accessions": unsupported_accessions,
            "sabio_supported_accession_count": len(sabio_supported_accessions),
            "enzyme_supported_accession_count": len(enzyme_supported_accessions),
            "dual_supported_accession_count": sum(
                1 for row in supported_rows if row["support_source_count"] == 2
            ),
            "single_source_supported_accession_count": sum(
                1 for row in supported_rows if row["support_source_count"] == 1
            ),
            "supported_high_priority_accession_count": sum(
                1 for row in supported_rows if row.get("operator_priority") == "high"
            ),
            "supported_medium_priority_accession_count": sum(
                1 for row in supported_rows if row.get("operator_priority") == "medium"
            ),
            "supported_observe_accession_count": sum(
                1 for row in supported_rows if row.get("operator_priority") == "observe"
            ),
            "query_scope_field_present": query_scope_present,
            "live_kinetic_law_verified_count": 0,
            "live_enzyme_activity_verified_count": 0,
            "dashboard_status": dashboard_status,
            "operator_go_no_go": operator_go_no_go,
            "ready_for_next_wave": ready_for_next_wave,
            "support_status_counts": dict(
                sorted(
                    Counter(
                        row["kinetics_support_status"]
                        for row in supported_rows + unsupported_rows
                    ).items()
                )
            ),
        },
        "truth_boundary": {
            "summary": (
                "This is a support-only kinetics/enzyme accession matrix built from the "
                "local SABIO-RK accession seed and local PDB-chain-enzyme mapping. It "
                "does not verify live kinetic-law IDs or enzyme activity, and it does not "
                "change the blocked operator dashboard."
            ),
            "report_only": True,
            "local_source_only": True,
            "live_kinetic_ids_verified": False,
            "live_enzyme_activity_verified": False,
            "dashboard_blocked": dashboard_status == "blocked_on_release_grade_bar",
            "ready_for_operator_preview": True,
            "ready_for_bundle_preview": True,
            "governing_for_split_or_leakage": False,
        },
    }


def build_kinetics_enzyme_support_validation(
    kinetics_enzyme_support_preview: dict[str, Any],
    accession_matrix: dict[str, Any],
    sabio_accession_seed_text: str,
    sabio_search_fields_xml: str,
    pdb_chain_enzyme_path: Path,
    operator_dashboard: dict[str, Any],
) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    rows = [
        row for row in kinetics_enzyme_support_preview.get("rows") or [] if isinstance(row, dict)
    ]
    matrix_rows = [
        row for row in accession_matrix.get("rows") or [] if isinstance(row, dict)
    ]
    sabio_accessions = [
        accession
        for accession in (
            line.strip() for line in sabio_accession_seed_text.splitlines()
        )
        if accession
    ]
    sabio_accession_seed = set(sabio_accessions)
    pdb_chain_enzyme_row_count, pdb_chain_enzyme_support = _read_pdb_chain_enzyme_support(
        pdb_chain_enzyme_path
    )
    expected_supported_accessions = [
        row["accession"]
        for row in matrix_rows
        if row.get("accession") in sabio_accession_seed
        or row.get("accession") in pdb_chain_enzyme_support
    ]
    expected_unsupported_accessions = [
        row["accession"]
        for row in matrix_rows
        if row.get("accession") not in sabio_accession_seed
        and row.get("accession") not in pdb_chain_enzyme_support
    ]
    supported_rows = [
        row for row in rows if row.get("kinetics_support_status") == SUPPORTED_STATUS
    ]
    unsupported_rows = [
        row for row in rows if row.get("kinetics_support_status") == UNSUPPORTED_STATUS
    ]
    supported_accessions = [row["accession"] for row in supported_rows]
    unsupported_accessions = [row["accession"] for row in unsupported_rows]

    if kinetics_enzyme_support_preview.get("row_count") != len(rows):
        issues.append("row_count does not match emitted kinetics/enzyme support rows")
    if len(matrix_rows) != len(rows):
        issues.append("matrix accession count does not match emitted rows")
    if kinetics_enzyme_support_preview.get("summary", {}).get("supported_accession_count") != len(
        supported_rows
    ):
        issues.append("supported_accession_count does not match supported rows")
    if kinetics_enzyme_support_preview.get("summary", {}).get("unsupported_accession_count") != len(
        unsupported_rows
    ):
        issues.append("unsupported_accession_count does not match unsupported rows")
    if (
        kinetics_enzyme_support_preview.get("summary", {}).get("supported_accessions")
        != expected_supported_accessions
    ):
        issues.append("supported_accessions do not match local source overlap")
    if (
        kinetics_enzyme_support_preview.get("summary", {}).get("unsupported_accessions")
        != expected_unsupported_accessions
    ):
        issues.append("unsupported_accessions do not match local source gap")
    if (
        kinetics_enzyme_support_preview.get("summary", {}).get("query_scope_field_present")
        is not True
    ):
        issues.append("SABIO UniProtKB_AC query scope must be present")
    if (
        kinetics_enzyme_support_preview.get("summary", {}).get("dashboard_status")
        != "blocked_on_release_grade_bar"
    ):
        issues.append("operator dashboard status must remain blocked_on_release_grade_bar")
    if kinetics_enzyme_support_preview.get("summary", {}).get("operator_go_no_go") != "no-go":
        issues.append("operator go/no-go must remain no-go")
    if kinetics_enzyme_support_preview.get("policy_label") != POLICY_LABEL:
        issues.append(
            "kinetics support policy_label must remain preview_bundle_safe_non_governing"
        )
    if operator_dashboard.get("dashboard_status") != "blocked_on_release_grade_bar":
        issues.append("dashboard source artifact is no longer blocked_on_release_grade_bar")
    if (operator_dashboard.get("benchmark_summary") or {}).get("ready_for_next_wave") is not True:
        issues.append("benchmark summary is not ready for next wave")
    if not _search_field_present(sabio_search_fields_xml):
        issues.append("UniProtKB_AC search field is missing from SABIO search fields")
    if kinetics_enzyme_support_preview.get("truth_boundary", {}).get("report_only") is not True:
        issues.append("truth boundary must remain report_only")
    if (
        kinetics_enzyme_support_preview.get("truth_boundary", {}).get(
            "ready_for_bundle_preview"
        )
        is not True
    ):
        issues.append("truth boundary must mark kinetics support as preview-bundle-safe")
    if (
        kinetics_enzyme_support_preview.get("truth_boundary", {}).get(
            "governing_for_split_or_leakage"
        )
        is not False
    ):
        issues.append("kinetics support must remain non-governing for split/leakage")
    if (
        kinetics_enzyme_support_preview.get("truth_boundary", {}).get(
            "live_kinetic_ids_verified"
        )
        is not False
    ):
        issues.append("live kinetic-law IDs must remain unverified")
    if (
        kinetics_enzyme_support_preview.get("truth_boundary", {}).get(
            "live_enzyme_activity_verified"
        )
        is not False
    ):
        issues.append("live enzyme activity must remain unverified")
    if (
        kinetics_enzyme_support_preview.get("summary", {}).get("pdb_chain_enzyme_row_count")
        != pdb_chain_enzyme_row_count
    ):
        issues.append("pdb_chain_enzyme_row_count does not match local source")
    if (
        kinetics_enzyme_support_preview.get("summary", {}).get(
            "pdb_chain_enzyme_accession_count"
        )
        != len(pdb_chain_enzyme_support)
    ):
        issues.append("pdb_chain_enzyme_accession_count does not match local source")

    if rows:
        warnings.append(
            "support surface is local-source backed only; "
            "live kinetic-law IDs and enzyme activity remain unverified"
        )

    status = "aligned" if not issues else "attention_needed"
    return {
        "artifact_id": "kinetics_enzyme_support_validation",
        "schema_id": "proteosphere-kinetics-enzyme-support-validation-2026-04-02",
        "status": status,
        "validation": {
            "issue_count": len(issues),
            "warning_count": len(warnings),
            "row_count": len(rows),
            "matrix_accession_count": len(matrix_rows),
            "supported_accession_count": len(supported_rows),
            "unsupported_accession_count": len(unsupported_rows),
            "supported_accessions": supported_accessions,
            "unsupported_accessions": unsupported_accessions,
            "sabio_supported_accession_count": sum(
                1 for row in supported_rows if row.get("sabio_seed_match")
            ),
            "enzyme_supported_accession_count": sum(
                1 for row in supported_rows if row.get("enzyme_chain_match_count") > 0
            ),
            "dual_supported_accession_count": sum(
                1 for row in supported_rows if row.get("support_source_count") == 2
            ),
            "single_source_supported_accession_count": sum(
                1 for row in supported_rows if row.get("support_source_count") == 1
            ),
            "query_scope_field_present": _search_field_present(sabio_search_fields_xml),
            "live_kinetic_law_verified_count": 0,
            "live_enzyme_activity_verified_count": 0,
            "pdb_chain_enzyme_row_count": pdb_chain_enzyme_row_count,
            "pdb_chain_enzyme_accession_count": len(pdb_chain_enzyme_support),
            "dashboard_status": operator_dashboard.get("dashboard_status"),
            "operator_go_no_go": operator_dashboard.get("operator_go_no_go"),
            "issues": issues,
            "warnings": warnings,
        },
        "truth_boundary": {
            "summary": (
                "This validation confirms the kinetics/enzyme support preview is "
                "local-source backed and internally consistent. It does not certify live "
                "kinetic-law IDs or enzyme activity, and it does not change the blocked "
                "operator dashboard."
            ),
            "report_only": True,
            "local_source_only": True,
            "live_kinetic_ids_verified": False,
            "live_enzyme_activity_verified": False,
            "dashboard_blocked": operator_dashboard.get("dashboard_status")
            == "blocked_on_release_grade_bar",
        },
    }


def render_preview_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Kinetics / Enzyme Support Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Surface kind: `{payload['surface_kind']}`",
        f"- Matrix accessions: `{summary['matrix_accession_count']}`",
        f"- SABIO seed accessions: `{summary['sabio_seed_accession_count']}`",
        f"- PDB-chain-enzyme rows: `{summary['pdb_chain_enzyme_row_count']}`",
        f"- PDB-chain-enzyme accessions: `{summary['pdb_chain_enzyme_accession_count']}`",
        f"- Supported accessions: `{summary['supported_accession_count']}`",
        f"- Unsupported accessions: `{summary['unsupported_accession_count']}`",
        f"- Dashboard status: `{summary['dashboard_status']}`",
        f"- Operator go/no-go: `{summary['operator_go_no_go']}`",
        "",
        "## Supported Accessions",
        "",
    ]
    if summary["supported_accessions"]:
        for accession in summary["supported_accessions"]:
            row = next(
                row
                for row in payload["rows"]
                if row["accession"] == accession
                and row["kinetics_support_status"] == SUPPORTED_STATUS
            )
            lines.append(
                f"- `{accession}` - `{row['protein_name']}` via {', '.join(row['support_sources'])}"
            )
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Unsupported Accessions",
            "",
        ]
    )
    if summary["unsupported_accessions"]:
        for accession in summary["unsupported_accessions"]:
            row = next(
                row
                for row in payload["rows"]
                if row["accession"] == accession
                and row["kinetics_support_status"] == UNSUPPORTED_STATUS
            )
            lines.append(f"- `{accession}` - `{row['protein_name']}`")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            payload["truth_boundary"]["summary"],
        ]
    )
    return "\n".join(lines) + "\n"


def render_validation_markdown(payload: dict[str, Any]) -> str:
    validation = payload["validation"]
    lines = [
        "# Kinetics / Enzyme Support Validation",
        "",
        f"- Status: `{payload['status']}`",
        f"- Issue count: `{validation['issue_count']}`",
        f"- Warning count: `{validation['warning_count']}`",
        f"- Row count: `{validation['row_count']}`",
        f"- Supported accessions: `{validation['supported_accession_count']}`",
        f"- Unsupported accessions: `{validation['unsupported_accession_count']}`",
        f"- PDB-chain-enzyme accessions: `{validation['pdb_chain_enzyme_accession_count']}`",
        "",
        "## Issues",
        "",
    ]
    if validation["issues"]:
        for issue in validation["issues"]:
            lines.append(f"- {issue}")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Warnings",
            "",
        ]
    )
    if validation["warnings"]:
        for warning in validation["warnings"]:
            lines.append(f"- {warning}")
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            payload["truth_boundary"]["summary"],
        ]
    )
    return "\n".join(lines) + "\n"

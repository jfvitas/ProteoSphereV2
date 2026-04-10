from __future__ import annotations

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
DEFAULT_OPERATOR_DASHBOARD = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "operator_dashboard.json"
)

DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "sabio_rk_support_preview.json"
)
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "sabio_rk_support_preview.md"
DEFAULT_VALIDATION_JSON = (
    REPO_ROOT / "artifacts" / "status" / "sabio_rk_support_validation.json"
)
DEFAULT_VALIDATION_MD = (
    REPO_ROOT / "docs" / "reports" / "sabio_rk_support_validation.md"
)

SABIO_QUERY_SCOPE_FIELD = "UniProtKB_AC"
SUPPORTED_STATUS = "supported_now"
UNSUPPORTED_STATUS = "no_local_sabio_seed_coverage"


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


def _support_status(accession: str, sabio_accession_seed: set[str]) -> str:
    return SUPPORTED_STATUS if accession in sabio_accession_seed else UNSUPPORTED_STATUS


def _blocker_for_support_status(status: str) -> str:
    if status == SUPPORTED_STATUS:
        return "local_sabio_seed_only_no_live_kinetic_ids_verified"
    return "no_local_sabio_accession_seed"


def _next_stage_for_support_status(status: str) -> str:
    if status == SUPPORTED_STATUS:
        return "verify_accession_scoped_sabio_export"
    return "hold_for_sabio_acquisition"


def build_sabio_rk_support_preview(
    accession_matrix: dict[str, Any],
    sabio_accession_seed_text: str,
    sabio_search_fields_xml: str,
    operator_dashboard: dict[str, Any],
) -> dict[str, Any]:
    rows = [
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
    supported_rows: list[dict[str, Any]] = []
    unsupported_rows: list[dict[str, Any]] = []

    for row in rows:
        accession = str(row.get("accession") or "").strip()
        if not accession:
            continue
        support_status = _support_status(accession, sabio_accession_seed)
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
            "sabio_support_status": support_status,
            "sabio_seed_accession_present": support_status == SUPPORTED_STATUS,
            "sabio_query_scope": SABIO_QUERY_SCOPE_FIELD
            if support_status == SUPPORTED_STATUS
            else None,
            "current_blocker": _blocker_for_support_status(support_status),
            "next_truthful_stage": _next_stage_for_support_status(support_status),
            "source_provenance_refs": [
                "summary_library_operator_accession_matrix",
                "sabio_uniprotkb_acs",
                "sabio_search_fields",
                "operator_dashboard",
            ],
            "truth_note": (
                "Local SABIO accession seed overlaps this accession, but live kinetic-law "
                "IDs remain unverified."
                if support_status == SUPPORTED_STATUS
                else "No local SABIO accession seed overlaps this accession yet."
            ),
        }
        if support_status == SUPPORTED_STATUS:
            supported_rows.append(support_row)
        else:
            unsupported_rows.append(support_row)

    supported_accessions = [row["accession"] for row in supported_rows]
    unsupported_accessions = [row["accession"] for row in unsupported_rows]
    query_scope_present = _search_field_present(sabio_search_fields_xml)
    dashboard_status = str(operator_dashboard.get("dashboard_status") or "")
    operator_go_no_go = str(operator_dashboard.get("operator_go_no_go") or "")
    ready_for_next_wave = bool(
        (operator_dashboard.get("benchmark_summary") or {}).get("ready_for_next_wave")
    )
    return {
        "artifact_id": "sabio_rk_support_preview",
        "schema_id": "proteosphere-sabio-rk-support-preview-2026-04-02",
        "status": "complete",
        "surface_kind": "accession_level_kinetics_support_matrix",
        "row_count": len(rows),
        "rows": supported_rows + unsupported_rows,
        "summary": {
            "matrix_accession_count": len(rows),
            "sabio_seed_accession_count": len(sabio_accessions),
            "supported_accession_count": len(supported_rows),
            "unsupported_accession_count": len(unsupported_rows),
            "supported_accessions": supported_accessions,
            "unsupported_accessions": unsupported_accessions,
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
            "live_sbml_export_verified_count": 0,
            "dashboard_status": dashboard_status,
            "operator_go_no_go": operator_go_no_go,
            "ready_for_next_wave": ready_for_next_wave,
            "support_status_counts": dict(
                sorted(Counter(row["sabio_support_status"] for row in supported_rows + unsupported_rows).items())
            ),
        },
        "truth_boundary": {
            "summary": (
                "This is a support-only SABIO-RK accession matrix built from the local "
                "UniProt accession seed and query-field registry. It does not verify live "
                "kinetic-law IDs or SBML exports, and it does not change the blocked "
                "operator dashboard."
            ),
            "report_only": True,
            "seed_only": True,
            "live_kinetic_ids_verified": False,
            "live_sbml_exports_verified": False,
            "dashboard_blocked": dashboard_status == "blocked_on_release_grade_bar",
            "ready_for_operator_preview": True,
        },
    }


def build_sabio_rk_support_validation(
    sabio_rk_support_preview: dict[str, Any],
    accession_matrix: dict[str, Any],
    sabio_accession_seed_text: str,
    sabio_search_fields_xml: str,
    operator_dashboard: dict[str, Any],
) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    rows = [
        row for row in sabio_rk_support_preview.get("rows") or [] if isinstance(row, dict)
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
    expected_supported_accessions = [
        row["accession"]
        for row in matrix_rows
        if row.get("accession") in sabio_accession_seed
    ]
    expected_unsupported_accessions = [
        row["accession"]
        for row in matrix_rows
        if row.get("accession") not in sabio_accession_seed
    ]
    supported_rows = [
        row for row in rows if row.get("sabio_support_status") == SUPPORTED_STATUS
    ]
    unsupported_rows = [
        row for row in rows if row.get("sabio_support_status") == UNSUPPORTED_STATUS
    ]
    supported_accessions = [row["accession"] for row in supported_rows]
    unsupported_accessions = [row["accession"] for row in unsupported_rows]

    if sabio_rk_support_preview.get("row_count") != len(rows):
        issues.append("row_count does not match emitted SABIO-RK support rows")
    if len(matrix_rows) != len(rows):
        issues.append("matrix accession count does not match emitted rows")
    if sabio_rk_support_preview.get("summary", {}).get("supported_accession_count") != len(
        supported_rows
    ):
        issues.append("supported_accession_count does not match supported rows")
    if sabio_rk_support_preview.get("summary", {}).get("unsupported_accession_count") != len(
        unsupported_rows
    ):
        issues.append("unsupported_accession_count does not match unsupported rows")
    if sabio_rk_support_preview.get("summary", {}).get("supported_accessions") != expected_supported_accessions:
        issues.append("supported_accessions do not match local SABIO accession seed overlap")
    if sabio_rk_support_preview.get("summary", {}).get("unsupported_accessions") != expected_unsupported_accessions:
        issues.append("unsupported_accessions do not match local SABIO accession gap")
    if sabio_rk_support_preview.get("summary", {}).get("query_scope_field_present") is not True:
        issues.append("SABIO UniProtKB_AC query scope must be present")
    if sabio_rk_support_preview.get("summary", {}).get("dashboard_status") != "blocked_on_release_grade_bar":
        issues.append("operator dashboard status must remain blocked_on_release_grade_bar")
    if sabio_rk_support_preview.get("summary", {}).get("operator_go_no_go") != "no-go":
        issues.append("operator go/no-go must remain no-go")
    if operator_dashboard.get("dashboard_status") != "blocked_on_release_grade_bar":
        issues.append("dashboard source artifact is no longer blocked_on_release_grade_bar")
    if (operator_dashboard.get("benchmark_summary") or {}).get("ready_for_next_wave") is not True:
        issues.append("benchmark summary is not ready for next wave")
    if not _search_field_present(sabio_search_fields_xml):
        issues.append("UniProtKB_AC search field is missing from SABIO search fields")
    if sabio_rk_support_preview.get("truth_boundary", {}).get("report_only") is not True:
        issues.append("truth boundary must remain report_only")
    if sabio_rk_support_preview.get("truth_boundary", {}).get("live_kinetic_ids_verified") is not False:
        issues.append("live kinetic-law IDs must remain unverified")

    if rows:
        warnings.append(
            "support surface is seed-backed only; live kinetic-law IDs remain unverified"
        )

    status = "aligned" if not issues else "attention_needed"
    return {
        "artifact_id": "sabio_rk_support_validation",
        "schema_id": "proteosphere-sabio-rk-support-validation-2026-04-02",
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
            "query_scope_field_present": _search_field_present(sabio_search_fields_xml),
            "live_kinetic_law_verified_count": 0,
            "live_sbml_export_verified_count": 0,
            "dashboard_status": operator_dashboard.get("dashboard_status"),
            "operator_go_no_go": operator_dashboard.get("operator_go_no_go"),
            "issues": issues,
            "warnings": warnings,
        },
        "truth_boundary": {
            "summary": (
                "This validation confirms the SABIO-RK support preview is seed-backed and "
                "internally consistent. It does not certify live kinetic-law IDs or SBML "
                "exports, and it does not change the blocked operator dashboard."
            ),
            "report_only": True,
            "seed_only": True,
            "live_kinetic_ids_verified": False,
            "live_sbml_exports_verified": False,
            "dashboard_blocked": operator_dashboard.get("dashboard_status")
            == "blocked_on_release_grade_bar",
        },
    }


def render_preview_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# SABIO-RK Support Preview",
        "",
        f"- Status: `{payload['status']}`",
        f"- Surface kind: `{payload['surface_kind']}`",
        f"- Matrix accessions: `{summary['matrix_accession_count']}`",
        f"- SABIO seed accessions: `{summary['sabio_seed_accession_count']}`",
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
            row = next(row for row in payload["rows"] if row["accession"] == accession)
            lines.append(
                f"- `{accession}` -> priority=`{row['operator_priority']}`, "
                f"bundle=`{row['bundle_projection']}`, blocker=`{row['current_blocker']}`, "
                f"next=`{row['next_truthful_stage']}`"
            )
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            f"- {payload['truth_boundary']['summary']}",
            "",
        ]
    )
    return "\n".join(lines)


def render_validation_markdown(payload: dict[str, Any]) -> str:
    validation = payload["validation"]
    lines = [
        "# SABIO-RK Support Validation",
        "",
        f"- Status: `{payload['status']}`",
        f"- Rows: `{validation['row_count']}`",
        f"- Supported accessions: `{validation['supported_accession_count']}`",
        f"- Unsupported accessions: `{validation['unsupported_accession_count']}`",
        f"- Query scope field present: `{validation['query_scope_field_present']}`",
        f"- Dashboard status: `{validation['dashboard_status']}`",
        "",
        "## Supported Accessions",
        "",
        f"- `{', '.join(validation['supported_accessions']) or 'none'}`",
    ]
    if validation["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in validation["warnings"])
    if validation["issues"]:
        lines.extend(["", "## Issues", ""])
        lines.extend(f"- {issue}" for issue in validation["issues"])
    lines.extend(
        [
            "",
            "## Truth Boundary",
            "",
            f"- {payload['truth_boundary']['summary']}",
            "",
        ]
    )
    return "\n".join(lines)

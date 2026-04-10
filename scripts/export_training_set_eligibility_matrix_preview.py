from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts.modality_readiness_ladder import (
        LADDER_ABSENT,
        LADDER_CANDIDATE_ONLY,
        LADDER_GROUNDED_GOVERNING,
        LADDER_GROUNDED_PREVIEW_SAFE,
        LADDER_SUPPORT_ONLY,
        classify_ligand_readiness,
        ladder_accession_buckets,
        ladder_counts,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from modality_readiness_ladder import (
        LADDER_ABSENT,
        LADDER_CANDIDATE_ONLY,
        LADDER_GROUNDED_GOVERNING,
        LADDER_GROUNDED_PREVIEW_SAFE,
        LADDER_SUPPORT_ONLY,
        classify_ligand_readiness,
        ladder_accession_buckets,
        ladder_counts,
    )

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET_DEFICIT = REPO_ROOT / "artifacts" / "status" / "packet_deficit_dashboard.json"
DEFAULT_ACCESSION_MATRIX = (
    REPO_ROOT / "artifacts" / "status" / "summary_library_operator_accession_matrix.json"
)
DEFAULT_LIGAND_ROW_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "ligand_row_materialization_preview.json"
)
DEFAULT_LIGAND_SUPPORT_READINESS = (
    REPO_ROOT / "artifacts" / "status" / "ligand_support_readiness_preview.json"
)
DEFAULT_MOTIF_DOMAIN_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "motif_domain_compact_preview_family.json"
)
DEFAULT_INTERACTION_SIMILARITY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "interaction_similarity_signature_preview.json"
)
DEFAULT_KINETICS_SUPPORT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "kinetics_enzyme_support_preview.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / "artifacts" / "status" / "training_set_eligibility_matrix_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "training_set_eligibility_matrix_preview.md"
)

TASK_IDS = (
    "protein_reference",
    "full_packet_current_latest",
    "structure_conditioned_current_latest",
    "ppi_conditioned_current_latest",
    "grounded_ligand_similarity_preview",
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _index_by_accession(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        accession = str(row.get("accession") or "").strip()
        if accession:
            indexed[accession] = row
    return indexed


def _ligand_accession_sets(payload: dict[str, Any]) -> tuple[set[str], set[str]]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    grounded = {
        str(value).strip()
        for value in summary.get("grounded_accessions") or []
        if str(value).strip()
    }
    candidate_only = {
        str(value).strip()
        for value in summary.get("candidate_only_accessions") or []
        if str(value).strip()
    }
    return grounded, candidate_only


def _ligand_support_accessions(payload: dict[str, Any]) -> tuple[set[str], set[str], bool]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    support = {
        str(value).strip()
        for value in summary.get("support_accessions") or []
        if str(value).strip()
    }
    deferred = {
        str(value).strip()
        for value in summary.get("deferred_accessions") or []
        if str(value).strip()
    }
    bundle_included = bool(summary.get("bundle_ligands_included"))
    return support, deferred, bundle_included


def _motif_domain_accessions(payload: dict[str, Any] | None) -> set[str]:
    accessions: set[str] = set()
    if payload is None:
        return accessions
    for row in payload.get("rows") or []:
        if not isinstance(row, dict):
            continue
        for summary_id in row.get("supporting_summary_ids") or []:
            value = str(summary_id).strip()
            if value.startswith("protein:"):
                accessions.add(value.removeprefix("protein:"))
    return accessions


def _interaction_accession_sets(payload: dict[str, Any] | None) -> tuple[set[str], set[str], bool]:
    accessions: set[str] = set()
    candidate_only: set[str] = set()
    if payload is None:
        return accessions, candidate_only, False
    for row in payload.get("rows") or []:
        if not isinstance(row, dict):
            continue
        accession = str(row.get("accession") or "").strip()
        if not accession:
            continue
        accessions.add(accession)
        if bool(row.get("candidate_only")):
            candidate_only.add(accession)
    truth = payload.get("truth_boundary") or {}
    return accessions, candidate_only, bool(truth.get("interaction_family_materialized"))


def _kinetics_supported_accessions(payload: dict[str, Any] | None) -> set[str]:
    accessions: set[str] = set()
    if payload is None:
        return accessions
    for row in payload.get("rows") or []:
        if not isinstance(row, dict):
            continue
        accession = str(row.get("accession") or "").strip()
        if accession and str(row.get("kinetics_support_status") or "").strip() == "supported_now":
            accessions.add(accession)
    return accessions


def _task_status(
    *,
    accession: str,
    summary_row: dict[str, Any] | None,
    packet_row: dict[str, Any] | None,
    grounded_ligand_accessions: set[str],
    candidate_only_ligand_accessions: set[str],
) -> dict[str, dict[str, Any]]:
    summary_present = summary_row is not None and bool(summary_row.get("protein_summary_present"))
    packet_present = packet_row is not None
    packet_status = str(packet_row.get("status") or "").strip() if packet_row else ""
    packet_complete = packet_status == "complete"
    missing_modalities = set(packet_row.get("missing_modalities") or []) if packet_row else set()

    statuses: dict[str, dict[str, Any]] = {}
    statuses["protein_reference"] = {
        "status": "eligible_for_task" if summary_present else "audit_only",
        "reason": (
            "protein summary is materialized in the lightweight library"
            if summary_present
            else "protein summary is absent from the current lightweight preview"
        ),
    }
    statuses["full_packet_current_latest"] = {
        "status": (
            "eligible_for_task"
            if packet_complete
            else "blocked_pending_acquisition"
            if packet_present
            else "audit_only"
        ),
        "reason": (
            "all requested packet modalities are present in the protected latest surface"
            if packet_complete
            else f"latest packet is partial; missing modalities: {sorted(missing_modalities)}"
            if packet_present
            else "accession is not visible in the current packet latest surface"
        ),
    }
    statuses["structure_conditioned_current_latest"] = {
        "status": (
            "eligible_for_task"
            if packet_present and "structure" not in missing_modalities
            else "blocked_pending_acquisition"
            if packet_present
            else "audit_only"
        ),
        "reason": (
            "latest packet currently carries a structure lane"
            if packet_present and "structure" not in missing_modalities
            else "structure is missing in the current protected packet surface"
            if packet_present
            else "no packet surface exists for structure-conditioned checks"
        ),
    }
    statuses["ppi_conditioned_current_latest"] = {
        "status": (
            "eligible_for_task"
            if packet_present and "ppi" not in missing_modalities
            else "blocked_pending_acquisition"
            if packet_present
            else "audit_only"
        ),
        "reason": (
            "latest packet currently carries a PPI lane"
            if packet_present and "ppi" not in missing_modalities
            else "PPI is missing in the current protected packet surface"
            if packet_present
            else "no packet surface exists for PPI-conditioned checks"
        ),
    }
    if accession in grounded_ligand_accessions:
        ligand_status = "eligible_for_task"
        ligand_reason = (
            "grounded lightweight ligand rows exist and remain preview-safe while bundle "
            "inclusion stays false"
        )
    elif accession in candidate_only_ligand_accessions:
        ligand_status = "candidate_only_non_governing"
        ligand_reason = (
            "only candidate-only ligand evidence exists; keep it "
            "non-governing for split and leakage"
        )
    elif packet_present and "ligand" in missing_modalities:
        ligand_status = "blocked_pending_acquisition"
        ligand_reason = "latest packet is missing ligand coverage for this accession"
    elif packet_complete:
        ligand_status = "library_only"
        ligand_reason = (
            "packet appears ligand-complete, but lightweight ligand rows "
            "are not yet condensed here"
        )
    elif summary_present:
        ligand_status = "library_only"
        ligand_reason = (
            "accession is retained in the library, but no current "
            "grounded ligand rows are materialized"
        )
    else:
        ligand_status = "audit_only"
        ligand_reason = "insufficient lightweight coverage for ligand planning"
    statuses["grounded_ligand_similarity_preview"] = {
        "status": ligand_status,
        "reason": ligand_reason,
    }
    return statuses


def _primary_class(task_statuses: dict[str, dict[str, Any]]) -> str:
    ordered = (
        "candidate_only_non_governing",
        "blocked_pending_acquisition",
        "eligible_for_task",
        "library_only",
        "audit_only",
    )
    present = {value["status"] for value in task_statuses.values()}
    for status in ordered:
        if status in present:
            return status
    return "audit_only"


def build_training_set_eligibility_matrix_preview(
    packet_deficit_dashboard: dict[str, Any],
    accession_matrix: dict[str, Any],
    ligand_row_preview: dict[str, Any],
    ligand_support_readiness_preview: dict[str, Any] | None = None,
    motif_domain_preview: dict[str, Any] | None = None,
    interaction_similarity_preview: dict[str, Any] | None = None,
    kinetics_support_preview: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packet_rows = [
        row for row in packet_deficit_dashboard.get("packets") or [] if isinstance(row, dict)
    ]
    summary_rows = [
        row for row in accession_matrix.get("rows") or [] if isinstance(row, dict)
    ]
    packet_by_accession = _index_by_accession(packet_rows)
    summary_by_accession = _index_by_accession(summary_rows)
    grounded_ligand_accessions, candidate_only_ligand_accessions = _ligand_accession_sets(
        ligand_row_preview
    )
    support_accessions, deferred_accessions, bundle_ligands_included = _ligand_support_accessions(
        ligand_support_readiness_preview or {}
    )
    motif_accessions = _motif_domain_accessions(motif_domain_preview)
    interaction_accessions, interaction_candidate_only_accessions, interaction_materialized = (
        _interaction_accession_sets(interaction_similarity_preview)
    )
    kinetics_accessions = _kinetics_supported_accessions(kinetics_support_preview)

    all_accessions = sorted(
        set(summary_by_accession)
        | set(packet_by_accession)
        | grounded_ligand_accessions
        | candidate_only_ligand_accessions
        | support_accessions
        | deferred_accessions
        | motif_accessions
        | interaction_accessions
        | kinetics_accessions
    )
    rows: list[dict[str, Any]] = []
    task_status_counts = {task_id: Counter() for task_id in TASK_IDS}
    modality_readiness_counts: dict[str, Counter[str]] = {
        "ligand": Counter(),
        "structure": Counter(),
        "interaction": Counter(),
        "motif_domain": Counter(),
        "kinetics": Counter(),
    }

    for accession in all_accessions:
        summary_row = summary_by_accession.get(accession)
        packet_row = packet_by_accession.get(accession)
        task_statuses = _task_status(
            accession=accession,
            summary_row=summary_row,
            packet_row=packet_row,
            grounded_ligand_accessions=grounded_ligand_accessions,
            candidate_only_ligand_accessions=candidate_only_ligand_accessions,
        )
        for task_id, value in task_statuses.items():
            task_status_counts[task_id][value["status"]] += 1

        packet_present_modalities = (
            list(packet_row.get("present_modalities") or []) if packet_row else []
        )
        packet_missing_modalities = (
            list(packet_row.get("missing_modalities") or []) if packet_row else []
        )
        ligand_readiness = classify_ligand_readiness(
            accession,
            grounded_accessions=grounded_ligand_accessions,
            candidate_only_accessions=candidate_only_ligand_accessions,
            support_accessions=support_accessions,
            packet_status=str(packet_row.get("status") or "") if packet_row else None,
            packet_missing_modalities=packet_missing_modalities,
            bundle_ligands_included=bundle_ligands_included,
        )
        structure_readiness = (
            LADDER_GROUNDED_GOVERNING
            if summary_row and int(summary_row.get("structure_unit_count") or 0) > 0
            else LADDER_SUPPORT_ONLY
            if packet_row is not None and "structure" not in packet_missing_modalities
            else LADDER_ABSENT
        )
        interaction_readiness = (
            LADDER_CANDIDATE_ONLY
            if accession in interaction_candidate_only_accessions
            else LADDER_GROUNDED_PREVIEW_SAFE
            if accession in interaction_accessions and interaction_materialized
            else LADDER_ABSENT
        )
        motif_domain_readiness = (
            LADDER_GROUNDED_PREVIEW_SAFE if accession in motif_accessions else LADDER_ABSENT
        )
        kinetics_readiness = (
            LADDER_SUPPORT_ONLY if accession in kinetics_accessions else LADDER_ABSENT
        )
        modality_readiness = {
            "ligand": ligand_readiness,
            "structure": structure_readiness,
            "interaction": interaction_readiness,
            "motif_domain": motif_domain_readiness,
            "kinetics": kinetics_readiness,
        }
        for modality_name, ladder_value in modality_readiness.items():
            modality_readiness_counts[modality_name][ladder_value] += 1
        rows.append(
            {
                "accession": accession,
                "protein_ref": (
                    summary_row.get("protein_ref")
                    if summary_row
                    else packet_row.get("canonical_id")
                    if packet_row
                    else f"protein:{accession}"
                ),
                "protein_name": summary_row.get("protein_name") if summary_row else None,
                "protein_summary_present": bool(
                    summary_row and summary_row.get("protein_summary_present")
                ),
                "packet_present": packet_row is not None,
                "packet_status": packet_row.get("status") if packet_row else "absent",
                "packet_present_modalities": packet_present_modalities,
                "packet_missing_modalities": packet_missing_modalities,
                "grounded_ligand_rows_present": accession in grounded_ligand_accessions,
                "candidate_only_ligand_rows_present": accession in candidate_only_ligand_accessions,
                "ligand_readiness_ladder": ligand_readiness,
                "modality_readiness": modality_readiness,
                "variant_count": int(summary_row.get("variant_count") or 0) if summary_row else 0,
                "structure_unit_count": (
                    int(summary_row.get("structure_unit_count") or 0) if summary_row else 0
                ),
                "primary_missing_data_class": _primary_class(task_statuses),
                "task_eligibility": task_statuses,
            }
        )

    primary_class_counts = Counter(row["primary_missing_data_class"] for row in rows)
    readiness_ladder_counts = ladder_counts(
        [row["ligand_readiness_ladder"] for row in rows]
    )
    return {
        "artifact_id": "training_set_eligibility_matrix_preview",
        "schema_id": "proteosphere-training-set-eligibility-matrix-preview-2026-04-02",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "accession_count": len(rows),
            "packet_visible_accession_count": sum(1 for row in rows if row["packet_present"]),
            "protein_summary_accession_count": sum(
                1 for row in rows if row["protein_summary_present"]
            ),
            "grounded_ligand_accessions": sorted(grounded_ligand_accessions),
            "candidate_only_ligand_accessions": sorted(candidate_only_ligand_accessions),
            "ligand_readiness_ladder_counts": readiness_ladder_counts,
            "ligand_readiness_accessions": ladder_accession_buckets(rows),
            "modality_readiness_counts": {
                modality_name: dict(sorted(counter.items()))
                for modality_name, counter in sorted(modality_readiness_counts.items())
            },
            "primary_missing_data_class_counts": dict(sorted(primary_class_counts.items())),
            "task_status_counts": {
                task_id: dict(sorted(counter.items()))
                for task_id, counter in sorted(task_status_counts.items())
            },
        },
        "truth_boundary": {
            "summary": (
                "This matrix is a task-facing eligibility surface for the current lightweight "
                "preview and protected latest packet state. It does not invent missing values, "
                "it does not let candidate-only rows govern split policy, and it does not imply "
                "that every complete packet family has already been condensed into the bundle."
            ),
            "report_only": True,
            "support_only_rows_non_governing": True,
            "candidate_only_rows_non_governing": True,
            "grounded_preview_safe_rows_non_governing": True,
            "missing_values_imputed": False,
            "packet_latest_mutated": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Training Set Eligibility Matrix Preview",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Accessions: `{summary['accession_count']}`",
        f"- Packet-visible accessions: `{summary['packet_visible_accession_count']}`",
        f"- Protein-summary accessions: `{summary['protein_summary_accession_count']}`",
        "- Grounded ligand accessions: "
        f"`{', '.join(summary['grounded_ligand_accessions']) or 'none'}`",
        "- Candidate-only ligand accessions: "
        f"`{', '.join(summary['candidate_only_ligand_accessions']) or 'none'}`",
        "- Ligand readiness ladder counts: "
        f"`{json.dumps(summary['ligand_readiness_ladder_counts'], sort_keys=True)}`",
        "",
        "## Primary Class Counts",
        "",
    ]
    for status, count in summary["primary_missing_data_class_counts"].items():
        lines.append(f"- `{status}`: `{count}`")
    lines.extend(
        [
            "",
            "## Task Status Counts",
            "",
        ]
    )
    for task_id, counts in summary["task_status_counts"].items():
        rendered_counts = ", ".join(f"{key}={value}" for key, value in counts.items()) or "none"
        lines.append(f"- `{task_id}`: {rendered_counts}")
    lines.extend(
        [
            "",
            "## Accession Rows",
            "",
            "| Accession | Primary class | Packet status | Grounded ligand | "
            "Candidate-only ligand | Ligand readiness |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in payload["rows"]:
        lines.append(
            "| "
            + f"`{row['accession']}` | "
            + f"{row['primary_missing_data_class']} | "
            + f"{row['packet_status']} | "
            + f"{row['grounded_ligand_rows_present']} | "
            + f"{row['candidate_only_ligand_rows_present']} | "
            + f"{row['ligand_readiness_ladder']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export an accession-level training-set eligibility matrix preview."
    )
    parser.add_argument("--packet-deficit", type=Path, default=DEFAULT_PACKET_DEFICIT)
    parser.add_argument("--accession-matrix", type=Path, default=DEFAULT_ACCESSION_MATRIX)
    parser.add_argument("--ligand-row-preview", type=Path, default=DEFAULT_LIGAND_ROW_PREVIEW)
    parser.add_argument(
        "--ligand-support-readiness",
        type=Path,
        default=DEFAULT_LIGAND_SUPPORT_READINESS,
    )
    parser.add_argument("--motif-domain-preview", type=Path, default=DEFAULT_MOTIF_DOMAIN_PREVIEW)
    parser.add_argument(
        "--interaction-similarity-preview",
        type=Path,
        default=DEFAULT_INTERACTION_SIMILARITY_PREVIEW,
    )
    parser.add_argument(
        "--kinetics-support-preview",
        type=Path,
        default=DEFAULT_KINETICS_SUPPORT_PREVIEW,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload = build_training_set_eligibility_matrix_preview(
        _read_json(args.packet_deficit),
        _read_json(args.accession_matrix),
        _read_json(args.ligand_row_preview),
        _read_json(args.ligand_support_readiness),
        _read_json(args.motif_domain_preview),
        _read_json(args.interaction_similarity_preview),
        _read_json(args.kinetics_support_preview),
    )
    _write_json(args.output, payload)
    _write_text(args.markdown_output, render_markdown(payload))
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            "Training-set eligibility matrix exported: "
            f"accessions={payload['summary']['accession_count']} "
            f"grounded_ligands={len(payload['summary']['grounded_ligand_accessions'])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

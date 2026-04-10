from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
try:
    from scripts.web_enrichment_preview_support import read_json, write_json, write_text
except ModuleNotFoundError:  # pragma: no cover
    from web_enrichment_preview_support import read_json, write_json, write_text

DEFAULT_UNIREF_CLUSTER_CONTEXT = (
    REPO_ROOT / "artifacts" / "status" / "uniref_cluster_context_preview.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "sequence_redundancy_guard_preview.json"
)
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "sequence_redundancy_guard_preview.md"


def build_sequence_redundancy_guard_preview(
    uniref_cluster_context_preview: dict[str, Any],
) -> dict[str, Any]:
    rows = [
        row
        for row in (uniref_cluster_context_preview.get("rows") or [])
        if isinstance(row, dict)
    ]
    cluster_counts: dict[str, int] = {}
    for row in rows:
        cluster_id = str(row.get("uniref100_cluster_id") or "").strip()
        if cluster_id:
            cluster_counts[cluster_id] = cluster_counts.get(cluster_id, 0) + 1

    guard_rows = []
    for row in rows:
        cluster_id = str(row.get("uniref100_cluster_id") or "").strip()
        in_scope_count = cluster_counts.get(cluster_id, 0) if cluster_id else 0
        if not cluster_id:
            guard_status = "cluster_unknown_pending_tail"
        elif in_scope_count > 1:
            guard_status = "shared_cluster_guard_required"
        else:
            guard_status = "crossref_present_no_in_scope_collision"
        guard_rows.append(
            {
                "accession": row.get("accession"),
                "uniref100_cluster_id": cluster_id or None,
                "in_scope_cluster_member_count": in_scope_count,
                "shared_in_scope_cluster": in_scope_count > 1,
                "redundancy_guard_status": guard_status,
            }
        )

    return {
        "artifact_id": "sequence_redundancy_guard_preview",
        "schema_id": "proteosphere-sequence-redundancy-guard-preview-2026-04-03",
        "status": "report_only",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(guard_rows),
        "rows": guard_rows,
        "summary": {
            "accessions_with_cluster_ids": sum(
                1 for row in guard_rows if row.get("uniref100_cluster_id")
            ),
            "shared_cluster_accession_count": sum(
                1 for row in guard_rows if row["shared_in_scope_cluster"]
            ),
            "shared_cluster_group_count": sum(
                1 for count in cluster_counts.values() if count > 1
            ),
        },
        "truth_boundary": {
            "summary": (
                "This guard is a report-only in-scope redundancy check based on current "
                "UniProt UniRef100 cross-references. It does not collapse training units "
                "and remains non-governing in this phase."
            ),
            "report_only": True,
            "governing": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ["# Sequence Redundancy Guard Preview", ""]
    for row in payload.get("rows") or []:
        lines.append(
            f"- `{row['accession']}` / `{row['redundancy_guard_status']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build sequence redundancy guard preview.")
    parser.add_argument(
        "--uniref-cluster-context", type=Path, default=DEFAULT_UNIREF_CLUSTER_CONTEXT
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_sequence_redundancy_guard_preview(read_json(args.uniref_cluster_context))
    write_json(args.output_json, payload)
    write_text(args.output_md, render_markdown(payload))
    print(args.output_json)


if __name__ == "__main__":
    main()

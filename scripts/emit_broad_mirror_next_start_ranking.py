from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REMAINING_TRANSFER_STATUS_PATH = (
    REPO_ROOT / "artifacts" / "status" / "broad_mirror_remaining_transfer_status.json"
)
DEFAULT_SOURCE_POLICY_PATH = REPO_ROOT / "protein_data_scope" / "source_policy.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "artifacts" / "status" / "broad_mirror_next_start_ranking.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "reports" / "broad_mirror_next_start_ranking.md"

ROLE_RANK = {
    "direct": 0,
    "guarded": 1,
    "resolver": 2,
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _casefold(value: Any) -> str:
    return str(value or "").strip().casefold()


def _source_role_map(policy: dict[str, Any]) -> dict[str, str]:
    role_map: dict[str, str] = {}
    tiers = policy.get("tiers") if isinstance(policy.get("tiers"), dict) else {}
    for role, payload in tiers.items():
        if not isinstance(payload, dict):
            continue
        for source_id in payload.get("source_ids") or []:
            key = _casefold(source_id)
            if key:
                role_map[key] = str(role)
    return role_map


def _manageability_rank(filename: str) -> int:
    name = filename.casefold()
    if name.endswith(".txt.gz") or name.endswith(".tab.gz") or name.endswith(".fasta.gz"):
        return 0
    if name.endswith(".sql.gz") or name.endswith(".xml.gz"):
        return 1
    if name.endswith(".pdf"):
        return 2
    if name.endswith(".h5"):
        return 3
    return 4


def _uniprot_rank(filename: str) -> tuple[int, str]:
    ranking = {
        "idmapping_selected.tab.gz": (0, "crosswalk table with direct library utility"),
        "uniprot_sprot_varsplic.fasta.gz": (
            1,
            "isoform-aware Swiss-Prot sequence expansion",
        ),
        "uniref100.fasta.gz": (2, "broadest representative UniRef FASTA"),
        "uniref90.fasta.gz": (3, "mid-density UniRef FASTA"),
        "uniref90.xml.gz": (4, "mid-density UniRef XML"),
        "uniref50.fasta.gz": (5, "compact representative UniRef FASTA"),
        "uniref50.xml.gz": (6, "compact representative UniRef XML"),
    }
    return ranking.get(
        filename.casefold(),
        (99, "unrecognized UniProt backlog file"),
    )


def _string_rank(filename: str) -> tuple[int, str]:
    ranking = {
        "protein.physical.links.v12.0.txt.gz": (0, "core physical interaction table"),
        "protein.physical.links.detailed.v12.0.txt.gz": (
            1,
            "detailed physical interaction table",
        ),
        "protein.physical.links.full.v12.0.txt.gz": (2, "full physical interaction table"),
        "items_schema.v12.0.sql.gz": (3, "schema export for downstream loading"),
        "network_schema.v12.0.sql.gz": (4, "schema export for downstream loading"),
        "evidence_schema.v12.0.sql.gz": (5, "schema export for downstream loading"),
        "database.schema.v12.0.pdf": (6, "reference PDF for schema review"),
        "protein.network.embeddings.v12.0.h5": (
            7,
            "large embedding artifact with lower immediate library value",
        ),
        "protein.sequence.embeddings.v12.0.h5": (
            8,
            "large embedding artifact with lower immediate library value",
        ),
    }
    return ranking.get(
        filename.casefold(),
        (99, "unrecognized STRING backlog file"),
    )


def _file_rank(source_id: str, filename: str) -> tuple[int, int, str]:
    source_key = _casefold(source_id)
    if source_key == "uniprot":
        value_rank, rationale = _uniprot_rank(filename)
        manageability_rank = _manageability_rank(filename)
    elif source_key == "string":
        value_rank, rationale = _string_rank(filename)
        manageability_rank = _manageability_rank(filename)
    else:
        value_rank, rationale = (99, "unscored source")
        manageability_rank = _manageability_rank(filename)
    return value_rank, manageability_rank, rationale


def _build_file_entry(
    *,
    source_id: str,
    source_name: str,
    source_role: str,
    filename: str,
    gap_kind: str,
    category: str | None,
) -> dict[str, Any]:
    value_rank, manageability_rank, rationale = _file_rank(source_id, filename)
    role_rank = ROLE_RANK.get(source_role.casefold(), 99)
    return {
        "source_id": source_id,
        "source_name": source_name,
        "source_role": source_role,
        "category": category,
        "filename": filename,
        "gap_kind": gap_kind,
        "role_rank": role_rank,
        "value_rank": value_rank,
        "manageability_rank": manageability_rank,
        "launch_priority": (role_rank, value_rank, manageability_rank, _casefold(filename)),
        "ranking_rationale": rationale,
    }


def build_next_start_ranking(
    *,
    remaining_transfer_status_path: Path = DEFAULT_REMAINING_TRANSFER_STATUS_PATH,
    source_policy_path: Path = DEFAULT_SOURCE_POLICY_PATH,
) -> dict[str, Any]:
    remaining = _read_json(remaining_transfer_status_path)
    policy = _read_json(source_policy_path)
    role_map = _source_role_map(policy)
    source_rows = [row for row in remaining.get("sources") or [] if isinstance(row, dict)]

    ranked_sources: list[dict[str, Any]] = []
    ranked_files: list[dict[str, Any]] = []
    for source in source_rows:
        source_id = str(source.get("source_id") or "").strip()
        if not source_id:
            continue
        source_name = str(source.get("source_name") or source_id).strip()
        source_role = role_map.get(source_id.casefold(), "unknown")
        files = []
        for gap_kind, filenames in (
            ("missing", source.get("not_yet_started") or []),
        ):
            for item in filenames:
                filename = str(item.get("filename") or "").strip() if isinstance(item, dict) else ""
                if not filename:
                    continue
                entry = _build_file_entry(
                    source_id=source_id,
                    source_name=source_name,
                    source_role=source_role,
                    filename=filename,
                    gap_kind=gap_kind,
                    category=source.get("category"),
                )
                files.append(entry)
                ranked_files.append(entry)
        files.sort(key=lambda row: row["launch_priority"])
        ranked_sources.append(
            {
                "source_id": source_id,
                "source_name": source_name,
                "source_role": source_role,
                "category": source.get("category"),
                "not_yet_started_file_count": len(files),
                "top_launch_candidates": files[:5],
            }
        )

    ranked_sources.sort(
        key=lambda row: (
            ROLE_RANK.get(_casefold(row["source_role"]), 99),
            -int(row.get("not_yet_started_file_count") or 0),
            _casefold(row["source_id"]),
        )
    )
    ranked_files.sort(key=lambda row: row["launch_priority"])

    return {
        "schema_id": "proteosphere-broad-mirror-next-start-ranking-2026-03-31",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "planning",
        "basis": {
            "remaining_transfer_status_path": str(remaining_transfer_status_path).replace(
                "\\", "/"
            ),
            "source_policy_path": str(source_policy_path).replace("\\", "/"),
        },
        "summary": {
            "remaining_source_count": len(ranked_sources),
            "ranked_file_count": len(ranked_files),
            "source_role_counts": {
                role: sum(1 for row in ranked_sources if row["source_role"] == role)
                for role in sorted({row["source_role"] for row in ranked_sources})
            },
            "top_source_ids": [row["source_id"] for row in ranked_sources],
            "recommended_sidecar_launch_count": len(ranked_files),
        },
        "source_rankings": ranked_sources,
        "recommended_sidecar_launch_order": [
            {
                "rank": index,
                "source_id": row["source_id"],
                "source_name": row["source_name"],
                "source_role": row["source_role"],
                "filename": row["filename"],
                "gap_kind": row["gap_kind"],
                "value_rank": row["value_rank"],
                "manageability_rank": row["manageability_rank"],
                "ranking_rationale": row["ranking_rationale"],
            }
            for index, row in enumerate(ranked_files, start=1)
        ],
        "notes": [
            "The launch order is an inference from current source roles plus file-family utility and manageability.",
            "The active-vs-pending split comes from the current remaining-transfer-status report; only not-yet-started files are ranked here.",
        ],
    }


def _format_ranked_row(row: dict[str, Any]) -> str:
    return (
        f"{row['rank']}. `{row['source_id']}` ({row['source_role']}) "
        f"`{row['filename']}`"
    )


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Broad Mirror Next-Start Ranking",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Basis: `{payload['basis']['remaining_transfer_status_path']}`",
        f"- Source policy: `{payload['basis']['source_policy_path']}`",
        f"- Remaining sources: `{summary['remaining_source_count']}`",
        f"- Ranked files: `{summary['ranked_file_count']}`",
        f"- Recommended sidecar launches: `{summary['recommended_sidecar_launch_count']}`",
        "",
        "## Launch Order",
        "",
        "| Rank | Source | Role | File | Value | Manageability |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["recommended_sidecar_launch_order"]:
        lines.append(
            "| "
            + f"{row['rank']} | "
            + f"`{row['source_id']}` | "
            + f"{row['source_role']} | "
            + f"`{row['filename']}` | "
            + f"{row['value_rank']} | "
            + f"{row['manageability_rank']} |"
        )

    lines.extend(["", "## Source Summary", ""])
    for row in payload["source_rankings"]:
        lines.append(
            f"- `{row['source_id']}` ({row['source_role']}): "
            f"{row['not_yet_started_file_count']} files; "
            f"top candidate `{row['top_launch_candidates'][0]['filename']}`"
            if row["top_launch_candidates"]
            else f"- `{row['source_id']}` ({row['source_role']}): no ranked files"
        )

    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit the broad-mirror next-start ranking.")
    parser.add_argument(
        "--remaining-transfer-status",
        type=Path,
        default=DEFAULT_REMAINING_TRANSFER_STATUS_PATH,
    )
    parser.add_argument("--source-policy", type=Path, default=DEFAULT_SOURCE_POLICY_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-markdown", action="store_true")
    args = parser.parse_args(argv)

    payload = build_next_start_ranking(
        remaining_transfer_status_path=args.remaining_transfer_status,
        source_policy_path=args.source_policy,
    )
    _write_json(args.output, payload)
    if not args.no_markdown:
        _write_text(args.markdown_output, render_markdown(payload))

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Broad mirror next-start ranking exported: "
            f"files={payload['summary']['ranked_file_count']} "
            f"sources={payload['summary']['remaining_source_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

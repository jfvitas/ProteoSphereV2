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
DEFAULT_JSON_OUTPUT = REPO_ROOT / "artifacts" / "status" / "broad_mirror_lane_plan.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "reports" / "broad_mirror_lane_plan.md"

UNIPROT_CORE_FILENAMES = {
    "uniprot_sprot_varsplic.fasta.gz",
    "uniref100.fasta.gz",
    "uniref90.fasta.gz",
}

UNIPROT_TAIL_FILENAMES = {
    "uniref90.xml.gz",
    "uniref50.fasta.gz",
    "uniref50.xml.gz",
}

UNIPROT_FILE_RANK = {
    "uniprot_sprot_varsplic.fasta.gz": 0,
    "uniref100.fasta.gz": 1,
    "uniref90.fasta.gz": 2,
    "uniref90.xml.gz": 3,
    "uniref50.fasta.gz": 4,
    "uniref50.xml.gz": 5,
}

STRING_FILE_RANK = {
    "protein.physical.links.detailed.v12.0.txt.gz": 0,
    "protein.physical.links.full.v12.0.txt.gz": 1,
    "items_schema.v12.0.sql.gz": 2,
    "network_schema.v12.0.sql.gz": 3,
    "evidence_schema.v12.0.sql.gz": 4,
    "database.schema.v12.0.pdf": 5,
    "protein.network.embeddings.v12.0.h5": 6,
    "protein.sequence.embeddings.v12.0.h5": 7,
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


def _sort_filenames(filenames: list[str], rank_map: dict[str, int]) -> list[str]:
    return sorted(
        filenames,
        key=lambda filename: (
            rank_map.get(_casefold(filename), 99),
            _casefold(filename),
        ),
    )


def _build_batch(
    *,
    rank: int,
    batch_id: str,
    source_id: str,
    source_name: str,
    source_role: str,
    value_class: str,
    filenames: list[str],
    rationale: str,
    expected_impact: str,
) -> dict[str, Any]:
    return {
        "rank": rank,
        "batch_id": batch_id,
        "source_id": source_id,
        "source_name": source_name,
        "source_role": source_role,
        "value_class": value_class,
        "file_count": len(filenames),
        "files": filenames,
        "rationale": rationale,
        "expected_impact": expected_impact,
    }


def build_lane_plan(
    *,
    remaining_transfer_status_path: Path = DEFAULT_REMAINING_TRANSFER_STATUS_PATH,
    source_policy_path: Path = DEFAULT_SOURCE_POLICY_PATH,
) -> dict[str, Any]:
    remaining = _read_json(remaining_transfer_status_path)
    policy = _read_json(source_policy_path)
    role_map = _source_role_map(policy)

    source_rows = [row for row in remaining.get("sources") or [] if isinstance(row, dict)]
    source_lookup = {
        _casefold(row.get("source_id")): row
        for row in source_rows
        if _casefold(row.get("source_id"))
    }

    batches: list[dict[str, Any]] = []

    uniprot = source_lookup.get("uniprot")
    if uniprot:
        source_id = str(uniprot.get("source_id") or "uniprot").strip()
        source_name = str(uniprot.get("source_name") or source_id).strip()
        source_role = role_map.get(_casefold(source_id), "unknown")
        filenames = [
            str(item.get("filename") or "").strip()
            for item in uniprot.get("not_yet_started") or []
            if isinstance(item, dict) and str(item.get("filename") or "").strip()
        ]
        ordered = _sort_filenames(filenames, UNIPROT_FILE_RANK)
        core = [filename for filename in ordered if _casefold(filename) in UNIPROT_CORE_FILENAMES]
        tail = [filename for filename in ordered if _casefold(filename) in UNIPROT_TAIL_FILENAMES]
        extras = [
            filename
            for filename in ordered
            if _casefold(filename) not in UNIPROT_CORE_FILENAMES
            and _casefold(filename) not in UNIPROT_TAIL_FILENAMES
        ]

        if core:
            batches.append(
                _build_batch(
                    rank=len(batches) + 1,
                    batch_id="uniprot-core-backbone",
                    source_id=source_id,
                    source_name=source_name,
                    source_role=source_role,
                    value_class="direct-value",
                    filenames=core,
                    rationale=(
                        "Highest immediate library value: the isoform-aware Swiss-Prot file and "
                        "representative UniRef FASTA lanes are the smallest, most direct backbone."
                    ),
                    expected_impact=(
                        "Restores the core sequence reference layer first, with the best "
                        "direct-value payoff for library consumers."
                    ),
                )
            )

        if tail or extras:
            batches.append(
                _build_batch(
                    rank=len(batches) + 1,
                    batch_id="uniprot-tail-representatives",
                    source_id=source_id,
                    source_name=source_name,
                    source_role=source_role,
                    value_class="deferred-value",
                    filenames=tail + extras,
                    rationale=(
                        "Keep the lower-immediacy UniRef XML and compact representatives as a "
                        "second UniProt sidecar so the core lane can finish independently."
                    ),
                    expected_impact=(
                        "Completes the remaining UniProt coverage after the direct-value backbone "
                        "has landed."
                    ),
                )
            )

    string = source_lookup.get("string")
    if string:
        source_id = str(string.get("source_id") or "string").strip()
        source_name = str(string.get("source_name") or source_id).strip()
        source_role = role_map.get(_casefold(source_id), "unknown")
        filenames = [
            str(item.get("filename") or "").strip()
            for item in string.get("not_yet_started") or []
            if isinstance(item, dict) and str(item.get("filename") or "").strip()
        ]
        ordered = _sort_filenames(filenames, STRING_FILE_RANK)
        if ordered:
            batches.append(
                _build_batch(
                    rank=len(batches) + 1,
                    batch_id="string-guarded-network-pack",
                    source_id=source_id,
                    source_name=source_name,
                    source_role=source_role,
                    value_class="deferred-value",
                    filenames=ordered,
                    rationale=(
                        "STRING remains a guarded source, so keep the interaction tables, schema "
                        "exports, PDFs, and embeddings together in one sidecar lane."
                    ),
                    expected_impact=(
                        "Restores the remaining network reference payload without mixing guarded "
                        "STRING transfers across multiple sidecars."
                    ),
                )
            )

    source_roles = sorted({_casefold(row.get("source_id")) for row in source_rows if _casefold(row.get("source_id"))})
    source_role_counts = {}
    for role in sorted({role_map.get(source_id, "unknown") for source_id in source_roles}):
        source_role_counts[role] = sum(
            1 for source_id in source_roles if role_map.get(source_id, "unknown") == role
        )

    direct_value_file_count = sum(
        batch["file_count"] for batch in batches if batch["value_class"] == "direct-value"
    )
    deferred_value_file_count = sum(
        batch["file_count"] for batch in batches if batch["value_class"] == "deferred-value"
    )

    return {
        "schema_id": "proteosphere-broad-mirror-lane-plan-2026-03-31",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "planning",
        "basis": {
            "remaining_transfer_status_path": str(remaining_transfer_status_path).replace(
                "\\", "/"
            ),
            "source_policy_path": str(source_policy_path).replace("\\", "/"),
        },
        "summary": {
            "remaining_source_count": len(source_rows),
            "not_yet_started_file_count": int(
                remaining.get("summary", {}).get("not_yet_started_file_count") or 0
            ),
            "recommended_sidecar_batch_count": len(batches),
            "source_role_counts": source_role_counts,
            "direct_value_file_count": direct_value_file_count,
            "deferred_value_file_count": deferred_value_file_count,
        },
        "recommended_sidecar_launch_order": batches,
        "notes": [
            "This lane plan is an inference from the current remaining-transfer-status report and source policy roles.",
            "UniProt is split into a direct-value backbone batch and a deferred-value tail batch; STRING is kept as one guarded batch.",
            "No downloads are invented here: only files currently listed as not yet started are grouped into lanes.",
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Broad Mirror Lane Plan",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Basis: `{payload['basis']['remaining_transfer_status_path']}`",
        f"- Source policy: `{payload['basis']['source_policy_path']}`",
        f"- Remaining sources: `{summary['remaining_source_count']}`",
        f"- Not yet started files: `{summary['not_yet_started_file_count']}`",
        f"- Recommended sidecar batches: `{summary['recommended_sidecar_batch_count']}`",
        "",
        "## Launch Order",
        "",
        "| Rank | Batch | Source | Role | Value class | Files |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for batch in payload["recommended_sidecar_launch_order"]:
        lines.append(
            "| "
            + f"{batch['rank']} | "
            + f"`{batch['batch_id']}` | "
            + f"`{batch['source_id']}` | "
            + f"{batch['source_role']} | "
            + f"{batch['value_class']} | "
            + f"{batch['file_count']} |"
        )

    lines.extend(["", "## Batch Details", ""])
    for batch in payload["recommended_sidecar_launch_order"]:
        lines.append(
            f"### {batch['rank']}. `{batch['batch_id']}`"
            f" ({batch['value_class']})"
        )
        lines.append("")
        lines.append(f"- Source: `{batch['source_id']}` ({batch['source_role']})")
        lines.append(f"- Files: {', '.join(f'`{name}`' for name in batch['files'])}")
        lines.append(f"- Rationale: {batch['rationale']}")
        lines.append(f"- Expected impact: {batch['expected_impact']}")
        lines.append("")

    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit the broad-mirror lane plan.")
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

    payload = build_lane_plan(
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
            "Broad mirror lane plan exported: "
            f"batches={payload['summary']['recommended_sidecar_batch_count']} "
            f"files={payload['summary']['not_yet_started_file_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

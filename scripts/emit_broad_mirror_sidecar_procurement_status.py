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
DEFAULT_RUNTIME_DIR = REPO_ROOT / "artifacts" / "runtime"
DEFAULT_SEED_ROOT = REPO_ROOT / "data" / "raw" / "protein_data_scope_seed"
DEFAULT_JSON_OUTPUT = (
    REPO_ROOT / "artifacts" / "status" / "broad_mirror_sidecar_procurement_status.json"
)
DEFAULT_MARKDOWN_OUTPUT = (
    REPO_ROOT / "docs" / "reports" / "broad_mirror_sidecar_procurement_status.md"
)

SCARCORE = {"uniprot_sprot_varsplic.fasta.gz", "uniref100.fasta.gz", "uniref90.fasta.gz"}
SCARTAIL = {"uniref90.xml.gz", "uniref50.fasta.gz", "uniref50.xml.gz"}
SCARSCH = {
    "items_schema.v12.0.sql.gz",
    "network_schema.v12.0.sql.gz",
    "evidence_schema.v12.0.sql.gz",
    "database.schema.v12.0.pdf",
}
SCARPHYS = {
    "protein.physical.links.detailed.v12.0.txt.gz",
    "protein.physical.links.full.v12.0.txt.gz",
    "protein.network.embeddings.v12.0.h5",
    "protein.sequence.embeddings.v12.0.h5",
}


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object at {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _casefold(value: Any) -> str:
    return str(value or "").strip().casefold()


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _role_map(policy: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    tiers = policy.get("tiers") if isinstance(policy.get("tiers"), dict) else {}
    for role, payload in tiers.items():
        if not isinstance(payload, dict):
            continue
        for source_id in payload.get("source_ids") or []:
            key = _casefold(source_id)
            if key:
                result[key] = str(role)
    return result


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return [row for row in payload.get(key) or [] if isinstance(row, dict)]


def _files(rows: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str(row.get("filename") or "").strip()
            for row in rows
            if str(row.get("filename") or "").strip()
        },
        key=_casefold,
    )


def _partials(seed_root: Path, source_id: str, filenames: list[str]) -> list[str]:
    root = seed_root / source_id
    observed: list[str] = []
    for filename in filenames:
        for suffix in (".part", ".partial"):
            path = root / f"{filename}{suffix}"
            if path.exists():
                observed.append(_repo_relative(path))
    return sorted(observed, key=_casefold)


def _batch(
    *,
    rank: int,
    batch_id: str,
    source_id: str,
    source_name: str,
    source_role: str,
    value_class: str,
    files: list[str],
    runtime_dir: Path,
    seed_root: Path,
    launch_log_prefix: str,
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
        "files": files,
        "file_count": len(files),
        "launch_log": {
            "stdout": _repo_relative(runtime_dir / f"{launch_log_prefix}_stdout.log"),
            "stderr": _repo_relative(runtime_dir / f"{launch_log_prefix}_stderr.log"),
        },
        "observed_partial_files": _partials(seed_root, source_id, files),
        "rationale": rationale,
        "expected_impact": expected_impact,
    }


def build_sidecar_procurement_status(
    *,
    remaining_transfer_status_path: Path = DEFAULT_REMAINING_TRANSFER_STATUS_PATH,
    source_policy_path: Path = DEFAULT_SOURCE_POLICY_PATH,
    runtime_dir: Path = DEFAULT_RUNTIME_DIR,
    seed_root: Path = DEFAULT_SEED_ROOT,
) -> dict[str, Any]:
    remaining = _read_json(remaining_transfer_status_path)
    policy = _read_json(source_policy_path)
    role_map = _role_map(policy)

    sources = { _casefold(row.get("source_id")): row for row in _rows(remaining, "sources") }
    uniprot = sources.get("uniprot")
    string = sources.get("string")
    if not uniprot or not string:
        raise ValueError("remaining transfer status must include uniprot and string")

    active_rows = _rows(remaining, "actively_transferring_now")
    sidecar_batches = [
        _batch(
            rank=1,
            batch_id="uniprot-core",
            source_id="uniprot",
            source_name=str(uniprot.get("source_name") or "uniprot"),
            source_role=role_map.get("uniprot", "unknown"),
            value_class="direct-value",
            files=sorted(SCARCORE, key=_casefold),
            runtime_dir=runtime_dir,
            seed_root=seed_root,
            launch_log_prefix="uniprot_core_backbone",
            rationale="Direct-value UniProt backbone lane for the core Swiss-Prot and UniRef FASTA files.",
            expected_impact="Restores the core sequence reference layer without widening the active bulk jobs.",
        ),
        _batch(
            rank=2,
            batch_id="uniprot-tail",
            source_id="uniprot",
            source_name=str(uniprot.get("source_name") or "uniprot"),
            source_role=role_map.get("uniprot", "unknown"),
            value_class="deferred-value",
            files=sorted(SCARTAIL, key=_casefold),
            runtime_dir=runtime_dir,
            seed_root=seed_root,
            launch_log_prefix="uniprot_tail_sidecar",
            rationale="Deferred-value UniProt tail lane for the remaining UniRef XML and representative FASTA files.",
            expected_impact="Completes the remaining UniProt sidecar lane after the core batch is underway.",
        ),
        _batch(
            rank=3,
            batch_id="string-schema",
            source_id="string",
            source_name=str(string.get("source_name") or "string"),
            source_role=role_map.get("string", "unknown"),
            value_class="deferred-value",
            files=sorted(SCARSCH, key=_casefold),
            runtime_dir=runtime_dir,
            seed_root=seed_root,
            launch_log_prefix="string_schema_sidecar",
            rationale="Guarded STRING schema lane for the schema exports and reference PDF.",
            expected_impact="Restores the STRING metadata backbone while leaving the bulk lanes alone.",
        ),
        _batch(
            rank=4,
            batch_id="string-physical-tail",
            source_id="string",
            source_name=str(string.get("source_name") or "string"),
            source_role=role_map.get("string", "unknown"),
            value_class="deferred-value",
            files=sorted(SCARPHYS, key=_casefold),
            runtime_dir=runtime_dir,
            seed_root=seed_root,
            launch_log_prefix="string_physical_tail_sidecar",
            rationale="Guarded STRING physical-tail lane for the remaining physical-link and embedding files.",
            expected_impact="Finishes the remaining STRING payload without inventing new downloads.",
        ),
    ]

    sidecar_files = {filename for batch in sidecar_batches for filename in batch["files"]}
    active_names = {str(row.get("filename") or "").strip() for row in active_rows if str(row.get("filename") or "").strip()}
    sidecar_overlap = sorted(active_names & sidecar_files, key=_casefold)
    uncovered_rows = [
        row for row in _rows(remaining, "not_yet_started") if str(row.get("filename") or "").strip() not in sidecar_files
    ]
    bulk_rows = [row for row in active_rows if str(row.get("filename") or "").strip() not in sidecar_files]

    source_role_counts = {
        role: sum(1 for row in sources.values() if role_map.get(_casefold(row.get("source_id")), "unknown") == role)
        for role in sorted({role_map.get(_casefold(row.get("source_id")), "unknown") for row in sources.values()})
    }

    return {
        "schema_id": "proteosphere-broad-mirror-sidecar-procurement-status-2026-03-31",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "planning",
        "basis": {
            "remaining_transfer_status_path": _repo_relative(remaining_transfer_status_path),
            "source_policy_path": _repo_relative(source_policy_path),
            "runtime_dir": _repo_relative(runtime_dir),
        },
        "summary": {
            "remaining_file_count": len(active_rows) + len(_rows(remaining, "not_yet_started")),
            "active_sidecar_file_count": len(sidecar_files),
            "active_bulk_file_count": len(bulk_rows),
            "still_uncovered_file_count": len(uncovered_rows),
            "active_sidecar_overlap_file_count": len(sidecar_overlap),
            "active_sidecar_overlap_filenames": sidecar_overlap,
            "active_sidecar_count": len(sidecar_batches),
            "active_bulk_source_count": len(
                {str(row.get("source_id") or "").strip() for row in bulk_rows if str(row.get("source_id") or "").strip()}
            ),
            "source_role_counts": source_role_counts,
        },
        "active_sidecars": sidecar_batches,
        "active_bulk": [
            {
                "source_id": row.get("source_id"),
                "source_name": row.get("source_name"),
                "source_role": role_map.get(_casefold(row.get("source_id")), "unknown"),
                "filename": row.get("filename"),
                "gap_kind": row.get("gap_kind"),
                "evidence": row.get("evidence"),
            }
            for row in bulk_rows
        ],
        "still_uncovered_backlog": [
            {
                "source_id": row.get("source_id"),
                "source_name": row.get("source_name"),
                "source_role": role_map.get(_casefold(row.get("source_id")), "unknown"),
                "filename": row.get("filename"),
                "gap_kind": row.get("gap_kind"),
            }
            for row in uncovered_rows
        ],
        "notes": [
            "This is a lane-level snapshot: the four launched sidecars cover the still-not-started backlog, while the current transfer-status active rows are left in the bulk bucket.",
            f"The transfer-status rows currently double-count {len(sidecar_overlap)} filename(s) across active and not-yet-started evidence; those overlaps are listed in the summary.",
            "Runtime log presence is used as launch evidence; the report does not attempt to infer byte-level ownership from quiet logs.",
            "Any files not covered by those two buckets would show up in still_uncovered_backlog; on the current live state that bucket is empty.",
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Broad Mirror Sidecar Procurement Status",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Basis: `{payload['basis']['remaining_transfer_status_path']}`",
        f"- Source policy: `{payload['basis']['source_policy_path']}`",
        f"- Runtime dir: `{payload['basis']['runtime_dir']}`",
        f"- Remaining files: `{summary['remaining_file_count']}`",
        f"- Active sidecar files: `{summary['active_sidecar_file_count']}`",
        f"- Active bulk files: `{summary['active_bulk_file_count']}`",
        f"- Still uncovered: `{summary['still_uncovered_file_count']}`",
        f"- Active/not-yet-started overlap: `{summary['active_sidecar_overlap_file_count']}`",
        "",
        "## Active Sidecars",
        "",
        "| Rank | Batch | Source | Role | Value class | Files |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for batch in payload["active_sidecars"]:
        lines.append(
            "| "
            + f"{batch['rank']} | "
            + f"`{batch['batch_id']}` | "
            + f"`{batch['source_id']}` | "
            + f"{batch['source_role']} | "
            + f"{batch['value_class']} | "
            + f"{batch['file_count']} |"
        )
    lines.extend(["", "## Active Bulk", ""])
    for row in payload["active_bulk"]:
        lines.append(f"- `{row['source_id']}`: `{row['filename']}` ({row['gap_kind']})")
    lines.extend(["", "## Still-Uncovered Backlog", ""])
    if payload["still_uncovered_backlog"]:
        for row in payload["still_uncovered_backlog"]:
            lines.append(f"- `{row['source_id']}`: `{row['filename']}` ({row['gap_kind']})")
    else:
        lines.append("- none")
    lines.extend(["", "## Evidence", ""])
    for batch in payload["active_sidecars"]:
        logs = batch["launch_log"]
        lines.append(
            f"- `{batch['batch_id']}`: logs={', '.join([p for p in logs.values() if p])}; "
            f"partials={', '.join(batch['observed_partial_files']) or 'none'}"
        )
    if payload["summary"]["active_sidecar_overlap_filenames"]:
        lines.extend(["", "## Overlap", ""])
        lines.append(
            "- "
            + ", ".join(
                f"`{name}`" for name in payload["summary"]["active_sidecar_overlap_filenames"]
            )
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit a narrow broad-mirror sidecar procurement slice.")
    parser.add_argument("--remaining-transfer-status", type=Path, default=DEFAULT_REMAINING_TRANSFER_STATUS_PATH)
    parser.add_argument("--source-policy", type=Path, default=DEFAULT_SOURCE_POLICY_PATH)
    parser.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME_DIR)
    parser.add_argument("--seed-root", type=Path, default=DEFAULT_SEED_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-markdown", action="store_true")
    args = parser.parse_args(argv)

    payload = build_sidecar_procurement_status(
        remaining_transfer_status_path=args.remaining_transfer_status,
        source_policy_path=args.source_policy,
        runtime_dir=args.runtime_dir,
        seed_root=args.seed_root,
    )
    _write_json(args.output, payload)
    if not args.no_markdown:
        _write_text(args.markdown_output, render_markdown(payload))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Broad mirror sidecar procurement status exported: "
            f"sidecars={payload['summary']['active_sidecar_count']} "
            f"active_bulk={payload['summary']['active_bulk_file_count']} "
            f"uncovered={payload['summary']['still_uncovered_file_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

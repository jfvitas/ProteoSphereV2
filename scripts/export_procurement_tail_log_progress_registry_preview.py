from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.tasklib import load_json, save_json  # noqa: E402

DEFAULT_REMAINING_TRANSFER_STATUS_PATH = (
    REPO_ROOT / "artifacts" / "status" / "broad_mirror_remaining_transfer_status.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "procurement_tail_log_progress_registry_preview.json"
)

_PROGRESS_RE = re.compile(
    r"""
    ^\s*
    (?P<filename>.+?):\s+
    (?P<percent>\d+(?:\.\d+)?)%\s+
    (?P<current>\d+(?:\.\d+)?)\s+(?P<current_unit>[KMGTP]B)/
    (?P<total>\d+(?:\.\d+)?)\s+(?P<total_unit>[KMGTP]B)
    (?:\s+(?P<speed>\d+(?:\.\d+)?)\s+(?P<speed_unit>[KMGTP]B)/s)?
    """,
    re.VERBOSE,
)

_UNIT_SCALE = {
    "KB": 1024,
    "MB": 1024**2,
    "GB": 1024**3,
    "TB": 1024**4,
    "PB": 1024**5,
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _load_json_or_default(path: Path, default: Any) -> Any:
    return load_json(path, default) if path.exists() else default


def _normalize_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _bytes_from_value(value: str, unit: str) -> int:
    return int(float(value) * _UNIT_SCALE[unit])


def _tail_lines(path: Path, *, line_limit: int = 400) -> list[str]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    if line_limit <= 0:
        return lines
    return lines[-line_limit:]


def _match_progress_line(lines: list[str], filename: str) -> dict[str, Any] | None:
    filename = filename.strip()
    for line in reversed(lines):
        match = _PROGRESS_RE.match(line)
        if not match:
            continue
        if match.group("filename").strip() != filename:
            continue
        speed_value = match.group("speed")
        speed_unit = match.group("speed_unit")
        return {
            "percent_complete": float(match.group("percent")),
            "current_bytes_from_log": _bytes_from_value(
                match.group("current"), match.group("current_unit")
            ),
            "total_bytes_from_log": _bytes_from_value(
                match.group("total"), match.group("total_unit")
            ),
            "speed_bytes_per_second_from_log": (
                _bytes_from_value(speed_value, speed_unit)
                if speed_value and speed_unit
                else None
            ),
            "matched_line": line.strip(),
        }
    return None


def build_procurement_tail_log_progress_registry_preview(
    remaining_transfer_status: dict[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    observed_at = observed_at or _utc_now()
    remaining_transfer_status = (
        remaining_transfer_status if isinstance(remaining_transfer_status, dict) else {}
    )

    active_rows = _normalize_rows(remaining_transfer_status.get("actively_transferring_now"))
    rows: list[dict[str, Any]] = []
    parsed_count = 0
    exact_total_count = 0

    for row in active_rows:
        filename = str(row.get("filename") or "").strip()
        evidence_rows = _normalize_rows(row.get("evidence"))
        log_refs = [
            REPO_ROOT / str(evidence.get("log"))
            for evidence in evidence_rows
            if evidence.get("kind") == "stdout_log_tail" and evidence.get("log")
        ]
        match_payload = None
        matched_log = None
        for log_path in log_refs:
            match_payload = _match_progress_line(_tail_lines(log_path), filename)
            if match_payload is not None:
                matched_log = log_path
                break

        row_payload = {
            "source_id": row.get("source_id"),
            "source_name": row.get("source_name"),
            "filename": filename,
            "category": row.get("category"),
            "matched_log": str(matched_log).replace("\\", "/") if matched_log else None,
            "match_state": "no_progress_line_found",
        }
        if match_payload is not None:
            parsed_count += 1
            if match_payload.get("total_bytes_from_log"):
                exact_total_count += 1
            row_payload.update(match_payload)
            row_payload["match_state"] = "progress_line_parsed"
        rows.append(row_payload)

    if not rows:
        registry_state = "no_tail_rows"
        next_action = "No authoritative tail rows were available for log-progress parsing."
    elif parsed_count == len(rows):
        registry_state = "fully_parsed"
        next_action = (
            "Use the parsed log totals as the primary completion estimate "
            "for the remaining tail."
        )
    elif parsed_count > 0:
        registry_state = "partially_parsed"
        next_action = (
            "Use parsed totals where available and keep the unmatched tail "
            "rows under observation."
        )
    else:
        registry_state = "no_progress_match"
        next_action = "No matching progress lines were found; fall back to growth-only monitoring."

    return {
        "artifact_id": "procurement_tail_log_progress_registry_preview",
        "schema_id": "proteosphere-procurement-tail-log-progress-registry-preview-2026-04-03",
        "status": "report_only",
        "generated_at": observed_at.isoformat(),
        "summary": {
            "registry_state": registry_state,
            "tail_row_count": len(rows),
            "parsed_row_count": parsed_count,
            "exact_total_count": exact_total_count,
            "non_mutating": True,
            "report_only": True,
        },
        "rows": rows,
        "next_suggested_action": next_action,
        "source_artifacts": {
            "broad_mirror_remaining_transfer_status": str(
                DEFAULT_REMAINING_TRANSFER_STATUS_PATH
            ).replace("\\", "/")
        },
        "truth_boundary": {
            "summary": (
                "This is a report-only registry of progress totals parsed from "
                "the current tail-download stdout logs."
            ),
            "report_only": True,
            "non_mutating": True,
            "log_parse_only": True,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a report-only procurement tail log progress registry preview."
    )
    parser.add_argument(
        "--remaining-transfer-status-path",
        type=Path,
        default=DEFAULT_REMAINING_TRANSFER_STATUS_PATH,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSON)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_procurement_tail_log_progress_registry_preview(
        _load_json_or_default(args.remaining_transfer_status_path, {})
    )
    save_json(args.output, payload)
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

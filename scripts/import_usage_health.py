from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "artifacts" / "status" / "usage_health_import_preview.json"
DEFAULT_SCHEMA_ID = "proteosphere-usage-health-import-preview-2026-04-03"

AGGREGATE_FIELDS = (
    "active_users",
    "sessions",
    "events",
    "page_views",
    "requests",
    "errors",
    "error_count",
    "crashes",
    "crash_count",
    "warnings",
)

WINDOW_FIELDS = (
    "window_start",
    "window_end",
    "observed_at",
    "sample_start",
    "sample_end",
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else None


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _first_present(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in payload and payload[key] not in (None, "", [], {}, ()):
            return payload[key]
    return None


def _extract_usage_signal(source_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    signal: dict[str, Any] = {
        "source_path": str(source_path),
        "source_name": payload.get("source_name") or source_path.stem,
        "status": "absent",
        "privacy_safe": True,
        "window": {},
        "counts": {},
        "missing_fields": [],
        "notes": [],
    }

    window = {
        field: payload.get(field)
        for field in WINDOW_FIELDS
        if payload.get(field) not in (None, "")
    }
    if window:
        signal["window"] = window

    counts: dict[str, int] = {}
    present_fields: list[str] = []
    for field in AGGREGATE_FIELDS:
        value = _coerce_int(payload.get(field))
        if value is None:
            continue
        counts[field] = value
        present_fields.append(field)

    if counts:
        signal["counts"] = counts

    signals = payload.get("signals")
    if isinstance(signals, dict):
        for field, value in signals.items():
            normalized = _coerce_float(value)
            if normalized is not None:
                counts.setdefault(field, int(normalized) if normalized.is_integer() else normalized)

    missing_fields = [
        field for field in ("active_users", "sessions", "events") if field not in counts
    ]
    signal["missing_fields"] = missing_fields

    if counts and not missing_fields:
        signal["status"] = "complete"
    elif counts:
        signal["status"] = "partial"
    elif payload.get("status") in {"partial", "absent", "complete"}:
        signal["status"] = str(payload.get("status"))

    usage_summary = payload.get("summary")
    if isinstance(usage_summary, dict):
        summary = {
            key: usage_summary.get(key)
            for key in ("health", "release_phase", "monitoring_tier")
            if usage_summary.get(key) not in (None, "")
        }
        if summary:
            signal["notes"].append("summary_fields_present")
            signal["summary"] = summary

    if payload.get("privacy_safe") is False:
        signal["privacy_safe"] = False

    privacy_sensitive_keys = {
        "user_id",
        "user_ids",
        "email",
        "emails",
        "ip",
        "ip_address",
        "session_id",
        "client_id",
    }
    if any(key for key in payload if key.lower() in privacy_sensitive_keys):
        signal["notes"].append("identifier_fields_ignored")

    if not counts and not signal["window"]:
        signal["notes"].append("no_aggregate_usage_signals_present")
    elif missing_fields:
        signal["notes"].append("partial_aggregate_usage_signals")
    else:
        signal["notes"].append("complete_aggregate_usage_signals")

    return signal


def build_usage_health_import_report(source_paths: list[Path]) -> dict[str, Any]:
    signals: list[dict[str, Any]] = []
    missing_sources: list[str] = []
    for source_path in source_paths:
        payload = read_json(source_path)
        if payload is None:
            missing_sources.append(str(source_path))
            continue
        signals.append(_extract_usage_signal(source_path, payload))

    present_count = len(signals)
    complete_count = sum(1 for signal in signals if signal["status"] == "complete")
    partial_count = sum(1 for signal in signals if signal["status"] == "partial")
    absent_count = sum(1 for signal in signals if signal["status"] == "absent")
    privacy_safe = (
        all(signal.get("privacy_safe") is True for signal in signals)
        if signals
        else True
    )

    if present_count == 0:
        status = "absent"
    elif partial_count > 0 or missing_sources:
        status = "partial"
    else:
        status = "complete"

    report = {
        "artifact_id": "usage_health_import_preview",
        "schema_id": DEFAULT_SCHEMA_ID,
        "status": status,
        "generated_at": utc_now(),
        "privacy_boundary": {
            "privacy_safe": privacy_safe,
            "raw_user_identifiers_imported": False,
            "identifier_columns_preserved": False,
        },
        "summary": {
            "source_count": len(source_paths),
            "present_source_count": present_count,
            "missing_source_count": len(missing_sources),
            "complete_signal_count": complete_count,
            "partial_signal_count": partial_count,
            "absent_signal_count": absent_count,
        },
        "sources": signals,
        "missing_sources": missing_sources,
        "verdict": (
            "usable_with_caveats"
            if status in {"complete", "partial"}
            else "audit_only"
        ),
        "truth_boundary": {
            "report_only": True,
            "non_mutating": True,
            "privacy_safe": True,
            "supported_signals": [
                "active_users",
                "sessions",
                "events",
                "page_views",
                "requests",
                "errors",
                "crashes",
                "warnings",
            ],
            "forbidden_signals": [
                "raw_user_ids",
                "emails",
                "ip_addresses",
                "session_ids",
                "client_ids",
            ],
        },
    }
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import privacy-safe usage health signals into a report-only monitoring preview."
        )
    )
    parser.add_argument(
        "--input",
        action="append",
        type=Path,
        default=[],
        help="Privacy-safe usage-health JSON payload to import. Repeatable.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Print the generated report to stdout.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_usage_health_import_report(list(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.print_json:
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

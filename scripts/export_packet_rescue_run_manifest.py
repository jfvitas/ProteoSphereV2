from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRIORITY_PATH = REPO_ROOT / "artifacts" / "status" / "p32_packet_rescue_priority.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "artifacts" / "status" / "p32_packet_rescue_run_manifest.json"


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes, Path)):
        return (values,)
    if isinstance(values, tuple):
        return values
    if isinstance(values, list):
        return tuple(values)
    if isinstance(values, dict):
        return tuple(values.values())
    try:
        return tuple(values)
    except TypeError:
        return (values,)


def _dedupe_text(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _json_path(path: Path) -> str:
    return path.resolve().as_posix()


def _required_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"priority artifact missing required mapping: {key}")
    return value


def _required_sequence(payload: dict[str, Any], key: str) -> tuple[Any, ...]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"priority artifact missing required sequence: {key}")
    return tuple(value)


def _normalize_route(
    route: dict[str, Any],
    *,
    accession: str,
    accession_rank: int,
    route_rank: int,
    source_priority_artifact: Path,
    source_priority_generated_at: str,
) -> dict[str, Any]:
    route_text = _clean_text(route.get("route"))
    modality = _clean_text(route.get("modality"))
    confidence = _clean_text(route.get("confidence"))
    why = _clean_text(route.get("why"))
    sources = list(_dedupe_text(route.get("sources") or ()))

    if not route_text:
        raise ValueError(f"priority route missing route text for accession {accession}")
    if not modality:
        raise ValueError(f"priority route missing modality for accession {accession}")
    if not confidence:
        raise ValueError(f"priority route missing confidence for accession {accession}")
    if not why:
        raise ValueError(f"priority route missing why text for accession {accession}")
    if not sources:
        raise ValueError(f"priority route missing sources for accession {accession}")

    return {
        "accession": accession,
        "accession_rank": accession_rank,
        "route_rank": route_rank,
        "kind": "primary" if route_rank == 1 else "fallback",
        "modality": modality,
        "route": route_text,
        "sources": sources,
        "confidence": confidence,
        "why": why,
        "execution_state": "queued",
        "provenance": {
            "source_priority_artifact": _json_path(source_priority_artifact),
            "source_priority_artifact_generated_at": source_priority_generated_at,
            "source_priority_accession_rank": accession_rank,
            "source_priority_route_rank": route_rank,
            "source_priority_route_kind": "primary" if route_rank == 1 else "fallback",
            "source_priority_route_count": None,
        },
    }


def _sort_priority_rows(rows: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    def _row_rank(row: dict[str, Any]) -> tuple[int, str]:
        rank = row.get("rank")
        try:
            rank_value = int(rank)
        except (TypeError, ValueError):
            rank_value = 10**9
        return rank_value, _clean_text(row.get("accession")).casefold()

    return sorted((dict(row) for row in rows), key=_row_rank)


def build_packet_rescue_run_manifest(
    *,
    priority_path: Path = DEFAULT_PRIORITY_PATH,
) -> dict[str, Any]:
    if not priority_path.is_file():
        raise FileNotFoundError(priority_path)

    payload = _read_json(priority_path)
    if not isinstance(payload, dict):
        raise TypeError("packet rescue priority artifact must be a JSON object")

    priority_ranking = _sort_priority_rows(_required_sequence(payload, "priority_ranking"))
    source_availability = _required_mapping(payload, "source_availability")
    dashboard_summary = _required_mapping(payload, "dashboard_summary")

    accession_plans: list[dict[str, Any]] = []
    manifest_steps: list[dict[str, Any]] = []
    for accession_rank, row in enumerate(priority_ranking, start=1):
        accession = _clean_text(row.get("accession"))
        canonical_id = _clean_text(row.get("canonical_id"))
        packet_status = _clean_text(row.get("packet_status"))
        missing_modalities = list(_dedupe_text(row.get("missing_modalities") or ()))
        recommended_routes = _required_sequence(row, "recommended_routes")
        normalized_routes: list[dict[str, Any]] = []
        for route_rank, route in enumerate(recommended_routes, start=1):
            if not isinstance(route, dict):
                raise ValueError(f"priority route must be a JSON object for accession {accession}")
            normalized_route = _normalize_route(
                route,
                accession=accession,
                accession_rank=accession_rank,
                route_rank=route_rank,
                source_priority_artifact=priority_path,
                source_priority_generated_at=_clean_text(payload.get("generated_at")),
            )
            normalized_route["provenance"]["source_priority_route_count"] = len(recommended_routes)
            step_id = f"rescue-{accession_rank:02d}-{route_rank:02d}"
            manifest_steps.append({"step_id": step_id, **normalized_route})
            normalized_routes.append({**normalized_route, "step_id": step_id})

        primary_route = normalized_routes[0] if normalized_routes else None
        fallback_routes = normalized_routes[1:] if len(normalized_routes) > 1 else []
        accession_plans.append(
            {
                "rank": accession_rank,
                "accession": accession,
                "canonical_id": canonical_id,
                "packet_status": packet_status,
                "missing_modalities": missing_modalities,
                "route_count": len(normalized_routes),
                "primary_route": primary_route,
                "fallback_routes": fallback_routes,
                "step_ids": [route["step_id"] for route in normalized_routes],
                "execution_state": "queued",
                "provenance": {
                    "source_priority_artifact": _json_path(priority_path),
                    "source_priority_artifact_generated_at": _clean_text(payload.get("generated_at")),
                    "source_priority_rank": accession_rank,
                    "source_priority_route_count": len(normalized_routes),
                    "retained_route_ranks": [route["route_rank"] for route in normalized_routes],
                },
                "truth_boundary": (
                    "Queued planning only; keep all alternates and do not infer completion "
                    "or fill missing evidence from other sources."
                ),
            }
        )

    return {
        "schema_id": "proteosphere-p32-packet-rescue-run-manifest-2026-03-30",
        "report_type": "packet_rescue_run_manifest",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "status": "planning_only",
        "source_priority_artifact": _json_path(priority_path),
        "source_priority_artifact_generated_at": _clean_text(payload.get("generated_at")),
        "source_priority_artifact_schema_id": _clean_text(payload.get("schema_id")),
        "source_priority_summary": {
            "dashboard_summary": dashboard_summary,
            "source_availability": source_availability,
            "bindingdb_snapshot_behavior": list(_iter_values(payload.get("bindingdb_snapshot_behavior") or ())),
            "canonical_presence": list(_iter_values(payload.get("canonical_presence") or ())),
        },
        "execution_policy": {
            "selection_rule": (
                "Use the first recommended route as the primary execution target for each "
                "accession, then preserve the remaining routes as ordered fallbacks."
            ),
            "tie_rule": (
                "Do not invent a new tie-breaker; route rank from the priority artifact is the "
                "only ordering signal."
            ),
            "dissent_rule": (
                "If a route returns null, empty, or conflicting evidence, record it as unresolved "
                "and keep the manifest open rather than collapsing values."
            ),
            "provenance_rule": (
                "Every step must retain the source priority artifact path, accession rank, route "
                "rank, route kind, source list, confidence, and why text."
            ),
            "multi_value_rule": (
                "Keep alternate routes when the artifact provides them; do not collapse fallback "
                "routes into the primary route."
            ),
        },
        "current_deficit_accessions": [plan["accession"] for plan in accession_plans],
        "accession_plans": accession_plans,
        "manifest_steps": manifest_steps,
        "manifest_summary": {
            "accession_count": len(accession_plans),
            "step_count": len(manifest_steps),
            "primary_step_count": sum(1 for step in manifest_steps if step["kind"] == "primary"),
            "fallback_step_count": sum(1 for step in manifest_steps if step["kind"] == "fallback"),
        },
        "truth_boundary_note": (
            "This manifest is derived only from the packet rescue priority artifact. It is "
            "execution-ready in ordering, but it does not invent evidence, promote missing "
            "modalities, or collapse alternate routes."
        ),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the packet rescue run manifest from the priority artifact."
    )
    parser.add_argument("--priority", type=Path, default=DEFAULT_PRIORITY_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_packet_rescue_run_manifest(priority_path=args.priority)
    _write_json(args.output, payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Packet rescue run manifest exported: "
            f"accessions={payload['manifest_summary']['accession_count']} "
            f"steps={payload['manifest_summary']['step_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

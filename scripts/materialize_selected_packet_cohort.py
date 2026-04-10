from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from execution.materialization.training_packet_materializer import (  # noqa: E402
    TrainingPacketRequest,
    materialize_training_packets,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BALANCED_PLAN_PATH = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "balanced_dataset_plan.json"
)
DEFAULT_AVAILABLE_PAYLOADS_PATH = None
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "data" / "packages"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "packages" / "selected_cohort_materialization.json"
DEFAULT_REQUESTED_MODALITIES = ("sequence", "structure", "ligand", "ppi")


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
    if isinstance(values, Mapping):
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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_fingerprint(payload: Any) -> str:
    return _sha256_bytes(json.dumps(payload, sort_keys=True).encode("utf-8"))


def _status_rank(status: str) -> int:
    return {"unresolved": 0, "partial": 1, "complete": 2}.get(_clean_text(status), -1)


def _report_quality_key(payload: Mapping[str, Any]) -> tuple[int, int, int, int, int]:
    summary = payload.get("summary")
    if not isinstance(summary, Mapping):
        summary = {}
    return (
        _status_rank(_clean_text(payload.get("status"))),
        int(summary.get("complete_count") or 0),
        -int(summary.get("unresolved_count") or 0),
        -int(summary.get("partial_count") or 0),
        int(summary.get("packet_count") or 0),
    )


def _should_replace_report(candidate: Mapping[str, Any], output_path: Path) -> bool:
    if not output_path.exists():
        return True
    existing = _read_json(output_path)
    if not isinstance(existing, Mapping):
        return True
    return _report_quality_key(candidate) >= _report_quality_key(existing)


def _load_json_payload(path: Path | None) -> tuple[dict[str, Any], dict[str, Any]]:
    if path is None:
        return {}, {"path": "", "exists": False, "count": 0}
    if not path.exists():
        return {}, {"path": str(path), "exists": False, "count": 0}
    payload = _read_json(path)
    if isinstance(payload, Mapping):
        candidate = payload.get("available_payloads")
        if isinstance(candidate, Mapping):
            data = dict(candidate)
        else:
            candidate = payload.get("artifacts")
            if isinstance(candidate, Mapping):
                data = dict(candidate)
            else:
                data = dict(payload)
        available_payloads_sha256 = _json_fingerprint(data)
        registry_fingerprints = {
            "available_payloads_sha256": available_payloads_sha256,
            "build_sha256": _json_fingerprint(
                {
                    "file_sha256": _file_sha256(path),
                    "available_payloads_sha256": available_payloads_sha256,
                    "count": len(data),
                }
            ),
            "digest_basis": "sorted_json_content",
        }
        source = {
            "path": str(path),
            "exists": True,
            "count": len(data),
            "file_sha256": _file_sha256(path),
            "available_payloads_sha256": available_payloads_sha256,
            "registry_fingerprints": registry_fingerprints,
        }
        if isinstance(payload.get("input_fingerprints"), Mapping):
            source["input_fingerprints"] = dict(payload["input_fingerprints"])
        if isinstance(payload.get("registry_fingerprints"), Mapping):
            merged_fingerprints = dict(registry_fingerprints)
            merged_fingerprints.update(dict(payload["registry_fingerprints"]))
            source["registry_fingerprints"] = merged_fingerprints
        return data, source
    raise TypeError(f"expected a JSON object in {path}")


def _decode_payload_entry(value: Any) -> Any:
    if isinstance(value, Mapping):
        kind = _clean_text(value.get("kind"))
        if kind == "file_ref":
            file_path = _clean_text(value.get("path"))
            if not file_path:
                raise ValueError("file_ref payload is missing path")
            return Path(file_path)
        return {str(key): _decode_payload_entry(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_decode_payload_entry(item) for item in value]
    return value


def _load_plan(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    if not isinstance(payload, Mapping):
        raise TypeError("balanced plan must be a JSON object")
    return dict(payload)


def _plan_rows(payload: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    for key in ("selected_rows", "selected_examples", "rows", "proposals"):
        rows = payload.get(key) or ()
        if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes)):
            return tuple(dict(row) for row in rows if isinstance(row, Mapping))
    return ()


def _requested_modalities_from_row(row: Mapping[str, Any]) -> tuple[str, ...]:
    expectation = row.get("packet_expectation")
    if isinstance(expectation, Mapping):
        requested = _dedupe_text(
            (
                *(_iter_values(expectation.get("present_modalities"))),
                *(_iter_values(expectation.get("missing_modalities"))),
            )
        )
        if requested:
            return requested
    requested = _dedupe_text(row.get("requested_modalities") or ())
    if requested:
        return requested
    return DEFAULT_REQUESTED_MODALITIES


def _source_refs_for_row(row: Mapping[str, Any], modality: str, accession: str) -> tuple[str, ...]:
    modality_sources = row.get("modality_sources")
    if isinstance(modality_sources, Mapping):
        candidate = modality_sources.get(modality)
        refs = _dedupe_text(candidate or ())
        if refs:
            return refs
    return (f"{modality}:{accession}",)


def _raw_manifest_ids(row: Mapping[str, Any]) -> tuple[str, ...]:
    truth = row.get("truth")
    if isinstance(truth, Mapping):
        registry = truth.get("registry")
        if isinstance(registry, Mapping):
            refs = _dedupe_text(registry.get("source_manifest_ids") or ())
            if refs:
                return refs
    return _dedupe_text(row.get("raw_manifest_ids") or ())


def _provenance_refs(row: Mapping[str, Any]) -> tuple[str, ...]:
    refs = _dedupe_text(row.get("evidence_refs") or ())
    if refs:
        return refs
    return _dedupe_text(row.get("provenance_refs") or ())


def _notes_for_row(row: Mapping[str, Any]) -> tuple[str, ...]:
    notes: list[str] = []
    notes.extend(_dedupe_text(row.get("notes") or ()))
    expectation = row.get("packet_expectation")
    if isinstance(expectation, Mapping):
        notes.extend(_dedupe_text(expectation.get("notes") or ()))
        source = _clean_text(expectation.get("source"))
        if source:
            notes.append(f"packet_expectation_source={source}")
    status = _clean_text(row.get("status"))
    if status:
        notes.append(f"balanced_plan_status={status}")
    return _dedupe_text(notes)


def _build_request(row: Mapping[str, Any]) -> TrainingPacketRequest:
    accession = _clean_text(row.get("accession"))
    if not accession:
        raise ValueError("balanced-plan row is missing accession")
    canonical_id = _clean_text(row.get("canonical_id")) or f"protein:{accession}"
    requested_modalities = _requested_modalities_from_row(row)
    modality_sources = {
        modality: _source_refs_for_row(row, modality, accession)
        for modality in requested_modalities
    }
    planning_index_ref = _clean_text(row.get("planning_index_ref")) or None
    if planning_index_ref is None:
        truth = row.get("truth")
        if isinstance(truth, Mapping):
            planning_index_ref = _clean_text(truth.get("planning_index_ref")) or None
    return TrainingPacketRequest(
        packet_id=_clean_text(row.get("packet_id")) or f"packet-{accession}",
        accession=accession,
        canonical_id=canonical_id,
        requested_modalities=requested_modalities,
        modality_sources=modality_sources,
        planning_index_ref=planning_index_ref,
        split_name=_clean_text(row.get("split")) or None,
        raw_manifest_ids=_raw_manifest_ids(row),
        provenance_refs=_provenance_refs(row),
        notes=_notes_for_row(row),
        metadata={
            "balanced_plan_row": dict(row),
            "cohort_bucket": _clean_text(row.get("cohort_bucket")) or None,
            "score_trace": row.get("score_trace"),
            "packet_expectation": row.get("packet_expectation"),
        },
    )


def _load_available_payloads(path: Path | None) -> tuple[dict[str, Any], dict[str, Any]]:
    payloads, source = _load_json_payload(path)
    return (
        {ref: _decode_payload_entry(payload) for ref, payload in payloads.items()},
        source,
    )


def _packet_expectation_summary(row: Mapping[str, Any]) -> dict[str, Any]:
    expectation = row.get("packet_expectation")
    if not isinstance(expectation, Mapping):
        return {
            "status": None,
            "source": None,
            "requested_modalities": [],
            "present_modalities": [],
            "missing_modalities": [],
            "packet_ready": None,
        }
    return {
        "status": _clean_text(expectation.get("status")) or None,
        "source": _clean_text(expectation.get("source")) or None,
        "requested_modalities": list(
            _dedupe_text(expectation.get("requested_modalities") or ())
        ),
        "present_modalities": list(_dedupe_text(expectation.get("present_modalities") or ())),
        "missing_modalities": list(_dedupe_text(expectation.get("missing_modalities") or ())),
        "packet_ready": expectation.get("packet_ready"),
    }


def _packet_expectation_status(row: Mapping[str, Any]) -> str:
    expectation = row.get("packet_expectation")
    if isinstance(expectation, Mapping):
        return _clean_text(expectation.get("status")) or "unknown"
    return "unknown"


def _packet_row_summary(row: Any, expected_status: str | None = None) -> dict[str, Any]:
    payload = {
        "packet_id": row.packet_id,
        "accession": row.accession,
        "canonical_id": row.canonical_id,
        "status": row.status,
        "packet_dir": row.packet_dir,
        "manifest_path": row.manifest_path,
        "requested_modalities": list(row.requested_modalities),
        "present_modalities": list(row.present_modalities),
        "missing_modalities": list(row.missing_modalities),
        "raw_manifest_ids": list(row.raw_manifest_ids),
        "provenance_refs": list(row.provenance_refs),
        "notes": list(row.notes),
        "expected_status": expected_status,
    }
    return payload


def _latest_summary_consistency(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {
            "guard_active": True,
            "latest_exists": False,
            "status": "missing",
            "inconsistent_promoted_packet_count": 0,
            "notes": ["latest_summary_not_present"],
        }
    top_level_state = _clean_text(payload.get("latest_promotion_state"))
    top_level_release_grade_ready = bool(payload.get("release_grade_ready"))
    top_level_status = _clean_text(payload.get("status"))
    packets = payload.get("packets") or ()
    inconsistent = 0
    packet_count = 0
    for packet in packets:
        if not isinstance(packet, Mapping):
            continue
        packet_count += 1
        packet_state = _clean_text(packet.get("latest_promotion_state"))
        if (
            packet_state == "promoted"
            and not (
                top_level_status == "complete"
                and top_level_release_grade_ready
                and top_level_state == "promoted"
            )
        ):
            inconsistent += 1
    status = "consistent" if inconsistent == 0 else "inconsistent"
    notes = ["packet_latest_promotion_guard_active"]
    if inconsistent == 0:
        notes.append("no_promoted_packets_under_held_or_partial_latest")
    return {
        "guard_active": True,
        "latest_exists": True,
        "status": status,
        "top_level_status": top_level_status or None,
        "top_level_release_grade_ready": top_level_release_grade_ready,
        "top_level_latest_promotion_state": top_level_state or None,
        "packet_count": packet_count,
        "inconsistent_promoted_packet_count": inconsistent,
        "notes": notes,
    }


def build_selected_packet_cohort_materialization(
    *,
    balanced_plan_path: Path = DEFAULT_BALANCED_PLAN_PATH,
    available_payloads_path: Path | None = DEFAULT_AVAILABLE_PAYLOADS_PATH,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    output_path: Path = DEFAULT_OUTPUT,
    run_id: str | None = None,
) -> dict[str, Any]:
    plan = _load_plan(balanced_plan_path)
    available_payloads, available_payloads_source = _load_available_payloads(
        available_payloads_path
    )
    selected_rows = _plan_rows(plan)
    requests = tuple(_build_request(row) for row in selected_rows)
    if requests and not available_payloads:
        raise ValueError(
            "available payload registry is required for cohort materialization; "
            "refusing to overwrite data/packages/LATEST.json with an empty payload map"
        )
    result = materialize_training_packets(
        requests,
        available_payloads=available_payloads,
        output_root=output_root,
        run_id=run_id,
    )
    expected_status_counts = Counter(
        _packet_expectation_status(row)
        for row in selected_rows
    )
    actual_status_counts = Counter(packet.status for packet in result.packets)
    modality_missing_counts = Counter()
    status_mismatches: list[dict[str, Any]] = []
    packet_rows: list[dict[str, Any]] = []
    for row, packet in zip(selected_rows, result.packets, strict=False):
        for modality in packet.missing_modalities:
            modality_missing_counts[modality] += 1
        expectation = _packet_expectation_summary(row)
        if expectation["status"] and expectation["status"] != packet.status:
            status_mismatches.append(
                {
                    "accession": packet.accession,
                    "expected_status": expectation["status"],
                    "materialized_status": packet.status,
                }
            )
        packet_rows.append(
            {
                **_packet_row_summary(packet, expected_status=expectation["status"]),
                "packet_expectation": expectation,
            }
        )

    materialization_summary_path = (
        output_root / result.run_id / "materialization_summary.json"
    )
    latest_summary_path = output_root / "LATEST.json"
    report = {
        "task_id": "P26-T010",
        "schema_id": "proteosphere-selected-packet-cohort-materialization-2026-03-23",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "status": result.status,
        "balanced_plan_path": str(balanced_plan_path).replace("\\", "/"),
        "available_payloads": available_payloads_source,
        "available_payloads_build_sha256": _clean_text(
            (
                available_payloads_source.get("registry_fingerprints") or {}
            ).get("build_sha256")
        )
        or None,
        "output_root": str(output_root).replace("\\", "/"),
        "output_path": str(output_path).replace("\\", "/"),
        "run_id": result.run_id,
        "selected_count": len(selected_rows),
        "materialization_summary_path": str(materialization_summary_path).replace("\\", "/"),
        "latest_summary_path": str(latest_summary_path).replace("\\", "/"),
        "latest_summary_consistency": _latest_summary_consistency(
            _read_json(latest_summary_path) if latest_summary_path.exists() else None
        ),
        "selected_rows": packet_rows,
        "summary": {
            "packet_count": result.packet_count,
            "complete_count": result.complete_count,
            "partial_count": result.partial_count,
            "unresolved_count": result.unresolved_count,
            "packet_status_counts": dict(sorted(actual_status_counts.items())),
            "expected_status_counts": dict(sorted(expected_status_counts.items())),
            "missing_modality_counts": dict(sorted(modality_missing_counts.items())),
            "status_mismatch_count": len(status_mismatches),
            "status_mismatches": status_mismatches,
            "packet_manifest_paths": [packet.manifest_path for packet in result.packets],
            "packet_dir_paths": [packet.packet_dir for packet in result.packets],
        },
        "materialization": result.to_dict(),
    }
    run_scoped_output_path = output_root / result.run_id / "selected_cohort_materialization.json"
    _write_json(run_scoped_output_path, report)
    if _should_replace_report(report, output_path):
        _write_json(output_path, report)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize a selected cohort from a balanced plan into packet bundles."
        )
    )
    parser.add_argument("--balanced-plan", type=Path, default=DEFAULT_BALANCED_PLAN_PATH)
    parser.add_argument("--available-payloads", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_selected_packet_cohort_materialization(
        balanced_plan_path=args.balanced_plan,
        available_payloads_path=args.available_payloads,
        output_root=args.output_root,
        output_path=args.output,
        run_id=args.run_id,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "Selected packet cohort materialized: "
            f"packets={report['summary']['packet_count']} "
            f"status={report['status']} "
            f"output_root={report['output_root']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

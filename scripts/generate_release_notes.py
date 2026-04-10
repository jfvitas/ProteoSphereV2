from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_MANIFEST = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_bundle_manifest.json"
)
DEFAULT_NOTES_OUTPUT = (
    REPO_ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_notes.md"
)
DEFAULT_SUPPORT_OUTPUT = (
    REPO_ROOT
    / "runs"
    / "real_data_benchmark"
    / "full_results"
    / "release_support_manifest.json"
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_path(raw_path: str | Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def _artifact_entry(
    *,
    kind: str,
    role: str,
    path_value: str,
    required: bool,
    manifest_present: bool = True,
) -> dict[str, Any]:
    resolved_path = _resolve_path(path_value)
    present = manifest_present and resolved_path.exists()
    checksum = _sha256(resolved_path) if present else None
    return {
        "tag": f"{kind}:{role}",
        "kind": kind,
        "role": role,
        "path": path_value,
        "resolved_path": str(resolved_path).replace("\\", "/"),
        "present": present,
        "required": required,
        "size_bytes": resolved_path.stat().st_size if present else 0,
        "sha256": checksum,
    }


def _validate_required_artifacts(entries: list[dict[str, Any]]) -> None:
    missing = [
        entry for entry in entries if entry["required"] and not entry["present"]
    ]
    if not missing:
        return
    details = ", ".join(f"{item['tag']} ({item['path']})" for item in missing)
    raise FileNotFoundError(f"missing required release artifacts: {details}")


def _build_notes_markdown(
    *,
    source_manifest: dict[str, Any],
    evidence_entries: list[dict[str, Any]],
    support_manifest: dict[str, Any],
) -> str:
    blocker_categories = list(source_manifest.get("blocker_categories", []))
    bundle_summary = source_manifest.get("bundle_summary", {})
    truth_boundary = source_manifest.get("truth_boundary", {})
    release_artifacts = source_manifest.get("release_artifacts", [])
    supporting_artifacts = source_manifest.get("supporting_artifacts", [])

    lines: list[str] = [
        "# Release Notes",
        "",
        f"- Bundle ID: `{source_manifest.get('bundle_id', 'unknown')}`",
        f"- Bundle tag: `{support_manifest.get('bundle_tag', 'unknown')}`",
        f"- Release status: `{source_manifest.get('status', 'unknown')}`",
        f"- Generated at: `{support_manifest.get('generated_at', 'unknown')}`",
        "",
        "## Evidence Used",
    ]
    for entry in evidence_entries:
        lines.append(
            f"- `{entry['role']}`: `{entry['path']}`"
            f" ({'present' if entry['present'] else 'missing'})"
        )

    lines.extend(
        [
            "",
            "## Release Summary",
            f"- Cohort size: `{bundle_summary.get('cohort_size', 'unknown')}`",
            f"- Resolved accessions: `{bundle_summary.get('resolved_accessions', 'unknown')}`",
            f"- Unresolved accessions: `{bundle_summary.get('unresolved_accessions', 'unknown')}`",
            f"- Runtime surface: `{bundle_summary.get('runtime_surface', 'unknown')}`",
            "- Split counts: `"
            f"{json.dumps(bundle_summary.get('split_counts', {}), sort_keys=True)}`",
            "",
            "## Blockers",
        ]
    )
    for blocker in blocker_categories:
        lines.append(f"- {blocker}")

    lines.extend(
        [
            "",
            "## Truth Boundary",
            "- Allowed statuses: `"
            f"{json.dumps(truth_boundary.get('allowed_statuses', []))}`",
            "- Forbidden overclaims: `"
            f"{json.dumps(truth_boundary.get('forbidden_overclaims', []))}`",
            "",
            "## Artifact Coverage",
            f"- Release artifacts: `{len(release_artifacts)}`",
            f"- Supporting artifacts: `{len(supporting_artifacts)}`",
            f"- Support manifest path: `{support_manifest.get('output_path', 'unknown')}`",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def build_release_notes(
    *,
    source_manifest_path: Path = DEFAULT_SOURCE_MANIFEST,
    notes_output_path: Path = DEFAULT_NOTES_OUTPUT,
    support_output_path: Path = DEFAULT_SUPPORT_OUTPUT,
    bundle_version: str | None = None,
) -> dict[str, Any]:
    source_manifest = _read_json(source_manifest_path)
    bundle_id = str(source_manifest.get("bundle_id") or source_manifest_path.stem)
    version = bundle_version or str(source_manifest.get("bundle_version") or "v1")
    bundle_tag = f"release-notes:{bundle_id}@{version}"

    evidence_entries: list[dict[str, Any]] = [
        _artifact_entry(
            kind="source_manifest",
            role="release_bundle_manifest",
            path_value=str(source_manifest_path),
            required=True,
        )
    ]
    for section_name, kind in (
        ("release_artifacts", "release_artifact"),
        ("supporting_artifacts", "supporting_artifact"),
    ):
        for item in source_manifest.get(section_name, []):
            if not isinstance(item, dict):
                continue
            path_value = str(item.get("path") or "")
            if not path_value:
                continue
            evidence_entries.append(
                _artifact_entry(
                    kind=kind,
                    role=str(item.get("role") or "unknown"),
                    path_value=path_value,
                    required=bool(item.get("required", False)),
                    manifest_present=bool(item.get("present", True)),
                )
            )

    _validate_required_artifacts(evidence_entries)

    support_manifest = {
        "artifact_id": "release_support_manifest",
        "schema_version": "1.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "bundle_id": bundle_id,
        "bundle_version": version,
        "bundle_tag": bundle_tag,
        "output_path": str(support_output_path).replace("\\", "/"),
        "source_manifest": {
            "path": str(source_manifest_path).replace("\\", "/"),
            "sha256": _sha256(source_manifest_path),
        },
        "release_status": source_manifest.get("status"),
        "blocker_categories": list(source_manifest.get("blocker_categories", [])),
        "truth_boundary": source_manifest.get("truth_boundary", {}),
        "bundle_summary": source_manifest.get("bundle_summary", {}),
        "evidence_artifacts": evidence_entries,
        "artifact_sha256_index": {
            entry["tag"]: entry["sha256"]
            for entry in evidence_entries
            if entry["sha256"] is not None
        },
        "carry_through": {
            "blocker_categories": list(source_manifest.get("blocker_categories", [])),
            "notes_blocker_categories": list(source_manifest.get("blocker_categories", [])),
            "release_status": source_manifest.get("status"),
        },
    }

    notes_markdown = _build_notes_markdown(
        source_manifest=source_manifest,
        evidence_entries=evidence_entries,
        support_manifest=support_manifest,
    )

    support_manifest["notes_markdown_path"] = str(notes_output_path).replace("\\", "/")
    support_manifest["notes_markdown_sha256"] = hashlib.sha256(
        notes_markdown.encode("utf-8")
    ).hexdigest()

    _write_text(notes_output_path, notes_markdown)
    _write_json(support_output_path, support_manifest)

    return {
        "bundle_id": bundle_id,
        "bundle_version": version,
        "bundle_tag": bundle_tag,
        "notes_output_path": str(notes_output_path).replace("\\", "/"),
        "support_output_path": str(support_output_path).replace("\\", "/"),
        "notes_markdown": notes_markdown,
        "support_manifest": support_manifest,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate release notes and a support manifest from evidence-backed artifacts."
        )
    )
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--notes-output", type=Path, default=DEFAULT_NOTES_OUTPUT)
    parser.add_argument("--support-output", type=Path, default=DEFAULT_SUPPORT_OUTPUT)
    parser.add_argument("--bundle-version", type=str, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_release_notes(
        source_manifest_path=args.source_manifest,
        notes_output_path=args.notes_output,
        support_output_path=args.support_output,
        bundle_version=args.bundle_version,
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.procurement.source_release_manifest import SourceReleaseManifest  # noqa: E402

DEFAULT_SEED_ROOT = REPO_ROOT / "data" / "raw" / "protein_data_scope_seed"
DEFAULT_VALIDATION_PATH = (
    REPO_ROOT / "artifacts" / "status" / "protein_data_scope_seed_validation.json"
)
DEFAULT_PROMOTION_ROOT = DEFAULT_SEED_ROOT / "promotions"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "reports" / "protein_data_scope_seed_publish.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temp_path, path)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(text, encoding="utf-8")
    os.replace(temp_path, path)


def _clean_text(value: object | None) -> str:
    return str(value or "").strip()


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _stamp_from_manifest_path(path: Path) -> str:
    name = path.stem
    if name.startswith("download_run_"):
        return name.removeprefix("download_run_")
    return name


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_source_entry(manifest_path: Path, source_id: str) -> dict[str, Any]:
    manifest = _read_json(manifest_path)
    for source in manifest.get("sources") or ():
        if not isinstance(source, dict):
            continue
        if _clean_text(source.get("id")) == source_id:
            return dict(source)
    raise ValueError(f"source {source_id!r} not found in manifest {manifest_path}")


def _build_source_release_manifest(
    *,
    source_id: str,
    validation_source: dict[str, Any],
    manifest_path: Path,
) -> SourceReleaseManifest:
    source_entry = _load_source_entry(manifest_path, source_id)
    generated_at = _clean_text(_read_json(manifest_path).get("generated_at"))
    release_date = generated_at[:10] if generated_at else None
    local_artifact_refs = []
    reproducibility_metadata = [
        f"seed_manifest={_repo_relative(manifest_path)}",
        f"seed_run_stamp={_stamp_from_manifest_path(manifest_path)}",
    ]
    provenance = [
        f"validation_status={validation_source['status']}",
        f"validation_manifest={_clean_text(validation_source.get('manifest_path'))}",
    ]
    first_url: str | None = None
    for item in source_entry.get("items") or ():
        if not isinstance(item, dict):
            continue
        path_value = _clean_text(item.get("path"))
        if path_value:
            local_artifact_refs.append(_repo_relative(Path(path_value)))
        sha256 = _clean_text(item.get("sha256"))
        filename = _clean_text(item.get("filename"))
        if sha256 and filename:
            reproducibility_metadata.append(f"sha256:{filename}={sha256}")
        url = _clean_text(item.get("url"))
        if url and first_url is None:
            first_url = url
    if not local_artifact_refs:
        raise ValueError(f"source {source_id!r} has no local artifact refs")
    return SourceReleaseManifest(
        source_name=source_id,
        release_version=f"protein-data-scope-seed-{_stamp_from_manifest_path(manifest_path)}",
        release_date=release_date,
        retrieval_mode="download",
        source_locator=first_url,
        local_artifact_refs=tuple(local_artifact_refs),
        provenance=tuple(provenance),
        reproducibility_metadata=tuple(reproducibility_metadata),
    )


def _validate_promotable_artifact_set(validation_source: dict[str, Any]) -> None:
    validated_artifacts = validation_source.get("validated_artifacts") or ()
    if not isinstance(validated_artifacts, list) or not validated_artifacts:
        raise ValueError("validated_artifacts are required for promotion")
    for artifact in validated_artifacts:
        if not isinstance(artifact, dict):
            raise ValueError("validated_artifacts entries must be dictionaries")
        path_value = _clean_text(artifact.get("path"))
        if not path_value:
            raise ValueError("validated artifact is missing path")
        path = Path(path_value)
        if not path.exists():
            raise ValueError(f"validated artifact missing on disk: {path}")
        expected_size = int(artifact.get("size_bytes") or 0)
        actual_size = path.stat().st_size
        if expected_size != actual_size:
            raise ValueError(f"validated_artifact_set_mismatch: size differs for {path.name}")
        expected_sha256 = _clean_text(artifact.get("sha256"))
        actual_sha256 = _sha256_file(path)
        if not expected_sha256 or expected_sha256 != actual_sha256:
            raise ValueError(f"validated_artifact_set_mismatch: digest differs for {path.name}")


def build_seed_promotion(
    *,
    validation_path: Path,
    seed_root: Path,
) -> dict[str, Any]:
    validation = _read_json(validation_path)
    if _clean_text(validation.get("status")) != "passed":
        raise ValueError("seed validation must be passed before promotion")
    sources = validation.get("sources") or ()
    if not isinstance(sources, list):
        raise ValueError("validation sources must be a list")

    promoted_sources: list[dict[str, Any]] = []
    manifest_paths: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            continue
        if _clean_text(source.get("status")) != "passed":
            raise ValueError("all validation sources must be passed before promotion")
        _validate_promotable_artifact_set(source)
        manifest_path_value = _clean_text(source.get("manifest_path"))
        if not manifest_path_value:
            raise ValueError(
                f"source {_clean_text(source.get('source_id'))!r} is missing manifest_path"
            )
        manifest_path = Path(manifest_path_value)
        source_release = _build_source_release_manifest(
            source_id=_clean_text(source.get("source_id")),
            validation_source=source,
            manifest_path=manifest_path,
        )
        promoted_sources.append(
            {
                "source_id": _clean_text(source.get("source_id")),
                "seed_manifest_path": _repo_relative(manifest_path),
                "source_release": source_release.to_dict(),
            }
        )
        manifest_paths.add(_repo_relative(manifest_path))

    promoted_at = datetime.now(UTC).isoformat()
    promotion_id = f"protein-data-scope-seed:{promoted_at[:19].replace(':', '').replace('-', '')}"
    return {
        "schema_id": "proteosphere-protein-data-scope-seed-promotion-2026-03-23",
        "promotion_id": promotion_id,
        "promoted_at": promoted_at,
        "status": "promoted",
        "seed_root": _repo_relative(seed_root),
        "validation_path": _repo_relative(validation_path),
        "validation_status": "passed",
        "manifest_paths": sorted(manifest_paths),
        "source_count": len(promoted_sources),
        "sources": promoted_sources,
    }


def render_seed_promotion_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Protein Data Scope Seed Publish",
        "",
        f"- Status: `{payload['status']}`",
        f"- Promotion ID: `{payload['promotion_id']}`",
        f"- Promoted at: `{payload['promoted_at']}`",
        f"- Validation path: `{payload['validation_path']}`",
        f"- Seed root: `{payload['seed_root']}`",
        f"- Source count: `{payload['source_count']}`",
        "",
    ]
    for source in payload["sources"]:
        source_release = source["source_release"]
        lines.extend(
            [
                f"## {source['source_id']}",
                "",
                f"- Seed manifest: `{source['seed_manifest_path']}`",
                f"- Release manifest ID: `{source_release['manifest_id']}`",
                f"- Release version: `{source_release['release_version']}`",
                f"- Release date: `{source_release['release_date']}`",
                f"- Retrieval mode: `{source_release['retrieval_mode']}`",
                f"- Artifact refs: `{len(source_release['local_artifact_refs'])}`",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote a validated protein_data_scope seed run.")
    parser.add_argument("--seed-root", type=Path, default=DEFAULT_SEED_ROOT)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION_PATH)
    parser.add_argument("--promotion-root", type=Path, default=DEFAULT_PROMOTION_ROOT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_seed_promotion(validation_path=args.validation, seed_root=args.seed_root)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    summary_path = args.promotion_root / f"{stamp}.json"
    latest_path = args.promotion_root / "LATEST.json"
    _write_json(summary_path, payload)
    _write_json(latest_path, payload)
    _write_text(args.markdown_output, render_seed_promotion_markdown(payload))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Protein Data Scope seed promotion: "
            f"status={payload['status']} sources={payload['source_count']} "
            f"summary={_repo_relative(summary_path)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

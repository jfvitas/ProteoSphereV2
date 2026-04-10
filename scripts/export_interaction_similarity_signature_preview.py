from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from interaction_similarity_signature_common import (  # noqa: E402
    DEFAULT_BIOGRID_ARCHIVE,
    DEFAULT_BUNDLE_MANIFEST,
    DEFAULT_CANONICAL_SUMMARY,
    DEFAULT_INTACT_ROOT,
    DEFAULT_LOCAL_REGISTRY_RUNS_ROOT,
    DEFAULT_STRING_ROOT,
    _load_manifest,
    _read_json,
    build_interaction_similarity_signature_preview,
    render_preview_markdown,
)

DEFAULT_OUTPUT_JSON = (
    Path(__file__).resolve().parents[1]
    / "artifacts"
    / "status"
    / "interaction_similarity_signature_preview.json"
)
DEFAULT_OUTPUT_MD = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "reports"
    / "interaction_similarity_signature_preview.md"
)


def _latest_stamp(local_registry_runs_root: Path) -> str:
    payload = _read_json(local_registry_runs_root / "LATEST.json")
    return str(payload.get("stamp") or "").strip()


def _default_manifest_path(local_registry_runs_root: Path, source_name: str) -> Path:
    stamp = _latest_stamp(local_registry_runs_root)
    return (
        Path(__file__).resolve().parents[1]
        / "data"
        / "raw"
        / "local_registry"
        / stamp
        / source_name
        / "manifest.json"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the first compact interaction similarity signature preview."
    )
    parser.add_argument(
        "--local-registry-runs-root",
        type=Path,
        default=DEFAULT_LOCAL_REGISTRY_RUNS_ROOT,
    )
    parser.add_argument("--biogrid-manifest", type=Path, default=None)
    parser.add_argument("--string-manifest", type=Path, default=None)
    parser.add_argument("--intact-manifest", type=Path, default=None)
    parser.add_argument("--biogrid-archive", type=Path, default=DEFAULT_BIOGRID_ARCHIVE)
    parser.add_argument("--string-root", type=Path, default=DEFAULT_STRING_ROOT)
    parser.add_argument("--intact-raw-root", type=Path, default=DEFAULT_INTACT_ROOT)
    parser.add_argument("--canonical-summary", type=Path, default=DEFAULT_CANONICAL_SUMMARY)
    parser.add_argument("--bundle-manifest", type=Path, default=DEFAULT_BUNDLE_MANIFEST)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    biogrid_manifest_path = args.biogrid_manifest or _default_manifest_path(
        args.local_registry_runs_root, "biogrid"
    )
    string_manifest_path = args.string_manifest or _default_manifest_path(
        args.local_registry_runs_root, "string"
    )
    intact_manifest_path = args.intact_manifest or _default_manifest_path(
        args.local_registry_runs_root, "intact"
    )
    payload = build_interaction_similarity_signature_preview(
        biogrid_manifest=_load_manifest(biogrid_manifest_path),
        string_manifest=_load_manifest(string_manifest_path),
        intact_manifest=_load_manifest(intact_manifest_path),
        biogrid_archive_path=args.biogrid_archive,
        string_root=args.string_root,
        intact_raw_root=args.intact_raw_root,
        canonical_summary_path=args.canonical_summary,
        bundle_manifest=_read_json(args.bundle_manifest),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_preview_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

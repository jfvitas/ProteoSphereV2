from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from protein_data_scope.download_all_sources import (  # noqa: E402,I001
    default_destination_root,
    download_file,
    ensure_dir,
    safe_print,
    sha256_file,
    write_run_log,
    write_run_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESOLVER_JSON = (
    REPO_ROOT / "artifacts" / "status" / "p28_interpro_complexportal_resolver.json"
)


def filename_from_url(url: str) -> str:
    path = urlparse(url).path
    name = Path(path).name
    return name or "downloaded_file"


def load_resolver_payload(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Download resolver-pinned safe URLs.")
    parser.add_argument(
        "--resolver-json",
        type=Path,
        default=DEFAULT_RESOLVER_JSON,
        help="Resolver JSON containing safe_to_automate URL sets.",
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        required=True,
        help="Resolver source ids to download.",
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=default_destination_root(),
        help="Destination root directory.",
    )
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    payload = load_resolver_payload(args.resolver_json)
    selected = {source_id.strip().lower() for source_id in args.sources}
    sources = [
        source
        for source in payload.get("sources", [])
        if str(source.get("source_id", "")).strip().lower() in selected
    ]

    ensure_dir(args.dest)
    log_lines: list[str] = []
    run_manifest: dict[str, object] = {
        "generated_at": payload.get("generated_at"),
        "resolver_json": str(args.resolver_json),
        "destination_root": str(args.dest),
        "sources": [],
    }

    safe_print(f"Resolver source download root: {args.dest}")
    for source in sources:
        source_id = str(source.get("source_id"))
        source_dir = args.dest / source_id
        ensure_dir(source_dir)
        source_manifest: dict[str, object] = {
            "source_id": source_id,
            "resolver_status": source.get("resolver_status"),
            "items": [],
        }
        for url in source.get("safe_to_automate", []):
            filename = filename_from_url(str(url))
            dest_path = source_dir / filename
            safe_print(f"Downloading {source_id}: {url}")
            ok, msg = download_file(
                str(url),
                dest_path,
                timeout=args.timeout,
                retries=args.retries,
                overwrite=args.overwrite,
            )
            safe_print(msg)
            log_lines.append(f"[{source_id}] {msg} <- {url}")
            item_manifest: dict[str, object] = {
                "url": url,
                "filename": filename,
                "status": "downloaded" if ok else "failed",
                "message": msg,
            }
            if ok and dest_path.exists():
                item_manifest["path"] = str(dest_path)
                item_manifest["size_bytes"] = dest_path.stat().st_size
                item_manifest["sha256"] = sha256_file(dest_path)
            source_manifest["items"].append(item_manifest)
        run_manifest["sources"].append(source_manifest)

    write_run_log(args.dest, log_lines)
    write_run_manifest(args.dest, run_manifest)
    safe_print("Resolver-safe download run complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

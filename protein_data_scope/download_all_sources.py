#!/usr/bin/env python3
"""
Broad protein data source downloader.

Downloads top-level public files from a curated manifest into a destination tree,
defaulting to the repository raw-data seed area so fetched files stay inside the
ProteoSphere provenance model.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import tarfile
import time
import zipfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
MANIFEST_PATH = HERE / "sources_manifest.json"
POLICY_PATH = HERE / "source_policy.json"
VALIDATION_POLICY_PATH = HERE / "tier1_validation_policy.json"


def default_destination_root() -> Path:
    return HERE.parent / "data" / "raw" / "protein_data_scope_seed"


def load_manifest() -> dict:
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_policy() -> dict:
    if not POLICY_PATH.exists():
        return {"tiers": {}}
    with POLICY_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_validation_policy(path: Path | None = None) -> dict:
    policy_path = path or VALIDATION_POLICY_PATH
    if not policy_path.exists():
        return {"sources": {}}
    with policy_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def safe_print(*args, **kwargs):
    text = " ".join(str(a) for a in args)
    try:
        print(text, **kwargs)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"), **kwargs)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def human_bytes(num: float) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if num < 1024.0 or unit == units[-1]:
            return f"{num:,.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} B"


def _looks_like_html_placeholder(dest: Path, headers: object, sample: bytes) -> bool:
    filename = dest.name.strip().lower()
    if filename.endswith(".html") or filename.endswith(".htm"):
        return False

    content_type = ""
    if headers is not None and hasattr(headers, "get"):
        try:
            content_type = str(headers.get("Content-Type", "") or "").casefold()
        except Exception:  # noqa: BLE001
            content_type = ""

    if "text/html" in content_type:
        return True

    sniff = sample[:4096].lstrip().lower()
    return sniff.startswith(b"<!doctype html") or sniff.startswith(b"<html")


def download_file(
    url: str,
    dest: Path,
    timeout: int = 1800,
    retries: int = 3,
    overwrite: bool = False,
) -> tuple[bool, str]:
    if dest.exists() and not overwrite:
        return True, f"SKIP exists: {dest.name}"

    ensure_dir(dest.parent)
    temp_dest = dest.with_suffix(dest.suffix + ".part")
    headers = {"User-Agent": "Mozilla/5.0 protein-data-downloader/1.0"}

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=timeout) as resp:
                total = resp.headers.get("Content-Length")
                total_i = int(total) if total and total.isdigit() else None
                downloaded = 0
                chunk_size = 1024 * 1024
                started = time.time()
                first_bytes = bytearray()
                with temp_dest.open("wb") as out:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        out.write(chunk)
                        downloaded += len(chunk)
                        if len(first_bytes) < 4096:
                            remaining = 4096 - len(first_bytes)
                            first_bytes.extend(chunk[:remaining])
                        if total_i:
                            pct = downloaded * 100.0 / total_i
                            elapsed = max(time.time() - started, 0.001)
                            rate = downloaded / elapsed
                            safe_print(
                                (
                                    f"  {dest.name}: {pct:6.2f}%  "
                                    f"{human_bytes(downloaded)}/{human_bytes(total_i)}  "
                                    f"{human_bytes(rate)}/s"
                                ),
                                end="\r",
                            )
                if _looks_like_html_placeholder(dest, resp.headers, bytes(first_bytes)):
                    safe_print(" " * 120, end="\r")
                    temp_dest.unlink(missing_ok=True)
                    return False, f"FAILED {dest.name}: html placeholder response"
                if temp_dest.exists():
                    temp_dest.replace(dest)
                safe_print(" " * 120, end="\r")
                return True, f"OK downloaded: {dest.name}"
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = exc
            safe_print(f"  Attempt {attempt}/{retries} failed for {url}: {exc}")
            time.sleep(min(10 * attempt, 30))
        finally:
            if temp_dest.exists() and not dest.exists():
                try:
                    temp_dest.unlink()
                except OSError:
                    pass

    return False, f"FAILED {dest.name}: {last_error}"


def _safe_extract_zip(archive: zipfile.ZipFile, destination: Path) -> None:
    base = destination.resolve()
    for member in archive.infolist():
        member_path = (destination / member.filename).resolve()
        if not str(member_path).startswith(str(base)):
            raise ValueError(f"unsafe archive path: {member.filename}")
    archive.extractall(destination)


def _safe_extract_tar(archive: tarfile.TarFile, destination: Path) -> None:
    base = destination.resolve()
    for member in archive.getmembers():
        member_path = (destination / member.name).resolve()
        if not str(member_path).startswith(str(base)):
            raise ValueError(f"unsafe archive path: {member.name}")
    archive.extractall(destination)


def extract_file(path: Path, remove_archive: bool = False) -> str:
    out_dir = path.parent / f"{path.name}__extracted"
    ensure_dir(out_dir)

    try:
        if path.name.lower().endswith(".zip"):
            with zipfile.ZipFile(path, "r") as zf:
                _safe_extract_zip(zf, out_dir)
            msg = f"EXTRACT zip -> {out_dir}"
        elif path.name.lower().endswith(".tar.gz") or path.name.lower().endswith(".tgz"):
            with tarfile.open(path, "r:gz") as tf:
                _safe_extract_tar(tf, out_dir)
            msg = f"EXTRACT tar.gz -> {out_dir}"
        elif path.name.lower().endswith(".tar"):
            with tarfile.open(path, "r:") as tf:
                _safe_extract_tar(tf, out_dir)
            msg = f"EXTRACT tar -> {out_dir}"
        elif path.name.lower().endswith(".gz") and not path.name.lower().endswith(
            (".tar.gz", ".tgz")
        ):
            out_file = out_dir / path.stem
            with gzip.open(path, "rb") as src, out_file.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            msg = f"EXTRACT gz -> {out_file}"
        else:
            return f"SKIP no extractor for {path.name}"

        if remove_archive:
            path.unlink(missing_ok=True)
        return msg
    except Exception as exc:  # noqa: BLE001
        return f"FAILED extract {path.name}: {exc}"


def source_tier(source_id: str, policy: dict) -> str:
    source_key = source_id.strip().casefold()
    tiers = policy.get("tiers") or {}
    if not isinstance(tiers, dict):
        return "unclassified"
    for tier_name, tier_payload in tiers.items():
        if not isinstance(tier_payload, dict):
            continue
        source_ids = tier_payload.get("source_ids") or ()
        if source_key in {str(item).strip().casefold() for item in source_ids}:
            return str(tier_name).strip()
    return "unclassified"


def normalize_source_ids(
    manifest: dict,
    selected: list[str] | None,
    *,
    tiers: list[str] | None,
    policy: dict,
) -> list[dict]:
    sources = manifest["sources"]
    filtered = list(sources)

    if selected:
        selected_set = {s.strip().lower() for s in selected}
        filtered = [s for s in filtered if s["id"].lower() in selected_set]
        missing = sorted(selected_set - {s["id"].lower() for s in filtered})
    else:
        missing = []

    if missing:
        safe_print(f"Warning: unknown source IDs skipped: {', '.join(missing)}")

    if tiers:
        tier_set = {tier.strip().casefold() for tier in tiers}
        filtered = [
            source
            for source in filtered
            if source_tier(str(source.get("id") or ""), policy).casefold() in tier_set
        ]
    return filtered


def normalize_selected_filenames(values: list[str] | None) -> set[str]:
    selected: set[str] = set()
    for value in values or ():
        for item in str(value).split(","):
            filename = item.strip()
            if filename:
                selected.add(filename)
    return selected


def should_skip_source(source: dict, *, allow_manual: bool) -> tuple[bool, str | None]:
    if source.get("manual_review_required") and not allow_manual:
        return True, "manual_review_required"
    return False, None


def should_skip_item(
    source: dict,
    item: dict,
    *,
    allow_html_placeholders: bool,
) -> tuple[bool, str | None]:
    filename = str(item.get("filename") or "").strip().lower()
    url = str(item.get("url") or "").strip().lower()
    if (
        not allow_html_placeholders
        and (filename.endswith(".html") or url.endswith(".html"))
    ):
        return True, "html_placeholder"
    return False, None


def filter_top_level_files_for_required_core(
    source: dict,
    *,
    validation_policy: dict,
    required_core_only: bool,
    selected_filenames: set[str] | None = None,
) -> list[dict]:
    items = list(source.get("top_level_files") or ())
    if not required_core_only:
        filtered_items = items
    else:
        source_id = str(source.get("id") or "").strip()
        policy_entry = (validation_policy.get("sources") or {}).get(source_id) or {}
        required_core = {
            str(filename).strip()
            for filename in policy_entry.get("required_core_files") or ()
            if str(filename).strip()
        }
        if not required_core:
            filtered_items = items
        else:
            filtered_items = [
                item
                for item in items
                if str(item.get("filename") or "").strip() in required_core
            ]
    if not selected_filenames:
        return filtered_items
    return [
        item
        for item in filtered_items
        if str(item.get("filename") or "").strip() in selected_filenames
    ]


def write_run_log(dest_root: Path, lines: list[str]) -> None:
    ts = time.strftime("%Y%m%d_%H%M%S")
    log_path = dest_root / f"download_run_{ts}.log"
    with log_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    safe_print(f"Run log written to {log_path}")


def write_run_manifest(dest_root: Path, payload: dict) -> Path:
    ts = time.strftime("%Y%m%d_%H%M%S")
    manifest_path = dest_root / f"download_run_{ts}.json"
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    safe_print(f"Run manifest written to {manifest_path}")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download broad-scope protein data source files."
    )
    parser.add_argument(
        "--dest",
        default=str(default_destination_root()),
        help="Destination root directory.",
    )
    parser.add_argument("--sources", nargs="*", help="Optional source IDs to download.")
    parser.add_argument(
        "--tiers",
        nargs="*",
        help="Optional procurement tiers to download (for example: direct guarded resolver).",
    )
    parser.add_argument(
        "--extract", action="store_true", help="Extract archives after download."
    )
    parser.add_argument(
        "--remove-archives",
        action="store_true",
        help="Remove archives after successful extraction.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files.")
    parser.add_argument("--timeout", type=int, default=1800, help="Per-request timeout in seconds.")
    parser.add_argument("--retries", type=int, default=3, help="Retry count per file.")
    parser.add_argument(
        "--allow-manual",
        action="store_true",
        help="Allow sources marked manual_review_required.",
    )
    parser.add_argument(
        "--allow-html-placeholders",
        action="store_true",
        help="Allow landing-page HTML placeholders to be downloaded.",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        help="Optional comma-separated top-level filenames to fetch within the selected sources.",
    )
    parser.add_argument(
        "--required-core-only",
        action="store_true",
        help="Restrict each selected source to Tier 1 required core files when defined.",
    )
    parser.add_argument(
        "--validation-policy",
        type=Path,
        default=VALIDATION_POLICY_PATH,
        help="Validation policy used to determine required core files.",
    )
    args = parser.parse_args()

    manifest = load_manifest()
    policy = load_policy()
    validation_policy = load_validation_policy(args.validation_policy)
    selected_filenames = normalize_selected_filenames(args.files)
    dest_root = Path(args.dest)
    ensure_dir(dest_root)
    selected_sources = normalize_source_ids(
        manifest,
        args.sources,
        tiers=args.tiers,
        policy=policy,
    )

    log_lines: list[str] = []
    run_manifest: dict[str, object] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "destination_root": str(dest_root),
        "extract": bool(args.extract),
        "remove_archives": bool(args.remove_archives),
        "overwrite": bool(args.overwrite),
        "allow_manual": bool(args.allow_manual),
        "allow_html_placeholders": bool(args.allow_html_placeholders),
        "selected_filenames": sorted(selected_filenames),
        "required_core_only": bool(args.required_core_only),
        "validation_policy_path": str(args.validation_policy),
        "tiers": list(args.tiers or ()),
        "sources": [],
    }
    safe_print(f"Destination root: {dest_root}")
    safe_print(f"Sources selected: {', '.join(s['id'] for s in selected_sources)}")

    for source in selected_sources:
        source_dir = dest_root / source["id"]
        ensure_dir(source_dir)
        safe_print(f"\n=== {source['name']} [{source['id']}] ===")
        selected_items = filter_top_level_files_for_required_core(
            source,
            validation_policy=validation_policy,
            required_core_only=args.required_core_only,
            selected_filenames=selected_filenames,
        )
        source_manifest: dict[str, object] = {
            "id": source["id"],
            "name": source.get("name"),
            "tier": source_tier(str(source.get("id") or ""), policy),
            "manual_review_required": bool(source.get("manual_review_required")),
            "notes": source.get("notes"),
            "required_core_only": bool(args.required_core_only),
            "items": [],
        }
        skip_source, skip_reason = should_skip_source(source, allow_manual=args.allow_manual)
        if source.get("manual_review_required"):
            note = source.get("notes", "manual review recommended")
            safe_print(f"NOTE: manual review recommended for this source: {note}")
            log_lines.append(f"[{source['id']}] NOTE {note}")
        if skip_source:
            safe_print(f"SKIP source {source['id']}: {skip_reason}")
            log_lines.append(f"[{source['id']}] SKIP source: {skip_reason}")
            source_manifest["status"] = "skipped"
            source_manifest["skip_reason"] = skip_reason
            run_manifest["sources"].append(source_manifest)
            continue

        metadata_path = source_dir / "_source_metadata.json"
        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(source, f, indent=2)

        for item in selected_items:
            filename = item["filename"]
            url = item["url"]
            skip_item, item_skip_reason = should_skip_item(
                source,
                item,
                allow_html_placeholders=args.allow_html_placeholders,
            )
            item_manifest: dict[str, object] = {
                "filename": filename,
                "url": url,
            }
            if skip_item:
                safe_print(f"SKIP item {filename}: {item_skip_reason}")
                log_lines.append(f"[{source['id']}] SKIP {filename}: {item_skip_reason}")
                item_manifest["status"] = "skipped"
                item_manifest["skip_reason"] = item_skip_reason
                source_manifest["items"].append(item_manifest)
                continue
            dest_path = source_dir / filename
            safe_print(f"Downloading {url}")
            ok, msg = download_file(
                url,
                dest_path,
                timeout=args.timeout,
                retries=args.retries,
                overwrite=args.overwrite,
            )
            safe_print(msg)
            log_lines.append(f"[{source['id']}] {msg} <- {url}")
            item_manifest["status"] = "downloaded" if ok else "failed"
            item_manifest["message"] = msg
            if ok and dest_path.exists():
                item_manifest["path"] = str(dest_path)
                item_manifest["size_bytes"] = dest_path.stat().st_size
                item_manifest["sha256"] = sha256_file(dest_path)

            if ok and args.extract:
                extract_msg = extract_file(dest_path, remove_archive=args.remove_archives)
                safe_print(extract_msg)
                log_lines.append(f"[{source['id']}] {extract_msg}")
                item_manifest["extract_message"] = extract_msg
            source_manifest["items"].append(item_manifest)

        source_manifest["status"] = "processed"
        run_manifest["sources"].append(source_manifest)

    write_run_log(dest_root, log_lines)
    write_run_manifest(dest_root, run_manifest)
    safe_print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

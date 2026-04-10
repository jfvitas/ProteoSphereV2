#!/usr/bin/env python3
"""Resolve InterPro and Complex Portal bulk download snapshots.

The helper probes official FTP listings, classifies files by size, and emits a
truthful status artifact with concrete URLs that are safe to automate now and
URLs that should stay deferred.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin
from urllib.request import Request, urlopen

INTERPRO_RELEASE_NOTES = "https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/release_notes.txt"
INTERPRO_LISTING = "https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/"
COMPLEX_BASE = "https://ftp.ebi.ac.uk/pub/databases/intact/complex/current/"
COMPLEX_LISTINGS = {
    "complextab": urljoin(COMPLEX_BASE, "complextab/"),
    "psi25": urljoin(COMPLEX_BASE, "psi25/"),
    "psi30": urljoin(COMPLEX_BASE, "psi30/"),
}


@dataclass(frozen=True)
class ListingEntry:
    name: str
    url: str
    modified: str
    size_label: str
    size_bytes: int | None

    @property
    def is_directory(self) -> bool:
        return self.name.endswith("/")


def fetch_text(url: str, timeout: int = 30) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 resolver-pinning/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_size_label(size_label: str) -> int | None:
    value = size_label.strip()
    if not value or value == "-":
        return None
    match = re.fullmatch(r"([\d.]+)\s*([KMGT]?)", value)
    if not match:
        return None
    number = float(match.group(1))
    unit = match.group(2).upper()
    scale = {
        "": 1,
        "K": 1024,
        "M": 1024**2,
        "G": 1024**3,
        "T": 1024**4,
    }[unit]
    return int(number * scale)


def parse_apache_listing(url: str, html_text: str) -> list[ListingEntry]:
    entries: list[ListingEntry] = []
    row_re = re.compile(
        r'<tr><td valign="top"><img src="/icons/[^"]+" alt="\[[^\]]*\]"></td>'
        r'<td><a href="([^"]+)">([^<]+)</a></td>'
        r'<td align="right">([^<]*)</td><td align="right">([^<]*)</td>',
        re.IGNORECASE,
    )
    for href, raw_name, modified, size_label in row_re.findall(html_text):
        name = html.unescape(raw_name)
        abs_url = urljoin(url, href)
        entries.append(
            ListingEntry(
                name=name,
                url=abs_url,
                modified=modified.strip(),
                size_label=size_label.strip(),
                size_bytes=parse_size_label(size_label),
            )
        )
    return entries


def classify_entries(
    entries: Iterable[ListingEntry],
    *,
    max_safe_bytes: int,
) -> tuple[list[ListingEntry], list[ListingEntry]]:
    safe: list[ListingEntry] = []
    deferred: list[ListingEntry] = []
    for entry in entries:
        if entry.is_directory:
            continue
        if entry.name.endswith(".md5"):
            continue
        if entry.size_bytes is not None and entry.size_bytes <= max_safe_bytes:
            safe.append(entry)
        else:
            deferred.append(entry)
    return safe, deferred


def latest_modified(entries: Iterable[ListingEntry]) -> str | None:
    timestamps = [entry.modified for entry in entries if entry.modified]
    return max(timestamps) if timestamps else None


def resolve_interpro(*, max_safe_bytes: int) -> dict:
    release_notes = fetch_text(INTERPRO_RELEASE_NOTES)
    listing_html = fetch_text(INTERPRO_LISTING)
    entries = parse_apache_listing(INTERPRO_LISTING, listing_html)
    safe, deferred = classify_entries(entries, max_safe_bytes=max_safe_bytes)
    release_match = re.search(r"Release\s+(\d+\.\d+)", release_notes)
    release_token = release_match.group(1) if release_match else None
    return {
        "source_id": "interpro",
        "resolver_status": "resolved",
        "resolved_release_token": release_token,
        "snapshot_timestamp": latest_modified(entries),
        "listing_url": INTERPRO_LISTING,
        "release_notes_url": INTERPRO_RELEASE_NOTES,
        "safe_to_automate": [entry.url for entry in safe],
        "deferred": [
            {
                "url": entry.url,
                "size_label": entry.size_label,
                "reason": "over_size_threshold",
            }
            for entry in deferred
        ],
        "discovery_evidence": [INTERPRO_LISTING, INTERPRO_RELEASE_NOTES],
    }


def resolve_complex_portal(*, max_safe_bytes: int) -> dict:
    evidence = ["https://www.ebi.ac.uk/training/online/courses/complex-portal-quick-tour/getting-data-from-complex-portal/"]
    resolved: dict[str, object] = {
        "source_id": "complex_portal",
        "resolver_status": "resolved",
        "resolved_release_token": "current",
        "listing_url": COMPLEX_BASE,
        "discovery_evidence": evidence,
        "snapshots": {},
        "safe_to_automate": [],
        "deferred": [],
    }

    safe_urls: list[str] = []
    deferred: list[dict[str, str]] = []
    snapshots: dict[str, dict[str, str | None]] = {}

    for family, listing_url in COMPLEX_LISTINGS.items():
        html_text = fetch_text(listing_url)
        entries = parse_apache_listing(listing_url, html_text)
        safe, big = classify_entries(entries, max_safe_bytes=max_safe_bytes)
        safe_urls.extend(entry.url for entry in safe)
        deferred.extend(
            {
                "url": entry.url,
                "size_label": entry.size_label,
                "reason": "over_size_threshold",
            }
            for entry in big
        )
        snapshots[family] = {
            "listing_url": listing_url,
            "snapshot_timestamp": latest_modified(entries),
            "safe_count": str(len(safe)),
            "deferred_count": str(len(big)),
        }

    resolved["snapshots"] = snapshots
    resolved["safe_to_automate"] = safe_urls
    resolved["deferred"] = deferred
    return resolved


def build_payload(max_safe_bytes: int) -> dict:
    interpro = resolve_interpro(max_safe_bytes=max_safe_bytes)
    complex_portal = resolve_complex_portal(max_safe_bytes=max_safe_bytes)
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "max_safe_bytes": max_safe_bytes,
        "sources": [interpro, complex_portal],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve concrete bulk-download URLs for InterPro and Complex Portal."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output path. If omitted, print to stdout.",
    )
    parser.add_argument(
        "--max-safe-mb",
        type=int,
        default=100,
        help="Size threshold for safe-to-automate files, in mebibytes.",
    )
    args = parser.parse_args()
    payload = build_payload(args.max_safe_mb * 1024 * 1024)
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
from pathlib import Path

from scripts.download_resolver_safe_urls import filename_from_url, load_resolver_payload


def test_filename_from_url_uses_final_path_segment() -> None:
    assert (
        filename_from_url("https://ftp.ebi.ac.uk/pub/databases/interpro/current_release/entry.list")
        == "entry.list"
    )


def test_load_resolver_payload_reads_json(tmp_path: Path) -> None:
    payload_path = tmp_path / "resolver.json"
    payload = {"sources": [{"source_id": "interpro", "safe_to_automate": ["https://example.com/a"]}]}
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    assert load_resolver_payload(payload_path) == payload

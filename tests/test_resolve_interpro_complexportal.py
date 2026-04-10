from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import resolve_interpro_complexportal as resolver  # noqa: E402


def test_parse_size_label_handles_units() -> None:
    assert resolver.parse_size_label("632K") == 632 * 1024
    assert resolver.parse_size_label("39M") == 39 * 1024 * 1024
    assert resolver.parse_size_label("1.3T") == int(1.3 * 1024**4)
    assert resolver.parse_size_label("-") is None


def test_parse_apache_listing_and_threshold_classification() -> None:
    html_text = """
    <html><body><table>
    <tr><th colspan="5"><hr></th></tr>
    <tr><td valign="top"><img src="/icons/back.gif" alt="[PARENTDIR]"></td><td><a href="../">Parent Directory</a></td><td>&nbsp;</td><td align="right">  - </td><td>&nbsp;</td></tr>
    <tr><td valign="top"><img src="/icons/text.gif" alt="[TXT]"></td><td><a href="small.tsv">small.tsv</a></td><td align="right">2026-01-14 12:01</td><td align="right">4.5K</td><td>&nbsp;</td></tr>
    <tr><td valign="top"><img src="/icons/compressed.gif" alt="[   ]"></td><td><a href="large.zip">large.zip</a></td><td align="right">2026-01-14 12:03</td><td align="right">379M</td><td>&nbsp;</td></tr>
    </table></body></html>
    """
    entries = resolver.parse_apache_listing(
        "https://ftp.ebi.ac.uk/pub/databases/intact/complex/current/psi25/",
        html_text,
    )
    safe, deferred = resolver.classify_entries(entries, max_safe_bytes=100 * 1024 * 1024)
    assert [entry.name for entry in safe] == ["small.tsv"]
    assert [entry.name for entry in deferred] == ["large.zip"]

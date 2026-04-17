from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "artifacts" / "runtime" / "literature_hunt_tier1_source_bundle"
MANIFEST_PATH = OUTPUT_ROOT / "download_manifest.json"
SUMMARY_MD = REPO_ROOT / "docs" / "reports" / "literature_hunt_tier1_source_bundle.md"
EDGE_PATH = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
HEADERS = {"User-Agent": "Mozilla/5.0 (ProteoSphere tier1 bundle repair)"}

FIXES: dict[str, dict[str, str]] = {
    "graphscoredta2023": {
        "mode": "download",
        "url": "https://pdfs.semanticscholar.org/b1be/c5a4e31ded9c59b89bb6661ab19edd2e159a.pdf",
    },
    "capla2023": {
        "mode": "download",
        "url": "https://pdfs.semanticscholar.org/432a/6e08f48786dff6dbb259db58af9cc0d6dc01.pdf",
    },
    "csatdta2022": {
        "mode": "download",
        "url": "https://mdpi-res.com/d_attachment/ijms/ijms-23-08453/article_deploy/ijms-23-08453-v2.pdf?version=1659665969",
    },
    "deepdta2018": {
        "mode": "download_insecure",
        "url": "https://www.cmpe.boun.edu.tr/~hakime.ozturk/articles/eccb2018.pdf",
    },
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def simple_download(url: str, target: Path, verify: bool = True) -> dict[str, Any]:
    response = requests.get(url, headers=HEADERS, timeout=120, verify=verify)
    response.raise_for_status()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(response.content)
    return {"status": "downloaded", "path": str(target), "url": url}


def browser_print(url: str, target: Path) -> dict[str, Any]:
    cmd = [
        str(EDGE_PATH),
        "--headless=new",
        "--disable-gpu",
        f"--print-to-pdf={target}",
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False)
    if target.exists():
        return {"status": "downloaded", "path": str(target), "url": url}
    if proc.returncode != 0 or not target.exists():
        raise RuntimeError(proc.stderr[:400] or "no_pdf_created")
    return {"status": "downloaded", "path": str(target), "url": url}


def build_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# Tier 1 Source Bundle",
        "",
        f"- Papers requested: `{manifest['summary']['paper_count']}`",
        f"- PDFs downloaded: `{manifest['summary']['pdf_downloaded']}`",
        f"- PDFs blocked/unavailable: `{manifest['summary']['pdf_blocked_or_missing']}`",
        f"- Supplemental/evidence files downloaded: `{manifest['summary']['supplemental_downloads']}`",
        f"- Second-pass recovered PDFs: `{manifest['summary'].get('second_pass_recovered', 0)}`",
        "",
        "## Remaining Blocked or Missing PDFs",
        "",
    ]
    for row in manifest["papers"]:
        pdf = row["pdf"]
        if pdf.get("status") != "downloaded":
            lines.append(f"- `{row['paper_id']}`: `{pdf.get('status')}` {pdf.get('error', '')}".rstrip())
    return "\n".join(lines) + "\n"


def main() -> None:
    manifest = load_json(MANIFEST_PATH)
    for row in manifest["papers"]:
        spec = FIXES.get(row["paper_id"])
        if not spec:
            continue
        target = OUTPUT_ROOT / row["paper_id"] / "article_repaired" / "repaired.pdf"
        if spec["mode"] == "download":
            info = simple_download(spec["url"], target)
            source = "repair_download"
        elif spec["mode"] == "download_insecure":
            info = simple_download(spec["url"], target, verify=False)
            source = "repair_download_insecure"
        else:
            info = browser_print(spec["url"], target)
            source = "repair_browser_print"
        row.setdefault("recovery_attempts", []).append({"repair": info, "source": source})
        row["pdf"] = {"status": "downloaded", "path": info["path"], "source": source, "url": spec["url"]}

    manifest["summary"]["pdf_downloaded"] = sum(1 for row in manifest["papers"] if row["pdf"].get("status") == "downloaded")
    manifest["summary"]["pdf_blocked_or_missing"] = sum(1 for row in manifest["papers"] if row["pdf"].get("status") != "downloaded")
    write_json(MANIFEST_PATH, manifest)
    write_text(SUMMARY_MD, build_summary(manifest))
    print(json.dumps(manifest["summary"], indent=2))


if __name__ == "__main__":
    main()

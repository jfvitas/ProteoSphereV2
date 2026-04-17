from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import requests
import urllib3

try:
    import cloudscraper
except Exception:  # pragma: no cover
    cloudscraper = None

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REPO_ROOT = Path(__file__).resolve().parents[1]
MASTER_REPORT = REPO_ROOT / "artifacts" / "status" / "literature_hunt_tier1_master_summary.json"
OUTPUT_ROOT = REPO_ROOT / "artifacts" / "runtime" / "literature_hunt_tier1_source_bundle"
MANIFEST_PATH = OUTPUT_ROOT / "download_manifest.json"
SUMMARY_MD = REPO_ROOT / "docs" / "reports" / "literature_hunt_tier1_source_bundle.md"

EDGE_PATH = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
HEADERS = {"User-Agent": "Mozilla/5.0 (ProteoSphere tier1 pdf recovery)"}

RECOVERY_MAP: dict[str, dict[str, str]] = {
    "gnnseq2025": {
        "mode": "browser_print",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11945123/",
    },
    "empdta2024": {
        "mode": "browser_print",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11206982/",
    },
    "deattentiondta2024": {
        "mode": "download",
        "url": "https://pdfs.semanticscholar.org/dd54/1ea586e5a78ea6a7d61f3b31a712d4330724.pdf",
    },
    "imagedta2024": {
        "mode": "browser_print",
        "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11223229/",
    },
    "ss_gnn2023": {
        "mode": "download",
        "url": "https://arxiv.org/pdf/2206.07015.pdf",
    },
    "capla2023": {
        "mode": "download",
        "url": "https://pdfs.semanticscholar.org/b1be/c5a4e31ded9c59b89bb6661ab19edd2e159a.pdf",
    },
    "datadta2023": {
        "mode": "download",
        "url": "https://pdfs.semanticscholar.org/d6e2/43ef2393a7c7b575632ae8ce3fc2ba66d739.pdf",
    },
    "csatdta2022": {
        "mode": "download",
        "url": "https://pdfs.semanticscholar.org/e219/6b59bc79204f1d4620c9cabece37c5fcc0d5.pdf",
    },
    "graphdta2021": {
        "mode": "download_insecure",
        "url": "https://4llab.net/publication/btaa921.pdf",
    },
    "sagdta2021": {
        "mode": "download",
        "url": "https://mdpi-res.com/d_attachment/ijms/ijms-22-08993/article_deploy/ijms-22-08993-v2.pdf?version=1629686974",
    },
    "onionnet2019": {
        "mode": "cloudscraper",
        "url": "https://pubs.acs.org/doi/pdf/10.1021/acsomega.9b01997",
    },
    "pafnucy2018": {
        "mode": "download",
        "url": "https://arxiv.org/pdf/1811.08237.pdf",
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
    info = {"mode": "download", "url": url, "status": "failed"}
    try:
        response = requests.get(url, headers=HEADERS, timeout=120, verify=verify)
        info["http_status"] = response.status_code
        info["content_type"] = response.headers.get("content-type")
        if response.status_code >= 400:
            info["error"] = f"http_{response.status_code}"
            return info
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(response.content)
        info["status"] = "downloaded"
        info["path"] = str(target)
        return info
    except Exception as exc:
        info["error"] = str(exc)
        return info


def cloudscraper_download(url: str, target: Path) -> dict[str, Any]:
    info = {"mode": "cloudscraper", "url": url, "status": "failed"}
    if cloudscraper is None:
        info["error"] = "cloudscraper_unavailable"
        return info
    try:
        scraper = cloudscraper.create_scraper(browser={"browser": "chrome", "platform": "windows", "mobile": False})
        response = scraper.get(url, timeout=120)
        info["http_status"] = response.status_code
        info["content_type"] = response.headers.get("content-type")
        if response.status_code >= 400:
            info["error"] = f"http_{response.status_code}"
            return info
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(response.content)
        info["status"] = "downloaded"
        info["path"] = str(target)
        return info
    except Exception as exc:
        info["error"] = str(exc)
        return info


def browser_print(url: str, target: Path) -> dict[str, Any]:
    info = {"mode": "browser_print", "url": url, "status": "failed"}
    if not EDGE_PATH.exists():
        info["error"] = "edge_not_found"
        return info
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(EDGE_PATH),
        "--headless=new",
        "--disable-gpu",
        f"--print-to-pdf={target}",
        url,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False)
        info["exit_code"] = proc.returncode
        if proc.returncode != 0 or not target.exists():
            info["error"] = proc.stderr[:400] or "no_pdf_created"
            return info
        info["status"] = "downloaded"
        info["path"] = str(target)
        return info
    except Exception as exc:
        info["error"] = str(exc)
        return info


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
    lines.extend(["", "## Notes", ""])
    lines.append("- Second-pass recovery used alternate official or quasi-official sources such as PMC article pages, Semantic Scholar-hosted PDFs, mdpi-res deployment PDFs, ACS downloads through a browser-like client, and one author-hosted GraphDTA PDF.")
    return "\n".join(lines) + "\n"


def main() -> None:
    manifest = load_json(MANIFEST_PATH)
    recovered = 0
    for row in manifest["papers"]:
        if row["pdf"].get("status") == "downloaded":
            continue
        spec = RECOVERY_MAP.get(row["paper_id"])
        if not spec:
            continue
        target = OUTPUT_ROOT / row["paper_id"] / "article_recovered" / "recovered.pdf"
        mode = spec["mode"]
        if mode == "download":
            info = simple_download(spec["url"], target)
        elif mode == "download_insecure":
            info = simple_download(spec["url"], target, verify=False)
        elif mode == "cloudscraper":
            info = cloudscraper_download(spec["url"], target)
        elif mode == "browser_print":
            info = browser_print(spec["url"], target)
        else:
            info = {"mode": mode, "status": "failed", "error": "unknown_mode"}
        row.setdefault("recovery_attempts", []).append(info)
        if info.get("status") == "downloaded":
            row["pdf"] = {
                "status": "downloaded",
                "path": info["path"],
                "source": f"second_pass_{mode}",
                "url": spec["url"],
            }
            recovered += 1

    manifest["summary"]["pdf_downloaded"] = sum(1 for row in manifest["papers"] if row["pdf"].get("status") == "downloaded")
    manifest["summary"]["pdf_blocked_or_missing"] = sum(1 for row in manifest["papers"] if row["pdf"].get("status") != "downloaded")
    manifest["summary"]["second_pass_recovered"] = recovered
    write_json(MANIFEST_PATH, manifest)
    write_text(SUMMARY_MD, build_summary(manifest))
    print(json.dumps(manifest["summary"], indent=2))


if __name__ == "__main__":
    main()

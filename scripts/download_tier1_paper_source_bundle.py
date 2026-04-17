from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover
    BeautifulSoup = None


REPO_ROOT = Path(__file__).resolve().parents[1]
MASTER_REPORT = REPO_ROOT / "artifacts" / "status" / "literature_hunt_tier1_master_summary.json"
DEEP_PROOF_DIR = REPO_ROOT / "artifacts" / "status" / "literature_hunt_deep_proofs"
RECENT_PROOF_DIR = REPO_ROOT / "artifacts" / "status" / "literature_hunt_recent_expansion_proofs"
OUTPUT_ROOT = REPO_ROOT / "artifacts" / "runtime" / "literature_hunt_tier1_source_bundle"
MANIFEST_PATH = OUTPUT_ROOT / "download_manifest.json"
SUMMARY_MD = REPO_ROOT / "docs" / "reports" / "literature_hunt_tier1_source_bundle.md"

REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0 (ProteoSphere tier1 source bundle downloader)"}

EXTRA_LINKS: dict[str, list[str]] = {
    "d2cp05644e_2023": [
        "https://www.rsc.org/suppdata/d2/cp/d2cp05644e/d2cp05644e1.pdf",
        "https://github.com/DSIMB/PPSUS",
    ],
    "baranwal2022struct2graph": [
        "https://raw.githubusercontent.com/baranwa2/Struct2Graph/master/interactions_data.txt",
        "https://raw.githubusercontent.com/baranwa2/Struct2Graph/master/list_of_prots.txt",
    ],
}

LOCAL_PROOFS: dict[str, list[Path]] = {
    "baranwal2022struct2graph": [
        DEEP_PROOF_DIR / "struct2graph_local_audit.json",
        REPO_ROOT / "artifacts" / "status" / "paper_split_list" / "baranwal2022struct2graph.json",
        REPO_ROOT / "artifacts" / "status" / "struct2graph_overlap" / "struct2graph_reproduced_split_overlap.json",
        REPO_ROOT / "artifacts" / "status" / "struct2graph_overlap" / "4EQ6_train_test_overlay.png",
    ],
    "d2cp05644e_2023": [
        DEEP_PROOF_DIR / "d2cp05644e_local_forensic_audit.json",
        REPO_ROOT / "artifacts" / "status" / "paper_d2cp05644e" / "summary.json",
        REPO_ROOT / "artifacts" / "status" / "paper_d2cp05644e_detailed_audit.json",
    ],
    "attentiondta_tcbb2023": [
        RECENT_PROOF_DIR / "attentiondta_random_cv_family_audit.json",
    ],
}

FAMILY_PROOFS: dict[str, Path] = {
    "deepdta_setting1_family": DEEP_PROOF_DIR / "dta_setting1_family_audit.json",
    "pdbbind_core_family": DEEP_PROOF_DIR / "pdbbind_core_family_audit.json",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def slugify(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", text.strip())
    return text[:120].strip("_") or "file"


def guess_filename(url: str, content_type: str | None = None) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name
    if name and "." in name:
        return slugify(name)
    if content_type:
        if "pdf" in content_type:
            return "download.pdf"
        if "json" in content_type:
            return "download.json"
        if "html" in content_type:
            return "download.html"
    return "download.bin"


def request(url: str) -> requests.Response:
    return requests.get(url, headers=REQUEST_HEADERS, timeout=90, allow_redirects=True)


def crossref_message(doi_url: str) -> dict[str, Any]:
    doi = doi_url.replace("https://doi.org/", "").replace("http://doi.org/", "")
    response = request(f"https://api.crossref.org/works/{doi}")
    response.raise_for_status()
    return response.json()["message"]


def pick_pdf_link(message: dict[str, Any]) -> str | None:
    links = message.get("link") or []
    ranked: list[tuple[int, str]] = []
    for row in links:
        url = row.get("URL")
        if not url:
            continue
        content_type = str(row.get("content-type") or "")
        version = str(row.get("content-version") or "")
        rank = 0
        if "application/pdf" in content_type:
            rank += 10
        if version == "vor":
            rank += 3
        if url.lower().endswith(".pdf"):
            rank += 2
        ranked.append((rank, url))
    ranked.sort(reverse=True)
    return ranked[0][1] if ranked else None


def download_url(url: str, dest: Path) -> dict[str, Any]:
    info = {"url": url, "status": "failed"}
    try:
        response = request(url)
        info["http_status"] = response.status_code
        info["final_url"] = response.url
        info["content_type"] = response.headers.get("content-type")
        if response.status_code >= 400:
            info["error"] = f"http_{response.status_code}"
            return info
        filename = guess_filename(response.url or url, response.headers.get("content-type"))
        path = dest / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
        info["status"] = "downloaded"
        info["path"] = str(path)
        return info
    except Exception as exc:
        info["error"] = str(exc)
        return info


def find_supplement_links(html: str, base_url: str) -> list[str]:
    if not BeautifulSoup:
        return []
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    for anchor in soup.find_all("a", href=True):
        text = " ".join(anchor.get_text(" ", strip=True).split()).lower()
        href = anchor["href"]
        if any(token in text for token in ["supplement", "supporting information", "additional file", "source data", "appendix", "supp info", "si pdf"]):
            urls.append(urljoin(base_url, href))
    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique[:5]


def copy_local_file(path: Path, dest: Path) -> dict[str, Any]:
    info = {"path": str(path), "status": "missing"}
    if path.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        info["status"] = "copied"
        info["copied_to"] = str(dest)
    return info


def bundle_for_paper(row: dict[str, Any]) -> dict[str, Any]:
    paper_dir = OUTPUT_ROOT / row["paper_id"]
    paper_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "paper_id": row["paper_id"],
        "title": row["title"],
        "doi": row["doi"],
        "downloads": [],
        "local_proofs": [],
        "pdf": {"status": "not_attempted"},
        "supplements": [],
    }

    meta = crossref_message(row["doi"])
    write_json(paper_dir / "crossref_metadata.json", meta)

    pdf_url = pick_pdf_link(meta)
    if pdf_url:
        pdf_info = download_url(pdf_url, paper_dir / "article")
        result["pdf"] = pdf_info
    else:
        result["pdf"] = {"status": "unavailable_from_crossref"}

    landing = (meta.get("resource") or {}).get("primary", {}).get("URL")
    if landing:
        landing_info = download_url(landing, paper_dir / "landing")
        result["downloads"].append(landing_info)
        landing_path = landing_info.get("path")
        if landing_info.get("status") == "downloaded" and landing_path and str(landing_path).endswith(".html"):
            try:
                html = Path(landing_path).read_text(encoding="utf-8", errors="ignore")
                for idx, supp_url in enumerate(find_supplement_links(html, landing)[:3], start=1):
                    supp_info = download_url(supp_url, paper_dir / f"supplement_{idx}")
                    result["supplements"].append(supp_info)
            except Exception:
                pass

    for idx, url in enumerate(row.get("official_evidence_links") or [], start=1):
        result["downloads"].append(download_url(url, paper_dir / f"evidence_{idx}"))

    for idx, url in enumerate(EXTRA_LINKS.get(row["paper_id"], []), start=1):
        result["supplements"].append(download_url(url, paper_dir / f"extra_{idx}"))

    family_proof = FAMILY_PROOFS.get(row["benchmark_family"])
    if family_proof:
        proof_dest = paper_dir / "local_proofs" / family_proof.name
        result["local_proofs"].append(copy_local_file(family_proof, proof_dest))

    for proof_path in LOCAL_PROOFS.get(row["paper_id"], []):
        proof_dest = paper_dir / "local_proofs" / proof_path.name
        result["local_proofs"].append(copy_local_file(proof_path, proof_dest))

    write_json(paper_dir / "bundle_metadata.json", {"paper": row, "bundle": result})
    return result


def build_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# Tier 1 Source Bundle",
        "",
        f"- Papers requested: `{manifest['summary']['paper_count']}`",
        f"- PDFs downloaded: `{manifest['summary']['pdf_downloaded']}`",
        f"- PDFs blocked/unavailable: `{manifest['summary']['pdf_blocked_or_missing']}`",
        f"- Supplemental/evidence files downloaded: `{manifest['summary']['supplemental_downloads']}`",
        "",
        "## Blocked or Missing PDFs",
        "",
    ]
    for row in manifest["papers"]:
        pdf = row["pdf"]
        if pdf.get("status") != "downloaded":
            lines.append(f"- `{row['paper_id']}`: `{pdf.get('status')}` {pdf.get('error', '')}".rstrip())
    lines.extend(["", "## Notes", ""])
    lines.append("- For benchmark-family failures, the local proof JSON was copied into each paper bundle so the dataset issue is understandable even when the publisher PDF or supplement is blocked.")
    lines.append("- Official repo pages, raw README files, scripts, and supplemental PDFs were downloaded where reachable.")
    return "\n".join(lines) + "\n"


def main() -> None:
    report = load_json(MASTER_REPORT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    papers = report["papers"]
    bundled = [bundle_for_paper(row) for row in papers]
    manifest = {
        "artifact_id": "literature_hunt_tier1_source_bundle",
        "generated_at": Path(__file__).stat().st_mtime,
        "source_report": str(MASTER_REPORT),
        "summary": {
            "paper_count": len(bundled),
            "pdf_downloaded": sum(1 for row in bundled if row["pdf"].get("status") == "downloaded"),
            "pdf_blocked_or_missing": sum(1 for row in bundled if row["pdf"].get("status") != "downloaded"),
            "supplemental_downloads": sum(
                1
                for row in bundled
                for item in (row["downloads"] + row["supplements"] + row["local_proofs"])
                if item.get("status") in {"downloaded", "copied"}
            ),
        },
        "papers": bundled,
    }
    write_json(MANIFEST_PATH, manifest)
    write_text(SUMMARY_MD, build_summary(manifest))
    print(json.dumps(manifest["summary"], indent=2))


if __name__ == "__main__":
    main()

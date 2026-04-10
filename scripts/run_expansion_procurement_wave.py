from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from scripts.release_expansion_support import DEFAULT_EXTERNAL_DRIVE_ROOT, write_json
except ModuleNotFoundError:  # pragma: no cover
    from release_expansion_support import DEFAULT_EXTERNAL_DRIVE_ROOT, write_json


REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = REPO_ROOT / "artifacts" / "runtime" / "expansion_procurement_state.json"
LOG_ROOT = REPO_ROOT / "artifacts" / "runtime" / "expansion_procurement_logs"
USER_AGENT = "ProteoSphereV2-ExpansionWave/0.1"


class IndexLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


@dataclass(frozen=True)
class DatasetSpec:
    dataset_id: str
    mode: str
    source: str
    base_url: str | None = None
    explicit_files: tuple[str, ...] = ()
    skip_names: tuple[str, ...] = ()
    notes: str = ""
    max_depth: int = 0


DATASETS: tuple[DatasetSpec, ...] = (
    DatasetSpec(
        "uniprot_embeddings",
        "indexed",
        "UniProt embeddings",
        base_url="https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/embeddings/",
        max_depth=1,
    ),
    DatasetSpec(
        "uniprot_variants",
        "indexed",
        "UniProt variants",
        base_url="https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/variants/",
    ),
    DatasetSpec(
        "uniprot_proteomics_mapping",
        "indexed",
        "UniProt proteomics mapping",
        base_url="https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/proteomics_mapping/",
    ),
    DatasetSpec(
        "uniprot_genome_annotation_tracks",
        "indexed",
        "UniProt genome annotation tracks",
        base_url="https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/genome_annotation_tracks/",
        max_depth=1,
    ),
    DatasetSpec(
        "alphafold_additional_proteomes",
        "indexed",
        "AlphaFold latest additional proteomes",
        base_url="https://ftp.ebi.ac.uk/pub/databases/alphafold/latest/",
        skip_names=("swissprot_cif_v6.tar", "swissprot_pdb_v6.tar"),
    ),
    DatasetSpec(
        "uniprot_pan_proteomes",
        "indexed",
        "UniProt pan proteomes",
        base_url="https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/pan_proteomes/",
    ),
    DatasetSpec(
        "uniprot_reference_proteomes",
        "explicit",
        "UniProt reference proteomes",
        explicit_files=(
            "https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/reference_proteomes/README",
            "https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/reference_proteomes/RELEASE.metalink",
            "https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/reference_proteomes/STATS",
            "https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/reference_proteomes/Reference_Proteomes_2026_01.tar.gz",
        ),
        notes=(
            "The additional tarball from the planning report is not currently "
            "resolved on the live listing."
        ),
    ),
    DatasetSpec(
        "uniprot_taxonomic_divisions",
        "indexed",
        "UniProt taxonomic divisions",
        base_url="https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/taxonomic_divisions/",
    ),
    DatasetSpec(
        "ebi_qfo_reference_proteomes",
        "explicit",
        "EBI QfO reference proteomes",
        explicit_files=(
            "https://ftp.ebi.ac.uk/pub/databases/reference_proteomes/QfO/README",
            "https://ftp.ebi.ac.uk/pub/databases/reference_proteomes/QfO/STATS",
            "https://ftp.ebi.ac.uk/pub/databases/reference_proteomes/QfO/PROTEOME_ASSEMBLY_MAPPING",
            "https://ftp.ebi.ac.uk/pub/databases/reference_proteomes/QfO/UPKB_PROTEIN_GENE_MAPPING",
            "https://ftp.ebi.ac.uk/pub/databases/reference_proteomes/QfO/QfO_release_2025_04.tar.gz",
            "https://ftp.ebi.ac.uk/pub/databases/reference_proteomes/QfO/QfO_release_2025_04_additional.tar.gz",
        ),
        notes=(
            "Resolved live QfO release path under the EBI reference proteomes mirror, "
            "including core metadata and both release tarballs."
        ),
    ),
    DatasetSpec(
        "mega_motif_base_backbone_procurement",
        "explicit",
        "MegaMotifBase",
        explicit_files=(
            "https://caps.ncbs.res.in/MegaMotifbase/download.html",
            "https://caps.ncbs.res.in/MegaMotifbase/Megamotif-v1-sf-alignment.tar.gz",
            "https://caps.ncbs.res.in/MegaMotifbase/Megamotif-v1-sf-motif.gz",
            "https://caps.ncbs.res.in/MegaMotifbase/Megamotif-v1-fam-alignment.tar.gz",
            "https://caps.ncbs.res.in/MegaMotifbase/Megamotif-v1-fam-motif.gz",
            "https://caps.ncbs.res.in/MegaMotifbase/index.html",
            "https://caps.ncbs.res.in/MegaMotifbase/sflist.html",
            "https://caps.ncbs.res.in/MegaMotifbase/famlist.html",
            "https://caps.ncbs.res.in/MegaMotifbase/search.html",
            "https://caps.ncbs.res.in/MegaMotifbase/help.html",
        ),
        notes=(
            "Procure all four published MegaMotifBase download lanes plus core site pages "
            "covering family/superfamily navigation and help."
        ),
    ),
    DatasetSpec(
        "motivated_proteins_backbone_procurement",
        "explicit",
        "Motivated Proteins",
        explicit_files=(
            "https://motif.mvls.gla.ac.uk/index.html",
            "https://motif.mvls.gla.ac.uk/motif/index.html",
            "https://motif.mvls.gla.ac.uk/ProtMotif21/index.html",
            "https://motif.mvls.gla.ac.uk/motivator.html",
            "https://motif.mvls.gla.ac.uk/motifhelp/index.html",
            "https://motif.mvls.gla.ac.uk/helpRef/index.html",
            "https://motif.mvls.gla.ac.uk/downloads/Motivator2.dmg",
            "https://motif.mvls.gla.ac.uk/downloads/Motivator2_Win32.zip",
            "https://motif.mvls.gla.ac.uk/downloads/Motivator2_Win64.zip",
            "https://motif.mvls.gla.ac.uk/downloads/Motivator2_Unix.zip",
            "https://motif.mvls.gla.ac.uk/downloads/MotivatorManual.pdf",
            "https://motif.mvls.gla.ac.uk/downloads/MotivatorFiles.zip",
        ),
        notes=(
            "No single public bulk dump is exposed; preserve the original site, MP2 entrypoint, "
            "help/docs, and all downloadable desktop/data bundles."
        ),
    ),
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def fetch_text(url: str) -> str:
    command = [
        "curl.exe",
        "--fail",
        "--location",
        "--retry",
        "8",
        "--retry-all-errors",
        "--max-time",
        "180",
        "--user-agent",
        USER_AGENT,
        "--silent",
        "--show-error",
        url,
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"Failed to fetch index text for {url}: "
            f"curl exited {completed.returncode}: {completed.stderr.strip()}"
        )
    return completed.stdout


def fetch_size(url: str) -> int | None:
    command = [
        "curl.exe",
        "--fail",
        "--location",
        "--retry",
        "5",
        "--retry-all-errors",
        "--max-time",
        "120",
        "--user-agent",
        USER_AGENT,
        "--silent",
        "--show-error",
        "--head",
        url,
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    for line in completed.stdout.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip().lower() == "content-length":
            value = value.strip()
            return int(value) if value.isdigit() else None
    return None


def list_indexed_files(base_url: str, *, max_depth: int, skip_names: set[str]) -> list[str]:
    pending: list[tuple[str, int]] = [(base_url, 0)]
    seen_dirs: set[str] = set()
    files: list[str] = []
    while pending:
        current, depth = pending.pop()
        if current in seen_dirs:
            continue
        seen_dirs.add(current)
        parser = IndexLinkParser()
        parser.feed(fetch_text(current))
        for href in parser.links:
            if href.startswith("?") or href.startswith("/icons/") or href == "../":
                continue
            next_url = urljoin(current, href)
            name = Path(urlparse(next_url).path).name
            if name in skip_names:
                continue
            if href.endswith("/"):
                if depth < max_depth:
                    pending.append((next_url, depth + 1))
            elif name and name not in {"Parent Directory"}:
                files.append(next_url)
    return sorted(set(files))


def local_path_for_url(root: Path, dataset_id: str, url: str) -> Path:
    parsed = urlparse(url)
    relative = parsed.path.lstrip("/")
    relative_path = Path(*relative.split("/"))
    return root / "data" / "raw" / "expansion_procurement" / dataset_id / relative_path


def download_file(url: str, destination: Path, log_path: Path) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    remote_size = fetch_size(url)
    local_size = destination.stat().st_size if destination.exists() else None
    if remote_size is not None and local_size == remote_size:
        return {
            "url": url,
            "destination": str(destination),
            "status": "already_present",
            "remote_size": remote_size,
            "local_size": local_size,
        }
    with log_path.open("a", encoding="utf-8") as log_handle:
        log_handle.write(f"[{utc_now()}] download {url} -> {destination}\n")
        log_handle.flush()
        command = [
            "curl.exe",
            "--fail",
            "--location",
            "--retry",
            "8",
            "--retry-all-errors",
            "--continue-at",
            "-",
            "--output",
            str(destination),
            url,
        ]
        completed = subprocess.run(command, stdout=log_handle, stderr=log_handle, check=False)
    return {
        "url": url,
        "destination": str(destination),
        "status": "downloaded" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "remote_size": remote_size,
        "local_size": destination.stat().st_size if destination.exists() else None,
    }


def _write_state(
    *,
    external_root: Path,
    dataset_states: dict[str, Any],
    unresolved_items: list[dict[str, Any]],
    started_at: str,
    active_dataset: str | None = None,
    finished_at: str | None = None,
) -> None:
    write_json(
        STATE_PATH,
        {
            "started_at": started_at,
            "updated_at": utc_now(),
            "finished_at": finished_at,
            "external_root": str(external_root),
            "active_dataset": active_dataset,
            "dataset_results": dataset_states,
            "unresolved_items": unresolved_items,
        },
    )


def run_dataset(
    spec: DatasetSpec,
    external_root: Path,
    *,
    dataset_states: dict[str, Any],
    unresolved_items: list[dict[str, Any]],
    started_at: str,
) -> dict[str, Any]:
    dataset_log = LOG_ROOT / f"{spec.dataset_id}.log"
    dataset_states[spec.dataset_id] = {
        "source": spec.source,
        "mode": spec.mode,
        "status": "discovering",
        "file_count": None,
        "completed_count": 0,
        "failed_count": 0,
        "notes": spec.notes,
    }
    _write_state(
        external_root=external_root,
        dataset_states=dataset_states,
        unresolved_items=unresolved_items,
        started_at=started_at,
        active_dataset=spec.dataset_id,
    )
    if spec.mode == "indexed":
        urls = list_indexed_files(
            spec.base_url or "",
            max_depth=spec.max_depth,
            skip_names=set(spec.skip_names),
        )
    else:
        urls = list(spec.explicit_files)
    dataset_states[spec.dataset_id] = {
        "source": spec.source,
        "mode": spec.mode,
        "status": "downloading",
        "file_count": len(urls),
        "completed_count": 0,
        "failed_count": 0,
        "notes": spec.notes,
    }
    _write_state(
        external_root=external_root,
        dataset_states=dataset_states,
        unresolved_items=unresolved_items,
        started_at=started_at,
        active_dataset=spec.dataset_id,
    )
    results = []
    for url in urls:
        result = download_file(
            url,
            local_path_for_url(external_root, spec.dataset_id, url),
            dataset_log,
        )
        results.append(result)
        dataset_states[spec.dataset_id] = {
            "source": spec.source,
            "mode": spec.mode,
            "status": "failed" if result["status"] == "failed" else "downloading",
            "file_count": len(urls),
            "completed_count": sum(
                1 for item in results if item["status"] in {"downloaded", "already_present"}
            ),
            "failed_count": sum(1 for item in results if item["status"] == "failed"),
            "notes": spec.notes,
            "last_url": url,
            "last_destination": str(local_path_for_url(external_root, spec.dataset_id, url)),
        }
        _write_state(
            external_root=external_root,
            dataset_states=dataset_states,
            unresolved_items=unresolved_items,
            started_at=started_at,
            active_dataset=spec.dataset_id,
        )
        if result["status"] == "failed":
            break
    dataset_states[spec.dataset_id] = {
        "source": spec.source,
        "mode": spec.mode,
        "status": "completed" if all(item["status"] != "failed" for item in results) else "failed",
        "file_count": len(urls),
        "completed_count": sum(
            1 for item in results if item["status"] in {"downloaded", "already_present"}
        ),
        "failed_count": sum(1 for item in results if item["status"] == "failed"),
        "notes": spec.notes,
    }
    _write_state(
        external_root=external_root,
        dataset_states=dataset_states,
        unresolved_items=unresolved_items,
        started_at=started_at,
        active_dataset=spec.dataset_id,
    )
    return {
        "dataset_id": spec.dataset_id,
        "source": spec.source,
        "mode": spec.mode,
        "file_count": len(urls),
        "completed_count": sum(
            1 for item in results if item["status"] in {"downloaded", "already_present"}
        ),
        "failed_count": sum(1 for item in results if item["status"] == "failed"),
        "notes": spec.notes,
        "results": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the expansion procurement download wave.")
    parser.add_argument("--external-root", type=Path, default=DEFAULT_EXTERNAL_DRIVE_ROOT)
    parser.add_argument("--dataset", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.external_root.mkdir(parents=True, exist_ok=True)
    wanted = set(args.dataset or [spec.dataset_id for spec in DATASETS])
    selected = [spec for spec in DATASETS if spec.dataset_id in wanted]
    started_at = utc_now()
    unresolved_items: list[dict[str, Any]] = []
    dataset_states: dict[str, Any] = {}
    payload = {
        "started_at": started_at,
        "external_root": str(args.external_root),
        "datasets": [],
        "unresolved_items": unresolved_items,
    }
    _write_state(
        external_root=args.external_root,
        dataset_states=dataset_states,
        unresolved_items=unresolved_items,
        started_at=started_at,
        active_dataset=None,
    )
    for spec in selected:
        payload["datasets"].append(
            run_dataset(
                spec,
                args.external_root,
                dataset_states=dataset_states,
                unresolved_items=unresolved_items,
                started_at=started_at,
            )
        )
        write_json(STATE_PATH, payload)
    payload["finished_at"] = utc_now()
    write_json(STATE_PATH, payload)
    _write_state(
        external_root=args.external_root,
        dataset_states=dataset_states,
        unresolved_items=unresolved_items,
        started_at=started_at,
        active_dataset=None,
        finished_at=payload["finished_at"],
    )
    print(STATE_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

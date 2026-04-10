from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from connectors.bindingdb.client import BindingDBClient
from connectors.rcsb.client import RCSBClient
from connectors.uniprot.client import UniProtClient
from core.procurement.source_release_manifest import SourceReleaseManifest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_ROOT = ROOT / "data" / "raw"
DEFAULT_USEFULNESS_REVIEW = (
    ROOT
    / "runs"
    / "real_data_benchmark"
    / "full_results"
    / "usefulness_review.json"
)
USER_AGENT = "ProteoSphereV2-RawBootstrap/0.1"
DEFAULT_SOURCES = ("uniprot", "alphafold", "bindingdb", "intact", "rcsb_pdbe", "pdbbind")
INTACT_INTERACTOR_BASE = "https://www.ebi.ac.uk/intact/ws/interactor/findInteractor"
INTACT_PSICQUIC_BASE = (
    "https://www.ebi.ac.uk/Tools/webservices/psicquic/intact/webservices/current/search/query"
)
PDBe_BEST_STRUCTURES_BASE = "https://www.ebi.ac.uk/pdbe/api/mappings/best_structures"
ALPHAFOLD_API_BASE = "https://alphafold.ebi.ac.uk/api/prediction"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _timestamp_slug() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _write_json(path: Path, payload: Any) -> None:
    _write_text(path, json.dumps(payload, indent=2))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _normalize_accessions(values: Sequence[str]) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in values:
        accession = _text(value).upper()
        if accession:
            ordered.setdefault(accession.casefold(), accession)
    return tuple(ordered.values())


def _split_csv(values: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in values.split(",") if item.strip())


def _default_accessions() -> tuple[str, ...]:
    if not DEFAULT_USEFULNESS_REVIEW.exists():
        return ()
    payload = _read_json(DEFAULT_USEFULNESS_REVIEW)
    return _normalize_accessions(
        [
            _text(row.get("accession"))
            for row in payload.get("example_reviews") or ()
            if isinstance(row, Mapping)
        ]
    )


def _request_bytes(
    url: str,
    *,
    opener: Callable[..., Any] | None = None,
) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    request_opener = opener or urlopen
    with request_opener(request, timeout=60.0) as response:
        return response.read()


def _request_json(
    url: str,
    *,
    opener: Callable[..., Any] | None = None,
) -> Any:
    return json.loads(_request_bytes(url, opener=opener).decode("utf-8"))


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def _write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_bytes(path, payload.encode("utf-8"))


def _has_blocking_failures(results: Sequence[Mapping[str, Any]]) -> bool:
    for result in results:
        source = _text(result.get("source")).casefold()
        status = _text(result.get("status")).casefold()
        if status == "failed":
            return True
        if source == "pdbbind":
            continue
        if status in {"manual_acquisition_required", "manual_gate"}:
            continue
    return False


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _build_source_completion_metadata(
    *,
    release_dir: Path,
    dry_run: bool,
    failed: bool,
) -> dict[str, Any]:
    manifest_path = release_dir / "manifest.json"
    manifest_exists = manifest_path.exists()
    if dry_run:
        state = "dry_run"
    elif failed:
        state = "failed"
    elif manifest_exists:
        state = "materialized"
    else:
        state = "incomplete"
    return {
        "completion_state": state,
        "manifest_path": _display_path(manifest_path),
        "manifest_exists": manifest_exists,
        "completed_at": _utc_now().isoformat() if manifest_exists else None,
    }


def _build_source_identity_metadata(
    *,
    release_dir: Path,
    dry_run: bool,
    failed: bool,
) -> dict[str, Any]:
    if dry_run:
        return {
            "identity_basis": "not_materialized",
            "identity_state": "dry_run",
            "release_dir": _display_path(release_dir),
            "manifest_sha256": None,
            "artifact_inventory_sha256": None,
            "materialized_file_count": 0,
        }

    file_records: list[dict[str, Any]] = []
    manifest_path = release_dir / "manifest.json"
    for path in sorted(
        candidate
        for candidate in release_dir.rglob("*")
        if candidate.is_file() and not candidate.name.endswith(".tmp")
    ):
        file_records.append(
            {
                "path": _display_path(path),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )

    if failed:
        identity_state = (
            "partial_materialization"
            if file_records
            else "failed_without_materialization"
        )
    elif manifest_path.is_file():
        identity_state = "materialized"
    elif file_records:
        identity_state = "incomplete_without_manifest"
    else:
        identity_state = "empty"

    inventory_digest = None
    if file_records:
        inventory_digest = _sha256_bytes(
            json.dumps(file_records, indent=2, sort_keys=True).encode("utf-8")
        )

    return {
        "identity_basis": "local_materialized_file_inventory",
        "identity_state": identity_state,
        "release_dir": _display_path(release_dir),
        "manifest_sha256": _sha256_file(manifest_path) if manifest_path.is_file() else None,
        "artifact_inventory_sha256": inventory_digest,
        "materialized_file_count": len(file_records),
    }


def _safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)


def _make_manifest(
    *,
    source_name: str,
    retrieval_mode: str,
    source_locator: str,
    release_version: str | None,
    local_artifact_refs: Sequence[str],
    provenance: Sequence[str],
    reproducibility_metadata: Sequence[str] = (),
) -> dict[str, Any]:
    release_stamp = release_version or _utc_now().date().isoformat()
    manifest = SourceReleaseManifest(
        source_name=source_name,
        release_version=release_stamp,
        retrieval_mode=retrieval_mode,
        source_locator=source_locator,
        local_artifact_refs=tuple(local_artifact_refs),
        provenance=tuple(provenance),
        reproducibility_metadata=tuple(reproducibility_metadata),
    )
    return manifest.to_dict()


def _make_opener(*, allow_insecure_ssl: bool) -> Callable[..., Any] | None:
    if not allow_insecure_ssl:
        return None
    context = ssl._create_unverified_context()

    def opener(request: Any, timeout: float | None = None) -> Any:
        if isinstance(request, str):
            request = Request(request, headers={"User-Agent": USER_AGENT})
        return urlopen(request, timeout=timeout, context=context)

    return opener


def _download_uniprot(
    *,
    accessions: Sequence[str],
    release_dir: Path,
    opener: Callable[..., Any] | None,
    dry_run: bool,
) -> dict[str, Any]:
    client = UniProtClient()
    downloaded: list[str] = []
    for accession in accessions:
        accession_dir = release_dir / accession
        files = {
            "entry_json": accession_dir / f"{accession}.json",
            "fasta": accession_dir / f"{accession}.fasta",
            "txt": accession_dir / f"{accession}.txt",
        }
        if dry_run:
            downloaded.extend(str(path.relative_to(ROOT)) for path in files.values())
            continue
        _write_json(files["entry_json"], client.get_entry(accession, opener=opener))
        _write_text(files["fasta"], client.get_fasta(accession, opener=opener))
        _write_text(files["txt"], client.get_text(accession, opener=opener))
        downloaded.extend(str(path.relative_to(ROOT)) for path in files.values())

    manifest = _make_manifest(
        source_name="UniProt",
        retrieval_mode="api",
        source_locator="https://rest.uniprot.org/uniprotkb",
        release_version=_utc_now().date().isoformat(),
        local_artifact_refs=downloaded,
        provenance=("raw_bootstrap", "accession_scoped", "json_fasta_txt"),
    )
    if not dry_run:
        _write_json(release_dir / "manifest.json", manifest)
    return {"source": "uniprot", "downloaded_files": downloaded, "manifest": manifest}


def _alphafold_asset_urls(record: Mapping[str, Any]) -> dict[str, str]:
    keys = {
        "bcif": ("bcifUrl",),
        "cif": ("cifUrl",),
        "pdb": ("pdbUrl",),
        "msa": ("msaUrl",),
        "plddt_doc": ("plddtDocUrl",),
        "pae_doc": ("paeDocUrl",),
        "pae_image": ("paeImageUrl",),
    }
    resolved: dict[str, str] = {}
    for asset_name, candidates in keys.items():
        for candidate in candidates:
            value = _text(record.get(candidate))
            if value:
                resolved[asset_name] = value
                break
    return resolved


def _download_alphafold(
    *,
    accessions: Sequence[str],
    release_dir: Path,
    opener: Callable[..., Any] | None,
    dry_run: bool,
    download_assets: bool,
) -> dict[str, Any]:
    downloaded: list[str] = []
    missing_accessions: list[str] = []
    for accession in accessions:
        accession_dir = release_dir / accession
        api_url = f"{ALPHAFOLD_API_BASE}/{accession}"
        json_path = accession_dir / f"{accession}.prediction.json"
        if dry_run:
            downloaded.append(str(json_path.relative_to(ROOT)))
            continue
        try:
            payload = _request_json(api_url, opener=opener)
        except HTTPError as exc:
            if exc.code == 404:
                missing_accessions.append(accession)
                continue
            raise
        _write_json(json_path, payload)
        downloaded.append(str(json_path.relative_to(ROOT)))
        if not download_assets or not isinstance(payload, list) or not payload:
            continue
        asset_urls = _alphafold_asset_urls(payload[0])
        for asset_name, url in asset_urls.items():
            suffix = Path(url).suffix or ".bin"
            asset_path = accession_dir / f"{accession}.{asset_name}{suffix}"
            _write_bytes(asset_path, _request_bytes(url, opener=opener))
            downloaded.append(str(asset_path.relative_to(ROOT)))

    manifest = _make_manifest(
        source_name="AlphaFold DB",
        retrieval_mode="api",
        source_locator=ALPHAFOLD_API_BASE,
        release_version=_utc_now().date().isoformat(),
        local_artifact_refs=downloaded,
        provenance=("raw_bootstrap", "accession_scoped", "prediction_api"),
    )
    if not dry_run:
        _write_json(release_dir / "manifest.json", manifest)
    result: dict[str, Any] = {
        "source": "alphafold",
        "downloaded_files": downloaded,
        "manifest": manifest,
    }
    if missing_accessions:
        result["status"] = "partial"
        result["missing_accessions"] = list(missing_accessions)
        result["notes"] = [
            "one or more accessions returned AlphaFold HTTP 404 and were skipped"
        ]
    return result


def _download_bindingdb(
    *,
    accessions: Sequence[str],
    release_dir: Path,
    opener: Callable[..., Any] | None,
    dry_run: bool,
) -> dict[str, Any]:
    client = BindingDBClient()
    downloaded: list[str] = []
    for accession in accessions:
        accession_dir = release_dir / accession
        json_path = accession_dir / f"{accession}.bindingdb.json"
        if dry_run:
            downloaded.append(str(json_path.relative_to(ROOT)))
            continue
        payload = client.get_ligands_by_uniprot(accession, opener=opener)
        _write_json(json_path, payload)
        downloaded.append(str(json_path.relative_to(ROOT)))

    manifest = _make_manifest(
        source_name="BindingDB",
        retrieval_mode="api",
        source_locator="https://www.bindingdb.org/rest/getLigandsByUniprot",
        release_version=_utc_now().date().isoformat(),
        local_artifact_refs=downloaded,
        provenance=("raw_bootstrap", "accession_scoped", "ligands_by_uniprot"),
    )
    if not dry_run:
        _write_json(release_dir / "manifest.json", manifest)
    return {"source": "bindingdb", "downloaded_files": downloaded, "manifest": manifest}


def _download_intact(
    *,
    accessions: Sequence[str],
    release_dir: Path,
    opener: Callable[..., Any] | None,
    dry_run: bool,
    psicquic_max_results: int,
) -> dict[str, Any]:
    downloaded: list[str] = []
    for accession in accessions:
        accession_dir = release_dir / accession
        interactor_url = f"{INTACT_INTERACTOR_BASE}/{accession}"
        psicquic_url = (
            f"{INTACT_PSICQUIC_BASE}/id:{accession}"
            f"?format=tab25&firstResult=0&maxResults={psicquic_max_results}"
        )
        interactor_path = accession_dir / f"{accession}.interactor.json"
        psicquic_path = accession_dir / f"{accession}.psicquic.tab25.txt"
        if dry_run:
            downloaded.extend(
                [
                    str(interactor_path.relative_to(ROOT)),
                    str(psicquic_path.relative_to(ROOT)),
                ]
            )
            continue
        _write_json(interactor_path, _request_json(interactor_url, opener=opener))
        _write_bytes(psicquic_path, _request_bytes(psicquic_url, opener=opener))
        downloaded.extend(
            [
                str(interactor_path.relative_to(ROOT)),
                str(psicquic_path.relative_to(ROOT)),
            ]
        )

    manifest = _make_manifest(
        source_name="IntAct",
        retrieval_mode="api",
        source_locator=INTACT_INTERACTOR_BASE,
        release_version=_utc_now().date().isoformat(),
        local_artifact_refs=downloaded,
        provenance=("raw_bootstrap", "accession_scoped", "interactor_and_psicquic"),
    )
    if not dry_run:
        _write_json(release_dir / "manifest.json", manifest)
    return {"source": "intact", "downloaded_files": downloaded, "manifest": manifest}


def _best_structure_mapping(
    accession: str,
    *,
    opener: Callable[..., Any] | None,
) -> list[dict[str, Any]]:
    url = f"{PDBe_BEST_STRUCTURES_BASE}/{accession}"
    try:
        payload = _request_json(url, opener=opener)
    except HTTPError as exc:
        if exc.code == 404:
            return []
        raise
    entries = payload.get(accession) or payload.get(accession.upper()) or []
    return [dict(item) for item in entries if isinstance(item, Mapping)]


def _download_rcsb_pdbe(
    *,
    accessions: Sequence[str],
    release_dir: Path,
    opener: Callable[..., Any] | None,
    dry_run: bool,
    max_structures_per_accession: int,
    download_mmcif: bool,
) -> dict[str, Any]:
    client = RCSBClient()
    downloaded: list[str] = []
    structure_targets: dict[str, list[str]] = {}
    for accession in accessions:
        accession_dir = release_dir / accession
        mapping_path = accession_dir / f"{accession}.best_structures.json"
        mappings = _best_structure_mapping(accession, opener=opener) if not dry_run else []
        if dry_run:
            downloaded.append(str(mapping_path.relative_to(ROOT)))
            continue
        _write_json(mapping_path, mappings)
        downloaded.append(str(mapping_path.relative_to(ROOT)))
        pdb_ids: list[str] = []
        for item in mappings:
            pdb_id = _text(item.get("pdb_id")).upper()
            if pdb_id and pdb_id not in pdb_ids:
                pdb_ids.append(pdb_id)
            if len(pdb_ids) >= max_structures_per_accession:
                break
        structure_targets[accession] = list(pdb_ids)
        for pdb_id in pdb_ids:
            pdb_dir = accession_dir / pdb_id
            entry_path = pdb_dir / f"{pdb_id}.entry.json"
            _write_json(entry_path, client.get_entry(pdb_id, opener=opener))
            downloaded.append(str(entry_path.relative_to(ROOT)))
            if download_mmcif:
                cif_path = pdb_dir / f"{pdb_id}.cif"
                _write_text(cif_path, client.get_mmcif(pdb_id, opener=opener))
                downloaded.append(str(cif_path.relative_to(ROOT)))

    manifest = _make_manifest(
        source_name="RCSB/PDBe",
        retrieval_mode="api",
        source_locator=PDBe_BEST_STRUCTURES_BASE,
        release_version=_utc_now().date().isoformat(),
        local_artifact_refs=downloaded,
        provenance=("raw_bootstrap", "accession_scoped", "best_structures_plus_entry"),
    )
    if not dry_run:
        _write_json(release_dir / "manifest.json", manifest)
        _write_json(release_dir / "structure_targets.json", structure_targets)
    return {
        "source": "rcsb_pdbe",
        "downloaded_files": downloaded,
        "manifest": manifest,
        "structure_targets": structure_targets,
    }


def _register_pdbbind_placeholder(
    *,
    accessions: Sequence[str],
    release_dir: Path,
    dry_run: bool,
) -> dict[str, Any]:
    instructions = {
        "source": "pdbbind",
        "status": "manual_acquisition_required",
        "generated_at": _utc_now().isoformat(),
        "requested_accessions": list(accessions),
        "drop_location": _display_path(release_dir / "manual_drop"),
        "notes": [
            "This repo does not yet automate PDBBind acquisition.",
            (
                "Place the authorized archive or extracted release under the "
                "manual_drop directory."
            ),
            (
                "After adding the files, record the exact release identifier "
                "and checksum set in this folder."
            ),
        ],
    }
    if not dry_run:
        _write_json(release_dir / "manual_acquisition_required.json", instructions)
    manifest = _make_manifest(
        source_name="PDBBind",
        retrieval_mode="download",
        source_locator="manual_drop_required",
        release_version=_utc_now().date().isoformat(),
        local_artifact_refs=(
            _display_path(release_dir / "manual_acquisition_required.json"),
        )
        if not dry_run
        else (),
        provenance=("raw_bootstrap", "manual_gate"),
    )
    if not dry_run:
        _write_json(release_dir / "manifest.json", manifest)
    return {
        "source": "pdbbind",
        "downloaded_files": [],
        "manifest": manifest,
        "instructions": instructions,
    }


def run_bootstrap(
    *,
    accessions: Sequence[str],
    sources: Sequence[str],
    raw_root: Path,
    allow_insecure_ssl: bool,
    dry_run: bool,
    alphafold_assets: bool,
    max_structures_per_accession: int,
    download_mmcif: bool,
    psicquic_max_results: int,
) -> dict[str, Any]:
    opener = _make_opener(allow_insecure_ssl=allow_insecure_ssl)
    stamp = _timestamp_slug()
    raw_root.mkdir(parents=True, exist_ok=True)
    run_summary: dict[str, Any] = {
        "generated_at": _utc_now().isoformat(),
        "raw_root": str(raw_root),
        "sources": list(sources),
        "accessions": list(accessions),
        "stamp": stamp,
        "results": [],
    }

    source_funcs = {
        "uniprot": lambda release_dir: _download_uniprot(
            accessions=accessions,
            release_dir=release_dir,
            opener=opener,
            dry_run=dry_run,
        ),
        "alphafold": lambda release_dir: _download_alphafold(
            accessions=accessions,
            release_dir=release_dir,
            opener=opener,
            dry_run=dry_run,
            download_assets=alphafold_assets,
        ),
        "bindingdb": lambda release_dir: _download_bindingdb(
            accessions=accessions,
            release_dir=release_dir,
            opener=opener,
            dry_run=dry_run,
        ),
        "intact": lambda release_dir: _download_intact(
            accessions=accessions,
            release_dir=release_dir,
            opener=opener,
            dry_run=dry_run,
            psicquic_max_results=psicquic_max_results,
        ),
        "rcsb_pdbe": lambda release_dir: _download_rcsb_pdbe(
            accessions=accessions,
            release_dir=release_dir,
            opener=opener,
            dry_run=dry_run,
            max_structures_per_accession=max_structures_per_accession,
            download_mmcif=download_mmcif,
        ),
        "pdbbind": lambda release_dir: _register_pdbbind_placeholder(
            accessions=accessions,
            release_dir=release_dir,
            dry_run=dry_run,
        ),
    }

    for source in sources:
        release_dir = raw_root / source / stamp
        try:
            result = source_funcs[source](release_dir)
            result["status"] = _text(result.get("status")) or "ok"
            completion = _build_source_completion_metadata(
                release_dir=release_dir,
                dry_run=dry_run,
                failed=False,
            )
        except Exception as exc:  # pragma: no cover - live network/runtime path
            result = {
                "source": source,
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
                "downloaded_files": [],
            }
            completion = _build_source_completion_metadata(
                release_dir=release_dir,
                dry_run=dry_run,
                failed=True,
            )
        result["write_complete"] = bool(completion["manifest_exists"])
        result["completion_metadata"] = completion
        result["snapshot_identity"] = _build_source_identity_metadata(
            release_dir=release_dir,
            dry_run=dry_run,
            failed=_text(result.get("status")).casefold() == "failed",
        )
        run_summary["results"].append(result)

    summary_path = raw_root / "bootstrap_runs" / f"{stamp}.json"
    latest_path = raw_root / "bootstrap_runs" / "LATEST.json"
    has_blocking_failures = _has_blocking_failures(run_summary["results"])
    run_summary["status"] = "failed" if has_blocking_failures else "ok"
    if has_blocking_failures:
        run_summary["notes"] = [
            "one or more required bootstrap sources failed; LATEST was not promoted"
        ]
    if not dry_run:
        _write_json(summary_path, run_summary)
        if not has_blocking_failures:
            _write_json(latest_path, run_summary)
    run_summary["summary_path"] = _display_path(summary_path)
    return run_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download raw source payloads into data/raw.")
    parser.add_argument(
        "--accessions",
        type=str,
        default="",
        help="Comma-separated UniProt accessions. Defaults to the frozen benchmark cohort.",
    )
    parser.add_argument(
        "--sources",
        type=str,
        default=",".join(DEFAULT_SOURCES),
        help=(
            "Comma-separated source list. Supported: uniprot, alphafold, "
            "bindingdb, intact, rcsb_pdbe, pdbbind."
        ),
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=DEFAULT_RAW_ROOT,
        help="Root directory for raw source payloads.",
    )
    parser.add_argument(
        "--allow-insecure-ssl",
        action="store_true",
        help="Allow unverified SSL for endpoints that fail on this workstation's trust store.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned acquisition summary without writing files.",
    )
    parser.add_argument(
        "--download-alphafold-assets",
        action="store_true",
        help="Download AlphaFold per-accession asset URLs in addition to the prediction JSON.",
    )
    parser.add_argument(
        "--download-mmcif",
        action="store_true",
        help="Download mmCIF files for the selected RCSB best-structure entries.",
    )
    parser.add_argument(
        "--max-structures-per-accession",
        type=int,
        default=1,
        help="How many best-structure PDB IDs to materialize per accession.",
    )
    parser.add_argument(
        "--psicquic-max-results",
        type=int,
        default=5,
        help="Maximum PSICQUIC rows to capture per accession for the raw IntAct slice.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    accessions = _normalize_accessions(_split_csv(args.accessions) or _default_accessions())
    if not accessions:
        raise SystemExit("No accessions were provided and no default frozen cohort was found.")
    sources = tuple(_split_csv(args.sources))
    unsupported = sorted(set(sources) - set(DEFAULT_SOURCES))
    if unsupported:
        raise SystemExit(f"Unsupported sources: {', '.join(unsupported)}")
    summary = run_bootstrap(
        accessions=accessions,
        sources=sources,
        raw_root=args.raw_root,
        allow_insecure_ssl=args.allow_insecure_ssl,
        dry_run=args.dry_run,
        alphafold_assets=args.download_alphafold_assets,
        max_structures_per_accession=max(1, args.max_structures_per_accession),
        download_mmcif=args.download_mmcif,
        psicquic_max_results=max(1, args.psicquic_max_results),
    )
    print(json.dumps(summary, indent=2))
    if _text(summary.get("status")).casefold() == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

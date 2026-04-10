from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED_ROOT = REPO_ROOT / "data" / "raw" / "protein_data_scope_seed"
DEFAULT_POLICY_PATH = REPO_ROOT / "protein_data_scope" / "tier1_validation_policy.json"
DEFAULT_JSON_OUTPUT = REPO_ROOT / "artifacts" / "status" / "protein_data_scope_seed_validation.json"
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "reports" / "protein_data_scope_seed_validation.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _latest_manifest(seed_root: Path) -> Path:
    manifests = sorted(seed_root.glob("download_run_*.json"), key=lambda item: item.name)
    if not manifests:
        raise FileNotFoundError(f"no seed manifests found under {seed_root}")
    return manifests[-1]


def _latest_entries_by_source(seed_root: Path) -> dict[str, dict[str, Any]]:
    manifests = sorted(seed_root.glob("download_run_*.json"), key=lambda item: item.name)
    if not manifests:
        raise FileNotFoundError(f"no seed manifests found under {seed_root}")
    latest: dict[str, dict[str, Any]] = {}
    for manifest_path in manifests:
        payload = _read_json(manifest_path)
        for source in payload.get("sources") or ():
            if not isinstance(source, dict):
                continue
            source_id = str(source.get("id") or "").strip()
            if not source_id:
                continue
            latest[source_id] = dict(source)
            latest[source_id]["_manifest_path"] = str(manifest_path)
    return latest


def _is_gzip(path: Path) -> bool:
    return path.suffix.lower() == ".gz"


def _gzip_integrity(path: Path) -> tuple[bool, str | None]:
    try:
        with gzip.open(path, "rb") as handle:
            handle.read(4096)
    except OSError as exc:
        return False, str(exc)
    return True, None


def _sample_readable(path: Path) -> tuple[bool, str | None]:
    try:
        if _is_gzip(path):
            with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
                sample = handle.read(4096)
        else:
            sample = path.read_text(encoding="utf-8", errors="replace")[:4096]
    except OSError as exc:
        return False, str(exc)
    if not sample.strip():
        return False, "empty sample"
    return True, None


def _iter_text_lines(path: Path):
    if _is_gzip(path):
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                yield line
    else:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                yield line


def _first_meaningful_lines(
    path: Path,
    *,
    limit: int = 3,
    skip_hash_comments: bool = True,
) -> list[str]:
    lines: list[str] = []
    for raw_line in _iter_text_lines(path):
        line = raw_line.strip()
        if not line:
            continue
        if skip_hash_comments and line.startswith("#"):
            continue
        lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def _first_matching_lines(
    path: Path,
    *,
    limit: int,
    skip_hash_comments: bool = True,
) -> list[str]:
    return _first_meaningful_lines(
        path,
        limit=limit,
        skip_hash_comments=skip_hash_comments,
    )


def _json_parseable(path: Path) -> tuple[bool, str | None]:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, str(exc)
    return True, None


def _validate_reactome_core_file(filename: str, path: Path) -> tuple[bool, str | None]:
    lines = _first_meaningful_lines(path, limit=1)
    if not lines:
        return False, "no tabular rows"
    row = lines[0].split("\t")
    if filename == "UniProt2Reactome.txt":
        ok = len(row) >= 6 and bool(row[0]) and row[1].startswith("R-")
        return ok, None if ok else "expected accession and Reactome stable ID columns"
    if filename == "ReactomePathways.txt":
        ok = len(row) >= 3 and row[0].startswith("R-") and bool(row[2])
        return ok, None if ok else "expected pathway stable ID, name, and species columns"
    if filename == "ReactomePathwaysRelation.txt":
        ok = len(row) >= 2 and row[0].startswith("R-") and row[1].startswith("R-")
        return ok, None if ok else "expected parent and child Reactome stable IDs"
    return True, None


def _validate_sifts_core_file(filename: str, path: Path) -> tuple[bool, str | None]:
    expected_headers = {
        "pdb_chain_uniprot.tsv.gz": ["PDB", "CHAIN", "SP_PRIMARY"],
        "pdb_chain_go.tsv.gz": ["PDB", "CHAIN", "SP_PRIMARY", "GO_ID"],
        "pdb_chain_pfam.tsv.gz": ["PDB", "CHAIN", "SP_PRIMARY", "PFAM_ID"],
        "uniprot_pdb.tsv.gz": ["SP_PRIMARY", "PDB"],
    }
    lines = _first_meaningful_lines(path, limit=2)
    if len(lines) < 2:
        return False, "missing header or data row"
    header = lines[0].split("\t")
    row = lines[1].split("\t")
    required_headers = expected_headers.get(filename, [])
    ok = all(column in header for column in required_headers) and len(row) >= len(required_headers)
    return ok, None if ok else "expected SIFTS tabular header and first data row"


def _validate_uniprot_core_file(filename: str, path: Path) -> tuple[bool, str | None]:
    if filename == "uniprot_sprot.dat.gz":
        entry_lines: list[str] = []
        for line in _iter_text_lines(path):
            stripped = line.rstrip("\n")
            if not stripped.strip():
                continue
            entry_lines.append(stripped)
            if stripped == "//" or len(entry_lines) >= 400:
                break
        has_id = any(line.startswith("ID   ") for line in entry_lines)
        has_ac = any(line.startswith("AC   ") for line in entry_lines)
        has_sq = any(line.startswith("SQ   ") for line in entry_lines)
        has_terminator = any(line == "//" for line in entry_lines)
        ok = has_id and has_ac and has_sq and has_terminator
        return ok, None if ok else "expected UniProt DAT entry with ID, AC, SQ, and // terminator"
    if filename == "uniprot_sprot.fasta.gz":
        lines = _first_meaningful_lines(path, limit=2, skip_hash_comments=False)
        ok = (
            len(lines) >= 2
            and (lines[0].startswith(">sp|") or lines[0].startswith(">tr|"))
            and lines[1].isalpha()
        )
        return ok, None if ok else "expected FASTA header and sequence row"
    if filename == "idmapping.dat.gz":
        lines = _first_meaningful_lines(path, limit=1, skip_hash_comments=False)
        if not lines:
            return False, "no idmapping rows"
        row = lines[0].split("\t")
        ok = len(row) >= 3 and all(row[:3])
        return ok, None if ok else "expected accession, mapping type, and mapped identifier columns"
    return True, None


def _validate_source_specific_core_file(
    source_id: str,
    filename: str,
    path: Path,
) -> tuple[bool, str | None]:
    try:
        if source_id == "reactome":
            return _validate_reactome_core_file(filename, path)
        if source_id == "sifts":
            return _validate_sifts_core_file(filename, path)
        if source_id == "uniprot":
            return _validate_uniprot_core_file(filename, path)
    except OSError as exc:
        return False, str(exc)
    return True, None


def _reactome_cross_file_integrity(
    item_by_name: dict[str, dict[str, Any]],
) -> tuple[bool, str | None]:
    pathways_item = item_by_name.get("ReactomePathways.txt")
    relation_item = item_by_name.get("ReactomePathwaysRelation.txt")
    mapping_item = item_by_name.get("UniProt2Reactome.txt")
    if not pathways_item or not relation_item or not mapping_item:
        return False, "missing reactome companion files"
    pathways_path = Path(str(pathways_item.get("path") or "").strip())
    relation_path = Path(str(relation_item.get("path") or "").strip())
    mapping_path = Path(str(mapping_item.get("path") or "").strip())
    pathway_ids = {
        line.split("\t")[0]
        for line in _iter_text_lines(pathways_path)
        if "\t" in line and line.split("\t")[0].startswith("R-")
    }
    relation_parent_ids = [
        line.split("\t")[0]
        for line in _first_matching_lines(relation_path, limit=500)
        if "\t" in line and line.split("\t")[0].startswith("R-")
    ]
    mapping_ids = [
        line.split("\t")[1]
        for line in _first_matching_lines(mapping_path, limit=500)
        if len(line.split("\t")) >= 2 and line.split("\t")[1].startswith("R-")
    ]
    if not pathway_ids or not relation_parent_ids or not mapping_ids:
        return False, "reactome sample ids missing"
    missing_relation_parents = {item for item in relation_parent_ids if item not in pathway_ids}
    if missing_relation_parents:
        return False, "reactome relation parent ids do not resolve in pathways table"
    missing_mapping_ids = {item for item in mapping_ids if item not in pathway_ids}
    if missing_mapping_ids:
        return False, "reactome mapping ids do not resolve in pathways table"
    return True, None


def _sifts_cross_file_integrity(
    item_by_name: dict[str, dict[str, Any]],
) -> tuple[bool, str | None]:
    chain_item = item_by_name.get("pdb_chain_uniprot.tsv.gz")
    uniprot_pdb_item = item_by_name.get("uniprot_pdb.tsv.gz")
    if not chain_item or not uniprot_pdb_item:
        return False, "missing sifts companion files"
    chain_path = Path(str(chain_item.get("path") or "").strip())
    uniprot_pdb_path = Path(str(uniprot_pdb_item.get("path") or "").strip())
    chain_rows = [
        line.split("\t")
        for line in _first_matching_lines(chain_path, limit=200)
        if "\t" in line and not line.startswith("PDB\t")
    ]
    uniprot_rows = [
        line.split("\t")
        for line in _iter_text_lines(uniprot_pdb_path)
        if "\t" in line and not line.startswith("SP_PRIMARY\t")
    ]
    if not chain_rows or not uniprot_rows:
        return False, "sifts sample rows missing"
    accession_to_pdbs = {
        row[0]: {item.strip().lower() for item in row[1].split(";") if item.strip()}
        for row in uniprot_rows
        if len(row) >= 2 and row[0]
    }
    matched_rows = 0
    required_matches = min(10, len(chain_rows))
    for row in chain_rows:
        if len(row) < 3:
            continue
        pdb_id = row[0].strip().lower()
        accession = row[2].strip()
        if accession in accession_to_pdbs and pdb_id in accession_to_pdbs[accession]:
            matched_rows += 1
            if matched_rows >= required_matches:
                return True, None
    return False, "sifts accession-to-pdb join sample failed"


def _uniprot_cross_file_integrity(
    item_by_name: dict[str, dict[str, Any]],
) -> tuple[bool, str | None]:
    dat_item = item_by_name.get("uniprot_sprot.dat.gz")
    fasta_item = item_by_name.get("uniprot_sprot.fasta.gz")
    idmapping_item = item_by_name.get("idmapping.dat.gz")
    if not dat_item or not fasta_item or not idmapping_item:
        return False, "missing uniprot companion files"
    dat_path = Path(str(dat_item.get("path") or "").strip())
    fasta_path = Path(str(fasta_item.get("path") or "").strip())
    idmapping_path = Path(str(idmapping_item.get("path") or "").strip())
    dat_accessions = []
    for line in _first_matching_lines(dat_path, limit=200, skip_hash_comments=False):
        if line.startswith("AC   "):
            accession = line.removeprefix("AC   ").split(";")[0].strip()
            if accession:
                dat_accessions.append(accession)
            if len(dat_accessions) >= 3:
                break
    fasta_accessions = []
    for line in _first_matching_lines(fasta_path, limit=20, skip_hash_comments=False):
        if line.startswith(">"):
            parts = line.split("|")
            if len(parts) >= 2 and parts[1].strip():
                fasta_accessions.append(parts[1].strip())
            if len(fasta_accessions) >= 10:
                break
    idmapping_accessions = {
        line.split("\t")[0].strip()
        for line in _first_matching_lines(idmapping_path, limit=2000, skip_hash_comments=False)
        if "\t" in line and line.split("\t")[0].strip()
    }
    dat_set = set(dat_accessions)
    fasta_set = set(fasta_accessions)
    if not dat_set or not fasta_set or not idmapping_accessions:
        return False, "uniprot sample accessions missing"
    if not (dat_set & fasta_set):
        return False, "uniprot dat/fasta accession sample mismatch"
    if not (dat_set & idmapping_accessions):
        return False, "uniprot dat/idmapping accession sample mismatch"
    return True, None


def _cross_file_integrity(
    source_id: str,
    item_by_name: dict[str, dict[str, Any]],
) -> tuple[bool, str | None]:
    if source_id == "reactome":
        return _reactome_cross_file_integrity(item_by_name)
    if source_id == "sifts":
        return _sifts_cross_file_integrity(item_by_name)
    if source_id == "uniprot":
        return _uniprot_cross_file_integrity(item_by_name)
    return True, None


def _item_map(source_entry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in source_entry.get("items") or ():
        if not isinstance(item, dict):
            continue
        filename = str(item.get("filename") or "").strip()
        if filename:
            result[filename] = item
    return result


def _source_root_from_items(source_entry: dict[str, Any]) -> Path | None:
    for item in source_entry.get("items") or ():
        if not isinstance(item, dict):
            continue
        path_value = str(item.get("path") or "").strip()
        if not path_value:
            continue
        return Path(path_value).parent
    return None


def _check_core_files(
    source_entry: dict[str, Any],
    required_core_files: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    item_by_name = _item_map(source_entry)
    checks: list[dict[str, Any]] = []
    failures: list[str] = []
    for filename in required_core_files:
        item = item_by_name.get(filename)
        if item is None:
            checks.append(
                {"check": "required_core_file_present", "filename": filename, "status": "failed"}
            )
            failures.append("missing_required_core_file")
            continue
        if str(item.get("status") or "").casefold() != "downloaded":
            checks.append(
                {
                    "check": "required_core_file_downloaded",
                    "filename": filename,
                    "status": "failed",
                    "message": item.get("message"),
                }
            )
            failures.append("missing_required_core_file")
            continue
        path_value = str(item.get("path") or "").strip()
        if not path_value:
            checks.append(
                {"check": "required_core_file_path", "filename": filename, "status": "failed"}
            )
            failures.append("missing_required_core_file")
            continue
        path = Path(path_value)
        exists = path.exists()
        size_bytes = int(item.get("size_bytes") or 0)
        status = "passed" if exists and size_bytes > 0 else "failed"
        checks.append(
            {
                "check": "file_exists_non_empty",
                "filename": filename,
                "path": str(path),
                "status": status,
                "size_bytes": size_bytes,
            }
        )
        if status != "passed":
            failures.append("zero_byte_core_file" if exists else "missing_required_core_file")
    return checks, failures


def _validate_source(
    source_id: str,
    source_entry: dict[str, Any],
    policy_entry: dict[str, Any],
) -> dict[str, Any]:
    required_core_files = [str(item) for item in policy_entry.get("required_core_files") or ()]
    checks, failures = _check_core_files(source_entry, required_core_files)
    item_by_name = _item_map(source_entry)
    validated_artifacts: list[dict[str, Any]] = []

    gzip_files = []
    for filename in required_core_files:
        item = item_by_name.get(filename)
        if not item:
            continue
        path_value = str(item.get("path") or "").strip()
        if not path_value:
            continue
        path = Path(path_value)
        if path.exists() and _is_gzip(path):
            gzip_files.append((filename, path))

    for filename, path in gzip_files:
        ok, error = _gzip_integrity(path)
        checks.append(
            {
                "check": "gzip_integrity",
                "filename": filename,
                "path": str(path),
                "status": "passed" if ok else "failed",
                "error": error,
            }
        )
        if not ok:
            failures.append("gzip_validation_failed")

    for filename in required_core_files:
        item = item_by_name.get(filename)
        if not item:
            continue
        path_value = str(item.get("path") or "").strip()
        if not path_value:
            continue
        path = Path(path_value)
        if not path.exists():
            continue
        validated_artifacts.append(
            {
                "filename": filename,
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )
        ok, error = _validate_source_specific_core_file(source_id, filename, path)
        checks.append(
            {
                "check": "source_specific_parser_smoke",
                "filename": filename,
                "path": str(path),
                "status": "passed" if ok else "failed",
                "error": error,
            }
        )
        if not ok:
            failures.append(f"{source_id}_schema_invalid")

    cross_file_blockers = {
        "missing_required_core_file",
        "zero_byte_core_file",
        "gzip_validation_failed",
    }
    if cross_file_blockers & set(failures):
        checks.append(
            {
                "check": "cross_file_referential_integrity",
                "status": "skipped",
                "error": "skipped until required core files pass presence and gzip checks",
            }
        )
    else:
        try:
            cross_file_ok, cross_file_error = _cross_file_integrity(source_id, item_by_name)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            cross_file_ok, cross_file_error = False, str(exc)
        checks.append(
            {
                "check": "cross_file_referential_integrity",
                "status": "passed" if cross_file_ok else "failed",
                "error": cross_file_error,
            }
        )
        if not cross_file_ok:
            failures.append("cross_file_integrity_failed")

    source_root = _source_root_from_items(source_entry)
    if source_root is not None and source_root.exists():
        partial_files = sorted(path.name for path in source_root.glob("*.part"))
        checks.append(
            {
                "check": "partial_download_residue_absent",
                "path": str(source_root),
                "status": "passed" if not partial_files else "failed",
                "partial_files": partial_files,
            }
        )
        if partial_files:
            failures.append("partial_download_residue")

    representative_path: Path | None = None
    for filename in required_core_files:
        item = item_by_name.get(filename)
        if not item:
            continue
        path_value = str(item.get("path") or "").strip()
        if not path_value:
            continue
        candidate = Path(path_value)
        if candidate.exists():
            representative_path = candidate
            break

    if representative_path is not None:
        ok, error = _sample_readable(representative_path)
        checks.append(
            {
                "check": "representative_sample_readable",
                "path": str(representative_path),
                "status": "passed" if ok else "failed",
                "error": error,
            }
        )
        if not ok:
            failures.append("unreadable_sample")

    if "chebi.json" in required_core_files:
        item = item_by_name.get("chebi.json")
        if item and str(item.get("path") or "").strip():
            json_path = Path(str(item["path"]))
            if json_path.exists():
                ok, error = _json_parseable(json_path)
                checks.append(
                    {
                        "check": "json_parse_for_json_variant",
                        "filename": "chebi.json",
                        "path": str(json_path),
                        "status": "passed" if ok else "failed",
                        "error": error,
                    }
                )
                if not ok:
                    failures.append("json_parse_failed")

    manifest_path_value = str(source_entry.get("_manifest_path") or "").strip()
    manifest_path = Path(manifest_path_value) if manifest_path_value else None
    manifest_ok = bool(manifest_path and manifest_path.exists())
    checks.append(
        {
            "check": "release_manifest_written",
            "path": str(manifest_path) if manifest_path else None,
            "status": "passed" if manifest_ok else "failed",
        }
    )
    if not manifest_ok:
        failures.append("release_manifest_missing")
    normalized_failures = sorted({item for item in failures if item})
    return {
        "source_id": source_id,
        "status": "passed" if not normalized_failures else "failed",
        "manifest_path": manifest_path_value or None,
        "required_core_files": required_core_files,
        "validated_artifacts": validated_artifacts,
        "checks": checks,
        "failures": normalized_failures,
    }


def build_seed_validation(
    *,
    seed_root: Path | None = None,
    manifest_path: Path,
    policy_path: Path,
) -> dict[str, Any]:
    policy = _read_json(policy_path)
    if manifest_path == Path("__aggregate__"):
        if seed_root is None:
            raise ValueError("seed_root is required for aggregate validation")
        source_entries = _latest_entries_by_source(seed_root)
        manifest_input = _repo_relative(seed_root)
    else:
        manifest = _read_json(manifest_path)
        source_entries = {}
        for source in manifest.get("sources") or ():
            if not isinstance(source, dict):
                continue
            source_id = str(source.get("id") or "").strip()
            if not source_id:
                continue
            source_entry = dict(source)
            source_entry["_manifest_path"] = str(manifest_path)
            source_entries[source_id] = source_entry
        manifest_input = _repo_relative(manifest_path)
    validations = []
    for source_id, policy_entry in sorted((policy.get("sources") or {}).items()):
        source_entry = source_entries.get(source_id)
        if source_entry is None:
            validations.append(
                {
                    "source_id": source_id,
                    "status": "not_run",
                    "required_core_files": list(policy_entry.get("required_core_files") or ()),
                    "validated_artifacts": [],
                    "checks": [],
                    "failures": ["source_not_present_in_manifest"],
                }
            )
            continue
        validations.append(_validate_source(source_id, source_entry, policy_entry))

    passed_count = sum(1 for item in validations if item["status"] == "passed")
    failed_count = sum(1 for item in validations if item["status"] == "failed")
    not_run_count = sum(1 for item in validations if item["status"] == "not_run")
    if failed_count:
        overall_status = "failed"
    elif not_run_count:
        overall_status = "partial"
    else:
        overall_status = "passed"
    return {
        "schema_id": "proteosphere-protein-data-scope-seed-validation-2026-03-23",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": overall_status,
        "inputs": {
            "manifest_path": manifest_input,
            "policy_path": _repo_relative(policy_path),
        },
        "summary": {
            "source_count": len(validations),
            "passed_count": passed_count,
            "failed_count": failed_count,
            "not_run_count": not_run_count,
        },
        "sources": validations,
    }


def render_seed_validation_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Protein Data Scope Seed Validation",
        "",
        f"- Status: `{payload['status']}`",
        f"- Manifest: `{payload['inputs']['manifest_path']}`",
        f"- Policy: `{payload['inputs']['policy_path']}`",
        f"- Passed: `{payload['summary']['passed_count']}`",
        f"- Failed: `{payload['summary']['failed_count']}`",
        f"- Not run: `{payload['summary']['not_run_count']}`",
        "",
    ]
    for source in payload["sources"]:
        lines.append(f"## {source['source_id']}")
        lines.append("")
        lines.append(f"- Status: `{source['status']}`")
        if source["failures"]:
            lines.append(f"- Failures: `{', '.join(source['failures'])}`")
        else:
            lines.append("- Failures: none")
        lines.append("- Required core files:")
        for filename in source["required_core_files"]:
            lines.append(f"  - `{filename}`")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Protein Data Scope seed runs.")
    parser.add_argument("--seed-root", type=Path, default=DEFAULT_SEED_ROOT)
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    manifest_path = args.manifest or Path("__aggregate__")
    payload = build_seed_validation(
        seed_root=args.seed_root,
        manifest_path=manifest_path,
        policy_path=args.policy,
    )
    _write_json(args.json_output, payload)
    _write_text(args.markdown_output, render_seed_validation_markdown(payload))
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "Protein Data Scope seed validation: "
            f"status={payload['status']} "
            f"passed={payload['summary']['passed_count']} "
            f"failed={payload['summary']['failed_count']} "
            f"not_run={payload['summary']['not_run_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

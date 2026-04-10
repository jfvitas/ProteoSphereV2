from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.pdbbind_expansion_support import (
    build_pdb_paper_dataset_quality_verdict,
    build_pdb_paper_split_acceptance_gate,
    build_pdb_paper_split_assessment,
    build_pdb_paper_split_leakage_matrix,
    build_pdb_paper_split_mutation_audit,
    build_pdb_paper_split_sequence_signature_audit,
    build_pdb_paper_split_structure_state_audit,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGING_POINTER = (
    REPO_ROOT
    / "data"
    / "reports"
    / "expansion_staging"
    / "v2_post_procurement_expanded"
    / "LATEST_PDBBIND_EXPANDED.json"
)


def _normalize_pdb(value: Any) -> str:
    return str(value or "").strip().upper()


def _normalize_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _load_latest_corpus(pointer_path: Path) -> dict[str, Any]:
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    corpus_path = Path(pointer["corpus_path"])
    return json.loads(corpus_path.read_text(encoding="utf-8"))


def _stats(values: list[float]) -> dict[str, Any]:
    vals = sorted(values)
    return {
        "count": len(vals),
        "min": min(vals) if vals else None,
        "max": max(vals) if vals else None,
        "mean": round(statistics.mean(vals), 4) if vals else None,
        "median": round(statistics.median(vals), 4) if vals else None,
        "stdev": round(statistics.pstdev(vals), 4) if len(vals) > 1 else None,
    }


def _make_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _make_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, set):
        return sorted(_make_json_safe(item) for item in value)
    return value


def _bin_key(value: float | None, mean_value: float, stdev_value: float) -> str:
    if value is None:
        return "missing"
    if not stdev_value:
        return "mid"
    z_value = (value - mean_value) / stdev_value
    if z_value < -1.5:
        return "very_low"
    if z_value < -0.5:
        return "low"
    if z_value < 0.5:
        return "mid"
    if z_value < 1.5:
        return "high"
    return "very_high"


def _summarize_rows(rows: list[dict[str, Any]], mean_value: float, stdev_value: float) -> dict[str, Any]:
    values = [row["exp_dG"] for row in rows if row["exp_dG"] is not None]
    return {
        "count": len(rows),
        "exp_dG_stats": _stats(values),
        "source_counts": dict(
            Counter((row.get("source_dataset") or "unknown") for row in rows).most_common()
        ),
        "bin_counts": dict(
            Counter(_bin_key(row["exp_dG"], mean_value, stdev_value) for row in rows).most_common()
        ),
    }


def design_split(
    *,
    train_csv: Path,
    test_csv: Path,
    target_test_fraction: float,
    pointer_path: Path,
    cluster_level: str,
) -> dict[str, Any]:
    train_rows = _load_csv_rows(train_csv)
    test_rows = _load_csv_rows(test_csv)
    corpus = _load_latest_corpus(pointer_path)

    structure_index = {
        str(row.get("payload", {}).get("pdb_id") or "").upper(): row.get("payload", {})
        for row in corpus.get("rows") or []
        if isinstance(row, dict) and row.get("row_family") == "structure"
    }
    protein_index = {
        str(row.get("payload", {}).get("accession") or "").upper(): row.get("payload", {})
        for row in corpus.get("rows") or []
        if isinstance(row, dict) and row.get("row_family") == "protein"
    }

    union_rows: dict[str, dict[str, Any]] = {}
    for split_name, source_rows in (("orig_train", train_rows), ("orig_test", test_rows)):
        for source_row in source_rows:
            pdb_id = _normalize_pdb(source_row.get("PDB"))
            if not pdb_id:
                continue
            row = union_rows.setdefault(
                pdb_id,
                {
                    "pdb_id": pdb_id,
                    "exp_dG": _normalize_float(source_row.get("exp_dG")),
                    "source_dataset": source_row.get("Source Data Set"),
                    "structure_method": source_row.get("Structure Method"),
                    "subgroup": source_row.get("Subgroup"),
                    "orig_splits": set(),
                },
            )
            row["orig_splits"].add(split_name)
            if row["exp_dG"] is None:
                row["exp_dG"] = _normalize_float(source_row.get("exp_dG"))
            if not row["source_dataset"] and source_row.get("Source Data Set"):
                row["source_dataset"] = source_row.get("Source Data Set")
            if not row["structure_method"] and source_row.get("Structure Method"):
                row["structure_method"] = source_row.get("Structure Method")
            if not row["subgroup"] and source_row.get("Subgroup"):
                row["subgroup"] = source_row.get("Subgroup")

    core_rows: list[dict[str, Any]] = []
    excluded_rows: list[dict[str, Any]] = []
    for row in union_rows.values():
        payload = structure_index.get(row["pdb_id"])
        if not payload:
            excluded = dict(row)
            excluded["exclusion_reason"] = "missing_local_structure_mapping"
            excluded_rows.append(excluded)
            continue
        if payload.get("complex_type") != "protein_protein":
            excluded = dict(row)
            excluded["exclusion_reason"] = f"non_pp_complex_type:{payload.get('complex_type')}"
            excluded_rows.append(excluded)
            continue
        accessions = sorted(payload.get("mapped_protein_accessions") or [])
        cluster_key = {
            "uniref100": "uniref100_cluster",
            "uniref90": "uniref90_cluster",
        }[cluster_level]
        family_clusters = sorted(
            {
                protein_index.get(accession, {}).get(cluster_key)
                for accession in accessions
                if protein_index.get(accession, {}).get(cluster_key)
            }
        )
        core_row = dict(row)
        core_row["mapped_protein_accessions"] = accessions
        core_row["family_clusters"] = family_clusters
        core_row["complex_type"] = payload.get("complex_type")
        core_rows.append(core_row)

    dg_values = [row["exp_dG"] for row in core_rows if row["exp_dG"] is not None]
    global_mean = statistics.mean(dg_values)
    global_stdev = statistics.pstdev(dg_values) if len(dg_values) > 1 else 0.0

    # Build conservative graph components using exact accession or family-cluster overlap.
    parent = {row["pdb_id"]: row["pdb_id"] for row in core_rows}
    component_size = {row["pdb_id"]: 1 for row in core_rows}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: str, right: str) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left == root_right:
            return
        if component_size[root_left] < component_size[root_right]:
            root_left, root_right = root_right, root_left
        parent[root_right] = root_left
        component_size[root_left] += component_size[root_right]

    bucket_index: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in core_rows:
        for accession in row["mapped_protein_accessions"]:
            bucket_index[("acc", accession)].append(row["pdb_id"])
        for cluster_id in row["family_clusters"]:
            bucket_index[(cluster_level, cluster_id)].append(row["pdb_id"])
    for ids in bucket_index.values():
        if len(ids) < 2:
            continue
        anchor = ids[0]
        for pdb_id in ids[1:]:
            union(anchor, pdb_id)

    components: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in core_rows:
        components[find(row["pdb_id"])].append(row)

    wrapped_components = []
    for component_rows in components.values():
        source_diversity = len({row.get("source_dataset") or "unknown" for row in component_rows})
        bin_diversity = len(
            {
                _bin_key(row["exp_dG"], global_mean, global_stdev)
                for row in component_rows
            }
        )
        wrapped_components.append(
            {
                "items": sorted(component_rows, key=lambda item: item["pdb_id"]),
                "size": len(component_rows),
                "source_div": source_diversity,
                "bin_div": bin_diversity,
            }
        )

    total_core = len(core_rows)
    target_test_size = round(total_core * target_test_fraction)
    all_source_counts = Counter((row.get("source_dataset") or "unknown") for row in core_rows)
    all_bin_counts = Counter(
        _bin_key(row["exp_dG"], global_mean, global_stdev) for row in core_rows
    )

    selected_components = []
    selected_test_ids: set[str] = set()
    selected_source_counts: Counter[str] = Counter()
    selected_bin_counts: Counter[str] = Counter()
    selected_size = 0
    remaining_components = wrapped_components[:]

    while remaining_components and selected_size < target_test_size:
        best_component = None
        best_score = None
        for component in remaining_components:
            new_size = selected_size + component["size"]
            overshoot = max(0, new_size - target_test_size)
            component_source = Counter(
                (row.get("source_dataset") or "unknown") for row in component["items"]
            )
            component_bins = Counter(
                _bin_key(row["exp_dG"], global_mean, global_stdev) for row in component["items"]
            )
            score = overshoot * 10
            size_fraction = min(1.0, new_size / max(1, total_core))
            for key, value in component_source.items():
                desired = all_source_counts[key] * size_fraction
                after = selected_source_counts[key] + value
                score += abs(after - desired) * 0.8
            for key, value in component_bins.items():
                desired = all_bin_counts[key] * size_fraction
                after = selected_bin_counts[key] + value
                score += abs(after - desired) * 0.6
            score -= component["source_div"] * 0.5
            score -= component["bin_div"] * 0.5
            score += component["size"] * 0.05
            if best_score is None or score < best_score:
                best_score = score
                best_component = component
        assert best_component is not None
        selected_components.append(best_component)
        remaining_components.remove(best_component)
        selected_size += best_component["size"]
        for row in best_component["items"]:
            selected_test_ids.add(row["pdb_id"])
            selected_source_counts[row.get("source_dataset") or "unknown"] += 1
            selected_bin_counts[_bin_key(row["exp_dG"], global_mean, global_stdev)] += 1

    component_sets = [
        frozenset(row["pdb_id"] for row in component["items"]) for component in wrapped_components
    ]
    component_by_member = {
        row["pdb_id"]: component_set
        for component_set in component_sets
        for row in next(
            component["items"]
            for component in wrapped_components
            if frozenset(item["pdb_id"] for item in component["items"]) == component_set
        )
    }

    def split_rows(test_ids: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        test_subset = [row for row in core_rows if row["pdb_id"] in test_ids]
        train_subset = [row for row in core_rows if row["pdb_id"] not in test_ids]
        return train_subset, test_subset

    def objective(test_ids: set[str]) -> float:
        train_subset, test_subset = split_rows(test_ids)
        score = abs(len(test_subset) - target_test_size) * 3
        train_vals = [row["exp_dG"] for row in train_subset if row["exp_dG"] is not None]
        test_vals = [row["exp_dG"] for row in test_subset if row["exp_dG"] is not None]
        if train_vals and test_vals:
            score += abs(statistics.mean(train_vals) - statistics.mean(test_vals)) * 2
            score += abs(statistics.pstdev(train_vals) - statistics.pstdev(test_vals)) * 1.5
        test_source = Counter((row.get("source_dataset") or "unknown") for row in test_subset)
        test_bins = Counter(
            _bin_key(row["exp_dG"], global_mean, global_stdev) for row in test_subset
        )
        for key in all_source_counts:
            target_fraction = all_source_counts[key] / max(1, total_core)
            score += abs((test_source[key] / max(1, len(test_subset))) - target_fraction) * 8
        for key in all_bin_counts:
            target_fraction = all_bin_counts[key] / max(1, total_core)
            score += abs((test_bins[key] / max(1, len(test_subset))) - target_fraction) * 5
        return score

    current_test_ids = set(selected_test_ids)
    best_objective = objective(current_test_ids)
    improved = True
    while improved:
        improved = False
        current_component_sets = {component_by_member[pdb_id] for pdb_id in current_test_ids}
        for outgoing_set in list(current_component_sets):
            base_ids = current_test_ids - set(outgoing_set)
            for incoming_set in component_sets:
                if incoming_set in current_component_sets:
                    continue
                candidate_ids = base_ids | set(incoming_set)
                candidate_score = objective(candidate_ids)
                if candidate_score + 1e-9 < best_objective:
                    current_test_ids = candidate_ids
                    best_objective = candidate_score
                    improved = True
                    break
            if improved:
                break

    robust_test_ids = sorted(current_test_ids)
    robust_train_ids = sorted(
        row["pdb_id"] for row in core_rows if row["pdb_id"] not in current_test_ids
    )

    assessment = build_pdb_paper_split_assessment(
        train_ids=robust_train_ids,
        test_ids=robust_test_ids,
        corpus_payload=corpus,
    )
    leakage = build_pdb_paper_split_leakage_matrix(assessment)
    acceptance = build_pdb_paper_split_acceptance_gate(assessment, leakage)
    sequence_audit = build_pdb_paper_split_sequence_signature_audit(assessment)
    mutation_audit = build_pdb_paper_split_mutation_audit(assessment)
    structure_state = build_pdb_paper_split_structure_state_audit(assessment, corpus)
    verdict = build_pdb_paper_dataset_quality_verdict(
        assessment,
        leakage,
        acceptance,
        sequence_audit,
        mutation_audit,
        structure_state,
    )

    robust_train_rows = [row for row in core_rows if row["pdb_id"] in robust_train_ids]
    robust_test_rows = [row for row in core_rows if row["pdb_id"] in robust_test_ids]

    return {
        "artifact_id": "colleague_dataset_robust_split_candidate",
        "generated_at": datetime.now(UTC).isoformat(),
        "design_principles": [
            "use only locally covered protein-protein complexes for the core benchmark",
            f"split by connected components over shared protein accession or shared {cluster_level} cohort",
            "preserve approximate label and source distribution subject to independence constraints",
            "optimize for zero direct protein leakage and zero exact-sequence overlap when feasible",
            "favor GNN-safe graph separation by keeping connected protein neighborhoods in one split",
        ],
        "core_pool_summary": {
            "count": len(core_rows),
            "component_count": len(wrapped_components),
            "target_test_size": target_test_size,
            "cluster_level": cluster_level,
            "largest_component_sizes": sorted(
                (component["size"] for component in wrapped_components),
                reverse=True,
            )[:20],
        },
        "excluded_from_core_benchmark": [
            {
                **row,
                "orig_splits": sorted(row["orig_splits"]),
            }
            for row in excluded_rows
        ],
        "robust_split": {
            "train_ids": robust_train_ids,
            "test_ids": robust_test_ids,
            "train_summary": _summarize_rows(robust_train_rows, global_mean, global_stdev),
            "test_summary": _summarize_rows(robust_test_rows, global_mean, global_stdev),
        },
        "quality_assessment": {
            "assessment": assessment,
            "leakage_matrix": leakage,
            "acceptance_gate": acceptance,
            "sequence_audit": sequence_audit,
            "mutation_audit": mutation_audit,
            "structure_state_audit": structure_state,
            "quality_verdict": verdict,
        },
    }


def write_outputs(
    *,
    artifact: dict[str, Any],
    train_csv: Path,
    test_csv: Path,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"robust-split-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    train_rows = _load_csv_rows(train_csv)
    test_rows = _load_csv_rows(test_csv)
    union_rows = {}
    for row in train_rows + test_rows:
        pdb_id = _normalize_pdb(row.get("PDB"))
        if pdb_id:
            union_rows[pdb_id] = row

    train_ids = set(artifact["robust_split"]["train_ids"])
    test_ids = set(artifact["robust_split"]["test_ids"])
    robust_train_rows = [union_rows[pdb_id] for pdb_id in artifact["robust_split"]["train_ids"]]
    robust_test_rows = [union_rows[pdb_id] for pdb_id in artifact["robust_split"]["test_ids"]]

    robust_train_csv = run_dir / "robust_train_labels.csv"
    robust_test_csv = run_dir / "robust_test_labels.csv"
    excluded_json = run_dir / "excluded_from_core_benchmark.json"
    artifact_json = run_dir / "robust_split_candidate.json"

    if robust_train_rows:
        with robust_train_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(robust_train_rows[0].keys()))
            writer.writeheader()
            writer.writerows(robust_train_rows)
    if robust_test_rows:
        with robust_test_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(robust_test_rows[0].keys()))
            writer.writeheader()
            writer.writerows(robust_test_rows)

    excluded_json.write_text(
        json.dumps(_make_json_safe(artifact["excluded_from_core_benchmark"]), indent=2) + "\n",
        encoding="utf-8",
    )
    artifact_json.write_text(
        json.dumps(_make_json_safe(artifact), indent=2) + "\n",
        encoding="utf-8",
    )

    latest_pointer = output_dir / "LATEST_ROBUST_SPLIT.json"
    latest_pointer.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "run_dir": str(run_dir),
                "train_csv": str(robust_train_csv),
                "test_csv": str(robust_test_csv),
                "artifact_json": str(artifact_json),
                "excluded_json": str(excluded_json),
                "generated_at": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "run_dir": run_dir,
        "train_csv": robust_train_csv,
        "test_csv": robust_test_csv,
        "artifact_json": artifact_json,
        "excluded_json": excluded_json,
        "latest_pointer": latest_pointer,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Design a robust GNN-safe split.")
    parser.add_argument("--train-csv", type=Path, required=True)
    parser.add_argument("--test-csv", type=Path, required=True)
    parser.add_argument(
        "--target-test-fraction",
        type=float,
        default=0.2,
        help="Desired test fraction inside the core benchmark pool.",
    )
    parser.add_argument(
        "--pointer-path",
        type=Path,
        default=DEFAULT_STAGING_POINTER,
        help="LATEST_PDBBIND_EXPANDED pointer path.",
    )
    parser.add_argument(
        "--cluster-level",
        choices=("uniref100", "uniref90"),
        default="uniref90",
        help="Family-cluster level used to keep nearby sequence neighborhoods in one split.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "data" / "reports" / "robust_split_candidates",
    )
    args = parser.parse_args()

    artifact = design_split(
        train_csv=args.train_csv,
        test_csv=args.test_csv,
        target_test_fraction=args.target_test_fraction,
        pointer_path=args.pointer_path,
        cluster_level=args.cluster_level,
    )
    outputs = write_outputs(
        artifact=artifact,
        train_csv=args.train_csv,
        test_csv=args.test_csv,
        output_dir=args.output_dir,
    )

    summary = {
        "core_pool_count": artifact["core_pool_summary"]["count"],
        "excluded_count": len(artifact["excluded_from_core_benchmark"]),
        "robust_train_count": len(artifact["robust_split"]["train_ids"]),
        "robust_test_count": len(artifact["robust_split"]["test_ids"]),
        "verdict": artifact["quality_assessment"]["quality_verdict"]["summary"],
        "outputs": {key: str(value) for key, value in outputs.items()},
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

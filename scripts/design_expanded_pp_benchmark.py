from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "data" / "reports" / "expanded_pp_benchmark_candidates"
DEFAULT_PREVIEW_PATH = REPO_ROOT / "artifacts" / "status" / "expanded_pp_benchmark_preview.json"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "reports" / "expanded_pp_benchmark_recommendation.md"
THERMO_R_KCAL = 0.00198720425864083
DEFAULT_TEMPERATURE_K = 298.15


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


def _make_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _make_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, set):
        return sorted(_make_json_safe(item) for item in value)
    return value


def _stats(values: list[float]) -> dict[str, Any]:
    vals = sorted(values)
    return {
        "count": len(vals),
        "min": round(min(vals), 4) if vals else None,
        "max": round(max(vals), 4) if vals else None,
        "mean": round(statistics.mean(vals), 4) if vals else None,
        "median": round(statistics.median(vals), 4) if vals else None,
        "stdev": round(statistics.pstdev(vals), 4) if len(vals) > 1 else None,
    }


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


def _derive_exp_dg(value_molar: float, temperature_k: float) -> float:
    return round(THERMO_R_KCAL * temperature_k * math.log(value_molar), 4)


def _year_bucket(year: int | None) -> str:
    if year is None:
        return "unknown"
    return f"{(year // 5) * 5}s"


def _load_original_split_membership(
    train_csv: Path,
    test_csv: Path,
) -> tuple[dict[str, str], int, int]:
    original_membership: dict[str, str] = {}
    train_rows = _load_csv_rows(train_csv)
    test_rows = _load_csv_rows(test_csv)
    for row in train_rows:
        pdb_id = _normalize_pdb(row.get("PDB"))
        if pdb_id:
            original_membership[pdb_id] = "orig_train"
    for row in test_rows:
        pdb_id = _normalize_pdb(row.get("PDB"))
        if pdb_id:
            original_membership[pdb_id] = "orig_test"
    return original_membership, len(train_rows), len(test_rows)


def _build_candidate_rows(
    *,
    corpus_payload: dict[str, Any],
    original_membership: dict[str, str],
    cluster_level: str,
    temperature_k: float,
    allowed_measurement_types: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    structure_index: dict[str, dict[str, Any]] = {}
    protein_index: dict[str, dict[str, Any]] = {}
    measurement_index: dict[str, dict[str, Any]] = {}

    for row in corpus_payload.get("rows") or []:
        if not isinstance(row, dict):
            continue
        row_family = row.get("row_family")
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        if row_family == "structure":
            structure_index[str(payload.get("pdb_id") or "").upper()] = payload
        elif row_family == "protein":
            accession = str(payload.get("accession") or "").upper()
            if accession:
                protein_index[accession] = payload
        elif row_family == "measurement":
            pdb_id = str(payload.get("pdb_id") or "").upper()
            if pdb_id:
                measurement_index[pdb_id] = payload

    cluster_key = {
        "uniref50": "uniref50_cluster",
        "uniref90": "uniref90_cluster",
        "uniref100": "uniref100_cluster",
    }[cluster_level]

    excluded = []
    candidates = []
    for pdb_id, measurement in measurement_index.items():
        structure = structure_index.get(pdb_id)
        if not structure:
            excluded.append({"pdb_id": pdb_id, "reason": "missing_structure_row"})
            continue
        if structure.get("complex_type") != "protein_protein":
            excluded.append(
                {
                    "pdb_id": pdb_id,
                    "reason": f"non_pp_complex_type:{structure.get('complex_type')}",
                }
            )
            continue
        if not structure.get("structure_file_path"):
            excluded.append({"pdb_id": pdb_id, "reason": "missing_local_structure_file"})
            continue
        if measurement.get("measurement_type") not in allowed_measurement_types:
            excluded.append(
                {
                    "pdb_id": pdb_id,
                    "reason": f"measurement_type_filtered:{measurement.get('measurement_type')}",
                }
            )
            continue
        if measurement.get("relation") != "=":
            excluded.append(
                {
                    "pdb_id": pdb_id,
                    "reason": f"non_exact_relation:{measurement.get('relation')}",
                }
            )
            continue
        affinity_value = _normalize_float(measurement.get("value_molar_normalized"))
        if not affinity_value or affinity_value <= 0:
            excluded.append({"pdb_id": pdb_id, "reason": "missing_affinity_value"})
            continue
        accessions = sorted(structure.get("mapped_protein_accessions") or [])
        if len(accessions) < 2:
            excluded.append({"pdb_id": pdb_id, "reason": "insufficient_protein_mapping"})
            continue
        family_clusters = sorted(
            {
                protein_index.get(accession, {}).get(cluster_key)
                for accession in accessions
                if protein_index.get(accession, {}).get(cluster_key)
            }
        )
        candidate = {
            "pdb_id": pdb_id,
            "complex_type": "protein_protein",
            "measurement_type": str(measurement.get("measurement_type") or ""),
            "affinity_value_molar": affinity_value,
            "raw_binding_string": str(measurement.get("raw_binding_string") or ""),
            "exp_dG": _derive_exp_dg(affinity_value, temperature_k),
            "temperature_k": temperature_k,
            "source_dataset": "PDBbind v2020",
            "structure_file_path": str(structure.get("structure_file_path") or ""),
            "mapped_protein_accessions": accessions,
            "mapped_chain_ids": sorted(structure.get("mapped_chain_ids") or []),
            "family_clusters": family_clusters,
            "resolution_angstrom": _normalize_float(structure.get("resolution_angstrom")),
            "release_year": (
                int(structure.get("release_year"))
                if structure.get("release_year") is not None
                else None
            ),
            "original_membership": original_membership.get(pdb_id, "new"),
        }
        candidates.append(candidate)

    candidate_values = [row["exp_dG"] for row in candidates]
    mean_value = statistics.mean(candidate_values)
    stdev_value = statistics.pstdev(candidate_values) if len(candidate_values) > 1 else 0.0
    bin_counts = Counter(_bin_key(row["exp_dG"], mean_value, stdev_value) for row in candidates)
    year_counts = Counter(_year_bucket(row["release_year"]) for row in candidates)
    measurement_counts = Counter(row["measurement_type"] for row in candidates)

    for row in candidates:
        resolution = row["resolution_angstrom"] or 3.5
        row["label_bin"] = _bin_key(row["exp_dG"], mean_value, stdev_value)
        row["selection_utility"] = (
            (1.6 if row["original_membership"] == "new" else 0.2)
            + 1.0 / math.sqrt(bin_counts[row["label_bin"]])
            + 0.35 / math.sqrt(year_counts[_year_bucket(row["release_year"])])
            + (0.45 if row["measurement_type"] == "Ki" else 0.0)
            + max(0.0, (4.0 - resolution)) * 0.12
        )

    universe_summary = {
        "candidate_count": len(candidates),
        "excluded_count": len(excluded),
        "measurement_type_counts": dict(measurement_counts.most_common()),
        "label_bin_counts": dict(bin_counts.most_common()),
        "release_year_bucket_counts": dict(year_counts.most_common()),
        "exp_dG_stats": _stats(candidate_values),
    }
    return candidates, {"excluded": excluded, "summary": universe_summary}


def _build_components(
    rows: list[dict[str, Any]],
    *,
    cluster_level: str,
) -> list[list[dict[str, Any]]]:
    parent = {row["pdb_id"]: row["pdb_id"] for row in rows}
    component_size = {row["pdb_id"]: 1 for row in rows}

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
    for row in rows:
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
    for row in rows:
        components[find(row["pdb_id"])].append(row)
    return [sorted(component, key=lambda item: item["pdb_id"]) for component in components.values()]


def _component_score(component: list[dict[str, Any]]) -> float:
    unique_accessions = {
        accession for row in component for accession in row["mapped_protein_accessions"]
    }
    novelty_count = sum(1 for row in component if row["original_membership"] == "new")
    return (
        sum(row["selection_utility"] for row in component)
        + novelty_count * 0.4
        + len(unique_accessions) * 0.12
    )


def _select_components_exact_size(
    components: list[list[dict[str, Any]]],
    *,
    target_total: int,
) -> list[list[dict[str, Any]]]:
    scored_components = [
        {
            "rows": component,
            "size": len(component),
            "score": _component_score(component),
        }
        for component in components
    ]

    dp: dict[int, tuple[float, list[int]]] = {0: (0.0, [])}
    for index, component in enumerate(scored_components):
        new_dp = dict(dp)
        for total_size, (score, chosen) in dp.items():
            new_total = total_size + component["size"]
            if new_total > target_total:
                continue
            new_score = score + component["score"]
            incumbent = new_dp.get(new_total)
            if incumbent is None or new_score > incumbent[0]:
                new_dp[new_total] = (new_score, chosen + [index])
        dp = new_dp

    if target_total not in dp:
        raise RuntimeError(
            f"Unable to select components to exactly reach total size {target_total}."
        )

    return [scored_components[index]["rows"] for index in dp[target_total][1]]


def _objective_for_test_split(
    *,
    test_ids: set[str],
    selected_rows: list[dict[str, Any]],
    target_test_size: int,
    mean_value: float,
    stdev_value: float,
) -> float:
    test_subset = [row for row in selected_rows if row["pdb_id"] in test_ids]
    train_subset = [row for row in selected_rows if row["pdb_id"] not in test_ids]
    score = abs(len(test_subset) - target_test_size) * 5
    train_vals = [row["exp_dG"] for row in train_subset]
    test_vals = [row["exp_dG"] for row in test_subset]
    if train_vals and test_vals:
        score += abs(statistics.mean(train_vals) - statistics.mean(test_vals)) * 2.5
        score += abs(statistics.pstdev(train_vals) - statistics.pstdev(test_vals)) * 1.5

    all_bins = Counter(_bin_key(row["exp_dG"], mean_value, stdev_value) for row in selected_rows)
    test_bins = Counter(_bin_key(row["exp_dG"], mean_value, stdev_value) for row in test_subset)
    all_measurements = Counter(row["measurement_type"] for row in selected_rows)
    test_measurements = Counter(row["measurement_type"] for row in test_subset)

    for key in all_bins:
        target_fraction = all_bins[key] / max(1, len(selected_rows))
        score += abs((test_bins[key] / max(1, len(test_subset))) - target_fraction) * 7
    for key in all_measurements:
        target_fraction = all_measurements[key] / max(1, len(selected_rows))
        score += abs((test_measurements[key] / max(1, len(test_subset))) - target_fraction) * 6

    test_novel = sum(1 for row in test_subset if row["original_membership"] == "new")
    train_novel = sum(1 for row in train_subset if row["original_membership"] == "new")
    score += (
        abs((test_novel / max(1, len(test_subset))) - (train_novel / max(1, len(train_subset)))) * 4
    )
    return score


def _select_test_components(
    *,
    selected_components: list[list[dict[str, Any]]],
    target_test_size: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected_rows = [row for component in selected_components for row in component]
    mean_value = statistics.mean(row["exp_dG"] for row in selected_rows)
    stdev_value = (
        statistics.pstdev(row["exp_dG"] for row in selected_rows) if len(selected_rows) > 1 else 0.0
    )

    component_sets = [
        frozenset(row["pdb_id"] for row in component) for component in selected_components
    ]
    scored_components = sorted(
        selected_components,
        key=lambda component: (
            len(component),
            abs(statistics.mean(row["exp_dG"] for row in component) - mean_value),
            component[0]["pdb_id"],
        ),
    )

    current_test_ids: set[str] = set()
    for component in scored_components:
        if len(current_test_ids) + len(component) <= target_test_size:
            current_test_ids.update(row["pdb_id"] for row in component)
        if len(current_test_ids) == target_test_size:
            break

    if len(current_test_ids) != target_test_size:
        sizes = [len(component) for component in selected_components]
        possible: dict[int, tuple[int | None, int | None]] = {0: (None, None)}
        for index, size in enumerate(sizes):
            next_possible = dict(possible)
            for total in list(possible):
                new_total = total + size
                if new_total > target_test_size or new_total in next_possible:
                    continue
                next_possible[new_total] = (total, index)
            possible = next_possible
        if target_test_size not in possible:
            raise RuntimeError(
                f"Unable to select test components to exactly reach size {target_test_size}."
            )
        chosen_indices = []
        trace_total = target_test_size
        while trace_total:
            prev_total, component_index = possible[trace_total]
            assert prev_total is not None and component_index is not None
            chosen_indices.append(component_index)
            trace_total = prev_total
        current_test_ids = {
            row["pdb_id"]
            for component_index in chosen_indices
            for row in selected_components[component_index]
        }

    best_objective = _objective_for_test_split(
        test_ids=current_test_ids,
        selected_rows=selected_rows,
        target_test_size=target_test_size,
        mean_value=mean_value,
        stdev_value=stdev_value,
    )

    improved = True
    while improved:
        improved = False
        current_component_sets = {
            component_set for component_set in component_sets if component_set & current_test_ids
        }
        for outgoing_set in list(current_component_sets):
            base_ids = current_test_ids - set(outgoing_set)
            for incoming_set in component_sets:
                if (
                    incoming_set in current_component_sets
                    or len(base_ids) + len(incoming_set) != target_test_size
                ):
                    continue
                candidate_ids = base_ids | set(incoming_set)
                candidate_objective = _objective_for_test_split(
                    test_ids=candidate_ids,
                    selected_rows=selected_rows,
                    target_test_size=target_test_size,
                    mean_value=mean_value,
                    stdev_value=stdev_value,
                )
                if candidate_objective + 1e-9 < best_objective:
                    current_test_ids = candidate_ids
                    best_objective = candidate_objective
                    improved = True
                    break
            if improved:
                break

    test_rows = [row for row in selected_rows if row["pdb_id"] in current_test_ids]
    train_rows = [row for row in selected_rows if row["pdb_id"] not in current_test_ids]
    return train_rows, test_rows


def _predict_test_outliers(
    *,
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    component_size_by_pdb: dict[str, int],
) -> list[dict[str, Any]]:
    train_mean = statistics.mean(row["exp_dG"] for row in train_rows)
    train_stdev = (
        statistics.pstdev(row["exp_dG"] for row in train_rows) if len(train_rows) > 1 else 0.0
    )
    outliers = []
    for row in test_rows:
        resolution = row["resolution_angstrom"] or 3.5
        z_value = abs((row["exp_dG"] - train_mean) / train_stdev) if train_stdev else 0.0
        hardness = (
            z_value
            + (0.9 if row["measurement_type"] == "Ki" else 0.0)
            + max(0.0, resolution - 2.5) * 0.35
            + (0.4 if component_size_by_pdb.get(row["pdb_id"], 1) == 1 else 0.0)
            + (0.25 if row["original_membership"] == "new" else 0.0)
        )
        outliers.append(
            {
                "pdb_id": row["pdb_id"],
                "predicted_hardness_score": round(hardness, 4),
                "exp_dG": row["exp_dG"],
                "measurement_type": row["measurement_type"],
                "resolution_angstrom": row["resolution_angstrom"],
                "component_size": component_size_by_pdb.get(row["pdb_id"], 1),
                "original_membership": row["original_membership"],
            }
        )
    return sorted(outliers, key=lambda item: (-item["predicted_hardness_score"], item["pdb_id"]))[
        :20
    ]


def build_expanded_benchmark(
    *,
    train_csv: Path,
    test_csv: Path,
    pointer_path: Path,
    cluster_level: str,
    max_component_size: int,
    allowed_measurement_types: set[str],
    temperature_k: float,
) -> dict[str, Any]:
    original_membership, original_train_count, original_test_count = (
        _load_original_split_membership(
            train_csv,
            test_csv,
        )
    )
    corpus_payload = _load_latest_corpus(pointer_path)
    candidates, candidate_meta = _build_candidate_rows(
        corpus_payload=corpus_payload,
        original_membership=original_membership,
        cluster_level=cluster_level,
        temperature_k=temperature_k,
        allowed_measurement_types=allowed_measurement_types,
    )

    all_components = _build_components(candidates, cluster_level=cluster_level)
    eligible_components = [
        component for component in all_components if len(component) <= max_component_size
    ]
    excluded_large = [
        {
            "representative_pdb": component[0]["pdb_id"],
            "size": len(component),
            "reason": f"component_size_gt_{max_component_size}",
        }
        for component in all_components
        if len(component) > max_component_size
    ]

    target_total = original_train_count + original_test_count
    selected_components = _select_components_exact_size(
        eligible_components,
        target_total=target_total,
    )
    train_rows, test_rows = _select_test_components(
        selected_components=selected_components,
        target_test_size=original_test_count,
    )

    selected_rows = train_rows + test_rows
    component_size_by_pdb = {
        row["pdb_id"]: len(component) for component in selected_components for row in component
    }
    outlier_predictions = _predict_test_outliers(
        train_rows=train_rows,
        test_rows=test_rows,
        component_size_by_pdb=component_size_by_pdb,
    )

    assessment = build_pdb_paper_split_assessment(
        train_ids=sorted(row["pdb_id"] for row in train_rows),
        test_ids=sorted(row["pdb_id"] for row in test_rows),
        corpus_payload=corpus_payload,
    )
    leakage = build_pdb_paper_split_leakage_matrix(assessment)
    acceptance = build_pdb_paper_split_acceptance_gate(assessment, leakage)
    sequence_audit = build_pdb_paper_split_sequence_signature_audit(assessment)
    mutation_audit = build_pdb_paper_split_mutation_audit(assessment)
    structure_state = build_pdb_paper_split_structure_state_audit(assessment, corpus_payload)
    verdict = build_pdb_paper_dataset_quality_verdict(
        assessment,
        leakage,
        acceptance,
        sequence_audit,
        mutation_audit,
        structure_state,
    )

    selected_original = [row for row in selected_rows if row["original_membership"] != "new"]
    selected_new = [row for row in selected_rows if row["original_membership"] == "new"]
    selected_values = [row["exp_dG"] for row in selected_rows]
    mean_value = statistics.mean(selected_values)
    stdev_value = statistics.pstdev(selected_values) if len(selected_values) > 1 else 0.0

    return {
        "artifact_id": "expanded_pp_benchmark_candidate",
        "generated_at": datetime.now(UTC).isoformat(),
        "design_principles": [
            (
                "expand beyond the original examples but stay inside the "
                "protein-protein affinity scope"
            ),
            "use only exact Kd/Ki labels with local structure files present",
            (
                "split by connected components over shared protein accession "
                f"or shared {cluster_level} cohorts"
            ),
            f"exclude highly entangled components larger than {max_component_size}",
            (
                "keep total dataset size aligned with the original benchmark "
                "for apples-to-apples model comparisons"
            ),
            "optimize for zero direct protein leakage and zero exact-sequence reuse when feasible",
        ],
        "original_reference_counts": {
            "train_count": original_train_count,
            "test_count": original_test_count,
            "total_count": original_train_count + original_test_count,
        },
        "candidate_universe": {
            **candidate_meta["summary"],
            "component_count": len(all_components),
            "eligible_component_count": len(eligible_components),
            "excluded_large_component_count": len(excluded_large),
            "largest_component_sizes": sorted(
                (len(component) for component in all_components), reverse=True
            )[:20],
        },
        "selection_summary": {
            "cluster_level": cluster_level,
            "max_component_size": max_component_size,
            "selected_component_count": len(selected_components),
            "selected_component_size_summary": dict(
                Counter(len(component) for component in selected_components).most_common()
            ),
            "selected_total_count": len(selected_rows),
            "selected_original_overlap_count": len(selected_original),
            "selected_new_example_count": len(selected_new),
            "selected_original_train_overlap_count": sum(
                1 for row in selected_original if row["original_membership"] == "orig_train"
            ),
            "selected_original_test_overlap_count": sum(
                1 for row in selected_original if row["original_membership"] == "orig_test"
            ),
            "selected_measurement_type_counts": dict(
                Counter(row["measurement_type"] for row in selected_rows).most_common()
            ),
            "selected_exp_dG_stats": _stats(selected_values),
        },
        "split_summary": {
            "train_count": len(train_rows),
            "test_count": len(test_rows),
            "train_exp_dG_stats": _stats([row["exp_dG"] for row in train_rows]),
            "test_exp_dG_stats": _stats([row["exp_dG"] for row in test_rows]),
            "train_bin_counts": dict(
                Counter(
                    _bin_key(row["exp_dG"], mean_value, stdev_value) for row in train_rows
                ).most_common()
            ),
            "test_bin_counts": dict(
                Counter(
                    _bin_key(row["exp_dG"], mean_value, stdev_value) for row in test_rows
                ).most_common()
            ),
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
        "predicted_test_outliers": outlier_predictions,
        "selected_train_rows": train_rows,
        "selected_test_rows": test_rows,
        "selected_pdb_ids": sorted(row["pdb_id"] for row in selected_rows),
        "excluded_large_components": excluded_large,
        "excluded_candidate_rows": candidate_meta["excluded"],
    }


def _csv_row_from_selected(selected_row: dict[str, Any], split_name: str) -> dict[str, Any]:
    return {
        "Split": split_name,
        "PDB": selected_row["pdb_id"],
        "exp_dG": selected_row["exp_dG"],
        "Measurement Type": selected_row["measurement_type"],
        "Affinity Value (M)": selected_row["affinity_value_molar"],
        "Raw Affinity String": selected_row["raw_binding_string"],
        "Source Data Set": selected_row["source_dataset"],
        "Complex Type": selected_row["complex_type"],
        "Mapped Protein Accessions": ";".join(selected_row["mapped_protein_accessions"]),
        "Mapped Chain IDs": ";".join(selected_row["mapped_chain_ids"]),
        "Structure File": selected_row["structure_file_path"],
        "Resolution (A)": selected_row["resolution_angstrom"],
        "Release Year": selected_row["release_year"],
        "Original Membership": selected_row["original_membership"],
        "Label Temperature (K)": selected_row["temperature_k"],
        "Label Derivation": "exp_dG = RT ln(K) using exact PDBbind Kd/Ki value_molar_normalized",
    }


def write_outputs(
    *,
    artifact: dict[str, Any],
    output_root: Path,
    preview_path: Path,
    report_path: Path,
) -> dict[str, Path]:
    output_root.mkdir(parents=True, exist_ok=True)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    run_id = f"expanded-pp-benchmark-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    train_csv_path = run_dir / "expanded_train_labels.csv"
    test_csv_path = run_dir / "expanded_test_labels.csv"
    artifact_json_path = run_dir / "expanded_pp_benchmark_candidate.json"
    excluded_large_path = run_dir / "excluded_large_components.json"

    train_rows = [_csv_row_from_selected(row, "train") for row in artifact["selected_train_rows"]]
    test_rows = [_csv_row_from_selected(row, "test") for row in artifact["selected_test_rows"]]
    fieldnames = list(train_rows[0].keys() if train_rows else test_rows[0].keys())

    with train_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(train_rows)
    with test_csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(test_rows)

    artifact_json_path.write_text(
        json.dumps(_make_json_safe(artifact), indent=2) + "\n",
        encoding="utf-8",
    )
    excluded_large_path.write_text(
        json.dumps(_make_json_safe(artifact["excluded_large_components"]), indent=2) + "\n",
        encoding="utf-8",
    )
    preview_path.write_text(
        json.dumps(
            _make_json_safe(
                {
                    "artifact_id": artifact["artifact_id"],
                    "generated_at": artifact["generated_at"],
                    "selection_summary": artifact["selection_summary"],
                    "split_summary": artifact["split_summary"],
                    "quality_assessment_summary": {
                        "assessment": artifact["quality_assessment"]["assessment"]["summary"],
                        "leakage_matrix": artifact["quality_assessment"]["leakage_matrix"][
                            "summary"
                        ],
                        "acceptance_gate": artifact["quality_assessment"]["acceptance_gate"][
                            "summary"
                        ],
                        "sequence_audit": artifact["quality_assessment"]["sequence_audit"][
                            "summary"
                        ],
                        "mutation_audit": artifact["quality_assessment"]["mutation_audit"][
                            "summary"
                        ],
                        "structure_state_audit": artifact["quality_assessment"][
                            "structure_state_audit"
                        ]["summary"],
                        "quality_verdict": artifact["quality_assessment"]["quality_verdict"][
                            "summary"
                        ],
                    },
                    "predicted_test_outliers": artifact["predicted_test_outliers"][:10],
                }
            ),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    latest_pointer = output_root / "LATEST_EXPANDED_PP_BENCHMARK.json"
    latest_pointer.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "run_dir": str(run_dir),
                "train_csv": str(train_csv_path),
                "test_csv": str(test_csv_path),
                "artifact_json": str(artifact_json_path),
                "preview_path": str(preview_path),
                "report_path": str(report_path),
                "generated_at": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    measurement_types = sorted(
        {
            row["measurement_type"]
            for row in artifact["selected_train_rows"] + artifact["selected_test_rows"]
        }
    )
    assessment_summary = artifact["quality_assessment"]["assessment"]["summary"]
    leakage_summary = artifact["quality_assessment"]["leakage_matrix"]["summary"]
    acceptance_summary = artifact["quality_assessment"]["acceptance_gate"]["summary"]
    sequence_summary = artifact["quality_assessment"]["sequence_audit"]["summary"]
    mutation_summary = artifact["quality_assessment"]["mutation_audit"]["summary"]
    structure_summary = artifact["quality_assessment"]["structure_state_audit"]["summary"]
    quality_summary = artifact["quality_assessment"]["quality_verdict"]["summary"]
    shared_partner_line = (
        "- Shared partner overlap count: "
        f"`{assessment_summary.get('shared_partner_overlap_count')}`."
    )
    flagged_pair_line = (
        "- Flagged structure-pair count: "
        f"`{assessment_summary.get('flagged_structure_pair_count')}`."
    )
    summary_line_1 = (
        "- Designed a same-budget expanded benchmark with "
        f"`{artifact['split_summary']['train_count']}` train and "
        f"`{artifact['split_summary']['test_count']}` test examples."
    )
    summary_line_2 = (
        "- Total selected size: "
        f"`{artifact['selection_summary']['selected_total_count']}` examples, "
        "aligned to the original "
        f"`{artifact['original_reference_counts']['total_count']}`-example budget."
    )
    summary_line_3 = (
        "- Added beyond the original set: "
        f"`{artifact['selection_summary']['selected_new_example_count']}` new examples."
    )
    summary_line_4 = (
        "- Retained from the original set: "
        f"`{artifact['selection_summary']['selected_original_overlap_count']}` examples."
    )
    quality_verdict_line = f"- Quality verdict: `{quality_summary.get('overall_decision')}`."
    readiness_line = f"- Training readiness: `{quality_summary.get('readiness')}`."
    acceptance_line = f"- Acceptance gate: `{acceptance_summary.get('decision')}`."
    coverage_line = (
        "- Covered structures: "
        f"`{quality_summary.get('covered_structure_count')}` / "
        f"`{quality_summary.get('total_structure_count')}`."
    )
    universe_line = (
        "- Universe: exact "
        f"`{', '.join(measurement_types)}` protein-protein PDBbind "
        "measurements with local structure files."
    )
    leakage_guard_line = (
        "- Leakage guard: shared accession plus "
        f"`{artifact['selection_summary']['cluster_level']}` component splitting."
    )
    entanglement_line = (
        "- Entanglement control: excluded components larger than "
        f"`{artifact['selection_summary']['max_component_size']}` structures."
    )
    label_line = (
        "- Labels are derived transparently as `exp_dG = RT ln(K)` at "
        "`298.15 K` from local exact PDBbind affinity values."
    )
    selected_component_line = (
        "- Selected component count: "
        f"`{artifact['selection_summary']['selected_component_count']}`."
    )
    excluded_component_line = (
        "- Large entangled components excluded: "
        f"`{artifact['candidate_universe']['excluded_large_component_count']}`."
    )
    measurement_mix_line = (
        f"- Measurement mix: `{artifact['selection_summary']['selected_measurement_type_counts']}`."
    )
    component_size_line = (
        "- Selected component size mix: "
        f"`{artifact['selection_summary']['selected_component_size_summary']}`."
    )
    train_stats_line = f"- Train dG stats: `{artifact['split_summary']['train_exp_dG_stats']}`."
    test_stats_line = f"- Test dG stats: `{artifact['split_summary']['test_exp_dG_stats']}`."
    direct_overlap_line = (
        "- Direct protein overlap count: "
        f"`{assessment_summary.get('direct_protein_overlap_count')}`."
    )
    exact_overlap_line = (
        "- Exact sequence overlap count: "
        f"`{sequence_summary.get('exact_sequence_overlap_count')}`."
    )
    uniref90_line = (
        "- UniRef90 overlap count: "
        f"`{assessment_summary.get('uniref90_cluster_overlap_count')}`."
    )
    uniref50_line = (
        "- UniRef50 overlap count: "
        f"`{assessment_summary.get('uniref50_cluster_overlap_count')}`."
    )
    exact_protein_set_line = (
        "- Exact protein-set reuse count: "
        f"`{structure_summary.get('exact_protein_set_reuse_count', 0)}`."
    )
    shared_context_line = (
        "- Shared-protein different-context count: "
        f"`{structure_summary.get('shared_protein_different_context_count', 0)}`."
    )
    report_lines = [
        "# Expanded Protein-Protein Benchmark Recommendation",
        "",
        "## Summary",
        "",
        summary_line_1,
        summary_line_2,
        summary_line_3,
        summary_line_4,
        quality_verdict_line,
        readiness_line,
        acceptance_line,
        coverage_line,
        "",
        "## Design Choices",
        "",
        universe_line,
        leakage_guard_line,
        entanglement_line,
        label_line,
        "",
        "## Selection Snapshot",
        "",
        selected_component_line,
        excluded_component_line,
        measurement_mix_line,
        component_size_line,
        train_stats_line,
        test_stats_line,
        "",
        "## Leakage and Robustness Readout",
        "",
        direct_overlap_line,
        exact_overlap_line,
        uniref90_line,
        uniref50_line,
        exact_protein_set_line,
        shared_context_line,
        shared_partner_line,
        flagged_pair_line,
        f"- Sequence audit decision: `{sequence_summary.get('sequence_decision')}`.",
        f"- Mutation audit decision: `{mutation_summary.get('decision')}`.",
        f"- Structure-state decision: `{structure_summary.get('decision')}`.",
        f"- Leakage matrix verdict: `{leakage_summary.get('verdict')}`.",
        "",
        "## Predicted Hard Test Examples",
        "",
    ]
    for row in artifact["predicted_test_outliers"][:10]:
        report_lines.append(
            f"- `{row['pdb_id']}`: hardness `{row['predicted_hardness_score']}`, "
            f"`exp_dG={row['exp_dG']}`, `{row['measurement_type']}`, "
            f"`resolution={row['resolution_angstrom']}`, component size `{row['component_size']}`."
        )
    report_lines.extend(
        [
            "",
            "## Files",
            "",
            f"- Train CSV: `{train_csv_path}`",
            f"- Test CSV: `{test_csv_path}`",
            f"- Full artifact JSON: `{artifact_json_path}`",
            f"- Preview JSON: `{preview_path}`",
        ]
    )
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    return {
        "run_dir": run_dir,
        "train_csv": train_csv_path,
        "test_csv": test_csv_path,
        "artifact_json": artifact_json_path,
        "preview_path": preview_path,
        "report_path": report_path,
        "latest_pointer": latest_pointer,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Design an expanded same-budget protein-protein benchmark."
    )
    parser.add_argument("--train-csv", type=Path, required=True)
    parser.add_argument("--test-csv", type=Path, required=True)
    parser.add_argument("--pointer-path", type=Path, default=DEFAULT_STAGING_POINTER)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--preview-path", type=Path, default=DEFAULT_PREVIEW_PATH)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument(
        "--cluster-level", choices=["uniref50", "uniref90", "uniref100"], default="uniref50"
    )
    parser.add_argument("--max-component-size", type=int, default=10)
    parser.add_argument("--temperature-k", type=float, default=DEFAULT_TEMPERATURE_K)
    parser.add_argument(
        "--measurement-types",
        default="Kd,Ki",
        help="Comma-separated allowed measurement types.",
    )
    args = parser.parse_args()

    measurement_types = {
        measurement_type.strip()
        for measurement_type in args.measurement_types.split(",")
        if measurement_type.strip()
    }
    artifact = build_expanded_benchmark(
        train_csv=args.train_csv,
        test_csv=args.test_csv,
        pointer_path=args.pointer_path,
        cluster_level=args.cluster_level,
        max_component_size=args.max_component_size,
        allowed_measurement_types=measurement_types,
        temperature_k=args.temperature_k,
    )
    paths = write_outputs(
        artifact=artifact,
        output_root=args.output_root,
        preview_path=args.preview_path,
        report_path=args.report_path,
    )
    print(json.dumps({key: str(value) for key, value in paths.items()}, indent=2))


if __name__ == "__main__":
    main()

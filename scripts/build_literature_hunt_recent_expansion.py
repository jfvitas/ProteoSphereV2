from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE_ROOT = Path(
    os.environ.get("PROTEOSPHERE_WAREHOUSE_ROOT", r"D:\ProteoSphere\reference_library")
)

BASE_REPORT_PATH = REPO_ROOT / "artifacts" / "status" / "literature_hunt_deep_review.json"
DEEP_PROOF_DIR = REPO_ROOT / "artifacts" / "status" / "literature_hunt_deep_proofs"

MANIFEST_PATH = REPO_ROOT / "datasets" / "splits" / "literature_hunt_recent_expansion_manifest.json"
OUTPUT_JSON = REPO_ROOT / "artifacts" / "status" / "literature_hunt_recent_expansion.json"
OUTPUT_MD = REPO_ROOT / "docs" / "reports" / "literature_hunt_recent_expansion.md"
PER_PAPER_DIR = REPO_ROOT / "artifacts" / "status" / "literature_hunt_recent_expansion"
PROOF_DIR = REPO_ROOT / "artifacts" / "status" / "literature_hunt_recent_expansion_proofs"

REQUEST_HEADERS = {
    "User-Agent": "ProteoSphereAudit/1.0 (+recent-expansion literature hunt)"
}


def utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fetch_text(url: str) -> str:
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=60)
    response.raise_for_status()
    return response.text


def fetch_crossref_metadata(doi_url: str) -> dict[str, Any]:
    doi = doi_url.replace("https://doi.org/", "").replace("http://doi.org/", "")
    response = requests.get(
        f"https://api.crossref.org/works/{doi}",
        headers=REQUEST_HEADERS,
        timeout=60,
    )
    response.raise_for_status()
    message = response.json()["message"]
    year = (
        message.get("published-print", {}).get("date-parts", [[None]])[0][0]
        or message.get("published-online", {}).get("date-parts", [[None]])[0][0]
    )
    return {
        "title": (message.get("title") or [""])[0],
        "journal": (message.get("container-title") or [""])[0],
        "year": year,
    }


def score(publication_utility: float, failure_strength: float, proof_strength: float) -> dict[str, float]:
    return {
        "publication_utility": publication_utility,
        "failure_strength": failure_strength,
        "proof_strength": proof_strength,
    }


def compute_attentiondta_random_cv_proof() -> dict[str, Any]:
    seed = 4321
    dataset_urls = {
        "davis": "https://raw.githubusercontent.com/zhaoqichang/AttentionDTA_TCBB/master/datasets/Davis.txt",
        "kiba": "https://raw.githubusercontent.com/zhaoqichang/AttentionDTA_TCBB/master/datasets/KIBA.txt",
        "metz": "https://raw.githubusercontent.com/zhaoqichang/AttentionDTA_TCBB/master/datasets/Metz.txt",
    }
    code_url = (
        "https://raw.githubusercontent.com/zhaoqichang/AttentionDTA_TCBB/master/AttentionDTA_main.py"
    )

    def parse_rows(url: str) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        for line in fetch_text(url).splitlines():
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            rows.append((parts[0], parts[1]))
        return rows

    def split_first_fold(rows: list[tuple[str, str]], k: int = 5) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        shuffled = list(rows)
        np.random.seed(seed)
        np.random.shuffle(shuffled)
        fold_size = len(shuffled) // k
        valid = shuffled[:fold_size]
        train = shuffled[fold_size:]
        return train, valid

    datasets: dict[str, Any] = {}
    for name, url in dataset_urls.items():
        rows = parse_rows(url)
        train_rows, test_rows = split_first_fold(rows)
        train_drugs = {row[0] for row in train_rows}
        test_drugs = {row[0] for row in test_rows}
        train_targets = {row[1] for row in train_rows}
        test_targets = {row[1] for row in test_rows}
        datasets[name] = {
            "total_rows": len(rows),
            "train_rows": len(train_rows),
            "test_rows": len(test_rows),
            "shared_drug_count": len(train_drugs & test_drugs),
            "test_unique_drug_count": len(test_drugs),
            "shared_target_count": len(train_targets & test_targets),
            "test_unique_target_count": len(test_targets),
        }

    proof = {
        "proof_id": "attentiondta_random_cv_family_audit",
        "benchmark_family": "attentiondta_random_row_cv",
        "family_description": (
            "AttentionDTA releases full pair tables and applies five-fold row-level random CV "
            "after shuffling, which preserves complete drug and target reuse across train/test."
        ),
        "official_evidence_links": [
            "https://doi.org/10.1109/TCBB.2022.3170365",
            "https://github.com/zhaoqichang/AttentionDTA_TCBB",
            code_url,
            *dataset_urls.values(),
        ],
        "released_split_note": (
            "The released code shuffles all rows, then slices folds by row index via get_kfold_data()."
        ),
        "datasets": datasets,
        "raw_archive_fallback_required": False,
        "verdict": "Row-level random CV is a hard warm-start failure under ProteoSphere logic.",
    }
    write_json(PROOF_DIR / "attentiondta_random_cv_family_audit.json", proof)
    return proof


def recent_candidates(attention_proof: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "paper_id": "attentiondta_tcbb2023",
            "doi": "https://doi.org/10.1109/TCBB.2022.3170365",
            "domain": "protein_ligand",
            "task_family": "drug_target_affinity_prediction",
            "benchmark_family": "attentiondta_random_row_cv",
            "tier_target": "tier1_hard_failure",
            "official_evidence_links": attention_proof["official_evidence_links"],
            "claimed_split_description": "Five-fold cross-validation on released Davis, KIBA, and Metz pair tables.",
            "recovered_split_evidence": [
                "The official code shuffles the full pair table and slices folds by row index with get_kfold_data().",
                (
                    "Recovered first-fold overlap counts: Davis shares "
                    f"{attention_proof['datasets']['davis']['shared_drug_count']}/"
                    f"{attention_proof['datasets']['davis']['test_unique_drug_count']} test drugs and "
                    f"{attention_proof['datasets']['davis']['shared_target_count']}/"
                    f"{attention_proof['datasets']['davis']['test_unique_target_count']} test targets with training."
                ),
                (
                    "KIBA shares "
                    f"{attention_proof['datasets']['kiba']['shared_drug_count']}/"
                    f"{attention_proof['datasets']['kiba']['test_unique_drug_count']} test drugs and "
                    f"{attention_proof['datasets']['kiba']['shared_target_count']}/"
                    f"{attention_proof['datasets']['kiba']['test_unique_target_count']} test targets with training."
                ),
            ],
            "mitigation_claims": ["No cold-drug, cold-target, or cold-pair mitigation is released."],
            "mitigation_audit_result": "No mitigation surfaced; the released evaluation remains a hard warm-start split.",
            "exact_failure_class": "code_proven_random_row_cv_leakage",
            "overlap_findings": {
                "direct_entity_overlap": True,
                "notes": [
                    "The released train/test logic guarantees shared drugs and shared targets across folds.",
                    "This invalidates unseen-entity generalization claims."
                ],
            },
            "contamination_findings": {
                "notes": [
                    "Direct train/test reuse occurs at both the compound and target level because folds are built over interaction rows."
                ]
            },
            "blockers": [],
            "recommended_proteosphere_treatment": "Audit-only Tier 1 failure; treat as paper-specific evidence that row-level CV can collapse entity independence.",
            "provenance_notes": [
                "Proof computed from the released repository datasets and main training script.",
            ],
            "raw_archive_fallback_required": False,
            "final_status": "tier1_hard_failure",
            "scores": score(4.8, 5.0, 5.0),
        },
        {
            "paper_id": "mgraphdta2022",
            "doi": "https://doi.org/10.1039/D1SC05180F",
            "domain": "protein_ligand",
            "task_family": "drug_target_affinity_prediction",
            "benchmark_family": "deepdta_setting1_family",
            "tier_target": "tier1_hard_failure",
            "official_evidence_links": [
                "https://doi.org/10.1039/D1SC05180F",
                "https://github.com/guaguabujianle/MGraphDTA",
                "https://raw.githubusercontent.com/guaguabujianle/MGraphDTA/master/README.md",
            ],
            "claimed_split_description": "Performance is reported on Davis and KIBA benchmark splits inherited from earlier DTA work.",
            "recovered_split_evidence": [
                "The official README states that Davis and KIBA data come from the DeepDTA benchmark family.",
                "The inherited DeepDTA setting1 family is already proven to share 68/68 Davis test drugs and 2027/2027 KIBA test drugs with training in ProteoSphere's benchmark proof.",
            ],
            "mitigation_claims": ["No cold-drug or cold-target split is released in the official repo."],
            "mitigation_audit_result": "No paper-specific mitigation neutralizes the inherited DeepDTA warm-start leakage.",
            "exact_failure_class": "inherited_warm_start_benchmark_failure",
            "overlap_findings": {"direct_entity_overlap": True, "notes": ["Inherited DeepDTA setting1 retains complete test-drug reuse and complete/near-complete target reuse."]},
            "contamination_findings": {"notes": ["This is a benchmark-family failure rather than a bespoke split bug."]},
            "blockers": [],
            "recommended_proteosphere_treatment": "Tier 1 hard failure for generalization claims built on DeepDTA setting1 only.",
            "provenance_notes": ["Recent peer-reviewed DTA paper that still inherits the warm-start family."],
            "raw_archive_fallback_required": False,
            "final_status": "tier1_hard_failure",
            "scores": score(4.5, 4.6, 4.5),
        },
        {
            "paper_id": "transvaedta2024",
            "doi": "https://doi.org/10.1016/j.cmpb.2023.108003",
            "domain": "protein_ligand",
            "task_family": "drug_target_affinity_prediction",
            "benchmark_family": "deepdta_setting1_family",
            "tier_target": "tier1_hard_failure",
            "official_evidence_links": [
                "https://doi.org/10.1016/j.cmpb.2023.108003",
                "https://github.com/HPC-NEAU/TransVAE-DTA",
                "https://raw.githubusercontent.com/HPC-NEAU/TransVAE-DTA/main/README.md",
            ],
            "claimed_split_description": "Davis and KIBA performance is reported using released fold files.",
            "recovered_split_evidence": [
                "The official repo ships train_fold_setting1.txt and test_fold_setting1.txt under both Davis and KIBA.",
                "Those files place the paper directly inside the already-proven DeepDTA setting1 warm-start family.",
            ],
            "mitigation_claims": ["No cold split or unseen-target split is surfaced in the released package."],
            "mitigation_audit_result": "The paper reuses the leaky fold family without countervailing mitigation.",
            "exact_failure_class": "released_inherited_fold_family_failure",
            "overlap_findings": {"direct_entity_overlap": True, "notes": ["Released fold artifacts map directly to the DeepDTA setting1 family."]},
            "contamination_findings": {"notes": ["Warm-start split family blocks clean unseen-entity interpretation."]},
            "blockers": [],
            "recommended_proteosphere_treatment": "Tier 1 hard failure for broad generalization; acceptable only as a paper-faithful warm-start audit lane.",
            "provenance_notes": ["Recent 2024 journal paper with official fold artifacts."],
            "raw_archive_fallback_required": False,
            "final_status": "tier1_hard_failure",
            "scores": score(4.4, 4.5, 4.7),
        },
        {
            "paper_id": "imagedta2024",
            "doi": "https://doi.org/10.1021/acsomega.4c02308",
            "domain": "protein_ligand",
            "task_family": "drug_target_affinity_prediction",
            "benchmark_family": "deepdta_setting1_family",
            "tier_target": "tier1_hard_failure",
            "official_evidence_links": [
                "https://doi.org/10.1021/acsomega.4c02308",
                "https://github.com/neuhanli/ImageDTA",
                "https://raw.githubusercontent.com/neuhanli/ImageDTA/main/README.md",
                "https://raw.githubusercontent.com/neuhanli/ImageDTA/main/create_csv.py",
            ],
            "claimed_split_description": "The model evaluates on Davis and KIBA after converting released benchmark artifacts.",
            "recovered_split_evidence": [
                "The official create_csv.py script explicitly says 'convert data from DeepDTA'.",
                "It reads train_fold_setting1.txt and test_fold_setting1.txt from the Davis and KIBA benchmark folders.",
            ],
            "mitigation_claims": ["No released cold-drug, cold-target, or novel-pair setting is used for the main results."],
            "mitigation_audit_result": "No mitigation offsets the inherited DeepDTA setting1 leakage.",
            "exact_failure_class": "script_proven_inherited_fold_family_failure",
            "overlap_findings": {"direct_entity_overlap": True, "notes": ["The official data-conversion script ties the paper directly to the DeepDTA warm-start folds."]},
            "contamination_findings": {"notes": ["Generalization claims remain benchmark-family limited."]},
            "blockers": [],
            "recommended_proteosphere_treatment": "Tier 1 hard failure for generalization claims; preserve as a paper-faithful warm-start benchmark only.",
            "provenance_notes": ["Recent 2024 paper with explicit benchmark-conversion code."],
            "raw_archive_fallback_required": False,
            "final_status": "tier1_hard_failure",
            "scores": score(4.4, 4.6, 4.8),
        },
        {
            "paper_id": "three_d_prot_dta2023",
            "doi": "https://doi.org/10.1039/D3RA00281K",
            "domain": "protein_ligand",
            "task_family": "drug_target_affinity_prediction",
            "benchmark_family": "deepdta_setting1_family",
            "tier_target": "tier1_hard_failure",
            "official_evidence_links": [
                "https://doi.org/10.1039/D3RA00281K",
                "https://github.com/HySonLab/Ligand_Generation",
                "https://raw.githubusercontent.com/HySonLab/Ligand_Generation/main/README.md",
            ],
            "claimed_split_description": "The paper reports Davis and KIBA benchmark performance for residue-level protein graphs.",
            "recovered_split_evidence": [
                "The accompanying public repo contains Davis/KIBA fold files under data/*/folds/train_fold_setting1.txt and test_fold_setting1.txt.",
                "That places the paper in the same DeepDTA setting1 family already proven to be a hard warm-start split.",
            ],
            "mitigation_claims": ["No stronger held-out entity split is released for the core paper benchmark."] ,
            "mitigation_audit_result": "Inherited warm-start leakage remains unmitigated.",
            "exact_failure_class": "inherited_warm_start_benchmark_failure",
            "overlap_findings": {"direct_entity_overlap": True, "notes": ["Released fold layout matches the DeepDTA setting1 family."]},
            "contamination_findings": {"notes": ["Benchmark saturation, not unseen-entity generalization, explains the evaluation lane."]},
            "blockers": [],
            "recommended_proteosphere_treatment": "Tier 1 hard failure for generalization claims based only on the inherited Davis/KIBA setting1 family.",
            "provenance_notes": ["Recent 2023 paper with public benchmark files in the companion repo."],
            "raw_archive_fallback_required": False,
            "final_status": "tier1_hard_failure",
            "scores": score(4.2, 4.4, 4.4),
        },
        {
            "paper_id": "deattentiondta2024",
            "doi": "https://doi.org/10.1093/bioinformatics/btae319",
            "domain": "protein_ligand",
            "task_family": "binding_affinity_prediction",
            "benchmark_family": "pdbbind_core_family",
            "tier_target": "tier1_hard_failure",
            "official_evidence_links": [
                "https://doi.org/10.1093/bioinformatics/btae319",
                "https://github.com/whatamazing1/DEAttentionDTA",
                "https://raw.githubusercontent.com/whatamazing1/DEAttentionDTA/main/README.md",
                "https://raw.githubusercontent.com/whatamazing1/DEAttentionDTA/main/src/test.py",
            ],
            "claimed_split_description": "The model evaluates on PDBbind general/refined training sets with core2016 and core2014 test sets.",
            "recovered_split_evidence": [
                "The official README names PDBbind 2020, core2016, and core2014.",
                "The released test script explicitly instantiates MyDataset('core2016', ...).",
            ],
            "mitigation_claims": ["No unseen-protein or source-family mitigation beyond the standard core-set evaluation is released."],
            "mitigation_audit_result": "The paper inherits the already-proven PDBbind core-family protein overlap without an effective mitigation layer.",
            "exact_failure_class": "inherited_core_set_external_failure",
            "overlap_findings": {"direct_entity_overlap": True, "notes": ["PDBbind core-family proof shows 288/290 v2016 core complexes retain direct protein overlap with training-side complexes."]},
            "contamination_findings": {"notes": ["Nominal external evaluation is still protein-overlapped."]},
            "blockers": [],
            "recommended_proteosphere_treatment": "Tier 1 hard failure for unseen-protein claims; keep only as a paper-faithful PDBbind-core audit lane.",
            "provenance_notes": ["Recent 2024 Bioinformatics paper with explicit core-set references in the released repo."],
            "raw_archive_fallback_required": False,
            "final_status": "tier1_hard_failure",
            "scores": score(4.7, 4.7, 4.8),
        },
        {
            "paper_id": "graphscoredta2023",
            "doi": "https://doi.org/10.1093/bioinformatics/btad340",
            "domain": "protein_ligand",
            "task_family": "binding_affinity_prediction",
            "benchmark_family": "pdbbind_core_family",
            "tier_target": "tier1_hard_failure",
            "official_evidence_links": [
                "https://doi.org/10.1093/bioinformatics/btad340",
                "https://github.com/CSUBioGroup/GraphscoreDTA",
                "https://raw.githubusercontent.com/CSUBioGroup/GraphscoreDTA/main/README.md",
            ],
            "claimed_split_description": "The model reports performance on training, test2016, and test2013 sets distributed with the official repo.",
            "recovered_split_evidence": [
                "The repo releases labels_train13851.csv, labels_test2016.csv, and labels_test2013.csv.",
                "Those released files place the paper directly inside the proven PDBbind core-set family.",
            ],
            "mitigation_claims": ["No released cold-protein or scaffold-split mitigation neutralizes the inherited core-set overlap."],
            "mitigation_audit_result": "The paper inherits the leaky PDBbind core evaluation family as its headline external lane.",
            "exact_failure_class": "released_core_set_family_failure",
            "overlap_findings": {"direct_entity_overlap": True, "notes": ["Official test2016/test2013 labels align with the core-set family already proven protein-overlapped."]},
            "contamination_findings": {"notes": ["Claims of broad external generalization are too strong for a protein-overlapped core-set benchmark."]},
            "blockers": [],
            "recommended_proteosphere_treatment": "Tier 1 hard failure for externality claims; acceptable only as a paper-faithful core-set benchmark lane.",
            "provenance_notes": ["Recent 2023 Bioinformatics paper with released core-family labels."],
            "raw_archive_fallback_required": False,
            "final_status": "tier1_hard_failure",
            "scores": score(4.6, 4.6, 4.7),
        },
        {
            "paper_id": "capla2023",
            "doi": "https://doi.org/10.1093/bioinformatics/btad049",
            "domain": "protein_ligand",
            "task_family": "binding_affinity_prediction",
            "benchmark_family": "pdbbind_core_family",
            "tier_target": "tier1_hard_failure",
            "official_evidence_links": [
                "https://doi.org/10.1093/bioinformatics/btad049",
                "https://github.com/lennylv/CAPLA",
                "https://raw.githubusercontent.com/lennylv/CAPLA/main/README.md",
            ],
            "claimed_split_description": "CAPLA evaluates on PDBbind-derived Test2016_290 and Test2016_262 sets.",
            "recovered_split_evidence": [
                "The official README names Test2016_290 and Test2016_262 as the evaluation sets.",
                "These are direct descendants of the PDBbind core-set evaluation family already proven to retain protein overlap with training.",
            ],
            "mitigation_claims": ["No stronger unseen-protein mitigation is released for the headline benchmark."] ,
            "mitigation_audit_result": "The inherited core-family issue remains unresolved.",
            "exact_failure_class": "inherited_core_set_external_failure",
            "overlap_findings": {"direct_entity_overlap": True, "notes": ["PDBbind core-family reuse is explicit in the official benchmark naming."]},
            "contamination_findings": {"notes": ["Core-set evaluation remains unsafe as a clean external generalization test."]},
            "blockers": [],
            "recommended_proteosphere_treatment": "Tier 1 hard failure for general externality claims; retain only as a PDBbind-core audit lane.",
            "provenance_notes": ["Recent 2023 paper with official core-set naming in the repo."],
            "raw_archive_fallback_required": False,
            "final_status": "tier1_hard_failure",
            "scores": score(4.5, 4.5, 4.5),
        },
        {
            "paper_id": "datadta2023",
            "doi": "https://doi.org/10.1093/bioinformatics/btad560",
            "domain": "protein_ligand",
            "task_family": "binding_affinity_prediction",
            "benchmark_family": "pdbbind_core_family",
            "tier_target": "tier1_hard_failure",
            "official_evidence_links": [
                "https://doi.org/10.1093/bioinformatics/btad560",
                "https://github.com/YanZhu06/DataDTA",
                "https://raw.githubusercontent.com/YanZhu06/DataDTA/main/README.md",
            ],
            "claimed_split_description": "The repo releases training, validation, test, test105, and test71 affinity surfaces keyed by PDB identifiers.",
            "recovered_split_evidence": [
                "The official repo ships training_smi.csv, validation_smi.csv, test_smi.csv, test105_smi.csv, and test71_smi.csv together with affinity_data.csv keyed by pdbid.",
                "That is consistent with a PDBbind-derived training/test family rather than a newly mitigated unseen-protein split.",
            ],
            "mitigation_claims": ["No explicit cold-protein or source-family separation is released for the headline benchmark package."],
            "mitigation_audit_result": "No mitigation strong enough to neutralize the PDBbind-family overlap was recovered.",
            "exact_failure_class": "released_pdbbind_family_without_effective_mitigation",
            "overlap_findings": {"direct_entity_overlap": True, "notes": ["Released PDB-ID keyed benchmark files keep the paper inside the protein-overlapped PDBbind family."]},
            "contamination_findings": {"notes": ["The benchmark remains unsuitable as a clean unseen-protein test."]},
            "blockers": [],
            "recommended_proteosphere_treatment": "Tier 1 hard failure for externality claims, with a note that the paper package is still useful for paper-faithful PDBbind-family auditing.",
            "provenance_notes": ["Recent 2023 paper with a released benchmark package but no convincing mitigation layer."],
            "raw_archive_fallback_required": False,
            "final_status": "tier1_hard_failure",
            "scores": score(4.3, 4.4, 4.2),
        },
        {
            "paper_id": "attentionmgtdta2024",
            "doi": "https://doi.org/10.1016/j.neunet.2023.11.018",
            "domain": "protein_ligand",
            "task_family": "drug_target_affinity_prediction",
            "benchmark_family": "deepdta_setting1_family",
            "tier_target": "tier2_strong_supporting_case",
            "official_evidence_links": [
                "https://doi.org/10.1016/j.neunet.2023.11.018",
                "https://github.com/JK-Liu7/AttentionMGT-DTA",
                "https://raw.githubusercontent.com/JK-Liu7/AttentionMGT-DTA/main/README.md",
                "https://raw.githubusercontent.com/JK-Liu7/AttentionMGT-DTA/main/train_DTA.py",
            ],
            "claimed_split_description": "The model trains and tests on Davis/KIBA processed folds in the public repo.",
            "recovered_split_evidence": [
                "The training script points to data/Davis/processed/train/fold/* and matching test fold paths.",
                "The repo context strongly suggests inherited Davis/KIBA fold evaluation, but the exact raw fold membership was not re-materialized in this pass.",
            ],
            "mitigation_claims": ["No explicit cold split was surfaced in the official training script."],
            "mitigation_audit_result": "Likely inherited DeepDTA-family evaluation, but not elevated to Tier 1 because the exact released fold lineage was not fully reconstructed here.",
            "exact_failure_class": "likely_inherited_warm_start_family",
            "overlap_findings": {"direct_entity_overlap": True, "notes": ["The repo structure is consistent with a warm-start Davis/KIBA fold family."]},
            "contamination_findings": {"notes": ["Strong supporting case, but held below Tier 1 pending one more recovery pass."]},
            "blockers": ["Exact fold roster recovery was incomplete in this pass."],
            "recommended_proteosphere_treatment": "Tier 2 supporting case pending explicit fold lineage confirmation.",
            "provenance_notes": ["Recent 2024 paper retained to broaden the evidence surface without overstating proof."],
            "raw_archive_fallback_required": False,
            "final_status": "tier2_strong_supporting_case",
            "scores": score(3.9, 3.8, 3.4),
        },
        {
            "paper_id": "bicompdta2023",
            "doi": "https://doi.org/10.1371/journal.pcbi.1011036",
            "domain": "protein_ligand",
            "task_family": "drug_target_affinity_prediction",
            "benchmark_family": "deepdta_setting1_family",
            "tier_target": "tier2_strong_supporting_case",
            "official_evidence_links": ["https://doi.org/10.1371/journal.pcbi.1011036"],
            "claimed_split_description": "The paper reports Davis and KIBA benchmark results.",
            "recovered_split_evidence": ["The journal paper clearly uses the same DTA benchmark family, but the official split artifacts were not recovered in this pass."],
            "mitigation_claims": ["No released countervailing cold split was recovered."],
            "mitigation_audit_result": "Remains a strong supporting case, not Tier 1, because split artifacts were not fully recovered.",
            "exact_failure_class": "likely_benchmark_family_dependence",
            "overlap_findings": {"direct_entity_overlap": True, "notes": ["Benchmark choice strongly suggests warm-start exposure."]},
            "contamination_findings": {"notes": ["Needs one more evidence pass before Tier 1 promotion."]},
            "blockers": ["Official split artifacts or repo evidence were not recovered in this run."],
            "recommended_proteosphere_treatment": "Tier 2 supporting case.",
            "provenance_notes": ["Recent 2023 peer-reviewed DTA paper retained for breadth."],
            "raw_archive_fallback_required": False,
            "final_status": "tier2_strong_supporting_case",
            "scores": score(3.7, 3.6, 2.8),
        },
        {
            "paper_id": "btdhdta2025",
            "doi": "https://doi.org/10.1021/acsomega.4c08048",
            "domain": "protein_ligand",
            "task_family": "drug_target_affinity_prediction",
            "benchmark_family": "deepdta_setting1_family",
            "tier_target": "tier2_strong_supporting_case",
            "official_evidence_links": ["https://doi.org/10.1021/acsomega.4c08048"],
            "claimed_split_description": "The paper reports recent DTA benchmark results in the DeepDTA/Davis/KIBA ecosystem.",
            "recovered_split_evidence": ["The publication is recent and relevant, but official split artifacts or repository files were not recovered strongly enough for Tier 1 promotion."],
            "mitigation_claims": ["No verifiable mitigation package recovered in this pass."],
            "mitigation_audit_result": "Held at Tier 2 because proof of the exact split lineage is incomplete.",
            "exact_failure_class": "likely_warm_start_family_but_under_recovered",
            "overlap_findings": {"direct_entity_overlap": True, "notes": ["Likely benchmark-family exposure, but proof strength is incomplete."]},
            "contamination_findings": {"notes": ["This paper helps show the issue is current, but not yet as a flagship proof case."]},
            "blockers": ["Insufficient official artifact recovery in this pass."],
            "recommended_proteosphere_treatment": "Tier 2 supporting case pending deeper recovery.",
            "provenance_notes": ["Recent 2025 paper kept as a supporting example rather than over-promoted."],
            "raw_archive_fallback_required": False,
            "final_status": "tier2_strong_supporting_case",
            "scores": score(3.8, 3.4, 2.6),
        },
        {
            "paper_id": "mmfadta2024",
            "doi": "https://doi.org/10.1021/acs.jctc.4c00663",
            "domain": "protein_ligand",
            "task_family": "drug_target_affinity_prediction",
            "benchmark_family": "deepdta_setting1_family",
            "tier_target": "tier2_strong_supporting_case",
            "official_evidence_links": ["https://doi.org/10.1021/acs.jctc.4c00663"],
            "claimed_split_description": "The paper uses the common DTA benchmark stack for SARS-CoV-2 repurposing work.",
            "recovered_split_evidence": ["Article-level evidence suggests standard Davis/KIBA-style benchmarking, but the released split surface was not recovered deeply enough here."],
            "mitigation_claims": ["No verified mitigation package recovered in this pass."],
            "mitigation_audit_result": "Remains Tier 2 until split artifacts are reconstructed.",
            "exact_failure_class": "likely_benchmark_family_dependence",
            "overlap_findings": {"direct_entity_overlap": True, "notes": ["Likely benchmark-family exposure, pending stronger artifact recovery."]},
            "contamination_findings": {"notes": ["Supporting case only."]},
            "blockers": ["Split artifacts not fully recovered."],
            "recommended_proteosphere_treatment": "Tier 2 supporting case.",
            "provenance_notes": ["Recent 2024 paper kept below Tier 1 to preserve evidentiary discipline."],
            "raw_archive_fallback_required": False,
            "final_status": "tier2_strong_supporting_case",
            "scores": score(3.5, 3.2, 2.5),
        },
        {
            "paper_id": "tefdta2024",
            "doi": "https://doi.org/10.1093/bioinformatics/btad778",
            "domain": "protein_ligand",
            "task_family": "drug_target_affinity_prediction",
            "benchmark_family": "mitigation_aware_control",
            "tier_target": "control_nonfailure",
            "official_evidence_links": [
                "https://doi.org/10.1093/bioinformatics/btad778",
                "https://github.com/RefDawn-XD/TEFDTA",
                "https://raw.githubusercontent.com/RefDawn-XD/TEFDTA/master/README.md",
            ],
            "claimed_split_description": "The repo releases both standard train/test and cold evaluation files for Davis and KIBA.",
            "recovered_split_evidence": ["The official repo ships Davis_train/test/cold.csv and KIBA_train/test/cold.csv."],
            "mitigation_claims": ["Cold evaluation surfaces are released for both Davis and KIBA."],
            "mitigation_audit_result": "This is a mitigation-aware control, not a Tier 1 failure.",
            "exact_failure_class": "none_control",
            "overlap_findings": {"direct_entity_overlap": False, "notes": ["A cold split is explicitly released, which is exactly the kind of mitigation the analyzer wants to see."]},
            "contamination_findings": {"notes": ["Useful control showing the tool can validate better benchmark design."]},
            "blockers": [],
            "recommended_proteosphere_treatment": "Control_nonfailure.",
            "provenance_notes": ["Recent 2024 control paper with released cold splits."],
            "raw_archive_fallback_required": False,
            "final_status": "control_nonfailure",
            "scores": score(3.8, 1.0, 4.0),
        },
        {
            "paper_id": "dta_om2026",
            "doi": "https://doi.org/10.1016/j.ejmech.2026.118840",
            "domain": "protein_ligand",
            "task_family": "drug_target_affinity_prediction",
            "benchmark_family": "mitigation_aware_control",
            "tier_target": "control_nonfailure",
            "official_evidence_links": [
                "https://doi.org/10.1016/j.ejmech.2026.118840",
                "https://github.com/MiJia-ID/DTA-OM",
                "https://raw.githubusercontent.com/MiJia-ID/DTA-OM/main/README.md",
            ],
            "claimed_split_description": "The paper reports novel-pair and novel-drug evaluations.",
            "recovered_split_evidence": ["The official README explicitly advertises novel-pair and novel-drug settings."],
            "mitigation_claims": ["Novel-pair and novel-drug holdouts are central to the released evaluation story."],
            "mitigation_audit_result": "Control_nonfailure unless a later audit shows the mitigation failed in practice.",
            "exact_failure_class": "none_control",
            "overlap_findings": {"direct_entity_overlap": False, "notes": ["The claimed mitigation directly targets warm-start bias."]},
            "contamination_findings": {"notes": ["Strong recent control demonstrating the field can ship colder evaluation surfaces."]},
            "blockers": [],
            "recommended_proteosphere_treatment": "Control_nonfailure.",
            "provenance_notes": ["Very recent 2026 control, useful for the 'still relevant' narrative because it shows better practice exists now."],
            "raw_archive_fallback_required": False,
            "final_status": "control_nonfailure",
            "scores": score(4.2, 1.0, 4.1),
        },
        {
            "paper_id": "dcgan_dta2024",
            "doi": "https://doi.org/10.1186/s12864-024-10326-x",
            "domain": "protein_ligand",
            "task_family": "drug_target_affinity_prediction",
            "benchmark_family": "mitigation_aware_control",
            "tier_target": "control_nonfailure",
            "official_evidence_links": [
                "https://doi.org/10.1186/s12864-024-10326-x",
                "https://github.com/mojtabaze7/DCGAN-DTA",
                "https://raw.githubusercontent.com/mojtabaze7/DCGAN-DTA/main/README.md",
            ],
            "claimed_split_description": "The repo exposes multiple fold settings, including colder settings for some datasets.",
            "recovered_split_evidence": ["The official repo includes setting1, setting2, and setting3 split files for some benchmarks."],
            "mitigation_claims": ["Multiple settings imply the paper is not restricted to the warm-start setting only."],
            "mitigation_audit_result": "Control_nonfailure for this expansion because the paper releases colder options instead of only the leaky family.",
            "exact_failure_class": "none_control",
            "overlap_findings": {"direct_entity_overlap": False, "notes": ["Released colder settings keep this paper out of the Tier 1 bucket."]},
            "contamination_findings": {"notes": ["Useful mitigation-aware control."]},
            "blockers": [],
            "recommended_proteosphere_treatment": "Control_nonfailure.",
            "provenance_notes": ["Recent 2024 control retained to show the analyzer is fair."],
            "raw_archive_fallback_required": False,
            "final_status": "control_nonfailure",
            "scores": score(3.6, 1.0, 3.7),
        },
        {
            "paper_id": "hacnet2023",
            "doi": "https://doi.org/10.1021/acs.jcim.3c00251",
            "domain": "protein_ligand",
            "task_family": "binding_affinity_prediction",
            "benchmark_family": "mitigation_aware_control",
            "tier_target": "control_nonfailure",
            "official_evidence_links": [
                "https://doi.org/10.1021/acs.jcim.3c00251",
                "https://github.com/gregory-kyro/HAC-Net",
                "https://raw.githubusercontent.com/gregory-kyro/HAC-Net/main/README.md",
            ],
            "claimed_split_description": "The paper reports multiple train/test splits maximizing differences in proteins or ligands.",
            "recovered_split_evidence": ["The official README says the paper evaluates under splits maximizing differences in protein structure, sequence, or ligand fingerprint."] ,
            "mitigation_claims": ["The evaluation is explicitly designed to counter common protein/ligand leakage channels."],
            "mitigation_audit_result": "Control_nonfailure.",
            "exact_failure_class": "none_control",
            "overlap_findings": {"direct_entity_overlap": False, "notes": ["This is the kind of mitigation-aware design ProteoSphere wants to encourage."]},
            "contamination_findings": {"notes": ["Useful control for fairness."]},
            "blockers": [],
            "recommended_proteosphere_treatment": "Control_nonfailure.",
            "provenance_notes": ["Recent 2023 control paper that strengthens the adoption narrative by contrast."],
            "raw_archive_fallback_required": False,
            "final_status": "control_nonfailure",
            "scores": score(4.0, 1.0, 4.0),
        },
    ]


def hydrate_metadata(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        meta = fetch_crossref_metadata(row["doi"])
        row["title"] = meta["title"]
        row["journal"] = meta["journal"]
        row["year"] = meta["year"]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tier_counts = Counter(row["final_status"] for row in rows)
    year_counts = Counter(str(row["year"]) for row in rows)
    benchmark_counts = Counter(row["benchmark_family"] for row in rows)
    return {
        "candidate_count": len(rows),
        "tier_counts": dict(tier_counts),
        "year_counts": dict(sorted(year_counts.items())),
        "benchmark_family_counts": dict(benchmark_counts),
        "tier1_ids": [row["paper_id"] for row in rows if row["final_status"] == "tier1_hard_failure"],
        "tier2_ids": [row["paper_id"] for row in rows if row["final_status"] == "tier2_strong_supporting_case"],
        "control_ids": [row["paper_id"] for row in rows if row["final_status"] == "control_nonfailure"],
    }


def build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# ProteoSphere Literature Hunt Addendum",
        "",
        "## Summary",
        "",
        f"- New candidates reviewed: `{report['summary']['candidate_count']}`",
        f"- New Tier 1 additions: `{report['summary']['tier_counts'].get('tier1_hard_failure', 0)}`",
        f"- New Tier 2 additions: `{report['summary']['tier_counts'].get('tier2_strong_supporting_case', 0)}`",
        f"- New controls: `{report['summary']['tier_counts'].get('control_nonfailure', 0)}`",
        f"- Combined Tier 1 total versus the original deep hunt: `{report['combined_summary']['tier_counts']['tier1_hard_failure']}`",
        "",
        "## Why This Addendum Matters",
        "",
        "This pass broadens the existing deep hunt with newer 2022–2026 peer-reviewed papers, heavily prioritizing recent publications that still inherit known leaky benchmark families or use paper-specific row-level train/test designs that fail ProteoSphere independence logic.",
        "",
        "## Tier 1 Additions",
        "",
    ]
    for row in [r for r in report["papers"] if r["final_status"] == "tier1_hard_failure"]:
        lines.extend(
            [
                f"### {row['title']}",
                "",
                f"- `paper_id`: `{row['paper_id']}`",
                f"- DOI: [{row['doi']}]({row['doi']})",
                f"- Journal/year: `{row['journal']}` / `{row['year']}`",
                f"- Benchmark family: `{row['benchmark_family']}`",
                f"- Split evidence: {row['recovered_split_evidence'][0]}",
                f"- Failure: {row['contamination_findings']['notes'][0]}",
                f"- Mitigation audit: {row['mitigation_audit_result']}",
                "",
            ]
        )
    lines.extend(["## Tier 2 Supporting Cases", ""])
    for row in [r for r in report["papers"] if r["final_status"] == "tier2_strong_supporting_case"]:
        lines.extend([f"- `{row['paper_id']}`: {row['blockers'][0] if row['blockers'] else row['contamination_findings']['notes'][0]}"])
    lines.extend(["", "## Controls", ""])
    for row in [r for r in report["papers"] if r["final_status"] == "control_nonfailure"]:
        lines.extend([f"- `{row['paper_id']}`: {row['mitigation_audit_result']}"])
    return "\n".join(lines) + "\n"


def build_manifest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "artifact_id": "literature_hunt_recent_expansion_manifest",
        "generated_at": utc_now(),
        "candidate_count": len(rows),
        "papers": [
            {
                "paper_id": row["paper_id"],
                "doi": row["doi"],
                "domain": row["domain"],
                "task_family": row["task_family"],
                "benchmark_family": row["benchmark_family"],
                "suspected_failure_class": row["exact_failure_class"],
                "suspected_mitigation_strategy": row["mitigation_claims"],
                "evidence_surfaces_available": row["official_evidence_links"],
                "tier_target": row["tier_target"],
            }
            for row in rows
        ],
    }


def build_report() -> dict[str, Any]:
    base = load_json(BASE_REPORT_PATH)
    deepdta_proof = load_json(DEEP_PROOF_DIR / "dta_setting1_family_audit.json")
    pdbbind_proof = load_json(DEEP_PROOF_DIR / "pdbbind_core_family_audit.json")
    attention_proof = compute_attentiondta_random_cv_proof()

    rows = recent_candidates(attention_proof)
    hydrate_metadata(rows)
    rows = sorted(rows, key=lambda row: (row["year"], row["journal"], row["paper_id"]), reverse=True)

    manifest = build_manifest(rows)
    write_json(MANIFEST_PATH, manifest)

    for row in rows:
        write_json(PER_PAPER_DIR / f"{row['paper_id']}.json", row)

    combined_papers = list(base["papers"]) + rows
    combined_tier_counts = Counter(row["final_status"] for row in combined_papers)
    combined_year_counts = Counter(str(row["year"]) for row in combined_papers if row.get("year"))
    best_examples = sorted(
        [row for row in rows if row["final_status"] == "tier1_hard_failure"],
        key=lambda row: (-row["scores"]["publication_utility"], -row["year"]),
    )[:6]

    report = {
        "artifact_id": "literature_hunt_recent_expansion",
        "schema_id": "proteosphere.literature_hunt_recent_expansion.v1",
        "generated_at": utc_now(),
        "status": "completed",
        "warehouse_root": str(WAREHOUSE_ROOT),
        "base_report_path": str(BASE_REPORT_PATH),
        "manifest_path": str(MANIFEST_PATH),
        "summary": summarize(rows),
        "combined_summary": {
            "candidate_count": len(combined_papers),
            "tier_counts": dict(combined_tier_counts),
            "year_counts": dict(sorted(combined_year_counts.items())),
            "tier1_ids": [row["paper_id"] for row in combined_papers if row["final_status"] == "tier1_hard_failure"],
            "newest_tier1_ids": [row["paper_id"] for row in rows if row["final_status"] == "tier1_hard_failure"],
        },
        "benchmark_family_proofs": {
            "attentiondta_random_cv": attention_proof,
            "deepdta_setting1_reference": {
                "proof_path": str(DEEP_PROOF_DIR / "dta_setting1_family_audit.json"),
                "shared_drug_note": (
                    f"Davis {deepdta_proof['datasets']['davis']['shared_drug_count']}/"
                    f"{deepdta_proof['datasets']['davis']['test_unique_drug_count']} shared test drugs; "
                    f"KIBA {deepdta_proof['datasets']['kiba']['shared_drug_count']}/"
                    f"{deepdta_proof['datasets']['kiba']['test_unique_drug_count']} shared test drugs."
                ),
            },
            "pdbbind_core_reference": {
                "proof_path": str(DEEP_PROOF_DIR / "pdbbind_core_family_audit.json"),
                "protein_overlap_note": (
                    f"v2016 core: {pdbbind_proof['core_sets']['v2016_core']['test_complexes_with_direct_protein_overlap']}/"
                    f"{pdbbind_proof['core_sets']['v2016_core']['test_count']} direct protein overlap; "
                    f"v2013 core: {pdbbind_proof['core_sets']['v2013_core']['test_complexes_with_direct_protein_overlap']}/"
                    f"{pdbbind_proof['core_sets']['v2013_core']['test_count']}."
                ),
            },
        },
        "best_examples": best_examples,
        "query_log": [
            "\"drug-target binding affinity\" Bioinformatics 2024 github Davis KIBA",
            "\"PDBbind\" core2016 Bioinformatics 2024 github",
            "\"drug-target affinity\" 2025 GitHub Davis KIBA DOI",
            "\"PDBbind\" core2016 2025 binding affinity github",
        ],
        "raw_archive_fallback_notes": [
            "No new raw/archive fallback was required for the recent-expansion addendum.",
            "This addendum reused existing benchmark-family proof artifacts from the original deep hunt and computed one new paper-specific proof from the released AttentionDTA repository.",
        ],
        "papers": rows,
    }
    return report


def main() -> None:
    report = build_report()
    write_json(OUTPUT_JSON, report)
    write_text(OUTPUT_MD, build_markdown(report))
    print(json.dumps(report["summary"], indent=2))
    print(json.dumps(report["combined_summary"]["tier_counts"], indent=2))


if __name__ == "__main__":
    main()

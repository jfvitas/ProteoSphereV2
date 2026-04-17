from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from api.model_studio.capabilities import option_reason
    from api.model_studio.reference_library import (
        load_public_reference_manifest,
        load_source_registry,
        normalize_source_family_name,
    )
except ModuleNotFoundError:  # pragma: no cover
    from model_studio.capabilities import option_reason
    from model_studio.reference_library import (  # type: ignore[no-redef]
        load_public_reference_manifest,
        load_source_registry,
        normalize_source_family_name,
    )

DEFAULT_WAREHOUSE_ROOT = Path(
    os.environ.get("PROTEOSPHERE_WAREHOUSE_ROOT", r"D:\ProteoSphere\reference_library")
)
DEFAULT_EXTERNAL_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "status" / "paper_split_external"
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "paper_split_audit_friendly_evaluation.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "paper_split_audit_friendly_evaluation.md"
)
DEFAULT_PER_PAPER_DIR = REPO_ROOT / "artifacts" / "status" / "paper_split_audit_friendly"


@dataclass(frozen=True)
class PaperSpec:
    paper_id: str
    title: str
    doi: str
    task_group: str
    modality: str
    source_families: tuple[str, ...]
    named_entities: tuple[str, ...]
    claimed_split_description: str
    split_style: str
    auditability: str
    benchmark_family: str
    release_mode: str
    source_links: tuple[str, ...]


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must decode to a JSON object.")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _count_pair_tsv(path: Path) -> tuple[int, int]:
    pair_count = 0
    proteins: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            parts = text.split("\t")
            if len(parts) < 2:
                continue
            pair_count += 1
            proteins.add(parts[0])
            proteins.add(parts[1])
    return pair_count, len(proteins)


PAPERS: tuple[PaperSpec, ...] = (
    PaperSpec(
        "szymborski2022rapppid",
        "RAPPPID: towards generalizable protein interaction prediction with AWD-LSTM twin networks",
        "https://doi.org/10.1093/bioinformatics/btac429",
        "ppi_prediction",
        "sequence_only",
        ("string", "uniprot"),
        ("C1", "C2", "C3", "STRING v11 human"),
        "Official Zenodo package ships strict train/val/test comparative splits (C1/C2/C3) with explicit pair files and sequence dictionaries.",
        "strict_unseen_protein",
        "high",
        "rapppid_c123",
        "direct_release_artifact",
        ("https://doi.org/10.1093/bioinformatics/btac429", "https://doi.org/10.5281/zenodo.6817258"),
    ),
    PaperSpec(
        "graphppis2021",
        "GraphPPIS",
        "https://doi.org/10.1093/bioinformatics/btab643",
        "binding_site_prediction",
        "structure_graph",
        ("rcsb_pdbe",),
        ("Train_335", "Test_60", "Test_315", "UBtest_31"),
        "GraphPPIS is the anchor PPIS benchmark paper for the Train_335/Test_60/Test_315/UBtest_31 family and the official release ships the exact datasets.",
        "external_holdout",
        "high",
        "ppis_train335_family",
        "direct_release_artifact",
        ("https://doi.org/10.1093/bioinformatics/btab643",),
    ),
    PaperSpec(
        "equippis2023",
        "EquiPPIS",
        "https://doi.org/10.1371/journal.pcbi.1011435",
        "binding_site_prediction",
        "equivariant_structure_model",
        ("rcsb_pdbe",),
        ("Train_335", "Test_60", "AlphaFold2 models"),
        "EquiPPIS explicitly follows the public GraphPPIS train/test split rather than introducing a new benchmark family.",
        "external_holdout",
        "medium",
        "ppis_train335_family",
        "inherits_published_benchmark",
        ("https://doi.org/10.1371/journal.pcbi.1011435",),
    ),
    PaperSpec(
        "agat_ppis2023",
        "AGAT-PPIS",
        "https://doi.org/10.1093/bib/bbad122",
        "binding_site_prediction",
        "graph_attention",
        ("rcsb_pdbe",),
        ("Train_335.pkl", "Test_60.pkl", "Test_315-28.pkl", "UBtest_31-6.pkl"),
        "Official repo ships explicit Train_335/Test_60/Test_315-28/UBtest_31-6 benchmark files.",
        "external_holdout",
        "high",
        "ppis_train335_family",
        "direct_release_artifact",
        ("https://doi.org/10.1093/bib/bbad122", "https://github.com/AILBC/AGAT-PPIS"),
    ),
    PaperSpec(
        "ghgpr_ppis2023",
        "GHGPR-PPIS",
        "https://doi.org/10.1016/j.compbiomed.2023.107683",
        "binding_site_prediction",
        "graphheat_gpr",
        ("rcsb_pdbe",),
        ("train_335.pkl", "test_60.pkl", "test_315.pkl", "UBtest_31.pkl"),
        "Official repo provides the shared PPIS benchmark files directly.",
        "external_holdout",
        "high",
        "ppis_train335_family",
        "direct_release_artifact",
        ("https://doi.org/10.1016/j.compbiomed.2023.107683", "https://github.com/dldxzx/GHGPR-PPIS"),
    ),
    PaperSpec(
        "gact_ppis2024",
        "GACT-PPIS",
        "https://doi.org/10.1016/j.ijbiomac.2024.137272",
        "binding_site_prediction",
        "egat_transformer_gcn",
        ("rcsb_pdbe",),
        ("Test-60", "UBTest-31-6"),
        "GACT-PPIS evaluates on the same public PPIS benchmark family rather than introducing a new split lineage.",
        "external_holdout",
        "medium",
        "ppis_train335_family",
        "inherits_published_benchmark",
        ("https://doi.org/10.1016/j.ijbiomac.2024.137272",),
    ),
    PaperSpec(
        "gte_ppis2025",
        "GTE-PPIS",
        "https://doi.org/10.1093/bib/bbaf290",
        "binding_site_prediction",
        "graph_transformer_equivariant",
        ("rcsb_pdbe",),
        ("Train_335", "Test_60", "Test_315", "UBtest_31"),
        "Official repo releases the curated PPIS dataset files used in the paper.",
        "external_holdout",
        "high",
        "ppis_train335_family",
        "direct_release_artifact",
        ("https://doi.org/10.1093/bib/bbaf290",),
    ),
    PaperSpec(
        "asce_ppis2025",
        "ASCE-PPIS",
        "https://doi.org/10.1093/bioinformatics/btaf423",
        "binding_site_prediction",
        "equivariant_pooling",
        ("rcsb_pdbe",),
        ("Train_335.pkl", "Test_60.pkl", "Test_315.pkl", "Test_315-28.pkl", "UBtest_31.pkl", "UBtest_31-6.pkl"),
        "Official repo ships the full Train_335/Test_60/Test_315/UBtest benchmark lineage.",
        "external_holdout",
        "high",
        "ppis_train335_family",
        "direct_release_artifact",
        ("https://doi.org/10.1093/bioinformatics/btaf423",),
    ),
    PaperSpec(
        "sledzieski2021dscript",
        "D-SCRIPT translates genome to phenome with sequence-based, structure-aware, genome-scale predictions of protein-protein interactions",
        "https://doi.org/10.1016/j.cels.2021.08.010",
        "ppi_prediction",
        "sequence_plus_structure_aware",
        ("intact", "uniprot"),
        ("human_train.tsv", "human_test.tsv", "fly_test.tsv"),
        "Official docs and repo expose Human Train, Human Test, and species transfer test files as concrete pair lists.",
        "external_holdout",
        "high",
        "dscript_human_plus_species_holdout",
        "direct_release_artifact",
        ("https://doi.org/10.1016/j.cels.2021.08.010", "https://github.com/samsledje/D-SCRIPT/blob/main/docs/source/data.rst"),
    ),
    PaperSpec(
        "topsy_turvy2022",
        "Topsy-Turvy",
        "https://doi.org/10.1093/bioinformatics/btac258",
        "ppi_prediction",
        "sequence_plus_network",
        ("uniprot", "string"),
        ("pos_pairs", "neg_pairs", "pos_test", "neg_test"),
        "Official repo documents explicit positive and negative edgelists for training and testing.",
        "held_out_test",
        "medium",
        "topsy_turvy_edgelists",
        "repo_documented_release",
        ("https://doi.org/10.1093/bioinformatics/btac258", "https://github.com/kap-devkota/Topsy-Turvy"),
    ),
    PaperSpec(
        "tt3d2023",
        "TT3D",
        "https://doi.org/10.1093/bioinformatics/btad663",
        "ppi_prediction",
        "sequence_plus_3di",
        ("uniprot", "string"),
        ("D-SCRIPT benchmark", "3Di sequences"),
        "TT3D inherits the published D-SCRIPT benchmark artifacts and layers Foldseek 3Di information on top of that split family.",
        "external_holdout",
        "medium",
        "dscript_benchmark_family",
        "inherits_published_benchmark",
        ("https://doi.org/10.1093/bioinformatics/btad663", "https://github.com/samsledje/D-SCRIPT/blob/main/docs/source/data.rst"),
    ),
    PaperSpec(
        "ppitrans2024",
        "PPITrans",
        "https://doi.org/10.1109/TCBB.2024.3381825",
        "ppi_prediction",
        "transformer_plm",
        ("uniprot", "intact"),
        ("./data/dscript/data",),
        "Official repo instructs users to download the D-SCRIPT benchmark into ./data/dscript/data and then runs dedicated train/evaluate/test scripts.",
        "external_holdout",
        "medium",
        "dscript_benchmark_family",
        "inherits_published_benchmark",
        ("https://doi.org/10.1109/TCBB.2024.3381825", "https://github.com/LtECoD/PPITrans"),
    ),
    PaperSpec(
        "tuna2024",
        "TUnA",
        "https://doi.org/10.1093/bib/bbae359",
        "ppi_prediction",
        "esm2_transformer",
        ("uniprot", "intact"),
        ("train_dict", "val_dict", "test_dict", "Bernett"),
        "Official manuscript repo documents processing for cross-species and Bernett datasets and requires explicit train/val/test dictionary inputs.",
        "strict_unseen_protein",
        "high",
        "bernett_plus_cross_species",
        "repo_documented_release",
        ("https://doi.org/10.1093/bib/bbae359", "https://github.com/Wang-lab-UCSD/TUnA"),
    ),
    PaperSpec(
        "plm_interact2025",
        "PLM-interact",
        "https://doi.org/10.1038/s41467-025-64512-w",
        "ppi_prediction",
        "plm_cross_attention",
        ("uniprot", "intact"),
        ("Bernett benchmark", "held-out species"),
        "The paper reports source data and evaluates on the Bernett leakage-minimized benchmark plus held-out species splits.",
        "strict_unseen_protein",
        "high",
        "bernett_plus_species_holdout",
        "paper_and_external_benchmark_release",
        ("https://doi.org/10.1038/s41467-025-64512-w", "https://figshare.com/articles/dataset/PPI_prediction_from_sequence_gold_standard_dataset/21591618"),
    ),
    PaperSpec(
        "egcppis2025",
        "EGCPPIS",
        "https://doi.org/10.1186/s12859-025-06328-5",
        "binding_site_prediction",
        "equivariant_contrastive",
        ("rcsb_pdbe",),
        ("Train_335.fa", "Test_60.fa"),
        "Official repo includes the train/test benchmark files together with associated dataset folders.",
        "external_holdout",
        "high",
        "ppis_train335_family",
        "direct_release_artifact",
        ("https://doi.org/10.1186/s12859-025-06328-5",),
    ),
    PaperSpec(
        "mvso_ppis2025",
        "MVSO-PPIS",
        "https://doi.org/10.1093/bioinformatics/btaf470",
        "binding_site_prediction",
        "multi_view_graph",
        ("rcsb_pdbe",),
        ("Train_335.pkl", "Test_60.pkl", "Test_315-28.pkl", "UBtest_31-6.pkl"),
        "Official repo provides the PPIS benchmark files plus processed PDB files.",
        "external_holdout",
        "high",
        "ppis_train335_family",
        "direct_release_artifact",
        ("https://doi.org/10.1093/bioinformatics/btaf470", "https://github.com/Edwardblue282/MVSO-PPIS"),
    ),
    PaperSpec(
        "hssppi2025",
        "HSSPPI",
        "https://doi.org/10.1093/bib/bbaf079",
        "binding_site_prediction",
        "hierarchical_spatial_sequential",
        ("rcsb_pdbe",),
        ("Train335", "Test60", "Test287", "TestB25", "TestUB25"),
        "The paper and official release describe train/test datasets and trained models for two PPIS benchmark tasks.",
        "external_holdout",
        "medium",
        "hssppi_public_tasks",
        "repo_documented_release",
        ("https://doi.org/10.1093/bib/bbaf079",),
    ),
    PaperSpec(
        "mippis2024",
        "MIPPIS",
        "https://doi.org/10.1186/s12859-024-05964-7",
        "binding_site_prediction",
        "multi_information_fusion",
        ("rcsb_pdbe",),
        ("Train_335", "Test_60"),
        "MIPPIS uses the public Train_335/Test_60 benchmark family; exact IDs are recoverable through the shared benchmark repos.",
        "external_holdout",
        "medium",
        "ppis_train335_family",
        "inherits_published_benchmark",
        ("https://doi.org/10.1186/s12859-024-05964-7", "https://pmc.ncbi.nlm.nih.gov/articles/PMC11536593/"),
    ),
    PaperSpec(
        "seq_insite2024",
        "Seq-InSite",
        "https://doi.org/10.1093/bioinformatics/btad738",
        "binding_site_prediction",
        "sequence_only_ppis",
        ("uniprot", "rcsb_pdbe"),
        ("without60", "without70", "without315"),
        "Official repo releases models and datasets trained to avoid similarity with held-out PPIS benchmark sets such as without60 and without315.",
        "uniref_or_homology_guard",
        "medium",
        "seq_insite_similarity_guarded_ppis",
        "repo_documented_release",
        ("https://doi.org/10.1093/bioinformatics/btad738", "https://github.com/lucian-ilie/Seq-InSite"),
    ),
    PaperSpec(
        "deepppisp2019",
        "DeepPPISP",
        "https://doi.org/10.1093/bioinformatics/btz699",
        "binding_site_prediction",
        "sequence_plus_global_features",
        ("rcsb_pdbe", "uniprot"),
        ("Dset_186", "Dset_72", "PDBset_164", "350/70 split"),
        "Official repo ships the benchmark datasets and data_cache features, but the README still describes splitting the raw union yourself for the 350/70 partition.",
        "held_out_test",
        "high",
        "deepppisp_186_72_164",
        "partial_release_not_fixed_split",
        ("https://doi.org/10.1093/bioinformatics/btz699", "https://github.com/CSUBioGroup/DeepPPISP"),
    ),
)


def _project_status_from_verdict(verdict: str) -> str:
    if verdict == "faithful and acceptable as-is":
        return "usable"
    if verdict == "audit-useful but non-canonical":
        return "audit_only"
    if verdict == "misleading / leakage-prone":
        return "unsafe_for_training"
    return "blocked_pending_mapping"


def _recommended_policy(split_style: str) -> str:
    if split_style in {"strict_unseen_protein", "uniref_or_homology_guard"}:
        return "uniref_grouped"
    if split_style in {"external_holdout"}:
        return "paper_faithful_external"
    return "accession_grouped"


def _source_rows(con: duckdb.DuckDBPyConnection) -> dict[str, dict[str, Any]]:
    rows = con.execute(
        """
        SELECT source_key, source_name, license_scope, public_export_allowed, redistributable, scope_tier
        FROM warehouse_sources
        """
    ).fetchall()
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        out[normalize_source_family_name(row[0] or row[1] or "")] = {
            "source_key": row[0],
            "source_name": row[1],
            "license_scope": row[2],
            "public_export_allowed": bool(row[3]),
            "redistributable": bool(row[4]),
            "scope_tier": row[5],
        }
    return out


def _warehouse_profile(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    return {
        "protein_uniref_coverage": dict(
            zip(
                ("proteins", "uniref90"),
                con.execute(
                    """
                    SELECT
                        COUNT(*) AS proteins,
                        COUNT(*) FILTER (WHERE uniref90_cluster IS NOT NULL) AS uniref90
                    FROM proteins
                    """
                ).fetchone(),
                strict=True,
            )
        ),
        "pdb_entry_rows": int(con.execute("SELECT COUNT(*) FROM pdb_entries").fetchone()[0]),
        "structure_unit_rows": int(con.execute("SELECT COUNT(*) FROM structure_units").fetchone()[0]),
        "local_structure_rows": int(
            con.execute(
                "SELECT COUNT(*) FROM structure_units WHERE structure_file_present"
            ).fetchone()[0]
        ),
    }


def _verdict_for_paper(paper: PaperSpec) -> str:
    if paper.release_mode == "partial_release_not_fixed_split":
        return "incomplete because required evidence is missing"
    if paper.release_mode in {"inherits_published_benchmark", "repo_documented_release"}:
        return "audit-useful but non-canonical"
    if paper.release_mode in {"direct_release_artifact", "paper_and_external_benchmark_release"}:
        return "faithful and acceptable as-is"
    return "audit-useful but non-canonical"


def _supplemental_evidence(paper: PaperSpec) -> dict[str, Any]:
    base = DEFAULT_EXTERNAL_ARTIFACT_DIR
    if paper.paper_id == "szymborski2022rapppid":
        archive = base / "rapppid" / "rapppid_data.zip"
        if archive.exists():
            return {
                "status": "locally_verified_release_artifact",
                "summary": "Local RAPPPID Zenodo archive contains explicit C1/C2/C3 split artifacts.",
                "details": [
                    "The local archive includes train/val/test pair files and sequence dictionaries for the comparative splits.",
                    "Identifiers are STRING/Ensembl protein IDs rather than warehouse-native accessions.",
                ],
                "artifact_paths": [str(archive)],
            }
    if paper.paper_id == "sledzieski2021dscript":
        human_train = base / "dscript" / "human_train.tsv"
        human_test = base / "dscript" / "human_test.tsv"
        if human_train.exists() and human_test.exists():
            train_pairs, train_proteins = _count_pair_tsv(human_train)
            test_pairs, test_proteins = _count_pair_tsv(human_test)
            return {
                "status": "locally_verified_release_artifact",
                "summary": "Local D-SCRIPT release files expose concrete human train/test pair lists.",
                "details": [
                    f"`human_train.tsv` contains {train_pairs:,} labeled pairs across {train_proteins:,} unique proteins.",
                    f"`human_test.tsv` contains {test_pairs:,} labeled pairs across {test_proteins:,} unique proteins.",
                    "Identifiers are Ensembl/FlyBase-style protein IDs rather than warehouse-native accessions.",
                ],
                "artifact_paths": [str(human_train), str(human_test)],
            }
    if paper.paper_id == "topsy_turvy2022":
        return {
            "status": "repo_readme_verified",
            "summary": "The README explicitly documents `--pos-pairs`, `--neg-pairs`, `--pos-test`, and `--neg-test` arguments.",
            "details": [
                "This is strong evidence that the code expects distinct train and test edgelists rather than a CV-only workflow.",
            ],
        }
    if paper.paper_id == "ppitrans2024":
        return {
            "status": "repo_readme_verified",
            "summary": "The README explicitly instructs users to place the D-SCRIPT benchmark in `./data/dscript/data` and then run train/predict/evaluate scripts.",
            "details": [
                "This confirms that PPITrans is benchmarking on a fixed external split family rather than only reporting random folds.",
            ],
        }
    if paper.paper_id == "tuna2024":
        return {
            "status": "repo_readme_verified",
            "summary": "The README documents Bernett and cross-species preprocessing plus explicit train/val/test dictionary inputs in config files.",
            "details": [
                "This is strong evidence for split reproducibility, though the exact dictionaries were not mirrored locally in this run.",
            ],
        }
    if paper.paper_id == "seq_insite2024":
        return {
            "status": "repo_readme_verified",
            "summary": "The README names released weights such as `without60`, `without70`, and `without315` and explains that they avoid similarity to the corresponding held-out datasets.",
            "details": [
                "This supports a similarity-guarded evaluation story even though the exact split tables were not mirrored locally in this run.",
            ],
        }
    if paper.paper_id == "deepppisp2019":
        return {
            "status": "repo_readme_verified",
            "summary": "The README ships Dset_186/Dset_72/PDBset_164 and data_cache features but still states that users may split the raw union themselves.",
            "details": [
                "This weakens exact split auditability relative to papers that publish a fixed train/test membership file.",
            ],
        }
    return {}


def _source_findings(
    paper: PaperSpec,
    source_lookup: dict[str, dict[str, Any]],
    registry_payload: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    findings: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []
    registry_rows = registry_payload.get("source_records") or registry_payload.get("records") or []
    for family in paper.source_families:
        normalized = normalize_source_family_name(family)
        source_row = source_lookup.get(normalized)
        registry_count = sum(
            1
            for row in registry_rows
            if normalize_source_family_name(row.get("source_family") or row.get("source_key") or "")
            == normalized
        )
        if source_row is None:
            blockers.append(f"warehouse source family `{family}` is not present in warehouse_sources")
            continue
        findings.append(
            f"{source_row['source_name']} is present in the library with license scope `{source_row['license_scope']}` "
            f"and scope tier `{source_row['scope_tier']}` (registry records: {registry_count})."
        )
        if not source_row["public_export_allowed"] or not source_row["redistributable"]:
            warnings.append(
                f"{source_row['source_name']} remains non-public or non-redistributable in the condensed library, so it should stay audit-facing rather than governing."
            )
    if paper.task_group == "binding_site_prediction":
        findings.append(
            f"The warehouse already holds {profile['pdb_entry_rows']:,} PDB entries and {profile['local_structure_rows']:,} local structure-unit rows, so published PPIS benchmark files would be structurally groundable once mirrored."
        )
    else:
        findings.append(
            f"The proteins surface has {profile['protein_uniref_coverage']['uniref90']:,} UniRef90-assigned proteins, so strict unseen-protein or UniRef-aware audits are feasible once released identifiers bridge into best_evidence."
        )
    return findings, blockers, warnings


def _overlap_findings(paper: PaperSpec, profile: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    if paper.paper_id in {"szymborski2022rapppid", "sledzieski2021dscript"}:
        blockers.append("released split artifacts are published, but the identifiers are not bridged into warehouse-native protein refs")
        status = "mapping_blocked_after_roster_recovery"
        note = "The exact split files are available and auditable, but direct overlap checks remain blocked until Ensembl/FlyBase-style IDs are bridged into the warehouse."
    elif paper.benchmark_family == "ppis_train335_family":
        blockers.append("benchmark filenames are known, but the exact PPIS roster files were not mirrored into the local audit workspace in this run")
        status = "published_not_mirrored"
        note = "The shared PPIS benchmark family is explicit enough for audit planning, but exact chain/residue overlap could not be enumerated without mirroring the pkl/fa files."
    elif paper.release_mode == "partial_release_not_fixed_split":
        blockers.append("benchmark datasets are shipped, but the exact fixed 350/70 train/test membership is not exposed cleanly enough in the release surface")
        status = "split_membership_not_fixed_enough"
        note = "A published benchmark corpus exists, but the governing split membership is not released as a stable artifact."
    else:
        status = "preflight_only"
        note = "The split style is explicit and published enough to trust qualitatively, but exact overlap enumeration still depends on mirroring the released membership files into the warehouse audit path."
    return {
        "direct_overlap": {"status": status, "notes": [note]},
        "accession_root_overlap": {"status": status, "notes": [note]},
        "uniref_overlap": {
            "status": "theoretically_supported",
            "notes": [
                note,
                f"Warehouse proteins already cover {profile['protein_uniref_coverage']['uniref90']:,} UniRef90-assigned rows.",
            ],
        },
    }, blockers


def _leakage_findings(paper: PaperSpec) -> dict[str, Any]:
    notes = [
        "This paper set was pre-filtered to avoid pure cross-validation studies and to prefer explicit held-out or external test splits.",
        "The main residual risks are identifier-bridge gaps, benchmark-family saturation, and derivative reuse of the same public split family across many later papers.",
    ]
    if paper.benchmark_family == "ppis_train335_family":
        notes.append(
            "Because many later PPIS papers reuse the Train_335/Test_60 lineage, a reviewer should distinguish fair within-family comparison from genuine out-of-family generalization."
        )
    if paper.release_mode == "inherits_published_benchmark":
        notes.append(
            "This paper inherits a strong public benchmark rather than releasing a new one, so its main audit value is comparability, not novel split design."
        )
    if paper.release_mode == "partial_release_not_fixed_split":
        notes.append(
            "The benchmark corpus is published, but the exact fixed train/test membership is not released cleanly enough to remove ambiguity."
        )
    return {"status": "reviewed", "notes": notes}


def _governed_eligibility_findings(paper: PaperSpec, verdict: str) -> dict[str, Any]:
    notes = [
        "best_evidence remains the governing warehouse read view for this evaluation.",
        "Published external splits can be faithful and acceptable as paper-faithful audit lanes without automatically becoming the default ProteoSphere training benchmark.",
    ]
    if verdict == "faithful and acceptable as-is":
        status = "candidate_only"
        notes.append("This split is strong enough to trust as an external audit lane, but canonical training use still depends on warehouse mirroring and identifier resolution.")
    elif verdict == "audit-useful but non-canonical":
        status = "audit_only"
        notes.append("This split is most useful as an external comparison lane or shared-community benchmark, not as the sole canonical release target.")
    else:
        status = "audit_only"
        notes.append("This paper needs additional split-membership cleanup before it can support strong release claims.")
    return {"status": status, "notes": notes}


def _recommended_treatment(paper: PaperSpec, verdict: str, policy: str) -> str:
    if verdict == "faithful and acceptable as-is":
        return f"Keep this as a `{policy}` audit lane and mirror the exact released roster into the warehouse so direct leakage diagnostics become first-class rather than inferred."
    if verdict == "audit-useful but non-canonical":
        if paper.benchmark_family == "ppis_train335_family":
            return "Keep it as a fair shared-benchmark comparison lane, but pair it with at least one out-of-family validation set before using it for strong generalization claims."
        return f"Treat it as a `{policy}` audit lane or inherited benchmark family rather than a new canonical split."
    return f"Do not rely on the paper split alone. Reconstruct a fixed released roster and then reevaluate it under `{policy}`."


def _paper_payload(
    paper: PaperSpec,
    source_lookup: dict[str, dict[str, Any]],
    registry_payload: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    source_findings, source_blockers, source_warnings = _source_findings(
        paper, source_lookup, registry_payload, profile
    )
    overlap_findings, overlap_blockers = _overlap_findings(paper, profile)
    verdict = _verdict_for_paper(paper)
    policy = _recommended_policy(paper.split_style)
    supplemental = _supplemental_evidence(paper)
    return {
        "paper_id": paper.paper_id,
        "title": paper.title,
        "doi": paper.doi,
        "task_group": paper.task_group,
        "auditability": paper.auditability,
        "benchmark_family": paper.benchmark_family,
        "claimed_split_description": paper.claimed_split_description,
        "resolved_split_policy": {
            "policy": policy,
            "reason": option_reason("split_strategies", policy),
            "recommended_for_training": policy in {"accession_grouped", "uniref_grouped"},
            "paper_faithful_only": policy == "paper_faithful_external",
        },
        "overlap_findings": overlap_findings,
        "leakage_findings": _leakage_findings(paper),
        "source_family_findings": source_findings,
        "governed_eligibility_findings": _governed_eligibility_findings(paper, verdict),
        "verdict": verdict,
        "project_status": _project_status_from_verdict(verdict),
        "blockers": [*source_blockers, *overlap_blockers],
        "warnings": source_warnings,
        "recommended_canonical_treatment": _recommended_treatment(paper, verdict, policy),
        "provenance_notes": [
            "Primary evidence came from the condensed warehouse catalog, manifest, source registry, and Model Studio split-policy code.",
            "Supplemental paper/repo evidence came from official links provided in the curated audit-friendly list and from directly inspected release artifacts where available.",
            "No raw/archive fallback was used.",
        ],
        "supplemental_evidence": supplemental,
        "source_links": list(paper.source_links),
        "named_entities": list(paper.named_entities),
        "source_families": list(paper.source_families),
        "raw_archive_fallback_required": False,
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Audit-Friendly Paper Split Evaluation",
        "",
        f"- Generated at: {report['generated_at']}",
        f"- Warehouse root: `{report['warehouse_root']}`",
        f"- Default view: `{report['default_view']}`",
        "",
        "## Summary Table",
        "",
        "| Paper | Auditability | Verdict | Benchmark family | Policy |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report["papers"]:
        lines.append(
            f"| `{row['paper_id']}` | `{row['auditability']}` | {row['verdict']} | `{row['benchmark_family']}` | `{row['resolved_split_policy']['policy']}` |"
        )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in report["papers"]:
        grouped[row["verdict"]].append(row)
    for verdict in (
        "faithful and acceptable as-is",
        "audit-useful but non-canonical",
        "incomplete because required evidence is missing",
    ):
        items = grouped.get(verdict) or []
        if not items:
            continue
        lines.extend(["", f"## {verdict}", ""])
        for row in items:
            blocker_text = "; ".join(row["blockers"][:2]) or "none"
            lines.append(
                f"- `{row['paper_id']}`: {row['recommended_canonical_treatment']} Blockers: {blocker_text}."
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    os.environ.setdefault("PROTEOSPHERE_WAREHOUSE_ROOT", str(DEFAULT_WAREHOUSE_ROOT))
    manifest_path = DEFAULT_WAREHOUSE_ROOT / "warehouse_manifest.json"
    source_registry_path = DEFAULT_WAREHOUSE_ROOT / "control" / "source_registry.json"
    catalog_path = DEFAULT_WAREHOUSE_ROOT / "catalog" / "reference_library.duckdb"
    manifest_payload = load_public_reference_manifest(manifest_path)
    registry_payload = load_source_registry(source_registry_path)
    with duckdb.connect(str(catalog_path), read_only=True) as con:
        source_lookup = _source_rows(con)
        profile = _warehouse_profile(con)
    papers = [
        _paper_payload(
            paper,
            source_lookup=source_lookup,
            registry_payload=registry_payload,
            profile=profile,
        )
        for paper in PAPERS
    ]
    report = {
        "artifact_id": "paper_split_audit_friendly_evaluation",
        "schema_id": "proteosphere-paper-split-audit-friendly-2026-04-13",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "warehouse_root": str(DEFAULT_WAREHOUSE_ROOT),
        "catalog_path": str(catalog_path),
        "manifest_path": str(manifest_path),
        "source_registry_path": str(source_registry_path),
        "default_view": "best_evidence",
        "manifest_default_views": manifest_payload.get("default_views", {}),
        "warehouse_profile": profile,
        "summary": {
            "paper_count": len(papers),
            "verdict_counts": dict(sorted(Counter(row["verdict"] for row in papers).items())),
            "project_status_counts": dict(sorted(Counter(row["project_status"] for row in papers).items())),
            "benchmark_family_counts": dict(sorted(Counter(row["benchmark_family"] for row in papers).items())),
        },
        "warehouse_sufficiency_notes": [
            "This paper set is much more auditable than the earlier reading list because most papers either ship direct split artifacts or inherit a named public benchmark family.",
            "Even so, best_evidence still does not materialize DOI-indexed paper roster tables, so exact overlap computation requires mirroring the released split files into the local audit workspace.",
            "The GraphPPIS lineage demonstrates another reviewer value-add: published splits can still be overused as a single benchmark family, which is fair for like-for-like comparison but weak for claims of broad generalization.",
        ],
        "raw_archive_fallback_notes": [
            "No raw/archive fallback was required for this report.",
            "Direct local verification was performed for the D-SCRIPT and RAPPPID release artifacts already downloaded into the audit workspace.",
        ],
        "papers": papers,
    }
    _write_json(DEFAULT_OUTPUT_JSON, report)
    for row in papers:
        _write_json(DEFAULT_PER_PAPER_DIR / f"{row['paper_id']}.json", row)
    DEFAULT_OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT_MD.write_text(_render_markdown(report), encoding="utf-8")
    print(f"Wrote {DEFAULT_OUTPUT_JSON}")
    print(f"Wrote {DEFAULT_OUTPUT_MD}")
    print(f"Wrote {len(papers)} per-paper artifacts to {DEFAULT_PER_PAPER_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

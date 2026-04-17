from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz
import matplotlib.pyplot as plt
from matplotlib import gridspec
from matplotlib.patches import FancyBboxPatch
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle


REPO_ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_DIR = REPO_ROOT / "docs" / "manuscripts" / "proteosphere_paper"
SECTION_DIR = MANUSCRIPT_DIR / "sections"
REPORT_DIR = REPO_ROOT / "docs" / "reports"
STATUS_DIR = REPO_ROOT / "artifacts" / "status"
OUTPUT_DIR = REPO_ROOT / "output" / "pdf"
TMP_DIR = REPO_ROOT / "tmp" / "pdfs" / "proteosphere_paper"
FIGURE_DIR = OUTPUT_DIR / "proteosphere_paper_assets"
FIGURE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

WAREHOUSE_ROOT = Path(r"D:\ProteoSphere\reference_library")
WAREHOUSE_SUMMARY = WAREHOUSE_ROOT / "warehouse_summary.json"
WAREHOUSE_MANIFEST = WAREHOUSE_ROOT / "warehouse_manifest.json"
SOURCE_REGISTRY = WAREHOUSE_ROOT / "control" / "source_registry.json"
SOURCE_COVERAGE = REPORT_DIR / "source_coverage_matrix.md"
TIER1_SUMMARY = STATUS_DIR / "literature_hunt_tier1_master_summary.json"
DTA_PROOF = STATUS_DIR / "literature_hunt_deep_proofs" / "dta_setting1_family_audit.json"
PDBBIND_PROOF = STATUS_DIR / "literature_hunt_deep_proofs" / "pdbbind_core_family_audit.json"
ATTENTIONDTA_PROOF = STATUS_DIR / "literature_hunt_recent_expansion_proofs" / "attentiondta_random_cv_family_audit.json"
STRUCT2GRAPH_REPORT = REPORT_DIR / "struct2graph_reproduced_overlap.md"
STRUCT2GRAPH_OVERLAY = STATUS_DIR / "struct2graph_overlap" / "4EQ6_train_test_overlay.png"
D2CP_REPORT = REPORT_DIR / "paper_d2cp05644e_quality_assessment.md"

MAIN_MD = MANUSCRIPT_DIR / "proteosphere_manuscript_draft.md"
SUPP_MD = MANUSCRIPT_DIR / "proteosphere_supplementary_appendix.md"
PI_MD = MANUSCRIPT_DIR / "proteosphere_pi_briefing.md"
METHODS_MD = SECTION_DIR / "methods_systems.md"
RESULTS_MD = SECTION_DIR / "results_cases.md"
METHODS_CLAIMS = SECTION_DIR / "methods_systems.claims.json"
RESULTS_CLAIMS = SECTION_DIR / "results_cases.claims.json"

STORAGE_LEDGER_JSON = STATUS_DIR / "proteosphere_paper_storage_ledger.json"
STORAGE_LEDGER_MD = REPORT_DIR / "proteosphere_paper_storage_ledger.md"
CLAIM_LEDGER_JSON = MANUSCRIPT_DIR / "claim_ledger.json"
FIGURE_MANIFEST_JSON = MANUSCRIPT_DIR / "figure_manifest.json"

MAIN_PDF = OUTPUT_DIR / "proteosphere_manuscript_draft.pdf"
SUPP_PDF = OUTPUT_DIR / "proteosphere_manuscript_supplement.pdf"
PI_PDF = OUTPUT_DIR / "proteosphere_pi_briefing.pdf"
ASSET_MANIFEST = OUTPUT_DIR / "proteosphere_paper_package.assets.json"


@dataclass
class RenderContext:
    figure_map: dict[str, dict[str, Any]]
    tier1_summary: dict[str, Any]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def human_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(amount)} {unit}"
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{value} B"


def dir_stats(path: Path) -> dict[str, Any]:
    total = 0
    files = 0
    exists = path.exists()
    if exists:
        for root, _dirs, filenames in os.walk(path):
            for name in filenames:
                fp = Path(root) / name
                try:
                    total += fp.stat().st_size
                    files += 1
                except OSError:
                    continue
    return {
        "path": str(path),
        "exists": exists,
        "file_count": files,
        "byte_count": total,
        "human_bytes": human_bytes(total),
    }


def extract_int(markdown: str, label: str) -> int:
    match = re.search(rf"{re.escape(label)}:\s*`([\d,]+)`", markdown)
    if not match:
        raise ValueError(f"Could not find label {label!r}")
    return int(match.group(1).replace(",", ""))


def build_storage_ledger() -> dict[str, Any]:
    source_coverage_md = read_text(SOURCE_COVERAGE)
    source_count = extract_int(source_coverage_md, "Source count")
    present_files = extract_int(source_coverage_md, "Total present files")
    present_bytes = extract_int(source_coverage_md, "Total present bytes")

    warehouse_stats = dir_stats(WAREHOUSE_ROOT)
    raw_stats = dir_stats(REPO_ROOT / "data" / "raw")
    incoming_stats = dir_stats(Path(r"E:\ProteoSphere\reference_library\incoming_mirrors"))

    ledger = {
        "artifact_id": "proteosphere_paper_storage_ledger",
        "generated_from": [
            str(SOURCE_COVERAGE),
            str(WAREHOUSE_ROOT),
            str(REPO_ROOT / "data" / "raw"),
            str(Path(r"E:\ProteoSphere\reference_library\incoming_mirrors")),
        ],
        "tracked_source_estate": {
            "source_count": source_count,
            "present_file_count": present_files,
            "present_byte_count": present_bytes,
            "present_human_bytes": human_bytes(present_bytes),
        },
        "live_paths": {
            "warehouse_root": warehouse_stats,
            "repo_data_raw": raw_stats,
            "incoming_mirrors": incoming_stats,
        },
        "notes": [
            "Tracked source estate numbers come from the checked-in source coverage matrix.",
            "Live path sizes are current filesystem measurements in this environment and should not be treated as release-bound package sizes.",
            "These numbers support a 'large source estate versus smaller warehouse-first evidence surface' claim, but do not justify the unsupported exact phrase '>2 TB to ~25 GB'.",
        ],
    }
    STORAGE_LEDGER_JSON.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    md = "\n".join(
        [
            "# ProteoSphere Paper Storage Ledger",
            "",
            f"- Tracked source count: `{source_count}`",
            f"- Tracked present files: `{present_files}`",
            f"- Tracked present bytes: `{present_bytes}` (`{human_bytes(present_bytes)}`)",
            "",
            "## Live Path Measurements",
            "",
            f"- Warehouse root: `{warehouse_stats['human_bytes']}` across `{warehouse_stats['file_count']}` files",
            f"- Repo `data/raw`: `{raw_stats['human_bytes']}` across `{raw_stats['file_count']}` files",
            f"- Incoming mirrors: `{incoming_stats['human_bytes']}` across `{incoming_stats['file_count']}` files",
            "",
            "## Interpretation",
            "",
            "- The checked-in coverage report supports a very large tracked source estate.",
            "- The live filesystem measurements support a much smaller warehouse-first evidence surface in the current environment.",
            "- These figures are suitable for a constructive compactness claim, but not for the unsupported exact phrase `>2 TB -> ~25 GB`.",
            "",
        ]
    )
    STORAGE_LEDGER_MD.write_text(md, encoding="utf-8")
    return ledger


def safe_text(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r"<font face='Courier'>\1</font>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    return text


def styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle("Title", parent=sample["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=colors.HexColor("#102542"), spaceAfter=10),
        "H1": ParagraphStyle("H1", parent=sample["Heading1"], fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=colors.HexColor("#102542"), spaceBefore=8, spaceAfter=6),
        "H2": ParagraphStyle("H2", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=11.2, leading=13.6, textColor=colors.HexColor("#1f2937"), spaceBefore=6, spaceAfter=4),
        "Body": ParagraphStyle("Body", parent=sample["BodyText"], fontName="Helvetica", fontSize=9.4, leading=12.4, textColor=colors.HexColor("#24303d"), spaceAfter=4),
        "Bullet": ParagraphStyle("Bullet", parent=sample["BodyText"], fontName="Helvetica", fontSize=9.1, leading=11.8, leftIndent=14, firstLineIndent=-8, bulletIndent=0, textColor=colors.HexColor("#24303d"), spaceAfter=2),
        "Caption": ParagraphStyle("Caption", parent=sample["BodyText"], fontName="Helvetica-Oblique", fontSize=8.2, leading=10.0, textColor=colors.HexColor("#4b5563"), spaceAfter=6),
    }


def add_box(ax: Any, x: float, y: float, w: float, h: float, label: str, fc: str, ec: str = "#1f2937") -> None:
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.02", linewidth=1.2, edgecolor=ec, facecolor=fc)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=10, color="#111827", wrap=True)


def generate_figures(storage_ledger: dict[str, Any]) -> dict[str, Any]:
    tier1 = load_json(TIER1_SUMMARY)
    warehouse_summary = load_json(WAREHOUSE_SUMMARY)
    dta_proof = load_json(DTA_PROOF)
    pdbbind_proof = load_json(PDBBIND_PROOF)
    attention_proof = load_json(ATTENTIONDTA_PROOF)
    figures: dict[str, Any] = {}

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.axis("off")
    add_box(ax, 0.03, 0.58, 0.22, 0.22, "Pinned source estate\nUniProt, RCSB/PDBe,\nAlphaFold, BindingDB,\nBioGRID, IntAct,\nInterPro, Reactome", "#dbeafe")
    add_box(ax, 0.30, 0.58, 0.18, 0.22, "Release pinning\nand source registry", "#e0f2fe")
    add_box(ax, 0.53, 0.58, 0.18, 0.22, "Compact warehouse\n13 materialized\nfamilies", "#dcfce7")
    add_box(ax, 0.76, 0.58, 0.19, 0.22, "best_evidence\nlogical view", "#fef3c7")
    add_box(ax, 0.17, 0.18, 0.22, 0.20, "Runtime + review code\nreference_library.py\nruntime.py", "#ede9fe")
    add_box(ax, 0.46, 0.18, 0.22, 0.20, "Audit outputs\nleakage, provenance,\nadmissibility,\ncontrols", "#fee2e2")
    add_box(ax, 0.74, 0.18, 0.20, 0.20, "Canonical treatment\npaper-faithful audit,\nblock, or control", "#fce7f3")
    arrows = [
        ((0.25, 0.69), (0.30, 0.69)),
        ((0.48, 0.69), (0.53, 0.69)),
        ((0.71, 0.69), (0.76, 0.69)),
        ((0.39, 0.38), (0.46, 0.38)),
        ((0.68, 0.38), (0.74, 0.38)),
        ((0.62, 0.58), (0.56, 0.40)),
        ((0.82, 0.58), (0.82, 0.40)),
    ]
    for (x1, y1), (x2, y2) in arrows:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=1.5, color="#475569"))
    fig.suptitle("ProteoSphere system overview", fontsize=16, fontweight="bold", y=0.97)
    fig.tight_layout()
    path1 = FIGURE_DIR / "figure_1_system_overview.png"
    fig.savefig(path1, dpi=220, bbox_inches="tight")
    plt.close(fig)
    figures["FIGURE_1_PATH"] = {
        "path": str(path1),
        "caption": "ProteoSphere system overview: pinned source estate to warehouse-first review and canonical treatment.",
        "sources": [str(WAREHOUSE_SUMMARY), str(WAREHOUSE_MANIFEST), str(SOURCE_REGISTRY), str(REPO_ROOT / "api" / "model_studio" / "reference_library.py"), str(REPO_ROOT / "api" / "model_studio" / "runtime.py")],
    }

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    live = storage_ledger["live_paths"]
    labels = ["Warehouse root", "Repo data/raw", "Incoming mirrors"]
    vals = [
        live["warehouse_root"]["byte_count"] / (1024 ** 3),
        live["repo_data_raw"]["byte_count"] / (1024 ** 3),
        live["incoming_mirrors"]["byte_count"] / (1024 ** 3),
    ]
    axes[0].bar(labels, vals, color=["#10b981", "#3b82f6", "#6366f1"])
    axes[0].set_ylabel("GB")
    axes[0].set_title("Current local footprint")
    axes[0].tick_params(axis="x", rotation=20)
    axes[0].grid(axis="y", linestyle="--", alpha=0.3)
    axes[0].spines["top"].set_visible(False)
    axes[0].spines["right"].set_visible(False)
    axes[1].axis("off")
    summary_lines = [
        f"Tracked sources: {storage_ledger['tracked_source_estate']['source_count']}",
        f"Tracked present bytes: {storage_ledger['tracked_source_estate']['present_human_bytes']}",
        f"Warehouse default view: {warehouse_summary['default_view']}",
        f"Warehouse authoritative sources: {warehouse_summary['source_count']}",
        "Registry records / families: 113 / 69",
        f"Materialized families: {len(warehouse_summary['family_counts'])}",
        f"Structure units: {warehouse_summary['family_counts']['structure_units']:,}",
        f"Protein-ligand edges: {warehouse_summary['family_counts']['protein_ligand_edges']:,}",
        f"Protein-protein edges: {warehouse_summary['family_counts']['protein_protein_edges']:,}",
    ]
    y = 0.92
    axes[1].text(0.02, y, "Why the warehouse stays compact", fontsize=14, fontweight="bold", color="#102542", transform=axes[1].transAxes)
    y -= 0.12
    for line in summary_lines:
        axes[1].text(0.04, y, f"- {line}", fontsize=10.5, color="#24303d", transform=axes[1].transAxes)
        y -= 0.085
    axes[1].text(0.04, y - 0.02, "Hot path: planning and governance metadata.\nLazy path: heavy coordinates, maps, long tables, alignments.", fontsize=10, color="#4b5563", transform=axes[1].transAxes)
    fig.suptitle("Large source estate versus compact warehouse-first evidence surface", fontsize=15, fontweight="bold", y=0.98)
    fig.tight_layout()
    path2 = FIGURE_DIR / "figure_2_storage_footprint.png"
    fig.savefig(path2, dpi=220, bbox_inches="tight")
    plt.close(fig)
    figures["FIGURE_2_PATH"] = {
        "path": str(path2),
        "caption": "Current local footprint and warehouse-first compactness framing. Live path sizes are environment measurements, not release-bound package sizes.",
        "sources": [str(STORAGE_LEDGER_JSON), str(WAREHOUSE_SUMMARY), str(WAREHOUSE_MANIFEST)],
    }

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.axis("off")
    add_box(ax, 0.03, 0.62, 0.18, 0.18, "Recover claimed split\nor benchmark family", "#dbeafe")
    add_box(ax, 0.27, 0.62, 0.18, 0.18, "Map to warehouse\nbest_evidence records", "#dcfce7")
    add_box(ax, 0.51, 0.62, 0.18, 0.18, "Audit overlap:\nidentity, family,\npartner, structure", "#fef3c7")
    add_box(ax, 0.75, 0.62, 0.18, 0.18, "Audit mitigation:\ncold split, cluster,\ntime, source separation", "#fde68a")
    add_box(ax, 0.16, 0.20, 0.18, 0.18, "Tier 1 hard failure", "#fee2e2")
    add_box(ax, 0.41, 0.20, 0.18, 0.18, "Tier 2 supporting\nor audit-only", "#fce7f3")
    add_box(ax, 0.66, 0.20, 0.18, 0.18, "Control /\nnonfailure", "#d1fae5")
    for x in [0.21, 0.45, 0.69]:
        ax.annotate("", xy=(x + 0.06, 0.71), xytext=(x, 0.71), arrowprops=dict(arrowstyle="->", lw=1.5, color="#475569"))
    ax.annotate("", xy=(0.22, 0.38), xytext=(0.60, 0.62), arrowprops=dict(arrowstyle="->", lw=1.5, color="#475569"))
    ax.annotate("", xy=(0.47, 0.38), xytext=(0.68, 0.62), arrowprops=dict(arrowstyle="->", lw=1.5, color="#475569"))
    ax.annotate("", xy=(0.72, 0.38), xytext=(0.84, 0.62), arrowprops=dict(arrowstyle="->", lw=1.5, color="#475569"))
    ax.text(0.5, 0.06, "Direct split bugs, benchmark-family inheritance, and invalid external validation are treated as different failure classes.", ha="center", fontsize=10.5, color="#4b5563")
    fig.suptitle("ProteoSphere review logic", fontsize=16, fontweight="bold", y=0.97)
    fig.tight_layout()
    path3 = FIGURE_DIR / "figure_3_review_logic.png"
    fig.savefig(path3, dpi=220, bbox_inches="tight")
    plt.close(fig)
    figures["FIGURE_3_PATH"] = {
        "path": str(path3),
        "caption": "ProteoSphere review logic: recover, map, audit overlap, audit mitigation, then assign hard failure, supporting case, or control status.",
        "sources": [str(TIER1_SUMMARY), str(REPO_ROOT / "api" / "model_studio" / "runtime.py"), str(REPO_ROOT / "api" / "model_studio" / "reference_library.py")],
    }

    summary = tier1["summary"]
    fig = plt.figure(figsize=(11, 7))
    gs = gridspec.GridSpec(2, 2, figure=fig)
    ax1 = fig.add_subplot(gs[0, 0])
    years = summary["year_counts"]
    ax1.bar(list(years.keys()), list(years.values()), color="#2563eb")
    ax1.set_title("Tier 1 papers by year")
    ax1.grid(axis="y", linestyle="--", alpha=0.3)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax2 = fig.add_subplot(gs[0, 1])
    issues = summary["issue_family_counts"]
    ax2.barh(list(issues.keys()), list(issues.values()), color="#ef4444")
    ax2.set_title("Tier 1 issue families")
    ax2.grid(axis="x", linestyle="--", alpha=0.3)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax3 = fig.add_subplot(gs[1, 0])
    domains = summary["domain_counts"]
    ax3.pie(list(domains.values()), labels=list(domains.keys()), autopct="%1.0f%%", colors=["#10b981", "#8b5cf6"], startangle=90)
    ax3.set_title("Tier 1 domain concentration")
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis("off")
    txt = [
        f"Tier 1 total: {summary['tier1_total']}",
        f"2023+ papers: {summary['recent_2023plus_count']}",
        f"Warm-start family failures: {summary['issue_family_counts']['warm_start_benchmark_family']}",
        f"Protein-overlapped external families: {summary['issue_family_counts']['protein_overlapped_external_family']}",
        "Flagship paper-specific cases:",
        "- Struct2Graph",
        "- D2CP05644E",
        "- AttentionDTA",
    ]
    y = 0.90
    for i, line in enumerate(txt):
        ax4.text(0.02, y, line, fontsize=11 if i < 4 else 10.5, fontweight="bold" if i in {0, 1, 2, 3, 4} else None, color="#102542" if i < 5 else "#24303d", transform=ax4.transAxes)
        y -= 0.11 if i < 4 else 0.09
    fig.suptitle("Tier 1 landscape", fontsize=16, fontweight="bold", y=0.98)
    fig.tight_layout()
    path4 = FIGURE_DIR / "figure_4_tier1_landscape.png"
    fig.savefig(path4, dpi=220, bbox_inches="tight")
    plt.close(fig)
    figures["FIGURE_4_PATH"] = {
        "path": str(path4),
        "caption": "Tier 1 proof set across time, issue families, and domains.",
        "sources": [str(TIER1_SUMMARY)],
    }

    fig = plt.figure(figsize=(11, 8))
    gs = gridspec.GridSpec(2, 2, figure=fig)
    ax1 = fig.add_subplot(gs[0, 0])
    if STRUCT2GRAPH_OVERLAY.exists():
        img = plt.imread(STRUCT2GRAPH_OVERLAY)
        ax1.imshow(img)
        ax1.axis("off")
        ax1.set_title("Struct2Graph overlap example")
    else:
        ax1.axis("off")
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.bar(["Shared PDB IDs", "4EQ6 train", "4EQ6 test"], [643, 78, 9], color=["#dc2626", "#2563eb", "#16a34a"])
    ax2.set_title("Struct2Graph reproduced split")
    ax2.grid(axis="y", linestyle="--", alpha=0.3)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax3 = fig.add_subplot(gs[1, 0])
    d2cp_metrics = {"PDBbind direct": 4, "PDBbind shared partner": 110, "Nanobody direct": 1, "Nanobody shared partner": 16, "Metadynamics direct": 26, "Metadynamics shared partner": 75}
    ax3.barh(list(d2cp_metrics.keys()), list(d2cp_metrics.values()), color="#f59e0b")
    ax3.set_title("D2CP05644E panel contamination")
    ax3.grid(axis="x", linestyle="--", alpha=0.3)
    ax3.spines["top"].set_visible(False)
    ax3.spines["right"].set_visible(False)
    ax4 = fig.add_subplot(gs[1, 1])
    x = range(4)
    vals1 = [
        dta_proof["datasets"]["davis"]["shared_drug_count"],
        dta_proof["datasets"]["davis"]["shared_target_count"],
        attention_proof["datasets"]["davis"]["shared_drug_count"],
        attention_proof["datasets"]["davis"]["shared_target_count"],
    ]
    labels = ["DeepDTA\nDavis drug", "DeepDTA\nDavis target", "AttentionDTA\nDavis drug", "AttentionDTA\nDavis target"]
    ax4.bar(x, vals1, color=["#7c3aed", "#7c3aed", "#0ea5e9", "#0ea5e9"])
    ax4.set_xticks(list(x))
    ax4.set_xticklabels(labels)
    ax4.set_title("Warm-start and random-CV reuse")
    ax4.grid(axis="y", linestyle="--", alpha=0.3)
    ax4.spines["top"].set_visible(False)
    ax4.spines["right"].set_visible(False)
    ax4.text(0.02, 0.98, f"PDBbind v2016 direct protein overlap:\n{pdbbind_proof['core_sets']['v2016_core']['test_complexes_with_direct_protein_overlap']}/{pdbbind_proof['core_sets']['v2016_core']['test_count']}", transform=ax4.transAxes, va="top", fontsize=9.5, color="#4b5563")
    fig.suptitle("Flagship case studies", fontsize=16, fontweight="bold", y=0.98)
    fig.tight_layout()
    path5 = FIGURE_DIR / "figure_5_flagship_cases.png"
    fig.savefig(path5, dpi=220, bbox_inches="tight")
    plt.close(fig)
    figures["FIGURE_5_PATH"] = {
        "path": str(path5),
        "caption": "Flagship case studies spanning direct split reuse, invalid external validation, warm-start benchmark inheritance, and row-level random-CV leakage.",
        "sources": [str(STRUCT2GRAPH_REPORT), str(D2CP_REPORT), str(DTA_PROOF), str(PDBBIND_PROOF), str(ATTENTIONDTA_PROOF), str(STRUCT2GRAPH_OVERLAY)],
    }

    fig, ax = plt.subplots(figsize=(10.8, 5.4))
    ax.axis("off")
    add_box(ax, 0.05, 0.58, 0.25, 0.20, "Tier 1 hard failures\n29 confirmed papers", "#fee2e2")
    add_box(ax, 0.37, 0.58, 0.25, 0.20, "Tier 2 supporting cases\nused carefully", "#fef3c7")
    add_box(ax, 0.69, 0.58, 0.25, 0.20, "Controls\nmitigation-aware or stronger designs", "#d1fae5")
    add_box(ax, 0.10, 0.20, 0.35, 0.20, "What ProteoSphere says yes to:\n- paper-faithful audit lanes\n- stronger cold-split or grouped designs\n- explicit mitigation claims that survive audit", "#dbeafe")
    add_box(ax, 0.55, 0.20, 0.35, 0.20, "What ProteoSphere blocks or downgrades:\n- direct reuse\n- inherited warm-start generalization claims\n- protein-overlapped external benchmarks", "#ede9fe")
    for x1, y1, x2, y2 in [(0.18, 0.58, 0.26, 0.40), (0.50, 0.58, 0.50, 0.40), (0.82, 0.58, 0.74, 0.40)]:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=1.5, color="#475569"))
    ax.text(0.5, 0.06, "The reviewer is useful because it can both flag unsafe claims and validate better practice.", ha="center", fontsize=11, color="#102542")
    fig.suptitle("Constructive use of the reviewer", fontsize=16, fontweight="bold", y=0.97)
    fig.tight_layout()
    path6 = FIGURE_DIR / "figure_6_controls.png"
    fig.savefig(path6, dpi=220, bbox_inches="tight")
    plt.close(fig)
    figures["FIGURE_6_PATH"] = {
        "path": str(path6),
        "caption": "Controls and constructive use of ProteoSphere as a reviewer rather than a takedown tool.",
        "sources": [str(TIER1_SUMMARY), str(STATUS_DIR / "literature_hunt_deep_review.json"), str(STATUS_DIR / "literature_hunt_recent_expansion.json")],
    }
    return figures


def merge_claim_ledgers(storage_ledger: dict[str, Any]) -> list[dict[str, Any]]:
    claims = load_json(METHODS_CLAIMS) + load_json(RESULTS_CLAIMS)
    claims.extend(
        [
            {
                "claim_text": "The tracked source estate currently spans 53 tracked sources with 324,755,949,775 present bytes.",
                "source_path": str(SOURCE_COVERAGE),
                "status": "supported",
            },
            {
                "claim_text": f"The current live warehouse root measures {storage_ledger['live_paths']['warehouse_root']['human_bytes']}.",
                "source_path": str(STORAGE_LEDGER_JSON),
                "status": "supported",
            },
            {
                "claim_text": f"The current repo data/raw path measures {storage_ledger['live_paths']['repo_data_raw']['human_bytes']}.",
                "source_path": str(STORAGE_LEDGER_JSON),
                "status": "supported",
            },
            {
                "claim_text": f"The current incoming mirror path measures {storage_ledger['live_paths']['incoming_mirrors']['human_bytes']}.",
                "source_path": str(STORAGE_LEDGER_JSON),
                "status": "supported",
            },
            {
                "claim_text": "The current manuscript intentionally avoids the unsupported exact phrase '>2 TB to ~25 GB'.",
                "source_path": str(STORAGE_LEDGER_MD),
                "status": "supported",
            },
        ]
    )
    CLAIM_LEDGER_JSON.write_text(json.dumps(claims, indent=2) + "\n", encoding="utf-8")
    return claims


def build_figure_manifest(figures: dict[str, Any]) -> dict[str, Any]:
    manifest = {
        "artifact_id": "proteosphere_paper_figure_manifest",
        "figure_count": len(figures),
        "figures": [{"token": key, **value} for key, value in figures.items()],
    }
    FIGURE_MANIFEST_JSON.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def build_tier1_table() -> LongTable:
    report = load_json(TIER1_SUMMARY)
    rows = [["Paper", "Year", "Domain", "Issue family", "Recommended treatment"]]
    for row in report["papers"]:
        treatment = row["recommended_proteosphere_treatment"]
        if len(treatment) > 140:
            treatment = treatment[:137].rstrip() + "..."
        rows.append([row["paper_id"], str(row["year"]), row["domain"], row["issue_family"], treatment])
    table = LongTable(rows, colWidths=[1.4 * inch, 0.45 * inch, 1.0 * inch, 1.7 * inch, 3.0 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#102542")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.4),
                ("LEADING", (0, 0), (-1, -1), 9.0),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    return table


def replace_tokens(text: str, context: RenderContext) -> str:
    text = text.replace("{{METHODS_SYSTEMS}}", read_text(METHODS_MD))
    text = text.replace("{{RESULTS_CASES}}", read_text(RESULTS_MD))
    for token, meta in context.figure_map.items():
        text = text.replace("{{" + token + "}}", meta["path"])
    return text


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(safe_text(text), style)


def render_markdown_to_story(text: str) -> list[Any]:
    s = styles()
    story: list[Any] = []
    buffer: list[str] = []

    def flush_buffer() -> None:
        nonlocal buffer
        if buffer:
            story.append(paragraph(" ".join(part.strip() for part in buffer if part.strip()), s["Body"]))
            buffer = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped == "{{TIER1_TABLE}}":
            flush_buffer()
            story.append(build_tier1_table())
            story.append(Spacer(1, 0.12 * inch))
            continue
        if not stripped:
            flush_buffer()
            story.append(Spacer(1, 0.03 * inch))
            continue
        image_match = re.match(r"!\[(.*?)\]\((.*?)\)", stripped)
        if image_match:
            flush_buffer()
            caption = image_match.group(1)
            image_path = Path(image_match.group(2))
            if image_path.exists():
                story.append(Image(str(image_path), width=6.7 * inch, height=3.9 * inch))
                story.append(paragraph(caption, s["Caption"]))
            continue
        if stripped.startswith("# "):
            flush_buffer()
            story.append(paragraph(stripped[2:], s["Title"]))
            continue
        if stripped.startswith("## "):
            flush_buffer()
            story.append(paragraph(stripped[3:], s["H1"]))
            continue
        if stripped.startswith("### "):
            flush_buffer()
            story.append(paragraph(stripped[4:], s["H2"]))
            continue
        if stripped.startswith("- "):
            flush_buffer()
            story.append(paragraph(f"- {stripped[2:]}", s["Bullet"]))
            continue
        if re.match(r"^\d+\.\s+", stripped):
            flush_buffer()
            story.append(paragraph(stripped, s["Bullet"]))
            continue
        buffer.append(stripped)
    flush_buffer()
    return story


def render_pdf(markdown_path: Path, pdf_path: Path, render_context: RenderContext) -> Path:
    raw = read_text(markdown_path)
    expanded = replace_tokens(raw, render_context)
    story = render_markdown_to_story(expanded)
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter, leftMargin=0.72 * inch, rightMargin=0.72 * inch, topMargin=0.65 * inch, bottomMargin=0.65 * inch)
    doc.build(story)
    return pdf_path


def render_preview(pdf_path: Path, image_path: Path) -> None:
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
    pix.save(str(image_path))
    doc.close()


def main() -> None:
    storage_ledger = build_storage_ledger()
    figures = generate_figures(storage_ledger)
    build_figure_manifest(figures)
    merge_claim_ledgers(storage_ledger)
    tier1_summary = load_json(TIER1_SUMMARY)
    context = RenderContext(figure_map=figures, tier1_summary=tier1_summary)

    render_pdf(MAIN_MD, MAIN_PDF, context)
    render_pdf(SUPP_MD, SUPP_PDF, context)
    render_pdf(PI_MD, PI_PDF, context)

    preview_main = TMP_DIR / "proteosphere_manuscript_draft.preview.page1.png"
    preview_supp = TMP_DIR / "proteosphere_manuscript_supplement.preview.page1.png"
    preview_pi = TMP_DIR / "proteosphere_pi_briefing.preview.page1.png"
    render_preview(MAIN_PDF, preview_main)
    render_preview(SUPP_PDF, preview_supp)
    render_preview(PI_PDF, preview_pi)

    asset_manifest = {
        "main_pdf": str(MAIN_PDF),
        "supplement_pdf": str(SUPP_PDF),
        "pi_pdf": str(PI_PDF),
        "previews": [str(preview_main), str(preview_supp), str(preview_pi)],
        "figure_manifest": str(FIGURE_MANIFEST_JSON),
        "claim_ledger": str(CLAIM_LEDGER_JSON),
        "storage_ledger_json": str(STORAGE_LEDGER_JSON),
        "storage_ledger_md": str(STORAGE_LEDGER_MD),
        "figures": [meta["path"] for meta in figures.values()],
    }
    ASSET_MANIFEST.write_text(json.dumps(asset_manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(asset_manifest, indent=2))


if __name__ == "__main__":
    main()

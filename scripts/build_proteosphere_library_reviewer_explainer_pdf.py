from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import fitz
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "output" / "pdf"
TMP_DIR = REPO_ROOT / "tmp" / "pdfs" / "proteosphere_library_reviewer_explainer"
FIGURE_DIR = OUTPUT_DIR / "proteosphere_library_reviewer_explainer_assets"
REPORT_MD = REPO_ROOT / "docs" / "reports" / "proteosphere_library_reviewer_explainer.md"
PDF_PATH = OUTPUT_DIR / "proteosphere_library_reviewer_explainer.pdf"
ASSET_MANIFEST = OUTPUT_DIR / "proteosphere_library_reviewer_explainer.assets.json"
PREVIEW_PATH = TMP_DIR / "proteosphere_library_reviewer_explainer.preview.page1.png"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

WAREHOUSE_ROOT = Path(r"D:\ProteoSphere\reference_library")
WAREHOUSE_SUMMARY = WAREHOUSE_ROOT / "warehouse_summary.json"
WAREHOUSE_MANIFEST = WAREHOUSE_ROOT / "warehouse_manifest.json"
SOURCE_REGISTRY = WAREHOUSE_ROOT / "control" / "source_registry.json"

SOURCE_RELEASE_MATRIX = REPO_ROOT / "docs" / "reports" / "source_release_matrix.md"
SOURCE_STORAGE_STRATEGY = REPO_ROOT / "docs" / "reports" / "source_storage_strategy.md"
LIGHTWEIGHT_MASTER_PLAN = REPO_ROOT / "docs" / "reports" / "lightweight_reference_library_master_plan.md"
LITE_SCHEMA = REPO_ROOT / "docs" / "reports" / "proteosphere-lite.schema.md"
LITE_CONTENTS = REPO_ROOT / "docs" / "reports" / "proteosphere-lite.contents.md"
SOURCE_COVERAGE = REPO_ROOT / "docs" / "reports" / "source_coverage_matrix.md"
LIB_EQUIV = REPO_ROOT / "docs" / "reports" / "library_vs_broad_collection_equivalence.md"
STORAGE_LEDGER = REPO_ROOT / "docs" / "reports" / "proteosphere_paper_storage_ledger.md"
STORAGE_LEDGER_JSON = REPO_ROOT / "artifacts" / "status" / "proteosphere_paper_storage_ledger.json"

REFERENCE_LIBRARY_PY = REPO_ROOT / "api" / "model_studio" / "reference_library.py"
RUNTIME_PY = REPO_ROOT / "api" / "model_studio" / "runtime.py"
PAPER_EVAL_PIPELINE = REPO_ROOT / "api" / "model_studio" / "paper_evaluator" / "pipeline.py"
PAPER_EVAL_CLI = REPO_ROOT / "scripts" / "paper_dataset_evaluator_cli.py"
ASSESS_PDB_PAPER = REPO_ROOT / "scripts" / "assess_pdb_paper_split.py"
EXT_ASSESS_CLI = REPO_ROOT / "scripts" / "external_dataset_assessment_cli.py"
TRAINING_CLI = REPO_ROOT / "scripts" / "training_set_builder_cli.py"
EXPORT_PUBLIC_LIBRARY = REPO_ROOT / "scripts" / "export_public_library.py"
BUILD_LITE_BUNDLE = REPO_ROOT / "scripts" / "build_lightweight_preview_bundle_assets.py"
MATERIALIZE_CANONICAL = REPO_ROOT / "scripts" / "materialize_canonical_store.py"

TIER1_BUNDLE = REPO_ROOT / "artifacts" / "runtime" / "literature_hunt_tier1_source_bundle"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_int(markdown: str, label: str) -> int:
    import re

    match = re.search(rf"{re.escape(label)}:\s*`([\d,]+)`", markdown)
    if not match:
        raise ValueError(f"Could not find {label!r}")
    return int(match.group(1).replace(",", ""))


def extract_asset_size(markdown: str, asset_name: str) -> int:
    import re

    match = re.search(rf"`{re.escape(asset_name)}`.*?size `([\d,]+)` bytes", markdown, re.IGNORECASE | re.DOTALL)
    if not match:
        raise ValueError(f"Could not find asset size for {asset_name!r}")
    return int(match.group(1).replace(",", ""))


def human_bytes(value: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(amount)} {unit}"
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{value} B"


def size_detail(value: int) -> str:
    binary = human_bytes(value)
    decimal_gb = value / 1_000_000_000
    if decimal_gb >= 1000:
        return f"{value:,} bytes ({binary}; {decimal_gb / 1000:.2f} TB decimal)"
    if decimal_gb >= 1:
        return f"{value:,} bytes ({binary}; {decimal_gb:.1f} GB decimal)"
    decimal_mb = value / 1_000_000
    return f"{value:,} bytes ({binary}; {decimal_mb:.1f} MB decimal)"


def dir_stats(path: Path) -> tuple[int, int]:
    total = 0
    file_count = 0
    for root, _dirs, filenames in os.walk(path):
        for name in filenames:
            fp = Path(root) / name
            try:
                total += fp.stat().st_size
                file_count += 1
            except OSError:
                pass
    return total, file_count


def styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle("Title", parent=sample["Title"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=colors.HexColor("#102542")),
        "H1": ParagraphStyle("H1", parent=sample["Heading1"], fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=colors.HexColor("#102542"), spaceBefore=10, spaceAfter=6),
        "H2": ParagraphStyle("H2", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=11.2, leading=13.6, textColor=colors.HexColor("#1f2937"), spaceBefore=6, spaceAfter=4),
        "Body": ParagraphStyle("Body", parent=sample["BodyText"], fontName="Helvetica", fontSize=9.3, leading=12.3, textColor=colors.HexColor("#24303d"), spaceAfter=5),
        "Bullet": ParagraphStyle("Bullet", parent=sample["BodyText"], fontName="Helvetica", fontSize=9.1, leading=11.8, leftIndent=14, firstLineIndent=-8, bulletIndent=0, textColor=colors.HexColor("#24303d"), spaceAfter=2),
        "Caption": ParagraphStyle("Caption", parent=sample["BodyText"], fontName="Helvetica-Oblique", fontSize=8.1, leading=10.0, textColor=colors.HexColor("#4b5563")),
        "Small": ParagraphStyle("Small", parent=sample["BodyText"], fontName="Helvetica", fontSize=8.1, leading=10.0, textColor=colors.HexColor("#5b6472")),
    }


def para(text: str, style: ParagraphStyle) -> Paragraph:
    text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("`", "")
    )
    return Paragraph(text, style)


def add_box(ax: Any, x: float, y: float, w: float, h: float, text: str, fill: str) -> None:
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.03", linewidth=1.2, edgecolor="#334155", facecolor=fill)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=10, color="#111827", wrap=True)


def collect_facts() -> dict[str, Any]:
    warehouse_summary = load_json(WAREHOUSE_SUMMARY)
    source_coverage_md = read_text(SOURCE_COVERAGE)
    lite_contents = read_text(LITE_CONTENTS)
    storage_ledger = load_json(STORAGE_LEDGER_JSON)
    source_registry = load_json(SOURCE_REGISTRY)

    tracked_source_count = extract_int(source_coverage_md, "Source count")
    tracked_present_bytes = extract_int(source_coverage_md, "Total present bytes")
    preview_bundle_bytes = extract_asset_size(lite_contents, "proteosphere-lite.sqlite.zst")

    warehouse_bytes, warehouse_files = dir_stats(WAREHOUSE_ROOT)
    tier1_bundle_bytes, tier1_bundle_files = dir_stats(TIER1_BUNDLE)
    raw_bytes = storage_ledger["live_paths"]["repo_data_raw"]["byte_count"]
    raw_files = storage_ledger["live_paths"]["repo_data_raw"]["file_count"]
    mirrors_bytes = storage_ledger["live_paths"]["incoming_mirrors"]["byte_count"]
    mirrors_files = storage_ledger["live_paths"]["incoming_mirrors"]["file_count"]
    combined_raw_mirrors = raw_bytes + mirrors_bytes
    registry_records = list(source_registry.get("records") or [])
    registry_families = sorted({str(item.get("source_family") or "").strip() for item in registry_records if str(item.get("source_family") or "").strip()})
    promoted_records = [item for item in registry_records if str(item.get("integration_status") or "").strip().casefold() == "promoted"]

    return {
        "tracked_source_count": tracked_source_count,
        "tracked_present_bytes": tracked_present_bytes,
        "tracked_present_human": human_bytes(tracked_present_bytes),
        "tracked_present_detail": size_detail(tracked_present_bytes),
        "preview_bundle_bytes": preview_bundle_bytes,
        "preview_bundle_human": human_bytes(preview_bundle_bytes),
        "preview_bundle_detail": size_detail(preview_bundle_bytes),
        "warehouse_bytes": warehouse_bytes,
        "warehouse_human": human_bytes(warehouse_bytes),
        "warehouse_detail": size_detail(warehouse_bytes),
        "warehouse_files": warehouse_files,
        "tier1_bundle_bytes": tier1_bundle_bytes,
        "tier1_bundle_human": human_bytes(tier1_bundle_bytes),
        "tier1_bundle_detail": size_detail(tier1_bundle_bytes),
        "tier1_bundle_files": tier1_bundle_files,
        "warehouse_plus_tier1_bytes": warehouse_bytes + tier1_bundle_bytes,
        "warehouse_plus_tier1_human": human_bytes(warehouse_bytes + tier1_bundle_bytes),
        "warehouse_plus_tier1_detail": size_detail(warehouse_bytes + tier1_bundle_bytes),
        "raw_bytes": raw_bytes,
        "raw_human": human_bytes(raw_bytes),
        "raw_detail": size_detail(raw_bytes),
        "raw_files": raw_files,
        "mirrors_bytes": mirrors_bytes,
        "mirrors_human": human_bytes(mirrors_bytes),
        "mirrors_detail": size_detail(mirrors_bytes),
        "mirrors_files": mirrors_files,
        "combined_raw_mirrors_bytes": combined_raw_mirrors,
        "combined_raw_mirrors_human": human_bytes(combined_raw_mirrors),
        "combined_raw_mirrors_detail": size_detail(combined_raw_mirrors),
        "tracked_vs_warehouse_ratio": tracked_present_bytes / warehouse_bytes,
        "operator_vs_warehouse_ratio": combined_raw_mirrors / warehouse_bytes,
        "registry_record_count": len(registry_records),
        "registry_family_count": len(registry_families),
        "registry_promoted_count": len(promoted_records),
        "warehouse_summary": warehouse_summary,
    }


def generate_figures(facts: dict[str, Any]) -> dict[str, str]:
    paths: dict[str, str] = {}

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.axis("off")
    add_box(ax, 0.03, 0.60, 0.20, 0.20, "Pinned raw sources\nand mirrors", "#dbeafe")
    add_box(ax, 0.28, 0.60, 0.20, 0.20, "Canonicalization\nand normalization", "#e0f2fe")
    add_box(ax, 0.53, 0.60, 0.20, 0.20, "Compact warehouse\nmanifest + registry +\nDuckDB catalog", "#dcfce7")
    add_box(ax, 0.78, 0.60, 0.18, 0.20, "best_evidence\nreview surface", "#fef3c7")
    add_box(ax, 0.18, 0.18, 0.22, 0.18, "Paper reviewer\nsplit audit\npolicy mapping", "#fee2e2")
    add_box(ax, 0.48, 0.18, 0.20, 0.18, "Training-set builder\nleakage checks\ncohort planning", "#ede9fe")
    add_box(ax, 0.75, 0.18, 0.18, 0.18, "Optional deep\nforensics via\nraw fallback", "#fce7f3")
    for (x1, y1), (x2, y2) in [((0.23, 0.70), (0.28, 0.70)), ((0.48, 0.70), (0.53, 0.70)), ((0.73, 0.70), (0.78, 0.70)), ((0.60, 0.60), (0.58, 0.36)), ((0.82, 0.60), (0.82, 0.36))]:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=1.6, color="#475569"))
    ax.annotate("", xy=(0.29, 0.36), xytext=(0.80, 0.60), arrowprops=dict(arrowstyle="->", lw=1.4, color="#475569"))
    fig.suptitle("How ProteoSphere is organized", fontsize=16, fontweight="bold")
    fig.tight_layout()
    p = FIGURE_DIR / "architecture_stack.png"
    fig.savefig(p, dpi=220, bbox_inches="tight")
    plt.close(fig)
    paths["architecture"] = str(p)

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.axis("off")
    add_box(ax, 0.04, 0.62, 0.22, 0.20, "reference_library.py\nclaim views,\nconflict summaries,\nroute resolution", "#dbeafe")
    add_box(ax, 0.30, 0.62, 0.22, 0.20, "paper_evaluator/pipeline.py\nwarehouse snapshot,\nmember resolution,\nverdict assignment", "#dcfce7")
    add_box(ax, 0.56, 0.62, 0.22, 0.20, "runtime.py\nwarehouse lookup,\nmanifest-to-row conversion,\nsplit leakage summary", "#fef3c7")
    add_box(ax, 0.14, 0.18, 0.22, 0.18, "paper_dataset_evaluator_cli.py\npaper corpus -> report", "#fee2e2")
    add_box(ax, 0.40, 0.18, 0.22, 0.18, "assess_pdb_paper_split.py\nexplicit PDB split ->\noverlap report", "#ede9fe")
    add_box(ax, 0.66, 0.18, 0.22, 0.18, "external_dataset_assessment_cli.py\ntraining_set_builder_cli.py\noperator entrypoints", "#fce7f3")
    for (x1, y1), (x2, y2) in [((0.26, 0.72), (0.30, 0.72)), ((0.52, 0.72), (0.56, 0.72)), ((0.20, 0.62), (0.25, 0.36)), ((0.41, 0.62), (0.51, 0.36)), ((0.67, 0.62), (0.77, 0.36))]:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=1.5, color="#475569"))
    fig.suptitle("How the reviewer code is wired", fontsize=16, fontweight="bold")
    fig.tight_layout()
    p = FIGURE_DIR / "code_flow.png"
    fig.savefig(p, dpi=220, bbox_inches="tight")
    plt.close(fig)
    paths["code_flow"] = str(p)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    large_labels = ["Tracked sources", "Raw", "Mirrors", "Raw+mirrors", "Warehouse"]
    large_vals = [
        facts["tracked_present_bytes"] / (1024 ** 3),
        facts["raw_bytes"] / (1024 ** 3),
        facts["mirrors_bytes"] / (1024 ** 3),
        facts["combined_raw_mirrors_bytes"] / (1024 ** 3),
        facts["warehouse_bytes"] / (1024 ** 3),
    ]
    axes[0].bar(large_labels, large_vals, color=["#0ea5e9", "#3b82f6", "#6366f1", "#8b5cf6", "#10b981"])
    axes[0].set_title("Large-scale footprints")
    axes[0].set_ylabel("GB")
    axes[0].tick_params(axis="x", rotation=22)
    axes[0].grid(axis="y", linestyle="--", alpha=0.3)
    axes[0].spines["top"].set_visible(False)
    axes[0].spines["right"].set_visible(False)
    small_labels = ["Preview bundle", "Tier1 extras", "Warehouse", "Warehouse+Tier1"]
    small_vals = [
        facts["preview_bundle_bytes"],
        facts["tier1_bundle_bytes"],
        facts["warehouse_bytes"],
        facts["warehouse_plus_tier1_bytes"],
    ]
    axes[1].bar(small_labels, small_vals, color=["#94a3b8", "#f59e0b", "#10b981", "#059669"])
    axes[1].set_yscale("log")
    axes[1].set_title("Standalone package options")
    axes[1].set_ylabel("Bytes (log scale)")
    axes[1].tick_params(axis="x", rotation=22)
    axes[1].grid(axis="y", linestyle="--", alpha=0.3)
    axes[1].spines["top"].set_visible(False)
    axes[1].spines["right"].set_visible(False)
    fig.suptitle("Size economics", fontsize=16, fontweight="bold")
    fig.tight_layout()
    p = FIGURE_DIR / "size_comparison.png"
    fig.savefig(p, dpi=220, bbox_inches="tight")
    plt.close(fig)
    paths["sizes"] = str(p)

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.axis("off")
    add_box(ax, 0.05, 0.58, 0.24, 0.22, "Mode 1\nPreview bundle\nTiny demo artifact\nnot enough for full review", "#dbeafe")
    add_box(ax, 0.38, 0.58, 0.24, 0.22, "Mode 2\nAutonomous warehouse\noffline warehouse-first review", "#dcfce7")
    add_box(ax, 0.71, 0.58, 0.24, 0.22, "Mode 3\nMaintainer mode\nwarehouse + raw + mirrors\nfor rebuilds and deep recovery", "#fef3c7")
    add_box(ax, 0.12, 0.18, 0.22, 0.18, "Best for:\nexamples,\ndocs,\nsmoke tests", "#e0f2fe")
    add_box(ax, 0.45, 0.18, 0.22, 0.18, "Best for:\npaper review,\ntraining-set gating,\npolicy checks", "#d1fae5")
    add_box(ax, 0.76, 0.18, 0.16, 0.18, "Best for:\npromotion,\nrepair,\nforensics", "#fde68a")
    for (x1, y1), (x2, y2) in [((0.17, 0.58), (0.20, 0.36)), ((0.50, 0.58), (0.56, 0.36)), ((0.82, 0.58), (0.84, 0.36))]:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=1.5, color="#475569"))
    fig.suptitle("How open-source users would consume it", fontsize=16, fontweight="bold")
    fig.tight_layout()
    p = FIGURE_DIR / "open_source_modes.png"
    fig.savefig(p, dpi=220, bbox_inches="tight")
    plt.close(fig)
    paths["modes"] = str(p)
    return paths


def table(data: list[list[str]], col_widths: list[float]) -> LongTable:
    sample = getSampleStyleSheet()
    header_style = ParagraphStyle(
        "TableHeader",
        parent=sample["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=7.2,
        leading=8.8,
        textColor=colors.HexColor("#102542"),
    )
    body_style = ParagraphStyle(
        "TableBody",
        parent=sample["BodyText"],
        fontName="Helvetica",
        fontSize=7.2,
        leading=8.8,
        textColor=colors.HexColor("#24303d"),
    )

    wrapped: list[list[Any]] = []
    for row_index, row in enumerate(data):
        style = header_style if row_index == 0 else body_style
        wrapped_row: list[Any] = []
        for cell in row:
            if isinstance(cell, str):
                wrapped_row.append(para(cell, style))
            else:
                wrapped_row.append(cell)
        wrapped.append(wrapped_row)

    tbl = LongTable(wrapped, colWidths=[w * inch for w in col_widths], repeatRows=1)
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#102542")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    return tbl


def build_story(facts: dict[str, Any], figures: dict[str, str]) -> list[Any]:
    s = styles()
    story: list[Any] = []
    ws = facts["warehouse_summary"]

    def bullet(text: str) -> None:
        story.append(para(f"- {text}", s["Bullet"]))

    story.extend(
        [
            para("ProteoSphere Library And Dataset Reviewer Explainer", s["Title"]),
            Spacer(1, 0.08 * inch),
            para("A detailed plain-English guide to what the library is, how the reviewer code works, what was downloaded to build it, and what can realistically be shipped as a standalone open-source package.", s["Body"]),
            Spacer(1, 0.08 * inch),
            para("Direct answers first", s["H1"]),
        ]
    )
    bullet(f"If a user tried to download the currently tracked source content individually, the strict checked-in number is {facts['tracked_present_detail']}.")
    bullet(f"If you look at the current maintainer-grade raw plus mirror roots, the live combined footprint is {facts['combined_raw_mirrors_detail']}.")
    bullet(f"The current autonomous warehouse root is {facts['warehouse_detail']}.")
    bullet(f"So the warehouse is about {facts['tracked_vs_warehouse_ratio']:.1f}x smaller than the strict tracked source content, and about {facts['operator_vs_warehouse_ratio']:.1f}x smaller than the full live raw-plus-mirror maintainer estate.")
    bullet(f"The tiny `proteosphere-lite` preview bundle is only {facts['preview_bundle_detail']}, but it is a planning-only preview and is not large enough to replace the real autonomous warehouse.")
    bullet(f"If you want the current flagship paper-forensics extras too, the warehouse plus Tier 1 paper bundle is still only {facts['warehouse_plus_tier1_detail']}.")
    story.extend([Spacer(1, 0.08 * inch), Image(figures["sizes"], width=6.9 * inch, height=3.0 * inch), para("Figure 1. Size economics: unique tracked source content, live maintainer roots, and realistic standalone package options.", s["Caption"])])
    story.append(para("Glossary", s["H1"]))
    glossary_rows = [
        ["Term", "Meaning in plain English"],
        ["Warehouse", "The compact local library at D:\\ProteoSphere\\reference_library containing manifest files, control files, and a DuckDB catalog used by the reviewer."],
        ["Raw sources", "The original downloaded databases or exports, usually much larger and harder to work with directly."],
        ["Mirrors", "Maintainer-side duplicate or consolidated roots that preserve rebuild and forensic capability if live sources drift or vanish."],
        ["best_evidence", "The default logical read view that prefers the best current governing evidence instead of every raw or scraped claim at once."],
        ["Canonical store", "Normalized internal records keyed by stable identifiers while preserving source lineage."],
        ["Feature cache", "Small derived tables used to make filtering, grouping, and split checks fast."],
        ["Materialization", "Fetching or constructing a heavy asset only after the system has decided it is actually needed."],
        ["Leakage", "A train/test boundary failure where the model effectively sees the same biological object, family, or context on both sides."],
    ]
    story.append(table(glossary_rows, [1.2, 4.8]))

    story.append(para("1. What the library actually is", s["H1"]))
    story.append(para("ProteoSphere is not a copy of every original database. It is a compact, release-aware review surface that sits in front of the bigger raw estate. The design goal is to keep the information that is needed for identity resolution, provenance, leakage checks, similarity grouping, and policy decisions, while not forcing routine workflows to ship or re-open the heaviest assets every time.", s["Body"]))
    story.append(para("The master plan defines three layers: pinned source mirrors and local mirrors as the evidence layer, the lightweight reference library as the planning and governance layer, and on-demand training-example materialization as the heavy lane. In simple terms, the library answers 'what is this?', 'what is close to it?', 'what evidence supports it?', 'is it safe for train/test use?', and 'how would I build the full example if I chose it?'.", s["Body"]))
    story.append(para(f"The current warehouse summary says the default logical view is `{ws['default_view']}`, the source count is `{ws['source_count']}`, and the status is `{ws['status']}`. The control registry is broader than the hot warehouse summary surface: it currently tracks `{facts['registry_record_count']}` source records across `{facts['registry_family_count']}` source families, with `{facts['registry_promoted_count']}` marked promoted. Its materialized family counts include `{ws['family_counts']['proteins']:,}` proteins, `{ws['family_counts']['structure_units']:,}` structure units, `{ws['family_counts']['protein_ligand_edges']:,}` protein-ligand edges, `{ws['family_counts']['protein_protein_edges']:,}` protein-protein edges, `{ws['family_counts']['motif_domain_site_annotations']:,}` motif/domain/site annotations, and `{ws['family_counts']['pathway_roles']:,}` pathway-role rows.", s["Body"]))
    story.extend([Image(figures["architecture"], width=6.9 * inch, height=3.2 * inch), para("Figure 2. The ProteoSphere stack: sources and mirrors feed a normalized warehouse, which feeds the reviewer and training-set builder.", s["Caption"])])

    story.append(para("2. What source information went into it", s["H1"]))
    story.append(para("The easiest way to understand the source side is to group it by job rather than by database name. ProteoSphere uses some sources mainly for biological identity, some for structures, some for interaction evidence, some for annotation, and some for functional context.", s["Body"]))
    source_rows = [
        ["Source class", "Main sources", "What the warehouse keeps hot"],
        ["Identity spine", "UniProt, UniParc", "Accession-first protein identity, aliases, isoform lineage, sequence versioning, and cross-resource join keys."],
        ["Structure backbone", "RCSB/PDBe, SIFTS, AlphaFold DB, EMDB", "Structure-unit metadata, chain mappings, assembly context, quality summaries, and stable source identifiers."],
        ["Protein-ligand evidence", "BindingDB, BioLiP, PDBbind, ChEMBL, ChEBI", "Ligand identity, assay summaries, affinity metadata, bound-object context, and compact class or scaffold clues."],
        ["Protein-protein evidence", "BioGRID, IntAct, Complex Portal, SKEMPI", "Pair evidence, provenance, complex lineage, and interaction-context summaries."],
        ["Annotation and motif context", "InterPro, PROSITE, ELM, Pfam, DisProt, CATH", "Compact spans, domain and motif signatures, family clues, and disorder summaries."],
        ["Functional context", "Reactome, SABIO-RK, RNAcentral, STRING", "Pathway-role summaries, reaction context, and supporting biological grouping information."],
        ["Governance surfaces", "Catalog, splits, risk, reports, training examples", "The logic-bearing metadata that lets the reviewer and builder work offline."],
    ]
    story.append(table(source_rows, [1.1, 1.4, 3.5]))
    story.append(Spacer(1, 0.08 * inch))
    story.append(para("There are many promoted source families in the registry, but that does not mean every family is equally large or equally central. The key design pattern is that source-native truth is kept, but it is transformed into smaller planning and governance surfaces wherever possible.", s["Body"]))
    story.append(para("Two different source-size answers are both real and both useful. The strict checked-in coverage report says the currently tracked source content sums to about 302.5 GiB. That is the cleanest answer to 'what would I download if I fetched the known tracked sources one by one?'. The operational maintainer answer is larger: in the current workspace, the raw source tree plus incoming mirrors sum to about 3.12 TiB. That larger number reflects redundancy, rebuild lanes, and recovery surfaces that ordinary end users should not need to ship.", s["Body"]))

    story.append(para("3. How the library was built", s["H1"]))
    story.append(para("The build process is intentionally staged. First, source snapshots are pinned so the system is release-aware instead of relying on mutable live web pages. Second, canonicalization and normalization convert source-specific records into stable internal object classes such as proteins, variants, structure units, ligands, interaction edges, annotation spans, and provenance claims. Third, compact similarity and leakage-supporting metadata are computed so the reviewer can reason about identity, family, and context without reopening raw payloads.", s["Body"]))
    bullet("Pinned source mirrors and local mirrors preserve the original evidence boundary.")
    bullet("Canonicalization preserves source-native identifiers instead of flattening everything into one consensus row.")
    bullet("Planning index and feature-cache style layers keep the hot path small.")
    bullet("Heavy payloads such as raw mmCIF, map volumes, long assay tables, and full PSI-MI XML stay deferred until needed.")
    bullet("The warehouse manifest, source registry, and DuckDB catalog make the resulting library portable and queryable.")
    build_rows = [
        ["Build stage", "What happens"],
        ["Source pinning", "The project records the release boundary, file roots, and scope rules for each source so the system does not depend on mutable live portals."],
        ["Canonicalization", "materialize_canonical_store.py and the canonical pipelines promote pinned raw content into normalized proteins, variants, structures, ligands, edges, and provenance records."],
        ["Warehouse packaging", "The manifest, summary, control files, and DuckDB catalog are emitted into a portable warehouse root that can be copied and queried offline."],
        ["Preview export", "The lightweight preview scripts build a tiny schema-and-slice bundle for demos without pretending it is the full warehouse."],
        ["Reviewer outputs", "The paper evaluator and training-set CLIs sit on top of the warehouse and turn it into human-readable audit artifacts."],
    ]
    story.append(table(build_rows, [1.35, 4.65]))

    story.append(para("4. How the dataset reviewer code works", s["H1"]))
    story.append(para("The reviewer code is easier to understand if you follow it from the inside out. `reference_library.py` provides the low-level rules for reading claims, exposing conflicts, and resolving routes to materialized assets. `paper_evaluator/pipeline.py` loads a warehouse snapshot, reads a paper corpus, resolves explicit split members when possible, computes overlap and policy signals, and assigns reason codes and verdicts. `runtime.py` handles the training-set side: it finds the warehouse, converts manifest records into benchmark rows, and blocks splits that directly reuse proteins across train and test.", s["Body"]))
    story.extend([Image(figures["code_flow"], width=6.9 * inch, height=3.1 * inch), para("Figure 3. The reviewer code paths from core helper functions to CLI entrypoints.", s["Caption"])])
    code_rows = [
        ["Code surface", "What it does in plain English"],
        ["reference_library.py", "Reads claim views, reports conflicts between claim surfaces, and resolves local materialization routes through the source registry."],
        ["paper_evaluator/pipeline.py", "Loads a live warehouse snapshot, resolves paper members when possible, applies overlap and evidence checks, and assigns verdicts."],
        ["runtime.py", "Finds the warehouse root, converts manifest records into benchmark rows, and blocks direct protein overlap in train/test splits."],
        ["paper_dataset_evaluator_cli.py", "Runs the paper reviewer end to end and writes machine-readable plus Markdown-style outputs."],
        ["assess_pdb_paper_split.py", "Performs a deeper structured audit for explicit PDB-based train/test splits."],
        ["external_dataset_assessment_cli.py", "Operator entrypoint for broader external-dataset review tasks."],
        ["training_set_builder_cli.py", "Operator entrypoint for cohort compilation, split diagnostics, gating, and release-oriented training-set workflows."],
    ]
    story.append(table(code_rows, [1.55, 4.45]))
    story.append(PageBreak())

    story.append(para("5. Methodology: what the reviewer actually checks", s["H1"]))
    story.append(para("The reviewer is built around a small number of explicit questions. First, what split or external holdout does the paper claim to use? Second, can the members of that split be recovered or at least partially resolved? Third, once resolved, do train and test overlap directly, overlap at an accession-root or UniRef level, or retain shared partners/components? Fourth, did the paper apply any mitigation strategy such as cold splits, grouped splits, or source-family separation? Fifth, given all of that, what is the correct ProteoSphere treatment of the paper's benchmark claim?", s["Body"]))
    bullet("Claim recovery: parse the described train/test/external split and identify member type, such as PDB IDs or pair files.")
    bullet("Warehouse mapping: resolve the paper members into warehouse-supported entities when possible.")
    bullet("Overlap checking: direct identity, accession-root reuse, UniRef overlap, shared partner/component leakage, and source-family concerns.")
    bullet("Evidence grading: decide whether the split evidence is governing, candidate-only, audit-only, or unresolved.")
    bullet("Policy mapping: classify the split as accession-grouped, UniRef-grouped, paper-faithful external, or another project-recognized policy.")
    bullet("Verdicting: decide whether the paper is usable, usable with caveats, audit-only, blocked pending mapping, blocked pending cleanup, or unsafe for training.")
    story.append(para("Inside the paper-evaluator pipeline, the blocker reason codes are explicit: direct overlap, accession-root overlap, UniRef overlap, shared partner leakage, unresolved entity mapping, unresolved split membership, policy mismatch, and warehouse coverage gaps. That matters because the verdict is not a vague judgment. It is the consequence of named, inspectable reasons.", s["Body"]))
    blocker_rows = [
        ["Reason code", "Meaning and consequence"],
        ["DIRECT_OVERLAP", "Exactly the same resolved entities appear on both sides of the split, so the claimed boundary is not genuinely independent."],
        ["ACCESSION_ROOT_OVERLAP", "Different rows still reduce to the same accession-root identity, which means the split still reuses the same biology."],
        ["UNIREF_CLUSTER_OVERLAP", "Train and test land in the same similarity cluster, so the model may be tested on near-neighbors rather than novel cases."],
        ["SHARED_PARTNER_LEAKAGE", "The same interaction neighborhood or component context remains across the split, weakening external-style claims."],
        ["UNRESOLVED_ENTITY_MAPPING", "Some members cannot be mapped into warehouse entities, so the reviewer cannot claim more certainty than the identifiers support."],
        ["UNRESOLVED_SPLIT_MEMBERSHIP", "The paper does not expose enough roster detail to reconstruct the split deterministically."],
        ["POLICY_MISMATCH", "The paper's split may be paper-faithful but still non-canonical for ProteoSphere training policy."],
        ["WAREHOUSE_COVERAGE_GAP", "The warehouse is not yet rich enough to fully evaluate the claim; this is a library limitation, not automatically a paper failure."],
    ]
    story.append(table(blocker_rows, [1.55, 4.45]))
    policy_rows = [
        ["Resolved policy", "Interpretation"],
        ["accession_grouped", "A standard held-out or cross-validation style case that is acceptable only when the governed accession groups truly separate."],
        ["uniref_grouped", "A stricter family-aware policy used for unseen-protein or homology-guarded claims."],
        ["protein_ligand_component_grouped", "A component-aware policy for protein-ligand cases where either ligand or target pieces could otherwise leak."],
        ["paper_faithful_external", "A paper-specific external holdout that should be respected for audit purposes, but is not automatically a canonical training split."],
        ["unresolved_policy", "The split description does not map cleanly enough to a stable policy, so extra evidence or human review is needed."],
    ]
    story.append(table(policy_rows, [1.55, 4.45]))
    story.append(para("The training-set side uses the same philosophy. `runtime.py` first finds the warehouse catalog, then converts custom manifest records into benchmark rows, preserves accession and split metadata, and finally computes a leakage summary. That leakage summary is deliberately simple at the core: collect unique train and test accessions, compute exact overlap, and block the split if the overlap is non-zero. More advanced audits can then add accession-root, UniRef, and structure-level checks on top.", s["Body"]))

    story.append(para("6. Standalone open-source use: what can be shipped", s["H1"]))
    story.append(para("There are three realistic open-source packaging modes. The first is a tiny preview bundle for demonstration and schema inspection. The second is the real autonomous warehouse for offline warehouse-first review. The third is maintainer mode, where raw sources and mirrors are still retained for rebuilds, promotions, and deep paper-specific recovery.", s["Body"]))
    story.extend([Image(figures["modes"], width=6.9 * inch, height=3.1 * inch), para("Figure 4. Open-source consumption modes: tiny preview, autonomous warehouse, and maintainer mode.", s["Caption"])])
    package_rows = [
        ["Package mode", "Current size", "What it is good for", "What it loses"],
        ["Preview bundle (`proteosphere-lite`)", f"{facts['preview_bundle_bytes']:,} bytes ({facts['preview_bundle_human']})", "Demos, schema inspection, lightweight examples", "Not enough records or surfaces for the current full reviewer"],
        ["Autonomous warehouse root", f"{facts['warehouse_bytes']:,} bytes ({facts['warehouse_human']})", "Offline warehouse-first paper review, policy checks, dataset gating", "Still not fully evidence-equivalent to every raw artifact surface"],
        ["Autonomous warehouse + current Tier 1 paper bundle", f"{facts['warehouse_plus_tier1_bytes']:,} bytes ({facts['warehouse_plus_tier1_human']})", "Current warehouse-first review plus the flagship paper-forensics extras already recovered", "Still not a full replacement for all raw and mirror recovery lanes"],
        ["Tracked source content downloaded individually", f"{facts['tracked_present_bytes']:,} bytes ({facts['tracked_present_human']})", "A user-side rebuild of the currently tracked content without maintainers' extra mirror baggage", "Much larger than the autonomous warehouse and still requires building the condensed layer yourself"],
        ["Maintainer raw + mirrors", f"{facts['combined_raw_mirrors_bytes']:,} bytes ({facts['combined_raw_mirrors_human']})", "Rebuilds, repair, promotion of new surfaces, deep forensics, drift checking", "Too large for routine user distribution"],
    ]
    story.append(table(package_rows, [1.35, 1.0, 1.8, 1.85]))
    story.append(para("If the package is severed from live database links, the key question is whether the code can still resolve what it needs locally. For the warehouse-first path, the answer is yes: `runtime.py` explicitly looks for a local warehouse root, the paper evaluator opens the local manifest, validation file, registry, and DuckDB catalog, and `reference_library.py` resolves local claim views and local materialization routes. In other words, severing live links is acceptable for normal review as long as the autonomous warehouse is present. What breaks is only the deepest rebuild and recovery lane that still depends on unpromoted raw artifacts.", s["Body"]))

    story.append(para("7. So how small can the standalone library honestly be?", s["H1"]))
    story.append(para("Today, the truthful answer depends on what you mean by 'without losing any of the information we need'. If you mean 'without losing current warehouse-first review capability', the answer is the real warehouse root: about 74.2 GiB in the current environment. If you also want the current flagship paper forensic bundle, the answer is only slightly larger: roughly 74.5 GiB. If you mean 'without losing every last piece of raw evidence that the maintainers can currently reach during deep forensics', then the warehouse alone is not enough yet, because the equivalence memo explicitly says it is status-equivalent but not evidence-equivalent.", s["Body"]))
    story.append(para("This is the most important non-hand-wavy conclusion in the whole report. The library can already be severed from fragile live database links for normal warehouse-first use. But the tiny preview bundle is too small, and the current full raw-plus-mirror estate is still needed by maintainers for rebuilds and the deepest recovery cases. In other words: the practical standalone answer is already much smaller than the raw estate, but the mathematically smallest possible package is not yet the same thing as a full no-loss package.", s["Body"]))
    story.append(para("In concrete terms, the current autonomous warehouse root contains about 1,645 files and totals 74.2 GiB. The live raw tree contains about 271,607 files and the incoming mirrors add another 879 files. So the warehouse is not just smaller in bytes. It also collapses an enormous amount of operational sprawl into a much smaller, more stable object that users can actually copy, version, and point tools at.", s["Body"]))
    story.append(PageBreak())

    story.append(para("8. What value the mirrors add", s["H1"]))
    story.append(para("The mirrors do not mainly exist to make ordinary use faster. Their value is in resilience and depth. They let maintainers recover paper-specific artifacts that have not yet been promoted into the warehouse, rebuild surfaces when schemas change, check drift, rehydrate heavy evidence, and repair gaps when the warehouse is missing a roster, identifier bridge, or structure-level proof. For a normal open-source user, that is usually overkill. For a maintainer trying to make the reviewer stronger over time, it is essential.", s["Body"]))
    bullet("They preserve a fallback when live portals change or disappear.")
    bullet("They preserve raw or richer artifacts that are not yet fully promoted into warehouse-facing surfaces.")
    bullet("They let maintainers re-run canonicalization and preview-bundle generation.")
    bullet("They support deep paper-specific forensics, including exact split artifacts and structure-level reproductions.")
    bullet("They make it possible to improve the warehouse over time instead of freezing it permanently at its current surface.")

    story.append(para("9. The open-source user story in practice", s["H1"]))
    story.append(para("Once published as open source, the simplest user flow is: download the autonomous warehouse package, point `PROTEOSPHERE_WAREHOUSE_ROOT` at it, and run the paper or training-set assessment entrypoints locally. In that mode, the code is already designed to work without live database calls for warehouse-first workflows. `runtime.py` looks for the local warehouse catalog. The paper evaluator opens the local manifest, validation files, registry, and DuckDB catalog. The review helpers read local claim surfaces and local route records. That is the publishable value: the user gets the biological and provenance intelligence without having to assemble the original database stack themselves.", s["Body"]))
    usage_rows = [
        ["Typical user", "Downloads", "What they can do immediately"],
        ["Research user auditing a paper", "Autonomous warehouse root", "Run paper review and external-cohort assessment locally without rebuilding the full source stack."],
        ["Research user designing a new dataset", "Autonomous warehouse root", "Use the training-set builder and split diagnostics to check direct overlap and policy compatibility."],
        ["Power user reproducing flagship case studies", "Autonomous warehouse plus Tier 1 bundle", "Open the local PDFs, supplements, and proof artifacts that support the strongest literature findings."],
        ["Maintainer extending the system", "Warehouse plus raw and mirrors", "Promote new source slices, regenerate surfaces, and recover deeper evidence when the warehouse is not yet enough."],
    ]
    story.append(table(usage_rows, [1.4, 1.2, 3.4]))

    story.append(para("10. Current limits and the next honest shrink step", s["H1"]))
    story.append(para("The main limit is not that the warehouse is too big. The main limit is that some deep forensic detail still lives outside the default warehouse surfaces. The equivalence memo names those gaps clearly: richer paper-specific roster reconstruction, exact structure-level overlap reproductions such as the Struct2Graph 643-shared-PDB proof, and some identifier-bridge-heavy external split audits. The next real shrink step is therefore not to compress harder first. It is to promote more of that missing evidence into governed warehouse-facing surfaces. Once that promotion is done, the autonomous package can become smaller and more complete at the same time.", s["Body"]))
    story.append(para("So the order of work matters. First preserve truth. Then promote the evidence that still lives only in the broad collection. Then, once the promoted evidence is queryable inside the warehouse itself, shrink the external dependency surface further. That is a safer open-source strategy than stripping files first and hoping the missing detail never matters.", s["Body"]))

    story.append(para("Plain-language takeaway", s["H1"]))
    story.append(para("If someone downloaded the current sources one by one, the strict checked-in source-content number is about 302.5 GB. If they downloaded the current autonomous ProteoSphere warehouse instead, they would download about 74.2 GiB and get a review-ready, offline-capable, warehouse-first system rather than a pile of disconnected databases. If they were maintainers and wanted every current rebuild and forensic fallback lane too, they would keep the much larger multi-terabyte raw-plus-mirror estate. That is the whole benefit in one sentence: ProteoSphere turns a large, fragile, hard-to-use source stack into a much smaller, much more usable review surface, while still leaving a path to the deeper evidence when needed.", s["Body"]))
    return story


def write_markdown_companion(facts: dict[str, Any]) -> None:
    lines = [
        "# ProteoSphere Library And Reviewer Explainer",
        "",
        "## Key size answers",
        f"- Tracked source content: `{facts['tracked_present_bytes']}` bytes (`{facts['tracked_present_human']}`)",
        f"- Autonomous warehouse root: `{facts['warehouse_bytes']}` bytes (`{facts['warehouse_human']}`)",
        f"- Autonomous warehouse plus Tier 1 bundle: `{facts['warehouse_plus_tier1_bytes']}` bytes (`{facts['warehouse_plus_tier1_human']}`)",
        f"- Maintainer raw plus mirrors: `{facts['combined_raw_mirrors_bytes']}` bytes (`{facts['combined_raw_mirrors_human']}`)",
        "",
        "## Bottom line",
        "",
        "- The warehouse is already small enough to be a practical standalone offline review surface.",
        "- The preview bundle is far smaller still, but too incomplete for current full use.",
        "- The mirrors matter for rebuilds and deep forensics, not for most ordinary warehouse-first users.",
        "",
    ]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def render_preview(pdf_path: Path, image_path: Path) -> None:
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
    pix.save(str(image_path))
    doc.close()


def main() -> None:
    facts = collect_facts()
    figures = generate_figures(facts)
    write_markdown_companion(facts)
    story = build_story(facts, figures)
    doc = SimpleDocTemplate(str(PDF_PATH), pagesize=letter, leftMargin=0.72 * inch, rightMargin=0.72 * inch, topMargin=0.65 * inch, bottomMargin=0.65 * inch)
    doc.build(story)
    render_preview(PDF_PATH, PREVIEW_PATH)
    manifest = {
        "pdf": str(PDF_PATH),
        "preview": str(PREVIEW_PATH),
        "markdown_companion": str(REPORT_MD),
        "figures": figures,
        "fact_sources": [
            str(SOURCE_RELEASE_MATRIX),
            str(SOURCE_STORAGE_STRATEGY),
            str(LIGHTWEIGHT_MASTER_PLAN),
            str(LITE_SCHEMA),
            str(LITE_CONTENTS),
            str(SOURCE_COVERAGE),
            str(LIB_EQUIV),
            str(STORAGE_LEDGER),
            str(REFERENCE_LIBRARY_PY),
            str(RUNTIME_PY),
            str(PAPER_EVAL_PIPELINE),
            str(PAPER_EVAL_CLI),
            str(ASSESS_PDB_PAPER),
            str(EXT_ASSESS_CLI),
            str(TRAINING_CLI),
            str(EXPORT_PUBLIC_LIBRARY),
            str(BUILD_LITE_BUNDLE),
            str(MATERIALIZE_CANONICAL),
        ],
    }
    ASSET_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

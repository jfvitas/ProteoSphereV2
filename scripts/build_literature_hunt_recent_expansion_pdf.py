from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import fitz
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = REPO_ROOT / "artifacts" / "status" / "literature_hunt_recent_expansion.json"
OUTPUT_DIR = REPO_ROOT / "output" / "pdf"
TMP_DIR = REPO_ROOT / "tmp" / "pdfs" / "literature_hunt_recent_expansion"
PDF_PATH = OUTPUT_DIR / "proteosphere_literature_hunt_recent_expansion.pdf"
ASSET_MANIFEST = OUTPUT_DIR / "proteosphere_literature_hunt_recent_expansion.assets.json"
PREVIEW_PATH = TMP_DIR / "proteosphere_literature_hunt_recent_expansion.preview.page1.png"

STATUS_COLORS = {
    "tier1_hard_failure": "#9f1d35",
    "tier2_strong_supporting_case": "#1d4e89",
    "control_nonfailure": "#117733",
}


def load_report() -> dict[str, Any]:
    return json.loads(REPORT_JSON.read_text(encoding="utf-8"))


def sanitize(text: str) -> str:
    return str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")


def para(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(sanitize(text), style)


def build_styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle("Title", parent=sample["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=colors.HexColor("#14213d")),
        "H1": ParagraphStyle("H1", parent=sample["Heading1"], fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=colors.HexColor("#14213d")),
        "H2": ParagraphStyle("H2", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=colors.HexColor("#1f2937")),
        "Body": ParagraphStyle("Body", parent=sample["BodyText"], fontName="Helvetica", fontSize=9.6, leading=12.6, textColor=colors.HexColor("#24303d")),
        "Small": ParagraphStyle("Small", parent=sample["BodyText"], fontName="Helvetica", fontSize=8.3, leading=10.5, textColor=colors.HexColor("#5b6472")),
    }


def chart_tiers(report: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = report["summary"]["tier_counts"]
    labels = list(counts.keys())
    vals = [counts[k] for k in labels]
    cols = [STATUS_COLORS[k] for k in labels]
    fig, ax = plt.subplots(figsize=(7.4, 3.0))
    ax.bar(labels, vals, color=cols)
    ax.set_title("Recent-addendum tier counts")
    ax.set_ylabel("Paper count")
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def chart_years(report: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = report["summary"]["year_counts"]
    labels = list(counts.keys())
    vals = [counts[k] for k in labels]
    fig, ax = plt.subplots(figsize=(7.4, 2.9))
    ax.bar(labels, vals, color="#3a86ff")
    ax.set_title("Recent-addendum publication years")
    ax.set_ylabel("Paper count")
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def build_document(report: dict[str, Any]) -> tuple[list[Any], dict[str, Any]]:
    styles = build_styles()
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    tier_chart = chart_tiers(report, TMP_DIR / "recent_tier_counts.png")
    year_chart = chart_years(report, TMP_DIR / "recent_year_counts.png")

    tier1 = [row for row in report["papers"] if row["final_status"] == "tier1_hard_failure"]
    tier2 = [row for row in report["papers"] if row["final_status"] == "tier2_strong_supporting_case"]
    controls = [row for row in report["papers"] if row["final_status"] == "control_nonfailure"]
    best_examples = report["best_examples"]

    story: list[Any] = [
        para("ProteoSphere Literature Hunt Addendum", styles["Title"]),
        Spacer(1, 0.10 * inch),
        para("Recent-Publication Expansion", styles["H1"]),
        Spacer(1, 0.14 * inch),
        para(
            f"This addendum keeps the original deep review intact and adds {len(tier1)} new Tier 1 hard failures, {len(tier2)} Tier 2 supporting cases, and {len(controls)} new controls. The combined proof-backed Tier 1 count rises to {report['combined_summary']['tier_counts']['tier1_hard_failure']}, with the addendum concentrated in 2023–2026 publications.",
            styles["Body"],
        ),
        Spacer(1, 0.15 * inch),
        Image(str(tier_chart), width=6.8 * inch, height=2.7 * inch),
        Spacer(1, 0.10 * inch),
        Image(str(year_chart), width=6.8 * inch, height=2.6 * inch),
        Spacer(1, 0.14 * inch),
        para(
            "The strongest new proof is AttentionDTA, where the released code performs row-level random five-fold CV after shuffling full pair tables. The rest of the Tier 1 additions show that recent journal papers still inherit the DeepDTA warm-start family or the PDBbind core-set family without a mitigation strong enough to neutralize their known leakage channels.",
            styles["Body"],
        ),
        PageBreak(),
        para("Flagship New Tier 1 Additions", styles["H1"]),
        Spacer(1, 0.08 * inch),
    ]

    for row in best_examples:
        story.extend(
            [
                para(f"{row['title']} ({row['journal']}, {row['year']})", styles["H2"]),
                para(
                    f"DOI: {row['doi']}<br/>Benchmark family: {row['benchmark_family']}<br/>Why blocked: {row['contamination_findings']['notes'][0]}",
                    styles["Body"],
                ),
                para(f"Mitigation audit: {row['mitigation_audit_result']}", styles["Small"]),
                Spacer(1, 0.08 * inch),
            ]
        )

    story.append(PageBreak())
    story.append(para("All New Tier 1 Papers", styles["H1"]))
    story.append(Spacer(1, 0.08 * inch))
    rows = [["Paper", "Year", "Family", "Reason"]]
    for row in tier1:
        rows.append([row["paper_id"], str(row["year"]), row["benchmark_family"], row["contamination_findings"]["notes"][0]])
    table = Table(rows, colWidths=[1.55 * inch, 0.55 * inch, 1.45 * inch, 3.25 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.2),
                ("LEADING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.14 * inch))
    story.append(para("Tier 2 supporting papers were kept out of Tier 1 when the exact released split lineage was still one recovery step short. Controls were kept in the package to show that recent papers can and do ship colder or novelty-aware evaluation strategies.", styles["Body"]))

    story.append(PageBreak())
    story.append(para("Controls and Publication Framing", styles["H1"]))
    story.append(Spacer(1, 0.08 * inch))
    for row in controls:
        story.append(para(f"{row['title']} ({row['year']})", styles["H2"]))
        story.append(para(row["mitigation_audit_result"], styles["Body"]))
        story.append(Spacer(1, 0.05 * inch))
    story.append(Spacer(1, 0.12 * inch))
    story.append(
        para(
            "The safest publication story is now stronger than before: lead with the paper-specific failures, add the benchmark-family proofs, and then show that recent controls like DTA-OM and TEFDTA demonstrate what better benchmark practice looks like. That makes the analyzer look like a useful reviewer and design aid rather than a pure critique engine.",
            styles["Body"],
        )
    )

    assets = {"charts": [str(tier_chart), str(year_chart)], "embedded_images": []}
    return story, assets


def render_preview(pdf_path: Path, image_path: Path) -> None:
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
    image_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(image_path)
    doc.close()


def main() -> None:
    report = load_report()
    story, assets = build_document(report)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(PDF_PATH), pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch, topMargin=0.65 * inch, bottomMargin=0.65 * inch)
    doc.build(story)
    render_preview(PDF_PATH, PREVIEW_PATH)
    ASSET_MANIFEST.write_text(json.dumps({"pdf": str(PDF_PATH), "preview": str(PREVIEW_PATH), **assets}, indent=2) + "\n", encoding="utf-8")
    print(PDF_PATH)


if __name__ == "__main__":
    main()

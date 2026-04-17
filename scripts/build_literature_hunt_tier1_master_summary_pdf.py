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
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, Image


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = REPO_ROOT / "artifacts" / "status" / "literature_hunt_tier1_master_summary.json"
OUTPUT_DIR = REPO_ROOT / "output" / "pdf"
TMP_DIR = REPO_ROOT / "tmp" / "pdfs" / "literature_hunt_tier1_master_summary"
PDF_PATH = OUTPUT_DIR / "proteosphere_literature_hunt_tier1_master_summary.pdf"
ASSET_MANIFEST = OUTPUT_DIR / "proteosphere_literature_hunt_tier1_master_summary.assets.json"
PREVIEW_PATH = TMP_DIR / "proteosphere_literature_hunt_tier1_master_summary.preview.page1.png"


def load_report() -> dict[str, Any]:
    return json.loads(REPORT_JSON.read_text(encoding="utf-8"))


def sanitize(text: str) -> str:
    return str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")


def para(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(sanitize(text), style)


def styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle("Title", parent=sample["Title"], fontName="Helvetica-Bold", fontSize=21, leading=25, textColor=colors.HexColor("#14213d")),
        "H1": ParagraphStyle("H1", parent=sample["Heading1"], fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=colors.HexColor("#14213d")),
        "H2": ParagraphStyle("H2", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=colors.HexColor("#1f2937")),
        "Body": ParagraphStyle("Body", parent=sample["BodyText"], fontName="Helvetica", fontSize=9.4, leading=12.2, textColor=colors.HexColor("#24303d")),
        "Small": ParagraphStyle("Small", parent=sample["BodyText"], fontName="Helvetica", fontSize=8.2, leading=10.2, textColor=colors.HexColor("#5b6472")),
    }


def chart_counter(counter: dict[str, int], title: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    labels = list(counter.keys())
    values = [counter[k] for k in labels]
    fig, ax = plt.subplots(figsize=(7.6, 3.0))
    ax.bar(labels, values, color="#3a86ff")
    ax.set_title(title)
    ax.set_ylabel("Count")
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", rotation=24)
    fig.tight_layout()
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return path


def build_story(report: dict[str, Any]) -> tuple[list[Any], dict[str, Any]]:
    s = styles()
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    chart1 = chart_counter(report["summary"]["issue_family_counts"], "Tier 1 issue families", TMP_DIR / "issue_families.png")
    chart2 = chart_counter(report["summary"]["year_counts"], "Tier 1 publication years", TMP_DIR / "years.png")

    assess = report["review_paper_assessment"]
    papers = report["papers"]
    top_rows = papers[:10]

    story: list[Any] = [
        para("ProteoSphere Tier 1 Master Summary", s["Title"]),
        Spacer(1, 0.10 * inch),
        para("Confirmed Hard Failures, Detailed Explanations, and Review-Paper Assessment", s["H1"]),
        Spacer(1, 0.15 * inch),
        para(
            f"The current Tier 1 proof set contains {report['summary']['tier1_total']} confirmed hard failures, including {report['summary']['recent_2023plus_count']} papers from 2023 or later. This is now strong enough to support a serious review-paper narrative, provided the paper clearly separates direct leakage cases from inherited benchmark-family failures.",
            s["Body"],
        ),
        Spacer(1, 0.12 * inch),
        Image(str(chart1), width=6.8 * inch, height=2.7 * inch),
        Spacer(1, 0.08 * inch),
        Image(str(chart2), width=6.8 * inch, height=2.7 * inch),
        Spacer(1, 0.12 * inch),
        para(
            f"Quality: {assess['quality_score_10']}/10. Novelty: {assess['novelty_score_10']}/10. Publishability: {assess['publishability_score_10']}/10. Overall verdict: {assess['overall_verdict']}.",
            s["Body"],
        ),
        PageBreak(),
        para("Paper Assessment", s["H1"]),
        Spacer(1, 0.08 * inch),
    ]

    for heading, items in [
        ("Strengths", assess["strengths"]),
        ("Weaknesses", assess["weaknesses"]),
        ("Major risks", assess["major_risks"]),
        ("Highest-value next steps", assess["highest_value_next_steps"]),
    ]:
        story.append(para(heading, s["H2"]))
        for item in items:
            story.append(para(f"- {item}", s["Body"]))
        story.append(Spacer(1, 0.06 * inch))

    story.append(para("Best target venues", s["H2"]))
    for venue in assess["best_target_venues"]:
        story.append(para(f"- {venue}", s["Body"]))

    story.append(PageBreak())
    story.append(para("Tier 1 Overview", s["H1"]))
    story.append(Spacer(1, 0.08 * inch))
    rows = [["Paper", "Year", "Issue family", "Why it is Tier 1"]]
    for row in top_rows:
        rows.append([row["paper_id"], str(row["year"]), row["issue_family"], row["contamination_findings"]["notes"][0]])
    table = Table(rows, colWidths=[1.45 * inch, 0.55 * inch, 1.7 * inch, 3.1 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.1),
                ("LEADING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.12 * inch))
    story.append(para("The full paper-by-paper details continue on the following pages. The emphasis is on what exactly is wrong with the dataset design and why ProteoSphere would block or sharply downgrade the evaluation claim.", s["Body"]))

    for row in papers:
        story.append(PageBreak())
        story.append(para(row["title"], s["H1"]))
        story.append(Spacer(1, 0.05 * inch))
        story.append(para(f"{row['journal']} ({row['year']}) | DOI: {row['doi']}", s["Small"]))
        story.append(Spacer(1, 0.06 * inch))
        story.append(para(f"Benchmark family: {row['benchmark_family']}", s["Body"]))
        story.append(para(f"Issue family: {row['issue_family']}", s["Body"]))
        story.append(Spacer(1, 0.04 * inch))
        story.append(para("Claimed split", s["H2"]))
        story.append(para(row["claimed_split_description"], s["Body"]))
        story.append(para("Recovered evidence", s["H2"]))
        for item in row["recovered_split_evidence"][:3]:
            story.append(para(f"- {item}", s["Body"]))
        story.append(para("Why ProteoSphere flags it", s["H2"]))
        for item in row["contamination_findings"]["notes"]:
            story.append(para(f"- {item}", s["Body"]))
        story.append(para("Mitigation audit", s["H2"]))
        story.append(para(row["mitigation_audit_result"], s["Body"]))
        story.append(para("Recommended treatment", s["H2"]))
        story.append(para(row["recommended_proteosphere_treatment"], s["Body"]))

    assets = {"charts": [str(chart1), str(chart2)], "embedded_images": []}
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
    story, assets = build_story(report)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(PDF_PATH), pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch, topMargin=0.65 * inch, bottomMargin=0.65 * inch)
    doc.build(story)
    render_preview(PDF_PATH, PREVIEW_PATH)
    ASSET_MANIFEST.write_text(json.dumps({"pdf": str(PDF_PATH), "preview": str(PREVIEW_PATH), **assets}, indent=2) + "\n", encoding="utf-8")
    print(PDF_PATH)


if __name__ == "__main__":
    main()

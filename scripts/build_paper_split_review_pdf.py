from __future__ import annotations

import json
import re
import textwrap
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import fitz
import matplotlib.pyplot as plt
import requests
from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = REPO_ROOT / "artifacts" / "status" / "paper_split_list_evaluation.json"
OUTPUT_DIR = REPO_ROOT / "output" / "pdf"
TMP_DIR = REPO_ROOT / "tmp" / "pdfs" / "paper_split_review"
ASSET_DIR = TMP_DIR / "paper_assets"
PDF_PATH = OUTPUT_DIR / "proteosphere_paper_split_review.pdf"
MANIFEST_PATH = OUTPUT_DIR / "proteosphere_paper_split_review.assets.json"
PREVIEW_PATH = TMP_DIR / "proteosphere_paper_split_review.preview.page1.png"
STRUCT2GRAPH_OVERLAY = (
    REPO_ROOT
    / "artifacts"
    / "status"
    / "struct2graph_overlap"
    / "4EQ6_train_test_overlay.png"
)

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

PAPER_ORDER = [
    "zhang2012preppi",
    "sun2017sequence",
    "du2017deepppi",
    "hashemifar2018dppi",
    "chen2019siamese_rcnn",
    "sledzieski2021dscript",
    "szymborski2022rapppid",
    "baranwal2022struct2graph",
    "gainza2020masif",
    "dai2021geometric_interface",
    "xie2022interprotein_contacts",
    "tubiana2022scannet",
    "krapp2023pesto",
    "yugandhar2014affinity",
    "rodrigues2019mcsm_ppi2",
    "wang2020nettree",
    "zhang2020mutabind2",
    "zhou2024ddmut_ppi",
    "bryant2022af2_ppi",
    "gao2022af2complex",
]

GROUP_ORDER = [
    "ppi_prediction",
    "interface_prediction",
    "contact_prediction",
    "binding_site_prediction",
    "affinity_prediction",
    "mutation_effect_prediction",
    "complex_prediction",
]

GROUP_TITLES = {
    "ppi_prediction": "Predict Whether Two Proteins Interact",
    "interface_prediction": "Predict Where and How Proteins Bind",
    "contact_prediction": "Predict Where and How Proteins Bind",
    "binding_site_prediction": "Predict Where and How Proteins Bind",
    "affinity_prediction": "Predict Binding Strength or Mutation Effects",
    "mutation_effect_prediction": "Predict Binding Strength or Mutation Effects",
    "complex_prediction": "Predict the Bound Complex Directly",
}

PAPER_BLURBS: dict[str, dict[str, str]] = {
    "zhang2012preppi": {
        "citation": "Zhang et al. (2012), Nature",
        "summary": (
            "PrePPI combines structure modeling, homology, and functional evidence to "
            "score protein-protein interactions at genome scale in yeast and human."
        ),
        "reported_strength": (
            "The paper reports large high-confidence interaction catalogs and frames "
            "the method as competitive with high-throughput assays."
        ),
    },
    "sun2017sequence": {
        "citation": "Sun et al. (2017), BMC Bioinformatics",
        "summary": (
            "This model predicts binary PPIs from sequence-derived autocovariance "
            "features using stacked autoencoders."
        ),
        "reported_strength": (
            "The paper highlights very high cross-validation accuracy plus strong "
            "external-test performance."
        ),
    },
    "du2017deepppi": {
        "citation": "Du et al. (2017), Journal of Chemical Information and Modeling",
        "summary": (
            "DeepPPI learns pair representations for binary interaction prediction "
            "with a deep neural network over protein sequence features."
        ),
        "reported_strength": (
            "The paper emphasizes improved accuracy and precision over earlier "
            "sequence-based baselines."
        ),
    },
    "hashemifar2018dppi": {
        "citation": "Hashemifar et al. (2018), Bioinformatics",
        "summary": (
            "DPPI uses a Siamese-like convolutional architecture with sequence "
            "profiles, projection, and augmentation to model direct physical PPIs."
        ),
        "reported_strength": (
            "The paper reports strong precision, recall, and auPR performance on "
            "yeast benchmarks and argues that it generalizes to homodimers."
        ),
    },
    "chen2019siamese_rcnn": {
        "citation": "Chen et al. (2019), Bioinformatics",
        "summary": (
            "This Siamese residual RCNN targets multiple interaction tasks from raw "
            "sequence, including binary prediction, interaction type, and affinity."
        ),
        "reported_strength": (
            "The paper reports accuracy gains on SHS27k and SHS148k relative to prior "
            "sequence baselines."
        ),
    },
    "sledzieski2021dscript": {
        "citation": "Sledzieski et al. (2021), Cell Systems",
        "summary": (
            "D-SCRIPT is a sequence-only but structure-aware model that predicts a "
            "contact map and an interaction score, with an emphasis on cross-species transfer."
        ),
        "reported_strength": (
            "The paper highlights a human-trained model that improves downstream "
            "functional characterization in fly and shows contact-map agreement with structures."
        ),
    },
    "szymborski2022rapppid": {
        "citation": "Szymborski and Emad (2022), Bioinformatics",
        "summary": (
            "RAPPPID uses twin AWD-LSTM encoders and strong regularization to pursue "
            "more generalizable sequence-based PPI prediction."
        ),
        "reported_strength": (
            "The paper focuses on strict unseen-protein settings and claims stronger "
            "generalization than prior sequence models."
        ),
    },
    "baranwal2022struct2graph": {
        "citation": "Baranwal et al. (2022), BMC Bioinformatics",
        "summary": (
            "Struct2Graph treats proteins as structure graphs and applies graph "
            "attention to classify interactions and identify important residues."
        ),
        "reported_strength": (
            "The paper reports extremely high balanced and unbalanced accuracy and "
            "also positions the model as interpretable at the residue level."
        ),
    },
    "gainza2020masif": {
        "citation": "Gainza et al. (2020), Nature Methods",
        "summary": (
            "MaSIF learns geometric and chemical descriptors directly on protein "
            "surfaces for interface-site prediction and partner search."
        ),
        "reported_strength": (
            "The paper reports strong ROC AUC for site prediction and successful "
            "database-search ranking for example complexes."
        ),
    },
    "dai2021geometric_interface": {
        "citation": "Dai and Bailey-Kellogg (2021), Bioinformatics",
        "summary": (
            "This method uses point-cloud geometric deep learning to predict "
            "partner-specific interface regions on both proteins."
        ),
        "reported_strength": (
            "The paper positions the method as competitive or better than existing "
            "interface predictors across multiple benchmarks."
        ),
    },
    "xie2022interprotein_contacts": {
        "citation": "Xie and Xu (2022), Bioinformatics",
        "summary": (
            "GLINTER predicts residue-residue inter-protein contacts with a graph "
            "representation of structure plus a pretrained MSA language model."
        ),
        "reported_strength": (
            "The paper reports strong top-L/10 precision on CASP-CAPRI dimers and "
            "improved docking-decoy selection."
        ),
    },
    "tubiana2022scannet": {
        "citation": "Tubiana et al. (2022), Nature Methods",
        "summary": (
            "ScanNet predicts protein binding sites from local atomic and residue "
            "geometry while keeping the model interpretable."
        ),
        "reported_strength": (
            "The paper emphasizes performance on unseen folds and biological case "
            "studies such as SARS-CoV-2 spike epitopes."
        ),
    },
    "krapp2023pesto": {
        "citation": "Krapp et al. (2023), Nature Communications",
        "summary": (
            "PeSTo uses a rotation-equivariant transformer over atoms for interface "
            "prediction without hand-built physicochemical parameterization."
        ),
        "reported_strength": (
            "The paper reports improved median ROC AUC against strong baselines and "
            "strong behavior on an unbound PPDB5 example."
        ),
    },
    "yugandhar2014affinity": {
        "citation": "Yugandhar and Gromiha (2014), Bioinformatics",
        "summary": (
            "This paper predicts protein-protein binding affinity directly from "
            "sequence-derived descriptors using class-specific regression."
        ),
        "reported_strength": (
            "The paper reports strong jackknife correlations on a compact set of 135 complexes."
        ),
    },
    "rodrigues2019mcsm_ppi2": {
        "citation": "Rodrigues et al. (2019), Nucleic Acids Research",
        "summary": (
            "mCSM-PPI2 predicts mutation effects on PPIs using graph-based structural "
            "signatures, evolutionary context, and energetic/network terms."
        ),
        "reported_strength": (
            "The paper reports strong comparative performance and notes first-place "
            "ranking in CAPRI blind tests."
        ),
    },
    "wang2020nettree": {
        "citation": "Wang et al. (2020), Nature Machine Intelligence",
        "summary": (
            "NetTree combines persistent homology, convolutional networks, and "
            "gradient-boosting trees for mutation-driven PPI affinity change prediction."
        ),
        "reported_strength": (
            "The paper highlights improved correlation and RMSE on AB-Bind S645 and "
            "a blind homology subset."
        ),
    },
    "zhang2020mutabind2": {
        "citation": "Zhang et al. (2020), iScience",
        "summary": (
            "MutaBind2 predicts single and multiple mutation impacts on PPIs using a "
            "compact feature set tied to solvent interactions, conservation, and stability."
        ),
        "reported_strength": (
            "The paper claims improved performance, especially for affinity-increasing mutations."
        ),
    },
    "zhou2024ddmut_ppi": {
        "citation": "Zhou et al. (2024), Nucleic Acids Research",
        "summary": (
            "DDMut-PPI uses Siamese graph learning with ProtT5 embeddings and "
            "interaction-edge features for mutation effect prediction."
        ),
        "reported_strength": (
            "The paper reports strong Pearson correlation and RMSE on both single- and multiple-mutation sets."
        ),
    },
    "bryant2022af2_ppi": {
        "citation": "Bryant et al. (2022), Nature Communications",
        "summary": (
            "This work adapts AlphaFold2 for heterodimer prediction and uses pDockQ "
            "to rank models and distinguish plausible interactions."
        ),
        "reported_strength": (
            "The paper reports a much higher complex-prediction success rate than "
            "traditional docking baselines and a strong discrimination AUC."
        ),
    },
    "gao2022af2complex": {
        "citation": "Gao et al. (2022), Nature Communications",
        "summary": (
            "AF2Complex adapts AlphaFold2 to multimeric complexes without retraining "
            "and uses interface-based scores to rank candidate assemblies."
        ),
        "reported_strength": (
            "The paper highlights improved accuracy over docking and AF-Multimer in "
            "its large-scale E. coli evaluation."
        ),
    },
}


def sanitize(text: str) -> str:
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00a0": " ",
        "\u03b4": "delta",
        "\u0394": "Delta",
    }
    value = text
    for src, dst in replacements.items():
        value = value.replace(src, dst)
    return value


def load_report() -> dict[str, Any]:
    return json.loads(REPORT_JSON.read_text(encoding="utf-8"))


def europe_pmc_metadata(doi: str) -> dict[str, Any]:
    url = (
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        f'?query=DOI:"{doi}"&format=json&resultType=core'
    )
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=40)
    response.raise_for_status()
    results = response.json().get("resultList", {}).get("result", [])
    if not results:
        return {}
    return results[0]


def doi_page_metadata(doi_url: str) -> dict[str, Any]:
    response = requests.get(doi_url, headers=REQUEST_HEADERS, timeout=40, allow_redirects=True)
    result: dict[str, Any] = {
        "resolved_url": response.url,
        "status_code": response.status_code,
        "content_type": response.headers.get("content-type"),
    }
    if "text/html" not in (response.headers.get("content-type") or ""):
        return result
    text = response.text
    for pattern in (
        r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+(?:property|name)=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["image_url"] = match.group(1)
            break
    title_match = re.search(
        r'<meta[^>]+(?:name|property)=["\']citation_title["\'][^>]+content=["\']([^"\']+)["\']',
        text,
        re.IGNORECASE,
    )
    if title_match:
        result["title_meta"] = title_match.group(1)
    return result


def pdf_filename_from_pmc_xml(pmcid: str) -> str | None:
    url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=pmc&id={pmcid}&retmode=xml"
    )
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=40)
    response.raise_for_status()
    hrefs = re.findall(r'xlink:href="([^"]+\.pdf)"', response.text)
    if hrefs:
        return hrefs[0]
    return None


def create_fallback_card(path: Path, title: str, citation: str, doi: str, note: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = PILImage.new("RGB", (1400, 900), (248, 249, 251))
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("arial.ttf", 54)
        body_font = ImageFont.truetype("arial.ttf", 32)
        small_font = ImageFont.truetype("arial.ttf", 26)
    except OSError:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    draw.rounded_rectangle(
        (60, 60, 1340, 840),
        radius=36,
        fill=(255, 255, 255),
        outline=(210, 215, 225),
        width=3,
    )
    draw.text((100, 100), "Paper image fallback", font=small_font, fill=(30, 90, 150))
    wrapped_title = textwrap.fill(sanitize(title), width=34)
    draw.multiline_text((100, 160), wrapped_title, font=title_font, fill=(20, 24, 35), spacing=10)
    draw.multiline_text(
        (100, 430),
        textwrap.fill(sanitize(citation), width=48),
        font=body_font,
        fill=(60, 66, 80),
        spacing=8,
    )
    draw.multiline_text(
        (100, 560),
        textwrap.fill(sanitize(note), width=60),
        font=body_font,
        fill=(95, 102, 118),
        spacing=8,
    )
    draw.multiline_text((100, 760), sanitize(doi), font=small_font, fill=(30, 90, 150), spacing=4)
    image.save(path)


def render_pdf_first_page(pdf_path: Path, image_path: Path) -> bool:
    if not pdf_path.exists():
        return False
    doc = fitz.open(pdf_path)
    try:
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image_path.parent.mkdir(parents=True, exist_ok=True)
        pix.save(image_path)
        return True
    finally:
        doc.close()


def fetch_asset(row: dict[str, Any]) -> dict[str, Any]:
    asset: dict[str, Any] = {"paper_id": row["paper_id"], "image_kind": "none"}
    paper_id = row["paper_id"]
    doi_url = row["doi"]
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    metadata = europe_pmc_metadata(doi_url.replace("https://doi.org/", ""))
    page_meta = doi_page_metadata(doi_url)
    asset["europe_pmc"] = {
        "pmcid": metadata.get("pmcid"),
        "pmid": metadata.get("pmid"),
        "abstract": sanitize(re.sub(r"<[^>]+>", " ", metadata.get("abstractText", ""))).strip(),
        "title": sanitize(metadata.get("title") or ""),
        "is_open_access": metadata.get("isOpenAccess"),
        "has_pdf": metadata.get("hasPDF"),
    }
    asset["landing_page"] = page_meta

    image_url = page_meta.get("image_url")
    if image_url:
        ext = Path(image_url.split("?")[0]).suffix or ".png"
        image_path = ASSET_DIR / f"{paper_id}{ext}"
        if not image_path.exists():
            response = requests.get(image_url, headers=REQUEST_HEADERS, timeout=40)
            response.raise_for_status()
            image_path.write_bytes(response.content)
        asset["image_path"] = str(image_path)
        asset["image_kind"] = "publisher_figure"
        asset["image_source"] = image_url
        return asset

    pmcid = metadata.get("pmcid")
    if pmcid:
        pdf_name = pdf_filename_from_pmc_xml(pmcid)
        if pdf_name:
            pdf_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/{pdf_name}"
            pdf_path = ASSET_DIR / f"{paper_id}.pdf"
            if not pdf_path.exists():
                response = requests.get(pdf_url, headers=REQUEST_HEADERS, timeout=40, allow_redirects=True)
                if response.headers.get("content-type", "").lower().startswith("application/pdf"):
                    pdf_path.write_bytes(response.content)
            preview_path = ASSET_DIR / f"{paper_id}_page1.png"
            if render_pdf_first_page(pdf_path, preview_path):
                asset["image_path"] = str(preview_path)
                asset["image_kind"] = "pmc_pdf_page"
                asset["image_source"] = pdf_url
                return asset

    fallback_path = ASSET_DIR / f"{paper_id}_fallback.png"
    blurbs = PAPER_BLURBS.get(paper_id, {})
    create_fallback_card(
        fallback_path,
        row["title"],
        blurbs.get("citation", "Paper metadata"),
        row["doi"],
        (
            "Automatic paper-figure retrieval was blocked by publisher access controls, "
            "so this report uses a generated citation card instead."
        ),
    )
    asset["image_path"] = str(fallback_path)
    asset["image_kind"] = "generated_fallback"
    asset["image_source"] = page_meta.get("resolved_url") or row["doi"]
    return asset


def build_assets(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    manifest: dict[str, dict[str, Any]] = {}
    for row in rows:
        manifest[row["paper_id"]] = fetch_asset(row)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def create_verdict_chart(report: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = report["summary"]["verdict_counts"]
    labels = list(counts)
    values = [counts[label] for label in labels]
    fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=220)
    palette = ["#4464ad", "#4f9d69", "#d88c1d", "#c94c4c"]
    bars = ax.bar(range(len(labels)), values, color=palette[: len(labels)])
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(
        [label.replace(" because required evidence is missing", "") for label in labels],
        rotation=15,
        ha="right",
    )
    ax.set_ylabel("Paper count")
    ax.set_title("ProteoSphere verdict distribution across the 20-paper list")
    for bar, value in zip(bars, values, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.05,
            str(value),
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def create_issue_chart(rows: list[dict[str, Any]], path: Path) -> Path:
    issue_counts = Counter()
    for row in rows:
        blockers = " ".join(row.get("blockers") or []).lower()
        warnings = " ".join(row.get("warnings") or []).lower()
        if "roster" in blockers:
            issue_counts["missing roster"] += 1
        if "identifier" in blockers or "ensembl" in blockers or "flybase" in blockers:
            issue_counts["identifier bridge missing"] += 1
        if "split-construction logic" in blockers or row["verdict"] == "misleading / leakage-prone":
            issue_counts["split leakage"] += 1
        if "non-public" in warnings or "non-redistributable" in warnings:
            issue_counts["license / governance caution"] += 1
    labels = list(issue_counts)
    values = [issue_counts[label] for label in labels]
    fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=220)
    ax.barh(range(len(labels)), values, color="#6c8ebf")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_xlabel("Paper count")
    ax.set_title("Cross-cutting issues surfaced by the dataset review")
    for idx, value in enumerate(values):
        ax.text(value + 0.05, idx, str(value), va="center", fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17233b"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=colors.HexColor("#17324d"),
            spaceBefore=8,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#224d75"),
            spaceBefore=4,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodySmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=12,
            textColor=colors.HexColor("#1f2430"),
            alignment=TA_LEFT,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#1f2430"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="Label",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.4,
            leading=11,
            textColor=colors.HexColor("#17324d"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="Caption",
            parent=styles["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=10.5,
            textColor=colors.HexColor("#5f6775"),
            alignment=TA_CENTER,
        )
    )
    return styles


def make_bullet_list(items: list[str], style: ParagraphStyle) -> list[Paragraph]:
    return [Paragraph(f"• {sanitize(item)}", style) for item in items if item]


def consequence_text(row: dict[str, Any]) -> str:
    verdict = row["verdict"]
    if verdict == "misleading / leakage-prone":
        return (
            "Consequence: headline metrics can be inflated by reuse of the same proteins, "
            "structures, or partner context across partitions. A reader may believe the "
            "model generalizes when it is partly re-seeing the benchmark."
        )
    if verdict == "audit-useful but non-canonical":
        return (
            "Consequence: the split is still useful as a historical comparison lane, but "
            "it is not strong enough to serve as governing evidence for training or release claims."
        )
    return (
        "Consequence: without roster-level or identifier-level evidence, the review cannot "
        "falsify leakage or prove independence, so any benchmark claim stays provisional."
    )


def reviewer_value_text(row: dict[str, Any]) -> str:
    blockers = " ".join(row.get("blockers") or []).lower()
    if "ensembl" in blockers or "flybase" in blockers or "identifier" in blockers:
        return (
            "What the reviewer catches: the split may be published and reproducible, yet still "
            "be unusable for governed evaluation until identifiers bridge into the warehouse."
        )
    if row["verdict"] == "misleading / leakage-prone":
        return (
            "What the reviewer catches: pair-level or example-level partitioning can look "
            "rigorous in prose while still leaking the same biological entities across the split."
        )
    return (
        "What the reviewer catches: a paper can be influential and still lack enough released "
        "membership evidence to support fair, canonical benchmarking."
    )


def evidence_surface_text(row: dict[str, Any]) -> str:
    supplemental = row.get("supplemental_evidence") or {}
    if supplemental:
        return sanitize(supplemental.get("summary") or "Supplemental release evidence was used.")
    return (
        "This assessment is driven by the condensed warehouse, its runtime validation surfaces, "
        "and split-policy logic in Model Studio. No paper-specific roster was recovered here."
    )


def task_group_display(group: str) -> str:
    return GROUP_TITLES.get(group, group.replace("_", " ").title())


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(sanitize(text), style)


def callout_box(title: str, body: str, styles) -> Table:
    table = Table(
        [[Paragraph(f"<b>{sanitize(title)}</b><br/>{sanitize(body)}", styles["BodySmall"])]],
        colWidths=[6.9 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef4fb")),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#99b7db")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def build_story(report: dict[str, Any], assets: dict[str, dict[str, Any]]) -> list[Any]:
    styles = build_styles()
    rows = {row["paper_id"]: row for row in report["papers"]}
    ordered_rows = [rows[paper_id] for paper_id in PAPER_ORDER]

    verdict_chart = create_verdict_chart(report, TMP_DIR / "verdict_chart.png")
    issue_chart = create_issue_chart(ordered_rows, TMP_DIR / "issue_chart.png")
    story: list[Any] = []

    story.extend(
        [
            Spacer(1, 0.3 * inch),
            paragraph("ProteoSphere Dataset Review of 20 Protein Interaction Papers", styles["CoverTitle"]),
            paragraph(
                (
                    "A warehouse-first audit of train/test claims, leakage risk, identifier "
                    "resolvability, and split admissibility under ProteoSphere logic"
                ),
                styles["Body"],
            ),
            Spacer(1, 0.18 * inch),
            callout_box(
                "Why this report exists",
                (
                    "The goal is not to downgrade influential papers. It is to show that a modern "
                    "dataset reviewer can separate historical usefulness from canonical admissibility, "
                    "and can do so with explicit evidence instead of intuition."
                ),
                styles,
            ),
            Spacer(1, 0.18 * inch),
            paragraph(
                (
                    "Primary warehouse root: D:\\ProteoSphere\\reference_library. Default logical "
                    "view: best_evidence. Normal evaluation remained warehouse-first; supplemental "
                    "paper release artifacts were used only to strengthen provenance where the warehouse "
                    "lacked paper-specific roster membership."
                ),
                styles["BodySmall"],
            ),
            Spacer(1, 0.22 * inch),
            Image(str(verdict_chart), width=6.9 * inch, height=3.7 * inch),
            Spacer(1, 0.08 * inch),
            paragraph(
                "Figure 1. Verdict distribution across the 20-paper review set.",
                styles["Caption"],
            ),
            Spacer(1, 0.12 * inch),
            Image(str(issue_chart), width=6.9 * inch, height=3.7 * inch),
            Spacer(1, 0.08 * inch),
            paragraph(
                "Figure 2. Cross-cutting reasons a dataset reviewer changes the interpretation of paper splits.",
                styles["Caption"],
            ),
            PageBreak(),
            paragraph("Executive Summary", styles["SectionTitle"]),
        ]
    )

    summary_points = [
        "Only 3 of 20 papers were strong negative examples in the current pass, but none were faithful and acceptable as-is under ProteoSphere's governing logic.",
        "The most common problem was not obvious leakage. It was missing paper roster evidence: the condensed warehouse often cannot reconstruct the paper's exact train/test membership from best_evidence alone.",
        "Recovered supplements changed the interpretation of D-SCRIPT and RAPPPID from 'roster absent' to 'published split found but blocked on identifier bridging'.",
        "Struct2Graph became a stronger failure case after reading the released split code: the repository performs pair-level shuffling and slicing, which directly permits train/test structure reuse.",
        "A dataset reviewer creates value by forcing these cases into distinct buckets: governing, audit-only, blocked-pending-mapping, or unsafe-for-training.",
    ]
    story.extend(make_bullet_list(summary_points, styles["Body"]))
    story.extend(
        [
            Spacer(1, 0.14 * inch),
            paragraph("ProteoSphere Review Criteria", styles["SubTitle"]),
        ]
    )
    criteria_points = [
        "Direct overlap: the same accession, structure, or benchmark entity appears on both sides of the split.",
        "Accession-root overlap: isoform or accession-family variants leak even when exact identifiers differ.",
        "UniRef overlap: train and test are not separated at the sequence-similarity cluster level.",
        "Shared partner or component leakage: one side reuses binding partners or complex components from the other side.",
        "Source-family and governed-eligibility checks: the split may remain audit-only if provenance or licensing does not support canonical release use.",
    ]
    story.extend(make_bullet_list(criteria_points, styles["Body"]))
    story.extend(
        [
            Spacer(1, 0.16 * inch),
            callout_box(
                "Case study: why example-level splitting fails",
                (
                    "For Struct2Graph, a representative reproduction of the released split logic "
                    "created 643 shared PDB IDs across reproduced train and test. The same exact "
                    "structure, 4EQ6, appears 78 times in reproduced train and 9 times in reproduced test."
                ),
                styles,
            ),
            Spacer(1, 0.12 * inch),
            Image(str(STRUCT2GRAPH_OVERLAY), width=6.9 * inch, height=4.9 * inch),
            Spacer(1, 0.08 * inch),
            paragraph(
                (
                    "Figure 3. PyMOL overlay of 4EQ6 reused across reproduced Struct2Graph train and test "
                    "partitions. The exact match is the point: the split mechanism itself allows direct structure reuse."
                ),
                styles["Caption"],
            ),
            PageBreak(),
        ]
    )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ordered_rows:
        grouped[row["task_group"]].append(row)

    for group in GROUP_ORDER:
        section_rows = grouped.get(group)
        if not section_rows:
            continue
        story.append(paragraph(task_group_display(group), styles["SectionTitle"]))
        story.append(Spacer(1, 0.06 * inch))
        for row in section_rows:
            paper_id = row["paper_id"]
            blurbs = PAPER_BLURBS.get(paper_id, {})
            asset = assets[paper_id]
            image = Image(asset["image_path"], width=2.35 * inch, height=1.7 * inch)
            caption = paragraph(
                (
                    f"Paper visual: {asset['image_kind'].replace('_', ' ')}. "
                    f"Source: {sanitize(asset.get('image_source') or row['doi'])}"
                ),
                styles["Caption"],
            )
            left_col = [
                paragraph(f"{row['title']}", styles["SubTitle"]),
                paragraph(blurbs.get("citation", row["doi"]), styles["BodySmall"]),
                Spacer(1, 0.03 * inch),
                paragraph(blurbs.get("summary", "No summary available."), styles["Body"]),
                Spacer(1, 0.04 * inch),
                paragraph(blurbs.get("reported_strength", ""), styles["BodySmall"]),
            ]
            top_table = Table(
                [[left_col, [image, Spacer(1, 0.05 * inch), caption]]],
                colWidths=[4.85 * inch, 2.05 * inch],
            )
            top_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )

            verdict_line = (
                f"ProteoSphere verdict: {row['verdict']} | "
                f"Resolved split policy: {row['resolved_split_policy']['policy']}"
            )
            key_findings = [
                f"Claimed split: {row['claimed_split_description']}",
                f"Evidence surface: {evidence_surface_text(row)}",
                f"Leakage readout: {' '.join(row['leakage_findings']['notes'][:2])}",
                consequence_text(row),
                reviewer_value_text(row),
            ]
            blockers = row.get("blockers") or []
            warnings = row.get("warnings") or []
            if blockers:
                key_findings.append("Blockers: " + "; ".join(blockers[:3]))
            if warnings:
                key_findings.append("Warnings: " + "; ".join(warnings[:2]))
            if row.get("supplemental_evidence"):
                details = row["supplemental_evidence"].get("details") or []
                if details:
                    key_findings.append("Supplemental clarification: " + " ".join(details[:2]))

            story.extend(
                [
                    KeepTogether(
                        [
                            top_table,
                            Spacer(1, 0.06 * inch),
                            paragraph(verdict_line, styles["Label"]),
                            Spacer(1, 0.04 * inch),
                        ]
                    )
                ]
            )
            story.extend(make_bullet_list(key_findings, styles["Body"]))
            story.extend(
                [
                    Spacer(1, 0.08 * inch),
                    callout_box(
                        "Recommended canonical treatment",
                        row["recommended_canonical_treatment"],
                        styles,
                    ),
                    Spacer(1, 0.12 * inch),
                    HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#d6dbe4")),
                    Spacer(1, 0.12 * inch),
                ]
            )
        story.append(PageBreak())

    story.append(paragraph("Closing Interpretation", styles["SectionTitle"]))
    closing_points = [
        "The central benefit of a dataset reviewer is not only detecting obvious leakage. It is giving each published split the right status: faithful, audit-only, leakage-prone, or blocked by missing evidence.",
        "That status matters for downstream science. It changes whether a benchmark can support model selection, claims of external validity, or release-governing comparisons.",
        "In this 20-paper set, the reviewer added value in three distinct ways: by catching example-level leakage, by recognizing when a released split is still identifier-blocked, and by refusing to guess where the evidence surface is incomplete.",
        "A review paper built around this idea can argue that dataset review is now a first-class methodological layer, not just a hygiene step after modeling is finished.",
    ]
    story.extend(make_bullet_list(closing_points, styles["Body"]))
    story.extend([Spacer(1, 0.16 * inch), paragraph("Primary Sources", styles["SubTitle"])])
    for row in ordered_rows:
        story.append(
            paragraph(
                f"{row['title']} - {row['doi']}",
                styles["BodySmall"],
            )
        )
    return story


def add_page_number(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#5f6775"))
    canvas.drawRightString(7.4 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.drawString(0.75 * inch, 0.45 * inch, "ProteoSphere paper split review")
    canvas.restoreState()


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    report = load_report()
    rows = report["papers"]
    ordered_rows = [next(row for row in rows if row["paper_id"] == paper_id) for paper_id in PAPER_ORDER]
    assets = build_assets(ordered_rows)
    story = build_story(report, assets)
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.6 * inch,
        title="ProteoSphere Dataset Review of 20 Protein Interaction Papers",
        author="Codex for ProteoSphere",
    )
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    render_pdf_first_page(PDF_PATH, PREVIEW_PATH)
    print(f"Wrote {PDF_PATH}")
    print(f"Wrote {MANIFEST_PATH}")
    print(f"Wrote {PREVIEW_PATH}")


if __name__ == "__main__":
    main()

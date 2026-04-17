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
REPORT_JSON = REPO_ROOT / "artifacts" / "status" / "paper_split_audit_friendly_evaluation.json"
OUTPUT_DIR = REPO_ROOT / "output" / "pdf"
TMP_DIR = REPO_ROOT / "tmp" / "pdfs" / "audit_friendly_review"
ASSET_DIR = TMP_DIR / "paper_assets"
PDF_PATH = OUTPUT_DIR / "proteosphere_audit_friendly_paper_review.pdf"
MANIFEST_PATH = OUTPUT_DIR / "proteosphere_audit_friendly_paper_review.assets.json"
PREVIEW_PATH = TMP_DIR / "proteosphere_audit_friendly_paper_review.preview.page1.png"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

PAPER_ORDER = [
    "szymborski2022rapppid",
    "sledzieski2021dscript",
    "topsy_turvy2022",
    "tt3d2023",
    "ppitrans2024",
    "tuna2024",
    "plm_interact2025",
    "graphppis2021",
    "equippis2023",
    "agat_ppis2023",
    "ghgpr_ppis2023",
    "gact_ppis2024",
    "gte_ppis2025",
    "asce_ppis2025",
    "egcppis2025",
    "mvso_ppis2025",
    "hssppi2025",
    "mippis2024",
    "seq_insite2024",
    "deepppisp2019",
]

GROUP_ORDER = [
    "ppi_prediction",
    "binding_site_prediction",
]

GROUP_TITLES = {
    "ppi_prediction": "Predict Whether Two Proteins Interact",
    "binding_site_prediction": "Predict Protein-Protein Interface Sites",
}

PAPER_BLURBS: dict[str, dict[str, str]] = {
    "szymborski2022rapppid": {
        "citation": "Szymborski and Emad (2022), Bioinformatics",
        "summary": (
            "RAPPPID uses twin AWD-LSTM encoders with aggressive regularization and "
            "publishes strict C1/C2/C3 train, validation, and test splits designed to reduce leakage."
        ),
        "reported_strength": (
            "The paper emphasizes performance on unseen-protein conditions and releases "
            "the comparative split artifacts through Zenodo."
        ),
    },
    "sledzieski2021dscript": {
        "citation": "Sledzieski et al. (2021), Cell Systems",
        "summary": (
            "D-SCRIPT is a sequence-only but structure-aware PPI model that predicts a "
            "contact map and interaction score and publishes human plus held-out species benchmarks."
        ),
        "reported_strength": (
            "The paper reports improved functional characterization in fly and exposes "
            "concrete train/test pair lists through the official repo and docs."
        ),
    },
    "topsy_turvy2022": {
        "citation": "Devkota et al. (2022), Bioinformatics",
        "summary": (
            "Topsy-Turvy combines local and global sequence context for pair-level PPI "
            "prediction and trains from explicit positive and negative train/test edgelists."
        ),
        "reported_strength": (
            "The repository exposes the expected split-file interfaces directly, making "
            "the benchmark auditable even though it largely inherits established source families."
        ),
    },
    "tt3d2023": {
        "citation": "Sledzieski et al. (2023), Bioinformatics",
        "summary": (
            "TT3D extends Topsy-Turvy with Foldseek 3Di sequence information and is evaluated on the "
            "D-SCRIPT benchmark family rather than a new independently released split."
        ),
        "reported_strength": (
            "The paper reports clear gains over the earlier model, especially on cross-species settings."
        ),
    },
    "ppitrans2024": {
        "citation": "Wu et al. (2024), IEEE/ACM TCBB",
        "summary": (
            "PPITrans is a transformer-based pair predictor built on pretrained protein "
            "language model features and explicitly downloads the D-SCRIPT benchmark into the repo layout."
        ),
        "reported_strength": (
            "The paper reports stronger transfer to unseen-species PPIs than earlier sequence baselines."
        ),
    },
    "tuna2024": {
        "citation": "Wang et al. (2024), Briefings in Bioinformatics",
        "summary": (
            "TUnA is an uncertainty-aware transformer for sequence-based PPI prediction "
            "that uses ESM-2 embeddings and publishes processing flows for cross-species and Bernett benchmarks."
        ),
        "reported_strength": (
            "The paper reports state-of-the-art performance and lower false positives on unseen sequences."
        ),
    },
    "plm_interact2025": {
        "citation": "Li et al. (2025), Nature Communications",
        "summary": (
            "PLM-interact uses cross-attention over pretrained protein language model "
            "representations and evaluates on the Bernett leakage-minimized benchmark plus held-out species tests."
        ),
        "reported_strength": (
            "The paper reports strong yeast, E. coli, and Bernett benchmark performance and publishes source-data links."
        ),
    },
    "graphppis2021": {
        "citation": "Wang et al. (2021), Bioinformatics",
        "summary": (
            "GraphPPIS is the anchor structure-based PPIS benchmark paper for the widely reused "
            "Train_335/Test_60/Test_315/UBtest_31 family."
        ),
        "reported_strength": (
            "The paper reports competitive MCC, AUROC, and AUPRC and effectively defines the later PPIS comparison lane."
        ),
    },
    "equippis2023": {
        "citation": "Qiao et al. (2023), PLOS Computational Biology",
        "summary": (
            "EquiPPIS is a geometrically equivariant PPIS model that explicitly follows the GraphPPIS split family."
        ),
        "reported_strength": (
            "The paper reports strong improvements, including on AlphaFold2-derived structures."
        ),
    },
    "agat_ppis2023": {
        "citation": "Wang et al. (2023), Briefings in Bioinformatics",
        "summary": (
            "AGAT-PPIS augments graph attention with residual and identity mapping and ships the shared PPIS benchmark files directly."
        ),
        "reported_strength": (
            "The release surface is strong because the repository names the exact train and test pickle files used in the paper."
        ),
    },
    "ghgpr_ppis2023": {
        "citation": "Zhang et al. (2023), Computers in Biology and Medicine",
        "summary": (
            "GHGPR-PPIS combines heat-kernel graph diffusion, generalized PageRank, and edge attention for PPIS prediction."
        ),
        "reported_strength": (
            "The repository again ships the exact Train_335/Test_60/Test_315/UBtest_31 benchmark files."
        ),
    },
    "gact_ppis2024": {
        "citation": "Liu et al. (2024), International Journal of Biological Macromolecules",
        "summary": (
            "GACT-PPIS combines EGAT, Transformer blocks, and GCN components and evaluates on the public Test-60 and UBTest-31-6 family."
        ),
        "reported_strength": (
            "The paper reports leadership across recall, F1, MCC, AUROC, and AUPRC on the inherited benchmark family."
        ),
    },
    "gte_ppis2025": {
        "citation": "Zhang et al. (2025), Briefings in Bioinformatics",
        "summary": (
            "GTE-PPIS combines graph transformers with equivariant GNN components and releases the curated PPIS dataset files used for the study."
        ),
        "reported_strength": (
            "The paper reports consistent gains over prior PPIS baselines on the established benchmark lineage."
        ),
    },
    "asce_ppis2025": {
        "citation": "Liu et al. (2025), Bioinformatics",
        "summary": (
            "ASCE-PPIS uses equivariant graph pooling and graph collapse operations and ships both the main and similarity-reduced PPIS benchmark files."
        ),
        "reported_strength": (
            "The paper reports more than a ten-point improvement on Test60 over prior methods."
        ),
    },
    "egcppis2025": {
        "citation": "Zhao et al. (2025), BMC Bioinformatics",
        "summary": (
            "EGCPPIS uses hierarchical equivariant graph representations plus contrastive integration for PPIS prediction and releases fasta plus dataset folders."
        ),
        "reported_strength": (
            "The paper reports improved benchmark performance over previous methods on the same curated split family."
        ),
    },
    "mvso_ppis2025": {
        "citation": "Xu et al. (2025), Bioinformatics",
        "summary": (
            "MVSO-PPIS integrates multiple graph views with a structured objective and releases the same core PPIS benchmark files plus processed PDB inputs."
        ),
        "reported_strength": (
            "The paper positions itself as both more accurate and more structurally interpretable than prior PPIS models."
        ),
    },
    "hssppi2025": {
        "citation": "Li et al. (2025), Briefings in Bioinformatics",
        "summary": (
            "HSSPPI combines hierarchical and spatial-sequential structural modeling for "
            "PPIS prediction across multiple public tasks including Train335/Test60-style evaluations."
        ),
        "reported_strength": (
            "The paper reports better benchmark performance than comparison methods on two public tasks and ships train/test datasets."
        ),
    },
    "mippis2024": {
        "citation": "Wang et al. (2024), BMC Bioinformatics",
        "summary": (
            "MIPPIS fuses multiple information streams for PPIS prediction but still evaluates on the familiar Train_335/Test_60 benchmark family."
        ),
        "reported_strength": (
            "The paper reports AUROC and AUPRC gains while relying on the shared public benchmark lineage."
        ),
    },
    "seq_insite2024": {
        "citation": "Magrane and Ilie (2024), Bioinformatics",
        "summary": (
            "Seq-InSite is a sequence-only PPIS model that releases models trained without similarity to held-out sets such as without60, without70, and without315."
        ),
        "reported_strength": (
            "The paper argues that careful similarity guards let sequence-only models match or exceed strong structure-based baselines."
        ),
    },
    "deepppisp2019": {
        "citation": "Zeng et al. (2019), Bioinformatics",
        "summary": (
            "DeepPPISP combines local contextual and global sequence features for PPI-site prediction and releases benchmark datasets plus cached features."
        ),
        "reported_strength": (
            "The paper reports state-of-the-art PPIS performance, but the exact fixed 350/70 split used in the paper is not exposed cleanly enough in the release surface."
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
        benchmark_family = row.get("benchmark_family", "")
        if "identifier" in blockers or "ensembl" in blockers or "flybase" in blockers:
            issue_counts["identifier bridge missing"] += 1
        if "not mirrored" in blockers or "pkl" in blockers or "roster" in blockers:
            issue_counts["published split not mirrored"] += 1
        if benchmark_family == "ppis_train335_family":
            issue_counts["shared benchmark family reuse"] += 1
        if "exact fixed 350/70" in blockers or "not exposed cleanly enough" in blockers:
            issue_counts["fixed split still ambiguous"] += 1
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


def create_benchmark_chart(report: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = report["summary"]["benchmark_family_counts"]
    order = sorted(counts, key=counts.get, reverse=True)
    labels = [
        {
            "ppis_train335_family": "GraphPPIS / Train_335 family",
            "dscript_benchmark_family": "D-SCRIPT inherited family",
            "dscript_human_plus_species_holdout": "D-SCRIPT human + species holdout",
            "bernett_plus_cross_species": "Bernett + cross-species",
            "bernett_plus_species_holdout": "Bernett + held-out species",
            "rapppid_c123": "RAPPPID C1/C2/C3",
            "topsy_turvy_edgelists": "Topsy-Turvy edgelists",
            "hssppi_public_tasks": "HSSPPI public tasks",
            "seq_insite_similarity_guarded_ppis": "Seq-InSite similarity-guarded",
            "deepppisp_186_72_164": "DeepPPISP released datasets",
        }.get(key, key.replace("_", " "))
        for key in order
    ]
    values = [counts[key] for key in order]
    fig, ax = plt.subplots(figsize=(7.5, 4.4), dpi=220)
    ax.barh(range(len(labels)), values, color="#4f7ea8")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Paper count")
    ax.set_title("Benchmark-family concentration across the audit-friendly set")
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
    return [Paragraph(f"- {sanitize(item)}", style) for item in items if item]


def consequence_text(row: dict[str, Any]) -> str:
    verdict = row["verdict"]
    benchmark_family = row.get("benchmark_family")
    if verdict == "faithful and acceptable as-is":
        if benchmark_family == "ppis_train335_family":
            return (
                "Consequence: the split is fair for like-for-like comparison inside the published "
                "PPIS lineage, but strong claims about broad real-world generalization still need an out-of-family test."
            )
        return (
            "Consequence: this is a strong audit lane and can support paper-faithful comparison, "
            "but it still should not be confused with ProteoSphere's default governing benchmark unless mirrored and governed."
        )
    if verdict == "audit-useful but non-canonical":
        return (
            "Consequence: the split remains useful for historical comparison or external audit, "
            "but it is not strong enough on its own to govern model release or headline generalization claims."
        )
    if verdict == "incomplete because required evidence is missing":
        return (
            "Consequence: the benchmark cannot yet be trusted as a fixed held-out evaluation lane "
            "because the released surface does not pin down the exact paper split cleanly enough."
        )
    return (
        "Consequence: without roster-level or identifier-level evidence, the review cannot "
        "falsify leakage or prove independence, so the benchmark claim stays provisional."
    )


def reviewer_value_text(row: dict[str, Any]) -> str:
    blockers = " ".join(row.get("blockers") or []).lower()
    benchmark_family = row.get("benchmark_family", "")
    if "ensembl" in blockers or "flybase" in blockers or "identifier" in blockers:
        return (
            "What the reviewer catches: the split may be published and reproducible, yet still "
            "be unusable for governed evaluation until identifiers bridge into the warehouse."
        )
    if benchmark_family == "ppis_train335_family":
        return (
            "What the reviewer catches: reusing the same public benchmark family across many papers "
            "is fair for head-to-head comparison, but it is not the same thing as demonstrating new out-of-family robustness."
        )
    if row["verdict"] == "incomplete because required evidence is missing":
        return (
            "What the reviewer catches: a paper can release datasets and still fail the audit "
            "if the exact held-out membership used for the headline result is not recoverable."
        )
    return (
        "What the reviewer catches: a paper can be audit-friendly and still remain non-canonical "
        "because it inherits another benchmark family or lacks the evidence needed for governing use."
    )


def evidence_surface_text(row: dict[str, Any]) -> str:
    supplemental = row.get("supplemental_evidence") or {}
    if supplemental:
        return sanitize(supplemental.get("summary") or "Supplemental release evidence was used.")
    if row.get("benchmark_family") == "ppis_train335_family":
        return (
            "The split lineage is explicit in the paper and benchmark-family naming, but the exact "
            "pickle or fasta membership was not mirrored into the local audit workspace for direct overlap enumeration."
        )
    return (
        "This assessment is driven by the condensed warehouse, the source registry, and Model Studio split-policy logic, "
        "with the published benchmark or repo documentation used as supplemental provenance."
    )


def overlap_text(row: dict[str, Any]) -> str:
    direct = row["overlap_findings"]["direct_overlap"]
    status = direct.get("status", "not_reported").replace("_", " ")
    notes = " ".join(direct.get("notes") or [])
    return f"Overlap readout: {status}. {notes}"


def admissibility_text(row: dict[str, Any]) -> str:
    governed = row["governed_eligibility_findings"]
    status = governed.get("status", "unspecified").replace("_", " ")
    notes = " ".join(governed.get("notes") or [])
    return f"Governance and admissibility: {status}. {notes}"


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
    benchmark_chart = create_benchmark_chart(report, TMP_DIR / "benchmark_chart.png")
    issue_chart = create_issue_chart(ordered_rows, TMP_DIR / "issue_chart.png")
    story: list[Any] = []

    story.extend(
        [
            Spacer(1, 0.3 * inch),
            paragraph("ProteoSphere Audit of 20 Dataset-Forward Protein Interaction Papers", styles["CoverTitle"]),
            paragraph(
                (
                    "A warehouse-first review of explicit held-out splits, released benchmark artifacts, "
                    "and canonical admissibility under ProteoSphere logic"
                ),
                styles["Body"],
            ),
            Spacer(1, 0.18 * inch),
            callout_box(
                "Why this report exists",
                (
                    "This paper set was chosen because the authors publish split artifacts or inherit a named public benchmark family. "
                    "That makes it a better test of what a dataset reviewer adds after basic reproducibility is already in place."
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
            Image(str(benchmark_chart), width=6.9 * inch, height=3.85 * inch),
            Spacer(1, 0.08 * inch),
            paragraph(
                "Figure 2. Most papers in this set cluster around a small number of benchmark families, especially the GraphPPIS Train_335 lineage.",
                styles["Caption"],
            ),
            Spacer(1, 0.12 * inch),
            Image(str(issue_chart), width=6.9 * inch, height=3.7 * inch),
            Spacer(1, 0.08 * inch),
            paragraph(
                "Figure 3. Cross-cutting reasons a dataset reviewer still changes the interpretation of published splits.",
                styles["Caption"],
            ),
            PageBreak(),
            paragraph("Executive Summary", styles["SectionTitle"]),
        ]
    )

    summary_points = [
        "This audit-friendly set is materially stronger than the earlier reading list: 10 papers are faithful and acceptable as-is for paper-faithful evaluation, 9 are audit-useful but non-canonical, and only 1 remains incomplete because the held-out membership is still ambiguous.",
        "The main limitation is no longer rampant leakage. It is the difference between a published split and a governed split: mirroring, identifier bridging, and benchmark-family context still matter.",
        "RAPPPID and D-SCRIPT are especially strong examples of papers with real released split artifacts that still need warehouse-native identifier bridging before they become first-class governed lanes.",
        "The biggest family-level issue is PPIS benchmark saturation. Ten papers in this set reuse the Train_335/Test_60 lineage, which is fair for within-family comparison but weaker evidence for broad external generalization.",
        "DeepPPISP remains the outlier: the release ships benchmark datasets, but the fixed 350/70 train/test membership behind the paper's headline result is not exposed cleanly enough to audit as a stable held-out split.",
    ]
    story.extend(make_bullet_list(summary_points, styles["Body"]))
    story.extend(
        [
            Spacer(1, 0.14 * inch),
            paragraph("ProteoSphere Review Criteria", styles["SubTitle"]),
        ]
    )
    criteria_points = [
        "Faithful split recovery: can the exact train/test membership be reconstructed from the official release surface rather than inferred from prose?",
        "Warehouse resolvability: do the released identifiers map into best_evidence strongly enough to support direct overlap, accession-root, and UniRef checks?",
        "Leakage and benchmark lineage: even with published files, does the split inherit a heavily reused benchmark family that limits the strength of its generalization claim?",
        "Governance and admissibility: can the benchmark serve only as a paper-faithful audit lane, or is it strong enough to be proposed as a canonical ProteoSphere policy?",
        "Truthfulness under uncertainty: when the condensed warehouse cannot prove membership, the reviewer should say so rather than back-fill the claim from memory.",
    ]
    story.extend(make_bullet_list(criteria_points, styles["Body"]))
    story.extend(
        [
            Spacer(1, 0.16 * inch),
            callout_box(
                "Case study: benchmark-family saturation is not the same thing as external validity",
                (
                    "GraphPPIS created a strong and durable public PPIS benchmark, but ten papers in this review "
                    "reuse that lineage. A dataset reviewer should reward the transparency while also separating "
                    "within-family leaderboard progress from claims of broader robustness."
                ),
                styles,
            ),
            Spacer(1, 0.12 * inch),
            callout_box(
                "What changed relative to the earlier review set",
                (
                    "This time the user intentionally selected papers with explicit held-out splits or published benchmark artifacts. "
                    "That choice shifts the reviewer focus away from obvious split failures and toward canonicalization: identifier bridges, "
                    "benchmark-family dependence, and whether the released files are actually enough to recreate the headline evaluation."
                ),
                styles,
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
                f"Resolved split policy: {row['resolved_split_policy']['policy']} | "
                f"Benchmark family: {row.get('benchmark_family', 'none')}"
            )
            key_findings = [
                f"Claimed split: {row['claimed_split_description']}",
                f"Evidence surface: {evidence_surface_text(row)}",
                overlap_text(row),
                f"Leakage readout: {' '.join(row['leakage_findings']['notes'][:2])}",
                admissibility_text(row),
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
        "The strongest message from this report is that published splits are necessary but not sufficient. Auditability improves sharply when papers ship artifacts, but canonical benchmarking still depends on warehouse mapping, provenance governance, and family-level context.",
        "That distinction is exactly where a dataset reviewer becomes scientifically valuable. It explains why two perfectly reproducible papers may deserve different weight in training, release gating, and review articles about generalization.",
        "For a review paper, this set provides a constructive argument rather than a takedown: strong papers benefit from dataset review because the reviewer clarifies what their benchmark truly establishes and what it does not.",
        "ProteoSphere's advantage is not only stricter policy. It is the ability to turn published split claims into an explicit evidence graph: recoverable, comparable, and honest about what remains unresolved.",
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
    canvas.drawString(0.75 * inch, 0.45 * inch, "ProteoSphere audit-friendly dataset review")
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
        title="ProteoSphere Audit of 20 Dataset-Forward Protein Interaction Papers",
        author="Codex for ProteoSphere",
    )
    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    render_pdf_first_page(PDF_PATH, PREVIEW_PATH)
    print(f"Wrote {PDF_PATH}")
    print(f"Wrote {MANIFEST_PATH}")
    print(f"Wrote {PREVIEW_PATH}")


if __name__ == "__main__":
    main()

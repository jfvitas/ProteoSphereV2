from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INTERACTION_SIMILARITY_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "interaction_similarity_signature_preview.json"
)
DEFAULT_MOTIF_DOMAIN_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "motif_domain_compact_preview_family.json"
)
DEFAULT_KINETICS_SUPPORT_PREVIEW = (
    REPO_ROOT / "artifacts" / "status" / "kinetics_enzyme_support_preview.json"
)
DEFAULT_BUNDLE_MANIFEST = (
    REPO_ROOT / "artifacts" / "status" / "lightweight_bundle_manifest.json"
)
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT / "artifacts" / "status" / "compact_enrichment_policy_preview.json"
)
DEFAULT_OUTPUT_MD = (
    REPO_ROOT / "docs" / "reports" / "compact_enrichment_policy_preview.md"
)

POLICY_REPORT_ONLY = "report_only_non_governing"
POLICY_PREVIEW_BUNDLE = "preview_bundle_safe_non_governing"
POLICY_GROUNDED_GOVERNING = "grounded_and_governing"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _bundle_count(manifest: dict[str, Any], family_name: str) -> int:
    return int((manifest.get("record_counts") or {}).get(family_name, 0) or 0)


def _row(
    *,
    family_name: str,
    payload: dict[str, Any],
    manifest: dict[str, Any],
    bundle_family_name: str,
    policy_label: str,
    governing_for_split_or_leakage: bool,
    notes: list[str],
) -> dict[str, Any]:
    row_count = int(payload.get("row_count") or 0)
    bundle_record_count = _bundle_count(manifest, bundle_family_name)
    return {
        "family_name": family_name,
        "policy_label": policy_label,
        "row_count": row_count,
        "bundle_record_count": bundle_record_count,
        "bundle_included": bundle_record_count > 0,
        "governing_for_split_or_leakage": governing_for_split_or_leakage,
        "status": payload.get("status"),
        "notes": notes,
    }


def build_compact_enrichment_policy_preview(
    interaction_similarity_preview: dict[str, Any],
    motif_domain_preview: dict[str, Any],
    kinetics_support_preview: dict[str, Any],
    bundle_manifest: dict[str, Any],
) -> dict[str, Any]:
    motif_truth = motif_domain_preview.get("truth_boundary") or {}

    rows = [
        _row(
            family_name="interaction_similarity_preview",
            payload=interaction_similarity_preview,
            manifest=bundle_manifest,
            bundle_family_name="interaction_similarity_signatures",
            policy_label=POLICY_REPORT_ONLY,
            governing_for_split_or_leakage=False,
            notes=[
                "candidate-only interaction rows remain visible for audit context only",
                "interaction family stays outside the preview bundle until STRING tail "
                "completion and direct materialization are validated",
            ],
        ),
        _row(
            family_name="motif_domain_compact_preview_family",
            payload=motif_domain_preview,
            manifest=bundle_manifest,
            bundle_family_name="motif_domain_compact_preview_family",
            policy_label=POLICY_PREVIEW_BUNDLE,
            governing_for_split_or_leakage=bool(
                motif_truth.get("governing_for_split_or_leakage")
            ),
            notes=[
                "motif/domain rows are compact and bundle-safe",
                "motif/domain signals remain non-governing until explicitly promoted "
                "beyond preview",
            ],
        ),
        _row(
            family_name="kinetics_support_preview",
            payload=kinetics_support_preview,
            manifest=bundle_manifest,
            bundle_family_name="kinetics_support_preview",
            policy_label=POLICY_PREVIEW_BUNDLE,
            governing_for_split_or_leakage=False,
            notes=[
                "kinetics support is accession-resolved support-only and does not "
                "claim live kinetic ids",
                "kinetics support may be carried in the preview bundle as compact "
                "non-governing context",
            ],
        ),
    ]
    policy_counts: dict[str, int] = {}
    for row in rows:
        label = str(row["policy_label"])
        policy_counts[label] = policy_counts.get(label, 0) + 1

    return {
        "artifact_id": "compact_enrichment_policy_preview",
        "schema_id": "proteosphere-compact-enrichment-policy-preview-2026-04-02",
        "status": "complete",
        "generated_at": datetime.now(UTC).isoformat(),
        "row_count": len(rows),
        "rows": rows,
        "summary": {
            "policy_counts": dict(sorted(policy_counts.items())),
            "bundle_included_families": [
                row["family_name"] for row in rows if row["bundle_included"]
            ],
            "report_only_families": [
                row["family_name"]
                for row in rows
                if row["policy_label"] == POLICY_REPORT_ONLY
            ],
        },
        "allowed_policy_labels": [
            POLICY_REPORT_ONLY,
            POLICY_PREVIEW_BUNDLE,
            POLICY_GROUNDED_GOVERNING,
        ],
        "truth_boundary": {
            "summary": (
                "This is a control-plane policy surface for compact enrichment families. "
                "It does not mutate bundle contents by itself and does not promote any "
                "non-governing family into split or leakage governance."
            ),
            "report_only": True,
            "governing_promotion_performed": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Compact Enrichment Policy Preview",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Family count: `{payload['row_count']}`",
        "",
        "## Policy Rows",
        "",
    ]
    for row in payload["rows"]:
        lines.append(
            f"- `{row['family_name']}`: `{row['policy_label']}` / "
            f"bundle_included=`{row['bundle_included']}` / "
            f"governing=`{row['governing_for_split_or_leakage']}`"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export compact-family bundle/operator policy labels."
    )
    parser.add_argument(
        "--interaction-similarity-preview",
        type=Path,
        default=DEFAULT_INTERACTION_SIMILARITY_PREVIEW,
    )
    parser.add_argument(
        "--motif-domain-preview",
        type=Path,
        default=DEFAULT_MOTIF_DOMAIN_PREVIEW,
    )
    parser.add_argument(
        "--kinetics-support-preview",
        type=Path,
        default=DEFAULT_KINETICS_SUPPORT_PREVIEW,
    )
    parser.add_argument("--bundle-manifest", type=Path, default=DEFAULT_BUNDLE_MANIFEST)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_compact_enrichment_policy_preview(
        _read_json(args.interaction_similarity_preview),
        _read_json(args.motif_domain_preview),
        _read_json(args.kinetics_support_preview),
        _read_json(args.bundle_manifest),
    )
    _write_json(args.output_json, payload)
    _write_text(args.output_md, render_markdown(payload))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

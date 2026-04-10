from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.publish_release_cards import build_release_cards

ROOT = Path(__file__).resolve().parents[2]
SOURCE_MANIFEST = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_bundle_manifest.json"
)
SUPPORT_MANIFEST = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_support_manifest.json"
)
MODEL_PORTFOLIO = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "model_portfolio_benchmark.json"
)
RELEASE_LEDGER = (
    ROOT / "runs" / "real_data_benchmark" / "full_results" / "release_corpus_evidence_ledger.json"
)
SOURCE_COVERAGE = ROOT / "runs" / "real_data_benchmark" / "full_results" / "source_coverage.json"
METRICS_SUMMARY = ROOT / "runs" / "real_data_benchmark" / "full_results" / "metrics_summary.json"
RUN_SUMMARY = ROOT / "runs" / "real_data_benchmark" / "full_results" / "run_summary.json"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_json(path: Path, target: Path) -> Path:
    target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def test_publish_release_cards_writes_evidence_backed_cards_with_strict_boundaries(
    tmp_path: Path,
) -> None:
    manifest_output = tmp_path / "release_cards_manifest.json"
    output_dir = tmp_path / "cards"

    payload = build_release_cards(
        source_manifest_path=SOURCE_MANIFEST,
        support_manifest_path=SUPPORT_MANIFEST,
        model_portfolio_path=MODEL_PORTFOLIO,
        release_ledger_path=RELEASE_LEDGER,
        source_coverage_path=SOURCE_COVERAGE,
        metrics_summary_path=METRICS_SUMMARY,
        run_summary_path=RUN_SUMMARY,
        output_dir=output_dir,
        manifest_output_path=manifest_output,
    )

    manifest = _read_json(manifest_output)
    benchmark_card = (output_dir / "release_benchmark_card.md").read_text(encoding="utf-8")
    model_card = (output_dir / "release_model_card.md").read_text(encoding="utf-8")
    data_card = (output_dir / "release_data_card.md").read_text(encoding="utf-8")

    assert payload["status"] == "report_only"
    assert manifest["status"] == "report_only"
    assert manifest["summary"]["bundle_id"] == "release-benchmark-bundle-2026-03-22"
    assert manifest["summary"]["release_ready_count"] == 0
    assert manifest["truth_boundary"]["fail_closed"] is True
    assert manifest["truth_boundary"]["no_release_readiness_claim"] is True
    assert manifest["card_outputs"]["benchmark"]["present"] is True
    assert manifest["card_outputs"]["model"]["present"] is True
    assert manifest["card_outputs"]["data"]["present"] is True
    assert manifest["card_outputs"]["benchmark"]["sha256"] is not None
    assert manifest["card_outputs"]["model"]["sha256"] is not None
    assert manifest["card_outputs"]["data"]["sha256"] is not None

    assert "Release Benchmark Card" in benchmark_card
    assert "report-only" in benchmark_card
    assert "coverage not validation" in benchmark_card.lower()
    assert "assembled_with_blockers" in benchmark_card
    assert "production-equivalent runtime" in benchmark_card

    assert "Release Model Card" in model_card
    assert "proxy-derived" in model_card
    assert "no_go" in model_card
    assert "conservative_fusion_baseline" in model_card
    assert "separate independent family sweeps" in model_card

    assert "Release Data Card" in data_card
    assert "release corpus evidence ledger" in data_card.lower()
    assert "coverage not validation" in data_card.lower()
    assert "blocked" in data_card.lower()
    assert "release-grade corpus validation" in data_card


def test_publish_release_cards_fails_closed_on_manifest_mismatch(tmp_path: Path) -> None:
    source_manifest = _copy_json(SOURCE_MANIFEST, tmp_path / "release_bundle_manifest.json")
    support_manifest = _copy_json(SUPPORT_MANIFEST, tmp_path / "release_support_manifest.json")
    support_payload = _read_json(support_manifest)
    support_payload["bundle_id"] = "release-benchmark-bundle-mismatch"
    support_manifest.write_text(json.dumps(support_payload, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="bundle_id does not match"):
        build_release_cards(
            source_manifest_path=source_manifest,
            support_manifest_path=support_manifest,
            model_portfolio_path=MODEL_PORTFOLIO,
            release_ledger_path=RELEASE_LEDGER,
            source_coverage_path=SOURCE_COVERAGE,
            metrics_summary_path=METRICS_SUMMARY,
            run_summary_path=RUN_SUMMARY,
            output_dir=tmp_path / "cards",
            manifest_output_path=tmp_path / "release_cards_manifest.json",
        )


def test_publish_release_cards_fails_closed_on_overclaiming_ledger(tmp_path: Path) -> None:
    source_manifest = _copy_json(SOURCE_MANIFEST, tmp_path / "release_bundle_manifest.json")
    support_manifest = _copy_json(SUPPORT_MANIFEST, tmp_path / "release_support_manifest.json")
    model_portfolio = _copy_json(MODEL_PORTFOLIO, tmp_path / "model_portfolio_benchmark.json")
    ledger = _copy_json(RELEASE_LEDGER, tmp_path / "release_corpus_evidence_ledger.json")
    coverage = _copy_json(SOURCE_COVERAGE, tmp_path / "source_coverage.json")
    metrics_summary = _copy_json(METRICS_SUMMARY, tmp_path / "metrics_summary.json")
    run_summary = _copy_json(RUN_SUMMARY, tmp_path / "run_summary.json")

    ledger_payload = _read_json(ledger)
    ledger_payload["summary"]["release_ready_count"] = 1
    ledger_payload["rows"][0]["grade"] = "release_ready"
    ledger.write_text(json.dumps(ledger_payload, indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="release corpus ledger"):
        build_release_cards(
            source_manifest_path=source_manifest,
            support_manifest_path=support_manifest,
            model_portfolio_path=model_portfolio,
            release_ledger_path=ledger,
            source_coverage_path=coverage,
            metrics_summary_path=metrics_summary,
            run_summary_path=run_summary,
            output_dir=tmp_path / "cards",
            manifest_output_path=tmp_path / "release_cards_manifest.json",
        )


def test_publish_release_cards_fails_closed_when_required_schema_artifact_is_missing(
    tmp_path: Path,
) -> None:
    source_manifest = _copy_json(SOURCE_MANIFEST, tmp_path / "release_bundle_manifest.json")
    support_manifest = _copy_json(SUPPORT_MANIFEST, tmp_path / "release_support_manifest.json")
    model_portfolio = _copy_json(MODEL_PORTFOLIO, tmp_path / "model_portfolio_benchmark.json")
    ledger = _copy_json(RELEASE_LEDGER, tmp_path / "release_corpus_evidence_ledger.json")
    coverage = _copy_json(SOURCE_COVERAGE, tmp_path / "source_coverage.json")
    metrics_summary = _copy_json(METRICS_SUMMARY, tmp_path / "metrics_summary.json")
    run_summary = _copy_json(RUN_SUMMARY, tmp_path / "run_summary.json")

    source_payload = _read_json(source_manifest)
    schema_entry = next(
        item for item in source_payload["release_artifacts"] if item["role"] == "schema"
    )
    schema_entry["present"] = False
    source_manifest.write_text(json.dumps(source_payload, indent=2), encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="missing required release artifact: schema"):
        build_release_cards(
            source_manifest_path=source_manifest,
            support_manifest_path=support_manifest,
            model_portfolio_path=model_portfolio,
            release_ledger_path=ledger,
            source_coverage_path=coverage,
            metrics_summary_path=metrics_summary,
            run_summary_path=run_summary,
            output_dir=tmp_path / "cards",
            manifest_output_path=tmp_path / "release_cards_manifest.json",
        )

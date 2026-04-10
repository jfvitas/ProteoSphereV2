from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPANDED_LATEST = (
    REPO_ROOT
    / "data"
    / "reports"
    / "expanded_pp_benchmark_candidates"
    / "LATEST_EXPANDED_PP_BENCHMARK.json"
)
RELEASE_ROOT = (
    REPO_ROOT
    / "data"
    / "reports"
    / "model_studio_release_benchmarks"
    / "release-pp-alpha-benchmark-v1"
)
LATEST_RELEASE = (
    REPO_ROOT
    / "data"
    / "reports"
    / "model_studio_release_benchmarks"
    / "LATEST_RELEASE_PP_ALPHA_BENCHMARK.json"
)


def main() -> int:
    source = json.loads(EXPANDED_LATEST.read_text(encoding="utf-8-sig"))
    RELEASE_ROOT.mkdir(parents=True, exist_ok=True)
    train_src = Path(source["train_csv"])
    test_src = Path(source["test_csv"])
    candidate_src = Path(source["artifact_json"])

    train_dst = RELEASE_ROOT / "release_train_labels.csv"
    test_dst = RELEASE_ROOT / "release_test_labels.csv"
    candidate_dst = RELEASE_ROOT / "release_pp_alpha_benchmark_candidate.json"

    shutil.copy2(train_src, train_dst)
    shutil.copy2(test_src, test_dst)
    shutil.copy2(candidate_src, candidate_dst)

    manifest = {
        "dataset_ref": "release_pp_alpha_benchmark_v1",
        "frozen_from": str(EXPANDED_LATEST),
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "train_csv": str(train_dst),
        "test_csv": str(test_dst),
        "artifact_json": str(candidate_dst),
        "release_root": str(RELEASE_ROOT),
        "row_count": sum(1 for _ in train_dst.open("r", encoding="utf-8-sig")) - 1
        + sum(1 for _ in test_dst.open("r", encoding="utf-8-sig")) - 1,
    }
    (RELEASE_ROOT / "release_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    LATEST_RELEASE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(LATEST_RELEASE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

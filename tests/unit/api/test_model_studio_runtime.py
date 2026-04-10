from __future__ import annotations

import csv
import time
from pathlib import Path

from api.model_studio import runtime
from api.model_studio.catalog import default_pipeline_spec
from api.model_studio.contracts import pipeline_spec_from_dict


def _pdb_line(
    serial: int,
    atom: str,
    resname: str,
    chain: str,
    resseq: int,
    x: float,
    y: float,
    z: float,
    record: str = "ATOM",
) -> str:
    return (
        f"{record:<6}{serial:>5}  {atom:<4}{resname:>3} {chain}{resseq:>4}    "
        f"{x:>8.3f}{y:>8.3f}{z:>8.3f}  1.00 20.00           {atom[0]:>2}\n"
    )


def _write_toy_structure(path: Path, offset: float) -> None:
    lines = [
        _pdb_line(1, "CA", "LYS", "A", 1, 0.0 + offset, 0.0, 0.0),
        _pdb_line(2, "CB", "LYS", "A", 1, 0.4 + offset, 0.0, 0.0),
        _pdb_line(3, "CA", "ASP", "B", 1, 4.0 + offset, 0.0, 0.0),
        _pdb_line(4, "CB", "ASP", "B", 1, 4.4 + offset, 0.0, 0.0),
        _pdb_line(5, "O", "HOH", "W", 1, 2.0 + offset, 0.0, 0.0, record="HETATM"),
    ]
    path.write_text("".join(lines), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "PDB",
                "exp_dG",
                "Source Data Set",
                "Complex Type",
                "Mapped Protein Accessions",
                "Ligand Chains",
                "Receptor Chains",
                "Structure File",
                "Resolution (A)",
                "Release Year",
                "Label Temperature (K)",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def test_launch_run_persists_metrics_and_artifacts(tmp_path, monkeypatch) -> None:
    structures = tmp_path / "structures"
    structures.mkdir()
    train_csv = tmp_path / "train.csv"
    test_csv = tmp_path / "test.csv"

    for index in range(1, 7):
        _write_toy_structure(structures / f"toy{index}.pdb", offset=float(index))

    _write_csv(
        train_csv,
        [
            {
                "PDB": f"TOY{index}",
                "exp_dG": str(-7.0 - index),
                "Source Data Set": "Toy benchmark",
                "Complex Type": "protein_protein",
                "Mapped Protein Accessions": f"P0000{index};P0001{index}",
                "Ligand Chains": "A",
                "Receptor Chains": "B",
                "Structure File": str(structures / f"toy{index}.pdb"),
                "Resolution (A)": "2.0",
                "Release Year": str(2000 + index),
                "Label Temperature (K)": "298.15",
            }
            for index in range(1, 5)
        ],
    )
    _write_csv(
        test_csv,
        [
            {
                "PDB": f"TOY{index}",
                "exp_dG": str(-7.0 - index),
                "Source Data Set": "Toy benchmark",
                "Complex Type": "protein_protein",
                "Mapped Protein Accessions": f"P1000{index};P1001{index}",
                "Ligand Chains": "A",
                "Receptor Chains": "B",
                "Structure File": str(structures / f"toy{index}.pdb"),
                "Resolution (A)": "2.1",
                "Release Year": str(2000 + index),
                "Label Temperature (K)": "298.15",
            }
            for index in range(5, 7)
        ],
    )

    monkeypatch.setattr(runtime, "RUN_DIR", tmp_path / "runs")
    monkeypatch.setattr(
        runtime,
        "list_known_datasets",
        lambda: [
            {
                "dataset_ref": "toy_pp_benchmark",
                "label": "Toy benchmark",
                "task_type": "protein-protein",
                "split_strategy": "leakage_resistant_benchmark",
                "train_csv": str(train_csv),
                "test_csv": str(test_csv),
                "source_manifest": str(tmp_path / "manifest.json"),
                "row_count": 6,
                "tags": ["ppi", "toy"],
                "maturity": "training_ready_candidate",
            }
        ],
    )

    spec_dict = default_pipeline_spec().to_dict()
    spec_dict["pipeline_id"] = "pipeline:toy"
    spec_dict["study_title"] = "Toy Studio Run"
    spec_dict["training_plan"]["model_family"] = "mlp"
    spec_dict["training_plan"]["epoch_budget"] = 8
    spec_dict["data_strategy"]["dataset_refs"] = ["toy_pp_benchmark"]
    spec = pipeline_spec_from_dict(spec_dict)

    manifest = runtime.launch_run(spec)
    assert manifest["status"] == "running"

    for _ in range(300):
        run = runtime.load_run(manifest["run_id"])
        if run["run_manifest"]["status"] not in {"running", "queued"}:
            break
        time.sleep(0.05)
    else:
        raise AssertionError("Studio run did not reach a terminal state in time.")

    run = runtime.load_run(manifest["run_id"])
    assert run["run_manifest"]["status"] == "completed"
    assert run["metrics"]["resolved_backend"] == "sklearn-mlp-regressor"
    assert run["artifacts"]["metrics.json"].endswith("/metrics.json")
    assert run["outliers"]["items"]

    report_text = (runtime.RUN_DIR / manifest["run_id"] / "report.md").read_text(encoding="utf-8")
    assert "Model Studio Run Summary" in report_text


def test_preview_and_build_training_set_return_split_diagnostics(tmp_path, monkeypatch) -> None:
    structures = tmp_path / "structures"
    structures.mkdir()
    train_csv = tmp_path / "train.csv"
    test_csv = tmp_path / "test.csv"

    for index in range(1, 9):
        _write_toy_structure(structures / f"toy{index}.pdb", offset=float(index))

    _write_csv(
        train_csv,
        [
            {
                "PDB": f"PRE{index}",
                "exp_dG": str(-6.0 - index),
                "Source Data Set": "Preview benchmark",
                "Complex Type": "protein_protein",
                "Mapped Protein Accessions": f"P2000{index};P2001{index}",
                "Ligand Chains": "A",
                "Receptor Chains": "B",
                "Structure File": str(structures / f"toy{index}.pdb"),
                "Resolution (A)": "2.4",
                "Release Year": str(2010 + index),
                "Label Temperature (K)": "298.15",
            }
            for index in range(1, 5)
        ],
    )
    _write_csv(
        test_csv,
        [
            {
                "PDB": f"PRE{index}",
                "exp_dG": str(-6.0 - index),
                "Source Data Set": "Preview benchmark",
                "Complex Type": "protein_protein",
                "Mapped Protein Accessions": f"P2000{index};P2001{index}",
                "Ligand Chains": "A",
                "Receptor Chains": "B",
                "Structure File": str(structures / f"toy{index}.pdb"),
                "Resolution (A)": "2.2",
                "Release Year": str(2010 + index),
                "Label Temperature (K)": "298.15",
            }
            for index in range(5, 9)
        ],
    )

    monkeypatch.setattr(runtime, "TRAINING_SET_BUILD_DIR", tmp_path / "training_set_builds")
    monkeypatch.setattr(
        runtime,
        "list_known_datasets",
        lambda: [
            {
                "dataset_ref": "preview_pp_benchmark",
                "label": "Preview benchmark",
                "task_type": "protein-protein",
                "split_strategy": "leakage_resistant_benchmark",
                "train_csv": str(train_csv),
                "val_csv": None,
                "test_csv": str(test_csv),
                "source_manifest": str(tmp_path / "manifest.json"),
                "row_count": 8,
                "tags": ["ppi", "preview"],
                "maturity": "pilot_candidate",
                "catalog_status": "release",
            }
        ],
    )

    spec = default_pipeline_spec()
    preview = runtime.preview_training_set_request(
        spec.training_set_request,
        spec.split_plan,
        fallback_dataset_refs=("preview_pp_benchmark",),
    )
    assert preview["candidate_preview"]["row_count"] >= 1
    assert preview["candidate_preview"]["rows"]
    assert preview["split_preview"]["test_count"] >= 1

    built = runtime.build_training_set(
        spec.pipeline_id,
        spec.study_title,
        spec.training_set_request,
        spec.split_plan,
        fallback_dataset_refs=("preview_pp_benchmark",),
    )
    assert built["dataset_ref"].startswith("study_build:")
    assert Path(built["train_csv"]).exists()
    assert built["split_preview"]["train_count"] >= 1
    assert built["selected_rows_preview"]

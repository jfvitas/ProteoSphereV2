from __future__ import annotations

import subprocess
from pathlib import Path

from normalization.mapping.mmseqs2_backend import MMseqs2Backend, MMseqs2Sequence


def test_align_reports_runtime_unavailable_without_invoking_fallback() -> None:
    backend = MMseqs2Backend(which=lambda _: None, runner=_unexpected_runner)

    runtime = backend.inspect_runtime()
    result = backend.align([_sequence("query", "ACDE")], [_sequence("P1", "ACDE")])

    assert runtime.available is False
    assert runtime.reason == "mmseqs2_binary_not_found"
    assert result.status == "runtime_unavailable"
    assert result.reason == "mmseqs2_binary_not_found"
    assert result.hits == ()
    assert result.provenance.backend == "mmseqs2"
    assert result.provenance.runtime_available is False
    assert result.provenance.fallback_used is False
    assert result.provenance.command == ()


def test_align_parses_mmseqs2_hits_and_records_provenance(tmp_path: Path) -> None:
    runner = _FakeRunner(
        search_output=(
            "queryA\tP_MATCH\t97.5\t40\t1\t0\t1\t40\t2\t41\t1e-30\t115.0\t1\t0.91\n"
            "queryA\tP_SECOND\t92.0\t38\t3\t0\t1\t38\t5\t42\t4e-20\t95.0\t0.95\t0.84\n"
        )
    )
    backend = MMseqs2Backend(
        which=lambda _: "C:\\tools\\mmseqs.exe",
        runner=runner,
        temp_root=tmp_path,
    )

    result = backend.align(
        [_sequence("queryA", "ACDEFGHIKLMNPQRSTVWY")],
        [
            _sequence("P_MATCH", "ACDEFGHIKLMNPQRSTVWY"),
            _sequence("P_SECOND", "ACDEFGHIKLMNPQRSAVWY"),
        ],
        max_sequences=25,
        extra_args=("--threads", "2"),
    )

    assert result.status == "ok"
    assert result.reason == "alignment_completed"
    assert [hit.target_id for hit in result.hits] == ["P_MATCH", "P_SECOND"]
    assert result.hits[0].percent_identity == 97.5
    assert result.hits[0].bit_score == 115.0
    assert result.provenance.backend == "mmseqs2"
    assert result.provenance.mode == "alignment"
    assert result.provenance.runtime_available is True
    assert result.provenance.fallback_used is False
    assert result.provenance.executable == "C:\\tools\\mmseqs.exe"
    assert result.provenance.reference_records == 2
    assert result.to_dict()["provenance"]["backend"] == "mmseqs2"
    assert runner.calls[0] == ("C:\\tools\\mmseqs.exe", "--version")
    assert runner.calls[1][1] == "easy-search"
    assert "--format-output" in runner.calls[1]
    assert "--max-seqs" in runner.calls[1]
    assert "--threads" in runner.calls[1]


def test_align_returns_explicit_no_hits_when_mmseqs2_output_is_empty(tmp_path: Path) -> None:
    backend = MMseqs2Backend(
        which=lambda _: "C:\\tools\\mmseqs.exe",
        runner=_FakeRunner(search_output=""),
        temp_root=tmp_path,
    )

    result = backend.align([_sequence("queryA", "ACDE")], [_sequence("P1", "WXYZ")])

    assert result.status == "no_results"
    assert result.reason == "no_hits"
    assert result.hits == ()
    assert result.provenance.runtime_available is True
    assert result.provenance.reason == "no_hits"
    assert result.provenance.fallback_used is False


def test_cluster_parses_members_and_preserves_true_mmseqs2_provenance(
    tmp_path: Path,
) -> None:
    runner = _FakeRunner(
        cluster_output="seq1\tseq1\nseq1\tseq2\nseq3\tseq3\n",
    )
    backend = MMseqs2Backend(
        which=lambda _: "C:\\tools\\mmseqs.exe",
        runner=runner,
        temp_root=tmp_path,
    )

    result = backend.cluster(
        [
            _sequence("seq1", "AAAA"),
            _sequence("seq2", "AAAT"),
            _sequence("seq3", "GGGG"),
        ],
        min_sequence_identity=0.3,
        coverage=0.9,
        extra_args=("--threads", "4"),
    )

    assert result.status == "ok"
    assert result.reason == "clustering_completed"
    assert [(member.cluster_id, member.sequence_id) for member in result.members] == [
        ("seq1", "seq1"),
        ("seq1", "seq2"),
        ("seq3", "seq3"),
    ]
    assert [member.is_representative for member in result.members] == [True, False, True]
    assert result.provenance.backend == "mmseqs2"
    assert result.provenance.mode == "clustering"
    assert result.provenance.runtime_available is True
    assert result.provenance.fallback_used is False
    assert result.provenance.command[1] == "easy-cluster"
    assert "--min-seq-id" in result.provenance.command
    assert "--threads" in result.provenance.command


class _FakeRunner:
    def __init__(
        self,
        *,
        version_output: str = "MMseqs2 Version 15-6f452\n",
        search_output: str | None = None,
        cluster_output: str | None = None,
    ) -> None:
        self.version_output = version_output
        self.search_output = search_output
        self.cluster_output = cluster_output
        self.calls: list[tuple[str, ...]] = []

    def __call__(
        self,
        command: tuple[str, ...],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
        env: dict[str, str] | None,
    ) -> subprocess.CompletedProcess[str]:
        del capture_output, text, check, env
        self.calls.append(tuple(command))
        if len(command) > 1 and command[1] == "--version":
            return subprocess.CompletedProcess(command, 0, self.version_output, "")
        if len(command) > 1 and command[1] == "easy-search":
            Path(command[4]).write_text(self.search_output or "", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, "", "")
        if len(command) > 1 and command[1] == "easy-cluster":
            output_prefix = Path(command[3])
            output_path = output_prefix.with_name(f"{output_prefix.name}_cluster.tsv")
            output_path.write_text(self.cluster_output or "", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, "", "")
        raise AssertionError(f"unexpected MMseqs2 command: {command}")


def _unexpected_runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
    del args, kwargs
    raise AssertionError("runner should not be called when MMseqs2 is unavailable")


def _sequence(sequence_id: str, sequence: str) -> MMseqs2Sequence:
    return MMseqs2Sequence(sequence_id=sequence_id, sequence=sequence)

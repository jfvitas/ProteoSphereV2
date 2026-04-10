"""Concrete MMseqs2 backend for lockdown alignment and clustering tasks.

This module only reports real MMseqs2 execution. If the binary or runtime is
unavailable, callers receive an explicit blocked result with provenance instead
of a silent fallback.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

BackendStatus = Literal[
    "ok",
    "empty_input",
    "no_results",
    "runtime_unavailable",
    "execution_failed",
]
MMseqs2Mode = Literal["alignment", "clustering"]
_ALIGNMENT_OUTPUT_COLUMNS = (
    "query",
    "target",
    "pident",
    "alnlen",
    "mismatch",
    "gapopen",
    "qstart",
    "qend",
    "tstart",
    "tend",
    "evalue",
    "bits",
    "qcov",
    "tcov",
)
_DEFAULT_ALIGNMENT_OUTPUT_FORMAT = ",".join(_ALIGNMENT_OUTPUT_COLUMNS)
_DEFAULT_CLUSTER_COVERAGE = 0.8
_DEFAULT_ALIGNMENT_COVERAGE = 0.8
_DEFAULT_CLUSTER_MODE = 0
_DEFAULT_SEARCH_SENSITIVITY = 7.5
_MMSEQS2_BACKEND = "mmseqs2"


@dataclass(frozen=True, slots=True)
class MMseqs2Sequence:
    sequence_id: str
    sequence: str
    description: str = ""

    def __post_init__(self) -> None:
        sequence_id = str(self.sequence_id).strip()
        if not sequence_id:
            raise ValueError("sequence_id must not be empty")
        sequence = _normalize_sequence(self.sequence)
        if not sequence:
            raise ValueError("sequence must not be empty")
        object.__setattr__(self, "sequence_id", sequence_id)
        object.__setattr__(self, "sequence", sequence)
        object.__setattr__(self, "description", str(self.description).strip())

    def to_fasta_header(self) -> str:
        if self.description:
            return f">{self.sequence_id} {self.description}"
        return f">{self.sequence_id}"

    def to_dict(self) -> dict[str, object]:
        return {
            "sequence_id": self.sequence_id,
            "sequence": self.sequence,
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class MMseqs2RuntimeInfo:
    available: bool
    executable: str | None
    version: str | None
    reason: str
    probe_command: tuple[str, ...] = ()
    stderr: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "available": self.available,
            "executable": self.executable,
            "version": self.version,
            "reason": self.reason,
            "probe_command": list(self.probe_command),
            "stderr": self.stderr,
        }


@dataclass(frozen=True, slots=True)
class MMseqs2Provenance:
    backend: Literal["mmseqs2"]
    mode: MMseqs2Mode
    runtime_available: bool
    executable: str | None
    version: str | None
    command: tuple[str, ...]
    fallback_used: bool
    reason: str
    input_records: int
    reference_records: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "backend": self.backend,
            "mode": self.mode,
            "runtime_available": self.runtime_available,
            "executable": self.executable,
            "version": self.version,
            "command": list(self.command),
            "fallback_used": self.fallback_used,
            "reason": self.reason,
            "input_records": self.input_records,
            "reference_records": self.reference_records,
        }


@dataclass(frozen=True, slots=True)
class MMseqs2AlignmentHit:
    query_id: str
    target_id: str
    percent_identity: float
    alignment_length: int
    mismatches: int
    gap_openings: int
    query_start: int
    query_end: int
    target_start: int
    target_end: int
    evalue: float
    bit_score: float
    query_coverage: float
    target_coverage: float

    def to_dict(self) -> dict[str, object]:
        return {
            "query_id": self.query_id,
            "target_id": self.target_id,
            "percent_identity": self.percent_identity,
            "alignment_length": self.alignment_length,
            "mismatches": self.mismatches,
            "gap_openings": self.gap_openings,
            "query_start": self.query_start,
            "query_end": self.query_end,
            "target_start": self.target_start,
            "target_end": self.target_end,
            "evalue": self.evalue,
            "bit_score": self.bit_score,
            "query_coverage": self.query_coverage,
            "target_coverage": self.target_coverage,
        }


@dataclass(frozen=True, slots=True)
class MMseqs2AlignmentResult:
    status: BackendStatus
    reason: str
    provenance: MMseqs2Provenance
    hits: tuple[MMseqs2AlignmentHit, ...] = ()
    stderr: str = ""

    @property
    def succeeded(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "reason": self.reason,
            "provenance": self.provenance.to_dict(),
            "hits": [hit.to_dict() for hit in self.hits],
            "stderr": self.stderr,
        }


@dataclass(frozen=True, slots=True)
class MMseqs2ClusterMember:
    cluster_id: str
    sequence_id: str
    is_representative: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "cluster_id": self.cluster_id,
            "sequence_id": self.sequence_id,
            "is_representative": self.is_representative,
        }


@dataclass(frozen=True, slots=True)
class MMseqs2ClusteringResult:
    status: BackendStatus
    reason: str
    provenance: MMseqs2Provenance
    members: tuple[MMseqs2ClusterMember, ...] = ()
    stderr: str = ""

    @property
    def succeeded(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "reason": self.reason,
            "provenance": self.provenance.to_dict(),
            "members": [member.to_dict() for member in self.members],
            "stderr": self.stderr,
        }


def _default_runner(
    command: Sequence[str],
    *,
    capture_output: bool,
    text: bool,
    check: bool,
    env: Mapping[str, str] | None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        capture_output=capture_output,
        text=text,
        check=check,
        env=dict(env) if env is not None else None,
    )


_Runner = Callable[..., subprocess.CompletedProcess[str]]
_Which = Callable[[str], str | None]


@dataclass(slots=True)
class MMseqs2Backend:
    executable: str = "mmseqs"
    runner: _Runner = _default_runner
    which: _Which = shutil.which
    env: Mapping[str, str] | None = None
    temp_root: Path | None = None

    def inspect_runtime(self) -> MMseqs2RuntimeInfo:
        resolved_executable = self._resolve_executable()
        if resolved_executable is None:
            return MMseqs2RuntimeInfo(
                available=False,
                executable=None,
                version=None,
                reason="mmseqs2_binary_not_found",
            )

        probe_command = (resolved_executable, "--version")
        completed = self.runner(
            probe_command,
            capture_output=True,
            text=True,
            check=False,
            env=self._effective_env(),
        )
        version = _extract_first_line(completed.stdout)
        if completed.returncode != 0 or not version:
            return MMseqs2RuntimeInfo(
                available=False,
                executable=resolved_executable,
                version=version or None,
                reason="mmseqs2_version_probe_failed",
                probe_command=probe_command,
                stderr=(completed.stderr or "").strip(),
            )
        return MMseqs2RuntimeInfo(
            available=True,
            executable=resolved_executable,
            version=version,
            reason="mmseqs2_runtime_available",
            probe_command=probe_command,
            stderr=(completed.stderr or "").strip(),
        )

    def align(
        self,
        queries: Iterable[MMseqs2Sequence],
        targets: Iterable[MMseqs2Sequence],
        *,
        sensitivity: float = _DEFAULT_SEARCH_SENSITIVITY,
        coverage: float = _DEFAULT_ALIGNMENT_COVERAGE,
        max_sequences: int | None = None,
        extra_args: Sequence[str] = (),
    ) -> MMseqs2AlignmentResult:
        query_records = tuple(queries)
        target_records = tuple(targets)

        if not query_records:
            return MMseqs2AlignmentResult(
                status="empty_input",
                reason="no_query_sequences",
                provenance=_build_provenance(
                    mode="alignment",
                    runtime=None,
                    command=(),
                    reason="no_query_sequences",
                    input_records=0,
                    reference_records=len(target_records),
                ),
            )
        if not target_records:
            return MMseqs2AlignmentResult(
                status="empty_input",
                reason="no_target_sequences",
                provenance=_build_provenance(
                    mode="alignment",
                    runtime=None,
                    command=(),
                    reason="no_target_sequences",
                    input_records=len(query_records),
                    reference_records=0,
                ),
            )

        runtime = self.inspect_runtime()
        if not runtime.available:
            return MMseqs2AlignmentResult(
                status="runtime_unavailable",
                reason=runtime.reason,
                provenance=_build_provenance(
                    mode="alignment",
                    runtime=runtime,
                    command=(),
                    reason=runtime.reason,
                    input_records=len(query_records),
                    reference_records=len(target_records),
                ),
                stderr=runtime.stderr,
            )

        with TemporaryDirectory(dir=self._temp_root_string()) as temp_dir:
            temp_path = Path(temp_dir)
            query_path = temp_path / "query.fasta"
            target_path = temp_path / "target.fasta"
            output_path = temp_path / "alignment.tsv"
            scratch_path = temp_path / "tmp"

            _write_fasta(query_path, query_records)
            _write_fasta(target_path, target_records)

            command = [
                runtime.executable or self.executable,
                "easy-search",
                str(query_path),
                str(target_path),
                str(output_path),
                str(scratch_path),
                "--format-output",
                _DEFAULT_ALIGNMENT_OUTPUT_FORMAT,
                "-s",
                _format_float(sensitivity),
                "-c",
                _format_float(coverage),
            ]
            if max_sequences is not None:
                command.extend(("--max-seqs", str(int(max_sequences))))
            command.extend(str(argument) for argument in extra_args)

            completed = self.runner(
                tuple(command),
                capture_output=True,
                text=True,
                check=False,
                env=self._effective_env(),
            )
            if completed.returncode != 0:
                return MMseqs2AlignmentResult(
                    status="execution_failed",
                    reason="mmseqs2_alignment_failed",
                    provenance=_build_provenance(
                        mode="alignment",
                        runtime=runtime,
                        command=tuple(command),
                        reason="mmseqs2_alignment_failed",
                        input_records=len(query_records),
                        reference_records=len(target_records),
                    ),
                    stderr=(completed.stderr or "").strip(),
                )

            if not output_path.exists():
                return MMseqs2AlignmentResult(
                    status="execution_failed",
                    reason="missing_alignment_output",
                    provenance=_build_provenance(
                        mode="alignment",
                        runtime=runtime,
                        command=tuple(command),
                        reason="missing_alignment_output",
                        input_records=len(query_records),
                        reference_records=len(target_records),
                    ),
                    stderr=(completed.stderr or "").strip(),
                )

            hits = tuple(_parse_alignment_hits(output_path))
            if not hits:
                return MMseqs2AlignmentResult(
                    status="no_results",
                    reason="no_hits",
                    provenance=_build_provenance(
                        mode="alignment",
                        runtime=runtime,
                        command=tuple(command),
                        reason="no_hits",
                        input_records=len(query_records),
                        reference_records=len(target_records),
                    ),
                    stderr=(completed.stderr or "").strip(),
                )

            return MMseqs2AlignmentResult(
                status="ok",
                reason="alignment_completed",
                provenance=_build_provenance(
                    mode="alignment",
                    runtime=runtime,
                    command=tuple(command),
                    reason="alignment_completed",
                    input_records=len(query_records),
                    reference_records=len(target_records),
                ),
                hits=hits,
                stderr=(completed.stderr or "").strip(),
            )

    def cluster(
        self,
        sequences: Iterable[MMseqs2Sequence],
        *,
        min_sequence_identity: float,
        coverage: float = _DEFAULT_CLUSTER_COVERAGE,
        cluster_mode: int = _DEFAULT_CLUSTER_MODE,
        extra_args: Sequence[str] = (),
    ) -> MMseqs2ClusteringResult:
        sequence_records = tuple(sequences)
        if not sequence_records:
            return MMseqs2ClusteringResult(
                status="empty_input",
                reason="no_sequences_to_cluster",
                provenance=_build_provenance(
                    mode="clustering",
                    runtime=None,
                    command=(),
                    reason="no_sequences_to_cluster",
                    input_records=0,
                ),
            )

        runtime = self.inspect_runtime()
        if not runtime.available:
            return MMseqs2ClusteringResult(
                status="runtime_unavailable",
                reason=runtime.reason,
                provenance=_build_provenance(
                    mode="clustering",
                    runtime=runtime,
                    command=(),
                    reason=runtime.reason,
                    input_records=len(sequence_records),
                ),
                stderr=runtime.stderr,
            )

        with TemporaryDirectory(dir=self._temp_root_string()) as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "cluster_input.fasta"
            output_prefix = temp_path / "cluster_output"
            scratch_path = temp_path / "tmp"

            _write_fasta(input_path, sequence_records)

            command = [
                runtime.executable or self.executable,
                "easy-cluster",
                str(input_path),
                str(output_prefix),
                str(scratch_path),
                "--min-seq-id",
                _format_float(min_sequence_identity),
                "-c",
                _format_float(coverage),
                "--cluster-mode",
                str(int(cluster_mode)),
            ]
            command.extend(str(argument) for argument in extra_args)

            completed = self.runner(
                tuple(command),
                capture_output=True,
                text=True,
                check=False,
                env=self._effective_env(),
            )
            if completed.returncode != 0:
                return MMseqs2ClusteringResult(
                    status="execution_failed",
                    reason="mmseqs2_clustering_failed",
                    provenance=_build_provenance(
                        mode="clustering",
                        runtime=runtime,
                        command=tuple(command),
                        reason="mmseqs2_clustering_failed",
                        input_records=len(sequence_records),
                    ),
                    stderr=(completed.stderr or "").strip(),
                )

            output_path = _cluster_output_path(output_prefix)
            if not output_path.exists():
                return MMseqs2ClusteringResult(
                    status="execution_failed",
                    reason="missing_cluster_output",
                    provenance=_build_provenance(
                        mode="clustering",
                        runtime=runtime,
                        command=tuple(command),
                        reason="missing_cluster_output",
                        input_records=len(sequence_records),
                    ),
                    stderr=(completed.stderr or "").strip(),
                )

            members = tuple(_parse_cluster_members(output_path))
            if not members:
                return MMseqs2ClusteringResult(
                    status="no_results",
                    reason="no_clusters",
                    provenance=_build_provenance(
                        mode="clustering",
                        runtime=runtime,
                        command=tuple(command),
                        reason="no_clusters",
                        input_records=len(sequence_records),
                    ),
                    stderr=(completed.stderr or "").strip(),
                )

            return MMseqs2ClusteringResult(
                status="ok",
                reason="clustering_completed",
                provenance=_build_provenance(
                    mode="clustering",
                    runtime=runtime,
                    command=tuple(command),
                    reason="clustering_completed",
                    input_records=len(sequence_records),
                ),
                members=members,
                stderr=(completed.stderr or "").strip(),
            )

    def _resolve_executable(self) -> str | None:
        candidate = str(self.executable or "").strip()
        if not candidate:
            return None
        if _looks_like_path(candidate):
            return candidate if Path(candidate).exists() else None
        return self.which(candidate)

    def _effective_env(self) -> Mapping[str, str] | None:
        if self.env is None:
            return None
        merged = dict(os.environ)
        merged.update({str(key): str(value) for key, value in self.env.items()})
        return merged

    def _temp_root_string(self) -> str | None:
        if self.temp_root is None:
            return None
        return str(self.temp_root)


def _build_provenance(
    *,
    mode: MMseqs2Mode,
    runtime: MMseqs2RuntimeInfo | None,
    command: Sequence[str],
    reason: str,
    input_records: int,
    reference_records: int | None = None,
) -> MMseqs2Provenance:
    return MMseqs2Provenance(
        backend=_MMSEQS2_BACKEND,
        mode=mode,
        runtime_available=bool(runtime and runtime.available),
        executable=runtime.executable if runtime is not None else None,
        version=runtime.version if runtime is not None else None,
        command=tuple(command),
        fallback_used=False,
        reason=reason,
        input_records=input_records,
        reference_records=reference_records,
    )


def _parse_alignment_hits(path: Path) -> Iterable[MMseqs2AlignmentHit]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != len(_ALIGNMENT_OUTPUT_COLUMNS):
            raise ValueError(
                f"expected {len(_ALIGNMENT_OUTPUT_COLUMNS)} MMseqs2 alignment columns, "
                f"received {len(parts)}"
            )
        yield MMseqs2AlignmentHit(
            query_id=parts[0],
            target_id=parts[1],
            percent_identity=float(parts[2]),
            alignment_length=int(parts[3]),
            mismatches=int(parts[4]),
            gap_openings=int(parts[5]),
            query_start=int(parts[6]),
            query_end=int(parts[7]),
            target_start=int(parts[8]),
            target_end=int(parts[9]),
            evalue=float(parts[10]),
            bit_score=float(parts[11]),
            query_coverage=float(parts[12]),
            target_coverage=float(parts[13]),
        )


def _parse_cluster_members(path: Path) -> Iterable[MMseqs2ClusterMember]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        representative, member = line.split("\t", maxsplit=1)
        yield MMseqs2ClusterMember(
            cluster_id=representative,
            sequence_id=member,
            is_representative=representative == member,
        )


def _write_fasta(path: Path, sequences: Sequence[MMseqs2Sequence]) -> None:
    lines: list[str] = []
    for sequence in sequences:
        lines.append(sequence.to_fasta_header())
        lines.append(sequence.sequence)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _cluster_output_path(output_prefix: Path) -> Path:
    return output_prefix.with_name(f"{output_prefix.name}_cluster.tsv")


def _normalize_sequence(sequence: str) -> str:
    return "".join(character for character in str(sequence).upper() if not character.isspace())


def _extract_first_line(value: str | None) -> str:
    if not value:
        return ""
    return value.splitlines()[0].strip()


def _format_float(value: float) -> str:
    return format(float(value), "g")


def _looks_like_path(value: str) -> bool:
    separators = tuple(separator for separator in (os.sep, os.altsep) if separator)
    return any(separator in value for separator in separators) or value.endswith(".exe")


__all__ = [
    "BackendStatus",
    "MMseqs2AlignmentHit",
    "MMseqs2AlignmentResult",
    "MMseqs2Backend",
    "MMseqs2ClusteringResult",
    "MMseqs2ClusterMember",
    "MMseqs2Mode",
    "MMseqs2Provenance",
    "MMseqs2RuntimeInfo",
    "MMseqs2Sequence",
]

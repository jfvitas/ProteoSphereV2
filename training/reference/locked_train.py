from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

Scalar = str | int | float | bool


@dataclass(frozen=True, slots=True)
class LockedTrainingBlocker:
    stage: str
    requested_backend: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "stage": self.stage,
            "requested_backend": self.requested_backend,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class LockedTrainingSpec:
    optimizer: str
    learning_rate: float
    batch_size: int
    epochs: int
    scheduler: str
    mixed_precision: bool
    source_path: str
    config: dict[str, Scalar]

    def to_dict(self) -> dict[str, object]:
        return {
            "optimizer": self.optimizer,
            "learning_rate": self.learning_rate,
            "batch_size": self.batch_size,
            "epochs": self.epochs,
            "scheduler": self.scheduler,
            "mixed_precision": self.mixed_precision,
            "source_path": self.source_path,
            "config": dict(self.config),
        }


@dataclass(frozen=True, slots=True)
class LockedTrainingRuntimeStatus:
    stage: str
    requested_backend: str
    resolved_backend: str
    backend_ready: bool
    contract_fidelity: str
    provenance: dict[str, object] = field(default_factory=dict)
    blocker: LockedTrainingBlocker | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "stage": self.stage,
            "requested_backend": self.requested_backend,
            "resolved_backend": self.resolved_backend,
            "backend_ready": self.backend_ready,
            "contract_fidelity": self.contract_fidelity,
            "provenance": dict(self.provenance),
            "blocker": self.blocker.to_dict() if self.blocker is not None else None,
        }


@dataclass(frozen=True, slots=True)
class LockedLearningRatePoint:
    step: int
    learning_rate: float

    def to_dict(self) -> dict[str, object]:
        return {"step": self.step, "learning_rate": self.learning_rate}


@dataclass(frozen=True, slots=True)
class LockedTrainingPlan:
    optimizer_name: str
    scheduler_name: str
    precision_mode: str
    device_target: str
    batch_size: int
    gradient_accumulation_steps: int
    effective_batch_size: int
    epochs: int
    train_examples: int
    val_examples: int
    steps_per_epoch: int
    validation_steps: int
    optimizer_steps_per_epoch: int
    total_optimizer_steps: int
    learning_rate_points: tuple[LockedLearningRatePoint, ...]
    deterministic_seed: int
    plan_signature: str
    status: LockedTrainingRuntimeStatus

    def to_dict(self) -> dict[str, object]:
        return {
            "optimizer_name": self.optimizer_name,
            "scheduler_name": self.scheduler_name,
            "precision_mode": self.precision_mode,
            "device_target": self.device_target,
            "batch_size": self.batch_size,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "effective_batch_size": self.effective_batch_size,
            "epochs": self.epochs,
            "train_examples": self.train_examples,
            "val_examples": self.val_examples,
            "steps_per_epoch": self.steps_per_epoch,
            "validation_steps": self.validation_steps,
            "optimizer_steps_per_epoch": self.optimizer_steps_per_epoch,
            "total_optimizer_steps": self.total_optimizer_steps,
            "learning_rate_points": [point.to_dict() for point in self.learning_rate_points],
            "deterministic_seed": self.deterministic_seed,
            "plan_signature": self.plan_signature,
            "status": self.status.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class LockedTrainingState:
    phase: str
    current_epoch: int
    current_batch_in_epoch: int
    completed_optimizer_steps: int
    next_learning_rate: float
    best_metric: float | None
    checkpoint_tag: str
    deterministic_seed: int
    rng_streams: dict[str, int]
    state_signature: str

    def to_dict(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "current_epoch": self.current_epoch,
            "current_batch_in_epoch": self.current_batch_in_epoch,
            "completed_optimizer_steps": self.completed_optimizer_steps,
            "next_learning_rate": self.next_learning_rate,
            "best_metric": self.best_metric,
            "checkpoint_tag": self.checkpoint_tag,
            "deterministic_seed": self.deterministic_seed,
            "rng_streams": dict(self.rng_streams),
            "state_signature": self.state_signature,
        }


@dataclass(frozen=True, slots=True)
class LockedTrainingBackendResult:
    spec: LockedTrainingSpec
    plan: LockedTrainingPlan
    state: LockedTrainingState
    blockers: tuple[LockedTrainingBlocker, ...]

    @property
    def blocked_stages(self) -> tuple[str, ...]:
        return tuple(blocker.stage for blocker in self.blockers)

    def to_dict(self) -> dict[str, object]:
        return {
            "spec": self.spec.to_dict(),
            "plan": self.plan.to_dict(),
            "state": self.state.to_dict(),
            "blockers": [blocker.to_dict() for blocker in self.blockers],
        }


def load_locked_training_spec(repo_root: str | Path | None = None) -> LockedTrainingSpec:
    root = Path(repo_root or Path(__file__).resolve().parents[2]).resolve()
    path = (
        root
        / "master_handoff_package"
        / "01_LOCKDOWN_SPEC"
        / "training"
        / "default_training.yaml"
    )
    config = _parse_simple_yaml_mapping(path)

    optimizer = str(config.get("optimizer", "")).strip().lower()
    scheduler = str(config.get("scheduler", "")).strip().lower()
    if not optimizer or not scheduler:
        raise ValueError(f"Locked training spec is missing optimizer/scheduler in {path}")

    if "lr" not in config or "batch_size" not in config or "epochs" not in config:
        raise ValueError(f"Locked training spec is missing required scalar fields in {path}")

    return LockedTrainingSpec(
        optimizer=optimizer,
        learning_rate=float(config["lr"]),
        batch_size=int(config["batch_size"]),
        epochs=int(config["epochs"]),
        scheduler=scheduler,
        mixed_precision=bool(config.get("mixed_precision", False)),
        source_path=_relative_path(root, path),
        config=config,
    )


class LockedReferenceTrainingBackend:
    def __init__(self, *, repo_root: str | Path | None = None) -> None:
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[2]).resolve()
        self.spec = load_locked_training_spec(self.repo_root)

    def prepare(
        self,
        *,
        train_examples: int,
        val_examples: int = 0,
        gradient_accumulation_steps: int = 1,
        deterministic_seed: int = 0,
        device_target: str = "cpu",
        mixed_precision_dtype: str | None = None,
    ) -> LockedTrainingBackendResult:
        if train_examples < 0 or val_examples < 0:
            raise ValueError("train_examples and val_examples must be non-negative")
        if gradient_accumulation_steps < 1:
            raise ValueError("gradient_accumulation_steps must be at least 1")

        precision_mode = _resolve_precision_mode(
            mixed_precision=self.spec.mixed_precision,
            mixed_precision_dtype=mixed_precision_dtype,
        )
        steps_per_epoch = _ceil_div(train_examples, self.spec.batch_size)
        validation_steps = _ceil_div(val_examples, self.spec.batch_size)
        optimizer_steps_per_epoch = _ceil_div(steps_per_epoch, gradient_accumulation_steps)
        total_optimizer_steps = optimizer_steps_per_epoch * self.spec.epochs
        learning_rate_points = _cosine_schedule_preview(
            base_learning_rate=self.spec.learning_rate,
            total_optimizer_steps=total_optimizer_steps,
        )

        requested_backend = (
            f"{self.spec.optimizer}+{self.spec.scheduler}+{precision_mode}"
        )
        blocker = LockedTrainingBlocker(
            stage="trainer_runtime",
            requested_backend=requested_backend,
            reason=(
                "The repository can load the locked training spec and derive a deterministic "
                "plan/state contract, but no real deep-learning trainer runtime is wired under "
                "training/reference yet."
            ),
        )

        real_components = [
            "locked YAML config loading",
            "deterministic batch/step accounting",
            "deterministic cosine learning-rate preview",
            "deterministic initial training-state fingerprint",
        ]
        abstracted_components = [
            "AdamW optimizer object construction",
            "cosine scheduler object construction",
            "mixed-precision autocast or grad-scaler execution",
            "parameter updates and backward passes",
            "checkpoint serialization",
        ]
        provenance = {
            "config_source_path": self.spec.source_path,
            "real_components": real_components,
            "abstracted_components": abstracted_components,
            "device_target": device_target,
            "notes": (
                "This backend is intentionally honest: it materializes the locked training "
                "contract without claiming that a torch trainer loop already exists."
            ),
        }
        status = LockedTrainingRuntimeStatus(
            stage="trainer_runtime",
            requested_backend=requested_backend,
            resolved_backend="contract-plan-only",
            backend_ready=False,
            contract_fidelity="configuration-and-plan-only",
            provenance=provenance,
            blocker=blocker,
        )

        plan_signature = _fingerprint(
            {
                "optimizer": self.spec.optimizer,
                "scheduler": self.spec.scheduler,
                "precision_mode": precision_mode,
                "device_target": device_target,
                "learning_rate": self.spec.learning_rate,
                "batch_size": self.spec.batch_size,
                "epochs": self.spec.epochs,
                "train_examples": train_examples,
                "val_examples": val_examples,
                "gradient_accumulation_steps": gradient_accumulation_steps,
                "deterministic_seed": deterministic_seed,
                "learning_rate_points": [point.to_dict() for point in learning_rate_points],
            }
        )
        plan = LockedTrainingPlan(
            optimizer_name=self.spec.optimizer,
            scheduler_name=self.spec.scheduler,
            precision_mode=precision_mode,
            device_target=device_target,
            batch_size=self.spec.batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            effective_batch_size=self.spec.batch_size * gradient_accumulation_steps,
            epochs=self.spec.epochs,
            train_examples=train_examples,
            val_examples=val_examples,
            steps_per_epoch=steps_per_epoch,
            validation_steps=validation_steps,
            optimizer_steps_per_epoch=optimizer_steps_per_epoch,
            total_optimizer_steps=total_optimizer_steps,
            learning_rate_points=learning_rate_points,
            deterministic_seed=deterministic_seed,
            plan_signature=plan_signature,
            status=status,
        )

        next_learning_rate = (
            learning_rate_points[0].learning_rate
            if learning_rate_points
            else self.spec.learning_rate
        )
        state_signature = _fingerprint(
            {
                "plan_signature": plan_signature,
                "phase": "blocked",
                "current_epoch": 0,
                "current_batch_in_epoch": 0,
                "completed_optimizer_steps": 0,
                "next_learning_rate": next_learning_rate,
                "deterministic_seed": deterministic_seed,
            }
        )
        state = LockedTrainingState(
            phase="blocked",
            current_epoch=0,
            current_batch_in_epoch=0,
            completed_optimizer_steps=0,
            next_learning_rate=next_learning_rate,
            best_metric=None,
            checkpoint_tag=f"seed-{deterministic_seed:04d}-epoch-000",
            deterministic_seed=deterministic_seed,
            rng_streams={
                "python": deterministic_seed,
                "numpy": deterministic_seed,
                "torch": deterministic_seed,
            },
            state_signature=state_signature,
        )
        return LockedTrainingBackendResult(
            spec=self.spec,
            plan=plan,
            state=state,
            blockers=(blocker,),
        )


def prepare_locked_reference_training(
    *,
    train_examples: int,
    val_examples: int = 0,
    gradient_accumulation_steps: int = 1,
    deterministic_seed: int = 0,
    device_target: str = "cpu",
    mixed_precision_dtype: str | None = None,
    repo_root: str | Path | None = None,
) -> LockedTrainingBackendResult:
    return LockedReferenceTrainingBackend(repo_root=repo_root).prepare(
        train_examples=train_examples,
        val_examples=val_examples,
        gradient_accumulation_steps=gradient_accumulation_steps,
        deterministic_seed=deterministic_seed,
        device_target=device_target,
        mixed_precision_dtype=mixed_precision_dtype,
    )


def _ceil_div(numerator: int, denominator: int) -> int:
    if numerator <= 0:
        return 0
    return (numerator + denominator - 1) // denominator


def _cosine_schedule_preview(
    *,
    base_learning_rate: float,
    total_optimizer_steps: int,
) -> tuple[LockedLearningRatePoint, ...]:
    if total_optimizer_steps <= 0:
        return (LockedLearningRatePoint(step=0, learning_rate=float(base_learning_rate)),)

    preview_steps = sorted(
        {
            0,
            total_optimizer_steps // 3,
            (2 * total_optimizer_steps) // 3,
            total_optimizer_steps - 1,
        }
    )
    denominator = max(total_optimizer_steps - 1, 1)
    points = []
    for step in preview_steps:
        cosine = 0.5 * (1.0 + math.cos(math.pi * float(step) / float(denominator)))
        points.append(
            LockedLearningRatePoint(
                step=step,
                learning_rate=float(base_learning_rate) * cosine,
            )
        )
    return tuple(points)


def _resolve_precision_mode(*, mixed_precision: bool, mixed_precision_dtype: str | None) -> str:
    if not mixed_precision:
        return "fp32"
    if mixed_precision_dtype is None:
        return "fp16"
    value = str(mixed_precision_dtype).strip().lower()
    if value not in {"fp16", "bf16"}:
        raise ValueError("mixed_precision_dtype must be one of: fp16, bf16")
    return value


def _parse_simple_yaml_mapping(path: Path) -> dict[str, Scalar]:
    config: dict[str, Scalar] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError(f"Unsupported YAML line in {path}: {raw_line!r}")
        config[key.strip()] = _parse_scalar(value.strip())
    return config


def _parse_scalar(value: str) -> Scalar:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if re.fullmatch(r"[+-]?\d+", value):
        return int(value)
    if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?", value, re.IGNORECASE):
        return float(value)
    return value


def _fingerprint(payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _relative_path(root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")


__all__ = [
    "LockedLearningRatePoint",
    "LockedReferenceTrainingBackend",
    "LockedTrainingBackendResult",
    "LockedTrainingBlocker",
    "LockedTrainingPlan",
    "LockedTrainingRuntimeStatus",
    "LockedTrainingSpec",
    "LockedTrainingState",
    "load_locked_training_spec",
    "prepare_locked_reference_training",
]

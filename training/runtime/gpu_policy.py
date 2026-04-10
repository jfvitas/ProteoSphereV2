from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

DEFAULT_GPU_WORKER_LIMIT = 1
DEFAULT_GPU_TITLE_MARKERS = ("train",)
DEFAULT_GPU_DEVICE_TARGETS = (
    "cuda",
    "gpu",
    "single_cuda_gpu",
    "multi_gpu_data_parallel",
    "distributed_data_parallel",
    "fsdp",
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_text(value: Any) -> str:
    return _clean_text(value).casefold().replace("-", "_").replace(" ", "_")


def _normalize_text_tuple(values: Any) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        text = _normalize_text(values)
        return (text,) if text else ()
    if not isinstance(values, Iterable):
        values = (values,)
    ordered: dict[str, str] = {}
    for value in values:
        text = _normalize_text(value)
        if text:
            ordered.setdefault(text, text)
    return tuple(ordered.values())


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _value_get(value: Any, *keys: str) -> Any:
    if isinstance(value, Mapping):
        for key in keys:
            if key in value and value[key] is not None:
                return value[key]
        return None
    for key in keys:
        if hasattr(value, key):
            result = getattr(value, key)
            if result is not None:
                return result
    return None


def _coerce_provenance(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("provenance must be a mapping")
    return dict(value)


def _gpu_signals(
    *,
    title: Any = "",
    requested_device: Any = "",
    requires_gpu: Any = False,
    gpu_heavy: Any = False,
    gpu_title_markers: tuple[str, ...] = DEFAULT_GPU_TITLE_MARKERS,
    gpu_device_targets: tuple[str, ...] = DEFAULT_GPU_DEVICE_TARGETS,
) -> tuple[bool, tuple[str, ...]]:
    markers = _normalize_text_tuple(gpu_title_markers)
    device_targets = _normalize_text_tuple(gpu_device_targets)
    signals: list[str] = []

    if _normalize_bool(gpu_heavy):
        signals.append("gpu_heavy")
    if _normalize_bool(requires_gpu):
        signals.append("requires_gpu")

    normalized_device = _normalize_text(requested_device)
    if normalized_device and normalized_device in device_targets:
        signals.append(f"requested_device:{normalized_device}")

    normalized_title = _clean_text(title).casefold()
    for marker in markers:
        if marker and marker in normalized_title:
            signals.append(f"title_marker:{marker}")
            break

    return bool(signals), tuple(signals)


@dataclass(frozen=True, slots=True)
class GPUJobRequest:
    task_id: str = ""
    title: str = ""
    requested_device: str = "cpu"
    requires_gpu: bool = False
    provenance: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: Any) -> GPUJobRequest:
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping) and not hasattr(value, "__dict__"):
            raise TypeError("value must be a GPUJobRequest or mapping-like object")

        provenance = _coerce_provenance(
            _value_get(value, "provenance", "provenance_record")
        )
        return cls(
            task_id=_clean_text(_value_get(value, "task_id", "id", "request_id")),
            title=_clean_text(_value_get(value, "title", "name")),
            requested_device=_normalize_text(
                _value_get(
                    value,
                    "requested_device",
                    "device_target",
                    "device",
                    "runtime",
                )
            )
            or "cpu",
            requires_gpu=_normalize_bool(
                _value_get(value, "requires_gpu", "gpu_required", "gpu_heavy")
            ),
            provenance=provenance,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "requested_device": self.requested_device,
            "requires_gpu": self.requires_gpu,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class GPUWorkerSnapshot:
    task_id: str = ""
    title: str = ""
    gpu_heavy: bool = False
    device_target: str = "cpu"
    provenance: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: Any) -> GPUWorkerSnapshot:
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping) and not hasattr(value, "__dict__"):
            raise TypeError("value must be a GPUWorkerSnapshot or mapping-like object")

        provenance = _coerce_provenance(
            _value_get(value, "provenance", "provenance_record")
        )
        gpu_heavy, _signals = _gpu_signals(
            title=_value_get(value, "title", "name"),
            requested_device=_value_get(
                value,
                "device_target",
                "requested_device",
                "device",
                "runtime",
            ),
            requires_gpu=_value_get(value, "requires_gpu", "gpu_required"),
            gpu_heavy=_value_get(value, "gpu_heavy"),
        )
        return cls(
            task_id=_clean_text(_value_get(value, "task_id", "id", "worker_id")),
            title=_clean_text(_value_get(value, "title", "name")),
            gpu_heavy=gpu_heavy,
            device_target=_normalize_text(
                _value_get(value, "device_target", "requested_device", "device", "runtime")
            )
            or "cpu",
            provenance=provenance,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "gpu_heavy": self.gpu_heavy,
            "device_target": self.device_target,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class GPUSchedulingDecision:
    task_id: str = ""
    allowed: bool = False
    assignment: str = "defer"
    gpu_required: bool = False
    active_gpu_workers: int = 0
    gpu_worker_limit: int = 0
    gpu_slots_remaining: int = 0
    matched_signals: tuple[str, ...] = ()
    reason: str = ""
    request: dict[str, object] = field(default_factory=dict)
    policy_name: str = "gpu_capacity_policy_v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "allowed": self.allowed,
            "assignment": self.assignment,
            "gpu_required": self.gpu_required,
            "active_gpu_workers": self.active_gpu_workers,
            "gpu_worker_limit": self.gpu_worker_limit,
            "gpu_slots_remaining": self.gpu_slots_remaining,
            "matched_signals": list(self.matched_signals),
            "reason": self.reason,
            "request": dict(self.request),
            "policy_name": self.policy_name,
        }


@dataclass(frozen=True, slots=True)
class GPUSchedulingPolicy:
    gpu_worker_limit: int = DEFAULT_GPU_WORKER_LIMIT
    gpu_title_markers: tuple[str, ...] = DEFAULT_GPU_TITLE_MARKERS
    gpu_device_targets: tuple[str, ...] = DEFAULT_GPU_DEVICE_TARGETS
    policy_name: str = "gpu_capacity_policy_v1"

    def __post_init__(self) -> None:
        if self.gpu_worker_limit < 0:
            raise ValueError("gpu_worker_limit must be >= 0")
        object.__setattr__(
            self,
            "gpu_title_markers",
            _normalize_text_tuple(self.gpu_title_markers),
        )
        object.__setattr__(
            self,
            "gpu_device_targets",
            _normalize_text_tuple(self.gpu_device_targets),
        )
        object.__setattr__(
            self,
            "policy_name",
            _clean_text(self.policy_name) or "gpu_capacity_policy_v1",
        )

    def classify(self, request: Any) -> tuple[bool, tuple[str, ...]]:
        job = GPUJobRequest.from_value(request)
        return _gpu_signals(
            title=job.title,
            requested_device=job.requested_device,
            requires_gpu=job.requires_gpu,
            gpu_title_markers=self.gpu_title_markers,
            gpu_device_targets=self.gpu_device_targets,
        )

    def active_gpu_worker_count(self, active_workers: Iterable[Any]) -> int:
        count = 0
        for worker in active_workers:
            snapshot = GPUWorkerSnapshot.from_value(worker)
            gpu_required, _signals = _gpu_signals(
                title=snapshot.title,
                requested_device=snapshot.device_target,
                requires_gpu=snapshot.gpu_heavy,
                gpu_heavy=snapshot.gpu_heavy,
                gpu_title_markers=self.gpu_title_markers,
                gpu_device_targets=self.gpu_device_targets,
            )
            if gpu_required:
                count += 1
        return count

    def gpu_slots_remaining(self, active_workers: Iterable[Any]) -> int:
        return max(self.gpu_worker_limit - self.active_gpu_worker_count(active_workers), 0)

    def evaluate(
        self,
        request: Any,
        *,
        active_workers: Iterable[Any] = (),
    ) -> GPUSchedulingDecision:
        job = GPUJobRequest.from_value(request)
        gpu_required, matched_signals = self.classify(job)
        active_gpu_workers = self.active_gpu_worker_count(active_workers)
        slots_remaining = max(self.gpu_worker_limit - active_gpu_workers, 0)

        if gpu_required and slots_remaining <= 0:
            return GPUSchedulingDecision(
                task_id=job.task_id,
                allowed=False,
                assignment="defer",
                gpu_required=True,
                active_gpu_workers=active_gpu_workers,
                gpu_worker_limit=self.gpu_worker_limit,
                gpu_slots_remaining=slots_remaining,
                matched_signals=matched_signals,
                reason=(
                    f"GPU capacity exhausted: {active_gpu_workers} of "
                    f"{self.gpu_worker_limit} GPU worker slots are occupied."
                ),
                request=job.to_dict(),
                policy_name=self.policy_name,
            )

        if gpu_required:
            return GPUSchedulingDecision(
                task_id=job.task_id,
                allowed=True,
                assignment="gpu",
                gpu_required=True,
                active_gpu_workers=active_gpu_workers,
                gpu_worker_limit=self.gpu_worker_limit,
                gpu_slots_remaining=slots_remaining,
                matched_signals=matched_signals,
                reason=(
                    f"GPU-backed request accepted with {slots_remaining} GPU worker "
                    f"slot(s) remaining."
                ),
                request=job.to_dict(),
                policy_name=self.policy_name,
            )

        return GPUSchedulingDecision(
            task_id=job.task_id,
            allowed=True,
            assignment="cpu",
            gpu_required=False,
            active_gpu_workers=active_gpu_workers,
            gpu_worker_limit=self.gpu_worker_limit,
            gpu_slots_remaining=slots_remaining,
            matched_signals=matched_signals,
            reason="CPU-compatible request; no GPU slot required.",
            request=job.to_dict(),
            policy_name=self.policy_name,
        )


def evaluate_gpu_request(
    request: Any,
    *,
    active_workers: Iterable[Any] = (),
    gpu_worker_limit: int = DEFAULT_GPU_WORKER_LIMIT,
    gpu_title_markers: tuple[str, ...] = DEFAULT_GPU_TITLE_MARKERS,
    gpu_device_targets: tuple[str, ...] = DEFAULT_GPU_DEVICE_TARGETS,
) -> GPUSchedulingDecision:
    policy = GPUSchedulingPolicy(
        gpu_worker_limit=gpu_worker_limit,
        gpu_title_markers=gpu_title_markers,
        gpu_device_targets=gpu_device_targets,
    )
    return policy.evaluate(request, active_workers=active_workers)


def capacity_available(
    request: Any,
    *,
    active_workers: Iterable[Any] = (),
    gpu_worker_limit: int = DEFAULT_GPU_WORKER_LIMIT,
    gpu_title_markers: tuple[str, ...] = DEFAULT_GPU_TITLE_MARKERS,
    gpu_device_targets: tuple[str, ...] = DEFAULT_GPU_DEVICE_TARGETS,
) -> bool:
    return evaluate_gpu_request(
        request,
        active_workers=active_workers,
        gpu_worker_limit=gpu_worker_limit,
        gpu_title_markers=gpu_title_markers,
        gpu_device_targets=gpu_device_targets,
    ).allowed


def count_active_gpu_workers(
    active_workers: Iterable[Any],
    *,
    gpu_title_markers: tuple[str, ...] = DEFAULT_GPU_TITLE_MARKERS,
    gpu_device_targets: tuple[str, ...] = DEFAULT_GPU_DEVICE_TARGETS,
) -> int:
    return GPUSchedulingPolicy(
        gpu_title_markers=gpu_title_markers,
        gpu_device_targets=gpu_device_targets,
    ).active_gpu_worker_count(active_workers)


def gpu_slots_remaining(
    active_workers: Iterable[Any],
    *,
    gpu_worker_limit: int = DEFAULT_GPU_WORKER_LIMIT,
    gpu_title_markers: tuple[str, ...] = DEFAULT_GPU_TITLE_MARKERS,
    gpu_device_targets: tuple[str, ...] = DEFAULT_GPU_DEVICE_TARGETS,
) -> int:
    return GPUSchedulingPolicy(
        gpu_worker_limit=gpu_worker_limit,
        gpu_title_markers=gpu_title_markers,
        gpu_device_targets=gpu_device_targets,
    ).gpu_slots_remaining(active_workers)


__all__ = [
    "DEFAULT_GPU_DEVICE_TARGETS",
    "DEFAULT_GPU_TITLE_MARKERS",
    "DEFAULT_GPU_WORKER_LIMIT",
    "GPUSchedulingDecision",
    "GPUSchedulingPolicy",
    "GPUJobRequest",
    "GPUWorkerSnapshot",
    "capacity_available",
    "count_active_gpu_workers",
    "evaluate_gpu_request",
    "gpu_slots_remaining",
]

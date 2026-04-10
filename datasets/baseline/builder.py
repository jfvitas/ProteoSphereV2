from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from datasets.baseline.schema import BaselineDatasetExample, BaselineDatasetSchema, JSONValue


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Iterable):
        return tuple(values)
    return (values,)


def _normalize_examples(
    examples: Iterable[BaselineDatasetExample | Mapping[str, Any]],
) -> tuple[BaselineDatasetExample, ...]:
    normalized: list[BaselineDatasetExample] = []
    for example in examples:
        if isinstance(example, BaselineDatasetExample):
            normalized.append(example)
            continue
        if not isinstance(example, Mapping):
            raise TypeError("examples must contain BaselineDatasetExample objects or mappings")
        normalized.append(BaselineDatasetExample.from_dict(example))
    return tuple(normalized)


def _normalize_text_tuple(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = str(value or "").strip()
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _normalize_json_mapping(value: Mapping[str, Any] | None) -> dict[str, JSONValue]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("metadata must be a mapping")
    return dict(value)


@dataclass(frozen=True, slots=True)
class BaselineDatasetBuilder:
    dataset_id: str
    schema_version: int = 1
    requested_modalities: tuple[str, ...] = field(default_factory=tuple)
    package_id: str | None = None
    package_state: str | None = None
    created_at: Any | None = None
    source_packages: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, JSONValue] = field(default_factory=dict)

    def build(
        self,
        examples: Iterable[BaselineDatasetExample | Mapping[str, Any]],
    ) -> BaselineDatasetSchema:
        normalized_examples = _normalize_examples(examples)
        if not normalized_examples:
            raise ValueError("examples must not be empty")
        return BaselineDatasetSchema(
            dataset_id=self.dataset_id,
            schema_version=self.schema_version,
            examples=normalized_examples,
            requested_modalities=_normalize_text_tuple(self.requested_modalities),
            package_id=self.package_id,
            package_state=self.package_state,
            created_at=self.created_at,
            source_packages=_normalize_text_tuple(self.source_packages),
            notes=_normalize_text_tuple(self.notes),
            metadata=_normalize_json_mapping(self.metadata),
        )


def build_baseline_dataset(
    examples: Iterable[BaselineDatasetExample | Mapping[str, Any]],
    *,
    dataset_id: str,
    schema_version: int = 1,
    requested_modalities: Iterable[str] = (),
    package_id: str | None = None,
    package_state: str | None = None,
    created_at: Any | None = None,
    source_packages: Iterable[str] = (),
    notes: Iterable[str] = (),
    metadata: Mapping[str, JSONValue] | None = None,
) -> BaselineDatasetSchema:
    return BaselineDatasetBuilder(
        dataset_id=dataset_id,
        schema_version=schema_version,
        requested_modalities=tuple(requested_modalities),
        package_id=package_id,
        package_state=package_state,
        created_at=created_at,
        source_packages=tuple(source_packages),
        notes=tuple(notes),
        metadata=metadata or {},
    ).build(examples)


__all__ = ["BaselineDatasetBuilder", "build_baseline_dataset"]

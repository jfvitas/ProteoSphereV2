from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

RecipeRuleMode = Literal["all", "any", "none"]
RecipeRuleOperator = Literal[
    "eq",
    "neq",
    "in",
    "contains",
    "ge",
    "le",
    "truthy",
    "falsy",
]
LeakageScope = Literal["accession", "canonical_id", "custom"]

_RULE_MODES = {"all", "any", "none"}
_RULE_OPERATORS = {"eq", "neq", "in", "contains", "ge", "le", "truthy", "falsy"}
_LEAKAGE_SCOPES = {"accession", "canonical_id", "custom"}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _optional_text(value: Any) -> str | None:
    text = _clean_text(value)
    return text or None


def _required_text(value: Any, field_name: str) -> str:
    text = _clean_text(value)
    if not text:
        raise ValueError(f"{field_name} must be a non-empty string")
    return text


def _iter_values(values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        return (values,)
    if isinstance(values, Iterable):
        return tuple(values)
    return (values,)


def _clean_text_tuple(values: Any) -> tuple[str, ...]:
    ordered: dict[str, str] = {}
    for value in _iter_values(values):
        text = _clean_text(value)
        if text:
            ordered.setdefault(text.casefold(), text)
    return tuple(ordered.values())


def _normalize_int_or_none(value: Any, field_name: str) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be an integer or None")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field_name} must be an integer or None") from exc


def _normalize_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise TypeError(f"{field_name} must be a bool")


def _normalize_mode(value: Any) -> RecipeRuleMode:
    mode = _clean_text(value).casefold()
    if mode not in _RULE_MODES:
        raise ValueError(f"unsupported rule mode: {value!r}")
    return mode  # type: ignore[return-value]


def _normalize_operator(value: Any) -> RecipeRuleOperator:
    operator = _clean_text(value).replace("-", "_").replace(" ", "_").casefold()
    if operator not in _RULE_OPERATORS:
        raise ValueError(f"unsupported rule operator: {value!r}")
    return operator  # type: ignore[return-value]


def _normalize_leakage_scope(value: Any) -> LeakageScope:
    scope = _clean_text(value).replace("-", "_").replace(" ", "_").casefold()
    if scope not in _LEAKAGE_SCOPES:
        raise ValueError(f"unsupported leakage scope: {value!r}")
    return scope  # type: ignore[return-value]


def _candidate_values(candidate: Mapping[str, Any], field_name: str) -> tuple[Any, ...]:
    value = candidate.get(field_name)
    if value is None:
        return ()
    return _iter_values(value)


@dataclass(frozen=True, slots=True)
class RecipeSelectionRule:
    field_name: str
    operator: RecipeRuleOperator
    value: Any = None
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "field_name", _required_text(self.field_name, "field_name"))
        object.__setattr__(self, "operator", _normalize_operator(self.operator))
        object.__setattr__(self, "description", _clean_text(self.description))
        if self.operator in {"eq", "neq", "in", "contains", "ge", "le"} and self.value is None:
            raise ValueError(f"{self.operator} rules require a value")

    def evaluate(self, candidate: Mapping[str, Any]) -> bool:
        values = _candidate_values(candidate, self.field_name)
        if self.operator == "truthy":
            return any(bool(value) for value in values)
        if self.operator == "falsy":
            return not any(bool(value) for value in values)
        if self.operator == "eq":
            return any(value == self.value for value in values)
        if self.operator == "neq":
            return all(value != self.value for value in values) or not values
        if self.operator == "in":
            allowed = set(_iter_values(self.value))
            return any(value in allowed for value in values)
        if self.operator == "contains":
            needles = {_clean_text(value).casefold() for value in _iter_values(self.value)}
            haystack = {_clean_text(value).casefold() for value in values}
            return needles.issubset(haystack)
        if self.operator == "ge":
            return any(value is not None and value >= self.value for value in values)
        if self.operator == "le":
            return any(value is not None and value <= self.value for value in values)
        raise ValueError(f"unsupported operator: {self.operator!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "operator": self.operator,
            "value": self.value,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RecipeSelectionRule:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            field_name=payload.get("field_name") or payload.get("field") or "",
            operator=payload.get("operator") or "eq",
            value=payload.get("value"),
            description=payload.get("description") or payload.get("label") or "",
        )


@dataclass(frozen=True, slots=True)
class RecipeRuleGroup:
    mode: RecipeRuleMode
    rules: tuple[RecipeRuleNode, ...]
    description: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", _normalize_mode(self.mode))
        normalized_rules = tuple(self.rules)
        object.__setattr__(self, "rules", normalized_rules)
        object.__setattr__(self, "description", _clean_text(self.description))
        if not normalized_rules:
            raise ValueError("rule groups must contain at least one rule")

    def evaluate(self, candidate: Mapping[str, Any]) -> bool:
        results = tuple(rule.evaluate(candidate) for rule in self.rules)
        if self.mode == "all":
            return all(results)
        if self.mode == "any":
            return any(results)
        return not any(results)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "rules": [rule.to_dict() for rule in self.rules],
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RecipeRuleGroup:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            mode=payload.get("mode") or "all",
            rules=tuple(recipe_rule_from_dict(item) for item in _iter_values(payload.get("rules"))),
            description=payload.get("description") or payload.get("label") or "",
        )


RecipeRuleNode = RecipeSelectionRule | RecipeRuleGroup


def recipe_rule_from_dict(payload: Mapping[str, Any]) -> RecipeRuleNode:
    if "rules" in payload:
        return RecipeRuleGroup.from_dict(payload)
    return RecipeSelectionRule.from_dict(payload)


@dataclass(frozen=True, slots=True)
class RecipeCompletenessPolicy:
    requested_modalities: tuple[str, ...] = ()
    max_missing_modalities: int = 0
    min_lane_depth: int | None = None
    allow_thin_coverage: bool = False
    allow_mixed_evidence: bool = False
    require_packet_ready: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "requested_modalities",
            _clean_text_tuple(self.requested_modalities),
        )
        object.__setattr__(
            self,
            "max_missing_modalities",
            _normalize_int_or_none(self.max_missing_modalities, "max_missing_modalities") or 0,
        )
        object.__setattr__(
            self,
            "min_lane_depth",
            _normalize_int_or_none(self.min_lane_depth, "min_lane_depth"),
        )
        object.__setattr__(
            self,
            "allow_thin_coverage",
            _normalize_bool(self.allow_thin_coverage, "allow_thin_coverage"),
        )
        object.__setattr__(
            self,
            "allow_mixed_evidence",
            _normalize_bool(self.allow_mixed_evidence, "allow_mixed_evidence"),
        )
        object.__setattr__(
            self,
            "require_packet_ready",
            _normalize_bool(self.require_packet_ready, "require_packet_ready"),
        )
        if self.max_missing_modalities < 0:
            raise ValueError("max_missing_modalities must be >= 0")

    def evaluate(self, candidate: Mapping[str, Any]) -> tuple[bool, tuple[str, ...]]:
        reasons: list[str] = []
        missing_modalities = _clean_text_tuple(candidate.get("missing_modalities"))
        lane_depth = _normalize_int_or_none(candidate.get("lane_depth"), "lane_depth") or 0
        thin_coverage = bool(candidate.get("thin_coverage", False))
        mixed_evidence = bool(candidate.get("mixed_evidence", False))
        packet_ready = candidate.get("packet_ready")

        if len(missing_modalities) > self.max_missing_modalities:
            missing_count = len(missing_modalities)
            reasons.append(
                f"missing_modalities={missing_count} exceeds {self.max_missing_modalities}"
            )
        if self.min_lane_depth is not None and lane_depth < self.min_lane_depth:
            reasons.append(f"lane_depth={lane_depth} below {self.min_lane_depth}")
        if thin_coverage and not self.allow_thin_coverage:
            reasons.append("thin_coverage is not allowed")
        if mixed_evidence and not self.allow_mixed_evidence:
            reasons.append("mixed_evidence is not allowed")
        if self.require_packet_ready and packet_ready is not True:
            reasons.append("packet_ready is required")

        return (not reasons, tuple(reasons))

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_modalities": list(self.requested_modalities),
            "max_missing_modalities": self.max_missing_modalities,
            "min_lane_depth": self.min_lane_depth,
            "allow_thin_coverage": self.allow_thin_coverage,
            "allow_mixed_evidence": self.allow_mixed_evidence,
            "require_packet_ready": self.require_packet_ready,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RecipeCompletenessPolicy:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        requested_modalities = (
            payload.get("requested_modalities") or payload.get("modalities") or ()
        )
        return cls(
            requested_modalities=requested_modalities,
            max_missing_modalities=payload.get("max_missing_modalities", 0),
            min_lane_depth=payload.get("min_lane_depth"),
            allow_thin_coverage=payload.get("allow_thin_coverage", False),
            allow_mixed_evidence=payload.get("allow_mixed_evidence", False),
            require_packet_ready=payload.get("require_packet_ready", False),
        )


@dataclass(frozen=True, slots=True)
class RecipeLeakagePolicy:
    scope: LeakageScope = "accession"
    key_field: str = "leakage_key"
    forbid_cross_split: bool = True
    blocked_key_values: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "scope", _normalize_leakage_scope(self.scope))
        object.__setattr__(self, "key_field", _required_text(self.key_field, "key_field"))
        object.__setattr__(
            self,
            "forbid_cross_split",
            _normalize_bool(self.forbid_cross_split, "forbid_cross_split"),
        )
        object.__setattr__(self, "blocked_key_values", _clean_text_tuple(self.blocked_key_values))

    def candidate_key(self, candidate: Mapping[str, Any]) -> str | None:
        key = _optional_text(candidate.get(self.key_field))
        if self.scope == "canonical_id" and not key:
            key = _optional_text(candidate.get("canonical_id"))
        if self.scope == "accession" and not key:
            key = _optional_text(candidate.get("accession"))
        return key

    def evaluate(
        self,
        candidate: Mapping[str, Any],
        *,
        occupied_keys: Iterable[str] = (),
    ) -> tuple[bool, tuple[str, ...]]:
        reasons: list[str] = []
        key = self.candidate_key(candidate)
        if not key:
            reasons.append(f"missing leakage key for field {self.key_field}")
            return (False, tuple(reasons))
        if key in self.blocked_key_values:
            reasons.append(f"leakage key {key!r} is blocked")
        if self.forbid_cross_split and key in {item for item in occupied_keys if _clean_text(item)}:
            reasons.append(f"leakage key {key!r} already assigned")
        return (not reasons, tuple(reasons))

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "key_field": self.key_field,
            "forbid_cross_split": self.forbid_cross_split,
            "blocked_key_values": list(self.blocked_key_values),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> RecipeLeakagePolicy:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        return cls(
            scope=payload.get("scope") or "accession",
            key_field=payload.get("key_field") or payload.get("field") or "leakage_key",
            forbid_cross_split=payload.get("forbid_cross_split", True),
            blocked_key_values=payload.get("blocked_key_values") or (),
        )


@dataclass(frozen=True, slots=True)
class RecipeEvaluationContext:
    split_name: str | None = None
    occupied_leakage_keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "split_name", _optional_text(self.split_name))
        object.__setattr__(
            self,
            "occupied_leakage_keys",
            _clean_text_tuple(self.occupied_leakage_keys),
        )


@dataclass(frozen=True, slots=True)
class RecipeCandidateEvaluation:
    accepted: bool
    reasons: tuple[str, ...]
    matched_rules: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "reasons": list(self.reasons),
            "matched_rules": list(self.matched_rules),
        }


@dataclass(frozen=True, slots=True)
class TrainingRecipeSchema:
    recipe_id: str
    title: str
    goal: str
    requested_modalities: tuple[str, ...] = ()
    target_splits: Mapping[str, int] = field(default_factory=dict)
    selection_rule: RecipeRuleNode | None = None
    completeness_policy: RecipeCompletenessPolicy = field(
        default_factory=RecipeCompletenessPolicy
    )
    leakage_policy: RecipeLeakagePolicy = field(default_factory=RecipeLeakagePolicy)
    tags: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "recipe_id", _required_text(self.recipe_id, "recipe_id"))
        object.__setattr__(self, "title", _required_text(self.title, "title"))
        object.__setattr__(self, "goal", _required_text(self.goal, "goal"))
        object.__setattr__(
            self,
            "requested_modalities",
            _clean_text_tuple(self.requested_modalities),
        )
        object.__setattr__(self, "tags", _clean_text_tuple(self.tags))
        object.__setattr__(self, "notes", _clean_text_tuple(self.notes))
        object.__setattr__(self, "target_splits", dict(self.target_splits))
        if not isinstance(self.completeness_policy, RecipeCompletenessPolicy):
            object.__setattr__(
                self,
                "completeness_policy",
                RecipeCompletenessPolicy.from_dict(self.completeness_policy),
            )
        if not isinstance(self.leakage_policy, RecipeLeakagePolicy):
            object.__setattr__(
                self,
                "leakage_policy",
                RecipeLeakagePolicy.from_dict(self.leakage_policy),
            )
        if self.selection_rule is not None and not isinstance(
            self.selection_rule, (RecipeSelectionRule, RecipeRuleGroup)
        ):
            object.__setattr__(
                self,
                "selection_rule",
                recipe_rule_from_dict(self.selection_rule),
            )

    def evaluate_candidate(
        self,
        candidate: Mapping[str, Any],
        *,
        context: RecipeEvaluationContext | None = None,
    ) -> RecipeCandidateEvaluation:
        reasons: list[str] = []
        matched_rules: list[str] = []
        evaluation_context = context or RecipeEvaluationContext()

        if self.selection_rule is not None:
            rule_matched = self.selection_rule.evaluate(candidate)
            label = (
                self.selection_rule.description
                if isinstance(self.selection_rule, RecipeRuleGroup)
                else self.selection_rule.description or self.selection_rule.field_name
            )
            if rule_matched:
                if label:
                    matched_rules.append(label)
            else:
                reasons.append(f"selection rules not satisfied: {label or 'unnamed rule'}")

        completeness_ok, completeness_reasons = self.completeness_policy.evaluate(candidate)
        if not completeness_ok:
            reasons.extend(completeness_reasons)

        leakage_ok, leakage_reasons = self.leakage_policy.evaluate(
            candidate,
            occupied_keys=evaluation_context.occupied_leakage_keys,
        )
        if not leakage_ok:
            reasons.extend(leakage_reasons)

        return RecipeCandidateEvaluation(
            accepted=not reasons,
            reasons=tuple(reasons),
            matched_rules=tuple(matched_rules),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipe_id": self.recipe_id,
            "title": self.title,
            "goal": self.goal,
            "requested_modalities": list(self.requested_modalities),
            "target_splits": dict(self.target_splits),
            "selection_rule": (
                None if self.selection_rule is None else self.selection_rule.to_dict()
            ),
            "completeness_policy": self.completeness_policy.to_dict(),
            "leakage_policy": self.leakage_policy.to_dict(),
            "tags": list(self.tags),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TrainingRecipeSchema:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        selection_rule_payload = payload.get("selection_rule") or payload.get("rules")
        selection_rule = None
        if isinstance(selection_rule_payload, Mapping):
            selection_rule = recipe_rule_from_dict(selection_rule_payload)
        requested_modalities = (
            payload.get("requested_modalities") or payload.get("modalities") or ()
        )
        return cls(
            recipe_id=payload.get("recipe_id") or payload.get("id") or "",
            title=payload.get("title") or "",
            goal=payload.get("goal") or payload.get("objective") or "",
            requested_modalities=requested_modalities,
            target_splits=payload.get("target_splits") or {},
            selection_rule=selection_rule,
            completeness_policy=payload.get("completeness_policy") or {},
            leakage_policy=payload.get("leakage_policy") or {},
            tags=payload.get("tags") or (),
            notes=payload.get("notes") or (),
        )


__all__ = [
    "RecipeCandidateEvaluation",
    "RecipeCompletenessPolicy",
    "RecipeEvaluationContext",
    "RecipeLeakagePolicy",
    "RecipeRuleGroup",
    "RecipeRuleMode",
    "RecipeRuleNode",
    "RecipeRuleOperator",
    "RecipeSelectionRule",
    "TrainingRecipeSchema",
    "recipe_rule_from_dict",
]

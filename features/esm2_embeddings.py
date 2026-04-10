from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

DEFAULT_ESM2_MODEL = "facebook/esm2_t6_8M_UR50D"


class ESM2UnavailableError(RuntimeError):
    """Raised when frozen ESM2 embeddings are requested but unavailable."""


@dataclass(frozen=True, slots=True)
class ProteinEmbeddingResult:
    sequence: str
    model_name: str
    embedding_dim: int
    residue_embeddings: tuple[tuple[float, ...], ...]
    pooled_embedding: tuple[float, ...]
    cls_embedding: tuple[float, ...] | None = None
    source: str = "esm2"
    frozen: bool = True
    provenance: dict[str, object] = field(default_factory=dict)

    @property
    def residue_count(self) -> int:
        return len(self.residue_embeddings)

    def to_dict(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "model_name": self.model_name,
            "embedding_dim": self.embedding_dim,
            "residue_count": self.residue_count,
            "residue_embeddings": [list(row) for row in self.residue_embeddings],
            "pooled_embedding": list(self.pooled_embedding),
            "cls_embedding": list(self.cls_embedding) if self.cls_embedding is not None else None,
            "source": self.source,
            "frozen": self.frozen,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class _ESM2Modules:
    torch: Any
    AutoTokenizer: Any
    EsmModel: Any


_ESM2_CACHE: _ESM2Modules | None = None
_ESM2_IMPORT_FAILED = False


def _load_esm2_modules() -> _ESM2Modules | None:
    global _ESM2_CACHE, _ESM2_IMPORT_FAILED
    if _ESM2_CACHE is not None:
        return _ESM2_CACHE
    if _ESM2_IMPORT_FAILED:
        return None
    try:
        torch_module = import_module("torch")
        transformers_module = import_module("transformers")
        auto_tokenizer = getattr(transformers_module, "AutoTokenizer", None)
        esm_model = getattr(transformers_module, "EsmModel", None)
        if auto_tokenizer is None or esm_model is None:
            raise ModuleNotFoundError("transformers.EsmModel")
    except ModuleNotFoundError:
        _ESM2_IMPORT_FAILED = True
        return None
    _ESM2_CACHE = _ESM2Modules(
        torch=torch_module,
        AutoTokenizer=auto_tokenizer,
        EsmModel=esm_model,
    )
    return _ESM2_CACHE


def esm2_available() -> bool:
    return _load_esm2_modules() is not None


def _require_esm2_modules() -> _ESM2Modules:
    modules = _load_esm2_modules()
    if modules is None:
        raise ESM2UnavailableError(
            "Frozen ESM2 embeddings require torch and transformers with EsmModel support."
        )
    return modules


def _normalize_sequence(sequence: str) -> str:
    normalized = "".join(str(sequence or "").split()).upper()
    if not normalized:
        raise ValueError("sequence must not be empty")
    if any(not residue.isalpha() for residue in normalized):
        raise ValueError("sequence must contain only alphabetic residue codes")
    return normalized


def _move_to_device(value: Any, device: str) -> Any:
    mover = getattr(value, "to", None)
    if callable(mover):
        return mover(device)
    return value


def _move_batch_to_device(batch: dict[str, Any], device: str) -> dict[str, Any]:
    return {key: _move_to_device(value, device) for key, value in batch.items()}


def _tensor_to_rows(tensor: Any) -> tuple[tuple[float, ...], ...]:
    raw = tensor
    detach = getattr(raw, "detach", None)
    if callable(detach):
        raw = detach()
    cpu = getattr(raw, "cpu", None)
    if callable(cpu):
        raw = cpu()
    rows = raw.tolist() if hasattr(raw, "tolist") else raw
    if not isinstance(rows, list) or not rows:
        raise ValueError("ESM2 output did not contain embedding rows")
    if isinstance(rows[0], list) and rows[0] and isinstance(rows[0][0], list):
        rows = rows[0]
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], list):
        raise ValueError("ESM2 output shape is not compatible with sequence embeddings")
    return tuple(tuple(float(value) for value in row) for row in rows)


def _slice_residue_embeddings(
    rows: tuple[tuple[float, ...], ...],
    sequence_length: int,
) -> tuple[tuple[tuple[float, ...], ...], tuple[float, ...] | None]:
    if len(rows) < sequence_length:
        raise ValueError(
            f"ESM2 output length {len(rows)} is shorter than the sequence length {sequence_length}"
        )
    if len(rows) == sequence_length:
        return rows, None
    if len(rows) == sequence_length + 1:
        return rows[1:], rows[0]
    return rows[1 : sequence_length + 1], rows[0]


def _mean_embedding(rows: tuple[tuple[float, ...], ...]) -> tuple[float, ...]:
    if not rows:
        raise ValueError("Cannot pool an empty embedding set")
    width = len(rows[0])
    totals = [0.0] * width
    for row in rows:
        if len(row) != width:
            raise ValueError("Embedding rows must have a consistent width")
        for index, value in enumerate(row):
            totals[index] += float(value)
    return tuple(total / len(rows) for total in totals)


class FrozenESM2Embedder:
    """Lazy loader for frozen ESM2 sequence embeddings."""

    def __init__(
        self,
        *,
        model_name: str = DEFAULT_ESM2_MODEL,
        device: str = "cpu",
        cache_dir: str | None = None,
        backend: _ESM2Modules | Any | None = None,
        tokenizer: Any | None = None,
        model: Any | None = None,
    ) -> None:
        resolved_model_name = str(model_name or "").strip() or DEFAULT_ESM2_MODEL
        self.model_name = resolved_model_name
        self.device = str(device or "").strip() or "cpu"
        self.cache_dir = cache_dir
        self._backend = backend
        self._tokenizer = tokenizer
        self._model = model
        self._prepared = False

    def _resolve_backend(self) -> _ESM2Modules | Any:
        return self._backend or _require_esm2_modules()

    def _prepare_model(self) -> None:
        if self._prepared:
            return
        backend = self._resolve_backend()
        try:
            if self._tokenizer is None:
                self._tokenizer = backend.AutoTokenizer.from_pretrained(
                    self.model_name,
                    cache_dir=self.cache_dir,
                )
            if self._model is None:
                self._model = backend.EsmModel.from_pretrained(
                    self.model_name,
                    cache_dir=self.cache_dir,
                )
        except Exception as exc:  # noqa: BLE001
            raise ESM2UnavailableError(
                f"Unable to load frozen ESM2 model '{self.model_name}'. "
                f"Ensure the package stack and model weights are available. Original error: {exc}"
            ) from exc

        eval_fn = getattr(self._model, "eval", None)
        if callable(eval_fn):
            eval_fn()
        params_fn = getattr(self._model, "parameters", None)
        if callable(params_fn):
            for parameter in params_fn():
                if hasattr(parameter, "requires_grad"):
                    parameter.requires_grad = False
        model_to = getattr(self._model, "to", None)
        if callable(model_to):
            model_to(self.device)
        self._prepared = True

    def embed(self, sequence: str) -> ProteinEmbeddingResult:
        normalized_sequence = _normalize_sequence(sequence)
        self._prepare_model()
        backend = self._resolve_backend()
        encoded = self._tokenizer(normalized_sequence, return_tensors="pt")
        batch = _move_batch_to_device(dict(encoded), self.device)
        with backend.torch.no_grad():
            outputs = self._model(**batch)
        rows = _tensor_to_rows(outputs.last_hidden_state)
        residue_embeddings, cls_embedding = _slice_residue_embeddings(
            rows,
            len(normalized_sequence),
        )
        pooled_embedding = _mean_embedding(residue_embeddings)
        return ProteinEmbeddingResult(
            sequence=normalized_sequence,
            model_name=self.model_name,
            embedding_dim=len(pooled_embedding),
            residue_embeddings=residue_embeddings,
            pooled_embedding=pooled_embedding,
            cls_embedding=cls_embedding,
            provenance={
                "backend": type(backend).__name__,
                "device": self.device,
                "cache_dir": self.cache_dir,
                "model_name": self.model_name,
                "frozen": True,
            },
        )


def embed_sequence(
    sequence: str,
    *,
    model_name: str = DEFAULT_ESM2_MODEL,
    device: str = "cpu",
    cache_dir: str | None = None,
    backend: _ESM2Modules | Any | None = None,
) -> ProteinEmbeddingResult:
    return FrozenESM2Embedder(
        model_name=model_name,
        device=device,
        cache_dir=cache_dir,
        backend=backend,
    ).embed(sequence)

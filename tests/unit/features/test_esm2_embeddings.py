from __future__ import annotations

import pytest

import features.esm2_embeddings as esm2_embeddings


class _FakeParameter:
    def __init__(self) -> None:
        self.requires_grad = True


class _FakeTensor:
    def __init__(self, rows):
        self._rows = rows
        self.device = None

    def to(self, device: str):
        self.device = device
        return self

    def detach(self):
        return self

    def cpu(self):
        return self

    def tolist(self):
        return self._rows


class _FakeNoGrad:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, tb):  # noqa: ARG002
        return False


class _FakeTorch:
    @staticmethod
    def no_grad():
        return _FakeNoGrad()


class _FakeTokenizer:
    def __init__(self, model_name: str, cache_dir: str | None) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.calls: list[str] = []

    @classmethod
    def from_pretrained(cls, model_name: str, cache_dir: str | None = None):
        return cls(model_name, cache_dir)

    def __call__(self, sequence: str, return_tensors: str = "pt"):  # noqa: ARG002
        self.calls.append(sequence)
        return {
            "input_ids": _FakeTensor([[0, 1, 2, 3, 4]]),
            "attention_mask": _FakeTensor([[1, 1, 1, 1, 1]]),
        }


class _FakeModelOutput:
    def __init__(self, rows):
        self.last_hidden_state = _FakeTensor(rows)


class _FakeModel:
    def __init__(self, model_name: str, cache_dir: str | None) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.eval_called = False
        self.device = None
        self.parameters_list = [_FakeParameter(), _FakeParameter()]
        self.calls = []

    @classmethod
    def from_pretrained(cls, model_name: str, cache_dir: str | None = None):
        return cls(model_name, cache_dir)

    def eval(self):
        self.eval_called = True

    def to(self, device: str):
        self.device = device
        return self

    def parameters(self):
        return self.parameters_list

    def __call__(self, **batch):
        self.calls.append(batch)
        return _FakeModelOutput(
            [
                [
                    [0.0, 0.0],
                    [1.0, 1.0],
                    [2.0, 2.0],
                    [3.0, 3.0],
                    [9.0, 9.0],
                ]
            ]
        )


class _FakeBackend:
    torch = _FakeTorch
    AutoTokenizer = _FakeTokenizer
    EsmModel = _FakeModel


def test_embed_sequence_uses_frozen_esm2_backend():
    embedder = esm2_embeddings.FrozenESM2Embedder(
        model_name="facebook/esm2_t6_8M_UR50D",
        device="cpu",
        backend=_FakeBackend(),
    )

    result = embedder.embed("a c\nD")

    assert result.sequence == "ACD"
    assert result.model_name == "facebook/esm2_t6_8M_UR50D"
    assert result.embedding_dim == 2
    assert result.residue_count == 3
    assert result.residue_embeddings == ((1.0, 1.0), (2.0, 2.0), (3.0, 3.0))
    assert result.pooled_embedding == (2.0, 2.0)
    assert result.cls_embedding == (0.0, 0.0)
    assert result.frozen is True
    assert result.to_dict()["source"] == "esm2"
    assert result.provenance["backend"] == "_FakeBackend"
    assert result.to_dict()["provenance"]["device"] == "cpu"
    assert embedder._model.eval_called is True
    assert embedder._model.device == "cpu"
    assert all(parameter.requires_grad is False for parameter in embedder._model.parameters())


def test_embed_sequence_rejects_invalid_sequence():
    embedder = esm2_embeddings.FrozenESM2Embedder(backend=_FakeBackend())

    with pytest.raises(ValueError, match="alphabetic residue codes"):
        embedder.embed("ACD-1")


def test_embed_sequence_raises_clear_blocker_when_runtime_missing(monkeypatch):
    monkeypatch.setattr(esm2_embeddings, "_ESM2_CACHE", None)
    monkeypatch.setattr(esm2_embeddings, "_ESM2_IMPORT_FAILED", True)

    with pytest.raises(
        esm2_embeddings.ESM2UnavailableError,
        match="require torch and transformers",
    ):
        esm2_embeddings.embed_sequence("ACD")


def test_embed_sequence_raises_clear_error_when_model_load_fails():
    class _BrokenTokenizer:
        @staticmethod
        def from_pretrained(model_name: str, cache_dir: str | None = None):  # noqa: ARG002
            raise OSError("weights missing")

    class _BrokenBackend:
        torch = _FakeTorch
        AutoTokenizer = _BrokenTokenizer
        EsmModel = _FakeModel

    with pytest.raises(esm2_embeddings.ESM2UnavailableError, match="weights are available"):
        esm2_embeddings.embed_sequence(
            "ACD",
            backend=_BrokenBackend(),
            model_name="facebook/esm2_t12",
        )


def test_esm2_available_reflects_import_state(monkeypatch):
    monkeypatch.setattr(esm2_embeddings, "_ESM2_CACHE", None)
    monkeypatch.setattr(esm2_embeddings, "_ESM2_IMPORT_FAILED", True)

    assert esm2_embeddings.esm2_available() is False

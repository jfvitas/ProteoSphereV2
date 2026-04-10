from __future__ import annotations

from collections.abc import Callable

import pytest

from core.procurement.source_release_manifest import validate_source_release_manifest_payload
from execution.checkpoints.store import CheckpointRecord


class _RepeatedFailureExhausted(RuntimeError):
    def __init__(self, envelopes: tuple[dict[str, object], ...]) -> None:
        super().__init__(f"failure injection exhausted after {len(envelopes)} attempts")
        self.envelopes = envelopes


def _drive_repeated_error_injection(
    action: Callable[[int], None],
    *,
    attempts: int,
) -> None:
    envelopes: list[dict[str, object]] = []
    for attempt in range(1, attempts + 1):
        try:
            action(attempt)
        except Exception as exc:  # noqa: BLE001
            envelopes.append(
                {
                    "attempt": attempt,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )
            continue
        raise AssertionError("repeated failure injection unexpectedly recovered")
    raise _RepeatedFailureExhausted(tuple(envelopes))


def test_failure_injection_tracks_repeated_errors_and_stays_fail_closed() -> None:
    attempts: list[int] = []

    def _always_fail(attempt: int) -> None:
        attempts.append(attempt)
        raise RuntimeError(f"synthetic repeated failure #{attempt}")

    with pytest.raises(_RepeatedFailureExhausted) as excinfo:
        _drive_repeated_error_injection(_always_fail, attempts=3)

    assert attempts == [1, 2, 3]
    assert [envelope["attempt"] for envelope in excinfo.value.envelopes] == [1, 2, 3]
    assert [envelope["error_type"] for envelope in excinfo.value.envelopes] == [
        "RuntimeError",
        "RuntimeError",
        "RuntimeError",
    ]
    assert "synthetic repeated failure #3" in str(excinfo.value.envelopes[-1]["error_message"])


def test_failure_injection_rejects_bad_manifest_payloads() -> None:
    bad_payload = {
        "source_name": "AlphaFold DB",
        "release_version": "2026_03",
        "retrieval_mode": "screen-scrape",
        "source_locator": "https://alphafold.ebi.ac.uk/api/openapi.json",
    }

    with pytest.raises(ValueError, match="unsupported retrieval_mode"):
        validate_source_release_manifest_payload(bad_payload)


def test_failure_injection_rejects_corrupted_checkpoint_payloads() -> None:
    record = CheckpointRecord(
        run_id="chaos-run",
        checkpoint_state={"completed_nodes": ["ingest_sequences"]},
        version=1,
        provenance={"source": "integration-test"},
        metadata={"kind": "run"},
    )
    corrupted_payload = record.to_dict()
    corrupted_payload["checkpoint_key"] = "run:other-run"

    with pytest.raises(ValueError, match="checkpoint_key does not match"):
        CheckpointRecord.from_dict(corrupted_payload)

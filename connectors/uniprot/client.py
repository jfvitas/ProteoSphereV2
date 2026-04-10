from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class UniProtClientError(RuntimeError):
    """Raised when a UniProt request fails or returns invalid data."""


@dataclass(frozen=True)
class UniProtClient:
    """Small client for the UniProtKB REST endpoints.

    The baseline intentionally stays narrow: JSON entry fetches plus text
    sequence retrieval for downstream canonicalization tasks.
    """

    base_url: str = "https://rest.uniprot.org/uniprotkb"
    timeout: float = 30.0

    def get_entry(
        self, accession: str, opener: Callable[..., Any] | None = None
    ) -> dict[str, Any]:
        return self._get_json(f"/{self._normalize_accession(accession)}.json", opener=opener)

    def get_fasta(
        self, accession: str, opener: Callable[..., Any] | None = None
    ) -> str:
        return self._get_text(f"/{self._normalize_accession(accession)}.fasta", opener=opener)

    def get_text(
        self, accession: str, opener: Callable[..., Any] | None = None
    ) -> str:
        return self._get_text(f"/{self._normalize_accession(accession)}.txt", opener=opener)

    def _get_json(
        self, path: str, opener: Callable[..., Any] | None = None
    ) -> dict[str, Any]:
        payload = self._request(f"{self.base_url}{path}", opener=opener)
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise UniProtClientError("UniProt response was not valid JSON") from exc

    def _get_text(
        self, path: str, opener: Callable[..., Any] | None = None
    ) -> str:
        payload = self._request(f"{self.base_url}{path}", opener=opener)
        return payload.decode("utf-8")

    def _request(
        self, url: str, opener: Callable[..., Any] | None = None
    ) -> bytes:
        request = Request(url, headers={"User-Agent": "ProteoSphereV2-UniProtClient/0.1"})
        request_opener = opener or urlopen
        try:
            with request_opener(request, timeout=self.timeout) as response:
                return response.read()
        except HTTPError as exc:
            raise UniProtClientError(f"UniProt request failed with HTTP {exc.code}") from exc
        except (URLError, OSError) as exc:
            raise UniProtClientError("UniProt request could not be completed") from exc

    @staticmethod
    def _normalize_accession(accession: str) -> str:
        value = accession.strip().upper()
        if not value:
            raise ValueError("accession must not be empty")
        if not 6 <= len(value) <= 10 or not value.isalnum():
            raise ValueError("accession must be a 6-10 character alphanumeric UniProt accession")
        return value

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class RCSBClientError(RuntimeError):
    """Raised when an RCSB API request fails or returns invalid data."""


@dataclass(frozen=True)
class RCSBClient:
    """Small client for the RCSB Data API and archive endpoints.

    The implementation stays intentionally small so the downstream parser and
    execution tasks can build on a predictable transport layer.
    """

    base_url: str = "https://data.rcsb.org/rest/v1"
    archive_url: str = "https://files.rcsb.org/download"
    timeout: float = 30.0

    def get_entry(self, pdb_id: str, opener: Callable[..., Any] | None = None) -> dict[str, Any]:
        return self._get_json(f"/core/entry/{self._normalize_pdb_id(pdb_id)}", opener=opener)

    def get_entity(
        self, pdb_id: str, entity_id: str | int, opener: Callable[..., Any] | None = None
    ) -> dict[str, Any]:
        return self._get_json(
            f"/core/polymer_entity/{self._normalize_pdb_id(pdb_id)}/{self._normalize_entity_id(entity_id)}",
            opener=opener,
        )

    def get_assembly(
        self, pdb_id: str, assembly_id: str | int, opener: Callable[..., Any] | None = None
    ) -> dict[str, Any]:
        return self._get_json(
            f"/core/assembly/{self._normalize_pdb_id(pdb_id)}/{self._normalize_assembly_id(assembly_id)}",
            opener=opener,
        )

    def get_mmcif(
        self, pdb_id: str, opener: Callable[..., Any] | None = None
    ) -> str:
        url = f"{self.archive_url}/{self._normalize_pdb_id(pdb_id)}.cif"
        return self._get_text(url, opener=opener)

    def _get_json(
        self, path: str, opener: Callable[..., Any] | None = None
    ) -> dict[str, Any]:
        payload = self._request(f"{self.base_url}{path}", opener=opener)
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RCSBClientError("RCSB response was not valid JSON") from exc

    def _get_text(
        self, url: str, opener: Callable[..., Any] | None = None
    ) -> str:
        payload = self._request(url, opener=opener)
        return payload.decode("utf-8")

    def _request(
        self, url: str, opener: Callable[..., Any] | None = None
    ) -> bytes:
        request = Request(url, headers={"User-Agent": "ProteoSphereV2-RCSBClient/0.1"})
        request_opener = opener or urlopen
        try:
            with request_opener(request, timeout=self.timeout) as response:
                return response.read()
        except HTTPError as exc:
            raise RCSBClientError(f"RCSB request failed with HTTP {exc.code}") from exc
        except (URLError, OSError) as exc:
            raise RCSBClientError("RCSB request could not be completed") from exc

    @staticmethod
    def _normalize_pdb_id(pdb_id: str) -> str:
        value = pdb_id.strip().lower()
        if len(value) != 4 or not value.isalnum():
            raise ValueError("pdb_id must be a 4-character alphanumeric identifier")
        return value

    @staticmethod
    def _normalize_entity_id(entity_id: str | int) -> str:
        value = str(entity_id).strip()
        if not value or not value.isdigit():
            raise ValueError("entity_id must be a positive integer")
        return value

    @staticmethod
    def _normalize_assembly_id(assembly_id: str | int) -> str:
        value = str(assembly_id).strip()
        if not value or not value.isdigit():
            raise ValueError("assembly_id must be a positive integer")
        return value

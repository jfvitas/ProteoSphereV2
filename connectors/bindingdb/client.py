from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class BindingDBClientError(RuntimeError):
    """Raised when a BindingDB request fails or returns invalid data."""


@dataclass(frozen=True)
class BindingDBClient:
    """Small client for the BindingDB REST API."""

    base_url: str = "https://www.bindingdb.org"
    timeout: float = 30.0

    def get_ligands_by_pdbs(
        self,
        pdb_ids: Sequence[str] | str,
        *,
        cutoff: int | float | None = None,
        identity: int | None = None,
        opener: Callable[..., Any] | None = None,
    ) -> Any:
        params: dict[str, Any] = {
            "pdb": self._normalize_pdb_ids(pdb_ids),
            "response": "application/json",
        }
        if cutoff is not None:
            params["cutoff"] = cutoff
        if identity is not None:
            params["identity"] = identity
        return self._get_json("/rest/getLigandsByPDBs", params, opener=opener)

    def get_ligands_by_uniprots(
        self,
        uniprot_ids: Sequence[str] | str,
        *,
        cutoff: int | float | None = None,
        opener: Callable[..., Any] | None = None,
    ) -> Any:
        params: dict[str, Any] = {
            "uniprot": self._normalize_uniprot_ids(uniprot_ids),
            "response": "application/json",
        }
        if cutoff is not None:
            params["cutoff"] = cutoff
        return self._get_json("/rest/getLigandsByUniprots", params, opener=opener)

    def get_ligands_by_uniprot(
        self,
        uniprot_id: str,
        *,
        cutoff: int | float | None = None,
        opener: Callable[..., Any] | None = None,
    ) -> Any:
        params: dict[str, Any] = {
            "uniprot": self._normalize_uniprot_id(uniprot_id, append_cutoff=cutoff),
            "response": "application/json",
        }
        return self._get_json("/rest/getLigandsByUniprot", params, opener=opener)

    def get_target_by_compound(
        self,
        smiles: str,
        *,
        cutoff: float | None = None,
        opener: Callable[..., Any] | None = None,
    ) -> Any:
        params: dict[str, Any] = {
            "smiles": self._normalize_smiles(smiles),
            "response": "application/json",
        }
        if cutoff is not None:
            params["cutoff"] = cutoff
        return self._get_json("/rest/getTargetByCompound", params, opener=opener)

    def _get_json(
        self,
        path: str,
        params: dict[str, Any],
        opener: Callable[..., Any] | None = None,
    ) -> Any:
        payload = self._request(path, params, opener=opener)
        if not payload:
            return ""
        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise BindingDBClientError("BindingDB response was not valid JSON") from exc

    def _request(
        self,
        path: str,
        params: dict[str, Any],
        opener: Callable[..., Any] | None = None,
    ) -> str:
        url = f"{self.base_url}{path}?{urlencode(params, doseq=True)}"
        request = Request(url, headers={"User-Agent": "ProteoSphereV2-BindingDBClient/0.1"})
        request_opener = opener or urlopen
        try:
            with request_opener(request, timeout=self.timeout) as response:
                return response.read().decode("utf-8")
        except HTTPError as exc:
            raise BindingDBClientError(f"BindingDB request failed with HTTP {exc.code}") from exc
        except (URLError, OSError) as exc:
            raise BindingDBClientError("BindingDB request could not be completed") from exc

    @staticmethod
    def _normalize_pdb_ids(pdb_ids: Sequence[str] | str) -> str:
        values = [pdb_ids] if isinstance(pdb_ids, str) else list(pdb_ids)
        normalized = [BindingDBClient._normalize_pdb_id(value) for value in values]
        if not normalized:
            raise ValueError("pdb_ids must not be empty")
        return ",".join(normalized)

    @staticmethod
    def _normalize_uniprot_ids(uniprot_ids: Sequence[str] | str) -> str:
        values = [uniprot_ids] if isinstance(uniprot_ids, str) else list(uniprot_ids)
        normalized = [BindingDBClient._normalize_uniprot_id(value) for value in values]
        if not normalized:
            raise ValueError("uniprot_ids must not be empty")
        return ",".join(normalized)

    @staticmethod
    def _normalize_pdb_id(pdb_id: str) -> str:
        value = pdb_id.strip().upper()
        if len(value) != 4 or not value.isalnum():
            raise ValueError("pdb_id must be a 4-character alphanumeric identifier")
        return value

    @staticmethod
    def _normalize_uniprot_id(
        uniprot_id: str,
        *,
        append_cutoff: int | float | None = None,
    ) -> str:
        value = uniprot_id.strip().upper()
        if not value or any(ch.isspace() for ch in value) or "," in value:
            raise ValueError("uniprot_id must be a non-empty accession identifier")
        if append_cutoff is not None:
            return f"{value};{append_cutoff}"
        return value

    @staticmethod
    def _normalize_smiles(smiles: str) -> str:
        value = smiles.strip()
        if not value:
            raise ValueError("smiles must not be empty")
        return value

from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.model_studio.reference_library import load_source_registry, resolve_materialization_route
from api.model_studio.service import (
    _reference_library_hydration_requirements,
    _reference_library_install_status,
    _reference_library_query_contract,
    _reference_library_resolution,
    _reference_library_status,
    build_workspace_payload,
)
from scripts.reference_warehouse_common import DEFAULT_PRIMARY_WAREHOUSE_ROOT, write_json

RAW_OFFLINE_SUFFIX = "__offline_acceptance__"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _rename_offline(path: Path) -> Path:
    offline_path = path.with_name(f"{path.name}{RAW_OFFLINE_SUFFIX}")
    if offline_path.exists():
        raise FileExistsError(f"offline marker path already exists: {offline_path}")
    path.rename(offline_path)
    return offline_path


def _restore_online(offline_path: Path, original_path: Path) -> None:
    if not offline_path.exists():
        return
    original_path.parent.mkdir(parents=True, exist_ok=True)
    offline_path.rename(original_path)


def run_raw_disconnected_acceptance(
    *,
    warehouse_root: Path,
    roots_to_mask: list[Path],
    output_path: Path | None = None,
    run_workspace_payload: bool = True,
) -> dict[str, Any]:
    os.environ["PROTEOSPHERE_WAREHOUSE_ROOT"] = str(warehouse_root)
    masked_roots: list[dict[str, str]] = []
    with ExitStack() as stack:
        for root in roots_to_mask:
            if not root.exists():
                continue
            offline_path = _rename_offline(root)
            stack.callback(_restore_online, offline_path, root)
            masked_roots.append(
                {
                    "original_path": str(root).replace("\\", "/"),
                    "offline_path": str(offline_path).replace("\\", "/"),
                }
            )

        import duckdb  # type: ignore[import-not-found]

        catalog_path = warehouse_root / "catalog" / "reference_library.duckdb"
        source_registry_path = warehouse_root / "control" / "source_registry.json"
        source_registry_payload = load_source_registry(source_registry_path)
        with duckdb.connect(str(catalog_path), read_only=True) as connection:
            sample_route_row = connection.sql(
                """
                select
                    route_id,
                    pointer,
                    selector,
                    source_name,
                    snapshot_id
                from materialization_routes
                limit 1
                """
            ).fetchone()
            proteins_count = int(connection.sql("select count(*) from proteins").fetchone()[0])
            sample_route = {
                "route_id": sample_route_row[0],
                "pointer": sample_route_row[1],
                "selector": sample_route_row[2],
                "source_name": sample_route_row[3],
                "snapshot_id": sample_route_row[4],
            }

        route_resolution = resolve_materialization_route(sample_route, source_registry_payload)
        status_payload = _reference_library_status()
        install_status = _reference_library_install_status()
        resolution_payload = _reference_library_resolution()
        hydration_payload = _reference_library_hydration_requirements()
        query_contract = _reference_library_query_contract()
        workspace_payload_status: dict[str, Any] | None = None
        if run_workspace_payload:
            workspace_payload = build_workspace_payload()
            workspace_payload_status = {
                "schema_version": workspace_payload.get("schema_version"),
                "workspace_sections": workspace_payload.get("workspace_sections"),
                "active_primary_view": (
                    (workspace_payload.get("ui_contract") or {}).get("active_primary_view")
                ),
            }

        payload = {
            "status": "passed",
            "generated_at": _utc_now(),
            "warehouse_root": str(warehouse_root).replace("\\", "/"),
            "masked_roots": masked_roots,
            "library_checks": {
                "proteins_count": proteins_count,
                "reference_library_status": status_payload,
                "reference_library_install_status": install_status,
                "reference_library_resolution": resolution_payload,
                "reference_library_hydration_requirements": hydration_payload,
                "reference_library_query_contract": query_contract,
                "sample_materialization_route": sample_route,
                "sample_materialization_resolution": route_resolution,
                "workspace_payload_status": workspace_payload_status,
            },
        }
        if output_path is not None:
            write_json(output_path, payload)
        return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Temporarily take raw/archive roots offline and verify the library still operates."
    )
    parser.add_argument(
        "--warehouse-root",
        type=Path,
        default=DEFAULT_PRIMARY_WAREHOUSE_ROOT,
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-workspace-payload", action="store_true")
    parser.add_argument(
        "--mask-root",
        action="append",
        dest="mask_roots",
        default=[],
        help="Additional root to take offline during acceptance.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    default_roots = [
        Path(r"D:\documents\ProteoSphereV2\data\raw"),
        Path(r"C:\Users\jfvit\Documents\bio-agent-lab"),
        Path(r"C:\CSTEMP\ProteoSphereV2_overflow"),
        Path(r"C:\Users\jfvit\Documents\temp_storage\proteosphere_temp_archives"),
        Path(r"E:\ProteoSphere\reference_library\incoming_mirrors"),
    ]
    mask_roots = [*default_roots, *(Path(item) for item in args.mask_roots)]
    payload = run_raw_disconnected_acceptance(
        warehouse_root=args.warehouse_root,
        roots_to_mask=mask_roots,
        output_path=args.output,
        run_workspace_payload=not args.skip_workspace_payload,
    )
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

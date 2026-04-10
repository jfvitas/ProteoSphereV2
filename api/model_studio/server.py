# ruff: noqa: I001
from __future__ import annotations

import argparse
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from api.model_studio.service import (
    build_training_set_payload,
    build_hardware_profile_payload,
    build_program_status,
    build_workspace_payload,
    cancel_pipeline_run,
    compare_pipeline_runs,
    compile_pipeline_payload,
    record_session_event,
    list_training_set_build_records,
    launch_pipeline_run,
    list_pipeline_runs,
    list_pipeline_specs,
    load_training_set_build_record,
    load_pipeline_run,
    load_pipeline_run_artifacts,
    load_pipeline_run_logs,
    load_pipeline_spec,
    preview_training_set_payload,
    resume_pipeline_run,
    save_pipeline_spec,
    submit_feedback,
    validate_pipeline_payload,
)
from api.model_studio.runtime import recover_stale_runs


REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_ROOT = REPO_ROOT / "gui" / "model_studio_web"


class ModelStudioRequestHandler(BaseHTTPRequestHandler):
    server_version = "ProteoSphereModelStudio/0.1"

    def _write_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_file(self, path: Path, content_type: str) -> None:
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b"{}"
        return json.loads(body.decode("utf-8") or "{}")

    def _write_error(self, status: int, error: str, detail: str) -> None:
        self._write_json({"error": error, "detail": detail}, status=status)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._write_file(STATIC_ROOT / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/app.js":
            self._write_file(STATIC_ROOT / "app.js", "application/javascript; charset=utf-8")
            return
        if parsed.path == "/app_beta.js":
            self._write_file(STATIC_ROOT / "app_beta.js", "application/javascript; charset=utf-8")
            return
        if parsed.path == "/styles.css":
            self._write_file(STATIC_ROOT / "styles.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/beta_overrides.css":
            self._write_file(STATIC_ROOT / "beta_overrides.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/api/model-studio/health":
            self._write_json({"status": "ok", "service": "model-studio"})
            return
        if parsed.path == "/api/model-studio/catalog":
            self._write_json(build_workspace_payload()["catalog"])
            return
        if parsed.path == "/api/model-studio/workspace-preview":
            query = parse_qs(parsed.query)
            self._write_json(build_workspace_payload(query.get("pipeline_id", [None])[0]))
            return
        if parsed.path == "/api/model-studio/program-status":
            self._write_json(build_program_status())
            return
        if parsed.path == "/api/model-studio/hardware-profile":
            self._write_json(build_hardware_profile_payload())
            return
        if parsed.path == "/api/model-studio/pipeline-specs":
            self._write_json({"items": list_pipeline_specs()})
            return
        if parsed.path.startswith("/api/model-studio/pipeline-specs/"):
            pipeline_id = parsed.path.removeprefix("/api/model-studio/pipeline-specs/")
            try:
                self._write_json(load_pipeline_spec(pipeline_id))
            except FileNotFoundError:
                self._write_error(HTTPStatus.NOT_FOUND, "not_found", pipeline_id)
            return
        if parsed.path == "/api/model-studio/runs":
            self._write_json(list_pipeline_runs())
            return
        if parsed.path == "/api/model-studio/study-runs":
            self._write_json(list_pipeline_runs())
            return
        if parsed.path == "/api/model-studio/training-set-builds":
            self._write_json(list_training_set_build_records())
            return
        if parsed.path.startswith("/api/model-studio/training-set-builds/"):
            build_id = parsed.path.removeprefix("/api/model-studio/training-set-builds/")
            try:
                self._write_json(load_training_set_build_record(build_id))
            except FileNotFoundError:
                self._write_error(HTTPStatus.NOT_FOUND, "not_found", build_id)
            return
        if parsed.path.startswith("/api/model-studio/runs/") and parsed.path.endswith("/artifacts"):
            run_id = parsed.path.removeprefix("/api/model-studio/runs/").removesuffix("/artifacts")
            try:
                self._write_json(load_pipeline_run_artifacts(run_id))
            except FileNotFoundError:
                self._write_error(HTTPStatus.NOT_FOUND, "not_found", run_id)
            return
        if parsed.path.startswith("/api/model-studio/runs/") and parsed.path.endswith("/logs"):
            run_id = parsed.path.removeprefix("/api/model-studio/runs/").removesuffix("/logs")
            try:
                self._write_json(load_pipeline_run_logs(run_id))
            except FileNotFoundError:
                self._write_error(HTTPStatus.NOT_FOUND, "not_found", run_id)
            return
        if parsed.path.startswith("/api/model-studio/runs/"):
            run_id = parsed.path.removeprefix("/api/model-studio/runs/")
            try:
                self._write_json(load_pipeline_run(run_id))
            except FileNotFoundError:
                self._write_error(HTTPStatus.NOT_FOUND, "not_found", run_id)
            return
        if parsed.path == "/api/model-studio/compare":
            query = parse_qs(parsed.query)
            self._write_json(compare_pipeline_runs(query.get("run_id", [])))
            return
        self._write_json({"error": "not_found", "path": self.path}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self._read_json()
        except json.JSONDecodeError as exc:
            self._write_error(HTTPStatus.BAD_REQUEST, "invalid_json", str(exc))
            return

        if self.path == "/api/model-studio/pipeline-specs/save-draft":
            try:
                self._write_json(save_pipeline_spec(payload))
            except Exception as exc:  # pragma: no cover - surfaced to caller
                self._write_error(HTTPStatus.BAD_REQUEST, "invalid_spec", str(exc))
            return
        if self.path == "/api/model-studio/pipeline-specs/validate":
            try:
                self._write_json(validate_pipeline_payload(payload))
            except Exception as exc:  # pragma: no cover - surfaced to caller
                self._write_error(HTTPStatus.BAD_REQUEST, "invalid_spec", str(exc))
            return
        if self.path == "/api/model-studio/pipeline-specs/compile":
            try:
                self._write_json(compile_pipeline_payload(payload))
            except Exception as exc:  # pragma: no cover - surfaced to caller
                self._write_error(HTTPStatus.BAD_REQUEST, "invalid_spec", str(exc))
            return
        if self.path == "/api/model-studio/training-set-requests/preview":
            try:
                self._write_json(preview_training_set_payload(payload))
            except Exception as exc:  # pragma: no cover - surfaced to caller
                self._write_error(HTTPStatus.BAD_REQUEST, "training_set_preview_failed", str(exc))
            return
        if self.path == "/api/model-studio/training-set-builds/build":
            try:
                self._write_json(build_training_set_payload(payload))
            except Exception as exc:  # pragma: no cover - surfaced to caller
                self._write_error(HTTPStatus.BAD_REQUEST, "training_set_build_failed", str(exc))
            return
        if self.path == "/api/model-studio/feedback":
            try:
                self._write_json(submit_feedback(payload))
            except Exception as exc:  # pragma: no cover - surfaced to caller
                self._write_error(HTTPStatus.BAD_REQUEST, "feedback_failed", str(exc))
            return
        if self.path == "/api/model-studio/session-events":
            try:
                self._write_json(record_session_event(payload))
            except Exception as exc:  # pragma: no cover - surfaced to caller
                self._write_error(HTTPStatus.BAD_REQUEST, "session_event_failed", str(exc))
            return
        if self.path == "/api/model-studio/runs/launch":
            try:
                self._write_json(launch_pipeline_run(payload))
            except Exception as exc:  # pragma: no cover - surfaced to caller
                self._write_error(HTTPStatus.BAD_REQUEST, "launch_failed", str(exc))
            return
        if self.path == "/api/model-studio/study-runs/launch":
            try:
                self._write_json(launch_pipeline_run(payload))
            except Exception as exc:  # pragma: no cover - surfaced to caller
                self._write_error(HTTPStatus.BAD_REQUEST, "launch_failed", str(exc))
            return
        if self.path.startswith("/api/model-studio/runs/") and self.path.endswith("/resume"):
            run_id = self.path.removeprefix("/api/model-studio/runs/").removesuffix("/resume")
            try:
                self._write_json(resume_pipeline_run(run_id))
            except FileNotFoundError:
                self._write_error(HTTPStatus.NOT_FOUND, "not_found", run_id)
            return
        if self.path.startswith("/api/model-studio/runs/") and self.path.endswith("/cancel"):
            run_id = self.path.removeprefix("/api/model-studio/runs/").removesuffix("/cancel")
            try:
                self._write_json(cancel_pipeline_run(run_id))
            except FileNotFoundError:
                self._write_error(HTTPStatus.NOT_FOUND, "not_found", run_id)
            return
        self._write_error(HTTPStatus.NOT_FOUND, "not_found", self.path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the ProteoSphere Model Studio preview server."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    recover_stale_runs()
    server = ThreadingHTTPServer((args.host, args.port), ModelStudioRequestHandler)
    print(f"http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

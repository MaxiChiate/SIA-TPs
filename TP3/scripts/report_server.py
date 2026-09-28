#!/usr/bin/env python3
"""Serves the report of the latest run and reloads the page when a new run finishes.

    python3 scripts/report_server.py [--port 8000]

/ is the latest run, /run/<name> a specific one. The report is rendered from the run's CSVs on every
request, so it doesn't need report.html (runs made with ./build/neuron directly show up too).
"""

from __future__ import annotations

import argparse
import html
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from run_error import RESULTS_DIR
from run_report import load_run, render

POLL_MILLISECONDS = 2000

# Injected only when served: the page asks for the latest run and reloads when it changes
RELOAD_SCRIPT = """<script>
const shownRun = %s;
setInterval(async () => {
  try {
    const latest = await (await fetch("/latest", {cache: "no-store"})).text();
    if (latest && latest !== shownRun) location.reload();
  } catch (error) { /* server stopped: keep the page as is */ }
}, %d);
</script>"""


def finished_runs() -> list[Path]:
    """Oldest first. predictions.csv is the last file a run writes, so its presence means it finished."""
    if not RESULTS_DIR.exists():
        return []
    runs = [path for path in RESULTS_DIR.iterdir() if (path / "predictions.csv").exists()]
    return sorted(runs, key=lambda path: (path / "predictions.csv").stat().st_mtime)


def run_page(run_dir: Path, follow_latest: bool) -> str:
    page = render(load_run(run_dir))
    if follow_latest:
        script = RELOAD_SCRIPT % (f'"{html.escape(run_dir.name)}"', POLL_MILLISECONDS)
        page = page.replace("</body>", script + "\n</body>")
    return page


class ReportHandler(BaseHTTPRequestHandler):

    def do_GET(self) -> None:
        runs = finished_runs()
        if self.path == "/latest":
            self.send(HTTPStatus.OK, runs[-1].name if runs else "", "text/plain")
        elif self.path == "/":
            if runs:
                self.send_page(runs[-1], follow_latest=True)
            else:
                self.send(HTTPStatus.OK, waiting_page(), "text/html")
        elif self.path.startswith("/run/"):
            run_dir = RESULTS_DIR / unquote(self.path.removeprefix("/run/"))
            if run_dir in runs:
                self.send_page(run_dir, follow_latest=False)
            else:
                self.send(HTTPStatus.NOT_FOUND, "no such run", "text/plain")
        else:
            self.send(HTTPStatus.NOT_FOUND, "not found", "text/plain")

    def send_page(self, run_dir: Path, follow_latest: bool) -> None:
        try:
            self.send(HTTPStatus.OK, run_page(run_dir, follow_latest), "text/html")
        except (OSError, ValueError, KeyError) as error:
            self.send(HTTPStatus.INTERNAL_SERVER_ERROR, f"couldn't read {run_dir.name}: {error}", "text/plain")

    def send(self, status: HTTPStatus, body: str, content_type: str) -> None:
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args) -> None:
        pass  # the page polls every 2 seconds; logging each request would flood the terminal


def waiting_page() -> str:
    script = RELOAD_SCRIPT % ('""', POLL_MILLISECONDS)
    return f"<!doctype html><meta charset='utf-8'><title>Sin corridas</title><p>Todavía no hay corridas en {html.escape(str(RESULTS_DIR))}.</p>{script}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), ReportHandler)
    print(f"report -> http://localhost:{args.port}  (se actualiza con cada corrida; Ctrl+C para cortar)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

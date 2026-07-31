"""
Font Forge Studio - a local web front end for the sheet-to-font pipeline.

Drop an image of an alphabet, confirm what the detector found, get a font.

The studio never builds fonts itself: it drives ``autodetect`` to measure the
sheet, lets the user correct those measurements, and hands the resulting
config to the same ``SheetToFontBuilder`` the CLI uses. Every session leaves a
config.json behind, so any font made here can be rebuilt headlessly.

Runs on the standard library only, bound to localhost.
"""
from __future__ import annotations

import base64
import json
import re
import shutil
import threading
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from font_forge import autodetect
from font_forge.core import SheetToFontBuilder

STUDIO_DIR = Path(__file__).resolve().parent
MAX_UPLOAD_BYTES = 64 * 1024 * 1024


@dataclass
class Session:
    """The one sheet currently loaded. This is a single-user local tool."""
    workspace: Path
    source_name: str
    prepared_name: str
    analysis: autodetect.SheetAnalysis


class StudioState:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.session: Session | None = None
        self.lock = threading.Lock()


def safe_stem(name: str, fallback: str = "MyFont") -> str:
    """Reduce user text to a filename-safe stem so it cannot escape the workspace."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return cleaned or fallback


# --- request handlers ---------------------------------------------------


class StudioHandler(BaseHTTPRequestHandler):
    state: StudioState  # injected by serve()

    def log_message(self, fmt: str, *args: Any) -> None:
        pass  # the console belongs to the build output

    # -- plumbing --

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict, code: int = 200) -> None:
        self._send(code, json.dumps(payload).encode("utf-8"), "application/json")

    def _error(self, message: str, code: int = 400) -> None:
        self._send_json({"error": message}, code)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_UPLOAD_BYTES:
            raise ValueError("Upload too large")
        return self.rfile.read(length)

    def _read_json(self) -> dict:
        return json.loads(self._read_body().decode("utf-8") or "{}")

    # -- routes --

    @property
    def route(self) -> str:
        """Path without the query string, which the client uses to bust caches."""
        return urlsplit(self.path).path

    def do_GET(self) -> None:
        try:
            route = self.route
            if route in ("/", "/index.html"):
                self._send(200, (STUDIO_DIR / "studio.html").read_bytes(), "text/html; charset=utf-8")
            elif route == "/api/sheet.png":
                self._serve_sheet()
            elif route.startswith("/api/download/"):
                self._serve_download(unquote(route.rsplit("/", 1)[-1]))
            else:
                self._error("Not found", 404)
        except Exception as exc:  # a local tool should show the reason, not die
            self._error(f"{type(exc).__name__}: {exc}", 500)

    def do_POST(self) -> None:
        try:
            route = self.route
            if route == "/api/analyze":
                self._analyze()
            elif route == "/api/refine":
                self._refine()
            elif route == "/api/build":
                self._build()
            else:
                self._error("Not found", 404)
        except Exception as exc:
            self._error(f"{type(exc).__name__}: {exc}", 500)

    # -- implementations --

    def _require_session(self) -> Session:
        session = self.state.session
        if session is None:
            raise RuntimeError("No sheet loaded yet")
        return session

    def _serve_sheet(self) -> None:
        session = self._require_session()
        path = session.workspace / session.prepared_name
        self._send(200, path.read_bytes(), "image/png")

    def _serve_download(self, filename: str) -> None:
        session = self._require_session()
        path = session.workspace / Path(filename).name
        if not path.is_file():
            self._error("Not built yet", 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.send_header("Content-Length", str(path.stat().st_size))
        self.end_headers()
        self.wfile.write(path.read_bytes())

    def _analyze(self) -> None:
        raw = self._read_body()
        if not raw:
            self._error("Empty upload")
            return

        source_name = Path(self.headers.get("X-Filename", "sheet.png")).name
        stem = safe_stem(Path(source_name).stem, "sheet")

        with self.state.lock:
            workspace = self.state.workspace
            workspace.mkdir(parents=True, exist_ok=True)
            source_path = workspace / f"{stem}_source{Path(source_name).suffix or '.png'}"
            source_path.write_bytes(raw)

            analysis, prepared = autodetect.analyze(source_path)
            if not analysis.rows:
                self._error("No rows of glyphs found in that image")
                return

            prepared_name = f"{stem}_prepared.png"
            autodetect.save_prepared(prepared, workspace / prepared_name)

            self.state.session = Session(
                workspace=workspace,
                source_name=source_path.name,
                prepared_name=prepared_name,
                analysis=analysis,
            )

        self._send_json({"analysis": analysis.to_dict(), "suggested": suggest_rows(analysis)})

    def _refine(self) -> None:
        session = self._require_session()
        counts = [int(c) for c in self._read_json().get("counts", [])]
        with self.state.lock:
            autodetect.refine_rows(session.analysis, counts)
        self._send_json({"analysis": session.analysis.to_dict()})

    def _build(self) -> None:
        session = self._require_session()
        payload = self._read_json()
        rows_in = payload.get("rows", [])
        meta = payload.get("meta", {})

        # Apply any corrections the user dragged or typed before building.
        for row_payload in rows_in:
            index = int(row_payload.get("index", -1))
            row = next((r for r in session.analysis.rows if r.index == index), None)
            if row is None:
                continue
            for key in ("y_start", "y_end", "baseline"):
                if row_payload.get(key) is not None:
                    setattr(row, key, int(row_payload[key]))

        chars_by_index = {int(r.get("index", -1)): r.get("chars", "") for r in rows_in}
        row_chars = [chars_by_index.get(r.index, "") for r in session.analysis.rows]
        if not any(c.strip() for c in row_chars):
            self._error("Type the characters for at least one row")
            return

        family = str(meta.get("family_name") or "My Font")
        meta = {**meta, "family_name": family,
                "output_basename": safe_stem(family, "MyFont")}

        with self.state.lock:
            config = autodetect.build_config(
                session.analysis, session.prepared_name, row_chars, meta
            )
            config_path = session.workspace / "config.json"
            config_path.write_text(
                json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            report = SheetToFontBuilder(config, session.workspace).build()

        basename = config["output_basename"]
        woff2 = (session.workspace / f"{basename}.woff2").read_bytes()

        self._send_json({
            "report": report,
            "config": config,
            "basename": basename,
            "workspace": str(session.workspace),
            "preview": base64.b64encode(woff2).decode("ascii"),
        })


def suggest_rows(analysis: autodetect.SheetAnalysis) -> list[str]:
    """
    Guess what each row spells from its glyph count.

    Only a hint to save typing - the counts of the common Latin rows are
    distinctive enough to be worth offering, and the user confirms anyway.
    """
    presets = {
        26: ["ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"],
        10: ["0123456789"],
    }
    used: set[str] = set()
    suggestions = []
    for row in analysis.rows:
        options = presets.get(row.glyph_count, [])
        pick = next((o for o in options if o not in used), "")
        if pick:
            used.add(pick)
        suggestions.append(pick)
    return suggestions


def serve(workspace: Path, port: int = 8730, open_browser: bool = True) -> None:
    StudioHandler.state = StudioState(workspace)
    server = ThreadingHTTPServer(("127.0.0.1", port), StudioHandler)
    url = f"http://127.0.0.1:{port}/"

    print("Font Forge Studio")
    print(f"  {url}")
    print(f"  workspace: {workspace}")
    print("  Ctrl+C to stop\n")

    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()

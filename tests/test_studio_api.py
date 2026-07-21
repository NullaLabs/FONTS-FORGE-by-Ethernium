"""
HTTP contract of the studio server.

Driven over real sockets rather than by calling the handlers directly,
because the defect this suite exists to prevent was a routing one: the client
appends a cache-busting query string, and matching on the raw path made the
sheet endpoint return 404 while every direct-call test still passed.
"""
from __future__ import annotations

import base64
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest
from fontTools.ttLib import TTFont

from font_forge.studio import StudioHandler, StudioState, safe_stem

from conftest import FONT_LATIN, render_sheet, require_font

pytestmark = pytest.mark.slow

ROWS = ["ABCDEFGHIJKLMNOPQRSTUVWXYZ", "0123456789"]


@pytest.fixture
def studio(tmp_path):
    """A studio bound to an ephemeral port with its own workspace."""
    StudioHandler.state = StudioState(tmp_path / "workspace")
    server = ThreadingHTTPServer(("127.0.0.1", 0), StudioHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def get(base, path):
    with urllib.request.urlopen(base + path) as response:
        return response.status, response.read()


def post_json(base, path, payload):
    request = urllib.request.Request(
        base + path, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


def upload_sheet(base, sheet_path):
    request = urllib.request.Request(
        base + "/api/analyze", data=sheet_path.read_bytes(),
        headers={"X-Filename": sheet_path.name})
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


@pytest.fixture
def loaded_studio(studio, tmp_path):
    sheet = render_sheet(tmp_path / "sheet.png", ROWS, require_font(FONT_LATIN))
    return studio, upload_sheet(studio, sheet)


# --- routing ------------------------------------------------------------


def test_index_is_served(studio):
    status, body = get(studio, "/")
    assert status == 200
    assert b"Font Forge Studio" in body


def test_sheet_is_served_with_a_cache_busting_query(loaded_studio):
    """
    Regression: the client requests ``/api/sheet.png?t=<timestamp>``. Matching
    the raw path made this 404 and the canvas never rendered.
    """
    base, _ = loaded_studio
    status, body = get(base, "/api/sheet.png?t=1234567890")
    assert status == 200
    assert body.startswith(b"\x89PNG")


def test_unknown_route_is_rejected(studio):
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        get(studio, "/api/nope")
    assert excinfo.value.code == 404


# --- analysis -----------------------------------------------------------


def test_analyze_reports_rows_and_polarity(loaded_studio):
    _, result = loaded_studio
    analysis = result["analysis"]
    assert len(analysis["rows"]) == len(ROWS)
    assert analysis["inverted"] is True


def test_analyze_suggests_recognisable_rows(loaded_studio):
    """Row glyph counts are distinctive enough to offer a starting guess."""
    _, result = loaded_studio
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" in result["suggested"]


def test_refine_resegments_against_known_counts(loaded_studio):
    base, _ = loaded_studio
    result = post_json(base, "/api/refine", {"counts": [len(r) for r in ROWS]})
    counts = [row["glyph_count"] for row in result["analysis"]["rows"]]
    assert counts == [len(row) for row in ROWS]


# --- build --------------------------------------------------------------


def test_build_produces_a_usable_font(loaded_studio, tmp_path):
    base, result = loaded_studio
    post_json(base, "/api/refine", {"counts": [len(r) for r in ROWS]})

    rows = [{"index": row["index"], "chars": ROWS[i]}
            for i, row in enumerate(result["analysis"]["rows"])]
    built = post_json(base, "/api/build",
                      {"rows": rows, "meta": {"family_name": "Studio Test"}})

    assert all(row["ok"] for row in built["report"]["rows"])
    assert built["basename"] == "Studio_Test"

    # The preview is what the page loads as a web font, so it must be real.
    woff2 = tmp_path / "preview.woff2"
    woff2.write_bytes(base64.b64decode(built["preview"]))
    font = TTFont(str(woff2))
    try:
        assert font.flavor == "woff2"
        assert set("".join(ROWS)) <= {chr(c) for c in font.getBestCmap()}
    finally:
        font.close()


def test_build_writes_a_rebuildable_config(loaded_studio):
    """
    The studio must not be a second way to build fonts - it emits a config the
    headless engine consumes, so any session stays reproducible.
    """
    base, result = loaded_studio
    rows = [{"index": result["analysis"]["rows"][0]["index"], "chars": ROWS[0]}]
    built = post_json(base, "/api/build",
                      {"rows": rows, "meta": {"family_name": "Studio Test"}})

    config_path = StudioHandler.state.workspace / "config.json"
    assert config_path.is_file()
    assert json.loads(config_path.read_text(encoding="utf-8")) == built["config"]


def test_build_rejects_rows_with_no_characters(loaded_studio):
    base, result = loaded_studio
    rows = [{"index": row["index"], "chars": ""}
            for row in result["analysis"]["rows"]]
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        post_json(base, "/api/build", {"rows": rows, "meta": {}})
    assert excinfo.value.code == 400


def test_endpoints_fail_before_a_sheet_is_loaded(studio):
    with pytest.raises(urllib.error.HTTPError) as excinfo:
        get(studio, "/api/sheet.png")
    assert excinfo.value.code == 500


# --- filename safety ----------------------------------------------------


@pytest.mark.parametrize("raw, expected", [
    ("My Font", "My_Font"),
    ("../../etc/passwd", "etc_passwd"),
    ("C:\\Windows\\System32", "C_Windows_System32"),
    ("", "MyFont"),
    ("!!!", "MyFont"),
])
def test_family_names_cannot_escape_the_workspace(raw, expected):
    """The family name reaches the filesystem, so it must be neutralised."""
    assert safe_stem(raw, "MyFont") == expected

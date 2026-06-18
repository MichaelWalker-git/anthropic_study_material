"""
E2E browser test of navigation between questions (@e2e — only with --run-e2e).

This is the top of the pyramid: expensive, slow, but the only one that checks the
REAL frontend behavior in a browser. The instrumental/contract tests below don't
see the DOM, so the navigation-fix checks are placed here:
  * after "Back" the chosen option is visible;
  * feedback letters are consistent with the highlight (options are shuffled).

Requires: Chrome in /Applications, Node, puppeteer-core (installed once).
"""

import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

TESTS_DIR = Path(__file__).resolve().parent
APP_DIR = TESTS_DIR.parent
DRIVER = TESTS_DIR / "e2e_nav.mjs"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _puppeteer_path() -> str | None:
    """Looks for puppeteer-core; returns the path to the ESM entry or None."""
    for base in [APP_DIR / "node_modules", Path("/tmp/node_modules")]:
        entry = base / "puppeteer-core" / "lib" / "esm" / "puppeteer" / "puppeteer-core.js"
        if entry.exists():
            return str(entry)
    return None


@pytest.fixture
def server(tmp_path):
    """Starts uvicorn with an ISOLATED attempts.jsonl on a free port."""
    if not Path("/Applications/Google Chrome.app").exists():
        pytest.skip("Chrome not found")
    if shutil.which("node") is None:
        pytest.skip("Node not found")

    port = _free_port()
    # CRITICAL: pass the override into the subprocess environment, otherwise the
    # server writes to the user's real attempts.jsonl (this is the bug that hid here).
    env = {**os.environ, "ATTEMPTS_PATH_OVERRIDE": str(tmp_path / "attempts.jsonl")}
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "app:app", "--port", str(port)],
        cwd=APP_DIR, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    # Wait until ready.
    base = f"http://127.0.0.1:{port}/"
    import urllib.request
    for _ in range(50):
        try:
            urllib.request.urlopen(base, timeout=1)
            break
        except Exception:
            time.sleep(0.2)
    else:
        proc.terminate()
        pytest.fail("server did not start")
    yield base
    proc.terminate()
    proc.wait(timeout=10)


def test_back_navigation_shows_selection_and_consistent_letters(server):
    pup = _puppeteer_path()
    if pup is None:
        pytest.skip("puppeteer-core not installed (npm i puppeteer-core)")

    out = subprocess.run(
        ["node", str(DRIVER), server, pup],
        capture_output=True, text=True, timeout=90,
    )
    assert out.returncode == 0, out.stderr
    result = json.loads(out.stdout.strip().splitlines()[-1])
    assert result["ok"], result.get("error")

    # Fix #1: after "Back" the chosen option is visible.
    assert result["selectedVisible"], "the chosen option should be highlighted after 'Back'"
    assert result["selectedLetter"] == "B"
    assert result["feedbackVisible"]
    assert result["submitHidden"], "in review mode 'Answer' is hidden"

    # Fix #2: the letter in the feedback text == the highlighted button.
    assert result["correctHighlighted"] == result["correctInText"], \
        "the correct letter in the text should match the highlighted button"

    # Navigator: the grid exists, question 1 is done (colored) and marked current.
    assert result["navCellCount"] > 1, "the navigator should show question numbers"
    assert result["cell1Colored"], "a completed question in the navigator should be green/red"
    assert result["cell1IsCurrent"], "the current question should be marked in the navigator"
    # Clicking a number in the navigator jumps to that question.
    assert result["navClickWorks"]

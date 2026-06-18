"""
Shared test infrastructure.

Core principles (as a Principal QA would see them):
1. SIDE-EFFECT ISOLATION. No test touches the real attempts.jsonl — each gets a
   fresh temporary file via monkeypatch. Otherwise tests would depend on run
   order and pollute the user's real statistics.
2. DETERMINISM. We seed random in a fixture so shuffling/sampling are reproducible.
3. LLM IS SEPARATE. Agent tests do NOT hit Bedrock by default (mocked). Live
   calls happen only with the --run-live flag (they cost money, are slow, and
   are non-deterministic).
"""

import importlib
import random
import sys
from pathlib import Path

import pytest

# Application modules live one level above tests/ — add it to the path.
APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))


def pytest_addoption(parser):
    parser.addoption(
        "--run-live", action="store_true", default=False,
        help="Run tests that actually call Bedrock (costs money).",
    )
    parser.addoption(
        "--run-e2e", action="store_true", default=False,
        help="Run browser E2E tests (requires Chrome + Node/puppeteer).",
    )


def pytest_collection_modifyitems(config, items):
    """Skip marked tests when the corresponding flag was not passed."""
    gates = [
        ("live", "--run-live", "requires --run-live (real Bedrock call)"),
        ("e2e", "--run-e2e", "requires --run-e2e (browser test)"),
    ]
    for mark, flag, reason in gates:
        if config.getoption(flag):
            continue
        skip = pytest.mark.skip(reason=reason)
        for item in items:
            if mark in item.keywords:
                item.add_marker(skip)


@pytest.fixture
def app_module(tmp_path, monkeypatch):
    """Fresh import of app with an ISOLATED attempts.jsonl in tmp.

    We reload the module so the global ATTEMPTS_PATH is re-read, then immediately
    patch it to a temporary one — so each test's log is separate and empty.
    """
    import app
    importlib.reload(app)
    monkeypatch.setattr(app, "ATTEMPTS_PATH", tmp_path / "attempts.jsonl")
    return app


@pytest.fixture
def client(app_module):
    """TestClient on top of the isolated app."""
    from fastapi.testclient import TestClient
    return TestClient(app_module.app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def seeded_random():
    """Fix random for reproducible shuffles and samples."""
    random.seed(1234)
    yield


@pytest.fixture
def answer_all(app_module):
    """Helper: answer a list of public questions with a given strategy.

    strategy(q_raw) -> original_letter. Returns a list of verdicts.
    Uses the real /grade, so it writes to the isolated log.
    """
    from fastapi.testclient import TestClient
    cl = TestClient(app_module.app, raise_server_exceptions=False)

    def _run(public_questions, strategy, mode="practice"):
        verdicts = []
        for pq in public_questions:
            raw = app_module.QUESTIONS_BY_ID[pq["id"]]
            chosen = strategy(raw)
            v = cl.post("/api/grade", json={
                "question_id": pq["id"], "original_letter": chosen, "mode": mode,
            }).json()
            verdicts.append(v)
        return verdicts

    return _run

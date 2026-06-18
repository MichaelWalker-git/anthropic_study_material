"""
Contract for the deterministic API core: /scenarios, /session, /grade.

These are behavioral tests at the HTTP level — what the frontend relies on. There
is no LLM here, so they are fast and fully deterministic.
"""

import pytest


# --- /api/scenarios ---

def test_scenarios_shape(client, app_module):
    r = client.get("/api/scenarios")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == len(app_module.QUESTIONS)
    assert set(body["scenarios"]) == set(body["counts"])
    assert sum(body["counts"].values()) == body["total"]


# --- /api/session ---

def test_session_default_practice_returns_questions(client):
    r = client.post("/api/session", json={"mode": "practice"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == len(body["questions"]) > 0


def test_exam_session_capped_at_60(client):
    body = client.post("/api/session", json={"mode": "exam"}).json()
    assert body["count"] == 60


def test_session_scenario_filter(client, app_module):
    scenario = app_module.SCENARIOS[0]
    body = client.post("/api/session", json={"mode": "practice", "scenario": scenario}).json()
    for pq in body["questions"]:
        assert pq["scenario"] == scenario


def test_session_unknown_scenario_404(client):
    r = client.post("/api/session", json={"mode": "practice", "scenario": "Nope"})
    assert r.status_code == 404


def test_session_count_clamped_to_pool(client, app_module):
    """Requesting more questions than the scenario has is clamped to the pool size."""
    scenario = app_module.SCENARIOS[0]
    pool = sum(1 for q in app_module.QUESTIONS if q["scenario"] == scenario)
    body = client.post("/api/session",
                       json={"mode": "practice", "scenario": scenario, "count": pool + 999}).json()
    assert body["count"] == pool


def test_session_never_leaks_answer_key(client):
    """CRITICAL: a public question does NOT contain correct/why/explanations.

    If the client sees the correct answer up front, both practice and exam lose
    their point. This is a security invariant, not cosmetics.
    """
    body = client.post("/api/session", json={"mode": "exam"}).json()
    forbidden = {"correct", "why", "explanations", "correct_letter"}
    for pq in body["questions"]:
        assert not (forbidden & set(pq)), f"key leaked in question {pq['id']}: {pq.keys()}"
        for opt in pq["options"]:
            assert "correct" not in opt, "an option must not contain the correct flag"


def test_session_options_are_permutation(client):
    """Every question has exactly A-D, and original_letter is a permutation of A-D."""
    body = client.post("/api/session", json={"mode": "exam"}).json()
    for pq in body["questions"]:
        shown = [o["letter"] for o in pq["options"]]
        orig = [o["original_letter"] for o in pq["options"]]
        assert shown == ["A", "B", "C", "D"]
        assert sorted(orig) == ["A", "B", "C", "D"]


def test_shuffle_actually_varies_order(client, monkeypatch, app_module):
    """Shuffling actually changes positions (not always A->A)."""
    import random
    random.seed(7)
    body = client.post("/api/session", json={"mode": "exam"}).json()
    # In at least one question the shown letter should differ from the original.
    moved = any(o["letter"] != o["original_letter"]
                for pq in body["questions"] for o in pq["options"])
    assert moved, "shuffling changed no option at all — suspicious"


# --- /api/grade ---

def _first_question(client, app_module):
    pq = client.post("/api/session", json={"mode": "practice"}).json()["questions"][0]
    return pq, app_module.QUESTIONS_BY_ID[pq["id"]]


def test_grade_correct_answer(client, app_module):
    pq, raw = _first_question(client, app_module)
    r = client.post("/api/grade", json={"question_id": pq["id"], "original_letter": raw["correct"]})
    body = r.json()
    assert body["is_correct"] is True
    assert body["correct_letter"] == raw["correct"]
    assert body["why"]


def test_grade_wrong_answer(client, app_module):
    pq, raw = _first_question(client, app_module)
    wrong = next(l for l in "ABCD" if l != raw["correct"])
    body = client.post("/api/grade", json={"question_id": pq["id"], "original_letter": wrong}).json()
    assert body["is_correct"] is False
    assert body["correct_letter"] == raw["correct"]


def test_grade_wrong_on_mock_exam_returns_chosen_why(client, app_module):
    """For a mock-exam question, a wrong choice returns the explanation of that very option."""
    mock = next((q for q in app_module.QUESTIONS if q.get("source") == "mock-exam"), None)
    if mock is None:
        pytest.skip("no mock-exam questions in the bank")
    wrong = next(l for l in "ABCD" if l != mock["correct"])
    body = client.post("/api/grade", json={"question_id": mock["id"], "original_letter": wrong}).json()
    assert body["chosen_why"], "expected an explanation of the wrong option"


def test_grade_correct_has_no_chosen_why(client, app_module):
    mock = next((q for q in app_module.QUESTIONS if q.get("source") == "mock-exam"), None)
    if mock is None:
        pytest.skip("no mock-exam questions")
    body = client.post("/api/grade",
                       json={"question_id": mock["id"], "original_letter": mock["correct"]}).json()
    assert body["chosen_why"] is None


def test_grade_unknown_question_404(client):
    r = client.post("/api/grade", json={"question_id": 10**9, "original_letter": "A"})
    assert r.status_code == 404


def test_grade_writes_one_attempt_per_call(client, app_module):
    pq, raw = _first_question(client, app_module)
    client.post("/api/grade", json={"question_id": pq["id"], "original_letter": raw["correct"]})
    client.post("/api/grade", json={"question_id": pq["id"], "original_letter": "A"})
    lines = app_module.ATTEMPTS_PATH.read_text().strip().splitlines()
    assert len(lines) == 2

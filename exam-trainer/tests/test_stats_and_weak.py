"""
Statistics (/api/stats) and weak-spot sampling (mode="weak").

Subtle bugs live here: accuracy aggregation, weakest-topic detection, sample
weighting, absence of duplicates. We check both the logic and the DISTRIBUTION
(a statistical test over a large enough sample).
"""

import json

import pytest


def _seed_log(app_module, records):
    """Writes raw attempt lines into the isolated attempts.jsonl."""
    with app_module.ATTEMPTS_PATH.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")


# --- /api/stats ---

def test_stats_empty_when_no_log(client):
    body = client.get("/api/stats").json()
    assert body["total"] == 0
    assert body["by_scenario"] == {}


def test_stats_aggregates_accuracy(client, app_module):
    _seed_log(app_module, [
        {"question_id": 1, "scenario": "S-A", "is_correct": True},
        {"question_id": 2, "scenario": "S-A", "is_correct": False},
        {"question_id": 3, "scenario": "S-B", "is_correct": True},
    ])
    body = client.get("/api/stats").json()
    assert body["total"] == 3
    assert body["correct"] == 2
    assert body["by_scenario"]["S-A"]["accuracy"] == 0.5
    assert body["by_scenario"]["S-B"]["accuracy"] == 1.0


def test_stats_weakest_scenario(client, app_module):
    _seed_log(app_module, [
        {"question_id": 1, "scenario": "Strong", "is_correct": True},
        {"question_id": 2, "scenario": "Strong", "is_correct": True},
        {"question_id": 3, "scenario": "Weak", "is_correct": False},
        {"question_id": 4, "scenario": "Weak", "is_correct": False},
    ])
    assert client.get("/api/stats").json()["weakest_scenario"] == "Weak"


def test_stats_ignores_blank_lines(client, app_module):
    app_module.ATTEMPTS_PATH.write_text(
        '{"question_id":1,"scenario":"S","is_correct":true}\n\n\n', encoding="utf-8")
    assert client.get("/api/stats").json()["total"] == 1


# --- mode="weak" ---

def test_weak_session_returns_requested_count(client):
    body = client.post("/api/session", json={"mode": "weak", "count": 10}).json()
    assert body["count"] == 10


def test_weak_session_no_duplicates(client):
    body = client.post("/api/session", json={"mode": "weak", "count": 15}).json()
    ids = [q["id"] for q in body["questions"]]
    assert len(ids) == len(set(ids)), "a weak session must have no repeats"


def test_weak_count_clamped_to_pool(client, app_module):
    scenario = app_module.SCENARIOS[0]
    pool = sum(1 for q in app_module.QUESTIONS if q["scenario"] == scenario)
    body = client.post("/api/session",
                       json={"mode": "weak", "scenario": scenario, "count": pool + 50}).json()
    assert body["count"] == pool


def test_question_accuracy_ignores_generated(app_module):
    """Generated questions (id<0) do not enter accuracy statistics."""
    _seed_log(app_module, [
        {"question_id": -1, "scenario": "Gen", "is_correct": False},
        {"question_id": 1, "scenario": "S", "is_correct": True},
    ])
    acc = app_module._question_accuracy()
    assert -1 not in acc
    assert 1 in acc


def test_weak_weighting_favors_failed_questions(client, app_module, monkeypatch):
    """STATISTICAL test: over many runs, failed questions are picked more often
    than consistently correct ones. This is the essence of the feature — we check
    the distribution, not a single sample.
    """
    import random
    # Take real ids from a single scenario so the pool is controlled.
    scenario = app_module.SCENARIOS[0]
    ids = [q["id"] for q in app_module.QUESTIONS if q["scenario"] == scenario]
    failed_ids, passed_ids = set(ids[:3]), set(ids[3:6])

    log = []
    for qid in failed_ids:
        log += [{"question_id": qid, "scenario": scenario, "is_correct": False}] * 3
    for qid in passed_ids:
        log += [{"question_id": qid, "scenario": scenario, "is_correct": True}] * 3
    _seed_log(app_module, log)

    random.seed(0)
    from collections import Counter
    picks = Counter()
    for _ in range(300):
        body = client.post("/api/session",
                           json={"mode": "weak", "scenario": scenario, "count": 5}).json()
        for q in body["questions"]:
            if q["id"] in failed_ids: picks["failed"] += 1
            elif q["id"] in passed_ids: picks["passed"] += 1

    assert picks["failed"] > picks["passed"] * 2, \
        f"failed questions should be picked noticeably more often: {dict(picks)}"

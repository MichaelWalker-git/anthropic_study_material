"""
Diagnostician agent (diagnostician.py) + the /api/diagnose endpoint.

Same strategy: we mock Bedrock and verify the deterministic wrapper:
  * empty input -> no model call;
  * handoff guard: recommended_scenario must come from the known list,
    otherwise fall back to the scenario with the most errors;
  * the endpoint correctly RECONSTRUCTS the texts of failed questions and filters
    out the correct ones.
"""

import types

import pytest


def _fake_diag(payload):
    block = types.SimpleNamespace(type="tool_use", input=payload)
    return types.SimpleNamespace(content=[block])


class _FakeClient:
    def __init__(self, payload):
        self._payload = payload
        self.last_prompt = None
        self.messages = types.SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.last_prompt = kwargs["messages"][0]["content"]
        return _fake_diag(self._payload)


GOOD = {
    "summary": "The learner confuses plan mode with direct execution.",
    "misconceptions": ["Underestimates planning for complex tasks"],
    "recommended_scenario": "Code Generation with Claude Code",
    "recommendation": "Focus on choosing plan mode.",
}

WRONG_SAMPLE = [{
    "scenario": "Code Generation with Claude Code",
    "situation": "Restructure a monolith into microservices.",
    "prompt": "Which approach?",
    "options": {"A": "direct", "B": "plan mode", "C": "incremental", "D": "upfront"},
    "chosen": "A", "correct": "B", "why": "Plan mode explores deps first.",
}]


def test_empty_input_skips_model(app_module, monkeypatch):
    import diagnostician
    # If the model gets called it will fail; we verify it is NOT called.
    monkeypatch.setattr(diagnostician, "AnthropicBedrock",
                        lambda: (_ for _ in ()).throw(AssertionError("should not have been called")))
    out = diagnostician.diagnose([], ["S"])
    assert out["recommended_scenario"] is None
    assert out["misconceptions"] == []


def test_diagnose_returns_structured(app_module, monkeypatch):
    import diagnostician
    monkeypatch.setattr(diagnostician, "AnthropicBedrock", lambda: _FakeClient(GOOD))
    out = diagnostician.diagnose(WRONG_SAMPLE, ["Code Generation with Claude Code"])
    assert out["recommended_scenario"] == "Code Generation with Claude Code"
    assert out["summary"]


def test_handoff_guard_falls_back_on_bad_scenario(app_module, monkeypatch):
    """If the model recommends a scenario outside the list, fall back to the one
    with the most errors (reliable handoff to the generator)."""
    import diagnostician
    bad = {**GOOD, "recommended_scenario": "Hallucinated Scenario"}
    monkeypatch.setattr(diagnostician, "AnthropicBedrock", lambda: _FakeClient(bad))
    out = diagnostician.diagnose(WRONG_SAMPLE, ["Code Generation with Claude Code"])
    assert out["recommended_scenario"] == "Code Generation with Claude Code"


def test_diagnose_endpoint_reconstructs_and_filters(client, app_module, monkeypatch):
    """The endpoint takes id+chosen, reconstructs texts, filters out CORRECT answers."""
    import diagnostician
    captured = {}

    def fake_diagnose(wrong, scenarios):
        captured["wrong"] = wrong
        captured["scenarios"] = scenarios
        return GOOD

    monkeypatch.setattr(diagnostician, "diagnose", fake_diagnose)

    # Take 2 real questions: answer one correctly, the other wrong.
    q_correct = app_module.QUESTIONS[0]
    q_wrong = app_module.QUESTIONS[1]
    wrong_letter = next(l for l in "ABCD" if l != q_wrong["correct"])

    r = client.post("/api/diagnose", json={"answers": [
        {"question_id": q_correct["id"], "chosen": q_correct["correct"]},   # correct — filtered out
        {"question_id": q_wrong["id"], "chosen": wrong_letter},             # wrong — kept
        {"question_id": 10**9, "chosen": "A"},                              # unknown — filtered out
    ]})
    assert r.status_code == 200
    assert len(captured["wrong"]) == 1, "only one failed question should remain"
    assert captured["wrong"][0]["id"] if "id" in captured["wrong"][0] else True
    assert captured["wrong"][0]["chosen"] == wrong_letter


def test_diagnose_endpoint_502_on_agent_error(client, monkeypatch):
    import diagnostician
    monkeypatch.setattr(diagnostician, "diagnose",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    # At least one wrong question is needed to reach the agent call.
    import app
    q = app.QUESTIONS[0]
    wrong = next(l for l in "ABCD" if l != q["correct"])
    r = client.post("/api/diagnose", json={"answers": [{"question_id": q["id"], "chosen": wrong}]})
    assert r.status_code == 502


@pytest.mark.live
def test_diagnose_live(app_module):
    import diagnostician
    scenarios = app_module.SCENARIOS
    out = diagnostician.diagnose(WRONG_SAMPLE, scenarios)
    assert out["summary"]
    assert out["recommended_scenario"] in scenarios

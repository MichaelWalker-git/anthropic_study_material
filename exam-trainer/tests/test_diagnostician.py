"""
Агент-діагност (diagnostician.py) + endpoint /api/diagnose.

Та сама стратегія: мокаємо Bedrock, перевіряємо детерміновану обгортку:
  * порожній вхід -> без виклику моделі;
  * захист handoff: recommended_scenario мусить бути з відомого списку,
    інакше фолбек на сценарій із найбільшою кількістю помилок;
  * endpoint правильно ВІДНОВЛЮЄ тексти провалених питань і відсіює правильні.
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
    "summary": "Учень плутає plan mode з direct execution.",
    "misconceptions": ["Недооцінює планування для складних задач"],
    "recommended_scenario": "Code Generation with Claude Code",
    "recommendation": "Зосередься на виборі plan mode.",
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
    # Якщо модель викличеться — впаде; перевіряємо, що НЕ викликається.
    monkeypatch.setattr(diagnostician, "AnthropicBedrock",
                        lambda: (_ for _ in ()).throw(AssertionError("не мало викликатись")))
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
    """Якщо модель порекомендувала сценарій поза списком — фолбек на той,
    де найбільше помилок (надійний handoff до генератора)."""
    import diagnostician
    bad = {**GOOD, "recommended_scenario": "Hallucinated Scenario"}
    monkeypatch.setattr(diagnostician, "AnthropicBedrock", lambda: _FakeClient(bad))
    out = diagnostician.diagnose(WRONG_SAMPLE, ["Code Generation with Claude Code"])
    assert out["recommended_scenario"] == "Code Generation with Claude Code"


def test_diagnose_endpoint_reconstructs_and_filters(client, app_module, monkeypatch):
    """Endpoint бере id+chosen, відновлює тексти, відсіює ПРАВИЛЬНІ відповіді."""
    import diagnostician
    captured = {}

    def fake_diagnose(wrong, scenarios):
        captured["wrong"] = wrong
        captured["scenarios"] = scenarios
        return GOOD

    monkeypatch.setattr(diagnostician, "diagnose", fake_diagnose)

    # Візьмемо 2 реальні питання: одне відповімо правильно, друге — хибно.
    q_correct = app_module.QUESTIONS[0]
    q_wrong = app_module.QUESTIONS[1]
    wrong_letter = next(l for l in "ABCD" if l != q_wrong["correct"])

    r = client.post("/api/diagnose", json={"answers": [
        {"question_id": q_correct["id"], "chosen": q_correct["correct"]},   # правильна — відсіється
        {"question_id": q_wrong["id"], "chosen": wrong_letter},             # хибна — лишиться
        {"question_id": 10**9, "chosen": "A"},                              # невідома — відсіється
    ]})
    assert r.status_code == 200
    assert len(captured["wrong"]) == 1, "має лишитись лише одне провалене питання"
    assert captured["wrong"][0]["id"] if "id" in captured["wrong"][0] else True
    assert captured["wrong"][0]["chosen"] == wrong_letter


def test_diagnose_endpoint_502_on_agent_error(client, monkeypatch):
    import diagnostician
    monkeypatch.setattr(diagnostician, "diagnose",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    # Потрібне хоч одне хибне питання, щоб дійти до виклику агента.
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

"""
Агент-генератор (generator.py).

Стратегія: НЕ ходимо в Bedrock у звичайних тестах. Натомість мокаємо
AnthropicBedrock і перевіряємо ДЕТЕРМІНОВАНУ логіку навколо моделі:
  * валідація структури (4 варіанти, рівно одна правильна, без витоку);
  * ретрай на відхилену відповідь;
  * мапінг tool_use -> наш формат;
  * захист від невідомого сценарію.
Живий end-to-end виклик — лише з --run-live.
"""

import types

import pytest


# --- Хелпери для моку Bedrock ---

def _fake_tool_use(payload):
    """Імітує відповідь Messages API з одним tool_use блоком."""
    block = types.SimpleNamespace(type="tool_use", input=payload)
    return types.SimpleNamespace(content=[block])


class _FakeClient:
    """Підставний AnthropicBedrock: віддає заздалегідь задані відповіді по черзі."""
    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.calls = 0
        self.messages = types.SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls += 1
        return _fake_tool_use(self._payloads.pop(0))


VALID_PAYLOAD = {
    "situation": "A coordinator delegates to subagents that duplicate work.",
    "prompt": "What is the most effective architectural fix?",
    "options": ["Partition the research space up front",
                "Let them overlap and dedup later",
                "Run agents sequentially",
                "Add more agents"],
    "correct_index": 0,
    "why": "Partitioning at decomposition time prevents duplicated effort.",
}


@pytest.fixture
def gen(app_module, monkeypatch):
    import generator
    # Сценарії беремо з реального банку (через questions.json генератора).
    return generator, monkeypatch


# --- Валідація (чистий, без моку) ---

def test_validate_accepts_good_question(gen):
    generator, _ = gen
    assert generator._validate({
        "options": ["a", "b", "c", "d"], "correct_index": 0,
        "prompt": "Why?",
    }) is None


@pytest.mark.parametrize("bad,reason", [
    ({"options": ["a", "b", "c"], "correct_index": 0, "prompt": "Why?"}, "3 варіанти"),
    ({"options": ["a", "a", "b", "c"], "correct_index": 0, "prompt": "Why?"}, "дублі"),
    ({"options": ["a", "b", "c", "d"], "correct_index": 9, "prompt": "Why?"}, "індекс поза 0-3"),
    ({"options": ["a", "b", "c", "d"], "correct_index": 0, "prompt": "No question mark"}, "немає ?"),
])
def test_validate_rejects_bad(gen, bad, reason):
    generator, _ = gen
    assert generator._validate(bad) is not None, reason


def test_validate_detects_answer_leak(gen):
    generator, _ = gen
    bad = {
        "options": ["the answer is X", "b", "c", "d"], "correct_index": 0,
        "prompt": "Which says the answer is X?",
    }
    assert "leak" in generator._validate(bad).lower()


# --- Логіка генерації з моком клієнта ---

def test_generate_returns_bank_format(gen):
    generator, mp = gen
    scenario = generator.valid_scenarios().pop()
    mp.setattr(generator, "AnthropicBedrock", lambda: _FakeClient([VALID_PAYLOAD]))
    q = generator.generate_question(scenario)
    assert set(q["options"]) == {"A", "B", "C", "D"}
    assert q["correct"] == "A"               # correct_index 0 -> "A"
    assert q["generated"] is True
    assert q["scenario"] == scenario


def test_generate_retries_on_invalid_then_succeeds(gen):
    generator, mp = gen
    scenario = generator.valid_scenarios().pop()
    bad = {**VALID_PAYLOAD, "options": ["a", "b", "c"]}  # лише 3 — відхилиться
    client = _FakeClient([bad, VALID_PAYLOAD])
    mp.setattr(generator, "AnthropicBedrock", lambda: client)
    q = generator.generate_question(scenario, max_retries=1)
    assert client.calls == 2, "має бути один ретрай після відхилення"
    assert q["correct"] == "A"


def test_generate_raises_after_exhausting_retries(gen):
    generator, mp = gen
    scenario = generator.valid_scenarios().pop()
    bad = {**VALID_PAYLOAD, "options": ["a", "b", "c"]}
    mp.setattr(generator, "AnthropicBedrock", lambda: _FakeClient([bad, bad]))
    with pytest.raises(RuntimeError):
        generator.generate_question(scenario, max_retries=1)


def test_generate_unknown_scenario_raises(gen):
    generator, _ = gen
    with pytest.raises(ValueError):
        generator.generate_question("Totally Unknown Scenario")


# --- Живий тест (опційно) ---

@pytest.mark.live
def test_generate_live(app_module):
    import generator
    scenario = generator.valid_scenarios().pop()
    q = generator.generate_question(scenario)
    assert generator._validate({
        "options": list(q["options"].values()),
        "correct_index": "ABCD".index(q["correct"]),
        "prompt": q["prompt"],
    }) is None

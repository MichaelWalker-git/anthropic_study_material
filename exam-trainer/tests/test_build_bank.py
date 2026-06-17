"""
Збірка банку (build_bank.py): парсинг, нормалізація, дедуплікація.

Це найбагатша на регресії частина (саме тут був баг розсинхрону назв сценаріїв
та "Unknown scenario" у генераторі). Тестуємо чисті функції без I/O.
"""

import pytest

import build_bank


def test_similar_identical_is_high():
    assert build_bank._similar("hello world foo", "hello world foo") > 0.95


def test_similar_unrelated_is_low():
    assert build_bank._similar("alpha beta gamma", "completely different text here") < 0.4


def test_guide_scenario_aliases_normalize():
    """Назви з гайда зводяться до канонічних mock-exam (інакше дублі-сценарії)."""
    assert build_bank.GUIDE_SCENARIO_ALIASES["Customer Support Agent"] == \
        "Customer Support Resolution Agent"
    assert build_bank.GUIDE_SCENARIO_ALIASES["Multi-agent Research System"] == \
        "Multi-Agent Research System"


def test_merge_drops_near_duplicates():
    primary = [{"situation": None, "prompt": "What is the capital of France?"}]
    secondary = [
        {"situation": None, "prompt": "What is the capital of France?"},   # дубль
        {"situation": None, "prompt": "How do you configure an MCP server?"},  # новий
    ]
    merged, added = build_bank.merge(primary, secondary, threshold=0.6)
    assert added == 1
    assert len(merged) == 2


def test_merge_keeps_all_primary():
    primary = [{"situation": None, "prompt": f"Q{i}"} for i in range(3)]
    merged, _ = build_bank.merge(primary, [], threshold=0.6)
    assert len(merged) == 3


def test_built_bank_scenarios_are_canonical():
    """Обидва джерела дають канонічні назви — після злиття не буде дублів-
    сценаріїв, що різняться лише регістром. Перевіряємо на рівні load-функцій
    (саме там нормалізація), не запускаючи дорогий O(n*m) merge."""
    scenarios = {q["scenario"] for q in build_bank.load_mock_questions()}
    scenarios |= {q["scenario"] for q in build_bank.load_guide_questions()}
    assert len(scenarios) == len({s.lower() for s in scenarios}), \
        f"є сценарії, що різняться лише регістром: {sorted(scenarios)}"


def test_mock_questions_have_canonical_scenario_names():
    """S-коди розгортаються в людські назви."""
    mock = build_bank.load_mock_questions()
    names = {q["scenario"] for q in mock}
    assert "Multi-Agent Research System" in names
    assert not any(n.startswith("S") and n[1:].isdigit() for n in names), \
        "лишились нерозгорнуті S-коди"

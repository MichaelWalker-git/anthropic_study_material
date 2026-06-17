"""
Спільна тестова інфраструктура.

Головні принципи (як їх бачить Principal QA):
1. ІЗОЛЯЦІЯ ПОБІЧНИХ ЕФЕКТІВ. Жоден тест не торкається справжнього attempts.jsonl —
   кожен дістає свіжий тимчасовий файл через monkeypatch. Інакше тести залежали б
   від порядку запуску й засмічували б реальну статистику користувача.
2. ДЕТЕРМІНІЗМ. random сідаємо фікстурою, щоб перемішування/вибірка були відтворювані.
3. LLM — ОКРЕМО. Тести агентів за замовчуванням НЕ ходять у Bedrock (мок). Живі
   виклики — лише з прапором --run-live (коштують грошей, повільні, недетерміновані).
"""

import importlib
import random
import sys
from pathlib import Path

import pytest

# Модулі застосунку лежать на рівень вище від tests/ — додаємо в path.
APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))


def pytest_addoption(parser):
    parser.addoption(
        "--run-live", action="store_true", default=False,
        help="Запускати тести, що реально звертаються до Bedrock (платно).",
    )
    parser.addoption(
        "--run-e2e", action="store_true", default=False,
        help="Запускати браузерні E2E-тести (потрібен Chrome + Node/puppeteer).",
    )


def pytest_collection_modifyitems(config, items):
    """Пропускаємо marked-тести, якщо відповідний прапор не передано."""
    gates = [
        ("live", "--run-live", "потребує --run-live (реальний Bedrock-виклик)"),
        ("e2e", "--run-e2e", "потребує --run-e2e (браузерний тест)"),
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
    """Свіжий імпорт app з ІЗОЛЬОВАНИМ attempts.jsonl у tmp.

    Перезавантажуємо модуль, щоб глобальний ATTEMPTS_PATH перечитався, і одразу
    патчимо його на тимчасовий — так лог кожного тесту окремий і порожній.
    """
    import app
    importlib.reload(app)
    monkeypatch.setattr(app, "ATTEMPTS_PATH", tmp_path / "attempts.jsonl")
    return app


@pytest.fixture
def client(app_module):
    """TestClient поверх ізольованого app."""
    from fastapi.testclient import TestClient
    return TestClient(app_module.app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def seeded_random():
    """Фіксуємо random для відтворюваності перемішувань і вибірок."""
    random.seed(1234)
    yield


@pytest.fixture
def answer_all(app_module):
    """Хелпер: відповісти на список public-питань заданою стратегією.

    strategy(q_raw) -> original_letter. Повертає список вердиктів.
    Використовує справжній /grade, тож пише в ізольований лог.
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

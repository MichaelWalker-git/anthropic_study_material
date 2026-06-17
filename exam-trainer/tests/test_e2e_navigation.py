"""
E2E браузерний тест навігації між питаннями (@e2e — лише з --run-e2e).

Це вершина піраміди: дорогий, повільний, але єдиний, що перевіряє РЕАЛЬНУ
поведінку фронтенду в браузері. Інструментальні/контрактні тести нижче не
бачать DOM, тож саме сюди винесено перевірку фіксів навігації:
  * після "Назад" видно обраний варіант;
  * літери у фідбеку узгоджені з підсвіткою (варіанти перемішані).

Потребує: Chrome у /Applications, Node, puppeteer-core (ставиться разово).
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
    """Шукає puppeteer-core; повертає шлях до ESM-входу або None."""
    for base in [APP_DIR / "node_modules", Path("/tmp/node_modules")]:
        entry = base / "puppeteer-core" / "lib" / "esm" / "puppeteer" / "puppeteer-core.js"
        if entry.exists():
            return str(entry)
    return None


@pytest.fixture
def server(tmp_path):
    """Піднімає uvicorn з ІЗОЛЬОВАНИМ attempts.jsonl на вільному порту."""
    if not Path("/Applications/Google Chrome.app").exists():
        pytest.skip("Chrome не знайдено")
    if shutil.which("node") is None:
        pytest.skip("Node не знайдено")

    port = _free_port()
    # КРИТИЧНО: передаємо override у середовище subprocess, інакше сервер пише
    # в реальний attempts.jsonl користувача (саме цей баг тут і ховався).
    env = {**os.environ, "ATTEMPTS_PATH_OVERRIDE": str(tmp_path / "attempts.jsonl")}
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "app:app", "--port", str(port)],
        cwd=APP_DIR, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    # Чекаємо готовності.
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
        pytest.fail("сервер не піднявся")
    yield base
    proc.terminate()
    proc.wait(timeout=10)


def test_back_navigation_shows_selection_and_consistent_letters(server):
    pup = _puppeteer_path()
    if pup is None:
        pytest.skip("puppeteer-core не встановлено (npm i puppeteer-core)")

    out = subprocess.run(
        ["node", str(DRIVER), server, pup],
        capture_output=True, text=True, timeout=90,
    )
    assert out.returncode == 0, out.stderr
    result = json.loads(out.stdout.strip().splitlines()[-1])
    assert result["ok"], result.get("error")

    # Фікс №1: після "Назад" обраний варіант видно.
    assert result["selectedVisible"], "обраний варіант має бути підсвічений після 'Назад'"
    assert result["selectedLetter"] == "B"
    assert result["feedbackVisible"]
    assert result["submitHidden"], "у режимі перегляду 'Відповісти' приховано"

    # Фікс №2: літера у тексті фідбеку == підсвічена кнопка.
    assert result["correctHighlighted"] == result["correctInText"], \
        "літера правильної у тексті має збігатися з підсвіченою кнопкою"

    # Навігатор: сітка є, питання 1 пройдене (пофарбоване) і позначене поточним.
    assert result["navCellCount"] > 1, "навігатор має показувати номери питань"
    assert result["cell1Colored"], "пройдене питання в навігаторі має бути зелене/червоне"
    assert result["cell1IsCurrent"], "поточне питання має бути позначене в навігаторі"
    # Клік по номеру в навігаторі переходить на те питання.
    assert result["navClickWorks"]

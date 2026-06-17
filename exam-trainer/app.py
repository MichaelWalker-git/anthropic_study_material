"""
FastAPI-сервер тренажера для іспиту Claude Certified Architect — Foundations.

Архітектурний принцип (нагадування): ядро вікторини — детерміноване. Сервер
лише роздає питання з questions.json, перемішує їх, звіряє відповідь із полем
"correct" і пише спробу в attempts.jsonl. Жодного LLM тут немає — модель
з'являється тільки в окремому генераторі нових питань (generator.py).

Два режими (відрізняються ЛИШЕ моментом показу правильної відповіді):
  * practice — фідбек одразу після кожного питання;
  * exam     — відповіді ховаються до кінця сесії, потім — підсумковий бал.

Перемішування варіантів: у банку правильна відповідь часто "A" (33/88), тож
ми тасуємо порядок варіантів на кожне питання, щоб не можна було вгадати.
"""

import json
import os
import random
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent
QUESTIONS_PATH = BASE_DIR / "questions.json"
# Лог спроб; можна перенаправити через env (зручно для тестів — щоб не чіпати
# реальний attempts.jsonl користувача).
ATTEMPTS_PATH = Path(os.getenv("ATTEMPTS_PATH_OVERRIDE", BASE_DIR / "attempts.jsonl"))
STATIC_DIR = BASE_DIR / "static"

# Кількість питань у симуляції іспиту (реальний іспит — 60; банк має 88).
EXAM_QUESTION_COUNT = 60

app = FastAPI(title="Exam Trainer")

# Питання вантажимо один раз на старті — файл маленький, тримати в пам'яті дешево.
QUESTIONS: list[dict] = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
QUESTIONS_BY_ID: dict[int, dict] = {q["id"]: q for q in QUESTIONS}
SCENARIOS: list[str] = sorted({q["scenario"] for q in QUESTIONS})


def public_question(q: dict, *, shuffle: bool) -> dict:
    """Готує питання для фронтенду БЕЗ правильної відповіді й пояснення.

    Правильну відповідь ніколи не віддаємо клієнту наперед — інакше exam-режим
    втрачає сенс, та й у practice її показуємо тільки після відповіді (окремим
    запитом на /grade). Варіанти за потреби тасуємо.
    """
    letters = ["A", "B", "C", "D"]
    if shuffle:
        random.shuffle(letters)
    # Перемальовуємо варіанти на нові позиції A-D, зберігаючи оригінальну літеру,
    # щоб сервер міг звірити відповідь, не довіряючи клієнту.
    options = []
    for new_letter, orig_letter in zip(["A", "B", "C", "D"], letters):
        options.append({
            "letter": new_letter,
            "original_letter": orig_letter,
            "text": q["options"][orig_letter],
        })
    return {
        "id": q["id"],
        "scenario": q["scenario"],
        "situation": q["situation"],
        "prompt": q["prompt"],
        "options": options,
    }


class GenerateRequest(BaseModel):
    scenario: str | None = None     # None = взяти найслабшу тему зі статистики


class AnswerRecord(BaseModel):
    question_id: int
    chosen: str                     # original_letter обраного варіанту


class DiagnoseRequest(BaseModel):
    answers: list[AnswerRecord]     # усі відповіді сесії (правильні відсіємо)


class SessionRequest(BaseModel):
    mode: str = "practice"          # "practice" | "exam"
    scenario: str | None = None     # фільтр (тільки practice); None = усі
    count: int | None = None        # скільки питань; None = розумний дефолт


class GradeRequest(BaseModel):
    question_id: int
    original_letter: str            # оригінальна літера обраного варіанту
    mode: str = "practice"


@app.get("/api/scenarios")
def get_scenarios() -> dict:
    """Список сценаріїв + кількість питань у кожному — для меню вибору."""
    counts = {s: sum(1 for q in QUESTIONS if q["scenario"] == s) for s in SCENARIOS}
    return {"scenarios": SCENARIOS, "counts": counts, "total": len(QUESTIONS)}


@app.post("/api/session")
def start_session(req: SessionRequest) -> dict:
    """Формує набір питань для сесії (порядок і варіанти перемішані).

    Режим "weak" — добивання слабких місць: зважена вибірка за статистикою
    помилок з attempts.jsonl (детермінована логіка, без LLM). Зазвичай
    запускається з екрана результатів після тесту.
    """
    pool = QUESTIONS
    if req.scenario:
        if req.scenario not in SCENARIOS:
            raise HTTPException(404, f"Unknown scenario: {req.scenario}")
        pool = [q for q in QUESTIONS if q["scenario"] == req.scenario]

    if req.mode == "weak":
        chosen = _pick_weak(pool, req.count or 10)
    else:
        if req.mode == "exam":
            count = req.count or min(EXAM_QUESTION_COUNT, len(pool))
        else:
            count = req.count or len(pool)
        count = max(1, min(count, len(pool)))
        chosen = random.sample(pool, count)

    questions = [public_question(q, shuffle=True) for q in chosen]
    return {"mode": req.mode, "count": len(questions), "questions": questions}


def _question_accuracy() -> dict[int, dict[str, int]]:
    """Точність по кожному question_id з логу: {id: {attempts, correct}}."""
    acc: dict[int, dict[str, int]] = {}
    if not ATTEMPTS_PATH.exists():
        return acc
    for line in ATTEMPTS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        qid = rec.get("question_id")
        if qid is None or qid < 0:  # згенеровані питання (id=-1) ігноруємо
            continue
        b = acc.setdefault(qid, {"attempts": 0, "correct": 0})
        b["attempts"] += 1
        b["correct"] += int(rec["is_correct"])
    return acc


def _pick_weak(pool: list[dict], count: int) -> list[dict]:
    """Зважена вибірка без повторів: пріоритет — питання з низькою точністю.

    Вага = (частка помилок) + базовий бонус. Непобачені питання (немає в логу)
    отримують високу вагу — невідоме теж є слабким місцем, інакше тренажер
    застрягне на кількох провалених і ніколи не покаже решту.
    """
    acc = _question_accuracy()
    weights = []
    for q in pool:
        stat = acc.get(q["id"])
        if stat is None or stat["attempts"] == 0:
            w = 1.0  # ще не бачили — високий пріоритет
        else:
            error_rate = 1 - stat["correct"] / stat["attempts"]
            w = 0.15 + error_rate  # базовий шанс + штраф за помилки
        weights.append(w)

    count = max(1, min(count, len(pool)))
    # Вибір без повторів пропорційно вазі (random.choices — з повторами, тому so):
    chosen: list[dict] = []
    candidates = list(zip(pool, weights))
    for _ in range(count):
        total = sum(w for _, w in candidates)
        r = random.uniform(0, total)
        upto = 0.0
        for i, (q, w) in enumerate(candidates):
            upto += w
            if upto >= r:
                chosen.append(q)
                candidates.pop(i)
                break
    return chosen


@app.post("/api/grade")
def grade(req: GradeRequest) -> dict:
    """Звіряє одну відповідь, логує спробу й повертає вердикт + пояснення.

    Працює для обох режимів: practice показує результат фронтенду одразу, exam
    накопичує їх і показує лише наприкінці — але логіка звірки та логування
    однакова, відрізняється тільки поведінка UI.
    """
    q = QUESTIONS_BY_ID.get(req.question_id)
    if q is None:
        raise HTTPException(404, f"Unknown question id: {req.question_id}")

    is_correct = req.original_letter == q["correct"]
    _log_attempt(question_id=q["id"], scenario=q["scenario"],
                 chosen=req.original_letter, correct=q["correct"],
                 is_correct=is_correct, mode=req.mode)

    # Пояснення саме обраного варіанту — є лише в питаннях з mock-exam
    # (поле "explanations" з поясненням до кожної опції). Для guide-питань None.
    chosen_why = None
    if not is_correct:
        chosen_why = (q.get("explanations") or {}).get(req.original_letter)

    return {
        "question_id": q["id"],
        "is_correct": is_correct,
        "correct_letter": q["correct"],
        "correct_text": q["options"][q["correct"]],
        "why": q["why"],
        "chosen_why": chosen_why,
    }


def _log_attempt(**fields) -> None:
    """Дописує одну спробу в attempts.jsonl (append-only, JSON-native).

    Свідомо БЕЗ часу: Date/random у деяких середовищах недоступні, та й для
    однокористувацького тренажера порядок рядків у файлі вже = хронологія.
    """
    with ATTEMPTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(fields, ensure_ascii=False) + "\n")


@app.get("/api/stats")
def stats() -> dict:
    """Агрегує attempts.jsonl у точність по сценаріях (для 'найслабшої теми').

    Групування робимо в Python — на сотнях рядків це миттєво, і не тягне SQLite.
    """
    if not ATTEMPTS_PATH.exists():
        return {"total": 0, "by_scenario": {}}

    agg: dict[str, dict[str, int]] = {}
    total = 0
    correct_total = 0
    for line in ATTEMPTS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        s = rec["scenario"]
        bucket = agg.setdefault(s, {"attempts": 0, "correct": 0})
        bucket["attempts"] += 1
        bucket["correct"] += int(rec["is_correct"])
        total += 1
        correct_total += int(rec["is_correct"])

    by_scenario = {
        s: {
            "attempts": b["attempts"],
            "correct": b["correct"],
            "accuracy": round(b["correct"] / b["attempts"], 3) if b["attempts"] else 0.0,
        }
        for s, b in agg.items()
    }
    weakest = min(by_scenario, key=lambda s: by_scenario[s]["accuracy"]) if by_scenario else None
    return {
        "total": total,
        "correct": correct_total,
        "accuracy": round(correct_total / total, 3) if total else 0.0,
        "by_scenario": by_scenario,
        "weakest_scenario": weakest,
    }


@app.post("/api/generate")
def generate(req: GenerateRequest) -> dict:
    """Генерує НОВЕ питання через Sonnet (єдиний LLM-виклик у застосунку).

    Імпорт відкладено всередину функції: ядро вікторини має працювати навіть
    без налаштованого Bedrock-ключа — модель потрібна тільки для цієї кнопки.
    Якщо scenario не задано — беремо найслабшу тему з накопиченої статистики.
    """
    scenario = req.scenario
    if scenario is None:
        weakest = stats().get("weakest_scenario")
        scenario = weakest or SCENARIOS[0]

    try:
        from generator import generate_question
        q = generate_question(scenario)
    except Exception as exc:  # noqa: BLE001 — повертаємо причину фронтенду
        raise HTTPException(502, f"Generation failed: {exc}")

    # Віддаємо у вигляді public_question + одразу answer key (це тренувальне
    # питання поза банком; зберігати його в questions.json не обов'язково).
    pub = public_question({**q, "id": -1}, shuffle=True)
    pub["correct_original_letter"] = q["correct"]
    pub["why"] = q["why"]
    return pub


@app.post("/api/diagnose")
def diagnose_endpoint(req: DiagnoseRequest) -> dict:
    """Агент-діагност: аналізує помилки сесії й рекомендує тему (2-й LLM).

    Фронтенд шле лише id + обраний варіант; повні тексти провалених питань
    відновлюємо тут із банку (клієнту їх віддавати наперед не можна).
    """
    wrong = []
    for a in req.answers:
        q = QUESTIONS_BY_ID.get(a.question_id)
        if q is None or a.chosen == q["correct"]:
            continue  # пропускаємо невідомі та правильні
        wrong.append({
            "scenario": q["scenario"],
            "situation": q["situation"],
            "prompt": q["prompt"],
            "options": q["options"],
            "chosen": a.chosen,
            "correct": q["correct"],
            "why": q["why"],
        })

    try:
        from diagnostician import diagnose
        return diagnose(wrong, SCENARIOS)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Diagnosis failed: {exc}")


# --- Статика: фронтенд. Монтуємо в кінці, щоб не перекривати /api/*. ---
@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
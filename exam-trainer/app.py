"""
FastAPI server for the Claude Certified Architect — Foundations exam trainer.

Architectural principle (reminder): the quiz core is deterministic. The server
only serves questions from questions.json, shuffles them, checks the answer
against the "correct" field, and writes the attempt to attempts.jsonl. There is
no LLM here — the model only appears in the separate new-question generator
(generator.py).

Two modes (differing ONLY in when the correct answer is revealed):
  * practice — feedback immediately after each question;
  * exam     — answers are hidden until the end of the session, then a final score.

Option shuffling: in the bank the correct answer is often "A" (33/88), so we
shuffle the option order for every question to prevent guessing.
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
# Attempt log; can be redirected via env (handy for tests — to avoid touching
# the user's real attempts.jsonl).
ATTEMPTS_PATH = Path(os.getenv("ATTEMPTS_PATH_OVERRIDE", BASE_DIR / "attempts.jsonl"))
STATIC_DIR = BASE_DIR / "static"

# Number of questions in the exam simulation (the real exam has 60; the bank has 88).
EXAM_QUESTION_COUNT = 60

app = FastAPI(title="Exam Trainer")

# Load questions once at startup — the file is small, keeping it in memory is cheap.
QUESTIONS: list[dict] = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
QUESTIONS_BY_ID: dict[int, dict] = {q["id"]: q for q in QUESTIONS}
SCENARIOS: list[str] = sorted({q["scenario"] for q in QUESTIONS})


def public_question(q: dict, *, shuffle: bool) -> dict:
    """Prepares a question for the frontend WITHOUT the correct answer or explanation.

    We never hand the correct answer to the client up front — otherwise exam mode
    loses its point, and even in practice we only show it after the answer (via a
    separate request to /grade). Options are shuffled when needed.
    """
    letters = ["A", "B", "C", "D"]
    if shuffle:
        random.shuffle(letters)
    # Remap the options to new positions A-D, keeping the original letter so the
    # server can verify the answer without trusting the client.
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
    scenario: str | None = None     # None = take the weakest topic from stats


class AnswerRecord(BaseModel):
    question_id: int
    chosen: str                     # original_letter of the chosen option


class DiagnoseRequest(BaseModel):
    answers: list[AnswerRecord]     # all session answers (correct ones filtered out)


class SessionRequest(BaseModel):
    mode: str = "practice"          # "practice" | "exam"
    scenario: str | None = None     # filter (practice only); None = all
    count: int | None = None        # how many questions; None = smart default


class GradeRequest(BaseModel):
    question_id: int
    original_letter: str            # original letter of the chosen option
    mode: str = "practice"


@app.get("/api/scenarios")
def get_scenarios() -> dict:
    """List of scenarios + question count for each — for the selection menu."""
    counts = {s: sum(1 for q in QUESTIONS if q["scenario"] == s) for s in SCENARIOS}
    return {"scenarios": SCENARIOS, "counts": counts, "total": len(QUESTIONS)}


@app.post("/api/session")
def start_session(req: SessionRequest) -> dict:
    """Builds the set of questions for a session (order and options shuffled).

    The "weak" mode drills weak spots: a weighted sample based on error statistics
    from attempts.jsonl (deterministic logic, no LLM). Usually launched from the
    results screen after a test.
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
    """Accuracy per question_id from the log: {id: {attempts, correct}}."""
    acc: dict[int, dict[str, int]] = {}
    if not ATTEMPTS_PATH.exists():
        return acc
    for line in ATTEMPTS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        qid = rec.get("question_id")
        if qid is None or qid < 0:  # ignore generated questions (id=-1)
            continue
        b = acc.setdefault(qid, {"attempts": 0, "correct": 0})
        b["attempts"] += 1
        b["correct"] += int(rec["is_correct"])
    return acc


def _pick_weak(pool: list[dict], count: int) -> list[dict]:
    """Weighted sampling without replacement: prioritize low-accuracy questions.

    Weight = (error rate) + a base bonus. Unseen questions (not in the log) get a
    high weight — the unknown is also a weak spot, otherwise the trainer would get
    stuck on a few failed ones and never show the rest.
    """
    acc = _question_accuracy()
    weights = []
    for q in pool:
        stat = acc.get(q["id"])
        if stat is None or stat["attempts"] == 0:
            w = 1.0  # not seen yet — high priority
        else:
            error_rate = 1 - stat["correct"] / stat["attempts"]
            w = 0.15 + error_rate  # base chance + penalty for errors
        weights.append(w)

    count = max(1, min(count, len(pool)))
    # Sampling without replacement, proportional to weight (random.choices samples
    # with replacement, hence the manual loop):
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
    """Checks one answer, logs the attempt, and returns the verdict + explanation.

    Works for both modes: practice shows the result to the frontend immediately,
    exam accumulates them and shows them only at the end — but the checking and
    logging logic is the same, only the UI behavior differs.
    """
    q = QUESTIONS_BY_ID.get(req.question_id)
    if q is None:
        raise HTTPException(404, f"Unknown question id: {req.question_id}")

    is_correct = req.original_letter == q["correct"]
    _log_attempt(question_id=q["id"], scenario=q["scenario"],
                 chosen=req.original_letter, correct=q["correct"],
                 is_correct=is_correct, mode=req.mode)

    # Explanation for the specifically chosen option — only present in mock-exam
    # questions (the "explanations" field with an explanation for each option).
    # None for guide questions.
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
    """Appends one attempt to attempts.jsonl (append-only, JSON-native).

    Deliberately WITHOUT a timestamp: Date/random aren't available in some
    environments, and for a single-user trainer the line order in the file already
    equals the chronology.
    """
    with ATTEMPTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(fields, ensure_ascii=False) + "\n")


@app.get("/api/stats")
def stats() -> dict:
    """Aggregates attempts.jsonl into per-scenario accuracy (for the 'weakest topic').

    We do the grouping in Python — on hundreds of lines it's instant, and it doesn't
    pull in SQLite.
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
    """Generates a NEW question via Sonnet (the only LLM call in the app).

    The import is deferred inside the function: the quiz core must work even
    without a configured Bedrock key — the model is only needed for this button.
    If scenario is not specified, we take the weakest topic from accumulated stats.
    """
    scenario = req.scenario
    if scenario is None:
        weakest = stats().get("weakest_scenario")
        scenario = weakest or SCENARIOS[0]

    try:
        from generator import generate_question
        q = generate_question(scenario)
    except Exception as exc:  # noqa: BLE001 — return the reason to the frontend
        raise HTTPException(502, f"Generation failed: {exc}")

    # Return it as a public_question + the answer key right away (this is a practice
    # question outside the bank; storing it in questions.json is not required).
    pub = public_question({**q, "id": -1}, shuffle=True)
    pub["correct_original_letter"] = q["correct"]
    pub["why"] = q["why"]
    return pub


@app.post("/api/diagnose")
def diagnose_endpoint(req: DiagnoseRequest) -> dict:
    """Diagnostician agent: analyzes session mistakes and recommends a topic (2nd LLM).

    The frontend sends only id + chosen option; we reconstruct the full text of the
    failed questions here from the bank (they must not be handed to the client up front).
    """
    wrong = []
    for a in req.answers:
        q = QUESTIONS_BY_ID.get(a.question_id)
        if q is None or a.chosen == q["correct"]:
            continue  # skip unknown and correct ones
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


# --- Static: the frontend. Mounted at the end so it doesn't shadow /api/*. ---
@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# Exam Trainer

A local trainer for the **Claude Certified Architect — Foundations** exam.

## What this is

A web application for practicing against a bank of **457 questions** (all with correct
answers). The quiz core is deterministic (parsing + verification), no LLM. The only
LLM call is the "✨ New question (AI)" button, which generates a fresh question via
Sonnet (Bedrock).

> **Bank sources (assembled by `build_bank.py`):**
> 1. `mock-exam` (the TS project in `anthropic_study_material/`) — 376 questions, 6
>    scenarios, with a domain tag and an explanation for EVERY option.
> 2. `guide_en.MD` — 88 questions (12 from `Examples` + 76 from `Practice Test`); after
>    deduplication, 81 unique ones are added (7 overlap with mock-exam).
>
> The screenshots in `../../screens/` are NOT used — they are the same guide bank
> rendered in the exam UI, without correct answers.

## Running

```bash
cd learning/exam-trainer
uv sync                                       # once
uv run python build_bank.py                   # both sources -> questions.json (457 questions)
uv run uvicorn app:app --reload --port 8000   # server
# open http://localhost:8000
```

Question generation requires `AWS_BEARER_TOKEN_BEDROCK` in `learning/.env` (already
present). Everything else (practice / exam / stats) works without a key.

## Structure

| File | Role |
|---|---|
| `build_bank.py` | assembles `questions.json` from both sources (mock-exam + guide), deduplicates |
| `parse_guide.py` | guide parser (used by `build_bank.py`) |
| `app.py` | FastAPI server: serves questions, grades, logs attempts |
| `generator.py` | generator agent: Sonnet creates new questions (generate → validate) |
| `diagnostician.py` | diagnostician agent: Sonnet analyzes session mistakes, recommends a topic |
| `static/` | thin vanilla-JS frontend (3 screens: setup → question → result) |
| `questions.json` | generated bank (do not edit by hand — regenerate with the parser) |
| `attempts.jsonl` | append-only log of attempts (delete the file to reset stats) |

## Tests

Pyramid: a fast deterministic core at the bottom, expensive LLM/browser tests on top, behind a flag.

```bash
uv run pytest                 # 61 deterministic tests, ~3s, no network and no LLM
uv run pytest --run-live      # + 2 live Bedrock tests (generator, diagnostician) — paid
uv run pytest --run-e2e       # + browser navigation test (Chrome + puppeteer-core)
```

| File | What it covers |
|---|---|
| `test_bank_integrity.py` | data invariants: 4 unique options, exactly one correct, no leaks |
| `test_api_core.py` | /session, /grade contract; **the key never leaks to the client**; shuffling |
| `test_stats_and_weak.py` | accuracy aggregation, weakest topic, weighted sampling (statistical test) |
| `test_generator.py` | validation + retry (Bedrock mocked); `@live` — real generation |
| `test_diagnostician.py` | handoff guard, recovery of failed questions; `@live` — real diagnosis |
| `test_build_bank.py` | parsing, scenario name normalization, deduplication |
| `test_e2e_navigation.py` | `@e2e` — "Back" shows the selection, letter consistency (real browser) |

Isolation: each test gets a temporary `attempts.jsonl` (via `ATTEMPTS_PATH_OVERRIDE`),
so the real stats are never touched. `random` is seeded for reproducibility.

For E2E, once: `npm install puppeteer-core` in the project folder (or in `/tmp`).

## Modes

- **Practice** — a single scenario (or all); feedback shown immediately by default.
- **Exam** — 60 questions from all scenarios; score shown at the end by default.

**The "show answer immediately" checkbox** controls feedback SEPARATELY from the mode —
so you can take an exam with instant answers, or practice with deferred ones. The
question set (exam vs scenario) and the moment the answer is revealed are two
independent axes.

**Resume a session:** non-exam sessions are saved in the browser (`localStorage`),
so after a reload an "↩ Resume" button appears on the start screen. Exams are
deliberately NOT saved (this mimics a real exam without pauses).

Options are shuffled for each question.

**Navigation:** the "← Back" / "Next →" buttons let you return to questions you've
already done. In practice (immediate feedback), the review shows your choice, the
correct answer, and the explanation. In exam mode, the review lets you CHANGE your
choice without revealing whether it's correct (as on a real exam).

## Two agents (multi-agent with handoff)

On the results screen — an example of the same pattern used at Capital Group:
each agent has a single responsibility, and the data handoff is structured.

1. **🧠 Mistake review** (`diagnostician.py`) — Sonnet analyzes the PATTERN of your
   mistakes (which concepts you systematically confuse), writes a conclusion, and
   recommends a topic.
2. **✨ Generation** (`generator.py`) — Sonnet creates a fresh question. Handoff:
   the diagnostician recommends a scenario → the button generates a question
   specifically for it.

Design boundary: selecting weak questions is CODE (the `weak` mode, statistics). We
apply the LLM only where code cannot: generating something new and diagnosing *why*.

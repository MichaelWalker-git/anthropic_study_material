# CCA-F Mock Exam

A local practice exam for the **Claude Certified Architect – Foundations (CCA-F)** certification. It runs entirely in your browser — no backend, no API key, no account.

The app mirrors the real exam format: it assembles a sitting of **4 randomly chosen scenarios × 15 questions = 60**, gives immediate feedback with explanations, runs a countdown timer, and reports a scaled score (pass mark 720) with a per-domain and per-scenario breakdown.

## Quick start

You need [Node.js](https://nodejs.org) 18+ installed.

```bash
cd mock-exam
npm install      # first time only
npm run dev
```

Open the URL it prints (usually http://localhost:5173) and click **Start Exam**.

To make a production build instead:

```bash
npm run build    # type-checks and bundles into dist/
npm run preview  # serve the production build locally
```

## How a sitting works

1. **Start screen** — shows the current question pool and lets you pick a duration (default 90 min). Click **Start Exam**.
2. **The exam** — one question at a time:
   - Pick an option and click **Submit Answer** to see whether you were right, with an explanation on the correct answer (and on your wrong pick, if any). The header score updates live.
   - **Skip →** moves on without answering; **Next →** appears after you submit.
   - **Flag** marks a question for later; flagged questions are highlighted in the navigator and listed in the results.
   - The **navigator** (the 1–60 grid) lets you jump back to any question you've already reached. Questions ahead of you are locked until you reach them. Click the **?** for a legend.
   - The **countdown timer** auto-submits the exam when it hits zero.
3. **Results** — your scaled score (100–1000, pass ≥ 720), overall percentage, accuracy per domain and per scenario, and a review of every missed question with full explanations.

### Question selection is random every time

Each scenario has **60+ questions** in the bank, but a sitting only shows **15 per scenario**. Those 15 are drawn at random from the full pool on every run, and the 4 scenarios themselves are chosen at random from the 6. So two attempts rarely overlap — retaking the exam is genuine new practice, not the same 15 questions again.

## The exam blueprint

The exam covers 5 weighted domains across 6 scenarios (defined in `public/blueprint.json`):

| Domain | Weight |
|---|---|
| D1 — Agentic Architecture & Orchestration | 27% |
| D2 — Tool Design & MCP Integration | 18% |
| D3 — Claude Code Configuration & Workflows | 20% |
| D4 — Prompt Engineering & Structured Output | 20% |
| D5 — Context Management & Reliability | 15% |

Scenarios: S1 Customer Support Resolution Agent · S2 Code Generation with Claude Code · S3 Multi-Agent Research System · S4 Developer Productivity with Claude · S5 Claude Code for CI · S6 Structured Data Extraction.

## The question bank

Questions live in `public/bank/S1.json … S6.json` (one file per scenario), loaded and merged in the browser at runtime. The pool currently holds **~376 questions** (60+ per scenario).

Each question looks like this:

```json
{
  "id": "S1-D2-001",
  "scenario": "S1",
  "domain": "D2",
  "task_statement": "2.1",
  "stem": "Production logs show the agent ... What's the most effective first step?",
  "options": [
    { "id": "A", "text": "…", "correct": false, "explanation": "Why this is wrong." },
    { "id": "B", "text": "…", "correct": true,  "explanation": "Why this is right." },
    { "id": "C", "text": "…", "correct": false, "explanation": "…" },
    { "id": "D", "text": "…", "correct": false, "explanation": "…" }
  ]
}
```

Rules every question follows: exactly four options (`A`–`D`), exactly one `correct: true`, and a non-empty `explanation` on **every** option (so the review screen explains both your answer and the right one).

### Adding or editing questions

1. Edit the relevant `public/bank/S<n>.json` file. Keep ids unique within the scenario (format `S<n>-D<domain>-<seq>`, e.g. `S1-D2-007`).
2. Validate before committing:
   ```bash
   node scripts/validate-bank.mjs        # all scenarios (or pass S1 S2 … for specific ones)
   ```
   This checks for: 0 structural errors, exactly one correct option, 4 options, unique ids, no duplicate stems, and reports per-domain/per-task coverage.
3. Check answer-length balance (so the correct option isn't always the longest — otherwise testers can "pick the longest and win"):
   ```bash
   node scripts/rebalance-report.mjs S1  # lists questions where the correct option is the longest
   ```
   Aim to keep all four options within ~20 characters of each other.

## Project layout

```
mock-exam/
  public/
    blueprint.json        # domains, weights, scenarios, session config (15×4, 90 min, pass 720)
    bank/S1..S6.json       # the question pool, one file per scenario
  src/
    lib/loadData.ts        # fetches blueprint + merges the per-scenario bank files
    lib/session.ts         # picks 4 random scenarios, 15 random questions each
    lib/scoring.ts         # raw → scaled score, per-domain/per-scenario stats
    state/examStore.tsx    # session state, timer, live score, locked progression
    components/, routes/    # the UI (start, exam, results screens)
  scripts/
    validate-bank.mjs      # structural + balance validator
    rebalance-report.mjs   # answer-length-bias report
```

## Notes

- This is **practice material**, not the official exam. The scaled score is an approximation (`100 + raw × 900`) of the certification's SME-equated model, intended to gauge readiness against the real 720 pass mark.
- No data leaves your machine — everything runs client-side from the JSON files.

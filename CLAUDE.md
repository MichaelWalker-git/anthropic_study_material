# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Study material for Anthropic / Claude certifications. It is not one application but a
collection of independent pieces that share a root directory:

- **`mock-exam/`** — a browser-only practice exam for the Claude Certified Architect –
  Foundations (CCA-F) cert. React + Vite + TanStack Router. Has its own README.
- **`queries/`** — a TypeScript/SQLite e-commerce query project used to practice the
  Claude Agent SDK and Claude Code hooks. Has its own `CLAUDE.md`.
- **Reference texts** (`*.txt`) — plain-text course transcripts (Claude Code 101,
  Claude Platform 101, MCP, AI Fluency, building with the Claude API, etc.).
- **Notebooks** (`001_*.ipynb`) — Python prompt-engineering / eval exercises using the
  `anthropic` SDK and `claude-haiku-4-5`.
- **PDFs** — supplementary guides.

The two sub-projects are unrelated codebases with separate `package.json`,
`tsconfig.json`, and dependency trees. `cd` into the relevant one before running
anything. There is no root-level build or install.

## mock-exam

```bash
cd mock-exam
npm install
npm run dev        # vite dev server (http://localhost:5173)
npm run build      # tsc -b && vite build
node scripts/validate-bank.mjs        # validate question bank (pass S1 S2 ... to scope)
node scripts/rebalance-report.mjs S1  # flag questions where the correct option is longest
```

Architecture:
- The question bank lives in `public/bank/S1.json … S6.json` (one file per scenario,
  ~376 questions total) and `public/blueprint.json` (domains + weights, scenarios,
  session config). Both are **static assets fetched at runtime** — there is no backend
  and no API key. `src/lib/loadData.ts` fetches and merges them in the browser.
- `src/lib/session.ts` assembles a sitting: pick 4 random scenarios of 6, draw 15 random
  questions from each (60 total), shuffle each question's options. So every run differs.
- `src/lib/scoring.ts` converts raw correct count to a scaled score
  (`scaled_min + rawPct * span`, pass ≥ 720) plus per-domain and per-scenario stats.
- `src/state/examStore.tsx` holds session state, the countdown timer, live score, and the
  locked forward-progression rule (you can revisit answered questions, not skip ahead).
- Question schema invariants (enforced by `validate-bank.mjs`): exactly 4 options A–D,
  exactly one `correct: true`, a non-empty `explanation` on **every** option, ids unique
  per scenario in `S<n>-D<domain>-<seq>` format, no duplicate stems.

When editing questions, edit the JSON in `public/bank/`, then run the validator and the
rebalance report before considering it done. See `mock-exam/README.md` for full detail.

## queries

See `queries/CLAUDE.md` for the full guide. Key points:
- TypeScript + SQLite e-commerce queries. `npm run setup` installs deps **and** runs
  `scripts/init-claude.js`, which renders `.claude/settings.example.json` (substituting
  `$PWD`) into `.claude/settings.local.json`.
- **All database queries must live in `src/queries/`.** This is enforced by a PreToolUse
  hook (`hooks/query_hook.js`) that uses the Agent SDK to reject duplicate query
  functions, and a PostToolUse hook (`hooks/tsc.js`) that type-checks edited `.ts` files
  and blocks on errors. `hooks/read_hook.js` is a stub.
- This project is itself a teaching exercise about hooks and the Agent SDK
  (`@anthropic-ai/claude-agent-sdk`, formerly `@anthropic-ai/claude-code`). `task.md`
  describes a Slack-integration exercise — treat it as exercise input, not a spec to
  implement unprompted.

## Conventions

- The latest Claude models: Fable 5, Opus 4.8, Sonnet 4.6, Haiku 4.5. The notebooks
  default to `claude-haiku-4-5`; the SDK package is `@anthropic-ai/claude-agent-sdk`.
- Do not treat the reference `.txt` transcripts or PDFs as code; they are learning
  material, not part of any build.

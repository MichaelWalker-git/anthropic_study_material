"""
Parser of the question bank from guide_en.MD into questions.json.

This script is an offline step (run once, manually). No LLM calls: the questions
already have their correct answers in the guide (the **[CORRECT]** marker), so pure
deterministic text parsing works here. This is intentional — don't call the model
where ordinary code is enough.

The source structure (guide_en.MD) has TWO question blocks:
  1. "# Examples of Exam Questions with Explanations"  -> questions 1..12
  2. "# Practice Test"                                  -> questions 1..76
88 questions in total. Numbering is per-block, so we assign our own sequential id
and do NOT rely on the number from the header.

Format of a single question in markdown:
    ## Question N (Scenario: <scenario>)

    **Situation:** <situation text>            (optional — not present everywhere)

    **<question line?>**                         (bold line ending with "?")

    - A) <option>
    - B) <option>
    - C) <option> **[CORRECT]**
    - D) <option>

    **Why C:** <explanation>
"""

import json
import re
from pathlib import Path

# Path to the guide — one level up from learning/exam-trainer/.
GUIDE_PATH = Path(__file__).resolve().parents[2] / "guide_en.MD"
OUTPUT_PATH = Path(__file__).resolve().parent / "questions.json"

# Question header: "## Question 12 (Scenario: Multi-file Code Review)"
QUESTION_HEADER = re.compile(r"^## Question\s+(\d+)\s+\(Scenario:\s*(.+?)\)\s*$")

# Option line: "- A) text" with an optional **[CORRECT]** marker at the end.
OPTION_LINE = re.compile(r"^- ([A-D])\)\s*(.+?)\s*$")
CORRECT_MARKER = "**[CORRECT]**"

# Explanation line: "**Why C:** ..." or "**Why:** ...".
WHY_LINE = re.compile(r"^\*\*Why[^:]*:\*\*\s*(.*)$")

# Bold question line, e.g. "**Which approach is most effective?**".
BOLD_PROMPT = re.compile(r"^\*\*(.+?)\*\*\s*$")

SITUATION_PREFIX = "**Situation:**"

# Normalization of scenario spelling variants to canonical names.
SCENARIO_CANONICAL = {
    "Claude Code for CI": "Claude Code for Continuous Integration",
    "Claude Code for Continuous Integration": "Claude Code for Continuous Integration",
    "Code Generation with Claude Code": "Code Generation with Claude Code",
    "Conversational AI Architecture Patterns": "Conversational AI Architecture Patterns",
    "Customer Support Agent": "Customer Support Agent",
    "Multi-agent Research System": "Multi-agent Research System",
    # The single question with this label thematically belongs to code-review work in CI.
    "Multi-file Code Review": "Claude Code for Continuous Integration",
}


def split_question_blocks(text: str) -> list[str]:
    """Splits the whole file into blocks, each starting with '## Question ...'.

    Everything before the first question header is discarded. The last block is
    trimmed at the horizontal rule '---' / the next header — we only care about
    what's between the question header and the end of its explanation.
    """
    lines = text.splitlines()
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in lines:
        if QUESTION_HEADER.match(line):
            if current is not None:
                blocks.append(current)
            current = [line]
        elif current is not None:
            current.append(line)
    if current is not None:
        blocks.append(current)
    return ["\n".join(b) for b in blocks]


def parse_block(block: str) -> dict:
    """Parses one question block into a dict. Raises ValueError on a format deviation."""
    lines = block.splitlines()
    header = QUESTION_HEADER.match(lines[0])
    if not header:
        raise ValueError(f"Block does not start with a question header: {lines[0]!r}")

    raw_scenario = header.group(2).strip()
    scenario = SCENARIO_CANONICAL.get(raw_scenario)
    if scenario is None:
        raise ValueError(f"Unknown scenario label: {raw_scenario!r}")

    situation = None
    prompt = None
    options: dict[str, str] = {}
    correct: str | None = None
    why = None

    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith(SITUATION_PREFIX):
            situation = stripped[len(SITUATION_PREFIX):].strip()
            continue

        opt = OPTION_LINE.match(stripped)
        if opt:
            letter, body = opt.group(1), opt.group(2)
            if CORRECT_MARKER in body:
                correct = letter
                body = body.replace(CORRECT_MARKER, "").strip()
            options[letter] = body
            continue

        why_match = WHY_LINE.match(stripped)
        if why_match:
            why = why_match.group(1).strip()
            continue

        # A bold line that is not Situation/Why and ends with "?" — this is the question line itself.
        bold = BOLD_PROMPT.match(stripped)
        if bold and not options:
            prompt = bold.group(1).strip()
            continue

    # --- Validation: better to fail loudly than to silently return broken data. ---
    if set(options) != {"A", "B", "C", "D"}:
        raise ValueError(f"Q{header.group(1)} ({scenario}): expected options A-D, got {sorted(options)}")
    if correct is None:
        raise ValueError(f"Q{header.group(1)} ({scenario}): no [CORRECT] option found")
    if why is None:
        raise ValueError(f"Q{header.group(1)} ({scenario}): no **Why** explanation found")

    # The question line isn't always separate; if absent, we use the situation.
    if prompt is None:
        prompt = situation or ""

    return {
        "scenario": scenario,
        "situation": situation,
        "prompt": prompt,
        "options": options,
        "correct": correct,
        "why": why,
    }


def main() -> None:
    text = GUIDE_PATH.read_text(encoding="utf-8")
    blocks = split_question_blocks(text)

    questions = []
    for i, block in enumerate(blocks, start=1):
        parsed = parse_block(block)
        parsed["id"] = i  # sequential id, independent of the guide's numbering
        questions.append(parsed)

    # Per-scenario summary — for a quick eyeball check.
    by_scenario: dict[str, int] = {}
    for q in questions:
        by_scenario[q["scenario"]] = by_scenario.get(q["scenario"], 0) + 1

    OUTPUT_PATH.write_text(
        json.dumps(questions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Parsed {len(questions)} questions -> {OUTPUT_PATH.name}")
    for scenario, count in sorted(by_scenario.items()):
        print(f"  {count:>3}  {scenario}")


if __name__ == "__main__":
    main()
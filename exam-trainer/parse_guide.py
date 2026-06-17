"""
Парсер банку питань із guide_en.MD у questions.json.

Цей скрипт — offline-крок (запускається один раз вручну). Жодних LLM-викликів:
питання вже мають правильні відповіді в гайді (мітка **[CORRECT]**), тож тут
працює чистий детермінований парсинг тексту. Це навмисно — не варто кликати
модель там, де достатньо звичайного коду.

Структура джерела (guide_en.MD) має ДВА блоки питань:
  1. "# Examples of Exam Questions with Explanations"  -> питання 1..12
  2. "# Practice Test"                                  -> питання 1..76
Разом 88 питань. Нумерація в кожному блоці своя, тож ми присвоюємо власний
наскрізний id і НЕ покладаємось на номер із заголовка.

Формат одного питання в markdown:
    ## Question N (Scenario: <scenario>)

    **Situation:** <текст ситуації>            (опційно — є не всюди)

    **<питальний рядок?>**                       (жирний рядок, що закінчується "?")

    - A) <варіант>
    - B) <варіант>
    - C) <варіант> **[CORRECT]**
    - D) <варіант>

    **Why C:** <пояснення>
"""

import json
import re
from pathlib import Path

# Шлях до гайда — на рівень вище від learning/exam-trainer/.
GUIDE_PATH = Path(__file__).resolve().parents[2] / "guide_en.MD"
OUTPUT_PATH = Path(__file__).resolve().parent / "questions.json"

# Заголовок питання: "## Question 12 (Scenario: Multi-file Code Review)"
QUESTION_HEADER = re.compile(r"^## Question\s+(\d+)\s+\(Scenario:\s*(.+?)\)\s*$")

# Рядок варіанту: "- A) текст" з опційною міткою **[CORRECT]** у кінці.
OPTION_LINE = re.compile(r"^- ([A-D])\)\s*(.+?)\s*$")
CORRECT_MARKER = "**[CORRECT]**"

# Рядок пояснення: "**Why C:** ..." або "**Why:** ...".
WHY_LINE = re.compile(r"^\*\*Why[^:]*:\*\*\s*(.*)$")

# Жирний рядок-питання, напр. "**Which approach is most effective?**".
BOLD_PROMPT = re.compile(r"^\*\*(.+?)\*\*\s*$")

SITUATION_PREFIX = "**Situation:**"

# Нормалізація варіантів написання сценаріїв до канонічних назв.
SCENARIO_CANONICAL = {
    "Claude Code for CI": "Claude Code for Continuous Integration",
    "Claude Code for Continuous Integration": "Claude Code for Continuous Integration",
    "Code Generation with Claude Code": "Code Generation with Claude Code",
    "Conversational AI Architecture Patterns": "Conversational AI Architecture Patterns",
    "Customer Support Agent": "Customer Support Agent",
    "Multi-agent Research System": "Multi-agent Research System",
    # Єдине питання з цим лейблом тематично належить до code-review робіт у CI.
    "Multi-file Code Review": "Claude Code for Continuous Integration",
}


def split_question_blocks(text: str) -> list[str]:
    """Розбиває весь файл на блоки, кожен починається з '## Question ...'.

    Усе до першого заголовка питання відкидається. Останній блок обрізається
    по горизонтальній лінії '---' / наступному заголовку — нам важливо тільки
    те, що між заголовком питання і кінцем його пояснення.
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
    """Парсить один блок питання у словник. Кидає ValueError при відхиленні формату."""
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

        # Жирний рядок, що не Situation/Why і закінчується "?" — це сам питальний рядок.
        bold = BOLD_PROMPT.match(stripped)
        if bold and not options:
            prompt = bold.group(1).strip()
            continue

    # --- Валідація: краще впасти голосно, ніж тихо віддати биті дані. ---
    if set(options) != {"A", "B", "C", "D"}:
        raise ValueError(f"Q{header.group(1)} ({scenario}): expected options A-D, got {sorted(options)}")
    if correct is None:
        raise ValueError(f"Q{header.group(1)} ({scenario}): no [CORRECT] option found")
    if why is None:
        raise ValueError(f"Q{header.group(1)} ({scenario}): no **Why** explanation found")

    # Питальний рядок не завжди є окремо; якщо нема — використовуємо ситуацію.
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
        parsed["id"] = i  # наскрізний id, незалежний від нумерації в гайді
        questions.append(parsed)

    # Підсумок по сценаріях — для швидкої перевірки очима.
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
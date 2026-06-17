"""
Генератор НОВИХ екзаменаційних питань — єдине місце в проєкті, де працює LLM.

Чому саме тут (і ніде більше): 88 питань банку — скінченні, їх можна просто
завчити. Згенерувати свіже питання в тому ж стилі — це те, чого детермінований
код зробити не може. Це справжня RAG-задача: модель читає релевантний шматок
гайда і видає структурований MCQ.

Патерн "generate -> validate" (той самий, що в Capital Group pipeline):
  1. Sonnet через Bedrock з ПРИМУСОВИМ tool_use — модель мусить повернути JSON
     за схемою (stem, 4 варіанти, індекс правильного, пояснення).
  2. Детермінована перевірка в коді: рівно 4 варіанти, рівно одна правильна,
     відповідь не "протікає" в тексті питання, сценарій валідний.
  3. Якщо перевірка не пройшла — один ретрай зі скаргою. Це не другий LLM-суддя:
     структурні дефекти ловлять прості if-и, а не ще одна модель.

Запуск окремо (для дебагу):
    uv run python generator.py "Multi-agent Research System"
"""

import json
import os
import sys
from pathlib import Path

from anthropic import AnthropicBedrock
from dotenv import load_dotenv

# .env лежить на рівень вище (learning/.env) — спільний для всіх уроків.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

QUESTIONS_PATH = BASE_DIR / "questions.json"

# Sonnet — бо якість питання (рівно одна захищувано-правильна відповідь,
# правдоподібні дистрактори) важливіша за ціну, а це кнопка on-demand.
MODEL = "us.anthropic.claude-sonnet-4-6"

# Сценарії та приклади-контекст беремо з ЗІБРАНОГО банку (questions.json), а не
# з гайда: банк зливає кілька джерел, тож у ньому є всі сценарії (зокрема ті,
# яких у guide_en.MD немає). Це усуває розсинхрон назв сценаріїв.
_BANK_CACHE: list[dict] | None = None


def _bank() -> list[dict]:
    global _BANK_CACHE
    if _BANK_CACHE is None:
        _BANK_CACHE = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    return _BANK_CACHE


def valid_scenarios() -> set[str]:
    return {q["scenario"] for q in _bank()}

# JSON-схема інструмента: модель ЗОБОВ'ЯЗАНА повернути саме таку структуру.
QUESTION_TOOL = {
    "name": "emit_question",
    "description": "Return exactly one multiple-choice exam question in the required structure.",
    "input_schema": {
        "type": "object",
        "properties": {
            "situation": {
                "type": "string",
                "description": "A realistic 1-3 sentence scenario setting up the problem.",
            },
            "prompt": {
                "type": "string",
                "description": "The actual question, ending with a question mark.",
            },
            "options": {
                "type": "array",
                "description": "Exactly 4 answer options, plausible but only one correct.",
                "items": {"type": "string"},
                "minItems": 4,
                "maxItems": 4,
            },
            "correct_index": {
                "type": "integer",
                "description": "0-based index of the single correct option.",
                "minimum": 0,
                "maximum": 3,
            },
            "why": {
                "type": "string",
                "description": "Explanation of why the correct option is right.",
            },
        },
        "required": ["situation", "prompt", "options", "correct_index", "why"],
    },
}

def _bank_excerpt(scenario: str, max_examples: int = 4) -> str:
    """Формує приклади-контекст для RAG з реальних питань цього сценарію в банку.

    Беремо кілька існуючих питань як зразок стилю/складності, щоб модель
    відтворила формат. Приклади йдуть із зібраного banku, тож працюють для
    БУДЬ-ЯКОГО сценарію, наявного в questions.json.
    """
    examples = [q for q in _bank() if q["scenario"] == scenario][:max_examples]
    blocks = []
    for q in examples:
        opts = "\n".join(f"  {letter}) {text}" for letter, text in q["options"].items())
        blocks.append(
            f"Situation: {q.get('situation') or ''}\n"
            f"Question: {q['prompt']}\n{opts}\n"
            f"Correct: {q['correct']}"
        )
    return "\n\n".join(blocks)


def _build_prompt(scenario: str, excerpt: str, complaint: str | None) -> str:
    base = (
        f"You are writing a NEW practice question for the Claude Certified Architect "
        f"— Foundations exam, scenario: \"{scenario}\".\n\n"
        f"Below are real example questions from this scenario. Match their style, "
        f"difficulty, and the kind of trade-off reasoning they test. Do NOT copy them — "
        f"invent a fresh situation.\n\n"
        f"Rules:\n"
        f"- Exactly four options; exactly ONE must be defensibly correct.\n"
        f"- Distractors must be plausible but clearly wrong on reflection.\n"
        f"- Do NOT reveal the answer in the prompt or option wording.\n"
        f"- Return the question via the emit_question tool.\n\n"
        f"=== EXAMPLE QUESTIONS (style reference) ===\n{excerpt}\n=== END EXAMPLES ==="
    )
    if complaint:
        base += f"\n\nYour previous attempt was rejected: {complaint}\nFix it and try again."
    return base


def _validate(q: dict) -> str | None:
    """Детермінована перевірка. Повертає текст скарги або None, якщо все гаразд."""
    opts = q.get("options", [])
    if len(opts) != 4:
        return f"expected 4 options, got {len(opts)}"
    if len({o.strip().lower() for o in opts}) != 4:
        return "options must be distinct"
    idx = q.get("correct_index")
    if not isinstance(idx, int) or not 0 <= idx <= 3:
        return "correct_index must be 0-3"
    if not q.get("prompt", "").strip().endswith("?"):
        return "prompt must end with a question mark"
    # Перевірка на "протікання" відповіді: текст правильного варіанту не має
    # дослівно зустрічатись у питанні.
    correct_text = opts[idx].strip().lower()
    if correct_text and correct_text in q.get("prompt", "").lower():
        return "the correct answer text appears in the prompt (leak)"
    return None


def generate_question(scenario: str, max_retries: int = 1) -> dict:
    """Генерує одне валідоване питання. Кидає RuntimeError, якщо не вдалось."""
    if scenario not in valid_scenarios():
        raise ValueError(f"Unknown scenario: {scenario}")

    client = AnthropicBedrock()
    excerpt = _bank_excerpt(scenario)
    complaint: str | None = None

    for attempt in range(max_retries + 1):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=[QUESTION_TOOL],
            tool_choice={"type": "tool", "name": "emit_question"},
            messages=[{"role": "user", "content": _build_prompt(scenario, excerpt, complaint)}],
        )
        tool_use = next((b for b in resp.content if b.type == "tool_use"), None)
        if tool_use is None:
            complaint = "no tool call returned"
            continue

        q = tool_use.input
        complaint = _validate(q)
        if complaint is None:
            # Приводимо до того ж формату, що й банк (літери A-D).
            letters = ["A", "B", "C", "D"]
            return {
                "scenario": scenario,
                "situation": q["situation"],
                "prompt": q["prompt"],
                "options": dict(zip(letters, q["options"])),
                "correct": letters[q["correct_index"]],
                "why": q["why"],
                "generated": True,
            }

    raise RuntimeError(f"Generation failed validation after {max_retries + 1} tries: {complaint}")


if __name__ == "__main__":
    scenario = sys.argv[1] if len(sys.argv) > 1 else "Multi-agent Research System"
    if not os.getenv("AWS_BEARER_TOKEN_BEDROCK") and not os.getenv("AWS_ACCESS_KEY_ID"):
        sys.exit("Set AWS_BEARER_TOKEN_BEDROCK (or AWS creds) — see learning/.env")
    result = generate_question(scenario)
    print(json.dumps(result, ensure_ascii=False, indent=2))

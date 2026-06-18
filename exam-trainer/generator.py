"""
Generator of NEW exam questions — the only place in the project where the LLM runs.

Why here (and nowhere else): the 88 bank questions are finite, you can just
memorize them. Generating a fresh question in the same style is something that
deterministic code cannot do. This is a genuine RAG task: the model reads a
relevant chunk of the guide and emits a structured MCQ.

The "generate -> validate" pattern (the same one as in the Capital Group pipeline):
  1. Sonnet via Bedrock with FORCED tool_use — the model must return JSON
     matching the schema (stem, 4 options, index of the correct one, explanation).
  2. Deterministic validation in code: exactly 4 options, exactly one correct,
     the answer does not "leak" into the question text, the scenario is valid.
  3. If validation fails — one retry with a complaint. This is not a second LLM
     judge: structural defects are caught by simple ifs, not another model.

Run standalone (for debugging):
    uv run python generator.py "Multi-agent Research System"
"""

import json
import os
import sys
from pathlib import Path

from anthropic import AnthropicBedrock
from dotenv import load_dotenv

# .env sits one level up (learning/.env) — shared across all lessons.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

QUESTIONS_PATH = BASE_DIR / "questions.json"

# Sonnet — because question quality (exactly one defensibly correct answer,
# plausible distractors) matters more than cost, and this is an on-demand button.
MODEL = "us.anthropic.claude-sonnet-4-6"

# We take scenarios and example context from the ASSEMBLED bank (questions.json),
# not from the guide: the bank merges several sources, so it has all scenarios
# (including ones absent from guide_en.MD). This eliminates scenario-name drift.
_BANK_CACHE: list[dict] | None = None


def _bank() -> list[dict]:
    global _BANK_CACHE
    if _BANK_CACHE is None:
        _BANK_CACHE = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    return _BANK_CACHE


def valid_scenarios() -> set[str]:
    return {q["scenario"] for q in _bank()}

# Tool's JSON schema: the model is REQUIRED to return exactly this structure.
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
    """Builds RAG example context from real questions of this scenario in the bank.

    We take a few existing questions as a sample of style/difficulty so the model
    reproduces the format. The examples come from the assembled bank, so they work
    for ANY scenario present in questions.json.
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
    """Deterministic validation. Returns a complaint string, or None if all is fine."""
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
    # Answer "leak" check: the correct option's text must not appear verbatim
    # in the question.
    correct_text = opts[idx].strip().lower()
    if correct_text and correct_text in q.get("prompt", "").lower():
        return "the correct answer text appears in the prompt (leak)"
    return None


def generate_question(scenario: str, max_retries: int = 1) -> dict:
    """Generates one validated question. Raises RuntimeError if it fails."""
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
            # Convert to the same format as the bank (letters A-D).
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

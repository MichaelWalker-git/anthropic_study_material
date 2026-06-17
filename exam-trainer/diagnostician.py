"""
Агент-діагност — ДРУГИЙ LLM у проєкті (поряд із generator.py).

Навіщо окремий агент, а не функція в generator.py: це навмисний приклад
multi-agent патерну зі structured handoff (той самий, що в Capital Group):
  * діагност (цей файл) — аналізує твої помилки й пише висновок;
  * генератор (generator.py) — створює питання на знайдену слабину.
Кожен агент має ОДНУ відповідальність і власний scoped контекст. Handoff —
структурований: діагност повертає поле recommended_scenario, яке фронтенд
передає генератору.

Чому це справді задача для LLM (а не код): код може порахувати, ЯКІ питання ти
провалила (точність по сценаріях — це вже робить /api/stats). Але сказати, ЧОМУ
ти помиляєшся — який концепт ти системно плутаєш, який патерн хибного міркування
повторюється — це семантичний аналіз тексту твоїх відповідей. Оце і є LLM-робота.
"""

import json
import os
import sys
from pathlib import Path

from anthropic import AnthropicBedrock
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

# Sonnet — діагноз вимагає тонкого розуміння концептів, не дешева класифікація.
MODEL = "us.anthropic.claude-sonnet-4-6"

# Структурований вихід: змушуємо модель повернути саме висновок + рекомендацію,
# щоб handoff до генератора був надійним (recommended_scenario — машиночитане).
DIAGNOSIS_TOOL = {
    "name": "emit_diagnosis",
    "description": "Return a study diagnosis based on the learner's wrong answers.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "2-4 sentences: what conceptual patterns the learner is getting wrong. Write in Ukrainian; keep technical terms in English.",
            },
            "misconceptions": {
                "type": "array",
                "description": "Specific recurring misconceptions, each one short sentence (Ukrainian).",
                "items": {"type": "string"},
            },
            "recommended_scenario": {
                "type": "string",
                "description": "The single scenario name (verbatim from the provided list) the learner should drill next.",
            },
            "recommendation": {
                "type": "string",
                "description": "1-2 sentences (Ukrainian): why that scenario, what to focus on.",
            },
        },
        "required": ["summary", "misconceptions", "recommended_scenario", "recommendation"],
    },
}


def _build_prompt(wrong: list[dict], scenarios: list[str]) -> str:
    """Складає контекст: тексти провалених питань + правильні/обрані відповіді."""
    blocks = []
    for w in wrong:
        opts = "\n".join(f"  {l}) {t}" for l, t in w["options"].items())
        blocks.append(
            f"Scenario: {w['scenario']}\n"
            f"Situation: {w.get('situation') or ''}\n"
            f"Question: {w['prompt']}\n{opts}\n"
            f"Learner chose: {w['chosen']} ({w['options'].get(w['chosen'], '?')})\n"
            f"Correct answer: {w['correct']} ({w['options'].get(w['correct'], '?')})\n"
            f"Why correct: {w.get('why') or ''}"
        )
    joined = "\n\n---\n\n".join(blocks)
    return (
        "You are a study coach for the Claude Certified Architect — Foundations exam. "
        "Below are the questions a learner answered INCORRECTLY in one session, with "
        "their chosen answer and the correct one. Analyse the PATTERN of mistakes — not "
        "each question in isolation. Identify which concepts they systematically confuse "
        "(e.g. 'confuses plan mode with direct execution', 'under-uses escalation'). "
        "Then recommend ONE scenario to drill next.\n\n"
        f"Available scenarios (use one verbatim for recommended_scenario): {scenarios}\n\n"
        f"=== WRONG ANSWERS ===\n{joined}\n=== END ===\n\n"
        "Return your analysis via the emit_diagnosis tool. Write summary/recommendation "
        "in Ukrainian; keep technical terms (plan mode, tool_use, MCP, etc.) in English."
    )


def diagnose(wrong: list[dict], scenarios: list[str]) -> dict:
    """Аналізує провалені питання й повертає висновок + рекомендований сценарій.

    wrong: список словників {scenario, situation, prompt, options, chosen, correct, why}.
    """
    if not wrong:
        return {
            "summary": "У цій сесії немає помилок — діагностувати нічого. 🎉",
            "misconceptions": [],
            "recommended_scenario": None,
            "recommendation": "",
        }

    client = AnthropicBedrock()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[DIAGNOSIS_TOOL],
        tool_choice={"type": "tool", "name": "emit_diagnosis"},
        messages=[{"role": "user", "content": _build_prompt(wrong, scenarios)}],
    )
    tool_use = next((b for b in resp.content if b.type == "tool_use"), None)
    if tool_use is None:
        raise RuntimeError("Diagnostician returned no structured output")

    result = dict(tool_use.input)
    # Захист handoff: рекомендований сценарій має бути з відомого списку.
    if result.get("recommended_scenario") not in scenarios:
        # Фолбек — сценарій, де найбільше помилок у цій сесії.
        from collections import Counter
        result["recommended_scenario"] = Counter(w["scenario"] for w in wrong).most_common(1)[0][0]
    return result


if __name__ == "__main__":
    if not os.getenv("AWS_BEARER_TOKEN_BEDROCK") and not os.getenv("AWS_ACCESS_KEY_ID"):
        sys.exit("Set AWS_BEARER_TOKEN_BEDROCK (or AWS creds) — see learning/.env")
    # Демо на синтетичному прикладі.
    demo = [{
        "scenario": "Code Generation with Claude Code",
        "situation": "You need to restructure a monolith into microservices.",
        "prompt": "Which approach should you take?",
        "options": {"A": "Start direct execution", "B": "Enter plan mode first",
                    "C": "Incremental edits", "D": "Comprehensive upfront prompt"},
        "chosen": "A", "correct": "B",
        "why": "Plan mode lets you explore dependencies before changing code.",
    }]
    print(json.dumps(diagnose(demo, ["Code Generation with Claude Code"]),
                     ensure_ascii=False, indent=2))

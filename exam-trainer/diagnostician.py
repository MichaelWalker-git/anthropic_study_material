"""
Diagnostician agent — the SECOND LLM in the project (alongside generator.py).

Why a separate agent rather than a function in generator.py: this is a deliberate
example of a multi-agent pattern with a structured handoff (the same as in Capital
Group):
  * the diagnostician (this file) — analyzes your mistakes and writes a conclusion;
  * the generator (generator.py) — creates a question on the identified weakness.
Each agent has ONE responsibility and its own scoped context. The handoff is
structured: the diagnostician returns a recommended_scenario field, which the
frontend passes to the generator.

Why this is genuinely an LLM task (and not code): code can count WHICH questions
you failed (per-scenario accuracy — that's already done by /api/stats). But to say
WHY you're getting it wrong — which concept you systematically confuse, which
faulty-reasoning pattern recurs — is semantic analysis of the text of your answers.
That is the LLM's job.
"""

import json
import os
import sys
from pathlib import Path

from anthropic import AnthropicBedrock
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")

# Sonnet — diagnosis requires a nuanced understanding of concepts, not cheap classification.
MODEL = "us.anthropic.claude-sonnet-4-6"

# Structured output: we force the model to return exactly a conclusion + recommendation,
# so the handoff to the generator is reliable (recommended_scenario is machine-readable).
DIAGNOSIS_TOOL = {
    "name": "emit_diagnosis",
    "description": "Return a study diagnosis based on the learner's wrong answers.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "2-4 sentences: what conceptual patterns the learner is getting wrong. Write in English.",
            },
            "misconceptions": {
                "type": "array",
                "description": "Specific recurring misconceptions, each one short sentence (English).",
                "items": {"type": "string"},
            },
            "recommended_scenario": {
                "type": "string",
                "description": "The single scenario name (verbatim from the provided list) the learner should drill next.",
            },
            "recommendation": {
                "type": "string",
                "description": "1-2 sentences (English): why that scenario, what to focus on.",
            },
        },
        "required": ["summary", "misconceptions", "recommended_scenario", "recommendation"],
    },
}


def _build_prompt(wrong: list[dict], scenarios: list[str]) -> str:
    """Assembles the context: text of failed questions + correct/chosen answers."""
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
        "Return your analysis via the emit_diagnosis tool. Write the summary and "
        "recommendation in English; keep technical terms (plan mode, tool_use, MCP, etc.) as-is."
    )


def diagnose(wrong: list[dict], scenarios: list[str]) -> dict:
    """Analyzes failed questions and returns a conclusion + recommended scenario.

    wrong: list of dicts {scenario, situation, prompt, options, chosen, correct, why}.
    """
    if not wrong:
        return {
            "summary": "No mistakes in this session — nothing to diagnose. 🎉",
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
    # Handoff guard: the recommended scenario must come from the known list.
    if result.get("recommended_scenario") not in scenarios:
        # Fallback — the scenario with the most mistakes in this session.
        from collections import Counter
        result["recommended_scenario"] = Counter(w["scenario"] for w in wrong).most_common(1)[0][0]
    return result


if __name__ == "__main__":
    if not os.getenv("AWS_BEARER_TOKEN_BEDROCK") and not os.getenv("AWS_ACCESS_KEY_ID"):
        sys.exit("Set AWS_BEARER_TOKEN_BEDROCK (or AWS creds) — see learning/.env")
    # Demo on a synthetic example.
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

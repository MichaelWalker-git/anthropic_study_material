"""
Assembles a single question bank from TWO sources into questions.json:

  1. guide_en.MD          -> 88 questions (via parse_guide.py)
  2. mock-exam/public/bank -> 376 questions (a shared TS project)

The sources barely overlap (only ~7 in common), so we merge both. The "source"
field lets us tell the origin apart. We remove duplicates by text similarity
(normalized stem), keeping the richer variant (mock-exam has an explanation for
EVERY option, not just the correct one).

Run:
    uv run python build_bank.py
"""

import json
import re
from difflib import SequenceMatcher
from pathlib import Path

import parse_guide  # reuse the existing guide parser

BASE_DIR = Path(__file__).resolve().parent
MOCK_BANK_DIR = (
    BASE_DIR.parent.parent.parent
    / "anthropic_study_material" / "mock-exam" / "public" / "bank"
)
OUTPUT_PATH = BASE_DIR / "questions.json"

# mock-exam S-codes -> canonical scenario names (aligned with ours).
SCENARIO_NAMES = {
    "S1": "Customer Support Resolution Agent",
    "S2": "Code Generation with Claude Code",
    "S3": "Multi-Agent Research System",
    "S4": "Developer Productivity with Claude",
    "S5": "Claude Code for Continuous Integration",
    "S6": "Structured Data Extraction",
}


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return " ".join(s.split())


def _similar(a: str, b: str) -> float:
    wa, wb = set(_norm(a).split()), set(_norm(b).split())
    jac = len(wa & wb) / len(wa | wb) if (wa | wb) else 0
    seq = SequenceMatcher(None, _norm(a), _norm(b)).ratio()
    return 0.5 * jac + 0.5 * seq


# Scenario names in the guide differ in case/wording from mock-exam —
# we normalize them to canonical names so identical scenarios group together.
GUIDE_SCENARIO_ALIASES = {
    "Customer Support Agent": "Customer Support Resolution Agent",
    "Multi-agent Research System": "Multi-Agent Research System",
}


def load_guide_questions() -> list[dict]:
    """88 questions from the guide, in our format (via the existing parser)."""
    text = parse_guide.GUIDE_PATH.read_text(encoding="utf-8")
    out = []
    for block in parse_guide.split_question_blocks(text):
        q = parse_guide.parse_block(block)
        q["scenario"] = GUIDE_SCENARIO_ALIASES.get(q["scenario"], q["scenario"])
        q["source"] = "guide"
        out.append(q)
    return out


def load_mock_questions() -> list[dict]:
    """376 questions from mock-exam, converted to our format.

    Their variant is a list of {id,text,correct,explanation}; ours is a dict A-D +
    correct letter + why. We keep the explanation for each option in the
    "explanations" field (optional, richer than our guide format).
    """
    out = []
    for path in sorted(MOCK_BANK_DIR.glob("S*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else data.get("questions", data)
        for item in items:
            opts = item["options"]
            letters = [o["id"] for o in opts]            # usually A-D
            options = {o["id"]: o["text"] for o in opts}
            explanations = {o["id"]: o.get("explanation", "") for o in opts}
            correct = next(o["id"] for o in opts if o.get("correct"))
            out.append({
                "scenario": SCENARIO_NAMES.get(item["scenario"], item["scenario"]),
                "situation": None,                       # stem already contains the situation
                "prompt": item["stem"],
                "options": options,
                "correct": correct,
                "why": explanations.get(correct, ""),
                "explanations": explanations,            # explanations for all options
                "domain": item.get("domain"),
                "source": "mock-exam",
            })
    return out


def merge(primary: list[dict], secondary: list[dict], threshold: float = 0.6) -> list[dict]:
    """Merges two lists, dropping from secondary any duplicates already in primary.

    primary is the richer mock-exam (we keep it entirely); from guide we add only
    what isn't already present (this preserves per-option explanations where possible).
    """
    merged = list(primary)
    prim_texts = [(p.get("situation") or "") + " " + p["prompt"] for p in primary]
    added = 0
    for q in secondary:
        qt = (q.get("situation") or "") + " " + q["prompt"]
        if max((_similar(qt, pt) for pt in prim_texts), default=0) < threshold:
            merged.append(q)
            added += 1
    return merged, added


def main() -> None:
    mock = load_mock_questions()
    guide = load_guide_questions()
    merged, added = merge(mock, guide)

    for i, q in enumerate(merged, start=1):
        q["id"] = i

    OUTPUT_PATH.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    from collections import Counter
    by_scenario = Counter(q["scenario"] for q in merged)
    by_source = Counter(q["source"] for q in merged)
    print(f"Built bank: {len(merged)} questions -> {OUTPUT_PATH.name}")
    print(f"  mock-exam: {len(mock)} | guide loaded: {len(guide)} | guide added (deduped): {added}")
    print("  by source:", dict(by_source))
    for s, c in sorted(by_scenario.items()):
        print(f"    {c:>3}  {s}")


if __name__ == "__main__":
    main()

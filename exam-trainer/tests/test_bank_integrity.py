"""
Question bank integrity (questions.json).

This is the most fundamental level: if the data is broken, no feature above it
makes sense. We check INVARIANTS that must hold for EVERY one of the ~457 questions.
"""

import pytest


def test_bank_not_empty(app_module):
    assert len(app_module.QUESTIONS) > 0


def test_ids_are_unique(app_module):
    ids = [q["id"] for q in app_module.QUESTIONS]
    assert len(ids) == len(set(ids)), "question ids must be unique"


def test_by_id_index_matches_list(app_module):
    assert len(app_module.QUESTIONS_BY_ID) == len(app_module.QUESTIONS)


@pytest.mark.parametrize("field", ["id", "scenario", "prompt", "options", "correct", "why"])
def test_required_fields_present(app_module, field):
    missing = [q.get("id") for q in app_module.QUESTIONS if field not in q]
    assert not missing, f"field '{field}' missing in questions: {missing[:10]}"


def test_exactly_four_distinct_options(app_module):
    for q in app_module.QUESTIONS:
        opts = q["options"]
        assert set(opts) == {"A", "B", "C", "D"}, f"q{q['id']}: options != A-D"
        texts = [t.strip().lower() for t in opts.values()]
        assert len(set(texts)) == 4, f"q{q['id']}: options are not unique"


def test_correct_letter_is_valid(app_module):
    for q in app_module.QUESTIONS:
        assert q["correct"] in {"A", "B", "C", "D"}, f"q{q['id']}: bad correct letter"
        assert q["correct"] in q["options"], f"q{q['id']}: correct letter not in options"


def test_why_is_nonempty(app_module):
    for q in app_module.QUESTIONS:
        assert q["why"] is not None and q["why"].strip(), f"q{q['id']}: empty explanation"


def test_mock_exam_questions_have_per_option_explanations(app_module):
    """mock-exam questions have explanations for every option (for chosen_why)."""
    for q in app_module.QUESTIONS:
        if q.get("source") != "mock-exam":
            continue
        expl = q.get("explanations")
        assert expl and set(expl) == {"A", "B", "C", "D"}, \
            f"q{q['id']}: mock-exam must have explanations for all 4 options"


def test_scenarios_are_canonical(app_module):
    """Scenario names must not duplicate via case/spelling variants."""
    scenarios = {q["scenario"] for q in app_module.QUESTIONS}
    lowered = {s.lower() for s in scenarios}
    assert len(scenarios) == len(lowered), \
        f"scenarios that differ only by case: {sorted(scenarios)}"


def test_answer_not_trivially_leaked_in_prompt(app_module):
    """The correct answer text must not appear verbatim in the prompt (gross leak)."""
    leaks = []
    for q in app_module.QUESTIONS:
        correct_text = q["options"][q["correct"]].strip().lower()
        if correct_text and len(correct_text) > 25 and correct_text in q["prompt"].lower():
            leaks.append(q["id"])
    assert not leaks, f"correct answer appears verbatim in the prompt: {leaks}"

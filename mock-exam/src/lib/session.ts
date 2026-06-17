import type {
  Blueprint,
  Question,
  Session,
  SessionQuestion,
} from "../types";

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function toSessionQuestion(q: Question): SessionQuestion {
  const correct = q.options.find((o) => o.correct);
  return {
    question: q,
    options: shuffle(q.options),
    correctOptionId: correct ? correct.id : q.options[0].id,
  };
}

/**
 * Assemble a sitting that mirrors the real exam: pick `scenarios_per_session`
 * scenarios at random, then present `questions_per_scenario` questions from each,
 * grouped contiguously by scenario (S1 block, then S2 block, ...).
 */
export function assembleSession(
  blueprint: Blueprint,
  pool: Question[],
): Session {
  const { session } = blueprint;
  const warnings: string[] = [];
  const perScenario = session.questions_per_scenario;

  const chosenScenarioIds = shuffle(blueprint.scenarios.map((s) => s.id)).slice(
    0,
    session.scenarios_per_session,
  );

  const questions: SessionQuestion[] = [];

  for (const scenarioId of chosenScenarioIds) {
    const available = shuffle(pool.filter((q) => q.scenario === scenarioId));
    const taken = available.slice(0, perScenario);
    taken.forEach((q) => questions.push(toSessionQuestion(q)));

    const scenarioName =
      blueprint.scenarios.find((s) => s.id === scenarioId)?.name ?? scenarioId;
    if (taken.length < perScenario) {
      warnings.push(
        `${scenarioId} (${scenarioName}): wanted ${perScenario}, only ${taken.length} available in the pool.`,
      );
    }
  }

  if (questions.length < session.total_questions) {
    warnings.push(
      `Pool is short: assembled ${questions.length} of ${session.total_questions} questions. Generate more to fill a full sitting.`,
    );
  }

  return { questions, scenarioIds: chosenScenarioIds, warnings };
}

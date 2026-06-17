import type {
  Blueprint,
  DomainStat,
  MissedQuestion,
  Result,
  ScenarioStat,
  Session,
} from "../types";

/** answers: sessionQuestion index -> chosen option id (null = unanswered) */
export function scoreSession(
  blueprint: Blueprint,
  session: Session,
  answers: Record<number, string | null>,
): Result {
  const { session: cfg } = blueprint;
  const total = session.questions.length;

  const domainMap = new Map<string, DomainStat>();
  for (const d of blueprint.domains) {
    domainMap.set(d.id, {
      domainId: d.id,
      name: d.name,
      weight: d.weight,
      correct: 0,
      seen: 0,
    });
  }

  const scenarioMap = new Map<string, ScenarioStat>();
  for (const s of blueprint.scenarios) {
    scenarioMap.set(s.id, {
      scenarioId: s.id,
      name: s.name,
      correct: 0,
      seen: 0,
    });
  }

  const missed: MissedQuestion[] = [];
  let correct = 0;

  session.questions.forEach((sq, idx) => {
    const chosen = answers[idx] ?? null;
    const isCorrect = chosen !== null && chosen === sq.correctOptionId;

    const ds = domainMap.get(sq.question.domain);
    if (ds) {
      ds.seen++;
      if (isCorrect) ds.correct++;
    }
    const ss = scenarioMap.get(sq.question.scenario);
    if (ss) {
      ss.seen++;
      if (isCorrect) ss.correct++;
    }

    if (isCorrect) {
      correct++;
    } else {
      missed.push({
        question: sq.question,
        options: sq.options,
        chosenOptionId: chosen,
        correctOptionId: sq.correctOptionId,
      });
    }
  });

  const rawPct = total > 0 ? correct / total : 0;
  const span = cfg.scaled_max - cfg.scaled_min;
  const scaled = Math.round(cfg.scaled_min + rawPct * span);
  const passed = scaled >= cfg.pass_scaled;

  return {
    total,
    correct,
    rawPct,
    scaled,
    passed,
    passScaled: cfg.pass_scaled,
    domainStats: blueprint.domains
      .map((d) => domainMap.get(d.id)!)
      .filter((s) => s.seen > 0),
    scenarioStats: [...scenarioMap.values()].filter((s) => s.seen > 0),
    missed,
  };
}

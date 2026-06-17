import type { Blueprint, Question, QuestionBank } from "../types";

export async function loadData(): Promise<{
  blueprint: Blueprint;
  bank: QuestionBank;
}> {
  const blueprintRes = await fetch("/blueprint.json");
  if (!blueprintRes.ok) throw new Error("Failed to load blueprint.json");
  const blueprint = (await blueprintRes.json()) as Blueprint;

  const perScenario = await Promise.all(
    blueprint.scenarios.map(async (s) => {
      try {
        const res = await fetch(`/bank/${s.id}.json`);
        if (!res.ok) {
          console.warn(`No question file for scenario ${s.id} (/bank/${s.id}.json)`);
          return [] as Question[];
        }
        const data = (await res.json()) as QuestionBank;
        return data.questions ?? [];
      } catch (e) {
        console.warn(`Failed to load /bank/${s.id}.json:`, e);
        return [] as Question[];
      }
    }),
  );

  return { blueprint, bank: { questions: perScenario.flat() } };
}

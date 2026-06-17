export interface Domain {
  id: string;
  name: string;
  weight: number;
}

export interface Scenario {
  id: string;
  name: string;
  description: string;
  primary_domains: string[];
}

export interface SessionConfig {
  total_questions: number;
  scenarios_per_session: number;
  questions_per_scenario: number;
  default_minutes: number;
  pass_scaled: number;
  scaled_min: number;
  scaled_max: number;
}

export interface Blueprint {
  domains: Domain[];
  scenarios: Scenario[];
  session: SessionConfig;
}

export interface Option {
  id: string;
  text: string;
  correct: boolean;
  explanation: string;
}

export interface Question {
  id: string;
  scenario: string;
  domain: string;
  task_statement: string;
  stem: string;
  options: Option[];
}

export interface QuestionBank {
  questions: Question[];
}

/** A question prepared for a sitting: options are shuffled, correct id recorded. */
export interface SessionQuestion {
  question: Question;
  options: Option[];
  correctOptionId: string;
}

export interface Session {
  questions: SessionQuestion[];
  scenarioIds: string[];
  warnings: string[];
}

export interface DomainStat {
  domainId: string;
  name: string;
  weight: number;
  correct: number;
  seen: number;
}

export interface ScenarioStat {
  scenarioId: string;
  name: string;
  correct: number;
  seen: number;
}

export interface MissedQuestion {
  question: Question;
  options: Option[];
  chosenOptionId: string | null;
  correctOptionId: string;
}

export interface Result {
  total: number;
  correct: number;
  rawPct: number;
  scaled: number;
  passed: boolean;
  passScaled: number;
  domainStats: DomainStat[];
  scenarioStats: ScenarioStat[];
  missed: MissedQuestion[];
}

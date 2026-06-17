import { useEffect, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { loadData } from "../lib/loadData";
import { useExam } from "../state/examStore";
import type { Blueprint, Question } from "../types";

export function Start() {
  const navigate = useNavigate();
  const { startExam } = useExam();
  const [blueprint, setBlueprint] = useState<Blueprint | null>(null);
  const [pool, setPool] = useState<Question[]>([]);
  const [minutes, setMinutes] = useState(90);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData()
      .then(({ blueprint, bank }) => {
        setBlueprint(blueprint);
        setMinutes(blueprint.session.default_minutes);
        setPool(bank.questions);
      })
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <div className="screen">Failed to load data: {error}</div>;
  if (!blueprint) return <div className="loading">Loading…</div>;

  const byScenario = blueprint.scenarios.map((s) => ({
    s,
    count: pool.filter((q) => q.scenario === s.id).length,
  }));
  const byDomain = blueprint.domains.map((d) => ({
    d,
    count: pool.filter((q) => q.domain === d.id).length,
  }));
  const short = pool.length < blueprint.session.total_questions;

  const begin = () => {
    startExam(blueprint, pool, minutes);
    navigate({ to: "/exam" });
  };

  return (
    <div className="screen">
      <div className="panel">
        <h2>Claude Certified Architect — Foundations</h2>
        <p style={{ color: "var(--ink-soft)" }}>
          A practice sitting mirrors the real exam: {blueprint.session.scenarios_per_session}{" "}
          scenarios chosen at random, {blueprint.session.questions_per_scenario} questions
          from each ({blueprint.session.total_questions} total). Pass mark is{" "}
          {blueprint.session.pass_scaled} on a{" "}
          {blueprint.session.scaled_min}–{blueprint.session.scaled_max} scaled score.
        </p>

        {short && (
          <div className="warn">
            The question bank currently holds {pool.length} questions — fewer than a full{" "}
            {blueprint.session.total_questions}-question sitting. The exam will run with
            what's available. Generate more to fill a complete exam.
          </div>
        )}

        <div className="field">
          <label htmlFor="dur">Duration</label>
          <select
            id="dur"
            value={minutes}
            onChange={(e) => setMinutes(Number(e.target.value))}
          >
            <option value={5}>5 minutes (quick test)</option>
            <option value={30}>30 minutes</option>
            <option value={60}>60 minutes</option>
            <option value={90}>90 minutes</option>
            <option value={120}>120 minutes</option>
          </select>
        </div>

        <button className="btn" onClick={begin} disabled={pool.length === 0}>
          Start Exam →
        </button>
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Question pool by scenario</h3>
        <div className="summary-grid">
          {byScenario.map(({ s, count }) => (
            <div className="cellbox" key={s.id}>
              <b>{count}</b>
              {s.id} · {s.name}
            </div>
          ))}
        </div>
        <h3>Question pool by domain</h3>
        <div className="summary-grid">
          {byDomain.map(({ d, count }) => (
            <div className="cellbox" key={d.id}>
              <b>{count}</b>
              {d.id} · {d.name} ({Math.round(d.weight * 100)}%)
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

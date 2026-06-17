import { useState } from "react";
import { useExam } from "../state/examStore";
import { RichText } from "./RichText";

export function QuestionCard() {
  const { session, blueprint, current, answers, submitted, flagged, select, toggleFlag } =
    useExam();
  const [showContext, setShowContext] = useState(false);
  if (!session || !blueprint) return null;

  const sq = session.questions[current];
  const isSubmitted = !!submitted[current];
  const chosen = answers[current] ?? null;
  const scenario = blueprint.scenarios.find((s) => s.id === sq.question.scenario);

  const correctOpt = sq.options.find((o) => o.id === sq.correctOptionId)!;
  const chosenOpt = chosen ? sq.options.find((o) => o.id === chosen) ?? null : null;
  const gotItRight = isSubmitted && chosen === sq.correctOptionId;

  return (
    <section className="card">
      <div className="card-head">
        <h2>
          Question {current + 1} of {session.questions.length}
        </h2>
        <div className="head-actions">
          <button
            className={`flag-btn${flagged[current] ? " on" : ""}`}
            onClick={toggleFlag}
          >
            {flagged[current] ? "⚑ Flagged" : "⚐ Flag"}
          </button>
          <button
            className="scenario-chip"
            onClick={() => setShowContext((v) => !v)}
            title="Toggle scenario context"
          >
            Scenario: {scenario?.name ?? sq.question.scenario} {showContext ? "▴" : "▾"}
          </button>
        </div>
      </div>

      <div className="divider" />

      {showContext && scenario && (
        <div className="scenario-banner">
          <span className="banner-title">{scenario.name}.</span>{" "}
          <RichText text={scenario.description} />
        </div>
      )}

      <p className="stem">
        <RichText text={sq.question.stem} />
      </p>

      <div className="options">
        {sq.options.map((opt) => {
          const selected = chosen === opt.id;
          let cls = "option";
          if (isSubmitted) {
            if (opt.id === sq.correctOptionId) cls += " correct";
            else if (selected) cls += " wrong";
          } else if (selected) {
            cls += " selected";
          }
          return (
            <button
              key={opt.id}
              className={cls}
              disabled={isSubmitted}
              onClick={() => select(opt.id)}
            >
              <span className="badge">{opt.id}</span>
              <span className="option-body">
                <span className="option-text">
                  <RichText text={opt.text} />
                </span>
              </span>
            </button>
          );
        })}
      </div>

      {isSubmitted && (
        <div className={`feedback ${gotItRight ? "correct" : "wrong"}`}>
          <div className="fb-title">{gotItRight ? "Correct!" : "Incorrect"}</div>
          <div>
            <span className="fb-label">
              {correctOpt.id}. <RichText text={correctOpt.text} />
            </span>
            <br />
            <RichText text={correctOpt.explanation} />
          </div>
          {!gotItRight && chosenOpt && (
            <div className="fb-block">
              <span className="fb-label">Your answer — {chosenOpt.id}:</span>{" "}
              <RichText text={chosenOpt.explanation} />
            </div>
          )}
        </div>
      )}
    </section>
  );
}

import { useEffect, useMemo } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useExam } from "../state/examStore";
import { RichText } from "../components/RichText";

export function Results() {
  const { result, session } = useExam();
  const navigate = useNavigate();
  const res = useMemo(() => result(), [result]);

  useEffect(() => {
    if (!session) navigate({ to: "/" });
  }, [session, navigate]);

  if (!res) return null;

  return (
    <div className="screen">
      <div className="panel score-hero">
        <div className="score-num">{res.scaled}</div>
        <div style={{ color: "var(--ink-soft)" }}>
          scaled score · {res.correct}/{res.total} correct (
          {Math.round(res.rawPct * 100)}%)
        </div>
        <div className={`score-tag ${res.passed ? "pass" : "fail"}`}>
          {res.passed ? "PASS" : "FAIL"} · threshold {res.passScaled}
        </div>
        <p style={{ color: "var(--ink-soft)", fontSize: 13, marginTop: 18 }}>
          Scaled score is an approximation (100 + raw × 900) of the certification's
          SME-equated model, for practice only.
        </p>
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>By domain</h3>
        {res.domainStats.map((d) => {
          const pct = d.seen ? d.correct / d.seen : 0;
          return (
            <div className="bar-row" key={d.domainId}>
              <span>
                {d.domainId} · {d.name}{" "}
                <span style={{ color: "var(--ink-soft)" }}>
                  ({Math.round(d.weight * 100)}%)
                </span>
              </span>
              <span className="bar-track">
                <span className="bar-fill" style={{ width: `${pct * 100}%` }} />
              </span>
              <span>
                {d.correct}/{d.seen}
              </span>
            </div>
          );
        })}

        <h3>By scenario</h3>
        {res.scenarioStats.map((s) => {
          const pct = s.seen ? s.correct / s.seen : 0;
          return (
            <div className="bar-row" key={s.scenarioId}>
              <span>
                {s.scenarioId} · {s.name}
              </span>
              <span className="bar-track">
                <span className="bar-fill" style={{ width: `${pct * 100}%` }} />
              </span>
              <span>
                {s.correct}/{s.seen}
              </span>
            </div>
          );
        })}
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>
          Review — {res.missed.length} missed / unanswered
        </h3>
        {res.missed.length === 0 && <p>Perfect run. Nothing to review.</p>}
        {res.missed.map((m) => {
          const yours = m.chosenOptionId
            ? m.options.find((o) => o.id === m.chosenOptionId)
            : null;
          const correct = m.options.find((o) => o.id === m.correctOptionId)!;
          return (
            <div className="review-item" key={m.question.id}>
              <div className="stem">
                <RichText text={m.question.stem} />
              </div>
              <div className="review-line">
                <span className="tag-yours">Your answer:</span>{" "}
                {yours ? (
                  <>
                    {yours.id}. <RichText text={yours.text} />
                  </>
                ) : (
                  <em>unanswered</em>
                )}
              </div>
              {yours && (
                <div className="review-line" style={{ color: "var(--ink-soft)" }}>
                  <RichText text={yours.explanation} />
                </div>
              )}
              <div className="review-line">
                <span className="tag-correct">Correct answer:</span> {correct.id}.{" "}
                <RichText text={correct.text} />
              </div>
              <div className="review-line" style={{ color: "var(--ink-soft)" }}>
                <RichText text={correct.explanation} />
              </div>
            </div>
          );
        })}
      </div>

      <button className="btn" onClick={() => navigate({ to: "/" })}>
        ← Back to start
      </button>
    </div>
  );
}

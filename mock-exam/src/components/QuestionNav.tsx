import { Fragment, useState } from "react";
import { useExam } from "../state/examStore";

export function QuestionNav() {
  const { session, current, answers, submitted, flagged, maxVisited, goTo } =
    useExam();
  const [showLegend, setShowLegend] = useState(false);
  if (!session) return null;

  // Group consecutive questions by scenario for the S1/S2/... labels.
  let lastScenario = "";

  return (
    <nav className="nav">
      <button
        className="cell legend"
        title="What do the colors mean?"
        onClick={() => setShowLegend((v) => !v)}
      >
        ?
      </button>

      {showLegend && (
        <div className="nav-legend">
          Answer or flag each question to unlock the next. Click any previously
          visited question to jump back and change your answer.
          <div className="legend-keys">
            <span>
              <span className="cell current legend-swatch" /> Current
            </span>
            <span>
              <span className="cell selected legend-swatch" /> Answered
            </span>
            <span>
              <span className="cell flagged legend-swatch" /> Flagged
            </span>
            <span>
              <span className="cell answered legend-swatch" /> Submitted
            </span>
            <span>
              <span className="cell locked legend-swatch" /> Locked
            </span>
          </div>
        </div>
      )}

      {session.questions.map((sq, idx) => {
        const showLabel = sq.question.scenario !== lastScenario;
        lastScenario = sq.question.scenario;
        const isLocked = idx > maxVisited;
        const isAnswered = answers[idx] != null && !submitted[idx];
        const cls = [
          "cell",
          submitted[idx] ? "answered" : "",
          isAnswered ? "selected" : "",
          flagged[idx] ? "flagged" : "",
          idx === current ? "current" : "",
          isLocked ? "locked" : "",
        ]
          .filter(Boolean)
          .join(" ");
        return (
          <Fragment key={sq.question.id}>
            {showLabel && (
              <span className="group-label">{sq.question.scenario}</span>
            )}
            <button
              className={cls}
              onClick={() => goTo(idx)}
              disabled={isLocked}
              title={isLocked ? "Locked — reach this question first" : `Question ${idx + 1}`}
            >
              {idx + 1}
            </button>
          </Fragment>
        );
      })}
    </nav>
  );
}

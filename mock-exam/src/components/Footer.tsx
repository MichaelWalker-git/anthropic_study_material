import { useNavigate } from "@tanstack/react-router";
import { useExam } from "../state/examStore";

export function Footer() {
  const { session, current, answers, submitted, prev, next, submit, finish } =
    useExam();
  const navigate = useNavigate();
  if (!session) return null;

  const total = session.questions.length;
  const isLast = current === total - 1;
  const isSubmitted = !!submitted[current];
  const hasSelection = answers[current] != null;
  const unanswered = session.questions.filter((_, i) => !submitted[i]).length;

  const handleReview = () => {
    if (unanswered > 0) {
      const ok = window.confirm(
        `You still have ${unanswered} unanswered question${
          unanswered === 1 ? "" : "s"
        }. They will be scored as incorrect. Finish and review anyway?`,
      );
      if (!ok) return;
    }
    finish();
    navigate({ to: "/results" });
  };

  return (
    <div className="footer">
      <button className="btn muted" onClick={prev} disabled={current === 0}>
        ← Previous
      </button>
      <div className="footer-right">
        {!isSubmitted ? (
          <>
            <button className="btn" onClick={submit} disabled={!hasSelection}>
              Submit Answer
            </button>
            <button className="btn ghost" onClick={next} disabled={isLast}>
              Skip →
            </button>
          </>
        ) : (
          <button className="btn" onClick={next} disabled={isLast}>
            Next →
          </button>
        )}
        <button className="btn ghost" onClick={handleReview}>
          Review
        </button>
      </div>
    </div>
  );
}

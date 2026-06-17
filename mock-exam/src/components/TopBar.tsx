import { useExam } from "../state/examStore";

function fmt(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function TopBar() {
  const { score, session, secondsLeft } = useExam();
  const total = session?.questions.length ?? 0;
  const low = secondsLeft <= 60;
  return (
    <header className="topbar">
      <h1>Claude Certified Architect: Foundations Practice Exam</h1>
      <div className="meta">
        <span className="chip">
          Score: {score} / {total}
        </span>
        <span className={`chip timer mono${low ? " low" : ""}`}>
          {fmt(secondsLeft)}
        </span>
      </div>
    </header>
  );
}

import { useEffect } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useExam } from "../state/examStore";
import { TopBar } from "../components/TopBar";
import { QuestionNav } from "../components/QuestionNav";
import { QuestionCard } from "../components/QuestionCard";
import { Footer } from "../components/Footer";

export function Exam() {
  const { session, finished } = useExam();
  const navigate = useNavigate();

  useEffect(() => {
    if (!session) {
      navigate({ to: "/" });
    } else if (finished) {
      navigate({ to: "/results" });
    }
  }, [session, finished, navigate]);

  if (!session) return null;

  return (
    <>
      <TopBar />
      <QuestionNav />
      <QuestionCard />
      <Footer />
    </>
  );
}

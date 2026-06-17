import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { Blueprint, Result, Session } from "../types";
import { assembleSession } from "../lib/session";
import { scoreSession } from "../lib/scoring";

interface ExamState {
  blueprint: Blueprint | null;
  session: Session | null;
  current: number;
  answers: Record<number, string | null>;
  submitted: Record<number, boolean>;
  flagged: Record<number, boolean>;
  maxVisited: number;
  secondsLeft: number;
  finished: boolean;
}

interface ExamStore extends ExamState {
  score: number;
  startExam: (blueprint: Blueprint, pool: import("../types").Question[], minutes: number) => void;
  select: (optionId: string) => void;
  submit: () => void;
  goTo: (index: number) => void;
  next: () => void;
  prev: () => void;
  toggleFlag: () => void;
  finish: () => void;
  result: () => Result | null;
}

const Ctx = createContext<ExamStore | null>(null);

export function ExamProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ExamState>({
    blueprint: null,
    session: null,
    current: 0,
    answers: {},
    submitted: {},
    flagged: {},
    maxVisited: 0,
    secondsLeft: 0,
    finished: false,
  });

  const timerRef = useRef<number | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const startExam = useCallback(
    (blueprint: Blueprint, pool: import("../types").Question[], minutes: number) => {
      const session = assembleSession(blueprint, pool);
      setState({
        blueprint,
        session,
        current: 0,
        answers: {},
        submitted: {},
        flagged: {},
        maxVisited: 0,
        secondsLeft: minutes * 60,
        finished: false,
      });
    },
    [],
  );

  const finish = useCallback(() => {
    clearTimer();
    setState((s) => ({ ...s, finished: true }));
  }, [clearTimer]);

  // Countdown timer; auto-finish at 0.
  useEffect(() => {
    if (!state.session || state.finished) {
      clearTimer();
      return;
    }
    if (timerRef.current !== null) return;
    timerRef.current = window.setInterval(() => {
      setState((s) => {
        if (s.secondsLeft <= 1) {
          return { ...s, secondsLeft: 0, finished: true };
        }
        return { ...s, secondsLeft: s.secondsLeft - 1 };
      });
    }, 1000);
    return clearTimer;
  }, [state.session, state.finished, clearTimer]);

  const select = useCallback((optionId: string) => {
    setState((s) => {
      if (s.submitted[s.current]) return s;
      return { ...s, answers: { ...s.answers, [s.current]: optionId } };
    });
  }, []);

  const submit = useCallback(() => {
    setState((s) => {
      if (s.answers[s.current] == null) return s;
      return { ...s, submitted: { ...s.submitted, [s.current]: true } };
    });
  }, []);

  const goTo = useCallback((index: number) => {
    setState((s) => {
      if (!s.session) return s;
      // Locked: cannot jump ahead to a question that hasn't been reached yet.
      if (index > s.maxVisited) return s;
      const clamped = Math.max(0, Math.min(index, s.session.questions.length - 1));
      return { ...s, current: clamped };
    });
  }, []);

  const next = useCallback(() => {
    setState((s) => {
      if (!s.session) return s;
      const target = Math.min(s.current + 1, s.session.questions.length - 1);
      return {
        ...s,
        current: target,
        maxVisited: Math.max(s.maxVisited, target),
      };
    });
  }, []);

  const prev = useCallback(() => {
    setState((s) => ({ ...s, current: Math.max(s.current - 1, 0) }));
  }, []);

  const toggleFlag = useCallback(() => {
    setState((s) => ({
      ...s,
      flagged: { ...s.flagged, [s.current]: !s.flagged[s.current] },
    }));
  }, []);

  const score = useMemo(() => {
    if (!state.session) return 0;
    let n = 0;
    state.session.questions.forEach((sq, idx) => {
      if (state.submitted[idx] && state.answers[idx] === sq.correctOptionId) n++;
    });
    return n;
  }, [state.session, state.submitted, state.answers]);

  const result = useCallback((): Result | null => {
    if (!state.blueprint || !state.session) return null;
    return scoreSession(state.blueprint, state.session, state.answers);
  }, [state.blueprint, state.session, state.answers]);

  const store: ExamStore = {
    ...state,
    score,
    startExam,
    select,
    submit,
    goTo,
    next,
    prev,
    toggleFlag,
    finish,
    result,
  };

  return <Ctx.Provider value={store}>{children}</Ctx.Provider>;
}

export function useExam(): ExamStore {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useExam must be used within ExamProvider");
  return ctx;
}

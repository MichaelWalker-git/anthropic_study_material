import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
} from "@tanstack/react-router";
import { ExamProvider } from "./state/examStore";
import { Start } from "./routes/Start";
import { Exam } from "./routes/Exam";
import { Results } from "./routes/Results";

const rootRoute = createRootRoute({
  component: () => (
    <ExamProvider>
      <Outlet />
    </ExamProvider>
  ),
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: Start,
});

const examRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/exam",
  component: Exam,
});

const resultsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/results",
  component: Results,
});

const routeTree = rootRoute.addChildren([indexRoute, examRoute, resultsRoute]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

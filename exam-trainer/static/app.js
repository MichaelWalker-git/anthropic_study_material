// Trainer frontend. Deliberately plain vanilla JS — no frameworks:
// a 60-question quiz doesn't need them (the same "don't overcomplicate
// where simple is enough" principle as keeping the LLM out of the core).

const state = {
  mode: "practice",
  instantFeedback: true,  // show answer immediately (independent of mode)
  questions: [],   // questions of the current session
  index: 0,        // index of the current question
  maxReached: 0,   // furthest reached index (for the navigator: where you may jump)
  selected: null,  // chosen original_letter (for the current, not-yet-graded one)
  // answers[i] = {selected, verdict} for each answered question.
  // We index by position (not push) so you can go back and review
  // without duplicating records.
  answers: [],
};

// Results summary for the recap/diagnosis — answered questions only.
function answeredResults() {
  return state.answers
    .map((a, i) => a && { ...a.verdict, chosen_letter: a.selected,
                          scenario: state.questions[i].scenario })
    .filter(Boolean);
}

// Key for storing an unfinished session in the browser (resume). We don't store the exam.
const RESUME_KEY = "exam-trainer:session";

const $ = (id) => document.getElementById(id);

async function api(path, opts) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

// --- Session setup ---
async function initSetup() {
  const { scenarios, counts } = await api("/api/scenarios");
  const sel = $("scenario");
  for (const s of scenarios) {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = `${s} (${counts[s]})`;
    sel.appendChild(opt);
  }

  // In exam mode we hide the scenario filter (the exam draws from all), and
  // feedback is off by default — but the checkbox stays available if you want
  // an exam with instant answers.
  $("mode").addEventListener("change", (e) => {
    const isExam = e.target.value === "exam";
    $("scenario-row").classList.toggle("hidden", isExam);
    $("instant-feedback").checked = !isExam;
  });
  $("instant-feedback").checked = true; // practice — default

  showResumeOption();
  await refreshStats();
}

async function refreshStats() {
  const s = await api("/api/stats");
  if (!s.total) {
    $("stats-summary").textContent = "No attempts yet.";
    return;
  }
  const pct = Math.round(s.accuracy * 100);
  let txt = `Total attempts: ${s.total} · accuracy ${pct}%`;
  if (s.weakest_scenario) txt += ` · weakest topic: ${s.weakest_scenario}`;
  $("stats-summary").textContent = txt;
}

async function startSession() {
  state.mode = $("mode").value;
  state.instantFeedback = $("instant-feedback").checked;
  const scenario = state.mode === "exam" ? null : ($("scenario").value || null);
  const data = await api("/api/session", {
    method: "POST",
    body: JSON.stringify({ mode: state.mode, scenario }),
  });
  state.questions = data.questions;
  state.index = 0;
  state.answers = [];
  state.generatedAnswer = null;
  saveSession();
  show("quiz");
  renderQuestion();
}

// --- Question render ---
// A question can be in one of two states:
//   * new (not yet answered) — you can pick and press "Answer";
//   * already answered (there's a record in state.answers[index]) — REVIEW mode:
//     we show your choice, the correct answer and the explanation, no replay.
function renderQuestion() {
  state.maxReached = Math.max(state.maxReached, state.index);  // where jumping is allowed
  const q = state.questions[state.index];
  const prior = state.answers[state.index];  // record, if already answered
  state.selected = prior ? prior.selected : null;
  state.answered = !!prior;

  $("progress-text").textContent = `Question ${state.index + 1} of ${state.questions.length}`;
  $("scenario-tag").textContent = q.scenario;
  $("situation").textContent = q.situation || "";
  $("situation").classList.toggle("hidden", !q.situation);
  $("prompt").textContent = q.prompt;

  // Returning to an already-answered question = REVIEW mode (read-only):
  //   * your choice is ALWAYS visible (that's what you asked for);
  //   * correctness + explanation — if feedback is enabled in this session.
  // In an exam without feedback you see only your choice, no reveal of the correct one.
  const reviewing = !!prior;
  const showAnswer = prior && state.instantFeedback;

  const box = $("options");
  box.innerHTML = "";
  for (const opt of q.options) {
    const btn = document.createElement("button");
    btn.className = "option";
    btn.dataset.orig = opt.original_letter;
    btn.innerHTML = `<span class="letter">${opt.letter}</span> ${opt.text}`;
    if (reviewing) {
      // Always show the chosen option.
      if (opt.original_letter === prior.selected) btn.classList.add("selected");
      // Correctness — only if feedback is allowed.
      if (showAnswer) {
        if (opt.original_letter === prior.verdict.correct_letter) btn.classList.add("correct");
        else if (opt.original_letter === prior.selected) btn.classList.add("wrong");
      }
      // In review the choice can't be replayed (read-only).
    } else {
      btn.addEventListener("click", () => selectOption(btn, opt.original_letter));
    }
    box.appendChild(btn);
  }

  // Navigation buttons.
  $("prev").classList.toggle("hidden", state.index === 0);
  const hasNext = state.index + 1 < state.questions.length;

  if (reviewing) {
    // Review mode: submit hidden, "Next" walks forward through history.
    $("submit").classList.add("hidden");
    $("next").classList.toggle("hidden", !hasNext);
    if (showAnswer) {
      revealFeedback(prior.verdict);
      $("submit").classList.add("hidden");  // revealFeedback touches the buttons — fix them
      $("next").classList.toggle("hidden", !hasNext);
    } else {
      // Exam without feedback: show only the "your answer: X" label, no grading.
      const fb = $("feedback");
      fb.className = "feedback";
      fb.innerHTML = `<strong>Your answer: ${displayLetter(q, prior.selected)}</strong>`;
      fb.classList.remove("hidden");
    }
  } else {
    $("feedback").classList.add("hidden");
    $("submit").classList.remove("hidden");
    $("submit").disabled = true;
    $("next").classList.add("hidden");
  }

  renderNav();
}

// Question navigator at the bottom: numbers with state highlighting + jump on click.
// UX principle: do NOT reveal correctness in exam mode (feedback deferred) —
// there a visited question is neutral ("answered"), and green/red only when
// feedback is on. Otherwise the navigator would leak answers ahead of time.
function renderNav() {
  const grid = $("nav-grid");
  grid.innerHTML = "";
  const single = state.questions.length <= 1;       // a generated single one — no grid
  $("nav").classList.toggle("hidden", single);
  if (single) return;

  for (let i = 0; i < state.questions.length; i++) {
    const cell = document.createElement("button");
    cell.className = "nav-cell";
    cell.textContent = i + 1;

    const ans = state.answers[i];
    if (ans) {
      if (state.instantFeedback) {
        cell.classList.add(ans.verdict.is_correct ? "nav-correct" : "nav-wrong");
      } else {
        cell.classList.add("nav-answered");        // exam: only "answered", no grading
      }
    }
    if (i === state.index) cell.classList.add("nav-current");

    // Allow jumping only to already-REACHED questions (like a real exam:
    // we don't jump forward "blind"). Reached = index <= the furthest we've
    // already been (maxReached), not just the current one — otherwise, after
    // going back, we couldn't move forward again via the navigator.
    const reachable = i <= (state.maxReached ?? state.index);
    if (reachable && i !== state.index) {
      cell.addEventListener("click", () => { state.index = i; renderQuestion(); });
    } else if (!reachable) {
      cell.classList.add("nav-locked");
      cell.disabled = true;
    }
    grid.appendChild(cell);
  }

  // Legend for the mode's state.
  $("nav-legend").innerHTML = state.instantFeedback
    ? '<span class="lg nav-correct"></span>correct ' +
      '<span class="lg nav-wrong"></span>wrong ' +
      '<span class="lg nav-current"></span>current'
    : '<span class="lg nav-answered"></span>answered ' +
      '<span class="lg nav-current"></span>current';
}

// Translate the original (bank) letter into the displayed A-D (options are shuffled).
function displayLetter(q, originalLetter) {
  const opt = q.options.find((o) => o.original_letter === originalLetter);
  return opt ? opt.letter : originalLetter;
}

function prevQuestion() {
  if (state.index > 0) {
    state.index -= 1;
    renderQuestion();
  }
}

function selectOption(btn, origLetter) {
  if (state.answered) return; // after grading the choice is frozen
  state.selected = origLetter;
  document.querySelectorAll(".option").forEach((b) => b.classList.remove("selected"));
  btn.classList.add("selected");
  $("submit").disabled = false;
}

// --- Grading ---
async function submitAnswer() {
  if (state.selected == null) return;
  const q = state.questions[state.index];

  let verdict;
  if (q.id === -1 && state.generatedAnswer) {
    // A generated question isn't in the bank — grade on the client, no logging.
    const correct = state.generatedAnswer.correct;
    verdict = {
      is_correct: state.selected === correct,
      correct_letter: correct,
      why: state.generatedAnswer.why,
    };
  } else {
    verdict = await api("/api/grade", {
      method: "POST",
      body: JSON.stringify({
        question_id: q.id,
        original_letter: state.selected,
        mode: state.mode,
      }),
    });
  }
  state.answers[state.index] = { selected: state.selected, verdict };
  state.answered = true;
  saveSession();

  if (state.instantFeedback) {
    revealFeedback(verdict);
  }
  advanceOrFinish();
}

function revealFeedback(verdict) {
  // Highlight the correct and (if wrong) the chosen option.
  document.querySelectorAll(".option").forEach((b) => {
    const orig = b.dataset.orig;
    if (orig === verdict.correct_letter) b.classList.add("correct");
    else if (orig === state.selected) b.classList.add("wrong");
  });
  // In the text we show the SHUFFLED letters (as on screen), not the bank ones —
  // otherwise "correct (A)" might not match the highlighted button A.
  const q = state.questions[state.index];
  const fb = $("feedback");
  fb.className = "feedback " + (verdict.is_correct ? "ok" : "bad");
  let html = `<strong>${verdict.is_correct ? "Correct ✓" : "Wrong ✗"}</strong>`;
  // If wrong and there's an explanation for your specific option — show why it's wrong.
  if (!verdict.is_correct && verdict.chosen_why) {
    html += `<p><em>Why your choice (${displayLetter(q, state.selected)}) is wrong:</em> ${verdict.chosen_why}</p>`;
  }
  html += `<p><em>Why the correct one (${displayLetter(q, verdict.correct_letter)}) is right:</em> ${verdict.why}</p>`;
  fb.innerHTML = html;
  fb.classList.remove("hidden");
  $("submit").classList.add("hidden");
  $("next").classList.remove("hidden");
}

function advanceOrFinish() {
  // If we show feedback — wait for the "Next" button. If not (deferred
  // feedback) — advance automatically.
  if (!state.instantFeedback) {
    if (state.index + 1 < state.questions.length) {
      state.index += 1;
      renderQuestion();
    } else {
      finish();
    }
  }
}

function nextQuestion() {
  if (state.index + 1 < state.questions.length) {
    state.index += 1;
    saveSession();
    renderQuestion();
  } else {
    finish();
  }
}

// --- Recap ---
function finish() {
  const results = answeredResults();
  const total = results.length;
  const correct = results.filter((r) => r.is_correct).length;
  const pct = total ? Math.round((correct / total) * 100) : 0;
  $("score").innerHTML = `<div class="big">${correct} / ${total}</div><div>${pct}%</div>`;

  const byScenario = {};
  for (const r of results) {
    const b = (byScenario[r.scenario] ||= { total: 0, correct: 0 });
    b.total += 1;
    b.correct += r.is_correct ? 1 : 0;
  }
  const rows = Object.entries(byScenario)
    .map(([s, b]) => `<tr><td>${s}</td><td>${b.correct}/${b.total}</td>` +
      `<td>${Math.round((b.correct / b.total) * 100)}%</td></tr>`)
    .join("");
  $("breakdown").innerHTML = `<table><thead><tr><th>Scenario</th><th>Correct</th><th>%</th></tr></thead><tbody>${rows}</tbody></table>`;

  clearSession(); // session finished — nothing left to resume
  show("results");
  refreshStats();
}

// --- Drilling weak areas (weighted sampling by error statistics) ---
// Launched from the results screen: the test gave data -> we train the worst-known.
async function drillWeak() {
  const data = await api("/api/session", {
    method: "POST",
    body: JSON.stringify({ mode: "weak", count: 10 }),
  });
  state.mode = "practice";          // training, not an exam
  state.instantFeedback = true;     // show feedback immediately (else it inherits exam)
  state.questions = data.questions;
  state.index = 0;
  state.answers = [];
  state.generatedAnswer = null;
  show("quiz");
  renderQuestion();
}

// --- Diagnostician agent: analyzes the session's mistakes and recommends a topic ---
async function diagnose() {
  const btn = $("diagnose");
  const box = $("diagnosis");
  btn.disabled = true;
  btn.textContent = "Analyzing…";
  try {
    const answers = answeredResults().map((r) => ({
      question_id: r.question_id,
      chosen: r.chosen_letter,
    }));
    const d = await api("/api/diagnose", {
      method: "POST",
      body: JSON.stringify({ answers }),
    });
    let html = `<h3>Conclusion</h3><p>${d.summary}</p>`;
    if (d.misconceptions && d.misconceptions.length) {
      html += "<ul>" + d.misconceptions.map((m) => `<li>${m}</li>`).join("") + "</ul>";
    }
    if (d.recommended_scenario) {
      html += `<p><strong>Recommendation:</strong> ${d.recommendation}</p>`;
      // Handoff to the generator: the button creates a question on the recommended topic.
      html += `<button id="gen-recommended" class="secondary">` +
        `✨ Generate a question: ${d.recommended_scenario}</button>`;
    }
    box.innerHTML = html;
    box.classList.remove("hidden");
    if (d.recommended_scenario) {
      $("gen-recommended").addEventListener(
        "click", () => generateQuestion(d.recommended_scenario));
    }
  } catch (e) {
    box.innerHTML = `Could not analyze. Check the Bedrock key.<br>${e.message}`;
    box.classList.remove("hidden");
  } finally {
    btn.disabled = false;
    btn.textContent = "🧠 Review mistakes (AI)";
  }
}

// --- Generating a fresh question via Sonnet ---
// scenario is passed explicitly (from the diagnostician or the results); null = weakest topic.
async function generateQuestion(scenario = null) {
  try {
    const q = await api("/api/generate", {
      method: "POST",
      body: JSON.stringify({ scenario }),
    });
    // A generated question is a one-question practice mini-session.
    state.mode = "practice";
    state.instantFeedback = true;
    // On the server id = -1; it's no good for grade, so we handle it locally.
    state.questions = [q];
    state.index = 0;
    state.answers = [];
    state.generatedAnswer = { correct: q.correct_original_letter, why: q.why };
    show("quiz");
    renderQuestion();
  } catch (e) {
    alert("Could not generate a question. Check the Bedrock key in learning/.env.\n" + e.message);
  }
}

// --- Saving/restoring a session (localStorage, non-exam only) ---
// We deliberately do NOT save the exam: it mimics a real exam, where pauses and
// resuming aren't allowed. Generated AI questions aren't saved either
// (they're not in the bank, and after a reload the server won't return them).
function saveSession() {
  if (state.mode === "exam" || state.generatedAnswer) return;
  const snapshot = {
    mode: state.mode,
    instantFeedback: state.instantFeedback,
    questions: state.questions,
    index: state.index,
    maxReached: state.maxReached,
    answers: state.answers,
  };
  try {
    localStorage.setItem(RESUME_KEY, JSON.stringify(snapshot));
  } catch (_) { /* private mode / overflow — not critical */ }
}

function clearSession() {
  try { localStorage.removeItem(RESUME_KEY); } catch (_) {}
}

function loadSession() {
  try {
    const raw = localStorage.getItem(RESUME_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_) { return null; }
}

function showResumeOption() {
  const saved = loadSession();
  const row = $("resume-row");
  if (!saved || !saved.questions || saved.index >= saved.questions.length) {
    row.classList.add("hidden");
    return;
  }
  $("resume-info").textContent =
    `(question ${saved.index + 1} of ${saved.questions.length})`;
  row.classList.remove("hidden");
}

function resumeSession() {
  const saved = loadSession();
  if (!saved) return;
  state.mode = saved.mode;
  state.instantFeedback = saved.instantFeedback;
  state.questions = saved.questions;
  state.index = saved.index;
  state.maxReached = saved.maxReached ?? saved.index;
  state.answers = saved.answers || [];
  state.generatedAnswer = null;
  show("quiz");
  renderQuestion();
}

function show(screen) {
  for (const s of ["setup", "quiz", "results"]) {
    $(s).classList.toggle("hidden", s !== screen);
  }
  if (screen === "setup") showResumeOption();
}

// --- Event binding ---
$("start").addEventListener("click", startSession);
$("submit").addEventListener("click", submitAnswer);
$("next").addEventListener("click", nextQuestion);
$("prev").addEventListener("click", prevQuestion);
$("restart").addEventListener("click", () => show("setup"));
$("drill-weak").addEventListener("click", drillWeak);
$("diagnose").addEventListener("click", diagnose);
$("resume").addEventListener("click", resumeSession);

initSetup();

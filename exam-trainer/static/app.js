// Фронтенд тренажера. Навмисно простий vanilla JS — без фреймворків:
// вікторина на 60 питань їх не потребує (той самий принцип "не ускладнюй там,
// де достатньо простого", що й із відмовою від LLM у ядрі).

const state = {
  mode: "practice",
  instantFeedback: true,  // показувати відповідь одразу (окремо від режиму)
  questions: [],   // питання поточної сесії
  index: 0,        // індекс поточного питання
  maxReached: 0,   // найдальший досягнутий індекс (для навігатора: куди можна стрибати)
  selected: null,  // обрана original_letter (для поточного, ще не звіреного)
  // answers[i] = {selected, verdict} для кожного відповіданого питання.
  // Індексуємо за позицією (а не push), щоб можна було повертатись назад і
  // переглядати, не дублюючи записи.
  answers: [],
};

// Зведення результатів для підсумку/діагнозу — лише відповіддані питання.
function answeredResults() {
  return state.answers
    .map((a, i) => a && { ...a.verdict, chosen_letter: a.selected,
                          scenario: state.questions[i].scenario })
    .filter(Boolean);
}

// Ключ для збереження незавершеної сесії в браузері (resume). Екзам не зберігаємо.
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

// --- Налаштування сесії ---
async function initSetup() {
  const { scenarios, counts } = await api("/api/scenarios");
  const sel = $("scenario");
  for (const s of scenarios) {
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = `${s} (${counts[s]})`;
    sel.appendChild(opt);
  }

  // У exam-режимі фільтр за сценарієм ховаємо (іспит тягне з усіх), а фідбек
  // за замовч. вимикаємо — але галочка лишається доступною, якщо хочеш екзам
  // із миттєвими відповідями.
  $("mode").addEventListener("change", (e) => {
    const isExam = e.target.value === "exam";
    $("scenario-row").classList.toggle("hidden", isExam);
    $("instant-feedback").checked = !isExam;
  });
  $("instant-feedback").checked = true; // practice — дефолт

  showResumeOption();
  await refreshStats();
}

async function refreshStats() {
  const s = await api("/api/stats");
  if (!s.total) {
    $("stats-summary").textContent = "Ще немає спроб.";
    return;
  }
  const pct = Math.round(s.accuracy * 100);
  let txt = `Усього спроб: ${s.total} · точність ${pct}%`;
  if (s.weakest_scenario) txt += ` · найслабша тема: ${s.weakest_scenario}`;
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

// --- Рендер питання ---
// Питання може бути в одному з двох станів:
//   * нове (ще не відповіли) — можна вибирати й тиснути "Відповісти";
//   * вже відповіли (є запис у state.answers[index]) — режим ПЕРЕГЛЯДУ:
//     показуємо твій вибір, правильну відповідь і пояснення, без переграти.
function renderQuestion() {
  state.maxReached = Math.max(state.maxReached, state.index);  // куди дозволено стрибати
  const q = state.questions[state.index];
  const prior = state.answers[state.index];  // запис, якщо вже відповідали
  state.selected = prior ? prior.selected : null;
  state.answered = !!prior;

  $("progress-text").textContent = `Питання ${state.index + 1} з ${state.questions.length}`;
  $("scenario-tag").textContent = q.scenario;
  $("situation").textContent = q.situation || "";
  $("situation").classList.toggle("hidden", !q.situation);
  $("prompt").textContent = q.prompt;

  // Повернення на вже відповіддане питання = режим ПЕРЕГЛЯДУ (read-only):
  //   * твій вибір видно ЗАВЖДИ (це те, що ти питала);
  //   * правильність + пояснення — якщо в цій сесії фідбек увімкнено.
  // В екзамі без фідбеку бачиш лише свій вибір, без розкриття правильної.
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
      // Завжди показуємо обраний варіант.
      if (opt.original_letter === prior.selected) btn.classList.add("selected");
      // Правильність — лише якщо дозволено фідбек.
      if (showAnswer) {
        if (opt.original_letter === prior.verdict.correct_letter) btn.classList.add("correct");
        else if (opt.original_letter === prior.selected) btn.classList.add("wrong");
      }
      // У перегляді вибір не переграється (read-only).
    } else {
      btn.addEventListener("click", () => selectOption(btn, opt.original_letter));
    }
    box.appendChild(btn);
  }

  // Кнопки навігації.
  $("prev").classList.toggle("hidden", state.index === 0);
  const hasNext = state.index + 1 < state.questions.length;

  if (reviewing) {
    // Режим перегляду: submit прихований, "Далі" веде вперед по історії.
    $("submit").classList.add("hidden");
    $("next").classList.toggle("hidden", !hasNext);
    if (showAnswer) {
      revealFeedback(prior.verdict);
      $("submit").classList.add("hidden");  // revealFeedback чіпає кнопки — фіксуємо
      $("next").classList.toggle("hidden", !hasNext);
    } else {
      // Екзам без фідбеку: показуємо лише напис "твоя відповідь: X", без оцінки.
      const fb = $("feedback");
      fb.className = "feedback";
      fb.innerHTML = `<strong>Твоя відповідь: ${displayLetter(q, prior.selected)}</strong>`;
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

// Навігатор питань унизу: номери з підсвіткою стану + перехід по кліку.
// UX-принцип: НЕ розкривати правильність у exam-режимі (фідбек відкладено) —
// там пройдене питання нейтральне ("answered"), а зелене/червоне лише коли
// фідбек увімкнено. Інакше навігатор зливав би відповіді раніше часу.
function renderNav() {
  const grid = $("nav-grid");
  grid.innerHTML = "";
  const single = state.questions.length <= 1;       // згенероване одиночне — без сітки
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
        cell.classList.add("nav-answered");        // exam: лише "відповіли", без оцінки
      }
    }
    if (i === state.index) cell.classList.add("nav-current");

    // Перехід дозволяємо лише на вже ДОСЯГНУТІ питання (як на реальному іспиті:
    // вперед "наосліп" не стрибаємо). Досягнуте = індекс <= найдальшого, де ми
    // вже бували (maxReached), а не лише поточного — інакше, повернувшись назад,
    // не змогли б повернутись уперед по навігатору.
    const reachable = i <= (state.maxReached ?? state.index);
    if (reachable && i !== state.index) {
      cell.addEventListener("click", () => { state.index = i; renderQuestion(); });
    } else if (!reachable) {
      cell.classList.add("nav-locked");
      cell.disabled = true;
    }
    grid.appendChild(cell);
  }

  // Легенда під стан режиму.
  $("nav-legend").innerHTML = state.instantFeedback
    ? '<span class="lg nav-correct"></span>вірно ' +
      '<span class="lg nav-wrong"></span>хибно ' +
      '<span class="lg nav-current"></span>поточне'
    : '<span class="lg nav-answered"></span>відповіли ' +
      '<span class="lg nav-current"></span>поточне';
}

// Оригінальну (банкову) літеру переводимо в показану A-D (варіанти перемішані).
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
  if (state.answered) return; // після звірки вибір заморожено
  state.selected = origLetter;
  document.querySelectorAll(".option").forEach((b) => b.classList.remove("selected"));
  btn.classList.add("selected");
  $("submit").disabled = false;
}

// --- Звірка ---
async function submitAnswer() {
  if (state.selected == null) return;
  const q = state.questions[state.index];

  let verdict;
  if (q.id === -1 && state.generatedAnswer) {
    // Згенероване питання немає в банку — звіряємо на клієнті, без логування.
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
  // Підсвічуємо правильний і (якщо помилка) обраний варіант.
  document.querySelectorAll(".option").forEach((b) => {
    const orig = b.dataset.orig;
    if (orig === verdict.correct_letter) b.classList.add("correct");
    else if (orig === state.selected) b.classList.add("wrong");
  });
  // У тексті показуємо ПЕРЕМІШАНІ літери (як на екрані), а не банкові — інакше
  // "правильна (A)" може не збігатися з підсвіченою кнопкою A.
  const q = state.questions[state.index];
  const fb = $("feedback");
  fb.className = "feedback " + (verdict.is_correct ? "ok" : "bad");
  let html = `<strong>${verdict.is_correct ? "Правильно ✓" : "Неправильно ✗"}</strong>`;
  // Якщо помилка і є пояснення саме твого варіанту — показуємо чому він хибний.
  if (!verdict.is_correct && verdict.chosen_why) {
    html += `<p><em>Чому твій вибір (${displayLetter(q, state.selected)}) хибний:</em> ${verdict.chosen_why}</p>`;
  }
  html += `<p><em>Чому правильна (${displayLetter(q, verdict.correct_letter)}):</em> ${verdict.why}</p>`;
  fb.innerHTML = html;
  fb.classList.remove("hidden");
  $("submit").classList.add("hidden");
  $("next").classList.remove("hidden");
}

function advanceOrFinish() {
  // Якщо фідбек показуємо — чекаємо на кнопку "Далі". Якщо ні (відкладений
  // фідбек) — переходимо автоматично.
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

// --- Підсумок ---
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
  $("breakdown").innerHTML = `<table><thead><tr><th>Сценарій</th><th>Вірно</th><th>%</th></tr></thead><tbody>${rows}</tbody></table>`;

  clearSession(); // сесія завершена — більше нема чого відновлювати
  show("results");
  refreshStats();
}

// --- Добивання слабких місць (зважена вибірка за статистикою помилок) ---
// Запускається з екрана результатів: тест дав дані -> тренуємо найгірше знане.
async function drillWeak() {
  const data = await api("/api/session", {
    method: "POST",
    body: JSON.stringify({ mode: "weak", count: 10 }),
  });
  state.mode = "practice";          // тренування, не іспит
  state.instantFeedback = true;     // показуємо фідбек одразу (інакше успадкує екзам)
  state.questions = data.questions;
  state.index = 0;
  state.answers = [];
  state.generatedAnswer = null;
  show("quiz");
  renderQuestion();
}

// --- Агент-діагност: аналізує помилки сесії й рекомендує тему ---
async function diagnose() {
  const btn = $("diagnose");
  const box = $("diagnosis");
  btn.disabled = true;
  btn.textContent = "Аналізую…";
  try {
    const answers = answeredResults().map((r) => ({
      question_id: r.question_id,
      chosen: r.chosen_letter,
    }));
    const d = await api("/api/diagnose", {
      method: "POST",
      body: JSON.stringify({ answers }),
    });
    let html = `<h3>Висновок</h3><p>${d.summary}</p>`;
    if (d.misconceptions && d.misconceptions.length) {
      html += "<ul>" + d.misconceptions.map((m) => `<li>${m}</li>`).join("") + "</ul>";
    }
    if (d.recommended_scenario) {
      html += `<p><strong>Рекомендація:</strong> ${d.recommendation}</p>`;
      // Handoff до генератора: кнопка створює питання на рекомендовану тему.
      html += `<button id="gen-recommended" class="secondary">` +
        `✨ Згенерувати питання: ${d.recommended_scenario}</button>`;
    }
    box.innerHTML = html;
    box.classList.remove("hidden");
    if (d.recommended_scenario) {
      $("gen-recommended").addEventListener(
        "click", () => generateQuestion(d.recommended_scenario));
    }
  } catch (e) {
    box.innerHTML = `Не вдалося проаналізувати. Перевір Bedrock-ключ.<br>${e.message}`;
    box.classList.remove("hidden");
  } finally {
    btn.disabled = false;
    btn.textContent = "🧠 Розбір помилок (AI)";
  }
}

// --- Генерація свіжого питання через Sonnet ---
// scenario передаємо явно (від діагноста або з результатів); null = найслабша тема.
async function generateQuestion(scenario = null) {
  try {
    const q = await api("/api/generate", {
      method: "POST",
      body: JSON.stringify({ scenario }),
    });
    // Згенероване питання — це міні-сесія practice з одного питання.
    state.mode = "practice";
    state.instantFeedback = true;
    // У сервера id = -1; для grade воно не годиться, тож обробляємо локально.
    state.questions = [q];
    state.index = 0;
    state.answers = [];
    state.generatedAnswer = { correct: q.correct_original_letter, why: q.why };
    show("quiz");
    renderQuestion();
  } catch (e) {
    alert("Не вдалося згенерувати питання. Перевір Bedrock-ключ у learning/.env.\n" + e.message);
  }
}

// --- Збереження/відновлення сесії (localStorage, тільки не-екзам) ---
// Екзам навмисно НЕ зберігаємо: він імітує реальний іспит, де паузи й
// відновлення не передбачені. Згенеровані AI-питання теж не зберігаємо
// (їх немає в банку, після перезавантаження сервер їх не віддасть).
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
  } catch (_) { /* приватний режим / переповнення — не критично */ }
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
    `(питання ${saved.index + 1} з ${saved.questions.length})`;
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

// --- Прив'язка подій ---
$("start").addEventListener("click", startSession);
$("submit").addEventListener("click", submitAnswer);
$("next").addEventListener("click", nextQuestion);
$("prev").addEventListener("click", prevQuestion);
$("restart").addEventListener("click", () => show("setup"));
$("drill-weak").addEventListener("click", drillWeak);
$("diagnose").addEventListener("click", diagnose);
$("resume").addEventListener("click", resumeSession);

initSetup();

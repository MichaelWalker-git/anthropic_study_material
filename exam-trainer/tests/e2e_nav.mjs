// Браузерний драйвер для E2E-тесту навігації між питаннями.
// Запускається з test_e2e_navigation.py; пише результат JSON у stdout.
//
// Перевіряє дві поведінки, які раніше були баговані:
//   1) після "Назад" видно ОБРАНИЙ варіант (підсвічений);
//   2) літери у тексті фідбеку збігаються з підсвіченими кнопками
//      (бо варіанти перемішані — банкова літера != показана).
//
// Аргументи: process.argv[2] = baseURL, process.argv[3] = шлях до puppeteer-core.

const baseURL = process.argv[2];
const puppeteerPath = process.argv[3];
const puppeteer = (await import(puppeteerPath)).default;

const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

function fail(msg) { console.log(JSON.stringify({ ok: false, error: msg })); process.exit(0); }

let browser;
try {
  browser = await puppeteer.launch({ executablePath: CHROME, headless: "new", args: ["--no-sandbox"] });
  const page = await browser.newPage();
  await page.goto(baseURL, { waitUntil: "networkidle0" });

  await page.select("#mode", "practice");
  await page.click("#start");
  await page.waitForSelector("#quiz:not(.hidden) .option");

  // Відповісти на Q1 другим варіантом (показана "B") — щоб упіймати неоригінальну літеру.
  const opts = await page.$$(".option");
  await opts[1].click();
  await page.click("#submit");
  await page.waitForSelector("#feedback:not(.hidden)");

  // Q1 -> Q2 -> назад на Q1.
  await page.click("#next");
  await page.waitForFunction(() => document.getElementById("progress-text").textContent.includes("2 з"));
  await page.click("#prev");
  await page.waitForFunction(() => document.getElementById("progress-text").textContent.includes("1 з"));

  const r = await page.evaluate(() => {
    const sel = document.querySelector(".option.selected");
    const cor = document.querySelector(".option.correct");
    const fb = document.getElementById("feedback").textContent;
    const m = fb.match(/правильна \(([A-D])\)/);
    const cells = [...document.querySelectorAll(".nav-cell")];
    return {
      selectedVisible: !!sel,
      selectedLetter: sel ? sel.querySelector(".letter").textContent.trim() : null,
      correctHighlighted: cor ? cor.querySelector(".letter").textContent.trim() : null,
      correctInText: m ? m[1] : null,
      feedbackVisible: !document.getElementById("feedback").classList.contains("hidden"),
      submitHidden: document.getElementById("submit").classList.contains("hidden"),
      // Навігатор: q1 відповіли (тут поточне), має мати клас correct/wrong;
      // перевіряємо, що cell #1 пофарбований і поточний.
      navCellCount: cells.length,
      cell1Classes: cells[0] ? cells[0].className : null,
      cell1IsCurrent: cells[0] ? cells[0].classList.contains("nav-current") : null,
      cell1Colored: cells[0]
        ? (cells[0].classList.contains("nav-correct") || cells[0].classList.contains("nav-wrong"))
        : null,
    };
  });

  // Клік по номеру 2 у навігаторі має перейти на питання 2.
  const cells2 = await page.$$(".nav-cell");
  await cells2[1].click();
  await page.waitForFunction(() => document.getElementById("progress-text").textContent.includes("2 з"));
  r.navClickWorks = true;

  r.ok = true;
  console.log(JSON.stringify(r));
} catch (e) {
  fail(String(e));
} finally {
  if (browser) await browser.close();
}

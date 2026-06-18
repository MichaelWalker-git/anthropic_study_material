// Browser driver for the E2E navigation test between questions.
// Launched from test_e2e_navigation.py; prints the result JSON to stdout.
//
// Checks two behaviors that were previously buggy:
//   1) after "Back" the CHOSEN option is visible (highlighted);
//   2) the letters in the feedback text match the highlighted buttons
//      (because options are shuffled — the bank letter != the shown one).
//
// Arguments: process.argv[2] = baseURL, process.argv[3] = path to puppeteer-core.

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

  // Answer Q1 with the second option (shown "B") — to catch a non-original letter.
  const opts = await page.$$(".option");
  await opts[1].click();
  await page.click("#submit");
  await page.waitForSelector("#feedback:not(.hidden)");

  // Q1 -> Q2 -> back to Q1.
  await page.click("#next");
  await page.waitForFunction(() => document.getElementById("progress-text").textContent.includes("2 of"));
  await page.click("#prev");
  await page.waitForFunction(() => document.getElementById("progress-text").textContent.includes("1 of"));

  const r = await page.evaluate(() => {
    const sel = document.querySelector(".option.selected");
    const cor = document.querySelector(".option.correct");
    const fb = document.getElementById("feedback").textContent;
    const m = fb.match(/correct one \(([A-D])\)/);
    const cells = [...document.querySelectorAll(".nav-cell")];
    return {
      selectedVisible: !!sel,
      selectedLetter: sel ? sel.querySelector(".letter").textContent.trim() : null,
      correctHighlighted: cor ? cor.querySelector(".letter").textContent.trim() : null,
      correctInText: m ? m[1] : null,
      feedbackVisible: !document.getElementById("feedback").classList.contains("hidden"),
      submitHidden: document.getElementById("submit").classList.contains("hidden"),
      // Navigator: q1 was answered (current here), should have class correct/wrong;
      // we check that cell #1 is colored and current.
      navCellCount: cells.length,
      cell1Classes: cells[0] ? cells[0].className : null,
      cell1IsCurrent: cells[0] ? cells[0].classList.contains("nav-current") : null,
      cell1Colored: cells[0]
        ? (cells[0].classList.contains("nav-correct") || cells[0].classList.contains("nav-wrong"))
        : null,
    };
  });

  // Clicking number 2 in the navigator should jump to question 2.
  const cells2 = await page.$$(".nav-cell");
  await cells2[1].click();
  await page.waitForFunction(() => document.getElementById("progress-text").textContent.includes("2 of"));
  r.navClickWorks = true;

  r.ok = true;
  console.log(JSON.stringify(r));
} catch (e) {
  fail(String(e));
} finally {
  if (browser) await browser.close();
}

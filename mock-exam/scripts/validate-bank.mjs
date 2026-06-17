// Validates one or all per-scenario question files.
// Usage: node scripts/validate-bank.mjs [S1 S2 ...]
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const bankDir = join(here, "..", "public", "bank");
const ids = process.argv.slice(2);
const scenarios = ids.length ? ids : ["S1", "S2", "S3", "S4", "S5", "S6"];

let totalErrors = 0;
let grandTotal = 0;

for (const sid of scenarios) {
  let data;
  try {
    data = JSON.parse(readFileSync(join(bankDir, `${sid}.json`), "utf8"));
  } catch (e) {
    console.log(`${sid}: CANNOT READ/PARSE — ${e.message}`);
    totalErrors++;
    continue;
  }
  const qs = data.questions ?? [];
  const errors = [];
  const ids = new Set();
  const stems = new Set();
  const byDomain = {};
  const byTask = {};

  for (const q of qs) {
    if (ids.has(q.id)) errors.push(`duplicate id ${q.id}`);
    ids.add(q.id);
    if (q.scenario !== sid) errors.push(`${q.id}: scenario ${q.scenario} != ${sid}`);
    const stemKey = (q.stem || "").trim().toLowerCase();
    if (stems.has(stemKey)) errors.push(`${q.id}: duplicate stem`);
    stems.add(stemKey);
    if (!Array.isArray(q.options) || q.options.length !== 4)
      errors.push(`${q.id}: must have 4 options`);
    const correct = (q.options || []).filter((o) => o.correct);
    if (correct.length !== 1)
      errors.push(`${q.id}: needs exactly 1 correct (has ${correct.length})`);
    const optIds = (q.options || []).map((o) => o.id).join("");
    if (optIds !== "ABCD") errors.push(`${q.id}: option ids must be A,B,C,D (got ${optIds})`);
    for (const o of q.options || []) {
      if (!o.explanation || !o.explanation.trim())
        errors.push(`${q.id} opt ${o.id}: missing explanation`);
      if (!o.text || !o.text.trim())
        errors.push(`${q.id} opt ${o.id}: missing text`);
    }
    byDomain[q.domain] = (byDomain[q.domain] || 0) + 1;
    byTask[q.task_statement] = (byTask[q.task_statement] || 0) + 1;
  }

  // Length-bias analysis: how often is the correct option the strict longest,
  // and by what margin over the next-longest option.
  let correctLongest = 0;
  const bigMargins = [];
  for (const q of qs) {
    const lens = (q.options || []).map((o) => ({ id: o.id, len: (o.text || "").length, correct: o.correct }));
    if (lens.length !== 4) continue;
    const maxLen = Math.max(...lens.map((l) => l.len));
    const correct = lens.find((l) => l.correct);
    if (!correct) continue;
    const otherMax = Math.max(...lens.filter((l) => !l.correct).map((l) => l.len));
    const isStrictLongest = correct.len === maxLen && lens.filter((l) => l.len === maxLen).length === 1;
    if (isStrictLongest) {
      correctLongest++;
      const margin = correct.len - otherMax;
      if (margin > 20) bigMargins.push(`${q.id}(+${margin})`);
    }
  }
  const pctLongest = qs.length ? Math.round((100 * correctLongest) / qs.length) : 0;

  grandTotal += qs.length;
  const status = errors.length ? `❌ ${errors.length} errors` : "✅ ok";
  console.log(
    `${sid}: ${qs.length} questions ${status} | correct-longest ${correctLongest}/${qs.length} (${pctLongest}%) | domains ${JSON.stringify(
      byDomain,
    )} | tasks ${JSON.stringify(byTask)}`,
  );
  if (bigMargins.length) console.log(`   length-tell (margin>20): ${bigMargins.join(", ")}`);
  for (const e of errors.slice(0, 20)) console.log(`   - ${e}`);
  totalErrors += errors.length;
}

console.log(`\nTOTAL: ${grandTotal} questions, ${totalErrors} errors`);
process.exit(totalErrors ? 1 : 0);

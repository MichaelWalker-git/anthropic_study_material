// Lists questions whose correct option is the strict longest by margin>20,
// printing each option length so they can be rebalanced by hand.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
const here = dirname(fileURLToPath(import.meta.url));
const bankDir = join(here, "..", "public", "bank");
const sid = process.argv[2];
const data = JSON.parse(readFileSync(join(bankDir, `${sid}.json`), "utf8"));
for (const q of data.questions) {
  const lens = q.options.map((o) => ({ id: o.id, len: o.text.length, c: o.correct }));
  const correct = lens.find((l) => l.c);
  const otherMax = Math.max(...lens.filter((l) => !l.c).map((l) => l.len));
  const margin = correct.len - otherMax;
  const isLongest = correct.len === Math.max(...lens.map((l) => l.len));
  if (isLongest && margin > 20) {
    console.log(`${q.id}  margin +${margin}  [${lens.map((l) => `${l.id}${l.c ? "*" : ""}:${l.len}`).join(" ")}]`);
  }
}

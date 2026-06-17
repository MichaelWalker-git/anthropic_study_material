import { readFileSync } from "node:fs";
const sid = process.argv[2]; const min = Number(process.argv[3]||10);
const b = JSON.parse(readFileSync(`./public/bank/${sid}.json`,"utf8"));
for (const q of b.questions){
  const c=q.options.find(o=>o.correct);
  const om=Math.max(...q.options.filter(o=>!o.correct).map(o=>o.text.length));
  const isLong=c.text.length===Math.max(...q.options.map(o=>o.text.length));
  const m=c.text.length-om;
  if(isLong&&m>=min) console.log(`${q.id}\t+${m}\t${JSON.stringify(c.text)}`);
}

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
const here = dirname(fileURLToPath(import.meta.url));
const bankDir = join(here, "..", "public", "bank");
const scenarios = process.argv.slice(2).length ? process.argv.slice(2) : ["S1","S2","S3","S4","S5","S6"];
let grandLongest=0, grandTotal=0, grandWorst=[];
for (const sid of scenarios){
  let data; try{ data=JSON.parse(readFileSync(join(bankDir,`${sid}.json`),"utf8")); }catch{ continue; }
  const qs=data.questions||[]; let longest=0; const worst=[];
  for(const q of qs){
    const lens=q.options.map(o=>({id:o.id,len:o.text.length,correct:o.correct}));
    const maxLen=Math.max(...lens.map(l=>l.len));
    const correct=lens.find(l=>l.correct);
    const sorted=[...lens].sort((a,b)=>b.len-a.len);
    if(correct.len===maxLen){ longest++; 
      const margin = correct.len - (sorted.find(l=>!l.correct)?.len||0);
      worst.push({id:q.id, correctLen:correct.len, margin});
    }
  }
  grandLongest+=longest; grandTotal+=qs.length;
  worst.sort((a,b)=>b.margin-a.margin);
  console.log(`${sid}: correct-is-longest ${longest}/${qs.length} (${Math.round(100*longest/qs.length)}%). Worst margins: ${worst.slice(0,5).map(w=>w.id+`(+${w.margin})`).join(", ")}`);
}
console.log(`\nTOTAL correct-is-longest: ${grandLongest}/${grandTotal} (${Math.round(100*grandLongest/grandTotal)}%). Random baseline ~25%.`);

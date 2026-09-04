#!/usr/bin/env python3
"""Generate self-contained dashboard HTML with EMBEDDED data. No fetch needed."""
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(r"C:\Users\empir\Downloads\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026\Jonas_Abde_Intelligence_Systems_Research_Program_Q3_2026")
RECORDS = BASE / "data" / "study011_runs" / "confirmatory" / "canonical-run-002" / "run_records.jsonl"
OUT = BASE / "docs" / "study011-dashboard.html"

def main():
    recs = []
    if RECORDS.exists():
        for line in RECORDS.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip():
                try: recs.append(json.loads(line))
                except: pass

    cells = {}
    for x in recs:
        k = f"{x.get('provider_name','?')}|{x.get('condition','?')}"
        c = cells.setdefault(k, {"att":0,"lv":0,"fail":0})
        c["att"] += 1
        if x.get("execution_class")=="LIVE_VALID": c["lv"] += 1
        else: c["fail"] += 1

    a010 = [x for x in recs if str(x.get("implementation_fingerprint","")).startswith("dfe3513c")]
    a010_cells = {}
    for x in a010:
        k = f"{x.get('provider_name','?')}|{x.get('condition','?')}"
        c = a010_cells.setdefault(k, {"att":0,"lv":0})
        c["att"] += 1
        if x.get("execution_class")=="LIVE_VALID": c["lv"] += 1

    total_valid = sum(1 for x in recs if x.get("execution_class")=="LIVE_VALID")
    blocks = {
        "original_confirmatory": {"fp": "b6b7c2d0…", "records": sum(1 for x in recs if str(x.get("implementation_fingerprint","")).startswith("b6b7c2d0")), "valid": sum(1 for x in recs if str(x.get("implementation_fingerprint","")).startswith("b6b7c2d0") and x.get("execution_class")=="LIVE_VALID")},
        "original_openrouter_free": {"fp": "0c588022…", "records": sum(1 for x in recs if x.get("provider_name")=="openrouter" and str(x.get("implementation_fingerprint","")).startswith("0c588022")), "valid": 0},
        "post_amendment_010": {"fp": "dfe3513c…", "records": len(a010), "valid": sum(1 for x in a010 if x.get("execution_class")=="LIVE_VALID")},
    }

    data_json = json.dumps({"cells": cells, "a010_cells": a010_cells, "blocks": blocks,
                            "total_records": len(recs), "total_valid": total_valid,
                            "a010_records": len(a010), "a010_valid": sum(1 for x in a010 if x.get("execution_class")=="LIVE_VALID"),
                            "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})

    html = DATA_TEMPLATE.replace("__DATA__", data_json)
    OUT.write_text(html, encoding="utf-8", newline="\n")
    print(f"dashboard regenerated: {len(recs)} records, {total_valid} valid")

DATA_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="30">
<title>STUDY-011 — Live Confirmatory Matrix</title>
<style>
:root { --bg:#0a0e14; --surface:#111820; --border:#1e2833; --text:#d0d8e0; --dim:#5c6a78;
  --green:#34d399; --blue:#60a5fa; --amber:#fbbf24; --red:#f87171; --cyan:#22d3ee;
  --green-dim:#10b98122; --blue-dim:#3b82f622; --red-dim:#ef444422;
  --mono:'SF Mono','Fira Code',Consolas,monospace; --sans:-apple-system,'Segoe UI',Roboto,sans-serif; }
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:var(--sans)}
.header{padding:24px 32px 16px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}
.header h1{font-size:20px;font-weight:600}.header h1 span{color:var(--cyan)}
.header .meta{font-family:var(--mono);font-size:11px;color:var(--dim);text-align:right}
.header .live{color:var(--green);font-weight:600}
.header .live::before{content:'●';margin-right:5px;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:24px 32px 12px}
.stat{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px 18px}
.stat .label{font-size:10px;text-transform:uppercase;letter-spacing:.8px;color:var(--dim);margin-bottom:8px}
.stat .value{font-family:var(--mono);font-size:28px;font-weight:700;line-height:1}
.stat .sub{font-size:11px;color:var(--dim);margin-top:6px}
.stat .green{color:var(--green)}.stat .blue{color:var(--blue)}.stat .amber{color:var(--amber)}.stat .cyan{color:var(--cyan)}
.progress-bar{height:4px;background:var(--border);border-radius:2px;margin-top:10px;overflow:hidden}
.progress-bar .fill{height:100%;border-radius:2px}
.section{padding:16px 32px 8px}
.section h2{font-size:13px;text-transform:uppercase;letter-spacing:.8px;color:var(--dim);font-weight:600}
.cell-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;padding:12px 32px 24px}
.cell-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px 18px}
.cell-name{font-family:var(--mono);font-size:14px;font-weight:600;display:flex;justify-content:space-between;align-items:center}
.badge{font-size:10px;padding:3px 8px;border-radius:10px;font-weight:600}
.badge.done{background:var(--green-dim);color:var(--green)}
.badge.active{background:var(--blue-dim);color:var(--blue)}
.badge.burn{background:var(--red-dim);color:var(--red)}
.badge.pending{background:#1a2230;color:var(--dim)}
.nums{display:flex;gap:20px;margin-top:12px}
.num{font-family:var(--mono)}
.num .n{font-size:22px;font-weight:700}
.num .l{font-size:10px;color:var(--dim);text-transform:uppercase}
.num.valid .n{color:var(--green)}.num.fail .n{color:var(--red)}.num.att .n{color:var(--blue)}
.bar-label{display:flex;justify-content:space-between;font-size:10px;color:var(--dim);margin-bottom:4px}
.blocks{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:12px 32px 24px}
.block-card{background:var(--surface2,#161d27);border:1px solid var(--border);border-radius:10px;padding:14px 16px}
.block-card .bt{font-size:13px;font-weight:600;margin-bottom:4px}
.block-card .bp{font-family:var(--mono);font-size:11px;color:var(--dim);margin-top:6px}
.block-card .bs{font-size:11px}
.footer{padding:12px 32px 24px;text-align:center;font-family:var(--mono);font-size:10px;color:var(--dim)}
</style>
</head>
<body>
<div class="header">
  <h1>STUDY-011 <span>│</span> Confirmatory Matrix</h1>
  <div class="meta">
    <div class="live">LIVE</div>
    <div>Amendment 010 │ fp dfe3513c</div>
    <div>auto-refresh 30s</div>
  </div>
</div>
<div class="grid">
  <div class="stat"><div class="label">LIVE_VALID</div><div class="value green" id="v">--</div><div class="sub">of 464 target</div><div class="progress-bar"><div class="fill" id="vb" style="width:0%;background:var(--green)"></div></div></div>
  <div class="stat"><div class="label">TOTAL ATTEMPTS</div><div class="value blue" id="a">--</div><div class="sub">of 931 ceiling</div><div class="progress-bar"><div class="fill" id="ab" style="width:0%;background:var(--blue)"></div></div></div>
  <div class="stat"><div class="label">CELLS COMPLETE</div><div class="value amber" id="c">--</div><div class="sub">of 8 total</div><div class="progress-bar"><div class="fill" id="cb" style="width:0%;background:var(--amber)"></div></div></div>
  <div class="stat"><div class="label">PAID MODEL YIELD</div><div class="value cyan" id="y">--</div><div class="sub" id="ys">Amendment 010</div></div>
</div>
<div class="section"><h2>OPENROUTER × CONDITION (Amendment 010 — paid models)</h2></div>
<div class="cell-grid" id="or_cells"></div>
<div class="section"><h2>DIALAGRAM × CONDITION (Original Confirmatory)</h2></div>
<div class="cell-grid" id="dia_cells"></div>
<div class="section"><h2>INTEGRITY BLOCKS</h2></div>
<div class="blocks" id="blk"></div>
<div class="footer">STUDY-011 │ Amendment 010 │ self-contained │ generated <span id="gen">--</span></div>
<script>
const DATA = __DATA__;
// totals
document.getElementById('v').textContent = DATA.total_valid;
document.getElementById('vb').style.width = Math.min(100, DATA.total_valid/464*100) + '%';
document.getElementById('a').textContent = DATA.total_records;
document.getElementById('ab').style.width = Math.min(100, DATA.total_records/931*100) + '%';
document.getElementById('y').textContent = DATA.a010_att > 0 ? Math.round(DATA.a010_valid/DATA.a010_att*100) + '%' : '--';
document.getElementById('ys').textContent = DATA.a010_records + ' records';
document.getElementById('gen').textContent = DATA.last_updated;
// cells
let done = 0;
for (const [stratum, divId] of [['openrouter','or_cells'],['dialagram','dia_cells']]) {
  const div = document.getElementById(divId);
  div.innerHTML = '';
  for (const cond of ['A','C','F','G']) {
    const key = stratum + '|' + cond;
    const d = DATA.cells[key] || {att:0,lv:0,fail:0};
    const isDone = d.lv >= 58;
    if (isDone) done++;
    const badge = isDone ? '<span class="badge done">COMPLETE</span>' :
                  d.lv > 0 ? '<span class="badge active">RUNNING</span>' :
                  d.fail > 0 ? '<span class="badge burn">429 BURN</span>' :
                  '<span class="badge pending">PENDING</span>';
    const pct = Math.min(100, Math.round(d.lv/58*100));
    const a010d = DATA.a010_cells[key] || {att:0,lv:0};
    const yld = a010d.att > 0 ? Math.round(a010d.lv/a010d.att*100) + '%' : '--';
    const barColor = isDone ? 'var(--green)' : 'var(--blue)';
    div.innerHTML += `<div class="cell-card"><div class="cell-name">${key} ${badge}</div>` +
      `<div class="nums"><div class="num valid"><div class="n">${d.lv}</div><div class="l">valid</div></div>` +
      `<div class="num fail"><div class="n">${d.fail}</div><div class="l">fail</div></div>` +
      `<div class="num att"><div class="n">${d.att}</div><div class="l">att</div></div></div>` +
      `<div class="bar-wrap"><div class="bar-label"><span>valid/58</span><span>${pct}%</span></div>` +
      `<div class="progress-bar"><div class="fill" style="width:${pct}%;background:${barColor}"></div></div></div>` +
      (stratum === 'openrouter' ? `<div class="bar-label" style="margin-top:6px"><span style="color:var(--cyan)">paid yield</span><span style="color:var(--cyan)">${yld}</span></div>` : '') +
      `</div>`;
  }
}
document.getElementById('cb').textContent = done;
document.getElementById('cb').style.width = (done/8*100) + '%';
// blocks
const blkDefs = [
  {k:'original_confirmatory', n:'Block 1: Original Confirmatory', c:'var(--green)', s:'COMPLETE (4/4)'},
  {k:'original_openrouter_free', n:'Block 2: OpenRouter :free', c:'var(--red)', s:'NON-VIABLE (429 quota)'},
  {k:'post_amendment_010', n:'Block 3: Amendment 010 (paid)', c:'var(--cyan)', s:'RUNNING (paid models)'},
];
const blkDiv = document.getElementById('blk');
blkDiv.innerHTML = '';
for (const bd of blkDefs) {
  const b = DATA.blocks[bd.k] || {records:0, valid:0, fp:'--'};
  blkDiv.innerHTML += `<div class="block-card"><div class="bt" style="color:${bd.c}">${bd.name}</div>` +
    `<div class="bp">fp: ${b.fp}</div><div class="bs">${b.records} records │ ${b.valid} valid</div>` +
    `<div class="bs" style="color:${bd.c}">${bd.status}</div></div>`;
}
</script>
</body>
</html>"""

if __name__ == "__main__":
    main()

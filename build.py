"""Netlify 建置腳本：讀取 stocks.json，產生 dist/index.html。
要增減股票只需修改 stocks.json（上市股票自動加 .TW，上櫃可寫 "suffix": "TWO"）。"""
import json
from pathlib import Path

root = Path(__file__).parent
stocks = json.loads((root / "stocks.json").read_text(encoding="utf-8"))
for s in stocks:
    s["symbol"] = f'{s["code"]}.{s.get("suffix", "TW")}'

HTML = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>安東尼查看即時個股走勢</title>
<style>
  :root { --up:#ff4b3e; --down:#22c55e; --flat:#bbb; }
  * { box-sizing: border-box; }
  body { margin:0; background:#000; color:#fff; font-family:-apple-system,"PingFang TC","Noto Sans TC",sans-serif; }
  header { padding:10px 12px; display:flex; justify-content:space-between; font-size:13px; color:#999; }
  #grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:6px; padding:0 6px 12px; }
  .card { display:flex; border:1px solid #222; background:#000; min-height:112px; }
  .info { width:46%; display:flex; flex-direction:column; }
  .head { display:flex; justify-content:space-between; align-items:center; padding:6px 8px; background:#333; font-size:18px; }
  .head small { color:#aaa; font-size:13px; }
  .price { flex:1; display:flex; align-items:center; justify-content:center; font-size:30px; font-weight:500; }
  .chg { display:flex; justify-content:space-around; padding:0 4px 6px; font-size:15px; }
  .up .price,.up .chg { color:var(--up); } .down .price,.down .chg { color:var(--down); } .flat .price,.flat .chg { color:var(--flat); }
  .limit.up .head { background:#a3231a; } .limit.up .price,.limit.up .chg { color:#fff; }
  .limit.down .head { background:#15803d; } .limit.down .price,.limit.down .chg { color:#fff; }
  .info { background:#000; } .limit.up .info { background:#6b140f; } .limit.down .info { background:#0f4a26; }
  .chart { flex:1; }
  svg { width:100%; height:100%; display:block; }
  .err { color:#f87; padding:8px; }
</style>
</head>
<body>
<header><span>安東尼的台股即時走勢（約每 15 秒更新）</span><span id="time">--:--:--</span></header>
<div id="grid"></div>
<script>
const STOCKS = __STOCKS__;
const SYMBOLS = STOCKS.map(s => s.symbol).join(",");
const grid = document.getElementById("grid");

grid.innerHTML = STOCKS.map(s => `
  <div class="card flat" id="c-${s.code}">
    <div class="info">
      <div class="head"><span>${s.name}</span><small>${s.code}</small></div>
      <div class="price">--</div>
      <div class="chg"><span>--</span><span>--</span></div>
    </div>
    <div class="chart"></div>
  </div>`).join("");

function sparkline(q) {
  const W = 220, H = 100, L = 14, R = 6, T = 6, B = 16;
  const start = q.start, end = q.end, prev = q.prev;
  const pts = q.t.map((t, i) => [t, q.c[i]]).filter(p => p[1] != null);
  let dev = Math.max(prev * 0.01, ...pts.map(p => Math.abs(p[1] - prev)));
  dev *= 1.1;
  const x = t => L + (t - start) / (end - start) * (W - L - R);
  const y = v => T + (1 - (v - (prev - dev)) / (2 * dev)) * (H - T - B);
  let g = "";
  for (let h = 9; h <= 13; h++) {
    const gx = x(start + (h - 9) * 3600);
    g += `<line x1="${gx}" y1="${T}" x2="${gx}" y2="${H - B}" stroke="#555" stroke-width="1"/>
          <text x="${gx}" y="${H - 3}" fill="#aaa" font-size="10" text-anchor="middle">${String(h).padStart(2,"0")}</text>`;
  }
  const color = q.price > prev ? "#ff4b3e" : q.price < prev ? "#22c55e" : "#bbb";
  const path = pts.map((p, i) => (i ? "L" : "M") + x(p[0]).toFixed(1) + " " + y(p[1]).toFixed(1)).join(" ");
  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">
    <rect x="${L}" y="${T}" width="${W-L-R}" height="${H-T-B}" fill="none" stroke="#555"/>
    ${g}
    <line x1="${L}" x2="${W-R}" y1="${y(prev)}" y2="${y(prev)}" stroke="#3b82f6" stroke-width="1.5"/>
    <path d="${path}" fill="none" stroke="${color}" stroke-width="1.2" vector-effect="non-scaling-stroke"/>
  </svg>`;
}

function render(q) {
  const el = document.getElementById("c-" + q.code);
  if (!el) return;
  if (q.error) { el.querySelector(".chart").innerHTML = `<div class="err">${q.error}</div>`; return; }
  const diff = q.price - q.prev, pct = diff / q.prev * 100;
  const dir = diff > 0 ? "up" : diff < 0 ? "down" : "flat";
  const limit = Math.abs(pct) >= 9.5 ? " limit" : "";
  el.className = `card ${dir}${limit}`;
  el.querySelector(".price").textContent = q.price.toFixed(2);
  const arrow = dir === "up" ? "▲" : dir === "down" ? "▼" : "–";
  const sp = el.querySelectorAll(".chg span");
  sp[0].textContent = `${arrow} ${Math.abs(diff).toFixed(2)}`;
  sp[1].textContent = `${Math.abs(pct).toFixed(2)}%`;
  el.querySelector(".chart").innerHTML = sparkline(q);
}

async function refresh() {
  try {
    const res = await fetch("/.netlify/functions/quotes?s=" + SYMBOLS);
    const data = await res.json();
    data.forEach(q => { const s = STOCKS.find(s => s.symbol === q.symbol); q.code = s.code; render(q); });
    document.getElementById("time").textContent = new Date().toLocaleTimeString("zh-TW", {hour12:false});
  } catch (e) {
    document.getElementById("time").textContent = "連線失敗";
  }
}
refresh();
setInterval(refresh, 15000);
</script>
</body>
</html>
"""

out = root / "dist"
out.mkdir(exist_ok=True)
html = HTML.replace("__STOCKS__", json.dumps(stocks, ensure_ascii=False))
(out / "index.html").write_text(html, encoding="utf-8")
print(f"已產生 {out/'index.html'}，共 {len(stocks)} 檔股票")

// Netlify Function：代理 Yahoo Finance 日內資料（避免瀏覽器 CORS 限制）
// 注意：Netlify Functions 原生不支援 Python，所以這支用 JavaScript。
const UA = "Mozilla/5.0 (compatible; StockDashboard/1.0)";
const TZ = 8 * 3600; // 台北 UTC+8

async function getJson(url, ms = 6000) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), ms);
  try {
    const r = await fetch(url, { headers: { "User-Agent": UA }, signal: ctl.signal });
    return await r.json();
  } finally { clearTimeout(timer); }
}

// 加權指數：用證交所官方的「現價 z / 昨收 y」覆蓋，避免 Yahoo 昨收基準不一致造成方向錯誤
async function twseIndex() {
  try {
    const j = await getJson("https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw&json=1&delay=0", 4000);
    const m = j.msgArray[0];
    const y = parseFloat(m.y), z = parseFloat(m.z);
    return { prev: isNaN(y) ? null : y, price: isNaN(z) ? null : z };
  } catch (e) { return null; }
}

async function fetchOne(symbol) {
  const code = symbol.split(".")[0];
  const isIndex = symbol.startsWith("^");
  try {
    const range = isIndex ? "5d" : "1d";
    const j = await getJson(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=5m&range=${range}`);
    const res = j.chart.result[0];
    const m = res.meta;
    let t = res.timestamp || [];
    let c = res.indicators.quote[0].close || [];
    let price = m.regularMarketPrice;
    let prev = m.chartPreviousClose ?? m.previousClose;
    let start = m.currentTradingPeriod.regular.start;
    let end = m.currentTradingPeriod.regular.end;

    if (isIndex && t.length) {
      // 以資料中「最新交易日」為準：切出當日資料，昨收 = 前一交易日最後一筆收盤
      const dayOf = ts => Math.floor((ts + TZ) / 86400);
      const lastDay = dayOf(t[t.length - 1]);
      const iT = [], iC = [];
      let prevClose = null;
      t.forEach((ts, i) => {
        if (c[i] == null) return;
        if (dayOf(ts) === lastDay) { iT.push(ts); iC.push(c[i]); }
        else prevClose = c[i];
      });
      if (prevClose != null) prev = prevClose;
      t = iT; c = iC;
      start = lastDay * 86400 - TZ + 9 * 3600;
      end = lastDay * 86400 - TZ + 13.5 * 3600;
      if (c.length) price = c[c.length - 1];
      const tw = await twseIndex();
      if (tw) { if (tw.prev) prev = tw.prev; if (tw.price) price = tw.price; }
    }
    return { symbol, code, price, prev, start, end, t, c };
  } catch (e) {
    return { symbol, code, error: "取得資料失敗" };
  }
}

exports.handler = async (event) => {
  const symbols = (event.queryStringParameters?.s || "").split(",").filter(Boolean).slice(0, 40);
  const data = await Promise.all(symbols.map(fetchOne));
  return {
    statusCode: 200,
    headers: { "Content-Type": "application/json", "Cache-Control": "public, max-age=10" },
    body: JSON.stringify(data),
  };
};

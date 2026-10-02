// Netlify Function：代理 Yahoo Finance 日內資料（避免瀏覽器 CORS 限制）
// 注意：Netlify Functions 原生不支援 Python，所以這支用 JavaScript。
const UA = "Mozilla/5.0 (compatible; StockDashboard/1.0)";

async function fetchOne(symbol) {
  const code = symbol.split(".")[0];
  try {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=5m&range=1d`;
    const r = await fetch(url, { headers: { "User-Agent": UA } });
    const j = await r.json();
    const res = j.chart.result[0];
    const m = res.meta;
    return {
      symbol, code,
      price: m.regularMarketPrice,
      prev: m.chartPreviousClose ?? m.previousClose,
      start: m.currentTradingPeriod.regular.start,
      end: m.currentTradingPeriod.regular.end,
      t: res.timestamp || [],
      c: res.indicators.quote[0].close || [],
    };
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

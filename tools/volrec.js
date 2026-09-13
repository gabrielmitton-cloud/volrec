/* volrec shared runtime.

   Used by index.html (the paper) and tools/monitor.html (the instrument).
   No dependencies and no build step: GitHub Pages serves this file as-is.

   What lives here and nowhere else:
   - loading and parsing the two panels, straight from the repository
   - the panel-health rules, mirrored from tools/panel_health.py so the page and
     the daily check can never disagree about what "healthy" means
   - the lognormal strike-truncation model behind the paper's first figure
   - small SVG, tooltip and telemetry-rail helpers

   The pressure test checks that the watchlists and health constants below still
   match record.py, surface.py and panel_health.py. Change them there first. */
(function (global) {
  "use strict";
  const V = {};

  V.REPO = "https://github.com/gabrielmitton-cloud/volrec";
  V.RAW = "https://raw.githubusercontent.com/gabrielmitton-cloud/volrec/main/";

  V.WATCHLIST = ["SPY", "DIA", "QQQ", "IWM", "MDY", "GLD", "SLV", "TLT", "IEF", "USO", "UNG", "FXE", "EEM", "EFA", "XLK", "XLF", "XLE", "XLV", "XLP", "XLU", "XLI", "XLY", "XLB", "XRT", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AMD", "PLTR", "COIN", "MSTR", "SMCI", "JNJ", "PG", "KO", "PEP", "WMT", "MCD", "VZ", "JPM", "BAC", "GS", "XOM", "CVX", "CAT", "BA", "UNH", "COST", "LQD", "HYG", "FXI", "XLC", "XLRE", "SMH", "XBI", "KRE", "GDX", "IBIT", "XHB", "XOP", "AVGO", "ORCL", "CRM", "ADBE", "INTC", "MU", "QCOM", "TSM", "NFLX", "CSCO", "TXN", "MS", "WFC", "C", "AXP", "SCHW", "LLY", "ABBV", "PFE", "MRK", "TMO", "HD", "NKE", "TGT", "LOW", "DIS", "GE", "DE", "LMT", "UPS", "RTX", "COP", "SLB", "OXY", "NEE", "DUK", "T", "CMCSA", "RIVN", "SOFI", "HOOD", "MARA", "RBLX", "SNOW", "CRWD"];
  V.SURFACE = ["SPY", "QQQ", "IWM", "GLD", "USO", "TSLA", "NVDA", "AAPL"];

  V.NEED_DAYS = 40;          // trading days before the premium is worth estimating
  V.SPREAD_LIMIT = 60;       // bid-ask spread, % of mid, above which a quote is flagged

  // Mirrored from tools/panel_health.py.
  V.STALE_DAYS = 5;
  V.SURFACE_START = "2026-09-14";
  V.SURFACE_LANDED_HOUR_UTC = 20;

  // Scheduled times from the workflows. GitHub delays both by ~3 hours in practice.
  V.RECORD_CRON = [15, 30];
  V.SURFACE_CRON = [15, 40];

  V.T30 = 30 / 365;
  V.calm = !!(global.matchMedia && global.matchMedia("(prefers-reduced-motion: reduce)").matches);

  const INDEX = new Set(["SPY", "DIA", "QQQ", "IWM", "MDY", "EEM", "EFA", "FXI"]);
  const SECTOR = new Set(["XLK", "XLF", "XLE", "XLV", "XLP", "XLU", "XLI", "XLY", "XLB", "XRT", "XLC", "XLRE", "SMH", "XBI", "KRE", "GDX", "XHB", "XOP"]);
  const NONEQ = new Set(["GLD", "SLV", "TLT", "IEF", "USO", "UNG", "FXE", "LQD", "HYG", "IBIT"]);
  V.GROUPS = ["index ETF", "sector ETF", "non-equity", "single name"];
  V.group = s => INDEX.has(s) ? "index ETF" : NONEQ.has(s) ? "non-equity" : SECTOR.has(s) ? "sector ETF" : "single name";

  /* ---------------------------------------------------------------- numbers */

  V.num = v => { const n = parseFloat(v); return Number.isFinite(n) ? n : null; };
  V.fx = (n, d = 2) => n == null ? "n/a" : n.toFixed(d);
  V.pct = (v, d = 1) => v == null ? "n/a" : (v * 100).toFixed(d) + "%";
  V.int = n => n == null ? "n/a" : Math.round(n).toLocaleString("en-US");
  // Signed with a true minus, and a rounding-zero printed without a sign.
  V.sgn = (n, d = 2) => {
    if (n == null) return "n/a";
    const r = Math.abs(n) < 0.5 * Math.pow(10, -d) ? 0 : n;
    return (r > 0 ? "+" : r < 0 ? "−" : "") + Math.abs(r).toFixed(d);
  };
  V.spread = r => {
    const b = V.num(r.bid), a = V.num(r.ask), m = V.num(r.mid);
    return (b === null || a === null || !m) ? null : 100 * (a - b) / m;
  };

  /* ------------------------------------------------------------------ dates */

  V.isoDay = d => d.toISOString().slice(0, 10);
  V.dayDiff = (a, b) => Math.round((Date.parse(b + "T00:00:00Z") - Date.parse(a + "T00:00:00Z")) / 864e5);
  V.days = rows => [...new Set(rows.map(r => r.date).filter(Boolean))].sort();

  // The newest quote time on the newest day, as a Date. Falls back to the
  // recorder's typical landing time if the column is empty.
  V.lastSnapshot = rows => {
    if (!rows || !rows.length) return null;
    const d = V.days(rows), newest = d[d.length - 1];
    let best = null;
    for (const r of rows) {
      if (r.date !== newest || !r.quote_time) continue;
      const q = r.quote_time.includes("T") ? r.quote_time : `${newest}T${r.quote_time}`;
      const t = Date.parse(/[Zz]|[+-]\d\d:?\d\d$/.test(q) ? q : q + "Z");
      if (Number.isFinite(t) && (best === null || t > best)) best = t;
    }
    return new Date(best !== null ? best : Date.parse(`${newest}T18:45:00Z`));
  };

  V.nextRun = function (hm, now) {
    now = now || new Date();
    const d = new Date(now.getTime());
    d.setUTCHours(hm[0], hm[1], 0, 0);
    if (d <= now) d.setUTCDate(d.getUTCDate() + 1);
    while (d.getUTCDay() === 0 || d.getUTCDay() === 6) d.setUTCDate(d.getUTCDate() + 1);
    return d;
  };

  const p2 = n => String(n).padStart(2, "0");
  V.clock = ms => {
    ms = Math.max(0, ms);
    const s = Math.floor(ms / 1000), dd = Math.floor(s / 86400);
    return (dd ? dd + "d " : "") + p2(Math.floor(s % 86400 / 3600)) + ":" + p2(Math.floor(s % 3600 / 60)) + ":" + p2(s % 60);
  };
  V.since = ms => {
    const h = Math.max(0, ms) / 36e5;
    return h < 1 ? Math.round(h * 60) + "m ago" : h < 48 ? Math.floor(h) + "h " + p2(Math.round((h % 1) * 60)) + "m ago" : Math.floor(h / 24) + "d ago";
  };
  V.utc = d => p2(d.getUTCHours()) + ":" + p2(d.getUTCMinutes()) + ":" + p2(d.getUTCSeconds()) + "Z";

  /* --------------------------------------------------------------- loading */

  V.parseCSV = function (t) {
    const L = t.trim().split(/\r?\n/);
    if (!L.length || !L[0]) return [];
    const h = L[0].split(",");
    return L.slice(1).filter(l => l.length).map(l => { const c = l.split(","), o = {}; h.forEach((k,i)=>o[k]=c[i]); return o; });
  };

  // GitHub first: raw.githubusercontent sends access-control-allow-origin: * and
  // is at most five minutes behind the last commit. The Pages copy is the
  // fallback, and only redeploys after a push. A 404 from GitHub is authoritative:
  // the file does not exist yet, which is a state, not an error.
  V.load = async function (path, rel) {
    let missing = false, error = null;
    const tries = [[V.RAW + path + "?cb=" + Date.now(), "github"], [(rel || "") + path, "pages"]];
    for (const [url, src] of tries) {
      try {
        const r = await fetch(url, { cache: "no-store" });
        if (r.status === 404) { missing = true; if (src === "github") break; continue; }
        if (!r.ok) throw new Error("HTTP " + r.status);
        return { rows: V.parseCSV(await r.text()), src };
      } catch (e) {
        error = e.message;
      }
    }
    return { rows: null, missing, error: missing ? null : error };
  };

  /* ------------------------------------------------------------------ health */

  // The same verdicts tools/panel_health.py gives, computed in the browser.
  V.health = function (atm, surf, now) {
    now = now || new Date();
    const today = V.isoDay(now), hour = now.getUTCHours(), out = {};

    if (!atm || !atm.length) {
      out.atm = { state: "fail", label: "no rows", msg: "The ATM panel has no rows." };
    } else {
      const d = V.days(atm), newest = d[d.length - 1], age = V.dayDiff(newest, today);
      out.atm = age > V.STALE_DAYS
        ? { state: "fail", label: "stale", msg: `No ATM snapshot in ${age} days. The recorder has stopped.`, age, newest, days: d }
        : { state: "ok", label: "fresh", msg: `Newest snapshot ${newest}, ${age} day${age === 1 ? "" : "s"} old.`, age, newest, days: d };
    }

    if (surf == null) {
      const undue = today < V.SURFACE_START || (today === V.SURFACE_START && hour < V.SURFACE_LANDED_HOUR_UTC);
      const late = V.dayDiff(V.SURFACE_START, today);
      out.surface = undue
        ? { state: "pend", label: "pending", msg: `Not collected yet. The first scheduled run is Monday ${V.SURFACE_START}, judged from ${V.SURFACE_LANDED_HOUR_UTC}:00 UTC that day.` }
        : { state: "fail", label: "missing", msg: `surface.csv does not exist, ${late === 0 ? "later the same day as" : late + " days after"} the first scheduled run. A green run that commits nothing looks exactly like this.` };
    } else if (!surf.length) {
      out.surface = { state: "fail", label: "empty", msg: "surface.csv exists but has no rows." };
    } else {
      const d = V.days(surf), newest = d[d.length - 1], age = V.dayDiff(newest, today);
      const keys = surf.map(r => r.date + "|" + r.option_symbol);
      const dups = keys.length - new Set(keys).size;
      const latest = new Set(surf.filter(r => r.date === newest).map(r => r.symbol));
      const missing = V.SURFACE.filter(s => !latest.has(s));
      let state = "ok", label = "fresh", msg = `Newest surface ${newest}, ${latest.size} of ${V.SURFACE.length} underlyings.`;
      if (age > V.STALE_DAYS) { state = "fail"; label = "stale"; msg = `No surface rows in ${age} days.`; }
      else if (dups) { state = "fail"; label = "duplicates"; msg = `${dups} duplicate contract rows. The append guard has regressed.`; }
      else if (latest.size * 2 < V.SURFACE.length) { state = "fail"; label = "coverage"; msg = `Only ${latest.size} of ${V.SURFACE.length} underlyings on ${newest}; missing ${missing.join(", ")}.`; }
      else if (missing.length) { state = "warn"; label = "partial"; msg = `${newest} is missing ${missing.join(", ")}. One quiet name is normal; a name absent for several days is not.`; }
      const ready = d.length >= 2 && V.dayDiff(d[d.length - 2], newest) <= 4;
      out.surface = { state, label, msg, age, newest, days: d, missing, h4ready: ready,
        h4: d.length < 2 ? `${d.length} day collected. H4 needs two consecutive.` : ready ? `${d.length} days collected. H4 is testable.` : `${d.length} days, but the newest two are too far apart to count as consecutive.` };
    }
    return out;
  };

  /* ---------------------------------------------------- the truncation model */

  // Numerical Recipes' erfc: fractional error below 1.2e-7 everywhere, including
  // the deep tails, which is where the truncation integral lives.
  function erfc(x) {
    const z = Math.abs(x), t = 1 / (1 + 0.5 * z);
    const r = t * Math.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 +
      t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 + t * (-0.82215223 + t * 0.17087277)))))))));
    return x >= 0 ? r : 2 - r;
  }
  V.N = x => 0.5 * erfc(-x / Math.SQRT2);

  // Out-of-the-money option price per unit forward, r = 0: a put below the
  // forward, a call above it. This is Q(K) in Cboe's variance formula.
  V.otm = function (K, s, T) {
    const v = s * Math.sqrt(T), d1 = (-Math.log(K) + v * v / 2) / v, d2 = d1 - v;
    return K >= 1 ? V.N(d1) - K * V.N(d2) : K * V.N(-d2) - V.N(-d1);
  };

  // Volatility Cboe's formula recovers when the strikes stop at 1-b and 1+b,
  // under a lognormal forward with no skew:
  //   sigma_b^2 = (2/T) * integral over [1-b, 1+b] of Q(K) / K^2 dK
  // Integrated in log-strike (dK/K^2 = dx/K) with Simpson's rule.
  V.truncVol = function (s, b, T, n) {
    T = T || V.T30; n = n || 1200;
    const lo = Math.log(1 - b), hi = Math.log(1 + b), h = (hi - lo) / n;
    let acc = 0;
    for (let i = 0; i <= n; i++) {
      const x = lo + i * h, K = Math.exp(x), w = (i === 0 || i === n) ? 1 : (i % 2 ? 4 : 2);
      acc += w * V.otm(K, s, T) / K;
    }
    return Math.sqrt(Math.max(0, (2 / T) * acc * h / 3));
  };

  // Density of S_T / F under the same lognormal.
  V.lognPdf = function (k, s, T) {
    const v = s * Math.sqrt(T), z = (Math.log(k) + v * v / 2) / v;
    return Math.exp(-z * z / 2) / (k * v * Math.sqrt(2 * Math.PI));
  };

  /* -------------------------------------------------------------- drawing */

  const NS = "http://www.w3.org/2000/svg";
  function apply(e, attrs) {
    for (const k in attrs || {}) {
      const v = attrs[k];
      if (v == null || v === false) continue;
      if (k === "class") e.setAttribute("class", v);
      else if (k.slice(0, 2) === "on" && typeof v === "function") e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v === true ? "" : v);
    }
    return e;
  }
  V.s = (tag, attrs, parent, text) => {
    const e = apply(document.createElementNS(NS, tag), attrs);
    if (text != null) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  };
  V.h = (tag, attrs, parent, text) => {
    const e = apply(document.createElement(tag), attrs);
    if (text != null) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  };
  V.clear = el => { while (el.firstChild) el.removeChild(el.firstChild); return el; };

  V.lin = (d0, d1, r0, r1) => {
    const k = (r1 - r0) / ((d1 - d0) || 1);
    const f = v => r0 + (v - d0) * k;
    f.inv = p => d0 + (p - r0) / k;
    return f;
  };
  V.ticks = (lo, hi, n) => {
    n = n || 5;
    const raw = ((hi - lo) || 1) / n, mag = Math.pow(10, Math.floor(Math.log10(raw))), m = raw / mag;
    const step = (m < 1.5 ? 1 : m < 3 ? 2 : m < 7 ? 5 : 10) * mag, out = [];
    for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(+v.toFixed(10));
    return out;
  };

  // An oscilloscope screen: major divisions, with the two centre axes carrying
  // five minor ticks per division. Only draw the centre axes where the centre
  // means something (the forward, on the paper's first figure).
  V.graticule = function (g, x, y, w, h, cols, rows, centre) {
    const gr = V.s("g", { class: "grat", "aria-hidden": "true" }, g);
    for (let i = 0; i <= cols; i++) {
      const px = x + w * i / cols;
      V.s("line", { x1: px, y1: y, x2: px, y2: y + h, class: centre && i * 2 === cols ? "grat-axis" : "grat-line" }, gr);
    }
    for (let j = 0; j <= rows; j++) {
      const py = y + h * j / rows;
      V.s("line", { x1: x, y1: py, x2: x + w, y2: py, class: centre && j * 2 === rows ? "grat-axis" : "grat-line" }, gr);
    }
    if (centre) {
      const cx = x + w / 2, cy = y + h / 2;
      for (let i = 1; i < cols * 5; i++) if (i % 5) {
        const px = x + w * i / (cols * 5);
        V.s("line", { x1: px, y1: cy - 3, x2: px, y2: cy + 3, class: "grat-tick" }, gr);
      }
      for (let j = 1; j < rows * 5; j++) if (j % 5) {
        const py = y + h * j / (rows * 5);
        V.s("line", { x1: cx - 3, y1: py, x2: cx + 3, y2: py, class: "grat-tick" }, gr);
      }
    }
    return gr;
  };

  V.glowFilter = function (svg, id) {
    const defs = V.s("defs", null, svg);
    const f = V.s("filter", { id, x: "-20%", y: "-40%", width: "140%", height: "180%" }, defs);
    V.s("feGaussianBlur", { in: "SourceGraphic", stdDeviation: "3.2", result: "b" }, f);
    const m = V.s("feMerge", null, f);
    V.s("feMergeNode", { in: "b" }, m);
    V.s("feMergeNode", { in: "SourceGraphic" }, m);
    return defs;
  };

  /* ------------------------------------------------------------ tooltip */

  let tipEl = null;
  function tipNode() {
    if (!tipEl) { tipEl = V.h("div", { class: "vtip", role: "status" }, document.body); tipEl.hidden = true; }
    return tipEl;
  }
  // rows: [{ v: value, k: label, c: CSS colour for the line key }]. Text only,
  // never innerHTML: labels can come from CSV headers.
  V.tipShow = function (x, y, title, rows) {
    const t = V.clear(tipNode());
    if (title) V.h("div", { class: "vtip-t" }, t, title);
    for (const r of rows || []) {
      const row = V.h("div", { class: "vtip-r" }, t);
      const key = V.h("i", { class: "vtip-k" }, row);
      if (r.c) key.style.background = r.c; else key.style.visibility = "hidden";
      V.h("b", null, row, r.v);
      V.h("span", null, row, r.k);
    }
    t.hidden = false;
    const W = t.offsetWidth, H = t.offsetHeight;
    let px = x + 16, py = y + 16;
    if (px + W > innerWidth - 8) px = x - W - 16;
    if (py + H > innerHeight - 8) py = y - H - 16;
    t.style.left = Math.max(8, px) + "px";
    t.style.top = Math.max(8, py) + "px";
  };
  V.tipHide = () => { if (tipEl) tipEl.hidden = true; };
  V.hover = function (el, content) {
    const at = e => { const c = content(); if (c) V.tipShow(e.clientX, e.clientY, c[0], c[1]); };
    el.addEventListener("pointermove", at);
    el.addEventListener("pointerleave", V.tipHide);
    el.addEventListener("focus", () => {
      const b = el.getBoundingClientRect(), c = content();
      if (c) V.tipShow(b.left + b.width / 2, b.top, c[0], c[1]);
    });
    el.addEventListener("blur", V.tipHide);
  };

  /* --------------------------------------------------------------- rail */

  // The telemetry strip across the top of both pages. It ticks every second:
  // the UTC clock, the age of the last snapshot, and the countdown to the
  // recorder's next scheduled run are what make it read as a live system.
  V.rail = function (host, opt) {
    V.clear(host);
    const here = opt.here;
    const brand = V.h("a", { class: "rail-brand", href: opt.home }, host);
    V.h("i", { class: "pulse", "data-state": opt.state }, brand);
    V.h("span", null, brand, "volrec");

    const cells = V.h("div", { class: "rail-cells" }, host);
    const cell = (k, v, attrs) => {
      const c = V.h("div", Object.assign({ class: "rail-cell" }, attrs || {}), cells);
      V.h("span", { class: "rail-k" }, c, k);
      return V.h("span", { class: "rail-v" }, c, v);
    };
    const stateText = { live: "live", stale: "stale", offline: "offline", loading: "reading" }[opt.state] || opt.state;
    cell("feed", stateText, { "data-state": opt.state });
    const snap = opt.snapshot;
    cell("panel", opt.days != null ? `${opt.days} days` : "n/a");
    cell("rows", opt.rows != null ? V.int(opt.rows) : "n/a");
    const age = cell("last snapshot", "n/a");
    const next = cell("next record", "n/a");
    if (opt.surface) cell("surface", opt.surface.label, { "data-state": opt.surface.state });
    const clk = cell("utc", "n/a", { class: "rail-cell rail-clock" });

    const nav = V.h("nav", { class: "rail-nav", "aria-label": "pages" }, host);
    for (const [label, href, key] of opt.links) {
      const a = V.h("a", { href }, nav, label);
      if (key === here) a.setAttribute("aria-current", "page");
    }

    const tick = () => {
      const now = new Date();
      clk.textContent = V.utc(now);
      age.textContent = snap ? V.since(now - snap) : "n/a";
      next.textContent = "T−" + V.clock(V.nextRun(V.RECORD_CRON, now) - now);
    };
    tick();
    clearInterval(host._tick);
    host._tick = setInterval(tick, 1000);
  };

  global.V = V;
})(window);

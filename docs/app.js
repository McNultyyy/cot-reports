'use strict';

/* ── Palette (validated data-viz reference palette) ─────────────────────── */
const PAL = {
  light: {
    cat: ['#2a78d6', '#1baf7a', '#eda100', '#008300', '#4a3aa7', '#e34948', '#e87ba4', '#eb6834'],
    pos: '#2a78d6', neg: '#e34948',
    text1: '#0b0b0b', text2: '#52514e', muted: '#898781',
    grid: '#e1e0d9', baseline: '#c3c2b7', surface: '#fcfcfb',
    warning: '#fab219', critical: '#d03b3b',
  },
  dark: {
    cat: ['#3987e5', '#199e70', '#c98500', '#008300', '#9085e9', '#e66767', '#d55181', '#d95926'],
    pos: '#3987e5', neg: '#e66767',
    text1: '#ffffff', text2: '#c3c2b7', muted: '#898781',
    grid: '#2c2c2a', baseline: '#383835', surface: '#1a1a19',
    warning: '#fab219', critical: '#d03b3b',
  },
};

/* Smart-money & hedger category per report family (for tiles / defaults). */
const SMART = { legacy: 'Non-Commercial', tff: 'Leveraged', disagg: 'Managed Money' };
const REPORT_LABEL = { legacy: 'Legacy', tff: 'Fin. Futures (TFF)', disagg: 'Disaggregated' };

const CHART_GROUP = 'cot';
const state = {
  index: null,
  inst: null,          // loaded per-instrument record
  report: 'legacy',
  window: 52,
  charts: [],          // active ECharts instances
};

/* ── Theme ──────────────────────────────────────────────────────────────── */
function currentMode() {
  const t = document.documentElement.dataset.theme;
  if (t === 'dark') return 'dark';
  if (t === 'light') return 'light';
  return matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}
function pal() { return PAL[currentMode()]; }

function setTheme(mode) {
  document.documentElement.dataset.theme = mode;
  try { localStorage.setItem('cot-theme', mode); } catch (_) {}
  if (state.inst) renderCharts();          // re-theme open charts
}
document.getElementById('theme-toggle').addEventListener('click', () => {
  const next = currentMode() === 'dark' ? 'light' : 'dark';
  setTheme(next);
});

/* ── Number formatting ──────────────────────────────────────────────────── */
const fmt = new Intl.NumberFormat('en-US');
const sign = (n) => (n > 0 ? '+' : '') + fmt.format(n);
function compact(n) {
  const a = Math.abs(n);
  if (a >= 1e6) return (n / 1e6).toFixed(a >= 1e7 ? 0 : 1) + 'M';
  if (a >= 1e3) return (n / 1e3).toFixed(a >= 1e4 ? 0 : 1) + 'k';
  return String(n);
}

/* ── Boot ───────────────────────────────────────────────────────────────── */
(async function init() {
  const params = new URLSearchParams(location.search);
  const themeParam = params.get('theme');
  if (themeParam === 'dark' || themeParam === 'light') {
    document.documentElement.dataset.theme = themeParam;
  } else {
    try { const t = localStorage.getItem('cot-theme'); if (t) document.documentElement.dataset.theme = t; } catch (_) {}
  }

  const res = await fetch('./data/index.json');
  state.index = await res.json();

  document.getElementById('latest-date').textContent = state.index.latest_report_date || '—';
  document.getElementById('gen-time').textContent = (state.index.generated || '').replace('T', ' ').replace('Z', ' UTC');

  renderOverview();
  wireSearch();
  window.addEventListener('resize', () => state.charts.forEach((c) => c.resize()));
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (!document.documentElement.dataset.theme && state.inst) renderCharts();
  });
  window.addEventListener('hashchange', routeFromHash);
  routeFromHash();
})();

/* Deep-link support: #TICKER opens that market's detail view. */
function routeFromHash() {
  const t = decodeURIComponent(location.hash.replace(/^#/, '')).toUpperCase();
  if (t && state.index.instruments.some((i) => i.ticker === t)) {
    if (!state.inst || state.inst.ticker !== t) openDetail(t);
  } else if (!t && state.inst) {
    showOverview();
  }
}

/* ── Overview ───────────────────────────────────────────────────────────── */
function zClass(z) {
  const a = Math.abs(z);
  if (a >= 2) return { cls: 'alert', label: `z ${z >= 0 ? '+' : ''}${z.toFixed(1)}` };
  if (a >= 1) return { cls: 'warn', label: `z ${z >= 0 ? '+' : ''}${z.toFixed(1)}` };
  return { cls: 'calm', label: `z ${z >= 0 ? '+' : ''}${z.toFixed(1)}` };
}

function renderOverview() {
  const grid = document.getElementById('grid');
  grid.innerHTML = '';
  const byGroup = new Map();
  for (const it of state.index.instruments) {
    if (!byGroup.has(it.group)) byGroup.set(it.group, []);
    byGroup.get(it.group).push(it);
  }
  const order = state.index.group_order || [...byGroup.keys()];
  for (const g of order) {
    const items = byGroup.get(g);
    if (!items) continue;
    const head = document.createElement('div');
    head.className = 'group-head';
    head.textContent = g;
    grid.appendChild(head);

    const wrap = document.createElement('div');
    wrap.className = 'cards';
    for (const it of items) wrap.appendChild(card(it));
    grid.appendChild(wrap);
  }
}

function card(it) {
  const s = it.summary || { net: 0, wow: 0, z: 0 };
  const el = document.createElement('button');
  el.className = 'card';
  el.dataset.search = (it.ticker + ' ' + it.name).toLowerCase();
  const zc = zClass(s.z);
  const up = s.wow >= 0;
  el.innerHTML = `
    <div class="card-top">
      <span class="card-tick">${it.ticker}</span>
      <span class="card-name">${it.name}</span>
    </div>
    <div>
      <div class="card-net">${compact(s.net)}</div>
      <div class="card-cat">spec net · contracts</div>
    </div>
    <div class="card-bot">
      <span class="delta ${up ? 'up' : 'down'}">${up ? '▲' : '▼'} ${sign(s.wow)}</span>
      <span class="badge ${zc.cls}"><span class="dot"></span>${zc.label}</span>
    </div>`;
  el.addEventListener('click', () => openDetail(it.ticker));
  return el;
}

function wireSearch() {
  const box = document.getElementById('search');
  box.addEventListener('input', () => {
    const q = box.value.trim().toLowerCase();
    const inDetail = !document.getElementById('detail').hidden;
    if (inDetail && q) showOverview();
    document.querySelectorAll('.card').forEach((c) => {
      c.style.display = !q || c.dataset.search.includes(q) ? '' : 'none';
    });
    // hide empty group headers
    document.querySelectorAll('#grid .cards').forEach((w) => {
      const anyVisible = [...w.children].some((c) => c.style.display !== 'none');
      w.previousElementSibling.style.display = anyVisible ? '' : 'none';
    });
  });
}

/* ── Detail ─────────────────────────────────────────────────────────────── */
function showOverview() {
  document.getElementById('detail').hidden = true;
  document.getElementById('overview').hidden = false;
  disposeCharts();
  state.inst = null;
  history.replaceState(null, '', location.pathname + location.search);
}
document.getElementById('back').addEventListener('click', showOverview);

async function openDetail(ticker) {
  const res = await fetch(`./data/${ticker}.json`);
  state.inst = await res.json();
  state.report = state.inst.reports.legacy ? 'legacy' : Object.keys(state.inst.reports)[0];

  document.getElementById('overview').hidden = true;
  document.getElementById('detail').hidden = false;
  document.getElementById('search').value = '';
  window.scrollTo(0, 0);

  document.getElementById('d-name').textContent = `${state.inst.ticker} · ${state.inst.name}`;
  document.getElementById('d-meta').textContent = `${state.inst.group} · ${state.inst.market}`;
  if (decodeURIComponent(location.hash.replace(/^#/, '')).toUpperCase() !== ticker) {
    history.replaceState(null, '', '#' + ticker);
  }

  renderTabs();
  renderReport();
}

function renderTabs() {
  const box = document.getElementById('report-tabs');
  box.innerHTML = '';
  for (const r of Object.keys(REPORT_LABEL)) {
    if (!state.inst.reports[r]) continue;
    const b = document.createElement('button');
    b.className = 'tab';
    b.textContent = REPORT_LABEL[r];
    b.setAttribute('role', 'tab');
    b.setAttribute('aria-selected', String(r === state.report));
    b.addEventListener('click', () => { state.report = r; renderReport(); });
    box.appendChild(b);
  }
}

function cats() { return state.inst.reports[state.report].categories; }
function catNames() { return Object.keys(cats()); }

function renderReport() {
  document.querySelectorAll('#report-tabs .tab').forEach((t) => {
    t.setAttribute('aria-selected', String(t.textContent === REPORT_LABEL[state.report]));
  });

  // category selector (for z-score & pct focus)
  const sel = document.getElementById('cat-select');
  const names = catNames();
  const preferred = SMART[state.report] && names.includes(SMART[state.report]) ? SMART[state.report] : names[0];
  sel.innerHTML = names.map((n) => `<option ${n === preferred ? 'selected' : ''}>${n}</option>`).join('');
  sel.onchange = () => renderCharts();

  const win = document.getElementById('win-select');
  win.value = String(state.window);
  win.onchange = () => { state.window = +win.value; renderCharts(); };

  // date jump
  const rep = state.inst.reports[state.report];
  const ds = document.getElementById('date-select');
  ds.innerHTML = rep.dates.map((d, i) => `<option value="${i}">${d}</option>`).join('');
  ds.value = String(rep.dates.length - 1);
  ds.onchange = () => { updateSnapshot(+ds.value); markDate(+ds.value); };

  renderTiles();
  renderCharts();
  updateSnapshot(rep.dates.length - 1);
}

/* Weekly change z-score for one category's net series. */
function zScores(net, window) {
  const chg = net.map((v, i) => (i ? v - net[i - 1] : 0));
  const z = new Array(net.length).fill(null);
  for (let i = 1; i < net.length; i++) {
    const start = Math.max(1, i - window + 1);
    const win = chg.slice(start, i + 1);
    const m = win.reduce((a, b) => a + b, 0) / win.length;
    const sd = Math.sqrt(win.reduce((a, b) => a + (b - m) ** 2, 0) / win.length);
    z[i] = sd > 0 ? (chg[i] - m) / sd : 0;
  }
  return { chg, z };
}

function renderTiles() {
  const box = document.getElementById('tiles');
  const c = cats(); const names = catNames(); const p = pal();
  box.innerHTML = '';
  names.forEach((name, i) => {
    const net = c[name].net;
    const cur = net[net.length - 1];
    const prev = net[net.length - 2] ?? cur;
    const wow = cur - prev;
    const color = p.cat[i % p.cat.length];
    const t = document.createElement('div');
    t.className = 'tile';
    t.innerHTML = `
      <div class="t-lab"><span class="swatch" style="background:${color}"></span>${name}</div>
      <div class="t-val" style="color:${cur >= 0 ? 'inherit' : 'var(--critical)'}">${sign(cur).replace('+', '')}</div>
      <div class="t-sub">${wow >= 0 ? '▲' : '▼'} ${sign(wow)} wk · net long−short</div>`;
    box.appendChild(t);
  });
}

/* ── Charts ─────────────────────────────────────────────────────────────── */
function disposeCharts() {
  state.charts.forEach((c) => c.dispose());
  state.charts = [];
}
function mkChart(id) {
  const el = document.getElementById(id);
  const inst = echarts.init(el, null, { renderer: 'canvas' });
  inst.group = CHART_GROUP;
  state.charts.push(inst);
  return inst;
}

function baseGrid() { return { left: 58, right: 18, top: 28, bottom: 64 }; }
function axisCommon(p) {
  return {
    axisLine: { lineStyle: { color: p.baseline } },
    axisLabel: { color: p.muted, fontSize: 11 },
    splitLine: { lineStyle: { color: p.grid } },
    axisTick: { show: false },
  };
}
function dataZoom(p) {
  return [
    { type: 'inside', xAxisIndex: 0 },
    { type: 'slider', xAxisIndex: 0, height: 20, bottom: 20, borderColor: p.grid,
      fillerColor: currentMode() === 'dark' ? 'rgba(57,135,229,0.16)' : 'rgba(42,120,214,0.12)',
      handleStyle: { color: p.surface, borderColor: p.baseline },
      moveHandleStyle: { color: p.baseline },
      dataBackground: { lineStyle: { color: p.grid }, areaStyle: { color: p.grid } },
      textStyle: { color: p.muted, fontSize: 10 } },
  ];
}
function tooltipBox(p) {
  return {
    trigger: 'axis',
    backgroundColor: p.surface,
    borderColor: p.grid,
    textStyle: { color: p.text1, fontSize: 12 },
    valueFormatter: (v) => (v == null ? '—' : fmt.format(Math.round(v))),
  };
}

/* Invisible series whose only job is to host the "selected date" vertical line,
   so updating the marker never clobbers a real series' own markLine. */
function markerSeries(p) {
  return {
    type: 'line', data: [], silent: true, legendHoverLink: false, tooltip: { show: false },
    markLine: { silent: true, symbol: 'none', animation: false, label: { show: false },
      lineStyle: { color: p.text2, width: 1, opacity: 0.5 }, data: [] },
  };
}

function renderCharts() {
  disposeCharts();
  const p = pal();
  const rep = state.inst.reports[state.report];
  const dates = rep.dates;
  const c = cats(); const names = catNames();
  const focus = document.getElementById('cat-select').value || names[0];
  document.getElementById('cap-z').textContent = `${focus} — weekly change z-score`;

  /* 1 — Net positions by category (lines) */
  const net = mkChart('chart-net');
  const netSeries = names.map((name, i) => ({
    name, type: 'line', showSymbol: false, symbol: 'circle', symbolSize: 7,
    lineStyle: { width: 2, color: p.cat[i % p.cat.length] },
    itemStyle: { color: p.cat[i % p.cat.length] },
    emphasis: { focus: 'series' },
    markLine: i === 0 ? { silent: true, symbol: 'none', lineStyle: { color: p.baseline, type: 'dashed', width: 1 },
      data: [{ yAxis: 0 }], label: { show: false } } : undefined,
    data: c[name].net,
  }));
  net.__markerIdx = netSeries.length;
  net.setOption({
    grid: baseGrid(),
    legend: { top: 0, data: names, textStyle: { color: p.text2, fontSize: 12 }, itemWidth: 14, itemHeight: 8 },
    tooltip: tooltipBox(p),
    xAxis: { type: 'category', data: dates, boundaryGap: false, ...axisCommon(p) },
    yAxis: { type: 'value', name: 'net contracts', nameTextStyle: { color: p.muted, fontSize: 11 },
             axisLabel: { color: p.muted, fontSize: 11, formatter: compact }, splitLine: { lineStyle: { color: p.grid } },
             axisLine: { show: false } },
    dataZoom: dataZoom(p),
    series: [...netSeries, markerSeries(p)],
  });

  /* 2 — Weekly change z-score (diverging bars) for focus category */
  const { z } = zScores(c[focus].net, state.window);
  const zc = mkChart('chart-z');
  zc.__markerIdx = 1;
  zc.setOption({
    grid: { ...baseGrid(), left: 46 },
    tooltip: { ...tooltipBox(p), valueFormatter: (v) => (v == null ? '—' : (+v).toFixed(2)) },
    xAxis: { type: 'category', data: dates, boundaryGap: true, ...axisCommon(p) },
    yAxis: { type: 'value', axisLabel: { color: p.muted, fontSize: 11 }, splitLine: { lineStyle: { color: p.grid } }, axisLine: { show: false } },
    dataZoom: dataZoom(p),
    series: [{
      name: 'z-score', type: 'bar',
      data: z.map((v) => ({ value: v, itemStyle: { color: v == null ? p.muted : (v >= 0 ? p.pos : p.neg) } })),
      markLine: { silent: true, symbol: 'none', label: { color: p.muted, fontSize: 10, formatter: (d) => (d.value > 0 ? '+2σ' : '−2σ') },
        lineStyle: { color: p.warning, type: 'dashed', width: 1 }, data: [{ yAxis: 2 }, { yAxis: -2 }] },
    }, markerSeries(p)],
  });

  /* 3 — Net as % of open interest (lines) */
  const oi = rep.oi;
  const pctChart = mkChart('chart-pct');
  const pctSeries = names.map((name, i) => ({
    name, type: 'line', showSymbol: false, lineStyle: { width: 2, color: p.cat[i % p.cat.length] },
    itemStyle: { color: p.cat[i % p.cat.length] }, emphasis: { focus: 'series' },
    data: c[name].net.map((v, k) => (oi[k] ? +(v / oi[k] * 100).toFixed(2) : null)),
  }));
  pctChart.__markerIdx = pctSeries.length;
  pctChart.setOption({
    grid: baseGrid(),
    legend: { top: 0, data: names, textStyle: { color: p.text2, fontSize: 11 }, itemWidth: 14, itemHeight: 8 },
    tooltip: { ...tooltipBox(p), valueFormatter: (v) => (v == null ? '—' : (+v).toFixed(1) + '%') },
    xAxis: { type: 'category', data: dates, boundaryGap: false, ...axisCommon(p) },
    yAxis: { type: 'value', axisLabel: { color: p.muted, fontSize: 11, formatter: '{value}%' }, splitLine: { lineStyle: { color: p.grid } }, axisLine: { show: false } },
    dataZoom: dataZoom(p),
    series: [...pctSeries, markerSeries(p)],
  });

  /* 4 — Open interest (area) */
  const oiChart = mkChart('chart-oi');
  oiChart.__markerIdx = 1;
  oiChart.setOption({
    grid: baseGrid(),
    tooltip: tooltipBox(p),
    xAxis: { type: 'category', data: dates, boundaryGap: false, ...axisCommon(p) },
    yAxis: { type: 'value', axisLabel: { color: p.muted, fontSize: 11, formatter: compact }, splitLine: { lineStyle: { color: p.grid } }, axisLine: { show: false } },
    dataZoom: dataZoom(p),
    series: [{
      name: 'open interest', type: 'line', showSymbol: false,
      lineStyle: { width: 2, color: p.cat[0] }, itemStyle: { color: p.cat[0] },
      areaStyle: { color: currentMode() === 'dark' ? 'rgba(57,135,229,0.18)' : 'rgba(42,120,214,0.12)' },
      data: oi,
    }, markerSeries(p)],
  });

  echarts.connect(CHART_GROUP);
  const di = +document.getElementById('date-select').value;
  markDate(isNaN(di) ? dates.length - 1 : di);
}

/* Vertical marker for a chosen report date across all charts. Updates only the
   dedicated marker series so each chart keeps its own markLines intact. */
function markDate(idx) {
  const rep = state.inst.reports[state.report];
  const x = rep.dates[idx];
  state.charts.forEach((ch) => {
    const mi = ch.__markerIdx || 0;
    const series = [];
    for (let k = 0; k < mi; k++) series.push({});
    series.push({ markLine: { data: [{ xAxis: x }] } });
    ch.setOption({ series }, false, true);
  });
}

/* ── Snapshot table ─────────────────────────────────────────────────────── */
function updateSnapshot(idx) {
  const rep = state.inst.reports[state.report];
  const c = cats(); const names = catNames(); const p = pal();
  document.getElementById('snap-date').textContent = rep.dates[idx];
  document.getElementById('date-select').value = String(idx);
  const oi = rep.oi[idx] || 0;
  const tb = document.querySelector('#snap-table tbody');
  tb.innerHTML = names.map((name, i) => {
    const s = c[name];
    const net = s.net[idx];
    const wow = idx > 0 ? net - s.net[idx - 1] : 0;
    const pct = oi ? (net / oi * 100).toFixed(1) + '%' : '—';
    const color = p.cat[i % p.cat.length];
    return `<tr>
      <td class="cat"><span class="swatch" style="background:${color}"></span>${name}</td>
      <td>${fmt.format(s.long[idx])}</td>
      <td>${fmt.format(s.short[idx])}</td>
      <td class="${net >= 0 ? 'num-pos' : 'num-neg'}">${sign(net)}</td>
      <td class="${wow >= 0 ? 'num-pos' : 'num-neg'}">${sign(wow)}</td>
      <td>${pct}</td>
    </tr>`;
  }).join('') +
    `<tr><td class="cat" style="color:var(--muted)">Open interest</td><td colspan="5" style="text-align:left;color:var(--muted)">${fmt.format(oi)} contracts</td></tr>`;
}

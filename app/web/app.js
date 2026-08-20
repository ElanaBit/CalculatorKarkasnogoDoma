'use strict';

/* ============================= Состояние ============================= */
const state = {
  data: null,
  items: [],
  params: { area: 120, tier: 'base' },
  filters: { search: '', status: 'all', type: 'all' },
  totals: null,
  sourceFile: null,
  displayedTotal: 0,
};

const $ = (s, r) => (r || document).querySelector(s);
const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));

const FMT = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });
const money = (v) => FMT.format(Math.round(v || 0)) + ' ₽';

function fmtCompact(v) {
  v = v || 0;
  if (v >= 1e9) return (v / 1e9).toLocaleString('ru-RU', { maximumFractionDigits: 2 }) + ' млрд ₽';
  if (v >= 1e6) return (v / 1e6).toLocaleString('ru-RU', { maximumFractionDigits: 2 }) + ' млн ₽';
  if (v >= 1e3) return (v / 1e3).toLocaleString('ru-RU', { maximumFractionDigits: 1 }) + ' тыс. ₽';
  return money(v);
}

const isPercent = (it) => (it.unit || '').toLowerCase().includes('%');

const STATUS_GROUPS = ['Обязательно', 'Вариант', 'Опция', 'Рекомендуется'];
const TYPE_GROUPS = ['Материал', 'Работа', 'Материал + работа', 'Комплект', 'Оборудование', 'Услуга'];

/* ============================= Тосты ============================= */
function toast(msg, kind) {
  const box = $('#toast-container');
  const el = document.createElement('div');
  el.className = 'toast ' + (kind || '');
  el.textContent = msg;
  box.appendChild(el);
  setTimeout(() => {
    el.classList.add('out');
    setTimeout(() => el.remove(), 320);
  }, 3600);
}

/* ============================= Данные ============================= */
function whenBridgeReady(timeoutMs) {
  return new Promise((resolve) => {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.init) return resolve(true);
    let done = false;
    const finish = (v) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      window.removeEventListener('pywebviewready', onReady);
      resolve(v);
    };
    const onReady = () => finish(true);
    window.addEventListener('pywebviewready', onReady);
    const timer = setTimeout(
      () => finish(!!(window.pywebview && window.pywebview.api && window.pywebview.api.init)),
      timeoutMs
    );
  });
}

async function init() {
  bindEvents();
  let data = null;
  try {
    const bridge = await whenBridgeReady(1200);
    if (bridge) {
      const res = await window.pywebview.api.init();
      data = res.data;
      state.sourceFile = res.source_file || null;
    } else {
      const resp = await fetch('/data.json');
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      data = await resp.json();
      state.sourceFile = data.meta && data.meta.source_file || null;
    }
    if (data && data.items && data.items.length) {
      applyData(data);
      buildItems(true);
      toast('Справочник загружен. Нажмите «Начать расчет», чтобы приступить.');
    } else {
      state.data = null;
      state.items = [];
      toast('Справочник не загружен. Нажмите «Загрузить данные» и выберите файл прайса (xlsx).');
    }
  } catch (err) {
    console.error(err);
    state.data = null;
    state.items = [];
    toast('Не удалось загрузить данные: ' + (err && err.message), 'err');
  }
  renderAll();
  updateDataChip();
}

function applyData(data) {
  state.data = data;
  state.items = [];
  state.params.tier = 'base';
}

/* ============================= Построение позиций ============================= */
function defaultQty(it) {
  const u = (it.unit || '').toLowerCase();
  if (u.includes('м² площади')) return state.params.area;
  if (isPercent(it)) return 1;
  if (['дом', 'объект', 'участок', 'проект', 'комплект'].some((w) => u.includes(w))) return 1;
  return 0;
}

function buildCalc(it, withQty) {
  const price = it[state.params.tier] || it.base || it.min || it.max || 0;
  return {
    it,
    included: withQty ? it.status === 'Обязательно' : false,
    tier: state.params.tier,
    price,
    qty: withQty ? defaultQty(it) : 0,
    amount: 0,
  };
}

function buildItems(withDefaults) {
  state.items = state.data.items.map((it) => buildCalc(it, withDefaults));
}

/* ============================= Расчёт ============================= */
function computeTotals() {
  const perSection = {};
  const perSectionCount = {};
  let baseSum = 0;
  let includedCount = 0;

  for (const c of state.items) {
    c.amount = 0;
    if (!c.included) continue;
    includedCount++;
    if (isPercent(c.it)) continue;
    const amt = (c.qty || 0) * (c.price || 0);
    c.amount = amt;
    baseSum += amt;
    const sec = c.it.section || 'Прочее';
    perSection[sec] = (perSection[sec] || 0) + amt;
    perSectionCount[sec] = (perSectionCount[sec] || 0) + 1;
  }

  for (const c of state.items) {
    if (!c.included || !isPercent(c.it)) continue;
    const amt = ((c.price || 0) / 100) * baseSum;
    c.amount = amt;
    const sec = c.it.section || 'Прочее';
    perSection[sec] = (perSection[sec] || 0) + amt;
    perSectionCount[sec] = (perSectionCount[sec] || 0) + 1;
  }

  const grand = Object.values(perSection).reduce((s, v) => s + v, 0);

  const tiers = { min: 0, base: 0, max: 0 };
  for (const c of state.items) {
    if (!c.included) continue;
    for (const t of ['min', 'base', 'max']) {
      let v;
      if (isPercent(c.it)) v = ((c.it[t] || 0) / 100) * baseSum;
      else v = (c.qty || 0) * (c.it[t] || 0);
      tiers[t] += v;
    }
  }

  return { grand, baseSum, perSection, perSectionCount, tiers, includedCount };
}

/* ============================= Рендер ============================= */
function renderAll() {
  if (!state.data || !state.items.length) {
    const c = $('#sections-container');
    if (c) c.innerHTML =
      '<div class="no-match empty-state">' +
      '<div class="empty-icon">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8M8 17h5"/></svg>' +
      '</div>' +
      '<div class="empty-title">Справочник позиций не загружен</div>' +
      '<div class="empty-sub">Нажмите кнопку «Загрузить данные» в правом верхнем углу и выберите файл прайса (xlsx), чтобы выполнить расчёт.</div>' +
      '<button class="btn btn-primary" id="btn-empty-load">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M17 8l-5-5-5 5"/><path d="M12 3v12"/></svg>' +
      'Загрузить данные' +
      '</button>' +
      '</div>';
    $('#tier-min b').textContent = '0 ₽';
    $('#tier-base b').textContent = '0 ₽';
    $('#tier-max b').textContent = '0 ₽';
    $('#total-range').textContent = '';
    $('#total-info').textContent = 'Позиций: 0 · Включено: 0';
    $('#total-amount').textContent = '0 ₽';
    return;
  }
  renderChips();
  renderNav();
  renderSections();
  renderControls();
  renderTotal();
  renderMiniStats();
  updateDataChip();
}

function renderChips() {
  const sf = $('#status-filters');
  sf.innerHTML =
    '<span class="chip-row-label">Статус</span>' +
    chip('all', 'Все', state.filters.status === 'all', 'sf') +
    STATUS_GROUPS.map((s) => chip(s, s, state.filters.status === s, 'sf')).join('') +
    chip('other', 'Прочее', state.filters.status === 'other', 'sf');

  const tf = $('#type-filters');
  tf.innerHTML =
    '<span class="chip-row-label">Тип</span>' +
    chip('all', 'Все типы', state.filters.type === 'all', 'tf') +
    TYPE_GROUPS.map((t) => chip(t, t, state.filters.type === t, 'tf')).join('') +
    chip('other', 'Прочее', state.filters.type === 'other', 'tf');

  function chip(val, label, active, grp) {
    return '<button class="chip small' + (active ? ' active' : '') + '" data-grp="' + grp + '" data-val="' + val + '">' + label + '</button>';
  }
}

function matchItem(c) {
  const it = c.it;
  const q = state.filters.search.trim().toLowerCase();
  if (q) {
    const hay = (it.name + ' ' + (it.subsection || '') + ' ' + (it.unit || '') + ' ' + (it.comment || '')).toLowerCase();
    if (!hay.includes(q)) return false;
  }
  const st = state.filters.status;
  if (st === 'other') {
    if (STATUS_GROUPS.includes(it.status)) return false;
  } else if (st !== 'all' && it.status !== st) {
    return false;
  }
  const tp = state.filters.type;
  if (tp === 'other') {
    if (TYPE_GROUPS.includes(it.type)) return false;
  } else if (tp !== 'all' && it.type !== tp) {
    return false;
  }
  return true;
}

function iconCheck() {
  return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>';
}

function chevronSvg() {
  return '<svg class="chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></svg>';
}

function renderSections() {
  const container = $('#sections-container');
  const matched = state.items.filter(matchItem);

  if (!matched.length) {
    container.innerHTML = '<div class="no-match">По заданным фильтрам ничего не найдено.</div>';
    renderNav();
    return;
  }

  const groups = {};
  for (const c of matched) {
    const sec = c.it.section || 'Прочее';
    (groups[sec] = groups[sec] || []).push(c);
  }

  let html = '';
  for (const sec of state.data.sections) {
    if (!groups[sec]) continue;
    html += sectionCard(sec, groups[sec]);
  }
  // любые секции, отсутствующие в списке (например из загруженного прайса)
  for (const sec in groups) {
    if (state.data.sections.includes(sec)) continue;
    html += sectionCard(sec, groups[sec]);
  }
  container.innerHTML = html;
  updateSectionSums(state.totals || computeTotals());
  renderNav();
}

function sectionCard(sec, items) {
  const rows = items.map((c) => itemRow(c)).join('');
  const open = items.some((c) => c.included);
  return (
    '<section class="section-card' + (open ? ' open' : '') + '" data-section-name="' + esc(sec) + '" style="scroll-margin-top:96px">' +
    '<div class="section-head">' +
    chevronSvg() +
    '<div class="section-title">' + esc(sec) + '</div>' +
    '<div class="section-actions">' +
    '<button class="btn btn-ghost" data-action="sec-all">Все</button>' +
    '<button class="btn btn-ghost" data-action="sec-none">Снять</button>' +
    '</div>' +
    '<div class="section-sum"><span class="sec-amt">0 ₽</span></div>' +
    '</div>' +
    '<div class="section-body"><div class="section-body-inner">' + rows + '</div></div>' +
    '</section>'
  );
}

function itemRow(c) {
  const it = c.it;
  const pct = isPercent(it);
  const id = state.items.indexOf(c);
  const statusB = it.status
    ? '<span class="badge status-' + esc(it.status) + '">' + esc(it.status) + '</span>'
    : '';
  const metaParts = [it.unit || '', it.type || ''].filter(Boolean);
  const qtyCell = pct
    ? '<div class="item-qty"><input class="num-input qty" type="number" data-id="' + id + '" value="' + (c.qty || 1) + '" readonly><span class="unit">%</span></div>'
    : '<div class="item-qty"><input class="num-input qty" type="number" min="0" step="any" data-id="' + id + '" value="' + (c.qty || 0) + '"><span class="unit">' + esc(it.unit || '') + '</span></div>';

  return (
    '<div class="item ' + (c.included ? 'included' : 'excluded') + '" data-idx="' + id + '">' +
    '<label class="ck"><input type="checkbox" class="inc" data-id="' + id + '"' + (c.included ? ' checked' : '') + '><span class="box">' + iconCheck() + '</span></label>' +
    '<div class="item-main">' +
    '<div class="item-name">' + esc(it.name) + statusB + '</div>' +
    '<div class="item-meta">' + esc(metaParts.join(' · ')) + (it.comment ? '<span class="sep-dot">•</span>' + esc(it.comment) : '') + '</div>' +
    '</div>' +
    qtyCell +
    '<div class="item-price">' +
    '<input class="num-input price" type="number" min="0" step="any" data-id="' + id + '" value="' + (c.price || 0) + '">' +
    '<select class="tier-sel" data-id="' + id + '">' +
    '<option value="min"' + (c.tier === 'min' ? ' selected' : '') + '>Мин</option>' +
    '<option value="base"' + (c.tier === 'base' ? ' selected' : '') + '>База</option>' +
    '<option value="max"' + (c.tier === 'max' ? ' selected' : '') + '>Макс</option>' +
    '<option value="custom"' + (c.tier === 'custom' ? ' selected' : '') + '>Своя</option>' +
    '</select>' +
    '</div>' +
    '<div class="item-amount" data-amount="' + id + '">' + money(c.amount) + '</div>' +
    '</div>'
  );
}

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function updateSectionSums(totals) {
  for (const el of $$('.section-card')) {
    const sec = el.dataset.sectionName;
    if (sec == null) continue;
    const sum = totals.perSection[sec] || 0;
    const sumEl = $('.section-sum', el);
    if (sumEl) $('.sec-amt', sumEl).textContent = money(sum);
  }
}

function renderNav() {
  const nav = $('#sections-nav');
  let html = '';
  state.data.sections.forEach((sec) => {
    const count = state.items.filter((c) => c.it.section === sec).length;
    const inc = state.items.filter((c) => c.it.section === sec && c.included).length;
    html +=
      '<div class="nav-item" data-nav="' + esc(sec) + '">' +
      '<span>' + esc(sec) + '</span>' +
      '<span class="nav-count">' + inc + '/' + count + '</span>' +
      '</div>';
  });
  nav.innerHTML = html;
}

function renderControls() {
  const el = $('#controls-list');
  if (!state.data.controls || !state.data.controls.length) {
    el.innerHTML = '<div class="hint">Контрольные бюджеты не загружены.</div>';
    return;
  }
  el.innerHTML = state.data.controls.map((c) =>
    '<div class="control-card" data-area="' + (c.area || 0) + '">' +
    '<div class="ctrl-name">' + esc(c.scenario) + '</div>' +
    '<div class="ctrl-area">' + (c.area ? c.area + ' м²' : '') + '</div>' +
    '<div class="ctrl-price">' + money(c.min) + ' – ' + money(c.max) + '</div>' +
    (c.comment ? '<div class="ctrl-note">' + esc(c.comment) + '</div>' : '') +
    '</div>'
  ).join('');
}

function renderMiniStats() {
  $('#stat-items').textContent = state.items.length;
  const t = state.totals || computeTotals();
  $('#stat-included').textContent = t.includedCount;
  $('#stat-sections').textContent = (state.data.sections || []).length;
}

function renderTotal() {
  const t = computeTotals();
  state.totals = t;
  const amountEl = $('#total-amount');
  animateAmount(amountEl, t.grand);
  $('#total-range').textContent = 'Диапазон: ' + fmtCompact(t.tiers.min) + ' – ' + fmtCompact(t.tiers.max);
  $('#total-info').textContent = 'Позиций: ' + state.items.length + ' · Включено: ' + t.includedCount;
  $('#tier-min b').textContent = fmtCompact(t.tiers.min);
  $('#tier-base b').textContent = fmtCompact(t.tiers.base);
  $('#tier-max b').textContent = fmtCompact(t.tiers.max);
  updateSectionSums(t);
  renderMiniStats();
}

function animateAmount(el, to) {
  const from = state.displayedTotal;
  state.displayedTotal = to;
  const dur = 550;
  const t0 = performance.now();
  function step(now) {
    const k = Math.min(1, (now - t0) / dur);
    const eased = 1 - Math.pow(1 - k, 3);
    el.textContent = money(from + (to - from) * eased);
    if (k < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function updateItemAmountDom(id, c) {
  const el = $('[data-amount="' + id + '"]');
  if (el) el.textContent = money(c.amount);
  const card = $('.item[data-idx="' + id + '"]');
  if (card) {
    card.classList.toggle('included', c.included);
    card.classList.toggle('excluded', !c.included);
  }
}

function updateDataChip() {
  const chip = $('#data-chip');
  const txt = $('#data-chip-text');
  const meta = (state.data && state.data.meta) || {};
  if (state.sourceFile) {
    chip.className = 'data-chip';
    txt.textContent = 'Прайс: ' + state.sourceFile + ' · ' + meta.items_total + ' позиций';
  } else if (meta.items_total) {
    chip.className = 'data-chip';
    txt.textContent = 'Справочник 2026 · ' + meta.items_total + ' позиций';
  } else {
    chip.className = 'data-chip';
    txt.textContent = 'Справочник не загружен — «Загрузить данные»';
  }
}

/* ============================= Экшены ============================= */
function startCalc() {
  if (!state.data || !state.items.length) { toast('Сначала загрузите прайс (кнопка «Загрузить данные»)', 'err'); return; }
  buildItems(true);
  state.filters = { search: '', status: 'all', type: 'all' };
  $('#search').value = '';
  renderAll();
  toast('Расчет начат: автоматически включены обязательные позиции.');
}

function newCalc() {
  if (!state.data || !state.items.length) { toast('Сначала загрузите прайс (кнопка «Загрузить данные»)', 'err'); return; }
  state.params.area = 120;
  $('#area').value = 120;
  buildItems(false);
  renderAll();
  toast('Новый расчет: смета очищена.');
}

function recalc() {
  renderTotal();
  const bar = $('.totalbar');
  bar.classList.remove('flash-recalc');
  void bar.offsetWidth;
  bar.classList.add('flash-recalc');
  toast('Смета пересчитана.');
}

function applyNewData(data) {
  const oldItems = state.items;
  const oldIncluded = {};
  const oldQty = {};
  for (const c of oldItems) {
    const key = (c.it.section || '') + '|' + c.it.name;
    oldIncluded[key] = c.included;
    oldQty[key] = c.qty;
  }
  applyData(data);
  state.items = data.items.map((it) => {
    const key = (it.section || '') + '|' + it.name;
    const c = buildCalc(it, true);
    c.included = oldIncluded[key] === undefined ? c.included : oldIncluded[key];
    c.qty = oldQty[key] === undefined ? c.qty : oldQty[key];
    return c;
  });
}

async function handleLoadResult(res) {
  if (!res) return;
  if (res.ok) {
    applyNewData(res.data);
    state.sourceFile = res.source_file || null;
    state.filters = { search: '', status: 'all', type: 'all' };
    $('#search').value = '';
    renderAll();
    toast(res.message || 'Данные загружены.', 'ok');
  } else if (!res.canceled) {
    toast(res.message || 'Ошибка загрузки данных.', 'err');
  }
}

async function updateData() {
  const chip = $('#data-chip');
  chip.classList.add('busy');
  try {
    let res;
    if (window.pywebview && window.pywebview.api) {
      res = await window.pywebview.api.update_price_from_url();
    } else {
      res = await fetch('/update', { method: 'POST' }).then((r) => r.json());
    }
    await handleLoadResult(res);
  } finally {
    chip.classList.remove('busy');
  }
}

async function loadData() {
  if (window.pywebview && window.pywebview.api) {
    const chip = $('#data-chip');
    chip.classList.add('busy');
    try {
      const res = await window.pywebview.api.choose_and_load_price();
      await handleLoadResult(res);
    } finally {
      chip.classList.remove('busy');
    }
    return;
  }
  // браузерный режим
  const input = $('#file-input');
  input.value = '';
  input.click();
}

async function exportEstimate() {
  if (!state.items.length) { toast('Смета пуста. Начните расчет.', 'err'); return; }
  const inc = state.items.filter((c) => c.included);
  if (!inc.length) { toast('Нет включенных позиций.', 'err'); return; }
  const payload = {
    params: { area: state.params.area, client: '', object: '', comment: '' },
    items: inc.map((c) => ({
      name: c.it.name,
      section: c.it.section,
      subsection: c.it.subsection,
      unit: c.it.unit,
      type: c.it.type,
      status: c.it.status,
      qty: c.qty,
      price: c.price,
      amount: c.amount,
    })),
  };
  if (window.pywebview && window.pywebview.api) {
    const res = await window.pywebview.api.export_estimate(payload, true);
    if (res.ok) toast(res.message, 'ok');
    else if (!res.canceled) toast(res.message, 'err');
    return;
  }
  const res = await fetch('/export', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).then((r) => r.json());
  if (res.ok && res.b64) {
    const a = document.createElement('a');
    a.href = 'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,' + res.b64;
    a.download = res.filename || 'smeta.xlsx';
    document.body.appendChild(a);
    a.click();
    a.remove();
    toast('Смета скачана.', 'ok');
  } else {
    toast((res && res.message) || 'Ошибка экспорта.', 'err');
  }
}

function openTotalModal() {
  if (!state.items.length) { toast('Сначала начните расчет.', 'err'); return; }
  const t = computeTotals();
  state.totals = t;
  const modal = $('#total-modal');
  $('#modal-total-amount').textContent = money(t.grand);
  $('#modal-total-range').textContent =
    'Диапазон: ' + fmtCompact(t.tiers.min) + ' – ' + fmtCompact(t.tiers.max) + ' · База: ' + fmtCompact(t.tiers.base);

  const body = $('#breakdown-body');
  const rows = [];
  for (const sec of state.data.sections) {
    const sum = t.perSection[sec] || 0;
    const cnt = t.perSectionCount[sec] || 0;
    if (!sum && !cnt) continue;
    const share = t.grand ? (sum / t.grand) * 100 : 0;
    rows.push(
      '<tr>' +
      '<td>' + esc(sec) + '</td>' +
      '<td class="num">' + cnt + '</td>' +
      '<td class="num">' + money(sum) + '</td>' +
      '<td class="num" style="min-width:110px"><div class="bar"><i style="width:' + share.toFixed(1) + '%"></i></div></td>' +
      '</tr>'
    );
  }
  for (const sec in t.perSection) {
    if (state.data.sections.includes(sec)) continue;
    const sum = t.perSection[sec];
    const cnt = t.perSectionCount[sec];
    const share = t.grand ? (sum / t.grand) * 100 : 0;
    rows.push(
      '<tr>' +
      '<td>' + esc(sec) + '</td>' +
      '<td class="num">' + cnt + '</td>' +
      '<td class="num">' + money(sum) + '</td>' +
      '<td class="num"><div class="bar"><i style="width:' + share.toFixed(1) + '%"></i></div></td>' +
      '</tr>'
    );
  }
  body.innerHTML = rows.join('');

  // сравнение с контрольными бюджетами
  const cc = $('#controls-compare');
  if (state.data.controls && state.data.controls.length) {
    cc.innerHTML = state.data.controls.map((c) => {
      const hit = t.grand >= (c.min || 0) && t.grand <= (c.max || 0);
      return (
        '<div class="compare-card' + (hit ? ' hit' : '') + '">' +
        '<div class="cc-name">' + esc(c.scenario) + (hit ? ' ✓' : '') + '</div>' +
        '<div class="cc-area">' + (c.area ? c.area + ' м²' : '') + '</div>' +
        '<div class="cc-price">' + money(c.min) + ' – ' + money(c.max) + '</div>' +
        (c.comment ? '<div class="cc-note">' + esc(c.comment) + '</div>' : '') +
        '</div>'
      );
    }).join('');
  } else {
    cc.innerHTML = '<div class="hint">Контрольные бюджеты не загружены.</div>';
  }

  modal.hidden = false;
}

/* ============================= События ============================= */
function bindEvents() {
  $('#btn-update').addEventListener('click', updateData);
  $('#btn-load').addEventListener('click', loadData);
  document.addEventListener('click', (e) => {
    if (e.target.closest('#btn-empty-load')) loadData();
  });
  $('#btn-start').addEventListener('click', startCalc);
  $('#btn-recalc').addEventListener('click', recalc);
  $('#btn-new').addEventListener('click', newCalc);
  $('#btn-export').addEventListener('click', exportEstimate);
  $('#btn-total').addEventListener('click', openTotalModal);
  $('#modal-close').addEventListener('click', () => ($('#total-modal').hidden = true));
  $('#modal-close2').addEventListener('click', () => ($('#total-modal').hidden = true));
  $('#modal-export').addEventListener('click', () => { $('#total-modal').hidden = true; exportEstimate(); });
  $('#total-modal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) $('#total-modal').hidden = true;
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') $('#total-modal').hidden = true;
  });

  $('#file-input').addEventListener('change', async (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async () => {
      const b64 = btoa(String.fromCharCode(...new Uint8Array(reader.result)));
      let res;
      if (window.pywebview && window.pywebview.api) {
        res = await window.pywebview.api.load_price_b64(b64, file.name);
      } else {
        res = await fetch('/upload', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ b64, filename: file.name }),
        }).then((r) => r.json());
      }
      await handleLoadResult(res);
    };
    reader.readAsArrayBuffer(file);
  });

  $('#search').addEventListener('input', (e) => {
    state.filters.search = e.target.value;
    renderSections();
  });

  $('#status-filters').addEventListener('click', (e) => {
    const chip = e.target.closest('[data-grp]');
    if (!chip || chip.dataset.grp !== 'sf') return;
    state.filters.status = chip.dataset.val;
    renderChips();
    renderSections();
  });

  $('#type-filters').addEventListener('click', (e) => {
    const chip = e.target.closest('[data-grp]');
    if (!chip || chip.dataset.grp !== 'tf') return;
    state.filters.type = chip.dataset.val;
    renderChips();
    renderSections();
  });

  $('#area').addEventListener('input', (e) => {
    state.params.area = Math.max(0, parseFloat(e.target.value) || 0);
    for (const c of state.items) {
      if ((c.it.unit || '').toLowerCase().includes('м² площади')) c.qty = state.params.area;
    }
    renderSections();
    renderTotal();
  });

  $('#tier-group').addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-tier]');
    if (!btn) return;
    state.params.tier = btn.dataset.tier;
    $$('#tier-group button').forEach((b) => b.classList.toggle('active', b === btn));
  });

  $('#btn-apply-tier').addEventListener('click', () => {
    for (const c of state.items) {
      c.tier = state.params.tier;
      c.price = c.it[state.params.tier] || c.it.base || c.price;
    }
    renderSections();
    renderTotal();
    toast('Уровень цен применен ко всем позициям.', 'ok');
  });

  $('#sections-nav').addEventListener('click', (e) => {
    const item = e.target.closest('.nav-item');
    if (!item) return;
    const sec = item.dataset.nav;
    const card = $('.section-card[data-section-name="' + sec.replace(/"/g, '\\"') + '"]');
    if (card) card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    $$('.nav-item').forEach((n) => n.classList.toggle('active', n === item));
  });

  const container = $('#sections-container');

  container.addEventListener('click', (e) => {
    const head = e.target.closest('.section-head');
    const action = e.target.closest('[data-action]');
    if (action) {
      const card = action.closest('.section-card');
      const sec = card ? card.dataset.sectionName : null;
      const on = action.dataset.action === 'sec-all';
      for (const c of state.items) {
        if (c.it.section === sec) c.included = on;
      }
      renderSections();
      renderTotal();
      return;
    }
    if (head) {
      const card = head.closest('.section-card');
      card.classList.toggle('open');
      return;
    }
  });

  container.addEventListener('change', (e) => {
    const inc = e.target.closest('input.inc');
    if (inc) {
      const id = Number(inc.dataset.id);
      state.items[id].included = inc.checked;
      updateAll();
      return;
    }
    const sel = e.target.closest('select.tier-sel');
    if (sel) {
      const id = Number(sel.dataset.id);
      const c = state.items[id];
      c.tier = sel.value;
      if (sel.value !== 'custom') c.price = c.it[sel.value] || c.price;
      const priceEl = $('.price[data-id="' + id + '"]');
      if (priceEl) priceEl.value = c.price;
      updateAll();
    }
  });

  container.addEventListener('input', (e) => {
    const inp = e.target.closest('input.num-input');
    if (!inp) return;
    const id = Number(inp.dataset.id);
    const c = state.items[id];
    if (inp.classList.contains('qty')) {
      c.qty = Math.max(0, parseFloat(inp.value) || 0);
    } else if (inp.classList.contains('price')) {
      c.price = parseFloat(inp.value) || 0;
      c.tier = 'custom';
      const sel = $('.tier-sel[data-id="' + id + '"]');
      if (sel) sel.value = 'custom';
    }
    updateAll();
    updateItemAmountDom(id, c);
  });
}

function updateAll() {
  renderTotal();
}

/* ============================= Запуск ============================= */
document.addEventListener('DOMContentLoaded', () => {
  init();
  if (location.search.includes('selftest')) setTimeout(runSelfTest, 900);
});

/* ============================= Самопроверка (?selftest) ============================= */
async function runSelfTest() {
  const out = [];
  const ok = (name) => out.push('PASS ' + name);
  const bad = (name, e) => out.push('FAIL ' + name + ' :: ' + (e && e.message || e));

  try {
    // приложение стартует без встроенного справочника
    for (let i = 0; i < 50 && !state.data && !$('#sections-container .empty-state'); i++) await new Promise((r) => setTimeout(r, 100));
    ok(!state.data || !state.items.length ? 'starts empty' : 'starts with data');

    // загрузка справочника: POST /upload (как после нажатия «Загрузить данные»)
    const refResp = await fetch('/reference.xlsx');
    const buf = await refResp.arrayBuffer();
    const bytes = new Uint8Array(buf);
    let bin = '';
    for (let i = 0; i < bytes.length; i += 8192) {
      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 8192));
    }
    const b64 = btoa(bin);
    const up = await fetch('/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ b64, filename: 'spravochnik.xlsx' }),
    }).then((r) => r.json());
    if (up.ok && up.data) {
      await handleLoadResult(up);
      ok(state.items.length === 145 ? 'upload items=145' : 'upload items!=' + state.items.length);
    } else {
      bad('upload', up && up.message);
    }

    startCalc();
    const inc = state.items.filter((c) => c.included).length;
    ok(inc === 36 ? 'startCalc inc=36' : 'startCalc inc=' + inc);

    const t0 = state.totals ? state.totals.grand : 0;
    const w = state.items.find((c) => c.it.name.includes('ПВХ-окно'));
    if (w) {
      w.included = true;
      w.qty = 20;
      w.price = w.it.base;
      renderTotal();
      const t1 = state.totals.grand;
      ok(t1 > t0 ? 'grand grows (' + Math.round(t0) + ' -> ' + Math.round(t1) + ')' : 'grand NOT grown');
    } else {
      bad('window item found');
    }

    recalc();
    ok(state.totals && state.totals.grand > 0 ? 'recalc grand=' + Math.round(state.totals.grand) : 'recalc zero');

    state.filters.status = 'Вариант';
    renderSections();
    const vis = $$('.section-card').length;
    ok(vis > 0 ? 'filter render (' + vis + ' sections)' : 'no sections after filter');

    openTotalModal();
    const mt = $('#modal-total-amount').textContent;
    ok(mt !== '0 ₽' ? 'modal total ' + mt : 'modal total is zero');

    const incItems = state.items.filter((c) => c.included);
    const payload = {
      params: { area: state.params.area },
      items: incItems.slice(0, 30).map((c) => ({
        name: c.it.name, section: c.it.section, subsection: c.it.subsection,
        unit: c.it.unit, type: c.it.type, status: c.it.status,
        qty: c.qty, price: c.price, amount: c.amount,
      })),
    };
    const res = await fetch('/export', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then((r) => r.json());
    ok(res.ok && res.b64 ? 'export ok' : 'export fail ' + (res && res.message));
  } catch (e) {
    bad('selftest crashed', e);
  }

  finish();

  function finish() {
    let el = $('#selftest-output');
    if (!el) {
      el = document.createElement('div');
      el.id = 'selftest-output';
      document.body.appendChild(el);
    }
    el.textContent = out.join(' | ');
  }
}


/**
 * Prode Mundial 2026 — Main Application Logic
 * Handles UI interactions, API calls, and result rendering.
 */

// ============================================================
// State
// ============================================================
const state = {
  teams: [],
  teamsMap: {},
  matches: [],
  groups: {},
  lastResults: null,
};

// ============================================================
// Init
// ============================================================
document.addEventListener('DOMContentLoaded', async () => {
  await loadTeams();
  await loadMatches();
  initTabs();
  initSliders();
  initTeamSelectors();
  initSimulateButton();
  renderUpcomingMatches();
  loadGroups();
});

// ============================================================
// Data Loading
// ============================================================
async function loadTeams() {
  const res = await fetch('/api/teams');
  const data = await res.json();
  state.teams = data.teams;
  state.teamsMap = {};
  data.teams.forEach(t => { state.teamsMap[t.code] = t; });
}

async function loadMatches() {
  const res = await fetch('/api/matches');
  const data = await res.json();
  state.matches = data.matches;
}

async function loadGroups() {
  const res = await fetch('/api/groups');
  state.groups = await res.json();
  renderGroups();
}

// ============================================================
// Tabs
// ============================================================
function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
      if (btn.dataset.tab === 'calendar') renderCalendar();
    });
  });
}

// ============================================================
// Sliders
// ============================================================
function initSliders() {
  const sliders = [
    { id: 'lam-home', valId: 'lam-home-val', format: v => parseFloat(v).toFixed(2) },
    { id: 'lam-away', valId: 'lam-away-val', format: v => parseFloat(v).toFixed(2) },
    { id: 'rho', valId: 'rho-val', format: v => parseFloat(v).toFixed(2) },
    { id: 'nsims', valId: 'nsims-val', format: v => parseInt(v).toLocaleString() },
  ];
  sliders.forEach(({ id, valId, format }) => {
    const el = document.getElementById(id);
    const val = document.getElementById(valId);
    el.addEventListener('input', () => { val.textContent = format(el.value); });
  });
}

// ============================================================
// Team Selectors
// ============================================================
function initTeamSelectors() {
  const homeSelect = document.getElementById('home-team');
  const awaySelect = document.getElementById('away-team');

  // Sort teams alphabetically by name
  const sorted = [...state.teams].sort((a, b) => a.name.localeCompare(b.name));

  sorted.forEach(t => {
    const opt1 = new Option(`${t.flag} ${t.name} (${t.code})`, t.code);
    const opt2 = new Option(`${t.flag} ${t.name} (${t.code})`, t.code);
    homeSelect.add(opt1);
    awaySelect.add(opt2);
  });

  homeSelect.addEventListener('change', onTeamChange);
  awaySelect.addEventListener('change', onTeamChange);
}

function onTeamChange() {
  const homeCode = document.getElementById('home-team').value;
  const awayCode = document.getElementById('away-team').value;
  const btn = document.getElementById('btn-simulate');

  // Update flags
  const homeTeam = state.teamsMap[homeCode];
  const awayTeam = state.teamsMap[awayCode];
  document.getElementById('home-flag').textContent = homeTeam ? homeTeam.flag : '🏠';
  document.getElementById('away-flag').textContent = awayTeam ? awayTeam.flag : '🏟️';

  // Enable button if both selected
  const isValid = homeCode && awayCode && homeCode !== awayCode;
  btn.disabled = !isValid;

  // Auto-calibrate or reset
  if (isValid) {
    autoCalibrate(homeCode, awayCode);
  } else {
    document.getElementById('calibration-info').innerHTML = `
      <p class="text-muted text-sm">Seleccioná dos equipos para ver la calibración sugerida.</p>
    `;
  }

  // Auto-calibrate button fallback handler
  document.getElementById('btn-auto-calibrate').onclick = () => {
    if (isValid) autoCalibrate(homeCode, awayCode);
  };
}

async function autoCalibrate(homeCode, awayCode) {
  if (!homeCode || !awayCode) return;

  const res = await fetch('/api/suggest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ home_team: homeCode, away_team: awayCode })
  });
  const data = await res.json();

  // Set sliders
  const lamHome = document.getElementById('lam-home');
  const lamAway = document.getElementById('lam-away');
  const rho = document.getElementById('rho');

  lamHome.value = data.home_xg.xg;
  lamAway.value = data.away_xg.xg;
  rho.value = data.rho.rho;

  // Update displays
  document.getElementById('lam-home-val').textContent = data.home_xg.xg.toFixed(2);
  document.getElementById('lam-away-val').textContent = data.away_xg.xg.toFixed(2);
  document.getElementById('rho-val').textContent = data.rho.rho.toFixed(2);

  // Show calibration reasoning
  const calInfo = document.getElementById('calibration-info');
  const homeTeam = state.teamsMap[homeCode];
  const awayTeam = state.teamsMap[awayCode];

  const homeLive = data.live_stats && data.live_stats.home;
  const awayLive = data.live_stats && data.live_stats.away;

  const homeBadge = homeLive && homeLive.matches > 0
    ? `<div style="background:rgba(16,185,129,0.15);color:#10b981;border:1px solid rgba(16,185,129,0.3);padding:2px 6px;border-radius:4px;font-size:0.7rem;display:inline-block;margin-left:8px;font-weight:600;vertical-align:middle;">🟢 FOTMOB LIVE (${homeLive.matches} PJ)</div>`
    : `<div style="background:rgba(107,114,128,0.15);color:#9ca3af;border:1px solid rgba(107,114,128,0.3);padding:2px 6px;border-radius:4px;font-size:0.7rem;display:inline-block;margin-left:8px;font-weight:600;vertical-align:middle;">⚪ BASE HISTÓRICA</div>`;

  const awayBadge = awayLive && awayLive.matches > 0
    ? `<div style="background:rgba(16,185,129,0.15);color:#10b981;border:1px solid rgba(16,185,129,0.3);padding:2px 6px;border-radius:4px;font-size:0.7rem;display:inline-block;margin-left:8px;font-weight:600;vertical-align:middle;">🟢 FOTMOB LIVE (${awayLive.matches} PJ)</div>`
    : `<div style="background:rgba(107,114,128,0.15);color:#9ca3af;border:1px solid rgba(107,114,128,0.3);padding:2px 6px;border-radius:4px;font-size:0.7rem;display:inline-block;margin-left:8px;font-weight:600;vertical-align:middle;">⚪ BASE HISTÓRICA</div>`;

  calInfo.innerHTML = `
    <div style="margin-bottom:14px;">
      <div>
        <strong style="color:var(--accent-cyan);vertical-align:middle;">${homeTeam.flag} ${homeTeam.name}</strong>
        ${homeBadge}
      </div>
      <div class="text-xs text-muted mt-1">Ranking FIFA: #${homeTeam.ranking} · Estilo: ${homeTeam.style}</div>
      <ul class="text-sm" style="margin-top:6px;padding-left:18px;color:var(--text-secondary);">
        ${data.home_xg.reasoning.map(r => `<li>${r}</li>`).join('')}
      </ul>
    </div>
    <div>
      <div>
        <strong style="color:var(--accent-purple);vertical-align:middle;">${awayTeam.flag} ${awayTeam.name}</strong>
        ${awayBadge}
      </div>
      <div class="text-xs text-muted mt-1">Ranking FIFA: #${awayTeam.ranking} · Estilo: ${awayTeam.style}</div>
      <ul class="text-sm" style="margin-top:6px;padding-left:18px;color:var(--text-secondary);">
        ${data.away_xg.reasoning.map(r => `<li>${r}</li>`).join('')}
      </ul>
    </div>
    <div class="mt-1 text-xs text-muted">
      <strong>ρ:</strong> ${data.rho.reasoning}
    </div>
  `;
}

// ============================================================
// Upcoming Matches
// ============================================================
function renderUpcomingMatches() {
  const container = document.getElementById('upcoming-matches');
  const upcoming = state.matches.filter(m => m.status === 'scheduled').slice(0, 8);

  if (upcoming.length === 0) {
    container.innerHTML = '<p class="text-muted text-sm">No hay partidos programados.</p>';
    return;
  }

  container.innerHTML = upcoming.map(m => {
    const h = state.teamsMap[m.home];
    const a = state.teamsMap[m.away];
    if (!h || !a) return '';
    return `<button class="btn btn-secondary btn-sm" onclick="selectMatch('${m.home}','${m.away}')">
      ${h.flag} ${h.code} vs ${a.code} ${a.flag}
    </button>`;
  }).join('');
}

function selectMatch(homeCode, awayCode) {
  document.getElementById('home-team').value = homeCode;
  document.getElementById('away-team').value = awayCode;
  onTeamChange();
  autoCalibrate(homeCode, awayCode);
}

// ============================================================
// Simulate
// ============================================================
function initSimulateButton() {
  document.getElementById('btn-simulate').addEventListener('click', runSimulation);
}

async function runSimulation() {
  const homeCode = document.getElementById('home-team').value;
  const awayCode = document.getElementById('away-team').value;
  const lamHome = parseFloat(document.getElementById('lam-home').value);
  const lamAway = parseFloat(document.getElementById('lam-away').value);
  const rho = parseFloat(document.getElementById('rho').value);
  const nSims = parseInt(document.getElementById('nsims').value);

  if (!homeCode || !awayCode) return;

  // Show loading
  const overlay = document.getElementById('loading-overlay');
  overlay.querySelector('.loading-text').textContent =
    `Corriendo ${nSims.toLocaleString()} simulaciones...`;
  overlay.classList.add('active');

  // Build request
  const body = {
    home_team: homeCode,
    away_team: awayCode,
    lam_home: lamHome,
    lam_away: lamAway,
    rho: rho,
    n_sims: nSims,
  };

  // Add market odds if provided
  const oddsH = parseFloat(document.getElementById('odds-home').value);
  const oddsD = parseFloat(document.getElementById('odds-draw').value);
  const oddsA = parseFloat(document.getElementById('odds-away').value);
  if (oddsH > 1 && oddsD > 1 && oddsA > 1) {
    body.market_odds = { home: oddsH, draw: oddsD, away: oddsA };
  }

  try {
    const res = await fetch('/api/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const data = await res.json();

    if (data.error) {
      alert('Error: ' + data.error);
      return;
    }

    state.lastResults = data;
    renderResults(data);
  } catch (err) {
    alert('Error de conexión: ' + err.message);
  } finally {
    overlay.classList.remove('active');
  }
}

// ============================================================
// Render Results
// ============================================================
function renderResults(data) {
  const section = document.getElementById('results-section');
  section.classList.add('active');

  render1X2(data);
  renderHeatmap(data);
  renderExactScores(data);
  renderOverUnder(data);
  renderBTTSCS(data);
  renderValidation(data);
  renderConfidence(data);
  renderRecommendation(data);
  renderSummary(data);

  // Scroll to results
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function render1X2(data) {
  const { one_x_two, home_team, away_team } = data;
  const maxProb = Math.max(one_x_two.home, one_x_two.draw, one_x_two.away);

  document.getElementById('one-x-two').innerHTML = `
    <div class="one-x-two-item ${one_x_two.home === maxProb ? 'highlight' : ''}">
      <div class="label">${home_team.flag || ''} ${home_team.code || 'Local'}</div>
      <div class="prob home">${(one_x_two.home * 100).toFixed(1)}%</div>
      <div class="bar home" style="width:${one_x_two.home * 100}%"></div>
    </div>
    <div class="one-x-two-item ${one_x_two.draw === maxProb ? 'highlight' : ''}">
      <div class="label">Empate</div>
      <div class="prob draw">${(one_x_two.draw * 100).toFixed(1)}%</div>
      <div class="bar draw" style="width:${one_x_two.draw * 100}%"></div>
    </div>
    <div class="one-x-two-item ${one_x_two.away === maxProb ? 'highlight' : ''}">
      <div class="label">${away_team.flag || ''} ${away_team.code || 'Visitante'}</div>
      <div class="prob away">${(one_x_two.away * 100).toFixed(1)}%</div>
      <div class="bar away" style="width:${one_x_two.away * 100}%"></div>
    </div>
  `;
}

function renderHeatmap(data) {
  const matrix = data.prob_matrix;
  const maxProb = Math.max(...matrix.flat());
  const container = document.getElementById('heatmap-container');
  const size = Math.min(matrix.length, 7); // Show 0-6

  let html = '<div class="heatmap" style="grid-template-columns: 40px repeat(' + size + ', 1fr);">';

  // Header row — away goals
  html += '<div class="heatmap-cell corner"></div>';
  for (let j = 0; j < size; j++) {
    html += `<div class="heatmap-cell header">${j}</div>`;
  }

  // Data rows
  for (let i = 0; i < size; i++) {
    html += `<div class="heatmap-cell header">${i}</div>`;
    for (let j = 0; j < size; j++) {
      const prob = matrix[i][j];
      const intensity = prob / maxProb;
      const pct = (prob * 100).toFixed(1);

      // Color: cyan for higher probability
      const r = Math.round(6 + (15 - 6) * (1 - intensity));
      const g = Math.round(182 * intensity + 23 * (1 - intensity));
      const b = Math.round(212 * intensity + 42 * (1 - intensity));
      const alpha = 0.1 + intensity * 0.7;

      html += `<div class="heatmap-cell" style="background:rgba(${r},${g},${b},${alpha});"
        title="${i}-${j}: ${pct}%">${pct}%</div>`;
    }
  }
  html += '</div>';
  html += '<p class="text-xs text-muted mt-1 text-center">Filas = goles local · Columnas = goles visitante</p>';
  container.innerHTML = html;
}

function renderExactScores(data) {
  const container = document.getElementById('exact-scores');
  const scores = data.exact_scores.slice(0, 10);
  const maxPct = scores[0]?.pct || 1;

  container.innerHTML = scores.map((s, i) => `
    <div class="score-item">
      <span class="rank">#${i + 1}</span>
      <span class="score-val">${s.score}</span>
      <div class="score-bar"><div class="fill" style="width:${(s.pct / maxPct) * 100}%"></div></div>
      <span class="score-pct">${s.pct}%</span>
    </div>
  `).join('');
}

function renderOverUnder(data) {
  const container = document.getElementById('over-under-markets');
  const thresholds = ['0.5', '1.5', '2.5', '3.5', '4.5'];

  container.innerHTML = thresholds.map(t => {
    const ou = data.over_under[t];
    if (!ou) return '';
    return `
      <div class="market-row">
        <span class="label">O/U ${t} goles</span>
        <div class="values">
          <span class="val over">Over ${(ou.over * 100).toFixed(1)}%</span>
          <span class="val under">Under ${(ou.under * 100).toFixed(1)}%</span>
        </div>
      </div>
    `;
  }).join('');
}

function renderBTTSCS(data) {
  const container = document.getElementById('btts-cs-markets');
  const { btts, clean_sheet, home_team, away_team } = data;

  container.innerHTML = `
    <div class="market-row">
      <span class="label">Ambos Marcan (BTTS)</span>
      <div class="values">
        <span class="val over">Sí ${(btts.yes * 100).toFixed(1)}%</span>
        <span class="val under">No ${(btts.no * 100).toFixed(1)}%</span>
      </div>
    </div>
    <div class="market-row">
      <span class="label">Valla invicta ${home_team.code || 'Local'}</span>
      <div class="values">
        <span class="val ${clean_sheet.home > 0.4 ? 'over' : ''}">${(clean_sheet.home * 100).toFixed(1)}%</span>
      </div>
    </div>
    <div class="market-row">
      <span class="label">Valla invicta ${away_team.code || 'Visitante'}</span>
      <div class="values">
        <span class="val ${clean_sheet.away > 0.4 ? 'over' : ''}">${(clean_sheet.away * 100).toFixed(1)}%</span>
      </div>
    </div>
  `;
}

function renderValidation(data) {
  const section = document.getElementById('validation-section');
  const container = document.getElementById('validation-content');

  if (!data.market_validation || !data.market_validation.model) {
    section.style.display = 'none';
    return;
  }

  section.style.display = 'block';
  const v = data.market_validation;

  const devClass = (d) => d > 7 ? 'deviation-bad' : d > 5 ? 'deviation-warn' : 'deviation-ok';

  container.innerHTML = `
    <table class="validation-table">
      <thead>
        <tr><th>Mercado</th><th>Modelo</th><th>Mercado (de-vig)</th><th>Desviación</th></tr>
      </thead>
      <tbody>
        <tr>
          <td style="font-family:var(--font-sans);">Local</td>
          <td>${(v.model.home * 100).toFixed(1)}%</td>
          <td>${(v.market.home * 100).toFixed(1)}%</td>
          <td class="${devClass(v.deviation.home)}">${v.deviation.home}pp</td>
        </tr>
        <tr>
          <td style="font-family:var(--font-sans);">Empate</td>
          <td>${(v.model.draw * 100).toFixed(1)}%</td>
          <td>${(v.market.draw * 100).toFixed(1)}%</td>
          <td class="${devClass(v.deviation.draw)}">${v.deviation.draw}pp</td>
        </tr>
        <tr>
          <td style="font-family:var(--font-sans);">Visitante</td>
          <td>${(v.model.away * 100).toFixed(1)}%</td>
          <td>${(v.market.away * 100).toFixed(1)}%</td>
          <td class="${devClass(v.deviation.away)}">${v.deviation.away}pp</td>
        </tr>
      </tbody>
    </table>
    <p class="text-sm mt-1">${v.alert || ''}</p>
    <p class="text-xs text-muted mt-1">Margen del book: ${v.market.margin}%</p>
  `;
}

function renderConfidence(data) {
  const badge = document.getElementById('confidence-badge');
  const expl = document.getElementById('confidence-explanation');
  const c = data.confidence;
  const cls = c === 'ALTA' ? 'alta' : c === 'MEDIA' ? 'media' : 'baja';
  const icons = { ALTA: '🟢', MEDIA: '🟡', BAJA: '🔴' };

  badge.innerHTML = `<span class="confidence-badge ${cls}">${icons[c]} ${c}</span>`;

  const maxP = Math.max(data.one_x_two.home, data.one_x_two.draw, data.one_x_two.away);
  expl.textContent = c === 'ALTA'
    ? `Favorito claro (${(maxP * 100).toFixed(0)}%). El modelo tiene lectura fuerte.`
    : c === 'MEDIA'
    ? `Favorito moderado (${(maxP * 100).toFixed(0)}%). Incertidumbre considerable.`
    : `Partido muy parejo (${(maxP * 100).toFixed(0)}%). El modelo no tiene lectura fuerte — cualquier resultado es posible.`;
}

function renderRecommendation(data) {
  const { recommendation, home_team, away_team } = data;
  const resultEl = document.getElementById('rec-result');
  const scoreEl = document.getElementById('rec-score');

  const labels = {
    home: `${home_team.flag || ''} ${home_team.name || home_team.code || 'Local'}`,
    away: `${away_team.flag || ''} ${away_team.name || away_team.code || 'Visitante'}`,
    draw: '🤝 Empate'
  };

  resultEl.textContent = labels[recommendation.result] || recommendation.result;
  scoreEl.textContent = recommendation.score;
}

function renderSummary(data) {
  const container = document.getElementById('summary-stats');
  const s = data.summary;
  const p = data.params;

  const stats = [
    { label: 'xG Local', value: s.home_goals_mean.toFixed(2), color: 'var(--accent-cyan)' },
    { label: 'xG Visitante', value: s.away_goals_mean.toFixed(2), color: 'var(--accent-purple)' },
    { label: 'Total goles', value: s.total_goals_mean.toFixed(2), color: 'var(--accent-emerald)' },
    { label: 'Simulaciones', value: p.n_sims.toLocaleString(), color: 'var(--accent-amber)' },
  ];

  container.innerHTML = stats.map(s => `
    <div style="text-align:center;padding:12px;background:var(--bg-glass);border-radius:var(--radius-sm);">
      <div class="text-xs text-muted" style="margin-bottom:4px;">${s.label}</div>
      <div style="font-family:var(--font-mono);font-size:1.3rem;font-weight:700;color:${s.color};">${s.value}</div>
    </div>
  `).join('');
}

// ============================================================
// Groups
// ============================================================
function renderGroups() {
  const container = document.getElementById('groups-container');
  const groupKeys = Object.keys(state.groups).sort();

  container.innerHTML = groupKeys.map(g => {
    const teams = state.groups[g];
    return `
      <div class="card group-card">
        <h3>Grupo ${g}</h3>
        <table class="group-table">
          <thead>
            <tr><th>Equipo</th><th>PJ</th><th>G</th><th>E</th><th>P</th><th>GF</th><th>GC</th><th>DG</th><th>Pts</th></tr>
          </thead>
          <tbody>
            ${teams.map((t, i) => `
              <tr class="${i < 2 ? 'qualified' : ''}">
                <td>${t.flag} ${t.code}</td>
                <td>${t.played}</td>
                <td>${t.won}</td>
                <td>${t.drawn}</td>
                <td>${t.lost}</td>
                <td>${t.gf}</td>
                <td>${t.ga}</td>
                <td>${t.gd > 0 ? '+' : ''}${t.gd}</td>
                <td><strong>${t.points}</strong></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }).join('');
}

// ============================================================
// Calendar
// ============================================================
function renderCalendar() {
  const container = document.getElementById('calendar-container');
  const matchesByDate = {};

  state.matches.forEach(m => {
    if (!matchesByDate[m.date]) matchesByDate[m.date] = [];
    matchesByDate[m.date].push(m);
  });

  const dates = Object.keys(matchesByDate).sort();

  container.innerHTML = dates.map(date => {
    const matches = matchesByDate[date];
    const d = new Date(date + 'T12:00:00');
    const dateStr = d.toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' });

    return `
      <div class="card" style="margin-bottom:16px;">
        <div class="card-header">
          <span class="icon">📅</span>
          <h2>${dateStr}</h2>
        </div>
        ${matches.map(m => {
          const h = state.teamsMap[m.home];
          const a = state.teamsMap[m.away];
          if (!h || !a) return '';
          const isPlayed = m.status === 'played';
          return `
            <div class="market-row" style="cursor:${isPlayed ? 'default' : 'pointer'};"
              ${!isPlayed ? `onclick="selectMatch('${m.home}','${m.away}')"` : ''}>
              <span class="label">
                ${h.flag} <strong>${h.code}</strong>
                ${isPlayed ? `<span style="color:var(--accent-cyan);font-family:var(--font-mono);font-weight:700;margin:0 8px;">${m.home_goals} - ${m.away_goals}</span>` : '<span style="color:var(--text-muted);margin:0 8px;">vs</span>'}
                <strong>${a.code}</strong> ${a.flag}
              </span>
              <span class="text-xs text-muted">Grupo ${m.group} · ${m.venue}</span>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }).join('');
}

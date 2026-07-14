/**
 * app.js — Sistem Simulasi Dasar Tenaga Pengajar 2027
 * =====================================================
 * This file connects the HTML page to the FastAPI backend.
 * It handles:
 *   1. Checking if the backend is online (health check)
 *   2. Loading dropdown filter options (negeri, PPD, sekolah, tahun)
 *   3. Showing the right input field based on the selected policy type
 *   4. Sending the simulation request to POST /api/simulate
 *   5. Displaying results: KPI cards, charts, table, explanation
 *   6. Running the AI agent via POST /api/agent/run
 *   7. Downloading the CSV result file
 *
 * No framework is used — only plain JavaScript (fetch, DOM manipulation).
 */

// ============================================================
// CONFIGURATION
// ============================================================

/** The base URL of the FastAPI backend. Change this if the server runs on a different port. */
const API_BASE = window.location.protocol.startsWith('http')
  ? window.location.origin
  : 'http://127.0.0.1:8002';

// Uses sessionStorage, not localStorage: sessionStorage is cleared automatically
// when the browser (or tab) closes, so a user who closes the browser without
// logging out — or simply forgets to log out — must log in again next time,
// with no explicit logout action required.
function getStoredAuth() {
  try {
    return JSON.parse(sessionStorage.getItem('workforce_auth') || 'null');
  } catch {
    return null;
  }
}

function setStoredAuth(payload) {
  sessionStorage.setItem('workforce_auth', JSON.stringify(payload));
  state.auth = payload;
}

function clearAuth() {
  sessionStorage.removeItem('workforce_auth');
  state.auth = { token: null, username: null, role_name: null, is_first_login: false };
}

function showLoginScreen(message = '') {
  document.getElementById('loginScreen').style.display = 'flex';
  document.getElementById('loginError').textContent = message;
  document.getElementById('agentFab').style.display = 'none';
}

function hideLoginScreen() {
  document.getElementById('loginScreen').style.display = 'none';
}

function showChangePasswordScreen() {
  document.getElementById('changePasswordScreen').classList.add('visible');
  document.getElementById('agentFab').style.display = 'none';
}

function hideChangePasswordScreen() {
  document.getElementById('changePasswordScreen').classList.remove('visible');
  if (state.auth.username) {
    document.getElementById('agentFab').style.display = 'flex';
  }
}

async function runChangePassword() {
  const btn = document.getElementById('btnChangePassword');
  const currentPassword = document.getElementById('cpCurrentPassword').value;
  const newPassword = document.getElementById('cpNewPassword').value;
  const confirmPassword = document.getElementById('cpConfirmPassword').value;
  const errorEl = document.getElementById('changePasswordError');
  errorEl.textContent = '';

  if (!currentPassword || !newPassword || !confirmPassword) {
    errorEl.textContent = t('cp.error.missing');
    return;
  }
  if (newPassword !== confirmPassword) {
    errorEl.textContent = t('cp.error.mismatch');
    return;
  }
  if (newPassword.length < 8) {
    errorEl.textContent = t('cp.error.short');
    return;
  }

  btn.disabled = true;
  btn.classList.add('loading');
  try {
    await apiFetch('/api/auth/change-password', {
      method: 'POST',
      body: { current_password: currentPassword, new_password: newPassword },
    });
    state.auth.is_first_login = false;
    setStoredAuth(state.auth);
    hideChangePasswordScreen();
    document.getElementById('cpCurrentPassword').value = '';
    document.getElementById('cpNewPassword').value = '';
    document.getElementById('cpConfirmPassword').value = '';
    showToast(t('cp.success'), 'success');
  } catch (err) {
    errorEl.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.classList.remove('loading');
  }
}

/** Human-friendly role label, reusing the labels already defined for the create-user role dropdown. */
function roleLabel(role) {
  const key = `admin.role.${role}`;
  const label = t(key);
  return label === key ? role : label;
}

function updateUserChip() {
  const info = document.getElementById('userInfo');
  const fab = document.getElementById('agentFab');
  if (!state.auth.username) {
    info.style.display = 'none';
    fab.style.display = 'none';
    return;
  }
  info.style.display = 'flex';
  if (!state.auth.is_first_login) {
    fab.style.display = 'flex';
  }

  const initial = state.auth.username.charAt(0).toUpperCase();
  document.getElementById('userAvatarInitial').textContent = initial;
  document.getElementById('userMenuProfileAvatar').textContent = initial;
  document.getElementById('userMenuProfileName').textContent = state.auth.username;
  document.getElementById('userMenuProfileEmail').textContent = state.auth.email || '';
  document.getElementById('userMenuProfileRole').textContent = roleLabel(state.auth.role_name);
}

/** Scrolls the sidebar so the Agent AI section is in view and focuses its input.
 *  Used by the floating shortcut button (.agent-fab) that mirrors this section
 *  from anywhere on the page, similar to a corner chat-widget launcher. */
function focusAgentSection() {
  const section = document.querySelector('.agent-section--sidebar');
  if (!section) return;
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  document.getElementById('agentQuestion').focus();
  const fab = document.getElementById('agentFab');
  fab.classList.remove('pulse');
  void fab.offsetWidth; // restart the pulse animation on repeated clicks
  fab.classList.add('pulse');
}

function toggleUserMenu() {
  const menu = document.getElementById('userMenu');
  const isVisible = menu.classList.contains('visible');
  if (isVisible) {
    hideUserMenu();
  } else {
    showMenuView();
    menu.classList.add('visible');
  }
}

function hideUserMenu() {
  document.getElementById('userMenu').classList.remove('visible');
}

function showProfileView() {
  document.getElementById('userMenuList').style.display = 'none';
  document.getElementById('userMenuProfile').style.display = 'block';
}

function showMenuView() {
  document.getElementById('userMenuProfile').style.display = 'none';
  document.getElementById('userMenuList').style.display = 'flex';
}

function openChangePasswordFromMenu() {
  hideUserMenu();
  showChangePasswordScreen();
}

// Close the account menu when clicking anywhere outside it.
document.addEventListener('click', event => {
  const info = document.getElementById('userInfo');
  if (info && !info.contains(event.target)) {
    hideUserMenu();
  }
});

async function runLogout() {
  // Tell the backend first, while the token is still attached — this is what
  // actually records the logout time in the audit log. clearAuth() below
  // drops the token from state, so it must happen after this call, not before.
  try {
    await apiFetch('/api/auth/logout', { method: 'POST' });
  } catch {
    // Best-effort: still log the user out locally even if the request fails
    // (e.g. server unreachable) — no audit entry in that case, but the user
    // isn't stuck unable to log out.
  }
  clearAuth();
  showLoginScreen('');
  document.getElementById('loginUsername').value = '';
  document.getElementById('loginPassword').value = '';
  console.log('Logged out successfully');
}

function showAdminPanel() {
  const adminBtn = document.getElementById('adminBtn');
  const auditBtn = document.getElementById('auditLogBtn');
  const myRunsBtn = document.getElementById('myRunsBtn');
  adminBtn.style.display = state.auth.role_name === 'superadmin' ? 'inline-block' : 'none';
  const canSeeAudit = state.auth.role_name === 'superadmin'
    || (state.auth.role_name === 'admin' && state.auth.can_view_audit_log);
  auditBtn.style.display = canSeeAudit ? 'inline-block' : 'none';
  myRunsBtn.style.display = state.auth.role_name === 'user' ? 'inline-block' : 'none';
}

function goToAdminPage() {
  document.getElementById('mainPanel').style.display = 'none';
  document.getElementById('auditLogPage').style.display = 'none';
  document.getElementById('myRunsPage').style.display = 'none';
  document.getElementById('adminPage').style.display = 'block';
  applyLang(); // Ensure translations are applied
  loadUserList();
}

function goToDashboard() {
  document.getElementById('adminPage').style.display = 'none';
  document.getElementById('auditLogPage').style.display = 'none';
  document.getElementById('myRunsPage').style.display = 'none';
  document.getElementById('mainPanel').style.display = 'block';
  applyLang(); // Ensure translations are applied
}

function goToAuditLogPage() {
  const canSeeAudit = state.auth.role_name === 'superadmin'
    || (state.auth.role_name === 'admin' && state.auth.can_view_audit_log);
  if (!canSeeAudit) {
    showToast(t('toast.no.permission'), 'error');
    return;
  }
  document.getElementById('mainPanel').style.display = 'none';
  document.getElementById('adminPage').style.display = 'none';
  document.getElementById('myRunsPage').style.display = 'none';
  document.getElementById('auditLogPage').style.display = 'block';
  applyLang();
  loadAuditLog();
}

function goToMyRunsPage() {
  if (state.auth.role_name !== 'user') {
    showToast(t('toast.no.permission'), 'error');
    return;
  }
  document.getElementById('mainPanel').style.display = 'none';
  document.getElementById('adminPage').style.display = 'none';
  document.getElementById('auditLogPage').style.display = 'none';
  document.getElementById('myRunsPage').style.display = 'block';
  applyLang();
  loadMyRuns();
}

async function loadAuditLog() {
  const tbody = document.getElementById('auditLogBody');
  tbody.innerHTML = '';
  try {
    const data = await apiFetch('/api/audit-log');
    (data.entries || []).forEach(entry => {
      const tr = document.createElement('tr');
      const values = [entry.occurred_at, entry.actor, entry.role, entry.action, entry.details];
      values.forEach(value => {
        const td = document.createElement('td');
        td.textContent = value == null ? '' : value;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
  } catch (err) {
    showToast('Failed to load audit log: ' + err.message, 'error');
  }
}

/** Loads the current Policy Maker's own last 20 simulation runs and renders
 *  them as a table with a per-row PDF re-download button. */
async function loadMyRuns() {
  const tbody = document.getElementById('myRunsBody');
  const emptyMsg = document.getElementById('myRunsEmpty');
  tbody.innerHTML = '';
  try {
    const data = await apiFetch('/api/my-runs');
    const runs = data.runs || [];
    emptyMsg.style.display = runs.length ? 'none' : 'block';
    const policyLabels = getPolicyLabels();

    runs.forEach(run => {
      const scenario = run.scenario || {};
      const tr = document.createElement('tr');

      const tdTime = document.createElement('td');
      tdTime.textContent = run.run_timestamp || '';
      tr.appendChild(tdTime);

      const tdScope = document.createElement('td');
      const subject = scenario.subject === 'SEMUA' ? t('all.subjects') : formatSubject(scenario.subject);
      const negeri = scenario.negeri === 'SEMUA' ? t('all.states') : toTitleCase(scenario.negeri || '');
      tdScope.textContent = `${subject} / ${negeri}`;
      tr.appendChild(tdScope);

      const tdPolicy = document.createElement('td');
      const activePolicies = scenario.active_policies?.length
        ? scenario.active_policies
        : [scenario.policy_type].filter(Boolean);
      tdPolicy.textContent = activePolicies.map(value => policyLabels[value] || value).join(' + ') || '—';
      tr.appendChild(tdPolicy);

      const tdAction = document.createElement('td');
      const btn = document.createElement('button');
      btn.className = 'btn btn-teal btn-sm';
      btn.textContent = t('btn.download.summary');
      btn.addEventListener('click', () => downloadPdfForRun(scenario));
      tdAction.appendChild(btn);
      tr.appendChild(tdAction);

      tbody.appendChild(tr);
    });
  } catch (err) {
    showToast('Failed to load my runs: ' + err.message, 'error');
  }
}

function onNewRoleChange() {
  const role = document.getElementById('newRole').value;
  document.getElementById('canViewAuditGroup').style.display = role === 'admin' ? 'block' : 'none';
}

async function handleCreateUser(event) {
  event.preventDefault();
  const btn = event.target.querySelector('button[type="submit"]');
  const errorEl = document.getElementById('createUserError');
  errorEl.textContent = '';

  const username = document.getElementById('newUsername').value.trim();
  const email = document.getElementById('newEmail').value.trim();
  const role = document.getElementById('newRole').value;
  const canViewAudit = document.getElementById('newCanViewAudit').checked;

  if (!username || !email) {
    errorEl.textContent = 'Please fill all fields';
    return;
  }

  btn.disabled = true;
  btn.classList.add('loading');

  try {
    const data = await apiFetch('/api/admin/create-user', {
      method: 'POST',
      body: {
        username, email, role_name: role,
        can_view_audit_log: canViewAudit,
        lang: (typeof getLang === 'function' ? getLang() : 'bm'),
      },
    });
    showToast(data.message || t('admin.create.success'), 'success');
    if (!data.email_sent) {
      showToast(t('admin.email.failed'), 'warning');
    }
    document.getElementById('createUserForm').reset();
    loadUserList();
  } catch (err) {
    errorEl.textContent = err.message;
  } finally {
    btn.disabled = false;
    btn.classList.remove('loading');
  }
}

async function loadUserList() {
  const tbody = document.getElementById('userListBody');
  if (!tbody) return;
  tbody.innerHTML = '';
  try {
    const data = await apiFetch('/api/admin/users');
    (data.users || []).forEach(user => tbody.appendChild(buildUserRow(user)));
  } catch (err) {
    showToast('Failed to load user list: ' + err.message, 'error');
  }
}

function formatUserTimestamp(value) {
  if (!value) return '—';
  return value.slice(0, 19).replace('T', ' ');
}

function buildUserRow(user) {
  const tr = document.createElement('tr');
  const statusClass = user.is_active ? 'active' : 'inactive';
  const statusLabel = user.is_active ? t('admin.status.active') : t('admin.status.inactive');
  const isSelf = user.username === state.auth.username;
  const resetDisabled = !user.is_active;
  const deactivateDisabled = !user.is_active || isSelf;

  const usernameTd = document.createElement('td');
  usernameTd.textContent = user.username;
  const emailTd = document.createElement('td');
  emailTd.textContent = user.email;
  const roleTd = document.createElement('td');
  roleTd.textContent = user.role_name;
  const statusTd = document.createElement('td');
  const statusPill = document.createElement('span');
  statusPill.className = `status-pill ${statusClass}`;
  statusPill.textContent = statusLabel;
  statusTd.appendChild(statusPill);
  const createdTd = document.createElement('td');
  createdTd.textContent = formatUserTimestamp(user.created_at);
  const lastLoginTd = document.createElement('td');
  lastLoginTd.textContent = formatUserTimestamp(user.last_login_at);

  const actionsTd = document.createElement('td');
  actionsTd.className = 'user-actions';
  actionsTd.innerHTML = `
    <button class="icon-btn" title="${t('admin.action.reset')}" ${resetDisabled ? 'disabled' : ''}>📝</button>
    <button class="icon-btn" title="${t('admin.action.deactivate')}" ${deactivateDisabled ? 'disabled' : ''}>🗑️</button>`;

  tr.append(usernameTd, emailTd, roleTd, statusTd, createdTd, lastLoginTd, actionsTd);

  const [resetBtn, deactivateBtn] = tr.querySelectorAll('.icon-btn');
  resetBtn.addEventListener('click', () => confirmResetPassword(user.id, user.email));
  deactivateBtn.addEventListener('click', () => confirmDeactivateUser(user.id, user.username));
  return tr;
}

async function confirmResetPassword(id, email) {
  if (!confirm(t('admin.confirm.reset', email))) return;
  try {
    const data = await apiFetch(`/api/admin/users/${id}/reset-password`, { method: 'POST' });
    showToast(data.message, 'success');
    if (!data.email_sent) {
      showToast(t('admin.email.failed'), 'warning');
    }
  } catch (err) {
    showToast('Failed: ' + err.message, 'error');
  }
}

async function confirmDeactivateUser(id, username) {
  if (!confirm(t('admin.confirm.deactivate', username))) return;
  try {
    const data = await apiFetch(`/api/admin/users/${id}/deactivate`, { method: 'POST' });
    showToast(data.message, 'success');
    loadUserList();
  } catch (err) {
    showToast('Failed: ' + err.message, 'error');
  }
}

function initAuth() {
  const stored = getStoredAuth();
  if (stored?.token && stored?.username && stored?.role_name) {
    state.auth = stored;
    hideLoginScreen();
    updateUserChip();
    showAdminPanel();
    if (stored.is_first_login) {
      showChangePasswordScreen();
    }
    return;
  }
  showLoginScreen('');
}

async function runLogin() {
  const btn = document.getElementById('btnLogin');
  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;
  const errorEl = document.getElementById('loginError');
  errorEl.textContent = '';

  if (!username || !password) {
    errorEl.textContent = t('login.error.missing');
    return;
  }

  btn.disabled = true;
  btn.classList.add('loading');
  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) {
      errorEl.textContent = data.detail || t('login.error.invalid');
      return;
    }
    setStoredAuth(data);
    updateUserChip();
    showAdminPanel();
    hideLoginScreen();
    if (data.is_first_login) {
      showChangePasswordScreen();
    }
  } catch (err) {
    errorEl.textContent = t('login.error.network');
  } finally {
    btn.disabled = false;
    btn.classList.remove('loading');
  }
}

/** All available grade/form codes that a user can select */
const ALL_GRADES = ['D1','D2','D3','D4','D5','D6','T1','T2','T3','T4','T5'];

/** Human-friendly label for each grade code */
const GRADE_LABELS = {
  D1:'Year 1', D2:'Year 2', D3:'Year 3',
  D4:'Year 4', D5:'Year 5', D6:'Year 6',
  T1:'Form 1', T2:'Form 2', T3:'Form 3',
  T4:'Form 4', T5:'Form 5'
};

/** Human-friendly labels for each policy type — uses current language */
function getPolicyLabels() {
  const lang = (typeof getLang === 'function') ? getLang() : 'bm';
  const bm = {
    baseline:         'Unjuran Tanpa Perubahan Dasar',
    option_ratio:     'Nisbah Guru Opsyen Mata Pelajaran',
    teaching_hours:   'Waktu Pengajaran Mata Pelajaran Tahunan',
    teacher_capacity: 'Kapasiti Waktu Pengajaran Tahunan Guru',
    coteaching:       'Pengajaran Bersama',
  };
  const en = {
    baseline:         'Forecast Without Policy Change',
    option_ratio:     'Subject-Option Teacher Ratio',
    teaching_hours:   'Annual Subject Teaching Hours',
    teacher_capacity: 'Annual Teacher Teaching-Hour Capacity',
    coteaching:       'Co-teaching',
  };
  return lang === 'en' ? en : bm;
}

const SCENARIO_SOURCE_LABELS = {
  'Local fallback parser': '⚙️ Question interpreted by the local system (without AI)',
  'Direct user controls': '📝 User-selected parameters',
};

function _uiLang() {
  return (typeof getLang === 'function') ? getLang() : 'en';
}

function formatScenarioSource(source) {
  if (!source) return '';
  const lang = _uiLang();
  const model = source.match(/\(([^)]+)\)/)?.[1] || (lang === 'bm' ? 'tidak dinyatakan' : 'not specified');
  if (source.startsWith('OpenAI Scenario Agent')) {
    return lang === 'bm'
      ? `🤖 Soalan ditafsirkan oleh OpenAI · Model: ${model}`
      : `🤖 Question interpreted by OpenAI · Model: ${model}`;
  }
  if (source.startsWith('Groq Scenario Agent')) {
    return lang === 'bm'
      ? `🤖 Soalan ditafsirkan oleh Groq · Model: ${model}`
      : `🤖 Question interpreted by Groq · Model: ${model}`;
  }
  if (source === 'Local fallback parser' || source === 'Direct user controls') {
    return lang === 'bm' ? '⚙️ Ditafsirkan oleh sistem tempatan' : '⚙️ Interpreted by local system';
  }
  return source;
}

function formatExplanationSource(source) {
  if (!source) return '';
  const lang = _uiLang();
  const model = source.match(/\(([^)]+)\)/)?.[1] || (lang === 'bm' ? 'tidak dinyatakan' : 'not specified');
  if (source.startsWith('OpenAI Explanation Agent')) {
    return lang === 'bm'
      ? `🤖 Penjelasan dijana oleh OpenAI · Model: ${model}`
      : `🤖 Explanation generated by OpenAI · Model: ${model}`;
  }
  if (source.startsWith('Groq Explanation Agent')) {
    return lang === 'bm'
      ? `🤖 Penjelasan dijana oleh Groq · Model: ${model}`
      : `🤖 Explanation generated by Groq · Model: ${model}`;
  }
  if (source === 'Deterministic explanation') {
    return lang === 'bm'
      ? '⚙️ Penjelasan disediakan oleh sistem tempatan (tanpa AI)'
      : '⚙️ Explanation prepared by the local system (without AI)';
  }
  if (source.includes('fallback')) {
    return lang === 'bm'
      ? '⚙️ Pembekal AI gagal; penjelasan disediakan oleh sistem tempatan'
      : '⚙️ AI provider failed; explanation prepared by the local system';
  }
  return source;
}

// ============================================================
// STATE — keeps track of current selections and run info
// ============================================================

const state = {
  currentRunId: null,    // The run_id returned by the API after a simulation
  chartComparison: null, // Chart.js instance for the comparison bar chart
  chartSubject: null,    // Chart.js instance for the subject breakdown chart
  chartRisk: null,       // Chart.js instance for the state risk ranking chart
  policyValues: {
    option_ratio: 70,
    teaching_hours: 0,
    teacher_capacity: 0,
    coteaching: 30,
  },
  auth: {
    token: null,
    username: null,
    role_name: null,
    is_first_login: false,
  },
};

// ============================================================
// INITIALISATION — runs when the page first loads
// ============================================================

// Saved once at startup so resetAll() can restore it without hardcoding HTML
let emptyStateOriginalHTML = '';

document.addEventListener('DOMContentLoaded', () => {
  emptyStateOriginalHTML = document.getElementById('emptyState').innerHTML;
  buildGradeGrid();        // Draw the grade/form checkboxes
  initPolicyCards();       // Set up policy type radio card clicks
  renderPolicyValueArea(); // Show the input field for the default policy
  loadNegeri();            // Load states from the API
  checkHealth();           // Check if the backend is running
  initAuth();              // Show login screen until user authenticates
});

// ============================================================
// HEALTH CHECK
// ============================================================

/**
 * Calls GET /api/health and updates the status badge in the header.
 * The user can also click the badge to re-run this check.
 */
async function checkHealth() {
  setStatus('checking', t('status.checking'));
  try {
    const res  = await fetch(`${API_BASE}/api/health`);
    const data = await res.json();

    // The health endpoint returns { status: "ok"|"degraded", ... }
    const isOk = data.status === 'ok' || res.ok;
    setStatus(isOk ? 'online' : 'offline', isOk ? t('status.online') : t('status.issue'));

    if (!isOk) {
      showToast(t('toast.health.warn'), 'warning');
    }
  } catch {
    // Network error — backend is not reachable
    setStatus('offline', t('status.offline'));
    showToast(t('toast.health.err'), 'error');
  }
}

/** Updates the coloured dot and text in the header status badge */
function setStatus(state, text) {
  const dot  = document.getElementById('statusDot');
  const span = document.getElementById('statusText');
  dot.className  = `status-dot ${state}`;
  span.textContent = text;
}

// ============================================================
// FILTERS — load dropdown options from the API
// ============================================================

/**
 * Loads the list of states (negeri) from GET /api/filters/negeri
 * and populates the Negeri dropdown.
 */
async function loadNegeri() {
  try {
    const data = await apiFetch(`/api/filters/negeri`);
    const sel  = document.getElementById('selNegeri');
    // API returns { field: "negeri", values: [...] } — we need the values array
    const values = data.values ?? data;
    // Keep the "Semua Negeri" option already in HTML, add the rest
    resetSelect(sel, t('all.states'));
    values.filter(n => n !== 'SEMUA').forEach(n => {
      const opt = document.createElement('option');
      opt.value = n;
      opt.textContent = toTitleCase(n);
      sel.appendChild(opt);
    });
  } catch (error) {
    showToast(t('toast.load.negeri') + error.message, 'error');
  }
}

/**
 * Called when the user changes the Negeri dropdown.
 * Loads the PPD list for the selected state.
 */
async function onNegeriChange() {
  const negeri = document.getElementById('selNegeri').value;
  const selPPD = document.getElementById('selPPD');
  const selSek = document.getElementById('selSekolah');

  // Reset PPD and school dropdowns
  resetSelect(selPPD, t('all.ppds'));
  resetSelect(selSek, t('all.schools'));
  selSek.disabled = true;

  if (negeri === 'SEMUA') {
    selPPD.disabled = true;
    return;
  }

  selPPD.disabled = true;
  try {
    const data = await apiFetch(`/api/filters/ppd?negeri=${encodeURIComponent(negeri)}`);
    const values = data.values ?? data;
    values.forEach(p => addOption(selPPD, p, toTitleCase(p)));
    selPPD.disabled = false;
  } catch {
    showToast(t('toast.load.ppd'), 'error');
  }
}

/**
 * Called when the user changes the PPD dropdown.
 * Loads the school list for the selected negeri + PPD combination.
 */
async function onPPDChange() {
  const negeri = document.getElementById('selNegeri').value;
  const ppd    = document.getElementById('selPPD').value;
  const selSek = document.getElementById('selSekolah');

  resetSelect(selSek, t('all.schools'));
  selSek.disabled = true;

  if (ppd === 'SEMUA') return;

  try {
    const data = await apiFetch(
      `/api/filters/kod_sekolah?negeri=${encodeURIComponent(negeri)}&ppd=${encodeURIComponent(ppd)}`
    );
    const values = data.values ?? data;
    values.forEach(s => addOption(selSek, s, s));
    selSek.disabled = false;
  } catch {
    showToast(t('toast.load.school'), 'error');
  }
}

// ============================================================
// GRADE GRID — clickable chips for Darjah/Tingkatan selection
// ============================================================

/**
 * Builds the grade chip buttons (D1–D6, T1–T5) inside #gradeGrid.
 * One extra chip "Semua" is added first — selecting it toggles all grades.
 */
function buildGradeGrid() {
  const grid = document.getElementById('gradeGrid');

  // "Semua" chip — selects/deselects all grades at once
  const allChip = document.createElement('label');
  allChip.className = 'grade-chip checked';
  allChip.id = 'gradeAll';
  allChip.innerHTML = `<input type="checkbox" value="SEMUA" checked /> ${t('grade.all')}`;
  allChip.addEventListener('click', onGradeAllClick);
  grid.appendChild(allChip);

  // Individual grade chips
  ALL_GRADES.forEach(code => {
    const chip = document.createElement('label');
    chip.className = 'grade-chip';
    chip.dataset.grade = code;
    chip.innerHTML = `<input type="checkbox" value="${code}" /> ${code}`;
    chip.addEventListener('click', onGradeChipClick);
    grid.appendChild(chip);
  });
}

/** Handles clicking the "Semua" grade chip */
function onGradeAllClick(e) {
  e.preventDefault();
  const allChip = document.getElementById('gradeAll');
  const isChecked = allChip.classList.contains('checked');

  if (isChecked) {
    // Deselect all — uncheck "Semua", keep individual chips unchecked
    allChip.classList.remove('checked');
  } else {
    // Select all — check "Semua", uncheck all individual chips
    allChip.classList.add('checked');
    document.querySelectorAll('#gradeGrid .grade-chip[data-grade]').forEach(c => c.classList.remove('checked'));
  }
}

/** Handles clicking an individual grade chip (e.g. D1, T3) */
function onGradeChipClick(e) {
  e.preventDefault();
  const chip    = e.currentTarget;
  const allChip = document.getElementById('gradeAll');

  // Toggle this chip
  chip.classList.toggle('checked');

  // If any individual chip is selected, uncheck "Semua"
  const anyIndividual = [...document.querySelectorAll('#gradeGrid .grade-chip[data-grade]')]
    .some(c => c.classList.contains('checked'));

  allChip.classList.toggle('checked', !anyIndividual);
}

/**
 * Reads which grades the user has selected and returns them as an array.
 * Returns ["SEMUA"] if the "Semua" chip is checked, otherwise lists individual codes.
 */
function getSelectedGrades() {
  const allChip = document.getElementById('gradeAll');
  if (allChip.classList.contains('checked')) return ['SEMUA'];

  const selected = [...document.querySelectorAll('#gradeGrid .grade-chip[data-grade].checked')]
    .map(c => c.dataset.grade);

  // If nothing is selected, default to SEMUA
  return selected.length > 0 ? selected : ['SEMUA'];
}

// ============================================================
// POLICY CARDS — radio-style selection cards
// ============================================================

/** Sets up click handlers on all policy type cards */
function initPolicyCards() {
  document.querySelectorAll('.policy-card').forEach(card => {
    card.addEventListener('click', event => {
      event.preventDefault();
      const mode = getPolicyMode();
      const input = card.querySelector('input[name=policyType]');
      if (mode === 'single') {
        document.querySelectorAll('.policy-card').forEach(other => {
          const selected = other === card;
          other.classList.toggle('selected', selected);
          other.querySelector('input[name=policyType]').checked = selected;
        });
      } else {
        input.checked = !input.checked;
        card.classList.toggle('selected', input.checked);
      }
      renderPolicyValueArea();
    });
  });
}

function getPolicyMode() {
  return document.querySelector('input[name=policyMode]:checked')?.value || 'single';
}

function onPolicyModeChange() {
  const mode = getPolicyMode();
  document.querySelectorAll('.mode-option').forEach(option => {
    option.classList.toggle('active', option.querySelector('input').checked);
  });
  const selected = getSelectedPolicies();
  if (mode === 'single') {
    const keep = selected[0] || 'option_ratio';
    document.querySelectorAll('.policy-card').forEach(card => {
      const active = card.dataset.policy === keep;
      card.classList.toggle('selected', active);
      card.querySelector('input[name=policyType]').checked = active;
    });
    document.getElementById('policyModeHint').textContent = t('hint.single');
  } else {
    document.getElementById('policyModeHint').textContent = t('hint.combined');
  }
  renderPolicyValueArea();
}

function getSelectedPolicies() {
  return [...document.querySelectorAll('.policy-card.selected')]
    .map(card => card.dataset.policy);
}

/** Returns the currently selected policy type string (e.g. "option_ratio") */
function getSelectedPolicy() {
  return getSelectedPolicies()[0] || 'option_ratio';
}

// ============================================================
// POLICY VALUE INPUT — rendered dynamically based on policy type
// ============================================================

/**
 * Renders the appropriate input control(s) in #policyValueArea
 * based on which policy card is currently selected.
 */
function renderPolicyValueArea() {
  capturePolicyInputValues();
  const policies = getSelectedPolicies();
  document.getElementById('policyValueArea').innerHTML = policies
    .map(policyInputHTML)
    .join('');
}

function capturePolicyInputValues() {
  const option = document.getElementById('valOptionRatio');
  const hours = document.getElementById('valTeachingHours');
  const capacity = document.getElementById('valTeacherCapacity');
  const coteaching = document.getElementById('valCoteaching');
  if (option) state.policyValues.option_ratio = Number(option.value);
  if (hours) state.policyValues.teaching_hours = Number(hours.value);
  if (capacity) state.policyValues.teacher_capacity = Number(capacity.value);
  if (coteaching) state.policyValues.coteaching = Number(coteaching.value);
}

function policyInputHTML(policy) {
  switch (policy) {

    // --- Option Ratio: a percentage slider (0–100%) ---
    case 'option_ratio':
      const optionValue = state.policyValues.option_ratio;
      return `
        <div class="policy-value-group">
          <label>${t('val1.label')}</label>
          <div class="slider-group">
            <input type="range" id="valOptionRatio" min="0" max="100" value="${optionValue}" step="5"
                   oninput="document.getElementById('valOptionRatioDisplay').textContent=this.value+'%'" />
            <span class="slider-value" id="valOptionRatioDisplay">${optionValue}%</span>
          </div>
          <div class="hint">${t('val1.hint')}</div>
        </div>`;

    // --- Teaching Hours: percentage change (negative = reduce, positive = increase) ---
    case 'teaching_hours':
      return `
        <div class="policy-value-group">
          <label>${t('val2.label')}</label>
          <div class="input-with-unit">
            <input type="number" id="valTeachingHours" class="form-control" value="${state.policyValues.teaching_hours}"
                   min="-100" max="500" step="5" placeholder="0" />
            <span class="input-unit">%</span>
          </div>
          <div class="hint">${t('val2.hint')}</div>
        </div>`;

    // --- Teacher Capacity: percentage change ---
    case 'teacher_capacity':
      return `
        <div class="policy-value-group">
          <label>${t('val3.label')}</label>
          <div class="input-with-unit">
            <input type="number" id="valTeacherCapacity" class="form-control" value="${state.policyValues.teacher_capacity}"
                   min="-99" max="500" step="5" placeholder="0" />
            <span class="input-unit">%</span>
          </div>
          <div class="hint">${t('val3.hint')}</div>
        </div>`;

    // --- Co-teaching: asks the specific question about percentage of classes with two teachers ---
    case 'coteaching':
      const coteachingValue = state.policyValues.coteaching;
      return `
        <div class="policy-value-group">
          <label>${t('val4.label')}</label>
          <div class="slider-group">
            <input type="range" id="valCoteaching" min="0" max="100" value="${coteachingValue}" step="5"
                   oninput="document.getElementById('valCoteachingDisplay').textContent=this.value+'%'" />
            <span class="slider-value" id="valCoteachingDisplay">${coteachingValue}%</span>
          </div>
          <div class="hint">${t('val4.hint')}</div>
        </div>`;
    default:
      return '';
  }
}

/**
 * Reads the current policy value input and returns a partial payload object.
 * This is merged into the main simulation request.
 */
function getPolicyValues() {
  const policies = getSelectedPolicies();
  const policy = policies[0] || 'option_ratio';
  const base   = {
    policy_mode:                  getPolicyMode(),
    policy_type:                  policy,
    active_policies:              policies,
    option_ratio:                 0.70,
    teaching_hours_change_pct:    0,
    teacher_capacity_change_pct:  0,
    coteaching_share_pct:         0,
  };

  if (policies.includes('option_ratio')) {
    const raw = parseInt(document.getElementById('valOptionRatio')?.value ?? 70, 10);
    base.option_ratio = raw / 100;
  }
  if (policies.includes('teaching_hours')) {
    base.teaching_hours_change_pct = parseFloat(
      document.getElementById('valTeachingHours')?.value ?? 0
    );
  }
  if (policies.includes('teacher_capacity')) {
    base.teacher_capacity_change_pct = parseFloat(
      document.getElementById('valTeacherCapacity')?.value ?? 0
    );
  }
  if (policies.includes('coteaching')) {
    base.coteaching_share_pct = parseInt(
      document.getElementById('valCoteaching')?.value ?? 30,
      10
    );
  }
  return base;
}

// ============================================================
// FORM VALIDATION
// ============================================================

/**
 * Checks that the user's input is valid before sending the API request.
 * Returns true if everything is fine, false otherwise.
 */
function validateForm() {
  const msg     = [];
  const mode = getPolicyMode();
  const policies = getSelectedPolicies();
  const divMsg  = document.getElementById('formValidation');

  if (mode === 'single' && policies.length !== 1) {
    msg.push(t('val.single.err'));
  }
  if (mode === 'combined' && policies.length < 2) {
    msg.push(t('val.combined.err'));
  }

  if (policies.includes('teaching_hours')) {
    const v = parseFloat(document.getElementById('valTeachingHours')?.value);
    if (isNaN(v) || v < -100 || v > 500) {
      msg.push(t('val.hours.err'));
    }
  }

  if (policies.includes('teacher_capacity')) {
    const v = parseFloat(document.getElementById('valTeacherCapacity')?.value);
    if (isNaN(v) || v <= -100 || v > 500) {
      msg.push(t('val.capacity.err'));
    }
  }

  if (msg.length) {
    divMsg.innerHTML  = msg.join('<br/>');
    divMsg.style.display = 'block';
    return false;
  }

  divMsg.style.display = 'none';
  return true;
}

// ============================================================
// MAIN SIMULATION — POST /api/simulate
// ============================================================

/**
 * Builds the request payload from all current form selections,
 * sends it to POST /api/simulate, and renders the results.
 */
async function runSimulation() {
  if (!validateForm()) return;

  // Build the complete request body
  const payload = {
    target_year:        2027,
    subject:            document.getElementById('selSubject').value,
    negeri:             document.getElementById('selNegeri').value,
    ppd:                document.getElementById('selPPD').value,
    kod_sekolah:        document.getElementById('selSekolah').value,
    kodtingkatantahun:  getSelectedGrades(),
    lang:               (typeof getLang === 'function' ? getLang() : 'en'),
    ...getPolicyValues(),
  };

  // Show loading state
  setSimulateLoading(true);
  showLoading(t('loading.sim'));

  try {
    const data = await apiFetch('/api/simulate', { method:'POST', body: payload });
    state.currentRunId = data.artifacts?.run_id ?? null;
    renderResults(data, payload);
    showToast(t('toast.sim.ok'), 'success');
  } catch (err) {
    showLoading(null); // Hide loader
    showError(`Simulation failed: ${err.message}`);
  } finally {
    setSimulateLoading(false);
  }
}

/** Re-runs an archived scenario (from the "Simulasi Saya" list) through the
 *  normal simulate → render → PDF pipeline, so a Policy Maker can get back a
 *  report for a scenario they ran earlier without re-configuring the sidebar.
 *  Switches to the dashboard first — Chart.js needs a real, visible-sized
 *  canvas to draw into, so this cannot happen invisibly in the background
 *  (see the comments on downloadSummaryPDF for the related, already-fixed
 *  cold-render failure mode this would otherwise risk repeating). */
async function downloadPdfForRun(scenario) {
  goToDashboard();
  showLoading(t('loading.sim'));

  const payload = { ...scenario, lang: (typeof getLang === 'function' ? getLang() : 'en') };

  try {
    const data = await apiFetch('/api/simulate', { method: 'POST', body: payload });
    state.currentRunId = data.artifacts?.run_id ?? null;
    renderResults(data, payload);

    // Chart.js animates new charts in (~1s by default) — wait for that to
    // finish before html2canvas captures them, otherwise the PDF can contain
    // a mid-animation frame with partially-drawn bars.
    await new Promise(resolve => setTimeout(resolve, 1200));
    await downloadSummaryPDF();
  } catch (err) {
    showLoading(null);
    showError(`Failed to regenerate report: ${err.message}`);
  }
}

// ============================================================
// AI AGENT — POST /api/agent/run
// ============================================================

/**
 * Takes the natural-language question from the text input,
 * sends it to the AI agent endpoint, and shows the result.
 */
async function runAgent() {
  const question = document.getElementById('agentQuestion').value.trim();
  if (!question) {
    showToast(t('toast.no.question'), 'warning');
    return;
  }

  const btn = document.getElementById('btnAgent');
  setButtonLoading(btn, true);

  // Show a loading indicator inside the agent section
  document.getElementById('agentResult').classList.remove('visible');
  showLoading(t('loading.agent'));

  try {
    const data = await apiFetch('/api/agent/run', {
      method: 'POST',
      body: { question, lang: (typeof getLang === 'function' ? getLang() : 'en') }
    });

    state.currentRunId = data.artifacts?.run_id ?? null;

    // Render the full results just like a direct simulation
    renderResults(data, data.scenario ?? {});

    // Also show explanation and trace in the agent section
    showAgentResult(data);
    showToast(t('toast.agent.ok'), 'success');
  } catch (err) {
    showLoading(null);
    showError(`AI agent failed: ${err.message}`);
  } finally {
    setButtonLoading(btn, false);
  }
}

/** Fills in the agent text box with an example question when a chip is clicked */
function setAgentQuestion(chip) {
  document.getElementById('agentQuestion').value = chip.textContent.trim();
  document.getElementById('agentQuestion').focus();
}

/** Renders the agent trace steps in the agent result box.
 *  The explanation text itself is intentionally not duplicated here —
 *  it already appears in the "Ringkasan Bahasa Mudah" card via renderResults(). */
function showAgentResult(data) {
  const box = document.getElementById('agentResult');
  box.classList.add('visible');

  // Agent trace steps (shows which agents were called)
  const traceEl = document.getElementById('agentTrace');
  traceEl.innerHTML = '';
  (data.agent_trace || []).forEach(step => {
    const span = document.createElement('span');
    span.className = 'trace-step';
    span.textContent = step;
    traceEl.appendChild(span);
  });
}

// ============================================================
// RENDER RESULTS — builds all UI components from API response
// ============================================================

/**
 * Main function that takes the API response object and updates
 * all result sections: KPI cards, charts, table, explanation.
 * @param {Object} data    — full response from /api/simulate or /api/agent/run
 * @param {Object} payload — the scenario parameters that were sent
 */
function renderResults(data, payload) {
  const { summary, subject_summary, top_recommendations, rules, explanation,
          explanation_source, artifacts, policy_impacts } = data;

  // Kept so the PDF report can rebuild its own parameters/KPI sections
  // (rather than copying the dashboard's dark-themed HTML, which html2canvas
  // renders inconsistently on the report's white background — see
  // buildPdfKpiHtml for details).
  state.lastPayload = payload;
  state.lastSummary = summary;
  state.lastTopRecommendations = top_recommendations;

  // Hide loader and show results area
  showLoading(null);
  document.getElementById('emptyState').style.display    = 'none';
  document.getElementById('resultsWrapper').classList.add('visible');

  // --- Scenario Banner ---
  renderScenarioBanner(payload, data);

  // --- KPI Cards ---
  renderKPICards(summary, payload, top_recommendations);
  renderDecisionInsight(summary, payload);

  // --- Charts ---
  renderComparisonChart(summary, subject_summary, payload);
  renderSubjectChart(subject_summary);
  renderRiskRankingChart(top_recommendations);
  renderSubjectChips(subject_summary, payload);
  renderPolicyImpacts(policy_impacts || [], summary, payload);

  // --- Explanation ---
  const expBox = document.getElementById('explanationBox');
  const _noExp = _uiLang() === 'bm' ? 'Tiada penjelasan tersedia.' : 'No explanation available.';
  const _srcLabel = _uiLang() === 'bm' ? 'Sumber' : 'Source';
  expBox.innerHTML = (explanation || _noExp).replace(/\n/g, '<br/>');
  if (explanation_source) {
    const sourceText = formatExplanationSource(explanation_source);
    expBox.innerHTML += `<span class="explanation-source">${_srcLabel}: ${sourceText}</span>`;
  }

  // --- Rules ---
  const rulesList = document.getElementById('rulesList');
  rulesList.innerHTML = '';
  (rules || []).forEach(rule => {
    const li = document.createElement('li');
    li.textContent = rule;
    rulesList.appendChild(li);
  });

  // --- Recommendation Table ---
  renderRecTable(top_recommendations || []);

  // --- Show download buttons if we have a run_id ---
  const btnDl = document.getElementById('btnDownload');
  const btnDlSummary = document.getElementById('btnDownloadSummary');
  const btnDlSummaryCsv = document.getElementById('btnDownloadSummaryCsv');
  if (artifacts?.run_id) {
    state.currentRunId = artifacts.run_id;
    btnDl.style.display = state.auth.role_name === 'user' ? 'none' : 'inline-flex';
    btnDlSummary.style.display = 'inline-flex';
    btnDlSummaryCsv.style.display = 'inline-flex';
  } else {
    btnDl.style.display = 'none';
    btnDlSummary.style.display = 'none';
    btnDlSummaryCsv.style.display = 'none';
  }

  // Scroll to results
  document.getElementById('resultsWrapper').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/** Shows a one-line summary of what scenario was simulated */
function renderScenarioBanner(payload, data) {
  const banner = document.getElementById('scenarioBanner');
  const activePolicies = payload.active_policies?.length
    ? payload.active_policies
    : [payload.policy_type].filter(Boolean);
  const policyLabels = getPolicyLabels();
  const policy = activePolicies.map(value => policyLabels[value] || value).join(' + ') || '—';
  const subject = payload.subject === 'SEMUA' ? t('all.subjects') : formatSubject(payload.subject);
  const negeri  = payload.negeri  === 'SEMUA' ? t('all.states') : toTitleCase(payload.negeri || '');
  const sourceText = formatScenarioSource(data.scenario_source);
  const src = sourceText ? ` &nbsp;|&nbsp; <em>${sourceText}</em>` : '';

  const policyNote = payload.policy_mode !== 'combined' && payload.policy_type === 'option_ratio'
    ? `<br/><small>${t('sim.opt.note')}</small>`
    : '';
  banner.innerHTML = t('sim.banner', subject, negeri, policy) + src + policyNote;
  banner.classList.add('visible');
}

/** Builds the row of KPI metric cards at the top of results */
function getHighestRiskState(topRecommendations) {
  const stateTotals = {};
  (topRecommendations || []).forEach(row => {
    const state = row.negeri ? toTitleCase(row.negeri) : 'Unknown';
    const gap = Math.round(row.scenario_teacher_gap ?? 0);
    stateTotals[state] = (stateTotals[state] || 0) + gap;
  });
  const entries = Object.entries(stateTotals).sort((a, b) => b[1] - a[1]);
  return entries.length ? entries[0][0] : '—';
}

function renderKPICards(summary, payload = {}, topRecommendations = []) {
  const grid = document.getElementById('kpiGrid');
  grid.innerHTML = '';

  if (!summary) return;

  // Helper: create one card
  const card = (label, value, subLabel, colorClass) => {
    const numVal = typeof value === 'number' ? Math.round(value) : (value ?? '—');
    const valClass = typeof numVal === 'number'
      ? (numVal > 0 ? '' : numVal < 0 ? 'negative' : '')
      : '';
    return `
      <div class="kpi-card ${colorClass || ''}">
        <div class="kpi-label">${label}</div>
        <div class="kpi-value ${valClass}">${typeof numVal === 'number' ? numVal.toLocaleString('en-MY') : numVal}</div>
        <div class="kpi-sublabel">${subLabel || ''}</div>
      </div>`;
  };

  const base           = summary.baseline_required_2027   ?? 0;
  const available      = summary.available_2027_assumption ?? 0;
  const scenario       = summary.scenario_required_2027   ?? 0;
  const scenarioGap    = summary.scenario_teacher_gap      ?? 0;
  const optionGap      = summary.scenario_option_gap       ?? 0;
  const delta          = summary.change_required          ?? (scenario - base);
  const highestState   = getHighestRiskState(topRecommendations);

  const deltaText = delta > 0
    ? t('kpi.delta.inc')
    : delta < 0
      ? t('kpi.delta.dec')
      : t('kpi.delta.none');

  let cards =
    card(t('kpi.base.label'), base, t('kpi.base.sub'), '') +
    card(t('kpi.available.label'), available, t('kpi.available.sub'), 'teal') +
    card(t('kpi.shortage.label'), scenarioGap, t('kpi.shortage.sub'), scenarioGap > 0 ? 'red' : 'green') +
    card(t('kpi.optiongap.label'), optionGap, t('kpi.optiongap.sub'), optionGap > 0 ? 'amber' : 'green') +
    card(t('kpi.higheststate.label'), highestState, t('kpi.higheststate.sub'), 'amber') +
    card(t('kpi.policyimpact.label'), delta, deltaText, delta > 0 ? 'amber' : 'green');

  const activePolicies = payload.active_policies?.length
    ? payload.active_policies
    : [payload.policy_type].filter(Boolean);
  const includesOptionPolicy = activePolicies.includes('option_ratio');

  if (includesOptionPolicy) {
    const baselineOptGap = summary.baseline_option_gap ?? 0;
    const scenarioOptGap = summary.scenario_option_gap ?? 0;
    const optionChange   = summary.change_option_gap ?? (scenarioOptGap - baselineOptGap);
    const targetPct      = Math.round((payload.option_ratio ?? 0.90) * 100);
    const optionChangeText = optionChange < 0
      ? t('kpi.opt.chg.dec', Math.abs(optionChange).toLocaleString('en-MY'))
      : optionChange > 0
        ? t('kpi.opt.chg.inc', optionChange.toLocaleString('en-MY'))
        : t('kpi.opt.chg.none');

    cards +=
      card(t('kpi.opt.base.label'), baselineOptGap, t('kpi.opt.base.sub'), 'amber') +
      card(t('kpi.opt.scen.label', targetPct), scenarioOptGap, t('kpi.opt.scen.sub'), scenarioOptGap > 0 ? 'amber' : 'green') +
      card(t('kpi.opt.chg.label'), optionChange, optionChangeText, optionChange > 0 ? 'red' : 'green');
  }

  grid.innerHTML = cards;
}

function renderRiskRankingChart(topRecommendations) {
  const ctx = document.getElementById('chartRisk').getContext('2d');
  if (state.chartRisk) state.chartRisk.destroy();

  const aggregated = {};
  (topRecommendations || []).forEach(row => {
    const state = row.negeri ? toTitleCase(row.negeri) : 'Unknown';
    const gap   = Math.round(row.scenario_teacher_gap ?? 0);
    if (!aggregated[state]) aggregated[state] = 0;
    aggregated[state] += gap;
  });

  const rows = Object.entries(aggregated)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);

  const labels = rows.map(r => r[0]);
  const data   = rows.map(r => r[1]);

  state.chartRisk = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: t('chart.risk.label'),
        data,
        backgroundColor: 'rgba(232,160,32,0.85)',
        borderColor: 'rgba(232,160,32,1)',
        borderWidth: 1,
        borderRadius: 4,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.parsed.x.toLocaleString('en-MY')} teachers`,
          }
        }
      },
      scales: {
        x: {
          beginAtZero: true,
          ticks: { callback: v => v.toLocaleString('en-MY') }
        }
      }
    }
  });
}

/** Explains the relationship between demand, policy impact and shortage. */
function renderDecisionInsight(summary, payload = {}) {
  const box = document.getElementById('decisionInsight');
  if (!box || !summary) return;

  const base = summary.baseline_required_2027 ?? 0;
  const scenario = summary.scenario_required_2027 ?? 0;
  const delta = summary.change_required ?? (scenario - base);
  const baselineGap = summary.baseline_teacher_gap ?? 0;
  const scenarioGap = summary.scenario_teacher_gap ?? 0;
  const gapChange = summary.change_teacher_gap ?? (scenarioGap - baselineGap);
  const fmt = value => Math.abs(Math.round(value)).toLocaleString('en-MY');

  const demandSentence = delta > 0
    ? t('insight.demand.inc', fmt(delta), fmt(scenario))
    : delta < 0
      ? t('insight.demand.dec', fmt(delta), fmt(scenario))
      : t('insight.demand.same', fmt(scenario));

  const gapSentence = gapChange > 0
    ? t('insight.gap.inc', fmt(baselineGap), fmt(scenarioGap), fmt(gapChange))
    : gapChange < 0
      ? t('insight.gap.dec', fmt(baselineGap), fmt(scenarioGap), fmt(gapChange))
      : t('insight.gap.same', fmt(scenarioGap));

  const actionSentence = scenarioGap > 0
    ? t('insight.action.pos', fmt(scenarioGap))
    : t('insight.action.ok');

  box.innerHTML = `
    <div class="decision-insight-title">${t('insight.title')}</div>
    <p>${t('insight.rf', fmt(base))} ${demandSentence}</p>
    <p>${gapSentence}</p>
    <p class="decision-action"><strong>${t('insight.action.lbl')}</strong> ${actionSentence}</p>`;
}

/** Renders the bar chart comparing baseline vs scenario totals */
function renderComparisonChart(summary, subjectSummary, payload = {}) {
  const ctx = document.getElementById('chartComparison').getContext('2d');

  // Destroy old chart instance to avoid canvas reuse errors
  if (state.chartComparison) state.chartComparison.destroy();

  // Build labels and data from subject_summary rows, or fallback to totals
  const rows   = subjectSummary || [];
  const activePolicies = payload.active_policies?.length
    ? payload.active_policies
    : [payload.policy_type].filter(Boolean);
  const isOptionPolicy = payload.policy_mode !== 'combined'
    && activePolicies.length === 1
    && activePolicies.includes('option_ratio');
  const targetPct = Math.round((payload.option_ratio ?? 0.90) * 100);
  const titleEl = document.getElementById('comparisonChartTitle');
  if (titleEl) {
    titleEl.textContent = isOptionPolicy
      ? `📊 ${t('option.chart.title')}`
      : `📊 ${t('normal.chart.title')}`;
  }
  // subject_summary rows use "subjek" (Malay), not "subject"
  const labels = rows.length
    ? rows.map(r => formatSubject(r.subjek || 'Unknown'))
    : ['Total'];

  const baseData = rows.length
    ? rows.map(r => Math.round(
        isOptionPolicy ? (r.baseline_option_gap ?? 0) : (r.baseline_required_2027 ?? 0)
      ))
    : [Math.round(
        isOptionPolicy ? (summary?.baseline_option_gap ?? 0) : (summary?.baseline_required_2027 ?? 0)
      )];

  const scenData = rows.length
    ? rows.map(r => Math.round(
        isOptionPolicy ? (r.scenario_option_gap ?? 0) : (r.scenario_required_2027 ?? 0)
      ))
    : [Math.round(
        isOptionPolicy ? (summary?.scenario_option_gap ?? 0) : (summary?.scenario_required_2027 ?? 0)
      )];

  state.chartComparison = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: isOptionPolicy ? t('chart.base.label') : t('chart.rf.label'),
          data: baseData,
          backgroundColor: 'rgba(35,86,160,0.75)',
          borderColor: 'rgba(35,86,160,1)',
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: isOptionPolicy ? t('chart.scen.label', targetPct) : t('chart.policy.label'),
          data: scenData,
          backgroundColor: 'rgba(15,124,124,0.75)',
          borderColor: 'rgba(15,124,124,1)',
          borderWidth: 1,
          borderRadius: 4,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString('en-MY')} teachers`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { callback: v => v.toLocaleString('en-MY') }
        }
      }
    }
  });
}

/** Renders the subject breakdown bar chart */
function renderSubjectChart(subjectSummary) {
  const ctx = document.getElementById('chartSubject').getContext('2d');
  if (state.chartSubject) state.chartSubject.destroy();

  const rows = subjectSummary || [];
  if (!rows.length) return;

  const labels   = rows.map(r => formatSubject(r.subjek || '—'));
  const gapData  = rows.map(r => Math.round(r.scenario_teacher_gap ?? 0));
  const optData  = rows.map(r => Math.round(r.scenario_option_gap  ?? 0));

  state.chartSubject = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: t('kpi.scen.gap.label'),
          data: gapData,
          backgroundColor: 'rgba(185,32,32,0.75)',
          borderColor: 'rgba(185,32,32,1)',
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: t('th.opt.shortage'),
          data: optData,
          backgroundColor: 'rgba(232,160,32,0.75)',
          borderColor: 'rgba(232,160,32,1)',
          borderWidth: 1,
          borderRadius: 4,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString('en-MY')} teachers`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { callback: v => v.toLocaleString('en-MY') }
        }
      }
    }
  });
}

/** Renders small summary chips per subject below the subject chart */
function renderSubjectChips(subjectSummary, payload = {}) {
  const container = document.getElementById('subjectChips');
  container.innerHTML = '';
  (subjectSummary || []).forEach(row => {
    const chip = document.createElement('div');
    chip.className = 'subject-chip';
    const activePolicies = payload.active_policies?.length
      ? payload.active_policies
      : [payload.policy_type].filter(Boolean);
    const isOptionOnly = payload.policy_mode !== 'combined'
      && activePolicies.length === 1
      && activePolicies.includes('option_ratio');
    if (isOptionOnly) {
      const targetPct = Math.round((payload.option_ratio ?? 0.90) * 100);
      chip.innerHTML = `
        <div class="sc-name">${formatSubject(row.subjek || '—')}</div>
        <div class="sc-row">
          <span>${t('chart.base.label')}:</span>
          <span class="sc-val">${Math.round(row.baseline_option_gap ?? 0).toLocaleString('en-MY')}</span>
        </div>
        <div class="sc-row">
          <span>${t('chart.scen.label', targetPct)}:</span>
          <span class="sc-val">${Math.round(row.scenario_option_gap ?? 0).toLocaleString('en-MY')}</span>
        </div>`;
      container.appendChild(chip);
      return;
    }
    chip.innerHTML = `
      <div class="sc-name">${formatSubject(row.subjek || '—')}</div>
      <div class="sc-row">
        <span>${t('chart.rf.label')}:</span>
        <span class="sc-val">${Math.round(row.baseline_required_2027 ?? 0).toLocaleString('en-MY')}</span>
      </div>
      <div class="sc-row">
        <span>${t('chart.policy.label')}:</span>
        <span class="sc-val">${Math.round(row.scenario_required_2027 ?? 0).toLocaleString('en-MY')}</span>
      </div>
      <div class="sc-row">
        <span>${t('kpi.scen.gap.label')}:</span>
        <span class="sc-val" style="color:var(--danger)">${Math.round(row.scenario_teacher_gap ?? 0).toLocaleString('en-MY')}</span>
      </div>`;
    container.appendChild(chip);
  });
}

function renderPolicyImpacts(impacts, combinedSummary, payload = {}) {
  const card = document.getElementById('policyImpactCard');
  const body = document.getElementById('policyImpactBody');
  const isCombined = payload.policy_mode === 'combined';
  if (!isCombined || !impacts.length) {
    card.style.display = 'none';
    body.innerHTML = '';
    return;
  }

  const policyLabels = getPolicyLabels();
  const rows = [
    ...impacts.map(item => ({
      label: policyLabels[item.policy] || item.policy,
      ...item,
    })),
    {
      label: t('all.policies.combined'),
      scenario_required_2027: combinedSummary.scenario_required_2027,
      change_required: combinedSummary.change_required,
      scenario_teacher_gap: combinedSummary.scenario_teacher_gap,
      scenario_option_gap: combinedSummary.scenario_option_gap,
      combined: true,
    },
  ];

  body.innerHTML = rows.map(row => {
    const change = Math.round(row.change_required ?? 0);
    const changeLabel = change > 0 ? `+${change}` : `${change}`;
    return `
      <tr class="${row.combined ? 'combined-impact-row' : ''}">
        <td><strong>${row.label}</strong></td>
        <td>${Math.round(row.scenario_required_2027 ?? 0).toLocaleString('en-MY')}</td>
        <td>${changeLabel}</td>
        <td>${Math.round(row.scenario_teacher_gap ?? 0).toLocaleString('en-MY')}</td>
        <td>${Math.round(row.scenario_option_gap ?? 0).toLocaleString('en-MY')}</td>
      </tr>`;
  }).join('');
  card.style.display = 'block';
}

/** Renders the recommendation priority table */
function renderRecTable(rows) {
  const tbody   = document.getElementById('recTableBody');
  const infoEl  = document.getElementById('tableInfo');
  tbody.innerHTML = '';

  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align:center;color:var(--text-muted);padding:20px;">${t('table.no.data')}</td></tr>`;
    infoEl.textContent = '';
    return;
  }

  rows.forEach((row, i) => {
    const tr = document.createElement('tr');
    const gap  = Math.round(row.scenario_teacher_gap ?? 0);
    const base = Math.round(row.baseline_required_2027 ?? 0);
    const scen = Math.round(row.scenario_required_2027 ?? 0);
    const pri  = row.priority_label || 'RENDAH';
    tr.innerHTML = `
      <td>${i + 1}</td>
      <td><strong>${row.kod_sekolah || '—'}</strong></td>
      <td>${toTitleCase(row.negeri || '—')}</td>
      <td>${toTitleCase(row.ppd    || '—')}</td>
      <td>${formatSubject(row.subjek || '—')}</td>
      <td style="text-align:right">${base.toLocaleString('en-MY')}</td>
      <td style="text-align:right">${scen.toLocaleString('en-MY')}</td>
      <td style="text-align:right; color:var(--danger); font-weight:700">${gap.toLocaleString('en-MY')}</td>
      <td><span class="priority-badge ${pri}">${getPriorityLabel(pri)}</span></td>
      <td>${row.recommended_action || 'Continue monitoring'}</td>`;
    tbody.appendChild(tr);
  });

  infoEl.textContent = t('table.showing.n', rows.length);
}

// ============================================================
// CSV DOWNLOAD — GET /api/runs/{run_id}/detail.csv
// ============================================================

/**
 * Downloads the detail CSV file for the last completed simulation run.
 * The browser will prompt a file save dialog automatically.
 */
async function downloadCSV() {
  if (!state.currentRunId) {
    showToast('No simulation result is available for download.', 'warning');
    return;
  }

  const url = `${API_BASE}/api/runs/${state.currentRunId}/detail.csv`;

  try {
    // Fetch the CSV as raw text
    const res = await fetch(url, { headers: state.auth?.token ? { 'X-Auth-Token': state.auth.token } : {} });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const text = await res.text();

    // Create a temporary download link and trigger it
    const blob = new Blob([text], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href     = URL.createObjectURL(blob);
    link.download = `simulation_2027_${state.currentRunId}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);

    showToast(t('toast.csv.ok'), 'success');
  } catch (err) {
    showToast(`Failed to download CSV: ${err.message}`, 'error');
  }
}

/**
 * Downloads the summary CSV file for the last completed simulation run.
 */
async function downloadSummaryCSV() {
  if (!state.currentRunId) {
    showToast('No simulation result is available for download.', 'warning');
    return;
  }
  const url = `${API_BASE}/api/runs/${state.currentRunId}/summary.csv`;
  try {
    const res = await fetch(url, { headers: state.auth?.token ? { 'X-Auth-Token': state.auth.token } : {} });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const text = await res.text();
    const blob = new Blob([text], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `simulation_2027_summary_${state.currentRunId}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
    showToast(t('toast.csv.ok'), 'success');
  } catch (err) {
    showToast(`Failed to download summary CSV: ${err.message}`, 'error');
  }
}

/** Builds the "Simulation Parameters" HTML block for the PDF report from the last run's payload. */
function buildPdfParamsHtml(payload) {
  if (!payload) return '';
  const lang = _uiLang();
  const row = (label, value) => `
    <div class="pdf-param-row">
      <span class="pdf-param-label">${label}</span>
      <span class="pdf-param-value">${value}</span>
    </div>`;

  const allLabel = lang === 'bm' ? 'Semua' : 'All';
  const scopeSubject = payload.subject === 'SEMUA' || !payload.subject ? t('all.subjects') : formatSubject(payload.subject);
  const scopeNegeri  = payload.negeri  === 'SEMUA' || !payload.negeri  ? t('all.states')   : toTitleCase(payload.negeri);
  const scopePPD     = payload.ppd     === 'SEMUA' || !payload.ppd     ? allLabel           : toTitleCase(payload.ppd);
  const scopeSchool  = payload.kod_sekolah === 'SEMUA' || !payload.kod_sekolah ? allLabel   : payload.kod_sekolah;
  const grades = payload.kodtingkatantahun;
  const scopeGrades  = (!grades || !grades.length || grades[0] === 'SEMUA')
    ? allLabel
    : grades.join(', ');

  const modeLabel = payload.policy_mode === 'combined'
    ? (lang === 'bm' ? 'Gabungan' : 'Combined')
    : (lang === 'bm' ? 'Tunggal' : 'Single');

  const policyLabels = getPolicyLabels();
  const activePolicies = payload.active_policies?.length
    ? payload.active_policies
    : [payload.policy_type].filter(Boolean);
  const policyNames = activePolicies.map(p => policyLabels[p] || p).join(', ') || '—';

  let scopeRows =
    row(t('label.subject'), scopeSubject) +
    row(t('label.state'), scopeNegeri) +
    row(t('label.ppd'), scopePPD) +
    row(t('label.school'), scopeSchool) +
    row(t('label.grade'), scopeGrades);

  let policyRows =
    row(lang === 'bm' ? 'Mod Dasar' : 'Policy Mode', modeLabel) +
    row(lang === 'bm' ? 'Dasar Aktif' : 'Active Policies', policyNames);

  if (activePolicies.includes('option_ratio')) {
    policyRows += row(t('val1.label'), `${Math.round((payload.option_ratio ?? 0.7) * 100)}%`);
  }
  if (activePolicies.includes('teaching_hours')) {
    policyRows += row(t('val2.label'), `${payload.teaching_hours_change_pct ?? 0}%`);
  }
  if (activePolicies.includes('teacher_capacity')) {
    policyRows += row(t('val3.label'), `${payload.teacher_capacity_change_pct ?? 0}%`);
  }
  if (activePolicies.includes('coteaching')) {
    policyRows += row(t('val4.label'), `${payload.coteaching_share_pct ?? 0}%`);
  }

  return `
    <div class="pdf-params-subtitle">${lang === 'bm' ? 'Skop Analisis' : 'Analysis Scope'}</div>
    <div class="pdf-params-grid">${scopeRows}</div>
    <div class="pdf-params-subtitle" style="margin-top:16px;">${lang === 'bm' ? 'Tetapan Dasar' : 'Policy Settings'}</div>
    <div class="pdf-params-grid">${policyRows}</div>`;
}

/**
 * Builds the PDF report's own KPI cards from the raw summary data, using the
 * light-themed `.pdf-kpi-card` styles (plain hex colors, no CSS custom
 * properties). This is deliberate, not copied from `renderKPICards`'s
 * `.kpi-card` markup: html2canvas renders that dark, CSS-variable-driven
 * card style inconsistently once the report gets tall enough (KPI cards
 * come out washed out/illegible on some captures) — using plain hex colors
 * in a dedicated PDF-only template avoids that entirely.
 */
function buildPdfKpiHtml(summary, payload, topRecommendations) {
  if (!summary) return '';
  const card = (label, value, subLabel, colorClass) => {
    const numVal = typeof value === 'number' ? Math.round(value) : (value ?? '—');
    const valClass = typeof numVal === 'number'
      ? (numVal > 0 ? 'positive' : numVal < 0 ? 'negative' : '')
      : '';
    return `
      <div class="pdf-kpi-card ${colorClass || ''}">
        <h4>${label}</h4>
        <div class="pdf-kpi-value ${valClass}">${typeof numVal === 'number' ? numVal.toLocaleString('en-MY') : numVal}</div>
        <div class="pdf-kpi-sub">${subLabel || ''}</div>
      </div>`;
  };

  const base           = summary.baseline_required_2027   ?? 0;
  const available      = summary.available_2027_assumption ?? 0;
  const scenario       = summary.scenario_required_2027   ?? 0;
  const scenarioGap    = summary.scenario_teacher_gap      ?? 0;
  const optionGap      = summary.scenario_option_gap       ?? 0;
  const delta          = summary.change_required          ?? (scenario - base);
  const highestState   = getHighestRiskState(topRecommendations);

  const deltaText = delta > 0
    ? t('kpi.delta.inc')
    : delta < 0
      ? t('kpi.delta.dec')
      : t('kpi.delta.none');

  let cards =
    card(t('kpi.base.label'), base, t('kpi.base.sub'), '') +
    card(t('kpi.available.label'), available, t('kpi.available.sub'), 'teal') +
    card(t('kpi.shortage.label'), scenarioGap, t('kpi.shortage.sub'), scenarioGap > 0 ? 'red' : 'green') +
    card(t('kpi.optiongap.label'), optionGap, t('kpi.optiongap.sub'), optionGap > 0 ? 'amber' : 'green') +
    card(t('kpi.higheststate.label'), highestState, t('kpi.higheststate.sub'), 'amber') +
    card(t('kpi.policyimpact.label'), delta, deltaText, delta > 0 ? 'amber' : 'green');

  const activePolicies = payload?.active_policies?.length
    ? payload.active_policies
    : [payload?.policy_type].filter(Boolean);
  const includesOptionPolicy = activePolicies.includes('option_ratio');

  if (includesOptionPolicy) {
    const baselineOptGap = summary.baseline_option_gap ?? 0;
    const scenarioOptGap = summary.scenario_option_gap ?? 0;
    const optionChange   = summary.change_option_gap ?? (scenarioOptGap - baselineOptGap);
    const targetPct      = Math.round((payload.option_ratio ?? 0.90) * 100);
    const optionChangeText = optionChange < 0
      ? t('kpi.opt.chg.dec', Math.abs(optionChange).toLocaleString('en-MY'))
      : optionChange > 0
        ? t('kpi.opt.chg.inc', optionChange.toLocaleString('en-MY'))
        : t('kpi.opt.chg.none');

    cards +=
      card(t('kpi.opt.base.label'), baselineOptGap, t('kpi.opt.base.sub'), 'amber') +
      card(t('kpi.opt.scen.label', targetPct), scenarioOptGap, t('kpi.opt.scen.sub'), scenarioOptGap > 0 ? 'amber' : 'green') +
      card(t('kpi.opt.chg.label'), optionChange, optionChangeText, optionChange > 0 ? 'red' : 'green');
  }

  return cards;
}

/**
 * Generates and downloads a beautifully formatted PDF report of the summary.
 */
async function downloadSummaryPDF() {
  if (!state.currentRunId) {
    showToast('No simulation result is available for download.', 'warning');
    return;
  }
  
  showToast(t('toast.pdf.generating') || 'Menjana PDF...', 'success');
  
  // Set date
  const dateObj = new Date();
  document.getElementById('pdfDate').innerText = dateObj.toLocaleDateString('ms-MY', { year: 'numeric', month: 'long', day: 'numeric' });
  
  // Simulation parameters (scope + policy settings used for this run)
  document.getElementById('pdfParams').innerHTML = buildPdfParamsHtml(state.lastPayload);

  // Explanation text
  const explanationHtml = document.getElementById('explanationBox').innerHTML;
  document.getElementById('pdfExplanation').innerHTML = explanationHtml;

  // KPI Grid — built from raw data (see buildPdfKpiHtml for why), not copied
  // from the dashboard's #kpiGrid.
  document.getElementById('pdfKpiGrid').innerHTML =
    buildPdfKpiHtml(state.lastSummary, state.lastPayload, state.lastTopRecommendations);
  
  // Convert charts to images
  const chartCompCanvas = document.getElementById('chartComparison');
  const pdfChartComparisonImg = document.getElementById('pdfChartComparison');
  if (chartCompCanvas) {
    pdfChartComparisonImg.src = chartCompCanvas.toDataURL('image/png', 1.0);
  }

  const chartSubjCanvas = document.getElementById('chartSubject');
  const pdfChartSubjectImg = document.getElementById('pdfChartSubject');
  if (chartSubjCanvas) {
    pdfChartSubjectImg.src = chartSubjCanvas.toDataURL('image/png', 1.0);
  }

  const element = document.getElementById('pdfContent');

  // Make it momentarily visible so html2canvas can render it correctly.
  // Uses `position: fixed` (viewport-relative), not `absolute` (document-relative):
  // the download button sits near the bottom of a long scrollable results page, so
  // clicking it scrolls the page down first. An absolutely-positioned element pinned
  // to document (0,0) then sits far above the current scroll position — html2canvas
  // captures relative to the current viewport and produces a near-blank result in
  // that case. `fixed` keeps it at the viewport's origin regardless of scroll offset.
  // A high (not negative) z-index is required too: stacking the template behind the
  // dark dashboard/animated background canvas produced a washed-out capture (compositing
  // artifact from the layers behind it), even though the underlying content was correct.
  // Placing it on top very briefly — for the handful of milliseconds this function
  // runs — is a fine trade-off since it's hidden again in the `finally` block below.
  const pdfTemplate = document.getElementById('pdfTemplate');
  pdfTemplate.style.display = 'block';
  pdfTemplate.style.position = 'fixed';
  pdfTemplate.style.left = '0';
  pdfTemplate.style.top = '0';
  pdfTemplate.style.zIndex = '999999';
  // 794px ≈ the full A4 page width (8.27in * 96 CSS px/in), because the 2.54cm
  // margin is applied as real CSS padding on .pdf-container (see styles.css)
  // rather than via html2pdf's own `margin` option below (which is left at 0).
  // html2pdf's `margin` option has a real bug in this version: it scales the
  // captured content to the FULL page width regardless of the margin value,
  // then shifts it right by the margin — clipping that same amount off the
  // right edge, no matter how narrow the source content is. Baking the
  // margin in as padding sidesteps that bug entirely (confirmed: margin: 0
  // renders with no clipping, at any content width).
  pdfTemplate.style.width = '794px';

  // Wait for the browser to actually paint the newly-shown template, then
  // explicitly wait for the chart <img> data URIs to finish decoding before
  // html2canvas captures it. On a freshly loaded page, this is the FIRST
  // time these <img> elements ever get a src — decoding a large data URI
  // for the first time is genuinely async and not guaranteed to finish
  // within a fixed number of animation frames, unlike a warm/cached decode
  // on a repeat run. Without awaiting decode() here, the capture races the
  // decode and produces a near-blank PDF (reproduced reliably on cold page loads).
  await new Promise(resolve => requestAnimationFrame(resolve));
  await Promise.all([
    pdfChartComparisonImg.src ? pdfChartComparisonImg.decode().catch(() => {}) : Promise.resolve(),
    pdfChartSubjectImg.src ? pdfChartSubjectImg.decode().catch(() => {}) : Promise.resolve(),
  ]);

  const opt = {
    // 0, not 1in — the 2.54cm margin is applied as real CSS padding on
    // .pdf-container instead (see the width comment above for why).
    margin:       0,
    filename:     `simulation_2027_report_${state.currentRunId}.pdf`,
    image:        { type: 'jpeg', quality: 0.98 },
    // scrollX/scrollY: 0 is required here — html2canvas computes the capture
    // region using the page's current scroll offset by default, but this button
    // sits near the bottom of a long scrollable results page, so the page is
    // already scrolled down when this runs. Without pinning these to 0, the
    // capture region is offset by the scroll amount and grabs mostly blank
    // space instead of the (position:fixed, viewport-pinned) template.
    html2canvas:  { scale: 2, useCORS: true, scrollX: 0, scrollY: 0 },
    jsPDF:        { unit: 'in', format: 'a4', orientation: 'portrait' }
  };

  try {
    await html2pdf().set(opt).from(element).save();
    showToast(t('toast.pdf.ok') || 'Berjaya muat turun PDF', 'success');
  } catch (e) {
    console.error('PDF generation error:', e);
    showToast('Failed to generate PDF', 'error');
  } finally {
    pdfTemplate.style.display = 'none';
  }
}

// ============================================================
// UI HELPERS
// ============================================================

/** Shows or hides the full-screen loading overlay */
function showLoading(message) {
  const overlay = document.getElementById('loadingOverlay');
  const msgEl   = document.getElementById('loadingMsg');

  if (message) {
    msgEl.innerHTML = message;
    overlay.classList.add('visible');
    document.getElementById('resultsWrapper').classList.remove('visible');
  } else {
    overlay.classList.remove('visible');
  }
}

/** Displays an error message in the main panel */
function showError(message) {
  document.getElementById('emptyState').style.display = 'flex';
  document.getElementById('emptyState').innerHTML = `
    <div class="es-icon">⚠️</div>
    <h2>Error</h2>
    <p>${message}</p>
    <button class="btn btn-outline" style="margin-top:16px" onclick="resetAll()">${t('error.try.again')}</button>`;
}

/** Puts the Simulate button into a loading/disabled state */
function setSimulateLoading(isLoading) {
  const btn = document.getElementById('btnSimulate');
  if (isLoading) {
    btn.classList.add('loading');
    btn.disabled = true;
  } else {
    btn.classList.remove('loading');
    btn.disabled = false;
  }
}

/** Generic helper to set any button into loading state */
function setButtonLoading(btn, isLoading) {
  if (isLoading) {
    btn.classList.add('loading');
    btn.disabled = true;
  } else {
    btn.classList.remove('loading');
    btn.disabled = false;
  }
}

/**
 * Shows a toast notification at the top-right corner.
 * @param {string} message — text to show
 * @param {'success'|'error'|'warning'} type — colour variant
 */
function showToast(message, type = '') {
  const container = document.getElementById('toastContainer');
  const toast     = document.createElement('div');
  toast.className = `toast ${type}`;

  const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : type === 'warning' ? '⚠️' : 'ℹ️';
  toast.innerHTML = `${icon} ${message}`;

  container.appendChild(toast);

  // Auto-remove after 4 seconds (matches CSS fadeOut animation)
  setTimeout(() => toast.remove(), 4000);
}

/** Resets the entire page to its initial state */
function resetAll() {
  // 1. Reset policy values to defaults BEFORE any DOM capture runs
  state.policyValues = {
    option_ratio: 70,
    teaching_hours: 0,
    teacher_capacity: 0,
    coteaching: 30,
  };

  // 2. Clear the policy value area first so capturePolicyInputValues()
  //    inside renderPolicyValueArea() finds no stale inputs to read back.
  document.getElementById('policyValueArea').innerHTML = '';

  // 3. Reset policy mode to Single and select only option_ratio
  document.querySelector('input[name=policyMode][value=single]').checked = true;
  document.querySelectorAll('.policy-card').forEach(card => {
    const active = card.dataset.policy === 'option_ratio';
    card.classList.toggle('selected', active);
    card.querySelector('input[name=policyType]').checked = active;
  });

  // 4. Update mode hint text and re-render the policy value inputs
  //    (state.policyValues is already at defaults; no stale DOM to capture)
  onPolicyModeChange();

  // 5. Reset filter dropdowns back to "All"
  document.getElementById('selSubject').value = 'SEMUA';
  document.getElementById('selNegeri').value  = 'SEMUA';
  const selPPD = document.getElementById('selPPD');
  const selSek = document.getElementById('selSekolah');
  resetSelect(selPPD, t('all.ppds'));
  resetSelect(selSek, t('all.schools'));
  selPPD.disabled = true;
  selSek.disabled = true;

  // 6. Reset grade chips — check "All", uncheck individual chips
  const gradeAll = document.getElementById('gradeAll');
  if (gradeAll) gradeAll.classList.add('checked');
  document.querySelectorAll('#gradeGrid .grade-chip[data-grade]').forEach(c => c.classList.remove('checked'));

  // 7. Restore empty state with original onboarding HTML
  const emptyState = document.getElementById('emptyState');
  emptyState.style.display = 'flex';
  emptyState.innerHTML = emptyStateOriginalHTML;

  // 8. Hide results and agent output
  document.getElementById('resultsWrapper').classList.remove('visible');
  document.getElementById('scenarioBanner').classList.remove('visible');
  document.getElementById('agentResult').classList.remove('visible');
  document.getElementById('policyImpactCard').style.display = 'none';
  document.getElementById('agentQuestion').value = '';
  state.currentRunId = null;
  if (state.chartComparison) { state.chartComparison.destroy(); state.chartComparison = null; }
  if (state.chartSubject)    { state.chartSubject.destroy();    state.chartSubject    = null; }
}

// ============================================================
// UTILITY HELPERS
// ============================================================

/**
 * Generic fetch wrapper for JSON API calls.
 * Automatically sets Content-Type header and handles error responses.
 * @param {string} path    — URL path, e.g. '/api/simulate'
 * @param {Object} options — optional { method, body }
 */
async function apiFetch(path, options = {}) {
  const { method = 'GET', body } = options;
  const fetchOptions = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (state.auth?.token) {
    fetchOptions.headers['X-Auth-Token'] = state.auth.token;
  }
  if (body) fetchOptions.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, fetchOptions);

  if (!res.ok) {
    // Try to read a detailed error message from the response body
    let errMsg = `HTTP ${res.status}`;
    try {
      const errData = await res.json();
      errMsg = errData.detail || errData.message || errMsg;
    } catch {}
    if (res.status === 401 || res.status === 403) {
      showToast(t('toast.no.permission'), 'error');
    }
    throw new Error(errMsg);
  }

  return res.json();
}

/** Resets a <select> element to a single default option */
function resetSelect(selectEl, defaultLabel) {
  selectEl.innerHTML = `<option value="SEMUA">${defaultLabel}</option>`;
}

/** Adds a new <option> to a <select> element */
function addOption(selectEl, value, label) {
  const opt = document.createElement('option');
  opt.value       = value;
  opt.textContent = label;
  selectEl.appendChild(opt);
}

/**
 * Converts an ALL-CAPS string to Title Case.
 * e.g. "JOHOR BAHRU" → "Johor Bahru"
 */
function toTitleCase(str) {
  if (!str) return str;
  return str.toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
}

/** Returns translated priority label for TINGGI / SEDERHANA / RENDAH. */
function getPriorityLabel(pri) {
  const map = { TINGGI: 'priority.high', SEDERHANA: 'priority.medium', RENDAH: 'priority.low' };
  return map[pri] ? t(map[pri]) : pri;
}

/** Translates subject values while preserving the database codes sent to the API. */
function formatSubject(subject) {
  if (subject === 'SEMUA') return t('all.subjects');
  const lang = (typeof getLang === 'function') ? getLang() : 'bm';
  const labels = lang === 'en'
    ? { SAINS: 'Science', MATEMATIK: 'Mathematics' }
    : { SAINS: 'Sains', MATEMATIK: 'Matematik' };
  return labels[subject] || toTitleCase(subject);
}

/**
 * tour.js — Bilingual interactive tour for the Education Workforce Policy Simulation system.
 * Theme: matches existing dark system (--bg #07091A, --teal #0CC8A8, --gold #C4781C).
 * No external dependencies.
 */

/* ─────────────────────────────────────────────────────────────────
   TOUR CONTENT — bilingual step definitions
   ───────────────────────────────────────────────────────────────── */

const TOUR_STEPS = [
  {
    target: null,
    position: 'center',
    bm: {
      title: 'Selamat Datang ke Sistem Simulasi Dasar Tenaga Kerja Pendidikan',
      body:  'Panduan ringkas ini akan memperkenalkan anda kepada cara menggunakan sistem sokongan keputusan ini. Ia direka untuk perancang dasar tenaga kerja pendidikan di Kementerian Pendidikan Malaysia.',
      note:  'Unjuran 2027 · Semua cadangan memerlukan semakan manusia',
    },
    en: {
      title: 'Welcome to the Education Workforce Policy Simulation System',
      body:  'This short guided tour introduces you to how this decision-support system works. It is designed for education workforce policy planners at the Ministry of Education Malaysia.',
      note:  '2027 Projection · All recommendations require human review',
    },
  },
  {
    target: '.lang-toggle',
    position: 'bottom-left',
    bm: {
      title: 'Tukar Bahasa',
      body:  'Klik <strong>BM</strong> untuk Bahasa Melayu atau <strong>EN</strong> untuk Bahasa Inggeris. Semua label, arahan, dan kandungan antara muka akan dikemas kini dengan serta-merta.',
      note:  'Pilihan bahasa diingati dalam pelayar anda.',
    },
    en: {
      title: 'Language Toggle',
      body:  'Click <strong>BM</strong> for Bahasa Melayu or <strong>EN</strong> for English. All interface labels, instructions, and content update immediately.',
      note:  'Your language preference is remembered in your browser.',
    },
  },
  {
    target: '.sidebar-section:first-child',
    position: 'right',
    bm: {
      title: 'Langkah 1 — Tetapkan Skop Analisis',
      body:  'Pilih <strong>Mata Pelajaran</strong>, <strong>Negeri</strong>, <strong>PPD</strong>, <strong>Sekolah</strong>, dan <strong>Tahun / Tingkatan</strong> untuk menentukan skop analisis anda. Biarkan semua pada "Semua" untuk paparan nasional.',
      note:  'Pilihan PPD dan Sekolah aktif selepas negeri dipilih.',
    },
    en: {
      title: 'Step 1 — Set Analysis Scope',
      body:  'Select <strong>Subject</strong>, <strong>State</strong>, <strong>PPD</strong>, <strong>School</strong>, and <strong>Year / Form</strong> to define your analysis scope. Leave all on "All" for a national-level view.',
      note:  'PPD and School dropdowns activate after a state is selected.',
    },
  },
  {
    target: '.policy-mode-toggle',
    position: 'right',
    bm: {
      title: 'Langkah 2 — Pilih Mod Dasar',
      body:  '<strong>Dasar Tunggal</strong> membolehkan anda menguji satu tuas dasar pada satu masa. <strong>Gabungan</strong> membolehkan anda menguji dua, tiga, atau keempat-empat tuas sekaligus untuk melihat kesan bersama.',
      note:  'Mod gabungan berguna untuk senario dasar yang komprehensif.',
    },
    en: {
      title: 'Step 2 — Choose Policy Mode',
      body:  '<strong>Single Policy</strong> lets you test one policy lever at a time. <strong>Combined</strong> lets you test two, three, or all four levers together to see their joint effect.',
      note:  'Combined mode is useful for comprehensive policy scenario testing.',
    },
  },
  {
    target: '#policyCards',
    position: 'right',
    bm: {
      title: 'Empat Tuas Dasar',
      body:  'Pilih satu tuas (atau lebih dalam mod Gabungan):<br/><br/>' +
             '• <strong>Nisbah Opsyen</strong> — bahagian sasaran guru opsyen<br/>' +
             '• <strong>Waktu Pengajaran</strong> — jam mata pelajaran tahunan setiap kelas<br/>' +
             '• <strong>Kapasiti Guru</strong> — jam pengajaran tahunan setiap guru<br/>' +
             '• <strong>Pengajaran Bersama</strong> — bahagian kelas dua guru',
      note:  'Setiap tuas memetakan keputusan dasar sebenar.',
    },
    en: {
      title: 'Four Policy Levers',
      body:  'Select one lever (or more in Combined mode):<br/><br/>' +
             '• <strong>Option Ratio</strong> — target share of subject-option teachers<br/>' +
             '• <strong>Teaching Hours</strong> — annual subject hours per class<br/>' +
             '• <strong>Teacher Capacity</strong> — annual teaching hours per teacher<br/>' +
             '• <strong>Co-teaching</strong> — share of classes with two teachers',
      note:  'Each lever maps to a real policy decision.',
    },
  },
  {
    target: '#policyValueArea',
    position: 'right',
    bm: {
      title: 'Tetapkan Nilai Dasar',
      body:  'Setelah tuas dipilih, slaid atau medan nilai akan muncul di sini. Laraskan nilai untuk mensimulasikan impak yang ingin anda uji. Setiap perubahan memberi kesan langsung kepada pengiraan permintaan 2027.',
      note:  'Semua pengiraan adalah deterministik — formula telus, bukan AI.',
    },
    en: {
      title: 'Set Policy Values',
      body:  'Once a lever is selected, a slider or value field appears here. Adjust the value to simulate the impact you wish to test. Each change directly affects the 2027 demand calculation.',
      note:  'All calculations are deterministic — transparent formulas, not AI.',
    },
  },
  {
    target: '#btnSimulate',
    position: 'right',
    bm: {
      title: 'Langkah 3 — Jalankan Simulasi',
      body:  'Klik butang ini untuk menjalankan unjuran permintaan guru 2027 menggunakan skop dan parameter dasar yang anda tetapkan. Keputusan muncul di panel utama dalam beberapa saat.',
      note:  'Model Random Forest digunakan untuk unjuran permintaan asas.',
    },
    en: {
      title: 'Step 3 — Run the Simulation',
      body:  'Click this button to run the 2027 teacher demand projection using your selected scope and policy parameters. Results appear in the main panel within seconds.',
      note:  'A Random Forest model is used for the baseline demand projection.',
    },
  },
  {
    target: '.main-panel',
    position: 'left',
    bm: {
      title: 'Panel Keputusan',
      body:  'Keputusan simulasi dipaparkan di sini dalam beberapa bahagian:<br/><br/>' +
             '• <strong>KPI</strong> — permintaan, impak dasar, kekurangan<br/>' +
             '• <strong>Carta</strong> — perbandingan permintaan, mengikut mata pelajaran, dan ranking risiko negeri<br/>' +
             '• <strong>Cadangan</strong> — tindakan yang disyorkan<br/>' +
             '• <strong>Sekolah Keutamaan</strong> — 30 sekolah teratas memerlukan perhatian<br/>' +
             '• <strong>Muat turun CSV</strong> untuk laporan lanjut',
      note:  'Semua cadangan memerlukan semakan dan kelulusan manusia.',
    },
    en: {
      title: 'Results Panel',
      body:  'Simulation results are displayed here in several sections:<br/><br/>' +
             '• <strong>KPIs</strong> — demand, policy impact, shortages<br/>' +
             '• <strong>Charts</strong> — demand comparison, by subject, and state risk ranking<br/>' +
             '• <strong>Recommendations</strong> — suggested actions<br/>' +
             '• <strong>Priority Schools</strong> — top 30 schools needing attention<br/>' +
             '• <strong>Download CSV</strong> for further reporting',
      note:  'All recommendations require human review and approval.',
    },
  },
  {
    target: '.agent-section',
    position: 'top',
    bm: {
      title: 'Ejen AI — Tanya dalam Bahasa Semula Jadi',
      body:  'Taip soalan dalam <strong>Bahasa Melayu atau Bahasa Inggeris</strong>. Ejen AI akan mentafsirkan soalan anda, menjalankan simulasi yang sesuai, dan menyampaikan penjelasan dalam bahasa mudah.<br/><br/>' +
             'Contoh: <em>"Ramal permintaan guru Sains di Johor untuk 2027 dengan nisbah opsyen 70%"</em>',
      note:  'Ejen hanya menerangkan — semua pengiraan dilaksanakan oleh Python.',
    },
    en: {
      title: 'AI Agent — Ask in Natural Language',
      body:  'Type a question in <strong>Bahasa Melayu or English</strong>. The AI Agent interprets your question, runs the appropriate simulation, and returns an explanation in plain language.<br/><br/>' +
             'Example: <em>"Forecast Science teacher demand in Johor for 2027 with a 70% subject-option ratio"</em>',
      note:  'The agent explains only — all calculations are executed by Python.',
    },
  },
  {
    target: null,
    position: 'center',
    bm: {
      title: 'Anda Sudah Bersedia!',
      body:  'Anda kini memahami cara menggunakan sistem ini. Mulakan dengan menetapkan skop analisis di panel kiri, kemudian pilih dasar anda dan jalankan simulasi.<br/><br/>' +
             'Ingat: semua keputusan dan cadangan memerlukan semakan daripada pembuat keputusan manusia.',
      note:  'Sokongan keputusan berasaskan bukti untuk perancangan pendidikan yang lebih baik.',
    },
    en: {
      title: 'You Are Ready!',
      body:  'You now understand how to use this system. Begin by setting the analysis scope in the left panel, then select your policy and run the simulation.<br/><br/>' +
             'Remember: all results and recommendations require review by a human decision-maker.',
      note:  'Evidence-informed decision support for better education planning.',
    },
  },
];


/* ─────────────────────────────────────────────────────────────────
   TOUR STATE
   ───────────────────────────────────────────────────────────────── */

let _tourStep   = 0;
let _tourActive = false;


/* ─────────────────────────────────────────────────────────────────
   HELPERS
   ───────────────────────────────────────────────────────────────── */

function _tourLang() {
  if (typeof currentLang !== 'undefined') return currentLang;
  return document.documentElement.lang === 'ms' ? 'bm' : 'en';
}

function _getEl(selector) {
  if (!selector) return null;
  return document.querySelector(selector);
}


/* ─────────────────────────────────────────────────────────────────
   INJECT STYLES — dark system theme
   ───────────────────────────────────────────────────────────────── */

function _injectTourStyles() {
  if (document.getElementById('tour-styles')) return;
  const style = document.createElement('style');
  style.id = 'tour-styles';
  style.textContent = `
    /* ── Overlay backdrop ── */
    #tour-overlay {
      position: fixed; inset: 0; z-index: 9000;
      display: none;
      pointer-events: none;
    }
    #tour-overlay.tour-visible {
      display: block;
      pointer-events: auto;
    }
    #tour-overlay svg {
      position: absolute; inset: 0; width: 100%; height: 100%;
      pointer-events: none;
    }

    /* ── Highlight ring ── */
    #tour-ring {
      position: fixed; z-index: 9050; pointer-events: none;
      border: 2px solid #0CC8A8;
      border-radius: 8px;
      box-shadow: 0 0 0 3px rgba(12,200,168,0.15), 0 0 20px rgba(12,200,168,0.12);
      display: none;
      transition: top 0.22s ease, left 0.22s ease, width 0.22s ease, height 0.22s ease;
      animation: tourRingPulse 2.2s ease-in-out infinite;
    }
    @keyframes tourRingPulse {
      0%,100% { box-shadow: 0 0 0 3px rgba(12,200,168,0.15), 0 0 20px rgba(12,200,168,0.12); }
      50%      { box-shadow: 0 0 0 6px rgba(12,200,168,0.06), 0 0 28px rgba(12,200,168,0.08); }
    }

    /* ── Tooltip card ── */
    #tour-tooltip {
      position: fixed;
      z-index: 9100;
      width: 356px;
      max-width: calc(100vw - 24px);
      background: #0D1228;
      border: 1px solid rgba(255,255,255,0.07);
      border-radius: 10px;
      box-shadow: 0 8px 40px rgba(0,0,0,0.65), 0 2px 8px rgba(0,0,0,0.4);
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      font-size: 13px;
      color: #F0F4FF;
      display: none;
      pointer-events: auto;
      overflow: hidden;
    }
    #tour-tooltip.tour-visible { display: block; }
    #tour-tooltip.tour-center {
      top: 50% !important; left: 50% !important;
      transform: translate(-50%, -50%) !important;
      width: 420px;
    }

    /* Tooltip header */
    #tour-tt-header {
      background: #141B33;
      border-bottom: 1px solid rgba(255,255,255,0.06);
      padding: 13px 16px 11px;
      display: flex; align-items: flex-start; justify-content: space-between; gap: 10px;
    }
    #tour-tt-step {
      font-size: 10px; font-weight: 600; letter-spacing: 0.09em;
      color: #0CC8A8; text-transform: uppercase; margin-bottom: 3px;
    }
    #tour-tt-title {
      font-family: 'Palatino Linotype', Palatino, Georgia, serif;
      font-size: 14.5px; font-weight: 700;
      color: #F0F4FF; line-height: 1.35;
    }
    #tour-tt-close {
      background: none; border: none; cursor: pointer;
      color: rgba(200,210,240,0.35); font-size: 17px; line-height: 1;
      flex-shrink: 0; padding: 1px 2px; margin-top: 1px;
      transition: color 0.15s;
    }
    #tour-tt-close:hover { color: #F0F4FF; }

    /* Tooltip body */
    #tour-tt-body {
      padding: 13px 16px 8px;
      font-size: 13px; color: rgba(200,210,240,0.88); line-height: 1.65;
    }
    #tour-tt-body strong { color: #0CC8A8; font-weight: 600; }
    #tour-tt-body em { color: #E8A04A; font-style: normal; }

    /* Tooltip note */
    #tour-tt-note {
      margin: 6px 16px 0;
      padding: 7px 11px;
      background: rgba(196,120,28,0.10);
      border-left: 2.5px solid #C4781C;
      border-radius: 4px;
      font-size: 11.5px; color: rgba(200,210,240,0.55); line-height: 1.5;
    }

    /* Tooltip footer */
    #tour-tt-footer {
      padding: 11px 16px 13px;
      display: flex; align-items: center; justify-content: space-between; gap: 8px;
    }
    #tour-progress {
      display: flex; gap: 4px; align-items: center;
    }
    .tour-dot {
      width: 6px; height: 6px; border-radius: 50%;
      background: rgba(255,255,255,0.12); flex-shrink: 0;
      transition: background 0.2s, width 0.2s;
    }
    .tour-dot.active { background: #0CC8A8; width: 16px; border-radius: 3px; }
    .tour-btns { display: flex; gap: 7px; }

    #tour-btn-prev {
      background: none;
      border: 1px solid rgba(255,255,255,0.14);
      color: rgba(200,210,240,0.55);
      border-radius: 6px; padding: 6px 15px;
      font-size: 12.5px; cursor: pointer;
      font-family: 'Segoe UI', system-ui, sans-serif;
      transition: border-color 0.15s, color 0.15s;
    }
    #tour-btn-prev:hover:not(:disabled) {
      border-color: #0CC8A8; color: #0CC8A8;
    }
    #tour-btn-prev:disabled { opacity: 0.28; cursor: default; }

    #tour-btn-next {
      background: #0CC8A8; color: #07091A;
      border: none; border-radius: 6px;
      padding: 6px 18px; font-size: 12.5px;
      cursor: pointer; font-weight: 700;
      font-family: 'Segoe UI', system-ui, sans-serif;
      transition: background 0.15s;
    }
    #tour-btn-next:hover { background: #09A088; }
    #tour-btn-next.is-finish { background: #C4781C; color: #fff; }
    #tour-btn-next.is-finish:hover { background: #D4861E; }

    /* ── Launch button ── */
    #tour-launch-btn {
      display: inline-flex; align-items: center; gap: 6px;
      background: rgba(12,200,168,0.08);
      border: 1px solid rgba(12,200,168,0.28);
      color: #0CC8A8; border-radius: 20px;
      padding: 5px 13px; font-size: 12px; font-weight: 600;
      cursor: pointer;
      font-family: 'Segoe UI', system-ui, sans-serif;
      letter-spacing: 0.02em; white-space: nowrap;
      transition: background 0.18s, border-color 0.18s;
    }
    #tour-launch-btn:hover {
      background: rgba(12,200,168,0.16);
      border-color: rgba(12,200,168,0.55);
    }
    #tour-launch-btn svg { flex-shrink: 0; }
  `;
  document.head.appendChild(style);
}


/* ─────────────────────────────────────────────────────────────────
   BUILD TOUR DOM
   ───────────────────────────────────────────────────────────────── */

function _buildTourDOM() {
  // Overlay with SVG mask for spotlight cutout
  const overlay = document.createElement('div');
  overlay.id = 'tour-overlay';
  overlay.innerHTML = `<svg>
    <defs>
      <mask id="tour-mask">
        <rect width="100%" height="100%" fill="white"/>
        <rect id="tour-cutout" rx="9" ry="9" fill="black"/>
      </mask>
    </defs>
    <rect width="100%" height="100%" fill="rgba(7,9,26,0.82)" mask="url(#tour-mask)"/>
  </svg>`;
  // Click outside tooltip → skip
  overlay.addEventListener('click', function(e) {
    if (e.target === overlay || e.target.nodeName === 'svg' || e.target.nodeName === 'rect') {
      _tourEnd();
    }
  });

  // Highlight ring
  const ring = document.createElement('div');
  ring.id = 'tour-ring';

  // Tooltip
  const tooltip = document.createElement('div');
  tooltip.id = 'tour-tooltip';
  tooltip.innerHTML = `
    <div id="tour-tt-header">
      <div style="min-width:0;">
        <div id="tour-tt-step"></div>
        <div id="tour-tt-title"></div>
      </div>
      <button id="tour-tt-close" aria-label="Close tour">✕</button>
    </div>
    <div id="tour-tt-body"></div>
    <div id="tour-tt-note"></div>
    <div id="tour-tt-footer">
      <div id="tour-progress"></div>
      <div class="tour-btns">
        <button id="tour-btn-prev"></button>
        <button id="tour-btn-next"></button>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.appendChild(ring);
  document.body.appendChild(tooltip);

  // Button events
  document.getElementById('tour-tt-close').addEventListener('click', _tourEnd);
  document.getElementById('tour-btn-prev').addEventListener('click', _tourPrev);
  document.getElementById('tour-btn-next').addEventListener('click', _tourNext);
}


/* ─────────────────────────────────────────────────────────────────
   RENDER STEP
   ───────────────────────────────────────────────────────────────── */

function _renderStep(idx) {
  const step   = TOUR_STEPS[idx];
  const total  = TOUR_STEPS.length;
  const lang   = _tourLang();
  const copy   = step[lang] || step['en'];
  const isLast = (idx === total - 1);
  const prevLabel = lang === 'bm' ? 'Sebelumnya' : 'Previous';
  const nextLabel = isLast
    ? (lang === 'bm' ? 'Selesai' : 'Finish')
    : (lang === 'bm' ? 'Seterusnya' : 'Next');
  const stepLabel = lang === 'bm'
    ? `Langkah ${idx + 1} daripada ${total}`
    : `Step ${idx + 1} of ${total}`;

  // Fill content
  document.getElementById('tour-tt-step').textContent = stepLabel;
  document.getElementById('tour-tt-title').innerHTML  = copy.title;
  document.getElementById('tour-tt-body').innerHTML   = copy.body;
  document.getElementById('tour-tt-note').innerHTML   = copy.note;

  const prevBtn = document.getElementById('tour-btn-prev');
  const nextBtn = document.getElementById('tour-btn-next');
  prevBtn.textContent = prevLabel;
  prevBtn.disabled    = (idx === 0);
  nextBtn.textContent = nextLabel;
  nextBtn.className   = isLast ? 'is-finish' : '';

  // Progress dots
  document.getElementById('tour-progress').innerHTML =
    TOUR_STEPS.map((_, i) =>
      `<div class="tour-dot${i === idx ? ' active' : ''}"></div>`
    ).join('');

  // Position
  const targetEl = step.target ? _getEl(step.target) : null;
  const tooltip  = document.getElementById('tour-tooltip');
  const ring     = document.getElementById('tour-ring');
  const cutout   = document.getElementById('tour-cutout');

  if (!targetEl || step.position === 'center') {
    // Centre modal — hide spotlight
    cutout.setAttribute('width', '0');
    cutout.setAttribute('height', '0');
    ring.style.display = 'none';
    tooltip.classList.add('tour-center');
  } else {
    tooltip.classList.remove('tour-center');
    tooltip.style.top  = '';
    tooltip.style.left = '';
    tooltip.style.transform = '';
    // Scroll target into view, then position after settle
    targetEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    setTimeout(() => _applySpotlight(step, targetEl), 200);
  }
}

function _applySpotlight(step, targetEl) {
  const PAD  = 8;
  const r    = targetEl.getBoundingClientRect(); // already in viewport coords (fixed)
  const ring    = document.getElementById('tour-ring');
  const cutout  = document.getElementById('tour-cutout');
  const tooltip = document.getElementById('tour-tooltip');

  // SVG cutout (viewport-relative since overlay is fixed)
  cutout.setAttribute('x',      r.left - PAD);
  cutout.setAttribute('y',      r.top  - PAD);
  cutout.setAttribute('width',  r.width  + PAD * 2);
  cutout.setAttribute('height', r.height + PAD * 2);

  // Highlight ring
  ring.style.display = 'block';
  ring.style.left    = (r.left - PAD) + 'px';
  ring.style.top     = (r.top  - PAD) + 'px';
  ring.style.width   = (r.width  + PAD * 2) + 'px';
  ring.style.height  = (r.height + PAD * 2) + 'px';

  // Tooltip placement
  const TW  = 360;
  const TH  = tooltip.offsetHeight || 240;
  const vw  = window.innerWidth;
  const vh  = window.innerHeight;
  const pos = step.position;
  let top, left, transform = '';

  if (pos === 'right') {
    top  = r.top;
    left = r.right + 16;
    if (left + TW > vw - 8) left = r.left - TW - 16;
  } else if (pos === 'left') {
    top  = r.top;
    left = r.left - TW - 16;
    if (left < 8) left = r.right + 16;
  } else if (pos === 'bottom' || pos === 'bottom-left') {
    top  = r.bottom + 12;
    left = pos === 'bottom-left'
      ? Math.max(8, r.right - TW)
      : r.left;
  } else {
    // top
    top  = r.top - TH - 12;
    left = r.left;
  }

  // Clamp
  if (top + TH > vh - 8) top = vh - TH - 8;
  if (top < 8)           top = 8;
  if (left + TW > vw - 8) left = vw - TW - 8;
  if (left < 8)            left = 8;

  tooltip.style.top       = top  + 'px';
  tooltip.style.left      = left + 'px';
  tooltip.style.transform = transform;
}


/* ─────────────────────────────────────────────────────────────────
   TOUR CONTROLS
   ───────────────────────────────────────────────────────────────── */

function _tourNext() {
  if (_tourStep < TOUR_STEPS.length - 1) {
    _tourStep++;
    _renderStep(_tourStep);
  } else {
    _tourEnd();
  }
}

function _tourPrev() {
  if (_tourStep > 0) {
    _tourStep--;
    _renderStep(_tourStep);
  }
}

function _tourEnd() {
  _tourActive = false;

  // Hide all tour elements — critical: must remove tour-visible so pointer events clear
  const overlay = document.getElementById('tour-overlay');
  const tooltip = document.getElementById('tour-tooltip');
  const ring    = document.getElementById('tour-ring');

  if (overlay) {
    overlay.classList.remove('tour-visible');
    overlay.style.display = 'none';          // belt-and-suspenders: also hide via inline style
  }
  if (tooltip) {
    tooltip.classList.remove('tour-visible', 'tour-center');
    tooltip.style.display = 'none';
  }
  if (ring) {
    ring.style.display = 'none';
  }

  // Restore scroll and pointer events
  document.body.style.overflow     = '';
  document.body.style.pointerEvents = '';
}


/* ─────────────────────────────────────────────────────────────────
   PUBLIC: startTour()
   ───────────────────────────────────────────────────────────────── */

function startTour() {
  _injectTourStyles();
  if (!document.getElementById('tour-overlay')) _buildTourDOM();

  _tourStep  = 0;
  _tourActive = true;

  const overlay = document.getElementById('tour-overlay');
  const tooltip = document.getElementById('tour-tooltip');

  // Reset inline display overrides from a previous end()
  overlay.style.display = '';
  tooltip.style.display = '';

  overlay.classList.add('tour-visible');
  tooltip.classList.add('tour-visible');

  _renderStep(0);
}


/* ─────────────────────────────────────────────────────────────────
   INJECT LAUNCH BUTTON INTO HEADER
   ───────────────────────────────────────────────────────────────── */

function _injectTourButton() {
  if (document.getElementById('tour-launch-btn')) return;
  const langToggle = document.querySelector('.lang-toggle');
  if (!langToggle) return;

  const btn = document.createElement('button');
  btn.id = 'tour-launch-btn';
  btn.innerHTML = `
    <svg width="13" height="13" viewBox="0 0 20 20" fill="none">
      <circle cx="10" cy="10" r="8.5" stroke="currentColor" stroke-width="1.6"/>
      <path d="M10 9v5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
      <circle cx="10" cy="6.5" r="1" fill="currentColor"/>
    </svg>
    <span id="tour-btn-label"></span>
  `;
  btn.onclick = startTour;
  langToggle.parentNode.insertBefore(btn, langToggle);
  _updateTourBtnLabel();
}

function _updateTourBtnLabel() {
  const el = document.getElementById('tour-btn-label');
  if (!el) return;
  el.textContent = _tourLang() === 'bm' ? 'Panduan Sistem' : 'Take a Tour';
}


/* ─────────────────────────────────────────────────────────────────
   HOOK INTO setLang() from lang.js
   ───────────────────────────────────────────────────────────────── */

function _hookLangSwitch() {
  if (typeof setLang !== 'function' || window._tourLangHooked) return;
  const _orig = setLang;
  window.setLang = function(lang) {
    _orig(lang);
    _updateTourBtnLabel();
    if (_tourActive) _renderStep(_tourStep);
  };
  window._tourLangHooked = true;
}


/* ─────────────────────────────────────────────────────────────────
   INIT
   ───────────────────────────────────────────────────────────────── */

function initTour() {
  _injectTourStyles();
  _injectTourButton();
  _hookLangSwitch();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTour);
} else {
  initTour();
}

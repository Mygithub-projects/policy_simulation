/**
 * lang.js — Bilingual support (Bahasa Malaysia / English)
 * Default language: bm
 * Usage: t('key') returns the translated string for the current language.
 *        setLang('bm'|'en') switches and persists the choice.
 *        applyLang() re-renders all [data-i18n] elements on the page.
 */

const LANG_STRINGS = {
  bm: {
    /* ── NAV (landing) ──────────────────────── */
    'nav.brand': 'Simulasi Dasar Tenaga Kerja Pendidikan',
    'nav.features': 'Ciri-ciri',
    'nav.policy': 'Instrumen Dasar',
    'nav.launch': 'Buka Aplikasi →',

    /* ── HERO (landing) ──────────────────────── */
    'hero.eyebrow': 'Kementerian Pendidikan ·  Ramalan Tenaga Kerja 2027',
    'hero.h1.line1': 'Analisis.',
    'hero.h1.highlight': 'Simulasi.',
    'hero.h1.teal': 'Putuskan.',
    'hero.sub': 'Sistem <strong>sokongan keputusan</strong> untuk perancangan tenaga kerja guru Malaysia — ramal permintaan 2027, uji senario dasar dan kenal pasti sekolah yang memerlukan tindakan segera.',
    'hero.cta.primary': 'Mulakan Simulasi',
    'hero.cta.ghost': 'Lihat cara ia berfungsi ↓',

    /* ── STATS ───────────────────────────────── */
    'stats.states': 'Negeri diliputi',
    'stats.ppd': 'Pejabat Pendidikan Daerah',
    'stats.levers': 'Instrumen dasar untuk disimulasi',
    'stats.year': 'Ufuk ramalan sasaran',

    /* ── FEATURES (landing) ──────────────────── */
    'features.eyebrow': 'Apa yang sistem lakukan',
    'features.title.1': 'Semua yang anda perlukan untuk',
    'features.title.em': 'merancang tenaga kerja',
    'features.sub': 'Daripada unjuran permintaan peringkat kebangsaan hingga penarafan keutamaan sekolah — semua didorong oleh pilihan dasar anda.',
    'feat1.title': 'Ramalan Permintaan 2027',
    'feat1.desc': 'Model Random Forest Regresor yang dilatih pada data enrolmen dan penstafan 2022–2026 menganggar permintaan guru bagi setiap sekolah, mata pelajaran dan kumpulan tahun.',
    'feat1.tag': 'Pembelajaran Mesin',
    'feat2.title': 'Simulasi Senario Dasar',
    'feat2.desc': 'Laraskan nisbah opsyen mata pelajaran, waktu pengajaran, kapasiti guru atau bahagian pengajaran bersama — secara tunggal atau gabungan — dan lihat impak tenaga kerja serta-merta.',
    'feat2.tag': 'Deterministik',
    'feat3.title': 'Cadangan Peringkat Sekolah',
    'feat3.desc': 'Penskoran berasaskan peraturan menyenaraikan setiap sekolah mengikut keterukan kekurangan dan menjana cadangan tindakan dalam bahasa mudah untuk pengambilan, penempatan semula atau latihan.',
    'feat3.tag': 'Manusia-dalam-gelung',

    /* ── POLICY LEVERS (landing) ─────────────── */
    'levers.eyebrow': 'Empat instrumen dasar',
    'levers.title.1': 'Simulasi apa yang',
    'levers.title.em': 'benar-benar penting',
    'levers.sub': 'Setiap instrumen memetakan keputusan dasar sebenar. Ubah satu atau gabungkan semuanya — model mengira semula dengan serta-merta.',
    'lever1.title': 'Nisbah Opsyen Mata Pelajaran',
    'lever1.desc': 'Sasaran bahagian guru yang dikerahkan dalam opsyen mata pelajaran terlatih mereka — mengawal kualiti pengkhususan secara langsung.',
    'lever2.title': 'Waktu Pengajaran Tahunan',
    'lever2.desc': 'Jumlah waktu pengajaran mata pelajaran yang dijadualkan setiap kelas setahun — mempengaruhi bilangan guru yang diperlukan setiap sekolah.',
    'lever3.title': 'Kapasiti Waktu Guru',
    'lever3.desc': 'Maksimum waktu pengajaran tahunan yang boleh dibawa seorang guru — meningkatkan ini mengurangkan bilangan kepala yang diperlukan.',
    'lever4.title': 'Bahagian Pengajaran Bersama',
    'lever4.desc': 'Bahagian kelas yang diajar berpasukan oleh dua guru — meluaskan liputan tanpa menambah jawatan tetap.',
    'levers.vis.title': 'Pratonton dasar langsung',
    'levers.res.label': 'Anggaran perubahan permintaan',
    'levers.res.sub': '~1,148 FTE guru kurang berbanding asas',

    /* ── CTA / FOOTER (landing) ──────────────── */
    'cta.h2.line1': 'Data tenaga kerja anda.',
    'cta.h2.em': 'Pilihan dasar anda.',
    'cta.sub': 'Jalankan simulasi sekarang, keputusan dalam beberapa saat.',
    'footer.left': 'Sistem Simulasi Dasar Tenaga Kerja Pendidikan  ·  Kementerian Pendidikan',
    'footer.right': 'POC · Ramalan 2027 · Semua cadangan memerlukan semakan manusia',

    /* ── HEADER (simulation) ─────────────────── */
    'header.title': 'Ejen Simulasi Dasar dan Cadangan Tenaga Kerja Pendidikan',
    'header.sub': 'Kementerian Pendidikan  ·  Ramalan 2027',
    'status.checking': 'Menyemak…',
    'status.online': 'Sistem Dalam Talian',
    'status.issue': 'Sistem Bermasalah',
    'status.offline': 'Sistem Luar Talian',

    /* ── SIDEBAR (simulation) ────────────────── */
    'step1.title': 'Skop Analisis',
    'label.subject': 'Mata Pelajaran',
    'opt.all.subjects': 'Semua Mata Pelajaran',
    'opt.matematik': 'Matematik',
    'opt.sains': 'Sains',
    'label.state': 'Negeri',
    'opt.all.states': 'Semua Negeri',
    'label.ppd': 'Pejabat Pendidikan Daerah (PPD)',
    'opt.all.ppd': 'Semua PPD',
    'label.school': 'Sekolah',
    'opt.all.schools': 'Semua Sekolah',
    'label.grade': 'Tahun / Tingkatan',
    'grade.all': 'Semua',

    'step2.title': 'Simulasi Dasar',
    'mode.single': 'Dasar Tunggal',
    'mode.combined': 'Gabungan',
    'hint.single': 'Pilih satu instrumen dasar untuk disimulasi.',
    'hint.combined': 'Pilih sekurang-kurangnya dua dasar untuk digabungkan.',

    'pc.option_ratio.label': 'Nisbah Opsyen Mata Pelajaran',
    'pc.option_ratio.desc': 'Sasaran bahagian guru dalam opsyen mata pelajaran mereka',
    'pc.teaching_hours.label': 'Waktu Pengajaran',
    'pc.teaching_hours.desc': 'Waktu pengajaran mata pelajaran tahunan setiap kelas',
    'pc.teacher_capacity.label': 'Kapasiti Guru',
    'pc.teacher_capacity.desc': 'Kapasiti waktu pengajaran tahunan setiap guru',
    'pc.coteaching.label': 'Pengajaran Bersama',
    'pc.coteaching.desc': 'Bahagian kelas yang diajar oleh dua guru',

    'step3.title': 'Jalankan Simulasi',
    'btn.run': 'Jalankan Simulasi 2027',
    'btn.reset': '↺ Set Semula',

    /* ── SIDEBAR GROUPS (collapsible nav) ────── */
    'sidebar.group.forecast': 'Analisis Ramalan',
    'sidebar.group.agent': 'Ejen AI',
    'sidebar.group.report': 'Laporan',
    'sidebar.rail.expand': 'Kembangkan bar sisi',
    'sidebar.rail.collapse': 'Kuncupkan bar sisi',
    'sidebar.report.hint': 'Jalankan simulasi atau tanya Ejen AI untuk membuka muat turun.',

    /* ── EMPTY STATE ─────────────────────────── */
    'empty.eyebrow': 'Cara ia berfungsi',
    'empty.title': 'Konfigurasikan senario, kemudian jalankan simulasi',
    'ob1.label': 'Tetapkan skop',
    'ob1.desc': 'Pilih mata pelajaran, negeri, daerah, sekolah, dan kumpulan tahun di panel kiri',
    'ob2.label': 'Pilih dasar',
    'ob2.desc': 'Pilih instrumen dasar yang hendak diuji — nisbah, waktu, kapasiti, atau pengajaran bersama',
    'ob3.label': 'Baca keputusan',
    'ob3.desc': 'Semak ramalan permintaan 2027, kekurangan, dan tindakan yang disyorkan',
    'empty.hint': 'Atau tanya <strong>Ejen AI</strong> di panel kiri - taip soalan dan ia menjalankan simulasi untuk anda.',

    /* ── LOGIN SCREEN ───────────────────────── */
    'login.title': 'Log masuk ke papan pemuka dasar',
    'login.subtitle': 'Masukkan e-mel dan kata laluan anda untuk meneruskan ke sistem sokongan keputusan.',
    'login.username': 'Email',
    'login.password': 'Kata laluan',
    'login.placeholder.username': 'Masukkan alamat e-mel anda',
    'login.placeholder.password': 'Masukkan kata laluan',
    'login.submit': 'Log Masuk',
    'login.error.missing': 'Sila masukkan e-mel dan kata laluan.',
    'login.error.invalid': 'E-mel atau kata laluan tidak sah.',
    'login.error.network': 'Tidak dapat menyambung ke pelayan. Sila cuba lagi.',
    'login.logout': 'Keluar',

    /* ────── PENGURUSAN PENGGUNA ADMIN ────────── */
    'admin.title': 'Pengurusan Pengguna',
    'admin.username': 'Nama Pengguna',
    'admin.email': 'E-mel',
    'admin.password': 'Kata laluan Awal',
    'admin.role': 'Peranan',
    'admin.role.user': 'Pengguna',
    'admin.role.admin': 'Admin (Pegawai Perancangan)',
    'admin.role.superadmin': 'Superadmin (Akses Penuh)',
    'admin.create.btn': 'Cipta Pengguna',
    'admin.create.success': 'Pengguna berjaya dicipta',
    'admin.create.error': 'Gagal mencipta pengguna',
    'nav.admin': 'Pengurusan Pengguna',
    'nav.back': '← Kembali ke Papan Pemuka',
    'toast.no.permission': 'Anda tidak mempunyai kebenaran untuk melakukan tindakan ini.',
    'nav.audit': 'Log Audit',
    'nav.myruns': 'Simulasi Saya',
    'myruns.title': 'Simulasi Saya',
    'myruns.col.time': 'Tarikh & Masa',
    'myruns.col.scope': 'Skop',
    'myruns.col.policy': 'Dasar Disimulasikan',
    'myruns.col.action': 'Tindakan',
    'myruns.empty': 'Belum ada simulasi dijalankan.',
    'audit.title': 'Log Audit',
    'audit.col.time': 'Masa',
    'audit.col.actor': 'Pengguna',
    'audit.col.role': 'Peranan',
    'audit.col.action': 'Tindakan',
    'audit.col.details': 'Butiran',
    'btn.download': '⬇ Muat Turun CSV',
    'btn.download.summary': '⬇ Muat Turun Laporan PDF',
    'btn.download.summary.csv': '⬇ Muat Turun Ringkasan (CSV)',
    'btn.save.simulation': '💾 Simpan Simulasi',
    'btn.save.saved': '✅ Disimpan',
    'modal.save.title': 'Simpan Simulasi',
    'modal.save.hint': 'Namakan simulasi ini supaya anda boleh menjumpainya kembali di Simulasi Saya.',
    'modal.save.label': 'Nama Simulasi',
    'modal.save.placeholder': 'cth. Johor Sains nisbah opsyen 70%',
    'modal.save.cancel': 'Batal',
    'modal.save.confirm': 'Simpan',
    'toast.save.ok': 'Simulasi berjaya disimpan.',
    'toast.save.fail': 'Simpan simulasi gagal:',
    'myruns.col.name': 'Nama Simulasi',

    // --- PDF Template ---
    'pdf.title': 'Laporan Simulasi Tenaga Kerja Pendidikan 2027',
    'pdf.params.title': 'Parameter Simulasi',
    'pdf.summary.title': 'Ringkasan Penjelasan',
    'pdf.kpi.title': 'Penunjuk Prestasi Utama (KPI)',
    'pdf.charts.title': 'Visualisasi Data',
    'pdf.chart.comparison': 'Perbandingan Permintaan Guru',
    'pdf.chart.subject': 'Permintaan Mengikut Mata Pelajaran',
    'pdf.chart.risk': 'Ranking Risiko Negeri',
    'pdf.footer': 'Dijana oleh Sistem Simulasi Dasar Kementerian Pendidikan',

    'admin.canviewaudit': 'Boleh Lihat Log Audit',
    'admin.section.create': 'Cipta Pengguna',
    'admin.section.manage': 'Senarai Pengguna',
    'admin.password.note': 'Kata laluan sementara akan dijana secara automatik dan dihantar ke e-mel pengguna.',
    'admin.table.username': 'Nama Pengguna',
    'admin.table.email': 'Email',
    'admin.table.role': 'Peranan',
    'admin.table.status': 'Status',
    'admin.table.created': 'Dicipta',
    'admin.table.lastlogin': 'Log Masuk Terakhir',
    'admin.table.actions': 'Tindakan',
    'admin.status.active': 'Aktif',
    'admin.status.inactive': 'Tidak Aktif',
    'admin.action.reset': 'Tetapkan Semula Kata Laluan',
    'admin.action.deactivate': 'Nyahaktifkan Pengguna',
    'admin.confirm.reset': 'Hantar kata laluan sementara baharu ke %s?',
    'admin.confirm.deactivate': 'Nyahaktifkan pengguna "%s"? Mereka tidak akan dapat log masuk lagi.',
    'admin.email.failed': 'Tindakan berjaya, tetapi e-mel gagal dihantar. Sila cuba tetapkan semula kata laluan.',

    'cp.title': 'Tetapkan Kata Laluan Baharu',
    'cp.subtitle': 'Anda mesti menukar kata laluan sementara sebelum meneruskan.',
    'cp.current': 'Kata Laluan Semasa',
    'cp.new': 'Kata Laluan Baharu',
    'cp.confirm': 'Sahkan Kata Laluan Baharu',
    'cp.submit': 'Tetapkan Kata Laluan',
    'cp.error.missing': 'Sila isi semua medan.',
    'cp.error.mismatch': 'Kata laluan baharu tidak sepadan.',
    'cp.error.short': 'Kata laluan baharu mestilah sekurang-kurangnya 8 aksara.',
    'cp.success': 'Kata laluan berjaya ditukar.',

    'user.menu.viewprofile': 'Lihat Profil',
    'user.menu.changepassword': 'Tukar Kata Laluan',
    'user.menu.signout': 'Log Keluar',
    'user.menu.back': 'Kembali',

    /* ── RESULT CARD HEADERS ─────────────────── */
    'tab.overview': 'Ringkasan',
    'tab.charts': 'Carta',
    'tab.explanation': 'Penjelasan',
    'tab.recs': 'Cadangan Strategik',
    'tab.schools': 'Sekolah Keutamaan',
    'card.comparison': 'Perbandingan Permintaan Guru',
    'card.subject': 'Permintaan Mengikut Mata Pelajaran',
    'card.risk': 'Ranking Risiko Negeri',
    'card.policy': 'Kesan Dasar Individu dan Gabungan',
    'card.summary': 'Ringkasan Bahasa Mudah',
    'card.recs': 'Cadangan Strategik',
    'card.schools': 'Sekolah Keutamaan — 30 Teratas',

    /* ── KPI STRINGS FOR POLICY-MAKER DASHBOARD ── */
    'kpi.available.label': 'Guru Tersedia',
    'kpi.available.sub': 'Anggaran bekalan tersedia untuk 2027',
    'kpi.shortage.label': 'Kekurangan Selepas Dasar',
    'kpi.shortage.sub': 'Guru yang masih diperlukan selepas kesan dasar',
    'kpi.optiongap.label': 'Kekurangan Opsyen Selepas Dasar',
    'kpi.optiongap.sub': 'Guru opsyen mata pelajaran yang masih diperlukan',
    'kpi.higheststate.label': 'Negeri Risiko Tertinggi',
    'kpi.higheststate.sub': 'Negeri dengan kekurangan guru terbesar',
    'kpi.policyimpact.label': 'Kesan Dasar terhadap Permintaan',

    'chart.risk.label': 'Kekurangan mengikut negeri',

    /* ── TABLE HEADERS ───────────────────────── */
    'th.condition': 'Keadaan',
    'th.required': 'Guru Diperlukan',
    'th.change': 'Perubahan',
    'th.shortage': 'Kekurangan Guru',
    'th.opt.shortage': 'Kekurangan Guru Opsyen Mata Pelajaran',
    'th.num': '#',
    'th.school.code': 'Kod Sekolah',
    'th.state': 'Negeri',
    'th.ppd': 'PPD',
    'th.subject': 'Mata Pelajaran',
    'th.est.without': 'Anggaran tanpa\nperubahan dasar',
    'th.est.after': 'Anggaran selepas\nperubahan dasar',
    'th.teacher.shortage': 'Kekurangan Guru',
    'th.priority': 'Keutamaan',
    'th.action': 'Tindakan Dicadangkan',

    /* ── AI AGENT ────────────────────────────── */
    'agent.title': 'Ejen AI',
    'agent.sub': 'Tanya soalan dalam Bahasa Inggeris atau Bahasa Melayu',
    'agent.placeholder': 'cth. Ramal permintaan guru Sains di Johor untuk 2027 dengan nisbah opsyen mata pelajaran 70%',
    'btn.ask': 'Tanya',
    'chip1': 'Ramal guru Sains di Selangor untuk 2027',
    'chip2': 'Simulasi nisbah opsyen mata pelajaran 80% untuk Matematik di Johor',
    'chip3': 'Apa yang berlaku jika waktu pengajaran Sains tahunan meningkat 10%?',
    'chip4': 'Terapkan pengajaran bersama kepada 40% kelas di Kedah',

    /* ── DYNAMIC STRINGS (used in app.js) ────── */
    'all': 'Semua',
    'all.subjects': 'Semua Mata Pelajaran',
    'all.states': 'Semua Negeri',
    'all.ppds': 'Semua PPD',
    'all.schools': 'Semua Sekolah',
    'loading.sim': 'Menjalankan simulasi dasar tenaga kerja pendidikan 2027…',
    'loading.agent': 'Ejen AI sedang memproses soalan anda…',
    'loading.wait': 'Sila tunggu.',
    'toast.sim.ok': 'Simulasi berjaya diselesaikan!',
    'toast.agent.ok': 'Ejen AI berjaya memproses soalan anda!',
    'toast.csv.ok': 'CSV berjaya dimuat turun.',
    'toast.no.question': 'Sila masukkan soalan terlebih dahulu.',
    'toast.health.warn': 'Sistem menghadapi masalah. Semak sambungan backend.',
    'toast.health.err': 'Tidak dapat menyambung ke pelayan. Pastikan FastAPI sedang berjalan.',
    'toast.load.ppd': 'Gagal memuatkan senarai PPD.',
    'toast.load.school': 'Gagal memuatkan senarai sekolah.',
    'toast.load.negeri': 'Gagal memuatkan senarai negeri: ',
    'val1.label': 'Sasaran nisbah guru opsyen mata pelajaran',
    'val1.hint': 'Contoh: 70% bermaksud 70 daripada setiap 100 guru perlu mengajar dalam opsyen mata pelajaran mereka.',
    'val2.label': 'Perubahan waktu pengajaran tahunan untuk mata pelajaran terpilih (%)',
    'val2.hint': 'Perubahan terpakai kepada waktu mata pelajaran tahunan setiap kelas.<br/>Contoh: mata pelajaran dengan 80 jam setahun menjadi 88 jam selepas peningkatan 10%.',
    'val3.label': 'Perubahan waktu pengajaran tahunan yang disampaikan oleh seorang guru (%)',
    'val3.hint': 'Nilai asas: 600 jam setahun di sekolah rendah dan 800 jam di sekolah menengah.<br/>Contoh: +10% mengubah 600 kepada 660 jam dan 800 kepada 880 jam setahun.',
    'val4.label': 'Berapa peratus kelas akan menggunakan dua guru?',
    'val4.hint': 'Dasar ini memberikan guru kedua kepada kelas yang dipilih di bawah.',
    'kpi.base.label': 'Unjuran Permintaan Guru 2027',
    'kpi.base.sub': 'Ramalan Random Forest · tanpa perubahan dasar',
    'kpi.scenario.label': 'Permintaan Selepas Dasar',
    'kpi.scenario.sub': 'Selepas menerapkan dasar yang dipilih',
    'kpi.delta.label': 'Kesan Dasar Terhadap Permintaan',
    'kpi.delta.inc': 'Permintaan meningkat; ini bukan angka pengambilan terus',
    'kpi.delta.dec': 'Permintaan berkurang; ini bukan angka pengurangan kakitangan terus',
    'kpi.delta.none': 'Dasar tidak mengubah jumlah permintaan guru',
    'kpi.base.gap.label': 'Kekurangan Sebelum Dasar',
    'kpi.base.gap.sub': 'Kekurangan yang sedia ada tanpa perubahan dasar',
    'kpi.scen.gap.label': 'Kekurangan Selepas Dasar',
    'kpi.scen.gap.sub': 'Jumlah yang memerlukan tindakan lanjut',
    'kpi.gap.chg.label': 'Kekurangan Baru Akibat Dasar',
    'kpi.gap.chg.inc': 'Kekurangan meningkat berbanding tanpa perubahan dasar',
    'kpi.gap.chg.dec': 'Kekurangan berkurang berbanding tanpa perubahan dasar',
    'kpi.gap.chg.none': 'Tiada perubahan dalam kekurangan guru',
    'kpi.opt.base.label': 'Kekurangan Guru Opsyen Sebelum Dasar',
    'kpi.opt.base.sub': 'Berdasarkan keadaan tanpa sasaran baru',
    'kpi.opt.scen.label': 'Kekurangan Guru Opsyen Selepas Sasaran %d%%',
    'kpi.opt.scen.sub': 'Guru opsyen mata pelajaran tambahan yang masih diperlukan',
    'kpi.opt.chg.label': 'Perubahan Kekurangan Guru Opsyen',
    'kpi.opt.chg.inc': 'Kekurangan guru opsyen mata pelajaran meningkat sebanyak %d',
    'kpi.opt.chg.dec': 'Kekurangan guru opsyen mata pelajaran berkurang sebanyak %d',
    'kpi.opt.chg.none': 'Tiada perubahan dalam kekurangan guru opsyen mata pelajaran',
    'chart.base.label': 'Tanpa sasaran baru',
    'chart.scen.label': 'Selepas sasaran %d%%',
    'chart.rf.label': 'Unjuran Random Forest (tanpa perubahan dasar)',
    'chart.policy.label': 'Selepas perubahan dasar',
    'insight.title': 'Apa yang dimaksudkan angka ini untuk membuat keputusan?',
    'insight.rf': 'Ramalan Random Forest menganggar <strong>%d guru</strong> diperlukan pada 2027 jika dasar tidak berubah.',
    'insight.demand.inc': 'Dasar yang dipilih meningkatkan permintaan sebanyak <strong>%d guru</strong>, menjadikan jumlah permintaan <strong>%d guru</strong>.',
    'insight.demand.dec': 'Dasar yang dipilih mengurangkan permintaan sebanyak <strong>%d guru</strong>, menjadikan jumlah permintaan <strong>%d guru</strong>.',
    'insight.demand.same': 'Dasar yang dipilih tidak mengubah jumlah permintaan, yang kekal pada <strong>%d guru</strong>.',
    'insight.gap.inc': 'Selepas mengambil kira guru yang tersedia, kekurangan meningkat daripada <strong>%d</strong> kepada <strong>%d guru</strong>. Ini bermakna dasar mewujudkan <strong>%d jawatan kekurangan baru</strong>.',
    'insight.gap.dec': 'Selepas mengambil kira guru yang tersedia, kekurangan berkurang daripada <strong>%d</strong> kepada <strong>%d guru</strong>, pengurangan sebanyak <strong>%d</strong>.',
    'insight.gap.same': 'Selepas mengambil kira guru yang tersedia, kekurangan kekal pada <strong>%d guru</strong>.',
    'insight.action.lbl': 'Tindakan:',
    'insight.action.pos': 'Tumpukan penempatan semula, peruntukan guru, dan semakan pengambilan pada <strong>%d jawatan kekurangan selepas dasar</strong>. Jangan gunakan angka kesan dasar sebagai jumlah pengambilan terus.',
    'insight.action.ok': 'Bekalan guru mencukupi untuk skop ini; teruskan pemantauan dan semakan manusia.',
    'sim.banner': '<strong>Simulasi:</strong> Tahun 2027  |  %s  |  %s  |  Dasar: %s',
    'sim.opt.note': 'Dasar ini mengubah bilangan guru yang mengajar dalam opsyen mata pelajaran mereka, bukan jumlah permintaan guru.',
    'val.single.err': 'Sila pilih satu dasar.',
    'val.combined.err': 'Mod gabungan memerlukan sekurang-kurangnya dua dasar.',
    'val.hours.err': 'Perubahan waktu pengajaran mata pelajaran tahunan mestilah antara -100% dan 500%.',
    'val.capacity.err': 'Perubahan kapasiti waktu pengajaran tahunan guru mestilah antara -99% dan 500%.',
    'table.showing': 'Menunjukkan %d daripada %d sekolah',
    'option.chart.title': 'Perbandingan Permintaan Guru Opsyen Mata Pelajaran',
    'normal.chart.title': 'Perbandingan Permintaan Guru',
    'all.policies.combined': 'Semua Dasar Terpilih Digabungkan',
    'table.no.data': 'Tiada data cadangan tersedia.',
    'table.showing.n': 'Menunjukkan %d sekolah keutamaan tertinggi',
    'error.try.again': 'Cuba Semula',
    'priority.high': 'TINGGI',
    'priority.medium': 'SEDERHANA',
    'priority.low': 'RENDAH',
  },

  en: {
    /* ── NAV (landing) ──────────────────────── */
    'nav.brand': 'Education Workforce Policy Simulation',
    'nav.features': 'Features',
    'nav.policy': 'Policy Instruments',
    'nav.launch': 'Launch App →',

    /* ── HERO (landing) ──────────────────────── */
    'hero.eyebrow': 'Ministry of Education Malaysia  ·  2027 Workforce Forecast',
    'hero.h1.line1': 'Analyse.',
    'hero.h1.highlight': 'Simulate.',
    'hero.h1.teal': 'Decide.',
    'hero.sub': 'A <strong>decision-support system</strong> for Malaysia\'s teacher workforce planners — forecast 2027 demand, test policy scenarios, and surface where schools need action most.',
    'hero.cta.primary': 'Launch Simulation',
    'hero.cta.ghost': 'See how it works ↓',

    /* ── STATS ───────────────────────────────── */
    'stats.states': 'States covered',
    'stats.ppd': 'District Education Offices',
    'stats.levers': 'Policy instrument to simulate',
    'stats.year': 'Target forecast horizon',

    /* ── FEATURES (landing) ──────────────────── */
    'features.eyebrow': 'What the system does',
    'features.title.1': 'Everything you need to',
    'features.title.em': 'think in workforce',
    'features.sub': 'From national-level demand projection to school-by-school priority ranking — all driven by your policy choices.',
    'feat1.title': '2027 Demand Forecast',
    'feat1.desc': 'A Random Forest model trained on 2022–2026 enrolment and staffing data estimates teacher demand for every school, subject and year group.',
    'feat1.tag': 'Machine Learning',
    'feat2.title': 'Policy Scenario Simulation',
    'feat2.desc': 'Adjust the subject-option ratio, teaching hours, teacher capacity, or co-teaching share — alone or combined — and see the workforce impact immediately.',
    'feat2.tag': 'Deterministic',
    'feat3.title': 'School-Level Recommendations',
    'feat3.desc': 'Rule-based scoring ranks every school by shortage severity and generates plain-language action recommendations for hiring, redeployment, or training.',
    'feat3.tag': 'Human-in-the-loop',

    /* ── POLICY LEVERS (landing) ─────────────── */
    'levers.eyebrow': 'Four policy instruments',
    'levers.title.1': 'Simulate what',
    'levers.title.em': 'actually matters',
    'levers.sub': 'Each lever maps to a real policy decision. Change one or combine them all — the model recalculates instantly.',
    'lever1.title': 'Subject-Option Ratio',
    'lever1.desc': 'Target share of teachers deployed within their trained subject option — directly controls specialisation quality.',
    'lever2.title': 'Annual Teaching Hours',
    'lever2.desc': 'Total subject teaching hours scheduled per class each year — affects how many teachers are needed per school.',
    'lever3.title': 'Teacher Hour Capacity',
    'lever3.desc': 'Maximum annual teaching hours a single teacher can carry — raising this reduces the headcount required.',
    'lever4.title': 'Co-teaching Share',
    'lever4.desc': 'Proportion of classes team-taught by two teachers — expands coverage without adding permanent positions.',
    'levers.vis.title': 'Live policy preview',
    'levers.res.label': 'Estimated demand change',
    'levers.res.sub': '~1,148 fewer teacher-FTEs required vs. baseline',

    /* ── CTA / FOOTER (landing) ──────────────── */
    'cta.h2.line1': 'Your workforce data.',
    'cta.h2.em': 'Your policy choices.',
    'cta.sub': 'Run a simulation now — no account required, results in seconds.',
    'footer.left': 'Education Workforce Policy Simulation System  ·  Ministry of Education Malaysia',
    'footer.right': 'MVP · 2027 Forecast · All recommendations require human review',

    /* ── HEADER (simulation) ─────────────────── */
    'header.title': 'Education Workforce Policy Simulation & Recommendation Agent',
    'header.sub': 'Ministry of Education Malaysia  ·  2027 Forecast',
    'status.checking': 'Checking…',
    'status.online': 'System Online',
    'status.issue': 'System Issue',
    'status.offline': 'System Offline',

    /* ── SIDEBAR (simulation) ────────────────── */
    'step1.title': 'Analysis Scope',
    'label.subject': 'Subject',
    'opt.all.subjects': 'All Subjects',
    'opt.matematik': 'Mathematics',
    'opt.sains': 'Science',
    'label.state': 'State',
    'opt.all.states': 'All States',
    'label.ppd': 'District Education Office (PPD)',
    'opt.all.ppd': 'All PPDs',
    'label.school': 'School',
    'opt.all.schools': 'All Schools',
    'label.grade': 'Year / Form',
    'grade.all': 'All',

    'step2.title': 'Policy Simulation',
    'mode.single': 'Single Policy',
    'mode.combined': 'Combined',
    'hint.single': 'Select one policy instrument to simulate.',
    'hint.combined': 'Select at least two policies to combine.',

    'pc.option_ratio.label': 'Subject-Option Ratio',
    'pc.option_ratio.desc': 'Target share of teachers in their subject option',
    'pc.teaching_hours.label': 'Teaching Hours',
    'pc.teaching_hours.desc': 'Annual subject teaching hours per class',
    'pc.teacher_capacity.label': 'Teacher Capacity',
    'pc.teacher_capacity.desc': 'Annual teaching-hour capacity per teacher',
    'pc.coteaching.label': 'Co-teaching',
    'pc.coteaching.desc': 'Share of classes taught by two teachers',

    'step3.title': 'Run Simulation',
    'btn.run': 'Run 2027 Simulation',
    'btn.reset': '↺ Reset',

    /* ── SIDEBAR GROUPS (collapsible nav) ────── */
    'sidebar.group.forecast': 'Forecast Analysis',
    'sidebar.group.agent': 'AI Agent',
    'sidebar.group.report': 'Report',
    'sidebar.rail.expand': 'Expand sidebar',
    'sidebar.rail.collapse': 'Collapse sidebar',
    'sidebar.report.hint': 'Run a simulation or ask the AI agent to unlock downloads.',

    /* ── EMPTY STATE ─────────────────────────── */
    'empty.eyebrow': 'How it works',
    'empty.title': 'Configure a scenario, then run the simulation',
    'ob1.label': 'Set the scope',
    'ob1.desc': 'Choose subject, state, district, school, and year groups on the left panel',
    'ob2.label': 'Choose a policy',
    'ob2.desc': 'Select which policy instrument to test — ratio, hours, capacity, or co-teaching',
    'ob3.label': 'Read the results',
    'ob3.desc': 'Review the 2027 demand forecast, shortages, and recommended actions',
    'empty.hint': 'Or ask the <strong>AI Agent</strong> in the left panel - type a question and it runs the simulation for you.',

    /* ── LOGIN SCREEN ───────────────────────── */
    'login.title': 'Sign in to the policy dashboard',
    'login.subtitle': 'Enter your email and password to continue to the decision support system.',
    'login.username': 'Email',
    'login.password': 'Password',
    'login.placeholder.username': 'Enter your email address',
    'login.placeholder.password': 'Enter your password',
    'login.submit': 'Sign In',
    'login.error.missing': 'Please enter both email and password.',
    'login.error.invalid': 'Invalid email or password.',
    'login.error.network': 'Unable to reach the server. Please try again.',
    'login.logout': 'Sign Out',

    /* ────── ADMIN USER MANAGEMENT ─────────── */
    'admin.title': 'User Management',
    'admin.username': 'Username',
    'admin.email': 'Email',
    'admin.password': 'Initial Password',
    'admin.role': 'Role',
    'admin.role.user': 'User',
    'admin.role.admin': 'Admin (Forecasting Officer)',
    'admin.role.superadmin': 'Superadmin (Full Access)',
    'admin.create.btn': 'Create User',
    'admin.create.success': 'User created successfully',
    'admin.create.error': 'Failed to create user',
    'nav.admin': 'User Management',
    'nav.back': '← Back to Dashboard',
    'toast.no.permission': 'You do not have permission to perform this action.',
    'nav.audit': 'Audit Log',
    'nav.myruns': 'My Runs',
    'myruns.title': 'My Runs',
    'myruns.col.time': 'Date & Time',
    'myruns.col.scope': 'Scope',
    'myruns.col.policy': 'Policy Simulated',
    'myruns.col.action': 'Action',
    'myruns.empty': 'No simulations have been run yet.',
    'audit.title': 'Audit Log',
    'audit.col.time': 'Time',
    'audit.col.actor': 'User',
    'audit.col.role': 'Role',
    'audit.col.action': 'Action',
    'audit.col.details': 'Details',
    'btn.download': '⬇ Download CSV',
    'btn.download.summary': '⬇ Download PDF Report',
    'btn.download.summary.csv': '⬇ Download Summary (CSV)',
    'btn.save.simulation': '💾 Save Simulation',
    'btn.save.saved': '✅ Saved',
    'modal.save.title': 'Save Simulation',
    'modal.save.hint': 'Give this simulation a name so you can find it later in My Runs.',
    'modal.save.label': 'Simulation Name',
    'modal.save.placeholder': 'e.g. Johor Science 70% option ratio',
    'modal.save.cancel': 'Cancel',
    'modal.save.confirm': 'Save',
    'toast.save.ok': 'Simulation saved successfully.',
    'toast.save.fail': 'Save failed:',
    'myruns.col.name': 'Simulation Name',

    // --- PDF Template ---
    'pdf.title': 'Education Workforce Simulation Report 2027',
    'pdf.params.title': 'Simulation Parameters',
    'pdf.summary.title': 'Summary Explanation',
    'pdf.kpi.title': 'Key Performance Indicators (KPI)',
    'pdf.charts.title': 'Data Visualizations',
    'pdf.chart.comparison': 'Teacher Demand Comparison',
    'pdf.chart.subject': 'Demand by Subject',
    'pdf.chart.risk': 'State Risk Ranking',
    'pdf.footer': 'Generated by the Ministry of Education Education Workforce Policy Simulation & Recommendation Agent',

    'admin.canviewaudit': 'Can View Audit Log',
    'admin.section.create': 'Create User',
    'admin.section.manage': 'Manage Users',
    'admin.password.note': 'A temporary password will be generated automatically and emailed to the user.',
    'admin.table.username': 'Username',
    'admin.table.email': 'Email',
    'admin.table.role': 'Role',
    'admin.table.status': 'Status',
    'admin.table.created': 'Created',
    'admin.table.lastlogin': 'Last Login',
    'admin.table.actions': 'Actions',
    'admin.status.active': 'Active',
    'admin.status.inactive': 'Inactive',
    'admin.action.reset': 'Reset Password',
    'admin.action.deactivate': 'Deactivate User',
    'admin.confirm.reset': 'Send a new temporary password to %s?',
    'admin.confirm.deactivate': 'Deactivate user "%s"? They will no longer be able to log in.',
    'admin.email.failed': 'Action succeeded, but the email failed to send. Try the reset-password action again.',

    'cp.title': 'Set New Password',
    'cp.subtitle': 'You must change your temporary password before continuing.',
    'cp.current': 'Current Password',
    'cp.new': 'New Password',
    'cp.confirm': 'Confirm New Password',
    'cp.submit': 'Set Password',
    'cp.error.missing': 'Please fill in all fields.',
    'cp.error.mismatch': 'New passwords do not match.',
    'cp.error.short': 'New password must be at least 8 characters.',
    'cp.success': 'Password changed successfully.',

    'user.menu.viewprofile': 'View Profile',
    'user.menu.changepassword': 'Change Password',
    'user.menu.signout': 'Sign Out',
    'user.menu.back': 'Back',

    /* ── RESULT CARD HEADERS ─────────────────── */
    'tab.overview': 'Overview',
    'tab.charts': 'Charts',
    'tab.explanation': 'Explanation',
    'tab.recs': 'Recommendations',
    'tab.schools': 'Priority Schools',
    'card.comparison': 'Teacher Demand Comparison',
    'card.subject': 'Demand by Subject',
    'card.risk': 'State Risk Ranking',
    'card.policy': 'Individual and Combined Policy Effects',
    'card.summary': 'Plain-Language Summary',
    'card.recs': 'Strategic Recommendations',
    'card.schools': 'Priority Schools — Top 30',

    /* ── KPI STRINGS FOR POLICY-MAKER DASHBOARD ── */
    'kpi.available.label': 'Available Teachers',
    'kpi.available.sub': 'Assumed available supply for 2027',
    'kpi.shortage.label': 'Shortage After Policy',
    'kpi.shortage.sub': 'Teachers still needed after policy impact',
    'kpi.optiongap.label': 'Subject-Option Gap After Policy',
    'kpi.optiongap.sub': 'Qualified subject-option teachers still required',
    'kpi.higheststate.label': 'Highest Risk State',
    'kpi.higheststate.sub': 'State with the largest projected teacher shortage',
    'kpi.policyimpact.label': 'Policy Impact on Total Demand',

    'chart.risk.label': 'Shortage risk by state',

    /* ── TABLE HEADERS ───────────────────────── */
    'th.condition': 'Condition',
    'th.required': 'Teachers Required',
    'th.change': 'Change',
    'th.shortage': 'Teacher Shortage',
    'th.opt.shortage': 'Subject-Option Teacher Shortage',
    'th.num': '#',
    'th.school.code': 'School Code',
    'th.state': 'State',
    'th.ppd': 'PPD',
    'th.subject': 'Subject',
    'th.est.without': 'Estimate without\npolicy change',
    'th.est.after': 'Estimate after\npolicy change',
    'th.teacher.shortage': 'Teacher Shortage',
    'th.priority': 'Priority',
    'th.action': 'Recommended Action',

    /* ── AI AGENT ────────────────────────────── */
    'agent.title': 'AI Agent',
    'agent.sub': 'Ask a question in English or Malay',
    'agent.placeholder': 'e.g. Forecast Science teacher demand in Johor for 2027 with a 70% subject-option ratio',
    'btn.ask': 'Ask',
    'chip1': 'Forecast Science teachers in Selangor for 2027',
    'chip2': 'Simulate an 80% subject-option ratio for Mathematics in Johor',
    'chip3': 'What happens if annual Science teaching hours increase by 10%?',
    'chip4': 'Apply co-teaching to 40% of classes in Kedah',
    'btn.download': '⬇ Download CSV',

    /* ── DYNAMIC STRINGS ─────────────────────── */
    'all': 'All',
    'all.subjects': 'All Subjects',
    'all.states': 'All States',
    'all.ppds': 'All PPDs',
    'all.schools': 'All Schools',
    'loading.sim': 'Running the 2027 education workforce policy simulation...',
    'loading.agent': 'The AI agent is processing your question...',
    'loading.wait': 'Please wait.',
    'toast.sim.ok': 'Simulation completed successfully!',
    'toast.agent.ok': 'The AI agent processed your question successfully!',
    'toast.csv.ok': 'CSV downloaded successfully.',
    'toast.no.question': 'Please enter a question first.',
    'toast.health.warn': 'The system encountered a problem. Check the backend connection.',
    'toast.health.err': 'Unable to connect to the server. Make sure FastAPI is running.',
    'toast.load.ppd': 'Failed to load the PPD list.',
    'toast.load.school': 'Failed to load the school list.',
    'toast.load.negeri': 'Failed to load the state list: ',
    'val1.label': 'Target subject-option teacher ratio',
    'val1.hint': 'Example: 70% means 70 out of every 100 teachers should teach within their subject option.',
    'val2.label': 'Change in annual teaching hours for the selected subject (%)',
    'val2.hint': 'The change applies to annual subject hours for each class.<br/>Example: a subject with 80 hours per year becomes 88 hours after a 10% increase.',
    'val3.label': 'Change in annual teaching hours delivered by one teacher (%)',
    'val3.hint': 'Base values: 600 hours per year in primary schools and 800 hours in secondary schools.<br/>Example: +10% changes 600 to 660 hours and 800 to 880 hours per year.',
    'val4.label': 'What percentage of classes will use two teachers?',
    'val4.hint': 'This policy assigns a second teacher to the selected classes below.',
    'kpi.base.label': '2027 Teacher Demand Forecast',
    'kpi.base.sub': 'Random Forest Regressor · without policy change',
    'kpi.scenario.label': 'Demand After Policy',
    'kpi.scenario.sub': 'After applying the selected policy',
    'kpi.delta.label': 'Policy Effect on Demand',
    'kpi.delta.inc': 'Demand increases; this is not the direct recruitment figure',
    'kpi.delta.dec': 'Demand decreases; this is not the direct staff-reduction figure',
    'kpi.delta.none': 'The policy does not change total teacher demand',
    'kpi.base.gap.label': 'Shortage Before Policy',
    'kpi.base.gap.sub': 'Shortage already present without policy change',
    'kpi.scen.gap.label': 'Shortage After Policy',
    'kpi.scen.gap.sub': 'Total requiring further action',
    'kpi.gap.chg.label': 'New Shortage Caused by Policy',
    'kpi.gap.chg.inc': 'Shortage increases compared with no policy change',
    'kpi.gap.chg.dec': 'Shortage decreases compared with no policy change',
    'kpi.gap.chg.none': 'No change in teacher shortage',
    'kpi.opt.base.label': 'Subject-Option Teacher Shortage Before Policy',
    'kpi.opt.base.sub': 'Based on conditions without a new target',
    'kpi.opt.scen.label': 'Subject-Option Teacher Shortage After %d% Target',
    'kpi.opt.scen.sub': 'Additional subject-option teachers still required',
    'kpi.opt.chg.label': 'Change in Subject-Option Teacher Shortage',
    'kpi.opt.chg.inc': 'Subject-option teacher shortage increases by %d',
    'kpi.opt.chg.dec': 'Subject-option teacher shortage decreases by %d',
    'kpi.opt.chg.none': 'No change in subject-option teacher shortage',
    'chart.base.label': 'Without a new target',
    'chart.scen.label': 'After %d% target',
    'chart.rf.label': 'Random Forest forecast (without policy change)',
    'chart.policy.label': 'After policy change',
    'insight.title': 'What do these figures mean for decision-making?',
    'insight.rf': 'The Random Forest Regressor estimates that <strong>%d teachers</strong> will be required in 2027 if policy remains unchanged.',
    'insight.demand.inc': 'The selected policy increases demand by <strong>%d teachers</strong>, bringing total demand to <strong>%d teachers</strong>.',
    'insight.demand.dec': 'The selected policy reduces demand by <strong>%d teachers</strong>, bringing total demand to <strong>%d teachers</strong>.',
    'insight.demand.same': 'The selected policy does not change total demand, which remains at <strong>%d teachers</strong>.',
    'insight.gap.inc': 'After accounting for available teachers, the shortage increases from <strong>%d</strong> to <strong>%d teachers</strong>. This means the policy creates <strong>%d new shortage positions</strong>.',
    'insight.gap.dec': 'After accounting for available teachers, the shortage decreases from <strong>%d</strong> to <strong>%d teachers</strong>, a reduction of <strong>%d</strong>.',
    'insight.gap.same': 'After accounting for available teachers, the shortage remains at <strong>%d teachers</strong>.',
    'insight.action.lbl': 'Action:',
    'insight.action.pos': 'Focus redeployment, teacher allocation and recruitment review on the <strong>%d shortage positions after policy</strong>. Do not use the policy-effect figure as a direct recruitment total.',
    'insight.action.ok': 'Teacher supply is sufficient for this scope; continue monitoring and human review.',
    'sim.banner': '<strong>Simulation:</strong> Year 2027  |  %s  |  %s  |  Policy: %s',
    'sim.opt.note': 'This policy changes the number of teachers teaching within their subject option, not total teacher demand.',
    'val.single.err': 'Please select one policy.',
    'val.combined.err': 'Combined mode requires at least two policies.',
    'val.hours.err': 'The change in annual subject teaching hours must be between -100% and 500%.',
    'val.capacity.err': 'The change in annual teacher teaching-hour capacity must be between -99% and 500%.',
    'table.showing': 'Showing %d of %d schools',
    'option.chart.title': 'Subject-Option Teacher Demand Comparison',
    'normal.chart.title': 'Teacher Demand Comparison',
    'all.policies.combined': 'All Selected Policies Combined',
    'table.no.data': 'No recommendation data available.',
    'table.showing.n': 'Showing %d highest-priority schools',
    'error.try.again': 'Try Again',
    'priority.high': 'HIGH',
    'priority.medium': 'MEDIUM',
    'priority.low': 'LOW',
  }
};

/* ── Core helpers ─────────────────────────────────────────── */

/* Single source of truth — keeps language in memory so every t() call
   sees the new value immediately, without re-reading localStorage. */
let _activeLang = (function () {
  try { return localStorage.getItem('appLang') || 'bm'; } catch (e) { return 'bm'; }
})();

function getLang() {
  return _activeLang;
}

/** Translate key. Supports %d / %s printf-style substitutions. */
function t(key, ...args) {
  const lang = _activeLang;
  const pool = LANG_STRINGS[lang] || LANG_STRINGS.bm;
  const str = pool[key] !== undefined ? pool[key]
    : (LANG_STRINGS.en[key] !== undefined ? LANG_STRINGS.en[key] : key);
  if (!args.length) return str;
  let i = 0;
  return str.replace(/%[ds]/g, () => args[i++] ?? '');
}

/** Apply translations to every element with data-i18n / data-i18n-html / data-i18n-placeholder */
function applyLang() {
  const lang = _activeLang;

  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });

  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    el.innerHTML = t(el.dataset.i18nHtml);
  });

  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });

  /* sync toggle buttons */
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });

  /* update html[lang] attribute for accessibility */
  document.documentElement.lang = lang === 'en' ? 'en' : 'ms';
}

/** Switch language, persist, re-render, reload grade All chip label */
function setLang(lang) {
  _activeLang = lang;
  try { localStorage.setItem('appLang', lang); } catch (e) { }
  applyLang();

  /* update grade "All" chip if present */
  const gradeAll = document.getElementById('gradeAll');
  if (gradeAll) {
    gradeAll.innerHTML = `<input type="checkbox" value="SEMUA" /> ${t('grade.all')}`;
  }

  /* update policyModeHint text if present */
  const hint = document.getElementById('policyModeHint');
  if (hint) {
    const mode = document.querySelector('input[name=policyMode]:checked')?.value || 'single';
    hint.textContent = mode === 'single' ? t('hint.single') : t('hint.combined');
  }

  /* re-render policy value area if function exists */
  if (typeof renderPolicyValueArea === 'function') renderPolicyValueArea();

  /* update agent placeholder */
  const aq = document.getElementById('agentQuestion');
  if (aq) aq.placeholder = t('agent.placeholder');

  /* update select first options */
  const subj = document.getElementById('selSubject');
  if (subj && subj.options[0]) subj.options[0].textContent = t('opt.all.subjects');
  const neg = document.getElementById('selNegeri');
  if (neg && neg.options[0]) neg.options[0].textContent = t('opt.all.states');
  const ppd = document.getElementById('selPPD');
  if (ppd && ppd.options[0]) ppd.options[0].textContent = t('opt.all.ppd');
  const sek = document.getElementById('selSekolah');
  if (sek && sek.options[0]) sek.options[0].textContent = t('opt.all.schools');
}

/* ── Run on every page load ───────────────────────────────── */
document.addEventListener('DOMContentLoaded', applyLang);

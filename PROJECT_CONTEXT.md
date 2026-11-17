# PROJECT_CONTEXT — Capit-in · SIA Tambak Kepiting

## 1. Fungsi Aplikasi
Sistem Informasi Akuntansi (SIA) untuk **Tambak Kepiting Bapak Salim**
(Jl. Tambak Layur, Desa Morodemak, Kec. Bonang, Kab. Demak, Jawa Tengah).
Mencatat transaksi usaha budidaya/penjualan kepiting, membuat jurnal otomatis,
buku besar, neraca saldo, laporan keuangan, serta mengelola stok dan master data.

Peran pengguna: **Admin**, **Akuntan**, **Kasir** (hak akses berbeda per peran).

## 2. Teknologi
- **Python 3.11** saja (tanpa React/JS/HTML/CSS buatan sendiri) — UI dirender oleh **NiceGUI 4.0.0**
- **SQLite** (file `sia/data/sia.db`, dibuat otomatis + seed saat start)
- `bcrypt` (hash password), `fpdf2` (ekspor PDF), `python-dotenv` (konfigurasi), `pytest` (tes)
- Tema: teal & krem, logo kepiting di `sia/static/logo.png`

## 3. Struktur Folder (isi ZIP)
```
sia/                     <- APLIKASI UTAMA
├── main.py              entry point (ui.run, port dari SIA_PORT, static /static)
├── config.py            baca .env (DB path, port, secret, akun seed)
├── database.py          skema SQLite + seed (akun, produk, dll.)
├── security.py          hash & verifikasi password
├── .env.example         daftar variabel lingkungan (tanpa nilai rahasia)
├── requirements.txt     dependensi Python aplikasi
├── services/            logika bisnis: accounts, auth, journal, master, pdf, reports, stock, transactions
├── views/               layout, theme, components, crud, fmt, period
│   └── pages/           login, dashboard, transactions, journal, reports, master_data, accounts, stock
├── static/logo.png      logo sidebar & login
└── tests/               pytest (test_services.py)
data_backup/
└── sia-data.sql         dump data bisnis SQLite (TANPA tabel users)
frontend/package.json    script "start" menjalankan sia/main.py (khusus workspace Emergent)
backend/                 template FastAPI+MongoDB bawaan workspace (TIDAK dipakai aplikasi)
memory/, test_result.md  catatan workspace
```

## 4. Fitur yang Sudah Selesai
- Login + 3 peran (Admin, Akuntan, Kasir), menu `Pengguna` khusus Admin
- Dashboard ringkasan
- Transaksi (penjualan, pembelian, beban, dll.) dengan **jurnal otomatis**
- Jurnal Umum, Buku Besar, Neraca Saldo (+ ekspor PDF)
- Laporan Laba Rugi & Neraca (+ ekspor PDF)
- Master data: Produk Kepiting, Pengepul, Karyawan
- **Bagan Akun yang dapat diedit** + **indikator status saldo dinamis**
  (Total Debit / Total Kredit / Selisih, berubah saat input saldo awal)
- Stok kepiting (mutasi masuk/keluar)
- Logo kepiting Capit-in di sidebar (progres terakhir)
- Unit test service: 5/5 lulus

## 5. Progres Terakhir
Mengganti logo sidebar dengan logo kepiting Capit-in (`sia/static/logo.png`,
didaftarkan via `app.add_static_files('/static', ...)` di `main.py`, dirender di `views/layout.py::brand`).

## 6. Pekerjaan yang Masih Perlu Dilanjutkan
- Uji end-to-end menyeluruh semua alur UI (belum pernah dijalankan oleh testing agent)
- Verifikasi visual indikator status saldo pada Bagan Akun
- Isi `memory/test_credentials.md` di workspace baru (sesuai nilai .env yang Anda tetapkan)
- Opsional: penyempurnaan format PDF laporan, backup/restore data dari UI

## 7. Cara Melanjutkan di Workspace Baru
1. Ekstrak `project-backup.zip` ke `/app` (struktur folder dipertahankan).
2. Buat `sia/.env` dari `sia/.env.example`, isi nilai baru (password kuat, secret acak):
   `python -c "import secrets;print(secrets.token_hex(32))"` untuk `SIA_STORAGE_SECRET`.
3. Instal dependensi: `pip install -r sia/requirements.txt`
4. Jalankan: `cd sia && python main.py` (port = `SIA_PORT`, di Emergent gunakan 3000).
   Di Emergent, `frontend/package.json` sudah berisi script start yang menjalankan aplikasi Python ini.
5. Database dibuat & di-seed otomatis. Untuk memulihkan data bisnis lama, lihat bagian 8.
6. Tes: `cd sia && python -m pytest tests -q`

## 8. Database
### SQLite (database yang BENAR-BENAR dipakai)
- Lokasi diatur `SIA_DB_PATH` (contoh `data/sia.db`).
- Backup data: `data_backup/sia-data.sql` — berisi semua tabel bisnis
  (accounts, products, collectors, employees, transactions, journal_entries,
  journal_lines, stock_movements, sqlite_sequence). Tabel `users` **sengaja tidak disertakan**
  (berisi hash password); akun dibuat ulang otomatis dari `.env` saat start.
- Restore (setelah aplikasi dijalankan sekali agar skema & akun terbentuk, lalu hentikan aplikasi):
  ```bash
  cd sia
  python - <<'EOF'
  import sqlite3, os
  from dotenv import load_dotenv; load_dotenv('.env')
  c = sqlite3.connect(os.environ['SIA_DB_PATH'])
  for t in ['journal_lines','journal_entries','stock_movements','transactions','employees','collectors','products','accounts']:
      c.execute(f'DELETE FROM "{t}"')
  c.execute("DELETE FROM sqlite_sequence WHERE name != 'users'")
  c.executescript(open('../data_backup/sia-data.sql').read()); c.commit()
  EOF
  ```
  Catatan: kolom `created_by`/user id pada transaksi merujuk ke id user 1–3 (Admin, Akuntan, Kasir) sesuai urutan seed.

### MongoDB
- Aplikasi **tidak menggunakan MongoDB**. Workspace Emergent menyediakan `backend/server.py`
  (template FastAPI) dengan `MONGO_URL` & `DB_NAME`; saat backup, database tersebut hanya berisi
  koleksi `status_checks` dengan **0 dokumen** — tidak ada data yang perlu diamankan.
- Jika kelak ingin pindah ke MongoDB: set `MONGO_URL` dan `DB_NAME` di `backend/.env`
  dan ganti layer `database.py`/`services/*` — ini pekerjaan migrasi, bukan sekadar konfigurasi.

## 9. Deployment Railway
Tidak ditemukan konfigurasi Railway (railway.json/Procfile/nixpacks) di workspace ini —
proyek belum pernah di-deploy ke Railway. Langkah bila ingin deploy:
1. Push isi ZIP ke repo GitHub, buat project Railway dari repo tersebut.
2. Root directory: `sia`. Start command: `python main.py`.
3. Variables di Railway: semua kunci di `.env.example`; set `SIA_PORT` = `${{PORT}}`
   (Railway menyediakan `PORT`), `SIA_DB_PATH` = `/data/sia.db`.
4. Tambahkan **Volume** Railway yang di-mount ke `/data` agar SQLite tidak hilang saat redeploy.
5. Restore data dengan `data_backup/sia-data.sql` (bagian 8) bila diperlukan.

## 10. Keamanan
ZIP ini tidak berisi `.env`, password, API key, secret, file database berisi hash password,
`node_modules`, maupun cache. Semua nilai rahasia harus dibuat baru di workspace berikutnya.

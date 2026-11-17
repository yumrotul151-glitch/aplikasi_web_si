# 🎓 Sistem Informasi Peringatan Dini Akademik (SI Peringatan Dini)

Aplikasi web Sistem Informasi Peringatan Dini (*Early Warning System*) performa akademik mahasiswa yang dibangun menggunakan **Python 3.11+**, **Flask**, **Jinja2**, **Flask-SQLAlchemy (SQLAlchemy 2.x)**, **SQLite**, dan **Flask-WTF**.

Dokumen ini memuat rekapitulasi menyeluruh atas arsitektur sistem, evolusi tahapan pengembangan, spesifikasi teknis, serta panduan implementasi langkah demi langkah.

---

## 📑 Daftar Isi
1. [Arsitektur & Struktur Direktori](#-arsitektur--struktur-direktori)
2. [Rekapitulasi Tahapan Pengembangan](#-rekapitulasi-tahapan-pengembangan)
   - [Tahap 1: Inisialisasi, Routing Dasar, & Jinja2 Templates](#tahap-1-inisialisasi-routing-dasar--jinja2-templates)
   - [Tahap 2: Basis Data SQLite, Relasi ORM, & Validasi Formulir](#tahap-2-basis-data-sqlite-relasi-orm--validasi-formulir)
   - [Tahap 3: Pembaruan UI/UX & Pengujian Terisolasi](#tahap-3-pembaruan-uiux--pengujian-terisolasi)
3. [Daftar Endpoint & Routing](#-daftar-endpoint--routing)
4. [Kriteria Peringatan Dini & Filter Jinja](#-kriteria-peringatan-dini--filter-jinja)
5. [Panduan Penerapan Langkah Demi Langkah](#-panduan-penerapan-langkah-demi-langkah)
6. [Pengujian Otomatis (Automated Testing)](#-pengujian-otomatis-automated-testing)
7. [Prinsip Keamanan & Best Practices](#-prinsip-keamanan--best-practices)

---

## 📁 Arsitektur & Struktur Direktori

```text
c:/aplikasi_web_si/
│
├── app.py                     # Entry point aplikasi, konfigurasi Flask, CLI seed, & seluruh rute
├── models.py                  # Definisi skema ORM SQLAlchemy 2.x (Mahasiswa & Catatan)
├── forms.py                   # Validasi input sisi server menggunakan Flask-WTF & WTForms
├── uji_app.py                 # Skrip pengujian otomatis unit & integrasi terisolasi
├── requirements.txt           # Daftar dependensi pustaka Python
├── README.md                  # Dokumentasi teknis & rekapitulasi proyek
├── siews.db                   # Berkas basis data SQLite lokal (dibuat via CLI flask seed)
│
└── templates/                 # Berkas antarmuka Jinja2
    ├── base.html              # Template induk: layout, navigasi <nav>, flash message, footer
    ├── _makro.html            # Makro Jinja (render_field) untuk rendering formulir modular
    ├── index.html             # Dashboard metrik & tabel mahasiswa berisiko
    ├── mahasiswa.html         # Daftar seluruh mahasiswa & navigasi filter prodi
    ├── tambah.html            # Formulir penambahan mahasiswa baru
    ├── edit.html              # Formulir pengeditan profil & metrik akademik mahasiswa
    ├── detail.html            # Detail profil, riwayat catatan, form tambah catatan, tombol aksi
    ├── cari.html              # Formulir pencarian dengan pola Post/Redirect/Get (PRG)
    └── 404.html               # Halaman kustom HTTP 404 Not Found
```

---

## 🔄 Rekapitulasi Tahapan Pengembangan

### Tahap 1: Inisialisasi, Routing Dasar, & Jinja2 Templates
Pada tahap awal, aplikasi dibangun menggunakan penyimpanan data sementara (*in-memory list of dictionaries*) untuk memvalidasi alur routing dan *templating*:
- **Penerapan 5 Rute Utama**:
  1. Dashboard (`/`) untuk menampilkan ringkasan data.
  2. Rute berbasis *Query String* (`/mahasiswa?prodi=...`) untuk pemfilteran data.
  3. Rute berbasis *URL Parameter* (`/mahasiswa/<nim>`) untuk rincian individu.
  4. Rute formulir pencarian (`/cari`) dengan pola arsitektur **Post/Redirect/Get (PRG)**.
  5. Rute REST API berformat JSON (`/api/mahasiswa/<nim>`).
- **Custom Jinja Filters**:
  - `predikat`: Mengonversi nilai float IPK ke predikat akademik standar (Cumlaude, Sangat Memuaskan, Memuaskan, Cukup, Kurang).
  - `persen`: Memformat nilai kehadiran (desimal/skala 100) menjadi format persentase yang rapi (contoh: `92%`).
- **Struktur Pewarisan Template**:
  - `base.html` sebagai kerangka utama yang mendefinisikan navigasi `<nav>` menggunakan URL dinamis `url_for()` serta blok konten `{% block isi %}`.
  - Penggunaan struktur perulangan `{% for %}` dengan kondisi `{% else %}` saat data kosong.
  - Penggunaan filter bawaan Jinja: `length`, `title`, `sort`, dan `default`.
  - Pencegahan kerentanan XSS (*Cross-Site Scripting*) dengan tidak menggunakan filter `| safe` pada input dinamis.

---

### Tahap 2: Basis Data SQLite, Relasi ORM, & Validasi Formulir
Pada tahap ini, *list of dictionaries* digantikan dengan basis data relasional SQLite melalui **Flask-SQLAlchemy** dan **WTForms**:
- **Sintaks Modern SQLAlchemy 2.x (`models.py`)**:
  - Menggunakan deklarasi *type-hinted* `Mapped[...]` dan `mapped_column(...)`.
  - **Entitas `Mahasiswa`**: Kolom `id`, `nim` (String 14, unik, terindeks), `nama`, `prodi`, `ipk` (Float), `kehadiran` (Integer), dan `email`.
  - **Entitas `Catatan`**: Kolom `id`, `jenis`, `isi`, `dibuat` (DateTime default UTC/server time), dan `mahasiswa_id` (ForeignKey).
  - **Relasi One-to-Many Dua Arah**: Dihubungkan menggunakan parameter `back_populates` di kedua model dengan aturan `cascade="all, delete-orphan"` pada model Mahasiswa agar seluruh catatan anak otomatis terhapus saat data mahasiswa induk dihapus.
- **Validasi Sisi Server (`forms.py`)**:
  - **`MahasiswaForm`**:
    - `nim`: `DataRequired` dan pola regex institusi `^[A-Z]\d{2}\.\d{4}\.\d{5}$` (contoh: `A11.2023.00001`).
    - `nama`: `DataRequired` dan panjang karakter 3 - 100 (`Length`).
    - `prodi`: `DataRequired` dan pilihan terbatas `AnyOf(['SI', 'TI', 'MI'])`.
    - `ipk` & `kehadiran`: Menggunakan `InputRequired` (agar nilai `0` tetap sah) serta `NumberRange`.
    - `email`: `Optional` dan `Email`.
    - Validator khusus `validate_nim`: Mengeksekusi query ORM untuk memvalidasi bahwa NIM belum pernah terdaftar sebelumnya.
  - **`CatatanForm`**:
    - `jenis`: `SelectField` (*Akademik*, *Keuangan*, *Pribadi*).
    - `isi`: `TextAreaField` dengan panjang 10 - 500 karakter dan `NoneOf` untuk menolak teks uji coba seperti `'tes'`, `'test'`, atau `'-'`.
  - Seluruh pesan galat disajikan dalam Bahasa Indonesia yang komunikatif.
- **Operasi CRUD Lengkap (`app.py`)**:
  - Penambahan rute `GET & POST /mahasiswa/tambah` (merespons HTTP **422 Unprocessable Entity** jika validasi gagal, atau HTTP **302 Redirect** jika sukses).
  - Pembaruan rute `/mahasiswa/<nim>` untuk mendukung penambahan catatan konseling.
  - Penambahan rute `POST /mahasiswa/<nim>/hapus` untuk operasi penghapusan data secara berantai (*cascade*).
  - CLI khusus `@app.cli.command("seed")` (`flask seed`) untuk melakukan `db.drop_all()`, `db.create_all()`, dan menyuntikkan 5 data awal mahasiswa.

---

### Tahap 3: Pembaruan UI/UX & Pengujian Terisolasi
- **Makro Jinja Reusable (`templates/_makro.html`)**:
  - Fungsi makro `render_field(field)` yang secara otomatis me-render label input, elemen form (input/select/textarea) dengan status Bootstrap `is-invalid`, serta daftar pesan error validasi.
- **Proteksi CSRF**:
  - Seluruh tag `<form>` menyertakan token keamanan tersembunyi `{{ form.hidden_tag() }}`.
- **Sistem Flash Messaging**:
  - Blok penanganan notifikasi pada `base.html` menggunakan `get_flashed_messages(with_categories=true)` untuk menampilkan umpan balik sukses, info, atau peringatan secara interaktif.
- **Pengujian Otomatis Terisolasi (`uji_app.py`)**:
  - Memanfaatkan `app.test_client()` dengan basis data sementara di memori RAM (`sqlite://` + `StaticPool`) dan penonaktifan CSRF sementara (`WTF_CSRF_ENABLED=False`) agar eksekusi pengujian tidak mempengaruhi berkas basis data produksi/pengembangan `siews.db`.

---

## 🌐 Daftar Endpoint & Routing

| Metode | URL Endpoint | Deskripsi Fungsi | Respon / Pola |
| :---: | :--- | :--- | :--- |
| `GET` | `/` | Dashboard ikhtisar mahasiswa & metrik peringatan dini | Render `index.html` (HTTP 200) |
| `GET` | `/mahasiswa` | Menampilkan seluruh mahasiswa / filter prodi (`?prodi=...`) | Render `mahasiswa.html` (HTTP 200) |
| `GET` | `/mahasiswa/tambah` | Menampilkan formulir penambahan mahasiswa | Render `tambah.html` (HTTP 200) |
| `POST` | `/mahasiswa/tambah` | Memproses validasi dan penyimpanan mahasiswa baru | HTTP 302 (Redirect) jika valid / HTTP 422 jika gagal |
| `GET` | `/mahasiswa/<nim>` | Rincian profil mahasiswa, riwayat catatan, & form catatan | Render `detail.html` (HTTP 200 / 404 jika tidak ada) |
| `POST` | `/mahasiswa/<nim>` | Menyimpan catatan bimbingan/konseling baru | HTTP 302 (Redirect PRG) jika valid / HTTP 422 jika gagal |
| `GET` | `/mahasiswa/<nim>/edit` | Menampilkan formulir edit profil & nilai mahasiswa terisi | Render `edit.html` (HTTP 200 / 404 jika tidak ada) |
| `POST` | `/mahasiswa/<nim>/edit` | Memvalidasi dan menyimpan pembaruan data mahasiswa | HTTP 302 (Redirect ke detail) jika valid / HTTP 422 jika gagal |
| `POST` | `/mahasiswa/<nim>/hapus` | Menghapus data mahasiswa beserta riwayat catatannya | HTTP 302 (Redirect ke `/mahasiswa`) |
| `GET` | `/cari` | Menampilkan formulir pencarian mahasiswa / filter | Render `cari.html` (HTTP 200) |
| `POST` | `/cari` | Memproses input pencarian (NIM / Prodi) | HTTP 302 (Redirect PRG ke `/mahasiswa/<nim>` atau `/mahasiswa?prodi=`) |
| `GET` | `/api/mahasiswa/<nim>` | Endpoint REST API JSON data mahasiswa dan catatan | JSON Payload (HTTP 200 / HTTP 404) |

---

## 📊 Kriteria Peringatan Dini & Filter Jinja

### 1. Logika Peringatan Dini (`is_berisiko`)
Mahasiswa dikategorikan masuk ke dalam **Peringatan Dini Akademik Aktif** jika memenuhi salah satu kondisi berikut:
- **IPK < 2.75** (di bawah standar kelulusan reguler), ATAU
- **Kehadiran < 75%** (di bawah batas minimum presensi ujian akhir).

### 2. Custom Jinja Filters
- `{{ mhs.ipk | predikat }}`:
  - $\ge 3.51$ : *"Dengan Pujian (Cumlaude)"*
  - $3.00 - 3.50$ : *"Sangat Memuaskan"*
  - $2.76 - 2.99$ : *"Memuaskan"*
  - $2.00 - 2.75$ : *"Cukup"*
  - $< 2.00$ : *"Kurang (Perlu Perhatian)"*
- `{{ mhs.kehadiran | persen }}`:
  - Menerima rasio desimal (`0.92`) maupun integer skala 100 (`92`), menghasilkan string terformat: `92%`.

---

## 🚀 Panduan Penerapan Langkah Demi Langkah

Ikuti langkah-langkah berikut untuk menjalankan aplikasi di komputer lokal:

### 1. Persiapan Lingkungan & Instalasi Dependensi
Buka terminal pada direktori proyek (`c:\aplikasi_web_si`) dan instal seluruh pustaka yang dibutuhkan:

```bash
# (Opsional) Buat dan aktifkan lingkungan virtual
python -m venv venv
# Windows:
venv\Scripts\activate

# Instalasi dependensi
pip install -r requirements.txt
```

### 2. Inisialisasi Basis Data (*Seeding*)
Gunakan perintah CLI bawaan aplikasi untuk membuat tabel SQLite dan mengisinya dengan 5 data dummy mahasiswa:

```bash
flask seed
```
*Output yang diharapkan:*
```text
Basis data berhasil direset dan 5 data mahasiswa dummy telah dimasukkan!
```
Perintah ini akan secara otomatis membuat berkas basis data [siews.db](file:///c:/aplikasi_web_si/siews.db).

### 3. Menjalankan Server Pengembangan
Jalankan aplikasi Flask:

```bash
python app.py
```
Aplikasi akan aktif pada alamat default: **[http://127.0.0.1:5000/](http://127.0.0.1:5000/)**.

### 4. Skenario Pengujian Antarmuka Pengguna
- **Buka Dashboard**: Kunjungi `http://127.0.0.1:5000/` untuk melihat ringkasan total mahasiswa dan mahasiswa berisiko.
- **Filter Prodi**: Kunjungi `http://127.0.0.1:5000/mahasiswa?prodi=ti` untuk melihat mahasiswa program studi TI.
- **Tambah Mahasiswa**: Buka menu *Tambah Mahasiswa* (`/mahasiswa/tambah`) dan coba masukkan data valid (misal NIM: `A11.2023.00010`) atau coba masukkan data tidak valid untuk melihat pesan error validasi (HTTP 422).
- **Tambah Catatan Konseling**: Buka detail mahasiswa (`/mahasiswa/A11.2023.00001`), isi form pada panel sebelah kanan untuk menambahkan catatan bimbingan.
- **Cari Mahasiswa**: Buka menu *Pencarian* (`/cari`) untuk menguji alur form Post/Redirect/Get.
- **Endpoint API**: Akses `http://127.0.0.1:5000/api/mahasiswa/A11.2023.00001` untuk melihat data JSON.

---

## 🧪 Pengujian Otomatis (Automated Testing)

Pengujian otomatis telah disiapkan di dalam berkas [uji_app.py](file:///c:/aplikasi_web_si/uji_app.py). Pengujian berjalan pada basis data *in-memory* tanpa memengaruhi berkas `siews.db`.

### Cara Menjalankan Pengujian:
```bash
python uji_app.py
```
atau dengan keluaran verbose:
```bash
python -m unittest uji_app.py -v
```

### Cakupan Pengujian:
1. `test_rute_dasar_index` : Verifikasi HTTP 200 dan tampilan dashboard.
2. `test_rute_mahasiswa_filter_prodi` : Verifikasi query string filtering data.
3. `test_rute_mahasiswa_404` : Verifikasi penanganan error 404 pada NIM yang tidak terdaftar.
4. `test_rute_api_mahasiswa_json` : Verifikasi struktur dan payload JSON REST API.
5. `test_tambah_mahasiswa_valid` : Verifikasi pengiriman form valid menghasilkan status **302** (Redirect) dan data tersimpan via ORM.
6. `test_tambah_mahasiswa_semua_salah_422` : Verifikasi pengiriman data salah menghasilkan status **422** dan memunculkan seluruh pesan error Bahasa Indonesia.
7. `test_tambah_mahasiswa_nim_duplikat` : Verifikasi bahwa validator khusus `validate_nim` menolak NIM yang telah ada di database (status **422**).
8. `test_relasi_tambah_catatan_mahasiswa` : Verifikasi penambahan catatan konseling dan keterhubungannya dengan mahasiswa lewat relasi dua arah ORM (`back_populates`).
9. `test_rute_hapus_mahasiswa_cascade` : Verifikasi operasi penghapusan data mahasiswa beserta seluruh catatan terkaitnya secara otomatis (*cascade delete*).
10. `test_rute_edit_mahasiswa_tampil_form_200` : Verifikasi form edit menampilkan data awal mahasiswa secara benar (HTTP 200).
11. `test_rute_edit_mahasiswa_sukses_302` : Verifikasi pembaruan data mahasiswa (IPK, presensi, dll.) tersimpan via ORM, kalkulasi risiko otomatis disesuaikan, dan redirect ke rute detail (HTTP 302).
12. `test_rute_edit_mahasiswa_tetap_nim_sama` : Verifikasi mode edit dengan NIM yang sama tidak terblokir oleh validator keunikan NIM berkat `current_id`.
13. `test_rute_edit_mahasiswa_nim_duplikat_422` : Verifikasi jika NIM diubah menyerupai NIM mahasiswa lain, sistem menolak dengan HTTP 422.
14. `test_rute_edit_mahasiswa_404` : Verifikasi penanganan error 404 ketika mengakses rute edit untuk mahasiswa yang tidak ada.

---

## 🛡️ Prinsip Keamanan & Best Practices

1. **Proteksi Cross-Site Request Forgery (CSRF)**:
   - Setiap formulir HTML dilindungi menggunakan token CSRF unik yang dihasilkan oleh Flask-WTF melalui `{{ form.hidden_tag() }}`.
2. **Pencegahan Cross-Site Scripting (XSS)**:
   - Jinja2 secara otomatis mengonversi karakter berbahaya (`<`, `>`, `&`, `"`, `'`) menjadi entitas HTML aman tanpa menggunakan filter `| safe` pada input pengguna.
3. **Pencegahan SQL Injection**:
   - Seluruh interaksi basis data menggunakan SQLAlchemy 2.x dengan *parameterized queries* bawaan (`db.select(...)`), sehingga parameter input tidak pernah digabungkan secara mentah (*raw string concatenation*).
4. **Pola Post/Redirect/Get (PRG)**:
   - Seluruh request `POST` pada form pencarian, penambahan data, maupun penambahan catatan merespons dengan HTTP Status 302/Redirect ke rute `GET` tujuan untuk menghindari resubmisi data ganda saat pengguna me-*refresh* halaman peramban.
5. **Penanganan Status Kode HTTP Representatif**:
   - `200 OK` untuk pembacaan data yang sukses.
   - `302 Found / Redirect` untuk transisi setelah operasi tulis form berhasil.
   - `404 Not Found` untuk rute atau rekaman data yang tidak ada.
   - `422 Unprocessable Entity` untuk pengiriman form yang gagal memenuhi aturan validasi.
6. **Eksekusi Debug Terisolasi**:
   - Parameter `debug=True` diproteksi secara ketat di dalam blok `if __name__ == "__main__":` agar tidak aktif ketika aplikasi diuji atau dijalankan melalui WSGI server produksi.

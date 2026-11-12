# 🎓 Sistem Informasi Peringatan Dini Akademik (SI Peringatan Dini)

Aplikasi web Sistem Informasi Peringatan Dini (*Early Warning System*) performa akademik mahasiswa yang dibangun menggunakan **Python 3.11+**, **Flask**, **Jinja2**, **Flask-SQLAlchemy (SQLAlchemy 2.x)**, **SQLite**, dan **Flask-WTF**.

Dokumen ini memuat rekapitulasi menyeluruh atas arsitektur sistem, spesifikasi teknis, panduan pengujian, panduan instalasi lokal, serta **panduan deployment lengkap ke PythonAnywhere**.

---

## 📑 Daftar Isi
1. [Arsitektur & Struktur Direktori](#-arsitektur--struktur-direktori)
2. [Fitur Utama & Spesifikasi](#-fitur-utama--spesifikasi)
3. [Daftar Endpoint & Routing](#-daftar-endpoint--routing)
4. [Kriteria Peringatan Dini & Filter Jinja](#-kriteria-peringatan-dini--filter-jinja)
5. [Panduan Menjalankan Secara Lokal](#-panduan-menjalankan-secara-lokal)
6. [☁️ Panduan Deployment di PythonAnywhere (Langkah Demi Langkah)](#️-panduan-deployment-di-pythonanywhere-langkah-demi-langkah)
7. [Pengujian Otomatis (Automated Testing)](#-pengujian-otomatis-automated-testing)
8. [Prinsip Keamanan & Best Practices](#-prinsip-keamanan--best-practices)

---

## 📁 Arsitektur & Struktur Direktori

```text
c:/aplikasi_web_si/
│
├── app.py                     # Entry point aplikasi, konfigurasi Flask, CLI seed, & seluruh rute
├── models.py                  # Definisi skema ORM SQLAlchemy 2.x (Mahasiswa & Catatan)
├── forms.py                   # Validasi input sisi server menggunakan Flask-WTF & WTForms
├── uji_app.py                 # Skrip pengujian otomatis unit & integrasi terisolasi (18 skenario)
├── requirements.txt           # Daftar dependensi pustaka Python
├── README.md                  # Dokumentasi teknis & panduan deployment
├── siews.db                   # Berkas basis data SQLite lokal (dibuat via python app.py seed)
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

## 🚀 Fitur Utama & Spesifikasi

1. **Basis Data SQLite & Model SQLAlchemy 2.x (`models.py`)**
   - Menggunakan sintaks modern `Mapped` dan `mapped_column`.
   - **Model Mahasiswa**: Kolom `id`, `nim` (String 14, unik, terindeks), `nama`, `prodi`, `ipk` (Float), `kehadiran` (Integer), dan `email`.
   - **Model Catatan**: Kolom `id`, `jenis`, `isi`, `dibuat` (DateTime default UTC/server time), dan `mahasiswa_id` (ForeignKey).
   - **Relasi One-to-Many Dua Arah**: Dihubungkan dengan `back_populates` di kedua model dan aturan `cascade="all, delete-orphan"` pada model Mahasiswa (catatan otomatis terhapus saat data mahasiswa induk dihapus).

2. **Validasi Formulir Sisi Server (`forms.py`)**
   - **MahasiswaForm**:
     - `nim`: `DataRequired` dan pola regex institusi `^[A-Z]\d{2}\.\d{4}\.\d{5}$` (contoh: `A11.2023.00001`).
     - `nama`: `DataRequired` dan panjang karakter 3 - 100 (`Length`).
     - `prodi`: `DataRequired` dan pilihan terbatas `AnyOf(['SI', 'TI', 'MI'])`.
     - `ipk` & `kehadiran`: Menggunakan `InputRequired` (agar nilai `0` tetap sah) serta `NumberRange`.
     - `email`: `Optional` dan `Email`.
     - Validator khusus `validate_nim`: Mengecek keunikan NIM di basis data, mendukung mode edit tanpa memblokir NIM miliknya sendiri (`current_id`).
   - **CatatanForm**:
     - `jenis`: `SelectField` (*Akademik*, *Keuangan*, *Pribadi*).
     - `isi`: `TextAreaField` dengan panjang 10 - 500 karakter dan `NoneOf` untuk menolak teks uji coba (`tes`, `test`, `-`).
   - Seluruh pesan galat disajikan dalam Bahasa Indonesia yang komunikatif.

3. **Operasi CRUD & Fitur Tambahan (`app.py`)**
   - **Create**: Tambah mahasiswa baru (`/mahasiswa/tambah`) dan tambah catatan bimbingan (`/mahasiswa/<nim>`).
   - **Read**: Dashboard metrik (`/`), daftar mahasiswa (`/mahasiswa`), pencarian PRG (`/cari`), dan detail profil (`/mahasiswa/<nim>`).
   - **Update**: Edit data mahasiswa (`/mahasiswa/<nim>/edit`) dengan otomatis menghitung ulang status peringatan dini.
   - **Delete**: Hapus mahasiswa beserta catatan terkaitnya secara aman (`/mahasiswa/<nim>/hapus` via method POST).
   - **Export CSV**: Ekspor seluruh data atau data terfilter ke format CSV (`/mahasiswa/export`).
   - **REST API JSON**: Endpoint RESTful `/api/mahasiswa/<nim>`.
   - **CLI Seed**: Perintah `python app.py seed` atau `flask seed` untuk mereset dan menginisialisasi basis data dengan 5 data mahasiswa dummy.

---

## 🌐 Daftar Endpoint & Routing

| Metode | URL Endpoint | Deskripsi Fungsi | Respon / Pola |
| :---: | :--- | :--- | :--- |
| `GET` | `/` | Dashboard ikhtisar statistik mahasiswa & peringatan dini | Render `index.html` (HTTP 200) |
| `GET` | `/mahasiswa` | Menampilkan seluruh mahasiswa / filter prodi (`?prodi=...`) | Render `mahasiswa.html` (HTTP 200) |
| `GET` | `/mahasiswa/tambah` | Menampilkan formulir penambahan mahasiswa | Render `tambah.html` (HTTP 200) |
| `POST` | `/mahasiswa/tambah` | Memproses validasi dan penyimpanan mahasiswa baru | HTTP 302 (Redirect) jika valid / HTTP 422 jika gagal |
| `GET` | `/mahasiswa/<nim>` | Rincian profil mahasiswa, riwayat catatan, & form catatan | Render `detail.html` (HTTP 200 / 404 jika tidak ada) |
| `POST` | `/mahasiswa/<nim>` | Menyimpan catatan bimbingan/konseling baru | HTTP 302 (Redirect PRG) jika valid / HTTP 422 jika gagal |
| `GET` | `/mahasiswa/<nim>/edit` | Menampilkan formulir edit mahasiswa dengan data terisi | Render `edit.html` (HTTP 200 / 404 jika tidak ada) |
| `POST` | `/mahasiswa/<nim>/edit` | Memproses pembaruan data mahasiswa | HTTP 302 (Redirect ke detail) jika valid / HTTP 422 jika gagal |
| `POST` | `/mahasiswa/<nim>/hapus` | Menghapus data mahasiswa beserta riwayat catatannya | HTTP 302 (Redirect ke `/mahasiswa`) |
| `GET` | `/mahasiswa/export` | Mengunduh berkas rekap data dalam format CSV | Berkas CSV (`text/csv`) |
| `GET` | `/cari` | Menampilkan formulir pencarian mahasiswa / filter | Render `cari.html` (HTTP 200) |
| `POST` | `/cari` | Memproses input pencarian (NIM / Prodi) | HTTP 302 (Redirect PRG ke rute detail atau daftar) |
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

## 💻 Panduan Menjalankan Secara Lokal

```bash
# 1. Buka direktori proyek
cd c:\aplikasi_web_si

# 2. Buat dan aktifkan lingkungan virtual (opsional tapi disarankan)
python -m venv venv
venv\Scripts\activate

# 3. Instal dependensi
pip install -r requirements.txt

# 4. Inisialisasi basis data dengan 5 data dummy
python app.py seed

# 5. Jalankan server lokal
python app.py
```
Akses melalui browser di: **[http://127.0.0.1:5000/](http://127.0.0.1:5000/)**.

---

## ☁️ Panduan Deployment di PythonAnywhere (Langkah Demi Langkah)

Berikut adalah panduan lengkap cara men-deploy aplikasi ini ke layanan hosting **[PythonAnywhere](https://www.pythonanywhere.com/)**:

### Langkah 1: Buka Bash Console di PythonAnywhere
1. Masuk (*Log in*) ke akun **[PythonAnywhere](https://www.pythonanywhere.com/)**.
2. Di halaman Dashboard, buka tab **Consoles**.
3. Klik tombol **Bash** untuk membuka terminal baru.

---

### Langkah 2: Clone Repositori dari GitHub
Jalankan perintah berikut di dalam terminal Bash PythonAnywhere:

```bash
# Clone repository proyek Anda
git clone https://github.com/yumrotul151-glitch/aplikasi_web_si.git

# Masuk ke direktori proyek
cd aplikasi_web_si
```

---

### Langkah 3: Buat Virtual Environment & Instal Dependensi
Di dalam terminal Bash PythonAnywhere yang sama, buat virtual environment dengan Python 3.10 (atau versi Python yang tersedia pada akun Anda):

```bash
# Buat virtual environment bernama 'venv'
python3.10 -m venv venv

# Aktifkan virtual environment
source venv/bin/activate

# Tingkatkan versi pip & instal seluruh dependensi dari requirements.txt
pip install --upgrade pip
pip install -r requirements.txt
```

---

### Langkah 4: Inisialisasi Basis Data (*Seeding*) di PythonAnywhere
Jalankan perintah berikut untuk membuat tabel SQLite `siews.db` dan mengisinya dengan data awal mahasiswa:

```bash
python app.py seed
```

*Output yang diharapkan:*
```text
Basis data berhasil direset dan 5 data mahasiswa dummy telah dimasukkan!
```

---

### Langkah 5: Buat Aplikasi Web di Tab "Web"
1. Buka tab **Web** pada menu atas dashboard PythonAnywhere.
2. Klik tombol **"Add a new web app"**.
3. Jika menggunakan akun gratis (*Free Account*), klik **Next** untuk domain default (`username.pythonanywhere.com`).
4. Pada pilihan framework, pilih **"Manual configuration (including virtualenvs)"** (⚠️ **JANGAN** pilih *Flask* otomatis, agar konfigurasi virtualenv dan dependensi kita digunakan secara tepat).
5. Pilih versi Python: **Python 3.10** (sesuai versi yang digunakan saat membuat venv pada Langkah 3).
6. Klik **Next** sampai proses pembuatan selesai.

---

### Langkah 6: Konfigurasi Path & Virtualenv
Setelah web app terbuat, tetap berada di tab **Web** dan lakukan konfigurasi berikut:

1. **Bagian Code**:
   - **Source code**: `/home/<username>/aplikasi_web_si`
   - **Working directory**: `/home/<username>/aplikasi_web_si`
   *(Ganti `<username>` dengan username akun PythonAnywhere Anda)*

2. **Bagian Virtualenv**:
   - Klik kolom path virtualenv dan masukkan:
     `/home/<username>/aplikasi_web_si/venv`
   - Klik tanda centang hijau untuk menyimpan.

---

### Langkah 7: Konfigurasi Berkas WSGI
Di tab **Web**, gulir ke bagian **Code** dan klik tautan berkas **WSGI configuration file** (biasanya bernama `/var/www/<username>_pythonanywhere_com_wsgi.py`).

Hapus seluruh kode default di dalamnya, lalu ganti dengan kode berikut:

```python
import sys
import os

# 1. Definisikan path ke direktori proyek Anda
# GANTI '<username>' dengan username PythonAnywhere Anda!
path = '/home/<username>/aplikasi_web_si'
if path not in sys.path:
    sys.path.insert(0, path)

# 2. Set working directory ke folder proyek agar file database siews.db terbaca
os.chdir(path)

# 3. Konfigurasi Environment Variable untuk Keamanan & Basis Data
os.environ['SECRET_KEY'] = 'si_peringatan_dini_super_aman_produksi_2026'
os.environ['DATABASE_URL'] = f'sqlite:///{path}/siews.db'

# 4. Impor instance Flask 'app' sebagai 'application' (standar WSGI PythonAnywhere)
from app import app as application
```

> 💡 **Penting**: Pastikan Anda mengganti `<username>` dengan nama pengguna akun PythonAnywhere Anda (contoh: `/home/yumrotul/aplikasi_web_si`).
> Klik tombol **Save** di pojok kanan atas setelah selesai mengedit.

---

### Langkah 8: Reload Web App & Selesai! 🎉
1. Kembali ke tab **Web**.
2. Klik tombol hijau besar: **"Reload <username>.pythonanywhere.com"**.
3. Buka tautan situs Anda:
   **`https://<username>.pythonanywhere.com`**

Aplikasi web SI Peringatan Dini Anda kini sudah aktif dan dapat diakses publik!

---

### 🔧 Troubleshooting di PythonAnywhere

- **Muncul Pesan Error "Something went wrong (500 Internal Server Error)"**:
  - Buka tab **Web** di PythonAnywhere, gulir ke bagian **Log files**.
  - Klik **Error log** (`<username>.pythonanywhere.com.error.log`) untuk melihat penyebab error secara detail.
- **Tabel Basis Data Tidak Ditemukan (`no such table: mahasiswa`)**:
  - Masuk ke Bash console, navigasikan ke folder proyek (`cd ~/aplikasi_web_si`), aktifkan venv (`source venv/bin/activate`), lalu jalankan `python app.py seed`.
- **Perubahan Kode Tidak Muncul di Website**:
  - Setiap kali Anda melakukan perubahan file atau menjalankan `git pull` di console PythonAnywhere, selalu klik tombol **Reload** di tab **Web**.

---

## 🧪 Pengujian Otomatis (Automated Testing)

Pengujian otomatis terisolasi telah disiapkan di dalam berkas [uji_app.py](file:///c:/aplikasi_web_si/uji_app.py). Pengujian berjalan pada basis data sementara di memori RAM (*in-memory* `sqlite://`) tanpa memengaruhi data produksi `siews.db`.

Jalankan pengujian di terminal:
```bash
python uji_app.py
```
atau dengan opsi verbose:
```bash
python -m unittest uji_app.py -v
```

### Cakupan 18 Skenario Uji:
- `test_rute_dasar_index` : Verifikasi HTTP 200 dan tampilan dashboard.
- `test_rute_mahasiswa_filter_prodi` : Verifikasi query string filtering data.
- `test_rute_mahasiswa_404` : Verifikasi penanganan error 404 pada NIM salah.
- `test_rute_api_mahasiswa_json` : Verifikasi struktur dan payload REST API JSON.
- `test_tambah_mahasiswa_valid` : Verifikasi form tambah valid menghasilkan HTTP 302 dan tersimpan di DB.
- `test_tambah_mahasiswa_semua_salah_422` : Verifikasi input tidak valid menghasilkan HTTP 422 dan memunculkan seluruh pesan error Bahasa Indonesia.
- `test_tambah_mahasiswa_nim_duplikat` : Verifikasi validator keunikan NIM menolak duplikasi data (HTTP 422).
- `test_relasi_tambah_catatan_mahasiswa` : Verifikasi penambahan catatan konseling dan relasi dua arah ORM (`back_populates`).
- `test_rute_hapus_mahasiswa_cascade` : Verifikasi penghapusan mahasiswa otomatis menghapus seluruh catatan terkaitnya (*cascade delete*).
- `test_rute_edit_mahasiswa_tampil_form_200` : Verifikasi form edit menampilkan data awal mahasiswa (HTTP 200).
- `test_rute_edit_mahasiswa_sukses_302` : Verifikasi edit data valid tersimpan, kalkulasi status risiko terbarui, dan redirect ke detail.
- `test_rute_edit_mahasiswa_tetap_nim_sama` : Verifikasi edit dengan NIM yang sama tidak terblokir oleh validator unik berkat `current_id`.
- `test_rute_edit_mahasiswa_nim_duplikat_422` : Verifikasi edit dengan NIM milik mahasiswa lain ditolak dengan HTTP 422.
- `test_rute_edit_mahasiswa_404` : Verifikasi HTTP 404 saat mengakses edit untuk NIM yang tidak ada.
- `test_export_csv_semua_mahasiswa` : Verifikasi rute `/mahasiswa/export` menghasilkan file CSV valid.
- `test_export_csv_filter_prodi` : Verifikasi export CSV dengan parameter `?prodi=SI`.
- `test_export_csv_filter_berisiko` : Verifikasi export CSV dengan parameter `?status=berisiko`.
- `test_export_csv_nama_file_dinamis` : Verifikasi header filename CSV mengandung tanggal dan filter aktif.

---

## 🛡️ Prinsip Keamanan & Best Practices

1. **Proteksi Cross-Site Request Forgery (CSRF)**:
   - Setiap formulir HTML dilindungi menggunakan token CSRF unik yang dihasilkan oleh Flask-WTF melalui `{{ form.hidden_tag() }}`.
2. **Pencegahan Cross-Site Scripting (XSS)**:
   - Jinja2 secara otomatis mengonversi karakter berbahaya (`<`, `>`, `&`, `"`, `'`) menjadi entitas HTML aman tanpa menggunakan filter `| safe` pada input pengguna.
3. **Pencegahan SQL Injection**:
   - Seluruh interaksi basis data menggunakan SQLAlchemy 2.x dengan *parameterized queries* bawaan (`db.select(...)`).
4. **Pola Post/Redirect/Get (PRG)**:
   - Seluruh request `POST` merespons dengan HTTP Status 302/Redirect ke rute `GET` tujuan untuk menghindari resubmisi data ganda saat pengguna me-*refresh* halaman peramban.
5. **Penanganan Status Kode HTTP Representatif**:
   - `200 OK` untuk operasi baca sukses.
   - `302 Found / Redirect` untuk transisi sukses setelah pengiriman formulir.
   - `404 Not Found` untuk rute atau data yang tidak ditemukan.
   - `422 Unprocessable Entity` untuk pengiriman formulir yang gagal validasi.
6. **Eksekusi Debug Terisolasi**:
   - Parameter `debug=True` diproteksi secara ketat di dalam blok `if __name__ == "__main__":` sehingga nonaktif secara otomatis saat dijalankan di server produksi WSGI PythonAnywhere.

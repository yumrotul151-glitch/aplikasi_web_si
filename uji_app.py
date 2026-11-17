"""Script Pengujian Otomatis Aplikasi SI Peringatan Dini (Tahap 2).

Pengujian terisolasi menggunakan basis data in-memory (DATABASE_URL=sqlite://) dan penonaktifan CSRF.
Menguji operasi ORM SQLAlchemy 2.x, validasi formulir Flask-WTF, dan integrasi rute.
"""

import os
import unittest

# Konfigurasi DATABASE_URL menjadi sqlite:// sebelum mengimpor app
os.environ["DATABASE_URL"] = "sqlite://"

from app import app
from models import Catatan, Mahasiswa, db

# Konfigurasi testing dan matikan CSRF untuk pengujian
app.config["TESTING"] = True
app.config["WTF_CSRF_ENABLED"] = False


class TestSIPeringatanDini(unittest.TestCase):
    """Pengujian terisolasi untuk seluruh fungsionalitas aplikasi SI Peringatan Dini."""

    def setUp(self):
        """Inisialisasi basis data pengujian terisolasi sebelum setiap method test."""
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

        # Buat tabel di basis data in-memory
        db.create_all()

        # Bersihkan data lama jika ada
        db.session.execute(db.delete(Catatan))
        db.session.execute(db.delete(Mahasiswa))
        db.session.commit()

        # Seed data awal pengujian
        self.mhs_andi = Mahasiswa(
            nim="A11.2023.00001",
            nama="Andi Pratama",
            prodi="SI",
            ipk=3.75,
            kehadiran=92,
            email="andi@mhs.kampus.ac.id",
        )
        self.mhs_budi = Mahasiswa(
            nim="A11.2023.00002",
            nama="Budi Santoso",
            prodi="TI",
            ipk=2.45,
            kehadiran=68,
            email="budi@mhs.kampus.ac.id",
        )

        db.session.add_all([self.mhs_andi, self.mhs_budi])
        db.session.commit()

    def tearDown(self):
        """Bersihkan basis data setelah setiap method test selesai dieksekusi."""
        db.session.rollback()
        db.session.execute(db.delete(Catatan))
        db.session.execute(db.delete(Mahasiswa))
        db.session.commit()
        db.session.remove()
        self.app_context.pop()

    # -------------------------------------------------------------------------
    # 1. Pengiriman form MahasiswaForm dengan Data Valid (Status 302)
    # -------------------------------------------------------------------------
    def test_tambah_mahasiswa_valid(self):
        """Memastikan pengiriman data valid pada MahasiswaForm merespons HTTP 302 (Redirect) dan tersimpan di DB."""
        data_valid = {
            "nim": "A11.2023.00010",
            "nama": "Gita Savitri",
            "prodi": "SI",
            "ipk": "3.85",
            "kehadiran": "95",
            "email": "gita@mhs.kampus.ac.id",
        }

        response = self.client.post("/mahasiswa/tambah", data=data_valid)

        # 1. Pastikan kembali dengan status kode 302 (Redirect ke /mahasiswa)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/mahasiswa", response.headers.get("Location", ""))

        # 2. Verifikasi data tersimpan di basis data via ORM
        stmt = db.select(Mahasiswa).filter_by(nim="A11.2023.00010")
        mhs = db.session.execute(stmt).scalar_one_or_none()

        self.assertIsNotNone(mhs, "Mahasiswa baru harus tersimpan di basis data")
        self.assertEqual(mhs.nama, "Gita Savitri")
        self.assertEqual(mhs.prodi, "SI")
        self.assertAlmostEqual(mhs.ipk, 3.85)
        self.assertEqual(mhs.kehadiran, 95)
        self.assertEqual(mhs.email, "gita@mhs.kampus.ac.id")

    # -------------------------------------------------------------------------
    # 2. Pengiriman Form dengan Data yang Salah Semua (Status 422 & Error Message)
    # -------------------------------------------------------------------------
    def test_tambah_mahasiswa_semua_salah_422(self):
        """Memastikan pengiriman data yang salah semua menghasilkan HTTP 422 dan pesan error muncul."""
        data_salah = {
            "nim": "123_BUKAN_FORMAT",  # Format salah (gagal Regexp A11.2023.00001)
            "nama": "A",                 # Kurang dari 3 karakter (gagal Length min=3)
            "prodi": "KEDOKTERAN",       # Bukan SI, TI, MI (gagal AnyOf)
            "ipk": "5.50",               # Di atas 4.00 (gagal NumberRange)
            "kehadiran": "150",          # Di atas 100% (gagal NumberRange)
            "email": "bukan-format-email", # Email tidak valid (gagal Email)
        }

        response = self.client.post("/mahasiswa/tambah", data=data_salah)

        # 1. Pastikan kembali status kode 422 (Unprocessable Entity)
        self.assertEqual(response.status_code, 422)

        konten_html = response.get_data(as_text=True)

        # 2. Pastikan pesan error Bahasa Indonesia dari masing-masing validator muncul di HTML
        self.assertIn("Format NIM tidak valid", konten_html)
        self.assertIn("Nama lengkap harus memiliki panjang antara 3 hingga 100 karakter", konten_html)
        self.assertIn("Pilihan Program Studi harus salah satu dari: SI, TI, atau MI", konten_html)
        self.assertIn("Nilai IPK harus berada pada rentang skala 0.00 hingga 4.00", konten_html)
        self.assertIn("Tingkat kehadiran harus berada pada rentang 0 sampai 100 persen", konten_html)
        self.assertIn("Format alamat email tidak valid", konten_html)

    # -------------------------------------------------------------------------
    # 3. Pengiriman NIM yang Sudah Ada (Validasi Khusus validate_nim)
    # -------------------------------------------------------------------------
    def test_tambah_mahasiswa_nim_duplikat(self):
        """Memastikan validator khusus validate_nim menolak NIM yang telah terdaftar."""
        data_duplikat = {
            "nim": "A11.2023.00001",  # NIM milik Andi Pratama yang sudah ada di setUp
            "nama": "Mahasiswa Pengganda",
            "prodi": "TI",
            "ipk": "3.10",
            "kehadiran": "85",
            "email": "pengganda@mhs.kampus.ac.id",
        }

        response = self.client.post("/mahasiswa/tambah", data=data_duplikat)

        # Pastikan kembali status kode 422
        self.assertEqual(response.status_code, 422)

        # Pastikan pesan error dari fungsi validate_nim muncul
        konten_html = response.get_data(as_text=True)
        self.assertIn("sudah terdaftar dalam sistem", konten_html)

    # -------------------------------------------------------------------------
    # 4. Uji Relasi ORM (Menambahkan Catatan ke Mahasiswa & Query Relasi Dua Arah)
    # -------------------------------------------------------------------------
    def test_relasi_tambah_catatan_mahasiswa(self):
        """Memastikan catatan bimbingan berhasil terhubung ke mahasiswa lewat query relasi ORM."""
        nim_target = "A11.2023.00001"
        data_catatan = {
            "jenis": "Akademik",
            "isi": "Konseling rencana perbaikan nilai dan pengajuan mata kuliah semester pendek.",
        }

        # Kirim request POST ke rute detail mahasiswa untuk menambah catatan
        response = self.client.post(f"/mahasiswa/{nim_target}", data=data_catatan)

        # Verifikasi respons adalah Redirect (HTTP 302) mengikuti pola PRG
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/mahasiswa/{nim_target}", response.headers.get("Location", ""))

        # 1. Uji relasi lewat ORM: Query objek Mahasiswa
        stmt_mhs = db.select(Mahasiswa).filter_by(nim=nim_target)
        mahasiswa = db.session.execute(stmt_mhs).scalar_one_or_none()

        self.assertIsNotNone(mahasiswa)
        self.assertEqual(len(mahasiswa.catatan), 1, "Mahasiswa harus memiliki 1 catatan berelasi")

        # 2. Uji atribut objek Catatan yang berelasi
        catatan = mahasiswa.catatan[0]
        self.assertEqual(catatan.jenis, "Akademik")
        self.assertEqual(catatan.isi, "Konseling rencana perbaikan nilai dan pengajuan mata kuliah semester pendek.")

        # 3. Uji relasi balik dua arah (back_populates): Catatan -> Mahasiswa
        self.assertEqual(catatan.mahasiswa.nim, nim_target)
        self.assertEqual(catatan.mahasiswa.nama, "Andi Pratama")

    # -------------------------------------------------------------------------
    # 5. Skenario Tambahan: Uji Rute GET, API JSON, dan Hapus (Cascade Delete)
    # -------------------------------------------------------------------------
    def test_rute_dasar_index(self):
        """Memastikan rute dasar (/) menghasilkan HTTP 200 dan memuat ringkasan statistik."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        konten = response.get_data(as_text=True)
        self.assertIn("Dashboard Peringatan Dini", konten)
        self.assertIn("Total Mahasiswa", konten)

    def test_rute_mahasiswa_filter_prodi(self):
        """Memastikan filter query string ?prodi=ti menampilkan data yang sesuai."""
        response = self.client.get("/mahasiswa?prodi=ti")
        self.assertEqual(response.status_code, 200)
        konten = response.get_data(as_text=True)
        self.assertIn("Budi Santoso", konten)
        self.assertNotIn("Andi Pratama", konten)

    def test_rute_mahasiswa_404(self):
        """Memastikan rute detail mahasiswa dengan NIM salah mengembalikan 404."""
        response = self.client.get("/mahasiswa/A11.2099.99999")
        self.assertEqual(response.status_code, 404)

    def test_rute_api_mahasiswa_json(self):
        """Memastikan API JSON mengembalikan data mahasiswa dan daftar relasi catatannya."""
        response = self.client.get("/api/mahasiswa/A11.2023.00001")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_json)

        payload = response.get_json()
        self.assertTrue(payload.get("success"))
        self.assertEqual(payload["data"]["nama"], "Andi Pratama")
        self.assertIn("catatan", payload["data"])

    def test_rute_hapus_mahasiswa_cascade(self):
        """Memastikan penghapusan mahasiswa menghapus data beserta relasi catatannya (cascade delete)."""
        # Tambah catatan terlebih dahulu untuk Budi
        catatan_budi = Catatan(jenis="Keuangan", isi="Kendala pembayaran UKT semester ini.", mahasiswa=self.mhs_budi)
        db.session.add(catatan_budi)
        db.session.commit()
        id_budi = self.mhs_budi.id

        # Hapus mahasiswa Budi via form POST
        response = self.client.post("/mahasiswa/A11.2023.00002/hapus")
        self.assertEqual(response.status_code, 302)

        # Verifikasi mahasiswa terhapus
        stmt_mhs = db.select(Mahasiswa).filter_by(nim="A11.2023.00002")
        mhs_terhapus = db.session.execute(stmt_mhs).scalar_one_or_none()
        self.assertIsNone(mhs_terhapus)

        # Verifikasi seluruh catatan milik Budi terhapus secara otomatis oleh cascade="all, delete-orphan"
        stmt_catatan = db.select(Catatan).filter_by(mahasiswa_id=id_budi)
        catatan_terhapus = db.session.execute(stmt_catatan).scalars().all()
        self.assertEqual(len(catatan_terhapus), 0)

    # -------------------------------------------------------------------------
    # 6. Pengujian Fitur Edit / Pembaruan Data Mahasiswa (/mahasiswa/<nim>/edit)
    # -------------------------------------------------------------------------
    def test_rute_edit_mahasiswa_tampil_form_200(self):
        """Memastikan rute GET /mahasiswa/<nim>/edit menampilkan form terisi dan status HTTP 200."""
        response = self.client.get("/mahasiswa/A11.2023.00001/edit")
        self.assertEqual(response.status_code, 200)

        konten_html = response.get_data(as_text=True)
        self.assertIn("Edit Data Mahasiswa", konten_html)
        self.assertIn("Andi Pratama", konten_html)
        self.assertIn("A11.2023.00001", konten_html)

    def test_rute_edit_mahasiswa_sukses_302(self):
        """Memastikan pembaruan data valid merespons HTTP 302, tersimpan di DB, dan status risiko terbarui."""
        data_update = {
            "nim": "A11.2023.00002",
            "nama": "Budi Santoso Updated",
            "prodi": "TI",
            "ipk": "3.25",       # Nilai ditingkatkan dari 2.45
            "kehadiran": "88",   # Presensi ditingkatkan dari 68%
            "email": "budi_baru@mhs.kampus.ac.id",
        }

        response = self.client.post("/mahasiswa/A11.2023.00002/edit", data=data_update)

        # 1. Pastikan redirect ke halaman detail mahasiswa
        self.assertEqual(response.status_code, 302)
        self.assertIn("/mahasiswa/A11.2023.00002", response.headers.get("Location", ""))

        # 2. Verifikasi perubahan di database via ORM
        stmt = db.select(Mahasiswa).filter_by(nim="A11.2023.00002")
        mhs = db.session.execute(stmt).scalar_one_or_none()

        self.assertIsNotNone(mhs)
        self.assertEqual(mhs.nama, "Budi Santoso Updated")
        self.assertAlmostEqual(mhs.ipk, 3.25)
        self.assertEqual(mhs.kehadiran, 88)
        self.assertEqual(mhs.email, "budi_baru@mhs.kampus.ac.id")

        # 3. Verifikasi evaluasi peringatan dini berubah menjadi aman (tidak berisiko)
        self.assertFalse(mhs.is_berisiko, "Mahasiswa yang telah memperbaiki IPK dan presensi harus keluar dari kategori risiko")

    def test_rute_edit_mahasiswa_tetap_nim_sama(self):
        """Memastikan mode edit dengan NIM yang sama tidak terblokir oleh validator keunikan NIM."""
        data_sama = {
            "nim": "A11.2023.00001",  # NIM tetap sama
            "nama": "Andi Pratama Edit",
            "prodi": "SI",
            "ipk": "3.80",
            "kehadiran": "94",
            "email": "andi@mhs.kampus.ac.id",
        }

        response = self.client.post("/mahasiswa/A11.2023.00001/edit", data=data_sama)
        self.assertEqual(response.status_code, 302)

        stmt = db.select(Mahasiswa).filter_by(nim="A11.2023.00001")
        mhs = db.session.execute(stmt).scalar_one_or_none()
        self.assertEqual(mhs.nama, "Andi Pratama Edit")

    def test_rute_edit_mahasiswa_nim_duplikat_422(self):
        """Memastikan mode edit menolak jika NIM diubah menjadi NIM milik mahasiswa lain (HTTP 422)."""
        data_bentrok = {
            "nim": "A11.2023.00001",  # Mencoba memakai NIM milik Andi Pratama
            "nama": "Budi Santoso",
            "prodi": "TI",
            "ipk": "2.45",
            "kehadiran": "68",
            "email": "budi@mhs.kampus.ac.id",
        }

        response = self.client.post("/mahasiswa/A11.2023.00002/edit", data=data_bentrok)
        self.assertEqual(response.status_code, 422)

        konten_html = response.get_data(as_text=True)
        self.assertIn("sudah terdaftar dalam sistem", konten_html)

    def test_rute_edit_mahasiswa_404(self):
        """Memastikan akses edit mahasiswa dengan NIM tidak terdaftar menghasilkan HTTP 404."""
        response = self.client.get("/mahasiswa/A11.2099.99999/edit")
        self.assertEqual(response.status_code, 404)


# -----------------------------------------------------------------------------
# Eksekusi Test Runner
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Aplikasi Web Sistem Informasi Peringatan Dini Akademik (SI Peringatan Dini).

Dibangun menggunakan Python 3.11+, Flask, Jinja2, Flask-SQLAlchemy, dan Flask-WTF.
Menggunakan basis data SQLite dengan gaya query SQLAlchemy 2.x serta validasi sisi server.
"""

import csv
import io
import os
from datetime import datetime, timezone
from typing import Any
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

# Impor instance database dan model dari models.py
from models import Catatan, Mahasiswa, db

# Impor kelas formulir dari forms.py
from forms import CatatanForm, MahasiswaForm

# -----------------------------------------------------------------------------
# Inisialisasi & Konfigurasi Aplikasi Flask
# -----------------------------------------------------------------------------
app = Flask(__name__)

# Konfigurasi SECRET_KEY untuk perlindungan sesi dan form CSRF
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "si_peringatan_dini_secret_key_super_aman_2026"
)

# Konfigurasi SQLAlchemy Database URI (SQLite siews.db)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///siews.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Hubungkan instance SQLAlchemy dengan aplikasi Flask
db.init_app(app)

# Buat tabel otomatis jika belum ada saat inisialisasi aplikasi
with app.app_context():
    db.create_all()


# -----------------------------------------------------------------------------
# Custom Jinja Filters
# -----------------------------------------------------------------------------
@app.template_filter("predikat")
def filter_predikat(ipk: float | int | Any) -> str:
    """Filter Jinja: Mengonversi nilai IPK ke predikat akademik standar."""
    try:
        val = float(ipk)
        if val >= 3.51:
            return "Dengan Pujian (Cumlaude)"
        elif val >= 3.00:
            return "Sangat Memuaskan"
        elif val >= 2.76:
            return "Memuaskan"
        elif val >= 2.00:
            return "Cukup"
        else:
            return "Kurang (Perlu Perhatian)"
    except (ValueError, TypeError):
        return "-"


@app.template_filter("persen")
def filter_persen(kehadiran: float | int | Any) -> str:
    """Filter Jinja: Memformat angka rasio/persentase menjadi format persen (%).

    Mendukung format rasio desimal (0.85 -> 85%) maupun skala 100 (85 -> 85%).
    """
    try:
        val = float(kehadiran)
        if val <= 1.0:
            val = val * 100
        return f"{val:.0f}%"
    except (ValueError, TypeError):
        return "-"


# -----------------------------------------------------------------------------
# Routing Aplikasi
# -----------------------------------------------------------------------------

# 1. Rute Dasar (/): Dashboard Peringatan Dini
@app.route("/")
def index():
    """Rute dasar: Dashboard SI Peringatan Dini menggunakan query SQLAlchemy 2.x."""
    # Eksekusi query gaya SQLAlchemy 2.x
    stmt = db.select(Mahasiswa).order_by(Mahasiswa.nama)
    semua_mahasiswa = db.session.execute(stmt).scalars().all()

    total_mahasiswa = len(semua_mahasiswa)
    mahasiswa_berisiko = [m for m in semua_mahasiswa if m.is_berisiko]
    total_berisiko = len(mahasiswa_berisiko)

    return render_template(
        "index.html",
        total_mahasiswa=total_mahasiswa,
        total_berisiko=total_berisiko,
        mahasiswa_berisiko=mahasiswa_berisiko,
    )


# 2. Rute Daftar Mahasiswa (/mahasiswa): Mendukung filter ?prodi=
@app.route("/mahasiswa")
def daftar_mahasiswa():
    """Rute daftar mahasiswa: Mendukung filter query string ?prodi= dengan gaya SQLAlchemy 2.x."""
    prodi_filter = request.args.get("prodi", "").strip()

    stmt = db.select(Mahasiswa)
    if prodi_filter:
        stmt = stmt.filter(Mahasiswa.prodi.ilike(f"%{prodi_filter}%"))

    mahasiswa = db.session.execute(stmt.order_by(Mahasiswa.nama)).scalars().all()

    # Query daftar prodi unik untuk opsi filter antarmuka
    stmt_prodi = db.select(Mahasiswa.prodi).distinct().order_by(Mahasiswa.prodi)
    daftar_prodi = db.session.execute(stmt_prodi).scalars().all()

    return render_template(
        "mahasiswa.html",
        mahasiswa=mahasiswa,
        prodi_aktif=prodi_filter,
        daftar_prodi=daftar_prodi,
    )


# 3. Rute Tambah Mahasiswa (/mahasiswa/tambah): GET & POST dengan MahasiswaForm
@app.route("/mahasiswa/tambah", methods=["GET", "POST"])
def tambah_mahasiswa():
    """Rute penambahan mahasiswa baru dengan validasi MahasiswaForm.

    Jika form.validate_on_submit() lolos, simpan ke database dengan db.session.add dan commit().
    Jika tidak lolos validasi, kembalikan dengan status kode 422.
    """
    form = MahasiswaForm()

    if request.method == "POST":
        if form.validate_on_submit():
            mhs_baru = Mahasiswa(
                nim=form.nim.data.strip().upper(),
                nama=form.nama.data.strip(),
                prodi=form.prodi.data,
                ipk=float(form.ipk.data),
                kehadiran=int(form.kehadiran.data),
                email=form.email.data.strip() if form.email.data else None,
            )
            db.session.add(mhs_baru)
            db.session.commit()
            flash(
                f"Data mahasiswa {mhs_baru.nama} ({mhs_baru.nim}) berhasil ditambahkan ke basis data!",
                "success",
            )
            return redirect(url_for("daftar_mahasiswa"))

        # Jika validasi gagal saat submit POST, kembalikan respons dengan status kode 422
        return render_template("tambah.html", form=form), 422

    # Request GET: Tampilkan formulir kosong
    return render_template("tambah.html", form=form)


# 4. Rute Detail & Tambah Catatan (/mahasiswa/<nim>): GET & POST dengan CatatanForm
@app.route("/mahasiswa/<nim>", methods=["GET", "POST"])
def detail_mahasiswa(nim: str):
    """Rute detail mahasiswa serta penambahan catatan bimbingan menggunakan CatatanForm."""
    stmt = db.select(Mahasiswa).filter_by(nim=nim)
    mhs = db.session.execute(stmt).scalar_one_or_none()

    if not mhs:
        abort(404, description=f"Mahasiswa dengan NIM '{nim}' tidak ditemukan.")

    form = CatatanForm()

    if request.method == "POST":
        if form.validate_on_submit():
            catatan_baru = Catatan(
                jenis=form.jenis.data,
                isi=form.isi.data.strip(),
                mahasiswa=mhs,
            )
            db.session.add(catatan_baru)
            db.session.commit()
            flash(
                f"Catatan konseling kategori '{catatan_baru.jenis}' berhasil ditambahkan!",
                "success",
            )
            # Pola Post/Redirect/Get (PRG)
            return redirect(url_for("detail_mahasiswa", nim=nim))

        # Jika validasi CatatanForm gagal pada POST
        return (
            render_template(
                "detail.html",
                mahasiswa=mhs,
                berisiko=mhs.is_berisiko,
                form=form,
            ),
            422,
        )

    # Request GET
    return render_template(
        "detail.html",
        mahasiswa=mhs,
        berisiko=mhs.is_berisiko,
        form=form,
    )


# 5. Rute Hapus Mahasiswa (/mahasiswa/<nim>/hapus): Hanya menerima POST
@app.route("/mahasiswa/<nim>/hapus", methods=["POST"])
def hapus_mahasiswa(nim: str):
    """Rute penghapusan mahasiswa beserta catatannya (Hanya menerima metode POST)."""
    stmt = db.select(Mahasiswa).filter_by(nim=nim)
    mhs = db.session.execute(stmt).scalar_one_or_none()

    if not mhs:
        abort(404, description=f"Mahasiswa dengan NIM '{nim}' tidak ditemukan.")

    nama_mhs = mhs.nama
    db.session.delete(mhs)
    db.session.commit()
    flash(
        f"Data mahasiswa {nama_mhs} ({nim}) beserta seluruh catatannya berhasil dihapus dari sistem.",
        "info",
    )
    return redirect(url_for("daftar_mahasiswa"))


# 6. Rute Form Pencarian (/cari): Metode POST merespons dengan Redirect (PRG Pattern)
@app.route("/cari", methods=["GET", "POST"])
def cari():
    """Rute pencarian menerapkan pola Post/Redirect/Get (PRG)."""
    if request.method == "POST":
        nim = request.form.get("nim", "").strip()
        prodi = request.form.get("prodi", "").strip()

        # Prioritas 1: Jika pencarian NIM diisi, redirect ke detail mahasiswa
        if nim:
            return redirect(url_for("detail_mahasiswa", nim=nim))

        # Prioritas 2: Jika prodi diisi, redirect ke daftar mahasiswa dengan query string
        if prodi:
            return redirect(url_for("daftar_mahasiswa", prodi=prodi))

        return redirect(url_for("daftar_mahasiswa"))

    stmt_prodi = db.select(Mahasiswa.prodi).distinct().order_by(Mahasiswa.prodi)
    daftar_prodi = db.session.execute(stmt_prodi).scalars().all()
    return render_template("cari.html", daftar_prodi=daftar_prodi)


# 7. Rute Export CSV (/mahasiswa/export): GET dengan query string ?prodi= & ?status=
@app.route("/mahasiswa/export")
def export_mahasiswa_csv():
    """Rute export data mahasiswa ke file CSV.

    Query string opsional:
      - ?prodi=SI        -> filter berdasarkan program studi
      - ?status=berisiko -> hanya mahasiswa berisiko
    """
    prodi_filter = request.args.get("prodi", "").strip()
    status_filter = request.args.get("status", "").strip().lower()

    stmt = db.select(Mahasiswa)
    if prodi_filter:
        stmt = stmt.filter(Mahasiswa.prodi.ilike(f"%{prodi_filter}%"))
    stmt = stmt.order_by(Mahasiswa.nama)
    semua = db.session.execute(stmt).scalars().all()

    if status_filter == "berisiko":
        semua = [m for m in semua if m.is_berisiko]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "NIM", "Nama", "Program Studi", "IPK", "Kehadiran (%)",
        "Predikat", "Status Peringatan", "Email", "Jumlah Catatan"
    ])
    for m in semua:
        writer.writerow([
            m.nim,
            m.nama,
            m.prodi,
            f"{m.ipk:.2f}",
            m.kehadiran,
            filter_predikat(m.ipk),
            "BERISIKO" if m.is_berisiko else "Aman",
            m.email or "",
            len(m.catatan),
        ])

    tanggal = datetime.now(timezone.utc).strftime("%Y%m%d")
    bagian_prodi = f"_{prodi_filter.upper()}" if prodi_filter else ""
    bagian_status = "_berisiko" if status_filter == "berisiko" else ""
    nama_file = f"mahasiswa{bagian_prodi}{bagian_status}_{tanggal}.csv"

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f"attachment; filename={nama_file}"
    return response


# 8. Rute REST API JSON (/api/mahasiswa/<nim>): Menggunakan SQLAlchemy 2.x
@app.route("/api/mahasiswa/<nim>")
def api_mahasiswa(nim: str):
    """Rute API RESTful: Mengembalikan data mahasiswa dan relasi catatan dalam format JSON."""
    stmt = db.select(Mahasiswa).filter_by(nim=nim)
    mhs = db.session.execute(stmt).scalar_one_or_none()

    if not mhs:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Mahasiswa tidak ditemukan",
                    "nim": nim,
                    "status_code": 404,
                }
            ),
            404,
        )

    # Format data catatan berelasi
    daftar_catatan = [
        {
            "id": c.id,
            "jenis": c.jenis,
            "isi": c.isi,
            "dibuat": c.dibuat.isoformat() if c.dibuat else None,
        }
        for c in mhs.catatan
    ]

    data_response = {
        "success": True,
        "data": {
            "id": mhs.id,
            "nim": mhs.nim,
            "nama": mhs.nama,
            "prodi": mhs.prodi,
            "ipk": mhs.ipk,
            "kehadiran": mhs.kehadiran,
            "email": mhs.email,
            "predikat": filter_predikat(mhs.ipk),
            "kehadiran_persen": filter_persen(mhs.kehadiran),
            "berisiko": mhs.is_berisiko,
            "total_catatan": len(daftar_catatan),
            "catatan": daftar_catatan,
        },
    }
    return jsonify(data_response), 200


# -----------------------------------------------------------------------------
# Penanganan Error (Error Handler 404)
# -----------------------------------------------------------------------------
@app.errorhandler(404)
def page_not_found(error):
    """Handler penanganan error HTTP 404 Not Found."""
    pesan_error = getattr(error, "description", "Halaman tidak ditemukan")

    if request.path.startswith("/api/") or request.is_json:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Resource tidak ditemukan",
                    "message": pesan_error,
                    "status_code": 404,
                }
            ),
            404,
        )

    return (
        render_template(
            "404.html",
            pesan=pesan_error,
        ),
        404,
    )


# -----------------------------------------------------------------------------
# Custom Flask CLI Command: flask seed
# -----------------------------------------------------------------------------
@app.cli.command("seed")
def seed():
    """Inisialisasi basis data dan memasukkan 5 data mahasiswa dummy."""
    # Reset schema basis data
    db.drop_all()
    db.create_all()

    dummy_mahasiswa = [
        Mahasiswa(
            nim="A11.2023.00001",
            nama="Andi Pratama",
            prodi="SI",
            ipk=3.75,
            kehadiran=92,
            email="andi@mhs.kampus.ac.id",
        ),
        Mahasiswa(
            nim="A11.2023.00002",
            nama="Budi Santoso",
            prodi="TI",
            ipk=2.45,
            kehadiran=68,
            email="budi@mhs.kampus.ac.id",
        ),
        Mahasiswa(
            nim="A11.2023.00003",
            nama="Citra Lestari",
            prodi="SI",
            ipk=3.85,
            kehadiran=96,
            email="citra@mhs.kampus.ac.id",
        ),
        Mahasiswa(
            nim="A11.2023.00004",
            nama="Dedi Kurniawan",
            prodi="MI",
            ipk=1.95,
            kehadiran=60,
            email="dedi@mhs.kampus.ac.id",
        ),
        Mahasiswa(
            nim="A11.2023.00005",
            nama="Eka Rahmawati",
            prodi="SI",
            ipk=3.10,
            kehadiran=85,
            email="eka@mhs.kampus.ac.id",
        ),
    ]

    # Berikan data catatan relasi untuk mahasiswa berisiko
    catatan_budi = Catatan(
        jenis="Akademik",
        isi="Mahasiswa dipanggil untuk bimbingan khusus karena nilai IPK semester ini di bawah standar 2.75.",
        mahasiswa=dummy_mahasiswa[1],
    )
    catatan_dedi = Catatan(
        jenis="Pribadi",
        isi="Konseling kendala presensi kehadiran kuliah di bawah 75% akibat masalah kesehatan.",
        mahasiswa=dummy_mahasiswa[3],
    )

    db.session.add_all(dummy_mahasiswa)
    db.session.add_all([catatan_budi, catatan_dedi])
    db.session.commit()

    print("Basis data berhasil direset dan 5 data mahasiswa dummy telah dimasukkan!")


# -----------------------------------------------------------------------------
# Menjalankan Server Aplikasi
# debug=True HANYA jika script dieksekusi langsung
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)

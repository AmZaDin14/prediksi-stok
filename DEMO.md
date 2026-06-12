# Prediksi Stok — Presentasi & Demo untuk Stakeholder

**Sistem Prediksi Stok berbasis AI untuk Toko/Gudang**

Dokumen ini adalah panduan presentasi dan demonstrasi sistem. Tidak perlu
pengetahuan teknis mendalam — cukup ikuti skenario demo.

---

## Daftar Isi

1. [Masalah & Solusi](#1-masalah--solusi)
2. [Cara Kerja Sistem](#2-cara-kerja-sistem)
3. [Tur Fitur](#3-tur-fitur)
4. [Skenario Demo Langsung](#4-skenario-demo-langsung)
5. [Tanya Jawab](#5-tanya-jawab)

---

## 1. Masalah & Solusi

### Masalah

| Masalah | Dampak |
|---------|--------|
| Stok habis tanpa diketahui | Kehilangan penjualan ↔ pelanggan kecewa |
| Stok berlebihan barang expired | Rugi modal, barang terbuang |
| Tidak tahu kapan harus order | Order mendadak, tergantung supplier |
| Catatan manual / di kepala | Rawan lapor, susah evaluasi |

### Solusi

**Prediksi Stok** adalah sistem yang:

- **Mencatat penjualan harian** — via chat WhatsApp, semudah kirim pesan
- **Menghitung stok tersisa secara real-time** — tanpa perlu catatan manual
- **Memprediksi kapan stok akan habis** — pakai AI Prophet dari Facebook
- **Mengingatkan sebelum kehabisan** — notifikasi otomatis ke WhatsApp
- **Menyediakan dashboard** — pantau semua produk dalam satu layar

### Target Pengguna

| Peran | Kebutuhan |
|-------|-----------|
| **Pemilik toko** | Pantau stok via WhatsApp, dapat notifikasi, lihat dashboard |
| **Kasir / pegawai** | Lapor penjualan via chat, tanpa ribet |
| **Manajer gudang** | Lihat prediksi, rencanakan order ke supplier |

---

## 2. Cara Kerja Sistem

```
                        ┌──────────────────────┐
                        │   WhatsApp Anda       │
                        │   (kirim "terjual"    │
                        │    & "cek stok")      │
                        └──────────┬───────────┘
                                   │
                                   ▼
┌──────────────────────┐    ┌──────────────────────┐
│  Bot WhatsApp        │───►│  Server Prediksi     │
│  (membaca pesan)     │    │  (mencatat, hitung,  │
│                      │◄───│  prediksi, kirim     │
│                      │    │  notifikasi)         │
└──────────────────────┘    └──────────┬───────────┘
                                       │
                         ┌─────────────┼──────────────┐
                         │             │              │
                         ▼             ▼              ▼
                   ┌──────────┐  ┌──────────┐  ┌──────────┐
                   │ Database │  │ AI Model │  │ Dashboard│
                   │ (SQLite) │  │(Prophet) │  │Streamlit │
                   └──────────┘  └──────────┘  └──────────┘
```

### Alur Sederhana

```
PAGI:  Pegawai kirim "terjual gula 5"       → sistem catat penjualan
SIANG: Pegawai kirim "terjual minyak 20"     → stok berkurang otomatis
SORE:  Pemilik cek "cek stok"                → lihat status + prediksi
MALAM: Pemilik konfirmasi "ok"               → stok diselaraskan
       atau sistem auto-confirm jam 23:00    → aman walau lupa
       Sistem akan retrain model prediksi    → makin akurat tiap hari
```

---

## 3. Tur Fitur

### 3.1. Catat Penjualan via WhatsApp

Cukup kirim pesan ke nomor bot:

```
terjual gula 5
          ↓
✅ Bot balas: "Gula +5 sak (total hari ini: 5)"
```

**Kelebihan:**
- Bisa multi produk: `terjual gula 2, minyak 10, beras 30`
- Auto-correct: `gula5 minyak10` tetap terbaca
- Deteksi jumlah mencurigakan: jika >10x rata-rata harian
- Langsung dapat total penjualan hari ini

### 3.2. Cek Status Stok Real-time

```
cek stok
          ↓
✅ Bot balas daftar semua produk:
   Gula: 27 sak | habis: 12 Jun ↓
   Minyak: 980 dus | habis: 19 Jun →
   ...
```

**Dibaca sebagai:**

| Ikon | Arti |
|------|------|
| `↑ ↓ →` | Tren penjualan naik/turun/stabil |
| `B` / `BL` / `M` | Fase model: bootstrap / blend / mature (makin matang makin akurat) |
| `high` / `med` / `low` | Tingkat kepercayaan prediksi |

### 3.3. Konfirmasi Stok Akhir Hari

**Opsi termudah — balas "ok":**

```
ok
          ↓
✅ "Stok hari ini dikonfirmasi:
   ✓ Gula: 27 sak
   ✓ Minyak: 980 dus
   ..."
```

**Atau manual untuk koreksi:**

```
cek stok gula 25, minyak 950
          ↓
✅ "Stok diperbarui. Gula: 25 sak (susut 2 sak, 7%)"
```

**Sistem akan mendeteksi:**
- ✓ **Sesuai** — selisih dalam batas wajar
- ⚠️ **Susut** — barang hilang/rusak/curi (selisih >10%)
- 🔄 **Restok** — ada barang masuk tak tercatat

### 3.4. Notifikasi Otomatis (Tanpa Diminta)

| Waktu | Notifikasi | Fungsi |
|-------|-----------|--------|
| 🕐 **08:00** | *"⚠️ PERINGATAN: Beras diperkirakan habis dalam 2 hari"* | Alert kehabisan — segera order! |
| 🕐 **20:00** | *"🔔 Waktunya cek stok! Expected hari ini..."* | Reminder + daftar stok |
| 🕐 **21:30** | *"⚠️ Stok BELUM dikonfirmasi untuk: ..."* | Eskalasi jika lupa |
| 🕐 **23:00** | *"🔄 Stok otomatis dikonfirmasi"* | Auto-confirm + backup harian |

### 3.5. Dashboard Web

Buka `http://localhost:8501` (password: `admin123`)

**Fitur:**

| Fitur | Manfaat |
|-------|---------|
| **Tabel stok** | Semua produk: stok, prediksi habis, tren, status (hijau/kuning/merah) |
| **Grafik penjualan 30 hari** | Lihat tren harian per produk |
| **Grafik prediksi 30 hari** | Lihat kapan stok akan habis |
| **Status WhatsApp** | QR code untuk pairing, status koneksi |
| **Tambah/Edit/Hapus produk** | Kelola katalog tanpa edit file |
| **Refresh otomatis** | Update tiap 10 detik |

### 3.6. Restok

```
restock aqua 200
          ↓
✅ "Aqua di-restok 200 dus. Stok sekarang: 480 dus."
```

### 3.7. Backup Otomatis

Setiap hari jam 23:00, sistem backup database dan konfigurasi produk.
Riwayat 7 hari terakhir disimpan. Aman dari kehilangan data.

---

## 4. Skenario Demo Langsung

### Persiapan

**Minimal:**
```bash
cd /home/amri/Projects/prediksi_stok
uv run uvicorn app.server:app --host 0.0.0.0 --port 8765
```

**Lengkap (untuk demo WhatsApp + Dashboard):**
```bash
# Terminal 1 — Server
uv run uvicorn app.server:app --host 0.0.0.0 --port 8765

# Terminal 2 — WhatsApp bot
cd whatsapp-bot && OWNER_NUMBER=+6281279454414 node index.js

# Terminal 3 — Dashboard
uv run streamlit run dashboard.py --server.port 8501
```

### Demo 1: Catat Penjualan via API (Tanpa WhatsApp)

Cukup pakai `curl` — cocok untuk demo di laptop tanpa WhatsApp sungguhan.

```bash
# 1. Cek server hidup
curl http://localhost:8765/health

# 2. Catat penjualan
curl -X POST http://localhost:8765/webhook \
  -H "Content-Type: application/json" \
  -d '{"from_number":"+62812","body":"terjual gula 3, minyak 10"}'

# 3. Cek status stok
curl -X POST http://localhost:8765/webhook \
  -H "Content-Type: application/json" \
  -d '{"from_number":"+62812","body":"cek stok"}'

# 4. Auto-confirm semua
curl -X POST http://localhost:8765/webhook \
  -H "Content-Type: application/json" \
  -d '{"from_number":"+62812","body":"ok"}'

# 5. Lihat prediksi
curl http://localhost:8765/predict/Gula

# 6. Lihat semua prediksi
curl http://localhost:8765/predict
```

### Demo 2: Catat Penjualan via WhatsApp

**Yang perlu disiapkan:**
1. WhatsApp bot berjalan → scan QR code dari dashboard
2. Nomor owner sudah terdaftar di `.env`

**Demo flow:**

| Langkah | Kirim Pesan | Yang Terjadi |
|---------|-------------|--------------|
| 1 | `terjual gula 2` | Bot balas "*Gula +2 sak (total hari ini: 2)*" |
| 2 | `terjual minyak 5, beras 20` | Bot balas multi produk |
| 3 | `cek stok` | Bot tampilkan semua produk + prediksi |
| 4 | `ok` | Semua stok dikonfirmasi dengan nilai expected |
| 5 | `cek stok gula 25` | Koreksi manual untuk produk tertentu |
| 6 | `restock aqua 200` | Tambah stok |
| 7 | `help` | Tampilkan bantuan |

### Demo 3: Dashboard

1. Buka `http://localhost:8501`
2. Login dengan `admin123`
3. Tunjukan tabel stok — warna hijau/kuning/merah
4. Pilih produk dari dropdown — grafik penjualan & prediksi
5. Buka **Status WhatsApp** — tunjukan QR code
6. Buka **Tambah Produk Baru** — tambah produk contoh

### Demo 4: Skenario Lengkap Satu Hari

Jalankan perintah ini berurutan untuk simulasi:

```bash
echo "═══ PAGI: catat penjualan ═══"
curl -X POST http://localhost:8765/webhook \
  -H "Content-Type: application/json" \
  -d '{"from_number":"+62812","body":"terjual gula 3, minyak 15"}'

echo "═══ SIANG: cek stok ═══"
curl -X POST http://localhost:8765/webhook \
  -H "Content-Type: application/json" \
  -d '{"from_number":"+62812","body":"cek stok"}'

echo "═══ SORE: tambah penjualan ═══"
curl -X POST http://localhost:8765/webhook \
  -H "Content-Type: application/json" \
  -d '{"from_number":"+62812","body":"terjual beras 25, aqua 10"}'

echo "═══ MALAM: konfirmasi stok ═══"
curl -X POST http://localhost:8765/webhook \
  -H "Content-Type: application/json" \
  -d '{"from_number":"+62812","body":"ok"}'

echo "═══ LIHAT PREDIKSI ═══"
curl http://localhost:8765/predict | python3 -m json.tool

echo "═══ BUKA DASHBOARD ═══"
echo "→ http://localhost:8501 (password: admin123)"
```

---

## 5. Tanya Jawab

### Q: Apakah harus pakai WhatsApp? Bisa pakai cara lain?

WhatsApp adalah cara termudah: pegawai cukup kirim pesan seperti chat biasa.
Tapi sistem juga punya API HTTP — bisa diintegrasikan dengan aplikasi kasir,
aplikasi chat lain, atau diotomatisasi.

### Q: Bagaimana akurasi prediksi?

Akurasi meningkat seiring waktu. Tiga fase:

| Fase | Data | Akurasi |
|------|------|---------|
| **Bootstrap** (0 hari) | Data sintetis berdasarkan estimasi owner | Perkiraan awal |
| **Blend** (1-59 hari) | Sintetis + data nyata | Mulai akurat |
| **Mature** (≥60 hari) | Data nyata 100% | Tinggi |

### Q: Kalau lupa / tidak sempat konfirmasi stok malam?

Tidak masalah. Sistem akan:
1. Mengingatkan jam 20:00 dan 21:30
2. Otomatis konfirmasi jam 23:00 dengan stok yang diperkirakan
3. Besok pagi bisa koreksi jika ada selisih

### Q: Bagaimana kalau ada barang rusak / hilang / curi?

Sistem mendeteksi penyusutan (shrinkage). Saat konfirmasi malam, jika stok
aktual berbeda >10% dari perkiraan, sistem akan menandai sebagai **susut**.
Ini membantu owner mengetahui adanya barang hilang atau rusak.

### Q: Bisakah untuk banyak toko?

Saat ini untuk satu toko/gudang. Bisa dikembangkan untuk multi-toko dengan
menambahkan identitas toko di setiap data penjualan.

### Q: Apakah data aman?

- Semua data tersimpan di database lokal (SQLite) — tidak dikirim ke cloud
- Backup otomatis setiap hari (riwayat 7 hari)
- Dashboard dilindungi password
- Koneksi WhatsApp aman (end-to-end encrypted)

### Q: Berapa biaya operasional?

- **Server**: bisa di laptop/Raspberry Pi/VPS murah (spesifikasi minimal)
- **WhatsApp**: gratis (pakai nomor biasa)
- **Lisensi**: open source, tidak ada biaya langganan
- **Listrik**: sangat kecil

### Q: Bagaimana cara memulai?

1. Install Python + Node.js di laptop/VPS
2. Clone repositori, install dependensi
3. Generate data sintetis (untuk langsung lihat prediksi)
4. Jalankan server + WhatsApp bot
5. Scan QR code — siap digunakan

> Waktu setup: ~15 menit.

---

## Lampiran: Perintah Cepat

### WhatsApp

| Perintah | Fungsi |
|----------|--------|
| `terjual gula 5` | Catat penjualan 5 sak gula |
| `terjual gula 2, minyak 10` | Catat multi produk |
| `cek stok` | Status semua produk + prediksi |
| `ok` / `oke` | Auto-confirm semua stok |
| `cek stok gula 25` | Konfirmasi manual gula = 25 |
| `restock aqua 200` | Tambah stok aqua 200 dus |
| `help` | Tampilkan bantuan |

### API (HTTP)

| Endpoint | Fungsi |
|----------|--------|
| `GET /health` | Cek server |
| `POST /webhook` | Kirim perintah (body: `from_number`, `body`) |
| `GET /predict` | Prediksi semua produk |
| `GET /predict/{produk}` | Prediksi satu produk |
| `GET /outgoing` | Lihat pesan keluar yang antri |
| `POST /restart-bot` | Restart WhatsApp bot |

### Dashboard

Buka `http://localhost:8501` — password: `admin123`

---

> Dokumentasi lengkap: `SIMULASI.md` (demo via API) dan `SIMULASI_WA.md` (demo via WhatsApp)

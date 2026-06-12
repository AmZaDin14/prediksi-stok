# Panduan Simulasi via WhatsApp — End-to-End

Dokumen ini memandu simulasi lengkap sistem menggunakan WhatsApp sungguhan.
Anda perlu **dua nomor WhatsApp**: satu untuk owner (bot), satu untuk
admin/operator yang mengirim perintah.

---

## Daftar Isi

1. [Setup Awal](#1-setup-awal)
2. [Pairing WhatsApp](#2-pairing-whatsapp)
3. [Menjalankan Sistem](#3-menjalankan-sistem)
4. [Skenario Simulasi](#4-skenario-simulasi)
   - [Hari 1 — Setup & Familiarisasi](#hari-1--setup--familiarisasi)
   - [Hari 2-3 — Operasi Normal](#hari-2-3--operasi-normal)
   - [Hari 4-5 — Manajemen Stok & Restok](#hari-4-5--manajemen-stok--restok)
   - [Hari 6-7 — Akhir Pekan & Evaluasi](#hari-6-7--akhir-pekan--evaluasi)
5. [Perintah Cepat](#5-perintah-cepat)
6. [Apa yang Terjadi di Belakang](#6-apa-yang-terjadi-di-belakang)

---

## 1. Setup Awal

### Prasyarat

| Komponen | Keterangan |
|----------|------------|
| Python 3.14 + `uv` | Lihat `docs.astral.sh/uv` |
| Node.js 18+ | Termasuk `npm` |
| WhatsApp pribadi | Untuk scan QR dan jadi bot |
| WhatsApp kedua (opsional) | Untuk kirim perintah sebagai "owner" |
| Koneksi internet | whatsapp-web.js perlu koneksi ke WWeb |

### Install

```bash
cd /home/amri/Projects/prediksi_stok

# Python deps
uv sync

# Node deps (whatsapp-web.js)
cd whatsapp-bot && npm install && cd ..

# Seed data sintetis + train model
uv run python -c "
from app.seeder import seed_synthetic_data
from app.predictor import train_all_products
import os; os.makedirs('data/models', exist_ok=True)
seed_synthetic_data('data/prediksi.db', 'products.json', days=90)
train_all_products('data/prediksi.db', 'products.json')
print('Siap — 90 hari data sintetis + 7 model.')
"
```

### Konfigurasi (.env)

File `.env` sudah ada, pastikan isinya:

```env
FASTAPI_PORT=8765
DB_PATH=data/prediksi.db
PRODUCTS_FILE=products.json
DASHBOARD_PASSWORD=admin123
OWNER_NUMBER=+6281279454414
```

> **`OWNER_NUMBER`** adalah nomor WhatsApp yang akan menerima notifikasi otomatis
> (alert kehabisan pukul 08:00, reminder cek stok pukul 20:00).
>
> Format: kode negara tanpa `+` atau dengan `+` — whatsapp-web.js biasanya
> pakai format internasional dengan `+`.

---

## 2. Pairing WhatsApp

Proses pairing menghubungkan nomor WhatsApp Anda sebagai **bot** yang akan
membaca pesan masuk dan membalas otomatis.

### Jalankan Bot

```bash
cd /home/amri/Projects/prediksi_stok/whatsapp-bot
OWNER_NUMBER=+6281279454414 node index.js
```

Output pertama:
```
[2026-06-05T10:00:00] QR code saved to data/qr.png
[2026-06-05T10:00:00] Scan the QR code with WhatsApp to connect.
```

### Scan QR Code

**Opsi A — Buka Dashboard (mudah):**
1. Jalankan dashboard: `uv run streamlit run dashboard.py`
2. Buka `http://localhost:8501`, login `admin123`
3. Scroll ke **Status WhatsApp** — QR code muncul di situ
4. Buka WhatsApp → Ponsel: *Titik 3* → *Perangkat tertaut* → *Tautkan perangkat*
5. Scan QR code dari dashboard

**Opsi B — Buka file QR langsung:**
```bash
# Di terminal (linux dengan display)
xdg-open data/qr.png

# Atau via browser
file:///home/amri/Projects/prediksi_stok/data/qr.png
```

### Setelah Tersambung

```
[2026-06-05T10:01:00] WhatsApp connected!
[2026-06-05T10:01:00] Bot number: +628991140903
```

Status di dashboard berubah jadi **WhatsApp Terhubung** (hijau).

> **Catatan**: Sesi WhatsApp bertahan selama ~2-3 minggu. File session
> tersimpan di `data/wwebjs_profile/`. Restart bot akan pakai session lama
> tanpa scan ulang.

---

## 3. Menjalankan Sistem

### Arsitektur Sistem

```
                         ┌──────────────────┐
                         │   WhatsApp Anda   │
                         │   (kirim perintah)│
                         └────────┬─────────┘
                                  │ pesan WA
                                  ▼
┌──────────────────┐    POST /webhook    ┌──────────────────┐
│  whatsapp-bot/   │ ──────────────────► │  FastAPI Server  │
│  index.js        │                     │  port 8765       │
│  (Node)          │ ◄────────────────── │  (Python)        │
└──────────────────┘    GET /outgoing     └────────┬─────────┘
       │                                           │
       │ QR pairing                                │
       ▼                                           ▼
┌──────────────────┐                     ┌────────────────┐ ┌────────┐
│  WhatsApp Web    │                     │  SQLite        │ │Prophet │
│  (headless)      │                     │  prediksi.db   │ │models  │
└──────────────────┘                     └────────────────┘ └────────┘

┌──────────────────┐
│  Dashboard       │  http://localhost:8501 (password: admin123)
│  Streamlit       │
└──────────────────┘

┌──────────────────┐
│  Scheduler       │  08:00 → alert kehabisan
│  (otomatis)      │  20:00 → reminder + expected stock
│                  │  21:30 → eskalasi produk pending
│                  │  23:00 → backup + auto-confirm
└──────────────────┘
```

### Terminal

```bash
# Terminal 1 — FastAPI server
cd /home/amri/Projects/prediksi_stok
uv run uvicorn app.server:app --host 0.0.0.0 --port 8765 --reload

# Terminal 2 — WhatsApp bot
cd /home/amri/Projects/prediksi_stok/whatsapp-bot
OWNER_NUMBER=+6281279454414 node index.js

# Terminal 3 — Dashboard (opsional, untuk monitoring)
cd /home/amri/Projects/prediksi_stok
uv run streamlit run dashboard.py --server.port 8501
```

Atau pakai `setup.sh` yang menjalankan FastAPI + WhatsApp bot otomatis:

```bash
cd /home/amri/Projects/prediksi_stok
bash setup.sh
```

---

## 4. Skenario Simulasi

Asumsikan:
- **Nomor bot**: `+628991140903` (nomor yang di-scan)
- **Nomor owner**: `+6281279454414` (di `OWNER_NUMBER`)
- **Nomor operator**: nomor lain yang kirim perintah

Semua perintah dikirim sebagai **pesan WhatsApp biasa** ke nomor bot.

---

### Hari 1 — Setup & Familiarisasi

#### Pagi: Kirim beberapa penjualan

Dari nomor operator, kirim pesan ke nomor bot:

```
terjual gula 2
```

Bot balas:
```
OK. Gula +2 sak (total hari ini: 2)
```

> Kalau lupa format, kirim `help` atau `bantuan`:
> ```
> help
> ```
> Balas:
> ```
> Perintah yang tersedia:
> • terjual [produk] [jumlah] — Catat penjualan
>   Contoh: terjual gula 5
> • restock [produk] [jumlah] — Catat restok
> • cek stok — Lihat status stok
> • cek stok [produk] [jumlah] — Laporkan stok aktual
> • help/bantuan — Tampilkan pesan ini
> ```

#### Siang: Cek status stok

Kirim:
```
cek stok
```

Bot balas:
```
✓  Gula: 28 sak | habis: 2026-06-12 ↓ | BL/low
   Minyak: 985 dus | habis: 2026-06-19 → | BL/med
✓  Tepung: 300 dus | habis: >30 hari → | BL/med
✓  Beras: 2960 kg | habis: 2026-06-12 → | BL/med
✓  Aqua: 290 dus | habis: 2026-06-19 ↓ | BL/med
✓  Roti hitam manis: 35 dus | habis: >30 hari → | BL/med
✓  Garam: 495 pak | habis: 2026-06-12 ↑ | BL/med
```

#### Sore: Catat lebih banyak

```
terjual minyak 10, beras 30, garam 3
```

Balas:
```
OK. Minyak +10 dus (total hari ini: 10), Beras +30 kg (total hari ini: 30), Garam +3 pak (total hari ini: 3)
```

#### Malam: Konfirmasi stok akhir hari

Sekarang ada **3 cara** konfirmasi akhir hari:

**Opsi 1 — Auto-confirm semua dengan "ok" (paling mudah):**
Kirim:
```
ok
```

Bot balas:
```
✅ Stok hari ini dikonfirmasi:
✓ Gula: 28 sak
✓ Minyak: 975 dus
✓ Tepung: 300 dus
✓ Beras: 2930 kg
✓ Aqua: 300 dus
✓ Roti hitam manis: 35 dus
✓ Garam: 492 pak

Ada selisih? Kirim "cek stok [produk] [jumlah]" untuk koreksi.
```

> "ok" akan auto-confirm semua produk dengan nilai expected. Kalau ada selisih,
> tinggal kirim koreksi setelahnya, misal: `cek stok gula 25`

**Opsi 2 — Manual untuk produk tertentu:**
Kirim:
```
cek stok gula 28, minyak 975, tepung 300, beras 2930, aqua 300, roti hitam manis 35, garam 492
```

Bot balas:
```
Stok diperbarui. Gula: 28 sak (sesuai); Minyak: 975 dus (sesuai); Tepung: 300 dus (sesuai); Beras: 2930 kg (sesuai); Aqua: 300 dus (sesuai); Roti hitam manis: 35 dus (sesuai); Garam: 492 pak (sesuai)
```

**Opsi 3 — Auto-confirm otomatis jam 23:00 (jika lupa):**
Kalau owner tidak kirim apapun, sistem akan auto-confirm jam 23:00.

> Setiap konfirmasi memicu **retraining model Prophet hanya untuk produk yang
> dikonfirmasi** — lebih cepat dari sebelumnya yang retrain semua 7 produk.

#### Notifikasi malam (otomatis)

Jika scheduler berjalan, pukul **20:00** bot akan kirim reminder lengkap dengan
expected stock:

```
🔔 Waktunya cek stok!

Expected stok hari ini:
  Gula: 28 sak
  Minyak: 975 dus
  Tepung: 300 dus
  Beras: 2930 kg
  Aqua: 300 dus
  Roti hitam manis: 35 dus
  Garam: 492 pak

Balas: "ok" jika semua sesuai
Atau: gula 28, minyak 975, ...
```

Pukul **21:30** jika ada yang belum dikonfirmasi:
```
⚠️ Stok BELUM dikonfirmasi untuk: Tepung, Beras, Aqua, ...
Kirim "ok" jika semua sesuai.
```

Pesan ini masuk ke **nomor owner** (`OWNER_NUMBER`).

#### Flowchart Konfirmasi Akhir Hari

```
                        20:00
                          │
                          ▼
              ┌───────────────────────┐
              │  Reminder dgn         │
              │  expected stock       │
              └──────────┬────────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
          Owner balas            Owner
          "ok"                 diam / lupa
              │                     │
              ▼                     ▼
    ┌─────────────────┐   21:30    ┌─────────────────┐
    │ Auto-confirm    ├───────►    │ Eskalasi:       │
    │ semua produk    │            │ produk yg blm   │
    │ dgn expected    │            │ dikonfirmasi    │
    └─────────────────┘            └────────┬────────┘
                                            │
                                 ┌──────────┴──────────┐
                                 │                     │
                             Owner balas           Owner
                             "ok" / manual       diam / lupa
                                 │                     │
                                 ▼                     ▼
                       ┌─────────────────┐   23:00    ┌─────────────────┐
                       │ Konfirmasi      ├───────────►│ Auto-confirm    │
                       │ manual/partial  │            │ semua sisa      │
                       └────────┬────────┘            │ dgn expected    │
                                │                     └────────┬────────┘
                                ▼                              ▼
                       ┌─────────────────────────────────────────┐
                       │  Record confirmation + retrain model    │
                       │  hanya untuk produk yg dikonfirmasi     │
                       └─────────────────────────────────────────┘
```

---

### Hari 2-3 — Operasi Normal

#### Kirim penjualan sepanjang hari

```
terjual gula 1, tepung 3
terjual beras 25
terjual minyak 8, aqua 5
```

#### Coba fitur auto-correct — spasi terlekat

Kirim:
```
terjual gula3 minyak5
```

Bot tetap paham:
```
OK. Gula +3 sak (total hari ini: 3), Minyak +5 dus (total hari ini: 5)
```

#### Coba error handling — produk tidak dikenal

Kirim:
```
terjual indomie 10
```

Balas:
```
Unknown product "indomie". Available products: aqua, beras, garam, gula, minyak, roti hitam manis, tepung
```

#### Coba batas mencurigakan — quantity >10x estimasi

Kirim:
```
terjual gula 100
```

Bot akan tetap mencatat tapi flag untuk konfirmasi (response tetap sukses).
Estimasi harian gula = 30/7 ≈ 4.3 sak, jadi 100 > 43 → kena threshold.

#### Konfirmasi akhir hari (dengan deteksi penyusutan)

Kirim data yang sengaja kurang:
```
cek stok gula 25, minyak 970, tepung 295, beras 2900
```

Balas (contoh jika ada susut):
```
Stok diperbarui. Gula: 25 sak (susut 2 sak, 7%); Minyak: 970 dus (sesuai); Tepung: 295 dus (sesuai); Beras: 2900 kg (sesuai)
```

---

### Hari 4-5 — Manajemen Stok & Restok

#### Cek prediksi — lihat produk yang hampir habis

Kirim:
```
cek stok
```

Perhatikan kolom `habis:` — jika ada produk dengan estimasi habis ≤ 3 hari,
status dashboard akan merah **Urgent**.

#### Restok produk

Kirim:
```
restock aqua 200
```

Balas:
```
OK. Aqua di-restok 200 dus. Stok sekarang: 490 dus.
```

#### Notifikasi pagi otomatis (08:00)

Jika ada produk yang depletion ≤ lead time supplier, pukul **08:00** bot kirim:
```
⚠️ PERINGATAN: Beras diperkirakan habis dalam 2 hari (lead time 2 hari). Segera lakukan pemesanan!
```

#### Konfirmasi dengan skenario restok tak tercatat

Misalnya Anda restok fisik tanpa kirim `restock` — lalu konfirmasi malam:
```
cek stok aqua 500
```

Bot akan deteksi:
```
Stok diperbarui. Aqua: 500 dus (restok 10 dus)
```

---

### Hari 6-7 — Akhir Pekan & Evaluasi

#### Buka Dashboard untuk analisis

Di browser: `http://localhost:8501` (password: `admin123`)

Yang bisa dilihat:
1. **Tabel stok** — status real-time semua produk dengan warna (hijau/kuning/merah)
2. **Grafik penjualan 30 hari** — pilih produk dari dropdown
3. **Grafik prediksi** — garis turun menunjukkan perkiraan sisa stok 30 hari ke depan
4. **Regenerate model** — otomatis setiap kali buka dashboard jika ada model kurang

#### Tambah produk baru via dashboard

1. Buka dashboard → scroll ke **Tambah Produk Baru**
2. Isi: Nama="Telur", Stok Awal=200, Satuan="kg", Waktu Habis=7, Simpan=14, Lead Time=3
3. Klik **Tambah**
4. Sistem otomatis: generate data sintetis 90 hari + train model baru

#### Konfirmasi via WhatsApp untuk produk baru

```
terjual telur 5
cek stok telur 195
```

---

## 5. Perintah Cepat

Kirim ke nomor bot WhatsApp:

| Perintah | Fungsi |
|----------|--------|
| `terjual gula 5` | Catat penjualan 5 sak gula |
| `terjual gula 2, minyak 10` | Catat multi produk |
| `terjual gula3 minyak5` | Auto-correct spasi |
| `cek stok` | Status semua produk + prediksi |
| `ok` / `oke` | Auto-confirm semua produk dgn expected stock |
| `cek stok gula 25` | Konfirmasi stok gula = 25 |
| `cek stok gula 25, minyak 900` | Konfirmasi multi produk |
| `restock aqua 200` | Tambah stok aqua 200 dus |
| `help` / `bantuan` | Tampilkan perintah |

---

## 6. Apa yang Terjadi di Belakang

```
Anda ──[WhatsApp]──→ Bot (whatsapp-web.js)
                        │
                        ▼
                  POST /webhook
                        │
                        ├── parser.py    — parse "terjual gula 5"
                        ├── data.py      — simpan ke SQLite
                        ├── predictor.py — hitung prediksi (jika perlu)
                        ├── reconciliation.py — bandingkan expected vs actual
                        └── response balik ──→ Bot ──→ WhatsApp Anda
```

**Pesan keluar** (notifikasi, reminder):

```
Scheduler ──→ queue_outgoing_message() ──→ SQLite outgoing_messages
                                                  │
                                          Bot polling GET /outgoing
                                                  │
                                              Kirim WhatsApp
```

**Jadwal Scheduler Otomatis:**

| Waktu | Aksi |
|-------|------|
| 08:00 | Cek semua produk → alert kehabisan |
| 20:00 | Kirim reminder + expected stock per produk |
| 21:30 | Eskalasi untuk produk yang belum dikonfirmasi |
| 23:00 | Backup database + auto-confirm stok + retrain model |

**Setelah konfirmasi (manual atau auto):**
- Rekonsiliasi: bandingkan expected vs actual → deteksi susut/restok
- Retrain Prophet: hanya untuk produk yang dikonfirmasi, bukan semua 7

**Pairing ulang** jika sesi expired:

Dashboard → tombol **Pasang Ulang** → POST `/restart-bot` → bot restart → QR baru

---

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| QR tidak muncul | Hapus `data/wwebjs_profile/` lalu restart bot |
| Bot tidak balas | Cek: FastAPI running? `curl localhost:8765/health` |
| "Server returned 404" | Webhook URL di `index.js` — pastikan `FASTAPI_PORT` cocok |
| "Session expired" | Dashboard → Pasang Ulang (atau hapus `wwebjs_profile/` + restart) |
| QR di dashboard tidak muncul | Refresh halaman, tunggu 5-10 detik |
| Bot spam restart | Cek `connection_status.json` — hapus file jika corrupt |
| Nomor tidak terdaftar WA | whatsapp-web.js cuma jalan di nomor WhatsApp yang valid |
| Pesan owner tidak kebaca | Bot cuma baca pesan yang dikirim KE nomor bot, bukan dari bot |

---

## Quick Start (Ringkasan)

```bash
# 1 terminal: FastAPI
cd /home/amri/Projects/prediksi_stok
uv run uvicorn app.server:app --host 0.0.0.0 --port 8765

# 2 terminal: WhatsApp bot
cd /home/amri/Projects/prediksi_stok/whatsapp-bot
OWNER_NUMBER=+6281279454414 node index.js

# 3 terminal: Dashboard
cd /home/amri/Projects/prediksi_stok
uv run streamlit run dashboard.py

# Scan QR dari dashboard (http://localhost:8501)
# Kirim pesan ke nomor bot dari WhatsApp Anda
```

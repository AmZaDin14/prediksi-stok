# PRD: Prediksi Stok — Sistem Prediksi Stok Berbasis AI

## Pernyataan Masalah

Pemilik toko kecil mencatat stok secara manual di kertas. Barang dengan masa kadaluarsa pendek menyebabkan kerugian jika stok berlebih (barang kadaluarsa sebelum terjual), sedangkan stok kurang menyebabkan kehilangan penjualan. Pemilik hanya memiliki perkiraan kasar berdasarkan pengalaman (misalnya "30 sak Gula habis sekitar 7 hari"), tapi tidak ada cara sistematis untuk memprediksi kapan harus memesan ulang atau mendeteksi penyusutan stok. Tidak ada data penjualan historis digital — hanya catatan kertas.

## Solusi

Sistem yang dijalankan secara lokal dengan dua antarmuka:

1. **Bot WhatsApp** — pemilik mengirim laporan penjualan real-time ke bot (contoh: "terjual gula 5"). Di akhir hari, bot meminta konfirmasi stok; pemilik mengecek rak dan melaporkan stok aktual. Sistem merekonsiliasi stok yang diharapkan vs aktual untuk mendeteksi selisih. Bot secara proaktif mengirim peringatan kehabisan stok dan pengingat akhir hari.

2. **Dashboard web** — halaman tunggal Streamlit dengan autentikasi password sederhana. Menampilkan gambaran stok, prediksi depletion, indikator kepercayaan, formulir manajemen produk, dan status koneksi WhatsApp dengan QR pairing ulang.

Sistem menghasilkan data sintetis dari perkiraan pemilik untuk menumbuhkan model Prophet saat peluncuran, sehingga prediksi tersedia segera. Seiring data penjualan nyata terkumpul, data sintetis dihapus bertahap melalui jendela geser 90 hari.

## Cerita Pengguna

1. Sebagai pemilik toko, saya ingin mengirim laporan penjualan via WhatsApp ("terjual gula 5, minyak 20"), sehingga sistem mencatat apa yang saya jual secara real-time.
2. Sebagai pemilik toko, saya ingin mengirim laporan penjualan kapan saja sepanjang hari saat transaksi terjadi, sehingga sistem mengakumulasi total harian yang akurat.
3. Sebagai pemilik toko, saya ingin bot mengingatkan saya di akhir hari untuk konfirmasi stok rak ("cek stok"), sehingga saya merekonsiliasi stok fisik dengan stok yang diharapkan.
4. Sebagai pemilik toko, saya ingin sistem mendeteksi selisih antara stok yang diharapkan dan stok aktual di rak, sehingga saya mendapat peringatan potensi pencurian, kerusakan, atau kesalahan pencatatan.
5. Sebagai pemilik toko, saya ingin sistem menangani stok masuk secara otomatis (ketika saya melaporkan stok lebih tinggi dari yang diharapkan saat konfirmasi), sehingga saya tidak perlu perintah "restok" terpisah.
6. Sebagai pemilik toko, saya ingin mengecek prediksi kapan saja dengan mengirim "cek stok" via WhatsApp, sehingga saya bisa melihat tanggal kehabisan dan rekomendasi pemesanan ulang sesuai permintaan.
7. Sebagai pemilik toko, saya ingin bot mengirim peringatan kehabisan stok secara proaktif ketika Tanggal Kehabisan suatu Produk berada dalam ambang batas yang dapat dikonfigurasi (default: Waktu Tunggu Pemasok + 2 hari), sehingga saya tahu kapan harus memesan ulang tanpa pemantauan terus-menerus.
8. Sebagai pemilik toko, saya ingin bot mengirim pengingat akhir harian setiap hari, sehingga saya tidak lupa konfirmasi stok rak.
9. Sebagai pemilik toko, saya ingin dashboard web menampilkan semua Produk dengan stok saat ini, prediksi kehabisan, arah tren, dan indikator kepercayaan, sehingga saya mendapat gambaran visual sekilas.
10. Sebagai pemilik toko, saya ingin dashboard web menampilkan indikator kepercayaan ketika stok belum dikonfirmasi (kuning) atau ketika data penjualan sudah basi (merah), sehingga saya tahu seberapa andal prediksi tersebut.
11. Sebagai pemilik toko, saya ingin menambah Produk baru melalui formulir dashboard, sehingga saya bisa mulai melacak barang baru tanpa mengedit file konfigurasi.
12. Sebagai pemilik toko, saya ingin mengedit atau menghapus Produk yang ada melalui formulir dashboard, sehingga katalog produk saya tetap terkini.
13. Sebagai pemilik toko, saya ingin dashboard menampilkan status koneksi WhatsApp dan menyediakan kode QR untuk pairing ulang jika terputus, sehingga saya bisa memperbaiki masalah koneksi dari dashboard.
14. Sebagai pemilik toko, saya ingin prediksi tersedia sejak hari pertama, meskipun saya tidak memiliki data digital historis, sehingga saya tidak perlu menunggu berminggu-minggu agar sistem berguna.
15. Sebagai pemilik toko, saya ingin sistem menangani kesalahan ketik di pesan WhatsApp (huruf kapital, spasi berlebih) secara otomatis, sehingga saya tidak frustrasi dengan format yang ketat.
16. Sebagai pemilik toko, saya ingin sistem menolak input yang jelas-jelas tidak valid (jumlah negatif, nilai hilang) dengan pesan kesalahan yang jelas, sehingga saya tahu apa yang salah.
17. Sebagai pemilik toko, saya ingin diminta konfirmasi jika saya memasukkan jumlah yang tidak masuk akal, sehingga kesalahan pengetikan terdeteksi.
18. Sebagai pemilik toko, saya ingin prediksi tetap berjalan meskipun saya melewatkan satu hari pelaporan, dengan dashboard menampilkan indikator kepercayaan alih-alih menjadi tidak andal secara diam-diam.
19. Sebagai pemilik toko, saya ingin sistem bertahan dari restart mesin atau mati listrik, dengan semua data tersimpan di SQLite dan pemulihan otomatis saat startup.
20. Sebagai pemilik toko, saya ingin bot WhatsApp otomatis terhubung kembali jika sesi terputus, sehingga saya tidak perlu memulai ulang sistem secara manual.
21. Sebagai pemilik toko, saya ingin pengaturan satu-perintah yang menghasilkan data awal, memulai semua layanan, dan menampilkan kode QR untuk pairing WhatsApp, sehingga saya bisa memulai dengan usaha minimal.
22. Sebagai pemilik toko, saya ingin sistem menyimpan cadangan SQLite harian (7 salinan bergilir), sehingga data historis tidak hilang jika database korup.

## Keputusan Implementasi

### Modul

**1. Katalog Produk** (`products.json` + CRUD dashboard)
- Atribut statis per Produk: nama, stok awal, satuan, estimasi waktu habis (hari), masa simpan (hari), waktu tunggu pemasok (hari)
- Diisi dari `products.json` saat pertama kali dijalankan
- Dikelola melalui formulir dashboard Streamlit (tambah, edit, hapus)
- Daftar Produk digunakan oleh semua modul lain sebagai sumber kebenaran untuk nama Produk yang valid

**2. Data Penjualan** (SQLite — `data/prediksi.db`)
- Menyimpan Laporan Penjualan individual dengan timestamp, Produk, jumlah
- Mengakumulasi total harian per Produk untuk input prediksi
- Stok yang diharapkan berjalan = stok terakhir dikonfirmasi - total penjualan kumulatif
- Skema: `sales_reports(id INTEGER PK, product_name TEXT NOT NULL, quantity REAL NOT NULL, reported_at TEXT NOT NULL)`, `stock_snapshots(id INTEGER PK, product_name TEXT NOT NULL, quantity REAL NOT NULL, snapshot_date TEXT NOT NULL, is_confirmation INTEGER NOT NULL DEFAULT 0)`

**3. Rekonsiliasi Stok**
- Dipicu oleh Konfirmasi Akhir Hari
- Membandingkan stok yang diharapkan vs stok aktual yang dilaporkan
- Menandai selisih di atas ambang batas (default 10% atau 1 satuan, mana yang lebih besar)
- Memperbarui stok dasar baru untuk setiap Produk
- Tidak memperlakukan selisih sebagai konsumsi untuk perhitungan kecepatan

**4. Generator Data Sintetis**
- Dipanggil saat pertama kali dijalankan (dan ketika katalog produk berubah)
- Menghasilkan 90 hari penjualan harian per Produk pada rata-rata estimasi pemilik
- Menyuntikkan derau Gaussian + variasi hari-dalam-minggu di sekitar rata-rata
- Format output cocok dengan skema Laporan Penjualan nyata sehingga keduanya bisa digabung

**5. Mesin Prediksi** (Prophet)
- Peramalan penjualan harian dengan musiman hari-dalam-minggu
- Tiga fase: bootstrap (sintetis saja), campuran (sintetis+nyata, jendela geser 90 hari), matang (nyata saja setelah ≥60 hari nyata)
- Cakrawala prediksi tetap 30 hari untuk semua Produk
- Tanggal Kehabisan diturunkan dari ramalan kumulatif melintasi stok saat ini
- Melatih ulang setelah setiap Konfirmasi Akhir Hari
- Cadangan ke proyeksi linear (stok / estimasi waktu habis) jika Prophet gagal konvergen
- Siklus pelatihan berikutnya mencoba Prophet lagi; promosi otomatis kembali jika berhasil
- Dashboard menampilkan fase dan status cadangan per Produk

**6. Pengurai Input** (penguraian pesan WhatsApp)
- Format ketat dengan koreksi otomatis: huruf kecil, hapus spasi berlebih
- Menangani: `terjual gula 5, minyak 20`, `terjual gula5` (spasi hilang → diperbaiki), `Terjual Gula 5` (huruf kapital → diperbaiki)
- Menolak: nama produk tidak dikenal (mengembalikan daftar produk tersedia), jumlah negatif, jumlah hilang
- Meminta konfirmasi pada jumlah tidak masuk akal (>10x penjualan harian tipikal)
- Menerima nol sebagai valid

**7. Bot WhatsApp** (Node.js — `whatsapp-web.js`)
- Mikrolayanan tipis: menerima pesan → POST ke webhook FastAPI; menerima permintaan kirim dari Python → mengirim via WhatsApp
- Koneksi ulang otomatis dengan jendela percobaan 5 menit
- Pada kegagalan persisten: mengekspos endpoint pairing ulang QR yang dikonsumsi dashboard
- Satu pemilik, satu nomor telepon

**8. Layanan FastAPI** (Python)
- Server HTTP tunggal yang menjadi host endpoint prediksi/penjualan dan webhook dari WhatsApp
- APScheduler: pengingat akhir hari, pemeriksaan ambang kehabisan, cadangan SQLite harian, pelatihan ulang setelah konfirmasi
- Semua logika bisnis terkoordinasi di sini

**9. Dashboard** (Streamlit, halaman tunggal, autentikasi password)
- Tabel gambaran: semua Produk dengan stok, prediksi kehabisan, tren, indikator kepercayaan
- Formulir manajemen produk (tambah/edit/hapus)
- Indikator status koneksi WhatsApp + QR pairing ulang
- Membaca/menulis database SQLite bersama

### Arsitektur Runtime

- Mikrolayanan Node ↔ Python FastAPI melalui HTTP di `localhost` (dua arah: Node POST pesan masuk ke FastAPI; FastAPI memanggil endpoint Node untuk memicu pengiriman pesan keluar)
- APScheduler dalam proses FastAPI menangani semua pekerjaan terjadwal
- Dashboard dan FastAPI berbagi database SQLite yang sama (dashboard baca-tulis untuk katalog produk, baca-saja untuk data penjualan/prediksi)
- Pengaturan satu-perintah: menghasilkan data sintetis → melatih model awal → memulai FastAPI → memulai Node → mencetak QR WhatsApp

### Aturan Validasi Input

| Input | Tindakan |
|---|---|
| Jumlah negatif | Tolak dengan error |
| Jumlah nol | Terima (valid — tidak ada penjualan) |
| Jumlah tidak masuk akal (>10x rata-rata harian) | Minta konfirmasi ("y" untuk terima) |
| Nama produk tidak dikenal | Tolak, daftar Produk tersedia |
| Jumlah hilang | Tolak dengan pengingat format |
| Spasi berlebih / huruf kapital salah | Koreksi otomatis secara diam-diam |

### Fase Prediksi

| Fase | Kondisi | Sumber Data | Jendela |
|---|---|---|---|
| Bootstrap | Peluncuran | Sintetis saja | N/A |
| Campuran | 1-59 hari nyata | Sintetis + nyata digabung | Geser 90 hari |
| Matang | ≥60 hari nyata | Nyata saja | Geser 90 hari |

## Keputusan Pengujian

- **Uji perilaku eksternal, bukan detail implementasi.** Pengujian "dengan Laporan Penjualan ini, stok yang diharapkan sama dengan X" itu baik. Pengujian "Mesin Prediksi memanggil Prophet.train() dengan parameter persis ini" tidak baik.
- **Mesin Prediksi** — uji: pemicu cadangan saat Prophet error, tanggal kehabisan bergerak benar saat stok berubah, transisi fase bekerja, prediksi campuran dengan data sintetis+nyata yang diketahui memberikan hasil yang diharapkan, cakrawala 30 hari benar menampilkan ">30 hari" saat stok melebihi ramalan. Gunakan injeksi dependensi untuk melewatkan tiruan atau pembungkus di sekitar Prophet sehingga pengujian tidak memerlukan kompiler C Prophet yang sebenarnya.
- **Pengurai Input** — uji: semua aturan koreksi (huruf kapital, spasi), semua kasus penolakan (negatif, hilang, tidak dikenal), permintaan konfirmasi untuk nilai tidak masuk akal. Pengurai adalah fungsi murni string → data terstruktur, jadi cepat dan deterministik.
- **Data Penjualan** — uji: pengambilan catatan berdasarkan rentang tanggal, kebenaran agregasi harian, perhitungan stok yang diharapkan dengan urutan penjualan yang diketahui. Gunakan SQLite dalam memori untuk isolasi pengujian.
- **Rekonsiliasi Stok** — uji: kecocokan tepat tidak menghasilkan peringatan, selisih kecil di bawah ambang tidak menghasilkan peringatan, selisih besar di atas ambang menandai dengan benar, stok masuk (aktual > diharapkan) memperbarui dasar tanpa peringatan.
- **Generator Data Sintetis** — uji: keluaran memiliki jumlah hari yang benar untuk setiap Produk, nilai harian non-negatif, rata-rata mingguan cocok dengan estimasi pemilik dalam batas statistik, pola hari-dalam-minggu ada.
- **Bot WhatsApp** — tidak diuji secara unit (padat I/O). Diuji melalui integrasi dengan endpoint webhook FastAPI.
- **Dashboard** — tidak diuji secara unit (padat UI).

## Di Luar Lingkup

- Penyebaran multi-toko atau multi-pengguna
- Aplikasi seluler (asli atau lainnya) — WhatsApp adalah antarmuka seluler
- Impor data otomatis dari sistem POS atau catatan digital yang ada
- Pelacakan stok real-time melalui IoT/pemindaian barcode
- Perhitungan keuangan (margin keuntungan, harga pokok penjualan, ROI)
- Manajemen pemasok atau pembuatan pesanan pembelian
- Model ML kompleks di luar Prophet (LSTM, ARIMA, dll.) — ditunda sampai data nyata yang cukup ada
- Mata uang ganda atau konversi satuan
- Bot SMS atau Telegram (WhatsApp saja)
- Hosting cloud atau akses jarak jauh — penyebaran lokal saja

## Catatan Lain

- Semua tingkat konsumsi dimulai sebagai perkiraan pemilik. Sistem jujur tentang ini: prediksi dari data sintetis tidak disajikan sebagai "telah dilatih pada data nyata." Dashboard menunjukkan fase setiap Produk.
- "Tanggal Kehabisan" adalah konsep inti yang akan berinteraksi dengan pengguna. Semua UI dan peringatan berpusat di sekitar angka tunggal ini.
- Sistem harus dengan anggun menangani skenario di mana pemilik berhenti menggunakannya sepenuhnya selama berminggu-minggu — prediksi berlanjut dari titik data terakhir yang baik dengan indikator kepercayaan merah, dan pengingat akhir hari tetap terkirim setiap hari.
- Jika katalog produk diedit (tambah/hapus produk), data sintetis dihasilkan ulang hanya untuk produk baru. Produk yang ada mempertahankan data nyata mereka.

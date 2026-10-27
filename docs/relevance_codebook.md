# Codebook Anotasi dan Skema Relevansi ANMEDSOS

**Judul Penelitian:**  
*Keresahan Ketenagakerjaan dan Aspirasi Bekerja ke Luar Negeri di Era #KaburAjaDulu: Analisis Topik dan Sentimen Wacana Publik di Platform X*

---

## 1. Definisi dan Batasan Relevansi

### 1.1 Kriteria Inklusi Utama (`include`)
Sebuah postingan diklasifikasikan sebagai **relevan (`include`)** apabila memuat salah satu atau kombinasi dari dimensi berikut:
1. **Isu Ketenagakerjaan Domestik (RQ1):**
   - Kesulitan memperoleh pekerjaan (pengangguran, *underemployment*, *fresh graduate*, batasan usia/pengalaman).
   - Prekaritas kerja dan kompensasi (upah rendah, UMR/UMK, pemotongan gaji, lembur tidak dibayar, penahanan ijazah).
   - Pemutusan Hubungan Kerja (PHK) dan kerentanan status kerja (kontrak/outsourcing).
   - Keluhan ekonomi struktural terkait pasar kerja Indonesia.
2. **Aspirasi Bekerja ke Luar Negeri (RQ2 Personal):**
   - Pernyataan niat, rencana, keinginan, atau motivasi pribadi untuk bermigrasi atau bekerja di luar negeri (misal: penggunaan tagar `#KaburAjaDulu` dalam konteks pribadi, persiapan program magang/visa kerja Jepang, Korea, Singapura, Australia/WHV).
3. **Wacana Publik Ketenagakerjaan Global (RQ2 Publik):**
   - Diskusi publik, berita, pengalaman, saran/tips, atau perbandingan gaji/biaya hidup mengenai peluang kerja luar negeri yang relevan bagi audiens Indonesia.
4. **Kaitan Eksplisit Isu Domestik dan Solusi Luar Negeri (RQ2 Link):**
   - Narasi kausal yang secara gamblang menghubungkan keputusasaan pasar kerja domestik dengan keputusan/keinginan bekerja ke luar negeri.
   - *Catatan Metodologis:* Label ini dipetakan secara ketat ke **RQ2** (bukan RQ3; RQ3 adalah analisis sentimen yang belum dijalankan). Hanya 6 postingan terklasifikasi sebagai *explicit issue–abroad link* dalam satu tweet tunggal, dan klasifikasi ini masih bersifat **provisional / eksploratori**. Hubungan push-factor yang lebih luas akan diteliti pada tahap pemodelan topik silang.

---

### 1.2 Kriteria Eksklusi Utama (`exclude`)
Postingan wajib **dieksklusikan (`exclude`)** apabila topiknya didominasi oleh:
1. **Rekrutmen Olahraga & Atlet:** Pembelian/transfer pemain sepak bola, pelatih timnas, atau liga olahraga.
2. **Casting & Hiburan:** Audisi casting film, k-pop idol, fan merchandise, atau jual-beli tiket konser.
3. **Spam & Iklan Komersial:** Siaran lowongan kerja otomatis/komersial (*job board link dumps*), promo judi/slot, giveaway pulsa/saldo e-wallet, atau jasa berbayar (review CV, optimasi LinkedIn komersial).
4. **Tugas Akademik & Domestik:** Tugas sekolah/kuliah (PR, skripsi, kerja kelompok kampus) atau pekerjaan rumah tangga/domestik non-pasar kerja.
5. **Berita Regional Luar Negeri Murni:** Berita ketenagakerjaan negara asing tanpa sangkut paut dengan tenaga kerja asal Indonesia.
6. **Gossip / Insidental Drama:** Cerita perselingkuhan, pertengkaran pribadi di media sosial, atau kecelakaan lalu lintas insidental yang sekadar menyebut kata kerja/kantor.
7. **Sebutan Insidental:** Kata kunci muncul tanpa substansi ketenagakerjaan atau aspirasi migrasi.

---

### 1.3 Kasus Ambigu / Perlu Konteks (`review`)
Postingan dikelompokkan ke dalam antrean tinjauan manual (`review`) jika:
1. Terpotong secara fatal sehingga makna utamanya hilang.
2. Mengandung ungkapan sarkasme atau *code-mixing* ekstrem yang membuat intensi tidak dapat ditentukan secara deterministik.
3. Kehilangan referen percakapan (misal balasan singkat *"bener banget ini"* terhadap cuitan orang lain yang tidak terbaca).

---

## 2. Skema Multi-Label RQ

| Label | Nilai | RQ Target | Makna & Syarat Bukti |
|:---|:---:|:---:|:---|
| `employment_issue` | 0 / 1 / null | **RQ1** | **1** jika memuat keluhan/permasalahan ketenagakerjaan Indonesia. Bukti dicatat dalam `rq_evidence`. |
| `abroad_aspiration` | 0 / 1 / null | **RQ2** | **1** jika memuat niat atau keinginan **pribadi** untuk bekerja di luar negeri. |
| `abroad_discourse` | 0 / 1 / null | **RQ2** | **1** jika memuat wacana umum, saran, berita, atau perdebatan publik tentang kerja luar negeri. |
| `issue_abroad_link` | 0 / 1 / null | **RQ2** | **1** jika menghubungkan kesulitan kerja lokal dengan dorongan bekerja ke luar negeri. Memerlukan bukti gabungan isu domestik dan luar negeri. (6 tweet, provisional). |

---

## 3. Protokol Perlindungan Ground Truth
1. Label manusia historis (64 `confirmed_relevant` dan 31 `confirmed_excluded` pada `data/interim/manual_labels.csv`) bersifat **otoritatif** dan tidak boleh diubah oleh model.
2. Postingan yang dimasukkan ke korpus akhir melalui model klasifikasi ditandai sebagai `selection_source = "model_include"` dan `final_selection_status = "provisional_model_included"`.

---

## 4. Deskripsi Model Klasifikasi Relevansi
- **Pengenal Model:** `anmedsos-rule-hybrid-v1`
- **Arsitektur Aktual:** Pengklasifikasi lokal berbasis *expert deterministic rules*, leksikon domain, dan pola diskursus (*lexical-discourse classifier*).
- **Keterbukaan Akademik:** Model ini beroperasi 100% lokal di mesin peneliti tanpa memanggil API LLM berbayar eksternal (OpenAI/Anthropic/Gemini) dan tanpa model inferensi *neural embeddings*. Hal ini memastikan reproduktifitas penuh tanpa biaya API dan tanpa latensi jaringan.

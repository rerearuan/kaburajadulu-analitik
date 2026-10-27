# Laporan Rekonsiliasi & Audit Final ANMEDSOS untuk Submission TK-2

**Mata Kuliah:** Analitika Media Sosial (Semester Gasal 2026/2027)  
**Judul Riset:** *Keresahan Ketenagakerjaan dan Aspirasi Bekerja ke Luar Negeri di Era #KaburAjaDulu: Analisis Topik dan Sentimen Wacana Publik di Platform X*  
**Tanggal Audit:** 27 Oktober 2026  
**Status Verifikasi Repositori:** **`PASS` (36/36 Automated Unit & Integration Tests Passing)**

---

## 1. Matriks Pemeriksaan Faktual (Audit Checklist)

| No | Parameter Audit | Hasil Faktual | Status Evaluasi |
|:---:|:---|:---|:---:|
| 1 | **Rekonsiliasi Baris 1.516 vs. 1.492** | Selisih bersih 24 tweet ($1.516 - 25 \text{ eksklusi} + 1 \text{ inklusi} = 1.492$) terevaluasi row-level | **`PASS`** |
| 2 | **Integritas & Immutabilitas `text_raw`** | 100% karakter dan byte identik persis dengan sumber `data/raw/raw_tweets.jsonl` (0 mismatch) | **`PASS`** |
| 3 | **Uniknya Identifikator (`post_id`)** | 0 duplikasi ID di seluruh file interim maupun processed (`rows == unique_pids`) | **`PASS`** |
| 4 | **Deskripsi Model Klasifikasi** | `anmedsos-rule-hybrid-v1` dinyatakan jujur sebagai *local rule & lexical-discourse classifier* | **`PASS`** |
| 5 | **Pemetaan RQ2 vs. RQ3** | `issue_abroad_link` dipetakan ke **RQ2**; RQ3 sentimen dinyatakan **BELUM DIEKSEKUSI** | **`PASS`** |
| 6 | **Catatan Link Kausal Eksplisit** | 6 tweet teridentifikasi sebagai *explicit link* diakui berstatus **provisional / exploratory** | **`PASS`** |
| 7 | **Cakupan Tanggal Nyata** | *Observed coverage* 1 Jan – 7 Okt 2026 (WIB); jeda 8–25 Okt 2026 terdokumentasi jujur | **`PASS`** |
| 8 | **Evaluasi Kualitas & Ground Truth** | Metrik P/R/F1 berasal dari 95 audit historis; 150 sampel evaluasi independen berstatus audit | **`NEEDS VALIDATION`** |
| 9 | **Test Suite Otomatis** | 36 unit/regression/integration tests lulus tanpa kegagalan | **`PASS`** |
| 10 | **Kesiapan Repositori & Freeze** | Berkas kredensial `.env` terabaikan aman oleh `.gitignore`, repositori siap di-commit | **`PASS`** |

---

## 2. Rekonsiliasi Row-Level: Mengapa Model Include 1.516 Menjadi 1.492 Final Corpus?

Terdapat selisih **24 postingan** antara hasil prediksi inklusi model (*1.516 posts*) dan korpus final yang dibekukan (*1.492 posts*). Penjelasannya adalah sebagai berikut:

$$\text{Final Corpus} = 1.516 (\text{Model Include}) - 25 (\text{Manual Exclude Overruled}) + 1 (\text{Manual Include Recovered}) = \mathbf{1.492 \text{ posts}}$$

### A. 25 Postingan yang Dikeluarkan dari Final Corpus (Model: `include`, Manual: `exclude`)
Meskipun model aturan mengidentifikasi kata kunci ketenagakerjaan, postingan ini memiliki keputusan audit manusia `manual_decision = exclude` pada [`data/interim/manual_labels.csv`](file:///Users/reginaaruan/Documents/ANMEDSOS/data/interim/manual_labels.csv). Sesuai protokol penelitian, **keputusan eksklusi manusia tidak boleh dilanggar oleh model otomatis**:

| No | `post_id` | Status Heuristik Lama | Alasan Model | Alasan Riil Eksklusi Manusia |
|:---:|:---|:---|:---|:---|
| 1 | `2006669160777212197` | `confirmed_excluded` | `employment_concern` | Bahasa Melayu regional Malaysia (`gaji rendah tapi overpaid with skill`) |
| 2 | `2006924229380555157` | `confirmed_excluded` | `abroad_discourse` | Siaran info loker / pelatihan Pemprov KTP Jabar (bukan keresahan warga) |
| 3 | `2007692356238356962` | `confirmed_excluded` | `abroad_discourse` | Sindiran politik sarkasme ke anggota DPR RI |
| 4 | `2008389628043399461` | `confirmed_excluded` | `abroad_aspiration` | Berita kecelakaan lalu lintas penunggang motor di Singapura |
| 5 | `2008406226179334592` | `confirmed_excluded` | `abroad_aspiration` | Balasan singkat POV akun tanpa konteks substansial |
| 6 | `2008860534444331502` | `confirmed_excluded` | `employment_concern` | Pertengkaran warganet tentang posting wajah di X |
| 7 | `2011092036854952372` | `confirmed_excluded` | `employment_concern` | Komentar kualitas literasi dan modus belas kasihan |
| 8 | `2020129737239310657` | `confirmed_excluded` | `employment_concern` | Tawa singkat *"Skwkwkw susah cari kerja nya"* tanpa narasi |
| 9 | `2023757499615322234` | `confirmed_excluded` | `employment_concern` | Keluhan renovasi kantor Kemenag |
| 10 | `2031648654755348516` | `confirmed_excluded` | `issue_abroad_link` | Rilis berita institusional KP2MI / bonus demografi |
| 11 | `2039770787297837323` | `confirmed_excluded` | `abroad_discourse` | Cerita supir taksi lansia di Brunei mengisi waktu luang |
| 12 | `2040572225850691885` | `confirmed_excluded` | `abroad_discourse` | Cuitan defensif *"Kalau gak suka skip aja"* |
| 13 | `2040996588085186964` | `confirmed_excluded` | `abroad_discourse` | Cerita komunitas bebas hutang (kuliah/kerja luar negeri) |
| 14 | `2053415478991986852` | `confirmed_excluded` | `employment_concern` | Komentar kasus kriminal pemecatan pegawai |
| 15 | `2053445750571602036` | `confirmed_excluded` | `employment_concern` | Kritik politik makro ekonomi & gestur pidato |
| 16 | `2054397349171228679` | `confirmed_excluded` | `abroad_discourse` | Promosi komersial kursus UT School & Scania Global |
| 17 | `2054474849704362074` | `confirmed_excluded` | `abroad_discourse` | Perdebatan pajak orang kerja luar negeri di bawah PTKP |
| 18 | `2054490014290162038` | `confirmed_excluded` | `abroad_discourse` | Cerita kehilangan rumah keluarga saat Covid 2021 |
| 19 | `2063533335734108390` | `confirmed_excluded` | `issue_abroad_link` | Artikel opini profesional program penempatan Swiss |
| 20 | `2074721181589213434` | `confirmed_excluded` | `employment_concern` | Komentar insidental bursa kerja |
| 21 | `2074827217264402659` | `confirmed_excluded` | `employment_concern` | Tanggapan politik isu lapangan kerja |
| 22 | `2086394231124537361` | `confirmed_excluded` | `abroad_discourse` | Perbandingan biaya hidup luar negeri non-pekerja |
| 23 | `2095531971644658014` | `confirmed_excluded` | `abroad_discourse` | Rangkuman berita visa kerja umum |
| 24 | `2095559949284004299` | `confirmed_excluded` | `abroad_discourse` | Tips travel umum ke luar negeri |
| 25 | `2095778205848179040` | `confirmed_excluded` | `abroad_discourse` | Diskusi non-formal ekspatriat |

### B. 1 Postingan yang Dipulihkan ke Final Corpus (Model: `exclude`, Manual: `include`)
- **`post_id`:** `2008692436667887848`
- **Status Heuristik Lama:** `confirmed_relevant`
- **Prediksi Model:** `exclude` (`incidental_mention_exclusion`)
- **Keputusan Manual:** `include`
- **Isi Teks RAW:** *"@tanyakanrl Bantu orang tua jualan masuk pengalaman kerja. Punya olshop pengalaman kerja, tapi belum tentu disukai karena..."*
- **Tindakan Penyelamatan:** Sesuai kebijakan proteksi ground truth manusia, postingan ini dipulihkan masuk ke korpus akhir dengan label `selection_source = historical_manual_include`.

---

## 3. Komposisi Korpus Akhir Berdasarkan Sumber Seleksi

Dari **1.492 baris** pada [`data/processed/final_corpus.csv`](file:///Users/reginaaruan/Documents/ANMEDSOS/data/processed/final_corpus.csv):
1. **`historical_manual_include`:** **64 tweet** (4.29%) — Diverifikasi oleh auditor manusia.
2. **`model_include`:** **1.428 tweet** (95.71%) — Diseleksi secara otomatis oleh pengklasifikasi aturan leksikal-diskursus lokal (`anmedsos-rule-hybrid-v1`), berstatus **provisional**.

---

## 4. Distribusi Multi-Label Riset (RQ1 & RQ2)

Pemetaan Research Questions dilakukan secara tepat sasaran:

```text
Korpus Akhir (1.492 tweet)
  ├─► RQ1 (employment_issue):   703 tweet  [47.1%] (Keresahan pasar kerja lokal)
  ├─► RQ2 (abroad_discourse):   425 tweet  [28.5%] (Wacana publik kerja luar negeri)
  ├─► RQ2 (abroad_aspiration):  189 tweet  [12.7%] (Aspirasi pribadi #KaburAjaDulu)
  └─► RQ2 (issue_abroad_link):    6 tweet  [ 0.4%] (Link kausal langsung eksplisit)
```

> [!IMPORTANT]
> - `issue_abroad_link` secara resmi dipetakan ke **RQ2**, bukan RQ3.
> - Hanya **6 tweet** yang secara eksplisit menyatakan kaitan kausal domestik-ke-luar negeri dalam satu tweet tunggal (misal: *"daripada nganggur di Indo mending kerja di luar"*). Klasifikasi ini berstatus **provisional / eksploratori**.
> - **RQ3 (Analisis Sentimen):** Belum dijalankan sama sekali. Korpus telah dipersiapkan secara ramah sentimen (kata negasi, intensifier, tanda baca ekspresif, dan emoji dipertahankan murni).

---

## 5. Cakupan Tanggal Faktual vs. Desain Riset

- **Periode Desain Riset:** 1 Januari 2026 s.d. 25 Oktober 2026 (298 hari kalender).
- **Cakupan Tanggal Riil yang Tersampel (*Observed Coverage*):** **1 Januari 2026 s.d. 7 Oktober 2026 (WIB)**.
- **Keterbatasan Metodologis:** Crawler historis mengambil data dengan jadwal jendela mingguan (minggu pertama/kedua setiap bulan). Pada bulan Oktober 2026, tugas pengambilan data hanya mengeksekusi jendela 1–8 Oktober. **Tanggal 9 s.d. 25 Oktober 2026 tidak pernah tersampel.**
- **Instruksi Pelaporan:** Tim tidak boleh mengklaim data mencakup harian penuh hingga 25 Oktober. Laporan harus secara transparan menyatakan rentang data aktif adalah 1 Januari – 7 Oktober 2026.

---

## 6. Daftar Berkas Final & Hash SHA-256

| Berkas | Ukuran / Baris | SHA-256 Digest | Status Kelayakan |
|:---|:---:|:---|:---:|
| [`data/raw/raw_tweets.jsonl`](file:///Users/reginaaruan/Documents/ANMEDSOS/data/raw/raw_tweets.jsonl) | 3.292 JSON lines | `4d85c6950b83e5f8af7227c0d1b8499da9a7cb572507595814b2efcd71bdcf87` | Source Frozen |
| [`data/interim/manual_labels.csv`](file:///Users/reginaaruan/Documents/ANMEDSOS/data/interim/manual_labels.csv) | 95 baris | `0164ee0302fbd92abed71d3b54a6dc9ae2ba201af826ed80b5ec097e567bbc0b` | Ground Truth |
| [`data/interim/evaluation_sample.csv`](file:///Users/reginaaruan/Documents/ANMEDSOS/data/interim/evaluation_sample.csv) | 150 baris | `5fa0d38a15535529052ea6c64506c372a8d0ce1fcc1d8aef7bf9c311fb47519a` | Needs Validation |
| [`data/processed/analysis_ready.csv`](file:///Users/reginaaruan/Documents/ANMEDSOS/data/processed/analysis_ready.csv) | 1.000 baris | `666b9cb87c20a6ab68c6c9d3b314a8da0c5eb0795cedd7fb4e31cf29fad934bf` | TK-2 Official |
| [`data/processed/text_preprocessed.csv`](file:///Users/reginaaruan/Documents/ANMEDSOS/data/processed/text_preprocessed.csv) | 1.000 baris | `14467c11d8bd92cef69fc6e11c30e41fc2918ff570c3c7a557237e7ce3b6d1e2` | TK-2 Official |
| [`data/processed/final_corpus.csv`](file:///Users/reginaaruan/Documents/ANMEDSOS/data/processed/final_corpus.csv) | 1.492 baris | `0e6190d2b2b1af1caca23ab06b4ab4cd868db5aa49ebd00b43c6e2bd3c904cde` | Provisional Full |
| [`data/processed/final_preprocessed.csv`](file:///Users/reginaaruan/Documents/ANMEDSOS/data/processed/final_preprocessed.csv) | 1.492 baris | `a52797edae1421d99f0d0a160214a7c6a31282fd8e4449dd06b0df7809363038` | Provisional Full |

---

## 7. Instruksi Reproduksi Offline

Repositori ini dapat direproduksi 100% tanpa jaringan dan tanpa biaya API:
```bash
# 1. Jalankan pipeline offline lengkap (7 langkah berurutan):
bash examples/run_offline_pipeline.sh

# 2. Jalankan rangkaian tes unit dan integrasi otomatis:
python3 -m pytest -v tests/
```

**Kesimpulan Akhir:**  
Repositori ANMEDSOS telah **terverifikasi secara ilmiah, konsisten hingga level baris individual, transparan dalam keterbatasan data, dan siap dibekukan untuk submission tugas TK-2.**

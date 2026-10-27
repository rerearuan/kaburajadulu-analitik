# Metodologi Preprocessing Teks ANMEDSOS

**Judul Penelitian:**  
*Keresahan Ketenagakerjaan dan Aspirasi Bekerja ke Luar Negeri di Era #KaburAjaDulu: Analisis Topik dan Sentimen Wacana Publik di Platform X*

---

## 1. Filosofi dan Prinsip Dasar Preprocessing

1. **Integritas Bukti Primer (*Data Trace Integrity*):**  
   Teks asli (`text_raw`) dipertahankan 100% tanpa perubahan (*byte-exact*). Tidak ada modifikasi *in-place* pada berkas sumber.
2. **Kesesuaian dengan Pemodelan Hilir (*Downstream NLP Compatibility*):**  
   - **BERTopic:** Menggunakan model semantik berbasis *contextual embeddings* (misal IndoBERT atau RoBERTa). Model transformer memerlukan urutan kata alami, tanda baca bermakna, dan struktur tata bahasa utuh. Oleh karena itu, **tidak digunakan stemming agresif** atau pembuangan *stopwords* sembarangan pada teks input representasi topik.
   - **Analisis Sentimen:** Membutuhkan kata-kata negasi (*tidak, bukan, belum, jangan, nggak*), intensifier (*banget*), tanda baca ekspresif (*!!, ??*), serta emoji emosional (😭, 🥹, 😂). Seluruh elemen ini dilindungi.

---

## 2. Multi-Representasi Teks

Prapemrosesan menghasilkan 4 kolom teks terpisah untuk fungsi yang berbeda:

| Kolom | Tujuan | Karakteristik Transformasi |
|:---|:---|:---|
| `text_raw` | Arsip & audit | Teks asli platform X tanpa modifikasi sama sekali. |
| `text_clean` | Analisis EDA & inspeksi | Pembersihan standar: unescape HTML, URL stripped, handle mention stripped, casefold, normalisasi slang token utuh. |
| `text_topic` | Input embedding BERTopic | Struktur sintaksis alami dipertahankan, tagar `#kaburajadulu` dipertahankan, URL dan mention dihilangkan. |
| `text_sentiment` | Analisis sentimen hilir | Polaritas dan intensitas dilindungi: negasi dinormalisasi (`tidak`), emoji utuh, tanda baca ekspresif terjaga. |

---

## 3. Tahapan Preprocessing Bertahap

```text
[text_raw]
   │
   ├─► 1. HTML Unescape (html.unescape): decoding entity &amp;, &lt;, &gt;, dsb.
   ├─► 2. Unicode Normalization: NFC standardization (menggabungkan decomposed glyphs).
   ├─► 3. Conservative URL Removal: regex (?i)https?://\S+|www\.\S+ diganti spasi tunggal.
   ├─► 4. Mention Sanitization: regex (?<!\w)@[A-Za-z0-9_]{1,15}\b diganti spasi (melindungi privasi).
   ├─► 5. Control Character Stripping: kategori Unicode Cc dan Cf dihilangkan.
   ├─► 6. Case Folding: normalisasi ke huruf kecil secara deterministik (casefold).
   ├─► 7. Whole-Token Slang Normalization: regex (?<![\w#])(?:term)(?!\w) untuk mencegah false substring.
   └─► 8. Whitespace Collapse: perapihan spasi berlebih menjadi spasi tunggal dan strip margin.
```

---

## 4. Evaluasi Pemotongan Teks (*Truncation Refinement*)

Pemeriksaan teks terpotong tidak lagi menggunakan heuristik panjang karakter semata. Dua metrik disediakan:
1. `possible_truncation`: Peringatan heuristik panjang ($\ge 90$ karakter tanpa tanda baca terminal).
2. `explicit_truncation`: Peringatan ketat pemotongan eksplisit:
   - Kalimat diakhiri tanda elipsis (`…` atau `...`).
   - Kalimat menggantung diakhiri konjungsi/preposisi (*dan, yang, karena, atau, di, ke, dari, with, and*).

---

## 5. Diagnostik Bahasa (*Language Variety*)

Mendeteksi keragaman bahasa tweet pada kolom `detected_language`:
- `indonesian`: Teks dominan kosakata bahasa Indonesia.
- `english`: Teks dominan kosakata bahasa Inggris.
- `mixed_id_en`: Teks campur kode (*code-mixing*) khas warganet (misal: istilah *fresh graduate*, *overqualified*, *job market* bercampur dengan partikel bahasa Indonesia).
- `unknown`: Teks pendek tanpa token leksikal yang memadai.

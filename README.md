# SHRERATE-TOOLS

Sebuah tool uji beban HTTP dan stress test yang canggih, dirancang untuk menguji performa dan ketahanan server/aplikasi web Anda terhadap volume permintaan tinggi. Dilengkapi dengan fitur-fitur seperti manajemen proxy, variasi payload, spoofing header, dan tampilan real-time yang informatif.

---

## 🌟 Dibuat oleh: azkiah 🌟

---

## 💡 Gambaran Umum

Tool ini mensimulasikan trafik dari banyak klien secara bersamaan untuk mengirimkan permintaan HTTP ke target URL yang ditentukan. Ini sangat berguna untuk:

* **Uji Performa:** Mengukur bagaimana server/aplikasi Anda merespons di bawah beban tinggi.
* **Identifikasi Bottleneck:** Menemukan batasan sumber daya (CPU, RAM, Jaringan) pada server.
* **Pengujian Ketahanan (Stress Test):** Memastikan aplikasi tetap stabil dan berfungsi meskipun diserang dengan banyak permintaan.
* **Simulasi Pengguna:** Dengan fitur "thinking time" dan User Agent yang bervariasi, traffic terlihat lebih natural.

**Penting:** Tool ini dibuat untuk tujuan **ETIS dan PENDIDIKAN**. **JANGAN PERNAH** menggunakannya untuk menyerang atau merusak sistem yang tidak Anda miliki atau tidak memiliki izin tertulis untuk mengujinya. Penyalahgunaan tool ini bisa berujung pada konsekuensi hukum yang serius.

## ✨ Fitur Utama

* **Multi-threading:** Mengirim permintaan secara konkurensi menggunakan banyak thread.
* **Kontrol RPS (Requests Per Second):** Menyesuaikan laju permintaan per thread.
* **Metode HTTP Fleksibel:** Mendukung metode GET, POST, dan HEAD.
* **Spoofing Header:** Menggunakan User-Agent dan X-Forwarded-For palsu untuk simulasi traffic yang lebih realistis.
* **Random Parameter & Payload:** Menghasilkan parameter URL acak dan data JSON bervariasi untuk POST request.
* **Waktu Berpikir (Thinking Time):** Menambahkan jeda acak antar permintaan untuk mensimulasikan perilaku pengguna alami.
* **Manajemen Proxy (Opsional):** Mampu membaca dan merotasi proxy dari file teks (`proxies.txt`).
* **Statistik Real-time:** Menampilkan total permintaan, sukses, gagal, RPS rata-rata, dan waktu respons rata-rata.
* **Laporan Ringkasan Detail:** Menyajikan distribusi status kode HTTP dan laporan error proxy di akhir pengujian.
* **Tampilan CLI Interaktif:** Output berwarna dan rapi di terminal (mendukung `rich` library untuk visualisasi yang lebih canggih).
* **Logika Retry:** Mengulang permintaan yang gagal untuk ketahanan pengujian.

## ⚙️ Persyaratan Sistem

* Python 3.x
* Koneksi internet (untuk mengunduh dependencies dan mengakses target URL)

## 📦 Cara Instalasi

1.  **Clone Repositori (atau Unduh File):**
    ```bash
    git clone https://github.com/memed123-del/SHRERATE-TOOLS.git
    cd SHRERATE-TOOLS
    python pol3.py
    ```
    
    Jika Anda hanya mengunduh file `.py` secara manual, cukup letakkan di folder pilihan Anda.

2.  **Instal Dependensi Python:**
    Buka terminal Anda dan jalankan perintah berikut:
    ```bash
    pip install requests rich
    ```
    * `requests`: Library HTTP untuk mengirim permintaan.
    * `rich` (Opsional): Library untuk tampilan terminal yang lebih canggih. Jika Anda tidak ingin menginstalnya (misalnya untuk menghemat resource atau menghindari dependensi), skrip akan otomatis *fallback* ke tampilan CLI standar.

## 🚀 Cara Penggunaan

### 1. Buat File Proxy (Opsional)

Jika Anda ingin menggunakan proxy, buat file bernama `proxies.txt` di direktori yang sama dengan skrip Python Anda. Isi file ini dengan daftar proxy Anda, satu proxy per baris.

**Contoh `proxies.txt`:**

http://192.168.1.1:8080
http://user:password@proxy.example.com:3128
https://secureproxy.net:443

*Jika file ini tidak ada atau kosong, skrip akan menggunakan koneksi langsung.*

### 2. Jalankan Skrip

Buka terminal Anda, navigasikan ke direktori tempat Anda menyimpan skrip, lalu jalankan dengan perintah berikut:

```bash
python3 pol3.py <TARGET_URL> [OPSI_OPSI_LAINNYA]

Contoh penggunaan dasar:
Bash

python3 pol3.py [https://target-aplikasi-anda.com](https://target-aplikasi-anda.com) -t 20 -r 4 -d 180

    Ini akan menguji https://target-aplikasi-anda.com dengan 20 thread, masing-masing mengirim 4 permintaan per detik, selama 180 detik.

Contoh penggunaan dengan proxy dan waktu berpikir:
Bash

python3 pol3.py [https://api.mywebsite.com/data](https://api.mywebsite.com/data) -t 15 -r 5 -d 60 --proxies-file proxies.txt --min-payload 0.5 --max-payload 1.5 --think-time-min 0.2 --think-time-max 0.8

📋 Opsi Command Line
Opsi Pendek	Opsi Panjang	Tipe	Default	Deskripsi
N/A	url	String	Wajib	Target URL untuk uji beban (misal: https://example.com/api/data).
-t	--threads	Integer	20	Jumlah thread konkurensi.
-r	--rps	Integer	4	Permintaan per detik per thread.
-d	--duration	Integer	180	Durasi pengujian dalam detik.
N/A	--timeout	Integer	8	Timeout untuk setiap permintaan (detik).
N/A	--retries	Integer	2	Jumlah percobaan ulang jika permintaan gagal.
N/A	--retry-delay	Float	1.0	Jeda antara percobaan ulang (detik).
N/A	--min-payload	Float	0.25	Ukuran payload POST minimum (KB).
N/A	--max-payload	Float	1.0	Ukuran payload POST maksimum (KB).
N/A	--think-time-min	Float	0.1	Waktu berpikir minimum acak antar permintaan (detik).
N/A	--think-time-max	Float	0.5	Waktu berpikir maksimum acak antar permintaan (detik).
N/A	--proxies-file	String	proxies.txt	Nama file yang berisi daftar proxy (satu per baris).
🤝 Kontribusi

Sangat dipersilakan jika ada yang ingin berkontribusi untuk pengembangan tool ini!
Silakan buka issue untuk laporan bug atau saran fitur, atau buat pull request dengan perubahan Anda.
⚠️ Disclaimer

Tool ini disediakan "apa adanya" tanpa jaminan apapun. Pengguna bertanggung jawab penuh atas segala dampak dari penggunaan tool ini.
Gunakan tool ini hanya pada sistem yang Anda miliki atau yang Anda memiliki izin eksplisit untuk mengujinya.

# ⚡ Wireless Android Device Manager

Tools untuk menghubungkan HP Android real device Anda secara nirkabel (Wireless Debugging) tanpa perlu repot mencatat IP dan port secara manual. Mendukung **File Explorer**, **Debugging/Logcat**, **Screen Mirroring (`scrcpy`)**, serta **Port Forwarding**.

---

## ✨ Fitur Utama

1. **Auto-Discovery (mDNS / Bonjour):**
   - Mendeteksi otomatis layanan `_adb-tls-connect` dan `_adb-tls-pairing` di jaringan Wi-Fi lokal.
   - Tidak perlu menebak port dinamis Android 11+.
2. **Web Dashboard Interaktif:**
   - Visualisasi perangkat: status baterai & pengisian daya, kapasitas penyimpanan, dan IP Wi-Fi.
   - **File Explorer visual**: navigasi folder `/sdcard/`, unduh (pull), hapus, dan unggah (push) via drag-and-drop.
   - **APK Auto-Install**: unggah file `.apk` dan langsung terpasang ke HP.
   - **Screen Mirroring (`scrcpy`)**: 1-klik untuk melihat dan mengontrol layar HP dari Mac.
   - **Reverse Port**: 1-klik untuk mengarahkan port dev server Mac (misal `3000`) agar bisa diakses langsung di HP via `localhost:3000`.
   - **Live Logcat**: memantau log aplikasi secara langsung dengan filter.
3. **Interactive Terminal CLI:**
   - Menu keyboard-friendly langsung di terminal jika tidak ingin membuka browser.
4. **USB to Wi-Fi Switcher:**
   - 1-klik beralih dari kabel USB ke mode wireless (`tcpip 5555`).

---

## 🚀 Cara Menjalankan

### Mode 1: Web Dashboard (Rekomendasi)
Cukup jalankan perintah berikut, browser akan otomatis terbuka:
```bash
python3 main.py
```
Akses dashboard di: **[http://localhost:8080](http://localhost:8080)**

Jika ingin menggunakan port lain atau tanpa membuka browser otomatis:
```bash
python3 main.py --port 9000 --no-browser
```

---

### Mode 2: Interactive Terminal CLI
Bagi yang menyukai bekerja langsung di terminal:
```bash
python3 main.py --cli
```

---

### Shortcut Perintah Cepat (One-Liner)

#### 📂 Transfer File & Folder:
* **Kirim file/folder dari Mac ke HP:**
  ```bash
  # Mengirim file ke /sdcard/Download/ (default)
  python3 main.py --send foto.jpg
  python3 main.py --send dokumen.pdf --dest /sdcard/Documents/
  ```
* **Ambil (unduh) file dari HP ke Mac:**
  ```bash
  # Mengunduh file ke folder kerja saat ini
  python3 main.py --get /sdcard/Download/dokumen.pdf
  python3 main.py --get /sdcard/DCIM/Camera/photo.jpg --dest ~/Downloads/
  ```
* **Lihat isi folder HP langsung dari terminal:**
  ```bash
  python3 main.py --ls
  python3 main.py --ls /sdcard/DCIM/Camera
  ```

#### 📱 Kontrol & Debugging:
* **Cek perangkat terhubung:**
  ```bash
  python3 main.py --devices
  ```
* **Luncurkan mirror layar (`scrcpy`):**
  ```bash
  python3 main.py --scrcpy
  ```
* **Konek langsung ke IP & Port:**
  ```bash
  python3 main.py --connect 192.168.0.71:37739
  ```
* **Pairing baru dengan PIN:**
  ```bash
  python3 main.py --pair 192.168.0.71:38291 123456
  ```
* **Alihkan HP colokan USB ke nirkabel:**
  ```bash
  python3 main.py --switch-usb <SERIAL_USB>
  ```

---

## 📁 Struktur Kode

```
wireless-connection-device/
├── main.py                  # Entry point (Web & CLI)
├── core/
│   ├── adb_manager.py       # Core wrapper ADB & scrcpy
│   ├── mdns_discovery.py    # Pemantau mDNS background
│   └── device_model.py      # Penyimpanan data perangkat
├── web/
│   ├── server.py            # HTTP Server & REST API
│   └── static/
│       ├── index.html       # Antarmuka Web Dashboard
│       ├── app.js           # Logika interaktif frontend
│       └── style.css        # Styling UI
└── cli/
    └── interactive_cli.py   # Menu interaktif terminal
```

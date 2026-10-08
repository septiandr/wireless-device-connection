#!/bin/bash
# Double-click file ini di Finder: Akan muncul jendela dialog Mac untuk memilih file lalu kirim ke HP
cd "$(dirname "$0")"

echo "📂 Membuka dialog pemilihan file..."
FILE_PATH=$(osascript -e 'POSIX path of (choose file with prompt "Pilih file yang ingin dikirim ke HP Android:")' 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
    echo "Pengiriman dibatalkan (tidak ada file yang dipilih)."
    exit 0
fi

echo ""
echo "Mengirim berkas: $FILE_PATH"
python3 main.py --send "$FILE_PATH"

echo ""
read -p "Selesai! Tekan Enter untuk menutup..."

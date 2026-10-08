#!/bin/bash
# Double-click file ini di Finder untuk langsung mirror layar HP via scrcpy
cd "$(dirname "$0")"
echo "📱 Menghubungkan dan membuka mirror layar (scrcpy)..."
python3 main.py --scrcpy
if [ $? -ne 0 ]; then
    echo ""
    read -p "Tekan Enter untuk keluar..."
fi

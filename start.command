#!/bin/bash
# Double-click file ini di Finder untuk langsung menjalankan Web Dashboard
cd "$(dirname "$0")"
echo "🚀 Memulai Wireless Android Device Manager..."
echo "Akan membuka browser di http://localhost:8080..."
python3 main.py

#!/bin/bash
# Double-click file ini di Finder untuk langsung masuk ke menu Terminal interaktif
cd "$(dirname "$0")"
python3 main.py --cli

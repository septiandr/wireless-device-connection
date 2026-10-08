#!/usr/bin/env python3
"""
Wireless Android Device Manager
A comprehensive tool for frictionless Android Wireless Debugging, File Transfer, and Developer Tooling.
"""

import argparse
import os
import sys
from core.adb_manager import ADBManager

def main():
    parser = argparse.ArgumentParser(description="Wireless Android Device Manager")
    parser.add_argument("--cli", action="store_true", help="Jalankan mode Interactive Terminal CLI")
    parser.add_argument("--port", type=int, default=8080, help="Port untuk Web Dashboard (default: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="Jangan buka browser secara otomatis")
    
    # Quick CLI shortcuts
    parser.add_argument("--connect", metavar="IP:PORT", help="Hubungkan langsung ke IP:Port tertentu")
    parser.add_argument("--pair", nargs=2, metavar=("IP:PORT", "PIN"), help="Pair langsung dengan IP:Port dan PIN")
    parser.add_argument("--scrcpy", action="store_true", help="Luncurkan screen mirror scrcpy untuk perangkat aktif")
    parser.add_argument("--devices", action="store_true", help="Tampilkan daftar perangkat terhubung")
    parser.add_argument("--switch-usb", metavar="SERIAL", help="Alihkan perangkat USB ke mode wireless TCP/IP")

    # File transfer shortcuts
    parser.add_argument("--send", "--push", metavar="LOCAL_PATH", help="Kirim file/folder dari Mac ke HP (default dest: /sdcard/Download/)")
    parser.add_argument("--get", "--pull", metavar="REMOTE_PATH", help="Ambil file/folder dari HP ke Mac (default dest: folder saat ini)")
    parser.add_argument("--dest", default="", help="Tujuan spesifik untuk transfer file (--send atau --get)")
    parser.add_argument("--ls", nargs="?", const="/sdcard/Download", help="Lihat isi folder di HP (default: /sdcard/Download)")

    args = parser.parse_args()
    adb = ADBManager()

    # Helper to get default active device
    def get_target_device():
        devs = adb.get_attached_devices()
        if not devs:
            print("\033[31mError: Tidak ada perangkat Android terhubung!\033[0m")
            print("Sambungkan HP via 'python3 main.py --connect <ip>:<port>' atau buka dashboard.")
            sys.exit(1)
        return devs[0]["serial"]

    # Handle quick shortcuts
    if args.devices:
        devs = adb.get_attached_devices()
        print(f"Total perangkat terhubung: {len(devs)}")
        for d in devs:
            w = "Wi-Fi" if d["is_wireless"] else "USB"
            print(f"- {d['model']} ({d['serial']}) [{w}]")
        sys.exit(0)

    # File Transfer: Send (Push)
    if args.send:
        serial = get_target_device()
        local_path = args.send.strip("'\"")
        if not os.path.exists(local_path):
            print(f"\033[31mError: File lokal '{local_path}' tidak ditemukan!\033[0m")
            sys.exit(1)
        dest = args.dest or "/sdcard/Download/"
        print(f"Mengirim '{local_path}' -> '{dest}' di HP ({serial})...")
        ok, msg = adb.push_file(serial, local_path, dest)
        if ok:
            print(f"\033[32mBerhasil terkirim!\033[0m {msg}")
        else:
            print(f"\033[31mGagal mengirim:\033[0m {msg}")
        sys.exit(0 if ok else 1)

    # File Transfer: Get (Pull)
    if args.get:
        serial = get_target_device()
        remote_path = args.get.strip("'\"")
        local_dest = args.dest or "./"
        print(f"Mengunduh '{remote_path}' -> '{local_dest}' dari HP ({serial})...")
        ok, msg = adb.pull_file(serial, remote_path, local_dest)
        if ok:
            print(f"\033[32mBerhasil diunduh!\033[0m {msg}")
        else:
            print(f"\033[31mGagal mengunduh:\033[0m {msg}")
        sys.exit(0 if ok else 1)

    # File Transfer: List (ls)
    if args.ls:
        serial = get_target_device()
        path = args.ls
        print(f"📁 Daftar file di '{path}' ({serial}):\n")
        items = adb.list_files(serial, path)
        for it in items:
            icon = "📁" if it["is_dir"] else "📄"
            size = f"({it['size']/1024/1024:.1f} MB)" if not it["is_dir"] and it["size"] > 0 else ""
            print(f"  {icon} {it['name']:<35} {size:<12} {it['date']}")
        sys.exit(0)

    if args.connect:
        target = args.connect
        ip, port = target.split(":") if ":" in target else (target, "5555")
        print(f"Menghubungkan ke {ip}:{port}...")
        ok, msg = adb.connect_device(ip, port)
        print(msg)
        sys.exit(0 if ok else 1)

    if args.pair:
        target, pin = args.pair
        ip, port = target.split(":") if ":" in target else (target, "")
        if not port:
            print("Format salah! Gunakan: --pair IP:PORT PIN")
            sys.exit(1)
        print(f"Memasangkan ke {ip}:{port} dengan PIN {pin}...")
        ok, msg = adb.pair_device(ip, port, pin)
        print(msg)
        sys.exit(0 if ok else 1)

    if args.scrcpy:
        devs = adb.get_attached_devices()
        if not devs:
            print("Tidak ada perangkat terhubung!")
            sys.exit(1)
        ok, msg = adb.launch_scrcpy(devs[0]["serial"])
        print(msg)
        sys.exit(0 if ok else 1)

    if args.switch_usb:
        ok, msg, ip = adb.switch_usb_to_wireless(args.switch_usb)
        print(msg)
        sys.exit(0 if ok else 1)

    # If --cli requested, run CLI mode
    if args.cli:
        from cli.interactive_cli import InteractiveCLI
        cli = InteractiveCLI()
        cli.run()
        return

    # Default: Run Web Dashboard
    from web.server import run_server
    run_server(host="127.0.0.1", port=args.port, open_browser=not args.no_browser)

if __name__ == "__main__":
    main()

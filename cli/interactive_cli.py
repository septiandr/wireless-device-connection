import os
import sys
from core.adb_manager import ADBManager
from core.device_model import DeviceStorage

class InteractiveCLI:
    def __init__(self):
        self.adb = ADBManager()

    def print_header(self):
        os.system("clear")
        print("\033[1;36m========================================================\033[0m")
        print("\033[1;32m      ⚡ WIRELESS ANDROID DEVICE MANAGER ⚡            \033[0m")
        print("\033[1;36m========================================================\033[0m")
        print(f"ADB: {self.adb.adb_path}")
        scrcpy_status = "\033[32mTerpasang\033[0m" if self.adb.scrcpy_path else "\033[31mTidak Ditemukan\033[0m"
        print(f"Scrcpy: {scrcpy_status}")
        print("--------------------------------------------------------\n")

    def show_attached_devices(self):
        devices = self.adb.get_attached_devices()
        print("\033[1;33m📱 Perangkat Terhubung:\033[0m")
        if not devices:
            print("   \033[90m(Tidak ada perangkat terhubung saat ini)\033[0m\n")
            return []

        for idx, dev in enumerate(devices, 1):
            conn_type = "📶 Wi-Fi" if dev["is_wireless"] else "🔌 USB"
            details = self.adb.get_device_details(dev["serial"])
            batt = f"🔋 {details['battery_level']}%" if details['battery_level'] >= 0 else ""
            ip = f"IP: {details.get('wifi_ip') or dev['ip']}"
            print(f"   [{idx}] \033[1m{dev['model']}\033[0m ({dev['serial']}) - {conn_type} {batt} {ip}")
        print()
        return devices

    def auto_discover_and_connect(self):
        print("\n\033[1;34m🔍 Memindai layanan mDNS Wireless Debugging...\033[0m")
        services = self.adb.get_mdns_services()
        connect_services = [s for s in services if "_adb-tls-connect" in s.get("service_type", "")]
        pairing_services = [s for s in services if "_adb-tls-pairing" in s.get("service_type", "")]

        if not services:
            print("   \033[33mTidak ada layanan mDNS yang terdeteksi secara otomatis.\033[0m")
            print("   Pastikan fitur 'Wireless debugging' aktif di Developer Options HP Anda.")
            manual = input("\nIngin masukkan IP dan Port manual? (y/N): ").strip().lower()
            if manual == "y":
                ip = input("Masukkan IP HP (contoh: 192.168.0.71): ").strip()
                port = input("Masukkan Port (contoh: 37739 atau 5555): ").strip() or "5555"
                print(f"Menghubungkan ke {ip}:{port}...")
                ok, msg = self.adb.connect_device(ip, port)
                print(f"\033[{'32' if ok else '31'}m{msg}\033[0m")
            return

        if connect_services:
            print("\n\033[1;32mDitemukan Perangkat Siap Konek:\033[0m")
            for i, svc in enumerate(connect_services, 1):
                print(f"   [{i}] {svc['service_name']} -> {svc['ip']}:{svc['port']}")
            choice = input(f"\nPilih perangkat untuk dihubungkan (1-{len(connect_services)}): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(connect_services):
                target = connect_services[int(choice) - 1]
                print(f"Menghubungkan ke {target['ip']}:{target['port']}...")
                ok, msg = self.adb.connect_device(target["ip"], target["port"])
                print(f"\033[{'32' if ok else '31'}m{msg}\033[0m")

        if pairing_services:
            print("\n\033[1;33mDitemukan Permintaan Pairing Baru:\033[0m")
            for i, svc in enumerate(pairing_services, 1):
                print(f"   [{i}] {svc['service_name']} -> {svc['ip']}:{svc['port']}")
            choice = input(f"Pilih untuk dipairing (atau enter untuk lewati): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(pairing_services):
                target = pairing_services[int(choice) - 1]
                pin = input("Masukkan 6-digit kode pairing dari layar HP: ").strip()
                ok, msg = self.adb.pair_device(target["ip"], target["port"], pin)
                print(f"\033[{'32' if ok else '31'}m{msg}\033[0m")

    def pair_manual(self):
        print("\n\033[1;34m🔑 Pairing Manual:\033[0m")
        print("Buka HP -> Developer Options -> Wireless debugging -> 'Pair device with pairing code'")
        ip = input("Masukkan IP perangkat: ").strip()
        port = input("Masukkan Pairing Port (misal: 38291): ").strip()
        pin = input("Masukkan 6-digit Pairing Code: ").strip()
        if ip and port and pin:
            print(f"Sedang melakukan pairing ke {ip}:{port}...")
            ok, msg = self.adb.pair_device(ip, port, pin)
            print(f"\033[{'32' if ok else '31'}m{msg}\033[0m")
            if ok:
                connect_port = input("Masukkan Port Koneksi utama (lihat di halaman utama Wireless debugging): ").strip()
                if connect_port:
                    print(f"Menghubungkan ke {ip}:{connect_port}...")
                    c_ok, c_msg = self.adb.connect_device(ip, connect_port)
                    print(f"\033[{'32' if c_ok else '31'}m{c_msg}\033[0m")

    def switch_usb(self):
        devices = self.adb.get_attached_devices()
        usb_devices = [d for d in devices if not d["is_wireless"]]
        if not usb_devices:
            print("\n\033[31mTidak ada perangkat terhubung via USB!\033[0m")
            print("Colokkan HP via kabel USB terlebih dahulu dengan USB Debugging aktif.")
            return

        print("\nPilih perangkat USB:")
        for i, d in enumerate(usb_devices, 1):
            print(f"   [{i}] {d['model']} ({d['serial']})")
        choice = input(f"Pilih (1-{len(usb_devices)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(usb_devices):
            target = usb_devices[int(choice) - 1]
            print("Mengalihkan ke mode TCP/IP port 5555...")
            ok, msg, wifi_ip = self.adb.switch_usb_to_wireless(target["serial"])
            print(f"\033[{'32' if ok else '31'}m{msg}\033[0m")

    def screen_mirror(self):
        devices = self.adb.get_attached_devices()
        if not devices:
            print("\n\033[31mTidak ada perangkat terhubung!\033[0m")
            return
        target = devices[0]["serial"]
        if len(devices) > 1:
            for i, d in enumerate(devices, 1):
                print(f"   [{i}] {d['model']} ({d['serial']})")
            choice = input(f"Pilih perangkat (1-{len(devices)}): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(devices):
                target = devices[int(choice) - 1]["serial"]

        print(f"Meluncurkan scrcpy untuk {target}...")
        ok, msg = self.adb.launch_scrcpy(target)
        print(f"\033[{'32' if ok else '31'}m{msg}\033[0m")

    def file_manager(self):
        devices = self.adb.get_attached_devices()
        if not devices:
            print("\n\033[31mTidak ada perangkat terhubung!\033[0m")
            return
        serial = devices[0]["serial"]
        current_path = "/sdcard/Download"
        
        while True:
            print(f"\n📁 File Explorer ({serial}): \033[1;34m{current_path}\033[0m")
            files = self.adb.list_files(serial, current_path)
            for idx, item in enumerate(files[:25], 1):
                icon = "📁" if item["is_dir"] else "📄"
                size_str = f"({item['size'] / 1024 / 1024:.1f} MB)" if not item["is_dir"] and item["size"] > 0 else ""
                print(f"   {icon} {item['name']} {size_str}")

            print("\nOpsi:")
            print("   1. Buka folder lain")
            print("   2. Push/Upload file ke HP")
            print("   3. Pull/Download file dari HP")
            print("   4. Kembali ke menu utama")
            cmd = input("Pilihan: ").strip()

            if cmd == "1":
                sub = input("Masukkan path atau nama subfolder: ").strip()
                if sub.startswith("/"):
                    current_path = sub
                else:
                    current_path = f"{current_path.rstrip('/')}/{sub}"
            elif cmd == "2":
                local = input("Path file lokal di Mac: ").strip().strip("'\"")
                if os.path.exists(local):
                    print(f"Mengirim {local} ke {current_path}...")
                    ok, msg = self.adb.push_file(serial, local, current_path)
                    print(f"\033[{'32' if ok else '31'}m{msg}\033[0m")
                else:
                    print("\033[31mFile lokal tidak ditemukan!\033[0m")
            elif cmd == "3":
                filename = input("Nama file di HP: ").strip()
                dest = os.path.expanduser("~/Downloads")
                remote_f = f"{current_path.rstrip('/')}/{filename}"
                print(f"Mengunduh ke {dest}...")
                ok, msg = self.adb.pull_file(serial, remote_f, dest)
                print(f"\033[{'32' if ok else '31'}m{msg}\033[0m")
            elif cmd == "4":
                break

    def run(self):
        while True:
            self.print_header()
            attached = self.show_attached_devices()

            print("\033[1mPilih Aksi:\033[0m")
            print("   1. 🔍 Auto-Discover & Sambungkan (mDNS)")
            print("   2. 🔑 Pair Perangkat Baru (6-Digit PIN)")
            print("   3. 🔌 Alihkan USB ke Wi-Fi (tcpip 5555)")
            print("   4. 🖥️  Mirror Layar HP (Scrcpy)")
            print("   5. 📁 File Manager (Kirim/Ambil File)")
            print("   6. 🌐 Buka Web Dashboard")
            print("   7. ❌ Putuskan Semua Koneksi Wireless")
            print("   0. Keluar")

            choice = input("\nMasukkan pilihan (0-7): ").strip()
            if choice == "1":
                self.auto_discover_and_connect()
            elif choice == "2":
                self.pair_manual()
            elif choice == "3":
                self.switch_usb()
            elif choice == "4":
                self.screen_mirror()
            elif choice == "5":
                self.file_manager()
            elif choice == "6":
                print("\nMemulai Web Dashboard di browser...")
                import webbrowser
                from web.server import run_server
                import threading
                t = threading.Thread(target=lambda: run_server(port=8080, open_browser=True), daemon=True)
                t.start()
                print("Web Dashboard berjalan di: http://localhost:8080")
                input("Tekan Enter untuk kembali ke CLI...")
            elif choice == "7":
                self.adb.run_cmd(["disconnect"])
                print("\033[32mKoneksi wireless berhasil diputus.\033[0m")
            elif choice == "0":
                print("Sampai jumpa!")
                sys.exit(0)
            
            input("\nTekan Enter untuk melanjutkan...")

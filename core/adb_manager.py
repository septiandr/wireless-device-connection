import os
import re
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple

class ADBManager:
    def __init__(self, adb_path: Optional[str] = None):
        self.adb_path = adb_path or self._find_adb()
        self.scrcpy_path = self._find_scrcpy()

    def _find_adb(self) -> str:
        # Check system PATH
        path = shutil.which("adb")
        if path:
            return path
        
        # Check standard macOS Android SDK path
        default_mac = os.path.expanduser("~/Library/Android/sdk/platform-tools/adb")
        if os.path.exists(default_mac):
            return default_mac
            
        return "adb"

    def _find_scrcpy(self) -> Optional[str]:
        return shutil.which("scrcpy") or ("/opt/homebrew/bin/scrcpy" if os.path.exists("/opt/homebrew/bin/scrcpy") else None)

    def run_cmd(self, args: List[str], timeout: int = 15) -> Tuple[int, str, str]:
        cmd = [self.adb_path] + args
        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)

    def get_mdns_services(self) -> List[Dict[str, str]]:
        """
        Parses `adb mdns services` to discover active devices advertising
        _adb-tls-connect._tcp and _adb-tls-pairing._tcp
        """
        code, out, _ = self.run_cmd(["mdns", "services"])
        services = []
        if code != 0 or not out:
            return services

        for line in out.splitlines():
            line = line.strip()
            if not line or line.startswith("List of discovered"):
                continue
            parts = line.split()
            if len(parts) >= 3:
                service_name = parts[0]
                service_type = parts[1]
                addr = parts[2]
                ip, port = "", ""
                if ":" in addr:
                    ip, port = addr.split(":", 1)
                services.append({
                    "service_name": service_name,
                    "service_type": service_type,
                    "ip": ip,
                    "port": port,
                    "raw_address": addr
                })
        return services

    def get_attached_devices(self) -> List[Dict]:
        """
        Returns list of connected devices from `adb devices -l`
        """
        code, out, _ = self.run_cmd(["devices", "-l"])
        devices = []
        if code != 0:
            return devices

        for line in out.splitlines():
            line = line.strip()
            if not line or line.startswith("List of devices"):
                continue
            
            parts = line.split()
            serial = parts[0]
            status = parts[1] if len(parts) > 1 else "unknown"
            
            # Extract attributes (model:XXX, product:XXX, etc.)
            props = {}
            for item in parts[2:]:
                if ":" in item:
                    k, v = item.split(":", 1)
                    props[k] = v

            is_wireless = ":" in serial or "._adb-tls-connect" in serial
            ip = ""
            port = 5555
            if ":" in serial and not "._adb-tls-connect" in serial:
                ip_parts = serial.split(":")
                ip = ip_parts[0]
                if len(ip_parts) > 1 and ip_parts[1].isdigit():
                    port = int(ip_parts[1])

            devices.append({
                "serial": serial,
                "status": status,
                "model": props.get("model", props.get("device", "Unknown")),
                "product": props.get("product", ""),
                "is_wireless": is_wireless,
                "ip": ip,
                "port": port
            })
        return devices

    def get_device_details(self, serial: str) -> Dict:
        """
        Gathers battery, android version, storage, and WiFi IP for a connected device.
        """
        details = {
            "battery_level": -1,
            "battery_charging": False,
            "android_version": "",
            "model_name": "",
            "storage_free": "",
            "storage_total": "",
            "wifi_ip": ""
        }

        # Model name
        _, out, _ = self.run_cmd(["-s", serial, "shell", "getprop", "ro.product.model"])
        if out:
            details["model_name"] = out

        # Android Version
        _, out, _ = self.run_cmd(["-s", serial, "shell", "getprop", "ro.build.version.release"])
        if out:
            details["android_version"] = out

        # Battery
        _, out, _ = self.run_cmd(["-s", serial, "shell", "dumpsys", "battery"])
        if out:
            for line in out.splitlines():
                if "level:" in line:
                    details["battery_level"] = int(line.split(":")[-1].strip())
                if "AC powered: true" in line or "USB powered: true" in line:
                    details["battery_charging"] = True

        # Storage (/sdcard)
        _, out, _ = self.run_cmd(["-s", serial, "shell", "df", "-h", "/sdcard"])
        if out:
            lines = out.strip().splitlines()
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 4:
                    details["storage_total"] = parts[1]
                    details["storage_free"] = parts[3]

        # Wi-Fi IP
        _, out, _ = self.run_cmd(["-s", serial, "shell", "ip", "-f", "inet", "addr", "show", "wlan0"])
        if out:
            m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", out)
            if m:
                details["wifi_ip"] = m.group(1)

        return details

    def pair_device(self, ip: str, port: str, pin: str) -> Tuple[bool, str]:
        """
        Executes `adb pair <ip>:<port> <pin>`
        """
        target = f"{ip}:{port}"
        # We can pass PIN as argument to adb pair: `adb pair ip:port pin`
        code, out, err = self.run_cmd(["pair", target, pin], timeout=20)
        output = f"{out}\n{err}".strip()
        if "Successfully paired to" in output or code == 0:
            return True, output or f"Successfully paired to {target}"
        return False, output or "Pairing failed"

    def connect_device(self, ip: str, port: str = "5555") -> Tuple[bool, str]:
        """
        Executes `adb connect <ip>:<port>`
        """
        target = f"{ip}:{port}"
        code, out, err = self.run_cmd(["connect", target], timeout=15)
        output = f"{out}\n{err}".strip()
        if "connected to" in output.lower() and "cannot connect" not in output.lower():
            return True, output
        return False, output

    def disconnect_device(self, target: str) -> Tuple[bool, str]:
        code, out, err = self.run_cmd(["disconnect", target])
        return code == 0, f"{out}\n{err}".strip()

    def switch_usb_to_wireless(self, usb_serial: str, port: int = 5555) -> Tuple[bool, str, str]:
        """
        Enables TCPIP on a USB device and attempts wireless connection.
        Returns (success, message, wifi_ip)
        """
        # Step 1: Get WiFi IP
        details = self.get_device_details(usb_serial)
        wifi_ip = details.get("wifi_ip")
        if not wifi_ip:
            # Fallback check
            _, out, _ = self.run_cmd(["-s", usb_serial, "shell", "ip", "route"])
            m = re.search(r"src\s+(\d+\.\d+\.\d+\.\d+)", out)
            if m:
                wifi_ip = m.group(1)

        if not wifi_ip:
            return False, "Perangkat tidak memiliki IP Wi-Fi yang aktif. Pastikan HP terhubung ke Wi-Fi.", ""

        # Step 2: Enable TCPIP
        code, out, err = self.run_cmd(["-s", usb_serial, "tcpip", str(port)])
        if code != 0:
            return False, f"Gagal mengaktifkan mode TCP/IP: {out} {err}", wifi_ip

        # Step 3: Connect via Wi-Fi
        ok, msg = self.connect_device(wifi_ip, str(port))
        if ok:
            return True, f"Berhasil beralih ke nirkabel! Sekarang Anda dapat mencabut kabel USB. (Koneksi: {wifi_ip}:{port})", wifi_ip
        return False, f"TCP/IP aktif, tetapi gagal terhubung via Wi-Fi: {msg}", wifi_ip

    def list_files(self, serial: str, remote_path: str = "/sdcard") -> List[Dict]:
        """
        Lists files and directories at remote_path
        """
        if not remote_path.endswith("/"):
            remote_path += "/"
        
        # Use ls -la -p to identify directories easily
        code, out, _ = self.run_cmd(["-s", serial, "shell", "ls", "-la", remote_path])
        items = []
        if code != 0 or not out:
            return items

        for line in out.splitlines():
            line = line.strip()
            if not line or line.startswith("total"):
                continue

            parts = line.split(maxsplit=7)
            if len(parts) >= 8:
                perms = parts[0]
                size_str = parts[4]
                date_str = f"{parts[5]} {parts[6]}"
                name = parts[7]
                
                if name in [".", ".."]:
                    continue

                is_dir = perms.startswith("d")
                items.append({
                    "name": name,
                    "is_dir": is_dir,
                    "size": int(size_str) if size_str.isdigit() else 0,
                    "date": date_str,
                    "path": f"{remote_path}{name}".replace("//", "/")
                })
        
        # Sort folders first, then files
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return items

    def make_dir(self, serial: str, remote_path: str) -> Tuple[bool, str]:
        code, out, err = self.run_cmd(["-s", serial, "shell", "mkdir", "-p", remote_path])
        return code == 0, f"{out}\n{err}".strip()

    def scan_media_file(self, serial: str, remote_file: str):
        """Notifies Android MediaScanner so new pictures/videos/audio appear in Gallery immediately."""
        self.run_cmd(["-s", serial, "shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{remote_file}"])

    def push_file(self, serial: str, local_file: str, remote_dest: str, timeout: int = 600) -> Tuple[bool, str]:
        code, out, err = self.run_cmd(["-s", serial, "push", local_file, remote_dest], timeout=timeout)
        output = f"{out}\n{err}".strip()
        if code == 0:
            # Trigger media scanner for common media files
            target_name = os.path.basename(local_file)
            target_remote = f"{remote_dest.rstrip('/')}/{target_name}"
            self.scan_media_file(serial, target_remote)
        return code == 0, output

    def pull_file(self, serial: str, remote_file: str, local_dest: str, timeout: int = 600) -> Tuple[bool, str]:
        code, out, err = self.run_cmd(["-s", serial, "pull", remote_file, local_dest], timeout=timeout)
        output = f"{out}\n{err}".strip()
        return code == 0, output

    def delete_remote_item(self, serial: str, remote_path: str) -> Tuple[bool, str]:
        code, out, err = self.run_cmd(["-s", serial, "shell", "rm", "-rf", remote_path])
        return code == 0, f"{out}\n{err}".strip()

    def install_apk(self, serial: str, apk_path: str) -> Tuple[bool, str]:
        code, out, err = self.run_cmd(["-s", serial, "install", "-r", "-d", apk_path], timeout=180)
        output = f"{out}\n{err}".strip()
        return "Success" in output, output

    def launch_scrcpy(self, serial: str) -> Tuple[bool, str]:
        if not self.scrcpy_path:
            return False, "scrcpy belum terinstall. Install dengan 'brew install scrcpy'."
        
        try:
            # Run scrcpy in detached background process
            subprocess.Popen([self.scrcpy_path, "-s", serial, "--stay-awake"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, "scrcpy berhasil diluncurkan!"
        except Exception as e:
            return False, f"Gagal menjalankan scrcpy: {e}"

    def reverse_port(self, serial: str, device_port: int, host_port: int) -> Tuple[bool, str]:
        code, out, err = self.run_cmd(["-s", serial, "reverse", f"tcp:{device_port}", f"tcp:{host_port}"])
        return code == 0, f"{out}\n{err}".strip()

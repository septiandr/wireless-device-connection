import cgi
import http.server
import json
import os
import socketserver
import tempfile
import urllib.parse
import webbrowser
from typing import Optional
from core.adb_manager import ADBManager

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
adb = ADBManager()

class WirelessServerHandler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, message: str, status: int = 400):
        self._send_json({"success": False, "error": message}, status)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        # Static files
        if path == "/" or path == "/index.html":
            return self._serve_file(os.path.join(STATIC_DIR, "index.html"), "text/html")
        elif path == "/app.js":
            return self._serve_file(os.path.join(STATIC_DIR, "app.js"), "application/javascript")
        elif path == "/style.css":
            return self._serve_file(os.path.join(STATIC_DIR, "style.css"), "text/css")

        # API: Status & Devices
        if path == "/api/status":
            attached = adb.get_attached_devices()
            # Enrich attached devices with battery & details
            enriched = []
            for d in attached:
                details = adb.get_device_details(d["serial"])
                enriched.append({**d, **details})

            mdns_svcs = adb.get_mdns_services()
            return self._send_json({
                "adb_path": adb.adb_path,
                "scrcpy_available": bool(adb.scrcpy_path),
                "attached_devices": enriched,
                "mdns_services": mdns_svcs
            })

        # API: File List
        if path == "/api/files":
            serial = params.get("serial", [""])[0]
            remote_path = params.get("path", ["/sdcard"])[0]
            if not serial:
                return self._send_error("Missing serial parameter")
            items = adb.list_files(serial, remote_path)
            return self._send_json({"path": remote_path, "items": items})

        # API: Download File
        if path == "/api/files/download":
            serial = params.get("serial", [""])[0]
            remote_path = params.get("path", [""])[0]
            if not serial or not remote_path:
                return self._send_error("Missing serial or path")

            filename = os.path.basename(remote_path)
            temp_file = os.path.join(tempfile.gettempdir(), f"adb_dl_{filename}")
            ok, msg = adb.pull_file(serial, remote_path, temp_file)
            if not ok or not os.path.exists(temp_file):
                return self._send_error(f"Download failed: {msg}")

            file_size = os.path.getsize(temp_file)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(file_size))
            self.end_headers()
            with open(temp_file, "rb") as f:
                while chunk := f.read(64 * 1024):
                    self.wfile.write(chunk)
            try:
                os.remove(temp_file)
            except Exception:
                pass
            return

        # API: Logcat snippet
        if path == "/api/logcat":
            serial = params.get("serial", [""])[0]
            filter_str = params.get("filter", [""])[0]
            if not serial:
                return self._send_error("Missing serial parameter")
            code, out, _ = adb.run_cmd(["-s", serial, "logcat", "-d", "-t", "100"])
            lines = out.splitlines() if code == 0 else []
            if filter_str:
                lines = [l for l in lines if filter_str.lower() in l.lower()]
            return self._send_json({"logs": lines})

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Handle multipart upload for files / apk
        if path in ["/api/files/upload", "/api/install-apk"]:
            return self._handle_multipart_upload(path)

        # Handle JSON payloads
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            data = json.loads(body)
        except Exception:
            data = {}

        if path == "/api/connect":
            ip = data.get("ip", "").strip()
            port = str(data.get("port", "5555")).strip()
            if not ip:
                return self._send_error("IP address is required")
            ok, msg = adb.connect_device(ip, port)
            return self._send_json({"success": ok, "message": msg})

        if path == "/api/pair":
            ip = data.get("ip", "").strip()
            port = str(data.get("port", "")).strip()
            pin = str(data.get("pin", "")).strip()
            if not ip or not port or not pin:
                return self._send_error("IP, port, and PIN are required")
            ok, msg = adb.pair_device(ip, port, pin)
            return self._send_json({"success": ok, "message": msg})

        if path == "/api/disconnect":
            serial = data.get("serial", "").strip()
            if not serial:
                ok, msg = adb.run_cmd(["disconnect"])
                return self._send_json({"success": ok == 0, "message": msg or "All disconnected"})
            ok, msg = adb.disconnect_device(serial)
            return self._send_json({"success": ok, "message": msg})

        if path == "/api/switch-usb":
            serial = data.get("serial", "").strip()
            if not serial:
                return self._send_error("Serial is required")
            ok, msg, wifi_ip = adb.switch_usb_to_wireless(serial)
            return self._send_json({"success": ok, "message": msg, "wifi_ip": wifi_ip})

        if path == "/api/scrcpy":
            serial = data.get("serial", "").strip()
            if not serial:
                return self._send_error("Serial is required")
            ok, msg = adb.launch_scrcpy(serial)
            return self._send_json({"success": ok, "message": msg})

        if path == "/api/reverse":
            serial = data.get("serial", "").strip()
            port = int(data.get("port", 3000))
            if not serial:
                return self._send_error("Serial is required")
            ok, msg = adb.reverse_port(serial, port, port)
            return self._send_json({"success": ok, "message": msg or f"Port {port} forwarded"})

        if path == "/api/files/mkdir":
            serial = data.get("serial", "").strip()
            folder_path = data.get("path", "").strip()
            if not serial or not folder_path:
                return self._send_error("Serial and path are required")
            ok, msg = adb.make_dir(serial, folder_path)
            return self._send_json({"success": ok, "message": msg or "Folder berhasil dibuat"})

        if path == "/api/files/delete":
            serial = data.get("serial", "").strip()
            target_path = data.get("path", "").strip()
            if not serial or not target_path:
                return self._send_error("Serial and path are required")
            ok, msg = adb.delete_remote_item(serial, target_path)
            return self._send_json({"success": ok, "message": msg})

        self.send_error(404, "Not Found")

    def _handle_multipart_upload(self, path: str):
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            return self._send_error("Content-Type must be multipart/form-data")

        # Parse multipart form data
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type}
        )

        serial = form.getvalue("serial", "")
        if not serial:
            return self._send_error("Device serial is required")

        if "file" not in form:
            return self._send_error("No file was uploaded")

        file_item = form["file"]
        if not file_item.file:
            return self._send_error("File data is empty")

        filename = os.path.basename(file_item.filename or "upload.bin")
        temp_dest = os.path.join(tempfile.gettempdir(), f"upload_{filename}")
        with open(temp_dest, "wb") as f:
            shutil.copyfileobj(file_item.file, f)

        if path == "/api/install-apk":
            ok, msg = adb.install_apk(serial, temp_dest)
            try:
                os.remove(temp_dest)
            except Exception:
                pass
            return self._send_json({"success": ok, "message": msg})

        # File upload to remote dir
        remote_dest = form.getvalue("remote_path", "/sdcard/Download")
        dest_path = f"{remote_dest.rstrip('/')}/{filename}"
        ok, msg = adb.push_file(serial, temp_dest, dest_path)
        try:
            os.remove(temp_dest)
        except Exception:
            pass
        return self._send_json({"success": ok, "message": msg, "destination": dest_path})

    def _serve_file(self, filepath: str, content_type: str):
        if not os.path.exists(filepath):
            return self.send_error(404, "File Not Found")
        with open(filepath, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        # Mute normal HTTP access logs for clean console
        pass

def run_server(host: str = "127.0.0.1", port: int = 8080, open_browser: bool = True):
    server = socketserver.TCPServer((host, port), WirelessServerHandler)
    url = f"http://{host}:{port}"
    print(f"\n🚀 Web Dashboard siap di: \033[1;32m{url}\033[0m")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMenutup server...")
        server.server_close()

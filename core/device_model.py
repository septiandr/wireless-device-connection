import json
import os
from typing import Dict, List, Optional

CONFIG_DIR = os.path.expanduser("~/.config/wireless_device_manager")
CONFIG_FILE = os.path.join(CONFIG_DIR, "devices.json")

class DeviceInfo:
    def __init__(self, serial: str, model: str = "Unknown", ip: str = "", port: int = 5555, 
                 connected: bool = False, is_wireless: bool = True, battery: int = -1, 
                 android_version: str = "", paired: bool = False):
        self.serial = serial
        self.model = model
        self.ip = ip
        self.port = port
        self.connected = connected
        self.is_wireless = is_wireless
        self.battery = battery
        self.android_version = android_version
        self.paired = paired

    def to_dict(self) -> dict:
        return {
            "serial": self.serial,
            "model": self.model,
            "ip": self.ip,
            "port": self.port,
            "connected": self.connected,
            "is_wireless": self.is_wireless,
            "battery": self.battery,
            "android_version": self.android_version,
            "paired": self.paired
        }

class DeviceStorage:
    @staticmethod
    def _ensure_dir():
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR, exist_ok=True)

    @classmethod
    def load_saved_devices(cls) -> List[dict]:
        cls._ensure_dir()
        if not os.path.exists(CONFIG_FILE):
            return []
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f).get("devices", [])
        except Exception:
            return []

    @classmethod
    def save_device(cls, device_data: dict):
        cls._ensure_dir()
        devices = cls.load_saved_devices()
        # Update existing or add new
        updated = False
        for i, d in enumerate(devices):
            if d.get("serial") == device_data.get("serial") or (d.get("ip") and d.get("ip") == device_data.get("ip")):
                devices[i] = {**d, **device_data}
                updated = True
                break
        if not updated:
            devices.append(device_data)

        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"devices": devices}, f, indent=2)
        except Exception as e:
            print(f"Error saving device config: {e}")

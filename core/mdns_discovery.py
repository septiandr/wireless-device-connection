import threading
import time
from typing import Callable, Dict, List
from core.adb_manager import ADBManager

class MDNSDiscovery:
    def __init__(self, adb_manager: ADBManager, on_device_discovered: Callable[[Dict], None] = None):
        self.adb = adb_manager
        self.on_device_discovered = on_device_discovered
        self._running = False
        self._thread = None
        self._discovered_services: Dict[str, Dict] = {}

    def get_services(self) -> List[Dict]:
        return list(self._discovered_services.values())

    def start(self, interval: int = 4):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _monitor_loop(self, interval: int):
        while self._running:
            try:
                services = self.adb.get_mdns_services()
                for svc in services:
                    key = f"{svc['service_name']}:{svc['service_type']}"
                    is_new = key not in self._discovered_services
                    self._discovered_services[key] = svc
                    if is_new and self.on_device_discovered:
                        self.on_device_discovered(svc)
            except Exception as e:
                pass
            time.sleep(interval)

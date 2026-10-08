let currentSelectedDevice = null;
let currentPath = "/sdcard";
let activeTab = "files";

// Initial load
document.addEventListener("DOMContentLoaded", () => {
    refreshData();
    setInterval(refreshData, 3500); // 3.5s periodic polling
    setupDragAndDrop();
});

function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    const colors = {
        success: "bg-emerald-900/90 border-emerald-500/50 text-emerald-200",
        error: "bg-rose-900/90 border-rose-500/50 text-rose-200",
        info: "bg-blue-900/90 border-blue-500/50 text-blue-200"
    };

    toast.className = `px-4 py-3 rounded-xl border shadow-2xl text-xs flex items-center gap-2.5 transition-all transform duration-300 translate-y-2 opacity-0 ${colors[type] || colors.info}`;
    toast.innerHTML = `
        <span class="font-medium">${message}</span>
    `;

    container.appendChild(toast);
    requestAnimationFrame(() => {
        toast.classList.remove("translate-y-2", "opacity-0");
    });

    setTimeout(() => {
        toast.classList.add("translate-y-2", "opacity-0");
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

async function refreshData() {
    const icon = document.getElementById("refreshIcon");
    if (icon) icon.classList.add("animate-spin");

    try {
        const res = await fetch("/api/status");
        const data = await res.json();

        // Update badges
        document.getElementById("scrcpyStatusBadge").classList.toggle("hidden", !data.scrcpy_available);

        renderDiscoveredMDNS(data.mdns_services || []);
        renderConnectedDevices(data.attached_devices || []);
    } catch (err) {
        console.error("Failed to fetch status:", err);
    } finally {
        if (icon) setTimeout(() => icon.classList.remove("animate-spin"), 500);
    }
}

function renderDiscoveredMDNS(services) {
    const container = document.getElementById("mdnsDiscoveredList");
    if (!services || services.length === 0) {
        container.classList.add("hidden");
        container.innerHTML = "";
        return;
    }

    container.classList.remove("hidden");
    container.innerHTML = services.map(svc => {
        const isPairing = svc.service_type.includes("_adb-tls-pairing");
        const actionBtn = isPairing
            ? `<button onclick="openPairModalWithPrefill('${svc.ip}', '${svc.port}')" class="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center gap-1">Pairing</button>`
            : `<button onclick="quickConnect('${svc.ip}', '${svc.port}')" class="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center gap-1">Connect</button>`;

        return `
            <div class="bg-gray-900/80 border border-gray-700/80 rounded-xl p-3 flex items-center justify-between">
                <div>
                    <div class="text-xs font-semibold text-white flex items-center gap-1.5">
                        <span class="w-2 h-2 rounded-full ${isPairing ? 'bg-amber-400' : 'bg-emerald-400'}"></span>
                        <span>${svc.service_name}</span>
                    </div>
                    <div class="text-[11px] font-mono text-gray-400 mt-0.5">${svc.ip}:${svc.port}</div>
                </div>
                ${actionBtn}
            </div>
        `;
    }).join("");
}

function renderConnectedDevices(devices) {
    const container = document.getElementById("devicesContainer");
    const noPlaceholder = document.getElementById("noDevicesPlaceholder");
    const countBadge = document.getElementById("connectedCount");

    countBadge.textContent = devices.length;

    if (devices.length === 0) {
        container.innerHTML = "";
        noPlaceholder.classList.remove("hidden");
        document.getElementById("activeDevicePanel").classList.add("hidden");
        currentSelectedDevice = null;
        return;
    }

    noPlaceholder.classList.add("hidden");

    // Auto-select first device if none selected
    if (!currentSelectedDevice || !devices.some(d => d.serial === currentSelectedDevice)) {
        currentSelectedDevice = devices[0].serial;
        selectDevice(currentSelectedDevice, devices[0].model);
    }

    container.innerHTML = devices.map(dev => {
        const isSelected = dev.serial === currentSelectedDevice;
        const isWireless = dev.is_wireless;
        const battLevel = dev.battery_level >= 0 ? `${dev.battery_level}%` : "--";
        const battColor = dev.battery_level > 20 ? "text-emerald-400" : "text-rose-400";
        const ipDisplay = dev.wifi_ip || dev.ip || (isWireless ? "Wireless" : "USB Connected");

        return `
            <div class="border rounded-2xl p-4 transition-all ${isSelected ? 'bg-gray-800/90 border-blue-500 shadow-lg shadow-blue-500/10' : 'bg-dark-800/70 border-gray-800 hover:border-gray-700'}">
                <div class="flex items-start justify-between">
                    <div>
                        <div class="flex items-center gap-2">
                            <h3 class="font-bold text-sm text-white">${dev.model_name || dev.model}</h3>
                            <span class="text-[10px] px-2 py-0.5 rounded-full ${isWireless ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'}">
                                ${isWireless ? '📶 Wi-Fi' : '🔌 USB'}
                            </span>
                        </div>
                        <p class="text-[11px] font-mono text-gray-400 mt-1">${ipDisplay}</p>
                    </div>

                    <!-- Battery Pill -->
                    <div class="flex items-center gap-1 text-xs px-2 py-1 rounded-lg bg-gray-900 border border-gray-800 font-mono ${battColor}">
                        <i data-lucide="${dev.battery_charging ? 'zap' : 'battery'}" class="w-3.5 h-3.5"></i>
                        <span>${battLevel}</span>
                    </div>
                </div>

                <!-- Storage Info -->
                ${dev.storage_total ? `
                    <div class="mt-3 text-[11px] text-gray-400 flex items-center justify-between border-t border-gray-800 pt-2 font-mono">
                        <span>Penyimpanan:</span>
                        <span>Sisa ${dev.storage_free} / ${dev.storage_total}</span>
                    </div>
                ` : ''}

                <!-- Quick Action Buttons -->
                <div class="mt-4 pt-3 border-t border-gray-800 grid grid-cols-2 gap-2 text-xs">
                    <button onclick="selectDevice('${dev.serial}', '${dev.model}')" class="py-1.5 px-3 rounded-lg bg-blue-600/20 hover:bg-blue-600 text-blue-300 hover:text-white font-medium transition flex items-center justify-center gap-1.5">
                        <i data-lucide="folder" class="w-3.5 h-3.5"></i>
                        <span>File Explorer</span>
                    </button>
                    <button onclick="launchScrcpy('${dev.serial}')" class="py-1.5 px-3 rounded-lg bg-indigo-600/20 hover:bg-indigo-600 text-indigo-300 hover:text-white font-medium transition flex items-center justify-center gap-1.5">
                        <i data-lucide="cast" class="w-3.5 h-3.5"></i>
                        <span>Mirror Layar</span>
                    </button>
                </div>

                <!-- Secondary actions (Reverse / Switch USB / Disconnect) -->
                <div class="mt-2 flex items-center justify-between text-[11px] text-gray-400 pt-2 border-t border-gray-800/60">
                    <button onclick="reversePort('${dev.serial}')" class="hover:text-blue-400 flex items-center gap-1 transition">
                        <i data-lucide="repeat" class="w-3 h-3"></i>
                        <span>Reverse 3000</span>
                    </button>

                    ${!isWireless ? `
                        <button onclick="switchUSB('${dev.serial}')" class="text-amber-400 hover:text-amber-300 font-medium transition">
                            Switch ke Wi-Fi
                        </button>
                    ` : `
                        <button onclick="disconnectDevice('${dev.serial}')" class="text-rose-400 hover:text-rose-300 transition">
                            Putuskan
                        </button>
                    `}
                </div>
            </div>
        `;
    }).join("");

    lucide.createIcons();
}

function selectDevice(serial, model) {
    currentSelectedDevice = serial;
    document.getElementById("activeDevicePanel").classList.remove("hidden");
    document.getElementById("activeDeviceLabel").textContent = `${model} (${serial})`;
    loadFiles(currentPath);
}

// Quick Connect
async function quickConnect(ip, port) {
    showToast(`Menghubungkan ke ${ip}:${port}...`, "info");
    try {
        const res = await fetch("/api/connect", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ip, port })
        });
        const data = await res.json();
        if (data.success) {
            showToast("Berhasil terhubung!", "success");
            refreshData();
        } else {
            showToast(`Gagal: ${data.message}`, "error");
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, "error");
    }
}

// Disconnect
async function disconnectDevice(serial) {
    try {
        const res = await fetch("/api/disconnect", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ serial })
        });
        const data = await res.json();
        showToast(data.message, data.success ? "success" : "error");
        refreshData();
    } catch (e) {
        showToast(`Error: ${e.message}`, "error");
    }
}

// Switch USB to WiFi
async function switchUSB(serial) {
    showToast("Mengalihkan perangkat USB ke TCP/IP mode...", "info");
    try {
        const res = await fetch("/api/switch-usb", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ serial })
        });
        const data = await res.json();
        if (data.success) {
            showToast("Berhasil beralih ke nirkabel! Kabel USB sudah bisa dicabut.", "success");
            refreshData();
        } else {
            showToast(`Gagal: ${data.message}`, "error");
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, "error");
    }
}

// Launch Scrcpy
async function launchScrcpy(serial) {
    showToast("Meluncurkan screen mirroring (scrcpy)...", "info");
    try {
        const res = await fetch("/api/scrcpy", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ serial })
        });
        const data = await res.json();
        showToast(data.message, data.success ? "success" : "error");
    } catch (e) {
        showToast(`Error: ${e.message}`, "error");
    }
}

// Reverse Port (e.g. 3000 -> 3000)
async function reversePort(serial) {
    const port = prompt("Masukkan port host untuk di-reverse ke HP (contoh: 3000 untuk dev server):", "3000");
    if (!port) return;
    try {
        const res = await fetch("/api/reverse", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ serial, port: parseInt(port) })
        });
        const data = await res.json();
        showToast(`Port ${port} berhasil di-forward: localhost:${port} di HP mengarah ke Mac!`, "success");
    } catch (e) {
        showToast(`Error: ${e.message}`, "error");
    }
}

// Files Navigation
async function loadFiles(path) {
    if (!currentSelectedDevice) return;
    currentPath = path;
    updateBreadcrumb(path);

    const tbody = document.getElementById("fileListBody");
    tbody.innerHTML = `<tr><td colspan="4" class="text-center py-6 text-gray-500">Memuat berkas...</td></tr>`;

    try {
        const res = await fetch(`/api/files?serial=${encodeURIComponent(currentSelectedDevice)}&path=${encodeURIComponent(path)}`);
        const data = await res.json();
        const items = data.items || [];

        if (items.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center py-6 text-gray-500">Folder kosong</td></tr>`;
            return;
        }

        tbody.innerHTML = items.map(item => {
            const isDir = item.is_dir;
            const sizeStr = isDir ? "-" : formatSize(item.size);
            const isApk = item.name.endsWith(".apk");

            return `
                <tr class="hover:bg-gray-800/60 transition">
                    <td class="py-2.5 px-3 flex items-center gap-2">
                        <i data-lucide="${isDir ? 'folder' : (isApk ? 'package' : 'file')}" class="w-4 h-4 ${isDir ? 'text-amber-400' : (isApk ? 'text-emerald-400' : 'text-gray-400')}"></i>
                        ${isDir ? `
                            <button onclick="loadFiles('${item.path}')" class="text-blue-400 hover:underline font-medium text-left truncate max-w-xs md:max-w-md">
                                ${item.name}
                            </button>
                        ` : `
                            <span class="text-gray-200 truncate max-w-xs md:max-w-md">${item.name}</span>
                        `}
                    </td>
                    <td class="py-2.5 px-3 text-gray-400 whitespace-nowrap">${sizeStr}</td>
                    <td class="py-2.5 px-3 text-gray-500 whitespace-nowrap">${item.date}</td>
                    <td class="py-2.5 px-3 text-right space-x-1 whitespace-nowrap">
                        ${!isDir ? `
                            <button onclick="downloadFile('${item.path}')" title="Download" class="p-1 rounded hover:bg-gray-700 text-blue-400">
                                <i data-lucide="download" class="w-3.5 h-3.5"></i>
                            </button>
                        ` : ''}
                        <button onclick="deleteFile('${item.path}')" title="Hapus" class="p-1 rounded hover:bg-gray-700 text-rose-400">
                            <i data-lucide="trash-2" class="w-3.5 h-3.5"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join("");

        lucide.createIcons();
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-center py-6 text-rose-400">Gagal memuat file: ${e.message}</td></tr>`;
    }
}

function updateBreadcrumb(path) {
    const container = document.getElementById("breadcrumbContainer");
    const parts = path.split("/").filter(Boolean);
    let cumulative = "";

    container.innerHTML = `
        <button onclick="loadFiles('/')" class="hover:text-blue-400">root</button>
        ${parts.map(p => {
            cumulative += "/" + p;
            const currentCum = cumulative;
            return `
                <span>/</span>
                <button onclick="loadFiles('${currentCum}')" class="hover:text-blue-400">${p}</button>
            `;
        }).join("")}
    `;
}

function formatSize(bytes) {
    if (!bytes || bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

// Download
function downloadFile(remotePath) {
    if (!currentSelectedDevice) return;
    showToast("Mengunduh berkas ke Mac Anda...", "info");
    const url = `/api/files/download?serial=${encodeURIComponent(currentSelectedDevice)}&path=${encodeURIComponent(remotePath)}`;
    window.location.href = url;
}

// Delete
async function deleteFile(remotePath) {
    if (!confirm(`Yakin ingin menghapus ${remotePath}?`)) return;
    try {
        const res = await fetch("/api/files/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ serial: currentSelectedDevice, path: remotePath })
        });
        const data = await res.json();
        showToast(data.message || "File berhasil dihapus", data.success ? "success" : "error");
        loadFiles(currentPath);
    } catch (e) {
        showToast(`Error: ${e.message}`, "error");
    }
}

// Create New Folder
async function createNewFolder() {
    if (!currentSelectedDevice) return;
    const folderName = prompt("Masukkan nama folder baru:");
    if (!folderName || !folderName.trim()) return;

    const targetPath = `${currentPath.rstrip ? currentPath.replace(/\/+$/, '') : currentPath}/${folderName.trim()}`;
    try {
        const res = await fetch("/api/files/mkdir", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ serial: currentSelectedDevice, path: targetPath })
        });
        const data = await res.json();
        showToast(data.message || "Folder berhasil dibuat!", data.success ? "success" : "error");
        loadFiles(currentPath);
    } catch (e) {
        showToast(`Gagal membuat folder: ${e.message}`, "error");
    }
}

// Upload file
async function handleFileUpload(event) {
    const files = event.target.files;
    if (!files || files.length === 0 || !currentSelectedDevice) return;
    for (let i = 0; i < files.length; i++) {
        await uploadFile(files[i]);
    }
    event.target.value = "";
}

async function uploadFile(file) {
    showToast(`Mengunggah ${file.name} ke ${currentPath}...`, "info");
    const formData = new FormData();
    formData.append("serial", currentSelectedDevice);
    formData.append("remote_path", currentPath);
    formData.append("file", file);

    const isApk = file.name.endsWith(".apk");
    const endpoint = isApk && confirm(`File ini adalah APK (${file.name}). Pasang (Install) langsung ke HP?`)
        ? "/api/install-apk"
        : "/api/files/upload";

    try {
        const res = await fetch(endpoint, {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        showToast(data.message || `Upload ${file.name} selesai!`, data.success ? "success" : "error");
        loadFiles(currentPath);
    } catch (e) {
        showToast(`Upload gagal: ${e.message}`, "error");
    }
}

// Drag & Drop
function setupDragAndDrop() {
    const dropZone = document.getElementById("dropZone");
    if (!dropZone) return;

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        }, false);
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            uploadFile(files[0]);
        }
    });
}

// Tabs
function switchTab(tab) {
    activeTab = tab;
    const tabFiles = document.getElementById("tabFiles");
    const tabLogcat = document.getElementById("tabLogcat");
    const filePanel = document.getElementById("fileExplorerTab");
    const logcatPanel = document.getElementById("logcatTab");

    if (tab === "files") {
        tabFiles.className = "py-3 text-blue-400 border-b-2 border-blue-500 flex items-center gap-2";
        tabLogcat.className = "py-3 text-gray-400 hover:text-gray-200 flex items-center gap-2";
        filePanel.classList.remove("hidden");
        logcatPanel.classList.add("hidden");
    } else {
        tabLogcat.className = "py-3 text-blue-400 border-b-2 border-blue-500 flex items-center gap-2";
        tabFiles.className = "py-3 text-gray-400 hover:text-gray-200 flex items-center gap-2";
        filePanel.classList.add("hidden");
        logcatPanel.classList.remove("hidden");
        fetchLogcat();
    }
}

// Logcat
async function fetchLogcat() {
    if (!currentSelectedDevice) return;
    const filter = document.getElementById("logcatFilter").value;
    const box = document.getElementById("logcatBox");

    try {
        const res = await fetch(`/api/logcat?serial=${encodeURIComponent(currentSelectedDevice)}&filter=${encodeURIComponent(filter)}`);
        const data = await res.json();
        const logs = data.logs || [];
        box.innerHTML = logs.map(l => `<div>${escapeHtml(l)}</div>`).join("");
        box.scrollTop = box.scrollHeight;
    } catch (e) {
        box.innerHTML = `<div class="text-rose-400">Gagal mengambil log: ${e.message}</div>`;
    }
}

function filterLogs() {
    fetchLogcat();
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.innerText = text;
    return div.innerHTML;
}

// Modals
function openPairModal() {
    document.getElementById("pairModal").classList.remove("hidden");
}

function openPairModalWithPrefill(ip, port) {
    document.getElementById("pairIp").value = ip;
    document.getElementById("pairPort").value = port;
    document.getElementById("pairModal").classList.remove("hidden");
    document.getElementById("pairPin").focus();
}

function closePairModal() {
    document.getElementById("pairModal").classList.add("hidden");
}

async function submitPairing() {
    const ip = document.getElementById("pairIp").value.trim();
    const port = document.getElementById("pairPort").value.trim();
    const pin = document.getElementById("pairPin").value.trim();

    if (!ip || !port || !pin) {
        showToast("Lengkapi IP, Port, dan PIN!", "error");
        return;
    }

    const btn = document.getElementById("pairBtn");
    btn.disabled = true;
    btn.textContent = "Memasangkan...";

    try {
        const res = await fetch("/api/pair", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ip, port, pin })
        });
        const data = await res.json();
        if (data.success) {
            showToast("Pairing berhasil! Silakan hubungkan (connect).", "success");
            closePairModal();
            refreshData();
        } else {
            showToast(`Gagal pair: ${data.message}`, "error");
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, "error");
    } finally {
        btn.disabled = false;
        btn.textContent = "Pasangkan (Pair)";
    }
}

function openManualConnectModal() {
    document.getElementById("manualConnectModal").classList.remove("hidden");
}

function closeManualConnectModal() {
    document.getElementById("manualConnectModal").classList.add("hidden");
}

async function submitManualConnect() {
    const ip = document.getElementById("manualIp").value.trim();
    const port = document.getElementById("manualPort").value.trim() || "5555";

    if (!ip) {
        showToast("Masukkan IP!", "error");
        return;
    }

    const btn = document.getElementById("connectBtn");
    btn.disabled = true;
    btn.textContent = "Menghubungkan...";

    try {
        const res = await fetch("/api/connect", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ip, port })
        });
        const data = await res.json();
        if (data.success) {
            showToast("Berhasil terhubung!", "success");
            closeManualConnectModal();
            refreshData();
        } else {
            showToast(`Gagal konek: ${data.message}`, "error");
        }
    } catch (e) {
        showToast(`Error: ${e.message}`, "error");
    } finally {
        btn.disabled = false;
        btn.textContent = "Hubungkan";
    }
}

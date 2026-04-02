import { app, BrowserWindow, ipcMain, shell } from 'electron';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import os from 'node:os';
import { execFileSync, spawn } from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const isDev = !app.isPackaged;

let mainWindow = null;
let lastCpuSnapshot = captureCpuSnapshot();

const defaultRuntimeSettings = {
  profile: 'balanced',
  cpuLimit: 55,
  gpuLimit: 60,
  memoryLimit: 50,
};


const applicationCatalog = [
  { id: 'app-vscode', key: 'vscode', name: 'VS Code', detail: 'Connected workspace editor', pathField: 'vscode_path' },
  { id: 'app-blender', key: 'blender', name: 'Blender', detail: '3D and asset creation layer', pathField: 'blender_path' },
  { id: 'app-unreal', key: 'unreal', name: 'Unreal Engine', detail: 'Real-time scene and game environment', pathField: 'unreal_engine_path' },
  { id: 'app-unity', key: 'unity', name: 'Unity', detail: 'Game editor and runtime workspace', pathField: 'unity_path' },
  { id: 'app-photoshop', key: 'photoshop', name: 'Photoshop', detail: 'Image editing and compositing', pathField: 'photoshop_path' },
  { id: 'app-davinci', key: 'davinci', name: 'DaVinci Resolve', detail: 'Video finishing and timeline work', pathField: 'davinci_resolve_path' },
  { id: 'app-premiere', key: 'premiere', name: 'Premiere Pro', detail: 'Timeline editing and media cuts', pathField: 'premiere_pro_path' },
  { id: 'app-aftereffects', key: 'aftereffects', name: 'After Effects', detail: 'Motion graphics and animation', pathField: 'after_effects_path' },
  { id: 'app-figma', key: 'figma', name: 'Figma', detail: 'Design workspace and review surface', pathField: 'figma_path' },
  { id: 'app-flstudio', key: 'flstudio', name: 'FL Studio', detail: 'Audio composition workspace', pathField: 'fl_studio_path' },
  { id: 'app-substance', key: 'substance', name: 'Substance Painter', detail: 'Material and texture authoring', pathField: 'substance_painter_path' },
];

function getUpdateManifestCandidates() {
  const appPath = app.getAppPath();
  const cwd = process.cwd();
  return [
    path.join(appPath, 'data', 'updates', 'update-manifest.json'),
    path.join(cwd, 'data', 'updates', 'update-manifest.json'),
    path.join(path.dirname(appPath), 'data', 'updates', 'update-manifest.json'),
  ];
}

function getUpdateManifestPath() {
  for (const candidate of getUpdateManifestCandidates()) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return getUpdateManifestCandidates()[0];
}

function getRuntimeSettingsPath() {
  return path.join(app.getPath('userData'), 'runtime-settings.json');
}

function getBackendSettingsCandidates() {
  const appPath = app.getAppPath();
  const cwd = process.cwd();
  return [
    path.join(appPath, 'data', 'settings', 'user_settings.json'),
    path.join(cwd, 'data', 'settings', 'user_settings.json'),
    path.join(path.dirname(appPath), 'data', 'settings', 'user_settings.json'),
  ];
}

function getSharedBackendSettingsPath() {
  for (const candidate of getBackendSettingsCandidates()) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return getBackendSettingsCandidates()[0];
}

function readRuntimeSettings() {
  try {
    const filePath = getRuntimeSettingsPath();
    if (fs.existsSync(filePath)) {
      const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8'));
      return { ...defaultRuntimeSettings, ...parsed };
    }

    const backendPath = getSharedBackendSettingsPath();
    if (fs.existsSync(backendPath)) {
      const backend = JSON.parse(fs.readFileSync(backendPath, 'utf8'));
      return {
        profile: 'balanced',
        cpuLimit: Number(backend.cpu_limit_percent ?? defaultRuntimeSettings.cpuLimit),
        gpuLimit: Number(backend.gpu_limit_percent ?? defaultRuntimeSettings.gpuLimit),
        memoryLimit: Number(backend.memory_limit_percent ?? defaultRuntimeSettings.memoryLimit),
      };
    }

    return { ...defaultRuntimeSettings };
  } catch {
    return { ...defaultRuntimeSettings };
  }
}

function mirrorRuntimeSettingsToBackend(nextSettings) {
  try {
    const backendPath = getSharedBackendSettingsPath();
    const payload = fs.existsSync(backendPath)
      ? JSON.parse(fs.readFileSync(backendPath, 'utf8'))
      : {};

    payload.cpu_limit_percent = nextSettings.cpuLimit;
    payload.gpu_limit_percent = nextSettings.gpuLimit;
    payload.memory_limit_percent = nextSettings.memoryLimit;

    fs.mkdirSync(path.dirname(backendPath), { recursive: true });
    fs.writeFileSync(backendPath, JSON.stringify(payload, null, 2), 'utf8');
  } catch {
    // Keep desktop settings working even if backend mirror is unavailable.
  }
}


function readBackendUserSettings() {
  try {
    const backendPath = getSharedBackendSettingsPath();
    if (!fs.existsSync(backendPath)) return {};
    return JSON.parse(fs.readFileSync(backendPath, 'utf8'));
  } catch {
    return {};
  }
}

function compareVersions(left, right) {
  const leftParts = String(left || '0.0.0').split('.').map((part) => Number.parseInt(part, 10) || 0);
  const rightParts = String(right || '0.0.0').split('.').map((part) => Number.parseInt(part, 10) || 0);
  const maxLength = Math.max(leftParts.length, rightParts.length);

  for (let index = 0; index < maxLength; index += 1) {
    const leftPart = leftParts[index] ?? 0;
    const rightPart = rightParts[index] ?? 0;
    if (leftPart > rightPart) return 1;
    if (leftPart < rightPart) return -1;
  }

  return 0;
}

function readUpdateManifest() {
  try {
    const manifestPath = getUpdateManifestPath();
    if (!fs.existsSync(manifestPath)) {
      return null;
    }

    const parsed = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    return {
      channel: String(parsed.channel || 'stable'),
      latestVersion: String(parsed.latestVersion || app.getVersion()),
      publishedAt: String(parsed.publishedAt || ''),
      downloadUrl: String(parsed.downloadUrl || '').trim(),
      entries: Array.isArray(parsed.entries) ? parsed.entries : [],
    };
  } catch {
    return null;
  }
}

function buildUpdateFeed() {
  const manifest = readUpdateManifest();
  const currentVersion = app.getVersion();
  const latestVersion = manifest?.latestVersion || currentVersion;
  const updateAvailable = compareVersions(latestVersion, currentVersion) > 0;

  return {
    currentVersion,
    latestVersion,
    publishedAt: manifest?.publishedAt || '',
    channel: manifest?.channel || 'stable',
    updateAvailable,
    downloadUrl: manifest?.downloadUrl || '',
    entries: manifest?.entries || [],
  };
}

function openUpdateDownload(downloadUrl) {
  const nextUrl = String(downloadUrl || '').trim();
  if (!nextUrl) {
    return { ok: false, message: 'Zatim neni publikovany zadny update balicek ke stazeni.' };
  }

  try {
    shell.openExternal(nextUrl);
    return { ok: true, message: 'Update download was opened in the default browser.' };
  } catch (error) {
    return { ok: false, message: `Update download could not be opened. ${error}` };
  }
}

function getApplicationsState() {
  const backend = readBackendUserSettings();
  return applicationCatalog.map((appDef) => {
    const configuredPath = String(backend[appDef.pathField] || '').trim();
    const pathExists = configuredPath ? fs.existsSync(configuredPath) : false;
    return {
      id: appDef.id,
      key: appDef.key,
      title: appDef.name,
      detail: appDef.detail,
      path: configuredPath,
      connected: pathExists,
      status: pathExists ? 'Connected' : configuredPath ? 'Path missing' : 'Not connected',
      ctaLabel: pathExists ? 'Open' : 'Setup required',
    };
  });
}

function updateApplicationPath(appKey, nextPath) {
  const appDef = applicationCatalog.find((item) => item.key === appKey);
  if (!appDef) {
    return { ok: false, message: 'Application could not be found.' };
  }

  try {
    const backendPath = getSharedBackendSettingsPath();
    const payload = fs.existsSync(backendPath)
      ? JSON.parse(fs.readFileSync(backendPath, 'utf8'))
      : {};
    payload[appDef.pathField] = String(nextPath || '').trim();
    fs.mkdirSync(path.dirname(backendPath), { recursive: true });
    fs.writeFileSync(backendPath, JSON.stringify(payload, null, 2), 'utf8');
    const updated = getApplicationsState().find((item) => item.key === appKey);
    return {
      ok: true,
      message: `${appDef.name} path saved.`,
      app: updated,
      apps: getApplicationsState(),
    };
  } catch (error) {
    return { ok: false, message: `${appDef.name} path could not be saved. ${error}` };
  }
}

function launchApplication(appKey) {
  const appState = getApplicationsState().find((item) => item.key === appKey);
  if (!appState) {
    return { ok: false, message: 'Application could not be found.' };
  }
  if (!appState.connected || !appState.path) {
    return { ok: false, message: `${appState.title} is not connected yet.` };
  }
  try {
    const child = spawn(appState.path, [], {
      detached: true,
      stdio: 'ignore',
      windowsHide: false,
    });
    child.unref();
    return { ok: true, message: `${appState.title} launched.`, app: appState };
  } catch (error) {
    return { ok: false, message: `${appState.title} failed to launch. ${error}` };
  }
}

function writeRuntimeSettings(nextSettings) {
  const normalized = { ...defaultRuntimeSettings, ...nextSettings };
  fs.writeFileSync(getRuntimeSettingsPath(), JSON.stringify(normalized, null, 2), 'utf8');
  mirrorRuntimeSettingsToBackend(normalized);
  return normalized;
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1600,
    height: 960,
    minWidth: 1240,
    minHeight: 760,
    show: false,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#060606',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
  });

  if (isDev) {
    mainWindow.loadURL('http://127.0.0.1:5173');
  } else {
    mainWindow.loadFile(path.join(app.getAppPath(), 'dist', 'index.html'));
  }
}

function captureCpuSnapshot() {
  const cpus = os.cpus();
  let idle = 0;
  let total = 0;

  for (const cpu of cpus) {
    idle += cpu.times.idle;
    total += cpu.times.user + cpu.times.nice + cpu.times.sys + cpu.times.irq + cpu.times.idle;
  }

  return { idle, total };
}

function readCpuUsagePercent() {
  const next = captureCpuSnapshot();
  const idleDiff = next.idle - lastCpuSnapshot.idle;
  const totalDiff = next.total - lastCpuSnapshot.total;
  lastCpuSnapshot = next;

  if (totalDiff <= 0) return 0;
  return Math.max(0, Math.min(100, Math.round((1 - idleDiff / totalDiff) * 100)));
}

function readPrimaryGpuInfo() {
  if (process.platform !== 'win32') return { name: 'Unavailable', vendor: 'unknown' };
  try {
    const raw = execFileSync(
      'powershell.exe',
      ['-NoProfile', '-Command', "$gpu = Get-CimInstance Win32_VideoController | Select-Object -First 1 Name, AdapterCompatibility; $gpu | ConvertTo-Json -Compress"],
      { encoding: 'utf8', windowsHide: true, timeout: 2500 },
    ).trim();
    const parsed = JSON.parse(raw);
    const name = String(parsed.Name || 'Unavailable').trim() || 'Unavailable';
    const compatibility = String(parsed.AdapterCompatibility || '').toLowerCase();
    let vendor = 'unknown';
    if (name.toLowerCase().includes('nvidia') || compatibility.includes('nvidia')) vendor = 'nvidia';
    else if (name.toLowerCase().includes('amd') || name.toLowerCase().includes('radeon') || compatibility.includes('advanced micro devices')) vendor = 'amd';
    else if (name.toLowerCase().includes('intel') || compatibility.includes('intel')) vendor = 'intel';
    return { name, vendor };
  } catch {
    return { name: 'Unavailable', vendor: 'unknown' };
  }
}

function readNvidiaGpuUsagePercent() {
  try {
    const raw = execFileSync(
      'nvidia-smi',
      ['--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
      { encoding: 'utf8', windowsHide: true, timeout: 2500 },
    ).trim().split(/\r?\n/).find(Boolean) || '';
    const parsed = Number(raw.trim());
    return Number.isFinite(parsed) ? Math.max(0, Math.min(100, Math.round(parsed))) : null;
  } catch {
    return null;
  }
}

function readWindowsGpuUsagePercent() {
  if (process.platform !== 'win32') return null;
  try {
    const script = [
      "$ErrorActionPreference = 'Stop'",
      "$samples = Get-Counter '\GPU Engine(*)\Utilization Percentage'",
      "$sum = ($samples.CounterSamples | Measure-Object -Property CookedValue -Sum).Sum",
      "if ($sum -eq $null) { '' } else { [math]::Round([double]$sum) }",
    ].join('; ');
    const raw = execFileSync('powershell.exe', ['-NoProfile', '-Command', script], {
      encoding: 'utf8',
      windowsHide: true,
      timeout: 3000,
    }).trim();
    if (!raw) return null;
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? Math.max(0, Math.min(100, parsed)) : null;
  } catch {
    return null;
  }
}

function readSystemMetrics() {
  const totalMemory = os.totalmem();
  const usedMemory = totalMemory - os.freemem();
  const gpuInfo = readPrimaryGpuInfo();
  const gpuUsagePercent = gpuInfo.vendor === 'nvidia' ? (readNvidiaGpuUsagePercent() ?? readWindowsGpuUsagePercent()) : readWindowsGpuUsagePercent();
  return {
    gpu: gpuInfo.name,
    gpuVendor: gpuInfo.vendor,
    cpuUsagePercent: readCpuUsagePercent(),
    gpuUsagePercent,
    memoryUsedGb: Math.max(0, Math.round(usedMemory / 1024 / 1024 / 1024)),
    memoryUsagePercent: Math.round((usedMemory / totalMemory) * 100),
  };
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

ipcMain.handle('window:minimize', () => {
  mainWindow?.minimize();
});

ipcMain.handle('window:maximize', () => {
  if (!mainWindow) return { maximized: false };
  if (mainWindow.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow.maximize();
  }
  return { maximized: mainWindow.isMaximized() };
});

ipcMain.handle('window:close', () => {
  mainWindow?.close();
});

ipcMain.handle('app:get-meta', () => {
  const metrics = readSystemMetrics();
  return {
    appName: 'LunaAI',
    version: app.getVersion(),
    platform: process.platform,
    deviceName: os.hostname(),
    os: `${os.type()} ${os.release()}`,
    arch: os.arch(),
    cpu: os.cpus()[0]?.model ?? 'Unknown CPU',
    gpu: metrics.gpu,
    gpuVendor: metrics.gpuVendor,
    cpuUsagePercent: metrics.cpuUsagePercent,
    gpuUsagePercent: metrics.gpuUsagePercent,
    memoryGb: Math.round(os.totalmem() / 1024 / 1024 / 1024),
    memoryUsedGb: metrics.memoryUsedGb,
    memoryUsagePercent: metrics.memoryUsagePercent,
    runtimeSettings: readRuntimeSettings(),
  };
});

ipcMain.handle('settings:get-runtime', () => {
  return readRuntimeSettings();
});

ipcMain.handle('settings:save-runtime', (_, nextSettings) => {
  return writeRuntimeSettings(nextSettings || {});
});

ipcMain.handle('apps:list', () => {
  return getApplicationsState();
});

ipcMain.handle('apps:update-path', (_, appKey, nextPath) => {
  return updateApplicationPath(String(appKey || ''), String(nextPath || ''));
});

ipcMain.handle('apps:launch', (_, appKey) => {
  return launchApplication(String(appKey || ''));
});

ipcMain.handle('updates:get-feed', () => {
  return buildUpdateFeed();
});

ipcMain.handle('updates:check', () => {
  return buildUpdateFeed();
});

ipcMain.handle('updates:download', (_, downloadUrl) => {
  const feed = buildUpdateFeed();
  return openUpdateDownload(String(downloadUrl || feed.downloadUrl || ''));
});

ipcMain.handle('luna:future-action', async (_, payload) => {
  return {
    ok: true,
    message: 'IPC bridge is ready for Luna backend integration.',
    payload,
  };
});

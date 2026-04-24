import { app, BrowserWindow, desktopCapturer, ipcMain, session } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import os from 'node:os';
import fs from 'node:fs/promises';

import { readRuntimeSettings, writeRuntimeSettings } from './services/runtimeSettings.js';
import { buildUpdateFeed, openUpdateDownload, prepareUpdateDownload, restartAndInstallUpdate } from './services/updates.js';
import { getApplicationsState, launchApplication, updateApplicationPath } from './services/applications.js';
import { runLunaBridge } from './services/lunaBridge.js';
import { createSystemMetricsReader } from './services/systemMetrics.js';
import { registerActionIpc } from './ipc/actionIpc.js';


const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const isDev = !app.isPackaged;

let mainWindow = null;
let pendingLunaAction = null;
let pendingScreenShareSourceId = '';
const readSystemMetrics = createSystemMetricsReader();

async function getScreenShareSources() {
  return desktopCapturer.getSources({
    types: ['screen', 'window'],
    thumbnailSize: { width: 640, height: 360 },
    fetchWindowIcons: true,
  });
}

function mapScreenShareSource(source) {
  return {
    id: source.id,
    name: source.name,
    kind: source.id.startsWith('screen:') ? 'screen' : 'window',
    thumbnailDataUrl: source.thumbnail && !source.thumbnail.isEmpty() ? source.thumbnail.toDataURL() : '',
    appIconDataUrl: source.appIcon && !source.appIcon.isEmpty() ? source.appIcon.toDataURL() : '',
  };
}

function pickScreenShareSource(sources) {
  const list = Array.isArray(sources) ? sources : [];
  const selected = list.find((source) => source.id === pendingScreenShareSourceId);
  if (selected) return selected;
  return list.find((source) => source.id.startsWith('screen:'))
    || list.find((source) => !/lunaai/i.test(source.name))
    || list[0]
    || null;
}


function mergePendingLunaAction(result) {
  if (!result || typeof result !== 'object') return result;
  if (pendingLunaAction) {
    return {
      ...result,
      pendingAction: {
        active: true,
        title: pendingLunaAction.title || 'Luna ceka na potvrzeni akce.',
      },
    };
  }
  return {
    ...result,
    pendingAction: {
      active: false,
      title: '',
      ...(result.pendingAction || {}),
    },
  };
}

async function runLunaChatAction(payload) {
  const result = await runLunaBridge(payload);
  const pendingTitle = String(result?.pendingAction?.title || '').trim();
  if (result?.ok && result?.pendingAction?.active) {
    pendingLunaAction = {
      payload,
      title: pendingTitle || String(result?.response || '').trim() || 'Luna ceka na potvrzeni akce.',
    };
  } else if (!result?.pendingAction?.active) {
    pendingLunaAction = null;
  }
  return mergePendingLunaAction(result);
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

app.whenReady().then(() => {
  session.defaultSession.setDisplayMediaRequestHandler(
    async (_request, callback) => {
      try {
        const sources = await getScreenShareSources();
        const source = pickScreenShareSource(sources);
        pendingScreenShareSourceId = '';

        if (!source) {
          callback({});
          return;
        }

        callback({ video: source });
      } catch {
        pendingScreenShareSourceId = '';
        callback({});
      }
    },
    { useSystemPicker: false },
  );

  registerActionIpc({
    ipcMain,
    getMainWindow: () => mainWindow,
  });

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

ipcMain.handle('files:read-as-data-url', async (_, filePath) => {
  const targetPath = String(filePath || '').trim();
  if (!targetPath) {
    return { ok: false, message: 'Missing file path.' };
  }

  try {
    const fileBuffer = await fs.readFile(targetPath);
    const extension = path.extname(targetPath).toLowerCase();
    const mimeByExtension = {
      '.png': 'image/png',
      '.jpg': 'image/jpeg',
      '.jpeg': 'image/jpeg',
      '.webp': 'image/webp',
      '.gif': 'image/gif',
    };
    const mime = mimeByExtension[extension] || 'application/octet-stream';
    return {
      ok: true,
      dataUrl: `data:${mime};base64,${fileBuffer.toString('base64')}`,
    };
  } catch (error) {
    return {
      ok: false,
      message: String(error),
    };
  }
});

ipcMain.handle('files:write-temp-data-url', async (_, payload) => {
  const dataUrl = String(payload?.dataUrl || '').trim();
  const extension = String(payload?.extension || 'png').trim().replace(/^\.+/, '').toLowerCase() || 'png';
  const previousPath = String(payload?.previousPath || '').trim();
  const tempRoot = path.join(app.getPath('userData'), 'stream-captures');

  if (!dataUrl.startsWith('data:')) {
    return { ok: false, message: 'Invalid data URL payload.' };
  }

  try {
    await fs.mkdir(tempRoot, { recursive: true });

    const [header, encoded] = dataUrl.split(',', 2);
    if (!header || !encoded) {
      return { ok: false, message: 'Malformed data URL.' };
    }

    const nextPath = path.join(tempRoot, `stream_${Date.now()}.${extension}`);
    const buffer = Buffer.from(encoded, 'base64');
    await fs.writeFile(nextPath, buffer);

    if (previousPath) {
      const normalizedPrevious = path.resolve(previousPath);
      if (normalizedPrevious.startsWith(path.resolve(tempRoot))) {
        await fs.unlink(normalizedPrevious).catch(() => {});
      }
    }

    return { ok: true, path: nextPath };
  } catch (error) {
    return { ok: false, message: String(error) };
  }
});

ipcMain.handle('screen-share:list-sources', async () => {
  try {
    const sources = await getScreenShareSources();
    return {
      ok: true,
      sources: sources
        .filter((source) => !/lunaai/i.test(source.name))
        .map(mapScreenShareSource),
    };
  } catch (error) {
    return {
      ok: false,
      message: String(error),
      sources: [],
    };
  }
});

ipcMain.handle('screen-share:select-source', async (_, sourceId) => {
  const nextSourceId = String(sourceId || '').trim();
  if (!nextSourceId) {
    pendingScreenShareSourceId = '';
    return { ok: false, message: 'Missing screen share source id.' };
  }

  pendingScreenShareSourceId = nextSourceId;
  return { ok: true };
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

ipcMain.handle('updates:prepare', () => {
  return prepareUpdateDownload();
});

ipcMain.handle('updates:restart-and-install', () => {
  return restartAndInstallUpdate();
});

ipcMain.handle('luna:get-state', async () => {
  return mergePendingLunaAction(await runLunaBridge({ action: 'state' }));
});

ipcMain.handle('luna:create-chat', async (_, title) => {
  pendingLunaAction = null;
  return mergePendingLunaAction(await runLunaBridge({ action: 'create_chat', title: String(title || 'New chat') }));
});

ipcMain.handle('luna:switch-chat', async (_, chatId) => {
  return mergePendingLunaAction(await runLunaBridge({ action: 'switch_chat', chatId: String(chatId || '') }));
});

ipcMain.handle('luna:rename-chat', async (_, chatId, title) => {
  return mergePendingLunaAction(await runLunaBridge({ action: 'rename_chat', chatId: String(chatId || ''), title: String(title || '') }));
});

ipcMain.handle('luna:delete-chat', async (_, chatId) => {
  pendingLunaAction = null;
  return mergePendingLunaAction(await runLunaBridge({ action: 'delete_chat', chatId: String(chatId || '') }));
});

ipcMain.handle('luna:send-message', async (_, payload) => {
  return await runLunaChatAction({ action: 'send_message', ...(payload || {}) });
});

ipcMain.handle('luna:observe-desktop', async (_, payload) => {
  return mergePendingLunaAction(await runLunaBridge({ action: 'observe_desktop', ...(payload || {}) }));
});

ipcMain.handle('luna:analyze-visual', async (_, payload) => {
  return mergePendingLunaAction(await runLunaBridge({ action: 'analyze_visual', ...(payload || {}) }));
});

ipcMain.handle('luna:set-observe-mode', async (_, enabled) => {
  return mergePendingLunaAction(await runLunaBridge({ action: 'set_observe_mode', enabled: Boolean(enabled) }));
});

ipcMain.handle('luna:confirm-pending-action', async () => {
  if (!pendingLunaAction?.payload) {
    return mergePendingLunaAction(await runLunaBridge({ action: 'state' }));
  }
  const replayPayload = { ...pendingLunaAction.payload, forceActionExecution: true };
  pendingLunaAction = null;
  return await runLunaChatAction({ action: 'send_message', ...replayPayload });
});

ipcMain.handle('luna:cancel-pending-action', async () => {
  pendingLunaAction = null;
  return mergePendingLunaAction(await runLunaBridge({ action: 'state' }));
});

ipcMain.handle('luna:future-action', async (_, payload) => {
  return {
    ok: true,
    message: 'IPC bridge is ready for Luna backend integration.',
    payload,
  };
});

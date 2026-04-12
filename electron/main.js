import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import os from 'node:os';

import { readRuntimeSettings, writeRuntimeSettings } from './services/runtimeSettings.js';
import { buildUpdateFeed, openUpdateDownload } from './services/updates.js';
import { getApplicationsState, launchApplication, updateApplicationPath } from './services/applications.js';
import { runLunaBridge } from './services/lunaBridge.js';
import { createSystemMetricsReader } from './services/systemMetrics.js';


const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const isDev = !app.isPackaged;

let mainWindow = null;
let pendingLunaAction = null;
const readSystemMetrics = createSystemMetricsReader();


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

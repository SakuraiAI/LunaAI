const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('lunaDesktop', {
  window: {
    minimize: () => ipcRenderer.invoke('window:minimize'),
    maximize: () => ipcRenderer.invoke('window:maximize'),
    close: () => ipcRenderer.invoke('window:close'),
  },
  app: {
    getMeta: () => ipcRenderer.invoke('app:get-meta'),
  },
  settings: {
    getRuntime: () => ipcRenderer.invoke('settings:get-runtime'),
    saveRuntime: (payload) => ipcRenderer.invoke('settings:save-runtime', payload),
  },
  apps: {
    list: () => ipcRenderer.invoke('apps:list'),
    updatePath: (appKey, nextPath) => ipcRenderer.invoke('apps:update-path', appKey, nextPath),
    launch: (appKey) => ipcRenderer.invoke('apps:launch', appKey),
  },
  updates: {
    getFeed: () => ipcRenderer.invoke('updates:get-feed'),
    check: () => ipcRenderer.invoke('updates:check'),
    download: (downloadUrl) => ipcRenderer.invoke('updates:download', downloadUrl),
  },
  luna: {
    futureAction: (payload) => ipcRenderer.invoke('luna:future-action', payload),
  },
});

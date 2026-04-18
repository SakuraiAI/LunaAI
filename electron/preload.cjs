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
  files: {
    readAsDataUrl: (filePath) => ipcRenderer.invoke('files:read-as-data-url', filePath),
    writeTempDataUrl: (payload) => ipcRenderer.invoke('files:write-temp-data-url', payload),
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
    getState: () => ipcRenderer.invoke('luna:get-state'),
    createChat: (title) => ipcRenderer.invoke('luna:create-chat', title),
    switchChat: (chatId) => ipcRenderer.invoke('luna:switch-chat', chatId),
    renameChat: (chatId, title) => ipcRenderer.invoke('luna:rename-chat', chatId, title),
    deleteChat: (chatId) => ipcRenderer.invoke('luna:delete-chat', chatId),
    sendMessage: (payload) => ipcRenderer.invoke('luna:send-message', payload),
    observeDesktop: (payload) => ipcRenderer.invoke('luna:observe-desktop', payload),
    analyzeVisual: (payload) => ipcRenderer.invoke('luna:analyze-visual', payload),
    setObserveMode: (enabled) => ipcRenderer.invoke('luna:set-observe-mode', enabled),
    confirmPendingAction: () => ipcRenderer.invoke('luna:confirm-pending-action'),
    cancelPendingAction: () => ipcRenderer.invoke('luna:cancel-pending-action'),
    futureAction: (payload) => ipcRenderer.invoke('luna:future-action', payload),
  },
});

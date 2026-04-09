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
    getState: () => ipcRenderer.invoke('luna:get-state'),
    createChat: (title) => ipcRenderer.invoke('luna:create-chat', title),
    switchChat: (chatId) => ipcRenderer.invoke('luna:switch-chat', chatId),
    renameChat: (chatId, title) => ipcRenderer.invoke('luna:rename-chat', chatId, title),
    deleteChat: (chatId) => ipcRenderer.invoke('luna:delete-chat', chatId),
    sendMessage: (payload) => ipcRenderer.invoke('luna:send-message', payload),
    futureAction: (payload) => ipcRenderer.invoke('luna:future-action', payload),
  },
});

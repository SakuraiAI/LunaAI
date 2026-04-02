import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('lunaDesktop', {
  window: {
    minimize: () => ipcRenderer.invoke('window:minimize'),
    maximize: () => ipcRenderer.invoke('window:maximize'),
    close: () => ipcRenderer.invoke('window:close'),
  },
  app: {
    getMeta: () => ipcRenderer.invoke('app:get-meta'),
  },
  luna: {
    futureAction: (payload) => ipcRenderer.invoke('luna:future-action', payload),
  },
});

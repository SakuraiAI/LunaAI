import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("screenShareAPI", {
    listSources: () => ipcRenderer.invoke("screen-share:list-sources"),
    selectSource: (sourceId) => ipcRenderer.invoke("screen-share:select-source", sourceId),
    clearSource: () => ipcRenderer.invoke("screen-share:clear-source"),
    actionEngine: {
        execute: (payload) => ipcRenderer.invoke("action-engine:execute", payload),
        onInternalAction: (handler) => {
            const listener = (_event, payload) => handler(payload);
            ipcRenderer.on("action-engine:internal-ui", listener);
            return () => ipcRenderer.removeListener("action-engine:internal-ui", listener);
        },
    },
});

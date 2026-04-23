import { app, BrowserWindow, desktopCapturer, ipcMain, session } from "electron";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { registerActionIpc } from "./ipc/actionIpc.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let selectedSourceId = null;
let mainWindow = null;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1440,
        height: 980,
        backgroundColor: "#111111",
        webPreferences: {
            preload: path.join(__dirname, "preload.js"),
            contextIsolation: true,
            nodeIntegration: false,
            sandbox: false,
        },
    });

    mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));
}

async function getAvailableSources() {
    const sources = await desktopCapturer.getSources({
        types: ["screen", "window"],
        fetchWindowIcons: true,
        thumbnailSize: { width: 480, height: 270 },
    });

    return sources.map((source) => ({
        id: source.id,
        name: source.name,
        thumbnail: source.thumbnail.isEmpty() ? "" : source.thumbnail.toDataURL(),
        appIcon: source.appIcon?.isEmpty() ? "" : source.appIcon.toDataURL(),
        kind: source.id.startsWith("screen:") ? "screen" : "window",
    }));
}

async function configureDisplayCapture() {
    session.defaultSession.setDisplayMediaRequestHandler(
        async (_request, callback) => {
            try {
                if (!selectedSourceId) {
                    callback({ video: null, audio: false });
                    return;
                }

                const sources = await desktopCapturer.getSources({
                    types: ["screen", "window"],
                    fetchWindowIcons: true,
                    thumbnailSize: { width: 1, height: 1 },
                });

                const source = sources.find((item) => item.id === selectedSourceId);
                callback({ video: source ?? null, audio: false });
            } catch (error) {
                console.error("Display media request failed:", error);
                callback({ video: null, audio: false });
            }
        },
        { useSystemPicker: false },
    );
}

app.whenReady().then(async () => {
    await configureDisplayCapture();
    createWindow();
    registerActionIpc({
        ipcMain,
        getMainWindow: () => mainWindow,
    });

    app.on("activate", () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
        app.quit();
    }
});

ipcMain.handle("screen-share:list-sources", async () => {
    return getAvailableSources();
});

ipcMain.handle("screen-share:select-source", async (_event, sourceId) => {
    selectedSourceId = typeof sourceId === "string" ? sourceId : null;
    return { ok: Boolean(selectedSourceId) };
});

ipcMain.handle("screen-share:clear-source", async () => {
    selectedSourceId = null;
    return { ok: true };
});

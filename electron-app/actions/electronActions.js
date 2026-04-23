export function createElectronActions({ getMainWindow }) {
    return {
        async execute(action, context = {}) {
            const mainWindow = getMainWindow();
            if (!mainWindow || mainWindow.isDestroyed()) {
                return {
                    ok: false,
                    executed: false,
                    message: "Main Electron window is not available.",
                };
            }

            mainWindow.webContents.send("action-engine:internal-ui", {
                action,
                context,
            });

            return {
                ok: true,
                executed: true,
                message: `Internal Electron action dispatched: ${action.type} -> ${action.target}`,
            };
        },
    };
}

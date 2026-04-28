import { createActionEngine } from '../actions/actionEngine.js';
import { createElectronActions } from '../actions/electronActions.js';
import { createSystemActions } from '../actions/systemActions.js';

export function registerActionIpc({ ipcMain, getMainWindow }) {
  const electronActions = createElectronActions({ getMainWindow });
  const systemActions = createSystemActions();
  const actionEngine = createActionEngine({ electronActions, systemActions });

  ipcMain.handle('action-engine:execute', async (_event, payload = {}) => {
    return actionEngine.execute(payload.action, payload.context || {});
  });

  ipcMain.handle('action-engine:get-pending', async () => {
    return {
      ok: true,
      pendingAction: actionEngine.getPendingAction(),
    };
  });

  ipcMain.handle('action-engine:confirm-pending', async () => {
    return actionEngine.confirmPendingAction();
  });

  ipcMain.handle('action-engine:cancel-pending', async () => {
    return actionEngine.cancelPendingAction();
  });

  return actionEngine;
}

import path from 'node:path';

import { createLocalPcActionAgent } from '../../app/agent/agent.js';

export function registerAgentIpc({ ipcMain }) {
  const workspaceRoot = process.cwd();
  const agent = createLocalPcActionAgent({
    workspaceRoot,
    appsConfigPath: path.join(workspaceRoot, 'config', 'apps.json'),
    logFilePath: path.join(workspaceRoot, 'data', 'logs', 'agent_actions.jsonl'),
  });

  ipcMain.handle('agent:execute', async (_event, payload = {}) => {
    return await agent.execute(payload);
  });

  return agent;
}

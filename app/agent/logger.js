import fs from 'node:fs/promises';
import path from 'node:path';

export function createAgentLogger(logFilePath) {
  const resolvedPath = path.resolve(logFilePath);

  async function log(entry) {
    const payload = {
      timestamp: new Date().toISOString(),
      ...entry,
    };
    await fs.mkdir(path.dirname(resolvedPath), { recursive: true });
    await fs.appendFile(resolvedPath, `${JSON.stringify(payload)}\n`, 'utf8');
  }

  return {
    log,
    path: resolvedPath,
  };
}

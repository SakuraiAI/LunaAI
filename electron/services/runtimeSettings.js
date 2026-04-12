import { app } from 'electron';
import path from 'node:path';
import fs from 'node:fs';

import { getSharedBackendSettingsPath } from './backendSettings.js';


export const defaultRuntimeSettings = {
  profile: 'balanced',
  cpuLimit: 55,
  gpuLimit: 60,
  memoryLimit: 50,
};

function getRuntimeSettingsPath() {
  return path.join(app.getPath('userData'), 'runtime-settings.json');
}

function mirrorRuntimeSettingsToBackend(nextSettings) {
  try {
    const backendPath = getSharedBackendSettingsPath();
    const payload = fs.existsSync(backendPath)
      ? JSON.parse(fs.readFileSync(backendPath, 'utf8'))
      : {};

    payload.cpu_limit_percent = nextSettings.cpuLimit;
    payload.gpu_limit_percent = nextSettings.gpuLimit;
    payload.memory_limit_percent = nextSettings.memoryLimit;

    fs.mkdirSync(path.dirname(backendPath), { recursive: true });
    fs.writeFileSync(backendPath, JSON.stringify(payload, null, 2), 'utf8');
  } catch {
    // Keep desktop settings working even if backend mirror is unavailable.
  }
}

export function readRuntimeSettings() {
  try {
    const filePath = getRuntimeSettingsPath();
    if (fs.existsSync(filePath)) {
      const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8'));
      return { ...defaultRuntimeSettings, ...parsed };
    }

    const backendPath = getSharedBackendSettingsPath();
    if (fs.existsSync(backendPath)) {
      const backend = JSON.parse(fs.readFileSync(backendPath, 'utf8'));
      return {
        profile: 'balanced',
        cpuLimit: Number(backend.cpu_limit_percent ?? defaultRuntimeSettings.cpuLimit),
        gpuLimit: Number(backend.gpu_limit_percent ?? defaultRuntimeSettings.gpuLimit),
        memoryLimit: Number(backend.memory_limit_percent ?? defaultRuntimeSettings.memoryLimit),
      };
    }

    return { ...defaultRuntimeSettings };
  } catch {
    return { ...defaultRuntimeSettings };
  }
}

export function writeRuntimeSettings(nextSettings) {
  const normalized = { ...defaultRuntimeSettings, ...nextSettings };
  fs.writeFileSync(getRuntimeSettingsPath(), JSON.stringify(normalized, null, 2), 'utf8');
  mirrorRuntimeSettingsToBackend(normalized);
  return normalized;
}


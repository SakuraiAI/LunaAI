import { app } from 'electron';
import path from 'node:path';
import fs from 'node:fs';


export function getBackendSettingsCandidates() {
  const appPath = app.getAppPath();
  const cwd = process.cwd();
  return [
    path.join(appPath, 'data', 'settings', 'user_settings.json'),
    path.join(cwd, 'data', 'settings', 'user_settings.json'),
    path.join(path.dirname(appPath), 'data', 'settings', 'user_settings.json'),
  ];
}

export function getSharedBackendSettingsPath() {
  for (const candidate of getBackendSettingsCandidates()) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return getBackendSettingsCandidates()[0];
}

export function readBackendUserSettings() {
  try {
    const backendPath = getSharedBackendSettingsPath();
    if (!fs.existsSync(backendPath)) return {};
    return JSON.parse(fs.readFileSync(backendPath, 'utf8'));
  } catch {
    return {};
  }
}


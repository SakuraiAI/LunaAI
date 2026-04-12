import { app, shell } from 'electron';
import path from 'node:path';
import fs from 'node:fs';


function getUpdateManifestCandidates() {
  const appPath = app.getAppPath();
  const cwd = process.cwd();
  return [
    path.join(appPath, 'data', 'updates', 'update-manifest.json'),
    path.join(cwd, 'data', 'updates', 'update-manifest.json'),
    path.join(path.dirname(appPath), 'data', 'updates', 'update-manifest.json'),
  ];
}

function getUpdateManifestPath() {
  for (const candidate of getUpdateManifestCandidates()) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return getUpdateManifestCandidates()[0];
}

function compareVersions(left, right) {
  const leftParts = String(left || '0.0.0').split('.').map((part) => Number.parseInt(part, 10) || 0);
  const rightParts = String(right || '0.0.0').split('.').map((part) => Number.parseInt(part, 10) || 0);
  const maxLength = Math.max(leftParts.length, rightParts.length);

  for (let index = 0; index < maxLength; index += 1) {
    const leftPart = leftParts[index] ?? 0;
    const rightPart = rightParts[index] ?? 0;
    if (leftPart > rightPart) return 1;
    if (leftPart < rightPart) return -1;
  }

  return 0;
}

function readUpdateManifest() {
  try {
    const manifestPath = getUpdateManifestPath();
    if (!fs.existsSync(manifestPath)) {
      return null;
    }

    const parsed = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    return {
      channel: String(parsed.channel || 'stable'),
      latestVersion: String(parsed.latestVersion || app.getVersion()),
      publishedAt: String(parsed.publishedAt || ''),
      downloadUrl: String(parsed.downloadUrl || '').trim(),
      entries: Array.isArray(parsed.entries) ? parsed.entries : [],
    };
  } catch {
    return null;
  }
}

export function buildUpdateFeed() {
  const manifest = readUpdateManifest();
  const currentVersion = app.getVersion();
  const latestVersion = manifest?.latestVersion || currentVersion;
  const updateAvailable = compareVersions(latestVersion, currentVersion) > 0;

  return {
    currentVersion,
    latestVersion,
    publishedAt: manifest?.publishedAt || '',
    channel: manifest?.channel || 'stable',
    updateAvailable,
    downloadUrl: manifest?.downloadUrl || '',
    entries: manifest?.entries || [],
  };
}

export function openUpdateDownload(downloadUrl) {
  const nextUrl = String(downloadUrl || '').trim();
  if (!nextUrl) {
    return { ok: false, message: 'Zatim neni publikovany zadny update balicek ke stazeni.' };
  }

  try {
    shell.openExternal(nextUrl);
    return { ok: true, message: 'Update download was opened in the default browser.' };
  } catch (error) {
    return { ok: false, message: `Update download could not be opened. ${error}` };
  }
}


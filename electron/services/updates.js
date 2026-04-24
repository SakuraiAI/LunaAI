import { app, shell } from 'electron';
import path from 'node:path';
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

let downloadTask = null;

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

function getUpdateCacheDir() {
  return path.join(app.getPath('userData'), 'updates');
}

function sanitizeFileName(value) {
  return String(value || 'update')
    .replace(/[<>:"/\\|?*\x00-\x1f]/g, '-')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
    || 'update';
}

function getPackageFileName(downloadUrl, latestVersion) {
  try {
    const parsed = new URL(downloadUrl);
    const baseName = path.basename(parsed.pathname || '');
    if (baseName && path.extname(baseName)) {
      return sanitizeFileName(baseName);
    }
  } catch {
    const baseName = path.basename(String(downloadUrl || ''));
    if (baseName && path.extname(baseName)) {
      return sanitizeFileName(baseName);
    }
  }

  return `LunaAI-${sanitizeFileName(latestVersion)}.update`;
}

function getPreparedPackagePath(feed) {
  if (!feed?.downloadUrl || !feed?.latestVersion) {
    return '';
  }
  return path.join(getUpdateCacheDir(), getPackageFileName(feed.downloadUrl, feed.latestVersion));
}

function getPreparedPackageInfo(feed) {
  const packagePath = getPreparedPackagePath(feed);
  if (!packagePath || !fs.existsSync(packagePath)) {
    return { readyToInstall: false, downloadedPath: '', downloadStatus: feed?.updateAvailable ? 'idle' : 'none' };
  }

  return {
    readyToInstall: true,
    downloadedPath: packagePath,
    downloadStatus: 'ready',
  };
}

function getLocalSourcePath(downloadUrl) {
  const nextUrl = String(downloadUrl || '').trim();
  if (!nextUrl) return '';

  if (/^file:\/\//i.test(nextUrl)) {
    return fileURLToPath(nextUrl);
  }
  if (/^[a-zA-Z]:[\\/]/.test(nextUrl) || nextUrl.startsWith('\\\\')) {
    return nextUrl;
  }
  return '';
}

async function downloadPackage(downloadUrl, destinationPath) {
  const nextUrl = String(downloadUrl || '').trim();
  if (!nextUrl) {
    return {
      ok: false,
      downloadStatus: 'missing-url',
      message: 'Update je dostupny, ale manifest zatim nema downloadUrl.',
    };
  }

  await fsp.mkdir(path.dirname(destinationPath), { recursive: true });

  const localSource = getLocalSourcePath(nextUrl);
  if (localSource) {
    await fsp.copyFile(localSource, destinationPath);
    return {
      ok: true,
      downloadStatus: 'ready',
      downloadedPath: destinationPath,
      message: 'Update balicek je pripraveny.',
    };
  }

  if (!/^https?:\/\//i.test(nextUrl)) {
    return {
      ok: false,
      downloadStatus: 'invalid-url',
      message: 'Update downloadUrl musi byt http, https, file URL nebo lokalni cesta.',
    };
  }

  const response = await fetch(nextUrl);
  if (!response.ok) {
    return {
      ok: false,
      downloadStatus: 'failed',
      message: `Stazeni update selhalo: HTTP ${response.status}.`,
    };
  }

  const arrayBuffer = await response.arrayBuffer();
  await fsp.writeFile(destinationPath, Buffer.from(arrayBuffer));

  return {
    ok: true,
    downloadStatus: 'ready',
    downloadedPath: destinationPath,
    message: 'Update balicek je pripraveny.',
  };
}

export function buildUpdateFeed() {
  const manifest = readUpdateManifest();
  const currentVersion = app.getVersion();
  const latestVersion = manifest?.latestVersion || currentVersion;
  const updateAvailable = compareVersions(latestVersion, currentVersion) > 0;
  const baseFeed = {
    currentVersion,
    latestVersion,
    publishedAt: manifest?.publishedAt || '',
    channel: manifest?.channel || 'stable',
    updateAvailable,
    downloadUrl: manifest?.downloadUrl || '',
    entries: manifest?.entries || [],
  };
  const packageInfo = getPreparedPackageInfo(baseFeed);

  return {
    ...baseFeed,
    ...packageInfo,
    autoDownloadSupported: Boolean(baseFeed.downloadUrl),
  };
}

export async function prepareUpdateDownload() {
  const feed = buildUpdateFeed();
  if (!feed.updateAvailable) {
    return {
      ...feed,
      ok: true,
      message: 'LunaAI uz bezi na nejnovejsi verzi.',
    };
  }
  if (feed.readyToInstall) {
    return {
      ...feed,
      ok: true,
      message: 'Nova verze je pripravena k instalaci.',
    };
  }
  if (!feed.downloadUrl) {
    return {
      ...feed,
      ok: false,
      downloadStatus: 'missing-url',
      message: 'Nova verze je dostupna, ale update manifest zatim nema downloadUrl.',
    };
  }
  if (downloadTask) {
    return downloadTask;
  }

  const destinationPath = getPreparedPackagePath(feed);
  downloadTask = downloadPackage(feed.downloadUrl, destinationPath)
    .then((result) => ({
      ...buildUpdateFeed(),
      ...result,
    }))
    .catch((error) => ({
      ...buildUpdateFeed(),
      ok: false,
      downloadStatus: 'failed',
      message: `Stazeni update selhalo: ${error}`,
    }))
    .finally(() => {
      downloadTask = null;
    });

  return downloadTask;
}

export async function restartAndInstallUpdate() {
  const feed = buildUpdateFeed();
  if (!feed.readyToInstall || !feed.downloadedPath) {
    return {
      ...feed,
      ok: false,
      message: 'Update jeste neni pripraveny k instalaci.',
    };
  }

  const openResult = await shell.openPath(feed.downloadedPath);
  if (openResult) {
    return {
      ...feed,
      ok: false,
      message: `Update balicek se nepodarilo otevrit: ${openResult}`,
    };
  }

  setTimeout(() => app.quit(), 300);
  return {
    ...feed,
    ok: true,
    message: 'Update installer se spousti. LunaAI se zavre.',
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

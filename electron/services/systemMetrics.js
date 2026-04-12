import os from 'node:os';
import { execFileSync } from 'node:child_process';


function captureCpuSnapshot() {
  const cpus = os.cpus();
  let idle = 0;
  let total = 0;

  for (const cpu of cpus) {
    idle += cpu.times.idle;
    total += cpu.times.user + cpu.times.nice + cpu.times.sys + cpu.times.irq + cpu.times.idle;
  }

  return { idle, total };
}

function readPrimaryGpuInfo() {
  if (process.platform !== 'win32') return { name: 'Unavailable', vendor: 'unknown' };
  try {
    const raw = execFileSync(
      'powershell.exe',
      ['-NoProfile', '-Command', "$gpu = Get-CimInstance Win32_VideoController | Select-Object -First 1 Name, AdapterCompatibility; $gpu | ConvertTo-Json -Compress"],
      { encoding: 'utf8', windowsHide: true, timeout: 2500 },
    ).trim();
    const parsed = JSON.parse(raw);
    const name = String(parsed.Name || 'Unavailable').trim() || 'Unavailable';
    const compatibility = String(parsed.AdapterCompatibility || '').toLowerCase();
    let vendor = 'unknown';
    if (name.toLowerCase().includes('nvidia') || compatibility.includes('nvidia')) vendor = 'nvidia';
    else if (name.toLowerCase().includes('amd') || name.toLowerCase().includes('radeon') || compatibility.includes('advanced micro devices')) vendor = 'amd';
    else if (name.toLowerCase().includes('intel') || compatibility.includes('intel')) vendor = 'intel';
    return { name, vendor };
  } catch {
    return { name: 'Unavailable', vendor: 'unknown' };
  }
}

function readNvidiaGpuUsagePercent() {
  try {
    const raw = execFileSync(
      'nvidia-smi',
      ['--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
      { encoding: 'utf8', windowsHide: true, timeout: 2500 },
    ).trim().split(/\r?\n/).find(Boolean) || '';
    const parsed = Number(raw.trim());
    return Number.isFinite(parsed) ? Math.max(0, Math.min(100, Math.round(parsed))) : null;
  } catch {
    return null;
  }
}

function readWindowsGpuUsagePercent() {
  if (process.platform !== 'win32') return null;
  try {
    const script = [
      "$ErrorActionPreference = 'Stop'",
      "$samples = Get-Counter '\\GPU Engine(*)\\Utilization Percentage'",
      "$sum = ($samples.CounterSamples | Measure-Object -Property CookedValue -Sum).Sum",
      "if ($sum -eq $null) { '' } else { [math]::Round([double]$sum) }",
    ].join('; ');
    const raw = execFileSync('powershell.exe', ['-NoProfile', '-Command', script], {
      encoding: 'utf8',
      windowsHide: true,
      timeout: 3000,
    }).trim();
    if (!raw) return null;
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? Math.max(0, Math.min(100, parsed)) : null;
  } catch {
    return null;
  }
}

export function createSystemMetricsReader() {
  let lastCpuSnapshot = captureCpuSnapshot();

  function readCpuUsagePercent() {
    const next = captureCpuSnapshot();
    const idleDiff = next.idle - lastCpuSnapshot.idle;
    const totalDiff = next.total - lastCpuSnapshot.total;
    lastCpuSnapshot = next;

    if (totalDiff <= 0) return 0;
    return Math.max(0, Math.min(100, Math.round((1 - idleDiff / totalDiff) * 100)));
  }

  return function readSystemMetrics() {
    const totalMemory = os.totalmem();
    const usedMemory = totalMemory - os.freemem();
    const gpuInfo = readPrimaryGpuInfo();
    const gpuUsagePercent = gpuInfo.vendor === 'nvidia' ? (readNvidiaGpuUsagePercent() ?? readWindowsGpuUsagePercent()) : readWindowsGpuUsagePercent();
    return {
      gpu: gpuInfo.name,
      gpuVendor: gpuInfo.vendor,
      cpuUsagePercent: readCpuUsagePercent(),
      gpuUsagePercent,
      memoryUsedGb: Math.max(0, Math.round(usedMemory / 1024 / 1024 / 1024)),
      memoryUsagePercent: Math.round((usedMemory / totalMemory) * 100),
    };
  };
}

import { app } from 'electron';
import path from 'node:path';
import fs from 'node:fs';
import { spawn } from 'node:child_process';


function getPythonExecutable() {
  return process.env.LUNA_PYTHON || 'python';
}

function getLunaBridgePath() {
  const appPath = app.getAppPath();
  const cwd = process.cwd();
  const candidates = [
    path.join(appPath, 'app', 'api', 'electron_bridge.py'),
    path.join(cwd, 'app', 'api', 'electron_bridge.py'),
    path.join(path.dirname(appPath), 'app', 'api', 'electron_bridge.py'),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }
  return candidates[0];
}

export function runLunaBridge(payload) {
  return new Promise((resolve) => {
    const child = spawn(getPythonExecutable(), [getLunaBridgePath()], {
      cwd: process.cwd(),
      windowsHide: true,
      env: {
        ...process.env,
        PYTHONUTF8: '1',
        PYTHONIOENCODING: 'utf-8',
      },
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';
    let settled = false;

    const finish = (result) => {
      if (settled) return;
      settled = true;
      resolve(result);
    };

    const timeoutId = setTimeout(() => {
      try {
        child.kill();
      } catch {}
      finish({ ok: false, message: 'Luna bridge timed out.' });
    }, 180000);

    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');

    child.stdout.on('data', (chunk) => {
      stdout += chunk;
    });

    child.stderr.on('data', (chunk) => {
      stderr += chunk;
    });

    child.on('error', (error) => {
      clearTimeout(timeoutId);
      finish({ ok: false, message: String(error) });
    });

    child.on('close', () => {
      clearTimeout(timeoutId);
      const raw = String(stdout || '').trim();
      const err = String(stderr || '').trim();
      if (!raw) {
        finish({ ok: false, message: err || 'Empty Luna bridge response.' });
        return;
      }
      try {
        finish(JSON.parse(raw));
      } catch {
        finish({ ok: false, message: err || raw });
      }
    });

    try {
      child.stdin.end(Buffer.from(JSON.stringify(payload || {}), 'utf8'));
    } catch (error) {
      clearTimeout(timeoutId);
      finish({ ok: false, message: String(error) });
    }
  });
}

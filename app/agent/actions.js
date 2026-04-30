import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';

import { sanitizeCommandPayload, sanitizeText } from './security.js';

function buildResult(success, action, target, message, error = null, extra = {}) {
  return {
    success,
    action,
    target,
    message,
    error,
    ...extra,
  };
}

async function openApp(command, context) {
  const target = sanitizeText(command?.target || '').toLowerCase();
  const appPath = context.appPaths[target];
  if (!appPath) {
    return buildResult(false, 'open_app', target, `App '${target}' is not configured.`, 'APP_NOT_CONFIGURED');
  }

  try {
    const child = spawn(appPath, [], {
      cwd: context.workspaceRoot,
      detached: true,
      stdio: 'ignore',
      windowsHide: true,
      shell: false,
    });
    child.unref();
    return buildResult(true, 'open_app', target, `${target} opened successfully`, null, { pid: child.pid ?? null });
  } catch (error) {
    return buildResult(false, 'open_app', target, `Failed to open ${target}`, String(error));
  }
}

async function runCommand(command, context) {
  const { executable, args, cwd } = sanitizeCommandPayload(command);
  const target = executable;
  const workingDirectory = cwd || context.workspaceRoot;

  return await new Promise((resolve) => {
    const child = spawn(executable, args, {
      cwd: workingDirectory,
      shell: false,
      windowsHide: true,
      env: {
        ...process.env,
        PYTHONUTF8: '1',
        PYTHONIOENCODING: 'utf-8',
      },
    });

    let stdout = '';
    let stderr = '';

    child.stdout?.setEncoding('utf8');
    child.stderr?.setEncoding('utf8');

    child.stdout?.on('data', (chunk) => {
      stdout += chunk;
    });
    child.stderr?.on('data', (chunk) => {
      stderr += chunk;
    });

    child.on('error', (error) => {
      resolve(buildResult(false, 'run_command', target, 'Command failed to start', String(error)));
    });

    child.on('close', (code) => {
      if (code === 0) {
        resolve(buildResult(true, 'run_command', target, 'Command completed successfully', null, {
          code,
          stdout: stdout.trim(),
          stderr: stderr.trim(),
        }));
        return;
      }
      resolve(buildResult(false, 'run_command', target, 'Command exited with an error', stderr.trim() || `Exit code ${code}`, {
        code,
        stdout: stdout.trim(),
        stderr: stderr.trim(),
      }));
    });
  });
}

async function readFileAction(command, context) {
  const target = path.resolve(sanitizeText(command?.target || command?.path || ''));
  try {
    const content = await fs.readFile(target, 'utf8');
    return buildResult(true, 'read_file', target, 'File read successfully', null, { content });
  } catch (error) {
    return buildResult(false, 'read_file', target, 'Failed to read file', String(error));
  }
}

async function writeFileAction(command, context) {
  const target = path.resolve(sanitizeText(command?.target || command?.path || ''));
  const content = typeof command?.content === 'string' ? command.content : '';
  try {
    await fs.mkdir(path.dirname(target), { recursive: true });
    await fs.writeFile(target, content, 'utf8');
    return buildResult(true, 'write_file', target, 'File written successfully');
  } catch (error) {
    return buildResult(false, 'write_file', target, 'Failed to write file', String(error));
  }
}

async function listFilesAction(command, context) {
  const target = path.resolve(sanitizeText(command?.target || command?.path || context.workspaceRoot));
  try {
    const entries = await fs.readdir(target, { withFileTypes: true });
    return buildResult(true, 'list_files', target, 'Files listed successfully', null, {
      entries: entries.map((entry) => ({
        name: entry.name,
        type: entry.isDirectory() ? 'directory' : entry.isFile() ? 'file' : 'other',
      })),
    });
  } catch (error) {
    return buildResult(false, 'list_files', target, 'Failed to list files', String(error));
  }
}

async function getSystemInfoAction() {
  return buildResult(true, 'get_system_info', 'local_pc', 'System info retrieved successfully', null, {
    system: {
      platform: process.platform,
      release: os.release(),
      arch: os.arch(),
      hostname: os.hostname(),
      cpuModel: os.cpus()[0]?.model || 'Unknown CPU',
      cpuCount: os.cpus().length,
      totalMemoryGb: Math.round(os.totalmem() / 1024 / 1024 / 1024),
      freeMemoryGb: Math.round(os.freemem() / 1024 / 1024 / 1024),
    },
  });
}

export function createAgentActions() {
  return {
    open_app: openApp,
    run_command: runCommand,
    read_file: readFileAction,
    write_file: writeFileAction,
    list_files: listFilesAction,
    get_system_info: getSystemInfoAction,
  };
}

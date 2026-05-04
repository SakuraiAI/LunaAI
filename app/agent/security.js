import path from 'node:path';

export const ALLOWED_ACTIONS = new Set([
  'open_app',
  'open_url',
  'run_command',
  'read_file',
  'write_file',
  'list_files',
  'find_app_path',
  'get_system_info',
]);

export const ALLOWED_APPS = new Set([
  'vscode',
  'chrome',
  'blender',
  'unreal',
  'discord',
  'explorer',
]);

const DANGEROUS_COMMAND_PATTERNS = [
  /^powershell(?:\.exe)?$/i,
  /^cmd(?:\.exe)?$/i,
  /\bdel\b/i,
  /\berase\b/i,
  /\brmdir\b/i,
  /\brd\b/i,
  /\bformat\b/i,
  /\bshutdown\b/i,
  /\brestart-computer\b/i,
  /\bstop-computer\b/i,
  /\breg(?:edit|\.exe)?\b/i,
  /\bsc\b\s+(?:delete|stop|config)\b/i,
  /\btakeown\b/i,
  /\bicacls\b/i,
  /\bdiskpart\b/i,
  /\bbcdedit\b/i,
  /\bsfc\b/i,
  /\bnetsh\b/i,
  /\btaskkill\b/i,
  /\bwmic\b/i,
  /\bmkfs\b/i,
  /\bchmod\b/i,
  /\bchown\b/i,
  /\bsudo\b/i,
  /\bRunAs\b/i,
  /system32/i,
  /powershell(?:\.exe)?\s+-.*(?:bypass|encodedcommand|enc)\b/i,
];

const SHELL_METACHAR_PATTERN = /[|&;><`]/;

function normalizePath(value) {
  return path.resolve(String(value || '').trim());
}

export function sanitizeText(value) {
  return String(value || '').replace(/\0/g, '').trim();
}

export function isPathInsideWorkspace(targetPath, workspaceRoot) {
  const absoluteTarget = normalizePath(targetPath);
  const absoluteWorkspace = normalizePath(workspaceRoot);
  if (absoluteTarget === absoluteWorkspace) return true;
  return absoluteTarget.startsWith(`${absoluteWorkspace}${path.sep}`);
}

export function isDangerousCommand(commandText) {
  const text = sanitizeText(commandText);
  if (!text) return true;
  if (SHELL_METACHAR_PATTERN.test(text)) return true;
  return DANGEROUS_COMMAND_PATTERNS.some((pattern) => pattern.test(text));
}

export function sanitizeCommandPayload(payload) {
  const executable = sanitizeText(payload?.command || payload?.target || '');
  const args = Array.isArray(payload?.args)
    ? payload.args.map((item) => sanitizeText(item)).filter(Boolean)
    : [];
  return {
    executable,
    args,
    cwd: sanitizeText(payload?.cwd || ''),
  };
}

export function validateAgentCommand(command, workspaceRoot) {
  const action = sanitizeText(command?.action || '').toLowerCase();
  if (!ALLOWED_ACTIONS.has(action)) {
    return { ok: false, error: `Action '${action || 'unknown'}' is not allowed.` };
  }

  if (action === 'open_app') {
    const target = sanitizeText(command?.target || '').toLowerCase();
    if (!ALLOWED_APPS.has(target)) {
      return { ok: false, error: `App '${target || 'unknown'}' is not in the whitelist.` };
    }
    return { ok: true };
  }

  if (action === 'open_url') {
    const target = sanitizeText(command?.target || command?.url || '');
    if (!/^(https?:\/\/|localhost:\d+|www\.|[a-z0-9.-]+\.[a-z]{2,})/i.test(target)) {
      return { ok: false, error: 'URL target is missing or invalid.' };
    }
    return { ok: true };
  }

  if (action === 'find_app_path') {
    const target = sanitizeText(command?.target || '').toLowerCase();
    if (!target) {
      return { ok: false, error: 'Missing app name.' };
    }
    return { ok: true };
  }

  if (action === 'run_command') {
    const { executable, args, cwd } = sanitizeCommandPayload(command);
    const allowedExecutables = new Set(['npm', 'node', 'python', 'py', 'pytest', 'dir', 'echo']);
    if (!executable) {
      return { ok: false, error: 'Missing command executable.' };
    }
    if (!allowedExecutables.has(executable.toLowerCase())) {
      return { ok: false, error: `Command '${executable}' is not in the safe executable allowlist.` };
    }
    const joined = [executable, ...args].join(' ');
    if (isDangerousCommand(joined)) {
      return { ok: false, error: 'The requested command is blocked by security policy.' };
    }
    if (/^npm$/i.test(executable)) {
      const npmStart = args.length === 1 && args[0] === 'start';
      const npmRun = args.length === 2 && args[0] === 'run' && ['dev', 'start', 'build', 'test'].includes(args[1]);
      const npmInstall = args.length >= 1 && ['install', 'i', 'add'].includes(args[0]) && args.slice(1).every((item) => /^[@a-z0-9._/-]+$/i.test(item));
      if (!npmStart && !npmRun && !npmInstall) {
        return { ok: false, error: 'Only npm start, npm run dev/start/build/test, and confirmed npm install commands are allowed.' };
      }
    }
    if (/^(python|py)$/i.test(executable)) {
      const joinedArgs = args.join(' ').replace(/\\/g, '/').toLowerCase();
      const allowedPython = ['main.py', 'src/main.py', 'app.py', '-m pytest'];
      if (!allowedPython.includes(joinedArgs)) {
        return { ok: false, error: 'Only python main.py, python src/main.py, python app.py, and python -m pytest are allowed.' };
      }
    }
    if (cwd && !isPathInsideWorkspace(cwd, workspaceRoot)) {
      return { ok: false, error: 'Command working directory must stay inside the workspace.' };
    }
    return { ok: true };
  }

  if (action === 'get_system_info') {
    return { ok: true };
  }

  const targetPath = sanitizeText(command?.target || command?.path || '');
  if (!targetPath) {
    return { ok: false, error: 'Missing target path.' };
  }

  if (action === 'write_file') {
    const content = typeof command?.content === 'string' ? command.content : '';
    if (!content && content !== '') {
      return { ok: false, error: 'Missing file content.' };
    }
  }

  return { ok: true };
}

export function requiresConfirmation(command, workspaceRoot) {
  const action = sanitizeText(command?.action || '').toLowerCase();
  const explicit = Boolean(command?.requires_confirmation);
  if (explicit) return true;

  if (action === 'write_file') {
    const targetPath = sanitizeText(command?.target || command?.path || '');
    const inside = isPathInsideWorkspace(targetPath, workspaceRoot);
    return !inside || command?.overwrite === true;
  }

  if (action === 'run_command') {
    const { executable, args } = sanitizeCommandPayload(command);
    const joined = [executable, ...args].join(' ').toLowerCase();
    if (/^npm (install|i|add)(?:\s|$)/i.test(joined)) return true;
    return !['npm start', 'python main.py', 'python src/main.py', 'dir'].includes(joined) && !joined.startsWith('echo ');
  }

  return false;
}

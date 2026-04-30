import path from 'node:path';

export const ALLOWED_ACTIONS = new Set([
  'open_app',
  'run_command',
  'read_file',
  'write_file',
  'list_files',
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

  if (action === 'run_command') {
    const { executable, args, cwd } = sanitizeCommandPayload(command);
    const allowedExecutables = new Set(['npm', 'node', 'python', 'py', 'git']);
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
    return !isPathInsideWorkspace(targetPath, workspaceRoot);
  }

  if (action === 'run_command') {
    const { executable } = sanitizeCommandPayload(command);
    return /^(npm|git|python|py|node)$/i.test(executable);
  }

  return false;
}

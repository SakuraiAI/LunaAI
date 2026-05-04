import fs from 'node:fs/promises';
import path from 'node:path';

import { createAgentActions } from './actions.js';
import { createAgentLogger } from './logger.js';
import {
  ALLOWED_ACTIONS,
  isPathInsideWorkspace,
  requiresConfirmation,
  sanitizeText,
  validateAgentCommand,
} from './security.js';

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

export class LocalPcActionAgent {
  constructor(options = {}) {
    this.workspaceRoot = path.resolve(options.workspaceRoot || process.cwd());
    this.appsConfigPath = path.resolve(options.appsConfigPath || path.join(this.workspaceRoot, 'config', 'apps.json'));
    this.logger = createAgentLogger(options.logFilePath || path.join(this.workspaceRoot, 'data', 'logs', 'agent_actions.jsonl'));
    this.actions = createAgentActions();
    this.pendingConfirmations = new Map();
  }

  async execute(rawCommand = {}) {
    const command = this.#normalizeCommand(rawCommand);

    if (command.action === 'confirm_pending') {
      return await this.confirmPending(command.confirmation_id);
    }
    if (command.action === 'cancel_pending') {
      return await this.cancelPending(command.confirmation_id);
    }

    if (!ALLOWED_ACTIONS.has(command.action)) {
      return await this.#logAndReturn(buildResult(false, command.action, command.target, 'Action is not allowed', 'ACTION_NOT_ALLOWED'));
    }

    const validation = validateAgentCommand(command, this.workspaceRoot);
    if (!validation.ok) {
      return await this.#logAndReturn(buildResult(false, command.action, command.target, validation.error, validation.error));
    }

    if (requiresConfirmation(command, this.workspaceRoot) || await this.#requiresDynamicConfirmation(command)) {
      const confirmationId = this.#buildConfirmationId(command);
      this.pendingConfirmations.set(confirmationId, command);
      return await this.#logAndReturn(buildResult(
        false,
        command.action,
        command.target,
        'Action is pending confirmation',
        null,
        {
          requires_confirmation: true,
          confirmation_id: confirmationId,
          pending: true,
        },
      ));
    }

    const pathPolicy = this.#validatePathPolicy(command);
    if (!pathPolicy.ok) {
      return await this.#logAndReturn(buildResult(false, command.action, command.target, pathPolicy.error, pathPolicy.error));
    }

    return await this.#executeValidatedCommand(command);
  }

  async confirmPending(confirmationId) {
    const cleanId = sanitizeText(confirmationId);
    const pendingCommand = this.pendingConfirmations.get(cleanId);
    if (!pendingCommand) {
      return await this.#logAndReturn(buildResult(false, 'confirm_pending', cleanId, 'Pending confirmation was not found', 'CONFIRMATION_NOT_FOUND'));
    }
    this.pendingConfirmations.delete(cleanId);
    return await this.#executeValidatedCommand({
      ...pendingCommand,
      requires_confirmation: false,
      confirmation_granted: true,
    });
  }

  async cancelPending(confirmationId) {
    const cleanId = sanitizeText(confirmationId);
    const removed = this.pendingConfirmations.delete(cleanId);
    if (!removed) {
      return await this.#logAndReturn(buildResult(false, 'cancel_pending', cleanId, 'Pending confirmation was not found', 'CONFIRMATION_NOT_FOUND'));
    }
    return await this.#logAndReturn(buildResult(true, 'cancel_pending', cleanId, 'Pending action cancelled successfully'));
  }

  async #executeValidatedCommand(command) {
    try {
      const appPaths = await this.#loadAppsConfig();
      const handler = this.actions[command.action];
      if (typeof handler !== 'function') {
        return await this.#logAndReturn(buildResult(false, command.action, command.target, 'Action handler is missing', 'HANDLER_NOT_FOUND'));
      }
      const result = await handler(command, {
        workspaceRoot: this.workspaceRoot,
        appPaths,
      });
      return await this.#logAndReturn(result);
    } catch (error) {
      return await this.#logAndReturn(buildResult(
        false,
        command.action,
        command.target,
        'Agent execution failed safely',
        String(error),
      ));
    }
  }

  #validatePathPolicy(command) {
    if (!['read_file', 'write_file', 'list_files'].includes(command.action)) {
      return { ok: true };
    }
    const targetPath = path.resolve(command.target);
    const insideWorkspace = isPathInsideWorkspace(targetPath, this.workspaceRoot);
    if (command.action === 'write_file' && !insideWorkspace) {
      if (command.confirmation_granted) {
        return { ok: true };
      }
      return { ok: false, error: 'Writing outside the workspace requires explicit confirmation.' };
    }
    if (!insideWorkspace) {
      return { ok: false, error: 'Target path is outside the workspace and is blocked.' };
    }
    return { ok: true };
  }

  async #requiresDynamicConfirmation(command) {
    if (command.confirmation_granted) {
      return false;
    }
    if (command.action !== 'write_file') {
      return false;
    }
    const targetPath = path.resolve(command.target);
    if (!isPathInsideWorkspace(targetPath, this.workspaceRoot)) {
      return true;
    }
    try {
      const stat = await fs.stat(targetPath);
      return stat.isFile();
    } catch {
      return false;
    }
  }

  async #loadAppsConfig() {
    try {
      const raw = await fs.readFile(this.appsConfigPath, 'utf8');
      const parsed = JSON.parse(raw);
      return typeof parsed === 'object' && parsed ? parsed : {};
    } catch {
      return {};
    }
  }

  #normalizeCommand(rawCommand) {
    const action = sanitizeText(rawCommand?.action || '').toLowerCase();
    return {
      ...rawCommand,
      action,
      target: sanitizeText(rawCommand?.target || rawCommand?.path || ''),
      requires_confirmation: Boolean(rawCommand?.requires_confirmation),
      confirmation_id: sanitizeText(rawCommand?.confirmation_id || ''),
    };
  }

  #buildConfirmationId(command) {
    return `agent_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
  }

  async #logAndReturn(result) {
    await this.logger.log({
      action: result.action,
      target: result.target,
      success: result.success,
      message: result.message,
      error: result.error,
      requires_confirmation: Boolean(result.requires_confirmation),
      confirmation_id: result.confirmation_id || '',
    });
    return result;
  }
}

export function createLocalPcActionAgent(options = {}) {
  return new LocalPcActionAgent(options);
}

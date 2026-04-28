const SAFE_INTERNAL_ACTIONS = {
  click_internal_ui: new Set([
    'start-share-desktop',
    'stop-share-desktop',
    'open-share-debug-panel',
    'close-share-debug-panel',
  ]),
  switch_internal_panel: new Set([
    'chat',
    'projects',
    'applications',
    'updates',
    'gallery',
    'friends',
    'settings',
  ]),
};

const CONFIRM_SYSTEM_ACTIONS = new Set([
  'open_app',
  'open_url',
  'open_path',
  'focus_window',
  'type_text',
  'mouse_click',
  'keyboard_input',
]);

const BLOCKED_ACTIONS = new Set([
  'run_shell_command',
  'delete_file',
  'remove_path',
  'write_registry',
]);

function normalizeAction(action) {
  return {
    type: String(action?.type || '').trim(),
    target: String(action?.target || '').trim(),
    args: action?.args && typeof action.args === 'object' ? action.args : {},
    requiresConfirmation: Boolean(action?.requiresConfirmation),
  };
}

export function evaluateActionPolicy(action) {
  const normalized = normalizeAction(action);

  if (!normalized.type) {
    return {
      decision: 'blocked',
      reason: 'Action type is missing.',
      action: normalized,
      layer: 'unknown',
    };
  }

  if (BLOCKED_ACTIONS.has(normalized.type)) {
    return {
      decision: 'blocked',
      reason: 'This action type is blocked by policy.',
      action: normalized,
      layer: 'system',
    };
  }

  if (SAFE_INTERNAL_ACTIONS[normalized.type]?.has(normalized.target)) {
    return {
      decision: 'safe',
      reason: 'Safe Electron-internal UI action.',
      action: {
        ...normalized,
        requiresConfirmation: false,
      },
      layer: 'electron',
    };
  }

  if (CONFIRM_SYSTEM_ACTIONS.has(normalized.type)) {
    return {
      decision: 'confirm',
      reason: 'System-level action requires explicit confirmation.',
      action: {
        ...normalized,
        requiresConfirmation: true,
      },
      layer: 'system',
    };
  }

  return {
    decision: 'blocked',
    reason: 'Action is not in the current allowlist.',
    action: normalized,
    layer: 'unknown',
  };
}

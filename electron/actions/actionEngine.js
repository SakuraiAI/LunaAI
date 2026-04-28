import { evaluateActionPolicy } from './actionPolicy.js';

function createPendingActionRecord(policy, context = {}) {
  const action = policy.action || {};
  const title = `${action.type || 'action'}${action.target ? ` -> ${action.target}` : ''}`;

  return {
    id: `action-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    active: true,
    title,
    message: policy.reason,
    action,
    layer: policy.layer,
    context,
    createdAt: new Date().toISOString(),
  };
}

export function createActionEngine({ electronActions, systemActions }) {
  let pendingAction = null;

  async function executeApprovedAction(action, context = {}) {
    const policy = evaluateActionPolicy(action);

    if (policy.decision === 'blocked') {
      return {
        ok: false,
        executed: false,
        status: 'blocked',
        message: policy.reason,
        action: policy.action,
      };
    }

    if (policy.layer === 'electron') {
      return electronActions.execute(policy.action, context);
    }

    return systemActions.execute(policy.action, context);
  }

  function getPendingAction() {
    if (!pendingAction) {
      return {
        active: false,
        title: '',
      };
    }

    return {
      ...pendingAction,
      active: true,
    };
  }

  return {
    getPendingAction,

    async execute(action, context = {}) {
      const policy = evaluateActionPolicy(action);

      if (policy.decision === 'blocked') {
        return {
          ok: false,
          executed: false,
          status: 'blocked',
          message: policy.reason,
          action: policy.action,
        };
      }

      if (policy.decision === 'confirm') {
        pendingAction = createPendingActionRecord(policy, context);
        return {
          ok: true,
          executed: false,
          status: 'confirmation_required',
          message: policy.reason,
          action: policy.action,
          confirmationRequest: {
            type: 'action_confirmation',
            message: policy.reason,
            action: policy.action,
            layer: policy.layer,
            context,
            id: pendingAction.id,
          },
          pendingAction: getPendingAction(),
        };
      }

      pendingAction = null;
      return executeApprovedAction(policy.action, context);
    },

    async confirmPendingAction() {
      if (!pendingAction) {
        return {
          ok: true,
          executed: false,
          status: 'no_pending_action',
          message: 'No Action Engine request is waiting for confirmation.',
          pendingAction: getPendingAction(),
        };
      }

      const actionToRun = pendingAction;
      pendingAction = null;
      const result = await executeApprovedAction(actionToRun.action, {
        ...actionToRun.context,
        confirmedAt: new Date().toISOString(),
        confirmationId: actionToRun.id,
      });

      return {
        ...result,
        pendingAction: getPendingAction(),
      };
    },

    cancelPendingAction() {
      const cancelled = pendingAction;
      pendingAction = null;

      return {
        ok: true,
        executed: false,
        status: cancelled ? 'cancelled' : 'no_pending_action',
        message: cancelled
          ? `Action cancelled: ${cancelled.title}`
          : 'No Action Engine request was waiting for cancellation.',
        action: cancelled?.action || null,
        pendingAction: getPendingAction(),
      };
    },
  };
}

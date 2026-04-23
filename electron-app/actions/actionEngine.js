import { evaluateActionPolicy } from "./actionPolicy.js";

export function createActionEngine({ electronActions, systemActions }) {
    return {
        async execute(action, context = {}) {
            const policy = evaluateActionPolicy(action);

            if (policy.decision === "blocked") {
                return {
                    ok: false,
                    executed: false,
                    status: "blocked",
                    message: policy.reason,
                    action: policy.action,
                };
            }

            if (policy.decision === "confirm") {
                return {
                    ok: true,
                    executed: false,
                    status: "confirmation_required",
                    message: policy.reason,
                    action: policy.action,
                    confirmationRequest: {
                        type: "action_confirmation",
                        message: policy.reason,
                        action: policy.action,
                        layer: policy.layer,
                        context,
                    },
                };
            }

            if (policy.layer === "electron") {
                return electronActions.execute(policy.action, context);
            }

            return systemActions.execute(policy.action, context);
        },
    };
}

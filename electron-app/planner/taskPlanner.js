import { routeThroughLuna } from "./lunaRouter.js";
import { routeThroughXeno } from "./xenoRouter.js";

export function createTaskPlanner() {
    return {
        plan({ userIntent = "", visionResult = {} } = {}) {
            // Vision output enters the planning flow right here.
            // Luna and Xeno receive the same visual result and can refine the action plan in sequence.
            const tags = Array.isArray(visionResult?.tags) ? visionResult.tags : [];
            const description = String(visionResult?.description || "").trim();

            let draftPlan = {
                ok: true,
                summaryParts: [],
                action: null,
                confirmationRequest: null,
                debug: {
                    userIntent,
                    visionDescription: description,
                    tags,
                },
            };

            if (tags.includes("coding_screen")) {
                draftPlan.summaryParts.push("Coding screen detected.");
                draftPlan.action = {
                    type: "click_internal_ui",
                    target: "open-debug-panel",
                    args: {},
                    requiresConfirmation: false,
                };
            } else if (tags.includes("system_settings")) {
                draftPlan.summaryParts.push("System settings screen detected.");
                draftPlan.action = {
                    type: "open_app",
                    target: "system-settings",
                    args: {},
                    requiresConfirmation: true,
                };
                draftPlan.confirmationRequest = {
                    type: "action_confirmation",
                    message: "System action suggested. Confirm before execution.",
                };
            } else {
                draftPlan.summaryParts.push("No high-confidence action was detected.");
            }

            draftPlan = routeThroughLuna({ userIntent, visionResult, draftPlan });
            draftPlan = routeThroughXeno({ userIntent, visionResult, draftPlan });

            return {
                ok: true,
                summary: draftPlan.summaryParts.join("\n") || "No structured suggestion.",
                action: draftPlan.action,
                confirmationRequest: draftPlan.confirmationRequest,
                debug: draftPlan.debug,
            };
        },
    };
}

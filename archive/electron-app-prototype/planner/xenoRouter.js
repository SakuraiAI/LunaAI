export function routeThroughXeno({ userIntent, visionResult, draftPlan }) {
    const nextPlan = {
        ...draftPlan,
        summaryParts: [...(draftPlan.summaryParts || [])],
    };

    // Xeno is the heavier reasoning layer: this is where strategic validation,
    // action safety, and plan refinement can happen before the action engine sees the plan.
    if (Array.isArray(visionResult?.tags) && visionResult.tags.includes("coding_screen")) {
        nextPlan.summaryParts.push("Xeno validates that opening the debug panel is a low-risk internal action.");
        if (!nextPlan.action) {
            nextPlan.action = {
                type: "click_internal_ui",
                target: "open-debug-panel",
                args: {},
                requiresConfirmation: false,
            };
        }
    }

    if (nextPlan.action && ["open_app", "focus_window", "type_text", "mouse_click", "keyboard_input"].includes(nextPlan.action.type)) {
        nextPlan.action = {
            ...nextPlan.action,
            requiresConfirmation: true,
        };
        nextPlan.summaryParts.push("Xeno marked the action as confirmation-only because it targets the operating system.");
    }

    return nextPlan;
}

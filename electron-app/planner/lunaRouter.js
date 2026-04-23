export function routeThroughLuna({ userIntent, visionResult, draftPlan }) {
    const normalizedIntent = String(userIntent || "").toLowerCase();
    const nextPlan = {
        ...draftPlan,
        summaryParts: [...(draftPlan.summaryParts || [])],
    };

    // Luna is the user-facing layer: this is where user phrasing and immediate task intent
    // can soften, redirect, or clarify the draft action plan before execution.
    if (normalizedIntent.includes("debug") && !nextPlan.action) {
        nextPlan.summaryParts.push("Luna noticed a direct debug-oriented intent.");
        nextPlan.action = {
            type: "click_internal_ui",
            target: "open-debug-panel",
            args: {},
            requiresConfirmation: false,
        };
    }

    if (Array.isArray(visionResult?.tags) && visionResult.tags.includes("coding_screen")) {
        nextPlan.summaryParts.push("Luna sees a coding workspace and keeps the guidance focused on developer tooling.");
    }

    return nextPlan;
}

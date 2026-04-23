export async function analyzeFrame(imageData, metadata = {}) {
    const simulatedLatencyMs = 80;
    await new Promise((resolve) => window.setTimeout(resolve, simulatedLatencyMs));

    const sizeKb = Math.max(1, Math.round(((imageData.split(",")[1] ?? "").length * 3) / 4 / 1024));
    const timestamp = metadata.capturedAt ? new Date(metadata.capturedAt).toLocaleTimeString() : "unknown time";
    const sourceName = metadata.sourceName || "shared source";
    const sourceNameNormalized = sourceName.toLowerCase();

    const tags = [];
    let description = "A general desktop screen is visible.";

    if (/code|vscode|visual studio|cursor|terminal|developer|editor/.test(sourceNameNormalized)) {
        tags.push("coding_screen", "editor");
        description = "A coding workspace is visible. The user appears to be working in an editor or developer tool.";
    } else if (/settings|control panel|system/.test(sourceNameNormalized)) {
        tags.push("system_settings");
        description = "A system settings or control surface appears to be visible.";
    } else if (/chrome|edge|firefox|browser/.test(sourceNameNormalized)) {
        tags.push("browser");
        description = "A browser window is visible.";
    }

    return {
        ok: true,
        description,
        summary: [
            description,
            `Vision input received from ${sourceName}.`,
            `Frame size: ${metadata.width}x${metadata.height}.`,
            `Compressed payload: ~${sizeKb} KB.`,
            `Captured at: ${timestamp}.`,
        ].join("\n"),
        tags,
        meta: {
            sizeKb,
            capturedAt: metadata.capturedAt || "",
            sourceName,
        },
    };
}

import { ScreenShareController } from "./screenShare.js";

window.addEventListener("DOMContentLoaded", () => {
    const controller = new ScreenShareController({
        sourceList: document.getElementById("sourceList"),
        preview: document.getElementById("preview"),
        previewEmpty: document.getElementById("previewEmpty"),
        refreshSourcesButton: document.getElementById("refreshSources"),
        startShareButton: document.getElementById("startShare"),
        stopShareButton: document.getElementById("stopShare"),
        shareState: document.getElementById("shareState"),
        frameCadence: document.getElementById("frameCadence"),
        lastFrameMeta: document.getElementById("lastFrameMeta"),
        pipelineStatus: document.getElementById("pipelineStatus"),
        visionResult: document.getElementById("visionResult"),
        plannerResult: document.getElementById("plannerResult"),
        confirmationResult: document.getElementById("confirmationResult"),
        debugPanel: document.getElementById("debugPanel"),
        debugLog: document.getElementById("debugLog"),
    });

    controller.init();
});

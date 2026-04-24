import { FramePipeline } from "./framePipeline.js";
import { analyzeFrame } from "../ai/visionClient.js";
import { createTaskPlanner } from "../planner/taskPlanner.js";

export class ScreenShareController {
    constructor(elements) {
        this.elements = elements;
        this.sources = [];
        this.selectedSourceId = "";
        this.mediaStream = null;
        this.pipeline = null;
        this.lastAutoActionKey = "";
        this.lastConfirmationKey = "";
        this.unsubscribeInternalAction = null;
        this.taskPlanner = createTaskPlanner();
    }

    init() {
        this.elements.refreshSourcesButton.addEventListener("click", () => {
            void this.loadSources();
        });

        this.elements.startShareButton.addEventListener("click", () => {
            void this.startCapture();
        });

        this.elements.stopShareButton.addEventListener("click", () => {
            void this.stopCapture();
        });

        if (window.screenShareAPI?.actionEngine?.onInternalAction) {
            this.unsubscribeInternalAction = window.screenShareAPI.actionEngine.onInternalAction((payload) => {
                this.handleInternalUiAction(payload?.action, payload?.context || {});
            });
        }

        void this.loadSources();
    }

    async loadSources() {
        this.setPipelineStatus("Loading sources");
        this.sources = await window.screenShareAPI.listSources();
        this.renderSourceList();
        this.setPipelineStatus(this.sources.length ? "Sources ready" : "No sources found");
    }

    renderSourceList() {
        const root = this.elements.sourceList;
        root.innerHTML = "";

        if (!this.sources.length) {
            root.textContent = "No screens or windows available.";
            return;
        }

        for (const source of this.sources) {
            const card = document.createElement("button");
            card.type = "button";
            card.className = `source-card${source.id === this.selectedSourceId ? " selected" : ""}`;
            card.addEventListener("click", () => {
                this.selectedSourceId = source.id;
                this.renderSourceList();
            });

            const thumbnail = document.createElement("img");
            thumbnail.className = "source-thumbnail";
            thumbnail.alt = source.name;
            thumbnail.src = source.thumbnail || "";

            const meta = document.createElement("div");
            meta.className = "source-meta";

            const name = document.createElement("div");
            name.className = "source-name";
            name.textContent = source.name;

            const kind = document.createElement("div");
            kind.className = "source-kind";
            kind.textContent = source.kind;

            meta.append(name, kind);
            card.append(thumbnail, meta);
            root.append(card);
        }
    }

    async startCapture() {
        if (!this.selectedSourceId) {
            this.setPipelineStatus("Select a source first");
            return;
        }

        await window.screenShareAPI.selectSource(this.selectedSourceId);

        try {
            this.mediaStream = await navigator.mediaDevices.getDisplayMedia({
                video: {
                    frameRate: {
                        ideal: 12,
                        max: 15,
                    },
                },
                audio: false,
            });
        } catch (error) {
            this.setPipelineStatus(`Capture failed: ${error.message}`);
            return;
        }

        const [videoTrack] = this.mediaStream.getVideoTracks();
        videoTrack?.addEventListener("ended", () => {
            void this.stopCapture();
        });

        this.elements.preview.srcObject = this.mediaStream;
        this.elements.previewEmpty.style.display = "none";
        this.elements.shareState.textContent = "Capturing";
        this.setPipelineStatus("Preparing first frame");
        this.elements.plannerResult.textContent = "Waiting for the first structured suggestion.";
        this.elements.confirmationResult.textContent = "No confirmation request.";
        this.lastAutoActionKey = "";
        this.lastConfirmationKey = "";
        this.resetDebugPanel();

        this.pipeline = new FramePipeline({
            video: this.elements.preview,
            intervalMs: 1000,
            maxWidth: 1280,
            quality: 0.72,
            format: "image/webp",
            analyzeFrame,
            sourceName: this.currentSourceName(),
            onFrameCaptured: (payload) => {
                this.elements.lastFrameMeta.textContent = `${payload.width}x${payload.height} • ${payload.sizeKb} KB`;
            },
            onAnalysis: async (result) => {
                this.elements.visionResult.textContent = result.summary;
                await this.handlePlannerResult(result);
            },
            onStatusChange: (status) => {
                this.setPipelineStatus(status);
            },
        });

        await this.pipeline.start();
    }

    async stopCapture() {
        if (this.pipeline) {
            this.pipeline.stop();
            this.pipeline = null;
        }

        if (this.mediaStream) {
            for (const track of this.mediaStream.getTracks()) {
                track.stop();
            }
            this.mediaStream = null;
        }

        this.elements.preview.srcObject = null;
        this.elements.previewEmpty.style.display = "grid";
        this.elements.shareState.textContent = "Idle";
        this.elements.lastFrameMeta.textContent = "No frame yet";
        this.setPipelineStatus("Stopped");
        this.elements.visionResult.textContent = "No analysis yet.";
        this.elements.plannerResult.textContent = "Waiting for the first structured suggestion.";
        this.elements.confirmationResult.textContent = "No confirmation request.";
        this.lastAutoActionKey = "";
        this.lastConfirmationKey = "";
        this.resetDebugPanel();
        await window.screenShareAPI.clearSource();
    }

    async handlePlannerResult(visionResult) {
        const plan = this.taskPlanner.plan({
            userIntent: "Observe the current screen and help the user with the next useful move.",
            visionResult,
        });

        this.elements.plannerResult.textContent = plan.summary || "No structured suggestion.";

        if (!plan.action) {
            this.elements.confirmationResult.textContent = "No confirmation request.";
            return;
        }

        const execution = await window.screenShareAPI.actionEngine.execute({
            action: plan.action,
            context: {
                plannerSummary: plan.summary,
                visionSummary: visionResult.summary,
                debug: plan.debug,
            },
        });

        if (execution?.confirmationRequest) {
            const requestKey = `${plan.action.type}:${plan.action.target}`;
            if (this.lastConfirmationKey !== requestKey) {
                this.lastConfirmationKey = requestKey;
            }
            this.elements.confirmationResult.textContent = JSON.stringify(execution.confirmationRequest, null, 2);
            return;
        }

        this.elements.confirmationResult.textContent = execution?.message || "No confirmation request.";
    }

    handleInternalUiAction(action, context = {}) {
        if (!action || typeof action !== "object") {
            return;
        }

        const actionKey = `${action.type}:${action.target}`;
        if (this.lastAutoActionKey === actionKey) {
            return;
        }

        if (action.type === "click_internal_ui" && action.target === "open-debug-panel") {
            this.elements.debugPanel.classList.add("is-open");
            this.appendDebugLog(`[${new Date().toLocaleTimeString()}] Debug panel opened.`);
            if (context?.plannerSummary) {
                this.appendDebugLog(`[Planner] ${context.plannerSummary}`);
            }
            this.lastAutoActionKey = actionKey;
            return;
        }

        if (action.type === "click_internal_ui" && action.target === "close-debug-panel") {
            this.elements.debugPanel.classList.remove("is-open");
            this.lastAutoActionKey = actionKey;
            return;
        }

        if (action.type === "click_internal_ui" && action.target === "refresh-sources-button") {
            void this.loadSources();
            this.lastAutoActionKey = actionKey;
            return;
        }

        if (action.type === "click_internal_ui" && action.target === "start-share-button") {
            void this.startCapture();
            this.lastAutoActionKey = actionKey;
            return;
        }

        if (action.type === "click_internal_ui" && action.target === "stop-share-button") {
            void this.stopCapture();
            this.lastAutoActionKey = actionKey;
        }
    }

    resetDebugPanel() {
        this.elements.debugPanel.classList.remove("is-open");
        this.elements.debugLog.innerHTML = "<div>Debug panel is closed.</div>";
    }

    appendDebugLog(line) {
        const entry = document.createElement("div");
        entry.textContent = line;
        this.elements.debugLog.prepend(entry);
    }

    currentSourceName() {
        return this.sources.find((item) => item.id === this.selectedSourceId)?.name ?? "Unknown source";
    }

    setPipelineStatus(status) {
        this.elements.pipelineStatus.textContent = status;
    }
}

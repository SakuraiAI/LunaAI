export class FramePipeline {
    constructor({
        video,
        intervalMs = 1000,
        maxWidth = 1280,
        quality = 0.72,
        format = "image/webp",
        analyzeFrame,
        sourceName = "Unknown source",
        onFrameCaptured = () => {},
        onAnalysis = () => {},
        onStatusChange = () => {},
    }) {
        this.video = video;
        this.intervalMs = intervalMs;
        this.maxWidth = maxWidth;
        this.quality = quality;
        this.format = format;
        this.analyzeFrame = analyzeFrame;
        this.sourceName = sourceName;
        this.onFrameCaptured = onFrameCaptured;
        this.onAnalysis = onAnalysis;
        this.onStatusChange = onStatusChange;

        this.canvas = document.createElement("canvas");
        this.context = this.canvas.getContext("2d", { willReadFrequently: true });
        this.signatureCanvas = document.createElement("canvas");
        this.signatureCanvas.width = 32;
        this.signatureCanvas.height = 18;
        this.signatureContext = this.signatureCanvas.getContext("2d", { willReadFrequently: true });

        this.timer = null;
        this.isProcessing = false;
        this.lastSignature = null;
    }

    async start() {
        await this.waitForVideoReady();
        await this.processFrame();
        this.timer = window.setInterval(() => {
            void this.processFrame();
        }, this.intervalMs);
        this.onStatusChange("Live");
    }

    stop() {
        if (this.timer) {
            window.clearInterval(this.timer);
            this.timer = null;
        }
        this.lastSignature = null;
        this.isProcessing = false;
    }

    async waitForVideoReady() {
        if (this.video.videoWidth > 0 && this.video.videoHeight > 0) {
            return;
        }

        await new Promise((resolve) => {
            this.video.addEventListener("loadedmetadata", resolve, { once: true });
        });
    }

    async processFrame() {
        if (this.isProcessing || this.video.videoWidth <= 0 || this.video.videoHeight <= 0) {
            return;
        }

        this.isProcessing = true;
        this.onStatusChange("Reading frame");

        try {
            const { width, height } = this.resolveFrameSize();
            this.canvas.width = width;
            this.canvas.height = height;
            this.context.drawImage(this.video, 0, 0, width, height);

            const signature = this.buildSignature(width, height);
            if (!this.hasMeaningfulChange(signature)) {
                this.onStatusChange("Frame unchanged");
                this.isProcessing = false;
                return;
            }

            this.lastSignature = signature;

            const imageData = this.canvas.toDataURL(this.format, this.quality);
            const result = await this.analyzeFrame(imageData, {
                width,
                height,
                sourceName: this.sourceName,
                capturedAt: new Date().toISOString(),
            });

            this.onFrameCaptured({
                width,
                height,
                sizeKb: this.estimateSizeKb(imageData),
            });
            await Promise.resolve(this.onAnalysis(result));
            this.onStatusChange("Analysis complete");
        } catch (error) {
            this.onStatusChange(`Pipeline error: ${error.message}`);
        } finally {
            this.isProcessing = false;
        }
    }

    resolveFrameSize() {
        const sourceWidth = this.video.videoWidth || 1280;
        const sourceHeight = this.video.videoHeight || 720;

        if (sourceWidth <= this.maxWidth) {
            return { width: sourceWidth, height: sourceHeight };
        }

        const ratio = this.maxWidth / sourceWidth;
        return {
            width: Math.round(sourceWidth * ratio),
            height: Math.round(sourceHeight * ratio),
        };
    }

    buildSignature(width, height) {
        this.signatureContext.clearRect(0, 0, this.signatureCanvas.width, this.signatureCanvas.height);
        this.signatureContext.drawImage(this.canvas, 0, 0, width, height, 0, 0, this.signatureCanvas.width, this.signatureCanvas.height);

        const data = this.signatureContext.getImageData(0, 0, this.signatureCanvas.width, this.signatureCanvas.height).data;
        const signature = [];

        for (let index = 0; index < data.length; index += 4) {
            const luminance = Math.round((data[index] * 0.299) + (data[index + 1] * 0.587) + (data[index + 2] * 0.114));
            signature.push(luminance);
        }

        return signature;
    }

    hasMeaningfulChange(nextSignature) {
        if (!this.lastSignature) {
            return true;
        }

        let changedPixels = 0;
        for (let index = 0; index < nextSignature.length; index += 1) {
            if (Math.abs(nextSignature[index] - this.lastSignature[index]) > 12) {
                changedPixels += 1;
            }
        }

        return changedPixels / nextSignature.length > 0.02;
    }

    estimateSizeKb(dataUrl) {
        const base64 = dataUrl.split(",")[1] ?? "";
        return Math.max(1, Math.round((base64.length * 3) / 4 / 1024));
    }
}

import { useEffect, useRef } from 'react';

export default function DesktopShareOverlay({ screenShare, onStopScreenShare }) {
  const videoRef = useRef(null);

  useEffect(() => {
    const node = videoRef.current;
    if (!node) return undefined;

    if (screenShare?.stream) {
      node.srcObject = screenShare.stream;
      node.play?.().catch(() => {});
    } else {
      node.srcObject = null;
    }

    return () => {
      if (node) node.srcObject = null;
    };
  }, [screenShare?.stream]);

  if (!screenShare?.active) return null;

  return (
    <aside className="desktop-share-overlay" aria-live="polite">
      <div className="desktop-share-overlay-head">
        <div className="desktop-share-overlay-title">
          <span className="desktop-share-overlay-live">LIVE</span>
          <strong>{screenShare.label || 'Sdílená obrazovka'}</strong>
        </div>
        <button type="button" className="desktop-share-overlay-stop" onClick={onStopScreenShare}>
          Stop
        </button>
      </div>

      <div className="desktop-share-overlay-preview">
        {screenShare.stream ? (
          <video
            ref={videoRef}
            className="desktop-share-overlay-video"
            autoPlay
            muted
            playsInline
          />
        ) : screenShare.previewUrl ? (
          <img
            src={screenShare.previewUrl}
            alt="Desktop share preview"
            className="desktop-share-overlay-image"
          />
        ) : (
          <div className="desktop-share-overlay-empty">Připravuju živý náhled...</div>
        )}
      </div>
    </aside>
  );
}

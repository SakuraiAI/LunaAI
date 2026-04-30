import Orb3D from './Orb3D';

export default function VoiceSessionOverlay({
  visible,
  listening = false,
  speaking = false,
  thinking = false,
  onToggleListen,
  onClose,
}) {
  if (!visible) return null;

  const phase = speaking
    ? 'speaking'
    : listening
      ? 'listening'
      : thinking
        ? 'thinking'
        : 'idle';

  const title = speaking
    ? 'Luna is speaking'
    : listening
      ? 'I am listening'
      : thinking
        ? 'Luna and Xeno are thinking'
        : 'Voice loop is ready';

  const detail = speaking
    ? 'Click Interrupt if you want to jump in. Otherwise Luna will continue and listen again after speaking.'
    : listening
      ? 'Speak naturally. When you stop talking, Luna will send it automatically.'
      : thinking
        ? 'Your voice and current screen context are being routed into the answer.'
        : 'Press Talk or keep Voice mode enabled to continue.';

  return (
    <div className={`voice-session-overlay is-${phase}`}>
      <div className="voice-session-card">
        <button className="voice-session-close" type="button" onClick={onClose} aria-label="Close voice mode">
          x
        </button>
        <div className="voice-session-orb-wrap">
          <div className="voice-session-connector voice-session-connector-left" />
          <div className="voice-session-orb">
            <Orb3D />
          </div>
          <div className="voice-session-connector voice-session-connector-right" />
        </div>
        <div className="voice-session-copy">
          <span>{phase}</span>
          <h2>{title}</h2>
          <p>{detail}</p>
        </div>
        <div className="voice-session-actions">
          <button className="secondary-button voice-session-talk" type="button" onClick={onToggleListen}>
            {speaking ? 'Interrupt' : listening ? 'Stop & send' : 'Talk'}
          </button>
          <button className="ghost-action voice-session-end" type="button" onClick={onClose}>
            End voice
          </button>
        </div>
      </div>
    </div>
  );
}

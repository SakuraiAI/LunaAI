import { useEffect, useRef } from 'react';
import Orb3D from './Orb3D';

function ThinkingPanel({ thinkingState }) {
  if (!thinkingState?.visible) return null;
  const lunaThinking = thinkingState?.lunaActive ?? !thinkingState?.xenoActive;
  const xenoThinking = Boolean(thinkingState?.xenoActive);
  const tracks = Array.isArray(thinkingState?.tracks) && thinkingState.tracks.length
    ? thinkingState.tracks
    : [
        ...(lunaThinking
          ? [{
              speaker: 'Luna',
              title: 'Luna',
              note: 'Analyzuje zadani a sklada odpoved.',
            }]
          : []),
        ...(xenoThinking
          ? [{
              speaker: 'Xeno',
              title: 'Xeno',
              note: 'Prochazi souvislosti, rizika a hloubejsi navrh.',
            }]
          : []),
      ];

  return (
    <div className="thinking-panel" aria-live="polite">
      <div className="thinking-panel-head">
        <span className="thinking-dot" />
        <strong>System activity</strong>
      </div>
      <div className="thinking-track-list">
        {tracks.map((track, index) => (
          <div key={`${track.speaker}-${index}`} className={`thinking-track ${track.speaker === 'Xeno' ? 'is-xeno' : ''}`}>
            <div className="thinking-track-copy">
              <span>{track.title || track.speaker}</span>
              <strong>{track.note}</strong>
            </div>
            <div className="thinking-bars" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
          </div>
        ))}
      </div>
      <p>Do chatu se ulozi jen finalni odpoved.</p>
    </div>
  );
}


function PendingActionPanel({ pendingAction, onConfirmPendingAction, onCancelPendingAction }) {
  if (!pendingAction?.active) return null;

  return (
    <div className="pending-action-panel" aria-live="polite" aria-label={pendingAction.title || 'Luna ceka na potvrzeni akce.'}>
      <div className="pending-action-buttons is-centered">
        <button type="button" className="secondary-button" onClick={onCancelPendingAction}>Cancel</button>
        <button type="button" className="primary-button" onClick={onConfirmPendingAction}>Accept</button>
      </div>
    </div>
  );
}

function ScreenSharePanel({ screenShare, onStopScreenShare }) {
  if (!screenShare?.active) return null;

  return (
    <aside className="screen-share-panel" aria-live="polite">
      <div className="screen-share-panel-head">
        <div>
          <strong>Desktop Share</strong>
          <span>{screenShare.label || 'Live preview for you, sampled frames for AI'}</span>
        </div>
        <button type="button" className="screen-share-panel-stop" onClick={onStopScreenShare}>
          Stop
        </button>
      </div>
      <div className="screen-share-panel-preview">
        {screenShare.previewUrl ? (
          <img src={screenShare.previewUrl} alt="Desktop share preview" />
        ) : (
          <div className="screen-share-panel-empty">Preparing preview…</div>
        )}
      </div>
      <p>{screenShare.status || 'Luna a Xeno ctou prubezne obnovovane framy ze sdilene obrazovky.'}</p>
      <div className={`screen-share-summary ${screenShare.summaryStatus === 'error' ? 'is-error' : ''}`}>
        <div className="screen-share-summary-head">
          <strong>Live vision summary</strong>
          <span>{screenShare.analyzing ? 'Analyzingâ€¦' : (screenShare.summaryStatusLabel || 'Ready')}</span>
        </div>
        <p>{screenShare.visionSummary || 'Waiting for the first visual readout.'}</p>
      </div>
    </aside>
  );
}

export default function ChatArea({
  messages,
  chatId = '',
  thinkingState = null,
  revealingMessage = null,
  pendingAction = null,
  onConfirmPendingAction = null,
  onCancelPendingAction = null,
  screenShare = null,
  onStopScreenShare = null,
}) {
  const hasMessages = messages.length > 0;
  const messagesPanelRef = useRef(null);
  const messagesEndRef = useRef(null);
  const lunaThinking = Boolean(thinkingState?.visible && (thinkingState?.lunaActive ?? !thinkingState?.xenoActive));
  const xenoThinking = Boolean(thinkingState?.visible && thinkingState?.xenoActive);
  const heroThinkingClass = lunaThinking && xenoThinking
    ? 'is-dual-thinking'
    : lunaThinking
      ? 'is-luna-thinking'
      : xenoThinking
        ? 'is-xeno-thinking'
        : '';

  useEffect(() => {
    if (!hasMessages && !revealingMessage?.content) return;

    const scrollToBottom = () => {
      messagesEndRef.current?.scrollIntoView({ block: 'end' });
      if (messagesPanelRef.current) {
        messagesPanelRef.current.scrollTop = messagesPanelRef.current.scrollHeight;
      }
    };

    scrollToBottom();
    const frame = window.requestAnimationFrame(scrollToBottom);
    const timeout = window.setTimeout(scrollToBottom, 80);

    return () => {
      window.cancelAnimationFrame(frame);
      window.clearTimeout(timeout);
    };
  }, [hasMessages, messages.length, chatId, thinkingState?.visible, thinkingState?.lunaActive, thinkingState?.xenoActive, revealingMessage?.content?.length]);

  if (!hasMessages && !revealingMessage?.content) {
    return (
      <section className="chat-workspace chat-workspace-empty">
        <div className="empty-chat-stage">
          <div className="empty-chat-core">
            <Orb3D />
          </div>
          <div className="empty-chat-copy">
            <h2>Co je dnes na programu?</h2>
            <p>Luna je pripravena naslouchat, premyslet a pomoci s dalsim krokem.</p>
          </div>
          <ThinkingPanel thinkingState={thinkingState} />
        </div>
      </section>
    );
  }

  return (
    <section className="chat-workspace is-live">
      <div className={`hero-panel ${hasMessages ? 'is-compact' : ''} ${heroThinkingClass}`}>
        <div className={`hero-node hero-node-left ${lunaThinking ? 'is-active' : ''} ${xenoThinking ? 'is-dual-active' : ''}`}>
          <span className="hero-node-eyebrow">Visible interface</span>
          <span className="hero-node-label">LunaAI</span>
        </div>
        <div className={`hero-center-orb ${heroThinkingClass}`}>
          <span className={`hero-connector hero-connector-left ${lunaThinking ? 'is-active' : ''} ${xenoThinking ? 'is-dual-active' : ''}`} aria-hidden="true" />
          <Orb3D />
          <span className={`hero-connector hero-connector-right ${xenoThinking ? 'is-active is-dual-active' : ''}`} aria-hidden="true" />
        </div>
        <div className={`hero-node hero-node-right ${xenoThinking ? 'is-active is-dual-active' : ''}`}>
          <span className="hero-node-eyebrow">Reasoning layer</span>
          <span className="hero-node-label">XenoAI</span>
        </div>
      </div>

      <div className="messages-panel" ref={messagesPanelRef}>
        <ScreenSharePanel screenShare={screenShare} onStopScreenShare={onStopScreenShare} />
        <ThinkingPanel thinkingState={thinkingState} />
        {messages.map((message) => (
          <article key={message.id} className={`message-row ${message.role === 'user' ? 'is-user' : 'is-assistant'}`}>
            <div className={`message-bubble ${message.role === 'user' ? 'is-user' : 'is-assistant'} ${message.author === 'Xeno' ? 'is-xeno' : ''}`}>
              <span className={`message-author ${message.author === 'Xeno' ? 'is-xeno' : ''}`}>{message.author}</span>
              <p>{message.content}</p>
            </div>
          </article>
        ))}
        {revealingMessage?.content ? (
          <article className="message-row is-assistant">
            <div className={`message-bubble is-assistant is-revealing ${(revealingMessage.author || 'Luna') === 'Xeno' ? 'is-xeno' : ''}`}>
              <span className={`message-author ${(revealingMessage.author || 'Luna') === 'Xeno' ? 'is-xeno' : ''}`}>{revealingMessage.author || 'Luna'}</span>
              <p>{revealingMessage.content}<span className="typing-caret" /></p>
            </div>
          </article>
        ) : null}
        <PendingActionPanel
          pendingAction={pendingAction}
          onConfirmPendingAction={onConfirmPendingAction}
          onCancelPendingAction={onCancelPendingAction}
        />
        <div ref={messagesEndRef} />
      </div>
    </section>
  );
}

import { useEffect, useRef } from 'react';
import Orb3D from './Orb3D';
import { repairDisplayedText } from '../utils/textRepair';

const markdownLinkPattern = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/gi;
const rawLinkPattern = /(https?:\/\/[^\s<>)]+|localhost:\d+(?:\/[^\s<>)]*)?)/gi;

function normalizeLinkHref(value) {
  const raw = String(value || '').trim();
  if (/^localhost:/i.test(raw)) {
    return `http://${raw}`;
  }
  return raw;
}

function trimLinkToken(value) {
  const token = String(value || '');
  const match = token.match(/^(.+?)([.,;:!?]+)?$/);
  if (!match) return { link: token, suffix: '' };
  return {
    link: match[1] || token,
    suffix: match[2] || '',
  };
}

function splitRawLinks(text, baseKey) {
  const parts = [];
  let cursor = 0;
  const source = String(text || '');

  for (const match of source.matchAll(rawLinkPattern)) {
    const index = match.index ?? 0;
    const fullToken = match[0] || '';
    if (index > cursor) {
      parts.push({ type: 'text', text: source.slice(cursor, index), key: `${baseKey}-text-${cursor}` });
    }

    const { link, suffix } = trimLinkToken(fullToken);
    parts.push({
      type: 'link',
      text: link,
      href: normalizeLinkHref(link),
      key: `${baseKey}-link-${index}`,
    });
    if (suffix) {
      parts.push({ type: 'text', text: suffix, key: `${baseKey}-suffix-${index}` });
    }
    cursor = index + fullToken.length;
  }

  if (cursor < source.length) {
    parts.push({ type: 'text', text: source.slice(cursor), key: `${baseKey}-text-${cursor}` });
  }

  return parts.length ? parts : [{ type: 'text', text: source, key: `${baseKey}-text-0` }];
}

function linkifyMessage(text) {
  const source = repairDisplayedText(text);
  const parts = [];
  let cursor = 0;

  for (const match of source.matchAll(markdownLinkPattern)) {
    const index = match.index ?? 0;
    const label = match[1] || match[2] || '';
    const href = match[2] || '';
    if (index > cursor) {
      parts.push(...splitRawLinks(source.slice(cursor, index), `before-${index}`));
    }
    parts.push({
      type: 'link',
      text: label,
      href,
      key: `markdown-link-${index}`,
    });
    cursor = index + (match[0] || '').length;
  }

  if (cursor < source.length) {
    parts.push(...splitRawLinks(source.slice(cursor), `after-${cursor}`));
  }

  return parts.length ? parts : [{ type: 'text', text: source, key: 'text-0' }];
}

function MessageContent({ content, trailingCaret = false }) {
  const parts = linkifyMessage(content);

  const openLink = (event, href) => {
    event.preventDefault();
    const targetUrl = normalizeLinkHref(href);
    if (window.lunaDesktop?.shell?.openExternal) {
      window.lunaDesktop.shell.openExternal(targetUrl);
      return;
    }
    window.open(targetUrl, '_blank', 'noopener,noreferrer');
  };

  return (
    <p>
      {parts.map((part) => (
        part.type === 'link' ? (
          <a
            key={part.key}
            className="message-link"
            href={normalizeLinkHref(part.href)}
            onClick={(event) => openLink(event, part.href)}
            rel="noreferrer"
          >
            {part.text}
          </a>
        ) : (
          <span key={part.key}>{part.text}</span>
        )
      ))}
      {trailingCaret ? <span className="typing-caret" /> : null}
    </p>
  );
}

function ThinkingPanel({ thinkingState }) {
  if (!thinkingState?.visible) return null;

  const lunaThinking = thinkingState?.lunaActive ?? !thinkingState?.xenoActive;
  const xenoThinking = Boolean(thinkingState?.xenoActive);
  const tracks = Array.isArray(thinkingState?.tracks) && thinkingState.tracks.length
    ? thinkingState.tracks
    : [
        ...(lunaThinking
          ? [{ speaker: 'Luna', title: 'Luna', note: 'Analyzuje zadání a skládá odpověď.' }]
          : []),
        ...(xenoThinking
          ? [{ speaker: 'Xeno', title: 'Xeno', note: 'Prochází souvislosti, rizika a hlubší návrh.' }]
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
      <p>Do chatu se uloží jen finální odpověď.</p>
    </div>
  );
}

function PendingActionPanel({ pendingAction, onConfirmPendingAction, onCancelPendingAction }) {
  if (!pendingAction?.active) return null;

  return (
    <div className="pending-action-panel" aria-live="polite" aria-label={pendingAction.title || 'Luna čeká na potvrzení akce.'}>
      <div className="pending-action-buttons is-centered">
        <button type="button" className="secondary-button" onClick={onCancelPendingAction}>Cancel</button>
        <button type="button" className="primary-button" onClick={onConfirmPendingAction}>Accept</button>
      </div>
    </div>
  );
}

function ScreenSharePanel({ screenShare, onStopScreenShare }) {
  if (!screenShare?.active) return null;

  const lastFrameLabel = screenShare.lastFrameAt
    ? new Date(screenShare.lastFrameAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : 'čekám na první frame';
  const previewVideoRef = useRef(null);

  useEffect(() => {
    const videoNode = previewVideoRef.current;
    if (!videoNode) return undefined;

    if (screenShare?.stream) {
      videoNode.srcObject = screenShare.stream;
      videoNode.play?.().catch(() => {});
    } else {
      videoNode.srcObject = null;
    }

    return () => {
      if (videoNode) {
        videoNode.srcObject = null;
      }
    };
  }, [screenShare?.stream]);

  return (
    <aside className="screen-share-panel" aria-live="polite">
      <div className="screen-share-panel-head">
        <div>
          <strong>Desktop share</strong>
          <span>{screenShare.label || 'Zivy nahled pro tebe, prubezne framy pro AI'}</span>
        </div>
        <button type="button" className="screen-share-panel-stop" onClick={onStopScreenShare}>
          Stop
        </button>
      </div>
      <div className="screen-share-meta">
        <span className="screen-share-live-badge">LIVE</span>
        <small>{screenShare.frameCount || 0} framů</small>
        <small>Poslední frame: {lastFrameLabel}</small>
      </div>
      <div className="screen-share-panel-preview">
        {screenShare.stream ? (
          <video
            ref={previewVideoRef}
            className="screen-share-live-video"
            autoPlay
            muted
            playsInline
          />
        ) : screenShare.previewUrl ? (
          <img src={screenShare.previewUrl} alt="Desktop share preview" />
        ) : (
          <div className="screen-share-panel-empty">Připravuju živý náhled...</div>
        )}
      </div>
      <p>{screenShare.status || 'Luna a Xeno čtou průběžně obnovované framy ze sdílené obrazovky.'}</p>
      <div className={`screen-share-summary ${screenShare.summaryStatus === 'error' ? 'is-error' : ''}`}>
        <div className="screen-share-summary-head">
          <strong>Live vision summary</strong>
          <span>{screenShare.analyzing ? 'Analyzuju…' : (screenShare.summaryStatusLabel || 'Ready')}</span>
        </div>
        <p>{screenShare.visionSummary || 'Čekám na první vizuální čtení.'}</p>
      </div>
    </aside>
  );
}

function ShareAutomationPanel({ shareAutomation, onCloseShareDebugPanel }) {
  const plannerSummary = String(shareAutomation?.plannerSummary || '').trim();
  const confirmationRequest = shareAutomation?.confirmationRequest;
  const action = shareAutomation?.lastAction;
  const debugTags = Array.isArray(shareAutomation?.debug?.tags) ? shareAutomation.debug.tags : [];

  if (!plannerSummary && !confirmationRequest && !shareAutomation?.debugPanelOpen) {
    return null;
  }

  return (
    <div className="screen-share-automation">
      <div className="screen-share-summary">
        <div className="screen-share-summary-head">
          <strong>Action planner</strong>
          <span>{shareAutomation?.lastActionStatus || 'idle'}</span>
        </div>
        <p>{plannerSummary || 'Planner zatim ceka na prvni jasny navrh.'}</p>
      </div>

      {confirmationRequest ? (
        <div className="screen-share-confirmation">
          <div className="screen-share-summary-head">
            <strong>Confirmation request</strong>
            <span>system</span>
          </div>
          <p>{confirmationRequest?.message || 'Systemova akce ceka na potvrzeni.'}</p>
          <small>
            {confirmationRequest?.action?.type || 'action'} {confirmationRequest?.action?.target ? `-> ${confirmationRequest.action.target}` : ''}
          </small>
        </div>
      ) : null}

      {shareAutomation?.debugPanelOpen ? (
        <div className="screen-share-debug-panel">
          <div className="screen-share-debug-head">
            <strong>Electron debug panel</strong>
            <button type="button" className="screen-share-mini-button" onClick={onCloseShareDebugPanel}>
              Close
            </button>
          </div>
          <div className="screen-share-debug-grid">
            <div>
              <span>Last action</span>
              <strong>{action ? `${action.type} -> ${action.target}` : 'No action yet'}</strong>
            </div>
            <div>
              <span>Status</span>
              <strong>{shareAutomation?.lastActionMessage || 'Waiting for the next planner pass.'}</strong>
            </div>
          </div>
          {debugTags.length ? (
            <div className="screen-share-debug-tags">
              {debugTags.map((tag) => (
                <span key={tag}>{tag}</span>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
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
  shareAutomation = null,
  onStopScreenShare = null,
  onCloseShareDebugPanel = null,
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
        <ThinkingPanel thinkingState={thinkingState} />
        {messages.map((message) => (
          <article key={message.id} className={`message-row ${message.role === 'user' ? 'is-user' : 'is-assistant'}`}>
            <div className={`message-bubble ${message.role === 'user' ? 'is-user' : 'is-assistant'} ${message.author === 'Xeno' ? 'is-xeno' : ''}`}>
              <span className={`message-author ${message.author === 'Xeno' ? 'is-xeno' : ''}`}>{message.author}</span>
              <MessageContent content={message.content} />
            </div>
          </article>
        ))}
        {revealingMessage?.content ? (
          <article className="message-row is-assistant">
            <div className={`message-bubble is-assistant is-revealing ${(revealingMessage.author || 'Luna') === 'Xeno' ? 'is-xeno' : ''}`}>
              <span className={`message-author ${(revealingMessage.author || 'Luna') === 'Xeno' ? 'is-xeno' : ''}`}>{revealingMessage.author || 'Luna'}</span>
              <MessageContent content={revealingMessage.content} trailingCaret />
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

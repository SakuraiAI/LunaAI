import { useEffect, useRef } from 'react';
import Orb3D from './Orb3D';

function ThinkingPanel({ thinkingState }) {
  if (!thinkingState?.visible) return null;

  return (
    <div className="thinking-panel" aria-live="polite">
      <div className="thinking-panel-head">
        <span className="thinking-dot" />
        <strong>System activity</strong>
      </div>
      <div className="thinking-track-list">
        <div className="thinking-track">
          <div className="thinking-track-copy">
            <span>Luna</span>
            <strong>Analyzuje zadani a sklada odpoved.</strong>
          </div>
          <div className="thinking-bars" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
        </div>
        {thinkingState.xenoActive ? (
          <div className="thinking-track is-xeno">
            <div className="thinking-track-copy">
              <span>Xeno</span>
              <strong>Prochazi souvislosti, rizika a hloubejsi navrh.</strong>
            </div>
            <div className="thinking-bars" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
          </div>
        ) : null}
      </div>
      <p>Do chatu se ulozi jen finalni odpoved.</p>
    </div>
  );
}

export default function ChatArea({ messages, chatId = '', thinkingState = null, revealingMessage = null }) {
  const hasMessages = messages.length > 0;
  const messagesPanelRef = useRef(null);
  const messagesEndRef = useRef(null);

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
  }, [hasMessages, messages.length, chatId, thinkingState?.visible, revealingMessage?.content?.length]);

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
      <div className={`hero-panel ${hasMessages ? 'is-compact' : ''}`}>
        <div className="hero-core-stack">
          <Orb3D />
          <div className="hero-core-label">AI Core</div>
        </div>
        <div className="hero-copy">
          <h2>LunaAI</h2>
          <p>System conversation remains calm, contextual, and action-ready across visible and hidden layers.</p>
          <div className="hero-signal-row">
            <span>Luna online</span>
            <span>Xeno linked</span>
            <span>Local bridge ready</span>
          </div>
        </div>
      </div>

      <div className="messages-panel" ref={messagesPanelRef}>
        <ThinkingPanel thinkingState={thinkingState} />
        {messages.map((message) => (
          <article key={message.id} className={`message-row ${message.role === 'user' ? 'is-user' : 'is-assistant'}`}>
            <div className={`message-bubble ${message.role === 'user' ? 'is-user' : 'is-assistant'}`}>
              <span className="message-author">{message.author}</span>
              <p>{message.content}</p>
            </div>
          </article>
        ))}
        {revealingMessage?.content ? (
          <article className="message-row is-assistant">
            <div className="message-bubble is-assistant is-revealing">
              <span className="message-author">{revealingMessage.author || 'Luna'}</span>
              <p>{revealingMessage.content}<span className="typing-caret" /></p>
            </div>
          </article>
        ) : null}
        <div ref={messagesEndRef} />
      </div>
    </section>
  );
}

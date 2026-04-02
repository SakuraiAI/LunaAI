import Orb3D from './Orb3D';

export default function ChatArea({ messages }) {
  const hasMessages = messages.length > 0;

  if (!hasMessages) {
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

      <div className="messages-panel">
        {messages.map((message) => (
          <article key={message.id} className={`message-row ${message.role === 'user' ? 'is-user' : 'is-assistant'}`}>
            <div className={`message-bubble ${message.role === 'user' ? 'is-user' : 'is-assistant'}`}>
              <span className="message-author">{message.author}</span>
              <p>{message.content}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

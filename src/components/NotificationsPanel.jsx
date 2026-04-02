export default function NotificationsPanel({ visible, items, onClose }) {
  return (
    <div className={`notifications-panel ${visible ? 'is-open' : ''}`}>
      <div className="notifications-panel-card">
        <div className="notifications-panel-head">
          <div>
            <h3>Notifications</h3>
            <p>Pozvanky, zadosti a systemove udalosti pro LunaAI.</p>
          </div>
          <button type="button" className="secondary-button notifications-close" onClick={onClose}>Close</button>
        </div>

        <div className="notifications-list">
          {items.length === 0 ? (
            <div className="notifications-empty">
              <strong>No notifications</strong>
              <p>Nove pozvanky a udalosti se objevi tady.</p>
            </div>
          ) : (
            items.map((item) => (
              <article key={item.id} className="notification-item">
                <div className="notification-item-copy">
                  <strong>{item.title}</strong>
                  <p>{item.detail}</p>
                </div>
                <span className={`notification-kind is-${item.kind}`}>{item.label}</span>
              </article>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function BellIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="topbar-icon-glyph">
      <path d="M12 4.5a4 4 0 0 0-4 4v2.3c0 .9-.3 1.8-.9 2.5L5.8 15a1 1 0 0 0 .8 1.6h10.8a1 1 0 0 0 .8-1.6l-1.3-1.7a4.1 4.1 0 0 1-.9-2.5V8.5a4 4 0 0 0-4-4Z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M10.2 18.5a2 2 0 0 0 3.6 0" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

export default function TopBar({
  collapsed,
  onToggleSidebar,
  profileName,
  onOpenProfile,
  onOpenNotifications,
  notificationCount,
  onWindowAction,
}) {
  return (
    <header className="topbar app-drag-region">
      <div className="topbar-left">
        <button className="topbar-toggle app-no-drag" type="button" onClick={onToggleSidebar} aria-label="Toggle sidebar">
          {collapsed ? '+' : '-'}
        </button>
        <div className="brand-mark">
          <div className="brand-mark-inner" />
        </div>
        <div className="brand-copy">
          <h1>LunaAI</h1>
          <p>Internal AI system dashboard</p>
        </div>
      </div>

      <div className="topbar-right">
        <div className="window-controls app-no-drag">
          <button className="window-button app-no-drag" type="button" onClick={() => onWindowAction('minimize')} aria-label="Minimize">-</button>
          <button className="window-button app-no-drag" type="button" onClick={() => onWindowAction('maximize')} aria-label="Maximize">+</button>
          <button className="window-button app-no-drag is-close" type="button" onClick={() => onWindowAction('close')} aria-label="Close">x</button>
        </div>
        <button className="notification-trigger app-no-drag" type="button" onClick={onOpenNotifications} aria-label="Open notifications">
          <BellIcon />
          {notificationCount > 0 ? <span className="notification-badge">{notificationCount}</span> : null}
        </button>
        <button className="profile-trigger app-no-drag" type="button" onClick={onOpenProfile}>
          <span className="profile-avatar">{profileName?.charAt(0) || 'L'}</span>
          <span className="profile-copy">
            <strong>{profileName}</strong>
            <span>Profile</span>
          </span>
        </button>
      </div>
    </header>
  );
}

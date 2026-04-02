export default function AppShell({ topbar, sidebar, main, profilePanel, notificationsPanel, contextMenu }) {
  return (
    <div className="app-shell">
      {topbar}
      <div className="app-shell-body">
        {sidebar}
        <main className="app-main">{main}</main>
      </div>
      {profilePanel}
      {notificationsPanel}
      {contextMenu}
    </div>
  );
}
